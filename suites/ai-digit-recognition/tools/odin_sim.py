"""Odin III simulation of the RTL: the 100-image quick tier through `sim_tb`, one row per design.

usage: odin_sim.py --manifest m.json --odin3 BIN --root DIR --out results/odin-sim.jsonl
                   [--timeout S] [--only DESIGN ...]
manifest.json: {"<design>": {"build": "<build.json>" | "sources": ["a.v", ..], "vec": "<dir>"}}.
Script: `read_verilog SRC...; proc; opt; lower --keep-mem-cells; sim_tb ...` (Odin III v1.6.1
simulates `$mem` without bit-blasting). Designs run smallest first (order of the manifest file); a
design already in --out is skipped. The row has `odin_sim` = the testbench summary (class and
score match against the golden, cycles) plus `wall_s`, or null with `error` = the located cause:
the last Odin error line, or the time limit with the last progress seen.
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "score"))
import common as C

ERR = re.compile(r"^odin3: (?:error|fatal)[^\n]*", re.M | re.I)


def project(path, incdirs, defines):
    lines = [f'incdir "{d}"' for d in incdirs] + [f'define "{k}={v}"' for k, v in defines.items()]
    path.write_text("\n".join(lines) + "\n")


def run_one(design, spec, odin3, root, timeout):
    work = root / design
    work.mkdir(parents=True, exist_ok=True)
    build = {}
    if "build" in spec:
        C.EXTRA_FILES[:] = []
        build = C.load_build(spec["build"])
        srcs = build["sources"]
    else:
        C.EXTRA_FILES[:] = []
        srcs = spec["sources"]
    n = C.stage_vectors(spec["vec"], work)
    defs = dict(build.get("defines", {}))
    project(work / "p.o3proj", build.get("incdirs", []), defs)
    reads = "read_verilog " + " ".join(str(Path(s).resolve()) for s in srcs)
    tbdefs = f"-D MNIST_N={n} -D MNIST_TMO=20000000" + (
        " -D MNIST_INIT=400000000" if "FLASH_LEN" in defs else "")
    script = (f"{reads}; proc; opt; lower --keep-mem-cells; sim_tb -I {work} {tbdefs} {C.TB}")
    cmd = [odin3, "--project", work / "p.o3proj", "--top", "mnist_top", "-p", script]
    row = {"schema": 1, "design": design, "tier": "quick", "odin3_binary": Path(odin3).parent.name,
           "script": script.replace(str(work), "<run>").replace(str(C.TB), "tb/mnist_tb.v"),
           "odin_sim": None, "error": None}
    t = time.time()
    # `timeout` inside the capped scope: a killed client would leave the simulator running
    r = C.capped(["timeout", "-s", "KILL", timeout, *cmd], cwd=work, timeout=timeout + 600,
                 mem="4G")
    text = r.stdout + r.stderr
    (work / "odin.log").write_text(text)
    res = C.parse_tb(r.stdout)
    if res:
        res["wall_s"] = round(time.time() - t, 1)
        row["odin_sim"] = res
    elif r.returncode in (124, 137, -9):
        row["error"] = (f"no result within the {timeout} s limit ({len(text.splitlines())} log "
                        "lines); sim_tb still running")
    else:
        found = [m.group(0) for m in ERR.finditer(text)]
        tail = text.strip().splitlines()[-1:] or ["no output"]
        row["error"] = f"exit {r.returncode}: {(found or tail)[-1]}"[:600]
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--odin3", required=True)
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--timeout", type=int, default=3 * 3600)
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    manifest = json.loads(Path(a.manifest).read_text())
    ver = subprocess.run([a.odin3, "--version"], capture_output=True, text=True).stdout.strip()
    build = f"{ver.splitlines()[0] if ver else '?'} ({Path(a.odin3).parent.name})"
    done = set()
    if Path(a.out).exists():
        done = {json.loads(x)["design"] for x in Path(a.out).read_text().splitlines() if x}
    for d, spec in manifest.items():
        if d in done or (a.only and d not in a.only):
            continue
        print(f"odin_sim: {d}", flush=True)
        row = run_one(d, spec, a.odin3, Path(a.root).resolve(), a.timeout)
        row["odin3_build"] = build
        with open(a.out, "a") as f:
            f.write(json.dumps(row, sort_keys=True) + "\n")
        print(f"odin_sim: {d} {'PASS' if row['odin_sim'] else 'ERROR ' + str(row['error'])}",
              flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
