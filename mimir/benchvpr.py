"""VPR measures of the catalogue: `odin3-flow` (Odin III, then VPR at the minimum channel width)
over registered Verilog designs that have no VPR record in the Mimir store. Returns rows
`[suite, design, key, value, source]` like `mimir.benchmeasure`."""

from __future__ import annotations

import contextlib
import json
import os
import re
import subprocess
from collections.abc import Callable
from pathlib import Path

from mimir import bench, benchcat, benchmeasure

Row = list[str]
KEYS = ["vtr_stage", "vtr_luts", "vtr_blocks", "vtr_ffs", "vtr_pins", "vtr_mult", "vtr_mem",
        "vtr_cpd", "vtr_cw"]
BLOCKS_RE = re.compile(r"^Netlist num_blocks:\s*(\d+)", re.M)
FLOW_REL = Path("tools") / "flow" / "odin3-flow"
OOM_CODES = {-9, 137}


def _row(d: bench.Design, key: str, val: str, src: str) -> Row:
    return [d.suite, d.design, key, val, src]


def _failed(d: bench.Design, stage: str, reason: str, src: str) -> list[Row]:
    rows = [_row(d, "vtr_stage", f"{stage}: {reason}", src)]
    rows += [_row(d, k, f"fail: {reason}", src) for k in KEYS[1:]]
    return rows


def _last_log_line(log: Path) -> str:
    try:
        lines = [ln.strip() for ln in log.read_text(errors="replace").splitlines() if ln.strip()]
    except OSError:
        return ""
    errs = [ln for ln in lines if "error" in ln.lower()]
    return re.sub(r"(?:/[^\s:'\"]+)+/([^/\s:'\"]+)", r"\1", (errs or lines or [""])[-1])[:100]


def classify_failure(out: Path, rc: int) -> tuple[str, str]:
    """(stage, reason) of a failed flow run: the step that stopped it and why. A timeout or a
    kill (the memory cap) is `too big for now`; the stage is where the flow stopped."""
    seconds: dict[str, float] = {}
    with contextlib.suppress(OSError, ValueError):
        seconds = json.loads((out / "summary.json").read_text()).get("seconds", {})
    stage = list(seconds)[-1] if seconds else "odin3"
    logs = sorted(out.rglob(f"{stage}.log"))
    text = logs[0].read_text(errors="replace") if logs else ""
    last = [ln for ln in text.splitlines() if ln.strip()]
    tail = last[-1] if last else ""
    if tail.startswith("timeout after"):
        return stage, f"too big for now ({tail}, stopped in {stage})"
    if rc in OOM_CODES or "Killed" in text[-400:] or "std::bad_alloc" in text[-2000:]:
        return stage, f"too big for now (memory cap, stopped in {stage})"
    return stage, (_last_log_line(logs[0]) if logs else "") or f"exit {rc}"


def success_rows(d: bench.Design, out: Path, src: str) -> list[Row]:
    """The VTR columns of one routed run (`summary.json`, `vpr.out`, the mapped BLIF)."""
    summary = json.loads((out / "summary.json").read_text())
    vpr_out = next((out / "vpr").rglob("vpr.out")).read_text(errors="replace")
    blocks = BLOCKS_RE.search(vpr_out)
    blif = next((out / "odin3").glob("*.blif"))
    c = benchmeasure.blif_counts(blif.read_text(errors="replace"))
    if summary.get("crit_path_ns") is None or summary.get("min_chan_width") is None:
        return _failed(d, "route", "no timing or channel width in the VTR parse", src)
    got = {"vtr_stage": benchcat.STAGE_DONE, "vtr_luts": str(summary["luts"]),
           "vtr_blocks": blocks.group(1) if blocks else "fail: no block count in vpr.out",
           "vtr_ffs": str(c["ffs"]), "vtr_pins": str(c["pins"]), "vtr_mult": str(c["mult"]),
           "vtr_mem": str(c["mem"]),
           "vtr_cpd": f"{float(summary['crit_path_ns']):g}",
           "vtr_cw": str(summary["min_chan_width"])}
    return [_row(d, k, got[k], src) for k in KEYS]


def measure_design(odin3: Path, vtr: Path, suite: bench.Suite, d: bench.Design,
                   out_root: Path, runner: Callable[..., int] | None = None) -> list[Row]:
    out = out_root / d.design
    src = (f"odin3-flow {odin3.parent.name} vpr min channel width seed 1 "
           f"{benchmeasure.VTR_ARCH}")
    tool = odin3.parent
    for _ in range(4):  # the flow script lives in the Odin III checkout above the build dir
        if (tool / FLOW_REL).is_file():
            break
        tool = tool.parent
    argv = [str(tool / FLOW_REL), "--odin3", str(odin3), "--out", str(out)]
    if d.top not in ("", "-"):
        argv += ["--top", d.top]
    argv.append(str(bench.source_path(suite, d)))
    env = {**os.environ, "VTR_ROOT": str(vtr)}
    run = runner or (lambda a, e: subprocess.run(a, env=e, capture_output=True, check=False)
                     .returncode)
    rc = run(argv, env)
    if rc == 0:
        try:
            return success_rows(d, out, src)
        except (OSError, ValueError, StopIteration, KeyError) as exc:
            return _failed(d, "route", f"no VPR result ({type(exc).__name__})", src)
    stage, reason = classify_failure(out, rc)
    return _failed(d, stage, reason, src)


def collect_vpr(idx: Path, odin3: Path, vtr: Path, suite_id: str, out_root: Path,
                limit: int | None, sink: Callable[[list[Row]], None],
                retry_failed: bool = False) -> int:
    """Run VPR for the designs of `suite_id` that have no `vtr_luts` row yet (a store record
    counts), smallest source first; `sink` gets the rows of each design. Returns the number run."""
    rows = bench.read_tsv(benchcat.measures_path(idx), 5)
    have = {(r[0], r[1]) for r in rows if r[2] == "vtr_luts" and not r[3].startswith("fail")}
    bad = {(r[0], r[1]) for r in rows if r[2] == "vtr_stage" and r[3] != benchcat.STAGE_DONE}
    seen = {(r[0], r[1]) for r in rows if r[2] == "vtr_stage"}
    skip = have | (seen - (bad if retry_failed else set()))
    su = bench.load_suites(idx)[suite_id]
    todo = sorted((d for d in bench.load_designs(idx) if d.suite == suite_id
                   and d.format == "verilog" and (d.suite, d.design) not in skip),
                  key=lambda d: (d.bytes, d.design))
    n = 0
    for d in todo[:limit]:
        sink(measure_design(odin3, vtr, su, d, out_root))
        n += 1
    return n
