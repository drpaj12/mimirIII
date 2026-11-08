#!/usr/bin/env python3
"""usage: mkrand.py <seed> : a 64 KiB RAM image: a register-initialising prologue at address 0, then pseudo-random
bytes everywhere else (HALT and DI replaced by NOP/EI so the CPU keeps running). A random opcode stream exercises
many instruction/prefix combinations (including undocumented ones) with the same stimulus on both DUTs."""
import random, sys
r = random.Random(int(sys.argv[1]))
b = [r.randrange(256) for _ in range(0x10000)]
b = [0x00 if x == 0x76 else (0xFB if x == 0xF3 else x) for x in b]
pro = [0x31, 0x00, 0xC0,              # ld sp,0C000h
       0xAF,                          # xor a  (defines A and the flags)
       0x01, 0x34, 0x12, 0x11, 0x78, 0x56, 0x21, 0xBC, 0x9A,   # ld bc,de,hl
       0x08, 0xAF, 0xD9, 0x01, 0x11, 0x22, 0x11, 0x33, 0x44, 0x21, 0x55, 0x66, 0xD9,   # af' bc' de' hl' defined
       0xDD, 0x21, 0x00, 0x80, 0xFD, 0x21, 0x00, 0x90,   # ix, iy
       0x3E, 0x00, 0xED, 0x47, 0xED, 0x56]               # ld a,0; ld i,a; im 1
b[0:len(pro)] = pro
for i in range(0, len(b), 16): print(' '.join('%02X' % x for x in b[i:i+16]) + ' ')
