"""Near-critical timing data: criticality of reported paths, per-run statistics and per-HDL-object
rows. Spec: docs/specs/2026-10-28-near-critical.md."""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mimir.schema import Record
from mimir.scrub import Scrubber, check_clean
from mimir.store import Store

THETAS = (0.90, 0.95, 0.99)
THETA_KEYS = ("090", "095", "099")
BINS = 20
DEFAULT_N = 100  # VPR's default --timing_report_npaths
SOURCE_MEASURER = "import-timing"
_CLOCKED = re.compile(r"clocked by ([^)\s]+)")
_LOC = re.compile(r"^(.*):(\d+)\.(\d+)-(\d+)\.(\d+)$")
_LINE = re.compile(r"^(.*):(\d+)$")


@dataclass(frozen=True)
class Node:
    """One path node as far as the HDL link needs it."""

    module: str
    span: str
    loc: str
    word: str
    bit: int
    via: str
    delay: float


@dataclass(frozen=True)
class PathRow:
    index: int
    start: str
    end: str
    slack: float
    required: float
    nodes: tuple[Node, ...]


@dataclass(frozen=True)
class TimingInput:
    """The paths of one run's report and what the source says about N."""

    paths: tuple[PathRow, ...]
    cpd_ns: float | None
    requested: int | None
    in_report: int
    kind: str  # 'attribution' or 'report'
    sha256: str


@dataclass(frozen=True)
class StructSpan:
    """An HDL structure's span: file base name and (line, column) start and end."""

    structure_id: str
    base: str
    start: tuple[int, int]
    end: tuple[int, int]


@dataclass
class Acc:
    """Per-object accumulator."""

    crit_max: float = 0.0
    paths: set[int] = field(default_factory=set)
    near: list[set[int]] = field(default_factory=lambda: [set(), set(), set()])
    delay090: float = 0.0
    vias: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class RunStats:
    cpd_ns: float | None
    worst_slack_ns: float | None
    requested: int | None
    in_report: int
    used: int
    max_req_ns: float | None
    pairs: int
    pairs_skipped: int
    last_crit: float | None
    trunc: tuple[int, int, int]
    n_paths: tuple[int, int, int]
    n_endpoints: tuple[int, int, int]


@dataclass(frozen=True)
class Result:
    stats: RunStats
    hist: dict[int, int]
    objects: dict[tuple[str, str, int], Acc]
    delay_total090: float


def _node(raw: Mapping[str, Any]) -> Node:
    bit = raw.get("bit")
    return Node(str(raw.get("module") or ""), str(raw.get("span") or ""),
                str(raw.get("loc") or ""), str(raw.get("word") or ""),
                bit if isinstance(bit, int) else -1, str(raw.get("word_via") or ""),
                float(raw.get("delay_ns") or 0.0))


def parse_attribution(data: Mapping[str, Any], sha256: str) -> TimingInput:
    """Read an odin3 attribution.json (schema_version 1)."""
    if data.get("schema_version") != 1:
        raise ValueError(f"attribution schema_version {data.get('schema_version')!r} is not 1")
    t = data.get("timing", {})
    rows = tuple(
        PathRow(int(p["index"]), str(p.get("startpoint", "")), str(p.get("endpoint", "")),
                float(p["slack_ns"]), float(p["required_ns"]),
                tuple(_node(n) for n in p.get("nodes", [])))
        for p in data.get("paths", []))
    req = t.get("paths_requested")
    inrep = t.get("paths_in_report")
    return TimingInput(rows, t.get("cpd_ns"), req if isinstance(req, int) else None,
                       int(inrep) if isinstance(inrep, int) else len(rows), "attribution", sha256)


_RPT_FIELDS = {"Startpoint": "start", "Endpoint": "end"}
_NUM = r"(-?\d+(?:\.\d+)?)"
_SLACK = re.compile(r"^slack \((?:VIOLATED|MET)\)\s+" + _NUM, re.M)
_REQ = re.compile(r"^data required time\s+" + _NUM, re.M)


