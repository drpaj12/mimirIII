"""Our own int8 LeNet-5 reference (numpy only), driven by the transmission file.

Topology and requant semantics follow the TPU ISA / Vector_Processor requant:
y = clip((M0*acc + (1<<(n-1))) >> n, -128, 127), arithmetic shift, biases dropped.
conv1(1->6,3x3) relu pool2 conv2(6->16,3x3) relu pool2 flat(400) fc1(120) relu
fc2(84) relu fc3(10). Weights are read from the MEM block (order: conv1.w, conv1.b,
conv2.w, conv2.b, fc1.w, ... contiguous from address 2); (M0, n) per layer are
read from the MUL instructions (opcode 0b1000) of the program.
"""
import numpy as np
from .tpu_bin import parse, bits

SHAPES = [("conv1", (6, 1, 3, 3), 6), ("conv2", (16, 6, 3, 3), 16),
          ("fc1", (120, 400), 120), ("fc2", (84, 120), 84), ("fc3", (10, 84), 10)]
MEAN, STD = 0.1307, 0.3018


class Net:
    def __init__(self, path, s_in):
        mem, instrs = parse(path)
        assert len(mem) == 1 and mem[0][0] == 2
        blob = mem[0][1]
        off, self.w = 0, {}
        for name, shp, nb in SHAPES:
            n = int(np.prod(shp))
            w = blob[off:off + n].astype(np.int64)
            # conv weights are the left operand [out, c*kh*kw]; fc weights are the
            # right operand of a row-vector matmul, stored [in, out] (found from the
            # program's rs2 tile addressing), so transpose to [out, in].
            self.w[name] = w.reshape(shp) if len(shp) == 4 else w.reshape(shp[1], shp[0]).T
            off += n + nb  # skip bias (dropped by the deployed program)
        assert off == len(blob)
        runs = []
        for x in instrs:
            if bits(x, 127, 124) == 0b1000:
                p = (bits(x, 35, 28), bits(x, 27, 20))
                if not runs or runs[-1] != p:
                    runs.append(p)
        assert len(runs) == 5, runs
        self.q = dict(zip([s[0] for s in SHAPES], runs))
        self.s_in = s_in

    def quant_image(self, img_u8):
        x = (img_u8.astype(np.float64) / 255.0 - MEAN) / STD
        return np.clip(np.round(x / self.s_in), -127, 127).astype(np.int64)

    @staticmethod
    def _rq(acc, m0, n):
        return np.clip((m0 * acc + ((1 << (n - 1)) if n else 0)) >> n, -128, 127)

    @staticmethod
    def _conv(x, w):
        C, H, W = x.shape
        O, _, kh, kw = w.shape
        oh, ow = H - kh + 1, W - kw + 1
        acc = np.zeros((O, oh, ow), dtype=np.int64)
        for ky in range(kh):
            for kx in range(kw):
                acc += np.tensordot(w[:, :, ky, kx], x[:, ky:ky + oh, kx:kx + ow], axes=([1], [0]))
        return acc

    @staticmethod
    def _pool(x):
        C, H, W = x.shape
        x = x[:, :H // 2 * 2, :W // 2 * 2].reshape(C, H // 2, 2, W // 2, 2)
        return x.max(axis=(2, 4))

    def scores(self, img_u8):
        x = self.quant_image(img_u8).reshape(1, 28, 28)
        for k in ("conv1", "conv2"):
            x = self._pool(np.maximum(self._rq(self._conv(x, self.w[k]), *self.q[k]), 0))
        v = x.reshape(-1)
        for k in ("fc1", "fc2", "fc3"):
            v = self._rq(self.w[k] @ v, *self.q[k])
            if k != "fc3":
                v = np.maximum(v, 0)
        return v.astype(np.int64)

    def classify(self, img_u8):
        s = self.scores(img_u8)
        return int(np.argmax(s)), s  # first max wins (numpy); ties: lowest index
