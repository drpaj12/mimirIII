# I1: Gabe Litteken's programmable TPU

Source: `https://github.com/littekge/USS_Tensor_Processing_Unit` at commit `8e85de4592fc7df6fa264c06ff9ff0891536e497`
(MIT). Read by path, never copied. A programmable output-stationary systolic array (N x N multiply-accumulate
units), a program memory of 128-bit instructions, two 64K x 8 data memories plus a 1K x 8 input/output buffer, a
vector processor pair (im2col, max pooling, requantisation, ReLU), and an SPI front end (Message Protocol v0.3).
The network (weights, per-layer requantisation) and the program are `Benchmarks/LeNet_5_TRANSMISSION.bin`.

## What each size N measures

N is the edge of the systolic array (`Systolic_Array #(.N(...))`, 8 in his build). The array is the only
datapath that scales; everything else (controller, vector processors, memories, SPI) is fixed. A smaller array
needs more tiles per matrix product, so N trades multipliers against cycles per image:

| N | MAC units (mult) | program | what it measures |
|---|---|---|---|
| 8 | 64 | his program, 1,350 instructions | his design as built |
| 4 | 16 | retiled, 6,607 instructions | quarter the multipliers, more passes |
| 2 | 4 | retiled, 33,140 instructions | smallest array; program memory widened to 16 address bits (65,536 words) |
| 16 | not built | - | not encodable: the ISA dimension fields are 4 bits (at most 15) and the array row/column selects are 4 bits |

The retiled programs come from `tools/retile_program.py`: each MUL/MULTIP run (one output tile accumulated over K)
is re-expanded into N x N output tiles accumulated over K chunks of at most N, with explicit `stride`
instructions; every other instruction is copied. His assembler cannot be used (it needs `stablehlo-opt`, not
installed). Weights and (M0, n) are untouched, so results stay bit-exact; checked with his Python interpreter
(`tools/check_retile.py`) and by simulation.

## Wrapper and models (ours)

- `rtl/i1_tpu/mnist_top_tpu.v`: the P0 interface on top of his `TPU`. It plays his Arduino: after reset it flashes
  the transmission over SPI from a ROM (`FLASH_HEX`, `FLASH_LEN`), lets the first run drain, raises `done`
  (initialisation, `docs/INTERFACE.md`); per image it sends an INPUT transmission (784 pixels to address 0x1), reads
  the ten outputs back (external mode) and takes the first maximum as the class. The ROM and the SPI master are
  the wrapper's cost, counted in the design. SPI runs at 8 clocks per bit, so streaming 784 bytes costs about
  51,000 cycles per image whatever N is.
- `rtl/i1_tpu/models/altsyncram.v`, `scfifo.v`: behavioural models of the two Altera megafunctions his
  generated wrappers instantiate. They reproduce the Cyclone V timing his testbenches expect: both his
  `TB_Step1_DataMemory` (10 tests) and `TB_Step8_FullSystem` (16 tests) pass with them. They are used for
  simulation and for the VTR flow. The LPM flow leaves `scfifo` and `altsyncram` as megafunction instances
  (`--read-opt=--auto-blackbox`).
- `tools/build_i1.py` writes the build directory: the flash hex, `gen/TPU.v` (his `TPU.v` with `.N(8)` changed to N;
  for N = 2 also the program-memory address widths), and `build.json` (his files by path, our files, defines).

## Findings about the TPU as a benchmark

- The program is data independent, so cycles per image are identical for every image of a tier.
- Compute dominates cycles per image at every N; the SPI input is a fixed cost of about 51,000 cycles (measured
  in simulation: 784 bytes at 65 cycles each).
- The design is sequential and not pipelined across images: initiation interval = cycles per image.
