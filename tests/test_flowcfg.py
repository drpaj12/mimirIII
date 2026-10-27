from __future__ import annotations

import json
import unittest
from dataclasses import replace
from pathlib import Path

from mimir.flowcfg import (
    config_coverage,
    import_runs,
    loki_spec,
    norns_spec,
    run_id_of,
    unknown_params,
)
from mimir.meta import Roots, register_designs
from mimir.store import Store
from tests.helpers import tmpdir
from tests.test_store import rec


def keys(spec_params: list[tuple[str, str, str, str, str]]) -> dict[str, tuple[str, str]]:
    return {f"{s}.{k}": (v, c) for s, k, v, c, _ in spec_params}


class NornsSpecTests(unittest.TestCase):
    def test_r7_stock_params(self) -> None:
        p = keys(norns_spec("norns-r7", "stock", False, "abc").params)
        self.assertEqual(p["place.timing_report_npaths"], ("200", "given"))
        self.assertEqual(p["pack.vpr_commit"][0], "3c9a4d23b2")
        self.assertEqual(p["odin.odin3_commit"][1], "unknown")
        self.assertEqual(p["arch.arch_file_sha256"], ("abc", "given"))

    def test_n5_design_is_full(self) -> None:
        spec = norns_spec("norns-r5", "known", True, "abc")
        self.assertEqual(spec.status(), "full")
        self.assertIn("--norns_affinity_weight 100", spec.text)

    def test_r12_unknowns(self) -> None:
        spec = norns_spec("norns-r1r2", "cold-off/coldoff-16", False, None)
        p = keys(spec.params)
        self.assertEqual(p["place.anneal_auto_init_t_scale"], ("16", "given"))
        self.assertEqual(p["pack.vpr_commit"][1], "unknown")
        self.assertEqual(p["place.variant_off"][1], "unknown")
        self.assertEqual(spec.status(), "partial")

    def test_r3_beta_and_pilot(self) -> None:
        p = keys(norns_spec("norns-r3", "word-b2/seed", False, "a").params)
        self.assertEqual(p["pack.norns_affinity_weight"], ("2", "given"))
        self.assertEqual(p["place.start"][0], "read_initial_place_file")
        q = keys(norns_spec("norns-r3-pilot", "pilot/pilot-module-b0.05", False, "a").params)
        self.assertEqual(q["pack.norns_affinity_source"], ("module", "given"))
        self.assertEqual(q["pack.norns_affinity_weight"], ("0.05", "given"))

    def test_hash_is_deterministic(self) -> None:
        a = norns_spec("norns-r4", "norns/wordseed", False, "a")
        b = norns_spec("norns-r4", "norns/wordseed", False, "a")
        self.assertEqual(a.config_hash(), b.config_hash())
        self.assertNotEqual(a.config_hash(),
                            norns_spec("norns-r4", "stock/wordseed", False, "a").config_hash())

    def test_no_home_paths(self) -> None:
        for src, arm in (("norns-r7", "h1"), ("norns-r1r2", "baseline"), ("norns-r6", "norns")):
            self.assertNotIn("/home/", norns_spec(src, arm, False, "a").text)


class LokiSpecTests(unittest.TestCase):
    SCRIPT = ["read_arch k6; read_verilog --nolatches d1.sv", "proc", "abc --lut 6"]

    def test_parse(self) -> None:
        spec = loki_spec("f1-k6", self.SCRIPT, {"odin3_version": "1.1.0", "abi_version": 6})
        p = keys(spec.params)
        self.assertEqual(p["arch.arch"], ("k6", "given"))
        self.assertEqual(p["abc.lut_k"], ("6", "given"))
        self.assertIn("<design>.sv", spec.text)
        self.assertEqual(spec.status(), "partial")

    def test_placeholder_arch_is_unknown(self) -> None:
        spec = loki_spec("f2", ["read_arch <arch>; read_verilog x.sv"], {})
        self.assertEqual(keys(spec.params)["arch.arch"][1], "unknown")


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
        s.add([replace(base, source="norns-r7", arm="stock", seed=1, family="analytic",
                       metric="vpr.flow_time", unit="s"),
               replace(base, source="norns-r7", arm="stock", seed=1, family="analytic",
                       metric="vpr.max_rss", value=900.0, unit="MiB"),
               replace(base, source="norns-r7", arm="h1", seed=1, family="analytic"),
               replace(rec("d1", "loki.nodes", 5), source="loki:loki-t/corpus", arch="f1-k6"),
               replace(rec("d2", "loki.nodes", 7), source="loki:loki-t/corpus", arch="f1-k6")])
        register_designs(s, Roots())
        return s, loki

    def test_runs_and_view(self) -> None:
        s, loki = self.build()
        counts = import_runs(s, "abc", loki)
        self.assertEqual(counts, {"loki:loki-t/corpus": 2, "norns-r7": 2})
        self.assertEqual(s.db.execute("SELECT COUNT(*) FROM flow_config").fetchone()[0], 3)
        row = s.db.execute("SELECT time_s, peak_rss_mib FROM run WHERE arm='stock'").fetchone()
        self.assertEqual(row, (12.5, 900.0))
        linked = s.db.execute("SELECT COUNT(*) FROM record_run").fetchone()[0]
        self.assertEqual(linked, 5)
        rid = run_id_of("norns-r7", "boundtop", s.db.execute(
            "SELECT arch FROM run WHERE arm='h1'").fetchone()[0], 1, "h1")
        self.assertEqual(s.db.execute("SELECT slug FROM run WHERE run_id=?", (rid,)).fetchone()[0],
                         "norns/boundtop")

    def test_idempotent_and_coverage(self) -> None:
        s, loki = self.build()
        import_runs(s, "abc", loki)
        n = [s.db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
             for t in ("run", "flow_config", "flow_param")]
        import_runs(s, "abc", loki)
        m = [s.db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
             for t in ("run", "flow_config", "flow_param")]
        self.assertEqual(n, m)
        cov = {(a, b): d for a, b, c, d in config_coverage(s)}
        self.assertEqual(cov[("norns-r7", "partial")], 2)
        self.assertIn(("odin.odin3_commit", "loki", 1), unknown_params(s))


if __name__ == "__main__":
    unittest.main()
