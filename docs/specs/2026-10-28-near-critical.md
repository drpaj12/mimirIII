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
named in VPR's source comment, full text not read). VPR 9 computes it in
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
and `worst_slack` and `max_req` taken over the paths of the report that share its (launch clock,
capture clock) pair. The pair is read from the `clocked by` text of the path's start and end point.
The criticality of an object (a statement, word, bit, module, structure) is the maximum criticality of
the paths through it, as VPR takes the worst criticality over the connections through a pin.

**Approximation, stated.** VPR takes `max_req` over all endpoints; the report holds only the N worst
paths. When all required times of a pair are equal up to the clock uncertainty (one clock, no input or
output delay, which is every run in this store) the two agree to within that spread. Mimir records
`dmax_source = 'report'` and `max_req_ns` so a reader can see the basis. `crit` of a path is
undefined when `max_req + shift <= 0`; such a pair is skipped and counted (`pairs_skipped`).

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
  not say), `paths_in_report`, `paths_used`. The set is truncated at theta when the report is full
  (`paths_in_report >= paths_requested`, or `paths_in_report >= 100` when N is not known: VPR's
  default) and the last path still has crit >= theta; the last path's crit is stored as `last_crit`.
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
| `structure` | `structure_id` | nodes whose `loc` lies inside the structure's `hdl_span` (same file base name); line range when a node has no `loc`. Lane 3 spans are whole lines (`file:L-L`), so two operators on one line share their nodes |

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

Migration 4 to 5 is additive: three tables, one version number. A version 4 store is migrated on open
(not with `readonly=True`); a version 5 store opens as before. A version 4 reader refuses a version 5
store, as a version 3 reader refused version 4.

    timing_run(run_id PK, cpd_ns, worst_slack_ns, paths_requested, paths_in_report, paths_used,
               max_req_ns, dmax_source, pairs, pairs_skipped, last_crit,
               trunc_090, trunc_095, trunc_099, n_endpoints_090, n_endpoints_095,
               n_endpoints_099, source_kind, source_sha256, analysis_n)
    timing_path_hist(run_id, bin, n,  PK (run_id, bin))
    timing_object(run_id, kind, object_key, bit, via, crit_max, n_paths, n_paths_090, n_paths_095,
                  n_paths_099, delay_share_090,  PK (run_id, kind, object_key, bit))

`source_kind` is `attribution` (an odin3 `attribution.json`: has objects) or `report` (a VPR
`report_timing.setup.rpt`: path-level only, no HDL link); `source_sha256` the sha256 of that input;
`analysis_n` the `--timing_report_npaths` of a re-run, null for the original.

`records` rows for the per-run scalars, registry metrics (level `routed`, kind `imported`, measurer
`import-timing`; the unit in `metrics.toml`): `timing.nc_paths_090`, `timing.nc_paths_095`,
`timing.nc_paths_099`, `timing.nc_endpoints_090`, `timing.nc_endpoints_095`, `timing.nc_endpoints_099`,
`timing.paths_used`, `timing.last_crit`, `timing.truncated_090` (1 or 0). Identity columns come from
the `run` row, so the `record_run` view joins them.

Idempotent: a re-import of a run replaces its rows in all three tables and its records.

## 4. Where the paths come from

The importer takes either an attribution JSON (`--attribution FILE --run-id ID`), the `timing` blobs
already in a store (`--from-blobs`: every `run_artifact` of kind `timing`), or a VPR report
(`--report FILE --run-id ID`). The sources per store, measured in Step 1, are in the lane report.
A run with no input is left without a `timing_run` row; it is counted as `cannot` with the reason.
A truncated run is re-analysed only on its stored routing (VPR `--analysis`, same architecture and
options, never re-place or re-route) under the Norns VPR lock.

## 5. Privacy

Object keys pass through `Scrubber.text` and `check_clean`; paths in an attribution are already
placeholders (`$OUT`, `$ODIN3`) or design-relative. No host, no `/home`. `mimir privacy-check` is run on
every store after writing.

## 6. Tests

On a small committed attribution fixture (`tests/fixtures/timing/`, a reduced copy of an odin3
fixture, MIT, same author, with a NOTICE line) and synthetic path lists with known answers: crit of
a hand-computed set, histogram bins, truncation, bit rows, idempotence, migration 4 to 5, old store
readable, privacy.
