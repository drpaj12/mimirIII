"""Line-level HDL graph of a run: which source line (and word, bit) feeds which, from the run's
stored BLIF and Odin III name map. Spec: docs/specs/2026-10-28-hdl-graph.md.

An atom is a primitive of the BLIF (LUT, flip-flop, adder cell, hard block); its source location is
Odin III's own atom -> span provenance (`timing_attr.Resolver`, the code the timing attribution
uses), so a node of this graph is the same (file:line, module, word, bit) as a node of a stored
timing path. An atom the name map does not hold has no location: the graph passes through it
(its fan-in is joined to its fan-out), so a chain of generated LUTs does not cut a cone.
"""

from __future__ import annotations

import importlib
import sys
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mimir.blif import Model, parse_models
from mimir.scrub import Scrubber, check_clean
from mimir.store import Store
from mimir.structmap import FF, atom_candidates

NO_SOURCE_NETS = frozenset(("gnd", "vcc", "unconn"))
CLOCK_PINS = frozenset(("clk", "clock", "clock0", "clock1"))
PI, PO = "PI", "PO"

Node = tuple[str, str, str, int]
"""(span file:line, module, word, bit); bit -1 when the origin gives none."""
Edge = tuple[Node, Node, int]
"""(source, destination, via_register): 1 when the signal leaves a register's output."""
Port = tuple[Node, str, str]
"""(node, kind PI or PO, port bit name)"""


@dataclass
class Graph:
    edges: set[Edge]
    ports: set[Port]
    n_atoms: int
    n_unattributed: int


def load_resolver_module(odin3_tree: Path) -> Any:
    """Import Odin III's `timing_attr` (and with it `name_map_v2`) from `<tree>/tools/flow`."""
    flow = str(odin3_tree / "tools" / "flow")
    if flow not in sys.path:
        sys.path.insert(0, flow)
    return importlib.import_module("timing_attr")


@dataclass(frozen=True)
class _Atom:
    name: str
    block_type: str
    cls: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]


def _atom_of(head: str, args: list[str], outs: Mapping[str, set[str]], nm: Any, top: str
             ) -> _Atom | None:
    got = atom_candidates(head, args, outs)
    if got is None or not got[0]:
        return None
    cands, cls = got
    name = next((c for c in cands if nm.atom(c, top) is not None), cands[0])
    if head == ".names":
        return _Atom(name, head, cls, tuple(args[:-1]), (args[-1],))
    if head == ".latch":
        return _Atom(name, head, cls, (args[0],), (args[1],))
    pins = [a.split("=", 1) for a in args[1:] if "=" in a]
    wanted = outs.get(args[0], set())
    is_out = [p.split("[")[0] in wanted or p in wanted for p, _ in pins]
    ins = tuple(n for (p, n), o in zip(pins, is_out, strict=True)
                if not o and p.split("[")[0].lower() not in CLOCK_PINS)
    outn = tuple(n for (_p, n), o in zip(pins, is_out, strict=True) if o)
    return _Atom(name, args[0], cls, ins, outn or tuple(n for _p, n in pins))


def _node(origin: Any) -> Node | None:
    span = origin.span
    if origin.category != "matched" or span is None:
        return None
    return (span, origin.module or "", origin.word or "", origin.bit if origin.bit is not None
            else -1)


def build(models: Sequence[Model], nm: Any, resolver_mod: Any) -> Graph:
    """The graph of the top model `models[0]` with the name map `nm` (see the module doc)."""
    top = models[0]
    outs = {m.name: set(m.outputs) for m in models}
    res = resolver_mod.Resolver(nm, None, top.name)
    atoms = [a for h, args in top.items
             if (a := _atom_of(h, args, outs, nm, top.name)) is not None]
    driver = {n: a for a in atoms for n in a.outputs}
    node_of = {a.name: _node(res.resolve(a.name, a.block_type)) for a in atoms}
    pi_node = {n: _node(res.resolve(n, ".names")) for n in top.inputs}
    memo: dict[str, frozenset[tuple[Node, int]]] = {}

    def sources(net: str, reg: int, seen: frozenset[str]) -> frozenset[tuple[Node, int]]:
        """Attributed sources feeding `net` (through atoms without a location)."""
        if net in NO_SOURCE_NETS:
            return frozenset()
        a = driver.get(net)
        if a is None:
            n = pi_node.get(net)
            return frozenset({(n, reg)}) if n is not None else frozenset()
        flag = reg or int(a.cls == FF)
        if node_of[a.name] is not None:
            return frozenset({(node_of[a.name], flag)})  # type: ignore[arg-type]
        return through(a, flag, seen)

    def through(a: _Atom, flag: int, seen: frozenset[str]) -> frozenset[tuple[Node, int]]:
        if a.name in seen:
            return frozenset()
        key = f"{a.name}/{flag}"
        if key not in memo:
            out: set[tuple[Node, int]] = set()
            for net in a.inputs:
                out |= sources(net, flag, seen | {a.name})
            memo[key] = frozenset(out)
        return memo[key]

    edges: set[Edge] = set()
    for a in atoms:
        dst = node_of[a.name]
        if dst is None:
            continue
        for net in a.inputs:
            for src, flag in sources(net, 0, frozenset({a.name})):
                if src != dst or flag:
                    edges.add((src, dst, flag))
    ports = _ports(top, node_of, pi_node, driver)
    return Graph(edges, ports, len(atoms), sum(1 for v in node_of.values() if v is None))


