// I2 wrapper, core = BRISC-V mcu (Arduino-on-RISC-V, MIT): its RV32I core files (fetch/decode/control/
// execute/memory/writeback, read by path from external/Arduino-on-RISC-V, never copied) with our memory
// and MMIO in place of the mcu peripherals (PLL, timer, ports, interrupt handler). Written for this suite.
// ROM (code + weights, readable by loads) at 0x0000_0000, RAM at 0x1000_0000, MMIO (i2_mmio) at
// 0x4000_0000. The core has no multiply (RV32I only). Memory answers one cycle after the request, the
// core's own protocol (valid = registered read, address echoed back).
`timescale 1ns/1ps
`ifndef ROM_AW
`define ROM_AW 14
`endif
`ifndef RAM_AW
`define RAM_AW 11
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
    wire        fetch_read, memory_read, memory_write;
    wire [31:0] fetch_address_out, memory_address_out, memory_data_out;
    wire [3:0]  memory_byte_en;
    reg  [31:0] fetch_address_in, memory_address_in;
    reg         fetch_valid, memory_valid;
    wire [31:0] fetch_data_in, memory_data_in;

    single_cycle_core #(.CORE(0), .RESET_PC(0), .DATA_WIDTH(32), .ADDRESS_BITS(32),
                        .SCAN_CYCLES_MIN(0), .SCAN_CYCLES_MAX(0)) core (
        .clock(clk), .reset(rst), .start(1'b0), .program_address(32'd0),
        .fetch_valid(fetch_valid), .fetch_ready(1'b1), .fetch_data_in(fetch_data_in),
        .fetch_address_in(fetch_address_in),
        .memory_valid(memory_valid), .memory_ready(1'b1), .memory_data_in(memory_data_in),
        .memory_address_in(memory_address_in),
        .fetch_read(fetch_read), .fetch_address_out(fetch_address_out),
        .memory_read(memory_read), .memory_write(memory_write), .memory_byte_en(memory_byte_en),
        .memory_address_out(memory_address_out), .memory_data_out(memory_data_out),
        .interrupt_execute(1'b0), .interrupt_done(1'b0), .interrupt_jump(1'b0),
        .interrupt_stall(1'b0), .saved_PC(32'd0), .scan(1'b0));

    wire [31:0] rom_f, rom_d, ram_q, io_r;
    wire sel_rom = memory_address_out[31:28] == 4'h0;
    wire sel_ram = memory_address_out[31:28] == 4'h1;
    wire sel_io  = memory_address_out[31:28] == 4'h4;

    i2_rom #(.AW(`ROM_AW)) rom (.clk(clk), .a1(fetch_address_out[`ROM_AW+1:2]), .q1(rom_f),
                                .a2(memory_address_out[`ROM_AW+1:2]), .q2(rom_d));
    i2_ram #(.AW(`RAM_AW)) ram (.clk(clk), .a(memory_address_out[`RAM_AW+1:2]),
                                .we({4{memory_write & sel_ram}} & memory_byte_en),
                                .d(memory_data_out), .q(ram_q));
    i2_mmio io (.clk(clk), .rst(rst), .start(start), .in_valid(in_valid), .in_data(in_data),
                .in_ready(in_ready), .done(done), .pred(pred), .scores(scores),
                .w_en(memory_write & sel_io), .w_idx(memory_address_out[4:2]),
                .w_data(memory_data_out), .r_idx(memory_address_out[4:2]), .r_data(io_r));

    reg [31:0] io_q;
    reg [1:0]  sel_q;
    always @(posedge clk) begin
        fetch_valid <= fetch_read;
        fetch_address_in <= fetch_address_out;
        memory_valid <= memory_read;
        memory_address_in <= memory_address_out;
        io_q <= io_r;
        sel_q <= {sel_ram, sel_io};
    end
    assign fetch_data_in  = rom_f;
    assign memory_data_in = sel_q[0] ? io_q : (sel_q[1] ? ram_q : rom_d);
endmodule
