"""The academic table of the AI digit recognition results (markdown, CSV, LaTeX booktabs) and its
Pareto plots (inline-SVG files, no dependency), written from the store's `aidigit_result` rows.
Spec: docs/specs/2026-11-10-ai-digit-results.md."""

from __future__ import annotations

import csv
import io
import math
from html import escape
from pathlib import Path
from typing import Any

from mimir import aidigitsheet, benchplot
from mimir.schema import AIDIGIT_COLUMNS

Row = dict[str, Any]
REF_W = 100  # the channel width most rows were routed and powered at
NA = "n/a"
DAGGER = "\u2020"

# (header, key, number format, tex header). Formats: i integer, f1/f2/f3 decimals, pct, s text.
VTR_COLS = (
    ("Impl", "impl_id", "s", "Impl"), ("Design", "design", "s", "Design"),
    ("Setting", "setting", "s", ""), ("Top-1 %", "acc_top1", "pct", "Top-1 (\\%)"),
    ("Images", "acc_n", "i", "Images"), ("Grid", "grid", "s", "Grid"),
    ("LUT", "area_lut", "i", "LUT"), ("FF", "area_ff", "i", "FF"), ("CLB", "area_clb", "i", "CLB"),
    ("mult_36", "area_mult36", "i", "mult\\_36"), ("RAM blk", "area_ram_blocks", "i", "RAM"),
    ("min W", "area_min_chan_width", "i", "min $W$"),
    ("CLB use %", "clb_util_pct", "f1", "CLB use (\\%)"),
    ("Fmax MHz", "speed_fmax_mhz", "f1", "Fmax (MHz)"),
    ("Cycles/img", "speed_cycles_per_img", "i", "Cycles/img"),
    ("Latency us", "speed_latency_us", "f1", "Latency ($\\mu$s)"),
    ("Power mW", "power_total_mw", "f1", "Power (mW)"), ("W", "power_channel_width", "w", "$W$"),
    ("Energy uJ/img", "energy_uj_per_img", "f3", "Energy ($\\mu$J/img)"),
)
FIXED_TARGET = "vtr-k6-fixed"
FIXED_COLS = (
    ("Impl", "impl_id", "s", "Impl"), ("Design", "design", "s", "Design"),
    ("Top-1 %", "acc_top1", "pct", "Top-1 (\\%)"), ("Grid", "grid", "s", "Grid"),
    ("W", "power_channel_width", "i", "$W$"), ("CLB", "area_clb", "i", "CLB"),
    ("CLB use %", "clb_util_pct", "f1", "CLB use (\\%)"),
    ("Fmax MHz", "speed_fmax_mhz", "f1", "Fmax (MHz)"),
    ("Wirelength", "area_wirelength", "i", "Wirelength"),
    ("Latency us", "speed_latency_us", "f1", "Latency ($\\mu$s)"),
    ("Power mW", "power_total_mw", "f1", "Power (mW)"),
    ("Static mW", "power_static_mw", "f1", "Static (mW)"),
    ("Energy uJ/img", "energy_uj_per_img", "f3", "Energy ($\\mu$J/img)"),
)
ODIN_COLS = (
    ("Impl", "impl_id", "s", "Impl"), ("Design", "design", "s", "Design"),
    ("2-image tier", "odin", "s", "2 images"), ("Cycles/s", "odin_sim_cycles_per_s", "i", ""),
    ("Wall s", "odin_sim_wall_s", "f1", ""), ("100-image quick tier", "odin_quick", "s", ""),
)
LPM_COLS = (
    ("Impl", "impl_id", "s", "Impl"), ("Design", "design", "s", "Design"),
    ("Setting", "setting", "s", ""), ("Top-1 %", "acc_top1", "pct", "Top-1 (\\%)"),
    ("Cycles/img", "speed_cycles_per_img", "i", "Cycles/img"),
    ("lpm_mult", "lpm_mult", "i", "lpm\\_mult"),
    ("lpm_add_sub", "lpm_add_sub", "i", "lpm\\_add\\_sub"),
    ("lpm_compare", "lpm_compare", "i", "lpm\\_compare"),
    ("altsyncram", "lpm_altsyncram", "i", "altsyncram"), ("scfifo", "lpm_scfifo", "i", "scfifo"),
    ("Netlist bytes", "netlist_bytes", "i", "Netlist (B)"),
)
FOOTNOTES = (
    "Accuracy is top-1 against the MNIST test labels over the images shown (10,000 = full test "
    "set). I1 is the reference LeNet-5, bit-exact: class and all ten scores equal the numpy golden "
    "(docs/GOLDEN.md). I6 and I8 are other models: they match the Python model of the design, "
    "not the golden.",
    "Area, speed and power come from the quick-tier legs (100 images); they do not depend on "
    "the tier. Latency = cycles per image x critical path; the designs are not pipelined across "
    "images, so images/s = 1 / latency. Energy per image = total power x latency.",
    "Power is ACE2 vectorless activity (-s 1) with the VPR power model (PTM 45 nm): a ranking "
    "estimate, not a measurement.",
    f"{DAGGER} Routed and powered at channel width W other than {REF_W}: not same-W comparable "
    f"with the other rows.",
    "Cyclone V (5CSEMA5F31C6) fit, timing and power are parked (Quartus not run; Peter "
    "2026-11-10); that target shows Odin III LPM instance counts only. A type with no instance "
    "counts as 0.",
    "Grid = VPR auto-sized square grid for k6_frac_N10 (10 BLEs per CLB); the largest resource "
    "column (RAM, DSP or CLB) sets the size. min W = minimum routable channel width. CLB use = "
    "CLBs used / CLB tiles of the grid (IO ring, RAM and mult_36 columns excluded).",
    "Fixed device: every design placed and routed from its existing flow BLIF (no re-synthesis) "
    "on one grid at one channel width (the numbers are in the heading of that table), power by "
    "the same ACE2 + VPR model. The whole device leaks whatever the design uses, so static power "
    "and energy per image are those of the full grid; a small design pays for the empty tiles. "
    "CLB use % there is CLBs used / CLB tiles of the fixed grid.",
    "n/a = not measured. The reason for every n/a is in the store (table `aidigit_null`) and in "
    "the last column of TABLE.csv; e.g. nl-A and nl-C: the Odin III `abc` pass exceeds its 4 GiB "
    "budget.",
)


