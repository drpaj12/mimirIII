"""Fixed-device comparison: place and route each design's existing flow BLIF on ONE fixed grid at
ONE fixed channel width, with ACE2 activity and the VPR power model. No re-synthesis.

usage: fixed_device.py --manifest m.json --width W --grid N --root DIR --out results/fixed-vtr.jsonl
                       [--only DESIGN ...]
manifest.json: {"<design>": "<path of the flow's mnist_top.blif>", ...}. The cycles per image and
the LUT count come from the design's own row in results/{vtr,lut-vtr,bnn-vtr}.jsonl (the same
RTL and BLIF). Designs run smallest first (clb count of that row); a design already in --out is
skipped. Row target: vtr-k6-fixed. Run it inside `ODIN3_HEAVY_OK=1 odin3/tools/heavy-run`.
"""
import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "score"))
import common as C
from vtr_leg import parse_vpr_stdout

RESULTS = Path(__file__).resolve().parent.parent / "results"
SOURCES = ("vtr.jsonl", "lut-vtr.jsonl", "bnn-vtr.jsonl")
TARGET = "vtr-k6-fixed"




def parse_power(report_dir):
    pw = sorted(report_dir.glob("*.power"))
    if not pw:
        return None
    tot = frac = None
    for line in pw[0].read_text().splitlines():
        m = re.match(r"^\s*Total\s+([0-9.e+-]+)\s+([0-9.e+-]+)\s+([\w.+-]+)", line)
        if m:
            tot = float(m.group(1))
            frac = 0.0 if "nan" in m.group(3) else float(m.group(3))
            break
    if tot is None:
        return None
    return {"total_mw": tot * 1e3, "dynamic_mw": tot * frac * 1e3,
            "static_mw": tot * (1 - frac) * 1e3}


def run_one(design, blif, src, a, root):
    out = root / design
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    row = C.new_row(design, TARGET, src.get("tier", "quick"))
    nr = row["null_reason"]
    row["tools"] = {"odin3": src["tools"].get("odin3"), "arch": C.ARCH.name,
                    "vpr": "VTR_ROOT build", "fixed_grid": a.grid, "fixed_width": a.width,
                    "flow_blif": "existing odin3-flow BLIF of results/" + src["_file"]}
    shutil.copy(blif, out / "in.blif")
    t = time.time()
    r = C.capped([C.VTR_ROOT / "build/ace2/ace", "-b", "in.blif", "-c", "clk", "-n",
                  "raw.ace.blif", "-o", "ace.act", "-s", "1"], cwd=out)
    if r.returncode:
        return fail(row, a, "ace2 failed: " + (r.stdout + r.stderr)[-200:])
    r = C.capped([C.VTR_ROOT / "vtr_flow/scripts/restore_multiclock_latch.pl", "in.blif",
                  "raw.ace.blif", "circuit.blif"], cwd=out)
    if r.returncode:
        return fail(row, a, "restore_multiclock_latch failed: " + r.stderr[-200:])
    # explicit stages: with none, this VPR runs the analytical placer, which the auto-grid rows
    # (run_vtr_flow.py: pack, place, route) did not use
    r = C.capped([C.VTR_ROOT / "build/vpr/vpr", C.ARCH, "circuit.blif", "--pack", "--place",
                  "--route", "--analysis", "--device", "auto",
                  "--device_width", str(a.grid), "--route_chan_width", str(a.width),
                  "--power", "--tech_properties", C.TECH, "--activity_file", "ace.act",
                  "--max_router_iterations", "100"], cwd=out, mem=a.mem)
    (out / "vpr_stdout.log").write_text(r.stdout + r.stderr)
    v = parse_vpr_stdout(r.stdout)
    wl = re.search(r"Total wirelength: (\d+)", r.stdout)
    routed = "Circuit successfully routed" in r.stdout
    if r.returncode or not routed or "fmax_mhz" not in v:
        return fail(row, a, f"vpr failed or unroutable at W={a.width} (exit {r.returncode}); "
                    "see vpr_stdout.log")
    cpd, sa = v["crit_path_ns"], src["area"]
    row["area"] = {"luts": sa.get("luts"), "ffs": v.get("ff"), "clbs": v.get("clb"),
                   "adders": v.get("adder"), "dsp_mult36": sa.get("dsp_mult36"),
                   "ram_blocks": sa.get("ram_blocks"), "min_chan_width": None,
                   "wirelength": int(wl.group(1)) if wl else None, "grid": v.get("grid")}
    nr["area.min_chan_width"] = f"not searched: channel width fixed at {a.width}"
    row["speed"] = {"crit_path_ns": cpd, "fmax_mhz": v["fmax_mhz"], "cycles_per_img": None,
                    "latency_us": None, "images_per_s": None}
    ss = src["speed"]
    cyc, ii = ss.get("cycles_per_img"), ss.get("ii_cycles")
    if cyc:
        lat = cyc * cpd / 1000.0
        row["speed"].update(cycles_per_img=cyc, latency_us=lat,
                            images_per_s=1e6 / ((ii or cyc) * cpd / 1000.0))
        if ii:
            row["speed"]["ii_cycles"] = ii
        row["speed"]["note"] = ss.get("note")
    else:
        nr["speed.cycles_per_img"] = "no cycles per image in the design's own row"
    p = parse_power(out)
    if p:
        p["method"] = (f"ACE2 vectorless (-s 1) + VPR --power, PTM_45nm, W={a.width}, "
                       f"fixed grid {a.grid}x{a.grid}")
        if row["speed"].get("latency_us"):
            p["energy_uj_per_img"] = p["total_mw"] * 1e-3 * row["speed"]["latency_us"]
        row["power"] = p
    else:
        nr["power"] = "no power report from VPR"
    row["tools"]["wall_s"] = round(time.time() - t, 1)
    row["notes"].append("RTL accuracy and cycles per image are those of the design's own "
                        "auto-grid row (same RTL, same BLIF)")
    C.append_row(row, a.out)
    return None


def fail(row, a, why):
    for k in ("area", "speed", "power"):
        row["null_reason"][k] = why
    C.append_row(row, a.out)
    return why


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--width", type=int, required=True)
    ap.add_argument("--grid", type=int, required=True)
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--mem", default="5G", help="memory cap of the VPR step")
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    manifest = json.loads(Path(a.manifest).read_text())
    rows = {}
    for name in SOURCES:
        for line in (RESULTS / name).read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                r["_file"] = name
                if r.get("area"):
                    rows[r["design"]] = r
    done = set()
    if Path(a.out).exists():  # keep the successful rows; a failed design is run again
        keep = [x for x in Path(a.out).read_text().splitlines() if x and json.loads(x)["area"]]
        Path(a.out).write_text("".join(x + "\n" for x in keep))
        done = {json.loads(x)["design"] for x in keep}
    todo = sorted((d for d in manifest if d in rows and d not in done
                   and (not a.only or d in a.only)), key=lambda d: rows[d]["area"]["clbs"])
    for d in todo:
        print(f"fixed_device: {d}", flush=True)
        err = run_one(d, Path(manifest[d]), rows[d], a, Path(a.root).resolve())
        if err:
            print(f"fixed_device: {d} FAILED: {err}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
