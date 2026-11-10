"""I7 batch: for each design generate, run the unit tests, simulate the quick tier on iverilog, then
tools/lut_legs.py (Verilator quick + full, VTR leg, LPM leg, Odin III netlist simulation).

usage: run_bnn.py <train_dir> <run_dir> <design> [<design> ...]
Per design D: <run_dir>/build/D (generated, not committed), <run_dir>/res/ (vtr.jsonl, lpm.jsonl,
D-{full,quick}.json, D-iverilog-quick.json, D-units.json), <run_dir>/work/ (flow runs). Smallest
designs first is the caller's order. A failed step is recorded in the JSON, not raised.
"""

import json
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent


def run(argv, **kw):
    return subprocess.run([str(a) for a in argv], capture_output=True, text=True, check=False, **kw)


def main(train, root, designs):
    root = Path(root).resolve()
    res = root / "res"
    res.mkdir(parents=True, exist_ok=True)
    for d in designs:
        build = root / "build" / d
        r = run(["python3", "-I", TOOLS / "gen_bnn.py", d, train, build])
        (res / f"{d}-gen.json").write_text((build / "gen.json").read_text())
        u = run(["python3", "-I", TOOLS / "run_bnn_units.py", build])
        (res / f"{d}-units.json").write_text(u.stdout)
        i = run(["python3", "-I", TOOLS / "run_lut.py", d, build, "quick", root / "work", "--sim",
                 "iverilog"])
        (res / f"{d}-iverilog-quick.json").write_text(i.stdout)
        run(["python3", "-I", TOOLS / "lut_legs.py", d, build, res, root / "work"])
        print(d, "done", r.returncode, u.returncode, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2], sys.argv[3:]))
