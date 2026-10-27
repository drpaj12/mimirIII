from __future__ import annotations

import json
import subprocess
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

import mimir.flowcfg as flowcfg
from mimir.armtables import ARM_TABLES, UnknownArm
from mimir.flowcfg import (
    ImportResult,
    config_coverage,
    import_runs,
    loki_spec,
    norns_spec,
    run_id_of,
    unknown_params,
)
from mimir.flowspec import Spec, SrcRoots
from mimir.meta import Roots, register_designs
from mimir.store import Store
from tests.helpers import tmpdir
from tests.test_store import rec

# one arm of each shape per round, as the data stores them
SAMPLE_ARMS = {
    "norns-r1r2": ["baseline", "cold/cold-16", "hot/hot-urd-32", "soft/soft-words-inter",
                   "soft/soft-words_partial_shuf-full", "hard/hard-words_partial",
                   "unseeded/unseeded-4", "cold-off/coldoff-8", "unseeded-off/unseededoff-8",
                   "cold-r2/cold-r2-words_partial-16", "hot-r2/hot-r2-words_partial-32"],
    "norns-r3": ["stock/seed", "word-b2/analytic", "wordio-b4/seed"],
    "norns-r3-pilot": ["pilot-stock", "pilot/pilot-module-b0.05"],
    "norns-r4": ["stock/analytic", "norns/stagebit"],
    "norns-r5": ["stock", "norns", "known"],
    "norns-r6": ["stock", "norns", "known"],
    "norns-r7": ["stock", "known", "h1", "h5", "net0", "net_h3", "net_known"],
}


def keys(spec_params: list[tuple[str, str, str, str, str]]) -> dict[str, tuple[str, str]]:
    return {f"{s}.{k}": (v, c) for s, k, v, c, _ in spec_params}


def all_specs() -> list[Spec]:
    return [norns_spec(src, arm, False, "abc") for src, arms in SAMPLE_ARMS.items()
            for arm in arms]


