# simple_spi testbench

tb_origin: `upstream-fixed`. The project's own bench (`bench/verilog/tst_bench_top.v`,
`wb_master_model.v`, `spi_slave_model.v`) is used unchanged except for one patch:

- `spi_slave_model.v.patch`: port list of `spi_slave_model` had `;` for `,` and a missing comma, so
  iverilog stops with a syntax error. Upstream licence applies to the patched file (Copyright 2004
  Richard Herveille, notice in the file header).
- `timescale.v` (new file, one line `` `timescale 1ns / 10ps ``): every upstream file does
  `` `include "timescale.v" `` but the project ships none. This file is ours (Mimir repo licence).

What the bench checks (its own): for cpol 0..1, cpha 0..1, clock divider e 0..3 it writes and reads
back the control and extended control registers, fills the slave model's 8-byte memory through SPDR,
reads it back through the SPI loop and compares each byte (`wb_cmp`). A mismatch prints
`Data compare error. Received .., expected ..`; the bench has no PASS line, so the pass criterion used
here is: ends with `Testbench done` and zero `Data compare error` lines. A mutation (slave model
inverts MOSI) gives 128 compare errors, so the compares bite.

Run (iverilog 2005 mode; `do` is a keyword in SystemVerilog):

    cp bench/verilog/*.v rtl/verilog/*.v run/ ; patch -p3 -d run < spi_slave_model.v.patch ; cp timescale.v run/
    iverilog -g2005 -I run -o sim.vvp run/*.v && vvp sim.vvp

(the patch is made with `a/bench/verilog/` paths: apply with `-p1` from a tree that has `bench/verilog/`).
iverilog prints two "procedural continuous assignments" warnings for the bench's `force`.
Odin III 1.5.0 passes, text equal to iverilog (about 2 s, release build; `force`, testbench-side modules
`wb_master_model` / `spi_slave_model` and the `include` directives are supported). In a directory with the patched
bench, `timescale.v`, `fifo4.v`, `simple_spi_top.v`:

    odin3 -p "read_verilog fifo4.v simple_spi_top.v; proc; opt; lower --keep-sel --async keep; sim_tb --out run.txt -I . tst_bench_top.v wb_master_model.v spi_slave_model.v"

`lower --async keep` is needed: the bench pulses the asynchronous reset for less than one clock edge.
