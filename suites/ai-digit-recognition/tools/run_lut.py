"""Simulate a generated LUT-network design (I6 NeuraLUT or I8 TreeLUT) on a tier; print JSON.

usage: run_lut.py <design> <build_dir> <tier: quick|full> <work_dir> [--sim verilator|iverilog]
<build_dir> is the output of tools/neuralut_gen.py or tools/treelut_gen.py (mnist_top.v, the core
file, vec/<tier>/ whose golden is the Python model of that design). The JSON has the shape of
tools/run_i1.py so score/vtr_leg.py and score/lpm_leg.py take it as --rtl-result.
"""

import importlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE / "score"))
C = importlib.import_module("common")


def sources(build):
    build = Path(build).resolve()
    core = next(build.glob("*_all.v"))
    return [build / "mnist_top.v", core]


def run(design, build, tier, work, sim="verilator"):
    vec = Path(build).resolve() / "vec" / tier
    run_dir = Path(work).resolve() / design / f"sim-{tier}-{sim}"
    if sim == "iverilog":
        res, err = C.sim_iverilog(sources(build), vec, run_dir)
    else:
        res, err = C.sim_verilator(sources(build), vec, run_dir)
    return {"design": design, "tier": tier, "sim": sim, "result": res, "error": err}


if __name__ == "__main__":
    a = sys.argv[1:]
    sim = a[a.index("--sim") + 1] if "--sim" in a else "verilator"
    print(json.dumps(run(a[0], a[1], a[2], a[3], sim), sort_keys=True))
