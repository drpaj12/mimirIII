# Near-critical timing data in Mimir, linked to the HDL through provenance

Date 2026-10-28. Lane: mimir-near-critical (branch `feat/near-critical`). Schema version 5
(additive on 4). Extends `2026-10-27-mimir-structures.md` (structures, `structure_mapping`) and
`2026-10-28-mimir-run-record.md` (the `run` rows this joins to).

## 1. Purpose, questions, measures

Purpose (Peter 2026-10-28): placement is hard because the critical path is followed by the next
problem path, and the one after it. The dataset must hold the near-critical paths behind the critical
one, per run and per HDL object (module, statement, word, bit, structure), so that hypotheses about
why things sit where they do can be tested against data.

Research questions (hub `docs/purpose.md`; this spec cites the IDs, it does not add any):

- **Mi Q2.1** (E5): do characteristics predict critical-path delay? The near-critical counts are
  extra response and feature columns for it. Speed.
- **Mi Q2.3** (E10): which parameters change the mapping, and what result quality follows. The
  near-critical set shows whether a change moved one path or the whole front. Area and speed.
- **N Q2.4**: which HDL relations (word, bit index, statement, module) predict where atoms sit.
  Per-object near-critical data is the link to the HDL. Area and speed.
- **L Q3.2**: are constructs on near-critical paths less recoverable than the rest. This table is the
  criticality band for that audit. Speed.
- **O Q2.1**: which statements, modules and words set the critical path. Extended from one path to
  the near-critical set. Speed.

Measures: speed = CPD, worst slack, near-critical path counts; area = LUTs and CLBs (already in the
store). Power is not measured. Papers that need an area link state the area and power correlation
with a real citation; no power metric is added here.

Success measures of the lane: share of stored VPR runs that have a `timing_run` row (target: every run
whose routing or report still exists), and the number of runs whose near-critical set is truncated
(target: 0, or each one named).

## 2. Definitions

### 2.1 Criticality

VPR's criticality of a connection is the "relaxed per constraint" criticality of Wainberg and Betz
(IEEE TCAD 34(12), 2015, doi 10.1109/TCAD.2015.2440316; `wainberg2015relaxed` in `citations.toml`,
named in VPR's source comment, record checked against Crossref 2026-10-28, full text not read). VPR 9 computes it in
`vpr/src/timing/timing_util.cpp` (`calc_relaxed_criticality`, lines 874-945 at VTR commit
3c9a4d23b2, the commit of `rose2012vtr` and `elgammal2025vtr9` data in this store):

    shift = -worst_slack if worst_slack < 0 else 0         (per clock domain pair)
    crit  = 1 - (slack + shift) / (max_req + shift)        clamped to [0, 1]

with `worst_slack` the smallest slack and `max_req` the largest required time over the endpoints of
the clock domain pair. The timing-driven placer and router use this crit to weight a connection
(`vpr/src/place/timing/PlacerCriticalities.h:76`). The definition "crit = 1 - slack / D_max" of the
brief is the case `worst_slack >= 0` of this formula, with `max_req` as D_max; Mimir uses VPR's formula
so that its numbers equal what the placer sees.

**Path criticality.** The criticality of a reported path is the formula above with the path's slack,
and `worst_slack` and `max_req` taken over the endpoints of its (launch clock, capture clock)
pair: exact when the run is `exhaustive` or `full-report`, else over the paths of the report
(2.1). The pair is read from the `clocked by` text of the path's start and end point.
The criticality of an object (a statement, word, bit, module, structure) is the maximum criticality of
the paths through it, as VPR takes the worst criticality over the connections through a pin.

**max_req: exact or a lower bound.** VPR takes `max_req` and the worst slack over all endpoints
(`SetupSlackCrit::recompute_max_req_and_worst_slack`, `vpr/src/timing/slack_evaluation.cpp:295-330`:
every logical output, every DATA_REQUIRED and slack tag). VPR prints no per-pair `max_req`: not in
the log, not in `--write_timing_summary` (cpd, fmax, sWNS, sTNS only) and not in
`--generate_net_timing_report` (slack only). What VPR does give is the full endpoint list: the
report collector (`libtatum .../report/TimingPathCollector.cpp`, `collect_worst_timing_paths`)
writes one path per (endpoint, clock domain pair) in ascending slack order and stops at
`--timing_report_npaths` N, and the VPR doc says the report holds fewer than N paths when the
circuit has fewer. So a report with fewer than N paths holds every endpoint and its `max_req` and
worst slack are VPR's. Mimir records which case a run is in, in `timing_run.dmax_source`:

- `exhaustive`: the run's own report holds fewer paths than N (`paths_in_report < paths_requested`,
  N = 100 when the attribution does not say). `max_req` and crit are VPR's.
