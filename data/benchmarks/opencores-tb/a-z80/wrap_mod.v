// Pin-level wrapper around the MODIFIED a-z80 top: D_in/D_out/D_oe and pins_oe are turned back into the
// tri-state pins here (in the bench only), so the pin-level trace is directly comparable with upstream.
`timescale 1us/100ns
module dut_wrap(
    input CLK, input nWAIT, input nINT, input nNMI, input nRESET, input nBUSRQ,
    output nM1, output nMREQ, output nIORQ, output nRD, output nWR, output nRFSH, output nHALT, output nBUSACK,
    output [15:0] A, inout [7:0] D);
  wire [15:0] A_i; wire nMREQ_i, nIORQ_i, nRD_i, nWR_i; wire [7:0] D_out; wire D_oe, pins_oe;
  z80_top_direct_n u(.nM1(nM1), .nMREQ(nMREQ_i), .nIORQ(nIORQ_i), .nRD(nRD_i), .nWR(nWR_i), .nRFSH(nRFSH),
    .nHALT(nHALT), .nBUSACK(nBUSACK), .nWAIT(nWAIT), .nINT(nINT), .nNMI(nNMI), .nRESET(nRESET),
    .nBUSRQ(nBUSRQ), .CLK(CLK), .A(A_i), .D_in(D), .D_out(D_out), .D_oe(D_oe), .pins_oe(pins_oe));
  assign D     = D_oe    ? D_out  : 8'bz;
  assign A     = pins_oe ? A_i    : 16'bz;
  assign nMREQ = pins_oe ? nMREQ_i : 1'bz;
  assign nIORQ = pins_oe ? nIORQ_i : 1'bz;
  assign nRD   = pins_oe ? nRD_i   : 1'bz;
  assign nWR   = pins_oe ? nWR_i   : 1'bz;
endmodule