def parse_report(text: str, sha256: str, requested: int | None = None) -> TimingInput:
    """Read a VPR `report_timing.setup.rpt`: path-level only (no HDL link)."""
    blocks = re.split(r"^#Path \d+\s*$", text, flags=re.M)[1:]
    rows = []
    for i, blk in enumerate(blocks, 1):
        st = re.search(r"^Startpoint:\s*(.*)$", blk, re.M)
        en = re.search(r"^Endpoint\s*:\s*(.*)$", blk, re.M)
        sl = _SLACK.search(blk)
        rq = _REQ.findall(blk)
        if not (st and en and sl and rq):
            continue  # a truncated last path is skipped, not guessed
        rows.append(PathRow(i, st.group(1), en.group(1), float(sl.group(1)), float(rq[-1]), ()))
    if not rows:
        raise ValueError("no usable setup path in the report")
    return TimingInput(tuple(rows), -rows[0].slack if rows[0].slack < 0 else None, requested,
                       len(rows), "report", sha256)


def domain_pair(row: PathRow) -> tuple[str, str]:
    a, b = _CLOCKED.search(row.start), _CLOCKED.search(row.end)
    return (a.group(1) if a else "", b.group(1) if b else "")


def path_criticalities(paths: Sequence[PathRow]) -> tuple[dict[int, float], int, int, float | None]:
    """Relaxed criticality per path index (VPR 9 calc_relaxed_criticality, per clock domain pair
    of the report). Returns (crit by index, pairs, pairs skipped, max_req of the worst pair)."""
    groups: dict[tuple[str, str], list[PathRow]] = defaultdict(list)
    for p in paths:
        groups[domain_pair(p)].append(p)
    crit: dict[int, float] = {}
    skipped = 0
    first_req: float | None = None
    for pair, rows in sorted(groups.items()):
        worst = min(r.slack for r in rows)
        max_req = max(r.required for r in rows)
        shift = -worst if worst < 0 else 0.0
        denom = max_req + shift
        if denom < 0 or (denom == 0 and any(r.slack + shift != 0 for r in rows)):
            skipped += 1
            continue
        if first_req is None or pair == domain_pair(paths[0]):
            first_req = max_req
        for r in rows:
            c = 1.0 if denom == 0 else 1.0 - (r.slack + shift) / denom
            crit[r.index] = min(1.0, max(0.0, c))
    return crit, len(groups), skipped, first_req


def bin_of(c: float) -> int:
    return min(BINS - 1, int(c * BINS))


_SPAN_COLS = re.compile(r"^(.*):(\d+)\.(\d+)-(\d+)\.(\d+)(?::\w+)?$")
_SPAN_LINES = re.compile(r"^(.*):(\d+)-(\d+)$")
_BIG = 10**9


def _struct_spans(rows: Iterable[tuple[str, str]]) -> list[StructSpan]:
    """StructSpans from (structure_id, hdl_span) rows. Two forms: `file:L-L` (the lane 3 HDL
    structures: whole lines) and `[hdl:]file:L.C-L.C[:op]`; a detector structure has an empty
    span and gives none."""
    out = []
    for sid, span in rows:
        text = span[4:] if span.startswith("hdl:") else span
        m = _SPAN_COLS.match(text)
        if m:
            out.append(StructSpan(sid, m.group(1).rsplit("/", 1)[-1],
                                  (int(m.group(2)), int(m.group(3))),
                                  (int(m.group(4)), int(m.group(5)))))
            continue
        m2 = _SPAN_LINES.match(text)
        if m2:
            out.append(StructSpan(sid, m2.group(1).rsplit("/", 1)[-1], (int(m2.group(2)), 0),
                                  (int(m2.group(3)), _BIG)))
    return out


def structures_of(node: Node, by_base: Mapping[str, Sequence[StructSpan]]) -> list[str]:
    """Structures whose span holds the node: its full `loc` when it has one, else its line."""
    m = _LOC.match(node.loc)
    if m:
        base = m.group(1).rsplit("/", 1)[-1]
        s, e = (int(m.group(2)), int(m.group(3))), (int(m.group(4)), int(m.group(5)))
        return [x.structure_id for x in by_base.get(base, ()) if x.start <= s and e <= x.end]
    m2 = _LINE.match(node.span)
    if not m2:
        return []
    base, line = m2.group(1).rsplit("/", 1)[-1], int(m2.group(2))
    return [x.structure_id for x in by_base.get(base, ())
            if x.start[0] <= line <= x.end[0]]


