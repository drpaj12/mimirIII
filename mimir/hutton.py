"""Structural characterisation of a netlist in the spirit of Hutton et al. (see the spec, 5.2).

The definitions are Mimir's own: the sources were not readable in the lane that wrote this.
"""

from __future__ import annotations

from collections import Counter

from mimir.netlist import COMB, CONST, HARD, LATCH, PI, Netlist

VERSION = "struct-2"
WINDOW = 8  # reconvergence search window, in levels past the stem
VISIT_BOUND = 5000  # reconvergence search bound, in visited nodes per stem
HIST_CAP = 32  # histogram bins above this are folded into the bin "33+"
WIDTH_CAP = 64  # level_width bins above this are not written

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


def _size_rows(nl: Netlist) -> list[Row]:
    edges = sum(len(nl.fanin[v]) for v in range(len(nl)) if nl.kind[v] in (COMB, LATCH, HARD))
    sizes = {"n_comb": COMB, "n_latch": LATCH, "n_hard": HARD, "n_pi": PI, "n_const": CONST}
    rows: list[Row] = [(f"struct.{k}", "", float(nl.count(v))) for k, v in sizes.items()]
    rows.append(("struct.n_po", "", float(len(nl.po_drivers))))
    rows.append(("struct.n_edges", "", float(edges)))
    rows.append(("struct.n_undriven", "", float(nl.undriven)))
    rows.append(("struct.n_multidriven", "", float(nl.multidriven)))
    rows.append(("struct.n_clock_pi", "", float(len(nl.clocks))))
    return rows


def _shape_rows(nl: Netlist, level: list[int]) -> list[Row]:
    comb = [v for v in range(len(nl)) if nl.kind[v] == COMB]
    depth = max((level[v] for v in comb), default=0)
    width = Counter(level[v] for v in comb)
    rows: list[Row] = [("struct.depth", "", float(depth))]
    rows += [
        ("struct.level_width", str(k), float(width[k])) for k in sorted(width) if k <= WIDTH_CAP
    ]
    inner, source = Counter[int](), Counter[int]()
    for v in comb:
        for u in nl.fanin[v]:
            (inner if nl.kind[u] == COMB else source)[level[v] - level[u]] += 1
    rows += [("struct.edge_len_hist", k, n) for k, n in _fold(inner).items()]
    _stats(rows, "edge_len", list(inner.elements()))
    rows += [("struct.src_edge_len_hist", k, n) for k, n in _fold(source).items()]
    _stats(rows, "src_edge_len", list(source.elements()))
    return rows


def _fanout_rows(nl: Netlist) -> list[Row]:
    fan = Counter[int]()
    for drivers in nl.fanin:
        fan.update(drivers)
    fan.update(nl.po_drivers)
    real = [fan[v] for v in range(len(nl)) if nl.kind[v] != CONST and v not in nl.clocks]
    consts = [fan[v] for v in range(len(nl)) if nl.kind[v] == CONST]
    rows: list[Row] = [("struct.fanout_hist", k, n) for k, n in _fold(Counter(real)).items()]
    _stats(rows, "fanout", real)
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


def _reconv_rows(nl: Netlist, level: list[int]) -> list[Row]:
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
        rows.append(("struct.reconv_stems", kind, float(stems[kind])))
        rows.append(("struct.reconv_truncated", kind, float(truncated[kind])))
        resolved = stems[kind] - truncated[kind]
        found = spans.get(kind, [])
        if resolved:
            rows.append(("struct.reconv_stem_fraction", kind, len(found) / resolved))
        if found:
            rows.append(("struct.reconv_span_mean", kind, sum(found) / len(found)))
    return rows


def characterise(nl: Netlist) -> list[Row]:
    """All structural rows for a netlist (metric, bin, value), in a fixed order."""
    level = levels(nl)
    return _size_rows(nl) + _shape_rows(nl, level) + _fanout_rows(nl) + _reconv_rows(nl, level)
