"""Import of the E10 placer-sweep metrics (nornsIII docs/plan/e10.md) into `records`, joined to the `run` rows.

The E10 layout has no runs.jsonl: each (config, design) has `<data>/placers/<label>-<config>_<design>.json` with a `runs` list. Every `run` row
whose source is `norns-placers-<label>-<config>` gets records with the same source, design, arch, seed, arm, family and input hash as the run row,
so `records` joins to `run` on those keys. The netlist LUT count (`struct.n_comb`, level lut: `.names` with at least one input) is read from the
netlist of the config when `netlists` is given. Read only on the Norns side.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

from mimir.importers.common import Ctx, Report
from mimir.schema import Record
from mimir.store import Store

MEASURER = "import-e10"
VERSION = "1"
SOURCE_PREFIX = "norns-placers-"
# JSON field -> (metric, level)
FIELDS: dict[str, tuple[str, str]] = {
    "wl": ("vpr.wirelength", "routed"),
    "W": ("vpr.chan_width", "routed"),
    "cpd_ns": ("vpr.cpd", "routed"),
    "route_s": ("vpr.route_time", "routed"),
    "flow_s": ("vpr.flow_time", "routed"),
    "rc": ("vpr.rc", "routed"),
    "clbs": ("vpr.blocks", "clb"),
    "pack_s": ("vpr.pack_time", "clb"),
    "sa_place_s": ("vpr.place_time", "placed"),
}
NETKEY = {"base": "base", "uon": "base", "uoff": "base", "plc": "base", "abc1": "abc1", "abc2": "abc2", "k4": "k4", "earch": "earch"}


def lut_count(blif: Path) -> int:
    """`.names` lines with at least one input (the LUT count of the E10 tables)."""
    n = 0
    with open(blif, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith(".names") and len(line.split()) >= 3:
                n += 1
    return n


def _num(v: object) -> float | None:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def import_e10(store: Store, data: Path, label: str, netlists: Path | None, report: Report) -> Iterator[Record]:
    """Records for every run row of source norns-placers-<label>-*; `data` is the run root's data dir (with placers/)."""
    rows = store.db.execute(
        "select source, design, arch, seed, arm, family, input_sha256, tool_commit from run where source like ?", (f"{SOURCE_PREFIX}{label}-%",)
    ).fetchall()
    cache: dict[Path, dict[tuple[str, int], dict[str, object]]] = {}
    luts: dict[tuple[str, str], int | None] = {}
    for source, design, arch, seed, arm, family, sha, commit in rows:
        cfg = source[len(f"{SOURCE_PREFIX}{label}-"):]
        report.seen[source] += 1
        path = data / "placers" / f"{label}-{cfg}_{design}.json"
        if path not in cache:
            cache[path] = {(r.get("arm", ""), r.get("seed", -1)): r for r in json.loads(path.read_text())["runs"]} if path.is_file() else {}
        res = cache[path].get((arm.split("-t")[0], seed))
        if res is None:
            report.skip(source, "run row without a result in data/placers")
            continue
        ctx = Ctx(design=design, source=source, origin=f"placers/{path.name}:{arm}.s{seed}", measurer=MEASURER, measurer_version=VERSION,
                  input_sha256=sha or "", tool_commit=commit or "", arch=arch, seed=seed, arm=arm, family=family or "")
        made = 0
        for key, (metric, level) in FIELDS.items():
            if (x := _num(res.get(key))) is not None:
                made += 1
                yield ctx.rec(metric, level, x)
        if netlists is not None and res.get("rc") == 0:
            k = (NETKEY.get(cfg, cfg), design)
            if k not in luts:
                b = netlists / k[0] / design / "netlist" / f"{design}.blif"
                luts[k] = lut_count(b) if b.is_file() else None
            if luts[k] is not None:
                made += 1
                yield ctx.rec("struct.n_comb", "lut", float(luts[k] or 0))
        report.used[source] += bool(made)
        report.records[source] += made
