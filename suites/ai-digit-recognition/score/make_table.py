"""Results tables (markdown) from the results files of the suite.

usage: make_table.py <results_dir>
Reads  rtl.jsonl  (tools/run_i1.py outputs: one JSON line per design x tier),
       vtr.jsonl and lpm.jsonl (score/vtr_leg.py and score/lpm_leg.py rows).
"""
import json
import sys
from pathlib import Path


def rows(path):
    p = Path(path)
    if not p.exists():
        return []
    with open(p) as f:
        return [json.loads(ln) for ln in f if ln.strip()]


def fmt(v, spec="{:,.0f}", dash="n/a"):
    return dash if v is None else spec.format(v)


def accuracy_table(rtl):
    out = ["| design | tier | images | class match | score match | top-1 vs label | cycles / image "
           "| init cycles | simulator | verdict |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(rtl, key=lambda x: (x["design"], x["tier"] != "quick")):
        t = r["result"]
        if not t:
            out.append(f"| {r['design']} | {r['tier']} | - | - | - | - | - | - | {r['sim']} | "
                       f"no result: {r['error']} |")
            continue
        out.append(f"| {r['design']} | {r['tier']} | {t['n']:,} | {t['class_match']:,} | "
                   f"{t['score_match']:,} | {100 * t['top1']:.2f} % | {t['cycles_per_img']:,} | "
                   f"{t['init_cycles']:,} | {r['sim']} | {t['verdict']} |")
    return out


def vtr_table(vtr):
    out = ["| N | LUT | FF | adder | CLB | mult_36 | RAM block | min W | wirelength | Fmax MHz "
           "| crit path ns | power mW | latency ms | images/s | energy mJ/image |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(vtr, key=lambda x: -int(x["design"].rsplit("n", 1)[1])):
        a, s, p = r["area"] or {}, r["speed"] or {}, r["power"] or {}
        n = r["design"].rsplit("n", 1)[1]
        lat = s.get("latency_us")
        en = p.get("energy_uj_per_img")
        out.append(f"| {n} | {fmt(a.get('luts'))} | {fmt(a.get('ffs'))} | {fmt(a.get('adders'))} "
                   f"| {fmt(a.get('clbs'))} | {fmt(a.get('dsp_mult36'))} "
                   f"| {fmt(a.get('ram_blocks'))} | {fmt(a.get('min_chan_width'))} "
                   f"| {fmt(a.get('wirelength'))} | {fmt(s.get('fmax_mhz'), '{:.1f}')} "
                   f"| {fmt(s.get('crit_path_ns'), '{:.2f}')} | {fmt(p.get('total_mw'), '{:.0f}')} "
                   f"| {fmt(lat and lat / 1000, '{:.1f}')} | {fmt(s.get('images_per_s'), '{:.1f}')} "
                   f"| {fmt(en and en / 1000, '{:.2f}')} |")
    return out


def lpm_table(lpm):
    out = ["| N | lpm_mult | lpm_add_sub | lpm_compare | altsyncram | scfifo | netlist bytes "
           "| purity | read-back | Quartus fit / timing / power |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(lpm, key=lambda x: -int(x["design"].rsplit("n", 1)[1])):
        c = r.get("lpm_cells") or {}
        k = r.get("checks") or {}
        n = r["design"].rsplit("n", 1)[1]
        out.append(f"| {n} | {c.get('lpm_mult', 'n/a')} | {c.get('lpm_add_sub', 'n/a')} "
                   f"| {c.get('lpm_compare', 'n/a')} | {c.get('altsyncram', 'n/a')} "
                   f"| {c.get('scfifo', 'n/a')} | {fmt(r.get('netlist_bytes'))} "
                   f"| {k.get('pure', 'n/a')} | {k.get('readback', 'n/a')} | needs laptop Quartus |")
    return out


def main(argv):
    d = Path(argv[0])
    print("## Accuracy and cycles (Verilator, RTL)\n")
    print("\n".join(accuracy_table(rows(d / "rtl.jsonl"))))
    print("\n## VTR k6 target (k6_frac_N10_frac_chain_mem32K_40nm, route + STA + power)\n")
    print("\n".join(vtr_table(rows(d / "vtr.jsonl"))))
    print("\n## Cyclone V target (Odin III LPM netlist, instance counts)\n")
    print("\n".join(lpm_table(rows(d / "lpm.jsonl"))))


if __name__ == "__main__":
    main(sys.argv[1:])
