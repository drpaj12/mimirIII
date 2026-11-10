"""Shared helpers: run a capped command, run the testbench, results row schema."""
import json
import os
import re
import subprocess
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TB = REPO / "tb" / "mnist_tb.v"
# Tool locations: environment overrides, else the workspace defaults.
WS = Path(os.environ.get("ODIN3_WS", Path.home() / "odin3-ws"))
ODIN3_BIN = Path(os.environ.get("ODIN3_BIN", WS / "odin3/build/rel-v161pre/odin3"))
ODIN3_FLOW = Path(os.environ.get("ODIN3_FLOW", WS / "odin3/tools/flow/odin3-flow"))
VTR_ROOT = Path(os.environ.get("VTR_ROOT", WS / "external/vtr-verilog-to-routing"))
ARCH = VTR_ROOT / "vtr_flow/arch/timing/k6_frac_N10_frac_chain_mem32K_40nm.xml"
TECH = VTR_ROOT / "vtr_flow/tech/PTM_45nm/45nm.xml"
SCHEMA_VERSION = 1

# Cyclone V SE 5CSEMA5 (A5 member): Table 10 of Cyclone V Device Overview CV-51001
# (2015.06.12), local copy
# external/openmsp430/fpga/altera_de0_nano_soc/doc/Terasic/DE0_NANO_SOC/Datasheet/FPGA/
# "Cyclone V Device Overview.pdf". M10K is given in Kb (3,970 Kb; one block is 10 Kb).
CYCLONE_V_5CSEMA5 = {"alm": 32075, "register": 128300, "m10k_kbit": 3970,
                     "m10k_blocks": 397, "dsp_blocks": 87, "mult_18x18": 174}


def capped(argv, cwd=None, mem="2G", timeout=None, env=None):
    """Run under systemd-run --user --scope with a memory cap; return CompletedProcess."""
    cmd = ["systemd-run", "--user", "--scope", "-q", "-p", f"MemoryMax={mem}",
           "-p", "MemorySwapMax=0"] + [str(a) for a in argv]
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)


_SUM = re.compile(r"MNIST_TB (PASS|FAIL) n=(\d+) class_match=(\d+) score_match=(\d+) "
                  r"label_correct=(\d+) timeouts=(\d+) cycles_total=(\d+) cycles_per_img=(\d+)"
                  r"(?: init_cycles=(\d+))?")


def parse_tb(text):
    m = _SUM.search(text)
    if not m:
        return None
    v = [int(x) if x is not None else 0 for x in m.groups()[1:]]
    return {"verdict": m.group(1), "n": v[0], "class_match": v[1], "score_match": v[2],
            "label_correct": v[3], "timeouts": v[4], "cycles_total": v[5],
            "cycles_per_img": v[6], "init_cycles": v[7], "top1": v[3] / v[0]}


def stage_vectors(vec_dir, run_dir):
    run_dir.mkdir(parents=True, exist_ok=True)
    for f in Path(vec_dir).glob("vec_*.hex"):
        link = run_dir / f.name
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to(f.resolve())
    return int(open(Path(vec_dir) / "vec_meta.hex").readline(), 16)


def sim_iverilog(dut_files, vec_dir, run_dir, timeout=6 * 3600, defines=()):
    n = stage_vectors(vec_dir, run_dir)
    r = subprocess.run(["iverilog", "-g2005", f"-DMNIST_N={n}"] + [f"-D{d}" for d in defines]
                       + ["-o", "t.vvp", str(TB)] + [str(f) for f in dut_files],
                       cwd=run_dir, capture_output=True, text=True)
    if r.returncode:
        return None, "iverilog compile failed: " + r.stderr[-300:]
    t = time.time()
    r = capped(["vvp", "t.vvp"], cwd=run_dir, timeout=timeout)
    res = parse_tb(r.stdout)
    if res:
        res["wall_s"] = round(time.time() - t, 2)
    return res, None if res else "no summary line: " + (r.stdout + r.stderr)[-300:]


def sim_verilator(dut_files, vec_dir, run_dir, defines=(), timeout=6 * 3600, mem="4G"):
    """Build the testbench + DUT with Verilator (--binary --timing, Verilog-2005) and run it.
    defines: ["NAME=value", ...] passed as -D. Used where iverilog is too slow."""
    n = stage_vectors(vec_dir, run_dir)
    cmd = ["verilator", "--binary", "--timing", "--language", "1364-2005", "-Wno-fatal",
           "-Wno-lint", "-Wno-style", "-Wno-WIDTH", "-Wno-TIMESCALEMOD", "-O2",
           "--top-module", "mnist_tb",
           "--Mdir", "obj", f"-DMNIST_N={n}", "-o", "simv"]
    cmd += [f"-D{d}" for d in defines] + [str(TB)] + [str(f) for f in dut_files]
    r = capped(cmd, cwd=run_dir, mem=mem)
    if r.returncode or not (Path(run_dir) / "obj" / "simv").exists():
        return None, "verilator build failed: " + (r.stdout + r.stderr)[-300:]
    t = time.time()
    r = capped([Path(run_dir) / "obj" / "simv"], cwd=run_dir, timeout=timeout, mem=mem)
    res = parse_tb(r.stdout)
    if res:
        res["wall_s"] = round(time.time() - t, 2)
    return res, None if res else "no summary line: " + (r.stdout + r.stderr)[-300:]


def sim_odin(read_cmd, vec_dir, run_dir, timeout=3600, extra=""):
    """read_cmd: Odin script that reads the DUT (RTL: 'read_verilog x.v; proc; opt; lower';
    netlist: 'read_blif x.blif')."""
    n = stage_vectors(vec_dir, run_dir)
    script = f"{read_cmd}; sim_tb {extra} -D MNIST_N={n} {TB}"
    t = time.time()
    r = capped([ODIN3_BIN, "-p", script], cwd=run_dir, timeout=timeout)
    res = parse_tb(r.stdout)
    if res:
        res["wall_s"] = round(time.time() - t, 2)
    return res, None if res else "no summary line: " + (r.stdout + r.stderr)[-300:]


def new_row(design, target, tier):
    """The results row: one per design x target. Every measured field may be null, with
    the cause in 'null_reason' keyed by the same field name."""
    return {"schema": SCHEMA_VERSION, "design": design, "target": target, "tier": tier,
            "accuracy": None,        # {rtl: tb result, netlist: tb result}
            "area": None,            # target-specific dict
            "speed": None,           # {fmax_mhz, crit_path_ns, cycles_per_img, latency_us, ...}
            "power": None,           # {total_mw, dynamic_mw, static_mw, method, energy_uj_per_img}
            "tools": {}, "null_reason": {}, "notes": []}


def append_row(row, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")


def load_build(path):
    """A build.json written by tools/build_i1.py: sources, models, defines."""
    b = json.loads(Path(path).read_text())
    b["define_args"] = [f"{k}={v}" for k, v in b["defines"].items()]
    b["flow_define_args"] = [f"{k}={v}" for k, v in b["flow_defines"].items()]
    return b
