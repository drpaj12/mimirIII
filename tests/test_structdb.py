from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock

from mimir import blobs
from mimir.scrub import Scrubber
from mimir.store import Store
from mimir.structcli import detect_one, detect_status, export_tables
from mimir.structdb import (
    DesignInfo,
    build_spec,
    commit_or_unknown,
    import_flow_dir,
    put_structures,
    read_vpr_log,
)
from mimir.structdet import DetectRun
from mimir.structmap import MapRow, Struct, post_levels, set_rows
from tests.depsfix import FIXTURES, deps
from tests.helpers import tmpdir

V3_TABLES = {"structure", "structure_mapping", "structure_member"}
ROOT = Path(__file__).resolve().parent.parent
FLOW = FIXTURES / "flow" / "bm_dag3_lpm"
V2_DB = FIXTURES / "v2-e6f5777.db"
V2_TABLES = ("design", "design_source", "design_meta", "design_lineage", "flow_config",
             "flow_param", "run", "run_artifact", "partition", "analysis_result", "records")


def tables(path: Path) -> set[str]:
    db = sqlite3.connect(path)
    got = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    db.close()
    return got


def dump(path: Path, names: tuple[str, ...]) -> dict[str, list[tuple[object, ...]]]:
    db = sqlite3.connect(path)
    out = {t: sorted(db.execute(f"SELECT * FROM {t}").fetchall(), key=repr) for t in names}
    db.close()
    return out


class MigrationV3Tests(unittest.TestCase):
    def test_v2_store_of_main_e6f5777_migrates_additively(self) -> None:
        """tests/fixtures/v2-e6f5777.db was made by the code of mimirIII main e6f5777 (every v2
        table holds rows). After the migration every row is unchanged and the v3 tables exist."""
        d = Path(tmpdir())
        shutil.copy(V2_DB, d / "v2.db")
        before = dump(d / "v2.db", V2_TABLES)
        self.assertTrue(all(before[t] for t in V2_TABLES), "fixture must fill every v2 table")
        self.assertFalse(V3_TABLES & tables(d / "v2.db"))
        s = Store(d / "v2.db")
        v = s.db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]
        self.assertEqual(v, "5")
        s.close()
        self.assertTrue(tables(d / "v2.db") >= V3_TABLES)
        self.assertEqual(dump(d / "v2.db", V2_TABLES), before)
        s = Store(d / "v2.db", readonly=True)  # a v3 store opens read only
        s.close()

    def test_v3_opens_read_only(self) -> None:
        d = Path(tmpdir())
        Store(d / "x.db").close()
        Store(d / "x.db", readonly=True).close()

    def test_kind_and_granularity_checks(self) -> None:
        s = Store(Path(tmpdir()) / "x.db")
        for kind, gran in (("blob", "block"), ("adder", "wide"), ("comparator", "block")):
            with self.assertRaises(sqlite3.IntegrityError):
                s.db.execute(
                    "INSERT INTO structure VALUES ('d','s',?,'','','hdl',1.0,'r','c',?,'')",
                    (kind, gran))
        s.db.execute("INSERT INTO structure VALUES ('d','s','unknown','','','hdl',NULL,'r','c',"
                     "'block','')")


def fake_map() -> object:
    from types import SimpleNamespace

    def rec(n: int, lv: str, flags: tuple[str, ...] = ()) -> SimpleNamespace:
        return SimpleNamespace(number=n, level=lv, flags=flags)

    return SimpleNamespace(
        records=[rec(1, "ble"), rec(2, "clb"), rec(3, "site", ("x=1", "y=2", "sub=0")),
                 rec(4, "ble"), rec(5, "clb"), rec(6, "site", ("x=3", "y=2", "sub=0"))],
        atoms=[("a", "r1,r2,r3", "-"), ("b", "r1,r2,r3", "-"), ("c", "r4,r5,r6", "-")])


