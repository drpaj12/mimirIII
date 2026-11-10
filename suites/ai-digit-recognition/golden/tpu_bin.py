"""Parse a Functional TPU transmission (Message Protocol v0.3): weights + program.

Read-only use of Gabe Litteken's LeNet_5_TRANSMISSION.bin, passed by path.
"""
import numpy as np

FLASH, MEM, PROGRAM, STOP = 0x55, 0x4D, 0x50, 0x53


def bits(x, hi, lo):
    return (x >> lo) & ((1 << (hi - lo + 1)) - 1)


def parse(path):
    """Return (mem: dict addr->int8 array of blocks, instrs: list of 128-bit ints)."""
    with open(path, "rb") as f:
        d = f.read()
    i = 0
    assert d[i] == FLASH
    i += 1
    mem, instrs = [], []
    while i < len(d):
        t = d[i]
        if t == MEM:
            a = int.from_bytes(d[i + 1:i + 4], "little")
            n = int.from_bytes(d[i + 4:i + 6], "little")
            mem.append((a, np.frombuffer(d[i + 6:i + 6 + n], dtype=np.int8)))
            i += 6 + n
        elif t == PROGRAM:
            instrs.append(int.from_bytes(d[i + 1:i + 17], "little"))
            i += 17
        elif t == STOP:
            assert i == len(d) - 1
            i += 1
        else:
            raise ValueError(f"bad tag {t:#x} at {i}")
    return mem, instrs
