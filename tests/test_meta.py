from __future__ import annotations

import tomllib
import unittest
from pathlib import Path

from mimir.meta import (
    Roots,
    derive_lineage,
    import_mcnc_meta,
    meta_coverage,
    register_designs,
    slug_of,
)
from mimir.store import Store
from tests.helpers import tmpdir
from tests.test_store import rec

REPO = Path(__file__).resolve().parents[1]
TOML = REPO / "data/meta/mcnc.toml"


def mk_store() -> tuple[Store, Path]:
    d = Path(tmpdir())
    s = Store(d / "x.db")
    from dataclasses import replace
    s.add([replace(rec("alu4", "m", 1), source="mcnc"),
           replace(rec("alu4", "m", 2), source="mcnc-k2"),
           replace(rec("boundtop", "m", 3), source="norns-r3"),
           replace(rec("d1", "m", 4), source="loki:ds/x")])
    return s, d


class MetaTests(unittest.TestCase):
    def test_slugs(self) -> None:
        self.assertEqual(slug_of("mcnc-k4", "alu4"), ("mcnc20", "mcnc20/alu4"))
        self.assertEqual(slug_of("wyrd-atlas-r7", "sha")[1], "norns/sha")
        self.assertEqual(slug_of("loki:a/b", "d")[1], "loki/a/b/d")

    def test_mcnc_meta_import(self) -> None:
        s, _ = mk_store()
        self.assertEqual(import_mcnc_meta(s, TOML, Roots()), 20)
        self.assertEqual(s.db.execute("SELECT COUNT(*) FROM design").fetchone()[0], 20)
        got = dict(s.db.execute(
            "SELECT field, conf FROM design_meta WHERE slug='mcnc20/alu4'").fetchall())
        self.assertEqual(got["function_class"], "primary")
        self.assertEqual(got["author"], "missing")
        steps = s.db.execute("SELECT tool FROM design_lineage WHERE slug='mcnc20/alu4' "
                             "ORDER BY step_no").fetchall()
        self.assertEqual([t for (t,) in steps][:2], ["original", "SIS"])
        # idempotent: the second import leaves every table as it was
        tables = ("design", "design_meta", "design_lineage")
        before = [s.db.execute(f"SELECT * FROM {t} ORDER BY 1, 2").fetchall() for t in tables]
        self.assertGreater(len(before[2]), 20)
        import_mcnc_meta(s, TOML, Roots())
        after = [s.db.execute(f"SELECT * FROM {t} ORDER BY 1, 2").fetchall() for t in tables]
        self.assertEqual(before, after)

    def test_missing_has_empty_value_and_lineage_conf_is_derived(self) -> None:
        s, _ = mk_store()
        import_mcnc_meta(s, TOML, Roots())
        bad = s.db.execute("SELECT slug, field FROM design_meta "
                           "WHERE conf = 'missing' AND value != ''").fetchall()
        self.assertEqual(bad, [])
        note = s.db.execute("SELECT source FROM design_meta WHERE slug='mcnc20/s38417' "
                            "AND field='intent'").fetchone()[0]
        self.assertIn("note: Not stated", note)
        for name, item in tomllib.loads(TOML.read_text(encoding="utf-8"))["circuit"].items():
            if item.get("in_circuits_txt") is False:
                continue
            conf, gaps = derive_lineage(item["lineage"])
            self.assertEqual((item["lineage_conf"], item["lineage_gaps"]), (conf, gaps), name)
            row = s.db.execute("SELECT value, conf FROM design_meta WHERE slug=? AND "
                               "field='lineage_gaps'", (f"mcnc20/{name}",)).fetchone()
            self.assertEqual(row, (str(gaps), conf))
            if gaps:
                self.assertNotEqual(conf, "primary")

    def test_derive_lineage(self) -> None:
        p: dict[str, object] = {"conf": "primary"}
        m: dict[str, object] = {"conf": "missing"}
        i: dict[str, object] = {"conf": "inferred"}
        self.assertEqual(derive_lineage([p, p]), ("primary", 0))
        self.assertEqual(derive_lineage([p, m]), ("secondary", 1))
        self.assertEqual(derive_lineage([p, i, m]), ("inferred", 1))
        self.assertEqual(derive_lineage([m]), ("missing", 1))

    def test_register_does_not_overwrite_sourced_meta(self) -> None:
        s, _ = mk_store()
        import_mcnc_meta(s, TOML, Roots())
        self.assertEqual(register_designs(s, Roots()), 3)
        conf = s.db.execute(
            "SELECT conf FROM design_meta WHERE slug='mcnc20/alu4' AND field='intent'"
        ).fetchone()[0]
        self.assertEqual(conf, "primary")
        row = s.db.execute(
            "SELECT value, conf FROM design_meta WHERE slug='norns/boundtop' AND field='suite'"
        ).fetchone()
        self.assertEqual(row, ("", "missing"))  # 'norns' is a lane label, not a suite
        row = s.db.execute("SELECT value, conf FROM design_meta WHERE slug='norns/boundtop' "
                           "AND field='records_source'").fetchone()
        self.assertEqual(row, ("norns-r3", "inferred"))
        self.assertIn(("function_class", "missing", 1), meta_coverage(s, "norns/"))
        self.assertEqual(s.db.execute("SELECT COUNT(*) FROM design_source").fetchone()[0], 4)

    def test_reregistration_refreshes_inferred_and_missing_only(self) -> None:
        s, d = mk_store()
        register_designs(s, Roots())
        q = "SELECT value, conf FROM design_meta WHERE slug='norns/boundtop' AND field=?"
        self.assertEqual(s.db.execute(q, ("repo_path",)).fetchone(), ("", "missing"))
        vtr = d / "vtr"
        (vtr / "vtr_flow/benchmarks/verilog").mkdir(parents=True)
        (vtr / "vtr_flow/benchmarks/verilog/boundtop.v").write_text("module m; endmodule\n")
        s.db.execute("UPDATE design_meta SET conf='primary', value='kept' WHERE "
                     "slug='norns/boundtop' AND field='intent'")
        s.db.commit()
        register_designs(s, Roots(vtr=vtr))
        self.assertEqual(s.db.execute(q, ("repo_path",)).fetchone(),
                         ("vtr:vtr_flow/benchmarks/verilog/boundtop.v", "inferred"))
        self.assertEqual(s.db.execute(q, ("intent",)).fetchone(), ("kept", "primary"))

    def test_register_never_touches_research_rows(self) -> None:
        s, _ = mk_store()
        import_mcnc_meta(s, TOML, Roots())
        q = "SELECT value, source, conf FROM design_meta WHERE slug='mcnc20/alu4' AND field=?"
        before = s.db.execute(q, ("author",)).fetchone()  # a research row with conf missing
        register_designs(s, Roots())
        self.assertEqual(s.db.execute(q, ("author",)).fetchone(), before)

    def test_no_home_paths_in_meta_files(self) -> None:
        for f in (REPO / "data/meta").iterdir():
            self.assertNotIn("/home/", f.read_text(encoding="utf-8"), f.name)


if __name__ == "__main__":
    unittest.main()
