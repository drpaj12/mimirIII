"""Kept timing evidence of Norns runs (docs/specs/2026-10-29-norns-keep-import.md).

A Norns run directory holds `mimir-run.json` and, when the run kept timing, `attribution.json.xz`
(Odin III timing attribution, paths already tokenised) and `keep-timing.json`; the blif and its
name map are kept once per (design, blif sha256) in the keep store. This module stores them as
the run artifacts `timing`, `blif` and `map` (the kinds and formats of lane 3), then fills the
timing tables (schema 5, 6) and the HDL graph (schema 7) through the existing code paths
(`timing.import_from_blobs`, `timing.backfill_paths`, `hdlgraph.backfill`). No new parsing.
Purpose: hub RQ W Q3.3 (speed = critical + near-critical paths).
"""

from __future__ import annotations

import hashlib
import json
import lzma
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mimir import blobs, hdlgraph, timing
from mimir.runrecord import FILE_NAME, _tool_commit, check_record
from mimir.scrub import Scrubber, check_clean
from mimir.store import Store

TOKENS = ("$VTR_ROOT", "$WS", "~")


@dataclass
class KeptReport:
    """Per run: (run directory, status). `ok` or `skipped: ...` or `error: ...`."""

    rows: list[tuple[str, str]] = field(default_factory=list)

    def count(self) -> Counter[str]:
        return Counter(s.split(":")[0] for _, s in self.rows)


def _read_xz(path: Path) -> bytes:
    return lzma.decompress(path.read_bytes())


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _run_dir_file(rec: dict[str, Any], role: str, run_dir: Path) -> Path | None:
    art = rec["artifacts"].get(role)
    if not art:
        return None
    path = run_dir / Path(str(art["path"])).name
    return path if path.is_file() else None


def _run_id(store: Store, rec: dict[str, Any]) -> str | None:
    rows = store.db.execute(
        "SELECT run_id FROM run WHERE source = ? AND design = ? AND arch = ? AND seed = ? "
        "AND arm = ? AND input_sha256 = ? AND tool_commit = ?",
        (rec["source"], rec["design"], rec["arch"], rec["seed"], rec["arm"],
         rec["inputs"]["netlist"]["sha256"], _tool_commit(rec))).fetchall()
    return str(rows[0][0]) if len(rows) == 1 else None


def _blob_text(data: bytes, scrub: Scrubber, what: str) -> bytes:
    """Scrub (idempotent on text the runner already tokenised) and check; the bytes to store."""
    text = scrub.text(data.decode("utf-8", "replace"))
    if not check_clean(text):
        raise ValueError(f"{what} still holds a home path")
    return text.encode("utf-8")


def _kept_inputs(rec: dict[str, Any], run_dir: Path, keep_store: Path
                 ) -> tuple[bytes, bytes, dict[str, Any]]:
    """The kept blif and name map (decompressed), sha256 checked against keep-timing.json."""
    kt_file = _run_dir_file(rec, "keep_timing", run_dir) or run_dir / "keep-timing.json"
    kt = json.loads(kt_file.read_text(encoding="utf-8"))
    blif_sha, map_sha = kt.get("blif_sha256"), kt.get("map_sha256")
    if not blif_sha or not map_sha:
        raise ValueError("keep-timing.json names no blif or no name map")
    if rec["inputs"]["netlist"]["sha256"] != blif_sha:
        raise ValueError("record netlist sha256 is not keep-timing blif_sha256")
    d = keep_store / rec["design"] / blif_sha
    blif = _read_xz(d / f"{rec['design']}.blif.xz")
    names = _read_xz(d / f"{rec['design']}.blif.names.xz")
    # The kept copies are path-tokenised, so their sha256 equals the original's only when no
    # path was rewritten in them; with rewrites, the tokens must be present instead.
    rewritten = sum(int(v) for v in kt.get("paths_rewritten", {}).values())
    for name, data, sha in (("blif", blif, blif_sha), ("map", names, map_sha)):
        if _sha(data) != sha and not (rewritten and any(t.encode() in data for t in TOKENS)):
            raise ValueError(f"kept {name} does not match its sha256")
    return blif, names, kt


