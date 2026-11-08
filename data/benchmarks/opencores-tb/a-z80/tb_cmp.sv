// Compare bench: one DUT (upstream or modified, selected by the wrapper file) + RAM/IO/IORQ models
// from the upstream repo; logs every pin at both clock edges. Run once per DUT; the two logs are diffed.
`timescale 1us/100ns
module tb_cmp;
  parameter NCYC = 40000;
  reg CLK = 1;
  reg nWAIT = 1, nINT = 1, nNMI = 1, nRESET = 0, nBUSRQ = 1;
  wire nM1, nMREQ, nIORQ, nRD, nWR, nRFSH, nHALT, nBUSACK;
  wire [15:0] A;
  wire [7:0] D;
  integer cyc = 0, tf;
  initial begin
    tf = $fopen("trace.txt", "w");
    repeat (NCYC) #1 CLK = ~CLK;
    $fclose(tf);
    $finish;
  end
  dut_wrap dw(.CLK(CLK), .nWAIT(nWAIT), .nINT(nINT), .nNMI(nNMI), .nRESET(nRESET), .nBUSRQ(nBUSRQ),
    .nM1(nM1), .nMREQ(nMREQ), .nIORQ(nIORQ), .nRD(nRD), .nWR(nWR), .nRFSH(nRFSH), .nHALT(nHALT),
    .nBUSACK(nBUSACK), .A(A), .D(D));
  ram  ram (.Address(A), .Data(D), .CS(nMREQ), .WE(nWR), .OE(nRD));
  io   io  (.Address(A), .Data(D), .CS(nIORQ), .WE(nWR), .OE(nRD));
  iorq iorq(.Data(D), .M1(nM1), .IORQ(nIORQ));

  // stimulus, identical for both DUTs (cycle numbers = clock periods)
  initial begin
    repeat (3) @(posedge CLK); nRESET <= 1;
  end
  initial begin  // INT pulses (held until acknowledged or 300 cycles), NMI pulses, WAIT and BUSRQ windows
    repeat (1000) @(posedge CLK); nINT <= 0; repeat (300) @(posedge CLK); nINT <= 1;
    repeat (4000) @(posedge CLK); nINT <= 0; repeat (300) @(posedge CLK); nINT <= 1;
  end
  initial begin
    repeat (500) @(posedge CLK); nNMI <= 0; repeat (2) @(posedge CLK); nNMI <= 1;
    repeat (3000) @(posedge CLK); nNMI <= 0; repeat (2) @(posedge CLK); nNMI <= 1;
  end
  initial begin
    repeat (1008) @(posedge CLK); nWAIT <= 0; repeat (5) @(posedge CLK); nWAIT <= 1;
    repeat (2000) @(posedge CLK); nWAIT <= 0; repeat (3) @(posedge CLK); nWAIT <= 1;
  end
  initial begin
    repeat (200) @(posedge CLK); nBUSRQ <= 0; repeat (10) @(posedge CLK); nBUSRQ <= 1;
    repeat (6000) @(posedge CLK); nBUSRQ <= 0; repeat (10) @(posedge CLK); nBUSRQ <= 1;
  end
  initial begin  // second reset in the middle of the run
    repeat (9000) @(posedge CLK); nRESET <= 0; repeat (3) @(posedge CLK); nRESET <= 1;
  end

`ifdef CHK_ONEDRV
`include "chk_onedrv.svh"
`endif
  always @(posedge CLK or negedge CLK) begin
    #0.3;
    $fdisplay(tf, "%0d %b %b %b %b%b%b%b%b%b%b%b", cyc, CLK, A, D, nM1, nMREQ, nIORQ, nRD, nWR, nRFSH, nHALT, nBUSACK);
    cyc = cyc + 1;
  end
endmodule
