"""Structural characterisation of a netlist after Hutton (PhD thesis, Toronto 1997) and Hutton,
Rose and Corneil (IEEE TCAD 2002); page numbers are in `metrics.toml` and the spec, 5.2.

Metrics named `struct.mimir_*` are Mimir's own variants, kept apart from the published ones."""

from __future__ import annotations

import math
from collections import Counter, deque

from mimir.netlist import COMB, CONST, HARD, LATCH, PI, Netlist

VERSION = "struct-3"
WINDOW = 8  # reconvergence search window, in levels past the stem
VISIT_BOUND = 5000  # reconvergence search bound, in visited nodes per stem
HIST_CAP = 32  # histogram bins above this are folded into the bin "33+"
WIDTH_CAP = 64  # level_width bins above this are not written
R_BUDGET = 50_000_000  # reconv_R is skipped when PIs x comb fanin pins exceeds this

Row = tuple[str, str, float]  # metric, bin, value


def levels(nl: Netlist) -> list[int]:
    """Comb level per node: sources (PI, const, latch, hard) are 0, a comb node is 1 + max fanin.

    Raises ValueError when the comb nodes contain a loop."""
    n = len(nl)
    level = [0] * n
    pending = [0] * n
    sinks: list[list[int]] = [[] for _ in range(n)]
    ready: list[int] = []
    for v in range(n):
        if nl.kind[v] != COMB:
            continue
        comb_in = [u for u in nl.fanin[v] if nl.kind[u] == COMB]
        pending[v] = len(comb_in)
        for u in comb_in:
            sinks[u].append(v)
        if not comb_in:
            level[v] = 1
            ready.append(v)
    done = 0
    while ready:
        u = ready.pop()
        done += 1
        for v in sinks[u]:
            level[v] = max(level[v], level[u] + 1)
            pending[v] -= 1
            if pending[v] == 0:
                ready.append(v)
    if done != nl.count(COMB):
        raise ValueError("combinational loop")
    return level


def _fold(counter: Counter[int]) -> dict[str, float]:
    out: dict[str, float] = {}
    for key, n in counter.items():
        label = str(key) if key <= HIST_CAP else f"{HIST_CAP + 1}+"
        out[label] = out.get(label, 0.0) + n
    return out


def _stats(rows: list[Row], name: str, values: list[int]) -> None:
    if values:
        rows.append((f"struct.{name}_mean", "", sum(values) / len(values)))
        rows.append((f"struct.{name}_max", "", float(max(values))))


def _data_pis(nl: Netlist) -> list[int]:
    """PIs that carry data: clock PIs are not part of Hutton's model (thesis p. 26, p. 45)."""
    return [v for v in range(len(nl)) if nl.kind[v] == PI and v not in nl.clocks]


def _size_rows(nl: Netlist) -> list[Row]:
    edges = sum(len(nl.fanin[v]) for v in range(len(nl)) if nl.kind[v] in (COMB, LATCH, HARD))
    sizes = {"n_comb": COMB, "n_latch": LATCH, "n_hard": HARD, "n_pi": PI, "n_const": CONST}
    rows: list[Row] = [(f"struct.{k}", "", float(nl.count(v))) for k, v in sizes.items()]
    n_pi = len(_data_pis(nl))
    rows.append(("struct.n_po", "", float(len(nl.po_drivers))))
    rows.append(("struct.size", "", float(n_pi + nl.count(COMB) + nl.count(LATCH))))
    rows.append(("struct.n_io", "", float(n_pi + len(nl.po_drivers))))
    rows.append(("struct.n_edges", "", float(edges)))
    k = max((len(set(nl.fanin[v])) for v in range(len(nl)) if nl.kind[v] == COMB), default=0)
    rows.append(("struct.fanin_max", "", float(k)))
    rows.append(("struct.n_undriven", "", float(nl.undriven)))
    rows.append(("struct.n_multidriven", "", float(nl.multidriven)))
    rows.append(("struct.n_clock_pi", "", float(len(nl.clocks))))
    return rows


def _shape_rows(nl: Netlist, level: list[int]) -> list[Row]:
    """Delay depth, shape (bin 0 = PIs and latches, delay 0) and the edge-length distribution.

    Hutton's edge length is delay(sink) - delay(source) over every fanin pin of a logic node, PI
    pins included; the comb-to-comb and source-driven parts are also written, as Mimir splits."""
    comb = [v for v in range(len(nl)) if nl.kind[v] == COMB]
    depth = max((level[v] for v in comb), default=0)
    width = Counter(level[v] for v in comb)
    width[0] = len(_data_pis(nl)) + nl.count(LATCH)
    rows: list[Row] = [("struct.depth", "", float(depth))]
    rows += [
        ("struct.level_width", str(k), float(width[k])) for k in sorted(width) if k <= WIDTH_CAP
    ]
    every, inner, source = Counter[int](), Counter[int](), Counter[int]()
    for v in comb:
        for u in nl.fanin[v]:
            length = level[v] - level[u]
            every[length] += 1
            (inner if nl.kind[u] == COMB else source)[length] += 1
    for name, counter in (("edge_len", every), ("mimir_edge_len_comb", inner),
                          ("mimir_edge_len_src", source)):
        rows += [(f"struct.{name}_hist", k, n) for k, n in _fold(counter).items()]
        _stats(rows, name, list(counter.elements()))
    return rows


