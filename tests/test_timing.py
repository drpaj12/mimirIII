from __future__ import annotations

import json
import sqlite3
import unittest
from pathlib import Path

from mimir import timing
from mimir.cli import main
from mimir.scrub import Scrubber
from mimir.store import Store
from tests.helpers import tmpdir

FIX = Path(__file__).parent / "fixtures" / "timing" / "bm_DL_BCD_adder.attribution.json"
CLK = "(.latch clocked by clk)"


def row(i: int, slack: float, req: float = 0.0, end: str | None = None,
        nodes: tuple[timing.Node, ...] = ()) -> timing.PathRow:
    return timing.PathRow(i, f"a {CLK}", f"{end or 'e' + str(i)} {CLK}", slack, req, nodes)


def node(span: str, word: str = "", bit: int = -1, via: str = "", delay: float = 1.0,
         module: str = "m", loc: str = "") -> timing.Node:
    return timing.Node(module, span, loc, word, bit, via, delay)


def tinput(paths: list[timing.PathRow], requested: int | None = 100,
           in_report: int | None = None) -> timing.TimingInput:
    return timing.TimingInput(tuple(paths), 10.0, requested, in_report or len(paths),
                              "attribution", "ab" * 32)


def run_store() -> tuple[Store, str]:
    s = Store(Path(tmpdir()) / "t.db")
    s.db.execute(
        "INSERT INTO run VALUES ('r1', 'slug', 'cfg', 'src', 'des', 'arch', 1, 'a', '', '', "
        "NULL, NULL, NULL, NULL, 'o', 'tc', 'in')")
    s.db.commit()
    return s, "r1"


class Crit(unittest.TestCase):
    def test_known_answer_negative_slack(self) -> None:
        # worst -10, req 0: shift 10, crit = 1 - (slack + 10) / 10 = -slack / 10
        paths = [row(1, -10.0), row(2, -9.5), row(3, -9.0), row(4, -5.0), row(5, -1.0)]
        crit, pairs, skipped, req = timing.path_criticalities(paths)
        self.assertEqual((pairs, skipped, req), (1, 0, 0.0))
        self.assertEqual([round(crit[i], 6) for i in range(1, 6)], [1.0, 0.95, 0.9, 0.5, 0.1])

    def test_met_timing_uses_no_shift(self) -> None:
        crit, _, _, _ = timing.path_criticalities([row(1, 1.0, 10.0), row(2, 4.0, 10.0)])
        self.assertAlmostEqual(crit[1], 0.9)
        self.assertAlmostEqual(crit[2], 0.6)

    def test_domain_pairs_are_separate(self) -> None:
        other = timing.PathRow(2, "a (.input clocked by v)", "b (.output clocked by v)",
                               -2.0, 0.0, ())
        crit, pairs, _, _ = timing.path_criticalities([row(1, -10.0), other])
        self.assertEqual(pairs, 2)
        self.assertEqual(crit[2], 1.0)  # worst of its own pair

    def test_unusable_pair_is_skipped_and_counted(self) -> None:
        bad = timing.PathRow(1, f"a {CLK}", f"b {CLK}", 5.0, -1.0, ())
        crit, pairs, skipped, _ = timing.path_criticalities([bad])
        self.assertEqual((crit, pairs, skipped), ({}, 1, 1))

    def test_bins(self) -> None:
        self.assertEqual([timing.bin_of(c) for c in (0.0, 0.049, 0.05, 0.95, 1.0)],
                         [0, 0, 1, 19, 19])


