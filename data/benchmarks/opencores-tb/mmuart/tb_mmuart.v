// tb_origin: mimir-written
// Self-checking testbench for the Milkymist UART (OpenCores mmuart: uart.v + uart_transceiver.v).
// Reference: the project's doc/uart.tex (8N1, divisor = clk_freq / (16 * baud), RX/TX interrupts)
// and an independent bit-level receiver and transmitter written here. Plain Verilog-2005 without
// tasks, so the Odin III sim_tb subset can read it. Prints "PASS ..." or "FAIL ..." and ends with $finish.
`timescale 1ns/1ps
module tb_mmuart;
  reg clk;
  reg rst;
  reg [13:0] csr_a;
  reg csr_we;
  reg [31:0] csr_di;
  wire [31:0] csr_do;
  wire rx_irq;
  wire tx_irq;
  wire uart_tx;
  reg rx_drv;
  reg lb;
  wire uart_rx;
  assign uart_rx = lb ? uart_tx : rx_drv;

  uart dut (.sys_clk(clk), .sys_rst(rst), .csr_a(csr_a), .csr_we(csr_we), .csr_di(csr_di),
            .csr_do(csr_do), .rx_irq(rx_irq), .tx_irq(tx_irq), .uart_rx(uart_rx),
            .uart_tx(uart_tx));

  integer errors;
  integer checks;
  integer p;
  integer i;
  integer j;
  integer nb;
  integer dv;
  integer guard;
  integer tx_cnt;
  integer rx_cnt;
  integer rx_base;
  integer tx_base;
  integer mon_n;
  integer mon_stop_bad;
  reg mon_en;
  reg [7:0] mon_mem [0:15];
  reg [7:0] bytes [0:4];
  reg [7:0] mbyte;
  reg [7:0] cur;
  reg [31:0] rd;

  initial clk = 0;
  always #5 clk = ~clk;

  always @(posedge clk) begin
    if (tx_irq) tx_cnt = tx_cnt + 1;
    if (rx_irq) rx_cnt = rx_cnt + 1;
  end

  // independent 8N1 receiver on uart_tx: bit time = 16*dv clocks, sampled at mid bit
  always @(negedge uart_tx) begin
    if (mon_en) begin
      repeat (8 * dv) @(posedge clk);
      if (uart_tx != 1'b0) mon_stop_bad = mon_stop_bad + 1;
      for (j = 0; j < 8; j = j + 1) begin
        repeat (16 * dv) @(posedge clk);
        mbyte = {uart_tx, mbyte[7:1]};
      end
      repeat (16 * dv) @(posedge clk);
      if (uart_tx != 1'b1) mon_stop_bad = mon_stop_bad + 1;
      mon_mem[mon_n] = mbyte;
      mon_n = mon_n + 1;
    end
  end

  initial begin
    errors = 0; checks = 0; tx_cnt = 0; rx_cnt = 0; mon_n = 0; mon_stop_bad = 0;
    mon_en = 0; dv = 54; lb = 0; rx_drv = 1; csr_a = 0; csr_we = 0; csr_di = 0; rst = 1;
    mbyte = 0;
    bytes[0] = 8'h55; bytes[1] = 8'h00; bytes[2] = 8'hFF; bytes[3] = 8'hA3; bytes[4] = 8'h41;
    repeat (4) @(posedge clk);
    @(negedge clk); rst = 0;
    // the thru flag has no reset in the RTL; the doc does not define it, so the testbench clears it
    @(negedge clk); csr_a = 2; csr_di = 0; csr_we = 1;
    @(negedge clk); csr_we = 0;

    // default divisor: clk_freq/baud/16 with the defaults 100000000 / 115200 / 16 = 54 (integer)
    @(negedge clk); csr_a = 1;
    @(negedge clk); @(negedge clk);
    rd = csr_do;
    checks = checks + 1;
    if (rd == 32'd54) begin end else begin errors = errors + 1; $display("FAIL default divisor %0d", rd); end

    for (p = 0; p < 2; p = p + 1) begin
      if (p == 1) begin
        dv = 5;
        @(negedge clk); csr_a = 1; csr_di = 5; csr_we = 1;
        @(negedge clk); csr_we = 0;
        repeat (200) @(posedge clk);
        @(negedge clk); csr_a = 1;
        @(negedge clk); @(negedge clk);
        checks = checks + 1;
        if (csr_do == 32'd5) begin end else begin errors = errors + 1; $display("FAIL divisor readback"); end
      end
      nb = (p == 0) ? 3 : 5;
      mon_n = 0; mon_en = 1; tx_base = tx_cnt;

      // TX: write bytes through the CSR, one at a time after the TX interrupt
      for (i = 0; i < nb; i = i + 1) begin
        @(negedge clk); csr_a = 0; csr_di = bytes[i]; csr_we = 1;
        @(negedge clk); csr_we = 0;
        guard = 0;
        while (tx_cnt < tx_base + i + 1 && guard < 40 * 16 * dv) begin
          @(posedge clk); guard = guard + 1;
        end
        checks = checks + 1;
        if (tx_cnt == tx_base + i + 1) begin end else begin errors = errors + 1; $display("FAIL no tx_irq byte %0d", i); end
      end
      repeat (40 * dv) @(posedge clk);
      mon_en = 0;
      checks = checks + 1;
      if (mon_n == nb) begin end else begin errors = errors + 1; $display("FAIL tx frames %0d of %0d", mon_n, nb); end
      for (i = 0; i < nb; i = i + 1) begin
        checks = checks + 1;
        if (mon_mem[i] == bytes[i]) begin end else begin errors = errors + 1; $display("FAIL tx byte %0d got %h want %h", i, mon_mem[i], bytes[i]); end
      end
      checks = checks + 1;
      if (mon_stop_bad == 0) begin end else begin errors = errors + 1; $display("FAIL tx start/stop bit"); end

      // RX: the testbench drives 8N1 frames; the core must raise rx_irq and hold the byte
      for (i = 0; i < nb; i = i + 1) begin
        rx_base = rx_cnt;
        cur = bytes[nb - 1 - i];
        rx_drv = 0;
        repeat (16 * dv) @(posedge clk);
        for (j = 0; j < 8; j = j + 1) begin
          rx_drv = cur[j];
          repeat (16 * dv) @(posedge clk);
        end
        rx_drv = 1;
        repeat (16 * dv) @(posedge clk);
        checks = checks + 1;
        if (rx_cnt == rx_base + 1) begin end else begin errors = errors + 1; $display("FAIL rx_irq count byte %0d", i); end
        @(negedge clk); csr_a = 0;
        @(negedge clk); @(negedge clk);
        checks = checks + 1;
        if (csr_do == {24'd0, cur}) begin end else begin errors = errors + 1; $display("FAIL rx byte %0d got %h want %h", i, csr_do, cur); end
      end

      // loopback: uart_tx fed to uart_rx
      lb = 1;
      for (i = 0; i < nb; i = i + 1) begin
        rx_base = rx_cnt;
        @(negedge clk); csr_a = 0; csr_di = bytes[i]; csr_we = 1;
        @(negedge clk); csr_we = 0;
        guard = 0;
        while (rx_cnt < rx_base + 1 && guard < 40 * 16 * dv) begin
          @(posedge clk); guard = guard + 1;
        end
        checks = checks + 1;
        if (rx_cnt == rx_base + 1) begin end else begin errors = errors + 1; $display("FAIL loopback no rx_irq %0d", i); end
        @(negedge clk); csr_a = 0;
        @(negedge clk); @(negedge clk);
        checks = checks + 1;
        if (csr_do == {24'd0, bytes[i]}) begin end else begin errors = errors + 1; $display("FAIL loopback byte %0d got %h want %h", i, csr_do, bytes[i]); end
        repeat (16 * dv) @(posedge clk);
      end
      lb = 0;
    end

    // thru mode: uart_tx follows uart_rx
    @(negedge clk); csr_a = 2; csr_di = 1; csr_we = 1;
    @(negedge clk); csr_we = 0;
    @(negedge clk); @(negedge clk);
    checks = checks + 1;
    if (csr_do == 32'd1) begin end else begin errors = errors + 1; $display("FAIL thru readback"); end
    for (i = 0; i < 6; i = i + 1) begin
      rx_drv = i[0];
      #1;
      checks = checks + 1;
      if (uart_tx == rx_drv) begin end else begin errors = errors + 1; $display("FAIL thru follow %0d", i); end
      @(negedge clk);
    end

    if (errors == 0) $display("PASS tb_mmuart checks=%0d errors=0", checks);
    else $display("FAIL tb_mmuart checks=%0d errors=%0d", checks, errors);
    $finish;
  end

  initial begin
    #200000000;
    $display("FAIL tb_mmuart timeout");
    $finish;
  end
endmodule