def _fanout_rows(nl: Netlist, level: list[int]) -> list[Row]:
    """Hutton fanout = edges leaving a node (thesis p. 26: a PO pin is not an edge), and the
    delay-level fanout shape; the variant that counts PO pins as sinks is `mimir_fanout_po`."""
    fan = Counter[int]()
    for drivers in nl.fanin:
        fan.update(drivers)
    with_po = Counter[int](fan)
    with_po.update(nl.po_drivers)
    nodes = [v for v in range(len(nl)) if nl.kind[v] != CONST and v not in nl.clocks]
    real = [fan[v] for v in nodes]
    rows: list[Row] = [("struct.fanout_hist", k, n) for k, n in _fold(Counter(real)).items()]
    _stats(rows, "fanout", real)
    shape = Counter[int]()
    for v in nodes:
        shape[level[v]] += fan[v]
    rows += [("struct.fanout_shape", str(k), float(shape[k])) for k in sorted(shape)
             if k <= WIDTH_CAP]
    po = [with_po[v] for v in nodes]
    rows += [("struct.mimir_fanout_po_hist", k, n) for k, n in _fold(Counter(po)).items()]
    _stats(rows, "mimir_fanout_po", po)
    consts = [fan[v] for v in range(len(nl)) if nl.kind[v] == CONST]
    rows += [("struct.const_fanout_hist", k, n) for k, n in _fold(Counter(consts)).items()]
    return rows


def _reconv_one(stem: int, branches: list[int], sinks: list[list[int]], level: list[int]) -> int:
    """Level distance from the stem to its nearest reconvergence; 0 none found, -1 truncated.

    All branches advance together, one level at a time, so the nearest meeting is found first and
    a large cone on one branch cannot use up the bound before the other branches are searched."""
    limit = max(level[b] for b in branches) + WINDOW
    pending: dict[int, dict[int, set[int]]] = {}  # level -> node -> branches that reach it

    def push(v: int, owners: set[int]) -> None:
        if level[v] <= limit:
            pending.setdefault(level[v], {}).setdefault(v, set()).update(owners)

    for b, root in enumerate(branches):
        push(root, {b})
    visited = 0
    while pending:
        lv = min(pending)
        front = pending.pop(lv)
        if any(len(owners) > 1 for owners in front.values()):
            return lv - level[stem]
        visited += len(front)
        if visited > VISIT_BOUND:
            return -1
        for v, owners in front.items():
            for w in sinks[v]:
                push(w, owners)
    return 0


def _comb_sinks(nl: Netlist) -> list[list[int]]:
    out: list[list[int]] = [[] for _ in range(len(nl))]
    for v in range(len(nl)):
        if nl.kind[v] == COMB:
            for u in set(nl.fanin[v]):
                out[u].append(v)
    return out


def _mimir_reconv_rows(nl: Netlist, level: list[int]) -> list[Row]:
    """Per stem kind: stems, truncated, fraction of resolved stems that reconverge, mean span."""
    sinks = _comb_sinks(nl)
    stems: dict[str, int] = Counter()
    truncated: dict[str, int] = Counter()
    spans: dict[str, list[int]] = {}
    for s in range(len(nl)):
        if len(sinks[s]) < 2 or nl.kind[s] == CONST:
            continue
        kind = nl.kind[s]
        stems[kind] += 1
        d = _reconv_one(s, sinks[s], sinks, level)
        if d > 0:
            spans.setdefault(kind, []).append(d)
        elif d < 0:
            truncated[kind] += 1
    rows: list[Row] = []
    for kind in sorted(stems):
        rows.append(("struct.mimir_reconv_stems", kind, float(stems[kind])))
        rows.append(("struct.mimir_reconv_truncated", kind, float(truncated[kind])))
        resolved = stems[kind] - truncated[kind]
        found = spans.get(kind, [])
        if resolved:
            rows.append(("struct.mimir_reconv_stem_fraction", kind, len(found) / resolved))
        if found:
            rows.append(("struct.mimir_reconv_span_mean", kind, sum(found) / len(found)))
    return rows


