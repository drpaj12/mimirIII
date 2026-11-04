# verilog_cordic_core testbench

tb_origin: `mimir-written` (`tb_cordic.v`, Mimir repo licence). The DUT `cordic.v` (Dale Drinkard, no licence
stated in the file) is not copied here. The project's `tb_cordic.v` only prints values; this one checks.

Configuration: the default `defines of `cordic.v` (RADIAN_16, PIPELINE, ROTATE, 16 bit + sign, 16 iterations,
`CORDIC_1` = 19896 as x input, y = 0). The generate loop builds ITERATIONS-1 = 15 rotators, so a result
appears 15 clock edges after its input (the table entry for iteration 15 is never used).

Checks (200; `PASS tb_cordic checks=200 errors=0 tol=10`): for 200 angle codes (91 whole degrees 0..90, 109
from a fixed LCG in 0..51471), one new input per clock, sin (`y_o`) and cos (`x_o`) within TOL = 10 LSB
(1 LSB = 2^-15) of the exact sin and cos of the angle the code represents (`gen_cordic_vectors.py`, math
module; the upstream tb's table is not used). 10 is the threshold the project's own tb uses to flag an error.
Largest error seen: 9 LSB (2.7e-4), more than the ~1e-4 the candidates survey expected; the cause is the
15 iterations and the 17-bit arithmetic with truncating shifts, not investigated. A mutation (one arctan table
entry changed by 100) gives 200 errors.

Run (iverilog), files in one directory (`$readmemh` paths):

    python3 gen_cordic_vectors.py .
    iverilog -g2005 -s tb_cordic -o sim.vvp cordic.v tb_cordic.v && vvp sim.vvp

Odin III: refused at the DUT: `odin3 -p "read_verilog cordic.v"` stops with
`cordic.v:178:5: error: for-loop condition is not constant (it reads 'i')` (the `signed_shifter` loop on the
input `i`). The testbench itself was not tried against Odin.
