"""Collectors for `measures.tsv` (see `mimir.benchcat`): each reads data that already exists and
returns rows `[suite, design, key, value, source]`. Nothing here runs a flow."""

from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import quote

from mimir import bench, blif, blobs

VTR_ARCH = "k6_frac_N10_frac_chain_mem32K_40nm"
VTR_SOURCE = "norns-placers-e10-base"
VTR_ARM = "vpr_sa"
VTR_SEED = 1
VTR_FLOWS = ("odin3-1.2.0-k6-verilog", "odin3-1.2.0-k6-blif")
MULT_MODELS = {"multiply"}
MEM_MODELS = {"single_port_ram", "dual_port_ram"}
Row = list[str]


# ---- VTR path -----------------------------------------------------------------------------

def blif_counts(text: str) -> dict[str, int]:
    """FFs, pins, mult and memory hard blocks of the top model of a mapped BLIF."""
    models = blif.parse_models(text)
    top = models[0]
    ffs = sum(1 for h, _ in top.items if h == ".latch")
    subs = [a[0] for h, a in top.items if h == ".subckt" and a]
    return {"ffs": ffs, "pins": len(top.inputs) + len(top.outputs),
            "mult": sum(1 for s in subs if s in MULT_MODELS),
            "mem": sum(1 for s in subs if s in MEM_MODELS)}


def _store_vals(db: Path) -> dict[str, dict[str, float]]:
    con = sqlite3.connect(f"file:{quote(str(db))}?mode=ro", uri=True)
    try:
        q = ("SELECT design, metric, value FROM records WHERE source = ? AND arch = ? AND seed = ? "
             "AND arm = ? AND metric IN ('struct.n_comb','vpr.blocks','vpr.cpd','vpr.chan_width')")
        out: dict[str, dict[str, float]] = {}
        for design, metric, value in con.execute(q, (VTR_SOURCE, VTR_ARCH, VTR_SEED, VTR_ARM)):
            out.setdefault(design, {})[metric] = value
        return out
    finally:
        con.close()


def _num(v: float) -> str:
    return str(int(v)) if v == int(v) else f"{v:g}"


def collect_vtr(idx: Path, store_db: Path, blob_dir: Path) -> list[Row]:
    """LUTs, blocks, cpd and channel width from the Norns e10-base run record (seed 1) in the
    store; FFs, pins, hard blocks from the mapped BLIF blob of the same design and flow."""
    vals = _store_vals(store_db)
    cite = f"{VTR_SOURCE}/{VTR_ARM}/seed{VTR_SEED}/{VTR_ARCH}"
    rows: list[Row] = []
    for n in bench.load_netlists(idx):
        if n.flow not in VTR_FLOWS or n.design not in vals:
            continue
        v = vals[n.design]
        for key, metric in (("vtr_luts", "struct.n_comb"), ("vtr_blocks", "vpr.blocks"),
                            ("vtr_cpd", "vpr.cpd"), ("vtr_cw", "vpr.chan_width")):
            if metric in v:
                rows.append([n.suite, n.design, key, _num(v[metric]), f"store {cite} {metric}"])
        c = blif_counts(blobs.get_bytes(blob_dir, n.sha256).decode("utf-8", "replace"))
        src = f"blob {n.sha256[:12]} flow {n.flow}"
        for key, name in (("vtr_ffs", "ffs"), ("vtr_pins", "pins"), ("vtr_mult", "mult"),
                          ("vtr_mem", "mem")):
            rows.append([n.suite, n.design, key, str(c[name]), src])
    return rows


# ---- silicon path -------------------------------------------------------------------------

STAGES = ["read", "elab", "map", "netlist", "equiv", "place", "route", "gds", "extract", "lvs"]


def _core_area(log: Path) -> str | None:
    if not log.is_file():
        return None
    for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.search(r"GPL-0016\] CoreArea: (\d+)", line)
        if m:
            return f"{int(m.group(1)) / 1e6:.1f}"
    return None


def _routed_cells(census: Path) -> str | None:
    if not census.is_file():
        return None
    steps = {s["step"]: s["total"] for s in json.loads(census.read_text(encoding="utf-8"))}
    return str(steps["s10_detail_route"]) if "s10_detail_route" in steps else None


