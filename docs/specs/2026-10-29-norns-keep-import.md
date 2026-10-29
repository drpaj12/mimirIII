# Norns kept timing evidence: import (purpose: hub W Q3.3, speed = critical + near-critical paths)

Norns runs (nornsIII `keep_timing`) keep, beside `mimir-run.json`: `attribution.json.xz` (Odin III
timing attribution, paths tokenised `$VTR_ROOT` / `$WS` / `~`), `keep-timing.json`, and once per
(design, blif sha256) in the keep store `<design>/<sha>/<design>.blif.xz` and `.blif.names.xz`.

`mimir import <db> norns --norns <root> --runs <dir> [--blobs D] [--odin3-tree T] [--keep-store K]`
imports the run records under `<dir>` (`import-runrecords`), then for each record with a
`timing_attribution` artifact:

- checks the file's sha256 against the record, the record netlist sha256 against `keep-timing.json`,
  and the kept blif and name map against their sha256 (a kept copy that was path-tokenised must hold
  a token instead);
- scrubs (idempotent) and stores three blobs, the kinds and formats lane 3 uses: `timing` (the
  attribution JSON text), `blif`, `map` (the `.blif.names` text); `run_artifact` rows are replaced
  for those three kinds only;
- fills schema 5 and 6 through `timing.import_from_blobs` and `timing.backfill_paths`, and schema 7
  through `hdlgraph.backfill` (needs `--odin3-tree` or `$MIMIR_ODIN3_TREE`; without it the status says
  the graph was not built and a later run builds it). No new parsing.

Idempotent: blobs are content addressed; a run whose three blobs are unchanged and which has a
`timing_run` row is not re-imported; a changed blob rebuilds the run's graph. A run without kept files
imports as before (run row only). Spans arrive as `$VTR_ROOT/...`, the same tokens lane 3 stores.
