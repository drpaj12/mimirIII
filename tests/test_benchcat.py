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
        self.assertEqual([r.tier for r in rows], [3, 4])
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
        row = "| a | - | [s1](#sources) | [repo](https://example.org/s1) | - | MIT | 7 | - | - |"
        self.assertIn(row, first[0])
        self.assertIn("| 12 |", first[0])
        self.assertNotIn("/home", first[0])

    def test_readme_section_replaced_only(self) -> None:
        idx = fixture()
        readme = idx / "README.md"
        readme.write_text(f"intro\n\n{benchcat.README_START}\nold\n{benchcat.README_END}\n\ntail\n")
        benchcat.generate(idx, idx / "c.md", "legend", readme)
        once = readme.read_text()
        self.assertTrue(once.startswith("intro\n\n") and once.endswith("\n\ntail\n"))
        self.assertNotIn("old", once)
        self.assertIn("<details><summary>T3 HDL, no testbench (1 designs)</summary>\n\nRule:", once)
        self.assertIn("### Sources", once)
        benchcat.generate(idx, idx / "c.md", "legend", readme)
        self.assertEqual(once, readme.read_text())
        readme.write_text("no markers\n")
        with self.assertRaises(benchcat.CatalogueError):
            benchcat.generate(idx, idx / "c.md", "legend", readme)

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


LOG = """odin3: info: stats: design: modules 2, top t
odin3: info: stats: module t: cell $dff 1
odin3: info: fsm: information on FSM 't.s':
odin3: info: stats: design: modules 1, top t
odin3: info: stats: module t: cell $dlatch 1
odin3: info: stats: module t: cell $mul 1
odin3: info: stats: module t: cell $add 1
odin3: info: stats: module t: cell $port_in 2
odin3: info: partial_map: 1 multiply, 8 adder in 1 chains, 0 single_port_ram + 0 dual_port_ram
odin3: info: stats: design: modules 1, top t
odin3: info: stats: module t: cell adder 8
"""


def mk(design: str, loc: str, fmt: str = "verilog", **vals: str) -> benchcat.Row:
    return benchcat.Row(0, 0, "s", design, fmt, "t", loc, ["s"], dict(vals))


class ViewTest(unittest.TestCase):
    def test_view_links_from_config(self) -> None:
        rows = [mk("a", "10"), mk("b", "10")]
        with tempfile.TemporaryDirectory() as d:
            idx = Path(d)
            benchcat.attach_views(rows, idx)  # no heimdall.toml: nothing linked
            self.assertEqual([r.view for r in rows], ["-", "-"])
            (idx / "heimdall.toml").write_text(
                'heimdall_base_url = "https://h.example/x"\npages = ["s:a"]\n', encoding="utf-8"
            )
            benchcat.attach_views(rows, idx)
            self.assertEqual(rows[0].view, "https://h.example/x/s-a/")
            self.assertEqual(rows[1].view, "-")
            (idx / "heimdall.toml").write_text('heimdall_base_url = ""\npages = ["s:b"]\n')
            rows[0].view = "-"
            benchcat.attach_views(rows, idx)
            self.assertEqual(rows[1].view, "-")

    def test_view_column_md_and_html(self) -> None:
        from mimir import benchcathtml

        row = mk("a", "10")
        row.view = "https://h.example/x/s-a/"
        self.assertEqual(benchcat._md("view", row, row.view), "[view](https://h.example/x/s-a/)")
        self.assertIn('id="a"', benchcathtml.render([row]))
        self.assertIn(">view</a>", benchcathtml.render([row]))


class TierTest(unittest.TestCase):
    def test_tier_rules(self) -> None:
        full = {"tb": "x/tb.v", "sim_iverilog": "1", "sim_odin": "1", "vtr_stage": "route"}
        cases = [
            (mk("a", "-", "blif (k4)"), 4),
            (mk("b", "500"), 3),
            (mk("c", "50", tb="x.sv"), 2),
            (mk("d", "500", tb="x.v"), 1),
            (mk("e", "500", **full), 0),
            (mk("f", "500", **{**full, "sim_odin": "0"}), 1),
            (mk("g", "500", **{**full, "vtr_stage": "place"}), 1),
            (mk("h", "50", **full), 2),
            (mk("i", "199", tb="x.v"), 2),
            (mk("j", "200", tb="x.v"), 1),
        ]
        for row, want in cases:
            self.assertEqual(benchcat.tier_of(row), want, row.design)

    def test_order_within_tier(self) -> None:
        rows = [mk("z", "300", tb="t", l6_luts="10"), mk("a", "900", tb="t"),
                mk("m", "300", tb="t", l6_luts="50"), mk("b", "300", tb="t", l6_luts="10"),
                mk("n", "400", tb="t")]
        got = [r.design for r in benchcat.rank_rows(rows)]
        self.assertEqual(got, ["m", "b", "z", "a", "n"])
        self.assertEqual([r.rank for r in benchcat.rank_rows(rows)], [1, 2, 3, 4, 5])
        self.assertEqual(got, [r.design for r in benchcat.rank_rows(list(reversed(rows)))])


