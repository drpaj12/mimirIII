"""HTML of the benchmark report (see benchreport.py): inline CSS, SVG and a little JS."""

from __future__ import annotations

import json
from collections import defaultdict
from html import escape

from mimir.benchplot import barchart, boxplot
from mimir.benchreport import METRICS, Report, Row

CSS = """
body{font:15px/1.5 system-ui,sans-serif;color:#2b2f36;background:#fff;margin:0 auto;
max-width:1100px;padding:24px}
h1{font-size:24px;margin:0 0 4px}
h2{font-size:18px;margin:32px 0 8px;border-bottom:1px solid #e3e5e8}
p.lead{color:#555;margin:4px 0}code{background:#f2f3f5;padding:1px 4px;border-radius:3px}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{padding:4px 8px;border-bottom:1px solid #e3e5e8;text-align:left;vertical-align:top}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
th{background:#f6f7f8;position:sticky;top:0;cursor:pointer;white-space:nowrap}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(520px,1fr));gap:12px}
svg.chart{width:100%;height:auto}.ct{font:600 13px system-ui;fill:#2b2f36}
.tk,.ax{font:11px system-ui;fill:#6b7280}.rl{font:12px system-ui;fill:#2b2f36}
.small{color:#6b7280;font-size:12px}.tablebox{max-height:560px;overflow:auto}
input,select{font:inherit;padding:3px 6px;margin-right:8px}
"""

JS = """
const D=JSON.parse(document.getElementById('data').textContent);
const C=D.cols;let sortKey=null,asc=true;
const q=document.getElementById('q'),sel=document.getElementById('suite');
const head=document.getElementById('head'),body=document.getElementById('body'),
cnt=document.getElementById('cnt');
C.forEach((c,i)=>{const th=document.createElement('th');th.textContent=c[1];
if(c[2])th.className='n';th.onclick=()=>{asc=sortKey===i?!asc:true;sortKey=i;draw()};
head.appendChild(th)});
D.suites.forEach(s=>{const o=document.createElement('option');o.value=s;o.textContent=s;
sel.appendChild(o)});
function draw(){const t=q.value.toLowerCase(),s=sel.value;
let r=D.rows.filter(x=>(!s||x[0]===s)&&(!t||x.join(' ').toLowerCase().includes(t)));
if(sortKey!==null)r.sort((a,b)=>{const u=a[sortKey],v=b[sortKey];
const m=(u===null)-(v===null);if(m)return m;
return (typeof u==='number'?u-v:String(u).localeCompare(String(v)))*(asc?1:-1)});
body.innerHTML='';r.forEach(x=>{const tr=document.createElement('tr');
x.forEach((v,i)=>{const td=document.createElement('td');if(C[i][2])td.className='n';
td.textContent=v===null?'':(typeof v==='number'?v.toLocaleString('en-US',
{maximumFractionDigits:3}):v);tr.appendChild(td)});body.appendChild(tr)});
cnt.textContent=r.length+' of '+D.rows.length+' designs'}
q.oninput=draw;sel.onchange=draw;draw();
"""

COLS = [("suite", "suite", False), ("design", "design", False), ("format", "format", False),
        ("top", "top", False), ("bytes", "bytes", True), ("lines", "lines", True),
        ("join", "store join", False), ("flows", "netlist flows", False)] + [
    (c, lab, True) for c, lab, _ in METRICS.values()]


def _size(n: int) -> str:
    for unit, k in (("MB", 1e6), ("kB", 1e3)):
        if n >= k:
            return f"{n / k:.1f} {unit}"
    return f"{n} B"


def _by_suite(rep: Report) -> dict[str, list[Row]]:
    out: dict[str, list[Row]] = defaultdict(list)
    for r in rep.rows:
        out[r.suite].append(r)
    return out


def _suite_table(rep: Report) -> str:
    by = _by_suite(rep)
    head = ("<tr><th>suite</th><th>what it is, where it came from</th><th>formats</th>"
            "<th class=n>designs</th><th class=n>total size</th><th>licence rule</th>"
            "<th class=n>in store</th></tr>")
    out = []
    for s in rep.suites:
        rows = by[s.id]
        fmts = ", ".join(f"{k} ({v})" for k, v in sorted(
            {r.format: sum(x.format == r.format for x in rows) for r in rows}.items()))
        rules = sorted({r.licence_rule for r in rows if r.licence_rule != "-"})
        lic = escape(s.licence) + (f"<br><span class=small>per-design rules: "
                                   f"{escape(', '.join(rules))}</span>" if rules else "")
        note = f"<br><span class=small>{escape(s.note)}</span>" if s.note else ""
        src = (f"{escape(s.title)}<br><span class=small>{escape(s.upstream)} at "
               f"<code>{escape(s.commit[:10])}</code>; hosting: {escape(s.hosting)}. "
               f"{escape(s.obtained)}</span>{note}")
        joined = sum(r.join != "-" for r in rows)
        out.append(f"<tr><td><b>{escape(s.id)}</b></td><td>{src}</td><td>{escape(fmts)}</td>"
                   f"<td class=n>{len(rows)}</td><td class=n>{_size(sum(r.bytes for r in rows))}"
                   f"</td><td>{lic}</td><td class=n>{joined}</td></tr>")
    return f"<table>{head}{''.join(out)}</table>"


