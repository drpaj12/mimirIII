# I4: fixed-weight datapath, weights as constants

Same generator and architecture as I3 (`docs/I3-DATAFLOW.md`), with `--design i4`: the weights are not in RAM; each
lane's weight read is a `case` on the weight address with the weights as constants in the Verilog (one synchronous
read, so the pipeline and the cycle counts are those of I3 with the same lanes). "Unrolled" here means a layer has one
lane per output channel (all channels computed at once, K sequential steps); a "folded" layer has one lane. A fully
spatial unroll (every product a constant multiplier, a K-input adder tree per channel) was not built, see below.
Registered in `implementations.toml` as `i4-fc`, `i4-conv2-fc`, `i4-all`.

## Settings

| Setting | Lanes conv1 / conv2 / fc1 / fc2 / fc3 | Latency (cycles) | II (cycles) | Slowest stage |
|---|---|---|---|---|
| `i4-fc` | 1 / 1 / 120 / 84 / 10 | 124,561 | 86,409 | conv2 (folded) |
| `i4-conv2-fc` | 1 / 16 / 120 / 84 / 10 | 43,576 | 36,513 | conv1 (folded) |
| `i4-all` | 6 / 16 / 120 / 84 / 10 | 13,161 | 6,098 | conv1 (169 windows x 4 x 9 = 6,084) |

## Verification

| Check | Result |
|---|---|
| Unit tbs per layer (3 frames, golden tensors), iverilog, all three settings | all PASS |
| Common tb and pipelined tb, quick tier, Verilator, all three | PASS 100/100 class and score, top-1 98/100 |
| Common tb and pipelined tb, full tier (10,000), Verilator, all three | PASS 10,000/10,000 class and score, top-1 9,874 (98.74 %) |
| Common tb, quick tier, iverilog, `i4-all` | PASS 100/100; wall 3,497 s (the unrolled lanes make iverilog slow) |
| Odin III v1.6.1 `sim_tb` (`lower --keep-mem-cells`), 2-image tier | PASS for all three, class and score 2 of 2: i4-all 21.6 cycles/s (1,217 s), i4-conv2-fc 27.5 (3,169 s), i4-fc 24.6 (10,118 s); 100-image quick tier running |

Verilator full-tier wall times: serial 252 / 736 / 1,657 s, pipelined 104 / 507 / 1,160 s (`i4-all` / `i4-conv2-fc` / `i4-fc`).

## Results (VTR k6, quick-tier legs; power at the routable channel width, marked in the table)

| Setting | LUT | FF | CLB | mult_36 | RAM blk | min W | Fmax MHz | latency us | images/s (pipelined) | power mW (W) | uJ/image |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `i4-fc` | 50,737 | 19,839 | 5,773 | 115 | 5 | 178 | 108.1 | 1,152.0 | 868 | 482.9 (240) | 556.3 |
| `i4-conv2-fc` | 51,841 | 21,021 | 5,422 | 123 | 5 | 172 | 110.1 | 395.7 | 2,527 | 462.9 (230) | 183.2 |
| `i4-all` | 52,259 | 21,377 | 5,448 | 124 | 5 | 180 | 108.0 | 121.9 | 8,205 | 488.8 (240) | 59.6 |

Findings:

- The constant weights cost about 50,000 LUTs whichever layers are unrolled: the 59,800 weight bytes become logic
  (a LUT6 ROM holds 64 bits, so at least 7,500 LUTs; the flow used far more). Against I3, `i3-df-p8` (4,926 LUTs, 28 RAM
  blocks) is 10 times smaller and, at 154.6 us, slower than `i4-all` (121.9 us) by only 27 %. At equal bit-exact accuracy
  (98.74 %) I3 dominates I4 on LUTs, power and energy; `i4-all` wins on latency and throughput.
- Lane count moves latency, not LUTs: the weight ROM, not the multipliers, is the area. The multiplier count
  (mult_36 115 to 124) follows the lanes, 221 to 241 `lpm_mult` in the LPM netlists.
- Fit: the LPM netlists have 221 to 241 `lpm_mult` against 87 variable-precision DSP blocks (174 18x18) on the 5CSEMA5;
  so I4 does not fit as DSP multipliers there (the fit is not measured: Quartus not run).
- Fully spatial unroll not built: it needs one constant multiplier per nonzero weight, 59,800 for the network
  (fc1 alone 48,000), each at least a few dozen LUTs, so well over a million LUTs against 32,075 ALMs; not attempted.
  No measurement of a constant multiplier was made, so this is an order-of-magnitude statement.
- Power: the VPR power step needs a channel width above 100 for these designs (W=230 to 240, 1.3 x the minimum
  width); power is therefore not same-W comparable with I3 (dagger in `TABLE.md`).

Odin III gaps: none new. The 120-lane case-ROM designs (1.8 MB of generated Verilog) went through `odin3-flow --target vtr`
and `--target lpm` without error.
