// tb_origin: mimir-written
// Self-checking testbench for the OpenCores verilog_cordic_core (cordic.v, default configuration:
// RADIAN_16, PIPELINE, ROTATE). Replaces tb_cordic.v of the project, which only prints values.
// Reference: math.sin / math.cos of the exact angle each U(1,15) code represents, scaled by 2^15
// (gen_cordic_vectors.py); 200 angles: 91 whole degrees 0..90, 109 from a fixed LCG.
// Tolerance: TOL output LSB (1 LSB = 2^-15) on sin and on cos; the project's own testbench flags errors above 10.
// The pipeline has 15 rotator stages (the generate loop runs ITERATIONS-1 times), so the result
// for an input appears 15 clock edges later.
// Plain Verilog-2005 without tasks or includes, so the Odin III sim_tb subset can read it.
// Prints "PASS ..." or "FAIL ..." and ends with $finish.
`timescale 1ns/1ns
module tb_cordic;
  parameter TOL = 10;
  parameter N = 200;
  parameter LAT = 15;
  reg clk;
  reg rst;
  reg signed [16:0] x_i;
  reg signed [16:0] y_i;
  reg signed [16:0] theta_i;
  wire signed [16:0] x_o;
  wire signed [16:0] y_o;
  wire signed [16:0] theta_o;

  cordic dut (.clk(clk), .rst(rst), .x_i(x_i), .y_i(y_i), .theta_i(theta_i),
              .x_o(x_o), .y_o(y_o), .theta_o(theta_o));

  reg [16:0] ang_m [0:199];
  reg [39:0] exp_m [0:199];
  reg [39:0] ew;

  integer errors;
  integer checks;
  integer cyc;
  integer m;
  integer ds;
  integer dc;
  integer es;
  integer ec;
  integer maxerr;

  initial clk = 0;
  always #5 clk = ~clk;

  initial begin
    errors = 0; checks = 0; maxerr = 0;
    $readmemh("angle.hex", ang_m);
    $readmemh("exp.hex", exp_m);
    rst = 1; x_i = 0; y_i = 0; theta_i = 0;
    repeat (3) @(posedge clk);
    @(negedge clk); rst = 0;
    for (cyc = 0; cyc < N + LAT + 2; cyc = cyc + 1) begin
      // at this negedge the output belongs to the input driven LAT negedges ago
      m = cyc - LAT;
      if (m >= 0 && m < N) begin
        ew = exp_m[m];
        es = $signed(ew[36:20]);
        ec = $signed(ew[16:0]);
        ds = y_o - es;
        if (ds < 0) ds = -ds;
        dc = x_o - ec;
        if (dc < 0) dc = -dc;
        if (ds > maxerr) maxerr = ds;
        if (dc > maxerr) maxerr = dc;
        checks = checks + 1;
        if (ds <= TOL && dc <= TOL) begin end
        else begin
          errors = errors + 1;
          if (errors < 8) $display("FAIL angle code %0d sin got %0d want %0d cos got %0d want %0d", ang_m[m], y_o, es, x_o, ec);
        end
      end
      if (cyc < N) begin
        x_i = 17'd19896; y_i = 0; theta_i = ang_m[cyc];
      end
      @(negedge clk);
    end
    $display("INFO largest |error| over sin and cos: %0d LSB", maxerr);
    if (errors == 0) $display("PASS tb_cordic checks=%0d errors=0 tol=%0d", checks, TOL);
    else $display("FAIL tb_cordic checks=%0d errors=%0d tol=%0d", checks, errors, TOL);
    $finish;
  end
endmodule
