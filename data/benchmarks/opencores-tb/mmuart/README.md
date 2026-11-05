# mmuart testbench

tb_origin: `mimir-written` (file `tb_mmuart.v`, Mimir repo licence). The RTL (`uart.v`,
`uart_transceiver.v`) is the Milkymist UART under GPL-3 and is not copied here.

Checks (61 checks, prints `PASS tb_mmuart checks=61 errors=0` or `FAIL ...`, ends with `$finish`):
- default divisor reads 54 (= 100000000 / 115200 / 16, integer) and a written divisor (5) reads back;
- TX: bytes 55 00 FF A3 41 (3 of them at divisor 54) written through the CSR are decoded by an
  independent 8N1 receiver in the testbench (start and stop bit levels checked), one `tx_irq` per byte;
- RX: the testbench drives 8N1 frames; one `rx_irq` per frame and the CSR data register holds the byte;
- loopback: `uart_tx` fed to `uart_rx`, same bytes returned;
- thru mode: `thru` reads back 1 and `uart_tx` follows `uart_rx`.

Reference: `doc/uart.tex` of the project (8 data bits, no parity, 1 stop bit,
divisor = clk_freq / (16 * baud)). The `thru` flag has no reset in the RTL (x in iverilog), so the
testbench clears it first.

Run (iverilog), with the two RTL files copied from `external/opencores/mmuart/rtl/`:

    iverilog -g2005 -o sim.vvp uart.v uart_transceiver.v tb_mmuart.v && vvp sim.vvp

Odin III: `odin3 -p "read_verilog uart.v uart_transceiver.v; proc; opt; lower; sim_tb --top tb_mmuart --out run.txt tb_mmuart.v"`.
The testbench uses no tasks, x/z literals or directives other than `timescale`.
A mutation (inverted TX data bit) makes it print FAIL with 16 errors, so the checks bite.
