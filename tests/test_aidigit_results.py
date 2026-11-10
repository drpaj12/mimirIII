"""AI digit recognition results in the store (schema 8): importer, migration, table, plots."""

from __future__ import annotations

import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from mimir import aidigit, aidigittable
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
        self.assertEqual(dict(self.data.per_impl()), {"I1": 6, "I3": 8, "I4": 6, "I6": 8, "I8": 6})

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


class Import(unittest.TestCase):
    def test_import_is_idempotent_and_replaces(self) -> None:
        store, d = _store()
        data = aidigit.load(SUITE)
        self.assertEqual(aidigit.write(store, data), (34, len(data.nulls)))
        first = aidigit.read_rows(store.db)
        aidigit.write(store, data)
        self.assertEqual(aidigit.read_rows(store.db), first)
        self.assertEqual(store.db.execute("SELECT COUNT(*) FROM aidigit_result").fetchone()[0], 34)
        aidigit.write(store, aidigit.Imported())  # an emptied input empties the suite's rows
        self.assertEqual(store.db.execute("SELECT COUNT(*) FROM aidigit_null").fetchone()[0], 0)
        store.close()

    def test_cli_import_prints_counts(self) -> None:
        d = Path(tempfile.mkdtemp())
        self.assertEqual(main(["import-aidigit", "--db", str(d / "m.db")]), 0)
        db = sqlite3.connect(d / "m.db")
        self.assertEqual(db.execute("SELECT COUNT(*) FROM aidigit_result").fetchone()[0], 34)
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
        self.assertEqual(v, "8")
        self.assertTrue(aidigit.has_tables(s.db))
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

    def test_tex_is_booktabs_and_balanced(self) -> None:
        tex = aidigittable.render_tex(self.rows)
        self.assertEqual(tex.count("\\toprule"), 2)
        self.assertEqual(tex.count("\\begin{table}"), tex.count("\\end{table}"))
        self.assertIn("mult\\_36", tex)
        self.assertIn("250$^\\dagger$", tex)
        self.assertNotIn("†", tex)

    def test_csv_has_one_line_per_row_and_all_columns(self) -> None:
        lines = aidigittable.render_csv(self.rows, self.nulls).splitlines()
        self.assertEqual(len(lines), 35)
        self.assertEqual(lines[0].split(",")[:3], ["suite", "design", "target"])
        self.assertTrue(lines[0].endswith(",null_reasons"))
        self.assertIn("area_alm: quartus not run here", "\n".join(lines))

    def test_plots_exclude_missing_points_and_mark_front(self) -> None:
        plots = {f: svg for f, _, svg in aidigittable.render_plots(self.rows)}
        self.assertEqual(len(plots), 3)
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
        for svg in (out / "plots").iterdir():
            self.assertEqual((docs / "plots" / svg.name).read_text(encoding="utf-8"),
                             svg.read_text(encoding="utf-8"), svg.name)

    def test_table_command_refuses_a_store_without_rows(self) -> None:
        d = Path(tempfile.mkdtemp())
        Store(d / "e.db").close()
        self.assertEqual(main(["aidigit-table", "--db", str(d / "e.db"), "--out-dir",
                               str(d / "o")]), 2)


if __name__ == "__main__":
    unittest.main()
