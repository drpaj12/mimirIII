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
    reg [AW-1:0] r1, r2;   // registered read addresses: the form Odin III maps to a synchronous RAM
    initial $readmemh(`ROM_HEX, rom);
    always @(posedge clk) begin
        r1 <= a1;
        r2 <= a2;
    end
    always @* begin
        q1 = rom[r1];
        q2 = rom[r2];
    end
endmodule

// Single read port (picorv32): a second port with a constant address loses its address register
// to optimisation and stays asynchronous, which keeps the whole memory soft in Odin III.
module i2_rom1 #(parameter AW = 14) (
    input               clk,
    input  [AW-1:0]     a,
    output reg [31:0]   q
);
    reg [31:0] rom [0:(1<<AW)-1];
    reg [AW-1:0] r;
    initial $readmemh(`ROM_HEX, rom);
    always @(posedge clk) r <= a;
    always @* q = rom[r];
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
    // Odin III maps a RAM when the write comes from registers and the read is a plain
    // register of the memory output (data merge). A store therefore lands one cycle after its
    // request; a read at the same edge as a pending write to the same word takes the written data
    // through the bypass below, so a load right after a store sees the new data.
    reg [AW-1:0] wa;
    reg [3:0]    wen;
    reg [31:0]   wd;
    always @(posedge clk) begin
        wa <= a;
        wen <= we;
        wd <= d;
        if (wen[0]) m0[wa] <= wd[7:0];
        if (wen[1]) m1[wa] <= wd[15:8];
        if (wen[2]) m2[wa] <= wd[23:16];
        if (wen[3]) m3[wa] <= wd[31:24];
    end
    // one register per byte lane: Odin III's data merge needs a register as wide as the memory port
    // (partial_map/mem_merge.c:151, `covered == rp->data.len`), so a shared 32-bit register fails.
    reg [7:0]  rd0, rd1, rd2, rd3;
    reg [31:0] bd;
    reg [3:0]  hit;
    always @(posedge clk) begin
        rd0 <= m0[a];
        rd1 <= m1[a];
        rd2 <= m2[a];
        rd3 <= m3[a];
        bd <= wd;
        hit <= wen & {4{wa == a}};
    end
    always @* q = {hit[3] ? bd[31:24] : rd3, hit[2] ? bd[23:16] : rd2,
                   hit[1] ? bd[15:8] : rd1, hit[0] ? bd[7:0] : rd0};
endmodule
