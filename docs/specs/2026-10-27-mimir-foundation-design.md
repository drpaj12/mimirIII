# Mimir III foundation: schema, import, Hutton and Rent measurers (spec)

Lane 1. Purpose: Mimir III is the circuit knowledge base of Yggdrasil III. This lane answers the
measurement part of Mi Q1 ("which characteristics classify circuits?"): are the measurers correct,
how much of designs x levels is covered, and is the import of existing data complete. See
`docs/purpose-draft.md`.

## 1. Scope

In: the schema (version 1), the metric registry, the SQLite store with CSV and Parquet export, the
read-only import of Norns, Loki and Wyrd-atlas data, the Hutton-style structural measurer, the Rent
measurer, validation, and a run over the MCNC set and the netlists found in the imported data.

Out: pattern detectors, routing-demand models, classification, generators, hub wiring.

## 2. Schema (version 1)

One tidy table `records`; one row is one measured value. Columns:

| Column | Meaning |
|---|---|
| design | design name (the netlist or the Norns/Loki design id) |
| source | where the design or run came from (`mcnc`, `norns-r5`, `loki-corpus`, ...) |
| input_sha256 | sha256 of the input file when one exists, else empty |
| tool_commit | commit of the tool that produced the value (VPR, Odin III) when known, else empty |
| script_hash | sha256 of the producing script or file (first 16 hex) when known, else empty |
| level | `hdl`, `elab`, `gate`, `lut`, `ble`, `clb`, `placed`, `routed` |
| arch | architecture name, empty if not applicable |
| seed | integer seed (the tool seed or the partitioner seed), -1 if none |
| arm | placer or experiment arm, empty if none |
| family | placer family: `analytic`, `annealing`, or empty |
| metric | key into the metric registry |
| bin | sub-key for distributions (a level, a fanout value, a depth), empty for scalars |
| value | REAL |
| unit | unit string from the registry |
| measurer | name of the code that computed or imported the value |
| measurer_version | version of that code |
| origin | file and line (relative) the row came from; makes imports idempotent |

`bin` is an addition to the brief's field list: distributions (nodes per level, edge-length and
fanout histograms, the Rent curve) need a sub-key and a tidy table has no other place for it.

Identity (primary key): all columns except `value`, `unit`, `measurer_version`. A second import of the
same input replaces rows with the same identity, so imports are idempotent. Tables are written in
sorted key order, so exports are byte-identical for the same input.

Also `meta(key, value)` holds `schema_version = 1`.

## 3. Metric registry

`mimir/data/metrics.toml`. Per metric: `key`, `description`, `unit`, `level` (list), `kind`
(`measured` by Mimir or `imported`), `measurer`, `definition_source` (`mimir` for definitions that
are ours, or a citation id), `citation` (list of ids in `citations.toml`), `validation`. A test
asserts that every metric written by the code is in the registry and that every citation id exists.

## 4. Import

Read only, deterministic, no new runs. Row counts are reported per source as imported and skipped
with the reason.

- Norns: `data/<design>/runs.jsonl` (round 2 and the base runs), `r3runs.jsonl`, `r4runs.jsonl`,
  `data/r5/runs.jsonl`, `data/r6/runs.jsonl`, and the round 7 corpus and atlas. Each scalar numeric
  field that is in the field map becomes a record; other fields are skipped and counted by name.
- Loki: corpus `manifest.json` files (design, split, benchmark, source) and the per-floor
  `meta.json` counts (nodes, edges, luts, gates, ffs, pi, po) as records at the matching level.
- Wyrd atlas exports (`*.json.gz` in the Norns round 7 data): the per-run scalars.

Placer family, per row from the flow each round recorded (sources read only: the Norns plan files
`docs/plan/round3.md`, `round7.md`, `vtr-interfaces.md` and the runners `scripts/matrix.py`,
`round3.py`, `round4.py`, `r7net.py`). The closed set is `analytic`, `annealing`, empty.

- `analytic` = VPR's default flow in the pinned build: analytical placement (`lp-b2b`, APPack),
  then VPR's annealing refinement at the default schedule, from the flow's own start
  (round3.md "Flow"; round7.md lines 33-36). The family is the one of the start of the flow; the
  refinement stage is part of that flow.
