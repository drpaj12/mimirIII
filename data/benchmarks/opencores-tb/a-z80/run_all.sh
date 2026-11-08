#!/bin/bash
# usage: A80=<upstream a-z80 project dir> run_all.sh <upstream cpu dir> <patched cpu dir> <runroot> [toggles] [programs]
# Runs upstream and modified on each program with identical stimulus and diffs the pin traces (0 mismatches expected).
B=$(cd "$(dirname "$0")" && pwd); O=$1; M=$2; R=$3; N=${4:-200000}; PROGS=${5:-"hello prog2 rand1 rand2 rand3"}
mkdir -p $R/prog
cp $B/prog2.hexdump $R/prog/; cp "${A80:?}/cpu/toplevel/simulation/modelsim/ram.hexdump" $R/prog/hello.hexdump
for s in 1 2 3; do python3 $B/mkrand.py $s > $R/prog/rand$s.hexdump; done
for p in $PROGS; do
  $B/run_sim.sh $O $B/wrap_orig.v $R/$p-orig $R/prog/$p.hexdump $N 2>/dev/null
  EXTRA="-DCHK_ONEDRV -I $B" $B/run_sim.sh $M $B/wrap_mod.v $R/$p-mod $R/prog/$p.hexdump $N 2>/dev/null
  mm=$(paste -d'|' $R/$p-orig/trace.txt $R/$p-mod/trace.txt | awk -F'|' '$1!=$2' | wc -l)
  nl=$(wc -l < $R/$p-orig/trace.txt)
  fe=$(awk '{print $5}' $R/$p-orig/trace.txt | cut -c1 | grep -c 0)   # samples with nM1 low (instruction fetch activity)
  echo "$p: samples=$nl mismatches=$mm m1_active=$fe $(grep ONEDRV $R/$p-mod/sim.log)"
done
