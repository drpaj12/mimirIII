from __future__ import annotations

import math
import unittest

from mimir import hutton
from mimir.hutton import characterise
from mimir.netlist import COMB, CONST, LATCH, PI, Netlist
from tests.helpers import chain, diamond, ladder, tree, with_latch


def get(nl: Netlist) -> dict[tuple[str, str], float]:
    return {(m, b): v for m, b, v in characterise(nl)}


class KnownAnswers(unittest.TestCase):
    def test_chain(self) -> None:
        r = get(chain(5))
        self.assertEqual(r[("struct.depth", "")], 5)
        self.assertEqual(r[("struct.n_comb", "")], 5)
        self.assertEqual([r[("struct.level_width", str(k))] for k in range(1, 6)], [1] * 5)
        self.assertEqual(r[("struct.edge_len_hist", "1")], 5)  # every pin, the PI pin included
        self.assertEqual(r[("struct.mimir_edge_len_comb_hist", "1")], 4)
        self.assertEqual(r[("struct.mimir_edge_len_src_hist", "1")], 1)  # the PI edge
        self.assertEqual(r[("struct.edge_len_max", "")], 1)
        self.assertEqual(r[("struct.fanout_hist", "1")], 5)  # a PO pin is not an edge
        self.assertEqual(r[("struct.fanout_hist", "0")], 1)  # the last node
        self.assertEqual(r[("struct.mimir_fanout_po_hist", "1")], 6)
        self.assertEqual(r[("struct.level_width", "0")], 1)  # the PI is at delay 0
        self.assertEqual(r[("struct.size", "")], 6)  # nPI + nLOG
        self.assertEqual(r[("struct.n_io", "")], 2)
        self.assertEqual(sum(v for (m, _), v in r.items() if m == "struct.fanout_shape"), 5)
        self.assertEqual(r[("struct.fanout_max", "")], 1)
        self.assertFalse([k for k in r if k[0] == "struct.mimir_reconv_stems"])
        self.assertEqual(r[("struct.n_undriven", "")], 0)

    def test_tree(self) -> None:
        r = get(tree(3))
        self.assertEqual(r[("struct.depth", "")], 3)
        self.assertEqual([r[("struct.level_width", str(k))] for k in (1, 2, 3)], [4, 2, 1])
        self.assertEqual(r[("struct.n_pi", "")], 8)
        self.assertEqual(r[("struct.n_edges", "")], 14)
        self.assertEqual(r[("struct.edge_len_hist", "1")], 14)
        self.assertEqual(r[("struct.mimir_edge_len_comb_hist", "1")], 6)
        self.assertEqual(r[("struct.mimir_edge_len_src_hist", "1")], 8)
        self.assertEqual(r[("struct.level_width", "0")], 8)
        self.assertEqual(r[("struct.reconv_R", "")], 0.0)  # every cone is a path or a tree
        self.assertEqual(r[("struct.fanin_max", "")], 2)
        self.assertFalse([k for k in r if k[0] == "struct.mimir_reconv_stems"])

    def test_diamond(self) -> None:
        r = get(diamond())
        self.assertEqual(r[("struct.depth", "")], 2)
        self.assertEqual(r[("struct.fanin_max", "")], 2)
        self.assertEqual(r[("struct.mimir_reconv_stems", "pi")], 1)
        self.assertNotIn(("struct.mimir_reconv_stems", "comb"), r)
        self.assertEqual(r[("struct.mimir_reconv_truncated", "pi")], 0)
        self.assertEqual(r[("struct.mimir_reconv_stem_fraction", "pi")], 1.0)
        self.assertEqual(r[("struct.mimir_reconv_span_mean", "pi")], 2.0)
        self.assertEqual(r[("struct.fanout_hist", "2")], 1)

    def test_ladder(self) -> None:
        r = get(ladder(3))
        self.assertEqual(r[("struct.depth", "")], 5)
        self.assertEqual([r[("struct.level_width", str(k))] for k in range(1, 6)], [1, 2, 3, 2, 1])
        self.assertEqual(r[("struct.n_comb", "")], 9)
        # stems are the nodes that feed two comb nodes: (0,0), (0,1), (1,0) and (1,1)
        self.assertEqual(r[("struct.mimir_reconv_stems", "comb")], 4)
        self.assertEqual(r[("struct.mimir_reconv_stem_fraction", "comb")], 1.0)
        self.assertNotIn(("struct.mimir_reconv_stems", "pi"), r)  # each ladder PI feeds one node

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
        self.assertEqual(r[("struct.mimir_edge_len_comb_hist", "1")], 2)
        self.assertEqual(r[("struct.mimir_edge_len_src_hist", "1")], 1)

    def test_fanout_bin_zero_and_const(self) -> None:
        nl = Netlist("dangling")
        p = nl.add(PI)
        k = nl.add(CONST)
        a = nl.add(COMB, (p, k))
        nl.add(COMB, (a,))  # drives nothing
        nl.po_drivers = [a]
        r = get(nl)
        self.assertEqual(r[("struct.fanout_hist", "0")], 1)  # the last node
        self.assertEqual(r[("struct.fanout_hist", "1")], 2)  # p and a (its PO pin is not an edge)
        self.assertEqual(r[("struct.mimir_fanout_po_hist", "2")], 1)  # a, counting the PO pin
        self.assertEqual(r[("struct.const_fanout_hist", "1")], 1)
        self.assertEqual(r[("struct.fanout_max", "")], 1)

    def test_reconv_split_by_stem_kind(self) -> None:
        nl = Netlist("kinds")
        p = nl.add(PI)
        s = nl.add(COMB, (p,))
        b = nl.add(COMB, (s,))
        c = nl.add(COMB, (s,))
        d = nl.add(COMB, (b, c))
        nl.po_drivers = [d]
        r = get(nl)
        self.assertEqual(r[("struct.mimir_reconv_stems", "comb")], 1)
        self.assertNotIn(("struct.mimir_reconv_stems", "pi"), r)  # p feeds one node
        self.assertEqual(r[("struct.mimir_reconv_span_mean", "comb")], 2.0)

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
        self.assertEqual(r[("struct.mimir_reconv_truncated", "pi")], 1)
        self.assertNotIn(("struct.mimir_reconv_stem_fraction", "pi"), r)  # nothing resolved

    def test_latch_cuts_depth(self) -> None:
        r = get(with_latch())
        self.assertEqual(r[("struct.depth", "")], 1)
        self.assertEqual(r[("struct.n_latch", "")], 1)
        self.assertEqual(r[("struct.level_width", "0")], 2)  # the PI and the latch are delay 0

    def test_loop_raises(self) -> None:
        nl = Netlist("loop")
        nl.add(COMB, (1,))
        nl.add(COMB, (0,))
        with self.assertRaises(ValueError):
            characterise(nl)


