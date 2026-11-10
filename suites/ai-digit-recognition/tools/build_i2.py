"""Assemble implementation I2 (soft CPU running the C int8 LeNet-5) in a build directory.

usage: build_i2.py <setting> <OUT_DIR>      settings: see SETTINGS
Compiles sw/{crt0.S,main.c,lenet.c} + the generated weights.c with riscv64-unknown-elf-gcc, links at
ROM 0x0 / RAM 0x10000000, writes the ROM image (i2_rom.hex: 32-bit words, padded to a power of two) and
build.json (sources by path, defines, include dirs). Third-party cores are read by path (env PICORV32,
BRISCV; defaults under <workspace>/external); nothing of them or of Gabe's weights is copied or committed.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
SUITE = Path(__file__).resolve().parent.parent
WS = Path(os.environ.get("ODIN3_WS", Path.home() / "odin3-ws"))
USS = Path(os.environ.get("USS_TPU", WS / "external/USS_Tensor_Processing_Unit"))
PICO = Path(os.environ.get("PICORV32", WS / "external/picorv32")) / "picorv32.v"
BRISC = Path(os.environ.get("BRISCV", WS / "external/Arduino-on-RISC-V/quartus_project_revert_timer"))
GCC = os.environ.get("RISCV_GCC", "riscv64-unknown-elf-gcc")

# setting -> (core, march, softmul table, defines for the wrapper)
SETTINGS = {
    "pico-i-tab": ("pico", "rv32i", 1, {}),
    "pico-i-gcc": ("pico", "rv32i", 0, {}),
    "pico-m": ("pico", "rv32im", 0, {"PICO_MUL": 1}),
    "pico-fm": ("pico", "rv32im", 0, {"PICO_FAST": 1}),
    "brisc-i-tab": ("brisc", "rv32i", 1, {}),
    "brisc-i-gcc": ("brisc", "rv32i", 0, {}),
}
BRISC_FILES = ["fetch_issue.v", "fetch_receive.v", "regFile.v", "decode_unit.v", "ALU.v",
               "execution_unit.v", "hazard_detection_unit.v", "control_unit.v",
               "single_cycle_control_unit.v", "memory_issue.v", "memory_receive.v",
               "writeback_unit.v", "single_cycle_core.v"]
TARGET_DESC = {"pico": "picorv32", "brisc": "BRISC-V mcu (Arduino-on-RISC-V, MIT)"}


def run(argv, **kw):
    r = subprocess.run([str(a) for a in argv], capture_output=True, text=True, **kw)
    if r.returncode:
        raise SystemExit(f"{argv[0]} failed:\n{r.stdout}{r.stderr}")
    return r.stdout


def compile_fw(out, march, soft, rom_bytes, ram_bytes):
    ld = out / "link.ld"
    ld.write_text((SUITE / "sw/link.ld").read_text()
                  .replace("ROM_BYTES", str(rom_bytes)).replace("RAM_BYTES", str(ram_bytes)))
    elf = out / "fw.elf"
    run([GCC, f"-march={march}", "-mabi=ilp32", "-O2", "-ffreestanding", "-fno-builtin",
         "-nostdlib", "-nostartfiles", f"-DSOFTMUL={soft}", "-I", out, "-T", ld,
         "-Wl,--gc-sections", "-Wl,-Map=" + str(out / "fw.map"), "-o", elf,
         SUITE / "sw/crt0.S", SUITE / "sw/main.c", SUITE / "sw/lenet.c", out / "weights.c",
         "-lgcc"])
    return elf


def sizes(elf):
    t = run([GCC.replace("gcc", "size"), "-A", elf])
    d = {m.group(1): int(m.group(2)) for m in re.finditer(r"^(\.\w+)\s+(\d+)", t, re.M)}
    return d.get(".text", 0) + d.get(".rodata", 0), d.get(".bss", 0)


def build(setting, out):
    core, march, soft, defs = SETTINGS[setting]
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    run([sys.executable, "-I", SUITE / "tools/gen_sw_weights.py",
         USS / "Benchmarks/LeNet_5_TRANSMISSION.bin", out / "weights.c"])
    elf = compile_fw(out, march, soft, 1 << 20, 1 << 16)       # first pass: measure
    rom_b, bss = sizes(elf)
    rom_aw = max(10, (rom_b + 3) // 4 - 1).bit_length()          # words address bits
    ram_aw = max(8, ((bss + 1024 + 3) // 4 - 1).bit_length())    # data + >= 1 KiB stack
    elf = compile_fw(out, march, soft, 4 << rom_aw, 4 << ram_aw)
    run([GCC.replace("gcc", "objcopy"), "-O", "binary", "--only-section=.text",
         "--only-section=.rodata", elf, out / "fw.bin"])
    data = (out / "fw.bin").read_bytes()
    data += b"\0" * ((4 << rom_aw) - len(data))
    (out / "i2_rom.hex").write_text("".join(
        f"{int.from_bytes(data[i:i + 4], 'little'):08x}\n" for i in range(0, len(data), 4)))
    mod = SUITE / "rtl/i2_softcpu"
    common = [mod / "i2_mem.v", mod / "i2_mmio.v"]
    if core == "pico":
        srcs = [PICO] + common + [mod / "mnist_top_pico.v"]
    else:
        srcs = [BRISC / f for f in BRISC_FILES] + common + [mod / "mnist_top_brisc.v"]
    d = {"ROM_AW": rom_aw, "RAM_AW": ram_aw, **defs}
    info = {"setting": setting, "core": TARGET_DESC[core], "march": march, "softmul": soft,
            "code_rodata_bytes": rom_b, "bss_bytes": bss, "rom_bytes": 4 << rom_aw,
            "ram_bytes": 4 << ram_aw, "sources": [str(s) for s in srcs],
            "models": [str(s) for s in common], "wrapper": str(srcs[-1]),
            "core_sources": [str(s) for s in srcs if s not in common and s != srcs[-1]],
            "defines": d, "flow_defines": d, "incdirs": [str(out)]}
    (out / "build.json").write_text(json.dumps(info, indent=1, sort_keys=True) + "\n")
    return info


if __name__ == "__main__":
    i = build(sys.argv[1], sys.argv[2])
    print(f"I2 {i['setting']}: code+rodata {i['code_rodata_bytes']} B (ROM {i['rom_bytes']}), "
          f"bss {i['bss_bytes']} B (RAM {i['ram_bytes']})")
