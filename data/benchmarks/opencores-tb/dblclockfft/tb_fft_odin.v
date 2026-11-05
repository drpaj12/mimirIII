// tb_origin: mimir-written
// Self-checking testbench for the OpenCores dblclockfft demo core (rtl/fftmain.v: 2048-point forward
// FFT, 15-bit complex input, 21-bit complex output, natural order output).
// Reference: numpy FFT of six 2048-sample input frames times the core's scale factor 2^-5, rounded
// (gen_fft_vectors.py; scale derived from the widths in fftmain.v and confirmed by the impulse
// frame: 8000 in gives 250 flat). Frames: impulse, shifted impulse, DC, a tone, full-scale
// pseudo-random, low-level pseudo-random. Tolerance: TOL output LSB on each of real and imaginary
// (the core rounds in 11 stages; see README.md for how TOL was chosen).
// Also checked: o_sync comes once per 2048 outputs and only there.
// Plain Verilog-2005 without tasks, so the Odin III sim_tb subset can read it.
// Prints "PASS ..." or "FAIL ..." and ends with $finish.
`timescale 1ns/1ps
module tb_fft;
  parameter TOL = 8;
  reg clk;
  reg rst;
  reg ce;
  reg [29:0] smp;
  wire [41:0] res;
  wire sync;

  fftmain dut (.i_clk(clk), .i_reset(rst), .i_ce(ce), .i_sample(smp), .o_result(res),
               .o_sync(sync));

  reg [29:0] in_m [0:12287];
  reg [41:0] exp_m [0:12287];
  reg [41:0] ew;

  integer errors;
  integer checks;
  integer n;
  integer idx;
  integer cyc;
  integer cyc_first_in;
  integer cyc_first_sync;
  integer started;
  integer a;
  integer b;
  integer dre;
  integer dim;
  integer maxerr [0:5];
  integer f;

  initial clk = 0;
  always #5 clk = ~clk;
  always @(posedge clk) cyc = cyc + 1;

  always @(negedge clk) begin
    if (sync) begin
      if (started == 0) begin
        started = 1;
        idx = 0;
        cyc_first_sync = cyc;
      end
      else begin
        checks = checks + 1;
        if ((idx % 2048) == 0) begin end
        else begin errors = errors + 1; $display("FAIL o_sync at output %0d", idx); end
      end
    end
    if (started == 1 && idx < 12288) begin
      ew = exp_m[idx];
      a = $signed(res[41:21]);
      b = $signed(ew[41:21]);
      dre = a - b;
      if (dre < 0) dre = -dre;
      a = $signed(res[20:0]);
      b = $signed(ew[20:0]);
      dim = a - b;
      if (dim < 0) dim = -dim;
      f = idx / 2048;
      if (dre > maxerr[f]) maxerr[f] = dre;
      if (dim > maxerr[f]) maxerr[f] = dim;
      checks = checks + 1;
      if (dre <= TOL && dim <= TOL) begin end
      else begin
        errors = errors + 1;
        if (errors < 8) $display("FAIL frame %0d output %0d got %h want %h", f, idx % 2048, res, ew);
      end
      idx = idx + 1;
    end
  end

  initial begin
    errors = 0; checks = 0; cyc = 0; started = 0; idx = 0; cyc_first_sync = -1;
    for (n = 0; n < 6; n = n + 1) maxerr[n] = 0;
    rst = 1; ce = 0; smp = 0;
    $readmemh("in.hex", in_m);
    $readmemh("exp.hex", exp_m);
    repeat (4) @(posedge clk);
    #1 rst = 0;
    @(posedge clk);
    cyc_first_in = cyc + 1;
    for (n = 0; n < 12288 + 4800; n = n + 1) begin
      #1 ce = 1;
      if (n < 12288) smp = in_m[n]; else smp = 0;
      @(posedge clk);
    end
    #1 ce = 0;
    repeat (4) @(posedge clk);

    checks = checks + 1;
    if (idx == 12288) begin end else begin errors = errors + 1; $display("FAIL captured %0d of 12288 outputs", idx); end
    $display("INFO first o_sync %0d clocks after the first input; max abs error per frame (LSB): %0d %0d %0d %0d %0d %0d",
             cyc_first_sync - cyc_first_in, maxerr[0], maxerr[1], maxerr[2], maxerr[3], maxerr[4], maxerr[5]);
    if (errors == 0) $display("PASS tb_fft checks=%0d errors=0 tol=%0d", checks, TOL);
    else $display("FAIL tb_fft checks=%0d errors=%0d tol=%0d", checks, errors, TOL);
    $finish;
  end

  initial begin
    #2000000000;
    $display("FAIL tb_fft timeout");
    $finish;
  end
endmodule
