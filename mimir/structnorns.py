"""Structures and their mapping for runs that already have a run record (E10 sweep).

`structdb.import_flow_dir` imports a whole `odin3-flow` output directory and makes its own run. A
Norns run (`mimir-run.json`, imported by `mimir import-runrecords`) has the run row already; this
module only adds the `structure`, `structure_member` and `structure_mapping` rows of that run, with
the run's id and flow configuration. The inputs are the BLIF VPR read, the Odin III name map
extended by `odin3-prov-post` with the run's own packing and placement, and the HDL files.

    python -m mimir.structnorns DB JOBS.json

JOBS.json is a list of objects with: `source`, `design`, `arch`, `seed`, `arm` (the key of the run
row), `slug` (the design slug the rows are written under), `blif`, `map`, `files` (HDL files).
Paths of the Odin III checkout and the Loki checkout come from `MIMIR_ODIN3_TREE` and
`MIMIR_LOKI_SRC`. Rows of the same run and slug are replaced; other runs' rows are untouched.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from mimir.blif import parse_models
from mimir.scrub import Scrubber
from mimir.store import Store
from mimir.structdb import files_sha256, put_structures
from mimir.structmap import Deps, analyse, atoms_from_blif, load_deps


def run_row(store: Store, job: dict[str, Any]) -> tuple[str, str]:
    """(run_id, config_hash) of the run row a job names; ValueError for none or several."""
    rows = store.db.execute(
        "SELECT run_id, config_hash FROM run WHERE source=? AND design=? AND arch=? AND seed=? "
        "AND arm=?",
        (job["source"], job["design"], job["arch"], job["seed"], job["arm"])).fetchall()
    if len(rows) != 1:
        raise ValueError(f"{job['source']}/{job['design']}/{job['arm']}/s{job['seed']}: "
                         f"{len(rows)} run rows (need exactly one: import the run records first)")
    return str(rows[0][0]), str(rows[0][1])


def clear_run(store: Store, slug: str, rid: str) -> None:
    """Delete the member and mapping rows of one run of a design (a re-import)."""
    for table in ("structure_member", "structure_mapping"):
        store.db.execute(f"DELETE FROM {table} WHERE design = ? AND run_id = ?", (slug, rid))


def import_job(store: Store, deps: Deps, scrub: Scrubber, job: dict[str, Any]) -> dict[str, int]:
    """Analyse one run's map and store its structure rows; returns the counts."""
    rid, cfg = run_row(store, job)
    slug = str(job["slug"])
    files = [Path(f) for f in job["files"]]
    nm = deps.nmv2.read_name_map(Path(job["map"]))
    blif = Path(job["blif"])
    models = parse_models(blif.read_text(encoding="utf-8"))
    atoms = atoms_from_blif(models, lambda n: nm.atom(n) is not None)
    texts = {f: Path(f).read_text(encoding="utf-8", errors="replace") for f in nm.files
             if Path(f).is_file()}
    a = analyse(nm, deps, atoms, texts, scrub.path)
    members: dict[str, set[str]] = {}
    for atom, sids in a.atom_structs.items():
        for sid in sids:
            members.setdefault(sid, set()).add(atom)
    sha = files_sha256(files)
    store.db.execute("INSERT OR REPLACE INTO design VALUES (?,?,?,?,?,?)",
                     (slug, sha, "hdl", str(job.get("suite", "norns-e10")), str(job["design"]),
                      scrub.path(str(files[0]))))
    store.db.execute("UPDATE run SET slug = ? WHERE run_id = ?", (slug, rid))
    clear_run(store, slug, rid)
    put_structures(store, slug, rid, cfg, a.structs, a.rows, members)
    store.db.commit()
    return {"structures": len(a.structs), "rows": len(a.rows), "atoms": len(atoms),
            "unattributed": a.unattributed}


def make_scrub(odin3: Path, loki: Path) -> Scrubber:
    vtr = os.environ.get("VTR_ROOT")
    return Scrubber({"$VTR_ROOT": Path(vtr) if vtr else None, "$ODIN3": odin3, "$LOKI": loki,
                     "$WS": Path.home() / "odin3-ws"})


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="mimir.structnorns")
    ap.add_argument("db")
    ap.add_argument("jobs", type=Path)
    ns = ap.parse_args(argv)
    odin3, loki = os.environ.get("MIMIR_ODIN3_TREE"), os.environ.get("MIMIR_LOKI_SRC")
    if not odin3 or not loki:
        print("error: set MIMIR_ODIN3_TREE and MIMIR_LOKI_SRC", file=sys.stderr)
        return 2
    deps = load_deps(Path(odin3), Path(loki))
    scrub = make_scrub(Path(odin3), Path(loki))
    store = Store(ns.db)
    failed = 0
    for job in json.loads(ns.jobs.read_text(encoding="utf-8")):
        try:
            counts = import_job(store, deps, scrub, job)
            print(f"{job['slug']} {job['arm']} s{job['seed']}: {counts}", flush=True)
        except (ValueError, OSError) as exc:
            store.db.rollback()
            failed += 1
            print(f"{job['slug']} {job['arm']} s{job['seed']}: FAILED {exc}", flush=True)
    store.close()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