- `full-report`: the run's report is cut at N, and a second `vpr --analysis` over the same stored
  routing with N above the endpoint count (`scripts/timing_rerun.py --report-only`, then
  `mimir import-timing --full-report`) gave the exact `max_req` and worst slack per pair.
  `max_req` and crit are VPR's; the near-critical set is still limited to the N paths of the run's
  own report (see truncation, 2.3).
- `report`: neither. `max_req` is the largest over the reported paths, no larger than VPR's, so the
  denominator is too small and **crit and every near-critical count are lower bounds**. The run
  stores `req_spread_ns`, the largest `max_req - min_req` over the reported paths of a pair: an
  upper bound on how far the denominator can move only when the unseen required times lie within
  the reported range, which is not known.

`req_spread_ns` is stored for every run. `crit` of a path is undefined when `max_req + shift <= 0`;
such a pair is skipped and counted (`pairs_skipped`). Crit is rounded to 9 decimals before it is
compared with theta or put in a bin, so a value that float arithmetic gives as 0.8999999999 is 0.9.

Observed in `lane3-structures.db` (79 runs, all one clock `clk`): see section 7.

### 2.2 Near-critical

A path (or object) is near-critical at theta when `crit >= theta`, theta in {0.90, 0.95, 0.99}. Why
these three: the timing-driven placer raises crit to an exponent that grows from
`--td_place_exp_first` (default 1.0) to `--td_place_exp_last` (default 8.0; `doc/src/vpr/command_line_usage.rst`
lines 1206-1222 at the VTR commit above). A connection at crit 0.90 keeps a weight of 0.9 at the start
and 0.43 at the end of the anneal; one at 0.5 keeps 0.5 and 0.004. So 0.90 is the edge below which
the end of the anneal ignores a path, 0.99 is "within one percent of the front", 0.95 is between. The
values are Mimir's choice, not a published constant; the histogram (2.3) lets a reader pick any other.
The placer's cost is `delay * crit` (`PlacerCriticalities.h:70-76`).

## 2.3 Per run

- **Path histogram**: 20 fixed bins of path crit, bin `b` = `[0.05 b, 0.05 (b+1))`, bin 19 includes
  1.0. In slack terms a bin is a slack window of 5% of `(max_req - worst_slack)` (about 5% of the
  CPD). Stored as `timing_path_hist(run_id, bin, n)`; empty bins are not stored.
