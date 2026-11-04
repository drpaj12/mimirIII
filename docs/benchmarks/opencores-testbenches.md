# OpenCores testbenches written or fixed by us

Purpose: a diverse OpenCores set in which every core passes a testbench through the whole flow (tier T0 of
the benchmark catalogue). A testbench we write is weaker evidence than the author's own, so each design
carries a `tb_origin` label (Peter 2026-11-04):

- `upstream`: the project's own testbench, unchanged.
- `upstream-fixed`: the project's own testbench with our minimal fix, kept as a `.patch` (or, for sdram_16bit,
  a Verilog-2005 port with the diffs); the reason is in the patch header or the README.
- `mimir-written`: a testbench we wrote; the README says what it checks and against what reference.

Files are in `data/benchmarks/opencores-tb/<project>/` (testbench, patches, vector generators with fixed
seeds, `README.md` with the run commands). Upstream sources are never edited; run copies were made under a
work directory. Results below were produced with iverilog 12.0 (`-g2005`, 600 s timeout, stdin closed) and
`odin3 sim_tb` (`build/rel-main2`). Not covered here (waiting for the candidate research): a-z80, amber,
attiny_atmega_xmega_core, usbhostslave.

| project | tb_origin | what is checked | reference | iverilog | Odin III sim_tb |
|---|---|---|---|---|---|
| mmuart | mimir-written | divisor register, TX frames via an independent 8N1 receiver, RX frames, loopback, thru mode (61 checks) | `doc/uart.tex` (8N1, divisor = clk/(16 baud)) | PASS, 61 checks, 0 errors | PASS, same output |
| wb_lcd | mimir-written | Wishbone ack/status, HD44780 4-bit nibble sequence of the first paint and a repaint, RS, RW, E width and gaps (307 checks) | HD44780 4-bit init and write sequence and the core's own timing comments; datasheet not read | PASS, 307 checks, 0 errors | PASS, same output (86 s, needs `--max-time 30000000`) |
| simple_spi | upstream-fixed | project bench: 16 cpol/cpha/divider combinations, register write/read-back, 8-byte SPI loop-back compares | the bench's own expected data; no PASS line (pass = no `Data compare error`) | PASS, 0 compare errors | refused: `tst_bench_top.v:50: unsupported: compiler directive` |
| vga_lcd | upstream-fixed (scenario subset) | project bench: register test, timing test (modes 0-1), pixel data test (all colour modes, delay 0), FIFO underrun; sync monitor, pixel compare, WB B3 check | the bench's own model of video memory and timing | PASS, 4 x `Total ERRORS: 0`, 466 s | refused: `test_bench_top.v:116: unsupported: compiler directive` |
| sdram_16bit | upstream-fixed (Verilog-2005 port) | random single/burst Wishbone traffic against a reference memory, read data compare per byte lane, no-stall timeout; 164574 responses, 80253 reads of written words | reference memory in the bench; SDRAM model `IS42VM16400K.v` | PASS, 10 ms simulated, 12.8 s | refused: `sdram.v:689:5: unresolved_module: module 'ODDR2' is not defined` (DUT, default target); the bench is refused at `top_tb.v:58: unsupported: compiler directive` |
| gng | mimir-written | 8192 samples against the project's C model (and with gaps in ce), 11-cycle latency, `gng_interp` with 1488 directed words (11733 checks) | project C model `c/taus176.c`, `c/icdf.c` (Python port, compared with gcc) | PASS, 0 errors (4 warm-up words differ, RTL finding) | PASS, same output (26 s) |
| dblclockfft | mimir-written | 6 frames x 2048 outputs within 8 LSB of numpy FFT x 2^-5; `o_sync` per frame (12295 checks) | numpy FFT, scale 2^-5 from the widths in `fftmain.v` | PASS, max error 4 LSB, 10 s | ODIN_FFT_PLACEHOLDER |

## Findings from writing the testbenches

- mmuart: the `thru` register has no reset (x in iverilog until written).
- wb_lcd: `LCD_RS` is 1 on the four init nibbles; the RAM has 67 words but the second line addresses run to
  0x4F, so 13 second-line characters read x (outside the RAM).
- gng: in `gng_interp.v` the x mask is applied one clock late; it matters only for leading-zero counts of
  46 or more (probability about 2^-46 per sample). The coefficient ROM and the MAC are vendor-generated
  and missing from the project; behavioural models are provided (`gng/README.md`).
- dblclockfft: `always @(*) idle = 0;` never runs in iverilog (idle stays x); dense inputs above about
  11585 per component overflow the first stage.
- vga_lcd and simple_spi: the bench does not compile as shipped (scalar port with vectored net; port-list
  punctuation; missing `timescale.v`).
- sdram_16bit: the bench drives its Wishbone master at the clock edge with blocking assignments, which races
  with the DUT; fixed in the port.
