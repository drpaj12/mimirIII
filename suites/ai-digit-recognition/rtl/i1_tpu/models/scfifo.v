// Behavioural model of the Altera scfifo megafunction (single clock FIFO), enough for Gabe
// Litteken's TPU: lpm_showahead "OFF" with the registered output (add_ram_output_register "ON"):
// q holds the head entry one edge after the edge that sampled rdreq. Written for this suite (not
// Altera's altera_mf). overflow/underflow checking: a write when full and a read when empty are
// ignored. sclr is synchronous. The flags follow the entry count (empty goes low after the edge that
// stored the first entry). Ignored: aclr, almost_*, eccstatus (outputs tied).
`timescale 1 ps / 1 ps
module scfifo #(
    parameter lpm_width = 8,
    parameter lpm_widthu = 8,
    parameter lpm_numwords = 256,
    parameter lpm_showahead = "OFF",
    parameter add_ram_output_register = "ON",
    parameter overflow_checking = "ON",
    parameter underflow_checking = "ON",
    parameter use_eab = "ON",
    parameter intended_device_family = "Cyclone V",
    parameter lpm_type = "scfifo",
    parameter lpm_hint = "",
    parameter almost_full_value = 0,
    parameter almost_empty_value = 0,
    parameter allow_rwcycle_when_full = "OFF",
    parameter maximum_depth = 0
) (
    input                   clock,
    input                   aclr,
    input                   sclr,
    input  [lpm_width-1:0]  data,
    input                   rdreq,
    input                   wrreq,
    output                  empty,
    output                  full,
    output                  almost_empty,
    output                  almost_full,
    output reg [lpm_width-1:0] q,
    output [lpm_widthu-1:0] usedw,
    output [2:0]            eccstatus
);
    reg [lpm_width-1:0] mem [0:lpm_numwords-1];
    reg [lpm_widthu-1:0] wp;
    reg [lpm_widthu-1:0] rp;
    reg [lpm_widthu:0]   cnt;

    assign empty = (cnt == 0);
    assign full = (cnt == lpm_numwords);
    assign almost_empty = 1'b0;
    assign almost_full = 1'b0;
    assign usedw = cnt[lpm_widthu-1:0];
    assign eccstatus = 3'b000;

    wire wr = wrreq & ~full;
    wire rd = rdreq & ~empty;

    always @(posedge clock) begin
        if (wr) mem[wp] <= data;
        if (rd) q <= mem[rp];
        if (sclr) begin
            wp <= 0;
            rp <= 0;
            cnt <= 0;
        end else begin
            if (wr) wp <= wp + 1'b1;
            if (rd) rp <= rp + 1'b1;
            if (wr & ~rd) cnt <= cnt + 1'b1;
            else if (rd & ~wr) cnt <= cnt - 1'b1;
        end
    end
endmodule
