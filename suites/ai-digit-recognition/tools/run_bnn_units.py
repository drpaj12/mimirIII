"""Run the per-layer unit testbenches that tools/gen_bnn.py wrote (iverilog), print JSON.

usage: run_bnn_units.py <build_dir>
Each tb_bnn_l<k>.v is compiled with the design's mnist_top.v and run in <build_dir>/unit.
"""

import json
import re
import subprocess
import sys
from pathlib import Path


def main(build):
    unit = Path(build).resolve() / "unit"
    top = Path(build).resolve() / "mnist_top.v"
    out = {}
    for tb in sorted(unit.glob("tb_bnn_l*.v")):
        vvp = unit / (tb.stem + ".vvp")
        r = subprocess.run(["iverilog", "-g2005", "-o", str(vvp), str(tb), str(top)],
                           capture_output=True, text=True, cwd=unit, check=False)
        if r.returncode:
            out[tb.stem] = {"verdict": "COMPILE_FAIL", "log": r.stderr[-300:]}
            continue
        r = subprocess.run(["vvp", str(vvp)], capture_output=True, text=True, cwd=unit, check=False)
        m = re.search(r"UNIT (\S+) (PASS|FAIL) n=(\d+)(?: cycles=(\d+))?", r.stdout)
        out[tb.stem] = ({"verdict": m.group(2), "n": int(m.group(3)),
                         "cycles": int(m.group(4)) if m.group(4) else None}
                        if m else {"verdict": "NO_RESULT", "log": r.stdout[-300:]})
        vvp.unlink()
    print(json.dumps(out, sort_keys=True))
    return 0 if all(v["verdict"] == "PASS" for v in out.values()) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
