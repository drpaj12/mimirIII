"""Altera leg (Quartus runs later, on another machine): odin3-flow --target lpm, then write a
Quartus project skeleton for the DE1-SoC device 5CSEMA5F31C6 next to the netlist.

usage: lpm_leg.py --design NAME --src a.v [...] --vec DIR --work DIR --out results.jsonl
                  [--tier quick|full] [--top TOP]
Row: target 'cyclonev-lpm'. Quartus-derived fields (ALMs, DSP, M10K, Fmax, power) are null with
the reason 'quartus not run here'; RTL accuracy and the device capacity are filled.
"""
import argparse
import importlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
C = importlib.import_module("common")

# Pins are NOT copied from Gabe's file: the skeleton only references it.
GABE_QSF = "System/Tensor_Processing_Unit/DE1_SoC_sets_up_pins.qsf"

QSF = """# Quartus project skeleton written by score/lpm_leg.py (design {design}); compile on the
# machine with Quartus Prime Lite. Device: DE1-SoC (Cyclone V SE 5CSEMA5F31C6).
set_global_assignment -name FAMILY "Cyclone V"
set_global_assignment -name DEVICE 5CSEMA5F31C6
set_global_assignment -name TOP_LEVEL_ENTITY {top}
set_global_assignment -name VERILOG_FILE {netlist}
set_global_assignment -name SDC_FILE {design}.sdc
set_global_assignment -name POWER_PRESET_COOLING_SOLUTION "23 MM HEAT SINK WITH 200 LFPM AIRFLOW"
# Pin assignments for the board rig: source Gabe Litteken's file by reference, not copied:
#   {gabe_root}/{gabe_qsf}
# (this benchmark's wrapper ports are not board pins; for a fit/timing/power run use
#  virtual pins: set_instance_assignment -name VIRTUAL_PIN ON -to *)
set_instance_assignment -name VIRTUAL_PIN ON -to *
"""
SDC = "create_clock -name clk -period 10.000 [get_ports clk]\nderive_clock_uncertainty\n"


LIB = ("lpm_add_sub", "lpm_mult", "lpm_compare", "altsyncram", "scfifo", "dcfifo")
INSTANCE = re.compile(r"^\s*(?:\(\*[^\n]*?\*\)\s*)?(\\?[A-Za-z_][^\s(#]*)\s+(?:#\(|\S+\s*\()", re.M)


def instance_counts(text):
    """Library cells per instance of the top module: the netlist is hierarchical, so a cell in a
    module that is instantiated 64 times counts 64 times."""
    mods = {}
    for m in re.finditer(r"^module\s+(\S+)(.*?)^endmodule", text, re.M | re.S):
        mods[m.group(1)] = m.group(2)
    names = set(mods)
    uses = {}
    for name, body in mods.items():
        c = {}
        for inst in INSTANCE.findall(body):
            if inst in names or inst in LIB:
                c[inst] = c.get(inst, 0) + 1
        uses[name] = c
    tops = names - {i for c in uses.values() for i in c}
    memo = {}

    def total(name):
        if name in LIB:
            return {name: 1}
        if name in memo:
            return memo[name]
        out = {}
        for child, n in uses.get(name, {}).items():
            for k, v in total(child).items():
                out[k] = out.get(k, 0) + n * v
        memo[name] = out
        return out

    return {t: total(t) for t in sorted(tops)}