def _num(v: Any, fmt: str) -> str:
    if v is None:
        return NA
    if fmt == "i":
        return f"{int(v):,}"
    if fmt == "pct":
        return f"{float(v) * 100:.2f}"
    if fmt == "w":
        return str(int(v))
    if fmt.startswith("f"):
        return f"{float(v):,.{int(fmt[1:])}f}"
    return str(v)


def _odin_cell(row: Row) -> str:
    st, n = row.get("odin_sim_status"), row.get("odin_sim_n")
    if st is None:
        return "not run"
    if st == "error":
        return "error (cause in TABLE.csv)"
    return f"{st}: class {row['odin_sim_class_match']}/{n}, score {row['odin_sim_score_match']}/{n}"


def _cell(row: Row, key: str, fmt: str) -> str:
    if key == "odin":
        return _odin_cell(row)
    if key == "odin_quick":
        n = row.get("odin_sim_n")
        return "running" if n is not None and n < 100 else (_odin_cell(row) if n else NA)
    if key == "grid":
        w, h = row.get("grid_w"), row.get("grid_h")
        return NA if w is None or h is None else f"{w}x{h}"
    text = _num(row.get(key), fmt)
    if key == "power_channel_width" and row.get(key) not in (None, REF_W):
        return text + DAGGER
    return text


def _rows_for(rows: list[Row], target: str) -> list[Row]:
    return sorted((r for r in rows if r["target"] == target),
                  key=lambda r: (r["impl_id"], r["design"]))


def _md_table(rows: list[Row], cols: tuple[tuple[str, str, str, str], ...]) -> str:
    head = "| " + " | ".join(c[0] for c in cols) + " |"
    rule = "|" + "|".join("---" for _ in cols) + "|"
    body = ["| " + " | ".join(_cell(r, k, f) for _, k, f, _ in cols) + " |" for r in rows]
    return "\n".join([head, rule, *body])


