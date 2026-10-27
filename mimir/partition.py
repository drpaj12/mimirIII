"""The `partition` table: algorithmic partitioning (packing, bisection, re-clustering) with its
parameters, its cluster assignment as a blob, and its quality as records
(source `partition:<id>`). Spec: docs/specs/2026-10-27-mimir-schema-v2.md, sections 3.6, 8."""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from mimir import blobs
from mimir.importers.common import Ctx, sha256_file
from mimir.importers.norns import ARCH
from mimir.schema import Record
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


def assignment_text(assignment: Mapping[str, int | str]) -> bytes:
    """The blob content: `object<TAB>cluster` lines sorted by object name."""
    return "".join(f"{k}\t{assignment[k]}\n" for k in sorted(assignment)).encode("utf-8")


def partition_id(spec: PartitionSpec, blob: str) -> str:
    key = json.dumps([spec.algorithm, dict(spec.params), spec.seed, spec.input_hash, blob],
                     sort_keys=True)
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
    """Store one partition and its metric records; return its id. `extra` is a list of
    (metric, value, bin) for imported quality or downstream values. Idempotent."""
    blob = blobs.put_bytes(blob_root, assignment_text(spec.assignment))
    pid = partition_id(spec, blob)
    source = f"partition:{pid}"
    store.db.execute(
        "INSERT OR REPLACE INTO partition VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (pid, spec.algorithm, spec.algorithm_version, json.dumps(dict(spec.params), sort_keys=True),
         spec.seed, spec.slug, spec.input_hash, len(spec.assignment),
         len(set(spec.assignment.values())), blob, spec.origin))
    store.db.commit()
    store.db.execute("DELETE FROM records WHERE source = ?", (source,))
    ctx = Ctx(design=spec.design, source=source, origin=spec.origin, measurer=MEASURER,
              measurer_version=VERSION, input_sha256=spec.input_hash, arch=spec.arch,
              arm=spec.arm)
    recs: list[Record] = [ctx.rec(m, spec.level, v) for m, v in size_metrics(spec.assignment)]
    imp = Ctx(design=spec.design, source=source, origin=spec.origin, measurer=IMPORT_MEASURER,
              measurer_version=VERSION, input_sha256=spec.input_hash, arch=spec.arch,
              arm=spec.arm)
    for metric, value, bin_ in extra:
        level = "routed" if metric == "partition.downstream_median_objective" else spec.level
        recs.append(imp.rec(metric, level, value, bin_))
    store.add(recs)
    return pid


def _read_assignment(path: Path) -> dict[str, int]:
    out: dict[str, int] = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            name, _, cluster = line.rstrip("\n").rpartition("\t")
            if name:
                out[name] = int(cluster)
    return out


def _git_head(path: Path) -> str:
    try:
        res = subprocess.run(["git", "-C", str(path), "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return ""
    return res.stdout.strip()


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
    spec = PartitionSpec(
        slug=str(row[0]) if row else f"norns/{design}", design=design, algorithm="norns-recluster",
        algorithm_version=f"norns {_git_head(norns_root)}".strip(),
        params={"source_arm": stats["source_arm"], "source_seed": stats["source_seed"],
                "rng_seed": RNG_SEED, "round": arm},
        seed=RNG_SEED, input_hash=sha256_file(net) if net.is_file() else "",
        assignment=_read_assignment(base / f"{arm}.affinity.tsv"),
        origin=f"runs/r7/{design}/{arm}.affinity.tsv", arch=ARCH, arm=arm)
    extra: list[tuple[str, float, str]] = []
    for key in ("cost_before", "cost_after", "atoms_moved"):
        extra.append((f"partition.{key}", float(stats[key]), ""))
    for name, value in sorted(rounds["medians"].items()):
        extra.append(("partition.downstream_median_objective", float(value), name))
    return add_partition(store, blob_root, spec, extra)

