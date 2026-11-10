// I2 shared MMIO block: the soft CPU sees the P0 interface (docs/INTERFACE.md) as a few registers.
// Written for this suite. The CPU polls; there are no blocking reads and no read side effects, so any
// core (one that re-issues a load, or holds a bus request several cycles) sees the same behaviour.
//
//   read  idx 0 STAT : bit0 = a pixel is waiting, bit1 = start pulse seen
//   read  idx 1 PIX  : the waiting pixel (int8, sign-extended)
//   write idx 0 ACK  : bit0 frees the pixel register, bit1 clears the start flag
//   write idx 1..3   : packed int8 scores (score k in bits [8k+7:8k] of the 80-bit vector)
//   write idx 4 DONE : pred = data[3:0], done goes high, the image is finished
// `done` is low from the `start` edge until DONE is written. in_ready = running & pixel register empty
// (a function of registers only, as the testbench requires).
module i2_mmio (
    input         clk,
    input         rst,
    input         start,
    input         in_valid,
    input  [7:0]  in_data,
    output        in_ready,
    output        done,
    output [3:0]  pred,
    output [79:0] scores,
    input         w_en,
    input  [2:0]  w_idx,
    input  [31:0] w_data,
    input  [2:0]  r_idx,
    output [31:0] r_data
);
    reg        run, full, spend, done_r;
    reg [7:0]  pix;
    reg [3:0]  pred_r;
    reg [79:0] sc;

    assign in_ready = run & ~full;
    assign done     = done_r;
    assign pred     = pred_r;
    assign scores   = sc;
    assign r_data   = (r_idx == 3'd0) ? {30'd0, spend, full}
                    : (r_idx == 3'd1) ? {{24{pix[7]}}, pix} : 32'd0;

    always @(posedge clk) begin
        if (rst) begin
            run <= 1'b0; full <= 1'b0; spend <= 1'b0; done_r <= 1'b0; pix <= 8'd0;
            pred_r <= 4'd0; sc <= 80'd0;
        end else begin
            if (w_en && w_idx == 3'd0) begin
                if (w_data[0]) full <= 1'b0;
                if (w_data[1]) spend <= 1'b0;
            end
            if (w_en && w_idx == 3'd1) sc[31:0] <= w_data;
            if (w_en && w_idx == 3'd2) sc[63:32] <= w_data;
            if (w_en && w_idx == 3'd3) sc[79:64] <= w_data[15:0];
            if (w_en && w_idx == 3'd4) begin
                pred_r <= w_data[3:0]; done_r <= 1'b1; run <= 1'b0;
            end
            if (in_valid & in_ready) begin
                pix <= in_data; full <= 1'b1;
            end
            if (start) begin
                spend <= 1'b1; run <= 1'b1; done_r <= 1'b0;
            end
        end
    end
endmodule
