"""Assemble implementation I1 (Gabe Litteken's TPU, array edge N) in a build directory.

Reads Gabe's files by path (USS_TPU env, default <workspace>/external/USS_Tensor_Processing_Unit;
the checkout must be at the pinned commit, see pins.toml) and writes only generated files into OUT:
  tpu_flash.hex   the flash transmission (weights + program retiled to N), one byte per line
  gen/TPU.v       his TPU.v with `Systolic_Array #(.N(8))` changed to N (the only edit)
  build.json      sources (his files by absolute path, our models and wrapper), defines
When the retiled program has more than 8192 instructions (N = 2), the program memory is widened
to 16 address bits (Program_Memory.v, Programmer.v, Feeder.v, TPU.v: address widths and depth
only), also written to gen/. Nothing from his repository is copied into the suite repository.

usage: build_i1.py <N> <OUT_DIR>
"""
import importlib
import json
import os
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE))
sys.path.insert(0, str(SUITE / "tools"))
parse = importlib.import_module("golden.tpu_bin").parse
RP = importlib.import_module("retile_program")

WS = Path(os.environ.get("ODIN3_WS", Path.home() / "odin3-ws"))
USS = Path(os.environ.get("USS_TPU", WS / "external/USS_Tensor_Processing_Unit"))
RTL = "System/Tensor_Processing_Unit/TPU"
GABE_FILES = [  # compile order; the *_bb.v black boxes, the VGA debug and demo files are not used
    "PROGRAMMER/SPI_LINK/SPI_Slave.v", "PROGRAMMER/SPI_LINK/SPI_INPUT_BUFFER/SPI_Input_buffer.v",
    "PROGRAMMER/SPI_LINK/SPI_Interface.v", "PROGRAMMER/PROGRAM_MEMORY/Program_Memory.v",
    "PROGRAMMER/Programmer.v", "PROGRAMMER/Feeder.v", "CONTROL/Controller.v",
    "MEMORY/0X1_BUFFER/TPU_0x1_Buffer.v", "MEMORY/MEM_UNIT/Mem_Unit.v", "MEMORY/Data_Memory.v",
    "MEMORY/VECTOR_BUFFER/Vector_Buffer.v", "PROCESSING/Activator.v", "PROCESSING/ALU.v",
    "PROCESSING/Pooler.v", "PROCESSING/Vector_Processor.v",
    "SYSTOLIC_ARRAY/Multiply_Accumulate_Unit.v", "SYSTOLIC_ARRAY/Systolic_Array_Input_Buffer.v",
    "SYSTOLIC_ARRAY/Systolic_Array.v"]


PM_EDITS = {  # file -> [(regex, replacement, expected count)]
    "PROGRAMMER/PROGRAM_MEMORY/Program_Memory.v": [
        (r"input\s+\[12:0\]\s+address;", "input [15:0] address;", 1),
        (r"numwords_a = 8192", "numwords_a = 65536", 1), (r"widthad_a = 13", "widthad_a = 16", 1)],
    "PROGRAMMER/Programmer.v": [
        (r"output reg \[12:0\]  o_pm_address", "output reg [15:0]  o_pm_address", 1),
        (r"parameter \[13:0\] PM_DEPTH = 14'd8192", "parameter [16:0] PM_DEPTH = 17'd65536", 1),
        (r"reg \[13:0\]  pc;", "reg [16:0]  pc;", 1),
        (r"o_pm_address        <= 13'd0", "o_pm_address        <= 16'd0", 1),
        (r"pc\[12:0\]", "pc[15:0]", 1)],
    "PROGRAMMER/Feeder.v": [
        (r"output reg \[12:0\]  o_pm_address", "output reg [15:0]  o_pm_address", 1),
        (r"parameter \[12:0\] PM_MAX_ADDRESS = 13'd8191",
         "parameter [15:0] PM_MAX_ADDRESS = 16'd65535", 1),
        (r"reg \[12:0\] pc;", "reg [15:0] pc;", 1), (r"13'd0", "16'd0", 2), (r"13'd1", "16'd1", 1)],
}


def widen_program_memory(gabe, gen, top):
    """Return the file map with the program-memory width edits applied (written under gen/)."""
    gabe = dict(gabe)
    for f, edits in PM_EDITS.items():
        text = Path(gabe[f]).read_text()
        for pat, rep, cnt in edits:
            text, k = re.subn(pat, rep, text)
            assert k == cnt, f"{f}: {pat!r} matched {k} times, expected {cnt}"
        dest = gen / Path(f).name
        dest.write_text(text)
        gabe[f] = str(dest)
    top, k = re.subn(r"wire \[12:0\]  (prog_pm_address|pm_address|feeder_pm_address);",
                     lambda m: f"wire [15:0]  {m.group(1)};", top)
    assert k == 3
    (gen / "TPU.v").write_text(top)
    return gabe


def build(n, out):
    out = Path(out).resolve()
    (out / "gen").mkdir(parents=True, exist_ok=True)
    mem, instrs = parse(USS / "Benchmarks/LeNet_5_TRANSMISSION.bin")
    new = RP.retile(instrs, n) if n != 8 else instrs
    tx = out / "tpu_flash.bin"
    RP.write(tx, mem, new)
    data = tx.read_bytes()
    (out / "tpu_flash.hex").write_text("".join(f"{b:02x}\n" for b in data))
    top = (USS / RTL / "TPU.v").read_text()
    top2, k = re.subn(r"Systolic_Array #\(\.N\(8\)\)", f"Systolic_Array #(.N({n}))", top)
    assert k == 1, "TPU.v: Systolic_Array #(.N(8)) not found"
    mod = SUITE / "rtl/i1_tpu"
    gabe = {f: str(USS / RTL / f) for f in GABE_FILES}
    if len(new) > 8192:
        gabe = widen_program_memory(gabe, out / "gen", top2)
    else:
        (out / "gen/TPU.v").write_text(top2)
    srcs = ([str(mod / "models/altsyncram.v"), str(mod / "models/scfifo.v")]
            + [gabe[f] for f in GABE_FILES]
            + [str(out / "gen/TPU.v"), str(mod / "mnist_top_tpu.v")])
    info = {"n": n, "instructions": len(new), "flash_bytes": len(data), "sources": srcs,
            "models": srcs[:2], "gabe_sources": srcs[2:-1], "wrapper": srcs[-1],
            "defines": {"FLASH_LEN": len(data), "FLASH_HEX": f'"{out}/tpu_flash.hex"',
                        "TPU_N": n},
            # odin3-flow takes no quote in a -D value: the flows find tpu_flash.hex through -I
            "flow_defines": {"FLASH_LEN": len(data), "TPU_N": n}, "incdirs": [str(out)]}
    (out / "build.json").write_text(json.dumps(info, indent=1, sort_keys=True) + "\n")
    return info


if __name__ == "__main__":
    i = build(int(sys.argv[1]), sys.argv[2])
    print(f"I1 N={i['n']}: {i['instructions']} instructions, {i['flash_bytes']} flash bytes")
