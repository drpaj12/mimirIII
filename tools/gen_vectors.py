"""Write hex vector files for a tier from MNIST t10k + the golden.

usage: gen_vectors.py <usstpu_root> <mnist_raw_dir> <out_dir> <n_images> [s_in]
Files (all $readmemh, one value per line, int8 as two hex digits):
  vec_images.hex   n*784 bytes, quantised input pixels, row-major
  vec_labels.hex   n digits (true MNIST label)
  vec_gclass.hex   n digits (golden class)
  vec_gscores.hex  n*10 bytes (golden int8 scores)
  vec_meta.hex     [0]=n, [1]=per-image cycle timeout (hex)
"""
import sys, os
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from golden.lenet_int8 import Net
from golden.mnist import load_idx

root, raw, out, n = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
s_in = float(sys.argv[5]) if len(sys.argv) > 5 else 0.02268019
os.makedirs(out, exist_ok=True)
X, y = load_idx(f"{raw}/t10k-images-idx3-ubyte", f"{raw}/t10k-labels-idx1-ubyte")
net = Net(f"{root}/Benchmarks/LeNet_5_TRANSMISSION.bin", s_in)
fi, fl, fc, fs = (open(f"{out}/{k}", "w") for k in
                  ("vec_images.hex", "vec_labels.hex", "vec_gclass.hex", "vec_gscores.hex"))
hx = lambda v: f"{int(v) & 0xFF:02x}\n"
ok = 0
for i in range(n):
    fi.writelines(hx(v) for v in net.quant_image(X[i]).reshape(-1))
    c, s = net.classify(X[i])
    fl.write(f"{int(y[i]):x}\n"); fc.write(f"{c:x}\n"); fs.writelines(hx(v) for v in s)
    ok += c == y[i]
for f in (fi, fl, fc, fs):
    f.close()
open(f"{out}/vec_meta.hex", "w").write(f"{n:x}\n{2000000:x}\n")
print(f"{out}: n={n} golden top-1 vs label {ok}/{n}")
