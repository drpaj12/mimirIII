"""VTR leg: odin3-flow --target vtr (k6_frac_N10_frac_chain_mem32K_40nm), VPR route + STA,
power by ACE2 activity + VPR power model; accuracy from the testbench on RTL and netlist.

usage: vtr_leg.py --design NAME --src a.v [b.v ...] --vec DIR --work DIR --out results.jsonl
                  [--tier quick|full] [--netlist-sim | --no-netlist-sim] [-I DIR] [-D X=Y]
Exit 0 when a row was written (even with null fields); 1 on usage error.
"""
import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C


def parse_vpr_stdout(text):
    d = {}
    m = re.search(r"Final critical path delay \(least slack\): ([\d.]+) ns, Fmax: ([\d.]+) MHz", text)
    if m:
        d["crit_path_ns"], d["fmax_mhz"] = float(m.group(1)), float(m.group(2))
    for key, pat in (("ff", r"\.latch\s*:\s*(\d+)"), ("adder", r"^\s*adder\s*:\s*(\d+)"),
                     ("fle", r"^\s*fle\s*:\s*(\d+)"), ("clb", r"^\s*clb\s*:\s*(\d+)")):
        m = re.search(pat, text, re.M)
        if m:
            d[key] = int(m.group(1))
    m = re.search(r"FPGA sized to (\d+) x (\d+)", text)
    if m:
        d["grid"] = [int(m.group(1)), int(m.group(2))]
    return d


