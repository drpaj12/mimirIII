from __future__ import annotations

import math
import statistics
import unittest
from unittest import mock

from mimir import rent
from mimir.netlist import COMB, PI, Netlist
from tests.helpers import chain, mesh, random_dag, random_graph, skip_without


def p_of(nl: Netlist, seeds: tuple[int, ...] = (1,)) -> list[float]:
    rows, _ = rent.measure(nl, seeds)
    return [v for m, _, _, v in rows if m == "rent.p"]


class Terminals(unittest.TestCase):
    def test_block_terminals(self) -> None:
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


def model_p(dims: tuple[int, ...]) -> float:
    """Expected fit exponent of a d-dimensional mesh of side n from a finite-size model, derived
    before the measurement. A cubic block of side s (B = s^d nodes) in the mesh has on average
    T = 2 d s^(d-1) (1 - s/n) terminals: each node reads its lower neighbour in every axis, so the
    nets crossing the block are the d upper faces (inside drivers, outside sinks) and the d lower
    faces (outside drivers), and a face on the edge of the mesh has no outside neighbour; the
    factor (1 - s/n) is the average fraction of faces that are not on the mesh edge. The model is
    fitted by least squares of log T on log B on the same block sizes N / 2^k and the same fit
    range as `rent.fit`, so it is the exponent the measurer should return for ideal cubic blocks.
    """
    d, n = len(dims), dims[0]
    total = n**d
    xs, ys = [], []
    k = 0
    while total / 2**k >= 4:
        b = total / 2**k
        if b <= total / 32:
            s = b ** (1 / d)
            xs.append(math.log(b))
            ys.append(math.log(2 * d * s ** (d - 1) * (1 - s / n)))
        k += 1
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    return sxy / sum((x - mx) ** 2 for x in xs)


@skip_without("pymetis")
class KnownExponents(unittest.TestCase):
    """The fit limit N/32 is fixed (see the spec, 5.3) and was tuned on meshes (exploratory), so
    the mesh checks are regression baselines at that limit plus a model band, not an independent
    test of the limit. The independent region-II check is `RegionTwo` below."""

    def test_chain_is_zero(self) -> None:
        self.assertAlmostEqual(p_of(chain(1024))[0], 0.0, delta=0.01)

    def test_mesh_2d(self) -> None:
        p = p_of(mesh((64, 64)))[0]
        self.assertAlmostEqual(model_p((64, 64)), 0.454, delta=0.001)  # recorded before the check
        self.assertAlmostEqual(p, model_p((64, 64)), delta=0.04)  # model band
        self.assertAlmostEqual(p, 0.471, delta=0.01)  # baseline at N/32, 5 seeds, sd 0.0024

    def test_mesh_3d(self) -> None:
        p = p_of(mesh((20, 20, 20)))[0]
        self.assertAlmostEqual(model_p((20, 20, 20)), 0.589, delta=0.001)
        self.assertAlmostEqual(p, model_p((20, 20, 20)), delta=0.07)  # blocks are not cubes
        self.assertAlmostEqual(p, 0.640, delta=0.01)  # baseline at N/32, 5 seeds, sd 0.0013

    def test_uniform_random_graph_is_high(self) -> None:
        # asymptote is 1; at N = 2048 the fit gives 0.8915 (5 seeds, sd 0.001)
        p = p_of(random_graph(2048, 3, 7))[0]
        self.assertGreater(p, 0.85)
        self.assertAlmostEqual(p, 0.8915, delta=0.01)

    def test_random_dag_baseline(self) -> None:
        # random_dag: each node reads 3 uniformly chosen EARLIER nodes (a DAG, not a uniform
        # random graph); baseline at N/32, 5 seeds 0.866, sd 0.0015
        self.assertAlmostEqual(p_of(random_dag(2048, 3, 7))[0], 0.866, delta=0.01)


