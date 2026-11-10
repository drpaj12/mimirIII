"""Generator for implementations I3 (layer-pipelined dataflow, weights in RAM) and I4 (fixed
weights as constants) of the int8 LeNet-5. Emits Verilog-2005 `mnist_top` (docs/INTERFACE.md).

usage: gen_lenet.py <OUT_DIR> --design i3|i4 [--p N | --lanes conv1=6,conv2=16,...]
                    [--weights ram|const] [--vec VECDIR] [--units 3]
Reads the golden network (golden/lenet_int8.py) from Gabe Litteken's transmission file by path
($USS_TPU, default <workspace>/external/USS_Tensor_Processing_Unit). Everything generated
(weights as hex files or constants, Verilog, unit-test vectors) goes to OUT_DIR; nothing generated
is committed.

Architecture (docs/I3-DATAFLOW.md): one stage per layer. A stage has a double-buffered input
activation RAM, P multiply-accumulate lanes (P output channels at once) that walk the reduction
sequentially, a shared requantiser, and a serial write of its outputs into the next stage's
buffer. Max pooling runs on the raw accumulators (requantise and ReLU are monotone, so
relu(rq(max a)) == max(relu(rq a)), bit-exact); the 2x2 window is four consecutive items.
"""
import importlib
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE))
Net = importlib.import_module("golden.lenet_int8").Net

WS = Path(os.environ.get("ODIN3_WS", Path.home() / "odin3-ws"))
USS = Path(os.environ.get("USS_TPU", WS / "external/USS_Tensor_Processing_Unit"))
S_IN = 0.02268019
ORDER = ["conv1", "conv2", "fc1", "fc2", "fc3"]
# kind, in channels, in height, in width (conv) / reduction length (fc), out channels
SPEC = {"conv1": ("conv", 1, 28, 28, 6), "conv2": ("conv", 6, 13, 13, 16),
        "fc1": ("fc", 1, 1, 400, 120), "fc2": ("fc", 1, 1, 120, 84), "fc3": ("fc", 1, 1, 84, 10)}


def bw(n):
    """Bits to hold the unsigned value n."""
    return max(1, int(n).bit_length())


def hx8(v):
    return f"{int(v) & 0xFF:02x}"


