"""Markdown tables for the LUT-network designs (I6 NeuraLUT, I8 TreeLUT).

usage: lut_table.py <results_dir>
Reads vtr.jsonl and lpm.jsonl (score/vtr_leg.py, score/lpm_leg.py rows, written by
tools/lut_legs.py); designs are named nl-<setting> (I6) and tl-<setting> (I8).
"""

import json
import sys
from pathlib import Path


def rows(path):
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(ln) for ln in p.read_text().splitlines() if ln.strip()]


def fmt(v, spec="{:,.0f}"):
    return "n/a" if v is None else spec.format(v)


def acc_line(r):
    a = r.get("accuracy") or {}
    full = a.get("rtl_verilator_full") or {}
    quick = a.get("rtl_verilator") or {}
    net = a.get("netlist_odin_sim") or {}
    n = full.get("n") or 1
    return (
        f"| {r['design']} | {fmt(full.get('label_correct'))} / {n:,} "
        f"({100 * full.get('label_correct', 0) / n:.2f} %) | {fmt(full.get('class_match'))} "
        f"| {fmt(full.get('score_match'))} "
        f"| {quick.get('class_match', 'n/a')} / {quick.get('n', 'n/a')} "
        f"| {net.get('class_match', 'n/a')} / {net.get('n', 'n/a')} "
        f"| {fmt(full.get('cycles_per_img'))} |"
    )


def vtr_line(r):
    a, s, p = r["area"] or {}, r["speed"] or {}, r["power"] or {}
    lat = s.get("latency_us")
    return (
        f"| {r['design']} | {fmt(a.get('luts'))} | {fmt(a.get('ffs'))} | {fmt(a.get('adders'))} "
        f"| {fmt(a.get('clbs'))} | {fmt(a.get('min_chan_width'))} | {fmt(a.get('wirelength'))} "
        f"| {fmt(s.get('fmax_mhz'), '{:.1f}')} | {fmt(s.get('crit_path_ns'), '{:.2f}')} "
        f"| {fmt(lat, '{:.1f}')} | {fmt(p.get('total_mw'), '{:.1f}')} "
        f"| {fmt(p.get('energy_uj_per_img'), '{:.3f}')} |"
    )


def lpm_line(r):
    c = r.get("lpm_cells") or {}
    k = r.get("checks") or {}
    return (
        f"| {r['design']} | {c.get('lpm_add_sub', 0)} | {c.get('lpm_compare', 0)} "
        f"| {c.get('lpm_mult', 0)} | {fmt(r.get('netlist_bytes'))} | {k.get('pure', 'n/a')} "
        f"| {k.get('readback', 'n/a')} |"
    )


def main(argv):
    d = Path(argv[0])
    vtr = sorted(rows(d / "vtr.jsonl"), key=lambda r: r["design"])
    lpm = sorted(rows(d / "lpm.jsonl"), key=lambda r: r["design"])
    print("## Accuracy (Verilator RTL; class and score match the Python model of each design)\n")
    print(
        "| design | top-1 vs label (10,000) | class match (10,000) | score match (10,000) "
        "| class match quick | Odin III netlist sim quick | cycles / image |"
    )
    print("|---|---|---|---|---|---|---|")
    print("\n".join(acc_line(r) for r in vtr))
    print("\n## VTR k6 target (route, STA, ACE2 + VPR power)\n")
    print(
        "| design | LUT | FF | adder | CLB | min W | wirelength | Fmax MHz | crit path ns "
        "| latency us | power mW | energy uJ / image |"
    )
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    print("\n".join(vtr_line(r) for r in vtr))
    print("\n## Cyclone V target (Odin III LPM netlist, instance counts)\n")
    print("| design | lpm_add_sub | lpm_compare | lpm_mult | netlist bytes | purity | read-back |")
    print("|---|---|---|---|---|---|---|")
    print("\n".join(lpm_line(r) for r in lpm))


if __name__ == "__main__":
    main(sys.argv[1:])
