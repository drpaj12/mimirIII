"""Fix round for the near-critical lane: v4 read-only, exact max_req, truncation, joins, import."""

from __future__ import annotations

import contextlib
import hashlib
import io
import sqlite3
import unittest
from pathlib import Path

from mimir import timing
from mimir.cli import main
from mimir.schema import Record
from mimir.scrub import Scrubber
from mimir.store import Store
from tests.helpers import tmpdir
from tests.test_timing import CLK, FIX, node, row, run_store, tinput

FULL_RPT = ("#Timing report of worst 100 path(s)\n\n"
            "#Path 1\nStartpoint: a (.latch clocked by clk)\n"
            "Endpoint  : b (.latch clocked by clk)\ndata required time   9.0\n"
            "slack (MET)   1.0\n\n"
            "#Path 2\nStartpoint: a (.latch clocked by clk)\n"
            "Endpoint  : c (.latch clocked by clk)\ndata required time   10.0\n"
            "slack (MET)   4.0\n\n")


def v4_store(d: Path) -> Path:
    path = d / "v4.db"
    s = Store(path)
    s.add([Record("des", "src", "in", "tc", "", "gate", "arch", 1, "a", "", "m.x", "", 3.0,
                  "u", "meas", "1", "o")])
    s.close()
    db = sqlite3.connect(path)
    for t in timing.TIMING_TABLES:
        db.execute(f"DROP TABLE {t}")
    db.execute("UPDATE meta SET value='4' WHERE key='schema_version'")
    db.commit()
    db.close()
    return path


def snap(path: Path) -> tuple[str, int]:
    return hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns


class V4ReadOnly(unittest.TestCase):
    def test_open_leaves_bytes_and_mtime(self) -> None:
        path = v4_store(Path(tmpdir()))
        before = snap(path)
        s = Store(path, readonly=True)
        self.assertFalse(timing.has_tables(s))
        with self.assertRaises(LookupError):
            timing.coverage(s)
        s.close()
        self.assertEqual(snap(path), before)

    def test_every_read_only_command_works_on_v4(self) -> None:
        path = v4_store(Path(tmpdir()))
        before = snap(path)
        csv = str(Path(tmpdir()) / "o.csv")
        cmds = [["coverage", str(path)], ["check", str(path)], ["run-coverage", str(path)],
                ["meta-coverage", str(path)], ["timing-coverage", str(path)],
                ["export", str(path), "--csv", csv]]
        for argv in cmds:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(main(argv), 0, argv)
        self.assertEqual(snap(path), before)

    def test_timing_coverage_message(self) -> None:
        path = v4_store(Path(tmpdir()))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            main(["timing-coverage", str(path)])
        self.assertIn("no timing tables", out.getvalue())

    def test_migrate_command_keeps_records(self) -> None:
        path = v4_store(Path(tmpdir()))
        before = sqlite3.connect(path).execute("SELECT * FROM records ORDER BY 1").fetchall()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["migrate", str(path)]), 0)
        db = sqlite3.connect(path)
        self.assertEqual(db.execute("SELECT * FROM records ORDER BY 1").fetchall(), before)
        self.assertEqual(db.execute("SELECT value FROM meta WHERE key='schema_version'"
                                    ).fetchone()[0], "5")
        self.assertEqual(db.execute("SELECT COUNT(*) FROM timing_run").fetchone()[0], 0)

    def test_v5_store_without_spread_column_gets_it(self) -> None:
        d = Path(tmpdir())
        Store(d / "x.db").close()
        db = sqlite3.connect(d / "x.db")
        db.execute("ALTER TABLE timing_run DROP COLUMN req_spread_ns")
        db.commit()
        db.close()
        Store(d / "x.db", readonly=True).close()
        cols = [r[1] for r in sqlite3.connect(d / "x.db").execute("PRAGMA table_info(timing_run)")]
        self.assertNotIn("req_spread_ns", cols)  # a read open writes nothing
        Store(d / "x.db").close()
        cols = [r[1] for r in sqlite3.connect(d / "x.db").execute("PRAGMA table_info(timing_run)")]
        self.assertIn("req_spread_ns", cols)