class NornsSpecTests(unittest.TestCase):
    def test_r7_stock_params(self) -> None:
        p = keys(norns_spec("norns-r7", "stock", False, "abc").params)
        self.assertEqual(p["place.timing_report_npaths"], ("200", "given"))
        self.assertEqual(p["pack.vpr_commit"][0], "3c9a4d23b2")
        self.assertEqual(p["odin.odin3_commit"][1], "unknown")
        self.assertEqual(p["odin.abc_script"][1], "default-unrecorded")
        self.assertEqual(p["arch.arch_file_sha256"], ("abc", "given"))

    def test_n5_design_needs_only_the_default_checkout(self) -> None:
        spec = norns_spec("norns-r5", "known", True, "abc")
        weak = [f"{p[0]}.{p[1]}" for p in spec.params if p[3] in ("unknown", "default-unrecorded")]
        self.assertEqual(weak, ["pack.allow_unrelated_clustering"])  # no nornsIII checkout given
        self.assertIn("--norns_affinity_weight 100", spec.text)

    def test_unrecognised_arms_raise(self) -> None:
        for src, arm in (("norns-r3", "weird/seed"), ("norns-r4", "mystery/analytic"),
                         ("norns-r5", "h2"), ("norns-r6", "h1"), ("norns-r7", "h6"),
                         ("norns-r7", "net_h9"), ("norns-r1r2", "soft/soft-nosuch-full"),
                         ("norns-r1r2", "cold/cold-"), ("norns-r3", "word-b/seed"),
                         ("norns-r3-pilot", "pilot/pilot-module-b3"), ("norns-r5", "norns/x"),
                         ("norns-r2", "stock")):
            with self.assertRaises(UnknownArm, msg=f"{src} {arm}"):
                norns_spec(src, arm, False, "abc")

    def test_r5_norns_weight_given_and_never_empty(self) -> None:
        spec = norns_spec("norns-r5", "norns", False, "abc")
        p = keys(spec.params)
        self.assertEqual(p["pack.norns_affinity_weight"], ("4", "given"))
        with self.assertRaises(UnknownArm):  # no norns arm on a netlist-level design
            norns_spec("norns-r5", "norns", True, "abc")

    def test_every_given_parameter_has_value_and_cited_source(self) -> None:
        for spec in all_specs():
            for step, key, value, conf, src in spec.params:
                self.assertTrue(src, f"{spec.name} {step}.{key}: no source")
                if conf in ("given", "default"):
                    self.assertNotEqual(value, "", f"{spec.name} {step}.{key}: {conf} but empty")
            self.assertNotIn("weight  ", spec.text)
            self.assertFalse(spec.text.rstrip().endswith("weight"), spec.name)

    def test_arm_tables_have_source_lines(self) -> None:
        for source, rows in ARM_TABLES.items():
            self.assertIn(source, SAMPLE_ARMS)
            for pattern, cite in rows:
                self.assertRegex(cite, r"\.py:\d+", f"{source} {pattern}")

    def test_r12_parameters_from_tags(self) -> None:
        spec = norns_spec("norns-r1r2", "cold-off/coldoff-16", False, None)
        p = keys(spec.params)
        self.assertEqual(p["place.anneal_auto_init_t_scale"], ("16", "given"))
        self.assertEqual(p["place.place_checkpointing"], ("off", "given"))
        self.assertEqual(p["pack.vpr_commit"][1], "unknown")
        self.assertEqual(p["place.flow"][1], "unknown")
        self.assertEqual(spec.status(), "partial")
        h = keys(norns_spec("norns-r1r2", "hot/hot-urd-32", False, None).params)
        self.assertEqual(h["place.seed_family"], ("urd", "given"))
        self.assertEqual(h["place.anneal_auto_init_t_scale"], ("32", "given"))

    def test_r3_beta_and_pilot(self) -> None:
        p = keys(norns_spec("norns-r3", "word-b2/seed", False, "a").params)
        self.assertEqual(p["pack.norns_affinity_weight"], ("2", "given"))
        self.assertEqual(p["place.start"][0], "read_initial_place_file")
        q = keys(norns_spec("norns-r3-pilot", "pilot/pilot-module-b0.05", False, "a").params)
        self.assertEqual(q["pack.norns_affinity_source"], ("module", "given"))
        self.assertEqual(q["pack.norns_affinity_weight"], ("0.05", "given"))

    def test_r7_hindsight_weight_cited(self) -> None:
        spec = norns_spec("norns-r7", "h2", False, "a")
        weight = [p for p in spec.params if p[1] == "norns_affinity_weight"][0]
        self.assertEqual(weight[2:4], ("100", "given"))
        self.assertIn("37", weight[4].split("r7lib.py:")[1])

    def test_r4_proposal_count_is_a_default_not_given(self) -> None:
        p = keys(norns_spec("norns-r4", "norns/analytic", False, "a").params)
        self.assertEqual(p["pack.norns_proposal_count"][1], "default-unrecorded")
        self.assertNotIn("--norns_proposal_count", norns_spec(
            "norns-r4", "norns/analytic", False, "a").text)

    def test_hash_deterministic_and_independent_of_arch_sha(self) -> None:
        a = norns_spec("norns-r4", "norns/wordseed", False, "a")
        b = norns_spec("norns-r4", "norns/wordseed", False, None)
        self.assertEqual(a.config_hash(), b.config_hash())
        self.assertNotEqual(a.status(), "full")
        self.assertNotEqual(
            a.config_hash(), norns_spec("norns-r4", "stock/wordseed", False, "a").config_hash())

    def test_no_home_paths(self) -> None:
        for spec in all_specs():
            self.assertNotIn("/home/", spec.text)

    def test_full_needs_a_cited_source(self) -> None:
        spec = Spec("x", "t", "o")
        spec.add("a", "k", "v", "given", "file:1")
        self.assertEqual(spec.status(), "full")
        spec.add("a", "k2", "v", "given", "")
        self.assertEqual(spec.status(), "partial")
        spec2 = Spec("y", "t", "o")
        spec2.add("a", "k", "", "default-unrecorded", "why")
        self.assertEqual(spec2.status(), "partial")


def odin3_repo() -> Path:
    """A tiny git repository shaped like Odin III: the abc default script and args.c."""
    d = Path(tmpdir())
    (d / "lib/abc").mkdir(parents=True)
    (d / "src/passes/abc").mkdir(parents=True)
    (d / "lib/abc/vtr.abc").write_text("strash\nif -K {K} -v\nprint_stats\n")
    (d / "lib/abc/gates.abc").write_text("strash\nmap -a\n")
    (d / "src/passes/abc/args.c").write_text("x\n    *out = (odin3_abc_opts){0};\n")
    for cmd in (["init", "-q"], ["add", "."],
                ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "c"],
                ["tag", "v1.1.0"]):
        subprocess.run(["git", "-C", str(d), *cmd], check=True, capture_output=True)
    return d


