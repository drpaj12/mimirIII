"""Rent's rule by recursive bisection with METIS (needs the `partition` extra: pymetis).

Method and every Mimir choice are in the spec, section 5.3.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field

from mimir.netlist import COMB, CONST, HARD, LATCH, PI, UNDRIVEN, Netlist

MIN_NODES = 512  # fewer nodes than this cannot give 3 depths in the fit range; Rent is not run
MIN_FIT_BLOCK = 4  # smallest mean block size in the fit
REGION2_DIV = 32  # largest mean block size in the fit is N / REGION2_DIV (excludes region II)
CLIQUE_MAX = 8  # nets with more in-block pins use a star rooted at the driver
EDGE_UNIT = 840  # lcm(1..8): integer weight max(1, EDGE_UNIT // (k - 1)) per edge
SPLIT_MIN = 4  # blocks with fewer nodes are not split; they are carried to the deeper depths
LOW_POINTS = 5  # a fit on fewer points than this is flagged low-confidence


@dataclass
class Net:
    pins: tuple[int, ...]  # node ids inside the partitioned set
    external: bool  # also touches the outside world (a PI or undriven driver, or a PO)
    driver: int = -1  # the driving node when it is inside the partitioned set, else -1


@dataclass
class Curve:
    """Mean block size B and mean terminals T per recursion depth, from one partitioner seed."""

    seed: int
    depth: list[int] = field(default_factory=list)
    blocks: list[int] = field(default_factory=list)
    size: list[float] = field(default_factory=list)
    terminals: list[float] = field(default_factory=list)


@dataclass(frozen=True)
class Fit:
    p: float
    k: float
    r2: float
    points: int


def partitioner_version() -> str:
    """The identifier recorded as the measurer version."""
    import pymetis

    return f"rent-1/pymetis-{pymetis.version}"


def build_nets(nl: Netlist) -> tuple[list[int], list[Net]]:
    """The partitioned node set (comb, latch, hard) and its nets (one per driving node)."""
    inside = {HARD, COMB, LATCH}
    nodes = [v for v in range(len(nl)) if nl.kind[v] in inside]
    sinks: list[list[int]] = [[] for _ in range(len(nl))]
    for v in nodes:
        for u in set(nl.fanin[v]):
            sinks[u].append(v)
    po = set(nl.po_drivers)
    nets: list[Net] = []
    for u in range(len(nl)):
        if nl.kind[u] == CONST:
            continue
        pins = ([u] if nl.kind[u] in inside else []) + sinks[u]
        ext = nl.kind[u] in (PI, UNDRIVEN) or u in po
        if len(pins) + (1 if ext else 0) >= 2 and pins:
            nets.append(Net(tuple(pins), ext, u if nl.kind[u] in inside else -1))
    return nodes, nets


def terminals(block: set[int], incident: Sequence[int], nets: Sequence[Net]) -> int:
    """Nets with a pin in `block` and a pin (or the outside world) outside it."""
    count = 0
    for ni in incident:
        net = nets[ni]
        inside = sum(1 for p in net.pins if p in block)
        if inside and (net.external or inside < len(net.pins)):
            count += 1
    return count


Csr = tuple[list[int], list[int], list[int]]


def _pairs(pins: list[int], driver: int) -> list[tuple[int, int]]:
    """Edges of one net in the block: a clique up to CLIQUE_MAX pins, else a star rooted at the
    driver (at the first pin when the driver is outside the block)."""
    if len(pins) <= CLIQUE_MAX:
        return [(a, b) for i, a in enumerate(pins) for b in pins[i + 1 :]]
    root = driver if driver in pins else pins[0]
    return [(root, b) for b in pins if b != root]


def _csr(block: list[int], nets: Sequence[Net], incident: dict[int, list[int]]) -> Csr:
    """Weighted CSR adjacency of the block (clique for small nets, a star for large ones)."""
    local = {v: i for i, v in enumerate(block)}
    adj: list[dict[int, int]] = [{} for _ in block]
    seen: set[int] = set()
    for v in block:
        for ni in incident[v]:
            if ni in seen:
                continue
            seen.add(ni)
            pins = [local[p] for p in nets[ni].pins if p in local]
            if len(pins) < 2:
                continue
            w = max(1, EDGE_UNIT // (len(pins) - 1))
            pairs = _pairs(pins, local.get(nets[ni].driver, -1))
            for a, b in pairs:
                adj[a][b] = adj[a].get(b, 0) + w
                adj[b][a] = adj[b].get(a, 0) + w
    xadj, adjncy, ew = [0], [], []
    for row in adj:
        for b in sorted(row):
            adjncy.append(b)
            ew.append(row[b])
        xadj.append(len(adjncy))
    return xadj, adjncy, ew


def bisect(
    block: list[int], nets: Sequence[Net], incident: dict[int, list[int]], seed: int
) -> tuple[list[int], list[int]]:
    """Split a block in two with METIS; fall back to halves when the graph has no edges."""
    import pymetis

    xadj, adjncy, ew = _csr(block, nets, incident)
    half = len(block) // 2
    if not adjncy:
        return block[:half], block[half:]
    opts = pymetis.Options()
    opts.seed = seed
    res = pymetis.part_graph(
        2, adjacency=pymetis.CSRAdjacency(xadj, adjncy), eweights=ew, options=opts
    )
    left = [v for v, p in zip(block, res.vertex_part, strict=True) if p == 0]
    right = [v for v, p in zip(block, res.vertex_part, strict=True) if p != 0]
    if not left or not right:
        return block[:half], block[half:]
    return left, right


def curve(nodes: list[int], nets: list[Net], seed: int) -> Curve:
    """Recursive bisection; one point set per depth, each over all blocks of that depth.

    A block with fewer than SPLIT_MIN nodes is not split but stays in the deeper depths, so a
    depth's mean is over the whole partition and not only over the blocks that can still split.
    Recursion ends at the first depth in which no block can be split."""
    incident: dict[int, list[int]] = {v: [] for v in nodes}
    for ni, net in enumerate(nets):
        for p in net.pins:
            incident[p].append(ni)
    out = Curve(seed)
    level = [sorted(nodes)]
    depth = 0
    while level:
        sizes: list[int] = []
        terms: list[int] = []
        nxt: list[list[int]] = []
        for block in level:
            members = set(block)
            inc = sorted({ni for v in block for ni in incident[v]})
            sizes.append(len(block))
            terms.append(terminals(members, inc, nets))
            if len(block) >= SPLIT_MIN:
                nxt.extend(bisect(block, nets, incident, seed))
            else:
                nxt.append(block)
        out.depth.append(depth)
        out.blocks.append(len(level))
        out.size.append(sum(sizes) / len(sizes))
        out.terminals.append(sum(terms) / len(terms))
        level, depth = (nxt if any(len(b) >= SPLIT_MIN for b in level) else []), depth + 1
    return out


def fit(c: Curve, n_nodes: int) -> Fit | None:
    """Least squares of log T on log B over MIN_FIT_BLOCK <= B <= N / REGION2_DIV (None if < 3)."""
    xs, ys = [], []
    for b, t in zip(c.size, c.terminals, strict=True):
        if MIN_FIT_BLOCK <= b <= n_nodes / REGION2_DIV and t > 0:
            xs.append(math.log(b))
            ys.append(math.log(t))
    if len(xs) < 3:
        return None
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    syy = sum((y - my) ** 2 for y in ys)
    slope = sxy / sxx
    r2 = 1.0 if syy == 0 else (sxy * sxy) / (sxx * syy)
    return Fit(slope, math.exp(my - slope * mx), r2, len(xs))


Row = tuple[str, str, int, float]  # metric, bin, seed, value


def measure(nl: Netlist, seeds: Sequence[int] = (1, 2, 3)) -> tuple[list[Row], int]:
    """Rent rows for each seed and the number of seeds whose fit was skipped."""
    nodes, nets = build_nets(nl)
    rows: list[Row] = [("rent.nodes", "", -1, float(len(nodes)))]
    skipped = 0
    if len(nodes) < MIN_NODES:
        return rows, len(seeds)
    for seed in seeds:
        c = curve(nodes, nets, seed)
        for d, b, t in zip(c.depth, c.size, c.terminals, strict=True):
            rows.append(("rent.curve_b", str(d), seed, b))
            rows.append(("rent.curve_t", str(d), seed, t))
        f = fit(c, len(nodes))
        if f is None:
            skipped += 1
            continue
        rows += [("rent.p", "", seed, f.p), ("rent.k", "", seed, f.k),
                 ("rent.r2", "", seed, f.r2), ("rent.points", "", seed, float(f.points)),
                 ("rent.low_confidence", "", seed, float(f.points < LOW_POINTS))]
    return rows, skipped
