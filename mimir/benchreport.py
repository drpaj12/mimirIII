"""`mimir bench report --html OUT`: one self-contained page (inline CSS, SVG and JS, no network)
that shows the benchmark registry and, where a design is in the Mimir store, its main metrics."""

from __future__ import annotations

import sqlite3
import statistics
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote

from mimir import bench, remote

# store metric key -> (column id, label, unit)
METRICS = {
    "struct.size": ("nodes", "nodes (PI + LUT + FF)", "nodes"),
    "struct.n_comb": ("luts", "LUTs", "LUTs"),
    "struct.n_latch": ("ffs", "flip-flops", "flip-flops"),
    "struct.depth": ("depth", "logic depth", "levels"),
    "rent.p": ("rent", "Rent exponent p", "ratio"),
}
# registry suites whose store records are named by (source, name) rather than by slug or hash
NAME_RULES = {"vtr-blif-k4": ("mcnc-k4", ""), "verilogeval": ("loki:loki-veval-exp/dataset", "ve_")}
PUBLIC = "public"


@dataclass
class Row:
    suite: str
    design: str
    format: str
    top: str
    bytes: int
    lines: int
    licence_rule: str
    flows: list[str]
    join: str = "-"
    metrics: dict[str, float] = field(default_factory=dict)


@dataclass
class Report:
    date: str
    commit: str
    suites: list[bench.Suite]
    rows: list[Row]
    flows: Counter[str]
    flow_info: dict[str, bench.Flow]
    withheld_netlists: int
    joins: Counter[str]
    store: str


# ---- store -------------------------------------------------------------------------------------

def open_ro(path: Path) -> sqlite3.Connection:
    """The store, read only (never written)."""
    con = sqlite3.connect(f"file:{quote(str(path))}?mode=ro", uri=True)
    con.execute("PRAGMA query_only = ON")
    return con


def _store_maps(con: sqlite3.Connection) -> tuple[dict[str, list[tuple[str, str]]],
                                                  dict[str, str], set[tuple[str, str]]]:
    """slug -> (source, name) pairs; design_hash -> slug; every (source, name) of the records."""
    pairs: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for source, name, slug in con.execute("SELECT source, name, slug FROM design_source"):
        pairs[slug].append((source, name))
    by_hash = {h: s for s, h in con.execute("SELECT slug, design_hash FROM design")}
    seen = set(con.execute("SELECT DISTINCT source, design FROM records"))
    return pairs, by_hash, seen


def _values(con: sqlite3.Connection) -> dict[tuple[str, str], dict[str, float]]:
    """Median over seeds and sources of each main metric at LUT level, per (source, design)."""
    marks = ",".join("?" * len(METRICS))
    q = (f"SELECT source, design, metric, value FROM records WHERE metric IN ({marks}) "
         "AND level = 'lut' AND bin = '' AND arm = ''")
    acc: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for source, design, metric, value in con.execute(q, list(METRICS)):
        acc[(source, design, metric)].append(value)
    out: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
    for (source, design, metric), vals in acc.items():
        out[(source, design)][metric] = statistics.median(vals)
    return out


def join_store(rows: list[Row], designs: list[bench.Design], con: sqlite3.Connection) -> None:
    """Attach store metrics to rows. Match order: registry slug, then sha256 equal to the store's
    design_hash, then the (source, name) rule of NAME_RULES."""
    pairs, by_hash, seen = _store_maps(con)
    vals = _values(con)
    for row, d in zip(rows, designs, strict=True):
        slug, how = (d.slug, "slug") if d.slug in pairs else (by_hash.get(d.sha256, ""), "hash")
        cand = pairs.get(slug, []) if slug else []
        if not cand and d.suite in NAME_RULES:
            src, pre = NAME_RULES[d.suite]
            cand, how = ([(src, pre + d.design)] if (src, pre + d.design) in seen else []), "name"
        merged: dict[str, list[float]] = defaultdict(list)
        for key in cand:
            for metric, v in vals.get(key, {}).items():
                merged[metric].append(v)
        if cand:
            row.join = how
        row.metrics = {m: statistics.median(v) for m, v in merged.items()}


# ---- registry ----------------------------------------------------------------------------------

def registry_commit(idx: Path) -> str:
    try:
        out = subprocess.run(["git", "-C", str(idx), "rev-parse", "HEAD"], capture_output=True,
                             text=True, check=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return out.stdout.strip() or "unknown"


def _public_netlists(idx: Path, nets: list[bench.Netlist]) -> list[bench.Netlist]:
    """Netlists whose own blob the blob index lists as public (no index: none)."""
    try:
        index = remote.load_blob_index(idx)
    except (OSError, ValueError):
        return []
    return [n for n in nets if n.sha256 in index and index[n.sha256].visibility == PUBLIC]


def collect(idx: Path, db: Path | None, date: str, commit: str = "") -> Report:
    suites = bench.load_suites(idx)
    designs = bench.load_designs(idx)
    all_nets = bench.load_netlists(idx)
    nets = _public_netlists(idx, all_nets)
    flows = bench.load_flows(idx)
    have: dict[tuple[str, str], list[str]] = defaultdict(list)
    for n in nets:
        have[(n.suite, n.design)].append(n.flow)
    rows = [Row(d.suite, d.design, d.format, d.top, d.bytes, d.lines, d.licence_rule,
                sorted(have[(d.suite, d.design)])) for d in designs]
    store = "none"
    if db is not None:
        con = open_ro(db)
        try:
            join_store(rows, designs, con)
        finally:
            con.close()
        store = db.name
    joins = Counter(r.join for r in rows)
    return Report(date, commit or registry_commit(idx), list(suites.values()), rows,
                  Counter(n.flow for n in nets), flows, len(all_nets) - len(nets), joins, store)
