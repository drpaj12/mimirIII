#!/usr/bin/env python3
"""usage: mkrand.py <seed> : a 64 KiB RAM image holding a random straight-line Z80 program.

Address 0: register-initialising prologue; 0x38: IM1 interrupt handler; 0x66: NMI handler;
0x80..: about 12000 random instructions drawn from templates (register loads, 8/16-bit ALU,
rotates, CB bit ops, IX/IY with displacement, exchanges, block ops with DE/HL pinned, RLD/RRD,
IN/OUT (C), stores into 0x8000-0x83FF only), then JP 0x80. Random instruction choice, not random
bytes: every register and flag is defined before use and no jump leaves the program.
"""

import random
import sys

rng = random.Random(int(sys.argv[1]))
mem = [0x00] * 0x10000


def put(addr: int, data: list[int]) -> None:
    mem[addr : addr + len(data)] = data


put(
    0,
    [
        0x31,
        0x00,
        0xC0,
        0xAF,
        0x01,
        0x34,
        0x12,
        0x11,
        0x78,
        0x56,
        0x21,
        0xBC,
        0x9A,
        0x08,
        0xAF,
        0xD9,
        0x01,
        0x11,
        0x22,
        0x11,
        0x33,
        0x44,
        0x21,
        0x55,
        0x66,
        0xD9,
        0xDD,
        0x21,
        0x00,
        0x80,
        0xFD,
        0x21,
        0x00,
        0x88,
        0x3E,
        0x00,
        0xED,
        0x47,
        0xED,
        0x56,
        0xFB,
        0xC3,
        0x80,
        0x00,
    ],
)
# IM1 handler: push af,bc; out 'I'; pop; ei; reti.  NMI handler: out 'N'; retn
put(0x38, [0xF5, 0xC5, 0x3E, 0x49, 0x01, 0x00, 0x08, 0xED, 0x79, 0xC1, 0xF1, 0xFB, 0xED, 0x4D])
put(0x66, [0xF5, 0x3E, 0x4E, 0xD3, 0x08, 0xF1, 0xED, 0x45])

REGS = [0, 1, 2, 3, 4, 5, 7]  # B C D E H L A, no (HL)
ALU_MEM = [0x86, 0x8E, 0x96, 0x9E, 0xA6, 0xAE, 0xB6, 0xBE, 0x34, 0x35]
SINGLE = [
    0x03,
    0x13,
    0x23,
    0x0B,
    0x1B,
    0x2B,
    0x09,
    0x19,
    0x29,
    0x39,
    0x07,
    0x0F,
    0x17,
    0x1F,
    0x27,
    0x2F,
    0x37,
    0x3F,
    0xEB,
    0xD9,
    0x08,
    0x00,
]
ED_ALU = [0x44, 0x4A, 0x5A, 0x6A, 0x42, 0x52, 0x62]
IDX_CB = [0x06, 0x0E, 0x16, 0x1E, 0x26, 0x2E, 0x36, 0x3E]
IDX_REG = [0x44, 0x45, 0x4C, 0x4D, 0x7C, 0x7D, 0x84, 0x85, 0x24, 0x2C]


def reg() -> int:
    return rng.choice(REGS)


def idx() -> int:
    return rng.choice([0xDD, 0xFD])


def disp() -> int:
    return rng.randrange(0, 0x7F)


def addr() -> list[int]:
    return [rng.randrange(256), 0x81 + rng.randrange(3)]


def idx_load_store() -> list[int]:
    if rng.random() < 0.5:
        return [idx(), 0x40 | reg() << 3 | 6, disp()]
    return [idx(), 0x70 | reg(), disp()]


def idx_cb() -> list[int]:
    prefix, offset = idx(), disp()
    ops = [*IDX_CB]
    ops += [base | rng.randrange(8) << 3 for base in (0x46, 0x86, 0xC6)]
    return [prefix, 0xCB, offset, rng.choice(ops)]


def push_pop() -> list[int]:
    return [0xC5, 0xD1] if rng.random() < 0.5 else [0xF5, 0xE1]


def abs_a(op_a: int, op_b: int) -> list[int]:
    return [op_a, *addr()] if rng.random() < 0.5 else [op_b, *addr()]


def ed_store_load() -> list[int]:
    op = rng.choice([0x43, 0x53, 0x63]) if rng.random() < 0.5 else rng.choice([0x4B, 0x5B, 0x6B])
    return [0xED, op, *addr()]


def template() -> list[int]:
    k = rng.randrange(26)
    table = {
        0: lambda: [0x40 | reg() << 3 | reg()],
        1: lambda: [0x06 | reg() << 3, rng.randrange(256)],
        2: lambda: [0x80 | rng.randrange(8) << 3 | reg()],
        3: lambda: [0xC6 | rng.randrange(8) << 3, rng.randrange(256)],
        4: lambda: [0x04 | reg() << 3 | rng.randrange(2)],
        5: lambda: [rng.choice(SINGLE)],
        6: lambda: [0xED, rng.choice(ED_ALU)],
        7: lambda: [0xCB, rng.randrange(256) & ~7 | reg()],
        8: lambda: [rng.choice([0x01, 0x11, 0x21]), rng.randrange(256), rng.randrange(256)],
        9: idx_load_store,
        10: lambda: [idx(), rng.choice(ALU_MEM), disp()],
        11: idx_cb,
        12: lambda: [idx(), rng.choice([0x09, 0x19, 0x29, 0x23, 0x2B])],
        13: push_pop,
        14: lambda: abs_a(0x32, 0x3A),
        15: lambda: abs_a(0x22, 0x2A),
        16: ed_store_load,
        17: lambda: [0x11, 0x00, 0x82, 0xED, rng.choice([0xA0, 0xA8])],
        18: lambda: [0xED, rng.choice([0xA1, 0xA9])],
        19: lambda: [0x21, 0x00, 0x83, 0xED, rng.choice([0x6F, 0x67])],
        20: lambda: [0xED, 0x40 | reg() << 3],
        21: lambda: [0xED, 0x41 | reg() << 3],
        22: lambda: [idx(), rng.choice(IDX_REG)],
        23: lambda: [0x3E, rng.randrange(256), 0xED, 0x47],
        24: lambda: [0x00],
    }
    if k in table:
        return table[k]()
    return [0xED, 0x57 if rng.random() < 0.5 else 0x5F]


a = 0x80
for _ in range(12000):
    ins = template()
    if a + len(ins) > 0x7000:
        break
    put(a, ins)
    a += len(ins)
put(a, [0xC3, 0x80, 0x00])
for i in range(0, 0x10000, 16):
    print(" ".join(f"{x:02X}" for x in mem[i : i + 16]) + " ")
