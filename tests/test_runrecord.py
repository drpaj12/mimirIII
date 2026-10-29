"""Run-record importer: the spec checks, the flow config and the run row (no tool is run)."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from mimir.flowcfg import config_coverage, import_runs
from mimir.runrecord import check_record, coverage, import_runrecords, non_given, record_spec
from mimir.store import Store

SHA = "a" * 64
COMMIT = "b" * 40


def param(value: str, conf: str = "given", source: str = "command line") -> dict[str, str]:
    return {"value": value, "conf": conf, "source": source}


def make_record(seed: int = 1, arm: str = "vpr_sa") -> dict[str, Any]:
    return {
        "record_version": 1, "kind": "norns-run", "source": "norns-placers-t", "design": "d1",
        "arch": "arch1", "seed": seed, "arm": arm, "family": "annealing", "host": "host-1",
        "kernel": "6.0", "started_utc": "2026-10-28T00:00:00Z", "ok": True, "time_s": 2.5,
        "peak_rss_mib": 70.0, "time_conf": "given",
        "steps": [{"name": "vpr", "argv": ["<vpr>", "<arch>", "<blif>", "--seed", str(seed)],
                   "exit_code": 0, "time_s": 2.5, "peak_rss_mib": 70.0, "time_conf": "given",
                   "locked": True, "shared": False}],
        "tools": {"vpr": {"commit": COMMIT, "clean": False, "binary_sha256": SHA}},
        "params": {
            "run.seed": param(str(seed)),
            "run.seed_default": param("1", "default", "vtr-tree vpr/src/base/read_options.cpp:7-9"),
            "tool.vpr_commit": param(COMMIT, "given", "vpr --version"),
            "vpr.netlist_opts.x": param("true", "given", "vpr.out:7"),
            "vpr.placer_opts.seed": param(str(seed), "given", "vpr.out:9"),  # VPR echoes the seed
        },
        "inputs": {"netlist": {"path": "<runs>/d1.blif", "sha256": SHA},
                   "arch": {"path": "<abs>/arch.xml", "sha256": "c" * 64}},
        "artifacts": {"vpr_out": {"path": "<run>/vpr.out", "sha256": SHA}},
    }


def write(root: Path, name: str, rec: object) -> None:
    (root / name).mkdir()
    (root / name / "mimir-run.json").write_text(json.dumps(rec), encoding="utf-8")


def make_other(kind: str, source: str, tool: str) -> dict[str, Any]:
    """A record of the two new writers: host `unknown`, no placer family."""
    rec = make_record()
    rec.update(kind=kind, source=source, arm="vtr+vpr", family="", host="unknown")
    rec["tools"] = {tool: {"commit": COMMIT, "clean": True, "binary_sha256": ""},
                    "abc": {"commit": "c" * 40, "clean": None, "binary_sha256": ""}}
    return rec


class NewKinds(unittest.TestCase):
    def test_both_kinds_pass_with_host_unknown(self) -> None:
        for kind, source, tool in (("odin3-flow-run", "odin3-flow", "odin3"),
                                   ("loki-run", "loki", "loki")):
            self.assertEqual(check_record(make_other(kind, source, tool)), [])

    def test_norns_still_needs_a_host_alias(self) -> None:
        rec = make_record()
        rec["host"] = "unknown"
        self.assertTrue(any("host must be" in e for e in check_record(rec)))

    def test_import_uses_the_main_tool_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rec = make_other("odin3-flow-run", "odin3-flow", "odin3")
            rec["tools"]["abc"]["commit"] = "d" * 40
            write(root, "a", rec)
            store = Store(root / "m.db")
            report = import_runrecords(store, root)
            self.assertEqual(report.refused, [])
            row = store.db.execute("SELECT tool_commit, host, source FROM run").fetchone()
            self.assertEqual(tuple(row), (COMMIT, "unknown", "odin3-flow"))


class CheckRecord(unittest.TestCase):
    def test_valid_record_passes(self) -> None:
        self.assertEqual(check_record(make_record()), [])

    def assert_refused(self, mutate: Any, fragment: str) -> None:
        rec = copy.deepcopy(make_record())
        mutate(rec)
        errs = check_record(rec)
        self.assertTrue(any(fragment in e for e in errs), (fragment, errs))

    def test_each_rule_refuses(self) -> None:
        cases = [
            (lambda r: r.update(record_version=2), "record_version"),
            (lambda r: r.pop("host"), "missing 'host'"),
            (lambda r: r.update(host="myrealname"), "host must be"),
            (lambda r: r.update(family="x"), "family"),
            (lambda r: r.update(kind="other"), "kind"),
            (lambda r: r.update(steps=[]), "steps: empty"),
            (lambda r: r["params"].update({"a.b": param("v", "guess")}), "conf"),
            (lambda r: r["params"].update({"a.b": param("v", "given", "")}), "empty source"),
            (lambda r: r["params"].update({"a.b": param("", "given")}), "empty value"),
            (lambda r: r["params"].update({"a.b": param("1", "default", "no line")}), "citation"),
            (lambda r: r["tools"]["vpr"].update(commit="abc"), "40 hex"),
            (lambda r: r["inputs"].pop("netlist"), "'netlist' role"),
            (lambda r: r["inputs"]["arch"].update(path="/x/arch.xml"), "relative"),
            (lambda r: r["inputs"]["arch"].update(sha256="zz"), "64 hex"),
            (lambda r: r["steps"][0]["argv"].append("/ho" + "me/u/f"), "absolute"),
            (lambda r: r["steps"][0]["argv"].append("--x=/tmp/y z"), "absolute"),
            (lambda r: r["steps"][0]["argv"].append("a:/tmp/y"), "absolute"),
            (lambda r: r["steps"][0]["argv"].append(3), "non-string"),
            (lambda r: r["steps"][0].pop("locked"), "missing 'locked'"),
            (lambda r: r.update(started_utc="2026-10-28"), "started_utc"),
            (lambda r: r.update(host="host-unmapped"), "host must be"),
            (lambda r: r["steps"][0].update(time_s=None), "time_s is null exactly"),
            (lambda r: r.update(time_conf="guess"), "time_conf"),
        ]
        for mutate, fragment in cases:
            with self.subTest(fragment=fragment):
                self.assert_refused(mutate, fragment)


class HostMapContract(unittest.TestCase):
    """The map format shared with the Norns writer (nornsIII scripts/runrecord.py `host_alias`)."""

    NORNS_LINES = ('# Private map of real host names to aliases. Never commit this file.\n[hosts]\n'
                   '"alpha" = "host-1"\n"we\\"ird\\\\name" = "host-2"\n')

    def test_reads_lines_in_the_form_the_norns_writer_appends(self) -> None:
        from mimir import hostalias
        with tempfile.TemporaryDirectory() as d:
            m = Path(d) / "hosts.toml"
            m.write_text(self.NORNS_LINES, encoding="utf-8")
            self.assertEqual(hostalias.load_map(m), {"alpha": "host-1", 'we"ird\\name': "host-2"})
            self.assertEqual(hostalias.alias_of("ALPHA", m), "host-1")
            self.assertEqual(hostalias.alias_of("gamma", m), "host-3")

    def test_norns_writer_appends_to_a_map_mimir_wrote(self) -> None:
        import importlib.util
        import os

        from mimir import hostalias
        src = Path(os.environ.get("NORNS_SCRIPTS", Path.home() / "odin3-ws" / "norns" / "scripts"))
        if not (src / "runrecord.py").is_file():
            self.skipTest("nornsIII scripts not found (set NORNS_SCRIPTS)")
        spec = importlib.util.spec_from_file_location("norns_runrecord", src / "runrecord.py")
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if not hasattr(mod, "host_table"):
            self.skipTest("this nornsIII checkout predates the map-format writer")
        with tempfile.TemporaryDirectory() as d:
            m = Path(d) / "hosts.toml"
            hostalias.init_map(m)
            self.assertEqual(hostalias.alias_of("first", m), "host-1")
            self.assertEqual(mod.host_alias("second", m), "host-2")
            self.assertEqual(hostalias.alias_of("second", m), "host-2")
            self.assertEqual(hostalias.alias_of("third", m), "host-3")


class Messages(unittest.TestCase):
    def test_refusal_names_the_key_not_the_value(self) -> None:
        rec = make_record()
        rec["params"]["a.b"] = param("/ab" + "solute/secretvalue")
        errs = check_record(rec)
        self.assertTrue(errs and all("secretvalue" not in e for e in errs), errs)
        self.assertIn("record.params.a.b.value", errs[0])

    def test_unknown_time_is_null_and_stored_null(self) -> None:
        rec = make_record()
        rec["time_s"], rec["time_conf"] = None, "unknown"
        rec["peak_rss_mib"] = None
        rec["steps"][0].update(time_s=None, time_conf="unknown", peak_rss_mib=None)
        self.assertEqual(check_record(rec), [])
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write(root, "a", rec)
            store = Store(root / "m.db")
            import_runrecords(store, root)
            self.assertEqual(store.db.execute("SELECT time_s, peak_rss_mib FROM run").fetchone(),
                             (None, None))

    def test_allowed_strings_pass(self) -> None:
        rec = make_record()
        rec["steps"][0]["argv"] += ["--route_file", "/dev/null", "vpr/src/base/x.cpp:1-2", "a / b"]
        rec["params"]["a.b"] = param("1/2 https://x.y/z", "given", "vpr.out:3")
        self.assertEqual(check_record(rec), [])


class Import(unittest.TestCase):
    def test_seeds_share_one_full_config_and_each_run_keeps_its_facts(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write(root, "a", make_record(seed=1))
            write(root, "b", make_record(seed=2))
            store = Store(root / "m.db")
            rep = import_runrecords(store, root)
            self.assertEqual((len(rep.imported), rep.refused), (2, []))
            self.assertEqual(coverage(store), [("vpr_sa", "full", 2)])
            self.assertEqual(config_coverage(store), [("norns-placers-t", "full", 1, 2)])
            row = store.db.execute(
                "SELECT seed, host, time_s, peak_rss_mib, tool_commit, input_sha256, "
                "tool_commits, command_line FROM run ORDER BY seed").fetchall()
            self.assertEqual(row[1][:6], (2, "host-1", 2.5, 70.0, COMMIT, SHA))
            self.assertEqual(row[0][6], f"vpr={COMMIT}-dirty")
            self.assertIn("--seed 1", row[0][7])
            text = store.db.execute("SELECT config_text_reconstructed FROM flow_config"
                                    ).fetchone()[0]
            self.assertIn("--seed <seed>", text)
            self.assertEqual(non_given(store),
                             [("vpr_sa", "run.seed_default", "default",
                               "vtr-tree vpr/src/base/read_options.cpp:7-9")])
            self.assertEqual(import_runrecords(store, root).refused, [])  # idempotent
            self.assertEqual(store.db.execute("SELECT COUNT(*) FROM run").fetchone()[0], 2)

    def test_vpr_echoed_seed_does_not_split_the_config(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for seed in (1, 2):
                write(root, f"s{seed}", make_record(seed=seed))
            store = Store(root / "m.db")
            import_runrecords(store, root)
            self.assertEqual(config_coverage(store), [("norns-placers-t", "full", 1, 2)])

    def test_import_runs_keeps_record_time_and_rss(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write(root, "a", make_record())
            store = Store(root / "m.db")
            import_runrecords(store, root)
            before = store.db.execute("SELECT run_id, time_s, peak_rss_mib FROM run").fetchall()
            import_runs(store, None, None)
            self.assertEqual(
                store.db.execute("SELECT run_id, time_s, peak_rss_mib FROM run").fetchall(),
                before)
            self.assertEqual(before[0][1:], (2.5, 70.0))

    def test_placer_tool_is_the_run_tool_commit(self) -> None:
        rec = make_record(arm="ext_nextpnr_sa")
        rec["tools"]["nextpnr"] = {"commit": "d" * 40, "clean": True, "binary_sha256": SHA}
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write(root, "a", rec)
            store = Store(root / "m.db")
            import_runrecords(store, root)
            commit, commits = store.db.execute(
                "SELECT tool_commit, tool_commits FROM run").fetchone()
            self.assertEqual(commit, "d" * 40)
            self.assertEqual(commits, f"nextpnr={'d' * 40}; vpr={COMMIT}-dirty")

    def test_clean_not_true_is_dirty(self) -> None:
        rec = make_record()
        rec["tools"]["vpr"]["clean"] = None
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write(root, "a", rec)
            store = Store(root / "m.db")
            import_runrecords(store, root)
            self.assertEqual(store.db.execute("SELECT tool_commits FROM run").fetchone()[0],
                             f"vpr={COMMIT}-dirty")

    def test_conflicting_reconstructed_config_refuses_the_record(self) -> None:
        rec = make_record()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write(root, "a", rec)
            store = Store(root / "m.db")
            h = record_spec(rec).config_hash()
            store.db.execute("INSERT INTO flow_config VALUES (?, 'x', 'other text', "
                             "'reconstructed', 'full', 'o')", (h,))
            rep = import_runrecords(store, root)
            self.assertEqual((len(rep.imported), len(rep.refused)), (0, 1))
            self.assertIn("config:", rep.refused[0][1][0])
            self.assertEqual(store.db.execute("SELECT config_text_reconstructed FROM flow_config"
                                              ).fetchone()[0], "other text")

    def test_source_filter_is_exact_and_root_must_be_a_dir(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write(root, "a", make_record())
            store = Store(root / "m.db")
            import_runrecords(store, root)
            self.assertEqual(coverage(store, "norns-placers-t"), [("vpr_sa", "full", 1)])
            self.assertEqual(coverage(store, "norns%"), [])
            self.assertEqual(coverage(store, "norns-placers-"), [])
            with self.assertRaises(NotADirectoryError):
                import_runrecords(store, root / "nope")

    def test_unknown_param_makes_the_config_partial_and_is_named(self) -> None:
        rec = make_record()
        rec["params"]["tool.vpr_commit"] = param("", "unknown", "binary does not name its commit")
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write(root, "a", rec)
            store = Store(root / "m.db")
            import_runrecords(store, root)
            self.assertEqual(coverage(store), [("vpr_sa", "partial", 1)])
            self.assertIn("tool.vpr_commit", [k for _, k, _, _ in non_given(store)])
            self.assertEqual(record_spec(rec).status(), "partial")

    def test_bad_record_is_refused_with_reasons_and_the_good_one_imported(self) -> None:
        bad = make_record(seed=2)
        bad["params"]["a.b"] = param("v", "guess")
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write(root, "a", make_record())
            write(root, "b", bad)
            store = Store(root / "m.db")
            rep = import_runrecords(store, root)
            self.assertEqual(len(rep.imported), 1)
            self.assertEqual([p for p, _ in rep.refused], ["b/mimir-run.json"])
            self.assertEqual(store.db.execute("SELECT COUNT(*) FROM run").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