def thesis_cone() -> Netlist:
    """The 12-node out-cone of Hutton thesis Figure 4.3 (node 0 is the root), edges read from the
    Kirchhoff matrix on p. 52: three nodes have two fanins, so there are 2**3 spanning out-trees."""
    edges = [(0, 1), (0, 2), (1, 3), (2, 3), (2, 4), (3, 5), (4, 7), (5, 6), (6, 8), (6, 10),
             (7, 8), (7, 10), (8, 9), (10, 11)]
    nl = Netlist("fig4.3")
    nl.add(PI)
    for v in range(1, 12):
        nl.add(COMB, tuple(a for a, b in edges if b == v))
    nl.po_drivers = [9, 11]
    return nl


class ReconvergenceNumber(unittest.TestCase):
    def test_thesis_figure_4_3(self) -> None:
        r = get(thesis_cone())
        self.assertAlmostEqual(r[("struct.reconv_R", "")], 3 / 12)  # log2(8) / 12 nodes
        self.assertAlmostEqual(r[("struct.mimir_reconv_R_total_fanin", "")], 3 / 12)

    def test_weighted_over_pis(self) -> None:
        nl = Netlist("two")
        p = nl.add(PI)
        a = nl.add(COMB, (p,))
        b = nl.add(COMB, (p,))
        d = nl.add(COMB, (a, b))
        q = nl.add(PI)
        e = nl.add(COMB, (q,))
        nl.po_drivers = [d, e]
        # cone(p) = 4 nodes and one fanin-2 node: log2(2) = 1; cone(q) = 2 nodes: 0
        self.assertAlmostEqual(get(nl)[("struct.reconv_R", "")], 1 / 6)

    def test_fanin_outside_the_cone_is_the_second_reading(self) -> None:
        nl = Netlist("outside")
        p = nl.add(PI)
        a = nl.add(COMB, (p,))
        b = nl.add(COMB, (p,))
        z = nl.add(PI)
        d = nl.add(COMB, (a, b, z))
        nl.po_drivers = [d]
        r = get(nl)
        # cone(p) = {p, a, b, d}: d has 2 fanins in the cone (1 bit), 3 in all (log2 3 bits);
        # cone(z) = {z, d}: d has 1 fanin in it
        self.assertAlmostEqual(r[("struct.reconv_R", "")], 1 / 6)
        self.assertAlmostEqual(r[("struct.mimir_reconv_R_total_fanin", "")], 2 * math.log2(3) / 6)

    def test_cone_stops_at_a_latch_and_clocks_are_not_roots(self) -> None:
        nl = Netlist("seq")
        p = nl.add(PI)
        a = nl.add(COMB, (p,))
        b = nl.add(COMB, (p,))
        d = nl.add(COMB, (a, b))
        q = nl.add(LATCH, (d,))
        e = nl.add(COMB, (q, p))  # past the latch the cone of p does not continue
        clk = nl.add(PI)
        nl.clocks = {clk}
        nl.po_drivers = [e]
        self.assertAlmostEqual(get(nl)[("struct.reconv_R", "")], 1 / 5)  # {p, a, b, d, e}

    def test_seqcone_continues_through_a_latch(self) -> None:
        nl = Netlist("seqcone")
        p = nl.add(PI)
        a = nl.add(COMB, (p,))
        b = nl.add(COMB, (p,))
        d = nl.add(COMB, (a, b))
        q = nl.add(LATCH, (d,))
        e = nl.add(COMB, (q, p))  # reads p and the latch: 2 fanins inside the sequential cone
        nl.po_drivers = [e]
        r = get(nl)
        self.assertAlmostEqual(r[("struct.reconv_R", "")], 1 / 5)  # cone {p, a, b, d, e}
        self.assertAlmostEqual(r[("struct.mimir_reconv_R_seqcone", "")], 2 / 6)
        self.assertAlmostEqual(get(diamond())[("struct.mimir_reconv_R_seqcone", "")], 1 / 4)

    def test_budget_skips_the_metric(self) -> None:
        old = hutton.R_BUDGET
        hutton.R_BUDGET = 1
        try:
            r = get(diamond())
        finally:
            hutton.R_BUDGET = old
        self.assertNotIn(("struct.reconv_R", ""), r)


