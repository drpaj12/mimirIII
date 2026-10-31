"""The benchmark registry: suites, flows, designs and compiled netlists (`data/benchmarks/`).

Spec: docs/specs/2026-10-31-benchmarks-design.md. Reference form: `suite:design@flow`.
"""

from __future__ import annotations

import os
import re
import tomllib
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, TypeVar

from mimir import blobs, remote
from mimir.scrub import check_clean

HOSTING = ("public", "local-only", "unchecked")
NONE = "-"
T = TypeVar("T")


class BenchError(Exception):
    pass


@dataclass(frozen=True)
class Suite:
    id: str
    title: str
    format: str
    upstream: str
    commit: str
    external: str
    subdir: str
    licence: str
    licence_source: str
    hosting: str
    obtained: str
    default_flow: str = ""
    glob: str = ""
    list: str = ""
    slug_prefix: str = ""
    top: str = ""
    strip_suffix: str = ""
    note: str = ""


@dataclass(frozen=True)
class Flow:
    id: str
    tool: str
    tool_version: str
    tool_commit: str
    binary_sha256: str
    input: str
    arch: str
    lut_k: int
    script: str
    source: str
    layout: str = ""
    record: str = ""
    build: str = ""
    note: str = ""


@dataclass(frozen=True)
class Design:
    suite: str
    design: str
    slug: str
    path: str
    format: str
    top: str
    bytes: int
    lines: int
    sha256: str
    licence_rule: str


@dataclass(frozen=True)
class Netlist:
    suite: str
    design: str
    flow: str
    sha256: str
    raw_bytes: int
    map_sha256: str
    flowrec_sha256: str
    origin: str

    def shas(self) -> list[str]:
        return [s for s in (self.sha256, self.map_sha256, self.flowrec_sha256) if s != NONE]


def index_dir() -> Path:
    env = os.environ.get("MIMIR_BENCH_INDEX")
    return Path(env) if env else Path(__file__).resolve().parents[1] / "data" / "benchmarks"


def external_root() -> Path:
    env = os.environ.get("MIMIR_EXTERNAL")
    return Path(env) if env else Path.home() / "odin3-ws" / "external"


# ---- files -------------------------------------------------------------------------------------

def _build(cls: type[T], item: dict[str, Any], names: set[str]) -> T:
    extra = sorted(set(item) - names)
    if extra:
        raise BenchError(f"{cls.__name__}: unknown keys {extra}")
    try:
        return cls(**item)
    except TypeError as exc:
        raise BenchError(f"{cls.__name__} {item.get('id', item)}: {exc}") from exc


def load_suites(idx: Path | None = None) -> dict[str, Suite]:
    path = (idx or index_dir()) / "suites.toml"
    out: dict[str, Suite] = {}
    for item in tomllib.loads(path.read_text(encoding="utf-8")).get("suite", []):
        suite = _build(Suite, item, {f.name for f in fields(Suite)})
        if suite.hosting not in HOSTING:
            raise BenchError(f"suite {suite.id}: bad hosting {suite.hosting!r}")
        if suite.id in out:
            raise BenchError(f"duplicate suite {suite.id}")
        out[suite.id] = suite
    return out


def load_flows(idx: Path | None = None) -> dict[str, Flow]:
    path = (idx or index_dir()) / "flows.toml"
    out: dict[str, Flow] = {}
    for item in tomllib.loads(path.read_text(encoding="utf-8")).get("flow", []):
        flow = _build(Flow, item, {f.name for f in fields(Flow)})
        if flow.id in out:
            raise BenchError(f"duplicate flow {flow.id}")
        out[flow.id] = flow
    return out


def read_tsv(path: Path, ncols: int) -> list[list[str]]:
    if not path.exists():
        return []
    rows = [ln.split("\t") for ln in path.read_text(encoding="utf-8").splitlines()[1:] if ln]
    for row in rows:
        if len(row) != ncols:
            raise BenchError(f"{path.name}: expected {ncols} columns, got {len(row)}: {row[:2]}")
    return rows