def _ports(top: Model, node_of: Mapping[str, Node | None], pi_node: Mapping[str, Node | None],
           driver: Mapping[str, _Atom]) -> set[Port]:
    out: set[Port] = set()
    for n in top.inputs:
        node = pi_node.get(n)
        if node is not None and n not in NO_SOURCE_NETS:
            out.add((node, PI, n))
    for n in top.outputs:
        a = driver.get(n)
        node = node_of.get(a.name) if a is not None else None
        if node is not None:
            out.add((node, PO, n))
    return out


# ---------------------------------------------------------------- store

TABLES = ("hdl_graph_run", "hdl_edge", "hdl_port")


def has_tables(store: Store) -> bool:
    found = {r[0] for r in store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    return all(t in found for t in TABLES)


def write_graph(store: Store, run_id: str, g: Graph, scrub: Scrubber, blif_sha: str,
                map_sha: str) -> tuple[int, int]:
    """Replace the run's rows. Does not commit. Raises ValueError before the first write when a
    /home path would be stored. Returns (edge rows, port rows)."""

    def n(node: Node) -> tuple[str, str, str, int]:
        t = scrub.text
        return (t(node[0]), t(node[1]), t(node[2]), node[3])

    erows = sorted((*n(s), *n(d), v) for s, d, v in g.edges)
    prows = sorted((*n(nd), k, scrub.text(p)) for nd, k, p in g.ports)
    for row in erows + prows:
        if not all(check_clean(x) for x in row if isinstance(x, str)):
            raise ValueError(f"run {run_id}: a graph text holds a /home path")
    db = store.db
    for t in TABLES:
        db.execute(f"DELETE FROM {t} WHERE run_id = ?", (run_id,))
    db.execute("INSERT INTO hdl_graph_run VALUES (?, ?, ?, ?, ?, ?, ?)",
               (run_id, g.n_atoms, g.n_unattributed, len(erows), len(prows), blif_sha, map_sha))
    db.executemany("INSERT INTO hdl_edge VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   [(run_id, *r) for r in erows])
    db.executemany("INSERT INTO hdl_port VALUES (?, ?, ?, ?, ?, ?, ?)",
                   [(run_id, *r) for r in prows])
    return len(erows), len(prows)


def build_run(store: Store, run_id: str, blobs_dir: Path, scrub: Scrubber, odin3_tree: Path,
              tmp_dir: Path) -> tuple[int, int]:
    """Build and store the graph of one run from its `blif` and `map` artifacts (sha256 checked).
    `tmp_dir` holds the map file the parser needs. One transaction."""
    from mimir import blobs

    rows = dict(store.db.execute(
        "SELECT kind, blob_sha256 FROM run_artifact WHERE run_id = ? AND kind IN ('blif', 'map')",
        (run_id,)).fetchall())
    if len(rows) != 2:
        raise ValueError(f"run {run_id}: needs a blif and a map artifact")
    mod = load_resolver_module(odin3_tree)
    blif = blobs.get_bytes(blobs_dir, rows["blif"]).decode("utf-8", "replace")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    map_path = tmp_dir / f"{run_id}.blif.names"
    map_path.write_bytes(blobs.get_bytes(blobs_dir, rows["map"]))
    nm = importlib.import_module("name_map_v2").read_name_map(map_path)
    g = build(parse_models(blif), nm, mod)
    db = store.db
    try:
        db.execute("BEGIN")
        counts = write_graph(store, run_id, g, scrub, rows["blif"], rows["map"])
        db.commit()
    except BaseException:
        db.rollback()
        raise
    return counts


def backfill(store: Store, blobs_dir: Path, scrub: Scrubber, odin3_tree: Path, tmp_dir: Path,
             only: set[str] | None = None) -> list[tuple[str, str]]:
    """Build the graph of every run that has a blif and a map artifact and no `hdl_graph_run`
    row. Idempotent. Returns (run_id, status) rows: `ok n edges` or `error: ...`."""
    todo = [r[0] for r in store.db.execute(
        "SELECT a.run_id FROM run_artifact a WHERE a.kind = 'map' AND a.run_id IN "
        "(SELECT run_id FROM run_artifact WHERE kind = 'blif') AND NOT EXISTS "
        "(SELECT 1 FROM hdl_graph_run g WHERE g.run_id = a.run_id) ORDER BY a.run_id")]
    out = []
    for run_id in todo:
        if only is not None and run_id not in only:
            continue
        try:
            e, p = build_run(store, run_id, blobs_dir, scrub, odin3_tree, tmp_dir)
            out.append((run_id, f"ok {e} edges {p} ports"))
        except (ValueError, KeyError, OSError) as exc:
            out.append((run_id, f"error: {exc}"))
    return out


def edge_stats(store: Store) -> Mapping[str, int]:
    d: dict[str, int] = defaultdict(int)
    for k, v in store.db.execute("SELECT 'runs', COUNT(*) FROM hdl_graph_run UNION ALL "
                                 "SELECT 'edges', COUNT(*) FROM hdl_edge UNION ALL "
                                 "SELECT 'ports', COUNT(*) FROM hdl_port"):
        d[str(k)] = int(v)
    return d
