"""I7 generator (ours, stdlib + numpy): a trained binarised MLP (tools/bnn_train.py) to a
Verilog-2005 `mnist_top` (docs/INTERFACE.md) in ONE file, plus the model vectors and unit tests.

usage: gen_bnn.py <design> <train_dir> <build_dir> [--tiers quick,full]
Designs: FOLDS below, each = a network (NETS) + a folding per layer. Writes into <build_dir>
(never committed): mnist_top.v, vec/<tier>/vec_*.hex (golden = the integer model of this
network: class and score bytes), unit/ (per-layer testbenches and vectors), gen.json.

Hardware. Weights and thresholds are constants (case ROMs). A hidden neuron is
`pc >= T`, pc = popcount(XNOR(x, w)); the last layer keeps pc and takes the argmax (first
maximum wins); score k = clip(pc_k - nin/2, -128, 127). Folding of a layer = (PE, SIMD): PE
neurons in parallel, SIMD input bits per cycle, `(nout/PE) * (nin/SIMD)` cycles. The input
register rotates by SIMD bits per step, the output shifts in PE bits per neuron group, so there
is no multiplexer on the data path (only the weight ROM). First layer, mode "int8": all
neurons accumulate +-q while the pixels stream in (PE = nout, SIMD = 1, no extra cycles).
First layer, mode "bin": the bit q >= QBIN is shifted into a 784-bit register as the pixels
arrive and the layer folds like the others.
"""

import argparse
import hashlib
import importlib
import json
import os
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

QBIN = 54  # q >= 54 is pixel >= 128 (q = round(((p/255 - 0.1307)/0.3018)/0.02268019))
AW1 = 18  # int8 first layer: accumulator bits (|acc| <= 127 * 784 = 99,568 < 2^17)
ACC_MAX = 127 * 784

NETS = {
    "M": {"layers": [784, 256, 256, 256, 10], "in_mode": "int8"},
    "S": {"layers": [784, 64, 64, 64, 10], "in_mode": "bin"},
}
# design -> (net, [per layer: None (int8 stream) or (PE, SIMD)])
FOLDS = {
    "M-f1": ("M", [None, (16, 32), (16, 32), (10, 32)]),
    "M-f2": ("M", [None, (64, 64), (64, 64), (10, 64)]),
    "S-par": ("S", [(64, 98), (64, 64), (64, 64), (10, 64)]),
    "S-f1": ("S", [(16, 49), (16, 16), (16, 16), (10, 16)]),
    "S-f2": ("S", [(8, 16), (8, 8), (8, 8), (2, 8)]),
}


def bl(n):
    return max(1, int(n).bit_length())


# ---------------------------------------------------------------- integer model


def layer_bits(net, params, k, x):
    """Hidden layer k: x is q (k == 0, int8), or 0/1 bits (n, nin). Returns (n, nout) 0/1 bits."""
    w = params[f"W{k}"].astype(np.int64)
    t = params[f"T{k}"]
    if k == 0 and net["in_mode"] == "int8":
        return (x @ w.T >= t[None, :]).astype(np.int64)
    pc = popcounts(x, w)
    return (pc >= t[None, :]).astype(np.int64)


def popcounts(bits, w):
    wp = (w > 0).astype(np.int64)
    return bits @ wp.T + (1 - bits) @ (1 - wp).T


