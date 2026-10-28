# Per-path timing tables (schema version 6)

Date 2026-10-28. Branch `feat/timing-paths`. Additive on version 5 (`2026-10-28-near-critical.md`).

## 1. Purpose

Hub RQ W Q3.3 (Wyrd visualises the dataset); measure: speed = critical plus near-critical paths.
Version 5 keeps per-object aggregates (`timing_object`: `crit_max`, `n_paths`), which say that a line
is hot but not which paths make it hot. Version 6 keeps the reported paths and their nodes, so a
viewer can list the paths through a line, bit or word and walk one path through the logic.

## 2. Tables

    timing_path(run_id, path_index, slack_ns, arrival_ns, required_ns, crit, startpoint, endpoint,
                n_nodes, PRIMARY KEY (run_id, path_index))
    timing_path_node(run_id, path_index, step, atom, block_type, pins, span, loc, module, word,
                     bit, word_via, category, cell_delay_ns, net_delay_in_ns, delay_ns,
                     PRIMARY KEY (run_id, path_index, step))
    indexes: timing_path_node(run_id, span), timing_path_node(run_id, word, bit)

- `path_index` is the attribution's 1-based index; `step` is the 1-based position of the node on the
  path (start to end).
- `crit` is the path criticality of `timing.criticalities` (the value the histogram and
  `timing_object` use, same per-clock-domain-pair `max_req` and shift). NULL for a path of a
  skipped pair (`timing_run.pairs_skipped`). A path-level `report` import has paths and no nodes
  (`n_nodes = 0`, `arrival_ns` NULL).
- `pins` is a compact JSON list of the atom pins on the path (`["in[0]","out[0]"]`). `bit` is -1 where the
  attribution gives none. `span`, `loc`, `module`, `word` are as in the attribution, passed through
  the `Scrubber` (a /home path never reaches a row; the import fails first).
- `word` and `module` are separate columns (`timing_object` joins them as `module/word`).

## 3. Writing

`mimir import-timing` writes both tables in the same transaction as the other timing tables (a re-import replaces
the run's path rows). `mimir migrate` takes a version 4 or 5 store to version 6. A version 5 store opens read
only as it is; the per-path tables are absent (`timing.has_path_tables`).

Backfill: `mimir import-timing STORE --paths-from-blobs [--blobs DIR] [--attr-dir DIR] [--full-dir DIR]`
fills the two tables for every run that has a `timing_run` row and no path rows, from the run's stored
`timing` artifact (sha256 checked by `blobs.get_bytes`). Idempotent. It writes only those two tables. A run is
skipped, with a reason, when the input's sha256 is not `timing_run.source_sha256` (the run was imported from
an `--attr-dir` file: give the same directory) or when the recomputed `paths_used` or `max_req_ns` differs
from the `timing_run` row (give `--full-dir`). Back the store up first.

## 4. Not in this version

The structural line-level HDL graph (cone of a line to primary outputs or inputs) is a later version.
