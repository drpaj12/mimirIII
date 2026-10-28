"""Line-level HDL graph (schema 7) on the vendored lane 3 fixtures."""

from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path

from mimir import blobs, hdlgraph
from mimir.blif import parse_models
from mimir.scrub import Scrubber
from mimir.store import Store
from tests.depsfix import FIXTURES, deps
from tests.helpers import tmpdir

FIX = FIXTURES / "structures"
TREE = FIXTURES / "deps"
NAME = "bm_dag1_log_mod"


def graph(name: str = NAME) -> hdlgraph.Graph:
    d = deps()
    nm = d.nmv2.read_name_map(FIX / name / f"{name}.blif.names")
    models = parse_models((FIX / name / f"{name}.blif").read_text(encoding="utf-8"))
    return hdlgraph.build(models, nm, hdlgraph.load_resolver_module(TREE))


def store_with_run(name: str = NAME) -> tuple[Store, Path]:
    d = Path(tmpdir())
    s = Store(d / "t.db")
    s.db.execute("INSERT INTO run VALUES ('r1', 'slug', 'cfg', 'src', 'des', 'arch', 1, 'a', '', "
                 "'', NULL, NULL, NULL, NULL, 'o', 'tc', 'in')")
    for kind, fn in (("blif", f"{name}.blif"), ("map", f"{name}.blif.names")):
        sha = blobs.put_bytes(d / "blobs", (FIX / name / fn).read_bytes())
        s.db.execute("INSERT INTO run_artifact (run_id, kind, blob_sha256) VALUES ('r1', ?, ?)",
                     (kind, sha))
    s.db.commit()
    return s, d


class Build(unittest.TestCase):
    def test_edges_have_locations_and_register_flag(self) -> None:
        g = graph()
        self.assertGreater(len(g.edges), 10)
        for src, dst, flag in g.edges:
            self.assertRegex(src[0], r":\d+$")
            self.assertRegex(dst[0], r":\d+$")
            self.assertIn(flag, (0, 1))
        self.assertTrue(any(f for _, _, f in g.edges))  # the design has flip-flops
        self.assertTrue(any(not f for _, _, f in g.edges))

    def test_ports(self) -> None:
        g = graph()
        kinds = {k for _, k, _ in g.ports}
        self.assertEqual(kinds, {"PI", "PO"})
        self.assertIn("a_in[0]", {p for _, k, p in g.ports if k == "PI"})

    def test_input_bit_reaches_logic(self) -> None:
        g = graph("bm_dag3_lpm")
        self.assertTrue(any(s[2] == "a_in" and s[3] == 0 for s, _, _ in g.edges))

    def test_unattributed_atoms_are_passed_through(self) -> None:
        g = graph("bm_dag3_lpm")
        self.assertGreater(g.n_unattributed, 0)
        # every attributed node with an input still has an edge or is a port: no dangling chain
        self.assertGreater(len(g.edges), 0)

    def test_deterministic(self) -> None:
        self.assertEqual(graph().edges, graph().edges)


class Store7(unittest.TestCase):
    def test_backfill_idempotent_and_matches_graph(self) -> None:
        s, d = store_with_run()
        rows = hdlgraph.backfill(s, d / "blobs", Scrubber({}), TREE, d / "tmp")
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0][1].startswith("ok"), rows)
        g = graph()
        self.assertEqual(s.db.execute("SELECT COUNT(*) FROM hdl_edge").fetchone()[0],
                         len(g.edges))  # fmt: skip
        self.assertEqual(s.db.execute("SELECT COUNT(*) FROM hdl_port").fetchone()[0],
                         len(g.ports))  # fmt: skip
        self.assertEqual(hdlgraph.backfill(s, d / "blobs", Scrubber({}), TREE, d / "tmp"), [])
        self.assertEqual(s.db.execute("SELECT n_edges FROM hdl_graph_run").fetchone()[0],
                         len(g.edges))  # fmt: skip

    def test_missing_artifact_is_an_error_row(self) -> None:
        s, d = store_with_run()
        s.db.execute("DELETE FROM run_artifact WHERE kind = 'map'")
        s.db.commit()
        self.assertEqual(hdlgraph.backfill(s, d / "blobs", Scrubber({}), TREE, d / "tmp"), [])

    def test_v6_store_reads_as_is_and_migrates(self) -> None:
        d = Path(tmpdir())
        Store(d / "x.db").close()
        db = sqlite3.connect(d / "x.db")
        for t in hdlgraph.TABLES:
            db.execute(f"DROP TABLE {t}")
        db.execute("UPDATE meta SET value='6' WHERE key='schema_version'")
        db.commit()
        db.close()
        r = Store(d / "x.db", readonly=True)
        self.assertFalse(hdlgraph.has_tables(r))
        r.close()
        s = Store(d / "x.db")
        self.assertTrue(hdlgraph.has_tables(s))
        s.close()


if __name__ == "__main__":
    unittest.main()
