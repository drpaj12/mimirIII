"""Simulate implementation I1 (Gabe's TPU, array edge N) on a tier and print the result as JSON.

usage: run_i1.py <N> <tier: quick|full> <work_dir> [--vec DIR] [--sim verilator|iverilog]
Builds into <work_dir>/i1-n<N> (build_i1.py), simulates in <work_dir>/i1-n<N>/sim-<tier>.
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
build_i1 = importlib.import_module("build_i1")
C = importlib.import_module("common")

INIT_BUDGET = 400_000_000


def run(n, tier, work, vec=None, sim="verilator"):
    data = Path(os.environ.get("AIDIGIT_DATA", C.WS / "work/ai-mnist-data"))
    vec = Path(vec) if vec else data / "vectors" / tier
    out = Path(work).resolve() / f"i1-n{n}"
    info = build_i1.build(n, out)
    defs = [f"{k}={v}" for k, v in info["defines"].items()]
    defs += [f"MNIST_INIT={INIT_BUDGET}", "MNIST_TMO=20000000"]
    run_dir = out / f"sim-{tier}"
    if sim == "iverilog":
        res, err = C.sim_iverilog(info["sources"], vec, run_dir, defines=defs)
    else:
        res, err = C.sim_verilator(info["sources"], vec, run_dir, defines=defs)
    return {"design": f"i1-tpu-n{n}", "tier": tier, "sim": sim, "result": res, "error": err}


if __name__ == "__main__":
    a = sys.argv[1:]
    vec = a[a.index("--vec") + 1] if "--vec" in a else None
    sim = a[a.index("--sim") + 1] if "--sim" in a else "verilator"
    r = run(int(a[0]), a[1], a[2], vec, sim)
    print(json.dumps(r, sort_keys=True))