def model_forward(net, params, q):
    """(class, scores (n, 10) int, pc (n, 10)) of the integer network on int8 pixels q."""
    nl = len(net["layers"]) - 1
    x = q.astype(np.int64)
    if net["in_mode"] == "bin":
        x = (x >= QBIN).astype(np.int64)
    for k in range(nl - 1):
        x = layer_bits(net, params, k, x)
    pc = popcounts(x, params[f"W{nl - 1}"].astype(np.int64))
    cls = np.argmax(pc, axis=1)  # first maximum wins
    sc = np.clip(pc - net["layers"][-2] // 2, -128, 127)
    return cls, sc


# ---------------------------------------------------------------- verilog helpers


def popcount_tree(lines, bits, pre):
    """Balanced adder tree over 1-bit signals with explicit widths; returns (name, width)."""
    cur = [(b, 1) for b in bits]
    n = 0
    while len(cur) > 1:
        nxt = []
        for i in range(0, len(cur) - 1, 2):
            (a, wa), (b, wb) = cur[i], cur[i + 1]
            w = max(wa, wb) + 1
            nm = f"{pre}_{n}"
            n += 1
            pa = f"{{{w - wa}'d0, {a}}}" if w > wa else a
            pb = f"{{{w - wb}'d0, {b}}}" if w > wb else b
            lines.append(f"  wire [{w - 1}:0] {nm} = {pa} + {pb};")
            nxt.append((nm, w))
        if len(cur) % 2:
            nxt.append(cur[-1])
        cur = nxt
    return cur[0]


def hexlit(width, val):
    return f"{width}'h{val:x}"


def rom(lines, out, aname, abits, depth, width, words):
    """out = words[aname], a constant case ROM (out is a reg)."""
    if depth == 1:
        lines.append(f"  always @({aname}) {out} = {hexlit(width, words[0])};")
        return
    lines.append(f"  always @({aname}) begin")
    lines.append(f"    case ({aname})")
    for i, v in enumerate(words):
        lines.append(f"      {abits}'d{i}: {out} = {hexlit(width, v)};")
    lines.append(f"      default: {out} = {width}'d0;")
    lines.append("    endcase")
    lines.append("  end")


def fold_module(name, w, t, pe, simd, final):
    """w: (nout, nin) +-1; t: thresholds (None for the last layer)."""
    nout, nin = w.shape
    assert nout % pe == 0 and nin % simd == 0, (name, nout, nin, pe, simd)
    ng, ns = nout // pe, nin // simd
    aw = bl(nin) if final else bl(nin + 1)
    yw = nout * aw if final else nout
    wb = (w > 0).astype(np.int64)
    words = []
    for g in range(ng):
        for s in range(ns):
            v = 0
            for p in range(pe):
                for i in range(simd):
                    v |= int(wb[g * pe + p, s * simd + i]) << (p * simd + i)
            words.append(v)
    L = []
    a = L.append
    a(f"module {name} (input clk, input rst, input go, input [{nin - 1}:0] xin,")
    a(f"    output reg fin, output reg [{yw - 1}:0] y);")
    a("  reg run;")
    a(f"  reg [{nin - 1}:0] xr;")
    sb, gb, ab = bl(ns - 1), bl(ng - 1), bl(ng * ns - 1)
    a(f"  reg [{sb - 1}:0] s;")
    a(f"  reg [{gb - 1}:0] g;")
    a(f"  reg [{ab - 1}:0] a;")
    a(f"  reg [{pe * simd - 1}:0] wv;")
    rom(L, "wv", "a", ab, ng * ns, pe * simd, words)
    if not final:
        a(f"  reg [{pe * aw - 1}:0] tv;")
        tw = []
        for g in range(ng):
            v = 0
            for p in range(pe):
                v |= int(t[g * pe + p]) << (p * aw)
            tw.append(v)
        rom(L, "tv", "g", gb, ng, pe * aw, tw)
    a(f"  wire [{simd - 1}:0] xs = xr[{simd - 1}:0];")
    pcw = bl(simd)
    nxts = []
    for p in range(pe):
        xn = []
        for i in range(simd):
            a(f"  wire x{p}_{i} = ~(xs[{i}] ^ wv[{p * simd + i}]);")
            xn.append(f"x{p}_{i}")
        nm, w_ = popcount_tree(L, xn, f"pc{p}")
        a(f"  reg [{aw - 1}:0] acc{p};")
        a(f"  wire [{aw - 1}:0] nx{p} = (s == {sb}'d0 ? {aw}'d0 : acc{p}) + "
          + (f"{{{aw - w_}'d0, {nm}}};" if aw > w_ else f"{nm};"))
        nxts.append(f"nx{p}")
    assert pcw == bl(simd)
    if final:
        newv = "{" + ", ".join(reversed(nxts)) + "}"
        keep = f", y[{yw - 1}:{pe * aw}]" if ng > 1 else ""
        ynew = f"{{{newv}{keep}}}" if ng > 1 else newv
    else:
        bits = []
        for p in range(pe):
            a(f"  wire b{p} = (nx{p} >= tv[{p * aw + aw - 1}:{p * aw}]);")
            bits.append(f"b{p}")
        newv = "{" + ", ".join(reversed(bits)) + "}"
        ynew = f"{{{newv}, y[{nout - 1}:{pe}]}}" if ng > 1 else newv
    rot = "xr" if simd == nin else f"{{xr[{simd - 1}:0], xr[{nin - 1}:{simd}]}}"
    a("  always @(posedge clk) begin")
    a("    fin <= 1'b0;")
    a("    if (rst) begin")
    a("      run <= 1'b0;")
    a("    end else if (go) begin")
    a(f"      xr <= xin; run <= 1'b1; s <= {sb}'d0; g <= {gb}'d0; a <= {ab}'d0;")
    a("    end else if (run) begin")
    for p in range(pe):
        a(f"      acc{p} <= nx{p};")
    a(f"      xr <= {rot};")
    a(f"      a <= a + {ab}'d1;")
    if ns > 1:
        a(f"      if (s == {sb}'d{ns - 1}) begin")
        a(f"        s <= {sb}'d0;")
    else:
        a("      begin")
    a(f"        y <= {ynew};")
    if ng > 1:
        a(f"        if (g == {gb}'d{ng - 1}) begin run <= 1'b0; fin <= 1'b1; end")
        a(f"        else g <= g + {gb}'d1;")
    else:
        a("        run <= 1'b0; fin <= 1'b1;")
    if ns > 1:
        a("      end else s <= s + " + f"{sb}'d1;")
    else:
        a("      end")
    a("    end")
    a("  end")
    a("endmodule")
    return "\n".join(L) + "\n", ng * ns


def stream_module(name, w, t):
    """int8 first layer: nout accumulators, one pixel per cycle."""
    nout, nin = w.shape
    assert nin == 784
    L = []
    a = L.append
    a(f"module {name} (input clk, input clr, input en, input [9:0] idx, input [7:0] q,")
    a(f"    output [{nout - 1}:0] y);")
    a(f"  reg [{nout - 1}:0] wv;")
    words = [sum(int(w[n, j] > 0) << n for n in range(nout)) for j in range(784)]
    rom(L, "wv", "idx", 10, 784, nout, words)
    a(f"  wire [{AW1 - 1}:0] qx = {{{{{AW1 - 8}{{q[7]}}}}, q}};")
    a(f"  wire [{AW1 - 1}:0] nq = {AW1}'d0 - qx;")
    a(f"  reg [{nout * AW1 - 1}:0] acc;")
    a("  always @(posedge clk) begin")
    a("    if (clr) acc <= " + f"{nout * AW1}'d0;")
    a("    else if (en) begin")
    for n in range(nout):
        sl = f"acc[{n * AW1 + AW1 - 1}:{n * AW1}]"
        a(f"      {sl} <= {sl} + (wv[{n}] ? qx : nq);")
    a("    end")
    a("  end")
    off = 1 << (AW1 - 1)
    for n in range(nout):
        sl = f"acc[{n * AW1 + AW1 - 1}:{n * AW1}]"
        tn = int(t[n])
        if tn > ACC_MAX:
            a(f"  assign y[{n}] = 1'b0;")
        elif tn <= -ACC_MAX:
            a(f"  assign y[{n}] = 1'b1;")
        else:
            a(f"  assign y[{n}] = {{~acc[{n * AW1 + AW1 - 1}], acc[{n * AW1 + AW1 - 2}:{n * AW1}]}}"
              f" >= {AW1}'d{tn + off};")
    a("endmodule")
    return "\n".join(L) + "\n"


def top_module(net, folds, params):
    nl = len(net["layers"]) - 1
    sizes = net["layers"]
    int8 = net["in_mode"] == "int8"
    nlast = sizes[-2]
    pcw = bl(nlast)
    half = nlast // 2
    assert half <= 128
    L = []
    a = L.append
    a("module mnist_top (input clk, input rst, input start, input in_valid, input [7:0] in_data,")
    a("                  output in_ready, output reg done, output reg [3:0] pred,")
    a("                  output reg [79:0] scores);")
    a("  reg loading;")
    a("  reg [9:0] cnt;")
    a("  reg fl1;")
    a("  assign in_ready = loading;")
    a("  wire xfer = loading & in_valid;")
    a("  wire clr = start | rst;")
    # first layer
    if int8:
        a(f"  wire [{sizes[1] - 1}:0] y0;")
        a("  bnn_l0 l0 (.clk(clk), .clr(clr), .en(xfer), .idx(cnt), .q(in_data), .y(y0));")
        go_next = "fl1"
    else:
        a("  reg [783:0] xb;")
        a("  wire [7:0] u = in_data ^ 8'h80;")
        a(f"  wire pbit = (u >= 8'd{QBIN + 128});")
        a("  always @(posedge clk) if (xfer) xb <= {pbit, xb[783:1]};")
        a(f"  wire [{sizes[1] - 1}:0] y0;")
        a("  wire f0;")
        a("  bnn_l0 l0 (.clk(clk), .rst(rst), .go(fl1), .xin(xb), .fin(f0), .y(y0));")
        go_next = "f0"
    prev_y, prev_f = "y0", go_next
    for k in range(1, nl):
        yw = sizes[k + 1] * (pcw if k == nl - 1 else 1)
        a(f"  wire [{yw - 1}:0] y{k};")
        a(f"  wire f{k};")
        a(f"  bnn_l{k} l{k} (.clk(clk), .rst(rst), .go({prev_f}), .xin({prev_y}), .fin(f{k}), "
          f".y(y{k}));")
        prev_y, prev_f = f"y{k}", f"f{k}"
    last = prev_y
    for k in range(10):
        a(f"  wire [{pcw - 1}:0] p{k} = {last}[{k * pcw + pcw - 1}:{k * pcw}];")
    a(f"  wire [{pcw - 1}:0] v0 = p0;")
    a("  wire [3:0] i0 = 4'd0;")
    for k in range(1, 10):
        a(f"  wire g{k} = (p{k} > v{k - 1});")
        a(f"  wire [{pcw - 1}:0] v{k} = g{k} ? p{k} : v{k - 1};")
        a(f"  wire [3:0] i{k} = g{k} ? 4'd{k} : i{k - 1};")
    dw = max(pcw, 8) + 1
    for k in range(10):
        pad = f"{{{dw - pcw}'d0, p{k}}}" if dw > pcw else f"p{k}"
        a(f"  wire [{dw - 1}:0] d{k} = {pad} - {dw}'d{half};")
        a(f"  wire [7:0] s{k} = (d{k} == {dw}'d128) ? 8'h7f : d{k}[7:0];")
    a("  always @(posedge clk) begin")
    a("    if (rst) begin")
    a("      loading <= 1'b0; cnt <= 10'd0; fl1 <= 1'b0; done <= 1'b0;")
    a("      pred <= 4'd0; scores <= 80'd0;")
    a("    end else begin")
    a("      fl1 <= 1'b0;")
    a("      if (start) begin loading <= 1'b1; cnt <= 10'd0; done <= 1'b0; end")
    a("      else if (xfer) begin")
    a("        cnt <= cnt + 10'd1;")
    a("        if (cnt == 10'd783) begin loading <= 1'b0; fl1 <= 1'b1; end")
    a("      end")
    a(f"      if ({prev_f}) begin")
    a("        done <= 1'b1; pred <= i9;")
    for k in range(10):
        a(f"        scores[{8 * k + 7}:{8 * k}] <= s{k};")
    a("      end")
    a("    end")
    a("  end")
    a("endmodule")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- unit tests


def hexw(width, v):
    return f"{int(v):0{(width + 3) // 4}x}\n"


def unit_tb_fold(name, nin, yw, vecdir, n):
    return f"""// Generated unit test of {name}: {n} random inputs against the integer model.
`timescale 1ns/1ps
module tb_{name};
  reg clk, rst, go;
  reg [{nin - 1}:0] xin;
  wire fin;
  wire [{yw - 1}:0] y;
  reg [{nin - 1}:0] xs [0:{n - 1}];
  reg [{yw - 1}:0] ys [0:{n - 1}];
  integer i, bad, cyc, tot;
  {name} dut (.clk(clk), .rst(rst), .go(go), .xin(xin), .fin(fin), .y(y));
  initial clk = 0;
  always #5 clk = ~clk;
  initial begin
    $readmemh("{vecdir}/{name}_x.hex", xs);
    $readmemh("{vecdir}/{name}_y.hex", ys);
    bad = 0; tot = 0; rst = 1; go = 0; xin = 0;
    repeat (3) @(negedge clk);
    rst = 0;
    @(negedge clk);
    for (i = 0; i < {n}; i = i + 1) begin
      xin = xs[i]; go = 1;
      @(negedge clk);
      go = 0; cyc = 1;
      while (!fin && cyc < 100000) begin @(negedge clk); cyc = cyc + 1; end
      if (y !== ys[i]) bad = bad + 1;
      tot = tot + cyc;
      @(negedge clk);
    end
    if (bad == 0) $display("UNIT {name} PASS n={n} cycles=%0d", tot/{n});
    else $display("UNIT {name} FAIL n={n} bad=%0d", bad);
    $finish;
  end
endmodule
"""


def unit_tb_stream(name, nout, vecdir, n):
    return f"""// Generated unit test of {name}: {n} random images against the integer model.
`timescale 1ns/1ps
module tb_{name};
  reg clk, clr, en;
  reg [9:0] idx;
  reg [7:0] q;
  wire [{nout - 1}:0] y;
  reg [7:0] xs [0:{n * 784 - 1}];
  reg [{nout - 1}:0] ys [0:{n - 1}];
  integer i, j, bad;
  {name} dut (.clk(clk), .clr(clr), .en(en), .idx(idx), .q(q), .y(y));
  initial clk = 0;
  always #5 clk = ~clk;
  initial begin
    $readmemh("{vecdir}/{name}_x.hex", xs);
    $readmemh("{vecdir}/{name}_y.hex", ys);
    bad = 0; clr = 1; en = 0; idx = 0; q = 0;
    @(negedge clk);
    for (i = 0; i < {n}; i = i + 1) begin
      clr = 1; en = 0;
      @(negedge clk);
      clr = 0; en = 1;
      for (j = 0; j < 784; j = j + 1) begin
        idx = j; q = xs[i*784+j];
        @(negedge clk);
      end
      en = 0;
      @(negedge clk);
      if (y !== ys[i]) bad = bad + 1;
    end
    if (bad == 0) $display("UNIT {name} PASS n={n}");
    else $display("UNIT {name} FAIL n={n} bad=%0d", bad);
    $finish;
  end
endmodule
"""


def write_units(bd, net, folds, params, mods, nunit=24):
    ud = Path(bd) / "unit"
    ud.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(11)
    nl = len(net["layers"]) - 1
    sizes = net["layers"]
    tbs = []
    for k in range(nl):
        name = f"bnn_l{k}"
        w = params[f"W{k}"].astype(np.int64)
        if k == 0 and net["in_mode"] == "int8":
            q = rng.integers(-127, 128, size=(nunit, 784))
            q[0] = -19  # a blank image
            y = layer_bits(net, params, 0, q)
            (ud / f"{name}_x.hex").write_text("".join(hexw(8, v & 0xFF) for v in q.reshape(-1)))
            (ud / f"{name}_y.hex").write_text(
                "".join(hexw(sizes[1], int("".join(str(b) for b in r[::-1]), 2)) for r in y)
            )
            (ud / f"tb_{name}.v").write_text(unit_tb_stream(name, sizes[1], ".", nunit))
        else:
            x = rng.integers(0, 2, size=(nunit, sizes[k]))
            if k == nl - 1:
                pc = popcounts(x, w)
                aw = bl(sizes[k])
                yv = [sum(int(r[c]) << (c * aw) for c in range(10)) for r in pc]
                ywid = 10 * aw
            else:
                y = layer_bits(net, params, k, x)
                yv = [int("".join(str(b) for b in r[::-1]), 2) for r in y]
                ywid = sizes[k + 1]
            xv = [int("".join(str(b) for b in r[::-1]), 2) for r in x]
            (ud / f"{name}_x.hex").write_text("".join(hexw(sizes[k], v) for v in xv))
            (ud / f"{name}_y.hex").write_text("".join(hexw(ywid, v) for v in yv))
            (ud / f"tb_{name}.v").write_text(unit_tb_fold(name, sizes[k], ywid, ".", nunit))
        tbs.append(f"tb_{name}.v")
    return tbs


# ---------------------------------------------------------------- main


def generate(design, train_dir, build_dir, tiers):
    netname, folds = FOLDS[design]
    net = NETS[netname]
    params = dict(np.load(os.path.join(train_dir, f"{netname}.npz")))
    nl = len(net["layers"]) - 1
    sizes = net["layers"]
    bd = Path(build_dir)
    bd.mkdir(parents=True, exist_ok=True)
    text = []
    cycles = {}
    for k in range(nl):
        w, t = params[f"W{k}"], params.get(f"T{k}")
        final = k == nl - 1
        if k == 0 and net["in_mode"] == "int8":
            assert folds[0] is None
            text.append(stream_module("bnn_l0", w, t))
            cycles["l0"] = 0
        else:
            pe, simd = folds[k]
            src, c = fold_module(f"bnn_l{k}", w, t, pe, simd, final)
            text.append(src)
            cycles[f"l{k}"] = c
    text.append(top_module(net, folds, params))
    head = f"// Generated by tools/gen_bnn.py (design {design}); do not edit. I7 binarised MLP.\n"
    (bd / "mnist_top.v").write_text(head + "\n".join(text))
    LC = importlib.import_module("lutnn_common")
    qte, yte = LC.load("test")
    cls, sc = model_forward(net, params, qte)
    info = {
        "design": design,
        "net": netname,
        "layers": sizes,
        "in_mode": net["in_mode"],
        "folds": folds,
        "layer_cycles": cycles,
        "model_top1_10000": int((cls == yte).sum()),
    }
    for t, n in (("quick", 100), ("full", 10000)):
        if t in tiers:
            info[f"model_label_correct_{t}"] = LC.write_vectors(
                bd / "vec" / t, n, qte, yte, cls, sc & 0xFF
            )
    write_units(bd, net, folds, params, None)
    h = hashlib.sha256((bd / "mnist_top.v").read_bytes()).hexdigest()
    info["sha256"] = {"mnist_top.v": h}
    info["verilog_bytes"] = (bd / "mnist_top.v").stat().st_size
    (bd / "gen.json").write_text(json.dumps(info, indent=1, sort_keys=True))
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("design")
    ap.add_argument("train_dir")
    ap.add_argument("build_dir")
    ap.add_argument("--tiers", default="quick,full")
    a = ap.parse_args()
    print(json.dumps(generate(a.design, a.train_dir, a.build_dir, a.tiers.split(",")),
                     indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
