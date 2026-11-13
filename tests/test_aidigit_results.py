"""AI digit recognition results in the store (schema 9): importer, migration, table, plots."""

from __future__ import annotations

import importlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from mimir import aidigit, aidigitsheet, aidigittable
from mimir.cli import main
from mimir.store import Store

SUITE = Path(__file__).resolve().parents[1] / "suites" / "ai-digit-recognition"


def _store() -> tuple[Store, Path]:
    d = Path(tempfile.mkdtemp())
    return Store(d / "m.db"), d


class Load(unittest.TestCase):
    def setUp(self) -> None:
        self.data = aidigit.load(SUITE)
        self.by = {(r["design"], r["target"]): r for r in self.data.rows}

    def test_row_counts_per_implementation(self) -> None:
        want = {"I1": 9, "I2": 12, "I3": 12, "I4": 9, "I6": 10, "I7": 15, "I8": 9}
        self.assertEqual(dict(self.data.per_impl()), want)

    def test_i1_n8_vtr_values_are_the_source_values(self) -> None:
        r = self.by[("i1-tpu-n8", "vtr-k6")]
        self.assertEqual((r["area_lut"], r["area_clb"], r["area_mult36"], r["area_ram_blocks"]),
                         (8268, 899, 73, 126))
        self.assertEqual((r["acc_n"], r["acc_label_correct"], r["acc_tier"]), (10000, 9874, "full"))
        self.assertEqual(r["power_channel_width"], 100)
        self.assertEqual(r["speed_ii_cycles"], 609339)
        self.assertAlmostEqual(r["energy_uj_per_img"], 2983.1405766966)
        self.assertEqual(r["model_kind"], "reference network, bit-exact")
        self.assertEqual(r["odin3_commit"], "59349797")
        self.assertEqual(r["design_source_commit"], "8e85de4592fc7df6fa264c06ff9ff0891536e497")

    def test_i2_pico_fm_values_and_tiers(self) -> None:
        r = self.by[("i2-pico-fm", "vtr-k6")]
        self.assertEqual((r["area_lut"], r["area_clb"], r["area_mult36"]), (5567, 448, 0))
        self.assertEqual((r["acc_n"], r["acc_label_correct"], r["acc_tier"]), (10000, 9874, "full"))
        self.assertEqual(r["model_kind"], "reference network, bit-exact")
        self.assertEqual(r["speed_ii_cycles"], 5667193)
        # the two settings with no multiplier and no full-tier run report the quick tier
        self.assertEqual(self.by[("i2-pico-i-gcc", "vtr-k6")]["acc_tier"], "quick")

    def test_i2_pico_m_row_comes_from_the_fixed_front_end(self) -> None:
        r = self.by[("i2-pico-m", "vtr-k6")]
        self.assertEqual((r["area_lut"], r["area_clb"], r["area_mult36"]), (3355, 322, 0))
        self.assertEqual((r["acc_n"], r["acc_label_correct"], r["acc_tier"]), (10000, 9874, "full"))
        self.assertEqual(r["speed_ii_cycles"], 11904561)

    def test_grid_columns_and_clb_use_of_i1_n8(self) -> None:
        r = self.by[("i1-tpu-n8", "vtr-k6")]
        self.assertEqual((r["grid_w"], r["grid_h"], r["grid_tiles"]), (80, 80, 6400))
        self.assertEqual(r["clb_tiles"], 4524)  # VPR prints 4524 clb for 80 x 80
        self.assertAlmostEqual(r["clb_util_pct"], 899 / 4524 * 100)
        self.assertEqual(r["area_min_chan_width"], 88)

    def test_clb_tiles_equal_the_counts_vpr_printed(self) -> None:
        layout = aidigit.load_layouts(SUITE)["k6_frac_N10_frac_chain_mem32K_40nm.xml"]
        # (W, H, clb tiles) from "Resource usage... Architecture ... blocks of type: clb" of the
        # stored VPR logs of the suite's runs
        for w, h, want in ((18, 18, 192), (21, 21, 266), (47, 47, 1530), (78, 78, 4332),
                           (80, 80, 4524), (86, 86, 5292)):
            self.assertEqual(aidigit.clb_tiles(layout, w, h), want, (w, h))

    def test_clb_tiles_match_the_arch_file_when_present(self) -> None:
        root = os.environ.get("VTR_ROOT", "")
        arch = Path(root) / "vtr_flow/arch/timing/k6_frac_N10_frac_chain_mem32K_40nm.xml"
        if not arch.is_file():
            self.skipTest("VTR arch file not available")
        lay = ET.parse(arch).getroot().find("layout/auto_layout")
        assert lay is not None
        cols = sorted((int(c.get("startx", "0")), int(c.get("repeatx", "0")))
                      for c in lay.findall("col") if c.get("type") != "EMPTY")
        want = aidigit.load_layouts(SUITE)["k6_frac_N10_frac_chain_mem32K_40nm.xml"]["columns"]
        self.assertEqual(cols, sorted((c["startx"], c["repeatx"]) for c in want))

    def test_grid_is_null_with_reason_where_absent(self) -> None:
        r = self.by[("nl-A", "vtr-k6")]
        self.assertIsNone(r["grid_w"])
        self.assertIsNone(r["clb_util_pct"])
        nulls = {(d, t, f): why for d, t, f, why in self.data.nulls}
        self.assertIn(("nl-A", "vtr-k6", "grid_w"), nulls)
        self.assertIn(("nl-A", "vtr-k6", "clb_util_pct"), nulls)

    def test_channel_width_is_read_from_the_power_method(self) -> None:
        self.assertEqual(self.by[("tl-T3", "vtr-k6")]["power_channel_width"], 250)
        self.assertEqual(self.by[("tl-T1", "vtr-k6")]["power_channel_width"], 180)

    def test_lut_designs_take_full_tier_accuracy_from_the_leg(self) -> None:
        r = self.by[("nl-A", "cyclonev-lpm")]
        self.assertEqual((r["acc_n"], r["acc_label_correct"]), (10000, 9555))
        self.assertEqual(r["model_kind"], "other model")

    def test_absent_cell_type_counts_zero_and_quartus_fields_are_null_with_reason(self) -> None:
        r = self.by[("tl-T2", "cyclonev-lpm")]
        self.assertEqual((r["lpm_mult"], r["lpm_add_sub"], r["lpm_compare"]), (0, 151, 1004))
        self.assertIsNone(r["area_alm"])
        nulls = {(d, t, f): why for d, t, f, why in self.data.nulls}
        self.assertEqual(nulls[("tl-T2", "cyclonev-lpm", "area_alm")], "quartus not run here")
        self.assertIn("Power Analyzer", nulls[("tl-T2", "cyclonev-lpm", "power_total_mw")])

    def test_failed_flow_rows_are_kept_with_the_reason(self) -> None:
        r = self.by[("nl-A", "vtr-k6")]
        self.assertIsNone(r["area_lut"])
        nulls = {(d, t, f): why for d, t, f, why in self.data.nulls}
        self.assertIn("odin3-flow failed", nulls[("nl-A", "vtr-k6", "area_lut")])
        self.assertIn("odin3-flow failed", nulls[("nl-A", "vtr-k6", "energy_uj_per_img")])

    def test_every_null_in_a_target_field_has_a_reason(self) -> None:
        nulls = {(d, t, f) for d, t, f, _ in self.data.nulls}
        for r in self.data.rows:
            for col in (*aidigit.COMMON_FIELDS, *aidigit.TARGET_FIELDS[r["target"]]):
                if r[col] is None:
                    self.assertIn((r["design"], r["target"], col), nulls)

    def test_unknown_design_and_duplicate_rows_are_refused(self) -> None:
        d = Path(tempfile.mkdtemp())
        shutil.copytree(SUITE / "results", d / "results")
        for name in ("implementations.toml", "pins.toml"):
            shutil.copy(SUITE / name, d / name)
        toml = (d / "implementations.toml").read_text(encoding="utf-8")
        (d / "implementations.toml").write_text(
            toml.replace('[[design]]\nid = "tl-T3"', '[[design]]\nid = "gone"', 1),
            encoding="utf-8")
        with self.assertRaises(ValueError) as ctx:
            aidigit.load(d)
        self.assertIn("tl-T3", str(ctx.exception))
        (d / "implementations.toml").write_text(toml, encoding="utf-8")
        extra = (d / "results" / "vtr.jsonl").read_text(encoding="utf-8")
        with open(d / "results" / "lpm.jsonl", "a", encoding="utf-8") as fh:
            fh.write(extra.splitlines()[0].replace('"vtr-k6"', '"cyclonev-lpm"') + "\n")
        with self.assertRaises(ValueError):
            aidigit.load(d)


