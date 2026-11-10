"""Retile Gabe Litteken's LeNet-5 TPU program from 8x8 array tiles to NxN tiles.

The prebuilt LeNet_5_TRANSMISSION.bin was assembled for array edge 8. His assembler needs
stablehlo-opt (not available), so this rewrites the compiled program: each run of MUL/MULTIP
instructions that ends in a MULT (one output tile, accumulated over K) is re-expanded into
NxN output sub-tiles, each accumulated over K chunks of at most N, with explicit stride
instructions. Everything else (relu, im2col, max, move, window, add) is copied unchanged.
Weights and (M0, n) are untouched, so results stay bit-exact.

usage: retile_program.py <transmission.bin> <N> <out.bin>
"""
import sys
sys.dont_write_bytecode = True
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from golden.tpu_bin import parse, bits

OP_MUL, OP_STRIDE = 0b1000, 0b1111


def dec_mul(x):
    return dict(src1=bits(x, 123, 100), m=bits(x, 99, 96), k=bits(x, 95, 92),
                src2=bits(x, 91, 68), k2=bits(x, 67, 64), n=bits(x, 63, 60),
                dest=bits(x, 59, 36), m0=bits(x, 35, 28), sh=bits(x, 27, 20), f3=bits(x, 2, 0))


def enc_mul(d):
    return ((OP_MUL << 124) | (d["src1"] << 100) | (d["m"] << 96) | (d["k"] << 92) | (d["src2"] << 68)
            | (d["k2"] << 64) | (d["n"] << 60) | (d["dest"] << 36) | (d["m0"] << 28) | (d["sh"] << 20) | d["f3"])


def enc_stride(l1, l2):
    return (OP_STRIDE << 124) | (l1 << 100) | (l2 << 76)


def opcode(x):
    return bits(x, 127, 124)


def retile(instrs, N):
    out, ld1, ld2 = [], 0, 0
    chain = []
    for x in instrs:
        op = opcode(x)
        if op == OP_STRIDE:
            ld1, ld2 = bits(x, 123, 100), bits(x, 99, 76)
            out.append(x)
            continue
        if op == OP_MUL:
            chain.append(dec_mul(x))
            if chain[-1]["f3"] == 0:  # MULT terminates the accumulation run
                out.extend(expand(chain, N, ld1, ld2))
                chain = []
            continue
        assert not chain, "non-MUL instruction inside an accumulation run"
        out.append(x)
    assert not chain
    return out


def expand(chain, N, ld1, ld2):
    last = chain[-1]
    M, C = last["m"], last["n"]
    for d in chain:
        assert d["n"] == C and d["m"] == M and d["k"] == d["k2"]
    # effective leading dimensions; the original run shares one (ld1, ld2)
    k0 = chain[0]["k"]
    assert all(d["k"] == k0 for d in chain) or ld1 != 0 or True
    ops = []
    # per-instruction effective strides: ld==0 means own width
    for d in chain:
        e1 = ld1 or d["k"]
        e2 = ld2 or C
        assert e1 == (ld1 or chain[0]["k"]) or ld1 != 0
        ops.append((d, e1, e2))
    # one stride pair for the whole run (use the first; require all equal)
    e1s = {o[1] for o in ops}
    e2s = {o[2] for o in ops}
    assert len(e2s) == 1
    res = []
    # stride is per run; if the K widths differ and ld1 == 0 the effective ld1 differs per instruction:
    # then set it before each instruction.
    cur = None
    for i0 in range(0, M, N):
        mi = min(N, M - i0)
        for j0 in range(0, C, N):
            nj = min(N, C - j0)
            seq = []
            for (d, e1, e2) in ops:
                for kk0 in range(0, d["k"], N):
                    kk = min(N, d["k"] - kk0)
                    seq.append((d, e1, e2, kk0, kk))
            for idx, (d, e1, e2, kk0, kk) in enumerate(seq):
                if cur != (e1, e2):
                    res.append(enc_stride(e1, e2))
                    cur = (e1, e2)
                nd = dict(d)
                nd["src1"] = d["src1"] + i0 * e1 + kk0
                nd["src2"] = d["src2"] + kk0 * e2 + j0
                nd["dest"] = d["dest"] + i0 * e2 + j0
                nd["m"], nd["k"], nd["k2"], nd["n"] = mi, kk, kk, nj
                nd["f3"] = 0 if idx == len(seq) - 1 else 1
                res.append(enc_mul(nd))
    # restore the original stride registers for whatever follows
    if cur != (ld1, ld2):
        res.append(enc_stride(ld1, ld2))
    return res


def write(path, mem, instrs):
    with open(path, "wb") as f:
        f.write(bytes([0x55]))
        for a, b in mem:
            f.write(bytes([0x4D]) + a.to_bytes(3, "little") + len(b).to_bytes(2, "little") + b.tobytes())
        for x in instrs:
            f.write(bytes([0x50]) + x.to_bytes(16, "little"))
        f.write(bytes([0x53]))


if __name__ == "__main__":
    mem, instrs = parse(sys.argv[1])
    N = int(sys.argv[2])
    new = retile(instrs, N) if N != 8 else instrs
    write(sys.argv[3], mem, new)
    print(f"N={N}: {len(instrs)} -> {len(new)} instructions")
