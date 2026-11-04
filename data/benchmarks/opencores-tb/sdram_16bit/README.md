# sdram_16bit testbench

tb_origin: `upstream-fixed`. The project's own testbench is SystemVerilog for Modelsim
(`testbench/top_tb.sv`, `wb_master.sv`, `simulation.svh`; iverilog 12 refuses it: unpacked structs,
queues, associative array, strings, `timescale` inside a module). It is ported to Verilog-2005 here,
keeping its checks. Files:

- `wb_master.v`, `top_tb.v`: the port. `*.sv.to.v.patch` are the diffs from the upstream `.sv` files.
  Upstream licence (GPL, Ultra-Embedded sdram_16bit) applies to these ported files.
- Unchanged and not copied here: `testbench/IS42VM16400K.v` (SDRAM model, compiles with `-g2005`) and
  `rtl/sdram.v`. The Makefile's `MT48LC8M16A2.v` is not needed (the `PART` define selects `IS42VM16400K`).

Checks kept from upstream: a random Wishbone master (single and 8-beat burst requests, random byte
selects on single writes, random delays) keeps a reference memory; every read response is compared per
byte lane with the reference (`!==`); a response with no outstanding request is an error; no accepted
request for 100000 cycles is an error. Changes beyond syntax:
1. Race fix. The upstream master drives its outputs with blocking assignments at the clock edge, which
   races with the DUT's `always @(posedge clk_i)`; under iverilog the unfixed port fails (a read
   returned the neighbouring word of an earlier burst). The port samples the handshake at the edge and
   drives 1 time unit later. This is our fix to a testbench race, not a core change.
2. `$urandom` / `$urandom_range` become `$random(seed)` with a fixed seed (1): the stimulus differs from
   a Modelsim run but is deterministic.
3. Added a final line: `PASS top_tb responses=N reads_checked=N reads_of_written_words=N writes=N`
   after 10 ms of simulated time when there were no errors, at least 1000 responses and at least 100
   reads of previously written words (reads of never-written words compare x with x), else `FAIL ...`.
   The waveform dump (`TRACE`) is dropped.

Result: PASS with 164574 responses, 82159 reads checked, 80253 of them of written words, 82415 writes
(12.8 s). A mutation of the DUT (read data bit 0 forced to 0) gives FAIL at the first read.

Run (iverilog), `p/` holding `wb_master.v top_tb.v IS42VM16400K.v sdram.v`:

    iverilog -g2005 -DMAX_ADDRESS=8192 -DPART=IS42VM16400K -s top_tb -o sim.vvp p/*.v && vvp sim.vvp

Odin III: not run to the end. `read_verilog sdram.v` stops with
`sdram.v:689:5: error: unresolved_module: module 'ODDR2' is not defined` (also `IOBUF`): the DUT instance
in the testbench sets `SDRAM_TARGET("SIMULATION")`, a parameter override on the DUT instance, which the
sim_tb subset does not accept, and the default target needs Xilinx primitives. With `--auto-blackbox` the
read passes and `sim_tb` of the testbench is refused: `top_tb.v:58: unsupported: compiler directive` (the `MAX_ADDRESS` macro; the testbench also has an inout bus, tasks and a model with delays).
