"""Import of the Wyrd atlas exports (`data/r7/atlas/*.json.gz` in the Norns checkout)."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

from mimir.importers.common import Ctx, Report, sha256_file
from mimir.importers.norns import ARCH, VTR_COMMIT
from mimir.schema import Record

MEASURER = "import-atlas"
VERSION = "1"
SOURCE = "wyrd-atlas-r7"
SCALARS = {
    "cpd_ns": ("vpr.cpd", "routed"),
    "wirelength": ("vpr.wirelength", "routed"),
    "chan_width": ("vpr.chan_width", "routed"),
}
COUNTS = {"clbs": ("atlas.n_clbs", "placed"), "atoms": ("atlas.n_atoms", "placed")}


def import_atlas(root: Path) -> tuple[list[Record], Report]:
    """Records for each atlas export: the three VPR outcomes and the CLB and atom counts."""
    report = Report()
    out: list[Record] = []
    for path in sorted((root / "data/r7/atlas").glob("*.json.gz")):
        report.seen[SOURCE] += 1
        d = json.loads(gzip.decompress(path.read_bytes()))
        rel = path.relative_to(root).as_posix()
        ctx = Ctx(
            design=d["design"], source=SOURCE, origin=rel, measurer=MEASURER,
            measurer_version=VERSION, input_sha256=sha256_file(path), tool_commit=VTR_COMMIT,
            arch=ARCH, seed=int(d["seed"]), arm=str(d["arm"]), family="analytic",
        )
        made = 0
        for key, (metric, level) in SCALARS.items():
            if isinstance(d.get(key), (int, float)):
                out.append(ctx.rec(metric, level, d[key]))
                made += 1
        for key, (metric, level) in COUNTS.items():
            if isinstance(d.get(key), list):
                out.append(ctx.rec(metric, level, len(d[key])))
                made += 1
        report.used[SOURCE] += bool(made)
        report.records[SOURCE] += made
        report.skip(SOURCE, "per-CLB and per-atom detail (grid, ids, criticality) not imported", 1)
    return out, report
