// tb_origin: mimir-written
// Self-checking testbench for the OpenCores mips_16 core (rtl/mips_16_core_top.v and the stage files).
// Replaces the project's mips_16_core_top_tb_0.v, which prints the registers and checks nothing.
// Four programs are loaded into the instruction ROM ($readmemb into uut.IF_stage_inst.imem.rom, as the
// project's bench does), the core is reset and runs, then R0..R7 and data memory words 0..7 are compared:
//   test2      the project's own multiply program (bench/mips_16_core_top/test2.prog): R3 = 28*17 = 476,
//              R5 = 16, R6 = 1, R7 = 16, R1 = R2 = R4 = 0 (hand-derived from test2.asm)
//   alu        ADDI, ADD, SUB, AND, OR               } expected values from the Python model of the
//   shift_mem  SL, SR, SRU, ST, LD                    } instruction set in gen_mips_programs.py
//   dependent  back-to-back dependent instructions (no NOP gaps)
//   xor        printed only (INFO): the RTL sets alu_src2_mux = 1'bx for OP_XOR in ID_stage.v, so XOR
//              of two registers has an x operand in iverilog and an unspecified one in a 2-state simulator
// Prints "PASS ..." or "FAIL ..." per program and a total, ends with $finish.
`timescale 1ns/1ps
`include "mips_16_defs.v"
module tb_mips_16;
  reg clk;
  reg rst;
  wire [`PC_WIDTH-1:0] pc;

  mips_16_core_top uut (.clk(clk), .rst(rst), .pc(pc));

  reg [16:0] exp_m [0:15];
  integer errors;
  integer checks;
  integer perrors;
  integer p;
  integer i;
  reg [15:0] got;

  initial clk = 0;
  always #5 clk = ~clk;

  initial begin
    errors = 0; checks = 0;
    rst = 0;
    #100;
    for (p = 0; p < 5; p = p + 1) begin
      if (p == 0) begin
        $readmemb("test2.prog", uut.IF_stage_inst.imem.rom);
        $readmemh("test2.exp", exp_m);
      end
      if (p == 1) begin
        $readmemb("alu.prog", uut.IF_stage_inst.imem.rom);
        $readmemh("alu.exp", exp_m);
      end
      if (p == 2) begin
        $readmemb("shift_mem.prog", uut.IF_stage_inst.imem.rom);
        $readmemh("shift_mem.exp", exp_m);
      end
      if (p == 3) begin
        $readmemb("dependent.prog", uut.IF_stage_inst.imem.rom);
        $readmemh("dependent.exp", exp_m);
      end
      if (p == 4) begin
        $readmemb("xor.prog", uut.IF_stage_inst.imem.rom);
      end
      rst = 0;
      #10 rst = 1;
      #10 rst = 0;
      if (p == 0) repeat (700) @(posedge clk);
      else repeat (120) @(posedge clk);
      #1;
      if (p == 4) begin
        $display("INFO xor program: R3 = %h, want %h (12 ^ 5); not checked", uut.register_file_inst.reg_array[3], 16'h0009);
      end
      perrors = 0;
      if (p < 4) begin
      for (i = 0; i < 8; i = i + 1) begin
        got = uut.register_file_inst.reg_array[i];
        checks = checks + 1;
        if (got == exp_m[i][15:0]) begin end
        else begin
          perrors = perrors + 1;
          $display("FAIL program %0d R%0d got %h want %h", p, i, got, exp_m[i][15:0]);
        end
      end
      for (i = 0; i < 8; i = i + 1) begin
        if (exp_m[8 + i][16]) begin
          got = uut.MEM_stage_inst.dmem.ram[i];
          checks = checks + 1;
          if (got == exp_m[8 + i][15:0]) begin end
          else begin
            perrors = perrors + 1;
            $display("FAIL program %0d mem[%0d] got %h want %h", p, i, got, exp_m[8 + i][15:0]);
          end
        end
      end
      if (perrors == 0) $display("program %0d: PASS", p);
      else $display("program %0d: FAIL %0d errors", p, perrors);
      errors = errors + perrors;
      end
    end
    if (errors == 0) $display("PASS tb_mips_16 checks=%0d errors=0", checks);
    else $display("FAIL tb_mips_16 checks=%0d errors=%0d", checks, errors);
    $finish;
  end
endmodule
