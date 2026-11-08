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

## a-z80-modified (`a-z80-modified/`, design `a-z80-modified`, 2026-11-08)

Peter 2026-11-08: a version of the A-Z80 CPU with no bidirectional wires, called "modified", every change commented.
The upstream clone is untouched; `a-z80-modified/cpu/**.patch` (15 files, `patch -p1` in the project root, `a/` = the
project directory, paths `cpu/...`) produce the variant. The registry sha256 and the design bytes stay those of
`a-z80`; the measures row `synth_origin` is `mimir-patched`. Every changed line ends in
`// MODIFIED (mimir a-z80-modified): <why>` and every patched file starts with a header comment saying what the
variant is and that the upstream is unchanged.

    cp -r <upstream a-z80>/cpu cpu && for p in $(find a-z80-modified -name '*.patch'); do patch -p1 < $p; done

Rules of the variant: no `inout`, no `z`, no tri-state assign anywhere in the RTL of the flow (checked by
`opencores-tb/a-z80/check_no_tristate.py`: 0 hits in 47 files, 244 in the upstream). Each former bidirectional net is
split into one-way signals. A reader gets its own input, driven by an AND-OR mux of the possible sources selected by
the existing enables. `data_switch` / `data_switch_mask` are two one-way gated paths (up-to-down and down-to-up). The
chip data bus `D` becomes the ports `D_in`, `D_out`, `D_oe`; the output enable of `A`, `nMREQ`, `nIORQ`, `nRD`, `nWR`
(the `pin_control_oe` that made them high-Z) is exported as `pins_oe`. The compare bench wraps the ports back into
tri-state pins, so the pin-level comparison against upstream still covers `D`, `A` and the control pins.
When no enable of a net is active the mux gives 0. The upstream RTL has no latch or register that holds a floating
bus (it is `z`), so nothing is held; pin traces are bit-identical to upstream including `x` states, so no consumer
depends on the floating value in the programs run.

### Driver table (step 1)

Segments of the internal data bus: `db0` (data pins, IR, bit-select), `db1` (ALU flags / constants / register low
side), `db2` (ALU, register high side), `gdfx_temp0/1` = `T0/T1` (register-file bus, low/high byte), `db_lo_as/db_hi_as`
= `A0/A1` (address side of the register file, with the address latch). Switch paths join them:
sw1 (`db0`-`db1`, `bus_sw_1u` db1 to db0, `bus_sw_1d` db0 to db1 with bits 7,6,2,1,0 masked by `bus_sw_mask543_en`),
sw2 (`db1`-`db2`, `bus_sw_2u` db2 to db1, `bus_sw_2d` db1 to db2), reg_file `ctl_reg_in_lo/hi` (db1/db2 to T0/T1),
`ctl_reg_out_lo/hi` (T0/T1 to db1/db2), `ctl_sw_4u` (A to T), `reg_sw_4d_lo/hi` (T to A).

| net | drivers (instance: enable) | readers |
| --- | --- | --- |
| `db0` | `data_pins_`: `ctl_bus_db_oe` (reg `dout`); `bus_control_`: `ctl_bus_ff_oe` or `ctl_bus_zero_oe` (FF / 00); sw1 up: `bus_sw_1u` | `ir_`, `interrupts_` (bits 4:3), `alu_` bit-select (bits 5:3), `data_pins_` (`ctl_bus_db_we`), sw1 down |
| `db1` | `alu_control_`: `ctl_66_oe` or `ctl_daa_oe`; `alu_flags_`: `ctl_flags_oe`; `reg_file_` low: `ctl_reg_out_lo`; sw1 down: `bus_sw_1d`; sw2 up: `bus_sw_2u` | `alu_flags_` (`ctl_flags_bus`), `reg_file_` low (`ctl_reg_in_lo`), sw1 up, sw2 down |
| `db2` | `alu_`: `alu_oe`; `reg_file_` high: `ctl_reg_out_hi`; sw2 down: `bus_sw_2d` | `alu_` shifter, `reg_file_` high (`ctl_reg_in_hi`), sw2 up |
| `T0`, `T1` (12 latches each) | `reg_latch` af2, af, bc2, bc, de2, de, hl2, hl, ix, iy, sp, wz: `oe` per latch; `ctl_sw_4u` (from A); `ctl_reg_in_lo/hi` (from db1/db2) | the same latches (`we`), A via `reg_sw_4d_lo/hi`, db1/db2 via `ctl_reg_out_lo/hi` |
| `A0`, `A1` (`db_lo_as`, `db_hi_as`) | `reg_latch` ir, pc: `oe`; `address_latch_`: `ctl_bus_inc_oe` (16 bits); T via `reg_sw_4d_lo/hi` | ir, pc latches (`we`), `address_latch_` (`abus`), T via `ctl_sw_4u` |
| ALU internal `db_low`, `db_high` | `alu_bs_oe`, `alu_op2_oe`, `alu_res_oe`, `alu_op1_oe`, `alu_shift_oe` | operand latch muxes, zero/sign/x/y taps, `alu_oe` to db2 |
| pin `D[7:0]` | `data_pins_`: `bus_db_pin_oe` | `data_pins_` (`bus_db_pin_re`) |
| pins `A[15:0]`, `nMREQ`, `nIORQ`, `nRD`, `nWR` | `address_pins_` / `control_pins_`: `pin_control_oe` | outside |

The segment graph is a tree (db0-db1-db2, db1-T0-A0, db2-T1-A1), so `core.vh` and `reg_file.v` compute one message per
direction of every path and each reader gets the value of its segment from all sources except its own driver. This
leaves no combinational loop through a disabled path. Two readers feed back into a driver of the same net in the
upstream RTL and were given the net value without the ALU driver, for the same reason: the shifter input `db_in` of
`alu` (bus db2 without `alu_oe`) and the bit-select input (db0 without the ALU path). A loop through the ALU driver
is never enabled in the programs run (see the one-driver check).

### Patch files (lines of unified diff)

alu/alu.v 206, alu/alu_control.v 34, alu/alu_flags.v 109, bus/address_latch.v 70, bus/address_pins.v 50,
bus/bus_control.v 43, bus/control_pins_n.v 29, bus/data_pins.v 84, bus/data_switch.v 65, bus/data_switch_mask.v 87,
registers/reg_file.v 457, registers/reg_latch.v 60, toplevel/core.vh 52, toplevel/coremodules.vh 86,
toplevel/z80_top_direct_n.v 44 (1476 in all). Not patched, not part of the flow: `toplevel/z80_top_ifc_n.sv`,
`bus/data_pins_lattice.v`, the project's own SystemVerilog benches (they use the `db` port names).
