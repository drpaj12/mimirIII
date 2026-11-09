# OpenCores suite (`opencores`)

Peter 2026-11-04: add stable, FPGA-proven Verilog projects of opencores.org to the benchmark list, runnable
through a testbench and as deep into the VTR flow as they go. Purpose: Mimir benchmark set for the Odin III
VTR flow and the silicon ladder. Measures: `sim_iverilog`, `sim_odin`, `vtr_stage`, LUTs, FFs, cpd.

Flow: Odin III 1.2.0 (ABI 7), commit 4c91edff1303e7c435f1f5e0bae16f0dc037bc52 (`build/rel-main2`), the 6-LUT script
of the catalogue (`read_verilog --nolatches --vtr-compat; proc; fsm; opt; flatten; opt -full; wreduce; hardmap;
lower; abc --lut 6`), then VPR (arch k6_frac_N10_frac_chain_mem32K_40nm, seed 1) through `odin3-flow`, or Odin III
plus a direct `vpr` run for designs that need include directories or file-relative data (the `source` text of
each `vtr_stage` row says which). Each design ran in one `heavy-run`. Design sha256 = sha256 of the sorted
`relpath sha256` lines of the RTL files read. Per-project licence, source URL, revision, page description and
OpenCores flags are `measures.tsv` rows (`licence`, `src_rev`, `desc`, `oc_stage`, `oc_design_done`,
`oc_fpga_proven`). `sim_odin` = Odin III `sim_tb` of the same testbench; `refused` carries the exact message in
`sim_odin_msg`. The table is ordered by RTL line count. Flags: stage / design done / FPGA proven as the OpenCores
page states them.