class HostPaths(unittest.TestCase):
    # bnn-lpm.jsonl (merged earlier, PR 57) still carries one host path in an error text
    KNOWN = {"bnn-lpm.jsonl"}

    def test_no_result_row_holds_a_host_path(self) -> None:
        for f in sorted((SUITE / "results").glob("*.jsonl")):
            if f.name in self.KNOWN:
                continue
            for n, line in enumerate(f.read_text().splitlines(), 1):
                self.assertNotIn("/" + "home/", line, f"{f.name}:{n}")


class Import(unittest.TestCase):
    def test_import_is_idempotent_and_replaces(self) -> None:
        store, d = _store()
        data = aidigit.load(SUITE)
        self.assertEqual(aidigit.write(store, data), (76, len(data.nulls)))
        first = aidigit.read_rows(store.db)
        aidigit.write(store, data)
        self.assertEqual(aidigit.read_rows(store.db), first)
        self.assertEqual(store.db.execute("SELECT COUNT(*) FROM aidigit_result").fetchone()[0], 76)
        aidigit.write(store, aidigit.Imported())  # an emptied input empties the suite's rows
        self.assertEqual(store.db.execute("SELECT COUNT(*) FROM aidigit_null").fetchone()[0], 0)
        store.close()

    def test_cli_import_prints_counts(self) -> None:
        d = Path(tempfile.mkdtemp())
        self.assertEqual(main(["import-aidigit", "--db", str(d / "m.db")]), 0)
        db = sqlite3.connect(d / "m.db")
        self.assertEqual(db.execute("SELECT COUNT(*) FROM aidigit_result").fetchone()[0], 76)
        db.close()


