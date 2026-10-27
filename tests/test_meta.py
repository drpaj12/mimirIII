from __future__ import annotations

import tomllib
import unittest
from pathlib import Path

from mimir.meta import (
    Roots,
    _toml_meta,
    derive_lineage,
    import_licences,
    import_mcnc_meta,
    load_licence_rules,
    meta_coverage,
    register_designs,
    rule_for,
    slug_of,
)
from mimir.store import Store
from tests.helpers import tmpdir
from tests.test_store import rec

REPO = Path(__file__).resolve().parents[1]
TOML = REPO / "data/meta/mcnc.toml"
LICENCES = REPO / "data/meta/licences.toml"


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
        item = dict(tomllib.loads(TOML.read_text(encoding="utf-8"))["circuit"]["apex2"])
        item.update(intent="", intent_conf="missing", intent_src="", intent_note="Not stated here")
        _toml_meta(s, "mcnc20/apex2", item)
        note = s.db.execute("SELECT source FROM design_meta WHERE slug='mcnc20/apex2' "
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

    def test_licence_rules_pick_the_specific_rule(self) -> None:
        rules = load_licence_rules(LICENCES)
        want = {"norns/or1200": "vtr-or1200", "norns/sha": "vtr-sha",
                "norns/diffeq2": "vtr-diffeq2", "norns/diffeq1": "vtr-other-verilog",
                "norns/stereovision3": "vtr-stereovision",
                "norns/n5_chain_ctl_16": "norns-synthetic",
                "norns/r6_x": "norns-synthetic", "loki/loki-exp4-data/corpus/r4_adder_000":
                "loki-synthetic", "loki/loki-exp4-data/corpus/r4t_a_000": "loki-synthetic",
                "loki/loki-veval-exp/ve_Prob001_zero": "verilogeval", "mcnc20/alu4": "mcnc",
                "loki/exp3/micro_and": "vtr-micro"}
        for slug, rid in want.items():
            rule = rule_for(slug, rules)
            self.assertIsNotNone(rule, slug)
            assert rule is not None
            self.assertEqual(rule["id"], rid, slug)
        self.assertIsNone(rule_for("norns/unknown_design", rules))
        self.assertEqual(len({r["id"] for r in rules}), len(rules))

    def test_licence_rows_for_every_design(self) -> None:
        s, _ = mk_store()
        import_mcnc_meta(s, TOML, Roots())
        register_designs(s, Roots())
        s.db.execute("INSERT INTO design VALUES ('norns/zzz', 'h', 'slug', 'norns', 'zzz', '')")
        self.assertEqual(import_licences(s, LICENCES), 21)
        slugs = [r[0] for r in s.db.execute("SELECT slug FROM design").fetchall()]
        self.assertEqual(len(slugs), 23)
        for slug in slugs:
            got = dict((f, (v, c)) for f, v, c in s.db.execute(
                "SELECT field, value, conf FROM design_meta WHERE slug=? AND field LIKE 'licence%'",
                (slug,)).fetchall())
            self.assertIn("licence", got, slug)
            if slug in ("norns/zzz", "loki/ds/x/d1"):
                self.assertEqual(got, {"licence": ("", "missing")})
            else:
                self.assertEqual(set(got), {"licence", "licence_source", "licence_notice"}, slug)
                self.assertNotEqual(got["licence"][0], "", slug)
        self.assertEqual(s.db.execute("SELECT value FROM design_meta WHERE slug='mcnc20/alu4' "
                                      "AND field='licence'").fetchone()[0], "none-stated")
        row = s.db.execute("SELECT value FROM design_meta WHERE slug='norns/boundtop' AND "
                           "field='licence'").fetchone()
        self.assertEqual(row[0], "none-stated")
        before = s.db.execute("SELECT * FROM design_meta ORDER BY 1, 2").fetchall()
        import_licences(s, LICENCES)  # idempotent
        self.assertEqual(before, s.db.execute("SELECT * FROM design_meta ORDER BY 1, 2").fetchall())

    def test_bad_licence_rule_is_refused(self) -> None:
        d = Path(tmpdir())
        bad = d / "l.toml"
        bad.write_text('[[rule]]\nid = "x"\nmatch = ["a/*"]\nlicence = ""\nlicence_source = ""\n'
                       'licence_notice = ""\nconf = "primary"\n', encoding="utf-8")
        with self.assertRaises(ValueError):
            load_licence_rules(bad)
        bad.write_text('[[rule]]\nid = "x"\nmatch = ["a/*"]\nlicence = "L"\nlicence_source = "s"\n'
                       'licence_notice = ""\nconf = "missing"\n', encoding="utf-8")
        with self.assertRaises(ValueError):
            load_licence_rules(bad)

    def test_original_header_is_at_most_five_lines(self) -> None:
        for name, item in tomllib.loads(TOML.read_text(encoding="utf-8"))["circuit"].items():
            self.assertLessEqual(len(str(item.get("original_header", "")).splitlines()), 5, name)
        s, d = mk_store()
        item = tomllib.loads(TOML.read_text(encoding="utf-8"))["circuit"]["alu4"]
        item["original_header"] = "1\n2\n3\n4\n5\n6"
        item["original_header_conf"] = "primary"
        with self.assertRaises(ValueError):
            _toml_meta(s, "mcnc20/alu4", item)


if __name__ == "__main__":
    unittest.main()