def object_keys(node: Node, scrub: Scrubber) -> list[tuple[str, str, int, str]]:
    """(kind, key, bit, via) rows one node feeds (spec 2.4)."""
    out: list[tuple[str, str, int, str]] = []
    if node.module:
        out.append(("module", scrub.text(node.module), -1, ""))
    if node.span:
        out.append(("span", scrub.text(node.span), -1, ""))
    if node.word and node.module and node.via in ("name", "pad", "declarator", "json-id"):
        key = scrub.text(f"{node.module}/{node.word}")
        out.append(("word", key, -1, node.via))
        if node.bit >= 0 and node.via in ("name", "pad"):
            out.append(("word", key, node.bit, node.via))
    return out


def analyse(inp: TimingInput, structs: Iterable[tuple[str, str]] = (),
            scrub: Scrubber | None = None) -> Result:
    """Criticalities, histogram, run statistics and object accumulators (spec 2, 3)."""
    scrub = scrub or Scrubber({})
    crit, pairs, skipped, max_req = path_criticalities(inp.paths)
    by_base: dict[str, list[StructSpan]] = defaultdict(list)
    for s in _struct_spans(structs):
        by_base[s.base].append(s)
    used = [p for p in inp.paths if p.index in crit]
    hist: dict[int, int] = defaultdict(int)
    objs: dict[tuple[str, str, int], Acc] = defaultdict(Acc)
    ends: list[set[str]] = [set(), set(), set()]
    total090 = 0.0
    for p in used:
        c = crit[p.index]
        hist[bin_of(c)] += 1
        for i, th in enumerate(THETAS):
            if c >= th:
                ends[i].add(p.end)
        if c >= THETAS[0]:
            total090 += sum(n.delay for n in p.nodes)
        _add_path(p, c, objs, by_base, scrub)
    worst = min((p.slack for p in inp.paths), default=None)
    last = crit.get(inp.paths[-1].index) if inp.paths else None
    n_req = inp.requested or DEFAULT_N
    full = inp.in_report >= n_req or len(inp.paths) < inp.in_report
    trunc = tuple(int(full and last is not None and last >= th) for th in THETAS)
    counts = tuple(sum(1 for p in used if crit[p.index] >= th) for th in THETAS)
    stats = RunStats(inp.cpd_ns, worst, inp.requested, inp.in_report, len(used), max_req, pairs,
                     skipped, last, (trunc[0], trunc[1], trunc[2]),
                     (counts[0], counts[1], counts[2]),
                     (len(ends[0]), len(ends[1]), len(ends[2])))
    return Result(stats, dict(sorted(hist.items())), dict(objs), total090)


def _add_path(p: PathRow, c: float, objs: dict[tuple[str, str, int], Acc],
              by_base: Mapping[str, Sequence[StructSpan]], scrub: Scrubber) -> None:
    delays: dict[tuple[str, str, int], float] = defaultdict(float)
    vias: dict[tuple[str, str, int], set[str]] = defaultdict(set)
    for n in p.nodes:
        keys = [(k, key, bit, via) for k, key, bit, via in object_keys(n, scrub)]
        keys += [("structure", scrub.text(s), -1, "") for s in structures_of(n, by_base)]
        for kind, key, bit, via in keys:
            delays[(kind, key, bit)] += n.delay
            if via:
                vias[(kind, key, bit)].add(via)
    for ident, delay in delays.items():
        acc = objs[ident]
        acc.crit_max = max(acc.crit_max, c)
        acc.paths.add(p.index)
        acc.vias |= vias[ident]
        for i, th in enumerate(THETAS):
            if c >= th:
                acc.near[i].add(p.index)
        if c >= THETAS[0]:
            acc.delay090 += delay


def _round(x: float | None) -> float | None:
    return None if x is None else round(x, 6)