class Migration(unittest.TestCase):
    def test_v7_store_migrates_to_v8_and_reads_as_it_is(self) -> None:
        d = Path(tempfile.mkdtemp())
        Store(d / "x.db").close()
        db = sqlite3.connect(d / "x.db")
        db.execute("DROP TABLE aidigit_result")
        db.execute("DROP TABLE aidigit_null")
        db.execute("UPDATE meta SET value='7' WHERE key='schema_version'")
        db.commit()
        db.close()
        ro = Store(d / "x.db", readonly=True)
        self.assertFalse(aidigit.has_tables(ro.db))
        ro.close()
        s = Store(d / "x.db")
        v = s.db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]
        self.assertEqual(v, "10")
        self.assertTrue(aidigit.has_tables(s.db))
        s.close()


class MigrationV8(unittest.TestCase):
    def test_v8_store_gains_the_grid_columns_and_keeps_rows(self) -> None:
        d = Path(tempfile.mkdtemp())
        s = Store(d / "x.db")
        aidigit.write(s, aidigit.load(SUITE))
        s.close()
        db = sqlite3.connect(d / "x.db")
        # rebuild the table as version 8 had it
        db.execute("ALTER TABLE aidigit_result DROP COLUMN clb_util_pct")
        for col in ("grid_w", "grid_h", "grid_tiles", "clb_tiles"):
            db.execute(f"ALTER TABLE aidigit_result DROP COLUMN {col}")
        db.execute("UPDATE meta SET value='8' WHERE key='schema_version'")
        db.commit()
        db.close()
        ro = Store(d / "x.db", readonly=True)
        old = aidigit.read_rows(ro.db)
        self.assertEqual(len(old), 76)
        self.assertNotIn("grid_w", old[0])
        ro.close()
        s = Store(d / "x.db")
        new = aidigit.read_rows(s.db)
        self.assertEqual(len(new), 76)
        self.assertIsNone(new[0]["grid_w"])
        self.assertEqual({k: v for k, v in new[0].items() if k in old[0]}, old[0])
        s.close()


class MigrationV9(unittest.TestCase):
    def test_v9_store_opens_and_gains_the_odin_columns(self) -> None:
        from mimir.schema import AIDIGIT_V10_COLUMNS

        d = Path(tempfile.mkdtemp())
        s = Store(d / "x.db")
        aidigit.write(s, aidigit.load(SUITE))
        s.close()
        db = sqlite3.connect(d / "x.db")
        for name, _ in AIDIGIT_V10_COLUMNS:
            db.execute(f"ALTER TABLE aidigit_result DROP COLUMN {name}")
        db.execute("UPDATE meta SET value='9' WHERE key='schema_version'")
        db.commit()
        db.close()
        s = Store(d / "x.db")
        rows = aidigit.read_rows(s.db)
        self.assertEqual(len(rows), 76)
        self.assertIn("odin_sim_status", rows[0])
        s.close()


