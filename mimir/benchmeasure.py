"""Collectors for `measures.tsv` (see `mimir.benchcat`): each reads data that already exists and
returns rows `[suite, design, key, value, source]`. Nothing here runs a flow."""

from __future__ import annotations

import json
import re
import sqlite3
import subprocess
import tomllib
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any
from urllib.parse import quote

from mimir import bench, benchcat, blif, blobs

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


# ---- other Mimir store records --------------------------------------------------------------

LOKI_SOURCE = "loki:loki-veval-exp/dataset"
LOKI_FLOOR = "f2"  # `lower; abc --lut 6` after the common front: the 6-LUT run of this catalogue
BLIF_STRUCT = {"vtr-blif-k4": "mcnc-k4", "mcnc20": "mcnc"}


def _ro(db: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{quote(str(db))}?mode=ro", uri=True)


def collect_store_extra(idx: Path, db: Path) -> list[Row]:
    """6-LUT counts of the VerilogEval designs (Loki floor f2, same passes as the 6-LUT run here,
    Odin III version not recorded in the store) and the 4-LUT count and logic depth of the
    shipped 4-LUT BLIF circuits (store sources mcnc-k4 and mcnc, `struct.n_comb`, `struct.depth`).
    Each source field names the store source, floor or metric."""
    reg = {(d.suite, d.design) for d in bench.load_designs(idx)}
    rows: list[Row] = []
    con = _ro(db)
    try:
        q = ("SELECT design, value FROM records WHERE source = ? AND arch = ? "
             "AND metric = 'loki.luts'")
        for design, value in con.execute(q, (LOKI_SOURCE, LOKI_FLOOR)):
            name = design[3:] if design.startswith("ve_") else design
            if ("verilogeval", name) in reg:
                src = f"store {LOKI_SOURCE} {LOKI_FLOOR} loki.luts (Odin version not recorded)"
                rows.append(["verilogeval", name, "l6_luts", _num(value), src])
        for suite, source in BLIF_STRUCT.items():
            q = ("SELECT design, metric, value FROM records WHERE source = ? AND level = 'lut' "
                 "AND metric IN ('struct.n_comb', 'struct.depth')")
            keys = {"struct.n_comb": "l4_luts", "struct.depth": "l4_depth"}
            for design, metric, value in con.execute(q, (source,)):
                if (suite, design) in reg:
                    src = f"store {source} {metric} (shipped 4-LUT BLIF, no remap)"
                    rows.append([suite, design, keys[metric], _num(value), src])
    finally:
        con.close()
    return rows


# ---- what a design does -----------------------------------------------------------------------

PROMPT_RE = re.compile(r"[Tt]he module should implement (.*?)\.(?:\s|$)")
VTR_DOC = "doc/src/vtr/benchmarks.rst"
DESC_MAX = 80


def _clean(text: str) -> str:
    text = " ".join(text.replace("|", "/").split())
    return text if len(text) <= DESC_MAX else text[: DESC_MAX - 3].rstrip() + "..."


def vtr_domains(rst: str) -> dict[str, str]:
    """name -> domain from the `table_vtr_benchmarks` table of the VTR documentation."""
    out: dict[str, str] = {}
    body = rst.split("table_vtr_benchmarks", 1)[-1]
    for line in body.splitlines()[:40]:
        m = re.match(r"\s{4}(\S+)\s{2,}(\S.*?)\s*$", line)
        if m and not set(m.group(1)) <= {"="} and m.group(1) != "Benchmark":
            out[m.group(1)] = m.group(2)
    return out


def collect_desc(idx: Path, ext_root: Path, meta_toml: Path) -> list[Row]:
    """One phrase per design from the suite's own text; no phrase where the source says none.
    VerilogEval: the prompt sentence `The module should implement ...`; VTR Verilog: the Domain
    column of the VTR documentation table; MCNC circuits: the `intent` of data/meta/mcnc.toml
    up to its first parenthesis; BRISC-V: the suite title."""
    suites = bench.load_suites(idx)
    domains = vtr_domains((ext_root / "vtr-verilog-to-routing" / VTR_DOC).read_text("utf-8"))
    mcnc = tomllib.loads(meta_toml.read_text("utf-8")).get("circuit", {})
    rows: list[Row] = []
    for d in bench.load_designs(idx):
        su, got = suites[d.suite], None
        if d.suite == "verilogeval":
            f = ext_root / su.external / su.subdir / f"{d.design}_prompt.txt"
            m = PROMPT_RE.search(" ".join(f.read_text("utf-8").split())) if f.is_file() else None
            got = (m.group(1), f"{su.external}/{su.subdir}/{d.design}_prompt.txt") if m else None
        elif d.suite == "vtr-verilog" and d.design in domains:
            got = (domains[d.design], f"VTR 7.0 benchmarks table, {VTR_DOC}")
        elif d.suite == "brisc-v":
            got = ("BRISC-V microcontroller (Arduino-on-RISC-V)", "suites.toml brisc-v title")
        elif d.design in mcnc and d.suite in ("mcnc20", "vtr-blif-k4", "vtr-blif-k2"):
            intent = str(mcnc[d.design].get("intent", "")).split(" (")[0].strip()
            got = (intent, f"data/meta/mcnc.toml circuit.{d.design}.intent") if intent else None
        if got:
            rows.append([d.suite, d.design, "desc", _clean(got[0]), got[1]])
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


# ---- Odin III: property checks, gate and LUT counts ---------------------------------------
# Three runs per Verilog design (properties on the VTR architecture, then soft logic mapped to
# 6-LUTs and to 4-LUTs); two per BLIF circuit. Commands are in docs/benchmarks/catalogue-method.md.

ARCH_REL = "vtr_flow/arch/timing/k6_frac_N10_frac_chain_mem32K_40nm.xml"
FRONT = "proc; fsm; opt; flatten; opt -full; wreduce"
CELL_RE = re.compile(r"stats: module (\S+): cell (\S+) (\d+)")
KNOWN_HARD = {"adder", "multiply", "single_port_ram", "dual_port_ram"}
TIMEOUT_S = 900


def _text(data: str | bytes | None) -> str:
    if data is None:
        return ""
    return data if isinstance(data, str) else data.decode("utf-8", "replace")


def run_odin(binary: Path, top: str, script: str, timeout: int = TIMEOUT_S) -> tuple[int, str]:
    cmd = [str(binary)] + (["--top", top] if top and top != "-" else []) + ["-p", script]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        out, err = _text(exc.stdout), _text(exc.stderr)
        return 124, TIMEOUT_TAG + (out + err)
    return res.returncode, res.stdout + res.stderr


TIMEOUT_TAG = "\x00timeout\x00"


def _fail_reason(rc: int, text: str) -> str:
    if text.startswith(TIMEOUT_TAG):
        done = re.findall(r"pass (\w+):", text)
        where = f"last finished pass {done[-1]}" if done else "before the first pass finished"
        return f"fail: too big for now (timeout {TIMEOUT_S} s, {where})"
    errs = [ln for ln in text.splitlines() if "error" in ln.lower()]
    first = errs[0].split("error:", 1)[-1].strip() if errs else f"exit {rc}"
    first = re.sub(r"(?:/[^\s:'\"]+)+/([^/\s:'\"]+)", r"\1", first)  # no absolute paths
    return "fail: " + first.replace("\t", " ")[:100]


def _cells(text: str, after: int = 0) -> dict[str, int]:
    """Cell-type counts of the stats block that starts at or after offset `after`."""
    out: dict[str, int] = {}
    for m in CELL_RE.finditer(text, after):
        out[m.group(2)] = out.get(m.group(2), 0) + int(m.group(3))
    return out


def _stats_blocks(text: str) -> list[dict[str, int]]:
    parts = text.split("stats: design:")[1:]
    return [_cells("stats: design:" + p) for p in parts]


def _modules(text: str) -> int:
    m = re.search(r"stats: design: modules (\d+)", text)
    return int(m.group(1)) if m else 0


def _flag(b: bool) -> str:
    return "1" if b else "0"


def properties(text: str) -> dict[str, str]:
    """The eight checks from the log of the property run (stats after read, after the front
    passes, after hardmap; the fsm and partial_map messages)."""
    blocks = _stats_blocks(text)
    if len(blocks) < 2:
        raise ValueError("no stats blocks")
    word = blocks[1]
    pm = re.search(r"partial_map: (\d+) multiply, (\d+) adder in \d+ chains, (\d+) single_port_ram"
                   r" \+ (\d+) dual_port_ram", text)
    mult, add, spr, dpr = (int(x) for x in pm.groups()) if pm else (0, 0, 0, 0)
    names = " ".join(word)
    return {
        "chk_seq": _flag(bool(re.search(r"\$\w*(dff|latch)", names, re.I)) or bool(spr + dpr)),
        "chk_lat": _flag(bool(re.search(r"\$\w*latch", names, re.I))),
        "chk_mem": _flag(bool(re.search(r"\$mem", names)) or bool(spr + dpr)
                         or "single_port_ram" in word or "dual_port_ram" in word),
        "chk_mul": _flag(bool(re.search(r"\$(mul|macc)\b", names)) or mult > 0),
        "chk_add": _flag(bool(re.search(r"\$(add|sub|alu|macc)\b", names)) or add > 0),
        "chk_fsm": _flag("fsm: information on FSM" in text),
        "chk_hier": _flag(_modules(text) > 1),
        "chk_bbx": _flag(any(not t.startswith("$") and t not in KNOWN_HARD for t in word)),
    }


GATE_SKIP = ("FF", "LATCH", "CONST")


def gates_count(block: dict[str, int]) -> int:
    n = 0
    for t, c in block.items():
        m = re.fullmatch(r"\$_([A-Z0-9]+)_", t)
        if m and not any(s in m.group(1) for s in GATE_SKIP):
            n += c
    return n


def lut_result(text: str) -> tuple[int, int]:
    """(LUTs, depth) from the abc pass: `$lut` cells of the last stats block and `final: depth`."""
    blocks = _stats_blocks(text)
    d = re.search(r"abc: final: depth (\d+)", text)
    if not blocks or "$lut" not in blocks[-1] or d is None:
        raise ValueError("no abc LUT result")
    return blocks[-1]["$lut"], int(d.group(1))


def _gate_total(d: bench.Design, blk: dict[str, int]) -> int:
    """Gates of the pre-LUT netlist: bit-level gates of a lowered design, `.names` nodes (`$sop`)
    of a BLIF circuit as shipped."""
    return blk.get("$sop", 0) if d.format == "blif" else gates_count(blk)


def _empty(rc: int, gates: int) -> str:
    """No logic level or LUT result: with no gates and a clean exit that is 0, else a failure."""
    return "0" if rc == 0 and gates == 0 else f"fail: exit {rc}"


def _luts_or_empty(rc: int, text: str, gates: int) -> tuple[str, str]:
    try:
        luts, depth = lut_result(text)
    except ValueError:
        if rc == 0 and gates == 0:
            return "0", "0"
        raise
    return str(luts), str(depth)


def _row(d: bench.Design, key: str, val: str, src: str) -> Row:
    return [d.suite, d.design, key, val, src]


def _fail_rows(d: bench.Design, keys: list[str], reason: str, src: str) -> list[Row]:
    return [_row(d, k, reason, src) for k in keys]


def _soft_runs(binary: Path, d: bench.Design, read: str, src: str) -> list[Row]:
    # `read` holds read_arch for Verilog, so hard-block instances (RAM models) resolve
    rows: list[Row] = []
    run_a = f"{read}; {FRONT}; lower; stats; levelize; abc --lut 6; stats"
    if d.format == "blif":
        run_a = f"{read}; stats; levelize; abc --lut 6; stats"
    rc, text = run_odin(binary, d.top, run_a)
    keys6 = ["g_gates", "g_depth", "l6_luts", "l6_depth"]
    try:
        blk = _stats_blocks(text)[0]
        gates = _gate_total(d, blk)
        rows.append(_row(d, "g_gates", str(gates), src))
        lv = re.search(r"levelize: .* max level (\d+)", text)
        rows.append(_row(d, "g_depth", lv.group(1) if lv else _empty(rc, gates), src))
        luts, depth = _luts_or_empty(rc, text, gates)
        rows += [_row(d, "l6_luts", luts, src), _row(d, "l6_depth", depth, src)]
    except (ValueError, IndexError):
        rows += _fail_rows(d, keys6, _fail_reason(rc, text), src)
    if d.format == "blif":  # the shipped circuits are 4-LUT mapped: l4 comes from the store
        return rows
    run_b = run_a.replace("--lut 6", "--lut 4")
    rc, text = run_odin(binary, d.top, run_b)
    try:
        gates4 = _gate_total(d, _stats_blocks(text)[0])
        luts, depth = _luts_or_empty(rc, text, gates4)
        rows += [_row(d, "l4_luts", luts, src), _row(d, "l4_depth", depth, src)]
    except (ValueError, IndexError):
        rows += _fail_rows(d, ["l4_luts", "l4_depth"], _fail_reason(rc, text), src)
    return rows


def _verilog_files(suite: bench.Suite, d: bench.Design) -> list[Path]:
    base = bench.external_root() / suite.external / suite.subdir
    if d.format == "verilog-project":
        return sorted(f for f in base.glob("*.v") if not f.stem.lower().startswith("tb_")
                      and not f.stem.endswith("_bb"))
    return [base / d.path]


def measure_design(binary: Path, vtr: Path, suite: bench.Suite, d: bench.Design,
                   version: str) -> list[Row]:
    src = f"odin3 {version} ({binary.parent.name})"
    arch = vtr / ARCH_REL
    if d.format == "blif":
        path = bench.source_path(suite, d)
        read = f"read_blif {path}"
        rows = _soft_runs(binary, d, read, src)
        rc, text = run_odin(binary, "", f"read_arch {arch}; {read}; stats")
        try:
            blk = _stats_blocks(text)[0]
            rows += _blif_props(d, blk, _modules(text), src)
        except IndexError:
            keys = [f"chk_{c}" for c in benchcat.CHECKS]
            rows += _fail_rows(d, keys, _fail_reason(rc, text), src)
        return rows
    files = " ".join(str(f) for f in _verilog_files(suite, d))
    flags = "--auto-blackbox " if d.format == "verilog-project" else ""
    read = f"read_verilog --nolatches --vtr-compat {flags}{files}"
    soft_read = f"read_arch {arch}; {read}"
    prop = f"read_arch {arch}; {read}; stats; {FRONT}; stats; hardmap; stats"
    rc, text = run_odin(binary, d.top, prop)
    try:
        rows = [_row(d, k, v, src) for k, v in properties(text).items()]
    except ValueError:
        rows = _fail_rows(d, [f"chk_{c}" for c in benchcat.CHECKS], _fail_reason(rc, text), src)
    return rows + _soft_runs(binary, d, soft_read, src)


def _blif_props(d: bench.Design, blk: dict[str, int], modules: int, src: str) -> list[Row]:
    seq = any("DFF" in t or "LATCH" in t for t in blk)
    sub = [t for t in blk if not t.startswith("$")]
    vals = {"chk_seq": _flag(seq), "chk_mem": _flag(any(t in MEM_MODELS for t in sub)),
            "chk_mul": _flag(any(t in MULT_MODELS for t in sub)),
            "chk_add": _flag("adder" in sub), "chk_hier": _flag(modules > 1),
            "chk_bbx": _flag(any(t not in KNOWN_HARD for t in sub)),
            "chk_fsm": "n/a", "chk_lat": "n/a"}
    return [_row(d, k, v, src) for k, v in vals.items()]


def collect_odin(idx: Path, binary: Path, vtr: Path, suite_id: str, done: set[tuple[str, str]],
                 limit: int | None, sink: Callable[[list[Row]], None]) -> int:
    """Run the measures for the designs of suite_id, smallest source first; `sink` is called
    after each design with its rows. Returns the number of designs run."""
    suites = bench.load_suites(idx)
    su = suites[suite_id]
    raw = subprocess.run([str(binary), "--version"], capture_output=True, text=True,
                         check=False).stdout.split()
    ver = " ".join(raw)
    todo = sorted((d for d in bench.load_designs(idx) if d.suite == suite_id
                   and (d.suite, d.design) not in done), key=lambda d: (d.bytes, d.design))
    n = 0
    for d in todo[:limit]:
        sink(measure_design(binary, vtr, su, d, ver))
        n += 1
    return n
