# I7: binarised neural network (our generator)

Purpose (Peter 2026-11-10): one application, many Verilog implementations, so that design patterns in AI
hardware can be studied. I7 is the binarised point: weights and activations are +1 or -1, so
multiply-accumulate becomes XNOR + popcount + threshold. A different model from the reference LeNet-5: scored
on top-1 against the MNIST labels. The Python (integer numpy) model and the Verilog agree on class and on all
ten scores for 10,000 / 10,000 images in every design.

## Networks

Trained in the one existing venv (`work/nnlut-env`, torch 2.4.0 CPU, no installs), plain torch with a
straight-through estimator (`tools/bnn_train.py`; Brevitas not used). Latent weights clipped to [-1, 1], sign
in the forward pass, hard-tanh gradient, batch norm after every layer but the last, Adam lr 0.003 with cosine
decay to 1e-5, batch 100, 100 epochs, seed 7, on the 60,000 training images mapped to the testbench's int8
pixels (`q * S_IN`, as I6/I8). CPU, 4 threads, 4 GB cap. The checkpoint is the last epoch; the test set is
evaluated each epoch for the log only. Last layer: no batch norm, logits = dot / sqrt(nin); at inference the
argmax is taken on the integer popcount (first maximum wins).

| net | layers | first layer | training time | float top-1 (10,000) | integer model top-1 |
|---|---|---|---|---|---|
| M | 784-256-256-256-10 | int8 pixel x binary weight, accumulated while the pixels stream in | 228.6 s | 97.77 % | 97.77 % |
| S | 784-64-64-64-10 | input binarised: bit = (q >= 54), i.e. pixel >= 128 | 106.4 s | 94.44 % | 94.44 % |

