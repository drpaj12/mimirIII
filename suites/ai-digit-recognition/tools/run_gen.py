"""Build and simulate a generated design (I3 or I4) on a tier; print the result as JSON.

usage: run_gen.py <name> <tier: quick|full> <work_dir> [--vec DIR] [--sim verilator|iverilog]
                  [--tb serial|pipe|both] [gen_lenet options: --design i3|i4 --p N --lanes a=n,..]
Builds into <work_dir>/<name> (gen_lenet.py), simulates in <work_dir>/<name>/sim-<tier>-<tb>.
The JSON has "result" (serial common tb/mnist_tb.v), "pipe" (tb/mnist_tb_pipe.v) and "error".
"""
import importlib
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
SUITE = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(SUITE / "score"), str(SUITE / "tools")]
gen = importlib.import_module("gen_lenet")
C = importlib.import_module("common")
TB_PIPE = SUITE / "tb" / "mnist_tb_pipe.v"


def run(name, tier, work, opt, vec=None, sim="verilator", which="both"):
    data = Path(os.environ.get("AIDIGIT_DATA", C.WS / "work/ai-mnist-data"))
    vec = Path(vec) if vec else data / "vectors" / tier
    out = Path(work).resolve() / name
    lanes = gen.parse_lanes(opt["--lanes"], int(opt.get("--p", 1))) if "--lanes" in opt else None
    info = gen.build(out, opt.get("--design", "i3"), int(opt.get("--p", 1)), lanes,
                     opt.get("--weights"), vec, 3)
    C.EXTRA_FILES[:] = info["data_files"]
    res = {"design": name, "tier": tier, "sim": sim, "result": None, "pipe": None, "error": None}
    defs = ["MNIST_TMO=20000000"]
    for key, tb, top in (("result", C.TB, "mnist_tb"), ("pipe", TB_PIPE, "mnist_tb_pipe")):
        if which not in ("both", "serial" if key == "result" else "pipe"):
            continue
        d = out / f"sim-{tier}-{key}"
        if sim == "iverilog":
            r, err = C.sim_iverilog(info["sources"], vec, d, defines=defs, tb=tb)
        else:
            r, err = C.sim_verilator(info["sources"], vec, d, defines=defs, tb=tb, top=top)
        res[key] = r
        if err:
            res["error"] = (res["error"] or "") + f"{key}: {err} "
    return res


if __name__ == "__main__":
    a = sys.argv[1:]
    opt = {a[i]: a[i + 1] for i in range(3, len(a) - 1, 2) if a[i].startswith("--")}
    r = run(a[0], a[1], a[2], opt, opt.get("--vec"), opt.get("--sim", "verilator"),
            opt.get("--tb", "both"))
    print(json.dumps(r, sort_keys=True))