class MappingRowTests(unittest.TestCase):
    def test_post_levels_joins_and_bbox(self) -> None:
        rows = post_levels(fake_map(), {"s1": {"a", "c"}, "s2": {"b"}})
        by = {(r.sid, r.level): r for r in rows}
        self.assertEqual(by[("s1", "ble")].n_bles, 2)
        self.assertEqual(by[("s1", "ble")].joined_with, "s2")  # a and b share the ble r1
        self.assertEqual(by[("s2", "ble")].n_pure, 0)
        self.assertEqual(by[("s1", "clb")].n_pure, 1)
        placed = by[("s1", "placed")]
        self.assertEqual(placed.bbox, (1, 2, 3, 2))
        self.assertEqual(placed.spread, 1.0)
        self.assertEqual(by[("s2", "placed")].spread, 0.0)

    def test_placed_row_counts_sites_not_clbs(self) -> None:
        rows = post_levels(fake_map(), {"s1": {"a", "c"}})
        by = {r.level: r for r in rows}
        self.assertEqual((by["placed"].n_sites, by["placed"].n_clbs), (2, None))
        self.assertEqual((by["clb"].n_clbs, by["clb"].n_sites), (2, None))

    def test_set_rows_without_a_map(self) -> None:
        atoms = {"a": "lut", "b": "ff", "c": "carry"}
        rows = set_rows({"s1": {"a", "b"}, "s2": {"b", "c"}}, atoms, None)
        by = {r.sid: r for r in rows}
        self.assertEqual((by["s1"].n_luts, by["s1"].n_ffs, by["s1"].n_pure), (1, 1, 1))
        self.assertEqual(by["s1"].joined_with, "s2")
        self.assertEqual(by["s2"].n_carry, 1)
        self.assertTrue(all(r.level == "lut" for r in rows))


class ExportTests(unittest.TestCase):
    def build(self, path: Path) -> None:
        s = Store(path)
        structs = [Struct("hdl:f:1.1-1.5", "adder", "f:1-1", "ALWAYS@f:1.1-1.5", "hdl", 0.85),
                   Struct("hdl:g:1.1-1.5", "unknown", "g:1-1", "", "hdl", None)]
        rows = [MapRow("hdl:f:1.1-1.5", "lut", 2, 1, 1, n_luts=2, joined_with="x", spread=None),
                MapRow("hdl:f:1.1-1.5", "placed", 1, 1, 0, n_sites=1, bbox=(1, 1, 2, 2),
                       spread=0.5)]
        put_structures(s, "micro/f", "run1", "cfg1", structs, rows,
                       {"hdl:f:1.1-1.5": {"b", "a"}})
        s.db.commit()
        s.close()

    def test_two_exports_are_byte_identical(self) -> None:
        d = Path(tmpdir())
        self.build(d / "a.db")
        self.build(d / "b.db")
        for name in ("a", "b"):
            export_tables(Store(d / f"{name}.db", readonly=True), d / name)
        for t in V3_TABLES:
            self.assertEqual((d / "a" / f"{t}.csv").read_bytes(),
                             (d / "b" / f"{t}.csv").read_bytes())
        text = (d / "a" / "structure_mapping.csv").read_text(encoding="utf-8")
        self.assertIn("0.5", text)
        self.assertNotIn("\r", text)

    def test_null_and_empty_text_differ(self) -> None:
        d = Path(tmpdir())
        self.build(d / "a.db")
        export_tables(Store(d / "a.db", readonly=True), d / "o")
        lines = (d / "o" / "structure.csv").read_text(encoding="utf-8").split("\n")
        self.assertIn("\\N", lines[1] + lines[2])      # confidence NULL
        self.assertIn(",,", lines[1] + lines[2])       # empty text stays empty

    def test_member_key_has_the_run(self) -> None:
        s = Store(Path(tmpdir()) / "m.db")
        st = [Struct("sid", "adder", "", "", "hdl", 0.5)]
        put_structures(s, "d", "run1", "c", st, [], {"sid": {"a"}})
        put_structures(s, "d", "run2", "c", st, [], {"sid": {"a"}})
        self.assertEqual(s.db.execute("SELECT run_id FROM structure_member ORDER BY 1").fetchall(),
                         [("run1",), ("run2",)])


