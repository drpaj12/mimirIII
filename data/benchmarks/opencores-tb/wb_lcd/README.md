# wb_lcd testbench

tb_origin: `mimir-written` (file `tb_wb_lcd.v`, Mimir repo licence). The RTL
(`verilog/wb_lcd/rtl/` of the OpenCores project, LGPL-3) is not copied here.

Checks (307 checks; prints `PASS tb_wb_lcd checks=307 errors=0` or `FAIL ...`, ends with `$finish`):
- Wishbone: 19 character writes (RAM 0x00..0x0F, 0x40..0x42) each get `wb_ack_o`; `wb_err_o` stays 0;
  status register (address 0x80) reads 1 while the display initialises and 0 after the paint;
- first paint: init nibbles 3 3 3 2, then bytes 28 06 0C 01 80, 16 characters (RS=1), C0 and the three
  second-line characters, as high nibble then low nibble, RS=0 for commands and 1 for characters;
- a NOP command (data 0 at 0x80) starts no repaint; then two characters are changed, a repaint command
  (data 1 at 0x80) gives the same 38 bytes again with the new characters;
- `LCD_RW` stays 0; E high >= 230 ns, gap >= 1 us inside a byte, >= 40 us between bytes. These three
  numbers are the ones in the core's own code comments (`lcd_display.v`, tx_state_high_hold /
  tx_state_oneus / tx_state_fortyus) at the 50 MHz clock the core assumes (`_1MS_DELAY_CYCLES 50`).

Reference: the HD44780 4-bit write sequence (init 3 3 3 2, function set 28, entry mode 06, display on
0C, clear 01, set DDRAM address 80 / C0) and the core's own comments. The project has no doc folder,
and the HD44780 datasheet was not read for this testbench: the sequence above is taken from the core's
code and common knowledge of the part, so it is the weaker kind of reference.

Observed, not asserted:
- `LCD_RS` is 1 on the four init nibbles (the RTL leaves RS at its default 1 outside command states); not checked.
- the RAM has 67 words but the second line addresses run 0x40..0x4F, so 0x43..0x4F are outside it (the
  paint reads x there in iverilog; Odin III reports "reads of addresses past SIZE 67 give x"). Only
  0x40..0x42 are checked; the other 13 second-line characters are checked for RS only.
- the testbench ignores the x-to-0 edge of `LCD_E` at time 0 (no rising edge before it).

Run (iverilog), with the four `.v` files copied from `external/opencores/wb_lcd/verilog/wb_lcd/rtl/`:

    iverilog -g2005 -I . -o sim.vvp wb_lcd.v lcd_display.v delay_counter.v lcd_defines.v tb_wb_lcd.v && vvp sim.vvp

Odin III (needs `--max-time`, the run is 25.9 ms of simulated time and the default is 10 ms; about 86 s):
`odin3 -p "read_verilog wb_lcd.v lcd_display.v delay_counter.v; proc; opt; lower; sim_tb --top tb_wb_lcd --max-time 30000000 --out run.txt tb_wb_lcd.v"`.
The output text equals the iverilog output. A mutation (low nibble sent as the high nibble) gives FAIL with 67 errors.
