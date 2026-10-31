from __future__ import annotations

import unittest
from pathlib import Path
from typing import Any
from unittest import mock

from mimir import graphlet as glet
from mimir.cli import main
from mimir.measure import measure_job
from mimir.registry import load_registry
from mimir.sets import Job
from mimir.store import Store
from tests.helpers import tmpdir

# a path of five nodes once the clock net is excluded: a -> L1 -> L2 -> L3 -> y
BLIF = """\
.model t
.inputs a clk
.outputs y
.latch a q1 re clk 2
.latch q1 q2 re clk 2
.latch q2 y re clk 2
.end
"""

RESULT = {
    "schema": "odin3-graphlets", "version": 1, "mode": "undirected-5", "n_orbits": 3,
    "groups": [{"nodes": 5, "edges": 4, "self_loops": 0, "global_nets": 1,
                "orbit_totals": [8, 6, 3]}],
}


def have_odin3() -> bool:
    try:
        glet.load_odin3()
    except glet.GraphletSkip:
        return False
    return True


def job() -> Job:
    d = Path(tmpdir())
    (d / "t.blif").write_text(BLIF, encoding="utf-8")
    return Job(d / "t.blif", "t", "unit", "lut", "unit:t.blif")


def have_techlib() -> bool:
    lib = glet.techlib_path()
    return lib is not None and lib.is_file()


class Rows(unittest.TestCase):
    def test_rows_of_pass_result(self) -> None:
        rows = dict(((m, b), v) for m, b, v in glet.rows_of(RESULT))
        self.assertEqual(rows[("graphlet_nodes", "undirected-5")], 5.0)
        self.assertEqual(rows[("graphlet_edges", "undirected-5")], 4.0)
        self.assertEqual(rows[("graphlet_global_nets", "undirected-5")], 1.0)
        self.assertEqual(rows[("graphlet_orbit_count", "undirected-5/2")], 3.0)
        self.assertEqual(len(rows), 4 + 3)

    def test_several_modules_are_skipped(self) -> None:
        bad: dict[str, Any] = {**RESULT, "groups": [{}, {}]}
        with self.assertRaises(glet.GraphletSkip):
            glet.rows_of(bad)

    def test_metrics_registered(self) -> None:
        reg = load_registry()
        for key in ("graphlet_orbit_count", "graphlet_nodes", "graphlet_edges",
                    "graphlet_self_loops", "graphlet_global_nets"):
            self.assertEqual(reg[key].measurer, "graphlet")
            self.assertEqual(reg[key].kind, "measured")

    def test_mode_name(self) -> None:
        self.assertEqual(glet.mode_name(True, 4), "directed-4")


class Skips(unittest.TestCase):
    def test_missing_package_is_a_note_not_a_crash(self) -> None:
        with mock.patch("importlib.import_module", side_effect=ImportError("no odin3")):
            out = measure_job(job(), rent=False, graphlet=True)
        self.assertIn("not available", out.graphlet_note)
        self.assertEqual({r.measurer for r in out.records}, {"struct"})

    def test_old_library_is_a_note(self) -> None:
        class Lib:
            pass

        class Mod:
            @staticmethod
            def default() -> object:
                return type("O", (), {"lib": Lib()})()

        with mock.patch("importlib.import_module", return_value=Mod()):
            out = measure_job(job(), rent=False, graphlet=True)
        self.assertIn("odin3_graphlets_count", out.graphlet_note)
        self.assertNotIn("graphlet", {r.measurer for r in out.records})

    def test_off_by_default(self) -> None:
        out = measure_job(job(), rent=False)
        self.assertEqual(out.graphlet_note, "")


class Check(unittest.TestCase):
    def test_check_flags_mixed_graphlet_versions(self) -> None:
        d = Path(tmpdir())
        s = Store(d / "x.db")
        recs = measure_job(job(), rent=False).records
        from dataclasses import replace

        g = replace(recs[0], measurer="graphlet", metric="graphlet_nodes", bin="undirected-5",
                    unit="nodes", measurer_version="graphlet-1/odin3-1.2.0/schema-x-v1")
        s.add([g, replace(g, bin="directed-4", measurer_version="graphlet-1/odin3-1.3.0/x")])
        s.close()
        self.assertEqual(main(["check", str(d / "x.db")]), 1)

    def test_coverage_has_graphlet_column(self) -> None:
        d = Path(tmpdir())
        self.assertEqual(main(["init", str(d / "x.db")]), 0)
        self.assertEqual(main(["coverage", str(d / "x.db")]), 0)


@unittest.skipUnless(have_odin3() and have_techlib(), "odin3 package or tech library not available")
class WithOdin3(unittest.TestCase):
    def test_path_of_five(self) -> None:
        out = measure_job(job(), rent=False, graphlet=True)
        self.assertEqual(out.graphlet_note, "")
        recs = [r for r in out.records if r.measurer == "graphlet"]
        got = {(r.metric, r.bin): r.value for r in recs}
        self.assertEqual(got[("graphlet_nodes", "undirected-5")], 6.0)  # five plus the clk port
        self.assertEqual(got[("graphlet_global_nets", "undirected-5")], 1.0)
        self.assertEqual(got[("graphlet_edges", "undirected-5")], 4.0)
        self.assertEqual(got[("graphlet_orbit_count", "undirected-5/0")], 8.0)  # sum of degrees
        self.assertEqual(sum(1 for r in recs if r.metric == "graphlet_orbit_count"), 73 + 129)
        self.assertTrue(all(r.measurer_version.startswith("graphlet-1/odin3-") for r in recs))
        self.assertEqual(len({r.measurer_version for r in recs}), 1)
        self.assertTrue(recs[0].measurer_version.endswith("/schema-odin3-graphlets-v1"))


if __name__ == "__main__":
    unittest.main()