def _cone_sums(
    pis: list[int], sinks: list[list[int]], dfan: dict[int, tuple[int, ...]], n: int
) -> tuple[float, float, int]:
    """Over the out-cones of `pis` (breadth-first along `sinks`): the sum of log2(fanin inside
    the cone), the sum of log2(full fanin) and the total cone size. The root adds 0."""
    mark = [-1] * n
    in_cone = total = 0.0
    size = 0
    for tag, x in enumerate(pis):
        mark[x] = tag
        cone = [x]
        for u in cone:  # the list grows while it is scanned: a breadth-first walk
            for w in sinks[u]:
                if mark[w] != tag:
                    mark[w] = tag
                    cone.append(w)
        size += len(cone)
        for y in cone[1:]:
            in_cone += math.log2(sum(1 for u in dfan[y] if mark[u] == tag))
            total += math.log2(len(dfan[y]))
    return in_cone, total, size


def _reconv_r_rows(nl: Netlist) -> list[Row]:
    """Hutton's reconvergence number R(G) (thesis p. 33-34, eq. 3.2): the weighted (by out-cone
    size) average over the data PIs of R(x) = sum over the out-cone of x of log2(fanin in the
    cone) / out-cone size. The out-cone follows logic nodes only (a forward edge, p. 45), so it
    stops at latches; the root has no fanin in its cone and adds 0. Written only when the work
    (PIs x fanin pins) is within R_BUDGET.

    Mimir variants: `mimir_reconv_R_total_fanin` uses the full fanin of each cone node (the
    wording of eq. 3.2 allows it); `mimir_reconv_R_seqcone` lets the cone continue through latches,
    counting like R but over the sequential out-cone (thesis p. 50-53 defines R_s by spanning-tree
    counts, which Mimir does not compute). Without latches the cones are equal."""
    pis = _data_pis(nl)
    pins = sum(len(nl.fanin[v]) for v in range(len(nl)) if nl.kind[v] in (COMB, LATCH))
    if not pis or len(pis) * pins > R_BUDGET:
        return []
    n = len(nl)
    sinks = _comb_sinks(nl)
    dfan = {v: tuple(set(nl.fanin[v])) for v in range(n) if nl.kind[v] in (COMB, LATCH)}
    in_cone, total, size = _cone_sums(pis, sinks, dfan, n)
    if nl.count(LATCH):
        through: list[list[int]] = [[] for _ in range(n)]
        for v in range(n):
            if nl.kind[v] in (COMB, LATCH):
                for u in dfan[v]:
                    through[u].append(v)
        seq_cone, _, seq_size = _cone_sums(pis, through, dfan, n)
    else:
        seq_cone, seq_size = in_cone, size
    return [("struct.reconv_R", "", in_cone / size),
            ("struct.mimir_reconv_R_total_fanin", "", total / size),
            ("struct.mimir_reconv_R_seqcone", "", seq_cone / seq_size)]


def seq_levels(nl: Netlist) -> list[int]:
    """Hutton's sequential level (thesis p. 45, TCAD 2002 Def. 2.2): 0 for a PI, 1 + the level of
    the D input for a latch, the minimum over the fanins otherwise. That is the fewest latches on
    any path from a PI, found by a 0-1 breadth-first search; -1 when no PI reaches the node."""
    sinks = nl.sinks()
    lvl = [-1] * len(nl)
    queue: deque[tuple[int, int]] = deque()
    for v in range(len(nl)):
        if nl.kind[v] == PI:
            lvl[v] = 0
            queue.append((0, v))
    while queue:
        d, u = queue.popleft()
        if d > lvl[u]:
            continue
        for v in sinks[u]:
            step = 1 if nl.kind[v] == LATCH else 0
            if lvl[v] < 0 or d + step < lvl[v]:
                lvl[v] = d + step
                (queue.append if step else queue.appendleft)((d + step, v))
    return lvl


def _seq_rows(nl: Netlist) -> list[Row]:
    """Sequential levels, the sequential shape (nodes per level: PIs, logic nodes, latches) and
    the back edges (a fanin pin of a logic node whose driver is at a deeper level)."""
    lvl = seq_levels(nl)
    data = {PI, COMB, LATCH}
    shape = Counter(lvl[v] for v in range(len(nl))
                    if nl.kind[v] in data and lvl[v] >= 0 and v not in nl.clocks)
    back = sum(1 for v in range(len(nl)) if nl.kind[v] in (COMB, HARD) and lvl[v] >= 0
               for u in nl.fanin[v] if lvl[u] > lvl[v])
    lost = sum(1 for v in range(len(nl)) if nl.kind[v] in (COMB, LATCH, HARD) and lvl[v] < 0)
    rows: list[Row] = [("struct.seq_levels", "", float(max(shape, default=-1) + 1))]
    rows += [("struct.seq_shape", str(k), float(shape[k])) for k in sorted(shape)]
    rows.append(("struct.n_back_edges", "", float(back)))
    rows.append(("struct.seq_unreached", "", float(lost)))
    return rows


def characterise(nl: Netlist) -> list[Row]:
    """All structural rows for a netlist (metric, bin, value), in a fixed order."""
    level = levels(nl)
    return (_size_rows(nl) + _shape_rows(nl, level) + _fanout_rows(nl, level)
            + _seq_rows(nl) + _reconv_r_rows(nl) + _mimir_reconv_rows(nl, level))
