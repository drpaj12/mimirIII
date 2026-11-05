"""The catalogue as one self-contained HTML page: a single wide table with a sticky header row and
first column, a scrollbar above the table that follows the one below, sortable columns and a filter
box. No network, no external files (inline CSS and JS)."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mimir.benchcat import Row

CSS = """
body{font:12px/1.3 system-ui,sans-serif;margin:8px;color:#222}
#bar{margin:4px 0}
#top,#wrap{overflow-x:auto}
#top{height:16px;overflow-y:hidden}
#wrap{max-height:80vh;overflow-y:auto;border:1px solid #bbb}
table{border-collapse:separate;border-spacing:0;white-space:nowrap}
th,td{vertical-align:top;padding:2px 6px;border-bottom:1px solid #ddd;border-right:1px solid #eee}
th{position:sticky;top:0;background:#eef;cursor:pointer;z-index:2;user-select:none}
td:first-child,th:first-child{position:sticky;left:0;background:#fff;z-index:1}
th:first-child{background:#eef;z-index:3}
tr:hover td{background:#fffbe0}
td.num{text-align:right}
td.txt{white-space:normal;min-width:18em;max-width:50em}
"""

JS = """
const t=document.getElementById('t'),wrap=document.getElementById('wrap');
const top_=document.getElementById('top'),body=t.tBodies[0];
document.getElementById('in').style.width=t.scrollWidth+'px';
top_.onscroll=()=>{wrap.scrollLeft=top_.scrollLeft};
wrap.onscroll=()=>{top_.scrollLeft=wrap.scrollLeft};
function val(td){const x=td.textContent.trim(),n=parseFloat(x);return isNaN(n)?x.toLowerCase():n}
const dir={};
t.tHead.rows[0].querySelectorAll('th').forEach((th,i)=>th.onclick=()=>{
 dir[i]=!dir[i];const rows=[...body.rows];
 rows.sort((a,b)=>{const x=val(a.cells[i]),y=val(b.cells[i]);
  const r=(typeof x===typeof y)?(x<y?-1:x>y?1:0):(typeof x==='number'?-1:1);
  return dir[i]?r:-r});
 rows.forEach(r=>body.appendChild(r))});
document.getElementById('q').oninput=e=>{
 const q=e.target.value.toLowerCase();let n=0;
 for(const r of body.rows){
  const show=r.textContent.toLowerCase().includes(q);
  r.style.display=show?'':'none';if(show)n++}
 document.getElementById('n').textContent=n+' rows'};
"""


TEXT_COLS = {"desc", "note", "status", "prov", "tb"}


def _td(col: str, value: str, num: bool) -> str:
    cls = ' class="num"' if num else ' class="txt"' if col in TEXT_COLS else ""
    if col == "link" and value.startswith("http"):
        v = escape(value, quote=True)
        return f'<td{cls}><a href="{v}">{v}</a></td>'
    return f"<td{cls}>{escape(value)}</td>"


def render(rows: list[Row]) -> str:
    from mimir.benchcat import LABELS, fields

    cols = ["design", "tier"] + [c for c in LABELS if c != "design"]
    head = "".join(f"<th>{escape('tier' if c == 'tier' else LABELS[c])}</th>" for c in cols)
    body: list[str] = []
    for r in rows:
        f = fields(r, html=True)
        f["tier"] = f"T{r.tier}"
        cells = []
        for c in cols:
            v = f[c]
            try:
                float(v.split("/")[0])
                num = c not in ("design", "tier")
            except ValueError:
                num = False
            cells.append(_td(c, v, num))
        body.append("<tr>" + "".join(cells) + "</tr>")
    return (
        '<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8">'
        "<title>Mimir benchmark catalogue</title>"
        f"<style>{CSS}</style></head><body>\n"
        "<h1>Mimir benchmark catalogue</h1>\n"
        '<div id="bar"><input id="q" placeholder="filter rows" size="30"> '
        f'<span id="n">{len(rows)} rows</span> &middot; click a header to sort &middot; '
        "<a href=\"https://github.com/drpaj12/mimirIII/blob/main/docs/benchmarks/"
        'catalogue-method.md">method</a></div>\n'
        '<div id="top"><div id="in" style="height:1px"></div></div>\n'
        f'<div id="wrap"><table id="t"><thead><tr>{head}</tr></thead>\n<tbody>\n'
        + "\n".join(body)
        + f"\n</tbody></table></div>\n<script>{JS}</script></body></html>\n"
    )


def write(path: Path, rows: list[Row]) -> None:
    path.write_text(render(rows), encoding="utf-8", newline="\n")