class RegionTwo(unittest.TestCase):
    """Fit-range check on a synthetic T = k B^p with a roll-off above a known B."""

    N = 65536
    P = 0.62
    K = 4.0

    def curve(self) -> rent.Curve:
        c = rent.Curve(1)
        roll = self.N / rent.REGION2_DIV  # known roll-off point; above it T is below the law
        for depth in range(15):
            b = self.N / 2**depth
            t = self.K * b**self.P
            if b > roll:
                t *= (roll / b) ** 2
            c.depth.append(depth)
            c.blocks.append(2**depth)
            c.size.append(b)
            c.terminals.append(t)
        return c

    def test_recovers_p_and_excludes_the_roll_off(self) -> None:
        f = rent.fit(self.curve(), self.N)
        assert f is not None
        self.assertAlmostEqual(f.p, self.P, delta=1e-9)
        self.assertAlmostEqual(f.k, self.K, delta=1e-6)
        self.assertEqual(f.points, 10)  # B = 2048 (= N/32), 1024, ..., 4
        self.assertAlmostEqual(f.r2, 1.0, delta=1e-9)

    def test_a_limit_inside_the_roll_off_would_fail(self) -> None:
        # power of the test: with the limit raised to N/4 the roll-off enters and p is wrong
        c = self.curve()  # built with the real roll-off point
        with mock.patch.object(rent, "REGION2_DIV", 4):
            f = rent.fit(c, self.N)
        assert f is not None
        self.assertGreater(abs(f.p - self.P), 0.1)


@skip_without("pymetis")
class Construction(unittest.TestCase):
    def test_star_weight_never_zero_and_rooted_at_driver(self) -> None:
        pins = list(range(1000))
        edges = rent._pairs(pins, 400)
        self.assertEqual(len(edges), 999)
        self.assertTrue(all(400 in e for e in edges))
        net = rent.Net(tuple(pins), False, 400)
        xadj, adjncy, ew = rent._csr(pins, [net], {v: [0] for v in pins})
        self.assertEqual(min(ew), 1)  # 840 // 999 would be 0
        self.assertEqual(xadj[-1], len(adjncy))

    def test_driver_outside_the_block_roots_at_first_pin(self) -> None:
        self.assertEqual(rent._pairs(list(range(10)), -1)[0], (0, 1))

    def test_small_blocks_are_carried_to_deeper_depths(self) -> None:
        nodes, nets = rent.build_nets(chain(30))
        c = rent.curve(nodes, nets, 1)
        for blocks, size in zip(c.blocks, c.size, strict=True):
            self.assertEqual(round(blocks * size), len(nodes))  # every node is in every depth

    def test_low_confidence_flag(self) -> None:
        def flags(nl: Netlist) -> list[float]:
            rows, _ = rent.measure(nl, (1,))
            return [v for m, _, _, v in rows if m == "rent.low_confidence"]

        self.assertEqual(flags(chain(1024)), [1.0])  # 4 points
        self.assertEqual(flags(mesh((64, 64))), [0.0])  # 5 points


@skip_without("pymetis")
class Repeatability(unittest.TestCase):
    def test_same_seed_same_value(self) -> None:
        nl = random_dag(600, 3, 3)
        self.assertEqual(p_of(nl, (4,)), p_of(nl, (4,)))

    def test_seed_retest(self) -> None:
        # observed sd over 5 seeds: 0.0024 (2-D mesh), 0.0013 (3-D mesh), 0.001 (random graph)
        for nl in (mesh((64, 64)), mesh((20, 20, 20)), random_graph(2048, 3, 7)):
            ps = p_of(nl, (1, 2, 3, 4, 5))
            self.assertEqual(len(ps), 5)
            self.assertLess(statistics.pstdev(ps), 0.006)

    def test_small_netlist_skips_fit(self) -> None:
        rows, skipped = rent.measure(chain(300), (1,))
        self.assertEqual(skipped, 1)
        self.assertFalse([r for r in rows if r[0] == "rent.p"])


if __name__ == "__main__":
    unittest.main()