def write_result(store: Store, run_id: str, inp: TimingInput, res: Result,
                 analysis_n: int | None = None) -> int:
    """Replace the run's rows in the three tables and its records. Returns the object rows."""
    db = store.db
    s = res.stats
    for table in ("timing_run", "timing_path_hist", "timing_object"):
        db.execute(f"DELETE FROM {table} WHERE run_id = ?", (run_id,))
    db.execute("INSERT INTO timing_run VALUES (" + ", ".join("?" * 20) + ")",
               (run_id, s.cpd_ns, s.worst_slack_ns, s.requested, s.in_report, s.used,
                s.max_req_ns, "report", s.pairs, s.pairs_skipped, _round(s.last_crit),
                *s.trunc, *s.n_endpoints, inp.kind, inp.sha256, analysis_n))
    db.executemany("INSERT INTO timing_path_hist VALUES (?, ?, ?)",
                   [(run_id, b, n) for b, n in sorted(res.hist.items())])
    rows = []
    for (kind, key, bit), a in sorted(res.objects.items()):
        share = a.delay090 / res.delay_total090 if res.delay_total090 > 0 and a.near[0] else None
        rows.append((run_id, kind, key, bit, "+".join(sorted(a.vias)), _round(a.crit_max),
                     len(a.paths), len(a.near[0]), len(a.near[1]), len(a.near[2]), _round(share)))
    db.executemany("INSERT INTO timing_object VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
    db.commit()
    return len(rows)


def records_of(store: Store, run_id: str, inp: TimingInput, res: Result) -> list[Record]:
    """The per-run scalars as records, identity columns from the run row."""
    row = store.db.execute(
        "SELECT source, design, arch, seed, arm, family, tool_commit, input_sha256 FROM run "
        "WHERE run_id = ?", (run_id,)).fetchone()
    if row is None:
        raise ValueError(f"no run {run_id}")
    s = res.stats
    vals: dict[str, float] = {"timing.paths_used": s.used, "timing.truncated_090": s.trunc[0]}
    for k, n, e in zip(THETA_KEYS, s.n_paths, s.n_endpoints, strict=True):
        vals[f"timing.nc_paths_{k}"] = n
        vals[f"timing.nc_endpoints_{k}"] = e
    if s.last_crit is not None:
        vals["timing.last_crit"] = round(s.last_crit, 6)
    return [Record(row[1], row[0], row[7], row[6], "", "routed", row[2], row[3], row[4], row[5],
                   k, "", float(v), _unit(k), SOURCE_MEASURER, "1", f"timing:{inp.sha256[:16]}")
            for k, v in sorted(vals.items())]


def _unit(key: str) -> str:
    from mimir.registry import unit_of

    return unit_of(key)


def import_run(store: Store, run_id: str, inp: TimingInput, scrub: Scrubber,
               analysis_n: int | None = None) -> tuple[Result, int]:
    """Analyse one run's input and write everything. Structures come from the store."""
    structs = store.db.execute(
        "SELECT structure_id, hdl_span FROM structure WHERE run_id = ? AND hdl_span <> ''",
        (run_id,)).fetchall()
    res = analyse(inp, [(a, b) for a, b in structs], scrub)
    n = write_result(store, run_id, inp, res, analysis_n)
    store.add(records_of(store, run_id, inp, res))
    return res, n


def sha_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_attribution_bytes(data: bytes) -> TimingInput:
    return parse_attribution(json.loads(data), sha_of(data))


def check_keys(store: Store, run_id: str) -> bool:
    """True when no stored object key holds a /home path (privacy gate)."""
    rows = store.db.execute("SELECT object_key FROM timing_object WHERE run_id = ?",
                            (run_id,)).fetchall()
    return all(check_clean(r[0]) for r in rows)


def import_from_blobs(store: Store, blobs_dir: Path, scrub: Scrubber,
                      only: set[str] | None = None) -> list[tuple[str, str]]:
    """Import every `timing` run artifact not yet imported. Returns (run_id, status) rows."""
    from mimir import blobs

    out = []
    arts = store.db.execute(
        "SELECT run_id, blob_sha256 FROM run_artifact WHERE kind='timing' ORDER BY run_id"
    ).fetchall()
    for run_id, sha in arts:
        if only is not None and run_id not in only:
            continue
        try:
            inp = load_attribution_bytes(blobs.get_bytes(blobs_dir, sha))
            res, _ = import_run(store, run_id, inp, scrub)
        except (ValueError, KeyError, OSError) as exc:
            out.append((run_id, f"error: {exc}"))
            continue
        out.append((run_id, "truncated" if res.stats.trunc[0] else "ok"))
    return out