class Table(unittest.TestCase):
    def setUp(self) -> None:
        self.store, _ = _store()
        aidigit.write(self.store, aidigit.load(SUITE))
        self.rows = aidigit.read_rows(self.store.db)
        self.nulls = aidigit.read_nulls(self.store.db)

    def test_pareto_front_known_answer(self) -> None:
        pts = [(1.0, 90.0, "a"), (2.0, 95.0, "b"), (3.0, 94.0, "c"), (0.5, 80.0, "d"),
               (2.0, 95.0, "e")]
        self.assertEqual(aidigittable.pareto_front(pts), {"a", "b", "d", "e"})

    def test_markdown_marks_other_width_and_missing(self) -> None:
        md = aidigittable.render_md(self.rows, [("t", "plots/p.svg")], self.nulls)
        line = next(x for x in md.splitlines() if x.startswith("| I8 | tl-T3 | T3"))
        self.assertIn("250†", line)
        self.assertIn("| 17,428 |", line)
        nl_a = next(x for x in md.splitlines() if x.startswith("| I6 | nl-A | A "))
        self.assertIn("n/a", nl_a)
        self.assertIn("No VTR point", md)

    def test_table_shows_grid_and_clb_use(self) -> None:
        md = aidigittable.render_md(self.rows, [], self.nulls)
        self.assertIn("| Grid |", md)
        self.assertIn("80x80", md)
        self.assertIn("CLB use %", md)
        self.assertIn("the largest resource column (RAM, DSP or CLB) sets the size", md)
        self.assertIn("CLB use (\\%)", aidigittable.render_tex(self.rows))

    def test_tex_is_booktabs_and_balanced(self) -> None:
        tex = aidigittable.render_tex(self.rows)
        self.assertEqual(tex.count("\\toprule"), 3)
        self.assertEqual(tex.count("\\begin{table}"), tex.count("\\end{table}"))
        self.assertIn("mult\\_36", tex)
        self.assertIn("250$^\\dagger$", tex)
        self.assertNotIn("†", tex)

    def test_csv_has_one_line_per_row_and_all_columns(self) -> None:
        lines = aidigittable.render_csv(self.rows, self.nulls).splitlines()
        self.assertEqual(len(lines), 77)
        self.assertEqual(lines[0].split(",")[:3], ["suite", "design", "target"])
        self.assertTrue(lines[0].endswith(",null_reasons"))
        self.assertIn("area_alm: quartus not run here", "\n".join(lines))

    def test_plots_exclude_missing_points_and_mark_front(self) -> None:
        plots = {f: svg for f, _, svg in aidigittable.render_plots(self.rows)}
        self.assertEqual(len(plots), 5)
        svg = plots["pareto-accuracy-lut.svg"]
        self.assertNotIn(">nl-A<", svg)
        self.assertIn(">tl-T3<", svg)
        self.assertIn("polyline", plots["pareto-accuracy-latency.svg"])

    def test_committed_table_is_current(self) -> None:
        out = Path(tempfile.mkdtemp())
        aidigittable.write_all(self.rows, self.nulls, out)
        docs = SUITE / "docs"
        for name in ("TABLE.md", "TABLE.csv", "TABLE.tex"):
            self.assertEqual((docs / name).read_text(encoding="utf-8"),
                             (out / name).read_text(encoding="utf-8"), name)
        for sheet in (out / "datasheets").iterdir():
            self.assertEqual((docs / "datasheets" / sheet.name).read_text(encoding="utf-8"),
                             sheet.read_text(encoding="utf-8"), sheet.name)
        for svg in (out / "plots").iterdir():
            self.assertEqual((docs / "plots" / svg.name).read_text(encoding="utf-8"),
                             svg.read_text(encoding="utf-8"), svg.name)

    def test_table_command_refuses_a_store_without_rows(self) -> None:
        d = Path(tempfile.mkdtemp())
        Store(d / "e.db").close()
        self.assertEqual(main(["aidigit-table", "--db", str(d / "e.db"), "--out-dir",
                               str(d / "o")]), 2)


class Fixes(unittest.TestCase):
    def test_migrate_accepts_db_flag_and_positional(self) -> None:
        d = Path(tempfile.mkdtemp())
        Store(d / "a.db").close()
        Store(d / "b.db").close()
        self.assertEqual(main(["migrate", str(d / "a.db")]), 0)
        self.assertEqual(main(["migrate", "--db", str(d / "b.db")]), 0)
        self.assertEqual(main(["migrate", str(d / "a.db"), "--db", str(d / "b.db")]), 2)
        self.assertEqual(main(["migrate"]), 2)

    def test_power_mem_cap_follows_the_route_step(self) -> None:
        sys.path.insert(0, str(SUITE / "score"))
        sys.dont_write_bytecode = True
        common = importlib.import_module("common")
        self.assertEqual(common.mem_cap_for(""), "2G")
        self.assertEqual(common.mem_cap_for("(max_rss 300.0 MiB)"), "2G")
        self.assertEqual(common.mem_cap_for("max_rss 100.0 MiB\nmax_rss 2538.0 MiB"), "5G")
        self.assertEqual(common.mem_cap_for("max_rss 9000.0 MiB"), "8G")


