# OpenCores synthesis variants (`synth_origin=mimir-patched`)

The upstream clones under `external/opencores*/` are never edited. Where the upstream RTL cannot give a real
VTR result, a labelled variant is built from a patch kept here, and the measures row `synth_origin` says so.
The registry sha256 of the design stays that of the upstream files.

- `verilog_cordic_core/cordic.v.patch`: the loop in `signed_shifter` (`cordic.v:178`) has the non-constant
  bound `j<i`, which Odin III rejects ("for-loop condition is not constant"). The patch uses the constant bound
  `1<<ITERATION_BITS` with an `if (j < i)` guard: same behaviour. The mimir-written testbench still passes under
  iverilog with the patched DUT (200 checks, 0 errors, largest error 9 LSB).
- `mips_16/instruction_mem.v.patch`: upstream fills the instruction ROM only from the testbench, so synthesis
  keeps just the PC (8 LUTs). The patch adds `initial $readmemb("test2.prog", rom);` (the project's own multiply
  program, `bench/mips_16_core_top/test2.prog`, placed beside the source; not copied here). The mimir-written
  testbench still passes under iverilog with the patched DUT (4 programs, 34 checks, 0 errors).

Apply with `patch -p1` in the project directory (`a/` = project root; `mips_16`: `rtl/instruction_mem.v`).
- `mips_16/mips_16_core_top.v.patch`: the top has only `pc` as output, so synthesis prunes every path that
  cannot reach `pc` (68 LUTs with the ROM patch alone). The patch adds observation outputs `dbg_wb_en`,
  `dbg_wb_dest`, `dbg_wb_data` (the register-file write-back) and `dbg_ex_pipeline` (the EX stage register,
  which holds the ALU result) so the datapath is kept. The testbench connects by name and is unchanged.
