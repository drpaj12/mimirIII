"""Write hex vector files for a tier from MNIST t10k + the golden.

usage: gen_vectors.py <usstpu_root> <mnist_raw_dir> <out_dir> <n_images> [s_in]
Files (all $readmemh, one value per line, int8 as two hex digits):
  vec_images.hex   n*784 bytes, quantised input pixels, row-major
  vec_labels.hex   n digits (true MNIST label)
  vec_gclass.hex   n digits (golden class)
  vec_gscores.hex  n*10 bytes (golden int8 scores)
  vec_meta.hex     [0]=n, [1]=per-image cycle timeout (hex)
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def hx(v):
    return f"{int(v) & 0xFF:02x}\n"


def main(argv):
    sys.dont_write_bytecode = True
    sys.path.insert(0, HERE)
    net_mod = importlib.import_module("golden.lenet_int8")
    mnist = importlib.import_module("golden.mnist")
    root, raw, out, n = argv[0], argv[1], argv[2], int(argv[3])
    s_in = float(argv[4]) if len(argv) > 4 else 0.02268019
    os.makedirs(out, exist_ok=True)
    x, y = mnist.load_idx(f"{raw}/t10k-images-idx3-ubyte", f"{raw}/t10k-labels-idx1-ubyte")
    net = net_mod.Net(f"{root}/Benchmarks/LeNet_5_TRANSMISSION.bin", s_in)
    ok = 0
    with (open(f"{out}/vec_images.hex", "w") as fi, open(f"{out}/vec_labels.hex", "w") as fl,
          open(f"{out}/vec_gclass.hex", "w") as fc, open(f"{out}/vec_gscores.hex", "w") as fs):
        for i in range(n):
            fi.writelines(hx(v) for v in net.quant_image(x[i]).reshape(-1))
            c, s = net.classify(x[i])
            fl.write(f"{int(y[i]):x}\n")
            fc.write(f"{c:x}\n")
            fs.writelines(hx(v) for v in s)
            ok += c == y[i]
    with open(f"{out}/vec_meta.hex", "w") as f:
        f.write(f"{n:x}\n{2000000:x}\n")
    print(f"{out}: n={n} golden top-1 vs label {ok}/{n}")


if __name__ == "__main__":
    main(sys.argv[1:])
