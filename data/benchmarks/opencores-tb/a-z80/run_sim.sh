#!/bin/bash
# usage: A80=<upstream a-z80 project dir> run_sim.sh <cpu dir> <wrapper.v> <outdir> <ram.hexdump> [toggles]
#   <cpu dir>  = A80/cpu (upstream) or the patched copy (patch -p1 of the a-z80-modified patches, see ../../opencores-synth/README.md)
#   toggles    = clock edges simulated (2 per cycle); the pin trace goes to <outdir>/trace.txt, ONEDRV result to sim.log
set -e
CPU=$1; WRAP=$2; OUT=$3; HEX=$4; N=${5:-40000}
BENCH=$(cd "$(dirname "$0")" && pwd)
UP=${A80:?set A80 to the upstream a-z80 project directory}/cpu/toplevel
mkdir -p "$OUT"; cp "$HEX" "$OUT/ram.hexdump"; : > "$OUT/io.hex"
FILES=$(ls $CPU/alu/*.v $CPU/bus/*.v $CPU/control/*.v $CPU/registers/*.v $CPU/toplevel/z80_top_direct_n.v | grep -v data_pins_lattice)
iverilog -g2012 -o "$OUT/sim.vvp" -P tb_cmp.NCYC=$N -I $CPU/control -I $CPU/toplevel $FILES $WRAP $BENCH/tb_cmp.sv $UP/tb_ram.sv $UP/tb_io.sv $UP/tb_iorq.sv $EXTRA
(cd "$OUT" && vvp sim.vvp > sim.log 2>&1)