class FixedAndOdin(unittest.TestCase):
    def _suite(self) -> Path:
        d = Path(tempfile.mkdtemp()) / "suite"
        (d / "results").mkdir(parents=True)
        for name in ("implementations.toml", "pins.toml"):
            shutil.copy(SUITE / name, d / name)
        for f in (SUITE / "results").glob("*.jsonl"):
            shutil.copy(f, d / "results" / f.name)
        return d

    def test_fixed_row_and_odin_row_are_imported(self) -> None:
        d = self._suite()
        fixed = {"schema": 1, "design": "i3-df-p1", "target": "vtr-k6-fixed", "tier": "quick",
                 "area": {"luts": 1481, "ffs": 1452, "clbs": 180, "adders": 787, "grid": [170, 170],
                          "min_chan_width": None, "wirelength": 22427, "dsp_mult36": 10,
                          "ram_blocks": 28},
                 "speed": {"crit_path_ns": 6.7, "fmax_mhz": 149.1, "cycles_per_img": 182666,
                           "latency_us": 1224.9},
                 "power": {"total_mw": 1313.0, "dynamic_mw": 407.7, "static_mw": 905.3,
                           "energy_uj_per_img": 1608.2,
                           "method": "ACE2 vectorless (-s 1) + VPR --power, W=320, fixed grid"},
                 "tools": {"arch": "k6_frac_N10_frac_chain_mem32K_40nm.xml"},
                 "null_reason": {"area.min_chan_width": "not searched: channel width fixed at 320"},
                 "accuracy": None, "notes": []}
        odin = {"schema": 1, "design": "i3-df-p1", "odin3_build": "odin3 1.6.1 (rel-v161)",
                "odin_sim": {"n": 100, "class_match": 100, "score_match": 100,
                             "cycles_total": 1000, "wall_s": 10.0}, "error": None}
        bad = {"schema": 1, "design": "i3-df-p2", "odin3_build": "odin3 1.6.1 (rel-v161)",
               "odin_sim": None, "error": "exit 1: odin3: error: unsupported cell"}
        (d / "results" / "fixed-vtr.jsonl").write_text(json.dumps(fixed) + "\n")
        (d / "results" / "odin-sim.jsonl").write_text(json.dumps(odin) + "\n"
                                                      + json.dumps(bad) + "\n")
        data = aidigit.load(d)
        rows = {(r["design"], r["target"]): r for r in data.rows}
        fx = rows[("i3-df-p1", "vtr-k6-fixed")]
        self.assertEqual((fx["area_grid"], fx["power_channel_width"], fx["grid_w"]),
                         ("170x170", 320, 170))
        self.assertEqual(fx["vtr_commit"], "3c9a4d23b2")
        self.assertAlmostEqual(fx["clb_util_pct"], 180 / aidigit.clb_tiles(
            aidigit.load_layouts(d)["k6_frac_N10_frac_chain_mem32K_40nm.xml"], 170, 170) * 100)
        nulls = {(a, b, c): w for a, b, c, w in data.nulls}
        self.assertIn("not searched", nulls[("i3-df-p1", "vtr-k6-fixed", "area_min_chan_width")])
        ok = rows[("i3-df-p1", "vtr-k6")]
        self.assertEqual((ok["odin_sim_status"], ok["odin_sim_class_match"]), ("pass", 100))
        self.assertAlmostEqual(ok["odin_sim_cycles_per_s"], 100.0)
        err = rows[("i3-df-p2", "vtr-k6")]
        self.assertEqual(err["odin_sim_status"], "error")
        self.assertIn("unsupported cell", nulls[("i3-df-p2", "vtr-k6", "odin_sim_n")])
        s = Store(d / "s.db")
        aidigit.write(s, data)
        self.assertEqual(len(aidigit.read_rows(s.db)), 57)
        s.close()

    def test_datasheet_per_design(self) -> None:
        d = self._suite()
        s = Store(d / "s.db")
        aidigit.write(s, aidigit.load(d))
        rows, nulls = aidigit.read_rows(s.db), aidigit.read_nulls(s.db)
        s.close()
        sheets = aidigitsheet.write_all(rows, nulls, d / "docs")
        self.assertEqual(len(sheets), 28)
        text = sheets[d / "docs" / "datasheets" / "i1-tpu-n8.md"]
        self.assertIn("# Datasheet: i1-tpu-n8", text)
        self.assertIn("3c9a4d23b2", text)
        self.assertIn("Odin III `sim_tb`, RTL | error", text)


if __name__ == "__main__":
    unittest.main()
