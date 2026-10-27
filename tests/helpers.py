"""Shared test helpers: optional-dependency skips and small constructed netlists."""

from __future__ import annotations

import importlib.util
import unittest
from collections.abc import Callable
from typing import TypeVar

from mimir.netlist import COMB, LATCH, PI, Netlist

T = TypeVar("T", bound="Callable[..., object] | type")


def skip_without(module: str) -> Callable[[T], T]:
    """unittest decorator: skip when an optional library is not installed."""
    ok = importlib.util.find_spec(module) is not None
    return unittest.skipUnless(ok, f"{module} not installed")


def chain(n: int) -> Netlist:
    """PI -> n comb nodes in a row -> PO."""
    nl = Netlist(f"chain{n}")
    prev = nl.add(PI)
    for _ in range(n):
        prev = nl.add(COMB, (prev,))
    nl.po_drivers = [prev]
    return nl


def tree(depth: int) -> Netlist:
    """Balanced binary fan-in tree with 2**depth PIs and one PO."""
    nl = Netlist(f"tree{depth}")
    layer = [nl.add(PI) for _ in range(2**depth)]
    while len(layer) > 1:
        layer = [nl.add(COMB, (layer[i], layer[i + 1])) for i in range(0, len(layer), 2)]
    nl.po_drivers = layer
    return nl


def diamond() -> Netlist:
    """a -> (b, c) -> d: one reconvergent stem."""
    nl = Netlist("diamond")
    a = nl.add(PI)
    b = nl.add(COMB, (a,))
    c = nl.add(COMB, (a,))
    d = nl.add(COMB, (b, c))
    nl.po_drivers = [d]
    return nl


def ladder(n: int) -> Netlist:
    """n x n grid of comb nodes; node (i, j) reads (i-1, j) and (i, j-1); boundary reads PIs."""
    nl = Netlist(f"ladder{n}")
    top = [nl.add(PI) for _ in range(n)]
    left = [nl.add(PI) for _ in range(n)]
    cell: dict[tuple[int, int], int] = {}
    for i in range(n):
        for j in range(n):
            up = cell[(i - 1, j)] if i else top[j]
            lf = cell[(i, j - 1)] if j else left[i]
            cell[(i, j)] = nl.add(COMB, (up, lf))
    nl.po_drivers = [cell[(n - 1, n - 1)]]
    return nl


def with_latch() -> Netlist:
    """PI -> g -> latch -> h -> PO."""
    nl = Netlist("latch")
    a = nl.add(PI)
    g = nl.add(COMB, (a,))
    q = nl.add(LATCH, (g,))
    h = nl.add(COMB, (q,))
    nl.po_drivers = [h]
    return nl


def tmpdir() -> str:
    """A fresh temp directory under /tmp/claude-1000 if it exists, else the default location."""
    import os
    import tempfile

    base = "/tmp/claude-1000"
    return tempfile.mkdtemp(prefix="mim-test-", dir=base if os.path.isdir(base) else None)


def mesh(dims: tuple[int, ...]) -> Netlist:
    """A regular mesh: a comb node per grid point, reading its lower neighbour in each dimension."""
    import itertools

    nl = Netlist("mesh" + "x".join(map(str, dims)))
    ids: dict[tuple[int, ...], int] = {}
    for pt in itertools.product(*(range(d) for d in dims)):
        ins = []
        for axis in range(len(dims)):
            if pt[axis] > 0:
                ins.append(ids[(*pt[:axis], pt[axis] - 1, *pt[axis + 1 :])])
        ids[pt] = nl.add(PI) if not ins else nl.add(COMB, tuple(ins))
    nl.po_drivers = [len(nl) - 1]
    return nl


def random_dag(n: int, fanin: int, seed: int) -> Netlist:
    """A random netlist: each of n nodes reads `fanin` earlier nodes chosen uniformly."""
    import random

    rng = random.Random(seed)
    nl = Netlist(f"random{n}")
    for v in range(n):
        if v < fanin:
            nl.add(PI)
        else:
            nl.add(COMB, tuple(rng.sample(range(v), fanin)))
    nl.po_drivers = [n - 1]
    return nl


def random_graph(n: int, fanin: int, seed: int) -> Netlist:
    """A uniform random graph: each of n nodes reads `fanin` distinct other nodes chosen uniformly
    from all n (loops allowed; only for structure that does not need levels, such as Rent)."""
    import random

    rng = random.Random(seed)
    nl = Netlist(f"graph{n}")
    for v in range(n):
        picks: set[int] = set()
        while len(picks) < fanin:
            u = rng.randrange(n)
            if u != v:
                picks.add(u)
        nl.add(COMB, tuple(sorted(picks)))
    nl.po_drivers = [n - 1]
    return nl
