"""Write an ODIN3_SHARE directory whose lib/lpm.o3lib declares the altsyncram parameters and ports
that Quartus-generated memory wrappers (Gabe Litteken's Mem_Unit, TPU_0x1_Buffer,
Program_Memory) use and the library of Odin III 1.6.1 (lib/lpm.o3lib:73-110) lacks.

Odin III reports these gaps (one per run, `read_verilog`):
  cell type 'altsyncram' has no parameter 'width_byteena_b' (also indata_reg_b, outdata_aclr_a,
  read_during_write_mode_port_b, wrcontrol_wraddress_reg_b, lpm_hint)
  cell type 'altsyncram' has no port 'byteena_a' (also byteena_b, eccstatus)
The additions use the altera_mf defaults. The Odin III tree is not changed.

usage: make_share.py <odin3_tree> <out_share_dir>
"""
import shutil
import sys
from pathlib import Path

PARAMS = '''  param indata_reg_b string "CLOCK1"
  param outdata_aclr_a string "NONE"
  param read_during_write_mode_port_b string "NEW_DATA_NO_NBE_READ"
  param width_byteena_b int 1
  param wrcontrol_wraddress_reg_b string "CLOCK1"
  param lpm_hint string "UNUSED"
'''
PORTS = '''  in  byteena_a width_byteena_a
  in  byteena_b width_byteena_b
  out eccstatus 3
'''


def make(tree, out):
    tree, out = Path(tree), Path(out)
    (out / "tools/flow").mkdir(parents=True, exist_ok=True)
    shutil.copytree(tree / "lib", out / "lib", dirs_exist_ok=True)
    shutil.copy(tree / "tools/flow/lpm.script", out / "tools/flow/lpm.script")
    lib = out / "lib/lpm.o3lib"
    text = lib.read_text()
    start = text.index("cell altsyncram")
    end = text.index("\nend", start)
    cell = text[start:end]
    anchor = '  param clock_enable_output_b string "NORMAL"\n'
    assert anchor in cell and "in  byteena_a" not in cell and "param indata_reg_b" not in cell
    cell = cell.replace(anchor, anchor + PARAMS) + "\n" + PORTS.rstrip("\n")
    lib.write_text(text[:start] + cell + text[end:])
    return out


if __name__ == "__main__":
    print(make(sys.argv[1], sys.argv[2]))
