"""Score one generated LUT-network design.

RTL simulation (both tiers on Verilator: iverilog needs 2.7 min for NeuraLUT B quick and over
25 min for TreeLUT T2 quick), then the VTR leg and the LPM leg on the quick tier (Odin III
netlist simulation on the quick tier).

usage: lut_legs.py <design> <build_dir> <res_dir> <work_dir> [--no-netlist-sim]
Appends rows to <res_dir>/{vtr,lpm}.jsonl and writes <res_dir>/<design>-{full,quick}.json (RTL).
The full-tier Verilator result is added to the VTR row as accuracy.rtl_verilator_full.
"""

import json
import subprocess
import sys
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent


def sh(argv):
    return subprocess.run([str(a) for a in argv], capture_output=True, text=True, check=False)


def main(argv):
    design, build, res, work = (Path(a).resolve() if i else a for i, a in enumerate(argv[:4]))
    res.mkdir(parents=True, exist_ok=True)
    nsim = "--no-netlist-sim" not in argv
    run = SUITE / "tools/run_lut.py"
    outs = {}
    for tier, sim in (("full", "verilator"), ("quick", "verilator")):
        r = sh(["python3", "-I", run, design, build, tier, work, "--sim", sim])
        (res / f"{design}-{tier}.json").write_text(r.stdout)
        outs[tier] = json.loads(r.stdout)
    for name in ("vtr.jsonl", "lpm.jsonl"):  # replace this design's earlier rows
        f = res / name
        if f.exists():
            keep = [ln for ln in f.read_text().splitlines() if json.loads(ln)["design"] != design]
            f.write_text("".join(ln + "\n" for ln in keep))
    vec = build / "vec/quick"
    # One file: score/vtr_leg.py runs one `read_verilog` per source and Odin III does not resolve a
    # module across two such commands.
    flat = build / "flat.v"
    flat.write_text(next(build.glob("*_all.v")).read_text() + (build / "mnist_top.v").read_text())
    src = [flat]
    quick = res / f"{design}-quick.json"
    common = [
        "--design",
        design,
        "--src",
        *src,
        "--vec",
        vec,
        "--work",
        work,
        "--tier",
        "quick",
        "--rtl-result",
        quick,
    ]
    sh(["python3", "-I", SUITE / "score/lpm_leg.py", *common, "--out", res / "lpm.jsonl"])
    vtr = ["python3", "-I", SUITE / "score/vtr_leg.py", *common, "--out", res / "vtr.jsonl"]
    sh(vtr if nsim else [*vtr, "--no-netlist-sim"])
    # attach the full-tier Verilator result to the VTR row of this design
    rows = [json.loads(ln) for ln in (res / "vtr.jsonl").read_text().splitlines() if ln.strip()]
    for row in rows:
        if row["design"] == design and row.get("accuracy") is not None:
            row["accuracy"]["rtl_verilator_full"] = outs["full"]["result"]
    (res / "vtr.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    print(json.dumps({"design": design, "full": outs["full"]["result"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