Batch norm is folded into one integer threshold per neuron (float64 fold of the running statistics): a hidden
neuron fires when `pc >= T` (XNOR popcount), and a neuron with a negative batch-norm scale has its weights
flipped. In the int8 first layer the neuron fires when `sum(+-q) >= T` with `q` the streamed int8. The integer
model is the model of record: the vector files' golden is its class and scores. Score k = `clip(pc_k - nin/2,
-128, 127)` (the only saturation: the all-match count of a 256-input layer, +128 to +127).

Not done: a binarised CNN (brief: "if time allows").

## Generator and folding (`tools/gen_bnn.py`, stdlib + numpy)

Emits one Verilog-2005 file `mnist_top` (INTERFACE.md), weights and thresholds as constant `case` ROMs, plus
per-layer unit testbenches and the vector files. A layer is folded by (PE, SIMD): PE neurons in parallel, SIMD
input bits per cycle, `(nout/PE) * (nin/SIMD)` cycles. The input register rotates by SIMD bits per step and the
output register shifts in PE bits per neuron group, so the data path has no multiplexer; only the ROM is
indexed. The int8 first layer of M has PE = nout, SIMD = 1 and costs no cycles (it runs during the 784-pixel
stream). Hidden and output layers use the folded engine. Five hardware points from the two networks:

| design | net | folding (PE x SIMD) per layer | layer cycles |
|---|---|---|---|
| S-par | S | first 64x98, hidden 64x64, output 10x64 | 8, 1, 1, 1 |
| S-f1 | S | first 16x49, hidden 16x16, output 10x16 | 64, 16, 16, 4 |
| S-f2 | S | first 8x16, hidden 8x8, output 2x8 | 392, 64, 64, 40 |
| M-f2 | M | hidden 64x64, output 10x64 | 0, 16, 16, 4 |
| M-f1 | M | hidden 16x32, output 10x32 | 0, 128, 128, 8 |

(M with fully parallel hidden layers would need about 65k XNOR-popcount inputs per layer; not generated.)
Design ids in the store are `bnn-<name>`.

## Verification

- Unit tests per layer (`tools/run_bnn_units.py`, iverilog, 24 random inputs per layer against the integer
  model): all 20 pass.
- Quick tier (100 images), iverilog RTL: class and score match 100 / 100 in all five designs.
- Full tier (10,000), Verilator RTL: class match 10,000, score match 10,000 in all five designs.
- Odin III `sim_tb` on the `abc --lut 6` netlist, quick tier: class and score match 100 / 100 in all five.

| design | top-1 vs label, model and Verilog (10,000) | class / score match (10,000) | label correct, quick (100) |
|---|---|---|---|
| S-par, S-f1, S-f2 | 9,444 (94.44 %) | 10,000 / 10,000 | 96 |
| M-f1, M-f2 | 9,777 (97.77 %) | 10,000 / 10,000 | 99 |

## Results (VTR k6, `k6_frac_N10_frac_chain_mem32K_40nm`; quick-tier legs; rows in `results/bnn-*.jsonl`)

| design | top-1 % | cycles / image | LUT | FF | adder | CLB | min W | Fmax MHz | latency us | power mW (W) | energy uJ / image |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S-par | 94.44 | 801 | 8,572 | 2,773 | 39,880 | 9,172 | 48 | 51.0 | 15.7 | 349.1 (100) | 5.480 |
| S-f1 | 94.44 | 890 | 5,560 | 2,613 | 5,998 | 1,522 | 42 | 53.9 | 16.5 | 58.5 (100) | 0.967 |
| S-f2 | 94.44 | 1,350 | 7,594 | 2,387 | 1,247 | 777 | 162 | 52.6 | 25.7 | 46.2 (210) | 1.185 |
| M-f2 | 97.77 | 825 | 34,620 | 7,343 | 40,272 | 11,266 | 242 | 47.4 | 17.4 | n/a | n/a |
| M-f1 | 97.77 | 1,053 | 33,092 | 6,493 | 10,385 | 4,249 | 246 | 51.9 | 20.3 | 317.6 (320) | 6.439 |

Context rows (same table, `docs/RESULTS.md`, `docs/RESULTS-LUT.md`): I1 TPU N=8: 98.74 %, 609,339 cycles, 8,268
LUTs, 73 mult_36, 126 RAM blocks; I6 nl-B: 91.63 %, 1,990 LUTs; I8 tl-T1: 96.26 %, 7,030 LUTs; tl-T3: 97.64 %,
17,428 LUTs. The full table with all columns and the Pareto plots are `docs/TABLE.md`, `.csv`, `.tex`, `plots/`
(regenerated with `mimir import-aidigit` and `mimir aidigit-table`).

Reading (no hypotheses; questions come later):
- Every design is bound by the 784-cycle pixel stream plus folded layer cycles; no design uses a multiplier or
  a RAM block (weights are ROM logic).
- Constant ROMs dominate LUT count of the folded M designs: M-f1 and M-f2 have almost the same LUTs (33,092 and
  34,620) although M-f2 has 4x the XNOR-popcount lanes; the lane logic shows as adders (10,385 vs 40,272) and
  CLBs (4,249 vs 11,266).
- S-f2 (most folded) has more LUTs than S-f1 (7,594 vs 5,560): the longer ROM addressing and counters cost more
  than the lanes saved. It also needs a wide channel (min W 162).
- Power: a power width other than 100 is marked in the table (the score script uses 1.3 x min W rounded up to
  10 when that exceeds 100, as for I6/I8).

## Odin III and tool gaps (build `rel-v161pre`)

- No new Odin III error in the five designs: all five read, lowered, mapped, routed and simulated. The two known
  I6/I8 findings apply: the design must be one file (`tools/lut_legs.py` flattens; here the generator already
  writes one file), and an unused extra module is rejected.
- `odin3-flow` got `--top mnist_top` in `score/vtr_leg.py` from M-f1 on (Peter 2026-11-10: the top is declared);
  S-par, S-f1, S-f2 and M-f2 ran before that change without it (Odin chose the same top; the BLIF is the same
  design).
- M-f2 power: the first `vpr --power` run (W = 320) died silently at "Build routing resource graph". Cause: the
  power step of `score/vtr_leg.py` runs under `capped()` with its default 2 GB cap (not the 4 GB first guessed); the
  rerun peaked at 2.9 GB RSS. Rerun alone (ACE2 + VPR --power, same blif, W = 320, 8 GB cap): total 759.2 mW,
  dynamic 206.5 mW, static 552.7 mW, 13.213 uJ per image. M-f1 (78 x 78) fit under 2 GB at the same W.
- VPR time is large for the M designs because of the wide channel (M-f2 routing about 2 h, M-f1 about 1.5 h).
- The LPM netlists were generated (purity and read-back checks as in the other rows); Cyclone V fit, timing and
  power are parked (Peter 2026-11-10).

## Deviations

- Plain torch STE instead of Brevitas (permitted by the brief).
- No binarised CNN.
- Weights as constants only (no RAM variant).
- Quick-tier VTR and LPM legs (as I1, I6, I8); full-tier accuracy from Verilator.
- Training: one run per network, no hyperparameter search; 100 epochs.

## Reproduce

    OMP_NUM_THREADS=4 work/nnlut-env/bin/python tools/bnn_train.py M <train_dir> --epochs 100   # and S
    python3 tools/run_bnn.py <train_dir> <run_dir> S-f2 S-f1 S-par M-f2 M-f1

(`run_bnn.py`: generate, unit tests, iverilog quick tier, then `tools/lut_legs.py`.) Generated Verilog,
weights and MNIST data are not committed. sha256 (first 16 hex digits) of the generated `mnist_top.v` of this
run: S-par 7a39f228d72c7589, S-f1 7cdbd32117279b89, S-f2 ddeb6b3b35a78b7d, M-f2 8b9d6bc0f1f7ce69, M-f1
5e55e2b1475ad67f. A retrain on other hardware may give different weights.
