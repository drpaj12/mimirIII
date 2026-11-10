"""I6: trained NeuraLUT model -> Verilog (their generator), our `mnist_top` wrapper, vectors.

usage: neuralut_gen.py <setting> <train_dir> <build_dir> [--registers] [--vec-tiers quick,full]
Runs in the nnlut venv. Reads <train_dir>/{checkpoint.pth,imask.pth} (tools/neuralut_train.py).
Writes into <build_dir> (outside the repository, never committed):
  neuralut_all.v    the library generator's module_list_to_verilog_module output, one file
  mnist_top.v       our wrapper: pixel quantiser ROM, bit buffer, `neuralut`, argmax, done
  vec/<tier>/       vec_*.hex for tb/mnist_tb.v; the "golden" is THIS model (docs/I6-NEURALUT.md)
  gen.json          accuracies (float model, LUT model, numpy table model), sha256 of the files
The numpy table model (independent of the library's lut_forward) is the reference the Verilog
must equal.
"""

import argparse
import importlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import torch

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
LC = importlib.import_module("lutnn_common")
NT = importlib.import_module("neuralut_train")


def build_models(setting, train_dir):
    s = LC.SETTINGS[setting]
    cfg = dict(s["model"])
    cfg.update(input_length=784, output_length=10, cuda=False, dense_forward=False)
    cfg["imask"] = torch.load(os.path.join(train_dir, "imask.pth"))
    cls = NT.load_models(LC.NEURALUT_ROOT)
    ck = torch.load(os.path.join(train_dir, "checkpoint.pth"), map_location="cpu")
    float_model, lut_model = cls(cfg), cls(cfg)
    for m in (float_model, lut_model):
        NT.no_cuda(m)
        m.load_state_dict(ck["model_dict"])
    return cfg, float_model, lut_model, ck


def acc(model, x, y, bs=250):
    model.eval()
    preds = []
    with torch.no_grad():
        for i in range(0, len(x), bs):
            out = model(x[i : i + bs])
            preds.append(out.argmax(1))
    p = torch.cat(preds)
    return 100.0 * (p == y).float().mean().item(), p


def state_start(quant):
    """Smallest state value of a quantiser = the value whose Verilog code is 0."""
    return int(quant.get_bin_state_space(False)[0])


def input_codes(lut_model):
    """Code (0..2^B-1) of every pixel for every q in -127..127: (255, 784) ints.
    From the model's own input quantiser (first layer input_quant: bn_in + bias + hardtanh)."""
    iq = lut_model.module_list[0].input_quant
    iq.bin_output()
    qs = np.arange(-127, 128)
    x = torch.from_numpy((qs[:, None] * LC.S_IN * np.ones((1, 784))).astype(np.float32))
    with torch.no_grad():
        v = iq(x).numpy().astype(np.int64)
    return v - state_start(iq)


def thresholds(codes):
    """Per pixel: (used?, T_u, c0). codes: (255,784) in {0,1} (input_bitwidth 1), indexed by q+127.
    code(q) = c0 for q+128 < T_u else 1-c0 (T_u in 1..256; 256 = never). Asserts a monotone step."""
    out = []
    for j in range(codes.shape[1]):
        c = codes[:, j]
        flips = np.nonzero(np.diff(c))[0]
        assert len(flips) <= 1, f"pixel {j}: input code not a single step"
        c0 = int(c[0])
        t = (
            int(flips[0]) + 1 + 1 if len(flips) else 256
        )  # first index with new code, +1: q=-127 is u=1
        out.append((t, c0))
    return out


def layer_tables(lut_model):
    """Per layer: imask (N,F), S states per input, start_in/out, table (N, S**F) of out codes."""
    res = []
    for m in lut_model.module_list:
        tt = m.neuron_truth_tables
        idx = np.stack([t[0].numpy() for t in tt]).astype(np.int64)
        perm = tt[0][1]
        s_in = int(perm.max() - perm.min() + 1)
        start_in = int(perm.min())
        start_out = state_start(m.output_quant)
        tab = np.stack([t[3].numpy().astype(np.int64) for t in tt]) - start_out
        res.append(
            {
                "idx": idx,
                "S": s_in,
                "start_in": start_in,
                "start_out": start_out,
                "tab": tab,
                "F": idx.shape[1],
                "out_bits": int(m.output_quant.get_scale_factor_bits(False)[1]),
            }
        )
    return res


