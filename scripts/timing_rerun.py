"""Timing-only re-analysis of a stored lane 3 run (spec docs/specs/2026-10-28-near-critical.md,
section 4). Rebuilds an odin3-flow directory from the run's blobs, runs `vpr --analysis` on the
stored routing (no pack, place or route) with `--timing_report_npaths N`, then `odin3-timing`.

Usage: timing_rerun.py STORE RUN_ID N WORKDIR   (env: VTR_ROOT, MIMIR_BLOBS, MIMIR_ODIN3_TREE)
The VPR step holds the Norns VPR lock (flock). Writes WORKDIR/flow/timing/attribution.json.
"""

from __future__ import annotations

import json
import lzma
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

LOCK = "/tmp/claude-1000/norns-vpr.lock"
ARCH = "vtr_flow/arch/timing/k6_frac_N10_frac_chain_mem32K_40nm.xml"


def blob(root: Path, sha: str) -> bytes:
    return lzma.open(root / sha[:2] / f"{sha}.xz").read()


def grab(pattern: str, text: str) -> str:
    m = re.search(pattern, text)
    if m is None:
        raise SystemExit(f"no match for {pattern}")
    return m.group(1)


def main(argv: list[str]) -> int:
    store, run_id, n, work = argv[1], argv[2], int(argv[3]), Path(argv[4])
    root = Path(os.environ["MIMIR_BLOBS"])
    db = sqlite3.connect(f"file:{store}?mode=ro", uri=True)
    arts = dict(db.execute("SELECT kind, blob_sha256 FROM run_artifact WHERE run_id=?", (run_id,)))
    cmd = db.execute("SELECT command_line FROM run WHERE run_id=?", (run_id,)).fetchone()[0]
    top = grab(r"--top (\S+)", cmd)
    log = blob(root, arts["log"]).decode(errors="replace")
    chan = grab(r"--route_chan_width (\d+)", log)
    flow, vrun = work / "flow", work / "flow" / "vpr" / "run"
    for d in (flow / "odin3", flow / "timing", vrun):
        d.mkdir(parents=True, exist_ok=True)
    blif = flow / "odin3" / f"{top}.blif"
    blif.write_bytes(blob(root, arts["blif"]))
    (flow / "odin3" / f"{top}.blif.names").write_bytes(blob(root, arts["map"]))
    for kind, ext in (("net", "net"), ("place", "place"), ("route", "route")):
        (vrun / f"{top}.{ext}").write_bytes(blob(root, arts[kind]))
    (vrun / f"{top}.pre-vpr.blif").write_bytes(blif.read_bytes())
    vtr = Path(os.environ["VTR_ROOT"])
    vpr = [str(vtr / "build/vpr/vpr"), str(vtr / ARCH), top, "--circuit_file",
           f"{top}.pre-vpr.blif", "--analysis", "--route_chan_width", chan,
           "--timing_report_npaths", str(n), "--net_file", f"{top}.net",
           "--place_file", f"{top}.place", "--route_file", f"{top}.route"]
    out = subprocess.run(["flock", LOCK, *vpr], cwd=vrun, capture_output=True, text=True)
    (vrun / "vpr.out").write_text(out.stdout + out.stderr)
    if out.returncode != 0:
        print(out.stdout[-2000:], out.stderr[-2000:])
        return out.returncode
    inputs = {"top": top, "blif": f"odin3/{top}.blif", "name_map": f"odin3/{top}.blif.names",
              "vpr_run_dir": "vpr/run", "paths_requested": n}
    (flow / "timing" / "inputs.json").write_text(json.dumps(inputs, indent=1, sort_keys=True))
    tree = Path(os.environ["MIMIR_ODIN3_TREE"])
    r = subprocess.run([str(tree / "tools/flow/odin3-timing"), str(flow)], capture_output=True,
                       text=True)
    print(r.stdout[-500:], r.stderr[-1500:])
    return r.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv))
