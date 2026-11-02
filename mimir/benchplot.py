"""Inline-SVG charts for the benchmark report: box plots per suite and a bar chart."""

from __future__ import annotations

import math
from collections.abc import Callable
from html import escape

INK = "#2b2f36"
MUTED = "#6b7280"
GRID = "#e3e5e8"
BOX = "#7d9bbd"
BOX_EDGE = "#3f5f86"
W = 560
LEFT = 150
RIGHT = 20
ROW = 26


def quantile(xs: list[float], q: float) -> float:
    """Linear-interpolation quantile of a sorted list."""
    pos = (len(xs) - 1) * q
    lo = math.floor(pos)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def fmt(v: float) -> str:
    if v != 0 and abs(v) < 0.01:
        return f"{v:.2g}"
    return f"{v:,.0f}" if abs(v) >= 100 else f"{v:.3g}"


def _ticks(lo: float, hi: float, log: bool) -> list[float]:
    if log:
        return [10.0 ** e for e in range(math.floor(math.log10(lo)), math.ceil(math.log10(hi)) + 1)]
    step = 10.0 ** math.floor(math.log10((hi - lo) / 4 or 1))
    for mult in (1, 2, 5, 10):
        if (hi - lo) / (step * mult) <= 6:
            step *= mult
            break
    first = math.ceil(lo / step) * step
    return [round(first + i * step, 10) for i in range(int((hi - first) / step) + 1)]


def boxplot(title: str, unit: str, rows: list[tuple[str, list[float]]]) -> str:
    """One box plot per row (label, values). A log axis when all values are positive and span
    two or more decades. Box = quartiles, bar = median, whiskers = 1.5 IQR, dots = beyond."""
    rows = [(n, sorted(v)) for n, v in rows if v]
    if not rows:
        return ""
    allv = [x for _, v in rows for x in v]
    lo, hi = min(allv), max(allv)
    log = lo > 0 and hi / lo >= 100
    ticks = _ticks(lo, hi, log)
    a, b = (min(lo, ticks[0]), max(hi, ticks[-1]))
    if a == b:
        a, b = a - 1, b + 1

    def x(v: float) -> float:
        t = (math.log10(v) - math.log10(a)) / (math.log10(b) - math.log10(a)) if log \
            else (v - a) / (b - a)
        return LEFT + t * (W - LEFT - RIGHT)

    h = 40 + ROW * len(rows) + 34
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h}" role="img" '
           f'aria-label="{escape(title)}" class="chart">',
           f'<text x="0" y="16" class="ct">{escape(title)}</text>']
    for t in ticks:
        out.append(f'<line x1="{x(t):.1f}" x2="{x(t):.1f}" y1="30" y2="{30 + ROW * len(rows)}" '
                   f'stroke="{GRID}"/><text x="{x(t):.1f}" y="{44 + ROW * len(rows)}" '
                   f'text-anchor="middle" class="tk">{fmt(t)}</text>')
    for i, (name, v) in enumerate(rows):
        cy = 30 + ROW * i + ROW / 2
        out.append(_box(name, v, cy, x))
    axis = f"{unit}, log scale" if log else unit
    out.append(f'<text x="{(LEFT + W - RIGHT) / 2:.0f}" y="{h - 4}" text-anchor="middle" '
               f'class="ax">{escape(axis)}</text></svg>')
    return "\n".join(out)


def _box(name: str, v: list[float], cy: float, x: Callable[[float], float]) -> str:
    q1, med, q3 = quantile(v, 0.25), quantile(v, 0.5), quantile(v, 0.75)
    iqr = q3 - q1
    inside = [e for e in v if q1 - 1.5 * iqr <= e <= q3 + 1.5 * iqr]
    wl, wh = inside[0], inside[-1]
    tip = (f"{name}: n={len(v)}, min {fmt(v[0])}, Q1 {fmt(q1)}, median {fmt(med)}, "
           f"Q3 {fmt(q3)}, max {fmt(v[-1])}")
    parts = [f"<g><title>{escape(tip)}</title>",
             f'<text x="{LEFT - 8}" y="{cy + 4:.1f}" text-anchor="end" class="rl">'
             f'{escape(name)} <tspan fill="{MUTED}">n={len(v)}</tspan></text>',
             f'<line x1="{x(wl):.1f}" x2="{x(wh):.1f}" y1="{cy:.1f}" y2="{cy:.1f}" '
             f'stroke="{BOX_EDGE}"/>']
    bx, bw = x(q1), max(x(q3) - x(q1), 1.5)
    parts.append(f'<rect x="{bx:.1f}" y="{cy - 7:.1f}" width="{bw:.1f}" height="14" '
                 f'fill="{BOX}" stroke="{BOX_EDGE}"/>')
    parts.append(f'<line x1="{x(med):.1f}" x2="{x(med):.1f}" y1="{cy - 7:.1f}" '
                 f'y2="{cy + 7:.1f}" stroke="{INK}" stroke-width="2"/>')
    for e in v:
        if e < wl or e > wh:
            parts.append(f'<circle cx="{x(e):.1f}" cy="{cy:.1f}" r="2" fill="none" '
                         f'stroke="{BOX_EDGE}"/>')
    return "".join(parts) + "</g>"


def barchart(title: str, unit: str, rows: list[tuple[str, int]]) -> str:
    """Horizontal bars (label, count), linear axis from zero."""
    if not rows:
        return ""
    top = max(n for _, n in rows) or 1
    h = 40 + ROW * len(rows) + 20
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W + 120} {h}" role="img" '
           f'aria-label="{escape(title)}" class="chart">',
           f'<text x="0" y="16" class="ct">{escape(title)}</text>']
    scale = (W - LEFT - RIGHT) / top
    for i, (name, n) in enumerate(rows):
        cy = 30 + ROW * i + ROW / 2
        out.append(f'<text x="{LEFT + 90}" y="{cy + 4:.1f}" text-anchor="end" class="rl">'
                   f'{escape(name)}</text><rect x="{LEFT + 98}" y="{cy - 7:.1f}" '
                   f'width="{n * scale:.1f}" height="14" fill="{BOX}"/>'
                   f'<text x="{LEFT + 104 + n * scale:.1f}" y="{cy + 4:.1f}" class="tk">{n}</text>')
    out.append(f'<text x="{LEFT + 98}" y="{h - 4}" class="ax">{escape(unit)}</text></svg>')
    return "\n".join(out)
