"""Structural characterisation of a netlist in the spirit of Hutton et al. (see the spec, 5.2).

The definitions are Mimir's own: the sources were not readable in the lane that wrote this.
"""

from __future__ import annotations

from collections import Counter

from mimir.netlist import COMB, CONST, HARD, LATCH, PI, Netlist

VERSION = "struct-1"
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
    return rows


def _shape_rows(nl: Netlist, level: list[int]) -> list[Row]:
    comb = [v for v in range(len(nl)) if nl.kind[v] == COMB]
    depth = max((level[v] for v in comb), default=0)
    width = Counter(level[v] for v in comb)
    rows: list[Row] = [("struct.depth", "", float(depth))]
    rows += [
        ("struct.level_width", str(k), float(width[k])) for k in sorted(width) if k <= WIDTH_CAP
    ]
    lengths = Counter[int]()
    for v in comb:
        for u in nl.fanin[v]:
            lengths[level[v] - level[u]] += 1
    rows += [("struct.edge_len_hist", k, n) for k, n in _fold(lengths).items()]
    _stats(rows, "edge_len", list(lengths.elements()))
    return rows


def _fanout_rows(nl: Netlist) -> list[Row]:
    fan = Counter[int]()
    for drivers in nl.fanin:
        fan.update(drivers)
    fan.update(nl.po_drivers)
    sizes = Counter(fan.values())
    rows: list[Row] = [("struct.fanout_hist", k, n) for k, n in _fold(sizes).items()]
    _stats(rows, "fanout", list(fan.values()))
    return rows


def _reconv_one(stem: int, branches: list[int], sinks: list[list[int]], level: list[int]) -> int:
    """Level distance from the stem to its nearest reconvergence; 0 none found, -1 truncated."""
    limit = max(level[b] for b in branches) + WINDOW
    seen: dict[int, int] = {}
    best = 0
    for b, root in enumerate(branches):
        stack = [root]
        while stack:
            v = stack.pop()
            if level[v] > limit:
                continue
            owner = seen.get(v)
            if owner is not None:
                if owner != b:
                    d = level[v] - level[stem]
                    best = d if best == 0 else min(best, d)
                continue
            seen[v] = b
            if len(seen) > VISIT_BOUND:
                return best if best else -1
            stack.extend(sinks[v])
    return best


def _comb_sinks(nl: Netlist) -> list[list[int]]:
    out: list[list[int]] = [[] for _ in range(len(nl))]
    for v in range(len(nl)):
        if nl.kind[v] == COMB:
            for u in set(nl.fanin[v]):
                out[u].append(v)
    return out


def _reconv_rows(nl: Netlist, level: list[int]) -> list[Row]:
    sinks = _comb_sinks(nl)
    stems = [u for u in range(len(nl)) if len(sinks[u]) >= 2 and nl.kind[u] != CONST]
    spans: list[int] = []
    truncated = 0
    for s in stems:
        d = _reconv_one(s, sinks[s], sinks, level)
        if d > 0:
            spans.append(d)
        elif d < 0:
            truncated += 1
    rows: list[Row] = [
        ("struct.reconv_stems", "", float(len(stems))),
        ("struct.reconv_truncated", "", float(truncated)),
    ]
    if stems:
        rows.append(("struct.reconv_stem_fraction", "", len(spans) / len(stems)))
    if spans:
        rows.append(("struct.reconv_span_mean", "", sum(spans) / len(spans)))
    return rows


def characterise(nl: Netlist) -> list[Row]:
    """All structural rows for a netlist (metric, bin, value), in a fixed order."""
    level = levels(nl)
    return _size_rows(nl) + _shape_rows(nl, level) + _fanout_rows(nl) + _reconv_rows(nl, level)
