"""Tests of the benchmark catalogue generator and the BLIF/silicon collectors."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mimir import bench, benchcat, benchmeasure

SUITES = '''
[[suite]]
id = "s1"
title = "Suite one"
format = "verilog"
upstream = "https://example.org/s1"
commit = "abc"
external = "s1"
subdir = "."
licence = "MIT"
licence_source = "LICENSE:1"
hosting = "public"
obtained = "clone"

[[suite]]
id = "vtr-blif-k2"
title = "k2"
format = "blif"
upstream = "https://example.org/b"
commit = "abc"
external = "b"
subdir = "2"
licence = "none"
licence_source = "none"
hosting = "unchecked"
obtained = "clone"

[[suite]]
id = "vtr-blif-k4"
title = "k4"
format = "blif"
upstream = "https://example.org/b"
commit = "abc"
external = "b"
subdir = "4"
licence = "none"
licence_source = "none"
hosting = "unchecked"
obtained = "clone"
'''
HEAD = "suite\tdesign\tslug\tpath\tformat\ttop\tbytes\tlines\tsha256\tlicence_rule\n"
DESIGNS = HEAD + "".join(
    f"{s}\t{d}\t-\t{d}.x\t{f}\t{t}\t10\t{n}\t{'0' * 64}\t-\n"
    for s, d, f, t, n in [("s1", "a", "verilog", "a", 7), ("vtr-blif-k2", "c", "blif", "-", 3),
                          ("vtr-blif-k4", "c", "blif", "-", 3)])
MEAS = ("suite\tdesign\tkey\tvalue\tsource\n"
        "s1\ta\tchk_seq\t1\tt\ns1\ta\tvtr_luts\t12\tt\nvtr-blif-k4\tc\tg_gates\t5\tt\n")


def fixture() -> Path:
    d = Path(tempfile.mkdtemp())
    (d / "suites.toml").write_text(SUITES, encoding="utf-8")
    (d / "designs.tsv").write_text(DESIGNS, encoding="utf-8")
    (d / "measures.tsv").write_text(MEAS, encoding="utf-8")
    return d


class CatalogueTest(unittest.TestCase):
    def test_rows_merge_blif_suites(self) -> None:
        idx = fixture()
        rows = benchcat.build_rows(bench.load_designs(idx), benchcat.load_measures(idx))
        self.assertEqual([(r.section, r.design) for r in rows],
                         [("s1", "a"), ("vtr-blif", "c")])
        self.assertEqual(rows[1].format, "blif (k2,k4)")
        self.assertEqual(rows[1].vals["g_gates"], "5")
        self.assertEqual(rows[0].loc, "7")

    def test_deterministic_and_dash_for_unrun(self) -> None:
        idx = fixture()
        out = idx / "c.md"
        benchcat.generate(idx, out, "legend")
        first = (out.read_text(), (idx / "catalogue.tsv").read_text())
        benchcat.generate(idx, out, "legend")
        self.assertEqual(first, (out.read_text(), (idx / "catalogue.tsv").read_text()))
        self.assertIn("| a | verilog | a | 7 | ✓ |", first[0])
        self.assertIn("| 12 |", first[0])
        self.assertNotIn("/home", first[0])

    def test_unknown_key_refused(self) -> None:
        with self.assertRaises(benchcat.CatalogueError):
            benchcat.upsert_measures(fixture(), [["s1", "a", "nope", "1", "t"]])

    def test_blif_counts(self) -> None:
        text = (".model m\n.inputs a b clk\n.outputs o\n.latch a q re clk 0\n"
                ".subckt multiply a=a b=b out=o\n.subckt single_port_ram addr=a\n"
                ".names a o\n1 1\n.end\n")
        c = benchmeasure.blif_counts(text)
        self.assertEqual(c, {"ffs": 1, "pins": 4, "mult": 1, "mem": 1})

    def test_silicon_row(self) -> None:
        d = Path(tempfile.mkdtemp())
        st = {"steps": {"read": "ok", "elab": "ok", "place": "FAILED openroad failed (rc 1)"}}
        got = dict(benchmeasure.silicon_row("x", st, d))
        self.assertEqual(got["si_stage"], "elab")
        self.assertTrue(got["si_lvs"].startswith("out of scope: stopped at place"))
        (d / "census.json").write_text(json.dumps([{"step": "s10_detail_route", "total": 9}]))
        (d / "openroad.log").write_text("[INFO GPL-0016] CoreArea: 2000000\n")
        st = {"steps": {"lvs": "ok"}}
        got = dict(benchmeasure.silicon_row("x", st, d))
        self.assertEqual((got["si_lvs"], got["si_cells"], got["si_area"]), ("match", "9", "2.0"))


if __name__ == "__main__":
    unittest.main()