def _tex_cell(row: Row, key: str, fmt: str) -> str:
    text = _cell(row, key, fmt).replace(DAGGER, "$^\\dagger$")
    if fmt == "s" or text == NA:
        return text.replace("_", "\\_") if text != NA else "n/a"
    return text.replace(",", "\\,")


def _tex_table(rows: list[Row], cols: tuple[tuple[str, str, str, str], ...], caption: str,
               label: str) -> str:
    use = [c for c in cols if c[3]]
    spec = "".join("l" if c[2] == "s" else "r" for c in use)
    lines = ["\\begin{table}[t]", "\\centering", "\\small", f"\\begin{{tabular}}{{{spec}}}",
             "\\toprule", " & ".join(c[3] for c in use) + " \\\\", "\\midrule"]
    prev = ""
    for r in rows:
        if prev and r["impl_id"] != prev:
            lines.append("\\midrule")
        prev = r["impl_id"]
        lines.append(" & ".join(_tex_cell(r, k, f) for _, k, f, t in use if t) + " \\\\")
    lines += ["\\bottomrule", "\\end{tabular}", f"\\caption{{{caption}}}",
              f"\\label{{{label}}}", "\\end{table}"]
    return "\n".join(lines)


def render_tex(rows: list[Row]) -> str:
    vtr = _tex_table(
        _rows_for(rows, "vtr-k6"), VTR_COLS,
        "AI digit recognition on the VTR k6 architecture (route, STA, ACE2 vectorless + VPR power "
        f"estimate; $^\\dagger$ channel width $W \\ne {REF_W}$, not same-$W$ comparable).",
        "tab:aidigit-vtr")
    lpm = _tex_table(
        _rows_for(rows, "cyclonev-lpm"), LPM_COLS,
        "AI digit recognition: Odin III LPM netlist instance counts for Cyclone V "
        "(Quartus fit, timing and power parked).", "tab:aidigit-lpm")
    fixed_rows = _rows_for(rows, FIXED_TARGET)
    if fixed_rows:
        lpm += "\n\n" + _tex_table(
            fixed_rows, FIXED_COLS,
            "AI digit recognition on one fixed device: same grid and channel width for every "
            "design, placed and routed from the flow BLIF of the table above.", "tab:aidigit-fixed")
    head = "% Generated by `mimir aidigit-table`; needs \\usepackage{booktabs}.\n"
    return head + vtr + "\n\n" + lpm + "\n"


def render_csv(rows: list[Row], nulls: dict[tuple[str, str, str], str]) -> str:
    """One line per row; the last column `null_reasons` lists "field: reason" for each NULL."""
    names = [n for n, _ in AIDIGIT_COLUMNS]
    buf = io.StringIO()
    out = csv.writer(buf, lineterminator="\n")
    out.writerow([*names, "null_reasons"])
    for r in sorted(rows, key=lambda r: (r["impl_id"], r["design"], r["target"])):
        why = "; ".join(f"{f}: {w}" for (d, t, f), w in sorted(nulls.items())
                        if d == r["design"] and t == r["target"])
        out.writerow(["" if r.get(n) is None else (repr(r[n]) if isinstance(r[n], float) else r[n])
                      for n in names] + [why])
    return buf.getvalue()


def _fixed_heading(fixed: list[Row]) -> str:
    grids = sorted({_cell(r, "grid", "s") for r in fixed} - {NA})
    widths = sorted({r["power_channel_width"] for r in fixed if r.get("power_channel_width")})
    return f"grid {', '.join(grids)}, channel width W = {', '.join(str(w) for w in widths)}"


