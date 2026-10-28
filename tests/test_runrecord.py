"""Run-record importer: the spec checks, the flow config and the run row (no tool is run)."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from mimir.flowcfg import config_coverage
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
        "peak_rss_mib": 70.0,
        "steps": [{"name": "vpr", "argv": ["<vpr>", "<arch>", "<blif>", "--seed", str(seed)],
                   "exit_code": 0, "time_s": 2.5, "peak_rss_mib": 70.0, "locked": True}],
        "tools": {"vpr": {"commit": COMMIT, "clean": False, "binary_sha256": SHA}},
        "params": {
            "run.seed": param(str(seed)),
            "run.seed_default": param("1", "default", "vtr-tree vpr/src/base/read_options.cpp:7-9"),
            "tool.vpr_commit": param(COMMIT, "given", "vpr --version"),
            "vpr.netlist_opts.x": param("true", "given", "vpr.out:7"),
        },
        "inputs": {"netlist": {"path": "<runs>/d1.blif", "sha256": SHA},
                   "arch": {"path": "<abs>/arch.xml", "sha256": "c" * 64}},
        "artifacts": {"vpr_out": {"path": "<run>/vpr.out", "sha256": SHA}},
    }


def write(root: Path, name: str, rec: object) -> None:
    (root / name).mkdir()
    (root / name / "mimir-run.json").write_text(json.dumps(rec), encoding="utf-8")


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
        ]
        for mutate, fragment in cases:
            with self.subTest(fragment=fragment):
                self.assert_refused(mutate, fragment)


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
