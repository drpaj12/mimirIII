# Results: I6 NeuraLUT-Assemble and I8 TreeLUT (tool-generated LUT networks)

Rows: `results/lut-vtr.jsonl`, `results/lut-lpm.jsonl` (schema 1). Tables: `python3 -I score/lut_table.py <dir with vtr.jsonl, lpm.jsonl>`.
Designs: `nl-A`, `nl-B`, `nl-C` (I6 settings, `docs/I6-NEURALUT.md`), `nl-B-reg` (B with registers between layers),
`tl-T1`, `tl-T2`, `tl-T3` (I8 settings, `docs/I8-TREELUT.md`). Tools: Odin III 1.6.1 pre-release (origin/main 59349797),
Verilator, VTR from the workspace checkout, architecture `k6_frac_N10_frac_chain_mem32K_40nm`. The RTL simulation ran
on the full tier (10,000 images) and the quick tier (100); the VTR and LPM legs, and the Odin III netlist simulation,
on the quick tier. The "golden" of the vector files is the Python model of each design (class and scores of the model
itself, `tools/neuralut_gen.py`, `tools/treelut_gen.py`), so class match and score match measure Verilog against
Python; accuracy against the labels is the last number of each row.

## Accuracy (Verilator RTL; class and score match the Python model of each design)

| design | top-1 vs label (10,000) | class match (10,000) | score match (10,000) | class match quick | Odin III netlist sim quick | cycles / image |
|---|---|---|---|---|---|---|
| nl-A | 9,555 / 10,000 (95.55 %) | 10,000 | 10,000 | 100 / 100 | n/a / n/a | 786 |
| nl-B | 9,163 / 10,000 (91.63 %) | 10,000 | 10,000 | 100 / 100 | 100 / 100 | 786 |
| nl-B-reg | 9,163 / 10,000 (91.63 %) | 10,000 | 10,000 | 100 / 100 | 100 / 100 | 790 |
| nl-C | 9,614 / 10,000 (96.14 %) | 10,000 | 10,000 | 100 / 100 | n/a / n/a | 786 |
| tl-T1 | 9,626 / 10,000 (96.26 %) | 10,000 | 10,000 | 100 / 100 | 100 / 100 | 788 |
| tl-T2 | 9,064 / 10,000 (90.64 %) | 10,000 | 10,000 | 100 / 100 | 100 / 100 | 786 |
| tl-T3 | 9,764 / 10,000 (97.64 %) | 10,000 | 10,000 | 100 / 100 | 100 / 100 | 788 |

## VTR k6 target (route, STA, ACE2 + VPR power)

| design | LUT | FF | adder | CLB | min W | wirelength | Fmax MHz | crit path ns | latency us | power mW | energy uJ / image |
|---|---|---|---|---|---|---|---|---|---|---|---|
| nl-A | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| nl-B | 1,990 | 471 | 51 | 188 | 74 | 26,922 | 57.2 | 17.49 | 13.7 | 7.5 | 0.103 |
| nl-B-reg | 2,938 | 1,643 | 56 | 223 | 70 | 30,575 | 73.0 | 13.71 | 10.8 | 10.7 | 0.116 |
| nl-C | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| tl-T1 | 7,030 | 2,758 | 1,390 | 719 | 138 | 152,728 | 46.4 | 21.57 | 17.0 | 41.2 | 0.699 |
| tl-T2 | 2,548 | 1,438 | 621 | 251 | 74 | 32,582 | 45.5 | 21.98 | 17.3 | 11.0 | 0.190 |
| tl-T3 | 17,428 | 3,821 | 3,096 | 1,847 | 192 | 548,779 | 42.4 | 23.60 | 18.6 | 120.6 | 2.243 |

## Cyclone V target (Odin III LPM netlist, instance counts)

| design | lpm_add_sub | lpm_compare | lpm_mult | netlist bytes | purity | read-back |
|---|---|---|---|---|---|---|
| nl-A | 12 | 100610 | 0 | 62,706,493 | pass | pass |
| nl-B | 12 | 28398 | 0 | 17,601,870 | pass | pass |
| nl-B-reg | 12 | 28399 | 0 | 17,607,158 | pass | pass |
| nl-C | 12 | 77452 | 0 | 47,676,057 | pass | pass |
| tl-T1 | 301 | 3098 | 0 | 6,073,168 | pass | pass |
| tl-T2 | 151 | 1004 | 0 | 1,820,039 | pass | pass |
| tl-T3 | 600 | 4157 | 0 | 16,673,791 | pass | pass |

## Reading

- Python model and Verilog agree on class and on all ten score fields for 10,000 / 10,000 images in all seven
  designs; the label accuracy of the Verilog equals the Python model's (no cause of difference to report).
- All designs classify one image in 786 to 790 cycles (784 to load the pixels, 2 to 6 for start, the pipeline and the
  result register); the cores are 1 to 4 cycles deep. For I1 (same boards, bit-exact LeNet-5, 98.74 %) an image takes
  609,339 cycles at N = 8 (`docs/RESULTS.md`): 0.1 % of that here, at 90.6 to 97.6 % top-1 and 1,990 to 17,428 LUTs
  (routed designs) against I1's 8,268 LUTs, 73 mult_36 and 126 RAM blocks. Here no design uses a multiplier or a RAM; the pixel
  stream (784 cycles) is the floor of every design with this interface.
- Best accuracy: tl-T3 (97.64 %, 17,428 LUTs); best accuracy per LUT among the routed designs: nl-B (91.63 %, 1,990
  LUTs) and tl-T1 (96.26 %, 7,030 LUTs). The two methods are not compared further here (questions come later).
- nl-B-reg against nl-B: +948 LUTs and +1,172 FFs (the registers sit before every layer, on 784-bit and wider
  vectors), critical path 17.49 ns to 13.71 ns, 4 more cycles.
- Missing cells: nl-A and nl-C have no VTR area, speed or power and no Odin III netlist-simulation result, because the
  Odin III `abc` pass exceeds its 4 GiB budget (details and exact error in `docs/I6-NEURALUT.md`). Their accuracy and
  LPM netlist rows exist. The Cyclone V columns beyond instance counts need Quartus (laptop, later).
- Power is ACE2 vectorless activity with the VPR model: a coarse estimate; the
  energy per image is power x latency (latency = cycles x critical path, no pipelining credit).

## sha256 of the generated Verilog of this run (not committed)

| design | files |
|---|---|
| nl-A | `mnist_top.v` a03e1571b3063f79 | `neuralut_all.v` a2c04019f484ed85 |
| nl-B | `mnist_top.v` 1f8ae6c2a0ac02fc | `neuralut_all.v` 99be6f62ffff45d1 |
| nl-B-reg | `mnist_top.v` 1abfeec993155c31 | `neuralut_all.v` b5cdc33590eb17e9 |
| nl-C | `mnist_top.v` aba5d4723b06dd40 | `neuralut_all.v` 2fc64969bc53fafe |
| tl-T1 | `mnist_top.v` 44382d2d96e6905b | `treelut_all.v` a5da94709eed1924 |
| tl-T2 | `mnist_top.v` 208aa746679665b7 | `treelut_all.v` bc40212d341b8cfe |
| tl-T3 | `mnist_top.v` c9627e61358bcd06 | `treelut_all.v` f787c7e3c20f0d0b |