class SplitTest(unittest.TestCase):
    def test_sub_tables_same_rows_and_order(self) -> None:
        rows = benchcat.rank_rows([mk("z", "300", tb="t", l6_luts="10"), mk("a", "900", tb="t"),
                                   mk("m", "300", tb="t", l6_luts="50")])
        tables = benchcat.sub_tables(rows)
        self.assertEqual(set(tables), set(benchcat.GROUPS))
        want = [r.design for r in rows]
        for name, lines in tables.items():
            self.assertTrue(lines[0].startswith("| design |"), name)
            self.assertEqual([ln.split(" | ")[0][2:] for ln in lines[2:]], want, name)
            self.assertLessEqual(max(len(ln) for ln in lines), 400, name)

    def test_licence_and_html(self) -> None:
        self.assertEqual(benchcat.short_licence("MIT (Copyright (c) 2021 x)"), "MIT")
        self.assertEqual(benchcat.short_licence("not read: the licence"), "not read")
        from mimir import benchcathtml

        rows = benchcat.rank_rows([mk("a<b", "50", tb="x.v", l6_luts="3")])
        page = benchcathtml.render(rows)
        self.assertIn("a&lt;b", page)
        self.assertNotIn("http://", page.replace("https://", ""))
        self.assertNotIn("<script src", page)
        self.assertIn("position:sticky", page)


class DescTest(unittest.TestCase):
    def test_vtr_domains_and_prompt(self) -> None:
        rst = ("x\n.. _table_vtr_benchmarks:\n\n.. table:: T\n\n    ====  ====\n"
               "    Benchmark           Domain\n    ====  ====\n"
               "    sha                 Cryptography\n    LU8PEEng            Math\n"
               "    ====  ====\n")
        want = {"sha": "Cryptography", "LU8PEEng": "Math"}
        self.assertEqual(benchmeasure.vtr_domains(rst), want)
        m = benchmeasure.PROMPT_RE.search("a. The module should implement a 4-bit adder. More")
        self.assertEqual(m.group(1) if m else "", "a 4-bit adder")


class FullTextTest(unittest.TestCase):
    def test_no_truncation(self) -> None:
        long = "x" * 400
        self.assertEqual(benchmeasure._clean(long + " | y"), long + " / y")
        for col in ("status", "desc", "note", "prov", "tb"):
            self.assertEqual(benchcat._md(col, None, long), long)  # type: ignore[arg-type]

    def test_repo_cells_not_cut(self) -> None:
        repo = Path(__file__).resolve().parent.parent
        meas = bench.read_tsv(repo / "data" / "benchmarks" / "measures.tsv", 5)
        from_source = {r[3] for r in meas if r[3].endswith("...")}
        text = (repo / "docs" / "benchmarks" / "catalogue.md").read_text("utf-8")
        for line in text.splitlines():
            if not line.startswith("|"):
                continue
            for cell in (c.strip() for c in line.strip("|").split("|")):
                if cell.endswith("..."):
                    self.assertIn(cell, from_source)


class OdinParseTest(unittest.TestCase):
    def test_properties(self) -> None:
        p = benchmeasure.properties(LOG)
        self.assertEqual([p[f"chk_{c}"] for c in benchcat.CHECKS],
                         ["1", "0", "1", "1", "1", "1", "1", "0"])

    def test_gates_and_luts(self) -> None:
        blk = {"$_AND_": 3, "$_MUX_": 2, "$_DFF_P_": 4, "$_CONST0_": 1, "$port_in": 2}
        self.assertEqual(benchmeasure.gates_count(blk), 5)
        text = ("odin3: info: stats: design: modules 1, top t\n"
                "odin3: info: abc: final: depth 3\n"
                "odin3: info: stats: design: modules 1, top t\n"
                "odin3: info: stats: module t: cell $lut 7\n")
        self.assertEqual(benchmeasure.lut_result(text), (7, 3))


class TimeoutTest(unittest.TestCase):
    def test_too_big_reason(self) -> None:
        tag = benchmeasure.TIMEOUT_TAG
        text = tag + "odin3: info: pass proc: 1 ms\nodin3: info: pass fsm: 2 ms\n"
        got = benchmeasure._fail_reason(124, text)
        self.assertIn("too big for now", got)
        self.assertIn("last finished pass fsm", got)
        self.assertIn("before the first pass", benchmeasure._fail_reason(124, tag))
