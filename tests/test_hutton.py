from __future__ import annotations

import unittest

from mimir.hutton import characterise
from mimir.netlist import COMB, PI, Netlist
from tests.helpers import chain, diamond, ladder, tree, with_latch


def get(nl: Netlist) -> dict[tuple[str, str], float]:
    return {(m, b): v for m, b, v in characterise(nl)}


class KnownAnswers(unittest.TestCase):
    def test_chain(self) -> None:
        r = get(chain(5))
        self.assertEqual(r[("struct.depth", "")], 5)
        self.assertEqual(r[("struct.n_comb", "")], 5)
        self.assertEqual([r[("struct.level_width", str(k))] for k in range(1, 6)], [1] * 5)
        self.assertEqual(r[("struct.edge_len_hist", "1")], 5)
        self.assertEqual(r[("struct.edge_len_max", "")], 1)
        self.assertEqual(r[("struct.fanout_hist", "1")], 6)
        self.assertEqual(r[("struct.fanout_max", "")], 1)
        self.assertEqual(r[("struct.reconv_stems", "")], 0)
        self.assertNotIn(("struct.reconv_stem_fraction", ""), r)

    def test_tree(self) -> None:
        r = get(tree(3))
        self.assertEqual(r[("struct.depth", "")], 3)
        self.assertEqual([r[("struct.level_width", str(k))] for k in (1, 2, 3)], [4, 2, 1])
        self.assertEqual(r[("struct.n_pi", "")], 8)
        self.assertEqual(r[("struct.n_edges", "")], 14)
        self.assertEqual(r[("struct.edge_len_hist", "1")], 14)
        self.assertEqual(r[("struct.reconv_stems", "")], 0)

    def test_diamond(self) -> None:
        r = get(diamond())
        self.assertEqual(r[("struct.depth", "")], 2)
        self.assertEqual(r[("struct.reconv_stems", "")], 1)
        self.assertEqual(r[("struct.reconv_stem_fraction", "")], 1.0)
        self.assertEqual(r[("struct.reconv_span_mean", "")], 2.0)
        self.assertEqual(r[("struct.fanout_hist", "2")], 1)

    def test_ladder(self) -> None:
        r = get(ladder(3))
        self.assertEqual(r[("struct.depth", "")], 5)
        self.assertEqual([r[("struct.level_width", str(k))] for k in range(1, 6)], [1, 2, 3, 2, 1])
        self.assertEqual(r[("struct.n_comb", "")], 9)
        # stems are the nodes that feed two comb nodes: (0,0), (0,1), (1,0) and (1,1)
        self.assertEqual(r[("struct.reconv_stems", "")], 4)
        self.assertEqual(r[("struct.reconv_stem_fraction", "")], 1.0)

    def test_long_edge(self) -> None:
        nl = Netlist("long")
        p = nl.add(PI)
        a = nl.add(COMB, (p,))
        b = nl.add(COMB, (a,))
        c = nl.add(COMB, (a, b))
        nl.po_drivers = [c]
        r = get(nl)
        self.assertEqual(r[("struct.edge_len_hist", "2")], 1)
        self.assertEqual(r[("struct.edge_len_hist", "1")], 3)
        self.assertEqual(r[("struct.edge_len_max", "")], 2)

    def test_latch_cuts_depth(self) -> None:
        r = get(with_latch())
        self.assertEqual(r[("struct.depth", "")], 1)
        self.assertEqual(r[("struct.n_latch", "")], 1)

    def test_loop_raises(self) -> None:
        nl = Netlist("loop")
        nl.add(COMB, (1,))
        nl.add(COMB, (0,))
        with self.assertRaises(ValueError):
            characterise(nl)


if __name__ == "__main__":
    unittest.main()
