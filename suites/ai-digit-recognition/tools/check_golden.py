"""Accuracy of our reference; cross-check vs Gabe's code (imported by path, read-only).

usage: check_golden.py <usstpu_root> <mnist_raw_dir> [s_in] [n_interp]
"""
import importlib
import os
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def interpreter_check(root, net, x, n_interp):
    check = importlib.import_module("check_retile")
    tpu_bin = importlib.import_module("golden.tpu_bin")
    sys.path[:0] = [f"{root}/System/Assembler/Interpreter", f"{root}/System/Assembler"]
    interp = importlib.import_module("Interpreter")
    mem, instrs = tpu_bin.parse(f"{root}/Benchmarks/LeNet_5_TRANSMISSION.bin")
    bad = 0
    with tempfile.TemporaryDirectory() as td:
        mp, pp = check.write_inputs(td, mem, instrs)
        prog = interp.parse_program(pp)
        for i in range(n_interp):
            t = interp.TPU()
            t.load_weights(mp)
            t.load_input(net.quant_image(x[i]))
            t.run(prog)
            got = [t.io[d] for d in range(10)]
            mine = [int(v) for v in net.scores(x[i])]
            bad += got != mine
            print(f"img {i}: interp {got} ours {mine} {'OK' if got == mine else 'DIFF'}")
    print(f"interpreter cross-check: {n_interp - bad}/{n_interp} bit-exact")


def emulator_check(x, y):
    emu = importlib.import_module("Emulator")
    npz = np.load(emu._NPZ_PATH, allow_pickle=False)
    qw, pairs = emu._quantized_weights(npz), emu._requant_pairs(npz)
    s_npz = float(npz["__scales__conv1.weight"][0])
    okq = okf = 0
    for i in range(len(x)):
        xn = ((x[i].astype(np.float64) / 255.0 - 0.1307) / 0.3018).reshape(1, 28, 28)
        img = np.clip(np.round(xn / s_npz), -127, 127).astype(np.int8)
        okq += int(np.argmax(emu.forward_int8(img, qw, pairs))) == y[i]
        if i < 2000:
            okf += int(np.argmax(emu.forward_float(xn, npz, use_bias=True))) == y[i]
    print(f"Gabe Emulator on npz weights (S_in={s_npz:.8f}): int8 {okq}/{len(x)} = "
          f"{100 * okq / len(x):.2f}%; float+bias first 2000: {100 * okf / 2000:.2f}%")
    print("npz M0,n:", pairs)


def main(argv):
    sys.dont_write_bytecode = True
    sys.path.insert(0, HERE)
    sys.path.insert(0, os.path.join(HERE, "tools"))
    net_mod = importlib.import_module("golden.lenet_int8")
    mnist = importlib.import_module("golden.mnist")
    root, raw = argv[0], argv[1]
    s_in = float(argv[2]) if len(argv) > 2 else 0.02268019
    n_interp = int(argv[3]) if len(argv) > 3 else 3
    x, y = mnist.load_idx(f"{raw}/t10k-images-idx3-ubyte", f"{raw}/t10k-labels-idx1-ubyte")
    net = net_mod.Net(f"{root}/Benchmarks/LeNet_5_TRANSMISSION.bin", s_in)
    print("M0,n per layer:", net.q)
    ok = sum(net.classify(x[i])[0] == y[i] for i in range(len(x)))
    print(f"ours (bin weights, s_in={s_in}): top-1 {ok}/{len(x)} = {100 * ok / len(x):.2f}%")
    interpreter_check(root, net, x, n_interp)
    emulator_check(x, y)


if __name__ == "__main__":
    main(sys.argv[1:])
