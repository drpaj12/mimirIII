"""Retile Gabe Litteken's LeNet-5 TPU program from 8x8 array tiles to NxN tiles.

The prebuilt LeNet_5_TRANSMISSION.bin was assembled for array edge 8. His assembler needs
stablehlo-opt (not available), so this rewrites the compiled program: each run of MUL/MULTIP
instructions that ends in a MULT (one output tile, accumulated over K) is re-expanded into
NxN output sub-tiles, each accumulated over K chunks of at most N, with explicit stride
instructions. Everything else (relu, im2col, max, move, window, add) is copied unchanged.
Weights and (M0, n) are untouched, so results stay bit-exact. The 4-bit dimension fields of the
ISA limit N to 15.

usage: retile_program.py <transmission.bin> <N> <out.bin>
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
if HERE not in sys.path:
    sys.path.insert(0, HERE)
tpu_bin = importlib.import_module("golden.tpu_bin")
bits = tpu_bin.bits

OP_MUL, OP_STRIDE = 0b1000, 0b1111
MULT, MULTIP = 0, 1


def dec_mul(x):
    return {"src1": bits(x, 123, 100), "m": bits(x, 99, 96), "k": bits(x, 95, 92),
            "src2": bits(x, 91, 68), "k2": bits(x, 67, 64), "n": bits(x, 63, 60),
            "dest": bits(x, 59, 36), "m0": bits(x, 35, 28), "sh": bits(x, 27, 20),
            "f3": bits(x, 2, 0)}


def enc_mul(d):
    return ((OP_MUL << 124) | (d["src1"] << 100) | (d["m"] << 96) | (d["k"] << 92)
            | (d["src2"] << 68) | (d["k2"] << 64) | (d["n"] << 60) | (d["dest"] << 36)
            | (d["m0"] << 28) | (d["sh"] << 20) | d["f3"])


def enc_stride(ld1, ld2):
    return (OP_STRIDE << 124) | (ld1 << 100) | (ld2 << 76)


def opcode(x):
    return bits(x, 127, 124)


def retile(instrs, n):
    """The program with every MUL run re-expanded for an n x n array."""
    out, ld1, ld2, chain = [], 0, 0, []
    for x in instrs:
        op = opcode(x)
        if op == OP_STRIDE:
            ld1, ld2 = bits(x, 123, 100), bits(x, 99, 76)
            out.append(x)
        elif op == OP_MUL:
            chain.append(dec_mul(x))
            if chain[-1]["f3"] == MULT:  # MULT ends the accumulation run
                out.extend(expand(chain, n, ld1, ld2))
                chain = []
        else:
            assert not chain, "non-MUL instruction inside an accumulation run"
            out.append(x)
    assert not chain
    return out


def expand(chain, n, ld1, ld2):
    """One MUL run -> n x n output tiles, each accumulated over K chunks of at most n."""
    rows, cols = chain[-1]["m"], chain[-1]["n"]
    for d in chain:
        assert d["n"] == cols and d["m"] == rows and d["k"] == d["k2"]
    res, cur = [], None
    for i0 in range(0, rows, n):
        for j0 in range(0, cols, n):
            seq = [(d, k0) for d in chain for k0 in range(0, d["k"], n)]
            for idx, (d, k0) in enumerate(seq):
                e1, e2 = ld1 or d["k"], ld2 or cols  # effective row strides (0 = own width)
                if cur != (e1, e2):
                    res.append(enc_stride(e1, e2))
                    cur = (e1, e2)
                nd = dict(d)
                nd["src1"] = d["src1"] + i0 * e1 + k0
                nd["src2"] = d["src2"] + k0 * e2 + j0
                nd["dest"] = d["dest"] + i0 * e2 + j0
                nd["m"], nd["n"] = min(n, rows - i0), min(n, cols - j0)
                nd["k"] = nd["k2"] = min(n, d["k"] - k0)
                nd["f3"] = MULT if idx == len(seq) - 1 else MULTIP
                res.append(enc_mul(nd))
    if cur != (ld1, ld2):  # restore the stride registers the original program expects
        res.append(enc_stride(ld1, ld2))
    return res


def write(path, mem, instrs):
    with open(path, "wb") as f:
        f.write(bytes([0x55]))
        for a, b in mem:
            f.write(bytes([0x4D]) + a.to_bytes(3, "little") + len(b).to_bytes(2, "little")
                    + b.tobytes())
        for x in instrs:
            f.write(bytes([0x50]) + x.to_bytes(16, "little"))
        f.write(bytes([0x53]))


if __name__ == "__main__":
    mem_blocks, program = tpu_bin.parse(sys.argv[1])
    size = int(sys.argv[2])
    new = retile(program, size) if size != 8 else program
    write(sys.argv[3], mem_blocks, new)
    print(f"N={size}: {len(program)} -> {len(new)} instructions")
