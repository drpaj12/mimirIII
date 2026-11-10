"""Run a (re)tiled transmission through Gabe's Python interpreter and compare with the golden.

usage: check_retile.py <usstpu_root> <mnist_raw_dir> <transmission.bin> [n_images]
"""
import sys, os, tempfile, pathlib
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from golden.lenet_int8 import Net
from golden.mnist import load_idx
from golden.tpu_bin import parse

root, raw, tx = sys.argv[1], sys.argv[2], sys.argv[3]
n_img = int(sys.argv[4]) if len(sys.argv) > 4 else 5
X, y = load_idx(f"{raw}/t10k-images-idx3-ubyte", f"{raw}/t10k-labels-idx1-ubyte")
net = Net(f"{root}/Benchmarks/LeNet_5_TRANSMISSION.bin", 0.02268019)
sys.path[:0] = [f"{root}/System/Assembler/Interpreter", f"{root}/System/Assembler"]
import Interpreter as I
mem, instrs = parse(tx)
with tempfile.TemporaryDirectory() as td:
    mp, pp = f"{td}/MEM.bin", f"{td}/PROGRAM.bin"
    with open(mp, "wb") as f:
        for a, b in mem:
            f.write(bytes([0x4D]) + a.to_bytes(3, "little") + len(b).to_bytes(2, "little") + b.tobytes())
    with open(pp, "wb") as f:
        for x in instrs:
            f.write(bytes([0x50]) + x.to_bytes(16, "little"))
    prog = I.parse_program(pathlib.Path(pp))
    bad = 0
    for i in range(n_img):
        t = I.TPU()
        t.load_weights(pathlib.Path(mp))
        t.load_input(net.quant_image(X[i]))
        t.run(prog)
        got = [t.io[d] for d in range(10)]
        bad += got != [int(v) for v in net.scores(X[i])]
print(f"{tx}: {len(instrs)} instrs, {n_img - bad}/{n_img} bit-exact vs golden")
sys.exit(1 if bad else 0)
