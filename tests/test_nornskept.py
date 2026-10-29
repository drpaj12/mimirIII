"""Kept timing evidence of Norns runs: blobs, timing tables, path tables, HDL graph."""

from __future__ import annotations

import contextlib
import copy
import gzip
import io
import json
import lzma
import sqlite3
import unittest
from pathlib import Path

from mimir import blobs
from mimir.cli import main
from mimir.importers.nornskept import import_kept
from mimir.runrecord import import_runrecords
from mimir.store import Store
from tests.depsfix import FIXTURES
from tests.helpers import tmpdir
from tests.test_runrecord import make_record
from tests.test_timing_paths import ATTR

NAME = "bm_dag1_log_mod"
FIX = FIXTURES / "structures" / NAME
TREE = FIXTURES / "deps"


def sha(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def make_run(root: Path, name: str, kept: bool = True, seed: int = 1) -> dict[str, object]:
    """A run directory `root/name` with its record, kept files and the keep store `root/_keep`."""
    blif = (FIX / f"{NAME}.blif").read_bytes()
    names = (FIX / f"{NAME}.blif.names").read_bytes()
    rec = copy.deepcopy(make_record(seed=seed))
    rec["design"] = NAME
    rec["inputs"]["netlist"]["sha256"] = sha(blif)
    run = root / name
    run.mkdir(parents=True)
    if kept:
        att = lzma.compress(json.dumps(ATTR).replace("/home/x", "$VTR_ROOT").encode())
        (run / "attribution.json.xz").write_bytes(att)
        kt = {"keep_timing": True, "attribution": True, "blif_sha256": sha(blif),
              "map_sha256": sha(names), "paths_rewritten": {"$VTR_ROOT": 0, "$WS": 0, "~": 0}}
        (run / "keep-timing.json").write_text(json.dumps(kt), encoding="utf-8")
        rec["artifacts"]["timing_attribution"] = {"path": "<run>/attribution.json.xz",
                                                  "sha256": sha(att)}
        rec["artifacts"]["keep_timing"] = {"path": "<run>/keep-timing.json",
                                           "sha256": sha((run / "keep-timing.json").read_bytes())}
        d = root / "_keep" / NAME / sha(blif)
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{NAME}.blif.xz").write_bytes(lzma.compress(blif))
        (d / f"{NAME}.blif.names.xz").write_bytes(lzma.compress(names))
    (run / "mimir-run.json").write_text(json.dumps(rec), encoding="utf-8")
    return rec


def count(store: Store, table: str) -> int:
    return int(store.db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


class KeptImport(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tmpdir())
        self.rec = make_run(self.root, "a")
        make_run(self.root, "b", kept=False, seed=2)
        self.store = Store(self.root / "t.db")
        import_runrecords(self.store, self.root)
        self.blobs = self.root / "blobs"

    def run_import(self, tree: Path | None = TREE) -> list[tuple[str, str]]:
        return import_kept(self.store, self.root, self.blobs, self.root / "_keep", tree).rows

    def test_fills_everything(self) -> None:
        rows = self.run_import()
        self.assertEqual(rows, [("a", "ok"), ("b", "skipped: no kept timing")])
        kinds = dict(self.store.db.execute("SELECT kind, blob_sha256 FROM run_artifact").fetchall())
        self.assertEqual(set(kinds), {"timing", "blif", "map"})
        self.assertEqual(blobs.get_bytes(self.blobs, kinds["blif"]),
                         (FIX / f"{NAME}.blif").read_bytes())
        self.assertEqual(blobs.get_bytes(self.blobs, kinds["map"]),
                         (FIX / f"{NAME}.blif.names").read_bytes())
        self.assertEqual(count(self.store, "timing_run"), 1)
        self.assertEqual(count(self.store, "timing_path"), 2)
        self.assertGreater(count(self.store, "timing_path_node"), 0)
        self.assertEqual(count(self.store, "hdl_graph_run"), 1)
        self.assertGreater(count(self.store, "hdl_edge"), 10)
        self.assertGreater(count(self.store, "hdl_port"), 0)

    def test_idempotent(self) -> None:
        self.run_import()
        before = [count(self.store, t) for t in ("timing_path", "hdl_edge", "hdl_port",
                                                  "run_artifact", "records")]
        self.assertEqual(self.run_import(), [("a", "ok"), ("b", "skipped: no kept timing")])
        self.assertEqual(before, [count(self.store, t) for t in (
            "timing_path", "hdl_edge", "hdl_port", "run_artifact", "records")])

    def test_without_tree_skips_graph(self) -> None:
        self.assertTrue(self.run_import(tree=None)[0][1].startswith("ok (HDL graph not built"))
        self.assertEqual(count(self.store, "timing_path"), 2)
        self.assertEqual(count(self.store, "hdl_graph_run"), 0)
        self.run_import()  # a later run with the tree builds it
        self.assertEqual(count(self.store, "hdl_graph_run"), 1)

    def test_run_without_kept_files_has_no_artifacts(self) -> None:
        self.run_import()
        self.assertEqual(count(self.store, "run"), 2)
        self.assertEqual(count(self.store, "run_artifact"), 3)

    def test_attribution_sha_mismatch_is_an_error(self) -> None:
        (self.root / "a" / "attribution.json.xz").write_bytes(lzma.compress(b"{}"))
        rows = self.run_import()
        self.assertTrue(rows[0][1].startswith("error: attribution sha256"), rows)
        self.assertEqual(count(self.store, "run_artifact"), 0)

    def test_kept_blif_mismatch_is_an_error(self) -> None:
        d = self.root / "_keep" / NAME / str(self.rec["inputs"]["netlist"]["sha256"])  # type: ignore[index]
        (d / f"{NAME}.blif.xz").write_bytes(lzma.compress(b".model x\n.end\n"))
        rows = self.run_import()
        self.assertTrue(rows[0][1].startswith("error: kept blif"), rows)

    def test_home_path_is_scrubbed_or_refused(self) -> None:
        att = lzma.compress(json.dumps(ATTR).encode())  # still holds /home/x
        (self.root / "a" / "attribution.json.xz").write_bytes(att)
        rec = json.loads((self.root / "a" / "mimir-run.json").read_text(encoding="utf-8"))
        rec["artifacts"]["timing_attribution"]["sha256"] = sha(att)
        (self.root / "a" / "mimir-run.json").write_text(json.dumps(rec), encoding="utf-8")
        self.assertEqual(self.run_import()[0], ("a", "ok"))
        for (h,) in self.store.db.execute("SELECT blob_sha256 FROM run_artifact"):
            self.assertNotIn(b"/home/", blobs.get_bytes(self.blobs, h))


class Cli(unittest.TestCase):
    def test_import_norns_runs(self) -> None:
        root = Path(tmpdir())
        make_run(root, "a")
        nornsroot = root / "norns"
        nornsroot.mkdir()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = main(["import", str(root / "t.db"), "norns", "--norns", str(nornsroot),
                       "--runs", str(root), "--blobs", str(root / "blobs"),
                       "--odin3-tree", str(TREE), "--keep-store", str(root / "_keep")])
        self.assertEqual(rc, 0, out.getvalue())
        self.assertIn("kept timing: ok 1", out.getvalue())
        db = sqlite3.connect(root / "t.db")
        self.assertEqual(db.execute("SELECT COUNT(*) FROM timing_path").fetchone()[0], 2)
        self.assertGreater(db.execute("SELECT COUNT(*) FROM hdl_edge").fetchone()[0], 0)


REPORT = """#Timing report of worst 2 path(s)

#Path 1
Startpoint: a.inpad[0] (.input clocked by virtual_io_clock)
Endpoint  : out:z.outpad[0] (.output clocked by virtual_io_clock)
Path Type : setup

data required time                                                         9.000
data arrival time                                                         -6.000
--------------------------------------------------------------------------------
slack (MET)                                                                3.000

#Path 2
Startpoint: b.inpad[0] (.input clocked by virtual_io_clock)
Endpoint  : out:y.outpad[0] (.output clocked by virtual_io_clock)
Path Type : setup

data required time                                                         9.000
data arrival time                                                         -5.000
--------------------------------------------------------------------------------
slack (MET)                                                                4.000
"""


def make_report_run(root: Path, name: str, seed: int = 3) -> None:
    """A report-only run: kept report and keep-timing.json, no attribution, no name map."""
    rec = copy.deepcopy(make_record(seed=seed))
    run = root / name
    run.mkdir(parents=True)
    gz = gzip.compress(REPORT.encode())
    (run / "report_timing.setup.rpt.gz").write_bytes(gz)
    (run / "keep-timing.json").write_text(json.dumps({"attribution": False, "map_sha256": None,
                                                      "paths_requested": 1000}), encoding="utf-8")
    rec["artifacts"]["timing_report_gz"] = {"path": "<run>/report_timing.setup.rpt.gz",
                                            "sha256": sha(gz)}
    rec["artifacts"]["keep_timing"] = {"path": "<run>/keep-timing.json",
                                       "sha256": sha((run / "keep-timing.json").read_bytes())}
    (run / "mimir-run.json").write_text(json.dumps(rec), encoding="utf-8")


class ReportOnly(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tmpdir())
        make_report_run(self.root, "r")
        self.store = Store(self.root / "t.db")
        import_runrecords(self.store, self.root)
        self.blobs = self.root / "blobs"

    def run_import(self) -> list[tuple[str, str]]:
        return import_kept(self.store, self.root, self.blobs).rows

    def test_fills_timing_from_report(self) -> None:
        self.assertEqual(self.run_import(), [("r", "ok (report only: no attribution)")])
        row = self.store.db.execute("SELECT source_kind, paths_in_report, paths_requested, "
                                    "worst_slack_ns FROM timing_run").fetchone()
        self.assertEqual(tuple(row), ("report", 2, 1000, 3.0))
        self.assertGreater(count(self.store, "timing_path_hist"), 0)
        kinds = [r[0] for r in self.store.db.execute("SELECT kind FROM run_artifact")]
        self.assertEqual(kinds, ["timing_report"])
        self.assertEqual(count(self.store, "hdl_graph_run"), 0)

    def test_idempotent(self) -> None:
        self.run_import()
        tables = ("timing_run", "timing_path_hist", "timing_object", "run_artifact", "records")
        before = [count(self.store, t) for t in tables]
        self.assertEqual(self.run_import(), [("r", "ok (report only: no attribution)")])
        self.assertEqual(before, [count(self.store, t) for t in tables])

    def test_sha_mismatch_is_an_error(self) -> None:
        (self.root / "r" / "report_timing.setup.rpt.gz").write_bytes(gzip.compress(b"x"))
        self.assertTrue(self.run_import()[0][1].startswith("error: report sha256"))
        self.assertEqual(count(self.store, "timing_run"), 0)


if __name__ == "__main__":
    unittest.main()
