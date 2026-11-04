// tb_origin: mimir-written model (behavioural replacement for the vendor-generated core that the
// OpenCores gng project does not ship). Multiply-add p = a*b + c, signed: a 16 bit, b 18 bit, c 37 bit,
// p 38 bit, three clock cycles from a/b to p, with c taken one cycle after a/b (the Xilinx DSP48 pattern:
// A and B register, product register, then add the C register into the P register).
// The latency and the alignment of c are not stated in the project; they are the only values that make
// gng_interp.v consistent: x_r4 (= x_r1 delayed 3) is used with p, and c1_r1 (= c1 delayed 1) is the c
// input while b = c2 is not delayed. The gng testbench compares the core against the project's C model
// (c/icdf.c), so a wrong guess would fail it.
`timescale 1 ns / 1 ps
module gng_smul_16_18_sadd_37 (
    input clk,
    input [15:0] a,
    input [17:0] b,
    input [36:0] c,
    output [37:0] p
);

reg signed [15:0] a_reg;
reg signed [17:0] b_reg;
reg signed [33:0] prod;
reg signed [36:0] c_reg;
reg signed [37:0] sum;

always @ (posedge clk) begin
    a_reg <= a;
    b_reg <= b;
end

always @ (posedge clk) begin
    prod <= a_reg * b_reg;
    c_reg <= c;
end

always @ (posedge clk) begin
    sum <= {{4{prod[33]}}, prod} + {c_reg[36], c_reg};
end

assign p = sum;

endmodule
