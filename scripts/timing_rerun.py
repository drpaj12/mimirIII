"""Timing-only re-analysis of a stored lane 3 run (spec docs/specs/2026-10-28-near-critical.md,
section 4). Rebuilds an odin3-flow directory from the run's blobs, runs `vpr --analysis` on the
stored routing (no pack, place or route) with `--timing_report_npaths N`, then `odin3-timing`.

Usage: timing_rerun.py STORE RUN_ID N WORKDIR [--report-only]
Env: VTR_ROOT, MIMIR_BLOBS (optional), MIMIR_ODIN3_TREE (not needed with --report-only).

The architecture comes from `run.arch` (mimir.timingrerun.ARCHS; an unknown name aborts) and the
VPR options from the command line the stored flow log printed (mimir.timingrerun.CARRIED are
passed on, the others are listed on stdout). The VPR step holds the Norns VPR lock (flock).
--report-only stops after VPR: WORKDIR/flow/vpr/run/report_timing.setup.rpt is the report (use it
with N above the number of endpoints as `mimir import-timing --full-report`). Otherwise writes
WORKDIR/flow/timing/attribution.json.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from mimir import blobs, timingrerun

LOCK = "/tmp/claude-1000/norns-vpr.lock"


def rebuild(db: sqlite3.Connection, run_id: str, work: Path, root: Path) -> tuple[str, str, Path]:
    """Write the stored blif, map, net, place and route into WORKDIR/flow; returns
    (top, log text, VPR run dir)."""
    arts = dict(db.execute("SELECT kind, blob_sha256 FROM run_artifact WHERE run_id=?", (run_id,)))
    cmd = db.execute("SELECT command_line FROM run WHERE run_id=?", (run_id,)).fetchone()[0]
    words = cmd.split()
    top = words[words.index("--top") + 1]
    log = blobs.get_bytes(root, arts["log"]).decode(errors="replace")
    flow, vrun = work / "flow", work / "flow" / "vpr" / "run"
    for d in (flow / "odin3", flow / "timing", vrun):
        d.mkdir(parents=True, exist_ok=True)
    blif = flow / "odin3" / f"{top}.blif"
    blif.write_bytes(blobs.get_bytes(root, arts["blif"]))
    (flow / "odin3" / f"{top}.blif.names").write_bytes(blobs.get_bytes(root, arts["map"]))
    for ext in ("net", "place", "route"):
        (vrun / f"{top}.{ext}").write_bytes(blobs.get_bytes(root, arts[ext]))
    (vrun / f"{top}.pre-vpr.blif").write_bytes(blif.read_bytes())
    return top, log, vrun


def main(argv: list[str]) -> int:
    report_only = "--report-only" in argv
    args = [a for a in argv[1:] if a != "--report-only"]
    store, run_id, n, work = args[0], args[1], int(args[2]), Path(args[3])
    root = blobs.default_dir()
    db = sqlite3.connect(f"file:{store}?mode=ro", uri=True)
    arch_name = db.execute("SELECT arch FROM run WHERE run_id=?", (run_id,)).fetchone()[0]
    try:
        arch = timingrerun.arch_path(arch_name)
    except ValueError as exc:
        print(f"abort: {exc}")
        return 2
    top, log, vrun = rebuild(db, run_id, work, root)
    try:
        carried, left = timingrerun.carried_options(timingrerun.stored_vpr_argv(log))
    except ValueError as exc:
        print(f"abort: {exc}")
        return 2
    print(f"arch {arch_name}; carried {' '.join(carried)}; not carried: {' '.join(left) or '-'}")
    vtr = Path(os.environ["VTR_ROOT"])
    argv_vpr = timingrerun.vpr_argv(str(vtr / "build/vpr/vpr"), str(vtr / arch), top, carried, n)
    out = subprocess.run(["flock", LOCK, *argv_vpr], cwd=vrun, capture_output=True, text=True)
    (vrun / "vpr.out").write_text(out.stdout + out.stderr)
    if out.returncode != 0:
        print(out.stdout[-2000:], out.stderr[-2000:])
        return out.returncode
    if report_only:
        return 0
    flow = work / "flow"
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
