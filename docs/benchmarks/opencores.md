# OpenCores suite (`opencores`)

Peter 2026-11-04: add stable, FPGA-proven Verilog projects of opencores.org to the benchmark list, runnable
through a testbench and as deep into the VTR flow as they go. Purpose: Mimir benchmark set for the Odin III
VTR flow and the silicon ladder. Measures: `sim_iverilog`, `sim_odin`, `vtr_stage`, LUTs, FFs, cpd.

Flow: Odin III 1.2.0 (ABI 7), commit 4c91edff1303e7c435f1f5e0bae16f0dc037bc52, 6-LUT script of the
catalogue; VTR flow via `odin3-flow` (arch k6_frac_N10_frac_chain_mem32K_40nm, seed 1), each design in one
`heavy-run`. Design sha256 = sha256 of the sorted `relpath sha256` lines of the RTL files read.

| project | licence | source | top | LOC | testbench | sim_iverilog | sim_odin | deepest VTR stage | LUTs | FFs | cpd | too big | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