- `annealing` = VPR's anneal from a start that was supplied or random: `--read_initial_place_file`
  continues placement from the file (vtr-interfaces.md line 11), or `--place --net_file` with the
  analytical placer disabled (round7.md lines 271-275), or an initial temperature changed with
  `--anneal_auto_init_t_scale`.
- empty = the flow is not stated for the row.

| Source | Rows | Family | Evidence |
|---|---|---|---|
| norns-r1r2 | `baseline`; `unseeded`, `unseeded-off` at scale 1 | analytic | default flow (matrix.py baseline, no seed) |
| norns-r1r2 | `soft`, `cold`, `cold-r2`, `cold-off`, `hot`, `hot-r2` | annealing | `--read_initial_place_file` (matrix.py, round2.py) |
| norns-r1r2 | `unseeded`, `unseeded-off` at scale other than 1 | annealing | initial temperature changed |
| norns-r1r2 | `hard` | empty | region constraints (`--read_vpr_constraints`); the flow under constraints is not stated |
| norns-r3 | start `analytic` | analytic | default flow |
| norns-r3 | start `seed` | annealing | `--read_initial_place_file` (round3.py) |
| norns-r3-pilot | all | analytic | `--analytical_place` (round3.py) |
| norns-r4 | start `analytic` | analytic | default flow |
| norns-r4 | start `wordseed`, `stagebit` | annealing | `--read_initial_place_file` (round4.py) |
| norns-r5, norns-r6 | all | analytic | default flow (round5.md) |
| norns-r7 (`runs/r7`) | all | analytic | default flow (round7.md lines 33-36) |
| norns-r7 (`runs/r7f`) | all | annealing | annealing from a random start (round7.md lines 271-275) |
| wyrd-atlas-r7 | all | analytic | exports of the round 7 default-flow runs |
| norns-r7-corpus | all | empty | corpus statistics, no placer |

The earlier lane labelled every default-flow and seeded row `analytic`; the table replaces that.
The `norns-experiment.md` sentence "SA from VTR's analytic start" is the design intent; the later
round files describe the flow actually run and are the evidence used.

The `arm` of a Norns row: rounds 1-2 and the round-3 pilot `arm/tag`; round 3 `arm/start`
(e.g. `module-b1/seed`); round 4 `pack/start` (e.g. `norns/wordseed`); rounds 5-7 `arm`. In the
data the round 3 and 4 `tag` already held the start (and the seed, redundantly), so the rows of the
real data were distinct; the importer relied on that by accident and the arm now carries the start
by construction, with no seed in the arm string.

Idempotence: an import is one transaction that first deletes the rows already stored for the
(source, origin file) pairs it is about to write, then inserts. A reordered or rewritten source
file gives the same rows as a fresh import (the line number in `origin` can move). `measure-set`
writes by identity (`INSERT OR REPLACE`) because its origins are whole files.

Loki: `tool_commit` is empty unless `meta.json` records a commit; the meta files hold only version
strings (`odin3_version`, `loki_version`, `abi_version`), which are not commits and are not stored.
`loki.in_train` is set from an explicit map (`train` = 1, `test` = 0); a manifest entry with any
other split value or none is counted as skipped with the reason and sets no value.

## 5. Measurers

### 5.1 Netlist model
`mimir.blif` parses BLIF (`.model .inputs .outputs .names .latch .subckt .end`, comments,
continuations) and flattens hierarchy: a `.subckt` of a model defined in the file is inlined; a
`.subckt` of a `.blackbox` model is a hard node with the directions from its model; an undefined
model is an error and the design is skipped. Node kinds: `pi`, `const` (a `.names` with no inputs),
`comb` (a `.names`: a gate or a LUT), `latch`, `hard`. A signal that is read and never driven becomes
an `undriven` source node (level 0): it is counted in `struct.n_undriven`, not in `n_const` or `n_pi`.
A signal with more than one driver keeps the first driver and is counted in `struct.n_multidriven`.
A `.latch`, `.names` or `.subckt` line with too few arguments raises `BlifError` and the design is
skipped. A latch clock that is a primary input stays a PI node (in `n_pi`); `struct.n_clock_pi`
counts those PIs and they are left out of the fanout histogram (they have no fanout pins).

