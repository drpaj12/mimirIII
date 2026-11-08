// Pin-level wrapper around the UPSTREAM a-z80 top (bidirectional D, tri-state A and control pins).
`timescale 1us/100ns
module dut_wrap(
    input CLK, input nWAIT, input nINT, input nNMI, input nRESET, input nBUSRQ,
    output nM1, output nMREQ, output nIORQ, output nRD, output nWR, output nRFSH, output nHALT, output nBUSACK,
    output [15:0] A, inout [7:0] D);
  z80_top_direct_n u(.nM1(nM1), .nMREQ(nMREQ), .nIORQ(nIORQ), .nRD(nRD), .nWR(nWR), .nRFSH(nRFSH),
    .nHALT(nHALT), .nBUSACK(nBUSACK), .nWAIT(nWAIT), .nINT(nINT), .nNMI(nNMI), .nRESET(nRESET),
    .nBUSRQ(nBUSRQ), .CLK(CLK), .A(A), .D(D));
endmodule
