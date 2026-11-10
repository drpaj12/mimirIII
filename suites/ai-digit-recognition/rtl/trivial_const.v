// Trivial DUT: ignores the image, always answers class 7 with fixed scores.
// Proves the testbench detects wrong answers (expected: FAIL, class_match ~ share of golden 7s).
module mnist_top (
  input clk, input rst, input start, input in_valid, input [7:0] in_data,
  output in_ready, output reg done, output [3:0] pred, output [79:0] scores
);
  reg [9:0] cnt;
  reg busy;
  assign in_ready = busy;
  assign pred = 4'd7;
  assign scores = {8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd1, 8'd0, 8'd0} ;
  always @(posedge clk) begin
    if (rst) begin cnt <= 0; busy <= 0; done <= 0; end
    else if (start) begin cnt <= 0; busy <= 1; done <= 0; end
    else if (busy && in_valid) begin
      if (cnt == 10'd783) begin busy <= 0; done <= 1; end
      cnt <= cnt + 10'd1;
    end
  end
endmodule
