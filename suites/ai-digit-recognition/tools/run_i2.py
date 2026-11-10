"""Simulate implementation I2 (soft CPU, C firmware) on a tier and print the result as JSON.

usage: run_i2.py <setting> <tier: quick|full|NAME> <work_dir> [--vec DIR] [--sim verilator|iverilog]
Builds into <work_dir>/i2-<setting> (build_i2.py), simulates in <work_dir>/i2-<setting>/sim-<tier>.
Vectors default to $AIDIGIT_DATA/vectors/<tier> (default <workspace>/work/ai-mnist-data).
"""
import importlib
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
SUITE = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(SUITE / "score"), str(SUITE / "tools")]
build_i2 = importlib.import_module("build_i2")
C = importlib.import_module("common")

TMO = 500_000_000   # per-image cycle budget (the slowest setting needs about 60 M)


def run(setting, tier, work, vec=None, sim="verilator", mem="4G"):
    data = Path(os.environ.get("AIDIGIT_DATA", C.WS / "work/ai-mnist-data"))
    vec = Path(vec) if vec else data / "vectors" / tier
    out = Path(work).resolve() / f"i2-{setting}"
    info = build_i2.build(setting, out)
    defs = [f"{k}={v}" for k, v in info["defines"].items()]
    defs += [f'ROM_HEX="{out}/i2_rom.hex"', f"MNIST_TMO={TMO}"]
    run_dir = out / f"sim-{tier}"
    if sim == "iverilog":
        res, err = C.sim_iverilog(info["sources"], vec, run_dir, defines=defs)
    else:
        res, err = C.sim_verilator(info["sources"], vec, run_dir, defines=defs, mem=mem, fast=True)
    return {"design": f"i2-{setting}", "tier": tier, "sim": sim, "result": res, "error": err}


if __name__ == "__main__":
    a = sys.argv[1:]
    vec = a[a.index("--vec") + 1] if "--vec" in a else None
    sim = a[a.index("--sim") + 1] if "--sim" in a else "verilator"
    r = run(a[0], a[1], a[2], vec, sim)
    print(json.dumps(r, sort_keys=True))
