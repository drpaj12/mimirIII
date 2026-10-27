"""Run a list of designs one at a time: the flow under `tools/heavy-run` (`structrun` takes the
Norns VPR lock around its `odin3-flow` step itself), import into the store, then the detectors
under `tools/heavy-run` too. Smallest design first; a design already in the store is skipped.
Every Odin III or Loki run is one heavy-run call. The caller must set ODIN3_HEAVY_OK=1 (heavy-run
exits 77 without it). Spec: docs/specs/2026-10-27-mimir-structures.md.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

MIN_FREE_GB = 30
MAX_DETECT_LUTS = 4000
_MODULE = re.compile(r"^\s*module\s+(\w+)", re.M)


def find_top(path: Path) -> str:
    """The module no other module of the file instantiates (the last one when several)."""
    text = path.read_text(encoding="utf-8", errors="replace")
    mods = _MODULE.findall(text)
    free = [m for m in mods if not re.search(rf"^\s*{re.escape(m)}\s+(?:#\s*\(.*?\)\s*)?\w+\s*\(",
                                               text, re.M | re.S)]
    return str((free or mods)[-1])


def free_gb(path: str = "/mnt/c") -> float:
    return shutil.disk_usage(path).free / 1e9


def done(db: Path, slug: str) -> bool:
    if not db.exists():
        return False
    con = sqlite3.connect(db)
    try:
        n = con.execute("SELECT COUNT(*) FROM run WHERE slug=? AND source='mimir-structures'",
                        (slug,)).fetchone()[0]
    except sqlite3.OperationalError:
        n = 0
    con.close()
    return bool(n)


def _call(argv: list[str]) -> int:
    return subprocess.run(argv, check=False).returncode


def finished(out: Path) -> bool:
    """True when `out` holds a finished run (`mimir-run.json` with ok) to import again."""
    try:
        return bool(json.loads((out / "mimir-run.json").read_text(encoding="utf-8"))["ok"])
    except (OSError, ValueError, KeyError):
        return False


def one(py: str, heavy: str, tree: Path, db: Path, work: Path, slug: str, suite: str,
        path: Path, extra: list[str], reuse: bool = False) -> str:
    name = path.stem
    out = work / name
    top = find_top(path)
    flow = [heavy, py, "-m", "mimir.structrun", "--tree", str(tree),
            "--odin3", str(tree / "build/release/odin3"), "--top", top, "--out", str(out),
            str(path)]
    if not (reuse and finished(out)) and _call(flow) != 0:
        return f"{slug}: flow failed"
    base = [py, "-m", "mimir.structcli"]
    imp = [*base, "import-flow", str(db), "--flow-dir", str(out), "--slug", slug, "--name", name,
           "--suite", suite, "--file", str(path), *extra]
    if _call(imp) != 0:
        return f"{slug}: import failed"
    luts = re.search(r'"luts": (\d+)', (out / "summary.json").read_text(encoding="utf-8"))
    if luts and int(luts.group(1)) > MAX_DETECT_LUTS:
        return f"{slug}: ok, detectors skipped ({luts.group(1)} LUTs)"
    det = [heavy, py, "-m", "mimir.structcli", "detect", str(db), "--flow-dir", str(out), "--slug",
           slug, "--name", name, "--work", str(work / "det"), *extra]
    return f"{slug}: ok" if _call(det) == 0 else f"{slug}: ok, detector failed"


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="mimir.structbatch")
    ap.add_argument("--db", required=True, type=Path)
    ap.add_argument("--tree", required=True, type=Path)
    ap.add_argument("--work", required=True, type=Path)
    ap.add_argument("--suite", required=True)
    ap.add_argument("--slug-prefix", required=True)
    ap.add_argument("--heavy-run", required=True,
                    help="path of tools/heavy-run; needs ODIN3_HEAVY_OK=1 set")
    ap.add_argument("--blobs")
    ap.add_argument("--reuse", action="store_true", help="import a finished flow dir, do not rerun")
    ap.add_argument("designs", nargs="+", type=Path)
    ns = ap.parse_args(argv)
    if os.environ.get("ODIN3_HEAVY_OK") != "1":
        print("mimir.structbatch: set ODIN3_HEAVY_OK=1 in the environment (heavy-run needs it)",
              file=sys.stderr)
        return 2
    extra = ["--blobs", ns.blobs] if ns.blobs else []
    py = sys.executable
    for path in sorted(ns.designs, key=lambda p: (p.stat().st_size, p.name)):
        slug = f"{ns.slug_prefix}/{path.stem}"
        if done(ns.db, slug):
            print(f"{slug}: already in the store")
            continue
        if free_gb() < MIN_FREE_GB:
            print(f"stop: /mnt/c has {free_gb():.1f} GB free")
            return 3
        print(one(py, ns.heavy_run, ns.tree, ns.db, ns.work, slug, ns.suite, path, extra, ns.reuse),
              flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
