"""`mimir bench publish-plan`: stage the public benchmark blobs for the static web host.

Same layout as `mimir remote publish-plan`: `blobs/<ab>/<sha256>.xz` (name = sha256 of the
decompressed bytes). The registry index goes to `index/bench/` so it never replaces the
`index/blobs.tsv.xz` of the archive data. Only blobs of a `hosting = "public"` suite whose row is
`public` are staged; a `local-only` or `unchecked` suite stays out. Nothing is uploaded or
deleted."""

from __future__ import annotations

import hashlib
import lzma
from dataclasses import dataclass, field
from pathlib import Path

from mimir import bench, blobs, remote
from mimir.meta import Rule, load_licence_rules
from mimir.publish import _put, process_bytes

INDEX_FILES = ("suites.toml", "flows.toml", "designs.tsv", "netlists.tsv", "blobs.tsv.xz")
SUMS = "index/bench/SHA256SUMS"


class BenchPubError(Exception):
    """A blob that does not match its index row, or an unreadable registry."""


@dataclass
class Staged:
    count: int = 0
    xz_bytes: int = 0
    by_suite: dict[str, int] = field(default_factory=dict)
    withheld: list[str] = field(default_factory=list)  # blobs left out (home path or identity)


def verdicts(suites: dict[str, bench.Suite]) -> dict[str, str]:
    """hostable | local-only | unchecked, from the suite's `hosting` field."""
    return {i: ("hostable" if s.hosting == "public" else s.hosting) for i, s in suites.items()}


def blob_suites(netlists: list[bench.Netlist]) -> dict[str, set[str]]:
    """Which suites name each blob."""
    out: dict[str, set[str]] = {}
    for n in netlists:
        for sha in n.shas():
            out.setdefault(sha, set()).add(n.suite)
    return out


def hostable_shas(idx: Path) -> dict[str, set[str]]:
    """sha -> suites, for the blobs that may be staged. A blob shared with a suite that is not
    hostable is left out (it is never staged for a licence that was not read)."""
    suites = bench.load_suites(idx)
    rows = remote.load_blob_index(idx)
    out: dict[str, set[str]] = {}
    for sha, names in blob_suites(bench.load_netlists(idx)).items():
        row = rows.get(sha)
        ok = all(suites[s].hosting == "public" for s in names if s in suites)
        if row is not None and row.visibility == "public" and ok:
            out[sha] = names
    return out


def check_blob(path: Path, row: remote.BlobRef) -> bytes:
    """The stored xz bytes, after checking size, decompressed size and sha256 against the row."""
    data = path.read_bytes()
    if len(data) != row.xz_bytes:
        raise BenchPubError(f"blob {row.sha}: {len(data)} xz bytes, index says {row.xz_bytes}")
    try:
        raw = lzma.decompress(data)
    except (lzma.LZMAError, EOFError) as exc:
        raise BenchPubError(f"blob {row.sha}: not valid xz ({exc})") from exc
    if len(raw) != row.raw_bytes or hashlib.sha256(raw).hexdigest() != row.sha:
        raise BenchPubError(f"blob {row.sha}: content does not match the index row")
    return data


def stage_blobs(idx: Path, store: Path, stage: Path) -> Staged:
    rows = remote.load_blob_index(idx)
    res = Staged()
    for sha, names in sorted(hostable_shas(idx).items()):
        path = blobs.blob_path(store, sha)
        if not path.is_file():
            raise BenchPubError(f"blob {sha}: not in the local store {store}")
        data = check_blob(path, rows[sha])
        new, _ = process_bytes(path.name, data, scrub=False)
        if new is None:
            res.withheld.append(sha)
            continue
        _put(stage / "blobs" / sha[:2] / f"{sha}.xz", data)
        res.count += 1
        res.xz_bytes += len(data)
        for s in names:
            res.by_suite[s] = res.by_suite.get(s, 0) + 1
    return res


def notice_text(idx: Path, rules: list[Rule], date: str) -> str:
    suites = bench.load_suites(idx)
    ver = verdicts(suites)
    lines = [f"Mimir III benchmark blobs, staged {date}. Each design keeps the licence it states;",
             "nothing is relicensed. This is not legal advice.", "", "Suites and verdicts:"]
    for s in suites.values():
        lines += [f"  {s.id}: {ver[s.id]}", f"    licence: {s.licence}",
                  f"    source: {s.licence_source} ({s.upstream} at {s.commit})"]
    used = sorted({d.licence_rule for d in bench.load_designs(idx) if d.licence_rule != "-"})
    by_id = {str(r.get("id")): r for r in rules}
    lines += ["", "Per-design licence rules in use:"]
    for rid in used:
        r = by_id.get(rid)
        if r is None:
            continue
        lines += [f"  {rid}: {r['licence']}", f"    source: {r['licence_source']}",
                  f"    notice: {r['licence_notice']}"]
    return "\n".join(lines) + "\n"


def write_sums(stage: Path) -> int:
    """SHA256SUMS of every staged file, relative to the stage root (the sums file excluded)."""
    lines = []
    for p in sorted(stage.rglob("*")):
        if p.is_file() and p.relative_to(stage).as_posix() != SUMS:
            digest = hashlib.sha256(p.read_bytes()).hexdigest()
            lines.append(f"{digest}  {p.relative_to(stage).as_posix()}")
    _put(stage / SUMS, ("\n".join(lines) + "\n").encode())
    return len(lines)


def run_stage(idx: Path, store: Path, stage: Path, meta_licences: Path, date: str) -> list[str]:
    res = stage_blobs(idx, store, stage)
    for name in INDEX_FILES:
        _put(stage / "index" / "bench" / name, (idx / name).read_bytes())
    _put(stage / "index" / "bench" / "NOTICE.txt",
         notice_text(idx, load_licence_rules(meta_licences), date).encode())
    n_sums = write_sums(stage)
    suites = bench.load_suites(idx)
    ver = verdicts(suites)
    report = [f"blobs staged: {res.count}; xz bytes: {res.xz_bytes}; "
              f"withheld (home path): {len(res.withheld)}; SHA256SUMS lines: {n_sums}"]
    report += [f"suite\t{i}\t{ver[i]}\tblobs {res.by_suite.get(i, 0)}" for i in suites]
    return report
