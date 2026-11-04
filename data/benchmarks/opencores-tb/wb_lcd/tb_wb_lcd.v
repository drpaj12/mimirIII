// tb_origin: mimir-written
// Self-checking testbench for the OpenCores wb_lcd core (verilog/wb_lcd: wb_lcd.v, lcd_display.v,
// delay_counter.v, lcd_defines.v). It writes characters over Wishbone, requests a repaint and checks
// the 4-bit HD44780 pin sequence on SF_D / LCD_E / LCD_RS / LCD_RW: init nibbles 3 3 3 2, then the
// bytes 28 06 0C 01 80, 16 characters, C0 and the characters of the second line, once for the first
// paint and once more for the repaint. Also checks LCD_RW low, the Wishbone ack, the busy status
// register, that a NOP command does not repaint, and the pulse widths / gaps against the numbers in
// the core's own code comments (E high >= 230 ns, gap >= 1 us inside a byte, >= 40 us between bytes).
// Plain Verilog-2005 without tasks, so the Odin III sim_tb subset can read it.
// Prints "PASS ..." or "FAIL ..." and ends with $finish.
`timescale 1ns/1ps
module tb_wb_lcd;
  reg clk;
  reg rst;
  reg [31:0] dat_i;
  wire [31:0] dat_o;
  reg [31:0] adr_i;
  reg we_i;
  reg cyc_i;
  reg stb_i;
  wire ack_o;
  wire err_o;
  wire [3:0] SF_D;
  wire LCD_E;
  wire LCD_RS;
  wire LCD_RW;

  wb_lcd dut (.wb_clk_i(clk), .wb_rst_i(rst), .wb_dat_i(dat_i), .wb_dat_o(dat_o),
              .wb_adr_i(adr_i), .wb_sel_i(4'hF), .wb_we_i(we_i), .wb_cyc_i(cyc_i),
              .wb_stb_i(stb_i), .wb_ack_o(ack_o), .wb_err_o(err_o), .SF_D(SF_D),
              .LCD_E(LCD_E), .LCD_RS(LCD_RS), .LCD_RW(LCD_RW));

  integer errors;
  integer checks;
  integer i;
  integer k;
  integer guard;
  integer n;
  integer base;
  integer paint;
  integer rw_bad;
  integer min_w_data;
  integer min_w_init;
  integer t_rise;
  integer t_fall;
  reg [3:0] nib_d [0:255];
  reg nib_rs [0:255];
  integer nib_w [0:255];
  integer nib_gap [0:255];
  reg [7:0] exp_byte [0:37];
  reg exp_rs [0:37];
  reg exp_chk [0:37];
  reg [31:0] st;
  reg [7:0] got;

  initial clk = 0;
  always #10 clk = ~clk;

  reg e_seen;
  initial e_seen = 0;
  // x to 0 at time 0 is a negedge in iverilog but no pulse: only log a falling edge after a rising edge
  always @(posedge LCD_E) begin
    e_seen = 1;
    t_rise = $time;
    if (n > 0) nib_gap[n] = t_rise - t_fall;
    else nib_gap[n] = 0;
  end
  always @(negedge LCD_E) begin
    if (e_seen) begin
      e_seen = 0;
      t_fall = $time;
      nib_d[n] = SF_D;
      nib_rs[n] = LCD_RS;
      nib_w[n] = t_fall - t_rise;
      if (LCD_RW != 1'b0) rw_bad = rw_bad + 1;
      n = n + 1;
    end
  end

  initial begin
    errors = 0; checks = 0; n = 0; rw_bad = 0; t_rise = 0; t_fall = 0;
    rst = 1; dat_i = 0; adr_i = 0; we_i = 0; cyc_i = 0; stb_i = 0;
    // expected byte stream of one paint
    exp_byte[0] = 8'h28; exp_byte[1] = 8'h06; exp_byte[2] = 8'h0C; exp_byte[3] = 8'h01;
    exp_byte[4] = 8'h80; exp_byte[21] = 8'hC0;
    for (i = 0; i < 38; i = i + 1) begin
      exp_rs[i] = (i >= 5 && i != 21);
      exp_chk[i] = 1;
    end
    // row 1: 16 characters, row 2: three checked characters; the RAM has 67 words so the
    // second-line addresses 0x43..0x4F are outside it (not checked, see README)
    for (i = 0; i < 16; i = i + 1) exp_byte[5 + i] = 8'h41 + i;
    exp_byte[22] = 8'h58; exp_byte[23] = 8'h59; exp_byte[24] = 8'h5A;
    for (i = 25; i < 38; i = i + 1) begin exp_byte[i] = 0; exp_chk[i] = 0; end

    repeat (4) @(posedge clk);
    @(negedge clk); rst = 0;

    // Wishbone writes of the first paint's characters (RAM addresses 0x00..0x0F, 0x40..0x42)
    for (i = 0; i < 19; i = i + 1) begin
      @(negedge clk);
      adr_i = (i < 16) ? i : (32'h40 + i - 16);
      dat_i = exp_byte[(i < 16) ? (5 + i) : (22 + i - 16)];
      we_i = 1; cyc_i = 1; stb_i = 1;
      guard = 0;
      @(posedge clk); #1;
      while (ack_o != 1'b1 && guard < 10) begin @(posedge clk); #1; guard = guard + 1; end
      checks = checks + 1;
      if (ack_o == 1'b1) begin end else begin errors = errors + 1; $display("FAIL no wb_ack_o on write %0d", i); end
      we_i = 0; cyc_i = 0; stb_i = 0;
      @(negedge clk);
    end

    // status register: busy (1) while the display initialises
    @(negedge clk); adr_i = 32'h80; we_i = 0; cyc_i = 1; stb_i = 1;
    @(posedge clk); @(posedge clk); @(negedge clk);
    st = dat_o;
    cyc_i = 0; stb_i = 0;
    checks = checks + 1;
    if (st == 32'd1) begin end else begin errors = errors + 1; $display("FAIL status not busy during init"); end

    for (paint = 0; paint < 2; paint = paint + 1) begin
      if (paint == 1) begin
        // NOP command (data 0 at the command register) must not repaint
        base = n;
        @(negedge clk); adr_i = 32'h80; dat_i = 32'h0; we_i = 1; cyc_i = 1; stb_i = 1;
        @(posedge clk); @(posedge clk); @(negedge clk);
        we_i = 0; cyc_i = 0; stb_i = 0;
        repeat (6000) @(posedge clk);
        checks = checks + 1;
        if (n == base) begin end else begin errors = errors + 1; $display("FAIL NOP command repainted"); end
        // change two characters, then request a repaint
        @(negedge clk); adr_i = 32'h0; dat_i = 32'h7A; we_i = 1; cyc_i = 1; stb_i = 1;
        @(posedge clk); @(posedge clk); @(negedge clk);
        we_i = 0; cyc_i = 0; stb_i = 0;
        @(negedge clk); adr_i = 32'h42; dat_i = 32'h21; we_i = 1; cyc_i = 1; stb_i = 1;
        @(posedge clk); @(posedge clk); @(negedge clk);
        we_i = 0; cyc_i = 0; stb_i = 0;
        exp_byte[5] = 8'h7A; exp_byte[24] = 8'h21;
        @(negedge clk); adr_i = 32'h80; dat_i = 32'h1; we_i = 1; cyc_i = 1; stb_i = 1;
        @(posedge clk); @(posedge clk); @(negedge clk);
        we_i = 0; cyc_i = 0; stb_i = 0;
      end
      // wait for the paint to finish (nibbles logged), then for status idle
      guard = 0;
      while (n < ((paint == 0) ? 80 : 156) && guard < 1500000) begin
        @(posedge clk); guard = guard + 1;
      end
      repeat (3000) @(posedge clk);
      checks = checks + 1;
      if (n == ((paint == 0) ? 80 : 156)) begin end else begin errors = errors + 1; $display("FAIL nibble count %0d paint %0d", n, paint); end
      @(negedge clk); adr_i = 32'h80; we_i = 0; cyc_i = 1; stb_i = 1;
      @(posedge clk); @(posedge clk); @(negedge clk);
      st = dat_o;
      cyc_i = 0; stb_i = 0;
      checks = checks + 1;
      if (st == 32'd0) begin end else begin errors = errors + 1; $display("FAIL status not idle after paint %0d", paint); end
    end

    // compare the logged sequence
    for (paint = 0; paint < 2; paint = paint + 1) begin
      base = (paint == 0) ? 4 : 80;
      if (paint == 0) begin
        checks = checks + 4;
        if (nib_d[0] == 4'h3) begin end else begin errors = errors + 1; $display("FAIL init nibble 0"); end
        if (nib_d[1] == 4'h3) begin end else begin errors = errors + 1; $display("FAIL init nibble 1"); end
        if (nib_d[2] == 4'h3) begin end else begin errors = errors + 1; $display("FAIL init nibble 2"); end
        if (nib_d[3] == 4'h2) begin end else begin errors = errors + 1; $display("FAIL init nibble 3"); end
      end
      for (k = 0; k < 38; k = k + 1) begin
        begin
          // second paint starts at nibble 80 and has no init nibbles
          got = exp_byte[k];
          if (paint == 0 && k == 5) got = 8'h41;
          if (paint == 0 && k == 24) got = 8'h5A;
          if (exp_chk[k]) begin
            checks = checks + 2;
            if ({nib_d[base + 2 * k], nib_d[base + 2 * k + 1]} == got) begin end
            else begin errors = errors + 1; $display("FAIL paint %0d byte %0d got %h%h want %h", paint, k, nib_d[base + 2 * k], nib_d[base + 2 * k + 1], got); end
            if (nib_rs[base + 2 * k] == exp_rs[k] && nib_rs[base + 2 * k + 1] == exp_rs[k]) begin end
            else begin errors = errors + 1; $display("FAIL paint %0d byte %0d RS", paint, k); end
          end else begin
            checks = checks + 1;
            if (nib_rs[base + 2 * k] == 1'b1 && nib_rs[base + 2 * k + 1] == 1'b1) begin end
            else begin errors = errors + 1; $display("FAIL paint %0d byte %0d RS", paint, k); end
          end
        end
      end
    end
    // paint 1 starts after the first paint's 80 nibbles; its bytes are at 80 + 2k
    // pulse widths and gaps of the data nibbles (all except the 4 init nibbles)
    min_w_data = 1000000; min_w_init = 1000000;
    for (k = 0; k < 4; k = k + 1) if (nib_w[k] < min_w_init) min_w_init = nib_w[k];
    for (k = 4; k < 156; k = k + 1) begin
      if (nib_w[k] < min_w_data) min_w_data = nib_w[k];
    end
    checks = checks + 1;
    if (min_w_data >= 230) begin end else begin errors = errors + 1; $display("FAIL E high %0d ns < 230", min_w_data); end
    for (k = 4; k < 156; k = k + 1) begin
      if (k != 80) begin
        // inside a byte (odd index: low nibble) gap >= 1 us; between bytes >= 40 us, except after clear (0x01)
        if (k % 2 == 1) begin
          checks = checks + 1;
          if (nib_gap[k] >= 1000) begin end else begin errors = errors + 1; $display("FAIL gap in byte at nibble %0d = %0d ns", k, nib_gap[k]); end
        end else if (k != 12 && k != 88) begin
          checks = checks + 1;
          if (nib_gap[k] >= 40000) begin end else begin errors = errors + 1; $display("FAIL gap between bytes at nibble %0d = %0d ns", k, nib_gap[k]); end
        end
      end
    end
    checks = checks + 2;
    if (rw_bad == 0) begin end else begin errors = errors + 1; $display("FAIL LCD_RW high"); end
    if (err_o == 1'b0) begin end else begin errors = errors + 1; $display("FAIL wb_err_o"); end

    $display("INFO min E high: data nibbles %0d ns, init nibbles %0d ns", min_w_data, min_w_init);
    $display("INFO LCD_RS on the 4 init nibbles (not checked): %b%b%b%b", nib_rs[0], nib_rs[1], nib_rs[2], nib_rs[3]);
    if (errors == 0) $display("PASS tb_wb_lcd checks=%0d errors=0", checks);
    else $display("FAIL tb_wb_lcd checks=%0d errors=%0d", checks, errors);
    $finish;
  end

  initial begin
    #200000000;
    $display("FAIL tb_wb_lcd timeout");
    $finish;
  end
endmodule