class LokiSpecTests(unittest.TestCase):
    SCRIPT = ["read_arch k6; read_verilog --nolatches d1.sv", "proc", "abc --lut 6"]
    META = {"odin3_version": "1.1.0", "abi_version": 6}

    def test_parse(self) -> None:
        spec = loki_spec("f1-k6", self.SCRIPT, self.META)
        p = keys(spec.params)
        self.assertEqual(p["arch.arch"], ("k6", "given"))
        self.assertEqual(p["abc.lut_k"], ("6", "given"))
        self.assertIn("<design>.sv", spec.text)
        self.assertEqual(spec.text_kind, "recorded-normalised")
        self.assertEqual(spec.status(), "partial")
        self.assertEqual(p["abc.abc_script"][1], "default-unrecorded")

    def test_placeholder_arch_is_unknown(self) -> None:
        spec = loki_spec("f2", ["read_arch <arch>; read_verilog x.sv"], {})
        self.assertEqual(keys(spec.params)["arch.arch"][1], "unknown")

    def test_defaults_read_from_the_named_version(self) -> None:
        roots = SrcRoots(odin3=odin3_repo())
        script = ["read_techlib c.o3lib; read_verilog x.sv", "abc --gates cmos6"]
        spec = loki_spec("f3", script, self.META, roots)
        p = {f"{s}.{k}": (v, c, src) for s, k, v, c, src in spec.params}
        self.assertEqual(p["abc.gates"][:2], ("cmos6", "given"))
        self.assertEqual(p["abc.lut_k"][:2], ("0", "default"))
        self.assertIn("args.c:2", p["abc.lut_k"][2])
        self.assertIn("v1.1.0", p["abc.lut_k"][2])
        self.assertEqual(p["abc.abc_script"][1], "default")
        self.assertIn("map -a", p["abc.abc_script"][0])
        no_flag = loki_spec("f1", ["read_arch k6; read_verilog x.sv", "abc --lut 6"], self.META,
                            roots)
        self.assertIn("if -K {K}", keys(no_flag.params)["abc.abc_script"][0])
        unknown_version = loki_spec("f1", self.SCRIPT, {"odin3_version": "9.9"}, roots)
        self.assertEqual(keys(unknown_version.params)["abc.abc_script"][1], "default-unrecorded")


