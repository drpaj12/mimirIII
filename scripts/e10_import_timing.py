"""Import the VPR setup timing reports of the E10 runs into the timing tables (schema 5).

Usage: e10_import_timing.py DB RUNROOT [--label e10] [--requested 200] [--only-source SRC]
       [--report OUT.json]

For every `run` row of source `norns-placers-<label>-<config>` the report is looked up at
RUNROOT/vpr/<label>-<config>/<design>/<arm dir>/(vpr/)report_timing.setup.rpt, with the arm dir
`<arm>.s<seed>` (`<arm base>.s<seed>.t<temp>` for an annealing external arm). Runs without a
report are counted and named. One transaction per run (mimir.timing.import_run). The reports hold
at most `--requested` paths (E10: `--timing_report_npaths 200`); a report that holds that many is
cut and the importer marks the run truncated. Path level only: a VPR report has no attribution,
so there are no HDL-object rows.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from mimir import timing
from mimir.scrub import Scrubber
from mimir.store import Store

PREFIX = "norns-placers-"


def arm_dir(arm: str, seed: int) -> str:
    base, _, temp = arm.partition("-t")
    return f"{base}.s{seed}.t{temp}" if temp else f"{base}.s{seed}"


def find_report(root: Path, label: str, source: str, design: str, arm: str,
                seed: int) -> Path | None:
    cfg = source[len(f"{PREFIX}{label}-"):]
    run = root / "vpr" / f"{label}-{cfg}" / design / arm_dir(arm, seed)
    for cand in (run / "report_timing.setup.rpt", run / "vpr" / "report_timing.setup.rpt"):
        if cand.is_file():
            return cand
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("root", type=Path)
    ap.add_argument("--label", default="e10")
    ap.add_argument("--requested", type=int, default=200)
    ap.add_argument("--only-source", default="")
    ap.add_argument("--report", type=Path, help="write the per-run result to this JSON file")
    ns = ap.parse_args(argv)
    store = Store(ns.db)
    scrub = Scrubber({})
    rows = store.db.execute(
        "SELECT run_id, source, design, arm, seed FROM run WHERE source LIKE ? "
        "ORDER BY source, design, arm, seed", (f"{PREFIX}{ns.label}-%",)).fetchall()
    out: list[dict[str, object]] = []
    for run_id, source, design, arm, seed in rows:
        if ns.only_source and source != ns.only_source:
            continue
        rpt = find_report(ns.root, ns.label, source, design, arm, seed)
        if rpt is None:
            out.append({"run_id": run_id, "source": source, "design": design, "arm": arm,
                        "seed": seed, "status": "no report"})
            continue
        data = rpt.read_bytes()
        try:
            text = data.decode("utf-8", "replace")
            inp = timing.parse_report(text, timing.sha_of(data), ns.requested)
            res, _ = timing.import_run(store, run_id, inp, scrub)
            status = timing.status_of(res)
        except ValueError as exc:
            status = f"error: {exc}"
        out.append({"run_id": run_id, "source": source, "design": design, "arm": arm,
                    "seed": seed, "status": status})
    store.close()
    print(json.dumps(dict(Counter(str(r["status"]).split(":")[0] for r in out)), sort_keys=True))
    if ns.report:
        ns.report.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return 1 if any(str(r["status"]).startswith("error") for r in out) else 0


if __name__ == "__main__":
    sys.exit(main())