def lpm_checks(net, sim, flow_log):
    """The tools/quartus-check legs that apply to a multi-file design: purity of the netlist
    (check_pure), the read-back of netlist + stubs (the flow's own readback step, which uses the
    same library as the flow) and iverilog -Wall lint (check_lint). The netlist alone is not read
    back: it instantiates megafunctions (scfifo) whose stubs are in the sim file."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "quartus_check", C.ODIN3_FLOW.parent.parent / "quartus-check" / "quartus_check.py")
    qc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(qc)
    out = {"readback": "pass" if "step readback: ok" in flow_log else "fail: see flow.log"}
    for name, fn in (("pure", lambda: qc.check_pure(net.read_text(), sim.read_text())),
                     ("lint", lambda: qc.check_lint(net, sim))):
        try:
            fn()
            out[name] = "pass"
        except qc.CheckError as exc:
            out[name] = f"note: {exc}"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--design", required=True)
    ap.add_argument("--src", nargs="+", default=[])
    ap.add_argument("--build", help="build.json (tools/build_i1.py); the behavioural megafunction "
                    "models are left out of the LPM flow (scfifo/altsyncram stay instances)")
    ap.add_argument("--rtl-result",
                    help="JSON of tools/run_i1.py used as the RTL simulation result")
    ap.add_argument("--vec", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tier", default="quick")
    ap.add_argument("--top", default="mnist_top")
    ap.add_argument("-I", dest="inc", action="append", default=[])
    ap.add_argument("-D", dest="defs", action="append", default=[])
    a = ap.parse_args()
    models = []
    if a.build:
        b = C.load_build(a.build)
        a.src = [x for x in b["sources"] if x not in b["models"]]
        models = b["models"]
        a.defs = a.defs + b["flow_define_args"]
        a.inc = a.inc + b["incdirs"]
        a.top = b.get("top", a.top)
    if not a.src:
        ap.error("give --src or --build")
    work = Path(a.work).resolve() / a.design / "lpm"
    row = C.new_row(a.design, "cyclonev-lpm", a.tier)
    nr = row["null_reason"]
    row["tools"] = {"odin3": C.ODIN3_BIN.name, "device": "5CSEMA5F31C6", "family": "Cyclone V"}
    row["area"] = {"device_capacity": C.CYCLONE_V_5CSEMA5, "alm": None, "register": None,
                   "dsp_blocks": None, "m10k_blocks": None, "fits": None}
    for k in ("alm", "register", "dsp_blocks", "m10k_blocks", "fits"):
        nr[f"area.{k}"] = "quartus not run here"
    nr["speed"] = "quartus not run here (Fmax from the Timing Analyzer)"
    nr["power"] = "quartus not run here (Power Analyzer with simulation activity)"

    if a.rtl_result:
        got = json.loads(Path(a.rtl_result).read_text())
        rtl, err = got["result"], got["error"]
        row["accuracy"] = {"rtl_" + got["sim"]: rtl}
        if got.get("pipe"):
            row["accuracy"]["rtl_" + got["sim"] + "_pipelined"] = got["pipe"]
        if err:
            nr["accuracy.rtl_" + got["sim"]] = err
    else:
        rtl, err = C.sim_iverilog([Path(s).resolve() for s in models + a.src], a.vec,
                                  work / "sim-rtl-iverilog")
        row["accuracy"] = {"rtl_iverilog": rtl}
        if err:
            nr["accuracy.rtl_iverilog"] = err
    if rtl:
        row["speed"] = {"cycles_per_img": rtl["cycles_per_img"]}
        if a.rtl_result and (got.get("pipe") or {}).get("ii_cycles"):
            row["speed"]["ii_cycles"] = got["pipe"]["ii_cycles"]

    flow_out = work / "flow"
    if flow_out.exists():
        shutil.rmtree(flow_out)
    cmd = [C.ODIN3_FLOW] + [str(Path(s).resolve()) for s in a.src] + [
        "--target", "lpm", "--family", "Cyclone V", "--top", a.top,
        "--read-opt=--auto-blackbox", "--odin3", C.ODIN3_BIN,
        "--out", flow_out]
    for i in a.inc:
        cmd += ["-I", i]
    for d in a.defs:
        cmd += ["-D", d]
    env = dict(os.environ)
    if models:  # Quartus-generated altsyncram wrappers need a few more library parameters/ports
        tree = C.ODIN3_FLOW.parent.parent.parent
        env["ODIN3_SHARE"] = str(importlib.import_module("make_share").make(tree, work / "share"))
        row["notes"].append("flow ran with an ODIN3_SHARE whose lpm.o3lib declares the altsyncram "
                            "parameters/ports Odin III 1.6.1 lacks (tools/make_share.py)")
    r = C.capped(cmd, timeout=6 * 3600, mem=C.FLOW_MEM, env=env)
    work.mkdir(parents=True, exist_ok=True)
    (work / "flow.log").write_text(r.stdout + r.stderr)
    net = flow_out / "odin3" / f"{a.top}.v"
    net = net if net.is_file() else None
    if r.returncode or not net:
        nr["netlist"] = f"odin3-flow --target lpm failed (exit {r.returncode}); see flow.log"
        C.append_row(row, a.out)
        return 0
    q = work / "quartus"
    q.mkdir(exist_ok=True)
    shutil.copy(net, q / net.name)
    (q / f"{a.design}.qsf").write_text(QSF.format(
        design=a.design, top=a.top, netlist=net.name,
        gabe_root="external/USS_Tensor_Processing_Unit", gabe_qsf=GABE_QSF))
    (q / f"{a.design}.sdc").write_text(SDC)
    row["netlist"] = str((q / net.name).relative_to(Path(a.work).resolve()))
    sim = next((flow_out / "odin3").glob("*_lpm_sim.v"), None)
    row["checks"] = lpm_checks(net, sim, (work / "flow.log").read_text())
    summ = flow_out / "summary.json"
    if summ.exists():
        row["lpm_cells_definitions"] = json.loads(summ.read_text()).get("lpm_cells")
    row["netlist_bytes"] = net.stat().st_size
    row["lpm_cells"] = instance_counts(net.read_text()).get(a.top)
    nr["accuracy.netlist"] = ("the LPM netlist needs Altera's lpm_* / altera_mf simulation models "
                              "(the stubs in <top>_lpm_sim.v are empty); not simulated here")
    C.append_row(row, a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
