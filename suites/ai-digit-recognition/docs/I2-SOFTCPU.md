# I2: a soft CPU running the int8 LeNet-5 written in C

Purpose: I2 is the processor point of the AI digit recognition design space. One small RISC-V core, a program ROM, a
data RAM and a small memory-mapped block run the same int8 LeNet-5 as the golden model, as C code. We measure top-1
accuracy and bit-exact match, cycles per image, and the VTR k6 and Cyclone V LPM rows, the same way as I1.

## What is in the design

- `sw/lenet.c`, `sw/main.c`, `sw/crt0.S`, `sw/link.ld`: the C port of `golden/lenet_int8.py`. `sw/host_test.c` runs
  the same `lenet()` on the host with gcc against the golden vectors.
- Weights and requantisation constants are not committed. `tools/gen_sw_weights.py` converts the pinned transmission
  file of Gabe Litteken's repository into `weights.c` / `weights.h` inside the build directory.
- `tools/build_i2.py <setting> <out_dir>` compiles the firmware with `riscv64-unknown-elf-gcc` (`-march=rv32i` or
  `rv32im`, `-mabi=ilp32`), writes the ROM image `i2_rom.hex` and `build.json`. Nothing of the cores or of the
  weights is copied: the cores are read by path from the pinned checkouts (`pins.toml`: `picorv32`, and the BRISC-V
  mcu "Arduino-on-RISC-V", MIT).
- `rtl/i2_softcpu/`: our own files. `mnist_top_pico.v` and `mnist_top_brisc.v` (the `mnist_top` wrapper of
  `docs/INTERFACE.md` around each core), `i2_mem.v` (a 64 KiB ROM with two read ports, loaded by `$readmemh`, and a
  4 KiB byte-writable RAM, both in the form Odin III maps to hard RAM), `i2_mmio.v` (the pixel stream in, and
  prediction, scores and done out). The CPU polls; there are no blocking reads. The wrapper, ROM and RAM count in the
  area.
- `tools/run_i2.py <setting> <tier> <work_dir>` builds and simulates. The common `tb/mnist_tb.v` is used unchanged.
  Per-image cycle budget 500 million. The simulator is Verilator (`--x-assign fast --x-initial fast -O3`), which
  does not change results; the Verilator cap is 4 GB and the run time limit 172800 s (48 h).

## Settings

| Id | Core | ISA | 8x8 products |
|---|---|---|---|
| `i2-pico-fm` | PicoRV32, ENABLE_FAST_MUL | rv32im | hardware, single cycle (`pcpi_fast_mul`) |
| `i2-pico-m` | PicoRV32, ENABLE_MUL | rv32im | hardware, multi-cycle (`picorv32_pcpi_mul`) |
| `i2-pico-i-tab` | PicoRV32, no multiplier | rv32i | quarter-square table in C |
| `i2-pico-i-gcc` | PicoRV32, no multiplier | rv32i | libgcc `__mulsi3` |
| `i2-brisc-i-tab` | BRISC-V mcu | rv32i | quarter-square table in C |
| `i2-brisc-i-gcc` | BRISC-V mcu | rv32i | libgcc `__mulsi3` |

The BRISC-V mcu core has no M extension, so it has only the two rv32i settings. Firmware: about 62 KB of code and
read-only data for the rv32im settings and about 64 KB for the rv32i settings (weights included), 2.4 KB of
zero-initialised data, so ROM 64 KiB and RAM 4 KiB.

## Results

Tiers: quick = 100 images, full = 10,000 images. Verilator everywhere. "Top-1" is label_correct over n. "Class" and
"score" are matches against the golden (all must equal n for bit-exact). The golden is 98.74 % on the full tier and 98
% on the quick tier.

| Setting | Cycles/img | Quick (100) class / score / top-1 | Full (10,000) class / score / top-1 |
|---|---|---|---|
| i2-pico-fm | 5,667,193 | 100 / 100 / 98 | 10000 / 10000 / 9874: PASS |
| i2-pico-m | 11,904,561 | 100 / 100 / 98 | 10000 / 10000 / 9874: PASS |
| i2-pico-i-tab | 21,619,520 | 100 / 100 / 98 | 10000 / 10000 / 9874: PASS |
| i2-pico-i-gcc | 35,714,755 | 100 / 100 / 98 | not run (quick tier only) |
| i2-brisc-i-tab | 8,165,741 | 100 / 100 / 98 | 10000 / 10000 / 9874: PASS |
| i2-brisc-i-gcc | 14,662,188 | 100 / 100 / 98 | not run (quick tier only) |

The C code was also checked on the host with gcc: 10,000 of 10,000 class and score match, 9,874 correct.
Verilator wall time on the full tier: pico-fm 12,336 s, brisc-i-tab 16,987 s, pico-i-tab 34,543 s, pico-m 19,349 s.

VTR k6 (`k6_frac_N10_frac_chain_mem32K_40nm`, route plus STA plus power, channel width 1.3 x minimum rounded up as for
I1, quick-tier activity). The full table with all columns is `TABLE.md`; one datasheet per design is in `datasheets/`.