| project | licence | top | LOC | tb_origin | sim_iverilog | sim_odin | deepest VTR stage | LUTs | FFs | cpd (ns) | oc flags | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| mmuart | GPL-3.0 | uart | 253 | mimir-written | pass | pass | timing | 126 | 96 | 2.31268 | stable/dd/fpga |  |
| verilog_cordic_core | none stated | cordic | 379 | mimir-written | pass | pass | timing | 1153 | 765 | 4.1275 | unknown/dd/fpga | synthesis variant (mimir-patched) |
| simple_spi | none stated | simple_spi_top | 456 | upstream-fixed | pass | pass | timing | 189 | 131 | 2.37109 | stable/dd/fpga |  |
| sha3_low | Apache-2.0 | keccak | 499 | upstream | pass | refused | timing | 5035 | 2244 | 4.44096 | stable/dd/fpga | Odin sim: testbench:0: expression could not be evaluated or written |
| sha3_high | Apache-2.0 | keccak | 618 | upstream | pass | refused | timing | 7824 | 2211 | 9.22457 | stable/dd/fpga | Odin sim: testbench:0: expression could not be evaluated or written |
| spi | LGPL-2.1+ | spi_top | 633 | upstream | pass | pass | timing | 612 | 229 | 6.56467 | stable/-/fpga |  |
| wb_lcd | LGPL-3.0+ | wb_lcd | 695 | mimir-written | pass | pass | timing | 1049 | 636 | 4.29499 | stable/dd/fpga |  |
| sdram_16bit | GPL-2.0+ | sdram | 741 | upstream-fixed | pass | fail | timing | 281 | 182 | 4.01425 | stable/dd/fpga | Odin sim: lower: '$tribuf' '$c6' (output net 'IO') has no bit-level cell in the registry and is not  |
| tiny_aes | Apache-2.0 | aes_128 | 764 | upstream | pass | pass | elab | - | - | - | stable/dd/fpga | too big for now: abc stops, needs more than 6 GB (design budget 6442450944 bytes); abc needs more than 6442450944 bytes (the design's budget is 6442450944 bytes: the smaller of 60% of physical  |
| i2cslave | LGPL-2.1+ | i2cSlaveTop | 769 | upstream | fail | fail | timing | 198 | 139 | 2.21504 | stable/dd/fpga | Odin sim: lower: '$tribuf' '$c18' (output net 'sda') has no bit-level cell in the registry and is no; iverilog: timeout (vvp cap reached) without end summary |
| mips_16 | none stated in the source or docs | mips_16_core_top | 945 | mimir-written | pass | pass | timing | 71 | 36 | 4.03484 | stable/dd/- | synthesis variant (mimir-patched) |
| mips_16_noxarm | none stated in the source or docs | mips_16_core_top | 945 | mimir-written | - | - | timing | 639 | 247 | 5.72277 | stable/dd/- |  |
| ca_prng | BSD-3-Clause style | ca_prng | 1311 | upstream | pass | pass | timing | 158 | 40 | 2.38342 | stable/dd/fpga |  |
| i2c | none named | i2c_master_top | 1556 | upstream | pass | refused | timing | 316 | 200 | 2.80648 | stable/dd/fpga | Odin sim: tst_bench_top.v:140: unsupported: parameter override on a DUT instance (the DUT is already |
| pipelined_fft_256 | none named | FFT256 | 2055 | upstream-fixed | pass | fail | none | - | - | - | stable/-/- | odin3_ast_comment_add: end is not 0 or a later loc of loc's buffer; Odin sim: parses and elaborates, did not finish within the sim time limit (1800 s) |
| des | none stated | des | 2061 | upstream | pass | refused | timing | 1877 | 1984 | 3.70378 | stable/-/- | Odin sim: des_test_po.v:452: unsupported: expression syntax |
| uart2spi | LGPL-2.1+ | top | 2583 | upstream-fixed | - | refused | timing | 685 | 422 | 3.30854 | unknown/-/- | Odin sim: tb_top.v:51: unsupported: real number |
| attiny_atmega_xmega_core | custom BSD-style one-condition not | mega_core | 3352 | none | none | none | timing | 1973 | 373 | 14.924 | stable/dd/fpga |  |
| dblclockfft | LGPL-3.0+ | fftmain | 3790 | mimir-written | pass | pass | timing | 43969 | 30280 | 5.19941 | stable/dd/fpga |  |
| sdr_ctrl | LGPL-2.1+ | sdrc_top | 3929 | upstream | pass | refused | timing | 1710 | 1130 | 5.57435 | stable/dd/- | Odin sim: tb_top.sv:111: unsupported: real number |
| reed_solomon_decoder | GPL-3.0+ | RS_dec | 4366 | upstream-fixed | pass | pass | timing | 4690 | 2882 | 6.14868 | stable/dd/fpga |  |
| vga_lcd | none named | vga_enh_top | 4900 | upstream-fixed | pass | refused | timing | 24862 | 16529 | 8.47413 | stable/dd/fpga | Odin sim: test_bench_top.v:569: unsupported: real number |
| amber | LGPL-2.1+ | a23_core | 5419 | none | none | none | map | - | - | - | stable/dd/fpga | lower: module 'a23_core': '$mem' '$c2032' would create 28238599 nodes (cap 16777216) |
| a-z80 | GPL-2.0 in license.txt; several fi | z80_top_direct_n | 5649 | none | none | none | none | - | - | - | stable/dd/fpga | coremodules.vh:404:10: error: net 'db1[0]' is driven by inout port 'db' of instance 'alu_flags_' and by logic  |
| a-z80-modified | GPL-2.0 in license.txt; several fi | z80_top_direct_n | 5649 | mimir-written | pass | none | timing | 2016 | 365 | 11.3704 | stable/dd/fpga | synthesis variant (mimir-patched) |
| ethmac | LGPL-2.1+ | eth_top | 12270 | upstream | fail | refused | timing | 16463 | 10543 | 7.71791 | stable/dd/fpga | Odin sim: wb_master32.v:355: unsupported: real number; iverilog: vvp cap reached (1800 s) without an end summary; last line seen: TEST 5: RANDOM RECEIVE AN |
| usbhostslave | LGPL-2.1+ | usbHostSlave | 12433 | upstream-fixed | pass | refused | timing | 10498 | 7079 | 5.49712 | stable/dd/fpga | Odin sim: sepHostSlaveTestHarness.v:49: unsupported: @* event control (list the signals) |

## Verdicts

- DES (opencores `des`, DES/Triple DES IP cores, performance-optimised variant `perf_opt/des.v`): the project's own
  testbench `des_test_po.v` passes in iverilog (self-check prints `ERROR:` on a mismatch, none appeared), and the
  design runs through the whole VTR flow to timing (1877 LUTs, 1984 FFs, 222 CLBs, 3.70 ns). Odin III's testbench
  pass refuses the bench (`des_test_po.v:66: unsupported: compiler directive`). Verdict: opencores DES is good;
  no own DES is needed. No licence is named in the sources or on the page ("none stated", flagged).
- Too big for now (stopped in a stage, kept in the table): tiny_aes (Odin III `abc` needs more than the 6 GB
  budget, stops at map). No other design hit the 3 GB or 2 h limits: the largest VTR runs were dblclockfft
  (43,969 LUTs, 1.3 GB, 582 s) and vga_lcd (24,862 LUTs, 0.77 GB, 230 s).

## Odin III gaps seen

- Tri-state / inout below the top is refused (D3): i2cslave, a-z80, sdr_ctrl (`'sdr_dq' has two drivers`);
  `write_blif --vtr` refuses an inout top port (sdram_16bit). Routed to the Odin III tri-state lane.
- pipelined_fft_256: the 1.4.0 parser error (`odin3_ast_comment_add`) is gone in 1.6.0; the testbench top is
  `FFT256_tb` (not `FFT256_TB`). `sim_tb` then runs past the 1800 s limit of the 2026-11-09 re-run (10240-14336
  flip-flop RAM models in the 4-state DUT).
- Non-constant for-loop bound (verilog_cordic_core `cordic.v:178`): worked around by a patch.
- Include directories only through a project file list (`-f` with `+incdir+`), not the working directory;
  `$readmemh`/`$readmemb` paths are resolved beside the source file (dblclockfft needed a run copy).
- `odin3-flow` cannot take `read_verilog` flags or include directories; direct runs were used where needed.
- Vendor primitives (`gng_coef`, `IOBUF`, `ODDR2`): `--auto-blackbox` elaborates, but `hardmap` / `write_blif --vtr`
  refuse the black boxes (`partial_map`).
- Odin III `sim_tb` (re-run 2026-11-09 with 1.6.0, `rel-v160`): compiler directives, tasks, several files, signals
  wider than 64 bits, x/z literals and bench-side submodules are supported now. Still refused: `real` (ethmac,
  sdr_ctrl, uart2spi, vga_lcd), `@*` (usbhostslave), a parameter override on a DUT instance (i2c), an expression
  syntax at `des_test_po.v:452`; `$tribuf` over an inout net fails in `lower` (i2cslave, sdram_16bit); sha3_low and
  sha3_high fail with `testbench:0: expression could not be evaluated or written` (no file:line). The messages are in
  the `sim_odin_msg` rows. Flows per design: `read_verilog [flags] files; proc; opt; lower --keep-sel; sim_tb -I -D
  tb files` (mips_16: `--case-xz-never`, no `opt`, `lower --keep-sel --keep-mem`; simple_spi: `lower --keep-sel
  --async keep`, patched bench).

## Removed from the suite

- gng (Gaussian Noise Generator, Peter 2026-11-04: "gng is OUT"): the project does not ship the vendor
  modules `gng_coef` and `gng_smul_16_18_sadd_37` (Xilinx-generated), so the RTL does not elaborate on its own
  (iverilog: `gng_interp.v:126: error: Unknown module type: gng_coef`; Odin III with `--auto-blackbox` stops at
  `hardmap`). It has no registry row and is not run again. The testbench we wrote for it stays in
  `data/benchmarks/opencores-tb/gng/` (mimir PR #35), with behavioural stand-ins for the two modules.

## Inout / tri-state designs

sdram_16bit (inout `sdram_data_io`: `write_blif --vtr` refuses it), i2cslave (tri-state driver below the top,
D3) and a-z80 (internal tri-state nets, D3) keep their current rows; they may get an Odin III conversion pass
later.
