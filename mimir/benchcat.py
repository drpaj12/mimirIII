"""`mimir bench catalogue`: one table of every registered design, grouped by suite (where it is
from), with the properties, size, VTR-path and silicon-path numbers that were measured.

Inputs: the registry (`designs.tsv`, `suites.toml`) and `measures.tsv`, a long table
`suite design key value source` that the collectors of `mimir.benchmeasure` write. Outputs:
`docs/benchmarks/catalogue.md` (GitHub markdown) and `data/benchmarks/catalogue.tsv`.

A cell is a measured value, `-` (not run), `n/a` (does not apply) or `fail: <reason>`. Nothing is
filled by guess: a key with no measures row is `-`."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from mimir import bench

MEASURES = "measures.tsv"
MEASURE_HEADER = ["suite", "design", "key", "value", "source"]
# the two BLIF suites hold the same circuits; one section, one row per name
MERGED = {"vtr-blif-k2": "vtr-blif", "vtr-blif-k4": "vtr-blif"}
MERGED_ORDER = ("vtr-blif-k4", "vtr-blif-k2")  # lookup order for a measure of a merged row
YES, NO = "✓", "✗"
CHECKS = ["seq", "mem", "mul", "add", "fsm", "lat", "hier", "bbx"]
CHECK_HEAD = ["seq", "mem", "mul", "add", "fsm", "latch", "hier", "bbox"]
KEYS = (
    [f"chk_{c}" for c in CHECKS]
    + ["tb", "vec", "sim_iverilog", "sim_odin", "vtr_stage", "desc"]
    + ["vtr_luts", "vtr_blocks", "vtr_ffs", "vtr_pins", "vtr_mult", "vtr_mem", "vtr_cpd", "vtr_cw"]
    + ["g_gates", "g_depth", "l4_luts", "l4_depth", "l6_luts", "l6_depth"]
    + ["si_cells", "si_area", "si_lvs", "si_stage"]
)
CHECK_KEYS = {f"chk_{c}" for c in CHECKS} | {"vec", "sim_iverilog", "sim_odin"}
TSV_HEAD = (["tier", "rank", "section", "design", "format", "top", "loc", "members", "link",
             "licence"] + KEYS)

# Tiers (rule uses measured columns only, never the suite name).
LOC_BIG = 200  # Verilog lines at or above which a design counts as larger
STAGE_DONE = "route"  # deepest VTR stage the T0 rule needs (routed, timing analysed)
TIERS = {
    0: ("T0 whole flow", f"HDL with its own testbench, {LOC_BIG}+ Verilog lines, the testbench "
        f"passes in iverilog (`sim_iverilog`=1) and in Odin III simulation (`sim_odin`=1), and "
        f"the VTR flow reaches `{STAGE_DONE}` with timing (`vtr_stage`)"),
    1: ("T1 HDL + testbench, larger", f"HDL with a testbench and {LOC_BIG}+ Verilog lines "
        "(and not T0)"),
    2: ("T2 HDL + testbench, small", f"HDL with a testbench and under {LOC_BIG} Verilog lines"),
    3: ("T3 HDL, no testbench", "HDL (Verilog) with no testbench file"),
    4: ("T4 netlist only", "BLIF netlist, no HDL"),
}


@dataclass
class Row:
    tier: int
    rank: int
    section: str
    design: str
    format: str
    top: str
    loc: str
    members: list[str]
    vals: dict[str, str]
    link: str = "-"
    licence: str = "-"


class CatalogueError(Exception):
    pass


def measures_path(idx: Path) -> Path:
    return idx / MEASURES


def load_measures(idx: Path) -> dict[tuple[str, str], dict[str, tuple[str, str]]]:
    """(suite, design) -> key -> (value, source)."""
    path = measures_path(idx)
    out: dict[tuple[str, str], dict[str, tuple[str, str]]] = defaultdict(dict)
    if not path.is_file():
        return out
    for suite, design, key, value, source in bench.read_tsv(path, 5):
        out[(suite, design)][key] = (value, source)
    return out


def save_measures(idx: Path, rows: list[list[str]]) -> None:
    bench.write_tsv(measures_path(idx), MEASURE_HEADER, sorted(rows))


def upsert_measures(idx: Path, new: list[list[str]]) -> int:
    """Add or replace rows by (suite, design, key); returns the row count written."""
    path = measures_path(idx)
    have = {(r[0], r[1], r[2]): r for r in bench.read_tsv(path, 5)} if path.is_file() else {}
    for r in new:
        if r[2] not in KEYS:
            raise CatalogueError(f"unknown measure key {r[2]!r}")
        have[(r[0], r[1], r[2])] = r
    save_measures(idx, list(have.values()))
    return len(have)


def build_rows(designs: list[bench.Design],
               measures: dict[tuple[str, str], dict[str, tuple[str, str]]]) -> list[Row]:
    """One row per design; the k2 and k4 BLIF suites join into one row per circuit name."""
    groups: dict[tuple[str, str], list[bench.Design]] = defaultdict(list)
    for d in designs:
        groups[(MERGED.get(d.suite, d.suite), d.design)].append(d)
    rows: list[Row] = []
    for (section, name), ds in sorted(groups.items()):
        ds.sort(key=lambda d: (MERGED_ORDER.index(d.suite) if d.suite in MERGED_ORDER else 0))
        lead = ds[0]
        members = [d.suite for d in ds]
        vals: dict[str, str] = {}
        for key in KEYS:
            for m in members:
                got = measures.get((m, name), {}).get(key)
                if got is not None:
                    vals[key] = got[0]
                    break
        if section in MERGED.values():
            fmt = "blif (" + ",".join(m.rsplit("-", 1)[1] for m in sorted(members)) + ")"
            loc = "-"
        else:
            fmt = lead.format
            loc = str(lead.lines) if lead.format != "blif" else "-"
        rows.append(Row(0, 0, section, name, fmt, lead.top, loc, sorted(members), vals))
    return rank_rows(rows)


def _num(v: str | None) -> float | None:
    try:
        return float(v) if v is not None else None
    except ValueError:
        return None


def tier_of(row: Row) -> int:
    """Tier from measured columns: format, testbench, size, simulation and VTR stage."""
    if row.format.startswith("blif"):
        return 4
    tb = row.vals.get("tb", "0")
    if tb in ("0", "-", ""):
        return 3
    loc = _num(row.loc)
    if loc is None or loc < LOC_BIG:
        return 2
    whole = (row.vals.get("sim_iverilog") == "1" and row.vals.get("sim_odin") == "1"
             and row.vals.get("vtr_stage") == STAGE_DONE)
    return 0 if whole else 1


def _lut_count(row: Row) -> float | None:
    for k in ("l6_luts", "vtr_luts", "l4_luts"):
        v = _num(row.vals.get(k))
        if v is not None:
            return v
    return None


def rank_rows(rows: list[Row]) -> list[Row]:
    """Set tier and rank and return the rows in table order: tier, testbench first, designs with a
    LUT count (largest first) before those with only LOC (largest first), then name."""
    def key(r: Row) -> tuple[int, int, int, float, str]:
        lut, loc = _lut_count(r), _num(r.loc) or 0.0
        has_tb = r.vals.get("tb", "0") not in ("0", "-", "")
        return (r.tier, 0 if has_tb else 1, 0 if lut is not None else 1,
                -(lut if lut is not None else loc), r.design)
    for r in rows:
        r.tier = tier_of(r)
    rows = sorted(rows, key=lambda r: (key(r), r.section))
    for i, r in enumerate(rows):
        r.rank = i + 1
    return rows


def _cell(key: str, row: Row) -> str:
    v = row.vals.get(key, "-")
    if key in CHECK_KEYS:
        return {"1": YES, "0": NO}.get(v, v)
    return v


def _pair(a: str, b: str) -> str:
    return "-" if a == "-" and b == "-" else f"{a}/{b}"


def short_licence(text: str) -> str:
    """The licence name of a suite's `licence` text: up to the first ( ; , or :."""
    head = re.split(r"[(;,:]", text, maxsplit=1)[0].strip()
    return head or "-"


