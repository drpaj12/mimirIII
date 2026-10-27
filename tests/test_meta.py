from __future__ import annotations

import unittest
from pathlib import Path

from mimir.meta import Roots, import_mcnc_meta, meta_coverage, register_designs, slug_of
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
        # idempotent
        import_mcnc_meta(s, TOML, Roots())
        self.assertEqual(s.db.execute("SELECT COUNT(*) FROM design_lineage").fetchone()[0],
                         sum(1 for _ in s.db.execute("SELECT 1 FROM design_lineage")))

    def test_register_does_not_overwrite_sourced_meta(self) -> None:
        s, _ = mk_store()
        import_mcnc_meta(s, TOML, Roots())
        self.assertEqual(register_designs(s, Roots()), 3)
        conf = s.db.execute(
            "SELECT conf FROM design_meta WHERE slug='mcnc20/alu4' AND field='intent'"
        ).fetchone()[0]
        self.assertEqual(conf, "primary")
        row = s.db.execute(
            "SELECT conf FROM design_meta WHERE slug='norns/boundtop' AND field='suite'"
        ).fetchone()
        self.assertEqual(row[0], "inferred")
        self.assertIn(("function_class", "missing", 1), meta_coverage(s, "norns/"))
        self.assertEqual(s.db.execute("SELECT COUNT(*) FROM design_source").fetchone()[0], 4)

    def test_no_home_paths_in_meta_files(self) -> None:
        for f in (REPO / "data/meta").iterdir():
            self.assertNotIn("/home/", f.read_text(encoding="utf-8"), f.name)


if __name__ == "__main__":
    unittest.main()