def fake_vtr(root: Path) -> str:
    """A tiny git repo with the `--seed` entry of read_options.cpp; returns its HEAD."""
    src = root / "vpr" / "src" / "base"
    src.mkdir(parents=True)
    (src / "read_options.cpp").write_text(
        '    place_grp.add_argument(args.seed, "--seed")\n        .help("seed")\n'
        '        .default_value("1")\n', encoding="utf-8")
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    for cmd in (["init", "-q"], ["add", "."], ["commit", "-q", "-m", "x"]):
        subprocess.run(["git", "-C", str(root), *cmd], check=True, env=env, capture_output=True)
    res = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], check=True,
                         capture_output=True, text=True)
    return res.stdout.strip()


class FlowDirTests(unittest.TestCase):
    """import_flow_dir on a committed flow directory (one micro, paths normalised)."""

    def setUp(self) -> None:
        self.cwd = os.getcwd()
        os.chdir(ROOT)  # the fixture's source path is relative to the repo root
        self.tmp = Path(tmpdir())
        self.flow = self.tmp / "flow"
        shutil.copytree(FLOW, self.flow)
        self.vtr = self.tmp / "vtr"
        self.head = fake_vtr(self.vtr)
        run_json = self.flow / "mimir-run.json"
        info = json.loads(run_json.read_text(encoding="utf-8"))
        info["vtr_commit"] = self.head
        run_json.write_text(json.dumps(info), encoding="utf-8")
        self.design = DesignInfo("micro/bm_dag3_lpm", "bm_dag3_lpm", "odin3-micro",
                                 (Path("tests/fixtures/flow/design/bm_dag3_lpm.v"),))

    def tearDown(self) -> None:
        os.chdir(self.cwd)

    def import_it(self, store: Store, vtr: Path | None = None) -> str:
        return import_flow_dir(store, self.tmp / "blobs", self.flow, self.design, deps(),
                               Scrubber({}), "test/flow", vtr if vtr is not None else self.vtr)

    def test_import_fills_every_table_and_is_full(self) -> None:
        s = Store(self.tmp / "s.db")
        rid = self.import_it(s)
        q = s.db.execute
        self.assertEqual(q("SELECT status FROM flow_config").fetchall(), [("full",)])
        self.assertEqual(q("SELECT seed, arch FROM run WHERE run_id=?", (rid,)).fetchone(),
                         (1, "k6_frac_N10_frac_chain_mem32K_40nm.xml"))
        kinds = {r[0] for r in q("SELECT kind FROM run_artifact WHERE run_id=?", (rid,))}
        self.assertTrue({"blif", "map", "net", "place", "route", "log", "timing", "hdl"} <= kinds)
        self.assertEqual(q("SELECT COUNT(*) FROM structure WHERE granularity='block'")
                         .fetchone()[0], 5)
        self.assertEqual(q("SELECT COUNT(*) FROM structure WHERE granularity='operator'")
                         .fetchone()[0], 7)
        self.assertGreater(q("SELECT COUNT(*) FROM structure_member").fetchone()[0], 0)
        levels = {r[0] for r in q("SELECT DISTINCT level FROM structure_mapping")}
        self.assertEqual(levels, {"gate", "lut", "ble", "clb", "placed"})
        self.assertGreater(q("SELECT COUNT(crit_share) FROM structure_mapping").fetchone()[0], 0)
        placed = q("SELECT n_sites, n_clbs FROM structure_mapping WHERE level='placed'").fetchall()
        self.assertTrue(all(n is not None and c is None for n, c in placed))
        self.assertEqual(q("SELECT COUNT(*) FROM records WHERE source='mimir-structures'")
                         .fetchone()[0], 8)
        self.assertEqual(q("SELECT metric FROM records WHERE metric='structure.atoms_unattributed'"
                           ).fetchone()[0], "structure.atoms_unattributed")

    def test_blobs_hold_no_home_path(self) -> None:
        s = Store(self.tmp / "s.db")
        rid = self.import_it(s)
        for kind, sha in s.db.execute("SELECT kind, blob_sha256 FROM run_artifact "
                                      "WHERE run_id=?", (rid,)).fetchall():
            self.assertNotIn(b"/home/", blobs.get_bytes(self.tmp / "blobs", sha), kind)

    def test_reimport_leaves_no_old_member_rows(self) -> None:
        s = Store(self.tmp / "s.db")
        rid = self.import_it(s)
        n = s.db.execute("SELECT COUNT(*) FROM structure_member").fetchone()[0]
        s.db.execute("UPDATE structure_member SET run_id='old'")  # rows of an earlier run
        s.db.commit()
        self.import_it(s)
        self.assertEqual(s.db.execute("SELECT COUNT(*) FROM structure_member").fetchone()[0], n)
        self.assertEqual(s.db.execute("SELECT DISTINCT run_id FROM structure_member").fetchall(),
                         [(rid,)])

    def test_without_the_vtr_checkout_the_config_is_partial(self) -> None:
        s = Store(self.tmp / "s.db")
        import_flow_dir(s, self.tmp / "blobs", self.flow, self.design, deps(), Scrubber({}),
                        "test/flow", None)
        self.assertEqual(s.db.execute("SELECT status FROM flow_config").fetchall(),
                         [("partial",)])
        row = s.db.execute("SELECT conf FROM flow_param WHERE key='seed_default'").fetchone()
        self.assertEqual(row[0], "default-unrecorded")

    def test_retry_run_without_a_seed_is_partial_and_seed_minus_one(self) -> None:
        log = self.flow / "vpr" / "run" / "vpr_stdout.log"
        log.write_text(log.read_text(encoding="utf-8").replace("placer_opts.seed", "placer_opts.x"),
                       encoding="utf-8")
        s = Store(self.tmp / "s.db")
        rid = self.import_it(s)
        self.assertEqual(s.db.execute("SELECT seed FROM run WHERE run_id=?", (rid,)).fetchone()[0],
                         -1)
        self.assertEqual(s.db.execute("SELECT status FROM flow_config").fetchall(),
                         [("partial",)])

    def test_changed_design_file_is_refused(self) -> None:
        s = Store(self.tmp / "s.db")
        info_path = self.flow / "mimir-run.json"
        info = json.loads(info_path.read_text(encoding="utf-8"))
        info["design_sha256"] = "0" * 64
        info_path.write_text(json.dumps(info), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.import_it(s)

    def test_commit_fields(self) -> None:
        self.assertEqual(commit_or_unknown("a" * 40), "a" * 40)
        for bad in ("", "abc", "HEAD", "g" * 40, "A" * 40):
            self.assertEqual(commit_or_unknown(bad), "unknown")

    def test_empty_commit_is_never_given(self) -> None:
        info = json.loads((self.flow / "mimir-run.json").read_text(encoding="utf-8"))
        info["vtr_commit"] = ""
        spec = build_spec(self.flow, info, Scrubber({}), "t", self.vtr)
        self.assertEqual(spec.status(), "partial")
        vtr = next(p for p in spec.params if p[1] == "vtr_commit")
        self.assertEqual(vtr[3], "unknown")

    def test_unbuilt_odin3_commit_is_not_given(self) -> None:
        info = json.loads((self.flow / "mimir-run.json").read_text(encoding="utf-8"))
        info["odin3_built_from_tree"] = False
        spec = build_spec(self.flow, info, Scrubber({}), "t", self.vtr)
        self.assertEqual(spec.status(), "partial")
        self.assertIn("inferred", next(p for p in spec.params if p[1] == "odin3_commit")[4])

    def test_vpr_log_blocks(self) -> None:
        cmd, line, opts = read_vpr_log(self.flow / "vpr" / "run" / "vpr_stdout.log")
        self.assertIn("--route_chan_width", cmd)
        self.assertGreater(line, 1)
        self.assertEqual(opts["placer_opts.seed"][0], "1")


class DetectOneTests(unittest.TestCase):
    def args(self, tmp: Path) -> Namespace:
        return Namespace(odin3_tree=str(tmp / "tree"), loki_src=str(tmp / "loki"), flow_dir=None,
                         blif=str(FIXTURES / "structures" / "bm_dag3_lpm" / "bm_dag3_lpm.blif"),
                         work=str(tmp / "work"), name="x", slug="mcnc20/x",
                         loki_python="python3", wall_limit=5.0, flow_run="")

    def setup_store(self, tmp: Path) -> Store:
        (tmp / "tree").mkdir()
        (tmp / "loki").mkdir()
        s = Store(tmp / "s.db")
        s.db.execute("INSERT INTO design VALUES ('mcnc20/x','h','blif','mcnc20','x','o')")
        s.db.commit()
        return s

    def fake_run(self, code: int, timed_out: bool = False) -> DetectRun:
        return DetectRun(("loki",), code, 1.0, 10.0, Path("."), timed_out, "tail text")

    def test_exit_one_needs_an_overlay_and_differs(self) -> None:
        out = Path(tmpdir())
        self.assertEqual(detect_status(self.fake_run(0), out), "failed")  # no overlay
        (out / "overlay.json").write_text("{}", encoding="utf-8")
        self.assertEqual(detect_status(self.fake_run(0), out), "ok")
        self.assertEqual(detect_status(self.fake_run(1), out), "failed")  # no report
        (out / "report.json").write_text(json.dumps({"final_equiv": {"status": "differs"}}),
                                         encoding="utf-8")
        self.assertEqual(detect_status(self.fake_run(1), out), "differs")
        self.assertEqual(detect_status(self.fake_run(2), out), "failed")
        self.assertEqual(detect_status(self.fake_run(-9, True), out), "timeout")

    def test_a_failed_run_is_recorded_and_stores_no_structure(self) -> None:
        tmp = Path(tmpdir())
        s = self.setup_store(tmp)
        with mock.patch("mimir.structcli.run_loki", return_value=self.fake_run(3)):
            rid = detect_one(s, deps(), tmp / "blobs", self.args(tmp), Scrubber({}))
        row = s.db.execute("SELECT origin FROM run WHERE run_id=?", (rid,)).fetchone()
        self.assertTrue(row[0].startswith("status=failed; exit=3;"))
        self.assertEqual(s.db.execute("SELECT COUNT(*) FROM structure").fetchone()[0], 0)
        self.assertEqual(s.db.execute("SELECT kind FROM run_artifact WHERE run_id=?",
                                      (rid,)).fetchall(), [("detect_log",)])

    def test_lock_note_is_in_the_run_record_and_log(self) -> None:
        tmp = Path(tmpdir())
        s = self.setup_store(tmp)
        args = self.args(tmp)
        args.lock_note = "no heavy lock held, because"
        with mock.patch("mimir.structcli.run_loki", return_value=self.fake_run(3)):
            rid = detect_one(s, deps(), tmp / "blobs", args, Scrubber({}))
        origin = s.db.execute("SELECT origin FROM run WHERE run_id=?", (rid,)).fetchone()[0]
        self.assertTrue(origin.endswith("; no heavy lock held, because"))
        sha = s.db.execute("SELECT blob_sha256 FROM run_artifact WHERE run_id=?",
                           (rid,)).fetchone()[0]
        self.assertIn(b"no heavy lock held", blobs.get_bytes(tmp / "blobs", sha))

    def test_an_error_after_the_run_rolls_the_store_back(self) -> None:
        tmp = Path(tmpdir())
        s = self.setup_store(tmp)
        out = tmp / "work" / "x" / "re"
        out.mkdir(parents=True)
        (out / "overlay.json").write_text(json.dumps({"hypotheses": []}), encoding="utf-8")
        s.db.execute("INSERT INTO structure VALUES ('mcnc20/x','det:old','mux','','',"
                     "'detector:mux',0.9,'r','c','','')")
        s.db.commit()
        with mock.patch("mimir.structcli.run_loki", return_value=self.fake_run(0)), \
                mock.patch("mimir.structcli.read_structs", side_effect=RuntimeError("boom")), \
                self.assertRaises(RuntimeError):
            detect_one(s, deps(), tmp / "blobs", self.args(tmp), Scrubber({}))
        self.assertEqual(s.db.execute("SELECT COUNT(*) FROM run").fetchone()[0], 0)
        self.assertEqual(s.db.execute("SELECT COUNT(*) FROM run_artifact").fetchone()[0], 0)
        self.assertEqual(s.db.execute("SELECT structure_id FROM structure").fetchall(),
                         [("det:old",)])  # the delete of the old detector rows was undone too
