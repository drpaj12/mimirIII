"""I7: train a binarised MLP (weights and activations +-1, batch norm per layer) with a
straight-through estimator in plain torch, on the testbench's pixels (q * S_IN, as I6/I8), then
fold batch norm into integer thresholds and write the integer network to <out_dir>/<net>.npz.

usage: bnn_train.py <net: M|S> <out_dir> [--epochs 60] [--threads 4]
Runs in the nnlut venv (torch 2.4.0 CPU). Nets: gen_bnn.NETS. Writes <out_dir>/<net>.npz
(W<k> = +-1 weights as int8 (out, in), T<k> = integer thresholds) and <out_dir>/<net>-train.json.

Hidden neuron: bit = sign(BN(w . x)); with w, x in +-1 the dot product is 2 pc - nin (pc =
XNOR popcount), and BN folds to `pc >= T`; a negative BN scale flips the neuron's weights.
First layer, mode "int8": x = q (the streamed int8 pixel), `acc = sum(+-q) >= T`.
First layer, mode "bin": x = +1 if q >= QBIN else -1. Last layer: no BN, logits = dot / sqrt(nin),
argmax of the integer pc at inference (first maximum wins).
"""

import argparse
import importlib
import json
import math
import os
import sys
import time

import numpy as np

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
LC = importlib.import_module("lutnn_common")
GB = importlib.import_module("gen_bnn")

QSCALE = 64.0  # training input of the int8 mode is q / 64 (batch norm absorbs the scale)


def build(torch, net):
    nn = torch.nn

    class Sign(torch.autograd.Function):
        @staticmethod
        def forward(ctx, x):
            ctx.save_for_backward(x)
            return torch.where(x >= 0, torch.ones_like(x), -torch.ones_like(x))

        @staticmethod
        def backward(ctx, g):
            (x,) = ctx.saved_tensors
            return g * (x.abs() <= 1).to(g.dtype)

    class BinLinear(nn.Module):
        def __init__(self, nin, nout):
            super().__init__()
            self.weight = nn.Parameter(torch.empty(nout, nin).uniform_(-1, 1))

        def forward(self, x):
            return x @ Sign.apply(self.weight).t()

    class Net(nn.Module):
        def __init__(self):
            super().__init__()
            sizes = net["layers"]
            pairs = zip(sizes[:-1], sizes[1:], strict=True)
            self.lin = nn.ModuleList(BinLinear(a, b) for a, b in pairs)
            self.bn = nn.ModuleList(nn.BatchNorm1d(b) for b in sizes[1:-1])
            self.scale = 1.0 / math.sqrt(sizes[-2])

        def forward(self, q):
            if net["in_mode"] == "int8":
                x = q / QSCALE
            else:
                x = torch.where(q >= GB.QBIN, torch.ones_like(q), -torch.ones_like(q))
            for lin, bn in zip(self.lin[:-1], self.bn, strict=True):
                x = Sign.apply(bn(lin(x)))
            return self.lin[-1](x) * self.scale

    return Net(), Sign


def fold(model, net):
    """Integer network from the trained model (float64 fold of the running batch-norm stats)."""
    out = {}
    nl = len(model.lin)
    for k in range(nl):
        w = np.where(model.lin[k].weight.detach().numpy() >= 0, 1, -1).astype(np.int64)
        nin = w.shape[1]
        if k == nl - 1:
            out[f"W{k}"] = w.astype(np.int8)
            continue
        bn = model.bn[k]
        mu = bn.running_mean.numpy().astype(np.float64)
        sd = np.sqrt(bn.running_var.numpy().astype(np.float64) + bn.eps)
        ga = bn.weight.detach().numpy().astype(np.float64)
        be = bn.bias.detach().numpy().astype(np.float64)
        with np.errstate(divide="ignore", invalid="ignore"):
            t = np.where(ga != 0, mu - be * sd / ga, np.where(be >= 0, -np.inf, np.inf))
        flip = ga < 0
        t = np.where(flip, -t, t)  # -dot >= -t
        w = np.where(flip[:, None], -w, w)
        if k == 0 and net["in_mode"] == "int8":
            acc_max = 127 * nin
            ti = np.ceil(np.clip(t * QSCALE, -acc_max - 1, acc_max + 1)).astype(np.int64)
        else:
            ti = np.ceil((np.clip(t, -nin - 2, nin + 2) + nin) / 2).astype(np.int64)
            ti = np.clip(ti, 0, nin + 1)
        out[f"W{k}"] = w.astype(np.int8)
        out[f"T{k}"] = ti
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("net")
    ap.add_argument("out_dir")
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--batch", type=int, default=100)
    ap.add_argument("--lr", type=float, default=0.003)
    a = ap.parse_args()
    import torch

    torch.set_num_threads(a.threads)
    torch.manual_seed(7)
    net = GB.NETS[a.net]
    model, _ = build(torch, net)
    qtr, ytr = LC.load("train")
    qte, yte = LC.load("test")
    xtr = torch.from_numpy(qtr.astype(np.float32))
    ytr_t = torch.from_numpy(ytr)
    xte = torch.from_numpy(qte.astype(np.float32))
    opt = torch.optim.Adam(model.parameters(), lr=a.lr)
    nb = (len(xtr) + a.batch - 1) // a.batch
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=a.epochs * nb, eta_min=1e-5)
    t0 = time.time()
    log = []
    for ep in range(a.epochs):
        model.train()
        perm = torch.randperm(len(xtr))
        tot = 0.0
        for b in range(nb):
            idx = perm[b * a.batch : (b + 1) * a.batch]
            opt.zero_grad()
            loss = torch.nn.functional.cross_entropy(model(xtr[idx]), ytr_t[idx])
            loss.backward()
            opt.step()
            sched.step()
            with torch.no_grad():
                for lin in model.lin:
                    lin.weight.clamp_(-1, 1)
            tot += float(loss)
        model.eval()
        with torch.no_grad():
            acc = float((model(xte).argmax(1).numpy() == yte).mean())
        log.append({"epoch": ep + 1, "loss": tot / nb, "test_top1_float": acc})
        print(json.dumps(log[-1]), flush=True)
    train_s = time.time() - t0
    os.makedirs(a.out_dir, exist_ok=True)
    params = fold(model, net)
    np.savez(os.path.join(a.out_dir, f"{a.net}.npz"), **params)
    cls, _ = GB.model_forward(net, params, qte)
    info = {
        "net": a.net,
        "layers": net["layers"],
        "in_mode": net["in_mode"],
        "epochs": a.epochs,
        "batch": a.batch,
        "lr": a.lr,
        "train_s": round(train_s, 1),
        "float_top1": log[-1]["test_top1_float"],
        "int_model_top1": float((cls == yte).mean()),
        "note": "last-epoch checkpoint; the test set is read each epoch for the log only",
    }
    with open(os.path.join(a.out_dir, f"{a.net}-train.json"), "w") as f:
        json.dump(info, f, indent=1, sort_keys=True)
    print(json.dumps(info, sort_keys=True))


if __name__ == "__main__":
    main()
