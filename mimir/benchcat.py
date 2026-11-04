"""`mimir bench catalogue`: one table of every registered design, grouped by suite (where it is
from), with the properties, size, VTR-path and silicon-path numbers that were measured.

Inputs: the registry (`designs.tsv`, `suites.toml`) and `measures.tsv`, a long table
`suite design key value source` that the collectors of `mimir.benchmeasure` write. Outputs:
`docs/benchmarks/catalogue.md` (GitHub markdown) and `data/benchmarks/catalogue.tsv`.

A cell is a measured value, `-` (not run), `n/a` (does not apply) or `fail: <reason>`. Nothing is
filled by guess: a key with no measures row is `-`."""

from __future__ import annotations

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
    + ["tb", "vec"]
    + ["vtr_luts", "vtr_blocks", "vtr_ffs", "vtr_pins", "vtr_mult", "vtr_mem", "vtr_cpd", "vtr_cw"]
    + ["g_gates", "g_depth", "l4_luts", "l4_depth", "l6_luts", "l6_depth"]
    + ["si_cells", "si_area", "si_lvs", "si_stage"]
)
CHECK_KEYS = {f"chk_{c}" for c in CHECKS} | {"vec"}
TSV_HEAD = ["section", "design", "format", "top", "loc", "members"] + KEYS


@dataclass
class Row:
    section: str
    design: str
    format: str
    top: str
    loc: str
    members: list[str]
    vals: dict[str, str]


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
        rows.append(Row(section, name, fmt, lead.top, loc, sorted(members), vals))
    return rows


def _cell(key: str, row: Row) -> str:
    v = row.vals.get(key, "-")
    if key in CHECK_KEYS:
        return {"1": YES, "0": NO}.get(v, v)
    if key == "tb":
        return NO if v == "0" else v
    return v


def _pair(a: str, b: str) -> str:
    return "-" if a == "-" and b == "-" else f"{a}/{b}"


def _md_cells(row: Row) -> list[str]:
    g = {k: _cell(k, row) for k in KEYS}
    cells = [row.design, row.format, row.top, row.loc]
    cells += [g[f"chk_{c}"] for c in CHECKS]
    cells += [g["tb"], g["vec"]]
    cells += [g["vtr_luts"], g["vtr_blocks"], g["vtr_ffs"], g["vtr_pins"],
              _pair(g["vtr_mult"], g["vtr_mem"]), g["vtr_cpd"], g["vtr_cw"]]
    cells += [_pair(g["g_gates"], g["g_depth"]), _pair(g["l4_luts"], g["l4_depth"]),
              _pair(g["l6_luts"], g["l6_depth"])]
    cells += [g["si_cells"], g["si_area"], g["si_lvs"], g["si_stage"]]
    return [c.replace("|", "/") for c in cells]


MD_HEAD = (["design", "format", "top", "LOC"] + CHECK_HEAD + ["testbench", "vectors"]
           + ["LUTs", "blocks", "FFs", "pins", "mult/mem", "cpd ns", "chan w"]
           + ["gates/depth", "4-LUT/depth", "6-LUT/depth"]
           + ["cells", "core um2", "LVS", "stage"])


def _origin(suites: dict[str, bench.Suite], section: str) -> str:
    ids = [s for s, sec in MERGED.items() if sec == section] or [section]
    su = suites[ids[0]]
    title = su.title if len(ids) == 1 else (
        "VTR blif/2 and blif/4: ISCAS-85, ISCAS-89 and MCNC mapped to 2-input and 4-input LUTs")
    lic = su.licence
    return (f"{title}. Upstream {su.upstream} at {su.commit}. Licence: {lic}.")


def _by_section(rows: list[Row]) -> dict[str, list[Row]]:
    by: dict[str, list[Row]] = defaultdict(list)
    for r in rows:
        by[r.section].append(r)
    return by


def _summary(by: dict[str, list[Row]], total: int) -> list[str]:
    out = ["| suite | rows |", "|---|---|"]
    out += [f"| {sec} | {len(by[sec])} |" for sec in sorted(by)]
    return out + [f"| total | {total} |"]


def _table(rows: list[Row]) -> list[str]:
    out = ["| " + " | ".join(MD_HEAD) + " |", "|" + "---|" * len(MD_HEAD)]
    return out + ["| " + " | ".join(_md_cells(r)) + " |" for r in rows]


def render_md(suites: dict[str, bench.Suite], rows: list[Row], legend: str) -> str:
    by = _by_section(rows)
    out = ["# Mimir benchmark catalogue", "", legend, ""] + _summary(by, len(rows))
    for sec in sorted(by):
        out += ["", f"## {sec}", "", _origin(suites, sec), ""] + _table(by[sec])
    return "\n".join(out) + "\n"


README_START = "<!-- catalogue:start (generated by `mimir bench catalogue`; do not edit) -->"
README_END = "<!-- catalogue:end -->"


def render_readme_section(suites: dict[str, bench.Suite], rows: list[Row], legend: str) -> str:
    """The README block: legend, rows per suite, then each suite table in a <details> fold."""
    by = _by_section(rows)
    out = [README_START, "## Benchmark catalogue", "", legend, ""] + _summary(by, len(rows))
    for sec in sorted(by):
        out += ["", f"<details><summary>{sec} ({len(by[sec])} designs)</summary>", "",
                _origin(suites, sec), ""] + _table(by[sec]) + ["", "</details>"]
    out += ["", "Same table: [docs/benchmarks/catalogue.md](docs/benchmarks/catalogue.md); method: "
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
    return [[r.section, r.design, r.format, r.top, r.loc, ",".join(r.members)]
            + [r.vals.get(k, "-") for k in KEYS] for r in rows]


def fill_counts(rows: list[Row]) -> dict[str, tuple[int, int]]:
    """key -> (rows with a value, rows total); a value that starts with fail or n/a counts as
    filled (it says why); `-` is not filled."""
    return {k: (sum(1 for r in rows if k in r.vals), len(rows)) for k in KEYS}


def generate(idx: Path, out_md: Path, legend: str, readme: Path | None = None) -> list[Row]:
    suites = bench.load_suites(idx)
    designs = bench.load_designs(idx)
    rows = build_rows(designs, load_measures(idx))
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(render_md(suites, rows, legend), encoding="utf-8", newline="\n")
    bench.write_tsv(idx / "catalogue.tsv", TSV_HEAD, render_tsv_rows(rows))
    if readme is not None:
        text = readme.read_text(encoding="utf-8")
        block = render_readme_section(suites, rows, legend)
        readme.write_text(replace_section(text, block), encoding="utf-8", newline="\n")
    return rows
