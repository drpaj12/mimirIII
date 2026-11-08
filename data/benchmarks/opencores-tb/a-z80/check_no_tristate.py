#!/usr/bin/env python3
"""usage: check_no_tristate.py <cpu dir>

Fails if any RTL file of the flow has `inout`, a literal with a z digit, `z`, tri, bufif, pmos,
nmos or tran primitives (comments stripped). Files not in the flow (z80_top_ifc_n.sv, the benches,
data_pins_lattice.v) are skipped.
"""

import glob
import os
import re
import sys

PATTERN = re.compile(
    r"\binout\b|\d*'[sS]?[bBhHoO]\w*[zZ]\w*"
    r"|\b(?:tri[01]?|bufif[01]|notif[01]|pmos|nmos|rpmos|rnmos|tranif[01]|tran|rtran)\b|\bz\b"
)


def flow_files(top: str) -> list[str]:
    found: list[str] = []
    for sub in ("alu", "bus", "control", "registers"):
        found += glob.glob(f"{top}/{sub}/*.v") + glob.glob(f"{top}/{sub}/*.vh")
    found += [f"{top}/toplevel/z80_top_direct_n.v", *glob.glob(f"{top}/toplevel/*.vh")]
    keep = [f for f in found if "data_pins_lattice" not in f and not f.endswith("test_fuse.vh")]
    return sorted(set(keep))


def hits(path: str) -> list[tuple[int, str]]:
    with open(path, errors="replace") as fh:
        text = fh.read()
    text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    out = []
    for number, line in enumerate(text.split("\n"), 1):
        code = re.sub(r"//.*", "", line)
        out += [(number, m.group(0)) for m in PATTERN.finditer(code)]
    return out


def main() -> int:
    top = sys.argv[1]
    files = flow_files(top)
    bad = 0
    for path in files:
        for number, word in hits(path):
            print(f"{os.path.relpath(path, top)}:{number}: {word}")
            bad += 1
    print(f"checked {len(files)} files, {bad} hits")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