### 5.2 Hutton-style characterisation
The sources are Hutton et al. DAC 1996 and FPGA 1997 (and Hutton's thesis). **None of the three
could be read in this lane** (the publisher pages block automated access; the thesis was not found
in an open record), so the definitions below are Mimir's own, written in the spirit of the named
characteristics, and they are not claimed to be Hutton's. The registry marks them
`definition_source = mimir`. Comparison with published tables is therefore not possible and no
reference value is used.

Definitions (levelisation: PIs, constants, latch outputs and hard-block outputs are level 0; a comb
node is 1 + the maximum level of its fanin):

- size: `n_comb`, `n_latch`, `n_hard`, `n_pi`, `n_po`, `n_const`; `n_edges` = fanin pins of comb,
  latch and hard nodes.
- `depth`: the maximum comb level.
- shape: `level_width`, bin = level, value = the comb nodes at that level. Bins above 64 are not
  written; `depth` and `n_comb` carry the totals.
- edge length: for each fanin pin of a comb node, level(sink) - level(driver) >= 1. Comb-to-comb
  pins give `edge_len_hist` (bin = length, lengths above 32 in bin `33+`), `edge_len_mean`,
  `edge_len_max`. Pins driven by a source (PI, constant, latch, hard block, undriven) have the
  driver at level 0, so their length is the level of the sink; they are a separate histogram,
  `src_edge_len_hist`, `src_edge_len_mean`, `src_edge_len_max`.
- fanout: sinks per non-constant node (comb, latch and hard fanin pins, plus one per PO).
  `fanout_hist` (bin = fanout, bin `0` = dangling drivers, above 32 in `33+`), `fanout_mean` and
  `fanout_max` over the same nodes. Constants are reported apart in `const_fanout_hist`. Latch
  clock PIs are left out (they have no fanout pins by construction).
- reconvergence: a *stem* is a non-constant node with at least two distinct comb sinks. A stem is
  *reconvergent* if two of its sink branches reach a common comb node no more than `W = 8` levels
  above the deepest sink of the stem. The search advances all branches together, one level at a
  time (so the nearest meeting is found first and a large cone on one branch cannot use up the bound
  before another branch is searched), and is bounded by 5000 visited nodes per stem. A stem that
  hits the bound before a reconvergence is found is *truncated*: counted in `reconv_truncated` and
  left out of both the fraction and the span. Every reconvergence metric has `bin` = the stem kind
  (`comb`, `pi`, `latch`, `hard`, `undriven`), so PI or latch stems (level 0, spans measured from
  level 0) are not mixed with comb stems. `reconv_stems`, `reconv_truncated`,
  `reconv_stem_fraction` = reconvergent stems / (stems - truncated), `reconv_span_mean` (mean level
  distance from the stem to its nearest reconvergence node). The window W = 8 and the bound are
  named in the registry definition of `reconv_stem_fraction`. A node has one output net, also for
  hard blocks with several outputs.

Unit-test constructions with known answers: a chain, a balanced tree, a diamond, a ladder mesh.

### 5.3 Rent measurer
Method: recursive bisection of the node set (comb, latch, hard; PIs and POs are the outside world)
with METIS through `pymetis`, and a pins-against-blocks curve.

- Graph for the partitioner: each net with k >= 2 pins inside the block being split (PIs and POs
  are not pins) gives a clique (k <= 8) or a star (k > 8); integer edge weight
  `max(1, 840 // (k - 1))` (the floor of 1 keeps the weight non-zero for k > 841). The star is rooted
  at the driver when the driver is inside the block, and at the first in-block pin when the driver
  is outside it (a PI driver, or a driver in the other half). k is counted per block, so a net can
  change from a star to a clique at deeper depths. The hypergraph is only approximated for
  partitioning; terminals are counted exactly on the nets.
- Terminals of a block: the nets with a pin inside the block and a pin outside it, where a PI driver
  and a PO sink count as outside.
- Curve: at each depth the mean block size B (nodes) and mean terminals T over the blocks. A block with
  fewer than 4 nodes is not split but stays in the deeper depths, so every depth's mean is over
  the whole partition and not only over blocks that can still split; recursion ends at the first
  depth in which no block can be split. Seeds fixed in a list (default 1, 2, 3); each seed gives
  its own curve and fit.
- Fit: least squares of log T on log B. The fit range is `4 <= B <= N / 32` (N = nodes). The upper
  limit excludes region II, the large-partition end of the curve where T falls below the power law.
  The `4` and the `32` are Mimir choices, not taken from a source. **The limit is fixed at `N / 32` and
  was tuned on meshes (exploratory)**; it is not changed by the tests below. At least 3 depths must lie in the
  range (so N >= 512), otherwise the fit is skipped and counted as skipped.
  **Disclosure:** the first choice was `N / 8`. An exploratory look at regular meshes showed that the
  curve is already rolling off at `N / 8`, so the limit was tightened to `N / 32`. The mesh validation
  therefore does not test this one parameter independently; the chain, the random graph and the
  seed test-retest do not depend on it. Exploratory fits of a 64 x 64 mesh were 0.438 (N/8), 0.462
  (N/16), 0.473 (N/32), 0.484 (N/64); a 20 x 20 x 20 mesh gave 0.589, 0.623, 0.641, 0.656.
- Few points: a fit on fewer than 5 depths is flagged by `rent.low_confidence` = 1 (one value per
  seed; `rent.points` carries the count). A chain of 1024 nodes has 4 points and is flagged.
- Metrics: `rent_p`, `rent_k` (the coefficient, T at B = 1 from the fit), `rent_r2`, `rent_points`,
  `rent_curve_T` (bin = depth, value = mean T), `rent_curve_B`, and `partitioner` provenance in the
  measurer version (`rent-1/pymetis-<version>`).
- References: the rule is Landman and Russo 1971; Christie and Stroobandt 2000 interpret it;
  METIS is Karypis and Kumar 1998. Their full texts were not read in this lane; the registry cites
  them for the rule, the interpretation and the partitioner only, not for numerical values.
  **Method source:** no source describing the measurement of Rent's rule by recursive bisection
  with a graph partitioner was read. The bisection procedure, the terminal count and the fit range
  are Mimir's own construction; Landman and Russo 1971 and Christie and Stroobandt 2000 are cited
  for the rule and its interpretation only, and neither is claimed to describe this method.

## 6. Validation (gates before any measurer is trusted)

- Hutton-style: hand-built netlists with known answers as unit tests.
- Rent, with the fit limit fixed at `N / 32` (tuned on meshes, exploratory, so the mesh checks do
  not test the limit independently):
  - chain of 1024: p = 0 by construction (a chain cuts at 2 nets), tolerance 0.01.
  - meshes: the expected p is derived from a finite-size model before the check. A cubic block of
    side s in a d-dimensional mesh of side n has on average T = 2 d s^(d-1) (1 - s/n) terminals
    (d upper faces with inside drivers, d lower faces with outside drivers, minus the faces on the
    mesh edge), fitted over the same block sizes N / 2^k and range as the measurer: 0.454 for the
    64 x 64 mesh and 0.589 for the 20 x 20 x 20 mesh (the model assumes ideal cubic blocks; the
    asymptotic value 1 - 1/d is not used). The measurement must lie within 0.04 (2-D) and 0.07 (3-D)
    of the model, and within 0.01 of a regression baseline measured at the fixed limit (5 seeds):
    2-D 0.471 (sd 0.0024), 3-D 0.640 (sd 0.0013). The baselines are recorded measurements, not
    independent truth.
  - region II, the direct check of the fit range: a synthetic curve T = k B^p (p = 0.62, k = 4) with
    a roll-off above B = N / 32 must give p to 1e-9 and 10 points; with the limit raised to N / 4 the
    same test must fail (it does: the roll-off enters), which shows the test has power.
  - a uniform random graph of 2048 nodes with 3 distinct fanin pins chosen from all other nodes:
    near 1 asymptotically; measured 0.8915 (sd 0.001), required > 0.85 and within 0.01 of that
    baseline. `random_dag` (each node reads 3 earlier nodes, a DAG and not a uniform random graph)
    is kept as a separate baseline, 0.866.
  - test-retest over partitioner seeds: sd of p over 5 seeds below 0.006 (observed 0.0024 at most)
    on both meshes and the random graph.
- Published values: none compared, with the reason in section 5.2.

## 7. Runs

MCNC BLIFs from `$VTR_ROOT/vtr_flow/benchmarks/blif/` (4-LUT netlists, level `lut`), the Norns BLIFs
under `runs/<design>/netlist/` (level `lut` with hard blocks) and the Loki corpus netlists
(`f1-k6` and `f2` = LUT level, `f3` = gate level; the floor id is stored in `arch`), smallest first.
Rent is run on netlists of 512 to 100000 nodes: fewer than 512 cannot give 3 depths in the fit range,
and larger ones are skipped for Rent with the reason recorded. Hutton runs on all.

## 8. Conventions

Python 3.11+, stdlib-only base install, ruff and `mypy --strict`, unittest, deterministic outputs
(sorted keys, `\n`, UTF-8), no absolute home paths in committed files (env vars or arguments).

## 9. Validation results (lane 1, fix round 1, 2026-10-27)

| Measurer | Construction | Known answer | Observed | Tolerance | Source of the known answer |
|---|---|---|---|---|---|
| struct | chain of 5 | depth 5, width 1 per level, 4 comb-to-comb edges of length 1, 1 source edge | as expected | exact | construction |
| struct | balanced tree, 8 PIs | depth 3, widths 4, 2, 1; 6 comb-to-comb and 8 source edges | as expected | exact | construction |
| struct | diamond | 1 reconvergent stem (kind pi), span 2 | as expected | exact | construction |
| struct | diamond behind a cone of 6400 nodes | the diamond stem reconverges at distance 2 | found (the depth-first search reported it truncated) | exact | construction |
| struct | 3 x 3 ladder mesh | depth 5, widths 1, 2, 3, 2, 1, 4 reconvergent comb stems | as expected | exact | construction |
| rent | chain of 1024 | p = 0 | 0.000 (5 seeds), 4 points, flagged low-confidence | 0.01 | construction (a chain cuts at 2 nets) |
| rent | 64 x 64 mesh | 0.454 | 0.471 (5 seeds, sd 0.0024) | model band 0.04; baseline 0.01 | finite-size model, section 6; derived before the check |
| rent | 20 x 20 x 20 mesh | 0.589 | 0.640 (5 seeds, sd 0.0013) | model band 0.07; baseline 0.01 | finite-size model, section 6; blocks are not cubes |
| rent | uniform random graph, 2048 nodes, 3 fanin | near 1 | 0.8915 (5 seeds, sd 0.001) | > 0.85; baseline 0.01 | asymptote 1; not derived at this size |
| rent | random DAG (earlier nodes), 2048 nodes, 3 fanin | baseline | 0.866 (5 seeds, sd 0.0015) | 0.01 | measurement at the fixed limit |
| rent | synthetic T = 4 B^0.62 with roll-off above N/32 | p = 0.62, k = 4, 10 points | exact to 1e-9; with the limit at N/4 p is off by more than 0.1 | 1e-9 | construction (region II check) |
| rent | test-retest, MCNC (20), Norns netlists (197), Loki (59) | repeatable across seeds | median sd over 3 seeds 0.0043, max 0.032 (276 netlists) | sd 0.006 on the constructions | measurement |

Published values: none compared. The three Hutton sources and the Kundarewich and Rose paper could
not be read, so no table or page is cited as a reference value.

The mesh and random-graph numbers are regression baselines measured at the fixed fit limit
`N / 32` (tuned on meshes, exploratory); only the chain, the model band and the region II test
have an expected value that does not come from the measurer. The model band is wide because the
model assumes cubic blocks.

A caution for users of `rent.p`: strongly clustered designs (the Norns synthetic chain, mesh and
tree families) give a curve whose terminals fall as the blocks shrink inside a cluster, so the
single-exponent fit gives p near 0 or negative with a low `rent.r2`. Read `rent.p` together with
`rent.r2`, `rent.points` and `rent.low_confidence` (354 of 828 fits, 12 of the 20 MCNC circuits,
use fewer than 5 points because N / 32 is small).