class Analyse(unittest.TestCase):
    def test_counts_endpoints_hist_and_truncation(self) -> None:
        paths = [row(1, -10.0, end="x"), row(2, -9.5, end="x"), row(3, -9.0, end="y"),
                 row(4, -5.0), row(5, -0.5)]
        res = timing.analyse(tinput(paths, requested=5))
        s = res.stats
        self.assertEqual(s.n_paths, (3, 2, 1))
        self.assertEqual(s.n_endpoints, (2, 1, 1))
        self.assertEqual(res.hist, {1: 1, 10: 1, 18: 1, 19: 2})
        self.assertEqual(s.trunc, (0, 0, 0))  # the last path has crit 0.05
        full = timing.analyse(tinput([row(1, -10.0), row(2, -9.7)], requested=2))
        self.assertEqual(full.stats.trunc, (1, 1, 0))  # last crit 0.97, report full
        part = timing.analyse(tinput([row(1, -10.0), row(2, -9.7)], requested=100))
        self.assertEqual(part.stats.trunc, (0, 0, 0))  # fewer paths than asked: complete

    def test_object_rows_words_and_bits(self) -> None:
        a = node("f.v:3", "S", 1, "name", 2.0)
        b = node("f.v:4", "S", -1, "json-id", 1.0)
        c = node("f.v:5", "T", -1, "declarator", 1.0)
        d = node("f.v:6", "", -1, "", 1.0)
        res = timing.analyse(tinput([row(1, -10.0, nodes=(a, b, c, d)),
                                     row(2, -1.0, nodes=(a,))]))
        o = res.objects
        self.assertEqual(len(o[("word", "m/S", 1)].paths), 2)
        self.assertEqual([k[2] for k in o if k[:2] == ("word", "m/S")], [-1, 1])  # no json-id bit
        self.assertNotIn(("word", "m/T", 0), o)  # declarator: word known, bit unknown
        word = o[("word", "m/S", -1)]
        self.assertEqual(sorted(word.vias), ["json-id", "name"])
        self.assertEqual((len(word.paths), len(word.near[0])), (2, 1))
        self.assertEqual(word.crit_max, 1.0)
        self.assertEqual(o[("module", "m", -1)].delay090, 5.0)
        self.assertNotIn(("word", "m/", -1), o)  # a node with no word joins module and span only
        self.assertIn(("span", "f.v:6", -1), o)

    def test_structure_by_loc_and_line(self) -> None:
        n1 = node("f.v:7", loc="f.v:7.14-7.20")
        n2 = node("f.v:7", loc="f.v:7.2-7.12")
        n3 = node("f.v:8")
        structs = [("s1", "hdl:/x/f.v:7.13-7.24:op"), ("s2", "hdl:/x/f.v:7.2-8.25"),
                   ("d1", ""), ("s3", "/x/f.v:8-8")]
        res = timing.analyse(tinput([row(1, -4.0, nodes=(n1, n2, n3))]), structs)
        keys = {k[1] for k in res.objects if k[0] == "structure"}
        self.assertEqual(keys, {"s1", "s2", "s3"})  # s3: whole line 8, so the line-only n3
        self.assertEqual(res.objects[("structure", "s1", -1)].delay090, 1.0)  # n1 only
        self.assertEqual(res.objects[("structure", "s2", -1)].delay090, 3.0)

    def test_report_parser(self) -> None:
        txt = ("#Path 1\nStartpoint: a (.latch clocked by clk)\n"
               "Endpoint  : b (.latch clocked by clk)\ndata required time   -0.024\n"
               "data required time   -0.024\nslack (VIOLATED)   -3.0\n\n"
               "#Path 2\nStartpoint: a (.latch clocked by clk)\n"
               "Endpoint  : c (.latch clocked by clk)\ndata required time   -0.024\n"
               "slack (VIOLATED)   -2.0\n\n#Path 3\nStartpoint: a\n")
        inp = timing.parse_report(txt, "00" * 32)
        self.assertEqual([p.slack for p in inp.paths], [-3.0, -2.0])
        self.assertEqual(inp.kind, "report")
        res = timing.analyse(inp)
        self.assertEqual(res.objects, {})


class Fixture(unittest.TestCase):
    def test_attribution_fixture(self) -> None:
        data = FIX.read_bytes()
        inp = timing.load_attribution_bytes(data)
        res = timing.analyse(inp)
        # req 0, worst -4.619: crit = -slack / 4.619, so only paths 1 and 2 reach 0.99
        self.assertEqual(res.stats.n_paths, (2, 2, 2))
        self.assertEqual(res.stats.trunc, (0, 0, 0))
        self.assertEqual(res.stats.cpd_ns, 4.61929)
        top = max(res.objects.items(), key=lambda kv: kv[1].delay090)
        self.assertEqual(top[1].crit_max, 1.0)

    def test_import_is_idempotent_and_joins_run(self) -> None:
        s, rid = run_store()
        inp = timing.load_attribution_bytes(FIX.read_bytes())
        _, n1 = timing.import_run(s, rid, inp, Scrubber({}))
        snap = [s.db.execute(f"SELECT * FROM {t} ORDER BY 1, 2, 3").fetchall()
                for t in ("timing_run", "timing_path_hist", "timing_object", "records")]
        _, n2 = timing.import_run(s, rid, inp, Scrubber({}))
        again = [s.db.execute(f"SELECT * FROM {t} ORDER BY 1, 2, 3").fetchall()
                 for t in ("timing_run", "timing_path_hist", "timing_object", "records")]
        self.assertEqual((snap, n1), (again, n2))
        self.assertGreater(n1, 5)
        got = s.db.execute("SELECT run_id FROM record_run WHERE run_id = 'r1' LIMIT 1").fetchone()
        self.assertEqual(got, ("r1",))
        metrics = {r[0] for r in s.db.execute("SELECT metric FROM records")}
        self.assertIn("timing.nc_paths_090", metrics)
        self.assertTrue(timing.check_keys(s, rid))
        raw = Path(s.path).read_bytes()
        self.assertNotIn(b"/home/", raw)
        s.close()

    def test_unknown_schema_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            timing.parse_attribution({"schema_version": 2}, "00")

    def test_cli(self) -> None:
        s, rid = run_store()
        s.close()
        self.assertEqual(main(["import-timing", s.path, str(FIX), "--run-id", rid]), 0)
        db = sqlite3.connect(s.path)
        self.assertEqual(db.execute("SELECT COUNT(*) FROM timing_run").fetchone()[0], 1)
        self.assertEqual(json.loads(FIX.read_text())["schema_version"], 1)


class Migration(unittest.TestCase):
    def test_v4_store_migrates_and_stays_readable(self) -> None:
        d = Path(tmpdir())
        Store(d / "x.db").close()
        db = sqlite3.connect(d / "x.db")
        for t in ("timing_run", "timing_path_hist", "timing_object"):
            db.execute(f"DROP TABLE {t}")
        db.execute("UPDATE meta SET value='4' WHERE key='schema_version'")
        db.commit()
        db.close()
        with self.assertRaises(ValueError):
            Store(d / "x.db", readonly=True)
        s = Store(d / "x.db")
        self.assertEqual(s.db.execute("SELECT COUNT(*) FROM timing_object").fetchone()[0], 0)
        v = s.db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]
        self.assertEqual(v, "5")
        s.close()
        Store(d / "x.db", readonly=True).close()


if __name__ == "__main__":
    unittest.main()