def silicon_row(name: str, status: Mapping[str, Any], out: Path) -> list[tuple[str, str]]:
    steps = status["steps"]
    ok = [s for s in STAGES if steps.get(s) == "ok"]
    failed = [s for s in STAGES if str(steps.get(s, "")).startswith("FAILED")]
    stage = ok[-1] if ok else "none"
    if "lvs" in ok:
        lvs = "match"
    elif "lvs" in failed:
        lvs = "mismatch"
    else:
        why = str(steps[failed[0]])[len("FAILED "):][:60] if failed else "not reached"
        lvs = f"out of scope: stopped at {failed[0] if failed else stage} ({why})"
    res = [("si_stage", stage), ("si_lvs", lvs)]
    cells = _routed_cells(out / "census.json")
    area = _core_area(out / "openroad.log")
    if cells is not None:
        res.append(("si_cells", cells))
    if area is not None:
        res.append(("si_area", area))
    return res


def collect_silicon(idx: Path, root: Path, run_label: str) -> list[Row]:
    """The silicon-flow run root (one dir per design, status.json and out/)."""
    reg = {(d.suite, d.design) for d in bench.load_designs(idx)}
    rows: list[Row] = []
    for d in sorted(root.iterdir()):
        sf = d / "status.json"
        hit = [s for (s, n) in reg if n == d.name and s == "verilogeval"]
        if not sf.is_file() or not hit:
            continue
        for key, val in silicon_row(d.name, json.loads(sf.read_text(encoding="utf-8")), d / "out"):
            rows.append(["verilogeval", d.name, key, val, f"{run_label}/{d.name}/status.json"])
    return rows


# ---- testbenches --------------------------------------------------------------------------

TB_PATTERNS = ("{d}_tb", "tb_{d}", "{d}_test", "test_{d}", "{d}_testbench")


def _find_tb(folder: Path, design: str, deep: bool) -> list[Path]:
    names = [p.format(d=design).lower() for p in TB_PATTERNS]
    files = sorted(folder.rglob("*") if deep else folder.glob("*"))
    return [f for f in files if f.is_file() and f.suffix in (".v", ".sv")
            and any(f.stem.lower().startswith(n) for n in names)]


def collect_testbench(idx: Path, ext_root: Path) -> list[Row]:
    """tb = path relative to the external dir, or 0; vec = 1 when the testbench compares against
    a reference module (VerilogEval: `<d>_test.sv` instantiates `<d>_ref.sv`) or reads a stimulus
    or expected-value file ($readmemh/$readmemb/$fscanf), else 0. The BRISC-V testbench is found
    by its name `tb_*` in the project dir."""
    suites = bench.load_suites(idx)
    rows: list[Row] = []
    for d in bench.load_designs(idx):
        su = suites[d.suite]
        if su.format == "blif":
            rows.append([d.suite, d.design, "tb", "0", "no testbench file in the suite dir"])
            rows.append([d.suite, d.design, "vec", "0", "no testbench file in the suite dir"])
            continue
        folder = ext_root / su.external / su.subdir
        if d.format == "verilog-project":
            found = sorted(f for f in folder.glob("*.v") if f.stem.lower().startswith("tb_"))
        elif d.suite == "verilogeval":
            one = folder / f"{d.design}_test.sv"
            found = [one] if one.is_file() else []
        else:
            found = _find_tb(folder, d.design, False)
        if not found:
            why = f"no tb/test file named for it in {su.subdir}"
            rows.append([d.suite, d.design, "tb", "0", why])
            rows.append([d.suite, d.design, "vec", "0", "no testbench"])
            continue
        rel = found[0].relative_to(ext_root).as_posix()
        text = found[0].read_text(encoding="utf-8", errors="replace")
        vec = bool(re.search(r"\$readmem[hb]|\$fscanf|_ref\b|RefModule", text))
        rows.append([d.suite, d.design, "tb", rel, "file scan"])
        rows.append([d.suite, d.design, "vec", "1" if vec else "0", "testbench text scan"])
    return rows
