"""The netlist sets Mimir measures: MCNC from VTR, the Norns netlists, the Loki corpora."""

from __future__ import annotations

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


def norns_jobs(norns_root: Path) -> list[Job]:
    """The Odin III netlists of the Norns designs (LUTs plus hard blocks)."""
    jobs = []
    for path in sorted(norns_root.glob("runs/*/netlist/*.blif")):
        rel = path.relative_to(norns_root).as_posix()
        jobs.append(Job(path, path.stem, "norns-netlist", "lut", rel, arch=NORNS_ARCH))
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
    "norns": (norns_jobs, "MIMIR_NORNS"),
    "loki": (loki_jobs, "MIMIR_LOKI"),
}
