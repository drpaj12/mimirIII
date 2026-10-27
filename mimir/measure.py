"""Run the measurers on a BLIF file and turn the results into records."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field, replace

from mimir import hutton
from mimir.blif import BlifError, read_blif
from mimir.importers.common import Ctx, sha256_file
from mimir.schema import Record
from mimir.sets import Job

RENT_MAX_NODES = 100000


@dataclass
class Outcome:
    records: list[Record] = field(default_factory=list)
    error: str = ""  # why the whole design was skipped
    rent_note: str = ""  # why Rent was not (fully) measured, empty if it was


def measure_job(
    job: Job, *, seeds: Sequence[int] = (1, 2, 3), rent: bool = True,
    rent_max_nodes: int = RENT_MAX_NODES,
) -> Outcome:
    """Hutton-style rows always; Rent rows when the extra is installed and the size allows."""
    out = Outcome()
    try:
        nl = read_blif(job.path)
        rows = hutton.characterise(nl)
    except (BlifError, ValueError) as exc:
        out.error = f"{type(exc).__name__}: {exc}"
        return out
    ctx = Ctx(design=job.design, source=job.source, origin=job.origin, measurer="struct",
              measurer_version=hutton.VERSION, input_sha256=sha256_file(job.path),
              tool_commit=job.tool_commit, arch=job.arch)
    out.records += [ctx.rec(m, job.level, v, b) for m, b, v in rows]
    if not rent:
        return out
    if len(nl) > rent_max_nodes:
        out.rent_note = f"size cap: more than {rent_max_nodes} nodes"
        return out
    from mimir import rent as rent_mod

    rctx = replace(ctx, measurer="rent", measurer_version=rent_mod.partitioner_version())
    rent_rows, skipped = rent_mod.measure(nl, seeds)
    for metric, bin_, seed, value in rent_rows:
        out.records.append(replace(rctx, seed=seed).rec(metric, job.level, value, bin_))
    if skipped:
        out.rent_note = f"fit skipped: {skipped} of {len(seeds)} seeds had too few nodes or points"
    return out
