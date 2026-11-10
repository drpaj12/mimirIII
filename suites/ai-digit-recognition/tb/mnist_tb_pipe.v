// Back-to-back (pipelined) testbench for the interface of docs/INTERFACE.md, extension
// "initiation interval". Images are streamed without waiting for results: `start` for image i+1 is
// pulsed as soon as image i's 784th pixel was taken. A result is collected at each rising edge of
// `done` (the DUT clears `done` at `start` and raises it when the oldest image finishes), in order.
// Compile with -DMNIST_N=<images>. Reports ii_cycles = mean cycles between consecutive results
// (steady-state initiation interval) and latency_first = cycles from the first start to the first result.
`timescale 1ns/1ps
module mnist_tb_pipe;
  reg clk, rst, start, in_valid;
  reg [7:0] in_data;
  wire in_ready, done;
  wire [3:0] pred;
  wire [79:0] scores;
  mnist_top dut (.clk(clk), .rst(rst), .start(start), .in_valid(in_valid), .in_data(in_data),
                 .in_ready(in_ready), .done(done), .pred(pred), .scores(scores));
  reg [7:0] img  [0:`MNIST_N*784-1];
  reg [7:0] gsc  [0:`MNIST_N*10-1];
  reg [3:0] gcls [0:`MNIST_N-1];
  reg [3:0] lab  [0:`MNIST_N-1];
  reg [31:0] meta [0:1];
  integer cyc, i, j, k, n_img, rcnt, cls_ok, sc_ok, lab_ok, bad, t_first, t_last, t_start0, guard;
  reg [7:0] tmp;
  reg done_prev, rdy_now, fed;
  reg [31:0] tst [0:`MNIST_N-1];
  initial clk = 0;
  always #5 clk = ~clk;
  initial cyc = 0;
  always @(posedge clk) cyc = cyc + 1;

  // collector: sample at the falling edge, rising edge of done = one result
  always @(negedge clk) begin
    if (done && !done_prev && rcnt < n_img) begin
      tst[rcnt] = $time / 10;
      if (pred == gcls[rcnt]) cls_ok = cls_ok + 1;
      if (pred == lab[rcnt]) lab_ok = lab_ok + 1;
      bad = 0;
      for (k = 0; k < 10; k = k + 1) begin
        tmp = scores >> (8*k);
        if (tmp != gsc[rcnt*10+k]) bad = bad + 1;
      end
      if (bad == 0) sc_ok = sc_ok + 1;
      rcnt = rcnt + 1;
    end
    done_prev = done;
  end

  initial begin
    $readmemh("vec_images.hex", img);
    $readmemh("vec_gscores.hex", gsc);
    $readmemh("vec_gclass.hex", gcls);
    $readmemh("vec_labels.hex", lab);
    $readmemh("vec_meta.hex", meta);
    n_img = meta[0];
    cls_ok = 0; sc_ok = 0; lab_ok = 0; rcnt = 0; t_first = 0; t_last = 0; done_prev = 0;
    rst = 1; start = 0; in_valid = 0; in_data = 0;
    repeat (4) @(negedge clk);
    rst = 0;
    repeat (2) @(negedge clk);
    t_start0 = $time / 10;
    for (i = 0; i < n_img; i = i + 1) begin
      start = 1;
      @(negedge clk);
      start = 0;
      j = 0;
      in_valid = 1;
      in_data = img[i*784];
      guard = 0;
      while (j < 784 && guard < 50000000) begin
        rdy_now = in_ready;
        @(negedge clk);
        guard = guard + 1;
        if (rdy_now) begin
          j = j + 1;
          if (j < 784) in_data = img[i*784+j];
          else in_valid = 0;
        end
      end
      in_valid = 0;
    end
    guard = 0;
    while (rcnt < n_img && guard < 50000000) begin @(negedge clk); guard = guard + 1; end
    if (cls_ok == n_img && sc_ok == n_img && rcnt == n_img)
      $write("MNIST_TB PASS ");
    else
      $write("MNIST_TB FAIL ");
    t_first = tst[0]; t_last = tst[n_img-1];
    $display("n=%0d class_match=%0d score_match=%0d label_correct=%0d timeouts=%0d cycles_total=%0d cycles_per_img=%0d init_cycles=0 ii_cycles=%0d latency_first=%0d results=%0d",
             n_img, cls_ok, sc_ok, lab_ok, n_img - rcnt, t_last - t_start0, (t_last - t_start0) / n_img,
             (rcnt > 1) ? (t_last - t_first) / (rcnt - 1) : 0, t_first - t_start0, rcnt);
    $finish;
  end
endmodule
