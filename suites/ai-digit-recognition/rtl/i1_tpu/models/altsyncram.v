// Behavioural model of the Altera altsyncram megafunction, enough for Gabe Litteken's TPU.
// Written for this suite (not Altera's altera_mf). Covers SINGLE_PORT and BIDIR_DUAL_PORT with the
// parameters his generated wrappers set. Timing (matches the Cyclone V M10K as his testbenches
// expect): address, data and write enable are registered at clock0; a write reaches the array one
// edge later; a read of the registered address goes to an optional output register (outdata_reg_*
// = "CLOCK0", else the combinational read). Same-port read-during-write returns the new data
// (NEW_DATA_NO_NBE_READ); mixed-port same-address read returns the old data (DONT_CARE).
// Ignored (tied off in his instances): aclr*, addressstall_*, byteena_*, clock1, clocken*, rden_*.
`timescale 1 ps / 1 ps
module altsyncram #(
    parameter operation_mode = "BIDIR_DUAL_PORT",
    parameter width_a = 8,
    parameter widthad_a = 8,
    parameter numwords_a = 256,
    parameter width_b = 8,
    parameter widthad_b = 8,
    parameter numwords_b = 256,
    parameter width_byteena_a = 1,
    parameter width_byteena_b = 1,
    parameter outdata_reg_a = "UNREGISTERED",
    parameter outdata_reg_b = "UNREGISTERED",
    parameter address_reg_b = "CLOCK0",
    parameter clock_enable_input_a = "BYPASS",
    parameter clock_enable_input_b = "BYPASS",
    parameter clock_enable_output_a = "BYPASS",
    parameter clock_enable_output_b = "BYPASS",
    parameter indata_reg_b = "CLOCK0",
    parameter intended_device_family = "Cyclone V",
    parameter lpm_type = "altsyncram",
    parameter lpm_hint = "",
    parameter outdata_aclr_a = "NONE",
    parameter outdata_aclr_b = "NONE",
    parameter power_up_uninitialized = "FALSE",
    parameter read_during_write_mode_mixed_ports = "DONT_CARE",
    parameter read_during_write_mode_port_a = "NEW_DATA_NO_NBE_READ",
    parameter read_during_write_mode_port_b = "NEW_DATA_NO_NBE_READ",
    parameter wrcontrol_wraddress_reg_b = "CLOCK0"
) (
    input  [widthad_a-1:0] address_a,
    input  [widthad_b-1:0] address_b,
    input                  clock0,
    input                  clock1,
    input  [width_a-1:0]   data_a,
    input  [width_b-1:0]   data_b,
    input                  wren_a,
    input                  wren_b,
    input                  rden_a,
    input                  rden_b,
    input                  clocken0,
    input                  clocken1,
    input                  clocken2,
    input                  clocken3,
    input                  aclr0,
    input                  aclr1,
    input                  addressstall_a,
    input                  addressstall_b,
    input  [width_byteena_a-1:0] byteena_a,
    input  [width_byteena_b-1:0] byteena_b,
    output [width_a-1:0]   q_a,
    output [width_b-1:0]   q_b,
    output [2:0]           eccstatus
);
    localparam TWO_PORT = (operation_mode == "BIDIR_DUAL_PORT");
    localparam REG_A = (outdata_reg_a == "CLOCK0");
    localparam REG_B = (outdata_reg_b == "CLOCK0");

    reg [width_a-1:0] mem [0:numwords_a-1];

    reg [widthad_a-1:0] aa;
    reg [width_a-1:0]   da;
    reg                 wa;
    reg [widthad_b-1:0] ab;
    reg [width_b-1:0]   db;
    reg                 wb;

    always @(posedge clock0) begin
        aa <= address_a;
        da <= data_a;
        wa <= wren_a;
        ab <= address_b;
        db <= data_b;
        wb <= wren_b;
        if (wa) mem[aa] <= da;
        if (TWO_PORT && wb) mem[ab] <= db;
    end

    // Read ports. Only the configured kind is described, so a registered-output memory has no
    // asynchronous read for a synthesis tool to trip over. The registered-output read is the plain
    // synchronous-read RAM pattern (read of the registered address into a register); the
    // same-port write-through (NEW_DATA) is a bypass multiplexer after that register, which gives
    // the same values as writing the bypass in front of the register.
    generate
        if (REG_A) begin : out_a_reg
            reg [width_a-1:0] rd;
            reg [width_a-1:0] bypd;
            reg               byp;
            always @(posedge clock0) rd <= mem[aa];
            always @(posedge clock0) begin
                bypd <= da;
                byp <= wa;
            end
            assign q_a = byp ? bypd : rd;
        end else begin : out_a_comb
            assign q_a = wa ? da : mem[aa];
        end
        if (!TWO_PORT) begin : out_b_none
            assign q_b = {width_b{1'b0}};
        end else if (REG_B) begin : out_b_reg
            reg [width_b-1:0] rd;
            reg [width_b-1:0] bypd;
            reg               byp;
            always @(posedge clock0) rd <= mem[ab];
            always @(posedge clock0) begin
                bypd <= db;
                byp <= wb;
            end
            assign q_b = byp ? bypd : rd;
        end else begin : out_b_comb
            assign q_b = wb ? db : mem[ab];
        end
    endgenerate
    assign eccstatus = 3'b000;
endmodule
