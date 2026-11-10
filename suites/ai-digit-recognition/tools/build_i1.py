"""Assemble implementation I1 (Gabe Litteken's TPU, array edge N) in a build directory.

Reads Gabe's files by path (USS_TPU env, default <workspace>/external/USS_Tensor_Processing_Unit; the
checkout must be at the pinned commit, see data/pins.toml) and writes only generated files into OUT:
  tpu_flash.hex   the flash transmission (weights + program retiled to N), one byte per line
  gen/TPU.v       his TPU.v with `Systolic_Array #(.N(8))` changed to N (the only edit)
  build.json      sources (his files by absolute path, our models and wrapper), defines
Nothing from his repository is copied into the suite repository.

usage: build_i1.py <N> <OUT_DIR>
"""
import json, os, re, sys
from pathlib import Path

sys.dont_write_bytecode = True
SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE))
sys.path.insert(0, str(SUITE / "tools"))
from golden.tpu_bin import parse  # noqa: E402
import retile_program as RP  # noqa: E402

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
    (out / "gen/TPU.v").write_text(top2)
    mod = SUITE / "rtl/i1_tpu"
    srcs = ([str(mod / "models/altsyncram.v"), str(mod / "models/scfifo.v")]
            + [str(USS / RTL / f) for f in GABE_FILES] + [str(out / "gen/TPU.v"),
                                                        str(mod / "mnist_top_tpu.v")])
    info = {"n": n, "instructions": len(new), "flash_bytes": len(data), "sources": srcs,
            "models": srcs[:2], "gabe_sources": srcs[2:-1], "wrapper": srcs[-1],
            "defines": {"FLASH_LEN": len(data), "FLASH_HEX": f'"{out}/tpu_flash.hex"',
                        "TPU_N": n}}
    (out / "build.json").write_text(json.dumps(info, indent=1, sort_keys=True) + "\n")
    return info


if __name__ == "__main__":
    i = build(int(sys.argv[1]), sys.argv[2])
    print(f"I1 N={i['n']}: {i['instructions']} instructions, {i['flash_bytes']} flash bytes")