def render_md(rows: list[Row], plots: list[tuple[str, str]], nulls: dict[tuple[str, str, str], str]
              ) -> str:
    counts = f"{len(rows)} rows from {len({r['design'] for r in rows})} designs"
    out = ["# Results table: AI digit recognition", "",
           "Generated by `mimir aidigit-table` from the Mimir store (table `aidigit_result`, "
           f"schema 10); {counts}. Do not edit by hand; regenerate (see `README.md`, section "
           "Results table).", "", "## VTR k6 target", "",
           _md_table(_rows_for(rows, "vtr-k6"), VTR_COLS), "",
           "## Cyclone V target (Odin III LPM netlist)", "",
           _md_table(_rows_for(rows, "cyclonev-lpm"), LPM_COLS), ""]
    fixed = _rows_for(rows, FIXED_TARGET)
    if fixed:
        out += [f"## VTR k6 fixed device ({_fixed_heading(fixed)})", "",
                _md_table(fixed, FIXED_COLS), ""]
    odin = _rows_for(rows, "vtr-k6") or _rows_for(rows, "rtl")
    if any(r.get("odin_sim_status") for r in odin):
        out += ["## Odin III v1.6.1 simulation (`sim_tb` on the RTL)", "",
                _md_table(odin, ODIN_COLS), ""]
    out += ["## Notes", ""]
    out += [f"{i}. {t}" for i, t in enumerate(FOOTNOTES, 1)]
    out += ["", "## Pareto plots (VTR k6, front marked with filled dots)", ""]
    out += [f"![{title}]({path})\n" for title, path in plots]
    missing = sorted({(d, t) for d, t, f in nulls if t == "vtr-k6" and f == "area_lut"})
    if missing:
        out.append("No VTR point (no area, speed or power): " +
                   ", ".join(d for d, _ in missing) + ".")
    return "\n".join(out).rstrip("\n") + "\n"


# ---- Pareto plots ------------------------------------------------------------------------------

PALETTE = {"I1": "#3f5f86", "I2": "#2a8a8a", "I3": "#7a4fa0", "I4": "#a03f5a", "I6": "#b5651d",
           "I7": "#8a7a1f", "I8": "#4a8a5a"}
PW, PH, ML, MR, MT, MB = 640, 420, 64, 150, 36, 48


def pareto_front(points: list[tuple[float, float, str]]) -> set[str]:
    """Names on the front: no other point has accuracy >= and cost <= with one strict."""
    front = set()
    for x, y, name in points:
        beaten = any(x2 <= x and y2 >= y and (x2 < x or y2 > y) for x2, y2, _ in points)
        if not beaten:
            front.add(name)
    return front


