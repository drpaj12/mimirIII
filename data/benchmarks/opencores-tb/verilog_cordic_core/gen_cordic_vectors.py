"""Golden vectors for the OpenCores verilog_cordic_core testbench (default configuration).

tb_origin: mimir-written. Default configuration of cordic.v: RADIAN_16, PIPELINE, ROTATE, 16 bit
+ sign, angles in U(1,15) radians (code = radians * 2**15), CORDIC_1 = 19896 as x input.
Each angle code gives the exact sin and cos of the angle that code represents (code / 2**15),
scaled by 2**15 and rounded: the reference is math.sin / math.cos, not the table in the upstream tb.

    python3 gen_cordic_vectors.py <output-dir>

Writes angle.hex (5 hex digits per angle) and exp.hex (sin then cos, 17 bit two's complement, one
line `sssss ccccc`). Deterministic: 91 angles at whole degrees, then 109 angles from a fixed LCG.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

SCALE = 1 << 15
M64 = (1 << 64) - 1
LCG_A = 6364136223846793005
LCG_C = 1442695040888963407
MAX_CODE = 51471  # 90 degrees, the largest code the upstream testbench uses


def angle_codes() -> list[int]:
    """91 whole-degree codes (round(deg * pi / 180 * 2**15)), then 109 LCG codes in 0..MAX_CODE."""
    codes = [round(d * math.pi / 180 * SCALE) for d in range(91)]
    state = 424242
    for _ in range(109):
        state = (state * LCG_A + LCG_C) & M64
        codes.append((state >> 33) % (MAX_CODE + 1))
    return codes


def expected(code: int) -> tuple[int, int]:
    """(sin, cos) of the angle `code` represents, scaled by 2**15 and rounded."""
    a = code / SCALE
    return round(math.sin(a) * SCALE), round(math.cos(a) * SCALE)


def build() -> dict[str, str]:
    codes = angle_codes()
    mask = (1 << 17) - 1
    angle = "".join(f"{c:05x}\n" for c in codes)
    exp = "".join(f"{s & mask:05x}{c & mask:05x}\n" for s, c in map(expected, codes))
    return {"angle.hex": angle, "exp.hex": exp}


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    out = Path(argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, text in build().items():
        (out / name).write_text(text, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