class SequentialLevels(unittest.TestCase):
    def test_latch_makes_two_levels(self) -> None:
        r = get(with_latch())
        self.assertEqual(r[("struct.seq_levels", "")], 2)
        self.assertEqual(r[("struct.seq_shape", "0")], 2)  # the PI and g
        self.assertEqual(r[("struct.seq_shape", "1")], 2)  # the latch and h
        self.assertEqual(r[("struct.n_back_edges", "")], 0)

    def test_feedback_is_a_back_edge(self) -> None:
        nl = with_latch()
        nl.add(COMB, (0, 3))  # reads the PI (level 0) and h (level 1)
        r = get(nl)
        self.assertEqual(r[("struct.n_back_edges", "")], 1)
        self.assertEqual(r[("struct.seq_shape", "0")], 3)  # the new node is level 0 (the minimum)

    def test_combinational_is_one_level(self) -> None:
        r = get(chain(3))
        self.assertEqual(r[("struct.seq_levels", "")], 1)
        self.assertEqual(r[("struct.seq_unreached", "")], 0)

    def test_node_without_a_pi_path_is_unreached(self) -> None:
        nl = Netlist("island")
        k = nl.add(CONST)
        nl.add(COMB, (k,))
        r = get(nl)
        self.assertEqual(r[("struct.seq_unreached", "")], 1)


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
        # stem s reconverges at d; stem a has the cone and no meeting
        self.assertEqual(r[("struct.mimir_reconv_span_mean", "comb")], 2.0)
        self.assertEqual(r[("struct.mimir_reconv_truncated", "comb")], 1)
        # 82 comb stems (s, a, 80 mids); a is truncated; one of the other 81 reconverges
        self.assertEqual(r[("struct.mimir_reconv_stems", "comb")], 82)
        self.assertAlmostEqual(r[("struct.mimir_reconv_stem_fraction", "comb")], 1 / 81)


if __name__ == "__main__":
    unittest.main()