class MaxReq(unittest.TestCase):
    def test_spread_and_lower_bound_source(self) -> None:
        paths = [row(1, -2.0, req=0.0), row(2, -1.0, req=-0.5), row(3, -0.5, req=-0.024)]
        res = timing.analyse(tinput(paths, requested=3))
        self.assertEqual(res.stats.dmax_source, "report")
        self.assertAlmostEqual(res.stats.req_spread_ns or 0.0, 0.5)

    def test_exhaustive_when_report_shorter_than_n(self) -> None:
        res = timing.analyse(tinput([row(1, -2.0), row(2, -1.0)], requested=100))
        self.assertEqual(res.stats.dmax_source, "exhaustive")
        self.assertEqual(res.stats.trunc, (0, 0, 0))

    def test_full_report_gives_exact_max_req(self) -> None:
        full = timing.exhaustive_extent(timing.parse_report(FULL_RPT, "00" * 32, 100))
        self.assertEqual(full, ((("clk", "clk"), 10.0, 1.0),))
        # the N=2 attribution holds only the two worst paths of a larger report
        paths = [row(1, 1.0, req=9.0), row(2, 2.0, req=9.0)]
        base = timing.analyse(tinput(paths, requested=2))
        inp = timing.TimingInput(tinput(paths, requested=2).paths, 10.0, 2, 2, "attribution",
                                 "ab" * 32, full)
        exact = timing.analyse(inp)
        self.assertEqual(exact.stats.dmax_source, "full-report")
        self.assertEqual(exact.stats.max_req_ns, 10.0)
        self.assertEqual(base.stats.max_req_ns, 9.0)
        # crit = 1 - slack / max_req: 0.9 for the worst path with the exact 10.0, 0.889 with 9.0
        self.assertEqual(exact.hist, {18: 1, 16: 1})
        self.assertEqual(base.hist, {17: 1, 15: 1})

    def test_cut_report_is_not_exhaustive(self) -> None:
        with self.assertRaises(ValueError):
            timing.exhaustive_extent(timing.parse_report(FULL_RPT, "00" * 32, 2))

    def test_cli_full_report(self) -> None:
        s, rid = run_store()
        s.close()
        rpt = Path(tmpdir()) / "full.rpt"
        rpt.write_text(FULL_RPT)
        with contextlib.redirect_stdout(io.StringIO()):
            rc = main(["import-timing", s.path, str(FIX), "--run-id", rid, "--full-report",
                       str(rpt), "--full-requested", "100"])
        self.assertEqual(rc, 0)
        got = sqlite3.connect(s.path).execute(
            "SELECT dmax_source FROM timing_run").fetchone()[0]
        self.assertEqual(got, "full-report")


class Truncation(unittest.TestCase):
    def test_last_crit_is_per_domain_pair(self) -> None:
        other = timing.PathRow(9, "a (.input clocked by v)", "b (.output clocked by v)",
                               -3.0, 0.0, ())
        paths = [row(1, -10.0), row(2, -2.0), other]  # pair clk: last -2.0 (crit .2); pair v: 1.0
        res = timing.analyse(tinput(paths, requested=3))
        self.assertEqual(res.stats.last_crit, 1.0)
        self.assertEqual(res.stats.trunc, (1, 1, 1))

    def test_unknown_when_no_usable_last_path(self) -> None:
        bad = timing.PathRow(1, f"a {CLK}", f"b {CLK}", 5.0, -1.0, ())
        res = timing.analyse(tinput([bad], requested=1))
        self.assertEqual(res.stats.trunc, (-1, -1, -1))
        s, rid = run_store()
        timing.import_run(s, rid, tinput([bad], requested=1), Scrubber({}))
        metrics = {r[0] for r in s.db.execute("SELECT metric FROM records")}
        self.assertNotIn("timing.truncated_090", metrics)
        self.assertEqual(s.db.execute("SELECT trunc_090 FROM timing_run").fetchone()[0], -1)

    def test_parser_dropped_path_flags_a_cut_report(self) -> None:
        inp = timing.TimingInput(tuple([row(1, -10.0), row(2, -9.9)]), 10.0, 100, 3,
                                 "attribution", "ab" * 32)
        self.assertEqual(timing.analyse(inp).stats.trunc, (1, 1, 1))


class Rounding(unittest.TestCase):
    def test_theta_boundary_is_rounded(self) -> None:
        # slack 1.0 of max_req 10.0 -> crit 0.9 exactly; 1 - 0.1 in floats is 0.9 as well, but
        # 1 - 0.7 / 7.0 is 0.9 only after rounding
        paths = [row(1, 0.7, req=7.0), row(2, 7.0, req=7.0)]
        crit, _, _, _ = timing.path_criticalities(paths)
        self.assertEqual(crit[1], 0.9)
        self.assertEqual(timing.analyse(tinput(paths, requested=100)).stats.n_paths[0], 1)
        self.assertEqual(timing.bin_of(0.35), 7)


