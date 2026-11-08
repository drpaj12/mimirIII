# uart2spi testbench

tb_origin: `upstream-fixed`. The project's own bench (`verif/tb/tb_top.v` with `uart_agent.v`, `uart_tasks.v`,
`spi_tasks.v`, `uart_test.v`, `spi_test.v`, and the ST M25P16 flash model in `verif/models`) is used with one
one-line patch, `uart_agent.v.patch` (upstream licence applies, LGPL 2.1 or later): `task read_char_chk`
declared scalar `input expected_data;` and then `reg [7:0] expected_data;`, which iverilog rejects. The patch
gives the input its width. Found by the candidates survey (controller note 2026-11-04), reproduced here.

What the bench checks (its own): flash commands through the UART-to-SPI bridge; each page read compares the
received bytes with the expected data (`read_char_chk`, prints `Matched` or a mismatch). Result: 64
`Matched`, no mismatch or error line, `$finish` at 20756889490000 ps simulated (20.7 s of simulated time).
Wall time 552 s with iverilog 12, i.e. within the 600 s limit but with little margin.

Run (iverilog 2005 mode) in a copy of the project where `rtl/` also sits under `verif/` (the project's
`verif/run/file.f` uses `../rtl/...` relative to `verif/run`), with the patched `uart_agent.v`:

    iverilog -g2005 -o sim.vvp -c file.f && vvp -n sim.vvp          # run in verif/run

Odin III 1.5.0: refused at `tb_top.v:51` (`#(XTAL_CLK_PERIOD/2.0)`, a `real` delay). Behind it the bench needs
fork/join, events, `disable` and a function (the flash model), not implemented in `sim_tb`.