def write_tsv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    for row in rows:
        if any("\t" in c or "\n" in c for c in row):
            raise BenchError(f"{path.name}: tab or newline in a field: {row[:2]}")
    text = "\n".join("\t".join(r) for r in [header, *sorted(rows)]) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


DESIGN_COLS = [f.name for f in fields(Design)]
NETLIST_COLS = [f.name for f in fields(Netlist)]


def load_designs(idx: Path | None = None) -> list[Design]:
    rows = read_tsv((idx or index_dir()) / "designs.tsv", len(DESIGN_COLS))
    return [Design(r[0], r[1], r[2], r[3], r[4], r[5], int(r[6]), int(r[7]), r[8], r[9])
            for r in rows]


def save_designs(idx: Path, designs: list[Design]) -> None:
    write_tsv(idx / "designs.tsv", DESIGN_COLS,
              [[d.suite, d.design, d.slug, d.path, d.format, d.top, str(d.bytes), str(d.lines),
                d.sha256, d.licence_rule] for d in designs])


def load_netlists(idx: Path | None = None) -> list[Netlist]:
    rows = read_tsv((idx or index_dir()) / "netlists.tsv", len(NETLIST_COLS))
    return [Netlist(r[0], r[1], r[2], r[3], int(r[4]), r[5], r[6], r[7]) for r in rows]


def save_netlists(idx: Path, netlists: list[Netlist]) -> None:
    write_tsv(idx / "netlists.tsv", NETLIST_COLS,
              [[n.suite, n.design, n.flow, n.sha256, str(n.raw_bytes), n.map_sha256,
                n.flowrec_sha256, n.origin] for n in netlists])


def write_blob_index(idx: Path, store: Path, suites: dict[str, Suite],
                     netlists: list[Netlist]) -> int:
    """`blobs.tsv.xz` (the data/remote format) for every blob the netlist rows name."""
    rows: dict[str, list[str]] = {}
    for n in netlists:
        vis = "public" if suites[n.suite].hosting == "public" else "private"
        for sha in n.shas():
            raw = blobs.get_bytes(store, sha)
            xz = blobs.blob_path(store, sha).stat().st_size
            rows[sha] = [sha, str(xz), str(len(raw)), "-", vis]
    text = "".join("\t".join(r) + "\n" for r in sorted(rows.values()))
    remote.write_xz(idx / "blobs.tsv.xz", text.encode("utf-8"))
    return len(rows)


# ---- references --------------------------------------------------------------------------------

_REF = re.compile(r"([^:@\s]+):([^@\s]+)(?:@([^@\s]+))?")


def parse_ref(ref: str) -> tuple[str, str, str | None]:
    m = _REF.fullmatch(ref)
    if not m:
        raise BenchError(f"not a benchmark reference (suite:design[@flow]): {ref!r}")
    return m.group(1), m.group(2), m.group(3)


@dataclass(frozen=True)
class Resolved:
    suite: Suite
    design: Design
    netlist: Netlist | None


def resolve(ref: str, idx: Path | None = None, need_netlist: bool = False) -> Resolved:
    suite_id, name, flow = parse_ref(ref)
    suites = load_suites(idx)
    if suite_id not in suites:
        raise BenchError(f"unknown suite {suite_id!r}")
    suite = suites[suite_id]
    designs = [d for d in load_designs(idx) if d.suite == suite_id and d.design == name]
    if not designs:
        raise BenchError(f"{suite_id}: no design {name!r}")
    nets = [n for n in load_netlists(idx) if n.suite == suite_id and n.design == name]
    chosen = _choose(suite, nets, flow, ref)
    if need_netlist and chosen is None:
        raise BenchError(f"{ref}: no netlist registered")
    return Resolved(suite, designs[0], chosen)


def _choose(suite: Suite, nets: list[Netlist], flow: str | None, ref: str) -> Netlist | None:
    if flow is not None:
        hit = [n for n in nets if n.flow == flow]
        if not hit:
            have = sorted(n.flow for n in nets)
            raise BenchError(f"{ref}: no netlist for flow {flow!r} (have {have})")
        return hit[0]
    if len(nets) <= 1:
        return nets[0] if nets else None
    hit = [n for n in nets if n.flow == suite.default_flow]
    if not hit:
        raise BenchError(f"{ref}: ambiguous, flows {sorted(n.flow for n in nets)}; add @flow")
    return hit[0]