- **Counts** of paths with crit >= theta, and of distinct endpoints among them, for the three thetas.
- **N and truncation.** `paths_requested` (N asked of VPR; null when the stored attribution does
  not say), `paths_in_report`, `paths_used`. The report is cut when it holds N paths or more
  (`paths_in_report >= paths_requested`, or `>= 100` when N is not known: VPR's default), or when
  the parser dropped a path (fewer paths parsed than `paths_in_report`: a last path cut off
  in the file; this second disjunct is conservative, it can flag a report that N did not cut).
  A cut report is truncated at theta when the last path of some clock domain pair still has
  crit >= theta; `last_crit` stores the largest such last-path crit over the pairs. A cut report
  with no usable last path (every pair skipped) is **unknown**: `trunc_*` = -1, and no
  `timing.truncated_090` record is written (an unknown is never stored as 0). An uncut report is 0.
  A run with a truncated 0.90 set is named in every report and gets the analysis re-run (section 4).
  The counts of a truncated run are lower bounds.
- **CPD and worst slack** as in the report.

### 2.4 Per HDL object

Through the odin3 attribution (`docs/user/timing-attribution.md`, `schema_version` 1): every node of a
path carries `module`, `span` (`file:line`), `loc` (full span `file:L.C-EL.EC`, with a name map),
`word`, `bit` and `word_via`.

| kind | object_key | what is joined |
|---|---|---|
| `module` | module instance path | nodes with that `module` (pads belong to the top module, as in the attribution) |
| `span` | `file:line` | nodes with that `span` |
| `word` | `module/word` | nodes with that module and word; `bit = -1` |
| `word` | `module/word` | the same, one row per declared `bit` where the node has one; `bit >= 0` |
| `structure` | `structure_id` | nodes whose `loc` lies inside the structure's `hdl_span`; line range when a node has no `loc`. `via` = `span` for a `line.col` span and `line` for the lane 3 whole-line form (`file:L-L`), where two operators on one line share their nodes |

The file of a node and of a structure are compared as paths: equal, or one a whole-component
suffix of the other (a design-relative path against one with the root placeholder in front), never
by base name alone. When two structure files of the same base name both match a node's path, the
name is ambiguous and the node joins no structure.

Per object and run: `crit_max`, `n_paths` (all paths through it), `n_paths_090/095/099` (paths through
it with crit >= theta, each path counted once), and `delay_share_090` = the delay of the object's nodes
on crit >= 0.90 paths over the delay of all nodes on those paths (node `delay_ns` as attributed:
cell delay plus the delay on the net the atom drives). Null when there is no crit >= 0.90 path of
positive delay.

**Where bits cannot be given.** A bit row exists only when the attribution gives the bit. It does for
a net named in the provenance name map or the netlist (`word_via` `name`) and for pads (`pad`). It does
not for a generated net (`word_via` `declarator`: word known, bit unknown; `json-id`: the word is a
heuristic from the JSON net numbering, `bit = ID + 1`). Rows from `json-id` nodes are kept at word
level only and the word row carries `via = 'json-id'` so a consumer can drop it; a node with no word
(`~name` guess only, `assigned_word`) joins by module and span only. The attribution's `~name`
guess from the source line is never used as a word.

A structure that comes from a detector (empty `hdl_span`) has no object row: there is no span
to join. Counted in the import report.

## 3. Storage (schema version 5)

Migration 4 to 5 is additive: three tables, one version number. A version 4 store is migrated on a write open
or by `mimir migrate DB` (back the file up first: copy and compare sha256); a read-only open
(`Store(readonly=True)`) of a version 4 store works as it is, changes no byte and no mtime, and has
no timing tables (`mimir timing-coverage` then says "no timing tables"). A version 5 store written
before `req_spread_ns` existed gets the column on its next write open. A version 4 reader refuses a
version 5 store, as a version 3 reader refused version 4.

    timing_run(run_id PK, cpd_ns, worst_slack_ns, paths_requested, paths_in_report, paths_used,
               max_req_ns, dmax_source, pairs, pairs_skipped, last_crit,
               trunc_090, trunc_095, trunc_099, n_endpoints_090, n_endpoints_095,
               n_endpoints_099, source_kind, source_sha256, analysis_n, req_spread_ns)
    timing_path_hist(run_id, bin, n,  PK (run_id, bin))
    timing_object(run_id, kind, object_key, bit, via, crit_max, n_paths, n_paths_090, n_paths_095,
                  n_paths_099, delay_share_090,  PK (run_id, kind, object_key, bit))

`dmax_source` is `exhaustive`, `full-report` or `report` (2.1); `trunc_*` is 1, 0 or -1
(unknown, 2.3); `req_spread_ns` is the largest `max_req - min_req` over the reported paths of a
pair. `source_kind` is `attribution` (an odin3 `attribution.json`: has objects) or `report` (a VPR
`report_timing.setup.rpt`: path-level only, no HDL link); `source_sha256` the sha256 of that input;
`analysis_n` the `--timing_report_npaths` of a re-run, null for the original.

`records` rows for the per-run scalars, registry metrics (level `routed`, kind `imported`, measurer
`import-timing`; the unit in `metrics.toml`): `timing.nc_paths_090`, `timing.nc_paths_095`,
`timing.nc_paths_099`, `timing.nc_endpoints_090`, `timing.nc_endpoints_095`, `timing.nc_endpoints_099`,
`timing.paths_used`, `timing.last_crit`, `timing.truncated_090` (1 or 0). Identity columns come from
the `run` row, so the `record_run` view joins them.

Idempotent: a re-import of a run replaces its rows in all three tables and its records.

## 4. Where the paths come from

The importer takes either an attribution JSON (`FILE --run-id ID`), the `timing` blobs
already in a store (`--from-blobs`: every `run_artifact` of kind `timing`), or a VPR report
(`--report FILE --run-id ID`). The sources per store, measured in Step 1, are in the lane report.
A run with no input is left without a `timing_run` row; it is counted as `cannot` with the reason.
`--full-report FILE --full-requested N` adds an exhaustive report of the same run (2.1). A run
whose id is not in the store is refused before any write; one import is one transaction (all
three tables and the records, or none). A truncated run is re-analysed only on its stored routing (VPR `--analysis`, same architecture and
options, never re-place or re-route) under the Norns VPR lock.

## 5. Privacy

Object keys pass through `Scrubber.text` and `check_clean`; paths in an attribution are already
placeholders (`$OUT`, `$ODIN3`) or design-relative. No host, no `/home`. `mimir privacy-check` is run on
every store after writing.

## 6. Tests

On a small committed attribution fixture (`tests/fixtures/timing/`, a reduced copy of an odin3
fixture, MIT, same author, with a NOTICE line) and synthetic path lists with known answers: crit of
a hand-computed set, histogram bins, truncation, bit rows, idempotence, migration 4 to 5, old store
readable, privacy, v4 read-only open (bytes and mtime), `mimir migrate`, exact max_req from an
exhaustive report, truncation unknown, structure `via`, path-based join, one-transaction import,
`timing_rerun` argument building (no VPR run).

No test compares crit with a criticality printed by VPR: VPR 9 prints none (the net timing report
holds slack only). The check is the formula against the source (`calc_relaxed_criticality`, 2.1) and
hand-computed cases.