def table_model(layers, codes0):
    """Numpy evaluation of the truth tables. codes0: (n, 784) input codes -> (n, 10) out codes."""
    c = codes0
    for L in layers:
        g = c[:, L["idx"]]  # (n, N, F)
        p = (g * (L["S"] ** np.arange(L["F"]))).sum(-1)  # first input = least significant (library)
        c = L["tab"][np.arange(L["tab"].shape[0])[None, :], p]
    return c


def argmax_first(sc):
    return np.argmax(sc, axis=1)  # first maximum wins, as the wrapper


def wrapper_verilog(layers, thr, used, n_stage, in_bits_per_pix=1):
    """mnist_top: ROM-driven pixel quantiser, compacted bit buffer of the used pixels, neuralut,
    argmax, result registers. n_stage = pipeline stages inside neuralut (0 = combinational)."""
    assert in_bits_per_pix == 1
    ranks, k = {}, 0
    for j in range(784):
        if used[j]:
            ranks[j] = k
            k += 1
    nu = k
    ob = layers[-1]["out_bits"]
    so = layers[-1]["start_out"] & 0xFF
    lines = []
    w = lines.append
    w("// Generated by tools/neuralut_gen.py (do not edit). I6 NeuraLUT wrapper (P0 interface).")
    w("module mnist_top (input clk, input rst, input start, input in_valid, input [7:0] in_data,")
    w("                  output in_ready, output reg done, output reg [3:0] pred,")
    w("                  output reg [79:0] scores);")
    w(f"  localparam NU = {nu};   // pixels the first layer reads (the others are not stored)")
    w("  reg loading;")
    w("  reg [9:0] cnt;")
    w("  reg waiting;")
    w("  reg [3:0] wcnt;")
    w("  reg [NU-1:0] sh;")
    w("  assign in_ready = loading;")
    w("  // per pixel: used flag, threshold on u = q + 128 (T in 1..256), code below threshold")
    w("  reg use_r;")
    w("  reg [8:0] thr_r;")
    w("  reg c0_r;")
    w("  always @(cnt) begin")
    w("    use_r = 1'b0; thr_r = 9'd256; c0_r = 1'b0;")
    w("    case (cnt)")
    for j in range(784):
        if used[j]:
            t, c0 = thr[j]
            w(f"      10'd{j}: begin use_r = 1'b1; thr_r = 9'd{t}; c0_r = 1'b{c0}; end")
    w("      default: begin use_r = 1'b0; thr_r = 9'd256; c0_r = 1'b0; end")
    w("    endcase")
    w("  end")
    w("  wire [8:0] u = {1'b0, in_data ^ 8'h80};   // q + 128 for the signed pixel byte")
    w("  wire code = ((u >= thr_r) ? ~c0_r : c0_r);")
    w("  wire [783:0] M0;")
    for j in range(784):
        w(f"  assign M0[{j}] = " + (f"sh[{nu - 1 - ranks[j]}];" if used[j] else "1'b0;"))
    nl = len(layers)
    w(f"  wire [{10 * ob - 1}:0] M{nl};")
    w(f"  neuralut core (.M0(M0), .clk(clk), .rst(rst), .M{nl}(M{nl}));")
    for kk in range(10):
        w(f"  wire [{ob - 1}:0] oc{kk} = M{nl}[{kk * ob + ob - 1}:{kk * ob}];")
    w("  // argmax over the output codes (offset binary: order-preserving), first maximum wins")
    w(f"  wire [{ob - 1}:0] v0 = oc0;")
    w("  wire [3:0] b0 = 4'd0;")
    for kk in range(1, 10):
        w(f"  wire g{kk} = (oc{kk} > v{kk - 1});")
        w(f"  wire [{ob - 1}:0] v{kk} = g{kk} ? oc{kk} : v{kk - 1};")
        w(f"  wire [3:0] b{kk} = g{kk} ? 4'd{kk} : b{kk - 1};")
    cap = n_stage
    w("  always @(posedge clk) begin")
    w("    if (rst) begin")
    w("      loading <= 1'b0; cnt <= 10'd0; waiting <= 1'b0; wcnt <= 4'd0; done <= 1'b0;")
    w("      pred <= 4'd0; scores <= 80'd0; sh <= {NU{1'b0}};")
    w("    end else begin")
    w("      if (start) begin loading <= 1'b1; cnt <= 10'd0; done <= 1'b0; waiting <= 1'b0; end")
    w("      else if (loading && in_valid) begin")
    w("        if (use_r) sh <= {sh[NU-2:0], code};")
    w("        cnt <= cnt + 10'd1;")
    w("        if (cnt == 10'd783) begin loading <= 1'b0; waiting <= 1'b1; wcnt <= 4'd0; end")
    w("      end else if (waiting) begin")
    w(f"        if (wcnt == 4'd{cap}) begin")
    w("          waiting <= 1'b0; done <= 1'b1; pred <= b9;")
    for kk in range(10):
        w(f"          scores[{8 * kk + 7}:{8 * kk}] <= {{{8 - ob}'d0, oc{kk}}} + 8'd{so};")
    w("        end else wcnt <= wcnt + 4'd1;")
    w("      end")
    w("    end")
    w("  end")
    w("endmodule")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("setting")
    ap.add_argument("train_dir")
    ap.add_argument("build_dir")
    ap.add_argument(
        "--registers", action="store_true", help="registers between layers (library option)"
    )
    ap.add_argument("--tiers", default="quick,full")
    a = ap.parse_args()
    os.makedirs(a.build_dir, exist_ok=True)
    cfg, fmodel, lmodel, ck = build_models(a.setting, a.train_dir)
    q_te, y_te = LC.load("test")
    x_te = torch.from_numpy((q_te * LC.S_IN).astype(np.float32))
    yt = torch.from_numpy(y_te)
    info = {
        "setting": a.setting,
        "registers": a.registers,
        "cfg": {k: v for k, v in cfg.items() if k != "imask"},
        "train_checkpoint_epoch": ck.get("epoch"),
        "train_log_test_acc": ck.get("test_accuracy"),
    }
    info["float_model_top1"], _ = acc(fmodel, x_te, yt)
    from neuralut.nn import generate_truth_tables, lut_inference, module_list_to_verilog_module

    generate_truth_tables(lmodel, verbose=False)
    lut_inference(lmodel)
    layers = layer_tables(lmodel)
    codes_q = input_codes(lmodel)  # (255, 784)
    thr = thresholds(codes_q)
    codes0 = codes_q[q_te + 127, np.arange(784)[None, :]]  # (n, 784) per-pixel code
    out_codes = table_model(layers, codes0)
    cls = argmax_first(out_codes)
    info["table_model_top1"] = 100.0 * float((cls == y_te).mean())
    lacc, lpred = acc(lmodel, x_te, yt)
    info["library_lut_top1"] = lacc
    info["library_lut_vs_table_class_agree"] = int((lpred.numpy() == cls).sum())
    used_set = set(np.unique(layers[0]["idx"]).tolist())
    used = [j in used_set for j in range(784)]
    info["pixels_used_by_layer0"] = int(sum(used))
    module_list_to_verilog_module(
        lmodel.module_list, "neuralut", a.build_dir, add_registers=a.registers
    )
    # one file: concatenate the generated modules in a fixed order
    files = sorted(
        f
        for f in os.listdir(a.build_dir)
        if f.startswith("layer") or f == "neuralut.v" or (a.registers and f == "myreg.v")
    )
    bd = Path(a.build_dir)
    with open(bd / "neuralut_all.v", "w") as out:
        for f in files:
            out.write((bd / f).read_text() + "\n")
            (bd / f).unlink()
    n_stage = len(lmodel.module_list) if a.registers else 0
    wv = wrapper_verilog(layers, thr, used, n_stage)
    (bd / "mnist_top.v").write_text(wv)
    tiers = {"quick": 100, "full": 10000}
    for t in a.tiers.split(","):
        n = tiers[t]
        vals = out_codes + layers[-1]["start_out"]
        c = LC.write_vectors(f"{a.build_dir}/vec/{t}", n, q_te, y_te, cls, vals)
        info[f"table_model_label_correct_{t}"] = c
    info["sha256"] = {
        f: LC.sha256_file(f"{a.build_dir}/{f}") for f in ("neuralut_all.v", "mnist_top.v")
    }
    info["verilog_neurons"] = [int(L["idx"].shape[0]) for L in layers]
    text = json.dumps(info, indent=1, sort_keys=True)
    (bd / "gen.json").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
