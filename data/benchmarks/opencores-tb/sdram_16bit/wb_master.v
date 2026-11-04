// tb_origin: upstream-fixed (Verilog-2005 port of testbench/wb_master.sv of OpenCores sdram_16bit)
// Port notes: requests are driven 1 time unit after the clock edge (race fix, see README); the request queue is a ring buffer, the sparse reference memory a 4096-word array with a
// valid bit per word, $urandom / $urandom_range are $random based, the ASSERT macro prints a line
// starting "FAIL" and calls $finish. The checks are those of the original: every read response is
// compared (byte lanes selected by sel, !==) with a reference memory written by the same requests, and
// a response with no outstanding request is an error. Upstream: GPL-2 or later (see the original file).
module wb_master
(
    input                               clk_i,
    input                               rst_i,

    // Wishbone I/F
    output reg [31:0]                   addr_o,
    output reg [31:0]                   data_o,
    input [31:0]                        data_i,
    output reg [3:0]                    sel_o,
    output reg [2:0]                    cti_o,
    output reg                          cyc_o,
    output reg                          stb_o,
    output reg                          we_o,
    input                               ack_i,
    input                               stall_i
);

parameter MIN_ADDRESS       = 0;
parameter MAX_ADDRESS       = 8192;
parameter BURST_ENABLED     = 1;
parameter READ_ONLY         = 0;
parameter WRITE_ONLY        = 0;
parameter SEQUENTIAL_ONLY   = 0;
parameter RANDOM_DELAY      = 1;
parameter DELAY_RATE        = 3;

// Request queue (ring buffer, 256 entries)
reg [31:0] q_address [0:255];
reg [31:0] q_data    [0:255];
reg [3:0]  q_sel     [0:255];
reg        q_we      [0:255];
integer    q_head;
integer    q_tail;
integer    q_size;

// Reference memory, word index = addr[31:2]
reg [31:0] mem  [0:4095];
reg        memv [0:4095];

integer    seed;
integer    resp_cnt;
integer    rd_checked;
integer    wr_done;
integer    rd_defined;
integer    failed;

// current request being built
reg [31:0] req_address;
reg [31:0] req_data;
reg [3:0]  req_sel;
reg        req_we;
reg        burst;
reg [2:0]  burst_cnt;
integer    dly;
reg        accepted;
integer    k;

function integer urange;
    input integer hi;
    input integer lo;
    integer r;
    begin
        r = $random(seed);
        if (r < 0) r = -r;
        urange = (r % (hi - lo + 1)) + lo;
    end
endfunction

reg [31:0] new_data;
reg        match;
reg [31:0] rd_data;

task write_bytes;
    input [31:0] addr;
    input [31:0] data;
    input [3:0]  sel;
    begin
        if (memv[addr[13:2]]) new_data = mem[addr[13:2]]; else new_data = 32'bx;
        if (sel[3]) new_data[31:24] = data[31:24];
        if (sel[2]) new_data[23:16] = data[23:16];
        if (sel[1]) new_data[15:8]  = data[15:8];
        if (sel[0]) new_data[7:0]   = data[7:0];
        mem[addr[13:2]]  = new_data;
        memv[addr[13:2]] = 1'b1;
    end
endtask

task compare;
    input [31:0] addr;
    input [31:0] data;
    input [3:0]  sel;
    begin
        if (memv[addr[13:2]]) new_data = mem[addr[13:2]]; else new_data = 32'bx;
        match = 1;
        if (sel[3]) if (new_data[31:24] !== data[31:24]) match = 0;
        if (sel[2]) if (new_data[23:16] !== data[23:16]) match = 0;
        if (sel[1]) if (new_data[15:8]  !== data[15:8])  match = 0;
        if (sel[0]) if (new_data[7:0]   !== data[7:0])   match = 0;
        if (!match)
            $display("ERROR: Expected %x Got %x Mask %x", new_data, data, sel);
    end
endtask

