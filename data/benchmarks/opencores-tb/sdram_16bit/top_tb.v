// tb_origin: upstream-fixed (Verilog-2005 port of testbench/top_tb.sv + simulation.svh of OpenCores sdram_16bit)
// Port notes: the simulation.svh macros are written out (no `timescale inside a module, no `__FILE__,
// no string stringification); the 10 ms run length is #100000000 in the 100 ps unit; the waveform dump
// is dropped. Added: at the end of the run a "PASS" line with the response counts, which needs at
// least 1000 responses and 100 reads of previously written words, else "FAIL". The timeout assertion (100000 cycles
// without an accepted request) is kept. Run with -DMAX_ADDRESS=8192 -DPART=IS42VM16400K.
`timescale 100ps/100ps
module top_tb ;

reg clk;
initial begin
   clk <= 0;
   forever #100 clk = ~clk;
end

reg rst;
initial begin
   rst <= 1;
   #200
   rst <= 0;
end

// TB_RUN_FOR(10ms)
initial begin
   #100000000;
   if (u_master.failed == 0 && u_master.resp_cnt >= 1000 && u_master.rd_defined >= 100)
      $display("PASS top_tb responses=%0d reads_checked=%0d reads_of_written_words=%0d writes=%0d", u_master.resp_cnt, u_master.rd_checked, u_master.rd_defined, u_master.wr_done);
   else
      $display("FAIL top_tb responses=%0d reads_checked=%0d failed=%0d", u_master.resp_cnt, u_master.rd_checked, u_master.failed);
   $finish;
end

wire [31:0] addr;
wire [31:0] data_w;
wire [31:0] data_r;
wire [3:0]  sel;
wire [2:0]  cti;
wire        stb;
wire        cyc;
wire        we;
wire        stall;
wire        ack;

wire          sdram_clk;
wire          sdram_cke;
wire          sdram_cs;
wire          sdram_ras;
wire          sdram_cas;
wire          sdram_we;
wire [1:0]    sdram_dqm;
wire [12:0]   sdram_addr;
wire [1:0]    sdram_ba;
wire [15:0]   sdram_data;

wb_master
#(
    .MIN_ADDRESS(0),
    .MAX_ADDRESS(`MAX_ADDRESS),
    .BURST_ENABLED(1),
    .READ_ONLY(0)
)
u_master
(
    .clk_i(clk),
    .rst_i(rst),
    .addr_o(addr),
    .data_o(data_w),
    .data_i(data_r),
    .stb_o(stb),
    .sel_o(sel),
    .cyc_o(cyc),
    .cti_o(cti),
    .we_o(we),
    .stall_i(stall),
    .ack_i(ack)
);

sdram
#(
    .SDRAM_START_DELAY(1000),
    .SDRAM_TARGET("SIMULATION")
)
u_dut
(
    .clk_i(clk),
    .rst_i(rst),
    .addr_i(addr),
    .data_i(data_w),
    .data_o(data_r),
    .stb_i(stb),
    .sel_i(sel),
    .cyc_i(cyc),
    .we_i(we),
    .stall_o(stall),
    .ack_o(ack),
    .sdram_clk_o(sdram_clk),
    .sdram_cke_o(sdram_cke),
    .sdram_cs_o(sdram_cs),
    .sdram_ras_o(sdram_ras),
    .sdram_cas_o(sdram_cas),
    .sdram_we_o(sdram_we),
    .sdram_dqm_o(sdram_dqm),
    .sdram_addr_o(sdram_addr),
    .sdram_ba_o(sdram_ba),
    .sdram_data_io(sdram_data)
);

`PART
u_ram
(
    .dq(sdram_data),
    .addr(sdram_addr),
    .ba(sdram_ba),
    .clk(sdram_clk),
    .cke(sdram_cke),
    .csb(sdram_cs),
    .rasb(sdram_ras),
    .casb(sdram_cas),
    .web(sdram_we),
    .dqm(sdram_dqm)
);

// TB_TIMEOUT(clk, rst, stb && !stall, 100000)
integer v_timeout_cycles;
always @(posedge rst or posedge clk)
if (rst)
    v_timeout_cycles <= 0;
else
begin
    if (stb && !stall)
        v_timeout_cycles <= 0;
    else
    begin
        v_timeout_cycles <= v_timeout_cycles + 1;
        if (!(v_timeout_cycles < 100000)) begin
            $display("FAIL: top_tb timeout, no accepted request for 100000 cycles");
            $finish;
        end
    end
end

endmodule
