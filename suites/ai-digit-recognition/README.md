# ai-mnist (working name Huginn III): P0 contract

One application (MNIST, int8 LeNet-5), many Verilog implementations, two targets (VTR k6 and Cyclone V via Odin III LPM).
See `docs/INTERFACE.md`, `docs/GOLDEN.md`. No third-party files or MNIST data in this repo.

    python3 -I tools/check_golden.py <usstpu_root> <mnist_raw_dir>          # golden vs Gabe's interpreter and emulator
    python3 -I tools/gen_vectors.py <usstpu_root> <mnist_raw_dir> <out> 100  # quick tier
    python3 -I tools/gen_oracle.py <vec_dir> oracle.v                        # lookup DUT, passes its tier
    python3 -I score/vtr_leg.py --design D --src d.v --vec <vec_dir> --work <w> --out vtr.jsonl
    python3 -I score/lpm_leg.py --design D --src d.v --vec <vec_dir> --work <w> --out lpm.jsonl

Trivial DUTs: `rtl/trivial_const.v` (fixed class, must FAIL), generated oracle (must PASS).
