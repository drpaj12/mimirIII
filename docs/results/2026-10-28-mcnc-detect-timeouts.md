# MCNC detector re-runs for the four 1800 s timeouts (2026-10-28)

Purpose: Mimir Q1.7, detector recall over all 20 MCNC circuits. Four circuits (alu4, misex3,
s298, seq) timed out at 1800 s in lane 3. They were re-run with a 14400 s limit. Result of the second pass: alu4, misex3 and s298 finished, seq timed out again at 14400 s.

## How the rows were made

- Store: `lane3-structures.db` holds the MCNC detector rows (slugs `mcnc20/<design>`,
  `source = mimir-detect`). `mimir-structures.db` and `structures.db` have none.
- Original command: `python -m mimir.structcli detect-mcnc <db> --work <dir> --wall-limit 1800
  --loki-python <loki venv python> --odin3-tree <odin3> --loki-src <loki> --blobs <dir>`. Each
  design runs `structcli detect --blif <mcnc blif>` at `nice -n 10`, no heavy lock. Loki options
  are unchanged: `loki.re.main <blif> --floor f1-k6 --detectors wordfirst,hard,ff_pattern,mux,arith,seqfn,fsm,bus,unit,role,wordgroup --seed 1 --timeout 30 --time-budget 600 --max-rounds 6 --calib none`.
- Re-run: same command, `--wall-limit 14400`, `--only <design>`, one design at a time, on a copy
  of the store. Loki is at 53a7d9b, as in the original run. The Odin III tree is at b01a803
  (the original run recorded 997cb609); the detectors do not depend on the Odin III build
  for these BLIF-only runs, but this is a difference.
- The store in the data directory was not written. A re-run adds a new run row beside the old
  timeout row (different run id).

## Per design

Second pass (after the VM restart wiped the first store copy). Persistent copy
`work/mimir-data/msd/lane3-structures.msd.db` (sha256 of the source at copy time and of the copy:
8184499d9639aa43cddaa920a11e8534845ca3fd1b4da9e77dea080b4b3aff92). One design at a time, alone in
the VM, `--wall-limit 14400`, `nice -n 10`, wall time and peak RSS from `/usr/bin/time -v`.

| design | status | wall time (s) | peak RSS (MiB) | detector rows |
|---|---|---|---|---|
| s298 | ok (final_equiv skipped:hard), 1938 cells, Loki stop reason time_budget | 5802 | 3725 | 0 (see below) |
| seq | timeout at 14400 s (SIGKILL, exit -9), no Loki output | 14400 | 6412 | none |
| alu4 | ok (final_equiv skipped:hard) | 1520 | 1313 | equality 27 (wordfirst 26, arith 1), mux 1 |
| misex3 | ok (final_equiv skipped:hard) | 3290 | 9660 | equality 36 (wordfirst 29, arith 7), mux 2 |

- s298 reports 201 `eq_const` pieces, but `read_structs` keeps only top-level hypotheses
  (no parents) with p_comp >= 0.5. Every `eq_const` hypothesis of s298 (1054, 1014 with
  p_comp >= 0.5) has a parent, so none is kept. This is the detector extraction rule, not
  changed here.
- seq: the stage reached is unknown. Loki wrote no output file and `re.stderr` is empty, and
  Loki logs no stage while running, so only the kill is recorded. Raising the limit from 1800 s to
  14400 s changed nothing: the wall limit (not memory, peak 6.4 GB) ended it.
- The old timeout row of each design stays in the store beside the new run row.

Detector runs by status in the copy: ok 99, timeout 5 (4 old rows plus seq at 14400 s). MCNC
designs with a finished detector run: 19 of 20 (seq missing).

## Old and new precision and recall

The per-class P/R is computed only for designs that have both detector rows and HDL structures
(`structcli report`). The 20 MCNC circuits have no HDL, every MCNC structure row is
`detector:*`, so MCNC rows do not enter it. The table is therefore identical before and after:

| class | detected | correct | precision | hdl | found | recall |
|---|---|---|---|---|---|---|
| register_word | 1281 | 400 | .312 | 202 | 67 | .332 |
| mux | 10 | 7 | .700 | 226 | 5 | .022 |
| adder | 56 | 0 | 0 | 612 | 0 | 0 |
| equality | 132 | 0 | 0 | 439 | 0 | 0 |
| relational | 0 | 0 | - | 370 | 0 | 0 |

`diff` of the report section between the pre-run and post-run store copies is empty. A recall
number over MCNC needs HDL-free ground truth, which the store does not have. What the re-runs
add is detector rows: 63 equality and 3 mux structures from alu4 and misex3 (s298 and seq add
none). `structcli report` on the copy after all four runs gives the same table as above.

## Merge into the live store (not done)

The live `lane3-structures.db` has since moved on (now a newer schema version than the copy, which is
v5), so a plain `mimir merge` of the copy needs the copy migrated first, and the live store is
written by other lanes. When the controller decides: take a backup of the live store, then

    python -m mimir.cli migrate <copy>      # only if the live store is newer than v5
    python -m mimir.cli merge <live lane3-structures.db> <copy>

The merge adds only rows that are not already present; the blob files in
`work/mimir-data/msd/blobs` must be copied (or `--blobs` pointed) into the live blob directory.
Run `mimir privacy-check --db <live> --blobs <blobs>` afterwards. Privacy check on the copy and
its blobs: 0 hits.

## Re-run seq

Only seq is open. It needs more than 14400 s or a faster detector; the command is the one used:

    PYTHONPATH=<mimir worktree> VTR_ROOT=<vtr> nice -n 10 python -m mimir.structcli detect-mcnc \
      <copy> --work <work dir> --wall-limit <s> --loki-python <loki venv python> \
      --odin3-tree <odin3> --loki-src <loki> --blobs <blob dir> --only seq

`detect-mcnc` skips a design with an `ok` or `differs` run. Script: `work/mimir-data/msd/run.sh`.