def import_kept(store: Store, runs_dir: Path, blobs_dir: Path, keep_store: Path | None = None,
                odin3_tree: Path | None = None) -> KeptReport:
    """Store and import the kept timing evidence of every run record under `runs_dir`.

    The run rows must exist (`import_runrecords`). A record whose attribution file is absent is
    left alone (status `skipped: no kept timing`). Idempotent: blobs are content addressed and a
    run whose artifacts are unchanged and already imported is not imported again. Without
    `odin3_tree` the HDL graph is not built (status says so)."""
    keep_store = keep_store or runs_dir / "_keep-inputs"
    scrub = Scrubber({})
    report = KeptReport()
    todo: list[str] = []
    kept: list[str] = []
    stale: list[str] = []
    for path in sorted(runs_dir.rglob(FILE_NAME)):
        run_dir = path.parent
        rel = run_dir.relative_to(runs_dir).as_posix()
        try:
            rec = json.loads(path.read_text(encoding="utf-8"))
            if check_record(rec):
                report.rows.append((rel, "skipped: record refused"))
                continue
            att = _run_dir_file(rec, "timing_attribution", run_dir)
            if att is None:
                report.rows.append((rel, "skipped: no kept timing"))
                continue
            art = rec["artifacts"]["timing_attribution"]
            data = att.read_bytes()
            if _sha(data) != art["sha256"]:
                raise ValueError("attribution sha256 differs from the run record")
            rid = _run_id(store, rec)
            if rid is None:
                raise ValueError("no unique run row (import the run records first)")
            blif, names, _ = _kept_inputs(rec, run_dir, keep_store)
            shas = {"timing": blobs.put_bytes(blobs_dir, _blob_text(lzma.decompress(data), scrub,
                                                                     "attribution")),
                    "blif": blobs.put_bytes(blobs_dir, _blob_text(blif, scrub, "blif")),
                    "map": blobs.put_bytes(blobs_dir, _blob_text(names, scrub, "name map"))}
        except (ValueError, KeyError, OSError, lzma.LZMAError, EOFError) as exc:
            report.rows.append((rel, f"error: {exc}"))
            continue
        old = dict(store.db.execute("SELECT kind, blob_sha256 FROM run_artifact WHERE run_id = ?",
                                    (rid,)).fetchall())
        changed = any(old.get(k) != v for k, v in shas.items())
        for kind, sha in shas.items():
            store.db.execute("INSERT OR REPLACE INTO run_artifact (run_id, kind, blob_sha256) "
                             "VALUES (?, ?, ?)", (rid, kind, sha))
        store.db.commit()
        has_timing = store.db.execute("SELECT 1 FROM timing_run WHERE run_id = ?",
                                      (rid,)).fetchone()
        kept.append(rid)
        if changed or not has_timing:
            todo.append(rid)
        if changed:
            stale.append(rid)
        report.rows.append((rel, f"ok {rid}"))
    _fill(store, report, todo, kept, stale, blobs_dir, scrub, odin3_tree)
    return report


def _fill(store: Store, report: KeptReport, todo: list[str], kept: list[str], stale: list[str],
          blobs_dir: Path, scrub: Scrubber, odin3_tree: Path | None) -> None:
    """Timing (v5, v6) and HDL graph (v7) of the runs in `todo`; a failure marks the run row."""
    only = set(todo)
    for rid in stale:  # a changed artifact: rebuild what hangs off the old one
        store.db.execute("DELETE FROM hdl_graph_run WHERE run_id = ?", (rid,))
    store.db.commit()
    bad: dict[str, str] = {}
    for rid, status in timing.import_from_blobs(store, blobs_dir, scrub, only=only):
        if status.startswith("error"):
            bad[rid] = status
    for rid, status in timing.backfill_paths(store, blobs_dir, scrub, only=only):
        if status != "ok":
            bad[rid] = status
    if odin3_tree is not None:
        with tempfile.TemporaryDirectory() as tmp:
            for rid, status in hdlgraph.backfill(store, blobs_dir, scrub, odin3_tree, Path(tmp),
                                                 set(kept)):
                if status.startswith("error"):
                    bad[rid] = status
    ok = "ok" if odin3_tree is not None else "ok (HDL graph not built: no --odin3-tree)"
    report.rows[:] = [(r, bad.get(s[3:], ok) if s.startswith("ok ") else s)
                      for r, s in report.rows]
