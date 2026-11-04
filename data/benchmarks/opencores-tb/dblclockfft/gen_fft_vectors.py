"""Twiddle files and golden vectors for the OpenCores dblclockfft testbench.

tb_origin: mimir-written. Input frames come from a fixed LCG (no random module); the expected
output of every frame is the DFT of the input, computed with numpy, times the core's scale factor
2**-(LGWIDTH - (OWIDTH - IWIDTH)) = 2**-5 (derived from the widths in rtl/fftmain.v: the core
gains OWIDTH - IWIDTH = 6 bits while an unscaled 2**LGWIDTH-point sum would need 11), rounded to
the nearest integer. The twiddle files cmem_<N>.hex are a port of gen_coeffs() in the project's
sw/fftlib.cpp; the widths come from the stage instances in fftmain.v.

    python3 gen_fft_vectors.py <path-to-dblclockfft/rtl/fftmain.v> <output-dir>

numpy is needed (the `analysis` extra).
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path

M64 = (1 << 64) - 1
LCG_A = 6364136223846793005
LCG_C = 1442695040888963407
FRAMES = 6


def parse_core(fftmain: str) -> tuple[int, int, int, list[tuple[int, int]]]:
    """(IWIDTH, OWIDTH, LGWIDTH, [(stage size, coefficient bits), ...]) from fftmain.v."""
    m = re.search(r"localparam\s+IWIDTH=(\d+),\s*OWIDTH=(\d+),\s*LGWIDTH=(\d+);", fftmain)
    if m is None:
        raise ValueError("IWIDTH/OWIDTH/LGWIDTH not found")
    iw, ow, lg = (int(g) for g in m.groups())
    stages: list[tuple[int, int]] = []
    for sm in re.finditer(r"fftstage\s*#\(([^,]+),([^,]+),[^)]*?\"cmem_(\d+)\.hex\"\)", fftmain):
        expr = sm.group(2).strip()
        cw = iw + int(expr.split("+")[1]) if expr.startswith("IWIDTH+") else int(expr)
        stages.append((int(sm.group(3)), cw))
    if not stages:
        raise ValueError("no fftstage instances found")
    return iw, ow, lg, stages


def llround(x: float) -> int:
    """C llround: halfway cases away from zero."""
    return int(math.floor(abs(x) + 0.5)) * (1 if x >= 0 else -1)


def coeff_lines(stage: int, cbits: int) -> list[str]:
    """Port of gen_coeffs(stage, cbits, nwide=1, offset=0, inverse=false) of sw/fftlib.cpp."""
    width = (cbits * 2 + 3) // 4
    mask = (1 << cbits) - 1
    out = []
    for k in range(stage // 2):
        w = -2.0 * math.pi * k / stage
        ic = llround((1 << (cbits - 2)) * math.cos(w))
        is_ = llround((1 << (cbits - 2)) * math.sin(w))
        out.append(f"{(((ic & mask) << cbits) | (is_ & mask)):0{width}x}")
    return out


def lcg_stream(seed: int, count: int) -> list[int]:
    """`count` 32-bit values (upper half of the 64-bit LCG state) from a fixed seed."""
    state = seed
    out = []
    for _ in range(count):
        state = (state * LCG_A + LCG_C) & M64
        out.append(state >> 32)
    return out


def input_frames(n: int, iwidth: int) -> list[list[tuple[int, int]]]:
    """FRAMES frames of n complex integer samples (re, im) that fit `iwidth` signed bits."""
    full = (1 << (iwidth - 1)) - 1
    frames: list[list[tuple[int, int]]] = []
    zero = [(0, 0)] * n
    f = list(zero)
    f[0] = (8000, 0)
    frames.append(f)
    f = list(zero)
    f[5] = (12000, -3000)
    frames.append(f)
    frames.append([(1000, -500)] * n)
    tone = 37
    frames.append(
        [
            (
                round(10000 * math.cos(2 * math.pi * tone * i / n)),
                round(10000 * math.sin(2 * math.pi * tone * i / n)),
            )
            for i in range(n)
        ]
    )
    r = lcg_stream(20241104, 2 * n)
    frames.append(
        [(r[2 * i] % (2 * 11000 + 1) - 11000, r[2 * i + 1] % 22001 - 11000) for i in range(n)]
    )
    r = lcg_stream(77, 2 * n)
    frames.append([(r[2 * i] % 601 - 300, r[2 * i + 1] % 601 - 300) for i in range(n)])
    for fr in frames:
        for re_, im in fr:
            if abs(re_) > full or abs(im) > full:
                raise ValueError("sample out of range")
    return frames


def pack_in(re_: int, im: int, iwidth: int) -> str:
    mask = (1 << iwidth) - 1
    word = ((re_ & mask) << iwidth) | (im & mask)
    return f"{word:0{(2 * iwidth + 3) // 4}x}\n"


def expected_frames(frames: list[list[tuple[int, int]]], shift: int) -> list[list[tuple[int, int]]]:
    """DFT of each frame times 2**-shift, rounded to the nearest integer (numpy)."""
    import numpy as np

    out = []
    for fr in frames:
        x = np.array([complex(a, b) for a, b in fr])
        y = np.fft.fft(x) / (1 << shift)
        out.append([(int(np.rint(v.real)), int(np.rint(v.imag))) for v in y])
    return out


def build(fftmain: str) -> dict[str, str]:
    """All generated files as name -> text."""
    iw, ow, lg, stages = parse_core(fftmain)
    n = 1 << lg
    frames = input_frames(n, iw)
    exp = expected_frames(frames, lg - (ow - iw))
    files: dict[str, str] = {}
    for stage, cbits in stages:
        files[f"cmem_{stage}.hex"] = "".join(line + "\n" for line in coeff_lines(stage, cbits))
    files["in.hex"] = "".join(pack_in(a, b, iw) for fr in frames for a, b in fr)
    om = (1 << ow) - 1
    files["exp.hex"] = "".join(
        f"{(((a & om) << ow) | (b & om)):0{(2 * ow + 3) // 4}x}\n" for fr in exp for a, b in fr
    )
    return files


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    files = build(Path(argv[1]).read_text(encoding="utf-8", errors="replace"))
    out = Path(argv[2])
    out.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (out / name).write_text(text, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