def attach_sources(rows: list[Row], suites: dict[str, bench.Suite]) -> None:
    """link = a `link` measure, else the upstream URL of the (first) suite; licence likewise."""
    for r in rows:
        su = suites[r.members[0]]
        r.link = r.vals.get("link", su.upstream)
        r.licence = r.vals.get("licence", short_licence(su.licence))


# (id, label): every displayed column; GROUPS pick ids for the narrow tables, HTML shows all
LABELS = {
    "design": "design", "desc": "what it does", "suite": "suite", "link": "link",
    "licence": "licence", "fmt": "format", "top": "top", "loc": "LOC", "tb": "tb", "vec": "vec",
    "iv": "iverilog", "osim": "Odin sim", "stage": "VTR stage", "luts": "LUTs", "blocks": "blocks",
    "ffs": "FFs", "pins": "pins", "hard": "mult/mem", "cpd": "cpd ns", "cw": "chan w",
    "gates": "gates/d", "l4": "4-LUT/d", "l6": "6-LUT/d",
    **{c: h for c, h in zip(CHECKS, CHECK_HEAD, strict=True)},
    "cells": "cells", "area": "core um2", "lvs": "LVS", "sstage": "Si stage",
}
GROUPS = {
    "Overview": ["design", "desc", "suite", "link", "licence", "loc", "tb", "vec"],
    "Flow and VTR QoR": ["design", "iv", "osim", "stage", "luts", "blocks", "ffs", "pins", "hard",
                         "cpd", "cw"],
    "LUT forms": ["design", "gates", "l4", "l6"],
    "Properties": ["design", *CHECKS],
    "Silicon": ["design", "cells", "area", "lvs", "sstage"],
}


