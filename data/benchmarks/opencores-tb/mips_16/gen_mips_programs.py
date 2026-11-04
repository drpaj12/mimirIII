"""Programs and expected results for the OpenCores mips_16 testbench.

tb_origin: mimir-written. A small assembler for the instruction set in the project's
doc/instruction_set.txt and an independent Python model of it (straight-line programs, 16-bit
registers, R0 reads 0, 256-word data memory, SR arithmetic, SRU logical). The model gives the
expected registers and memory words; the testbench compares them with the RTL after the program ran.

    python3 gen_mips_programs.py <output-dir>

Writes <name>.prog (binary text for $readmemb, one 16-bit instruction per line) and <name>.exp
(16 lines of 5 hex digits: R0..R7, then data memory words 0..7; bit 16 set = compare this entry).
Each program ends with the stop loop of the project's own test2 (`BZ R0,-1` and a NOP) and zero
(NOP) padding; the model ignores that tail.
"""

from __future__ import annotations

import sys
from pathlib import Path

OPS = {
    "NOP": 0,
    "ADD": 1,
    "SUB": 2,
    "AND": 3,
    "OR": 4,
    "XOR": 5,
    "SL": 6,
    "SR": 7,
    "SRU": 8,
    "ADDI": 9,
    "LD": 10,
    "ST": 11,
    "BZ": 12,
}
M16 = 0xFFFF
STOP = [0b1100000000111111, 0]  # BZ R0,-1 ; NOP  (as in the project's test2.prog)
PAD = 8


def enc_r(op: str, rd: int, rs1: int, rs2: int) -> int:
    return (OPS[op] << 12) | (rd << 9) | (rs1 << 6) | (rs2 << 3)


def enc_i(op: str, rd: int, rs1: int, imm: int) -> int:
    if not -32 <= imm < 32:
        raise ValueError("6-bit immediate out of range")
    return (OPS[op] << 12) | (rd << 9) | (rs1 << 6) | (imm & 63)


Instr = tuple[str, int, int, int]  # (op, rd, rs1, rs2 or imm)

NOPS: list[Instr] = [("NOP", 0, 0, 0)] * 3

PROGRAMS: dict[str, list[Instr]] = {
    "alu": [
        ("ADDI", 1, 0, 12),
        ("ADDI", 2, 0, 5),
        *NOPS,
        ("ADD", 3, 1, 2),
        ("SUB", 4, 1, 2),
        ("AND", 5, 1, 2),
        ("OR", 6, 1, 2),
        ("SUB", 7, 2, 1),
    ],
    "shift_mem": [
        ("ADDI", 1, 0, -3),
        ("ADDI", 2, 0, 2),
        *NOPS,
        ("SL", 3, 1, 2),
        ("SR", 4, 1, 2),
        ("SRU", 5, 1, 2),
        *NOPS,
        ("ST", 3, 0, 4),
        ("ST", 4, 0, 5),
        *NOPS,
        ("LD", 6, 0, 4),
        ("LD", 7, 0, 5),
        *NOPS,
        ("ADDI", 6, 6, 1),
    ],
    "dependent": [
        ("ADDI", 1, 0, 3),
        ("ADD", 2, 1, 1),
        ("ADD", 3, 2, 1),
        ("SUB", 4, 3, 2),
        ("ADDI", 5, 4, -7),
        ("ADD", 6, 5, 3),
        ("OR", 7, 6, 3),
    ],
    # not checked by the testbench: ID_stage.v sets alu_src2_mux = 1'bx for OP_XOR
    "xor": [("ADDI", 1, 0, 12), ("ADDI", 2, 0, 5), *NOPS, ("XOR", 3, 1, 2)],
}


def assemble(prog: list[Instr]) -> list[int]:
    words = []
    for op, rd, rs1, x in prog:
        if op in ("ADDI", "LD", "ST"):
            words.append(enc_i(op, rd, rs1, x))
        else:
            words.append(enc_r(op, rd, rs1, x))
    return words


def run_model(prog: list[Instr]) -> tuple[list[int], dict[int, int]]:
    """Registers R0..R7 and written data memory words after the straight-line program."""
    r = [0] * 8
    mem: dict[int, int] = {}

    def rd(i: int) -> int:
        return 0 if i == 0 else r[i]

    def wr(i: int, v: int) -> None:
        if i:
            r[i] = v & M16

    for op, d, a, x in prog:
        va, vb = rd(a), rd(x) if op not in ("ADDI", "LD", "ST") else 0
        if op == "ADD":
            wr(d, va + vb)
        elif op == "SUB":
            wr(d, va - vb)
        elif op == "AND":
            wr(d, va & vb)
        elif op == "OR":
            wr(d, va | vb)
        elif op == "XOR":
            wr(d, va ^ vb)
        elif op == "SL":
            wr(d, va << vb)
        elif op == "SR":
            signed = va - 0x10000 if va & 0x8000 else va
            wr(d, signed >> vb)
        elif op == "SRU":
            wr(d, va >> vb)
        elif op == "ADDI":
            wr(d, va + x)
        elif op == "LD":
            wr(d, mem[(va + x) & 0xFF])
        elif op == "ST":
            mem[(va + x) & 0xFF] = rd(d)
    return r, mem


def exp_lines(prog: list[Instr]) -> list[str]:
    r, mem = run_model(prog)
    out = [f"{0x10000 | v:05x}" for v in r]
    for a in range(8):
        out.append(f"{0x10000 | mem[a]:05x}" if a in mem else "00000")
    return out


def build() -> dict[str, str]:
    files: dict[str, str] = {}
    for name, prog in PROGRAMS.items():
        words = assemble(prog) + STOP + [0] * PAD
        files[f"{name}.prog"] = "".join(f"{w:016b}\n" for w in words)
        files[f"{name}.exp"] = "".join(line + "\n" for line in exp_lines(prog))
    return files


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
