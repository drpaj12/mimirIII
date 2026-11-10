"""Write an oracle DUT (lookup of golden scores by image index) for a tier.
It ignores pixel values and counts images, so it passes the testbench on the tier the
table was built from. It proves the PASS path and the scoring flow, not an implementation.
usage: gen_oracle.py <vec_dir> <out.v>
"""
import sys
d, out = sys.argv[1], sys.argv[2]
n = int(open(f"{d}/vec_meta.hex").readline(), 16)
gs = [l.strip() for l in open(f"{d}/vec_gscores.hex")]
gc = [l.strip() for l in open(f"{d}/vec_gclass.hex")]
L = ["// generated: oracle DUT for the mnist_tb contract (see tools/gen_oracle.py)",
     "module mnist_top (input clk, input rst, input start, input in_valid, input [7:0] in_data,",
     "  output in_ready, output reg done, output reg [3:0] pred, output reg [79:0] scores);",
     "  reg [9:0] cnt; reg busy; reg [13:0] idx;",
     "  assign in_ready = busy;",
     "  always @(posedge clk) begin",
     "    if (rst) begin cnt <= 0; busy <= 0; done <= 0; idx <= 14'h3fff; end",
     "    else if (start) begin cnt <= 0; busy <= 1; done <= 0; idx <= idx + 14'd1; end",
     "    else if (busy && in_valid) begin",
     "      if (cnt == 10'd783) begin busy <= 0; done <= 1; end",
     "      cnt <= cnt + 10'd1;",
     "    end",
     "  end",
     "  always @(*) begin",
     "    case (idx)"]
for i in range(n):
    sc = "".join(gs[i*10+k] for k in range(9, -1, -1))
    L.append(f"      14'd{i}: begin pred = 4'h{gc[i]}; scores = 80'h{sc}; end")
L += ["      default: begin pred = 4'd0; scores = 80'd0; end", "    endcase", "  end", "endmodule"]
open(out, "w").write("\n".join(L) + "\n")
