from __future__ import annotations

import unittest

from mimir import hutton
from mimir.hutton import characterise
from mimir.netlist import COMB, CONST, PI, Netlist
from tests.helpers import chain, diamond, ladder, tree, with_latch


def get(nl: Netlist) -> dict[tuple[str, str], float]:
    return {(m, b): v for m, b, v in characterise(nl)}


class KnownAnswers(unittest.TestCase):
    def test_chain(self) -> None:
        r = get(chain(5))
        self.assertEqual(r[("struct.depth", "")], 5)
        self.assertEqual(r[("struct.n_comb", "")], 5)
        self.assertEqual([r[("struct.level_width", str(k))] for k in range(1, 6)], [1] * 5)
        self.assertEqual(r[("struct.edge_len_hist", "1")], 4)  # comb to comb only
        self.assertEqual(r[("struct.src_edge_len_hist", "1")], 1)  # the PI edge
        self.assertEqual(r[("struct.edge_len_max", "")], 1)
        self.assertEqual(r[("struct.fanout_hist", "1")], 6)
        self.assertEqual(r[("struct.fanout_max", "")], 1)
        self.assertFalse([k for k in r if k[0] == "struct.reconv_stems"])
        self.assertEqual(r[("struct.n_undriven", "")], 0)

    def test_tree(self) -> None:
        r = get(tree(3))
        self.assertEqual(r[("struct.depth", "")], 3)
        self.assertEqual([r[("struct.level_width", str(k))] for k in (1, 2, 3)], [4, 2, 1])
        self.assertEqual(r[("struct.n_pi", "")], 8)
        self.assertEqual(r[("struct.n_edges", "")], 14)
        self.assertEqual(r[("struct.edge_len_hist", "1")], 6)
        self.assertEqual(r[("struct.src_edge_len_hist", "1")], 8)
        self.assertFalse([k for k in r if k[0] == "struct.reconv_stems"])

    def test_diamond(self) -> None:
        r = get(diamond())
        self.assertEqual(r[("struct.depth", "")], 2)
        self.assertEqual(r[("struct.reconv_stems", "pi")], 1)
        self.assertNotIn(("struct.reconv_stems", "comb"), r)
        self.assertEqual(r[("struct.reconv_truncated", "pi")], 0)
        self.assertEqual(r[("struct.reconv_stem_fraction", "pi")], 1.0)
        self.assertEqual(r[("struct.reconv_span_mean", "pi")], 2.0)
        self.assertEqual(r[("struct.fanout_hist", "2")], 1)

    def test_ladder(self) -> None:
        r = get(ladder(3))
        self.assertEqual(r[("struct.depth", "")], 5)
        self.assertEqual([r[("struct.level_width", str(k))] for k in range(1, 6)], [1, 2, 3, 2, 1])
        self.assertEqual(r[("struct.n_comb", "")], 9)
        # stems are the nodes that feed two comb nodes: (0,0), (0,1), (1,0) and (1,1)
        self.assertEqual(r[("struct.reconv_stems", "comb")], 4)
        self.assertEqual(r[("struct.reconv_stem_fraction", "comb")], 1.0)
        self.assertNotIn(("struct.reconv_stems", "pi"), r)  # each ladder PI feeds one node

    def test_long_edge(self) -> None:
        nl = Netlist("long")
        p = nl.add(PI)
        a = nl.add(COMB, (p,))
        b = nl.add(COMB, (a,))
        c = nl.add(COMB, (a, b))
        nl.po_drivers = [c]
        r = get(nl)
        self.assertEqual(r[("struct.edge_len_hist", "2")], 1)
        self.assertEqual(r[("struct.edge_len_hist", "1")], 2)
        self.assertEqual(r[("struct.edge_len_max", "")], 2)
        self.assertEqual(r[("struct.src_edge_len_hist", "1")], 1)

    def test_fanout_bin_zero_and_const(self) -> None:
        nl = Netlist("dangling")
        p = nl.add(PI)
        k = nl.add(CONST)
        a = nl.add(COMB, (p, k))
        nl.add(COMB, (a,))  # drives nothing
        nl.po_drivers = [a]
        r = get(nl)
        self.assertEqual(r[("struct.fanout_hist", "0")], 1)  # the last node
        self.assertEqual(r[("struct.fanout_hist", "2")], 1)  # a: a comb sink and the PO
        self.assertEqual(r[("struct.fanout_hist", "1")], 1)  # p
        self.assertEqual(r[("struct.const_fanout_hist", "1")], 1)
        self.assertEqual(r[("struct.fanout_max", "")], 2)

    def test_reconv_split_by_stem_kind(self) -> None:
        nl = Netlist("kinds")
        p = nl.add(PI)
        s = nl.add(COMB, (p,))
        b = nl.add(COMB, (s,))
        c = nl.add(COMB, (s,))
        d = nl.add(COMB, (b, c))
        nl.po_drivers = [d]
        r = get(nl)
        self.assertEqual(r[("struct.reconv_stems", "comb")], 1)
        self.assertNotIn(("struct.reconv_stems", "pi"), r)  # p feeds one node
        self.assertEqual(r[("struct.reconv_span_mean", "comb")], 2.0)

    def test_truncated_stems_leave_the_denominator(self) -> None:
        old = hutton.VISIT_BOUND
        hutton.VISIT_BOUND = 3
        try:
            nl = Netlist("trunc")
            s = nl.add(PI)
            a = nl.add(COMB, (s,))
            b = nl.add(COMB, (s,))
            for _ in range(5):  # tails without a meeting point
                a = nl.add(COMB, (a,))
                b = nl.add(COMB, (b,))
            nl.po_drivers = [a, b]
            r = get(nl)
        finally:
            hutton.VISIT_BOUND = old
        self.assertEqual(r[("struct.reconv_truncated", "pi")], 1)
        self.assertNotIn(("struct.reconv_stem_fraction", "pi"), r)  # nothing resolved

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


class ReconvergenceBound(unittest.TestCase):
    def test_wide_cone_does_not_hide_a_diamond(self) -> None:
        # stem s -> a, b; d = (a, b) is 2 levels from s. a also feeds a wide cone (created after d,
        # so a depth-first search takes it first) that is larger than the visit bound.
        nl = Netlist("cone")
        p = nl.add(PI)
        s = nl.add(COMB, (p,))
        a = nl.add(COMB, (s,))
        b = nl.add(COMB, (s,))
        d = nl.add(COMB, (a, b))
        mids = [nl.add(COMB, (a,)) for _ in range(80)]
        for m in mids:
            for _ in range(80):
                nl.add(COMB, (m,))
        nl.po_drivers = [d]
        self.assertGreater(len(nl), hutton.VISIT_BOUND)
        r = get(nl)
        self.assertEqual(r[("struct.reconv_span_mean", "comb")], 2.0)  # stem s: reconverges at d
        self.assertEqual(r[("struct.reconv_truncated", "comb")], 1)  # stem a: the cone, no meeting
        # 82 comb stems (s, a, 80 mids); a is truncated; one of the other 81 reconverges
        self.assertEqual(r[("struct.reconv_stems", "comb")], 82)
        self.assertAlmostEqual(r[("struct.reconv_stem_fraction", "comb")], 1 / 81)


if __name__ == "__main__":
    unittest.main()