initial begin
    seed = 1;
    q_head = 0; q_tail = 0; q_size = 0; resp_cnt = 0; rd_checked = 0; wr_done = 0; rd_defined = 0; failed = 0;
    for (k = 0; k < 4096; k = k + 1) memv[k] = 1'b0;

    addr_o = 32'bz;
    data_o = 32'bz;
    sel_o  = 4'bz;
    we_o   = 1'bz;
    stb_o  = 1'b0;
    cti_o  = 3'bz;
    burst  = 1'b0;
    burst_cnt = 0;
    req_address = 0;
    req_data = 0;
    req_sel = 0;
    req_we = 0;

    forever begin
        @(posedge clk_i);
        // sample the handshake at the edge, then drive 1 time unit after it: the original drove with
        // blocking assignments at the edge itself, which races with the DUT's always @(posedge clk_i)
        accepted = (stb_o && !stall_i);
        #1;

        // Command presented and accepted
        if (accepted) begin
            q_address[q_tail] = req_address;
            q_data[q_tail]    = req_data;
            q_sel[q_tail]     = req_sel;
            q_we[q_tail]      = req_we;
            q_tail = (q_tail + 1) % 256;
            q_size = q_size + 1;

            addr_o = 32'bz;
            data_o = 32'bz;
            sel_o  = 4'bz;
            we_o   = 1'bz;
            cti_o  = 3'bz;
            stb_o  = 1'b0;
        end

        // Continuation of a burst
        if (!stb_o && burst) begin
            req_address = req_address + 4;
            req_data    = req_we ? $random(seed) : 32'bz;

            addr_o = req_address;
            addr_o[1:0] = 2'b0;
            data_o = req_data;
            cti_o  = (burst_cnt == 1) ? 3'b111 : 3'b010;
            sel_o  = req_sel;
            we_o   = req_we;
            stb_o  = 1'b1;

            burst_cnt   = burst_cnt - 1;
            if (burst_cnt == 0)
                burst   = 0;
        end

        // Ready to issue a new command?
        if (!stb_o) begin
            if (RANDOM_DELAY) begin
                dly = urange(DELAY_RATE, 0);
                repeat (dly) @(posedge clk_i);
                #1;
            end

            if (SEQUENTIAL_ONLY)
                req_address = req_address + 4;
            else
                req_address = urange(MAX_ADDRESS, MIN_ADDRESS);

            if (READ_ONLY)
                req_we  = 1'b0;
            else if (WRITE_ONLY)
                req_we  = 1'b1;
            else
                req_we  = $random(seed);
            req_data    = req_we ? $random(seed) : 32'bz;

            if (BURST_ENABLED) begin
                burst       = $random(seed);
                burst_cnt   = 7;
            end
            else
                burst       = 0;

            req_sel     = (!burst && req_we) ? $random(seed) : 4'b1111;

            addr_o = req_address;
            addr_o[1:0] = 2'b0;
            data_o = req_data;
            sel_o  = req_sel;
            we_o   = req_we;
            cti_o  = (!burst) ? 3'b111 : 3'b010;
            stb_o  = 1'b1;
        end
    end
end

// response
always @(posedge clk_i) begin
    if (ack_i) begin
        if (!(q_size > 0)) begin
            $display("FAIL: response with no outstanding request (requests.size() > 0)");
            failed = failed + 1;
            $finish;
        end
        else begin
            resp_cnt = resp_cnt + 1;
            if (q_we[q_head]) begin
                write_bytes(q_address[q_head], q_data[q_head], q_sel[q_head]);
                wr_done = wr_done + 1;
            end
            else begin
                compare(q_address[q_head], data_i, q_sel[q_head]);
                rd_checked = rd_checked + 1;
                if (memv[q_address[q_head][13:2]]) rd_defined = rd_defined + 1;
                if (!match) begin
                    $display("FAIL: read data mismatch at address %x (match)", q_address[q_head]);
                    failed = failed + 1;
                    $finish;
                end
            end
            q_head = (q_head + 1) % 256;
            q_size = q_size - 1;
        end
    end
end

always @* begin
    cyc_o  = stb_o || (q_size > 0);
end

endmodule
