// I2 wrapper, core = picorv32 (YosysHQ, ISC; read by path from external/picorv32, never copied).
// Written for this suite. picorv32 native memory interface; ROM (code + weights) at 0x0000_0000, RAM at
// 0x1000_0000, MMIO (i2_mmio) at 0x4000_0000. Setting by define: PICO_MUL (ENABLE_MUL), PICO_FAST
// (ENABLE_FAST_MUL), PICO_DIV (ENABLE_DIV); none = rv32i without hardware multiply.
// Memory access: 2 cycles (request, registered ready), as the picosoc pattern.
`timescale 1ns/1ps
`ifndef ROM_AW
`define ROM_AW 14
`endif
`ifndef RAM_AW
`define RAM_AW 11
`endif
`ifndef PICO_MUL
`define PICO_MUL 0
`endif
`ifndef PICO_FAST
`define PICO_FAST 0
`endif
`ifndef PICO_DIV
`define PICO_DIV 0
`endif

module mnist_top (
    input         clk,
    input         rst,
    input         start,
    input         in_valid,
    input  [7:0]  in_data,
    output        in_ready,
    output        done,
    output [3:0]  pred,
    output [79:0] scores
);
    wire        mem_valid;
    wire [31:0] mem_addr, mem_wdata;
    wire [3:0]  mem_wstrb;
    reg         mem_ready;
    wire [31:0] mem_rdata;
    wire        resetn = ~rst;

    picorv32 #(
        .ENABLE_COUNTERS(0), .ENABLE_COUNTERS64(0), .CATCH_MISALIGN(0), .CATCH_ILLINSN(0),
        .ENABLE_MUL(`PICO_MUL), .ENABLE_FAST_MUL(`PICO_FAST), .ENABLE_DIV(`PICO_DIV),
        .PROGADDR_RESET(32'h0000_0000)
    ) cpu (
        .clk(clk), .resetn(resetn), .trap(),
        .mem_valid(mem_valid), .mem_instr(), .mem_ready(mem_ready), .mem_addr(mem_addr),
        .mem_wdata(mem_wdata), .mem_wstrb(mem_wstrb), .mem_rdata(mem_rdata),
        .mem_la_read(), .mem_la_write(), .mem_la_addr(), .mem_la_wdata(), .mem_la_wstrb(),
        .pcpi_valid(), .pcpi_insn(), .pcpi_rs1(), .pcpi_rs2(),
        .pcpi_wr(1'b0), .pcpi_rd(32'd0), .pcpi_wait(1'b0), .pcpi_ready(1'b0),
        .irq(32'd0), .eoi(), .trace_valid(), .trace_data()
    );

    wire sel_rom = mem_addr[31:28] == 4'h0;
    wire sel_ram = mem_addr[31:28] == 4'h1;
    wire sel_io  = mem_addr[31:28] == 4'h4;
    wire accept  = mem_valid & ~mem_ready;
    wire [3:0] wr = mem_wstrb;

    wire [31:0] rom_q, ram_q, io_r;
    i2_rom #(.AW(`ROM_AW)) rom (.clk(clk), .a1(mem_addr[`ROM_AW+1:2]), .q1(rom_q),
                                .a2({`ROM_AW{1'b0}}), .q2());
    i2_ram #(.AW(`RAM_AW)) ram (.clk(clk), .a(mem_addr[`RAM_AW+1:2]),
                                .we({4{accept & sel_ram}} & wr), .d(mem_wdata), .q(ram_q));
    i2_mmio io (.clk(clk), .rst(rst), .start(start), .in_valid(in_valid), .in_data(in_data),
                .in_ready(in_ready), .done(done), .pred(pred), .scores(scores),
                .w_en(accept & sel_io & (|wr)), .w_idx(mem_addr[4:2]), .w_data(mem_wdata),
                .r_idx(mem_addr[4:2]), .r_data(io_r));

    reg [31:0] io_q;
    reg [1:0]  sel_q;
    always @(posedge clk) begin
        io_q <= io_r;
        sel_q <= {sel_ram, sel_io};
        mem_ready <= rst ? 1'b0 : accept;
    end
    assign mem_rdata = sel_q[0] ? io_q : (sel_q[1] ? ram_q : rom_q);
endmodule
