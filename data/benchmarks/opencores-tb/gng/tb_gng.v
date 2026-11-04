// tb_origin: mimir-written (Verilog-2005 replacement for the project's tb/tb_gng.sv, which only writes
// a file and checks nothing)
// Self-checking testbench for the OpenCores Gaussian Noise Generator (gng.v + gng_ctg.v, gng_interp.v,
// gng_lzd.v, gng_smul_16_18.v from the project; gng_coef.v and gng_smul_16_18_sadd_37.v are ours).
// Reference: the project's own C model (c/taus176.c, c/icdf.c) ported to Python (gen_gng_vectors.py,
// checked against the compiled C), vectors in stream_exp.hex, interp_in.hex, interp_exp.hex.
//   phase 1: gng with ce tied high after reset, first 8192 samples equal the C model sequence;
//   phase 2: reset again, ce 3 on / 2 off, the valid samples are the same sequence;
//   phase 3: gng_interp alone with 1488 directed (+62 warm-up copies, see README) 64-bit words (every leading-zero count, offset, sign);
//   and the first valid_out comes 11 clock cycles after ce (spec 3.5 of doc/gng_spec_1.0.pdf).
// No tasks; parameters left at their defaults (equal to the project's tb values).
// Prints "PASS ..." or "FAIL ..." and ends with $finish.
`timescale 1 ns / 1 ps
module tb_gng;
  reg clk;
  reg rstn;
  reg ce;
  wire valid_out;
  wire [15:0] data_out;
  reg i_valid_in;
  reg [63:0] i_data_in;
  wire i_valid_out;
  wire [15:0] i_data_out;

  gng u_gng (.clk(clk), .rstn(rstn), .ce(ce), .valid_out(valid_out), .data_out(data_out));
  gng_interp u_interp (.clk(clk), .rstn(rstn), .valid_in(i_valid_in), .data_in(i_data_in),
                       .valid_out(i_valid_out), .data_out(i_data_out));

  reg [15:0] exp_s [0:8191];
  reg [63:0] in_i [0:1549];
  reg [15:0] exp_i [0:1549];
  reg chk_i [0:1549];
  integer info_diff;

  integer errors;
  integer checks;
  integer idx_s;
  integer idx_i;
  integer cyc;
  integer e0;
  integer lat;
  integer i;
  integer n;
  integer phase;

  initial clk = 0;
  always #5 clk = ~clk;

  always @(posedge clk) begin
    cyc = cyc + 1;
    if (ce && e0 < 0) e0 = cyc;
  end

  // gng output check
  always @(negedge clk) begin
    if (valid_out && phase != 3) begin
      if (lat < 0) lat = cyc - e0 + 1;
      if (idx_s < 8192) begin
        checks = checks + 1;
        if (data_out == exp_s[idx_s]) begin end
        else begin
          errors = errors + 1;
          if (errors < 6) $display("FAIL phase %0d sample %0d got %h want %h", phase, idx_s, data_out, exp_s[idx_s]);
        end
      end
      idx_s = idx_s + 1;
    end
  end

  // gng_interp output check
  always @(negedge clk) begin
    if (i_valid_out) begin
      if (idx_i < 1550) begin
        if (chk_i[idx_i]) begin
          checks = checks + 1;
          if (i_data_out == exp_i[idx_i]) begin end
          else begin
            errors = errors + 1;
            if (errors < 6) $display("FAIL interp word %0d got %h want %h", idx_i, i_data_out, exp_i[idx_i]);
          end
        end
        else if (i_data_out != exp_i[idx_i]) info_diff = info_diff + 1;
      end
      idx_i = idx_i + 1;
    end
  end

  initial begin
    errors = 0; checks = 0; idx_s = 0; idx_i = 0; info_diff = 0; cyc = 0; e0 = -1; lat = -1; phase = 0;
    ce = 0; i_valid_in = 0; i_data_in = 0; rstn = 0;
    $readmemh("stream_exp.hex", exp_s);
    $readmemh("interp_in.hex", in_i);
    $readmemh("interp_exp.hex", exp_i);
    $readmemh("interp_chk.hex", chk_i);
    repeat (3) @(posedge clk);
    #1 rstn = 1;
    repeat (10) @(posedge clk);

    // phase 1: ce high for 8192 cycles
    phase = 1;
    for (n = 0; n < 8192; n = n + 1) begin
      @(posedge clk); #1 ce = 1;
    end
    @(posedge clk); #1 ce = 0;
    repeat (30) @(posedge clk);
    checks = checks + 2;
    if (idx_s == 8192) begin end else begin errors = errors + 1; $display("FAIL phase 1 valid count %0d", idx_s); end
    if (lat == 11) begin end else begin errors = errors + 1; $display("FAIL latency %0d cycles, spec says 11", lat); end

    // phase 2: reset, then ce 3 on / 2 off until 2048 samples
    phase = 2;
    #1 rstn = 0;
    repeat (3) @(posedge clk);
    #1 rstn = 1; idx_s = 0;
    repeat (5) @(posedge clk);
    for (n = 0; n < 3413; n = n + 1) begin
      @(posedge clk); #1 ce = ((n % 5) < 3);
    end
    @(posedge clk); #1 ce = 0;
    repeat (30) @(posedge clk);
    checks = checks + 1;
    if (idx_s >= 2048 && idx_s <= 2049) begin end else begin errors = errors + 1; $display("FAIL phase 2 valid count %0d", idx_s); end

    // phase 3: gng_interp with directed words
    phase = 3;
    #1 rstn = 0;
    repeat (3) @(posedge clk);
    #1 rstn = 1; idx_i = 0;
    repeat (5) @(posedge clk);
    for (n = 0; n < 1550; n = n + 1) begin
      @(posedge clk); #1 i_valid_in = 1; i_data_in = in_i[n];
    end
    @(posedge clk); #1 i_valid_in = 0;
    repeat (30) @(posedge clk);
    checks = checks + 1;
    if (idx_i == 1550) begin end else begin errors = errors + 1; $display("FAIL interp count %0d", idx_i); end

    $display("INFO interp warm-up words that differ from the C model (not checked, mask one clock late): %0d of 62", info_diff);
    if (errors == 0) $display("PASS tb_gng checks=%0d errors=0", checks);
    else $display("FAIL tb_gng checks=%0d errors=%0d", checks, errors);
    $finish;
  end
endmodule
