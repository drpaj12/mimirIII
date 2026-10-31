"""The netlist sets Mimir measures: MCNC from VTR, the Norns netlists, the Loki corpora."""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from mimir.importers.loki import FLOOR_LEVEL, find_datasets

VTR_COMMIT = "3c9a4d23b2"
NORNS_ARCH = "k6_frac_N10_frac_chain_mem32K_40nm"


@dataclass(frozen=True)
class Job:
    path: Path
    design: str
    source: str
    level: str
    origin: str
    arch: str = ""
    tool_commit: str = ""


def _smallest_first(jobs: list[Job]) -> list[Job]:
    return sorted(jobs, key=lambda j: (j.path.stat().st_size, j.origin))


def mcnc_jobs(vtr_root: Path) -> list[Job]:
    """The 20 MCNC circuits named in circuits.txt (4-LUT netlists with flip flops)."""
    base = vtr_root / "vtr_flow/benchmarks/blif"
    names = [n.strip() for n in (base / "circuits.txt").read_text().splitlines() if n.strip()]
    return _smallest_first([
        Job(base / n, Path(n).stem, "mcnc", "lut", f"vtr:vtr_flow/benchmarks/blif/{n}",
            tool_commit=VTR_COMMIT)
        for n in names if (base / n).is_file()
    ])


def _lutk_jobs(vtr_root: Path, k: int) -> list[Job]:
    """Every MCNC circuit of VTR's blif/<k>/ directory (the whole set mapped to k-input LUTs)."""
    base = vtr_root / f"vtr_flow/benchmarks/blif/{k}"
    return _smallest_first([
        Job(path, path.stem, f"mcnc-k{k}", "lut", f"vtr:vtr_flow/benchmarks/blif/{k}/{path.name}",
            tool_commit=VTR_COMMIT)
        for path in sorted(base.glob("*.blif"))
    ])


def mcnc_k2_jobs(vtr_root: Path) -> list[Job]:
    return _lutk_jobs(vtr_root, 2)


def mcnc_k4_jobs(vtr_root: Path) -> list[Job]:
    return _lutk_jobs(vtr_root, 4)


def norns_jobs(norns_root: Path) -> list[Job]:
    """The Odin III netlists of the Norns designs (LUTs plus hard blocks)."""
    jobs = []
    for path in sorted(norns_root.glob("runs/*/netlist/*.blif")):
        rel = path.relative_to(norns_root).as_posix()
        jobs.append(Job(path, path.stem, "norns-netlist", "lut", rel, arch=NORNS_ARCH))
    return _smallest_first(jobs)


NORNS_SUITES = ("vtr-verilog", "mcnc20")
NORNS_FLOW_PREFIX = "odin3-1.2.0-k6-"


def norns_registry_jobs(blob_root: Path) -> list[Job]:
    """The Odin III netlists of the 35 Norns base designs (15 VTR Verilog, 20 MCNC), read from
    the benchmark registry (`data/benchmarks`): each blob is fetched (local store `blob_root`
    first) into the cache, hash checked, and measured from there."""
    from mimir import bench, remote

    idx = bench.index_dir()
    loc = dataclasses.replace(remote.Locations.from_env(), blobs=blob_root)
    cache = loc.cache / "bench"
    jobs = []
    for n in bench.load_netlists(idx):
        if n.suite in NORNS_SUITES and n.flow.startswith(NORNS_FLOW_PREFIX):
            ref = f"{n.suite}:{n.design}@{n.flow}"
            path = bench.materialise(ref, cache / f"{n.sha256}.blif", idx=idx, loc=loc)
            jobs.append(Job(path, n.design, "norns-netlist", "lut", f"bench:{ref}",
                            arch=NORNS_ARCH))
    return _smallest_first(jobs)


def loki_jobs(loki_root: Path) -> list[Job]:
    """The per-floor netlists of every Loki floor-layout dataset."""
    jobs = []
    for sub in sorted(loki_root.glob("loki-*")):
        for ds in find_datasets(sub) if sub.is_dir() else []:
            source = "loki:" + ds.relative_to(loki_root).as_posix()
            for path in sorted(ds.glob("*/*/netlist.blif")):
                level = FLOOR_LEVEL.get(path.parent.name)
                if level:
                    rel = path.relative_to(loki_root).as_posix()
                    jobs.append(Job(path, path.parent.parent.name, source, level, rel,
                                    arch=path.parent.name))
    return _smallest_first(jobs)


# set name -> (job builder, env var holding the root)
SETS: dict[str, tuple[Callable[[Path], list[Job]], str]] = {
    "mcnc": (mcnc_jobs, "VTR_ROOT"),
    "mcnc-k2": (mcnc_k2_jobs, "VTR_ROOT"),
    "mcnc-k4": (mcnc_k4_jobs, "VTR_ROOT"),
    "norns": (norns_registry_jobs, "MIMIR_BLOBS"),
    "norns-runs": (norns_jobs, "MIMIR_NORNS"),
    "loki": (loki_jobs, "MIMIR_LOKI"),
}
