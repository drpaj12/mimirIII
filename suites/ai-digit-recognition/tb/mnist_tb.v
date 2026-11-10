// MNIST benchmark testbench (Verilog-2005, subset accepted by iverilog and Odin III sim_tb).
// Contract: docs/INTERFACE.md. Reads vec_*.hex from the current directory.
// Compile with -DMNIST_N=<images in the tier> (100 quick, 10000 full); -DMNIST_INIT=<cycles> for a
// DUT that initialises itself after reset and raises `done` when ready (INTERFACE.md).
// Race-free by construction: the testbench changes its outputs and reads the DUT only at the
// falling clock edge; the DUT samples at the rising edge.
`timescale 1ns/1ps
module mnist_tb;
  reg clk;
  reg rst;
  reg start;
  reg in_valid;
  reg [7:0] in_data;
  wire in_ready;
  wire done;
  wire [3:0] pred;
  wire [79:0] scores;

  mnist_top dut (.clk(clk), .rst(rst), .start(start), .in_valid(in_valid),
                 .in_data(in_data), .in_ready(in_ready), .done(done),
                 .pred(pred), .scores(scores));

  reg [7:0] img   [0:`MNIST_N*784-1];
  reg [7:0] gsc   [0:`MNIST_N*10-1];
  reg [3:0] gcls  [0:`MNIST_N-1];
  reg [3:0] lab   [0:`MNIST_N-1];
  reg [31:0] meta [0:1];

  integer cyc;
  integer i, j, k, t0, waited;
  integer n_img, tmo;
  integer cls_ok, sc_ok, lab_ok, timeouts, cyc_total, cyc_i;
  integer bad_this, nprint, init_cycles, init_bad;
  reg [7:0] tmp;
  reg fin;

  initial clk = 0;
  always #5 clk = ~clk;
  initial cyc = 0;
  always @(posedge clk) cyc = cyc + 1;

  reg rdy_now;

  initial begin
    $readmemh("vec_images.hex", img);
    $readmemh("vec_gscores.hex", gsc);
    $readmemh("vec_gclass.hex", gcls);
    $readmemh("vec_labels.hex", lab);
    $readmemh("vec_meta.hex", meta);
    n_img = meta[0];
    tmo = meta[1];
    cls_ok = 0; sc_ok = 0; lab_ok = 0; timeouts = 0; cyc_total = 0; nprint = 0;
    rst = 1; start = 0; in_valid = 0; in_data = 0;
    repeat (4) @(negedge clk);
    rst = 0;
    repeat (2) @(negedge clk);
    init_cycles = 0;
    init_bad = 0;
`ifdef MNIST_INIT
    // Power-up initialisation (e.g. flashing weights): the DUT raises `done` when ready for the
    // first `start`. Not part of cycles_per_img; reported as init_cycles.
    while (!done && init_cycles < `MNIST_INIT) begin
      @(negedge clk);
      init_cycles = init_cycles + 1;
    end
    if (!done) begin
      $display("MNIST_TB init timeout after %0d cycles", init_cycles);
      init_bad = 1;
    end
`endif
    for (i = 0; i < n_img && !init_bad; i = i + 1) begin
      start = 1;
      t0 = cyc;
      @(negedge clk);
      start = 0;
      j = 0;
      in_valid = 1;
      in_data = img[i*784];
      waited = 0;
      while (j < 784 && waited < tmo) begin
        rdy_now = in_ready;        // a transfer happens at the next rising edge iff in_ready
        @(negedge clk);
        waited = waited + 1;
        if (rdy_now) begin
          j = j + 1;
          if (j < 784) in_data = img[i*784+j];
          else in_valid = 0;
        end
      end
      in_valid = 0;
      fin = 0;
      while (!fin && waited < tmo) begin
        if (done) fin = 1;
        else begin
          @(negedge clk);
          waited = waited + 1;
        end
      end
      if (!fin) begin
        timeouts = timeouts + 1;
        $display("MNIST_TB image %0d: timeout", i);
        rst = 1;
        repeat (4) @(negedge clk);
        rst = 0;
        repeat (2) @(negedge clk);
`ifdef MNIST_INIT
        init_cycles = 0;
        while (!done && init_cycles < `MNIST_INIT) begin
          @(negedge clk);
          init_cycles = init_cycles + 1;
        end
`endif
      end else begin
        cyc_i = cyc - t0;
        cyc_total = cyc_total + cyc_i;
        bad_this = 0;
        if (pred == gcls[i]) cls_ok = cls_ok + 1;
        else if (nprint < 5) begin
          nprint = nprint + 1;
          $display("MNIST_TB image %0d: class %0d want %0d", i, pred, gcls[i]);
        end
        if (pred == lab[i]) lab_ok = lab_ok + 1;
        for (k = 0; k < 10; k = k + 1) begin
          tmp = scores >> (8*k);
          if (tmp != gsc[i*10+k]) bad_this = bad_this + 1;
        end
        if (bad_this == 0) sc_ok = sc_ok + 1;
      end
    end
    if (cls_ok == n_img && sc_ok == n_img && timeouts == 0 && !init_bad)
      $display("MNIST_TB PASS n=%0d class_match=%0d score_match=%0d label_correct=%0d timeouts=%0d cycles_total=%0d cycles_per_img=%0d init_cycles=%0d",
               n_img, cls_ok, sc_ok, lab_ok, timeouts, cyc_total, cyc_total / n_img, init_cycles);
    else
      $display("MNIST_TB FAIL n=%0d class_match=%0d score_match=%0d label_correct=%0d timeouts=%0d cycles_total=%0d cycles_per_img=%0d init_cycles=%0d",
               n_img, cls_ok, sc_ok, lab_ok, timeouts, cyc_total, cyc_total / n_img, init_cycles);
    $finish;
  end
endmodule