def _charts(rep: Report) -> str:
    by = _by_suite(rep)
    ids = [s.id for s in rep.suites]
    charts = [boxplot("Source size, bytes", "bytes per design",
                      [(i, [float(r.bytes) for r in by[i]]) for i in ids]),
              boxplot("Source size, lines", "lines per design",
                      [(i, [float(r.lines) for r in by[i]]) for i in ids])]
    for key, (_, label, unit) in METRICS.items():
        rows = []
        for i in ids:
            vals = [r.metrics[key] for r in by[i] if key in r.metrics]
            if key != "rent.p":
                vals = [v for v in vals if v > 0]
            rows.append((i, vals))
        charts.append(boxplot(f"{label} (store, LUT level)", unit, rows))
    return '<div class="grid">' + "".join(c for c in charts if c) + "</div>"


def _flows(rep: Report) -> str:
    rows = sorted(rep.flows.items())
    chart = barchart("Netlists per flow", "netlists", [(f, n) for f, n in rows])
    trs = "".join(
        f"<tr><td>{escape(f)}</td><td>{escape(rep.flow_info[f].tool)} "
        f"{escape(rep.flow_info[f].tool_version)}</td><td>{escape(rep.flow_info[f].arch)}</td>"
        f"<td class=n>{rep.flow_info[f].lut_k}</td><td class=n>{n}</td></tr>" for f, n in rows)
    return (chart + "<table><tr><th>flow</th><th>tool</th><th>architecture</th><th class=n>K</th>"
            f"<th class=n>netlists</th></tr>{trs}</table>")


def _data(rep: Report) -> str:
    cols = [[c, lab, num] for c, lab, num in COLS]
    keys = list(METRICS)
    rows = [[r.suite, r.design, r.format, r.top, r.bytes, r.lines, r.join,
             ", ".join(r.flows) or "-", *[r.metrics.get(k) for k in keys]] for r in rep.rows]
    blob = json.dumps({"cols": cols, "suites": [s.id for s in rep.suites], "rows": rows},
                      separators=(",", ":"))
    return blob.replace("</", "<\\/")


def render(rep: Report) -> str:
    j = rep.joins
    matched = sum(v for k, v in j.items() if k != "-")
    n_net = sum(rep.flows.values())
    join_txt = (f"{matched} of {len(rep.rows)} registry designs match a store design "
                f"(by slug {j['slug']}, by source hash {j['hash']}, by source and name "
                f"{j['name']}); {j['-']} have no store record." if rep.store != "none"
                else "No store given: store metrics are not shown.")
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Mimir III benchmark overview</title><style>{CSS}</style></head><body>
<h1>Mimir III: benchmark overview</h1>
<p class="lead">Mimir III is the circuit knowledge base of Yggdrasil III: a registry of benchmark
suites, their compiled netlists, and a store of measured structure, Rent exponent, timing and QoR.
This page shows the registry and the main store metrics.</p>
<p class="lead">Generated {escape(rep.date)}. Registry commit <code>{escape(rep.commit)}</code>.
{len(rep.suites)} suites, {len(rep.rows)} designs, {n_net} public netlists
({rep.withheld_netlists} more netlist rows are left out because their blob is not public).
Store: {escape(rep.store)}. {escape(join_txt)}</p>
<p class="lead">Fetch a design: <code>mimir bench fetch SUITE:DESIGN --kind source --out FILE</code>
for the source, or <code>mimir bench fetch SUITE:DESIGN@FLOW --out FILE</code> for a netlist;
<code>mimir bench show SUITE:DESIGN</code> lists its flows, licence and hashes.</p>
<h2>1. Suites</h2>{_suite_table(rep)}
<h2>2. Distributions per suite</h2>
<p class="small">Box = quartiles, bar = median, whiskers = 1.5 IQR, circles = beyond. Log axis when
values span two decades. Store metrics are the median over seeds at LUT level, for the designs that
match the store; a suite with no match has no row. Zero values are not drawn on log axes.
Source size is the file size of the registered source (BLIF index suites: the BLIF).</p>
{_charts(rep)}
<h2>3. All designs</h2>
<p><input id="q" placeholder="filter text"><select id="suite"><option value="">all suites</option>
</select><span id="cnt" class="small"></span></p>
<div class="tablebox"><table><thead><tr id="head"></tr></thead><tbody id="body"></tbody></table>
</div>
<h2>4. Netlists per flow</h2>{_flows(rep)}
<script id="data" type="application/json">{_data(rep)}</script>
<script>{JS}</script></body></html>
"""
