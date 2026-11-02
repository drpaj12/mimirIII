from __future__ import annotations

import contextlib
import io
import json
import re
import sqlite3
import unittest
from pathlib import Path

from mimir import bench, benchplot, benchreport, remote
from mimir.cli import main
from tests.helpers import tmpdir

SUITES = """\
[[suite]]
id = "{id}"
title = "Suite {id}"
format = "verilog"
upstream = "https://example.org/{id}"
commit = "abcdef0123456789"
external = "repo"
subdir = "src"
glob = "*.v"
licence = "MIT"
licence_source = "LICENSE:1"
hosting = "public"
obtained = "clone"
"""
FLOWS = """\
[[flow]]
id = "f1"
tool = "odin3"
tool_version = "1"
tool_commit = "c1"
binary_sha256 = "b"
input = "verilog"
arch = "arch1"
lut_k = 6
script = "s"
source = "test"
"""
H = "0123456789abcdef" * 4


def _design(suite: str, name: str, slug: str, nbytes: int, sha: str) -> bench.Design:
    return bench.Design(suite, name, slug, f"{name}.v", "verilog", name, nbytes, nbytes // 10,
                        sha, "-")


def _registry(root: Path) -> None:
    (root / "suites.toml").write_text(SUITES.format(id="sa") + "\n" + SUITES.format(id="sb"))
    (root / "flows.toml").write_text(FLOWS)
    bench.save_designs(root, [
        _design("sa", "a1", "x/a1", 100, "1" * 64), _design("sa", "a2", "-", 1000, H),
        _design("sa", "a3", "-", 10000, "3" * 64), _design("sb", "b1", "-", 500, "4" * 64)])
    pub, priv = "5" * 64, "6" * 64
    bench.save_netlists(root, [
        bench.Netlist("sa", "a1", "f1", pub, 10, "-", "-", "$WS/secret/path.blif"),
        bench.Netlist("sa", "a2", "f1", priv, 10, "-", "-", "$WS/other.blif")])
    rows = f"{pub}\t1\t1\t-\tpublic\n{priv}\t1\t1\t-\tprivate\n"
    remote.write_xz(root / "blobs.tsv.xz", rows.encode())


def _store(path: Path) -> None:
    con = sqlite3.connect(path)
    con.executescript("""
    CREATE TABLE design (slug TEXT, design_hash TEXT, hash_kind TEXT, suite TEXT, name TEXT,
                         origin TEXT);
    CREATE TABLE design_source (source TEXT, name TEXT, slug TEXT);
    CREATE TABLE records (design TEXT, source TEXT, level TEXT, arm TEXT, bin TEXT,
                          metric TEXT, value REAL);
    INSERT INTO design VALUES ('x/a1', 'h1', 'blif', 's', 'a1', 'o'),
                              ('y/q', '""" + H + """', 'blif', 's', 'q', 'o');
    INSERT INTO design_source VALUES ('src', 'a1', 'x/a1'), ('src', 'q', 'y/q');
    """)
    recs = [("a1", "src", "struct.size", 50), ("a1", "src", "struct.depth", 4),
            ("a1", "src", "rent.p", 0.5), ("a1", "src", "rent.p", 0.7),
            ("q", "src", "struct.size", 500), ("b1", "src2", "struct.size", 9)]
    con.executemany("INSERT INTO records VALUES (?, ?, 'lut', '', '', ?, ?)", recs)
    con.commit()
    con.close()


class ReportTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tmpdir())
        self.idx = self.tmp / "idx"
        self.idx.mkdir()
        _registry(self.idx)
        self.db = self.tmp / "store.db"
        _store(self.db)

    def test_join_and_metrics(self) -> None:
        rep = benchreport.collect(self.idx, self.db, "2026-01-01", "deadbeef")
        by = {(r.suite, r.design): r for r in rep.rows}
        self.assertEqual(by[("sa", "a1")].join, "slug")
        self.assertEqual(by[("sa", "a2")].join, "hash")
        self.assertEqual(by[("sa", "a3")].join, "-")
        self.assertAlmostEqual(by[("sa", "a1")].metrics["rent.p"], 0.6)
        self.assertEqual(by[("sa", "a2")].metrics["struct.size"], 500.0)
        self.assertEqual(rep.joins["slug"], 1)
        self.assertEqual(rep.withheld_netlists, 1)
        self.assertEqual(rep.flows["f1"], 1)

    def test_cli_page(self) -> None:
        out = self.tmp / "o" / "index.html"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main(["bench", "report", "--index", str(self.idx), "--html", str(out),
                       "--db", str(self.db), "--date", "2026-01-01", "--commit", "deadbeef"])
        self.assertEqual(rc, 0)
        page = out.read_text()
        self.assertIn("deadbeef", page)
        self.assertIn("mimir bench fetch", page)
        self.assertNotIn("/home/", page)
        self.assertNotIn("secret", page)
        self.assertNotIn("$WS", page)
        found = re.search(r'id="data"[^>]*>(.*?)</script>', page, re.S)
        assert found is not None
        data = json.loads(found.group(1))
        self.assertEqual(len(data["rows"]), 4)
        self.assertEqual(page.count("<svg"), 6)  # sizes, 3 store metrics, flows

    def test_without_store(self) -> None:
        out = self.tmp / "p.html"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["bench", "report", "--index", str(self.idx),
                                   "--html", str(out)]), 0)
        self.assertIn("No store given", out.read_text())

    def test_missing_store(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            rc = main(["bench", "report", "--index", str(self.idx), "--html",
                       str(self.tmp / "x.html"), "--db", str(self.tmp / "none.db")])
        self.assertEqual(rc, 1)

    def test_store_not_written(self) -> None:
        before = self.db.read_bytes()
        benchreport.collect(self.idx, self.db, "2026-01-01")
        self.assertEqual(self.db.read_bytes(), before)


class PlotTest(unittest.TestCase):
    def test_quantile_and_empty(self) -> None:
        self.assertEqual(benchplot.quantile([1.0, 2.0, 3.0], 0.5), 2.0)
        self.assertEqual(benchplot.boxplot("t", "u", [("a", [])]), "")

    def test_log_axis(self) -> None:
        svg = benchplot.boxplot("t", "bytes", [("a", [1.0, 10.0, 1000.0])])
        self.assertIn("log scale", svg)
        self.assertNotIn("log scale", benchplot.boxplot("t", "p", [("a", [0.4, 0.6])]))