class Joins(unittest.TestCase):
    def test_structure_via_line_and_span(self) -> None:
        nodes = (node("d/x.v:5", loc="d/x.v:5.2-5.9"),)
        structs = [("L", "d/x.v:5-5"), ("S", "hdl:d/x.v:5.1-5.20:add")]
        res = timing.analyse(tinput([row(1, -1.0, nodes=nodes)]), structs)
        vias = {k[1]: a.vias for k, a in res.objects.items() if k[0] == "structure"}
        self.assertEqual(vias, {"L": {"line"}, "S": {"span"}})

    def test_same_base_name_other_directory_does_not_join(self) -> None:
        nodes = (node("a/x.v:5"),)
        structs = [("OTHER", "b/x.v:5-5"), ("SAME", "a/x.v:5-5")]
        res = timing.analyse(tinput([row(1, -1.0, nodes=nodes)]), structs)
        self.assertEqual({k[1] for k in res.objects if k[0] == "structure"}, {"SAME"})

    def test_root_placeholder_prefix_joins_and_collision_is_skipped(self) -> None:
        nodes = (node("micro/x.v:5"),)
        one = timing.analyse(tinput([row(1, -1.0, nodes=nodes)]), [("A", "$R/t/micro/x.v:5-5")])
        self.assertEqual({k[1] for k in one.objects if k[0] == "structure"}, {"A"})
        two = timing.analyse(tinput([row(1, -1.0, nodes=nodes)]),
                             [("A", "$R/t/micro/x.v:5-5"), ("B", "$R/u/micro/x.v:5-5")])
        self.assertEqual({k[1] for k in two.objects if k[0] == "structure"}, set())


class ImportRun(unittest.TestCase):
    def test_unknown_run_writes_nothing(self) -> None:
        s, _ = run_store()
        inp = timing.load_attribution_bytes(FIX.read_bytes())
        with self.assertRaises(ValueError):
            timing.import_run(s, "nope", inp, Scrubber({}))
        for t in (*timing.TIMING_TABLES, "records"):
            self.assertEqual(s.db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0], 0, t)

    def test_cli_unknown_run_is_a_clean_error(self) -> None:
        s, _ = run_store()
        s.close()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(main(["import-timing", s.path, str(FIX), "--run-id", "nope"]), 1)
        self.assertIn("no run nope", err.getvalue())

    def test_home_path_in_object_key_rolls_back(self) -> None:
        s, rid = run_store()
        class Leaky(Scrubber):
            def text(self, text: str) -> str:
                return text  # a scrubber that lets a home path through

        bad = (node("/home/someone/x.v:5", module="m"),)
        with self.assertRaises(ValueError):
            timing.import_run(s, rid, tinput([row(1, -1.0, nodes=bad)]), Leaky({}))
        for t in (*timing.TIMING_TABLES, "records"):
            self.assertEqual(s.db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0], 0, t)

    def test_reimport_replaces_stale_truncated_record(self) -> None:
        s, rid = run_store()
        bad = timing.PathRow(1, f"a {CLK}", f"b {CLK}", 5.0, -1.0, ())
        timing.import_run(s, rid, tinput([bad], requested=1), Scrubber({}))
        timing.import_run(s, rid, tinput([row(1, -1.0)], requested=100), Scrubber({}))
        self.assertEqual(s.db.execute(
            "SELECT value FROM records WHERE metric='timing.truncated_090'").fetchone()[0], 0.0)


class FromBlobs(unittest.TestCase):
    def test_attr_dir_and_full_dir(self) -> None:
        import lzma

        from mimir import blobs

        d = Path(tmpdir())
        s, rid = run_store()
        sha = blobs.put_bytes(d / "blobs", FIX.read_bytes())
        s.db.execute("INSERT INTO run_artifact VALUES (?, 'timing', ?)", (rid, sha))
        s.db.commit()
        (d / "full").mkdir()
        (d / "full" / f"{rid}.rpt.xz").write_bytes(lzma.compress(FULL_RPT.encode()))
        rows = timing.import_from_blobs(s, d / "blobs", Scrubber({}), full_dir=d / "full",
                                        full_requested=100)
        self.assertEqual(rows, [(rid, "ok")])
        self.assertEqual(s.db.execute("SELECT dmax_source, analysis_n FROM timing_run"
                                      ).fetchone(), ("full-report", None))
        (d / "attr").mkdir()
        (d / "attr" / f"{rid}.attribution.json").write_bytes(FIX.read_bytes())
        timing.import_from_blobs(s, d / "blobs", Scrubber({}), attr_dir=d / "attr")
        self.assertEqual(s.db.execute("SELECT dmax_source, analysis_n FROM timing_run"
                                      ).fetchone(), ("exhaustive", 100))


if __name__ == "__main__":
    unittest.main()
