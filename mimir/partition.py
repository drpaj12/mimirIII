"""The `partition` table: algorithmic partitioning (packing, bisection, re-clustering) with its
parameters, its cluster assignment as a blob, and its quality as records
(source `partition:<id>`). Spec: docs/specs/2026-10-27-mimir-schema-v2.md, sections 3.6, 8."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path

from mimir import blobs
from mimir.importers.common import Ctx, sha256_file
from mimir.importers.norns import ARCH
from mimir.schema import COLUMNS, Record, check_record
from mimir.store import Store

MEASURER = "partition-import"
IMPORT_MEASURER = "import-partition"
VERSION = "1"
RNG_SEED = 20261026  # scripts/r7lib.py RNG_SEED, the default seed of recluster()


@dataclass(frozen=True)
class PartitionSpec:
    """Everything one partition row needs; `assignment` maps object name to cluster id."""

    slug: str
    design: str
    algorithm: str
    algorithm_version: str
    params: Mapping[str, object]
    seed: int
    input_hash: str
    assignment: Mapping[str, int | str]
    origin: str
    level: str = "clb"
    arch: str = ""
    arm: str = ""
    version_kind: str = "recorded"  # or "importer-checkout": the version is the importer's checkout
    dirty: bool = False
    seed_conf: str = "confirmed-data"  # or "confirmed-script", "default-unconfirmed"


def assignment_text(assignment: Mapping[str, int | str]) -> bytes:
    """The blob content: `object<TAB>cluster` lines sorted by object name."""
    return "".join(f"{k}\t{assignment[k]}\n" for k in sorted(assignment)).encode("utf-8")


_ABS_AT = re.compile(r"@(/[^\t:@]*)")


def normalise_name(name: str) -> str:
    """An object name without machine-specific path prefixes: `x@/home/u/vtr/vtr_flow/a/b.v:3`
    becomes `x@vtr_flow/a/b.v:3`; an absolute path with no vtr_flow component keeps its file
    name. A name that still holds a home path afterwards is refused."""
    def short(m: re.Match[str]) -> str:
        path = m.group(1)
        i = path.find("/vtr_flow/")
        return "@" + (path[i + 1:] if i >= 0 else path.rsplit("/", 1)[-1])

    out = _ABS_AT.sub(short, name)
    if "/home/" in out:
        raise ValueError(f"object name keeps a home path after normalising: {name!r}")
    return out


def normalise_assignment(assignment: Mapping[str, int | str]) -> dict[str, int | str]:
    out: dict[str, int | str] = {}
    for name, cluster in assignment.items():
        key = normalise_name(name)
        if key in out and out[key] != cluster:
            raise ValueError(f"two objects normalise to {key!r} with different clusters")
        out[key] = cluster
    return out


def partition_id(spec: PartitionSpec, blob: str) -> str:
    """Identity: algorithm, its version, parameters, seed, design slug, input and result."""
    key = json.dumps([spec.algorithm, spec.algorithm_version, dict(spec.params), spec.seed,
                      spec.slug, spec.input_hash, blob], sort_keys=True)
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def size_metrics(assignment: Mapping[str, int | str]) -> list[tuple[str, float]]:
    sizes = Counter(assignment.values())
    n, k = len(assignment), len(sizes)
    out = [("partition.n_objects", float(n)), ("partition.n_clusters", float(k))]
    if k:
        out += [("partition.cluster_size_max", float(max(sizes.values()))),
                ("partition.cluster_size_mean", n / k)]
    return out


def add_partition(store: Store, blob_root: Path, spec: PartitionSpec,
                  extra: list[tuple[str, float, str]]) -> str:
    """Store one partition and its metric records in one transaction; return its id. `extra` is a
    list of (metric, value, bin) for imported quality or downstream values. Idempotent. The
    assignment is normalised first, so the blob and the ids do not depend on the machine."""
    assignment = normalise_assignment(spec.assignment)
    spec = replace(spec, assignment=assignment)
    blob = blobs.put_bytes(blob_root, assignment_text(assignment))
    pid = partition_id(spec, blob)
    source = f"partition:{pid}"
    recs = _records(spec, source, extra)
    for rec in recs:
        check_record(rec)
    marks = ", ".join("?" for _ in COLUMNS)
    try:
        store.db.execute(
            "INSERT OR REPLACE INTO partition VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (pid, spec.algorithm, spec.algorithm_version,
             json.dumps(dict(spec.params), sort_keys=True), spec.seed, spec.slug, spec.input_hash,
             len(assignment), len(set(assignment.values())), blob, spec.origin,
             spec.version_kind, int(spec.dirty), spec.seed_conf))
        store.db.execute("DELETE FROM records WHERE source = ?", (source,))
        store.db.executemany(f"INSERT OR REPLACE INTO records VALUES ({marks})",
                             [r.as_tuple() for r in recs])
        store.db.commit()
    except BaseException:
        store.db.rollback()
        raise
    return pid


def _records(spec: PartitionSpec, source: str, extra: list[tuple[str, float, str]]
             ) -> list[Record]:
    def ctx_of(measurer: str) -> Ctx:
        return Ctx(design=spec.design, source=source, origin=spec.origin, measurer=measurer,
                   measurer_version=VERSION, input_sha256=spec.input_hash, arch=spec.arch,
                   arm=spec.arm)

    ctx, imp = ctx_of(MEASURER), ctx_of(IMPORT_MEASURER)
    recs: list[Record] = [ctx.rec(m, spec.level, v) for m, v in size_metrics(spec.assignment)]
    for metric, value, bin_ in extra:
        level = "routed" if metric == "partition.downstream_median_objective" else spec.level
        recs.append(imp.rec(metric, level, value, bin_))
    return recs


def _read_assignment(path: Path) -> dict[str, int]:
    out: dict[str, int] = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            name, _, cluster = line.rstrip("\n").rpartition("\t")
            if name:
                out[name] = int(cluster)
    return out


def _git(path: Path, *args: str) -> str | None:
    try:
        res = subprocess.run(["git", "-C", str(path), *args], capture_output=True, text=True,
                             check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return res.stdout.strip()


def _git_head(path: Path) -> str:
    return _git(path, "rev-parse", "--short=10", "HEAD") or ""


def _dirty(path: Path) -> bool:
    """True when the scripts the clustering ran from (r7.py, r7lib.py) differ from the commit, or
    git is unavailable."""
    out = _git(path, "status", "--porcelain", "--", "scripts/r7.py", "scripts/r7lib.py")
    return out is None or out != ""


def _seed_conf(norns_root: Path) -> str:
    """`confirmed-script` when scripts/r7.py calls recluster() with no seed argument and
    scripts/r7lib.py sets RNG_SEED to the value used here; else `default-unconfirmed`."""
    try:
        lib = (norns_root / "scripts/r7lib.py").read_text(encoding="utf-8")
        r7 = (norns_root / "scripts/r7.py").read_text(encoding="utf-8")
    except OSError:
        return "default-unconfirmed"
    call = re.search(r"lib\.recluster\(view, flat, source_pcrit\([^()]*\)\)", r7)
    default = re.search(rf"^RNG_SEED = {RNG_SEED}\b", lib, re.MULTILINE)
    return "confirmed-script" if call and default else "default-unconfirmed"


def import_norns_hindsight(store: Store, blob_root: Path, norns_root: Path, design: str,
                           arm: str = "h1") -> str:
    """The worked example: the round 7 hindsight clustering `<arm>` of one design.

    Source files under runs/r7/<design>/ (read only): `<arm>.affinity.tsv` (atom, cluster),
    `<arm>.recluster.json` (statistics) and `rounds.json` (medians). The input is the `.net` of the
    stock run the clustering was derived from."""
    base = norns_root / "runs/r7" / design
    stats = json.loads((base / f"{arm}.recluster.json").read_text(encoding="utf-8"))
    rounds = json.loads((base / "rounds.json").read_text(encoding="utf-8"))
    net = base / f"{stats['source_arm']}.s{stats['source_seed']}" / f"{design}.net.gz"
    row = store.db.execute("SELECT slug FROM design_source WHERE source = 'norns-r7' AND name = ?",
                           (design,)).fetchone()
    recorded = str(stats.get("commit", ""))
    head = _git_head(norns_root)
    spec = PartitionSpec(
        slug=str(row[0]) if row else f"norns/{design}", design=design, algorithm="norns-recluster",
        algorithm_version=recorded or f"norns-exp scripts at {head or 'unknown'}",
        version_kind="recorded" if recorded else "importer-checkout",
        dirty=False if recorded else _dirty(norns_root),
        params={"source_arm": stats["source_arm"], "source_seed": stats["source_seed"],
                "rng_seed": RNG_SEED, "round": arm},
        seed=RNG_SEED, seed_conf=_seed_conf(norns_root),
        input_hash=sha256_file(net) if net.is_file() else f"missing:{net.name}",
        assignment=_read_assignment(base / f"{arm}.affinity.tsv"),
        origin=f"runs/r7/{design}/{arm}.affinity.tsv", arch=ARCH, arm=arm)
    extra: list[tuple[str, float, str]] = []
    for key in ("cost_before", "cost_after", "atoms_moved"):
        extra.append((f"partition.{key}", float(stats[key]), ""))
    for name, value in sorted(rounds["medians"].items()):
        extra.append(("partition.downstream_median_objective", float(value), name))
    return add_partition(store, blob_root, spec, extra)