class ImportRunsTests(unittest.TestCase):
    def build(self) -> tuple[Store, Path]:
        d = Path(tmpdir())
        loki = d / "loki"
        ds = loki / "loki-t" / "corpus"
        for name in ("d1", "d2"):
            fl = ds / name / "f1-k6"
            fl.mkdir(parents=True)
            (ds / name / "design.json").write_text("{}")
            (fl / "meta.json").write_text(json.dumps(
                {"floor": "f1-k6", "script": ["read_arch k6; read_verilog " + name + ".sv",
                                              "abc --lut 6"], "odin3_version": "1.1.0"}))
        s = Store(d / "x.db")
        base = rec("boundtop", "vpr.flow_time", 12.5)
        routed = replace(base, source="norns-r7", arm="stock", seed=1, family="analytic",
                         metric="vpr.flow_time", unit="s", level="routed")
        s.add([routed,
               replace(routed, metric="vpr.max_rss", value=900.0, unit="MiB"),
               replace(routed, arm="h1"),
               replace(rec("d1", "loki.nodes", 5), source="loki:loki-t/corpus", arch="f1-k6"),
               replace(rec("d2", "loki.nodes", 7), source="loki:loki-t/corpus", arch="f1-k6")])
        register_designs(s, Roots())
        return s, loki

    def test_runs_and_view(self) -> None:
        s, loki = self.build()
        res = import_runs(s, "abc", loki)
        self.assertEqual(res.counts, {"loki:loki-t/corpus": 2, "norns-r7": 2})
        self.assertEqual(s.db.execute("SELECT COUNT(*) FROM flow_config").fetchone()[0], 3)
        row = s.db.execute("SELECT time_s, peak_rss_mib FROM run WHERE arm='stock'").fetchone()
        self.assertEqual(row, (12.5, 900.0))
        linked = s.db.execute("SELECT COUNT(*) FROM record_run").fetchone()[0]
        self.assertEqual(linked, 5)
        arch = s.db.execute("SELECT arch FROM run WHERE arm='h1'").fetchone()[0]
        cfg = s.db.execute("SELECT config_hash FROM run WHERE arm='h1'").fetchone()[0]
        rid = run_id_of("norns-r7", "boundtop", arch, 1, "h1", cfg)
        self.assertEqual(s.db.execute("SELECT slug FROM run WHERE run_id=?", (rid,)).fetchone()[0],
                         "norns/boundtop")

    def test_idempotent_and_coverage(self) -> None:
        s, loki = self.build()
        import_runs(s, "abc", loki)
        tables = ("run", "flow_config", "flow_param")
        n = [s.db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables]
        import_runs(s, "abc", loki)
        m = [s.db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables]
        self.assertEqual(n, m)
        cov = {(a, b): d for a, b, c, d in config_coverage(s)}
        self.assertEqual(cov[("norns-r7", "partial")], 2)
        self.assertIn(("odin.odin3_commit", "loki", 1), unknown_params(s))
        self.assertIn(("odin.abc_script", "norns-r7", 2), unknown_params(s))

    def test_unrecognised_arm_is_skipped_with_reason(self) -> None:
        s, loki = self.build()
        s.add([replace(rec("boundtop", "m", 1.0), source="norns-r3", arm="weird/seed",
                       seed=1, level="routed")])
        register_designs(s, Roots())
        res = import_runs(s, "abc", loki)
        self.assertEqual(sum(res.skipped.values()), 1)
        self.assertIn("weird/seed", next(iter(res.skipped)))
        self.assertEqual(s.db.execute("SELECT COUNT(*) FROM run WHERE source='norns-r3'")
                         .fetchone()[0], 0)

    def test_run_key_separates_commit_and_input(self) -> None:
        s, loki = self.build()
        base = s.db.execute("SELECT * FROM records WHERE arm='stock' AND metric='vpr.max_rss'")
        row = base.fetchone()
        cols = [c[0] for c in base.description]
        r = dict(zip(cols, row, strict=True))
        s.db.execute("INSERT INTO records VALUES (" + ",".join("?" for _ in cols) + ")",
                     [r[c] if c != "input_sha256" else "ff" for c in cols])
        s.db.commit()
        res = import_runs(s, "abc", loki)
        self.assertEqual(res.counts["norns-r7"], 3)
        collisions = s.db.execute(
            "SELECT COUNT(*) FROM (SELECT 1 FROM run GROUP BY source, design, arch, seed, arm, "
            "config_hash, tool_commit, input_sha256 HAVING COUNT(*) > 1)").fetchone()[0]
        self.assertEqual(collisions, 0)
        self.assertEqual(s.db.execute("SELECT COUNT(*), COUNT(DISTINCT run_id) FROM run")
                         .fetchone()[0], 5)

    def test_run_id_escapes_separator(self) -> None:
        self.assertNotEqual(run_id_of("a|b", "c", "", 1, "x"), run_id_of("a", "b|c", "", 1, "x"))
        self.assertNotEqual(run_id_of("a\\", "|c", "", 1, "x"), run_id_of("a", "\\|c", "", 1, "x"))

    def test_reimport_keeps_runner_filled_columns(self) -> None:
        s, loki = self.build()
        import_runs(s, "abc", loki)
        s.db.execute("UPDATE run SET command_line='vpr x', host='h1' WHERE arm='stock'")
        s.db.commit()
        import_runs(s, "abc", loki)
        row = s.db.execute("SELECT command_line, host FROM run WHERE arm='stock'").fetchone()
        self.assertEqual(row, ("vpr x", "h1"))

    def test_ambiguous_time_is_null_not_max(self) -> None:
        s, loki = self.build()
        dup = s.db.execute("SELECT * FROM records WHERE metric='vpr.flow_time' AND arm='stock'")
        row = dup.fetchone()
        cols = [c[0] for c in dup.description]
        vals = [(99.0 if c == "value" else "o2" if c == "origin" else row[i])
                for i, c in enumerate(cols)]
        s.db.execute("INSERT INTO records VALUES (" + ",".join("?" for _ in cols) + ")", vals)
        s.db.commit()
        res = import_runs(s, "abc", loki)
        self.assertEqual(res.ambiguous_time, 1)
        got = s.db.execute("SELECT time_s, peak_rss_mib FROM run WHERE arm='stock'").fetchone()
        self.assertEqual(got, (None, 900.0))

    def test_unused_configs_pruned(self) -> None:
        s, loki = self.build()
        flowcfg.put_config(s, norns_spec("norns-r5", "stock", False, "abc"))
        import_runs(s, "abc", loki)
        left = s.db.execute("SELECT COUNT(*) FROM flow_config WHERE name LIKE 'norns-r5%'")
        self.assertEqual(left.fetchone()[0], 0)
        self.assertEqual(s.db.execute(
            "SELECT COUNT(*) FROM flow_param WHERE config_hash NOT IN "
            "(SELECT config_hash FROM flow_config)").fetchone()[0], 0)

    def test_import_rolls_back_on_error(self) -> None:
        s, loki = self.build()
        with (mock.patch.object(flowcfg, "_fill_time_rss", side_effect=RuntimeError("boom")),
              self.assertRaises(RuntimeError)):
            import_runs(s, "abc", loki)
        for table in ("run", "flow_config", "flow_param"):
            self.assertEqual(s.db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0], 0)

    def test_result_type(self) -> None:
        self.assertEqual(ImportResult().ambiguous_time, 0)


if __name__ == "__main__":
    unittest.main()
