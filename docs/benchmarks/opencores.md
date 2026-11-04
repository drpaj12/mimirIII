# OpenCores suite (`opencores`)

Peter 2026-11-04: add stable, FPGA-proven Verilog projects of opencores.org to the benchmark list, runnable
through a testbench and as deep into the VTR flow as they go. Purpose: Mimir benchmark set for the Odin III
VTR flow and the silicon ladder. Measures: `sim_iverilog`, `sim_odin`, `vtr_stage`, LUTs, FFs, cpd.

Flow: Odin III 1.2.0 (ABI 7), commit 4c91edff1303e7c435f1f5e0bae16f0dc037bc52, 6-LUT script of the
catalogue; VTR flow via `odin3-flow` (arch k6_frac_N10_frac_chain_mem32K_40nm, seed 1), each design in one
`heavy-run`. Design sha256 = sha256 of the sorted `relpath sha256` lines of the RTL files read.

| project | licence | source | top | LOC | testbench | sim_iverilog | sim_odin | deepest VTR stage | LUTs | FFs | cpd | too big | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

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
