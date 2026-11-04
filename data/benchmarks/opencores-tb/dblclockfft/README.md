# dblclockfft testbench

tb_origin: `mimir-written` (`tb_fft.v` for iverilog, `tb_fft_odin.v` for Odin III, Mimir repo licence).
The project has no testbench in its clone (`bench/` is missing). The RTL is the demo core in `rtl/`
(`fftmain.v` and the files it uses; GPL-3, Gisselquist Technology, not copied here): a 2048-point forward
FFT, `IWIDTH=15`, `OWIDTH=21`, natural-order output. `ifftmain.v` / `ifftstage.v` are not used (they
redefine `fftstage`).

Files:
- `gen_fft_vectors.py`: writes the twiddle files `cmem_<N>.hex` (a port of `gen_coeffs()` in the project's
  `sw/fftlib.cpp`; checked identical to the output of that function compiled with g++ for all 9 stages;
  the clone lacks `butterfly.h`, so `fftgen` itself does not build), `in.hex` (6 input frames) and `exp.hex`
  (expected output). Widths are read from `fftmain_stages.txt`, an extract of `fftmain.v`.
- `fftmain_stages.txt`: the width `localparam` line and the 9 `fftstage` instances of `rtl/fftmain.v`.

Reference: numpy FFT of each 2048-sample frame times the core's scale factor 2^-5, rounded to an integer.
The project doc (`doc/src/spec.tex`) says the FFT computes the DFT "to within a scale factor" and does not
give it. The factor is derived from the widths in `fftmain.v`: the core gains OWIDTH - IWIDTH = 6 bits while
an unscaled 2048-point sum needs 11, so 2^-(11-6) = 2^-5; the impulse frame confirms it (8000 in, 250 out
on every bin, error 0).

Frames (all 2048 samples): impulse at 0 (8000); impulse at 5 (12000, -3000); DC (1000, -500); a complex tone
at bin 37, amplitude 10000; pseudo-random components in +-11000 (fixed LCG); pseudo-random +-300.

Checks (12295; prints `PASS tb_fft checks=12295 errors=0 tol=8` or `FAIL ...`, ends with `$finish`): every
output sample, real and imaginary, within TOL = 8 LSB of the reference; `o_sync` high exactly on output 0
of each frame and nowhere else; all 12288 outputs seen. Printed, not checked: `o_sync` comes 4266 clocks
after the first input; the largest error per frame was 0 1 0 4 3 4 LSB. TOL is empirical: twice the largest
error seen on these frames (the core rounds convergently in each of 11 stages, so it has no tight analytic
bound that I derived). A corrupted twiddle (one `cmem_2048.hex` line) gives FAIL with 3072 errors.

Findings, observed not fixed:
1. iverilog never runs `always @(*) idle = 0;` in `fftstage.v` (no sensitivities), so `idle` stays x and the
   butterfly inputs are x wherever a data bit is 1; the outputs are x. `tb_fft.v` forces `idle` to 0 in the
   9 stages (`force dut.stage_N.idle`); the RTL is untouched. `tb_fft_odin.v` has no forces (Odin III is
   2-state) and is otherwise identical (a test checks that).
2. Input headroom: with components at +-16000 (of the 15-bit +-16383) the output is wrong by up to 12621 LSB
   on every odd output: the first stage output has 16 bits and the complex rotation of a difference can reach
   |d| * sqrt(2), so dense inputs must stay below about 2^15 / (2 sqrt(2)) = 11585 per component. The
   project does not state this limit; the dense frames here stay inside it.

Run (iverilog), in a directory with the 10 RTL files (`fftmain fftstage qtrstage laststage hwbfly butterfly
longbimpy bimpy bitreverse convround`), the generated `.hex` files and `tb_fft.v` (run in that directory,
`$readmemh` paths):

    python3 gen_fft_vectors.py fftmain_stages.txt .      # or use the committed .hex files
    iverilog -g2005 -s tb_fft -o sim.vvp fftmain.v fftstage.v qtrstage.v laststage.v hwbfly.v butterfly.v \
        longbimpy.v bimpy.v bitreverse.v convround.v tb_fft.v && vvp sim.vvp          # 10 s

Odin III: `odin3 -p "read_verilog <the 10 files>; proc; opt; lower; sim_tb --top tb_fft --max-time 400000 --out run.txt tb_fft_odin.v"`
run in the same directory. The Odin version avoids a part-select of a memory word (`exp_m[idx][41:21]`),
which sim_tb refuses.