| Setting | LUT | FF | CLB | RAM blocks | mult_36 | min W | Fmax MHz | Power mW | Latency ms/img |
|---|---|---|---|---|---|---|---|---|---|
| i2-pico-fm | 5,567 | 1,750 | 448 | 20 | 0 | 74 | 62.0 | 38.3 | 91.5 |
| i2-pico-m | 3,355 | 1,872 | 322 | 20 | 0 | 74 | 159.0 | 62.3 | 74.9 |
| i2-pico-i-tab / -gcc | 2,902 | 1,595 | 275 | 20 | 0 | 68 | 160.6 | 68.9 | 134.6 / 222.4 |
| i2-brisc-i-tab / -gcc | 4,206 | 1,265 | 402 | 20 | 0 | 82 | 69.9 | 55.6 | 116.9 / 209.9 |

(The same hardware serves the tab and gcc settings, so area and Fmax are equal; only the program differs.) The
power channel width W is in `TABLE.md` (100 for pico, 110 for BRISC-V).

Cyclone V LPM: the Odin III LPM netlist is produced for the six settings (`i2-pico-m` since the Odin III front-end fix below) (counts in
`results/i2-lpm.jsonl`). Quartus is not run here, so ALM, M10K, DSP, Fmax and power are NULL with that reason, and the
LPM netlist is not simulated (the library stubs are empty), as for I1.

## Deviations and what is not done

- The full tier was not run for `i2-pico-i-gcc` and `i2-brisc-i-gcc`. They need about 36 and 15 million cycles per
  image and add nothing to the bit-exact claim; their rows say "quick" in the accuracy tier column.
- `i2-pico-m` full tier: the third run (Verilator, `heavy-run`) finished: 10,000 of 10,000 class and score match,
  9,874 correct, 19,349 s. Earlier runs stopped at the old 6 h limit and were lost on 2026-11-11 (the lane's own
  `pkill` ended the wrapper process).
- `i2-pico-m` VTR and LPM legs used the Odin III release binary built from main b042fdf5 (PR #435, which fixes the
  ENABLE_MUL front-end error below). The other I2 rows keep the binary they were made with. Same architecture and
  options as the other I2 rows; quick-tier activity.
- iverilog on the quick tier: only `i2-pico-fm` finished (10,951 s). The other three runs stopped at the 21,600 s limit,
  so iverilog is recorded as "not finished" for them in `results/i2-rtl.jsonl`. Verilator is the simulator of record.
- Odin III `sim_tb` was not run on any I2 design. A probe with `lower` (no `--keep-mem-cells`) on the 2-image tier
  of `i2-pico-fm` simulated about 520 time units per second, which is 52 testbench cycles per second; one image
  needs 5.7 million cycles, so over 30 hours per image. The P6 runs found `lower --keep-mem-cells` much faster (about
  1,000 cycles per second on I3), which would still be about 1.5 hours per image for the fastest I2 setting; this was
  not tried. The rows say "Odin III sim_tb not run on this design".
- No `vtr-k6-fixed` rows (fixed-device comparison of P6) for I2.
- Power is vectorless ACE2 activity at the quick-tier stimulus, as for the other designs.

## Odin III gaps

- Fixed in Odin III PR #435 (was open when the other I2 rows were made): `i2-pico-m` (ENABLE_MUL): `picorv32.v:2264:34: error: non-constant index into 'next_rd' is not supported in a
  concatenation target`. The line is the carry-chain step of module `picorv32_pcpi_mul`
  (`{next_rdt[j+CARRY_CHAIN-1], next_rd[j +: CARRY_CHAIN]} = ...` in a loop over `j`), reached with the default
  `CARRY_CHAIN`. The pass `read_verilog` stops with `ODIN3_ERR_PARSE`; both the VTR and the LPM flow fail the same
  way, at once. We did not edit picorv32. With the fix both legs run. (`picorv32_pcpi_fast_mul`, used by `i2-pico-fm`, reads fine.)
- BRISC-V mcu: the LPM netlist is produced; Odin III warns `output port branch_op is coerced to inout` (and the same
  for `memRead`, `memWrite`) from the generated top. No effect on the results.

## Reproduce

    python3 -I tools/build_i2.py pico-fm <build_dir>
    python3 -I tools/run_i2.py pico-fm quick <work_dir>          # then full; Verilator
    python3 -I score/vtr_leg.py --design i2-pico-fm --build <work_dir>/i2-pico-fm/build.json \
        --rtl-result <result.json> --vec <vec>/quick --work <w> --out vtr.jsonl --no-netlist-sim
    python3 -I score/lpm_leg.py --design i2-pico-fm --build <work_dir>/i2-pico-fm/build.json \
        --rtl-result <result.json> --vec <vec>/quick --work <w> --out lpm.jsonl

Rows: `results/i2-rtl.jsonl` (simulations), `results/i2-vtr.jsonl`, `results/i2-lpm.jsonl`.
