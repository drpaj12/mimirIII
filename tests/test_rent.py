from __future__ import annotations

import statistics
import unittest

from mimir.netlist import COMB, PI, Netlist
from tests.helpers import chain, mesh, random_dag, skip_without


def p_of(nl: Netlist, seeds: tuple[int, ...] = (1,)) -> list[float]:
    from mimir import rent

    rows, _ = rent.measure(nl, seeds)
    return [v for m, _, _, v in rows if m == "rent.p"]


class Terminals(unittest.TestCase):
    def test_block_terminals(self) -> None:
        from mimir import rent

        nl = Netlist("t")
        a = nl.add(PI)
        b = nl.add(COMB, (a,))
        c = nl.add(COMB, (b,))
        d = nl.add(COMB, (b, c))
        nl.po_drivers = [d]
        nodes, nets = rent.build_nets(nl)
        self.assertEqual(nodes, [b, c, d])
        inc = list(range(len(nets)))
        self.assertEqual(rent.terminals({b, c, d}, inc, nets), 2)  # the PI net and the PO net
        self.assertEqual(rent.terminals({b}, inc, nets), 2)  # PI net in, net b out
        self.assertEqual(rent.terminals({c}, inc, nets), 2)  # net b in, net c out
        self.assertEqual(rent.terminals({d}, inc, nets), 3)  # nets b, c in, PO out


@skip_without("pymetis")
class KnownExponents(unittest.TestCase):
    def test_chain_is_zero(self) -> None:
        self.assertAlmostEqual(p_of(chain(1024))[0], 0.0, delta=0.05)

    def test_mesh_2d(self) -> None:
        self.assertAlmostEqual(p_of(mesh((64, 64)))[0], 0.5, delta=0.1)

    def test_mesh_3d(self) -> None:
        self.assertAlmostEqual(p_of(mesh((20, 20, 20)))[0], 2 / 3, delta=0.1)

    def test_random_is_high(self) -> None:
        self.assertGreater(p_of(random_dag(2048, 3, 7))[0], 0.8)


@skip_without("pymetis")
class Repeatability(unittest.TestCase):
    def test_same_seed_same_value(self) -> None:
        nl = random_dag(600, 3, 3)
        self.assertEqual(p_of(nl, (4,)), p_of(nl, (4,)))

    def test_seed_retest(self) -> None:
        for nl in (mesh((64, 64)), random_dag(2048, 3, 7)):
            ps = p_of(nl, (1, 2, 3, 4, 5))
            self.assertEqual(len(ps), 5)
            self.assertLess(statistics.pstdev(ps), 0.02)

    def test_small_netlist_skips_fit(self) -> None:
        from mimir import rent

        rows, skipped = rent.measure(chain(300), (1,))
        self.assertEqual(skipped, 1)
        self.assertFalse([r for r in rows if r[0] == "rent.p"])


if __name__ == "__main__":
    unittest.main()