def fields(row: Row, html: bool = False) -> dict[str, str]:
    """Every displayed value of a row. md: testbench as a mark, `|` removed; html: the testbench
    path and full texts."""
    g = {k: _cell(k, row) for k in KEYS}
    tb = row.vals.get("tb", "-")
    out = {
        "design": row.design, "desc": g["desc"], "suite": row.section, "link": row.link,
        "licence": row.licence, "fmt": row.format, "top": row.top, "loc": row.loc,
        "tb": tb if html else (NO if tb == "0" else YES if tb != "-" else "-"),
        "vec": g["vec"], "iv": g["sim_iverilog"], "osim": g["sim_odin"], "stage": g["vtr_stage"],
        "luts": g["vtr_luts"], "blocks": g["vtr_blocks"], "ffs": g["vtr_ffs"],
        "pins": g["vtr_pins"], "hard": _pair(g["vtr_mult"], g["vtr_mem"]), "cpd": g["vtr_cpd"],
        "cw": g["vtr_cw"], "gates": _pair(g["g_gates"], g["g_depth"]),
        "l4": _pair(g["l4_luts"], g["l4_depth"]), "l6": _pair(g["l6_luts"], g["l6_depth"]),
        "cells": g["si_cells"], "area": g["si_area"], "lvs": g["si_lvs"], "sstage": g["si_stage"],
        **{c: g[f"chk_{c}"] for c in CHECKS},
    }
    return out


MD_MAX = 30


def _md(col: str, row: Row, v: str) -> str:
    v = v.replace("|", "/")
    if col == "suite":
        return f"[{v}](#sources)"
    if col == "link":
        return f"[repo]({v})" if v.startswith("http") else v
    if col not in ("design", "desc") and len(v) > MD_MAX:
        return v[: MD_MAX - 3] + "..."
    return v


def _origin(suites: dict[str, bench.Suite], section: str) -> str:
    ids = [s for s, sec in MERGED.items() if sec == section] or [section]
    su = suites[ids[0]]
    title = su.title if len(ids) == 1 else (
        "VTR blif/2 and blif/4: ISCAS-85, ISCAS-89 and MCNC mapped to 2-input and 4-input LUTs")
    lic = su.licence
    return (f"{title}. Upstream {su.upstream} at {su.commit}. Licence: {lic}.")


def _by_tier(rows: list[Row]) -> dict[int, list[Row]]:
    by: dict[int, list[Row]] = defaultdict(list)
    for r in rows:
        by[r.tier].append(r)
    return by


def _summary(rows: list[Row]) -> list[str]:
    by = _by_tier(rows)
    out = ["| tier | rule | designs |", "|---|---|---|"]
    out += [f"| {TIERS[t][0]} | {TIERS[t][1]} | {len(by.get(t, []))} |" for t in sorted(TIERS)]
    suites: dict[str, int] = defaultdict(int)
    for r in rows:
        suites[r.section] += 1
    out += ["", "| suite | designs |", "|---|---|"]
    out += [f"| {s} | {n} |" for s, n in sorted(suites.items())]
    return out + [f"| total | {len(rows)} |"]


def sub_tables(rows: list[Row]) -> dict[str, list[str]]:
    """One narrow table per group; every table has the same rows in the same order and
    `design` as its first column."""
    out: dict[str, list[str]] = {}
    for name, cols in GROUPS.items():
        head = [LABELS[c] for c in cols]
        lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(cols)]
        for r in rows:
            f = fields(r)
            lines.append("| " + " | ".join(_md(c, r, f[c]) for c in cols) + " |")
        out[name] = lines
    return out


