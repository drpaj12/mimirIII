#!/usr/bin/env python3
"""Usage: check_no_tristate.py <cpu dir>. Fails if any RTL file of the flow has inout, a z literal, tri/bufif/pmos/nmos
(comments stripped). Files not in the flow (z80_top_ifc_n.sv, test benches, data_pins_lattice.v) are skipped."""
import re, sys, glob, os
d = sys.argv[1]
files = [f for sub in ('alu', 'bus', 'control', 'registers') for f in glob.glob(f'{d}/{sub}/*.v') + glob.glob(f'{d}/{sub}/*.vh')]
files += [f'{d}/toplevel/z80_top_direct_n.v'] + glob.glob(f'{d}/toplevel/*.vh')
files = sorted(f for f in files if 'data_pins_lattice' not in f and not f.endswith('test_fuse.vh'))
bad = 0
pat = re.compile(r"\binout\b|\b\d*'[bBhHdD][0-9a-fA-F_]*[zZxX?][0-9a-fA-F_zZxX?]*|\btri[01]?\b|\b(bufif[01]|notif[01]|pmos|nmos|rpmos|rnmos|tranif[01]|tran|rtran)\b|\bz\b")
for f in files:
    t = open(f, errors='replace').read()
    t = re.sub(r'/\*.*?\*/', lambda m: '\n' * m.group(0).count('\n'), t, flags=re.S)
    for i, l in enumerate(t.split('\n'), 1):
        l = re.sub(r'//.*', '', l)
        # x literals are not tri-state: only flag z/inout/tri primitives
        for m in re.finditer(r"\binout\b|\d*'[sS]?[bBhHoO]\w*[zZ]\w*|\b(?:tri[01]?|bufif[01]|notif[01]|pmos|nmos|rpmos|rnmos|tranif[01]|tran|rtran)\b|\bz\b", l):
            print(f'{os.path.relpath(f, d)}:{i}: {m.group(0)}'); bad += 1
print(f'checked {len(files)} files, {bad} hits')
sys.exit(1 if bad else 0)