def _scatter(title: str, xlabel: str, pts: list[tuple[float, float, str, str]]) -> str:
    front = pareto_front([(x, y, n) for x, y, n, _ in pts])
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    lx0, lx1 = math.floor(math.log10(min(xs))), math.ceil(math.log10(max(xs)))
    if lx0 == lx1:
        lx1 += 1
    y0 = math.floor(min(ys) - 1)
    y1 = min(100.0, math.ceil(max(ys) + 1))

    def px(v: float) -> float:
        return ML + (math.log10(v) - lx0) / (lx1 - lx0) * (PW - ML - MR)

    def py(v: float) -> float:
        return MT + (y1 - v) / (y1 - y0) * (PH - MT - MB)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {PW} {PH}" role="img" '
           f'aria-label="{escape(title)}" font-family="sans-serif" font-size="11">',
           f'<rect width="{PW}" height="{PH}" fill="#ffffff"/>',
           f'<text x="{ML}" y="18" font-size="13" fill="{benchplot.INK}">{escape(title)}</text>']
    for e in range(lx0, lx1 + 1):
        out.append(f'<line x1="{px(10.0 ** e):.1f}" x2="{px(10.0 ** e):.1f}" y1="{MT}" '
                   f'y2="{PH - MB}" stroke="{benchplot.GRID}"/><text x="{px(10.0 ** e):.1f}" '
                   f'y="{PH - MB + 14}" text-anchor="middle" fill="{benchplot.MUTED}">'
                   f'{benchplot.fmt(10.0 ** e)}</text>')
    for v in range(int(y0), int(y1) + 1, max(1, int((y1 - y0) // 5))):
        out.append(f'<line x1="{ML}" x2="{PW - MR}" y1="{py(v):.1f}" y2="{py(v):.1f}" '
                   f'stroke="{benchplot.GRID}"/><text x="{ML - 6}" y="{py(v) + 4:.1f}" '
                   f'text-anchor="end" fill="{benchplot.MUTED}">{v}</text>')
    out.append(f'<text x="{(ML + PW - MR) / 2:.0f}" y="{PH - 8}" text-anchor="middle" '
               f'fill="{benchplot.INK}">{escape(xlabel)} (log scale)</text>')
    out.append(f'<text transform="translate(14 {(MT + PH - MB) / 2:.0f}) rotate(-90)" '
               f'text-anchor="middle" fill="{benchplot.INK}">top-1 accuracy (%)</text>')
    line = sorted((p for p in pts if p[2] in front), key=lambda p: p[0])
    if len(line) > 1:
        path = " ".join(f"{px(x):.1f},{py(y):.1f}" for x, y, _, _ in line)
        out.append(f'<polyline points="{path}" fill="none" stroke="{benchplot.MUTED}" '
                   f'stroke-dasharray="4 3"/>')
    for x, y, name, impl in sorted(pts, key=lambda p: p[2]):
        c = PALETTE.get(impl, benchplot.INK)
        fill = c if name in front else "#ffffff"
        out.append(f'<g><title>{escape(name)}: {benchplot.fmt(x)}, {y:.2f} %</title>'
                   f'<circle cx="{px(x):.1f}" cy="{py(y):.1f}" r="5" fill="{fill}" stroke="{c}" '
                   f'stroke-width="1.5"/><text x="{px(x) + 7:.1f}" y="{py(y) - 6:.1f}" '
                   f'fill="{benchplot.INK}">{escape(name)}</text></g>')
    for i, (impl, c) in enumerate(PALETTE.items()):
        if any(p[3] == impl for p in pts):
            out.append(f'<circle cx="{PW - MR + 14}" cy="{MT + 6 + 16 * i}" r="5" fill="{c}"/>'
                       f'<text x="{PW - MR + 24}" y="{MT + 10 + 16 * i}" fill="{benchplot.INK}">'
                       f'{impl}</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


PLOTS = (  # (file, title, x label, column, target)
    ("pareto-accuracy-energy.svg", "Accuracy against energy per image (VTR k6)",
     "energy per image (uJ)", "energy_uj_per_img", "vtr-k6"),
    ("pareto-accuracy-lut.svg", "Accuracy against LUT count (VTR k6)", "LUTs", "area_lut",
     "vtr-k6"),
    ("pareto-accuracy-latency.svg", "Accuracy against latency per image (VTR k6)",
     "latency per image (us)", "speed_latency_us", "vtr-k6"),
    ("pareto-fixed-accuracy-energy.svg", "Accuracy against energy per image (fixed device)",
     "energy per image (uJ)", "energy_uj_per_img", FIXED_TARGET),
    ("pareto-fixed-accuracy-latency.svg", "Accuracy against latency per image (fixed device)",
     "latency per image (us)", "speed_latency_us", FIXED_TARGET),
)


def render_plots(rows: list[Row]) -> list[tuple[str, str, str]]:
    """(file name, title, svg) for each plot that has at least one point."""
    out = []
    for fname, title, xlabel, key, target in PLOTS:
        pts = [(float(r[key]), float(r["acc_top1"]) * 100, r["design"], r["impl_id"])
               for r in _rows_for(rows, target)
               if r.get(key) is not None and r.get("acc_top1") is not None and r[key] > 0]
        if pts:
            out.append((fname, title, _scatter(title, xlabel, pts)))
    return out


def write_all(rows: list[Row], nulls: dict[tuple[str, str, str], str], out_dir: Path) -> list[Path]:
    """Write TABLE.md, TABLE.csv, TABLE.tex and plots/*.svg under out_dir; return the paths."""
    plots = render_plots(rows)
    (out_dir / "plots").mkdir(parents=True, exist_ok=True)
    (out_dir / "datasheets").mkdir(parents=True, exist_ok=True)
    files = {
        out_dir / "TABLE.md": render_md(rows, [(t, f"plots/{f}") for f, t, _ in plots], nulls),
        out_dir / "TABLE.csv": render_csv(rows, nulls),
        out_dir / "TABLE.tex": render_tex(rows),
        **{out_dir / "plots" / f: svg for f, _, svg in plots},
        **aidigitsheet.write_all(rows, nulls, out_dir),
    }
    for path, text in files.items():
        path.write_text(text, encoding="utf-8", newline="\n")
    return sorted(files)