def _table(rows: list[Row]) -> list[str]:
    tables = sub_tables(rows)
    out = tables["Overview"]
    for name, lines in tables.items():
        if name != "Overview":
            out += ["", f"<details><summary>{name}</summary>", ""] + lines + ["", "</details>"]
    return out


def _sources(suites: dict[str, bench.Suite], rows: list[Row]) -> list[str]:
    out = ['<a id="sources"></a>', "", "### Sources", ""]
    for sec in sorted({r.section for r in rows}):
        out.append(f"- **{sec}**: {_origin(suites, sec)}")
    return out


def _tier_blocks(rows: list[Row], fold: bool) -> list[str]:
    by = _by_tier(rows)
    out: list[str] = []
    for t in sorted(TIERS):
        if t not in by:
            continue
        name, rule = TIERS[t]
        if fold:
            out += ["", f"<details><summary>{name} ({len(by[t])} designs)</summary>", "",
                    f"Rule: {rule}.", ""] + _table(by[t]) + ["", "</details>"]
        else:
            out += ["", f"## {name}", "", f"Rule: {rule}.", ""] + _table(by[t])
    return out


def render_md(suites: dict[str, bench.Suite], rows: list[Row], legend: str) -> str:
    out = ["# Mimir benchmark catalogue", "", legend, "",
           f"One sortable, filterable table with a top scrollbar: [catalogue.html]({HTML_URL}) "
           "(file `docs/benchmarks/catalogue.html`).", ""] + _summary(rows)
    out += _tier_blocks(rows, False) + [""] + _sources(suites, rows)
    return "\n".join(out) + "\n"


HTML_URL = "https://drpaj12.github.io/mimirIII/benchmarks/catalogue.html"
README_START = "<!-- catalogue:start (generated by `mimir bench catalogue`; do not edit) -->"
README_END = "<!-- catalogue:end -->"


def render_readme_section(suites: dict[str, bench.Suite], rows: list[Row], legend: str) -> str:
    """The README block: legend, tier and suite counts, each tier table in a <details> fold."""
    out = [README_START, "## Benchmark catalogue", "", legend, ""] + _summary(rows)
    out += _tier_blocks(rows, True) + [""] + _sources(suites, rows)
    out += ["", f"Sortable, filterable single-table page: [catalogue.html]({HTML_URL}) "
            "(GitHub Pages; the file is docs/benchmarks/catalogue.html). Same tables: "
            "[docs/benchmarks/catalogue.md](docs/benchmarks/catalogue.md); method: "
            "[docs/benchmarks/catalogue-method.md](docs/benchmarks/catalogue-method.md).",
            README_END]
    return "\n".join(out)


def replace_section(text: str, section: str) -> str:
    """Replace the marked block of `text`; the markers must both be present once."""
    i, j = text.find(README_START), text.find(README_END)
    if i < 0 or j < i or text.count(README_START) != 1:
        raise CatalogueError("README.md has no catalogue markers (or they are out of order)")
    return text[:i] + section + text[j + len(README_END):]


def render_tsv_rows(rows: list[Row]) -> list[list[str]]:
    return [[str(r.tier), f"{r.rank:05d}", r.section, r.design, r.format, r.top, r.loc,
             ",".join(r.members), r.link, r.licence]
            + [r.vals.get(k, "-") for k in KEYS] for r in rows]


def fill_counts(rows: list[Row]) -> dict[str, tuple[int, int]]:
    """key -> (rows with a value, rows total); a value that starts with fail or n/a counts as
    filled (it says why); `-` is not filled."""
    return {k: (sum(1 for r in rows if k in r.vals), len(rows)) for k in KEYS}


def generate(idx: Path, out_md: Path, legend: str, readme: Path | None = None) -> list[Row]:
    suites = bench.load_suites(idx)
    designs = bench.load_designs(idx)
    rows = build_rows(designs, load_measures(idx))
    attach_sources(rows, suites)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(render_md(suites, rows, legend), encoding="utf-8", newline="\n")
    bench.write_tsv(idx / "catalogue.tsv", TSV_HEAD, render_tsv_rows(rows))
    from mimir import benchcathtml

    benchcathtml.write(out_md.with_suffix(".html"), rows)
    if readme is not None:
        text = readme.read_text(encoding="utf-8")
        block = render_readme_section(suites, rows, legend)
        readme.write_text(replace_section(text, block), encoding="utf-8", newline="\n")
    return rows
