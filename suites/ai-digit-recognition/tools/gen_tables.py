"""Markdown results tables for the generated designs (I3, I4).

usage: gen_tables.py <rtl.jsonl ...> -- <vtr.jsonl> <lpm.jsonl>
rtl.jsonl: output lines of tools/run_gen.py; vtr/lpm: rows of score/vtr_leg.py, score/lpm_leg.py.
"""
import json
import sys


def load(path):
    with open(path) as f:
        return [json.loads(ln) for ln in f if ln.strip()]


def f(v, s="{:,.0f}"):
    return "n/a" if v is None else s.format(v)


def acc_table(rtl):
    out = ["| design | tier | testbench | n | class match | score match | top-1 "
           "| cycles/image | II |", "|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(rtl, key=lambda x: (x["design"], x["tier"] != "quick")):
        for key, label in (("result", "common (serial)"), ("pipe", "pipelined")):
            t = r[key]
            if t:
                out.append(f"| {r['design']} | {r['tier']} | {label} | {t['n']:,} | "
                           f"{t['class_match']:,} | {t['score_match']:,} | "
                           f"{100 * t['top1']:.2f} % | {t['cycles_per_img']:,} | "
                           f"{f(t.get('ii_cycles'))} |")
    return out


def vtr_table(vtr):
    out = ["| design | LUT | FF | adder | CLB | mult_36 | RAM blk | min W | wirelength "
           "| Fmax MHz | latency us | II cycles | images/s (pipelined) | power mW | uJ/image |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(vtr, key=lambda x: x["design"]):
        a, s, p = r["area"] or {}, r["speed"] or {}, r["power"] or {}
        cells = [r["design"], f(a.get("luts")), f(a.get("ffs")), f(a.get("adders")),
                 f(a.get("clbs")), f(a.get("dsp_mult36")), f(a.get("ram_blocks")),
                 f(a.get("min_chan_width")), f(a.get("wirelength")),
                 f(s.get("fmax_mhz"), "{:.1f}"), f(s.get("latency_us"), "{:.1f}"),
                 f(s.get("ii_cycles")), f(s.get("images_per_s")),
                 f(p.get("total_mw"), "{:.1f}"), f(p.get("energy_uj_per_img"), "{:.2f}")]
        out.append("| " + " | ".join(cells) + " |")
    return out


def lpm_table(lpm):
    out = ["| design | lpm_add_sub | lpm_mult | lpm_compare | altsyncram | netlist bytes "
           "| pure | lint | readback |", "|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(lpm, key=lambda x: x["design"]):
        c, k = r.get("lpm_cells") or {}, r.get("checks") or {}
        cells = [r["design"], f(c.get("lpm_add_sub", 0)), f(c.get("lpm_mult", 0)),
                 f(c.get("lpm_compare", 0)), f(c.get("altsyncram", 0)),
                 f(r.get("netlist_bytes", 0)), k.get("pure"), k.get("lint"), k.get("readback")]
        out.append("| " + " | ".join(str(x) for x in cells) + " |")
    return out


if __name__ == "__main__":
    a = sys.argv[1:]
    i = a.index("--")
    rtl = [r for p in a[:i] for r in load(p)]
    tables = [acc_table(rtl), vtr_table(load(a[i + 1])), lpm_table(load(a[i + 2]))]
    print("\n\n".join("\n".join(t) for t in tables))
