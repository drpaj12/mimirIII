"""Regression tests that pin published values where Mimir matches the source exactly.

T = Hutton PhD thesis (Toronto 1997), printed pages. The small constructions are worked by hand
from the definitions at the cited page; the alu4 test reads VTR's 4-LUT netlist and checks the
vectors of the thesis tables (it matches every vector, spec section 10.3)."""

from __future__ import annotations

import os
import unittest
from pathlib import Path

from mimir.blif import read_blif
from mimir.hutton import characterise
from mimir.netlist import COMB, LATCH, PI, Netlist

Rows = dict[tuple[str, str], float]


def get(nl: Netlist) -> Rows:
    return {(m, b): v for m, b, v in characterise(nl)}


def vec(r: Rows, metric: str, bins: range) -> list[float]:
    return [r.get((metric, str(k)), 0.0) for k in bins]


def small() -> Netlist:
    """PIs a, b, c; g1 = (a, b); g2 = (g1, c); g3 = (g1, g2); g3 is the PO."""
    nl = Netlist("small")
    a, b, c = nl.add(PI), nl.add(PI), nl.add(PI)
    g1 = nl.add(COMB, (a, b))
    g2 = nl.add(COMB, (g1, c))
    g3 = nl.add(COMB, (g1, g2))
    nl.po_drivers = [g3]
    return nl


class HandWorked(unittest.TestCase):
    def test_size_delay_shape(self) -> None:  # T p. 25-28, Sec. 3.2.1 and 3.3
        r = get(small())
        self.assertEqual(r[("struct.size", "")], 6)  # nPI + nLOG
        self.assertEqual(r[("struct.depth", "")], 3)
        self.assertEqual(vec(r, "struct.level_width", range(4)), [3, 1, 1, 1])  # PIs at delay 0

    def test_edge_length_counts_pi_pins(self) -> None:  # T p. 31, Sec. 3.3.2
        r = get(small())
        self.assertEqual(r[("struct.edge_len_hist", "1")], 4)
        self.assertEqual(r[("struct.edge_len_hist", "2")], 2)  # c into g2 and g1 into g3

    def test_fanout_without_po_pins(self) -> None:  # T p. 26 (a PO pin is not an edge), p. 32
        r = get(small())
        self.assertEqual(r[("struct.fanout_hist", "0")], 1)
        self.assertEqual(r[("struct.fanout_hist", "1")], 4)
        self.assertEqual(r[("struct.fanout_hist", "2")], 1)
        self.assertEqual(r[("struct.fanout_max", "")], 2)
        self.assertEqual(vec(r, "struct.fanout_shape", range(4)), [3, 2, 1, 0])  # delay-fanout

    def test_reconvergence_number(self) -> None:  # T p. 33 eq. 3.1, weighted p. 34
        # Roots a and b: cone {root, g1, g2, g3}, only g3 has both fanins in it, R = 1/4 each.
        # Root c: cone {c, g2, g3}, no node has two fanins in it, R = 0. Weighted: 2/11.
        self.assertAlmostEqual(get(small())[("struct.reconv_R", "")], 2 / 11)

    def test_sequential_level_and_back_edge(self) -> None:  # T p. 45-47, Table 4.1 columns
        nl = Netlist("loop")
        a = nl.add(PI)
        g = nl.add(COMB, (a,))
        q = nl.add(LATCH, (g,))
        h = nl.add(COMB, (q,))
        nl.add(COMB, (a, h))  # reads level 0 (a) and level 1 (h): a back edge
        nl.po_drivers = [h]
        r = get(nl)
        self.assertEqual(r[("struct.seq_levels", "")], 2)
        self.assertEqual([r[("struct.seq_shape", "0")], r[("struct.seq_shape", "1")]], [3, 2])
        self.assertEqual(r[("struct.n_back_edges", "")], 1)


ALU4 = "vtr_flow/benchmarks/blif/4/alu4.blif"


class Alu4(unittest.TestCase):
    """Thesis Tables 3.2-3.4 (T p. 30-32), 4-LUT alu4: 1536 nodes, delay 7, 5400 edges."""

    @unittest.skipUnless(os.environ.get("VTR_ROOT"), "VTR_ROOT is not set")
    def test_published_vectors(self) -> None:
        path = Path(os.environ["VTR_ROOT"]) / ALU4
        if not path.is_file():
            self.skipTest(f"{ALU4} not found")
        r = get_blif(path)
        self.assertEqual(r[("struct.size", "")], 1536)
        self.assertEqual(r[("struct.depth", "")], 7)
        self.assertEqual(r[("struct.fanout_max", "")], 249)
        self.assertEqual(r[("struct.n_edges", "")], 5400)
        self.assertEqual(vec(r, "struct.level_width", range(8)), [14, 692, 518, 198, 80, 21, 11, 2])
        self.assertEqual(vec(r, "struct.edge_len_hist", range(1, 6)), [4494, 757, 125, 23, 1])
        self.assertEqual(vec(r, "struct.fanout_shape", range(8)),
                         [2867, 1700, 529, 197, 79, 20, 8, 0])


def get_blif(path: Path) -> Rows:
    return get(read_blif(str(path)))


if __name__ == "__main__":
    unittest.main()
