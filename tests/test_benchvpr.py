"""Tests of the VPR collector (`mimir.benchvpr`) with a fake flow runner."""

from __future__ import annotations

import json
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path

from mimir import bench, benchvpr
from tests.test_benchcat import fixture

Runner = Callable[[list[str], dict[str, str]], int]
BLIF = ".model m\n.inputs a b clk\n.outputs o\n.latch a q re clk 0\n.names a b o\n11 1\n.end\n"


def ok_runner() -> Runner:
    def run(argv: list[str], env: dict[str, str]) -> int:
        out = Path(argv[argv.index("--out") + 1])
        (out / "odin3").mkdir(parents=True)
        (out / "vpr" / "run").mkdir(parents=True)
        (out / "odin3" / "a.blif").write_text(BLIF)
        (out / "vpr" / "run" / "vpr.out").write_text("Netlist num_blocks: 9\n")
        (out / "summary.json").write_text(json.dumps(
            {"luts": 1, "crit_path_ns": 2.5, "min_chan_width": 22,
             "seconds": {"odin3": 1.0, "vpr": 2.0}}))
        return 0
    return run


def timeout_runner(argv: list[str], env: dict[str, str]) -> int:
    out = Path(argv[argv.index("--out") + 1])
    (out / "vpr").mkdir(parents=True)
    (out / "vpr" / "vpr.log").write_text("$ vpr\nroute\n\ntimeout after 7260 s\n")
    (out / "summary.json").write_text(json.dumps({"seconds": {"odin3": 1.0, "vpr": 7260.0}}))
    return -9


class VprTest(unittest.TestCase):
    def setUp(self) -> None:
        self.idx = fixture()
        (self.idx / "measures.tsv").write_text("suite\tdesign\tkey\tvalue\tsource\n")
        self.su = bench.load_suites(self.idx)["s1"]
        self.d = next(d for d in bench.load_designs(self.idx) if d.suite == "s1")
        self.out = Path(tempfile.mkdtemp())

    def run_one(self, runner: Runner) -> list[list[str]]:
        return benchvpr.measure_design(Path("/x/build/odin3"), Path("/v"), self.su, self.d,
                                       self.out, runner)

    def test_success_rows(self) -> None:
        got = {r[2]: r[3] for r in self.run_one(ok_runner())}
        self.assertEqual(got, {"vtr_stage": "route", "vtr_luts": "1", "vtr_blocks": "9",
                               "vtr_ffs": "1", "vtr_pins": "4", "vtr_mult": "0", "vtr_mem": "0",
                               "vtr_cpd": "2.5", "vtr_cw": "22"})

    def test_timeout_is_too_big_with_stage(self) -> None:
        got = {r[2]: r[3] for r in self.run_one(timeout_runner)}
        self.assertTrue(got["vtr_stage"].startswith("vpr: too big for now (timeout after 7260 s"))
        self.assertTrue(got["vtr_cw"].startswith("fail: too big for now"))

    def test_collect_skips_done_and_retries(self) -> None:
        seen: list[list[str]] = []
        n = benchvpr.collect_vpr(self.idx, Path("/x/build/odin3"), Path("/v"), "s1", self.out,
                                 None, lambda rows: seen.append(rows[0]),
                                 runner=ok_runner())
        self.assertEqual(n, 1)
        self.assertEqual(seen[0][3], "route")


if __name__ == "__main__":
    unittest.main()
