# MCNC detector re-runs for the four 1800 s timeouts (2026-10-28)

Purpose: Mimir Q1.7, detector recall over all 20 MCNC circuits. Four circuits (alu4, misex3,
s298, seq) timed out at 1800 s in lane 3. They were re-run with a 14400 s limit. Result: 2 of
4 finished, 1 was stopped for a VM restart, 1 was not started.

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

| design | status | wall time (s) | peak RSS (MiB) | detector rows |
|---|---|---|---|---|
| alu4 | ok (final_equiv skipped:hard) | 2046 | 1313 | equality 27 (wordfirst 26, arith 1), mux 1 |
| misex3 | ok (final_equiv skipped:hard) | 4304 | 9660 | equality 36 (wordfirst 29, arith 7), mux 2 |
| s298 | stopped by the controller for the VM restart at 4115 s elapsed (SIGTERM, exit -15); recorded in the copy as `failed`, not a detector failure; no stage output beyond the BLIF copy and `re.stderr` | 4115 | 173 | none |
| seq | not started (old run: timeout at 1800 s, 1308 MiB) | - | - | none |

The old timeout row of each design stays in the store. Detector runs by status after the
re-runs: ok 98, failed 1 (the s298 stop), timeout 4 (old rows). MCNC designs with a finished
detector run: 18 of 20.

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
add is detector rows: 63 equality and 3 mux structures from alu4 and misex3.

## Re-run the rest

Needs the store copy `/tmp/claude-1000/msd-store/lane3-structures.db`, the blob dir
`/tmp/claude-1000/msd-blobs`, the work dir `/tmp/claude-1000/msd-work`, the Loki venv, the
Odin III tree, the Loki checkout and `$VTR_ROOT` (for the MCNC BLIF paths). One design at a time,
as a background run:

    PYTHONPATH=<mimir worktree> VTR_ROOT=<vtr> nice -n 10 python -m mimir.structcli detect-mcnc \
      /tmp/claude-1000/msd-store/lane3-structures.db --work /tmp/claude-1000/msd-work \
      --wall-limit 14400 --loki-python <loki .venv python> --odin3-tree <odin3> \
      --loki-src <loki> --blobs /tmp/claude-1000/msd-blobs --only s298

Then `--only seq`. `detect-mcnc` skips a design with an `ok` or `differs` run, so a repeated
call is safe. Memory: misex3 peaked at 9.7 GB, seq reached 1.3 GB in 1800 s, so check `free -g`.
