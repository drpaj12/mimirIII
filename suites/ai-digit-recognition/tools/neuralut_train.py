"""I6: train a NeuraLUT-Assemble MNIST model on CPU with the NeuraLUT library (read by path).

usage: neuralut_train.py <setting> <out_dir> [--dense-epochs N] [--epochs N] [--batch N]
                         [--max-minutes M]
Runs in the nnlut venv (torch CPU, brevitas, neuralut). Writes <out_dir>/{imask.pth,
checkpoint.pth,train.log}. The model class is NeuraLUT's `datasets/mnist/models.py` (imported
from the checkout, never copied). The training loop is ours (theirs needs CUDA and wandb): same
optimiser, scheduler, loss and group regulariser; the dense phase picks the connections
(top-|w|), the sparse phase trains from scratch with those connections (as their train.py does).

Input = the pixel values the testbench streams: x = q * S_IN with q the int8 of
`golden/lenet_int8.py:quant_image` (so train and test see exactly what the hardware wrapper sees).
"""

import argparse
import importlib
import importlib.util
import os
import sys
import time
import types

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "tools"))
LC = importlib.import_module("lutnn_common")

torch.set_num_threads(int(os.environ.get("OMP_NUM_THREADS", "4")))


def load_models(neuralut_root):
    # models.py imports pyverilator (Verilator co-simulation, needs tkinter, not installed and not
    # used here: our Verilog check is the testbench). Stub the module.
    sys.modules.setdefault("pyverilator", types.SimpleNamespace(PyVerilator=object))
    path = os.path.join(neuralut_root, "datasets/mnist/models.py")
    spec = importlib.util.spec_from_file_location("neuralut_mnist_models", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.MnistNeqModel


def no_cuda(model):
    """QuantBrevitasActivation defaults to cuda=True in the checkout's models.py; force CPU."""
    for m in model.modules():
        if m.__class__.__name__ == "QuantBrevitasActivation":
            m.cuda = False
        if m.__class__.__name__ == "SparseLinearNeq":
            m.cuda = False


def regularizer(model, cfg, tcfg):
    r = 0
    for i in range(len(cfg["hidden_layers"]) + 1):
        mod = model.module_list[i]
        if getattr(mod, "dense_forward", False):
            l1 = torch.cat(
                (mod.res2_dense.weight.abs().sum(-1), mod.fc1_dense.weight.abs().sum(-1)), 0
            )
            r = r + tcfg["wd"] * (torch.pow(2, tcfg["wd1"] * l1) - 1).sum()
    return r


def get_input_mask(model, cfg):
    max_fan = max(
        cfg["hidden_fanin"], cfg["input_fanin"], cfg["output_fanin"], cfg["support_fanin"]
    )
    rows = []
    for i in range(len(cfg["hidden_layers"]) + 1):
        mod = model.module_list[i]
        if getattr(mod, "dense_forward", False):
            w = mod.res2_dense.weight
            for r in range(w.size(0)):
                idx = torch.topk(w[r].abs(), mod.fan_in).indices
                rows.append(
                    torch.cat((idx, torch.zeros(max_fan - len(idx), dtype=torch.long))).unsqueeze(0)
                )
    return torch.cat(rows, 0).long()


def evaluate(model, x, y, bs=500):
    model.eval()
    ok = 0
    with torch.no_grad():
        for i in range(0, len(x), bs):
            ok += (model(x[i : i + bs]).argmax(1) == y[i : i + bs]).sum().item()
    return 100.0 * ok / len(x)


def run_phase(model, cfg, tcfg, x, y, xt, yt, epochs, dense, log, deadline, batch, ckpt):
    opt_params = {"decay": [], "nodecay": []}
    for n, p in model.named_parameters():
        if p.requires_grad:
            key = "nodecay" if any(s in n for s in ("bn", "bias", "learned_value")) else "decay"
            opt_params[key].append(p)
    opt = optim.AdamW(
        [
            {"params": opt_params["decay"], "weight_decay": tcfg["weight_decay"]},
            {"params": opt_params["nodecay"], "weight_decay": 0.0},
        ],
        lr=tcfg["learning_rate"],
        betas=(0.5, 0.999),
    )
    steps = (len(x) + batch - 1) // batch
    sched = optim.lr_scheduler.CosineAnnealingWarmRestarts(
        opt, T_0=max(1, steps * max(1, epochs)), T_mult=1
    )
    crit = nn.CrossEntropyLoss()
    best = 0.0
    for ep in range(epochs):
        model.train()
        perm = torch.randperm(len(x))
        t0 = time.time()
        for b in range(steps):
            idx = perm[b * batch : (b + 1) * batch]
            opt.zero_grad()
            out = model(x[idx])
            loss = crit(out, y[idx])
            if dense:
                loss = loss + regularizer(model, cfg, tcfg)
            loss.backward()
            opt.step()
            sched.step()
            if time.time() > deadline:
                break
        acc = evaluate(model, xt, yt)
        log(
            f"{'dense' if dense else 'sparse'} epoch {ep + 1}/{epochs} test_acc {acc:.2f} "
            f"epoch_s {time.time() - t0:.0f}"
        )
        if not dense:
            torch.save({"model_dict": model.state_dict(), "test_accuracy": acc, "epoch": ep}, ckpt)
            best = max(best, acc)
        if time.time() > deadline:
            log("time budget reached, stopping this phase")
            break
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("setting")
    ap.add_argument("out")
    ap.add_argument("--dense-epochs", type=int)
    ap.add_argument("--epochs", type=int)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--max-minutes", type=float, default=1e9, help="wall budget over both phases")
    a = ap.parse_args()
    s = LC.SETTINGS[a.setting]
    cfg = dict(s["model"])
    tcfg = dict(s["train"])
    if a.dense_epochs is not None:
        tcfg["dense_epochs"] = a.dense_epochs
    if a.epochs is not None:
        tcfg["epochs"] = a.epochs
    os.makedirs(a.out, exist_ok=True)
    log_path = os.path.join(a.out, "train.log")

    def log(msg):
        print(msg, flush=True)
        with open(log_path, "a") as logf:
            logf.write(msg + "\n")

    random_seed = tcfg["seed"]
    torch.manual_seed(random_seed)
    np.random.seed(random_seed)
    MnistNeqModel = load_models(LC.NEURALUT_ROOT)
    x, y, xt, yt = LC.torch_data()
    cfg.update(input_length=784, output_length=10, cuda=False)
    t_start = time.time()
    deadline = t_start + a.max_minutes * 60
    log(f"setting {a.setting} cfg {cfg} train {tcfg} batch {a.batch}")

    cfg["dense_forward"] = True
    cfg["imask"] = torch.tensor([])
    dense = MnistNeqModel(cfg)
    no_cuda(dense)
    run_phase(
        dense,
        cfg,
        tcfg,
        x,
        y,
        xt,
        yt,
        tcfg["dense_epochs"],
        True,
        log,
        t_start + 0.5 * a.max_minutes * 60 if a.max_minutes < 1e8 else deadline,
        a.batch,
        None,
    )
    imask = get_input_mask(dense, cfg)
    torch.save(imask, os.path.join(a.out, "imask.pth"))
    dense_s = time.time() - t_start
    log(f"dense phase {dense_s:.0f} s")
    del dense

    cfg["dense_forward"] = False
    cfg["imask"] = imask
    model = MnistNeqModel(cfg)
    no_cuda(model)
    best = run_phase(
        model,
        cfg,
        tcfg,
        x,
        y,
        xt,
        yt,
        tcfg["epochs"],
        False,
        log,
        deadline,
        a.batch,
        os.path.join(a.out, "checkpoint.pth"),
    )
    log(
        f"done: best sparse test acc {best:.2f}, total {time.time() - t_start:.0f} s "
        f"(dense {dense_s:.0f} s)"
    )


if __name__ == "__main__":
    main()
