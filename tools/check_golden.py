"""Accuracy of our reference; cross-check vs Gabe's code (imported by path, read-only).

usage: check_golden.py <usstpu_root> <mnist_raw_dir> [s_in] [n_interp]
"""
import sys, os
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from golden.lenet_int8 import Net
from golden.mnist import load_idx

root, raw = sys.argv[1], sys.argv[2]
s_in = float(sys.argv[3]) if len(sys.argv) > 3 else 0.02268019
n_interp = int(sys.argv[4]) if len(sys.argv) > 4 else 3
X, y = load_idx(f"{raw}/t10k-images-idx3-ubyte", f"{raw}/t10k-labels-idx1-ubyte")
net = Net(f"{root}/Benchmarks/LeNet_5_TRANSMISSION.bin", s_in)
print("M0,n per layer:", net.q)
ok = sum(net.classify(X[i])[0] == y[i] for i in range(len(X)))
print(f"ours (bin weights, s_in={s_in}): top-1 {ok}/{len(X)} = {100*ok/len(X):.2f}%")

# Gabe's TPU interpreter executing the real program of the same bin
import tempfile
from golden.tpu_bin import parse
sys.path[:0] = [f"{root}/System/Assembler/Interpreter", f"{root}/System/Assembler"]
import Interpreter as I
mem, instrs = parse(f"{root}/Benchmarks/LeNet_5_TRANSMISSION.bin")
with tempfile.TemporaryDirectory() as td:
    mp, pp = f"{td}/MEM.bin", f"{td}/PROGRAM.bin"
    with open(mp, "wb") as f:
        for a, b in mem:
            f.write(bytes([0x4D]) + a.to_bytes(3, "little") + len(b).to_bytes(2, "little") + b.tobytes())
    with open(pp, "wb") as f:
        for x in instrs:
            f.write(bytes([0x50]) + x.to_bytes(16, "little"))
    prog = I.parse_program(__import__("pathlib").Path(pp))
    bad = 0
    for i in range(n_interp):
        t = I.TPU()
        t.load_weights(__import__("pathlib").Path(mp))
        t.load_input(net.quant_image(X[i]))
        t.run(prog)
        got = [t.io[d] for d in range(10)]
        mine = [int(v) for v in net.scores(X[i])]
        bad += got != mine
        print(f"img {i}: interp {got} ours {mine} {'OK' if got == mine else 'DIFF'}")
print(f"interpreter cross-check: {n_interp - bad}/{n_interp} bit-exact")

# Gabe's Emulator on his committed npz (a DIFFERENT weight set from the bin; see docs)
import Emulator as E
npz = np.load(E._NPZ_PATH, allow_pickle=False)
qw, pairs = E._quantized_weights(npz), E._requant_pairs(npz)
s_npz = float(npz["__scales__conv1.weight"][0])
okq = okf = 0
for i in range(len(X)):
    xn = ((X[i].astype(np.float64) / 255.0 - 0.1307) / 0.3018).reshape(1, 28, 28)
    img = np.clip(np.round(xn / s_npz), -127, 127).astype(np.int8)
    okq += int(np.argmax(E.forward_int8(img, qw, pairs))) == y[i]
    if i < 2000:
        okf += int(np.argmax(E.forward_float(xn, npz, use_bias=True))) == y[i]
print(f"Gabe Emulator on npz weights (S_in={s_npz:.8f}): int8 {okq}/{len(X)} = {100*okq/len(X):.2f}%; "
      f"float+bias first 2000: {100*okf/2000:.2f}%")
print("npz M0,n:", pairs)