class Layer:
    def __init__(self, name, net, p, mode):
        self.name, self.p, self.mode = name, p, mode
        self.kind, self.c, self.h, self.w, self.oc = SPEC[name]
        self.m0, self.n = net.q[name]
        self.relu = name != "fc3"
        wt = net.w[name]
        self.wf = wt.reshape(self.oc, -1)
        if self.kind == "conv":
            self.k = self.c * 9
            self.ph, self.pw = (self.h - 2) // 2, (self.w - 2) // 2
            self.q = 4
            self.insz = self.c * self.h * self.w
        else:
            self.k = self.w
            self.ph = self.pw = 1
            self.q = 1
            self.insz = self.k
        self.phw = self.ph * self.pw
        self.outsz = self.oc * self.phw
        self.g = -(-self.oc // p)
        bound = 128 * int(np.abs(self.wf).sum(axis=1).max())
        self.accw = bw(bound) + 1
        self.mw = self.accw + 10  # M0 < 256, one sign bit, one headroom bit
        self.aw = bw(2 * (1 << bw(self.insz - 1)) - 1)  # bank bit + address
        self.ad = bw(self.insz - 1)
        self.wd = self.g * self.k  # weight words per lane

    def lane_words(self, lane):
        out = []
        for g in range(self.g):
            o = g * self.p + lane
            out += [int(v) for v in (self.wf[o] if o < self.oc else np.zeros(self.k, int))]
        return out


def stage_text(L):
    name, P, K, G, Q = L.name, L.p, L.k, L.g, L.q
    AD, WAW = L.ad, bw(L.wd - 1)
    conv = L.kind == "conv"
    kw, gw, ow = bw(K - 1), bw(max(G - 1, 1)), bw(L.outsz - 1)
    pwid = bw(max(L.phw - 1, 1))
    t = []
    a = t.append
    a(f"// stage {name}: {L.kind}, in {L.insz}, out {L.outsz}, K={K}, P={P}, G={G}, weights={L.mode}")
    a(f"module l_{name} (input clk, input rst,")
    a(f"  input in_we, input [{AD-1}:0] in_addr, input [7:0] in_data, input in_fd,")
    a("  output in_free, input ds_free,")
    a(f"  output reg o_we, output reg [{ow-1}:0] o_addr, output reg [7:0] o_data, output reg o_fd);")
    a(f"  reg [7:0] abuf [0:{(1 << (AD + 1)) - 1}];")
    a("  reg full0, full1, wbank, rbank;")
    a("  assign in_free = wbank ? ~full1 : ~full0;")
    a("  wire rfull = rbank ? full1 : full0;")
    a("  reg active, iss;")
    a("  // tags: [5]=valid [4]=item first [3]=item last [2]=window first [1]=window last [0]=frame last")
    a("  reg [5:0] tagA, tagB, tagC, tagD;")
    a("  wire rel = tagB[5] & tagB[0];")
    a("  always @(posedge clk) begin")
    a("    if (rst) begin full0 <= 1'b0; full1 <= 1'b0; wbank <= 1'b0; rbank <= 1'b0; end")
    a("    else begin")
    a("      if (in_fd) begin")
    a("        if (wbank) full1 <= 1'b1; else full0 <= 1'b1;")
    a("        wbank <= ~wbank;")
    a("      end")
    a("      if (rel) begin")
    a("        if (rbank) full1 <= 1'b0; else full0 <= 1'b0;")
    a("        rbank <= ~rbank;")
    a("      end")
    a("    end")
    a("  end")
    a("  always @(posedge clk) if (in_we) abuf[{wbank, in_addr}] <= in_data;")
    # ---- issue side
    a(f"  reg [{AD-1}:0] ra;")
    a(f"  reg [{WAW-1}:0] wa;")
    a(f"  reg [{kw-1}:0] kc;")
    a(f"  reg [{gw-1}:0] g;")
    a(f"  reg [{WAW-1}:0] wbase;")
    a(f"  reg [{AD-1}:0] koff;")
    if conv:
        a(f"  reg [{bw(L.pw-1)-1}:0] px;")
        a(f"  reg [{bw(L.ph-1)-1}:0] py;")
        a(f"  reg [{AD-1}:0] pbase;")
        a("  reg [1:0] q, kx, ky;")
        a(f"  wire [{AD-1}:0] qoff = (q == 2'd0) ? {AD}'d0 : (q == 2'd1) ? {AD}'d1 : "
          f"(q == 2'd2) ? {AD}'d{L.w} : {AD}'d{L.w + 1};")
    start = "~active & rfull & ds_free"
    a("  always @(posedge clk) begin")
    a("    if (rst) begin active <= 1'b0; iss <= 1'b0; tagA <= 6'd0; end")
    a("    else begin")
    a(f"      if ({start}) begin")
    a("        active <= 1'b1; iss <= 1'b1;")
    a(f"        kc <= 0; g <= 0; wbase <= 0; koff <= 0;")
    if conv:
        a("        px <= 0; py <= 0; pbase <= 0; q <= 2'd0; kx <= 2'd0; ky <= 2'd0;")
    a("      end")
    a("      if (o_fd) active <= 1'b0;")
    a("      tagA <= 6'd0;")
    a("      if (iss) begin")
    if conv:
        a(f"        ra <= pbase + qoff + koff;")
        lastpix = f"(px == {L.pw-1}) & (py == {L.ph-1})"
        flast = f"{lastpix} & (g == {G-1}) & (q == 2'd{Q-1}) & (kc == {K-1})"
        a(f"        tagA <= {{1'b1, (kc == 0), (kc == {K-1}), (q == 2'd0), (q == 2'd{Q-1}), {flast}}};")
    else:
        a("        ra <= koff;")
        flast = f"(g == {G-1}) & (kc == {K-1})"
        a(f"        tagA <= {{1'b1, (kc == 0), (kc == {K-1}), 1'b1, 1'b1, {flast}}};")
    a("        wa <= wbase + kc;")
    a(f"        if (kc == {K-1}) begin")
    a("          kc <= 0; koff <= 0;")
    if conv:
        a("          kx <= 2'd0; ky <= 2'd0;")
        a(f"          if (q == 2'd{Q-1}) begin")
        a("            q <= 2'd0;")
        a(f"            if (g == {G-1}) begin")
        a("              g <= 0; wbase <= 0;")
        a(f"              if (px == {L.pw-1}) begin")
        a("                px <= 0;")
        a(f"                if (py == {L.ph-1}) iss <= 1'b0;")
        a("                else py <= py + 1;")
        a(f"                pbase <= pbase + {AD}'d{2 * L.w - 2 * (L.pw - 1)};")
        a("              end else begin")
        a("                px <= px + 1;")
        a(f"                pbase <= pbase + {AD}'d2;")
        a("              end")
        a("            end else begin")
        a(f"              g <= g + 1; wbase <= wbase + {WAW}'d{K};")
        a("            end")
        a("          end else q <= q + 1;")
    else:
        a(f"          if (g == {G-1}) iss <= 1'b0;")
        a(f"          else begin g <= g + 1; wbase <= wbase + {WAW}'d{K}; end")
    a("        end else begin")
    a("          kc <= kc + 1;")
    if conv:
        a("          if (kx != 2'd2) begin kx <= kx + 1; koff <= koff + 1; end")
        a("          else begin")
        a("            kx <= 2'd0;")
        a(f"            if (ky != 2'd2) begin ky <= ky + 1; koff <= koff + {AD}'d{L.w - 2}; end")
        a(f"            else begin ky <= 2'd0; koff <= koff + {AD}'d{L.h * L.w - 2 * L.w - 2}; end")
        a("          end")
    else:
        a("          koff <= koff + 1;")
    a("        end")
    a("      end")
    a("    end")
    a("  end")
    # ---- datapath
    a("  reg signed [7:0] xd;")
    a("  always @(posedge clk) xd <= abuf[{rbank, ra}];")
    aw_ = L.accw
    for lane in range(P):
        a(f"  reg signed [7:0] wd{lane};")
        if L.mode == "ram":
            a(f"  reg [7:0] wm{lane} [0:{L.wd-1}];")
            a(f'  initial $readmemh("w_{name}_l{lane}.hex", wm{lane});')
            a(f"  always @(posedge clk) wd{lane} <= wm{lane}[wa];")
        else:
            a(f"  always @(posedge clk) begin")
            a(f"    case (wa)")
            for i, v in enumerate(L.lane_words(lane)):
                if v:
                    a(f"      {WAW}'d{i}: wd{lane} <= 8'h{hx8(v)};")
            a(f"      default: wd{lane} <= 8'h00;")
            a("    endcase")
            a("  end")
        a(f"  reg signed [15:0] prod{lane};")
        a(f"  wire signed [15:0] pm{lane} = wd{lane} * xd;")
        a(f"  reg signed [{aw_-1}:0] acc{lane}, mx{lane}, sr{lane};")
        a(f"  wire signed [{aw_-1}:0] mxn{lane} = tagD[2] ? acc{lane} : "
          f"((acc{lane} > mx{lane}) ? acc{lane} : mx{lane});")
    a("  always @(posedge clk) begin")
    a("    tagB <= tagA; tagC <= tagB; tagD <= tagC;")
    for lane in range(P):
        a(f"    prod{lane} <= pm{lane};")
        a(f"    if (tagC[5]) acc{lane} <= tagC[4] ? prod{lane} : (acc{lane} + prod{lane});")
    a("  end")
    # ---- window / output side
    a("  wire ev = tagD[5] & tagD[3];")
    a("  reg orun, swl;")
    a(f"  reg [{bw(P)-1}:0] ocnt;")
    a(f"  reg [{ow-1}:0] oa, o_pixgb;")
    a(f"  reg [{pwid-1}:0] o_pix;")
    a(f"  reg [{ow-1}:0] o_gbase;")
    a(f"  reg [{bw(G*P)-1}:0] och, o_gp;")
    a(f"  reg [{gw-1}:0] o_g;")
    a(f"  reg signed [{L.mw-1}:0] mreg;")
    a(f"  reg [{ow-1}:0] ta0, ta1;")
    a("  reg tw0, tl0, tv0, tw1, tl1;")
    a("  reg signed [7:0] yv;")
    rnd = (1 << (L.n - 1)) if L.n else 0
    a(f"  wire signed [{L.mw-1}:0] ysum = mreg + {L.mw}'sd{rnd};")
    a(f"  wire signed [{L.mw-1}:0] ysh = ysum >>> {L.n};")
    lo = 0 if L.relu else -128
    a("  always @(posedge clk) begin")
    a("    if (rst) begin")
    a("      orun <= 1'b0; swl <= 1'b0; o_pix <= 0; o_gbase <= 0; o_gp <= 0; o_g <= 0;")
    a("      tv0 <= 1'b0; tl0 <= 1'b0; tw0 <= 1'b0; tl1 <= 1'b0; tw1 <= 1'b0; o_we <= 1'b0; o_fd <= 1'b0;")
    a("    end else begin")
    for lane in range(P):
        a(f"      if (ev) mx{lane} <= mxn{lane};")
    a("      if (ev & tagD[1]) begin")
    for lane in range(P):
        a(f"        sr{lane} <= mxn{lane};")
    a(f"        orun <= 1'b1; ocnt <= 0; oa <= o_pix + o_gbase; och <= o_gp; swl <= tagD[0];")
    a(f"        if (o_g == {G-1}) begin")
    a("          o_g <= 0; o_gbase <= 0; o_gp <= 0;")
    a(f"          if (tagD[0]) o_pix <= 0; else o_pix <= o_pix + 1;")
    a("        end else begin")
    a(f"          o_g <= o_g + 1; o_gbase <= o_gbase + {ow}'d{P * L.phw}; o_gp <= o_gp + {P};")
    a("        end")
    a("      end else if (orun) begin")
    for lane in range(P - 1):
        a(f"        sr{lane} <= sr{lane + 1};")
    a(f"        oa <= oa + {ow}'d{L.phw}; och <= och + 1; ocnt <= ocnt + 1;")
    a(f"        if (ocnt == {P-1}) orun <= 1'b0;")
    a("      end")
    a("      tv0 <= orun;")
    a(f"      mreg <= sr0 * {L.mw}'sd{L.m0};")
    a("      ta0 <= oa;")
    a(f"      tw0 <= (och < {L.oc});")
    a(f"      tl0 <= (ocnt == {P-1}) & swl;")
    a("      ta1 <= ta0; tw1 <= tw0 & tv0; tl1 <= tl0 & tv0;")
    a("      o_we <= tw1; o_addr <= ta1; o_data <= yv; o_fd <= tl1;")
    a("    end")
    a("  end")
    a("  always @(posedge clk) begin")
    a(f"    if (ysh > 127) yv <= 8'sd127;")
    a(f"    else if (ysh < {lo}) yv <= {'8' + chr(39) + 'sd0' if lo == 0 else '-8' + chr(39) + 'sd128'};")
    a("    else yv <= ysh[7:0];")
    a("  end")
    a("endmodule")
    return "\n".join(t)


SINK = """// result stage: collects the ten fc3 scores, then the argmax (first maximum wins)
module l_sink (input clk, input rst, input we, input [7:0] data, input fd, input clr,
  output reg done, output reg [3:0] pred, output reg [79:0] scores);
  reg [79:0] tmp, sh;
  reg fd_d, run, fin;
  reg [3:0] i, besti;
  reg signed [7:0] bestv;
  wire signed [7:0] cur = sh[7:0];
  always @(posedge clk) begin
    if (rst) begin
      done <= 1'b0; fd_d <= 1'b0; run <= 1'b0; fin <= 1'b0; pred <= 4'd0; scores <= 80'd0;
      tmp <= 80'd0; sh <= 80'd0; i <= 4'd0; besti <= 4'd0; bestv <= 8'sd0;
    end else begin
      fd_d <= fd;
      if (we) tmp <= {data, tmp[79:8]};
      if (clr) done <= 1'b0;
      if (fd_d) begin scores <= tmp; sh <= tmp; i <= 4'd0; run <= 1'b1; done <= 1'b0; end
      if (run) begin
        if ((i == 4'd0) | (cur > bestv)) begin bestv <= cur; besti <= i; end
        sh <= {8'd0, sh[79:8]};
        i <= i + 4'd1;
        if (i == 4'd9) begin run <= 1'b0; fin <= 1'b1; end
      end
      if (fin) begin pred <= besti; done <= 1'b1; fin <= 1'b0; end
    end
  end
endmodule
"""


def top_text(layers):
    t = ["// generated by tools/gen_lenet.py: mnist_top per docs/INTERFACE.md",
         "module mnist_top (input clk, input rst, input start, input in_valid, input [7:0] in_data,",
         "  output in_ready, output done, output [3:0] pred, output [79:0] scores);",
         "  reg armed;", "  reg [9:0] pcnt;"]
    prev = None
    for i, L in enumerate(layers):
        t.append(f"  wire s{i}_free; wire s{i}_we, s{i}_fd; wire [{bw(L.insz-1)-1}:0] s{i}_addr; "
                 f"wire [7:0] s{i}_data;")
    t.append("  wire k_we, k_fd; wire [7:0] k_data;")
    t.append("  assign in_ready = armed & s0_free;")
    t.append("  wire fe_we = in_valid & in_ready;")
    t.append("  wire fe_fd = fe_we & (pcnt == 10'd783);")
    t.append("  always @(posedge clk) begin")
    t.append("    if (rst) begin armed <= 1'b0; pcnt <= 10'd0; end")
    t.append("    else begin")
    t.append("      if (start) armed <= 1'b1;")
    t.append("      if (fe_we) pcnt <= (pcnt == 10'd783) ? 10'd0 : pcnt + 10'd1;")
    t.append("      if (fe_fd) armed <= 1'b0;")
    t.append("    end")
    t.append("  end")
    n = len(layers)
    for i, L in enumerate(layers):
        if i == 0:
            src = ["fe_we", f"pcnt[{L.ad-1}:0]", "in_data", "fe_fd"]
        else:
            src = [f"s{i}_we", f"s{i}_addr", f"s{i}_data", f"s{i}_fd"]
        dsf = f"s{i+1}_free" if i + 1 < n else "1'b1"
        if i + 1 < n:
            outs = [f"s{i+1}_we", f"s{i+1}_addr", f"s{i+1}_data", f"s{i+1}_fd"]
        else:
            outs = ["k_we", f"k_addr", "k_data", "k_fd"]
        if i + 1 == n:
            t.append(f"  wire [{bw(L.outsz-1)-1}:0] k_addr;")
        t.append(f"  l_{L.name} u_{L.name} (.clk(clk), .rst(rst), .in_we({src[0]}), .in_addr({src[1]}), "
                 f".in_data({src[2]}), .in_fd({src[3]}), .in_free(s{i}_free), .ds_free({dsf}), "
                 f".o_we({outs[0]}), .o_addr({outs[1]}), .o_data({outs[2]}), .o_fd({outs[3]}));")
    t.append("  l_sink u_sink (.clk(clk), .rst(rst), .we(k_we), .data(k_data), .fd(k_fd), "
             ".clr(start), .done(done), .pred(pred), .scores(scores));")
    t.append("endmodule")
    return "\n".join(t)


def unit_tb(L, units):
    AD, ow = L.ad, bw(L.outsz - 1)
    return f"""// unit test of l_{L.name} against the golden intermediate tensors ({units} frames, fed back to back)
`timescale 1ns/1ps
module tb_unit_{L.name};
  reg clk, rst, in_we, in_fd;
  reg [{AD-1}:0] in_addr;
  reg [7:0] in_data;
  wire in_free, o_we, o_fd;
  wire [{ow-1}:0] o_addr;
  wire [7:0] o_data;
  l_{L.name} dut (.clk(clk), .rst(rst), .in_we(in_we), .in_addr(in_addr), .in_data(in_data),
    .in_fd(in_fd), .in_free(in_free), .ds_free(1'b1), .o_we(o_we), .o_addr(o_addr),
    .o_data(o_data), .o_fd(o_fd));
  reg [7:0] xin [0:{units * L.insz - 1}];
  reg [7:0] xexp [0:{units * L.outsz - 1}];
  reg [7:0] got [0:{L.outsz - 1}];
  integer f, i, errs, ofr, cyc, chk, j;
  initial clk = 0;
  always #5 clk = ~clk;
  initial cyc = 0;
  always @(posedge clk) cyc = cyc + 1;
  always @(posedge clk) if (o_we) got[o_addr] <= o_data;
  initial begin
    $readmemh("ut_{L.name}_in.hex", xin);
    $readmemh("ut_{L.name}_exp.hex", xexp);
    errs = 0; ofr = 0; chk = 0;
    rst = 1; in_we = 0; in_fd = 0; in_addr = 0; in_data = 0;
    repeat (4) @(negedge clk);
    rst = 0;
    repeat (2) @(negedge clk);
    for (f = 0; f < {units}; f = f + 1) begin
      while (!in_free) @(negedge clk);
      for (i = 0; i < {L.insz}; i = i + 1) begin
        in_we = 1; in_addr = i; in_data = xin[f*{L.insz} + i];
        @(negedge clk);
      end
      in_we = 0; in_fd = 1;
      @(negedge clk);
      in_fd = 0;
    end
    j = 0;
    while (ofr < {units} && j < 3000000) begin @(negedge clk); j = j + 1; end
    if (errs == 0 && ofr == {units}) $display("UNIT {L.name} PASS frames=%0d errors=%0d cycles=%0d", ofr, errs, cyc);
    else $display("UNIT {L.name} FAIL frames=%0d errors=%0d cycles=%0d", ofr, errs, cyc);
    $finish;
  end
  always @(posedge clk) if (o_fd) chk <= 1;
  always @(negedge clk) if (chk == 1) begin
    chk = 0;
    for (j = 0; j < {L.outsz}; j = j + 1)
      if (got[j] !== xexp[ofr*{L.outsz} + j]) begin
        errs = errs + 1;
        if (errs < 5) $display("UNIT {L.name} frame %0d idx %0d got %0h want %0h", ofr, j, got[j], xexp[ofr*{L.outsz}+j]);
      end
    ofr = ofr + 1;
  end
endmodule
"""


def trace(net, x8):
    """Golden per-layer tensors from the int8 network input (same arithmetic as Net.scores)."""
    x = x8.reshape(1, 28, 28).astype(np.int64)
    ins, outs = [x.reshape(-1)], []
    for k in ("conv1", "conv2"):
        x = Net._pool(np.maximum(Net._rq(Net._conv(x, net.w[k]), *net.q[k]), 0))
        outs.append(x.reshape(-1))
        ins.append(x.reshape(-1))
    v = x.reshape(-1)
    for k in ("fc1", "fc2", "fc3"):
        v = Net._rq(net.w[k] @ v, *net.q[k])
        if k != "fc3":
            v = np.maximum(v, 0)
        outs.append(v)
        ins.append(v)
    return ins, outs


def parse_lanes(s, default):
    d = dict.fromkeys(ORDER, default)
    for kv in s.split(","):
        k, v = kv.split("=")
        d[k] = int(v)
    return d


def build(out, design="i3", p=1, lanes=None, mode=None, vec=None, units=3):
    out = Path(out).resolve()
    (out / "gen").mkdir(parents=True, exist_ok=True)
    net = Net(USS / "Benchmarks/LeNet_5_TRANSMISSION.bin", S_IN)
    mode = mode or ("ram" if design == "i3" else "const")
    lanes = lanes or dict.fromkeys(ORDER, p)
    layers = [Layer(n, net, lanes[n], mode) for n in ORDER]
    data_files = []
    if mode == "ram":
        for L in layers:
            for lane in range(L.p):
                f = out / f"w_{L.name}_l{lane}.hex"
                f.write_text("".join(f"{hx8(v)}\n" for v in L.lane_words(lane)))
                data_files.append(str(f))
    text = "\n".join([stage_text(L) for L in layers] + [SINK, top_text(layers)]) + "\n"
    top = out / "gen" / "mnist_top.v"
    top.write_text(text)
    units_info = {}
    if vec:
        raw = [int(x, 16) for x in open(Path(vec) / "vec_images.hex").read().split()[:units * 784]]
        imgs = [np.array([v - 256 if v > 127 else v for v in raw[u * 784:(u + 1) * 784]])
                for u in range(units)]
        tr = [trace(net, im) for im in imgs]
        for i, L in enumerate(layers):
            fin = out / f"ut_{L.name}_in.hex"
            fex = out / f"ut_{L.name}_exp.hex"
            fin.write_text("".join(hx8(v) + "\n" for t in tr for v in t[0][i]))
            fex.write_text("".join(hx8(v) + "\n" for t in tr for v in t[1][i]))
            tbf = out / "gen" / f"tb_unit_{L.name}.v"
            tbf.write_text(unit_tb(L, units))
            data_files += [str(fin), str(fex)]
            units_info[L.name] = str(tbf)
    info = {"design": design, "mode": mode, "lanes": {L.name: L.p for L in layers},
            "sources": [str(top)], "models": [], "gabe_sources": [], "wrapper": str(top),
            "defines": {}, "flow_defines": {}, "incdirs": [str(out)], "data_files": data_files,
            "unit_tbs": units_info,
            "layers": {L.name: {"k": L.k, "g": L.g, "p": L.p, "accw": L.accw, "weight_words":
                                L.wd * L.p, "cycles_est": L.outsz * 0 + L.phw * L.g * L.q * L.k}
                       for L in layers}}
    (out / "build.json").write_text(json.dumps(info, indent=1, sort_keys=True) + "\n")
    return info


if __name__ == "__main__":
    a = sys.argv[1:]
    opt = {a[i]: a[i + 1] for i in range(1, len(a) - 1, 2) if a[i].startswith("--")}
    out = a[0]
    design = opt.get("--design", "i3")
    p = int(opt.get("--p", 1))
    lanes = parse_lanes(opt["--lanes"], p) if "--lanes" in opt else None
    r = build(out, design, p, lanes, opt.get("--weights"), opt.get("--vec"),
              int(opt.get("--units", 3)))
    print(json.dumps({k: r[k] for k in ("design", "mode", "lanes")}, sort_keys=True))
