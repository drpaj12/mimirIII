"""Run a (re)tiled transmission through Gabe's Python interpreter and compare with the golden.

usage: check_retile.py <usstpu_root> <mnist_raw_dir> <transmission.bin> [n_images]
"""
import importlib
import os
import pathlib
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def write_inputs(td, mem, instrs):
    mp, pp = f"{td}/MEM.bin", f"{td}/PROGRAM.bin"
    with open(mp, "wb") as f:
        for a, b in mem:
            f.write(bytes([0x4D]) + a.to_bytes(3, "little") + len(b).to_bytes(2, "little")
                    + b.tobytes())
    with open(pp, "wb") as f:
        for x in instrs:
            f.write(bytes([0x50]) + x.to_bytes(16, "little"))
    return pathlib.Path(mp), pathlib.Path(pp)


def main(argv):
    sys.dont_write_bytecode = True
    sys.path.insert(0, HERE)
    net_mod = importlib.import_module("golden.lenet_int8")
    mnist = importlib.import_module("golden.mnist")
    tpu_bin = importlib.import_module("golden.tpu_bin")
    root, raw, tx = argv[0], argv[1], argv[2]
    n_img = int(argv[3]) if len(argv) > 3 else 5
    x, _ = mnist.load_idx(f"{raw}/t10k-images-idx3-ubyte", f"{raw}/t10k-labels-idx1-ubyte")
    net = net_mod.Net(f"{root}/Benchmarks/LeNet_5_TRANSMISSION.bin", 0.02268019)
    sys.path[:0] = [f"{root}/System/Assembler/Interpreter", f"{root}/System/Assembler"]
    interp = importlib.import_module("Interpreter")
    mem, instrs = tpu_bin.parse(tx)
    bad = 0
    with tempfile.TemporaryDirectory() as td:
        mp, pp = write_inputs(td, mem, instrs)
        prog = interp.parse_program(pp)
        for i in range(n_img):
            t = interp.TPU()
            t.load_weights(mp)
            t.load_input(net.quant_image(x[i]))
            t.run(prog)
            got = [t.io[d] for d in range(10)]
            bad += got != [int(v) for v in net.scores(x[i])]
    print(f"{tx}: {len(instrs)} instrs, {n_img - bad}/{n_img} bit-exact vs golden")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
