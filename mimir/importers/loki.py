"""Import of Loki III datasets: manifests and per-floor `meta.json` counts (read only)."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from mimir.importers.common import Ctx, Report, sha256_file
from mimir.schema import Record

MEASURER = "import-loki"
VERSION = "1"
FLOOR_LEVEL = {"f1-k6": "lut", "f1-earch": "lut", "f2": "lut", "f3": "gate"}
COUNTS = {
    "nodes": "loki.nodes", "edges": "loki.edges", "lut": "loki.luts", "gate": "loki.gates",
    "ff": "loki.ffs", "hard": "loki.hard", "const": "loki.consts", "pi": "loki.pis",
    "po": "loki.pos",
}
TOP = {"loops_cut": "loki.loops_cut", "unmatched": "loki.unmatched"}
SKIP_DIRS = {".venv", "node_modules", "__pycache__", ".git"}
SPLIT_VALUE = {"train": 1.0, "test": 0.0}  # loki.in_train; any other split value is skipped


def find_datasets(root: Path) -> list[Path]:
    """Dataset directories under `root`: a directory whose design folders hold floor meta.json."""
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        if "design.json" in filenames:
            parent = Path(dirpath).parent
            if parent not in found and any(Path(dirpath).glob("*/meta.json")):
                found.append(parent)
            dirnames[:] = []
    return sorted(found)


def _manifest(ds: Path) -> dict[str, dict[str, object]]:
    path = ds / "manifest.json"
    if not path.is_file():
        return {}
    designs = json.loads(path.read_text(encoding="utf-8")).get("designs", [])
    return {d["design"]: d for d in designs}


def _script_hash(meta: dict[str, object]) -> str:
    script = meta.get("script")
    text = "\n".join(script) if isinstance(script, list) else ""
    return hashlib.sha256(text.encode()).hexdigest()[:16] if text else ""


def _commit(meta: dict[str, object]) -> str:
    """The tool commit when meta.json records one; empty otherwise. The meta files carry only
    version strings (odin3_version, loki_version), which are not commits and are not stored."""
    value = meta.get("tool_commit") or meta.get("odin3_commit")
    return value if isinstance(value, str) else ""


def _number(v: object) -> float | None:
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    return None


def import_dataset(root: Path, ds: Path, report: Report) -> list[Record]:
    """Records for one dataset; the source label is the dataset path relative to `root`."""
    source = "loki:" + ds.relative_to(root).as_posix()
    manifest = _manifest(ds)
    out: list[Record] = []
    for design_json in sorted(ds.glob("*/design.json")):
        design = design_json.parent.name
        info = manifest.get(design, {})
        for meta_path in sorted(design_json.parent.glob("*/meta.json")):
            out.extend(_floor(root, source, design, meta_path, info, report))
    return out


def _floor(
    root: Path, source: str, design: str, meta_path: Path, info: dict[str, object], report: Report
) -> list[Record]:
    report.seen[source] += 1
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    floor = str(meta.get("floor", meta_path.parent.name))
    level = FLOOR_LEVEL.get(floor)
    if level is None:
        report.skip(source, f"unknown floor {floor!r}")
        return []
    blif = meta_path.parent / "netlist.blif"
    ctx = Ctx(
        design=design, source=source, origin=meta_path.relative_to(root).as_posix(),
        measurer=MEASURER, measurer_version=VERSION,
        input_sha256=sha256_file(blif) if blif.is_file() else "",
        tool_commit=_commit(meta), arch=floor,
        script_hash=_script_hash(meta),
    )
    vals = [(COUNTS[k], x) for k, v in sorted(meta.get("counts", {}).items())
            if k in COUNTS and (x := _number(v)) is not None]
    vals += [(m, x) for k, m in TOP.items() if (x := _number(meta.get(k))) is not None]
    if info:
        _split(vals, info, source, report)
    recs = [ctx.rec(m, level, x) for m, x in vals]
    report.used[source] += bool(recs)
    report.records[source] += len(recs)
    return recs


def _split(
    vals: list[tuple[str, float]], info: dict[str, object], source: str, report: Report
) -> None:
    """Add loki.in_train for a known split value; count an absent or unknown split as skipped."""
    split = info.get("split")
    if isinstance(split, str) and split in SPLIT_VALUE:
        vals.append(("loki.in_train", SPLIT_VALUE[split]))
    elif split is None:
        report.skip(source, "manifest entry without a split")
    else:
        report.skip(source, f"unknown split value {split!r}: loki.in_train not set")


def import_loki(root: Path) -> tuple[list[Record], Report]:
    """Import every floor-layout dataset below `root` (the directory holding the loki-* dirs)."""
    report = Report()
    out: list[Record] = []
    for sub in sorted(root.glob("loki-*")):
        if not sub.is_dir():
            continue
        datasets = find_datasets(sub)
        for ds in datasets:
            out.extend(import_dataset(root, ds, report))
        if not datasets:
            n = sum(1 for _ in sub.iterdir())
            report.skip(
                "loki-round-results",
                f"{sub.name}: {n} free-form result entries (logs, calibration, probes); "
                "no per-design floor layout",
            )
            report.seen["loki-round-results"] += 0
    return out, report
