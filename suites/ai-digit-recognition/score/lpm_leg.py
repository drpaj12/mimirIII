"""Altera leg (Quartus runs later, on another machine): odin3-flow --target lpm, then write a
Quartus project skeleton for the DE1-SoC device 5CSEMA5F31C6 next to the netlist.

usage: lpm_leg.py --design NAME --src a.v [...] --vec DIR --work DIR --out results.jsonl
                  [--tier quick|full] [--top TOP]
Row: target 'cyclonev-lpm'. Quartus-derived fields (ALMs, DSP, M10K, Fmax, power) are null with
the reason 'quartus not run here'; RTL accuracy and the device capacity are filled.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C

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


def lpm_checks(net, sim):
    """tools/quartus-check legs that apply to a multi-file design: purity, read-back, lint."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "quartus_check", C.ODIN3_FLOW.parent.parent / "quartus-check" / "quartus_check.py")
    qc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(qc)
    out = {}
    legs = (("pure", lambda: qc.check_pure(net.read_text(), sim.read_text())),
            ("readback", lambda: qc.check_readback(str(C.ODIN3_BIN), qc.DEFAULT_LIB, net, sim)),
            ("lint", lambda: qc.check_lint(net, sim)))
    for name, fn in legs:
        try:
            fn()
            out[name] = "pass"
        except qc.CheckError as exc:
            out[name] = f"fail: {exc}"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--design", required=True)
    ap.add_argument("--src", nargs="+", default=[])
    ap.add_argument("--build", help="build.json (tools/build_i1.py); the behavioural megafunction "
                    "models are left out of the LPM flow (scfifo/altsyncram stay instances)")
    ap.add_argument("--rtl-result", help="JSON of tools/run_i1.py used as the RTL simulation result")
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
        a.defs = a.defs + b["define_args"]
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

    flow_out = work / "flow"
    if flow_out.exists():
        shutil.rmtree(flow_out)
    cmd = [C.ODIN3_FLOW] + [str(Path(s).resolve()) for s in a.src] + [
        "--target", "lpm", "--family", "Cyclone V", "--top", a.top, "--read-opt=--auto-blackbox", "--odin3", C.ODIN3_BIN,
        "--out", flow_out]
    for i in a.inc:
        cmd += ["-I", i]
    for d in a.defs:
        cmd += ["-D", d]
    r = C.capped(cmd, timeout=6 * 3600, mem="4G")
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
    row["checks"] = lpm_checks(net, sim)
    summ = flow_out / "summary.json"
    if summ.exists():
        row["lpm_cells"] = json.loads(summ.read_text()).get("lpm_cells")
    nr["accuracy.netlist"] = ("the LPM netlist needs Altera's lpm_* / altera_mf simulation models "
                              "(the stubs in <top>_lpm_sim.v are empty); not simulated here")
    C.append_row(row, a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
