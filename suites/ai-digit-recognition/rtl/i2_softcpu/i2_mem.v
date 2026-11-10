// I2 memories (behavioural, Odin III inferable): a ROM with two read ports (code and weights, loaded
// from a hex file of 32-bit words) and a byte-writable RAM. Written for this suite.
`ifndef ROM_HEX
`define ROM_HEX "i2_rom.hex"
`endif

module i2_rom #(parameter AW = 14) (
    input               clk,
    input  [AW-1:0]     a1,
    output reg [31:0]   q1,
    input  [AW-1:0]     a2,
    output reg [31:0]   q2
);
    reg [31:0] rom [0:(1<<AW)-1];
    initial $readmemh(`ROM_HEX, rom);
    always @(posedge clk) begin
        q1 <= rom[a1];
        q2 <= rom[a2];
    end
endmodule

module i2_ram #(parameter AW = 11) (
    input               clk,
    input  [AW-1:0]     a,
    input  [3:0]        we,
    input  [31:0]       d,
    output reg [31:0]   q
);
    reg [7:0] m0 [0:(1<<AW)-1];
    reg [7:0] m1 [0:(1<<AW)-1];
    reg [7:0] m2 [0:(1<<AW)-1];
    reg [7:0] m3 [0:(1<<AW)-1];
    always @(posedge clk) begin
        if (we[0]) m0[a] <= d[7:0];
        if (we[1]) m1[a] <= d[15:8];
        if (we[2]) m2[a] <= d[23:16];
        if (we[3]) m3[a] <= d[31:24];
        q <= {m3[a], m2[a], m1[a], m0[a]};
    end
endmodule