def source_path(suite: Suite, design: Design) -> Path:
    return external_root() / suite.external / suite.subdir / design.path


def materialise(ref: str, out: Path | None = None, kind: str = "netlist",
                idx: Path | None = None, loc: remote.Locations | None = None) -> Path:
    """Write the netlist (or its `map`, `flow` record) of a reference, sha256 verified; the
    `source` kind returns the path of the checkout file after checking its hash."""
    res = resolve(ref, idx, need_netlist=kind != "source")
    if kind == "source":
        path = source_path(res.suite, res.design)
        if res.design.format == "verilog-project":
            raise BenchError(f"{ref}: a project; its files are under {path}")
        if not path.is_file() or remote.sha256_path(path) != res.design.sha256:
            raise BenchError(f"{ref}: checkout file missing or changed: get {res.suite.upstream} "
                             f"at {res.suite.commit}, file {res.design.path}")
        return path
    assert res.netlist is not None
    sha = {"netlist": res.netlist.sha256, "map": res.netlist.map_sha256,
           "flow": res.netlist.flowrec_sha256}.get(kind)
    if sha is None:
        raise BenchError(f"unknown kind {kind!r} (netlist, map, flow, source)")
    if sha == NONE:
        raise BenchError(f"{ref}: no {kind} registered")
    try:
        return remote.fetch_blob(idx or index_dir(), loc or remote.Locations.from_env(), sha, out)
    except remote.FetchError as exc:
        raise BenchError(str(exc)) from exc


# ---- consistency -------------------------------------------------------------------------------

def check(idx: Path | None = None, store: Path | None = None, verify: bool = False) -> list[str]:
    """Problems of the committed index (and, with `store`, of the blobs it names)."""
    idx = idx or index_dir()
    suites, flows = load_suites(idx), load_flows(idx)
    designs = {(d.suite, d.design): d for d in load_designs(idx)}
    nets = load_netlists(idx)
    probs = _check_refs(suites, flows, designs, nets)
    for p in (idx / "suites.toml", idx / "flows.toml", idx / "designs.tsv", idx / "netlists.tsv"):
        if not check_clean(p.read_text(encoding="utf-8")):
            probs.append(f"{p.name}: holds a /home path")
    index = remote.load_blob_index(idx) if (idx / "blobs.tsv.xz").exists() else {}
    for sha in sorted({s for n in nets for s in n.shas()}):
        if sha not in index:
            probs.append(f"blob {sha}: not in blobs.tsv.xz")
        elif store is not None and not blobs.blob_path(store, sha).is_file():
            probs.append(f"blob {sha}: not in the local store")
    if store is not None and verify:
        probs += blobs.verify(store, sorted({s for n in nets for s in n.shas()
                                             if blobs.blob_path(store, s).is_file()}))
    return probs


def _check_refs(suites: dict[str, Suite], flows: dict[str, Flow],
                designs: dict[tuple[str, str], Design], nets: list[Netlist]) -> list[str]:
    probs = []
    for d in designs.values():
        if d.suite not in suites:
            probs.append(f"design {d.suite}:{d.design}: unknown suite")
    for s in suites.values():
        if s.default_flow and s.default_flow not in flows:
            probs.append(f"suite {s.id}: unknown default_flow {s.default_flow}")
    seen: set[tuple[str, str, str]] = set()
    for n in nets:
        key = (n.suite, n.design, n.flow)
        if key in seen:
            probs.append(f"netlist {key}: duplicate")
        seen.add(key)
        if (n.suite, n.design) not in designs:
            probs.append(f"netlist {key}: design not registered")
        if n.flow not in flows:
            probs.append(f"netlist {key}: unknown flow")
        if n.suite in suites and suites[n.suite].hosting == "unchecked":
            probs.append(f"netlist {key}: suite licence unchecked, no blobs allowed")
    return probs