def power_flow(blif, clock, out):
    """ACE2 vectorless activity, then VPR --power at fixed W=100 (as Wyrd Bifrost)."""
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy(blif, out / "in.blif")
    ace = VTR_ACE = C.VTR_ROOT / "build/ace2/ace"
    r = C.capped([ace, "-b", "in.blif", "-c", clock, "-n", "raw.ace.blif", "-o", "ace.act", "-s", "1"],
                 cwd=out)
    if r.returncode:
        return None, "ace2 failed: " + (r.stdout + r.stderr)[-200:]
    r = C.capped([C.VTR_ROOT / "vtr_flow/scripts/restore_multiclock_latch.pl", "in.blif",
                  "raw.ace.blif", "circuit.blif"], cwd=out)
    if r.returncode:
        return None, "restore_multiclock_latch failed: " + r.stderr[-200:]
    r = C.capped([C.VTR_ROOT / "build/vpr/vpr", C.ARCH, "circuit.blif", "--route_chan_width", "100",
                  "--power", "--tech_properties", C.TECH, "--activity_file", "ace.act"], cwd=out)
    (out / "vpr.log").write_text(r.stdout + r.stderr)
    pw = sorted(out.glob("*.power"))
    if r.returncode or not pw:
        return None, "vpr --power failed (see power/vpr.log)"
    rows = {}
    for line in pw[0].read_text().splitlines():
        m = re.match(r"^\s*(Total|Routing|PB Types|Clock)\s+([0-9.e+-]+)\s+([0-9.e+-]+)\s+([\w.+-]+)", line)
        if m and m.group(1) not in rows:
            frac = m.group(4)
            rows[m.group(1)] = (float(m.group(2)), 0.0 if "nan" in frac else float(frac))
    if "Total" not in rows:
        return None, "no power breakdown in VPR power report"
    tot, dfrac = rows["Total"]
    return {"total_mw": tot * 1e3, "dynamic_mw": tot * dfrac * 1e3, "static_mw": tot * (1 - dfrac) * 1e3,
            "method": "ACE2 vectorless (-s 1) + VPR --power, PTM_45nm, W=100"}, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--design", required=True)
    ap.add_argument("--src", nargs="+", default=[])
    ap.add_argument("--build", help="build.json (tools/build_i1.py): sources and defines of the design")
    ap.add_argument("--rtl-result", help="JSON of tools/run_i1.py: use it as the RTL simulation "
                    "result instead of simulating here")
    ap.add_argument("--vec", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tier", default="quick")
    ap.add_argument("--clock", default="clk")
    ap.add_argument("--netlist-sim", dest="nsim", action="store_true", default=True)
    ap.add_argument("--no-netlist-sim", dest="nsim", action="store_false")
    ap.add_argument("-I", dest="inc", action="append", default=[])
    ap.add_argument("-D", dest="defs", action="append", default=[])
    a = ap.parse_args()
    if a.build:
        b = C.load_build(a.build)
        a.src = b["sources"]
        a.defs = a.defs + b["define_args"]
    if not a.src:
        ap.error("give --src or --build")
    work = Path(a.work).resolve() / a.design / "vtr"
    row = C.new_row(a.design, "vtr-k6", a.tier)
    nr = row["null_reason"]
    row["tools"] = {"odin3": str(C.ODIN3_BIN.name), "arch": C.ARCH.name, "vpr": "VTR_ROOT build"}

    # 1. RTL simulation (iverilog)
    if a.rtl_result:
        got = json.loads(Path(a.rtl_result).read_text())
        rtl, err = got["result"], got["error"]
        row["accuracy"] = {"rtl_" + got["sim"]: rtl}
        if err:
            nr["accuracy.rtl_" + got["sim"]] = err
    else:
        rtl, err = C.sim_iverilog([Path(s).resolve() for s in a.src], a.vec, work / "sim-rtl-iverilog")
        row["accuracy"] = {"rtl_iverilog": rtl}
        if err:
            nr["accuracy.rtl_iverilog"] = err

    # 2. synthesis + VPR
    flow_out = work / "flow"
    if flow_out.exists():
        shutil.rmtree(flow_out)
    cmd = [C.ODIN3_FLOW] + [str(Path(s).resolve()) for s in a.src] + [
        "--target", "vtr", "--arch", C.ARCH, "--odin3", C.ODIN3_BIN, "--out", flow_out]
    for i in a.inc:
        cmd += ["-I", i]
    for d in a.defs:
        cmd += ["-D", d]
    t = time.time()
    r = C.capped(cmd, timeout=6 * 3600, mem="4G")
    (work / "flow.log").parent.mkdir(parents=True, exist_ok=True)
    (work / "flow.log").write_text(r.stdout + r.stderr)
    summ = flow_out / "summary.json"
    if r.returncode or not summ.exists():
        for k in ("area", "speed", "power"):
            nr[k] = f"odin3-flow failed (exit {r.returncode}); see flow.log"
        C.append_row(row, a.out)
        return 0
    s = json.loads(summ.read_text())
    vtxt = ""
    vo = flow_out / "vpr/run/vpr_stdout.log"
    if vo.exists():
        vtxt = vo.read_text()
    v = parse_vpr_stdout(vtxt)
    hb = s.get("hard_blocks", {})
    row["area"] = {"luts": s.get("luts"), "ffs": v.get("ff"), "clbs": s.get("clbs"),
                   "adders": v.get("adder"), "dsp_mult36": hb.get("mult_36"),
                   "ram_blocks": hb.get("memory"), "min_chan_width": s.get("min_chan_width"),
                   "wirelength": s.get("wirelength"), "grid": v.get("grid")}
    cpd = s.get("crit_path_ns")
    row["speed"] = {"crit_path_ns": cpd, "fmax_mhz": (1000.0 / cpd) if cpd else None,
                    "cycles_per_img": None, "latency_us": None, "images_per_s": None}
    row["tools"]["flow_wall_s"] = round(time.time() - t, 1)

    # 3. netlist simulation: Odin III sim_tb on the LUT-mapped netlist (abc --lut 6). The BLIF
    # file itself holds `adder` black boxes that sim_tb cannot evaluate, so the same mapping is
    # re-run in memory; carry-chain adders are plain LUT logic there (same function).
    blif = next((flow_out / "odin3").glob("*.blif"), None)
    if a.nsim:
        reads = "; ".join(f"read_verilog {Path(x).resolve()}" for x in a.src)
        nl, err = C.sim_odin(f"{reads}; proc; opt; lower; abc --lut 6", a.vec, work / "sim-netlist-odin")
        row["accuracy"]["netlist_odin_sim"] = nl
        if err:
            nr["accuracy.netlist_odin_sim"] = err
        else:
            row["notes"].append("netlist sim = in-memory abc --lut 6 netlist, not the BLIF (adder subckt black box)")
    else:
        nr["accuracy.netlist_odin_sim"] = "disabled"

    # cycles per image: from RTL sim (the netlist sim, when run, must agree)
    cyc = (rtl or {}).get("cycles_per_img")
    if cyc and cpd:
        lat = cyc * cpd / 1000.0  # us
        row["speed"].update(cycles_per_img=cyc, latency_us=lat, images_per_s=1e6 / lat)
        row["speed"]["note"] = "images_per_s = 1/latency (no pipelining credit; initiation interval = cycles_per_img)"
    else:
        nr["speed.cycles_per_img"] = "no RTL simulation result" if not cyc else "no critical path"

    # 4. power
    if blif:
        p, err = power_flow(blif, a.clock, work / "power")
        if p:
            if row["speed"].get("latency_us"):
                p["energy_uj_per_img"] = p["total_mw"] * 1e-3 * row["speed"]["latency_us"]
            else:
                nr["power.energy_uj_per_img"] = "no latency"
            row["power"] = p
        else:
            nr["power"] = err
    else:
        nr["power"] = "no BLIF"
    C.append_row(row, a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
