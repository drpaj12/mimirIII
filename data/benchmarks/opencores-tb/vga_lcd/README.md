# vga_lcd testbench

tb_origin: `upstream-fixed`. The project's own bench (`bench/verilog/`: `test_bench_top.v`, `tests.v`,
`wb_mast_model.v`, `wb_slv_model.v`, `sync_check.v`, `wb_b3_check.v`, `wb_model_defines.v`) is used with
three patches against the upstream files (upstream licence applies; each patch carries the reason in its header):

1. `wb_slv_model.v.patch`: `task set_delay` declares scalar `input dly;` then `reg [5:0] dly;`, which iverilog
   rejects (`Scalar port dly has a vectored net declaration [5:0]`). Fix: `input [5:0] dly;`. The only change
   needed to compile and run.
2. `tests.v.patch` and `test_bench_top.v.patch`: scenario subset, for run time only. The full quick
   regression (`reg_test; tim_test; pd1_test; pd2_test; ur_test`) did not finish within the 600 s limit
   (stopped inside `tim_test`, mode 3 of 6). The subset keeps every test task and check and cuts the loops:
   `tim_test` modes 0 and 1 (of 0..5), `pd1_test` memory delay 0 and VBL 0 (of 6 delays and 4 VBL values;
   all 4 colour modes), `pd2_test` not called. `reg_test` and `ur_test` unchanged.

What the bench checks (its own): register reset values and read/write patterns; the sync monitor
(`sync_check.v`) on h/v sync, blank and csync timing against the programmed values; every displayed pixel
(red, green, blue) against the video memory content for 8-bit grey, 8-bit colour, 16-bit and 24/32-bit
modes with and without the colour lookup table; FIFO underrun behaviour; Wishbone B3 protocol
(`wb_b3_check.v`). Each test prints `Total ERRORS: N`. The bench has no PASS line; the pass criterion used
here: it reaches `$finish` and prints `Total ERRORS: 0` for all four tests (reg, tim, pd1, ur).
Result: 4 x `Total ERRORS: 0`, `$finish` at 5500614480 (unit 10 ps) simulated time, 466 s wall (7 min 46 s).
One `WARNING: Recieved Interrupt` line in `reg_test` is the bench's own message.

Not in the clone and not needed here: the Makefile also lists `csm_spram_bw.v`, `vga_dvi_top.v`, `artsmcl18u_ram/*`
and `bist/*` (ASIC/DVI/BIST options, only used with defines that are off).

Run (iverilog 2005 mode); in a directory holding `rtl/verilog/*.v` and the patched `bench/verilog/*.v`
(`tests.v` is `` `include``d by `test_bench_top.v`, do not compile it on its own):

    iverilog -g2005 -I . -s test -o sim.vvp $(ls *.v | grep -v '^tests.v$') && vvp -n sim.vvp

Odin III: refused. `sim_tb --top test test_bench_top.v` stops with
`test_bench_top.v:116: unsupported: compiler directive` (the bench uses `ifdef`, `define`, `include`, tasks,
hierarchical writes and several modules; none are in the sim_tb subset). The DUT alone reads with
`--top vga_enh_top`.
