// I1 wrapper: Gabe Litteken's programmable TPU (USS_Tensor_Processing_Unit) behind the P0 interface
// (docs/INTERFACE.md). Written for this suite; Gabe's files are read by path, never copied.
//
// The TPU is a programmable accelerator on an SPI link (his Arduino rig). This wrapper plays the
// Arduino: after reset it flashes the whole LeNet-5 transmission (weights and program, message
// protocol v0.3) over SPI from a ROM (`FLASH_HEX`, one byte per line, `FLASH_LEN` bytes), lets the
// resulting first run drain (10 output bytes, discarded), then raises `done` (power-up ready: the
// testbench waits for it, INTERFACE.md "Initialisation"). For each image: `start`, then an INPUT
// transmission 'I' 'M' 01 00 00 10 03 <784 pixel bytes> 'S' (write 784 bytes at ISA address 0x1);
// the TPU re-runs the program and the Programmer emits the ten int8 outputs (external mode,
// device_ready held high). `scores` = the ten bytes, `pred` = first maximum (signed).
// Cost note: the ROM and the SPI master are the wrapper's cost, counted in the design.
`timescale 1ns/1ps
`ifndef FLASH_HEX
`define FLASH_HEX "tpu_flash.hex"
`endif
// FLASH_LEN (bytes in the flash transmission) must be defined on the command line.
`ifndef SPI_HALF
`define SPI_HALF 4
`endif
`ifndef TPU_N
`define TPU_N 8
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
    localparam FLASH_LEN = `FLASH_LEN;
    localparam HALF = `SPI_HALF;

    // ---- SPI master (mode 0, MSB first) ----
    reg        sck;
    reg        mosi;
    reg        ss;
    reg [7:0]  sh;
    reg [3:0]  bitn;       // bits left in the byte
    reg [3:0]  div;
    reg        busy;
    reg        phase;      // 0: sck low half, 1: sck high half
    wire       tx_ready = ~busy;
    reg        tx_valid;
    reg [7:0]  tx_byte;

    always @(posedge clk) begin
        if (rst) begin
            sck <= 1'b0; mosi <= 1'b0; busy <= 1'b0; phase <= 1'b0; div <= 4'd0; bitn <= 4'd0; sh <= 8'd0;
        end else if (~busy) begin
            if (tx_valid) begin
                busy <= 1'b1; sh <= {tx_byte[6:0], 1'b0}; mosi <= tx_byte[7]; bitn <= 4'd8;
                phase <= 1'b0; div <= 4'd1;
            end
        end else begin
            if (div == HALF - 1) begin
                div <= 4'd0;
                if (~phase) begin
                    sck <= 1'b1; phase <= 1'b1;
                end else begin
                    sck <= 1'b0; phase <= 1'b0;
                    bitn <= bitn - 4'd1;
                    if (bitn == 4'd1) busy <= 1'b0;
                    else begin mosi <= sh[7]; sh <= {sh[6:0], 1'b0}; end
                end
            end else div <= div + 4'd1;
        end
    end

    // ---- flash ROM ----
    reg [7:0] rom [0:FLASH_LEN-1];
    initial $readmemh(`FLASH_HEX, rom);
    reg [17:0] raddr;
    reg [7:0]  rdat;
    always @(posedge clk) rdat <= rom[raddr];

    // ---- Gabe's TPU ----
    wire [7:0] o_data;
    wire       o_valid;
    TPU tpu (
        .i_clk(clk), .i_rst(~rst),
        .i_SPI_Clk(sck), .o_SPI_MISO(), .i_SPI_MOSI(mosi), .i_SPI_SS(ss),
        .i_mode_select(1'b1), .i_input_data_valid(1'b0), .i_device_ready(1'b1), .i_input_data(8'd0),
        .o_output_data(o_data), .o_output_data_valid(o_valid), .o_end_reached(),
        .o_error_code(), .o_feeder_cycle_count(), .o_sa_cycle_count()
    );

    // ---- control ----
    localparam S_RESET = 4'd0, S_FLASH = 4'd1, S_FLASH_END = 4'd2, S_BOOT = 4'd3, S_IDLE = 4'd4,
               S_HDR = 4'd5, S_PIX = 4'd6, S_STOP = 4'd7, S_END = 4'd8, S_WAIT = 4'd9, S_SS = 4'd10;
    reg [3:0]  st;
    reg [2:0]  hdr_i;
    reg [9:0]  pix_n;
    reg [3:0]  out_n;
    reg [3:0]  gap;
    reg        done_r;
    reg [3:0]  pred_r;
    reg [79:0] sc_r;
    reg [7:0]  best;
    reg        fetch;      // ROM byte requested one cycle ago
    reg [3:0]  nxt;        // state after the chip-select setup wait

    assign in_ready = (st == S_PIX) & tx_ready & ~tx_valid;
    assign done = done_r;
    assign pred = pred_r;
    assign scores = sc_r;

    wire [7:0] hdr_byte = (hdr_i == 3'd0) ? 8'h49 :   // 'I'
                          (hdr_i == 3'd1) ? 8'h4D :   // 'M'
                          (hdr_i == 3'd2) ? 8'h01 :   // address 0x000001 (the 0x1 buffer), low byte
                          (hdr_i == 3'd3) ? 8'h00 :
                          (hdr_i == 3'd4) ? 8'h00 :
                          (hdr_i == 3'd5) ? 8'h10 :   // length 784 = 0x0310, low byte
                                            8'h03;

    always @(posedge clk) begin
        tx_valid <= 1'b0;
        if (rst) begin
            st <= S_SS; nxt <= S_FLASH; ss <= 1'b0; raddr <= 18'd0; fetch <= 1'b0; done_r <= 1'b0; out_n <= 4'd0;
            hdr_i <= 3'd0; pix_n <= 10'd0; gap <= 4'd0; pred_r <= 4'd0; sc_r <= 80'd0; best <= 8'd0;
            tx_byte <= 8'd0;
        end else begin
            case (st)
            S_SS: begin
                // chip select low; the slave debounces it for a few clocks before the first sck edge
                gap <= gap + 4'd1;
                if (gap == 4'd11) begin gap <= 4'd0; st <= nxt; end
            end
            S_FLASH: begin
                if (tx_ready & ~tx_valid & ~fetch) begin
                    // issue ROM read; the byte is on rdat next cycle
                    fetch <= 1'b1;
                end else if (fetch) begin
                    fetch <= 1'b0;
                    tx_byte <= rdat; tx_valid <= 1'b1;
                    if (raddr == FLASH_LEN - 1) st <= S_FLASH_END;
                    else raddr <= raddr + 18'd1;
                end
            end
            S_FLASH_END: begin
                if (tx_ready & ~tx_valid) begin
                    gap <= gap + 4'd1;
                    if (gap == 4'd15) begin ss <= 1'b1; gap <= 4'd0; out_n <= 4'd0; st <= S_BOOT; end
                end
            end
            S_BOOT: begin
                if (o_valid) begin
                    out_n <= out_n + 4'd1;
                    if (out_n == 4'd9) begin done_r <= 1'b1; st <= S_IDLE; end
                end
            end
            S_IDLE: begin
                if (start) begin
                    done_r <= 1'b0; hdr_i <= 3'd0; pix_n <= 10'd0; st <= S_SS; nxt <= S_HDR; ss <= 1'b0; gap <= 4'd0;
                end
            end
            S_HDR: begin
                if (tx_ready & ~tx_valid) begin
                    tx_byte <= hdr_byte; tx_valid <= 1'b1;
                    if (hdr_i == 3'd6) st <= S_PIX;
                    hdr_i <= hdr_i + 3'd1;
                end
            end
            S_PIX: begin
                if (in_valid & in_ready) begin
                    tx_byte <= in_data; tx_valid <= 1'b1;
                    pix_n <= pix_n + 10'd1;
                    if (pix_n == 10'd783) st <= S_STOP;
                end
            end
            S_STOP: begin
                if (tx_ready & ~tx_valid) begin
                    tx_byte <= 8'h53; tx_valid <= 1'b1; st <= S_END; gap <= 4'd0;
                end
            end
            S_END: begin
                if (tx_ready & ~tx_valid) begin
                    gap <= gap + 4'd1;
                    if (gap == 4'd15) begin ss <= 1'b1; out_n <= 4'd0; st <= S_WAIT; end
                end
            end
            S_WAIT: begin
                if (o_valid) begin
                    sc_r <= {o_data, sc_r[79:8]};
                    if (out_n == 4'd0 || $signed(o_data) > $signed(best)) begin
                        best <= o_data; pred_r <= out_n;
                    end
                    out_n <= out_n + 4'd1;
                    if (out_n == 4'd9) begin done_r <= 1'b1; st <= S_IDLE; end
                end
            end
            default: st <= S_FLASH;
            endcase
        end
    end
endmodule
