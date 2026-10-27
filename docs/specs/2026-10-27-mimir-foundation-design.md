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

### 5.2 Hutton characterisation
Lane 1b (2026-10-27) replaced the lane-1 definitions, which were Mimir's own because the sources
were unreadable, by those of Hutton's PhD thesis (Toronto 1997; `hutton1997thesis`, page numbers
are the printed ones) and Hutton, Rose and Corneil, TCAD 2002 (`hutton2002tcad`). Each metric's
registry entry gives the pages. The lane-1 definitions that differ are kept as `struct.mimir_*`
metrics. The full table of source definition against Mimir definition is in section 10.1.

Levelisation: PIs, constants, latch outputs and hard-block outputs are delay 0 (thesis p. 45: PI
or DFF is delay 0); a comb node is 1 + the maximum delay of its fanin. Clock PIs are left out of
Hutton's counts (thesis p. 26). Summary of the metrics (all `struct.`): `size`, `n_io`, `n_comb`,
`n_latch`, `n_po`, `n_edges`, `fanin_max`; `depth`; `level_width` (shape, bin 0 = data PIs and
latches); `edge_len_*` (every fanin pin of a comb node, PI pins included); `fanout_*` (edges leaving a
node; a PO pin is not an edge); `fanout_shape` (thesis Table 3.4); `reconv_R`; `seq_levels`,
`seq_shape`, `n_back_edges`. Mimir-only: `mimir_edge_len_comb_*` and `mimir_edge_len_src_*` (the
fix-round split of edge length), `mimir_fanout_po_*` (PO pins counted), `mimir_reconv_*` (the
window search of lane 1: a stem is reconvergent if two of its sink branches meet within W = 8
levels, bounded by 5000 visited nodes, per stem kind), `mimir_reconv_R_total_fanin`,
`mimir_reconv_R_seqcone`, `seq_unreached`, `n_hard`, `n_const`, `n_pi` (includes clocks).

Reconvergence number (thesis p. 33-34): for a PI x, R(x) is the sum over the out-cone of x of
log2(fanin of y inside the cone) divided by the cone size; R(G) is the mean of R(x) over the data
PIs weighted by cone size. The thesis wording of eq. 3.2 ("fanin(y)") does not say whether the
fanin is counted inside the cone; the Kirchhoff derivation of p. 33 (spanning out-trees of the
cone) and the text of eq. 3.1 ("fanin 2 in out-cone") do, and the published values agree (section
10.3), so the in-cone reading is `reconv_R`. The out-cone follows combinational edges (forward
edges, p. 45). The sequential reconvergence R_s (determinants of the Kirchhoff matrix, p. 50-53)
is not implemented.

Sequential level (thesis p. 45; TCAD 2002 Def. 2.2): 0 for a PI, 1 + the level of the D input
for a latch, the minimum over the fanins otherwise: the fewest latches on any path from a PI.

Unit-test constructions with known answers: a chain, a balanced tree, a diamond, a ladder mesh,
and the 12-node out-cone of thesis Figure 4.3 (R = log2(8) / 12, p. 52).

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
  **Lane 1b:** Hutton's thesis (p. 14-16) describes the usual way to get r: partition, sample
  modules (P_i, B_i), and regress log P on log B, with P and B averages over modules; it notes that
  the rule is unstable for fewer than 5 modules (Landman and Russo), that different partitioners give
  different values, and that the intrinsic parameter is the minimum over all partitioners. Mimir's
  recursive bisection with mean T and mean B per depth is that procedure and its fit keeps at least
  32 blocks, so nothing in the thesis contradicts the Rent measurer and it is unchanged. The thesis
  gives no Rent exponent for any MCNC circuit (it quotes 0.5 to 0.8 and the values of other
  authors), and the TCAD papers give none either; no Rent comparison with a published MCNC value is
  possible. **Method source (lane 1):** no source describing the measurement of Rent's rule by recursive bisection
  with a graph partitioner was read. The bisection procedure, the terminal count and the fit range
  are Mimir's own construction; Landman and Russo 1971 and Christie and Stroobandt 2000 are cited
  for the rule and its interpretation only, and neither is claimed to describe this method.

### 5.5 Inputs of the routing-demand line (for lane 2; not implemented here)
Fang and Rose, FPGA 2008 (`fang2008fpga`, p. 139-148) and Fang's MASc thesis (`fang2007masc`) model
the routing demand (tracks per channel) from architecture parameters (Fs, Fcin, Fcout, L, Eqv) and
two circuit-side inputs from El Gamal's master-slice model, W_avg = lambda * R^2:
- lambda: the average number of used inputs per logic block, measured by packing the circuit
  (paper Sec. 4.1, p. 142; Sec. 5.1, p. 145-146; thesis Sec. 3.1, p. 34, Sec. 4.2, p. 47-50, Sec.
  5.1.1, p. 112-116).
- R: the average two-pin connection length in logic blocks, measured by placement estimation (paper
  p. 142 and 146, where R averages 4.43 over the benchmark circuits and cluster sizes 1 to 16, lower at 1;
  thesis Sec. 5.1.2, p. 116).
Circuit size (4-LUT BLE count) and net count only balance the training and validation sets
(thesis Table 3.2, p. 40, and Table 3.3, p. 42); they are not model inputs. Rent's rule appears
only as related work (thesis Sec. 2.3.1, p. 16; the paper, p. 140); Rahman's model needs a Rent
exponent but Fang's does not. Neither lambda nor R is a netlist property: both need a packer or a
placement, so they belong to the placed and clustered levels of the schema.

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

## 9. Validation results (lane 1, fix round 1, 2026-10-27; struct rows were renamed in lane 1b, see section 10)

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

Published values: compared in lane 1b, section 10 (the sources were read there; in lane 1 they were
not).

The mesh and random-graph numbers are regression baselines measured at the fixed fit limit
`N / 32` (tuned on meshes, exploratory); only the chain, the model band and the region II test
have an expected value that does not come from the measurer. The model band is wide because the
model assumes cubic blocks.

A caution for users of `rent.p`: strongly clustered designs (the Norns synthetic chain, mesh and
tree families) give a curve whose terminals fall as the blocks shrink inside a cluster, so the
single-exponent fit gives p near 0 or negative with a low `rent.r2`. Read `rent.p` together with
`rent.r2`, `rent.points` and `rent.low_confidence` (354 of 828 fits, 12 of the 20 MCNC circuits,
use fewer than 5 points because N / 32 is small).

## 10. Lane 1b (2026-10-27): the Hutton definitions and the published values

Sources (local read-only copies, never committed): Hutton thesis 1997 (T), Hutton, Rose and Corneil
TCAD 2002 (H02), the preprint of the combinational TCAD paper (HC), Kundarewich and Rose TCAD 2004
manuscript (K04), Kundarewich MASc 2002, Fang and Rose FPGA 2008 and Fang MASc 2007. Page numbers
of T are printed pages (PDF page - 9). The DAC 1996 and FPGA 1997 PDFs and the combinational
TCAD preprint have unreadable text layers; the preprint was read as images, the other two only by
title page. The thesis appendix pages 141-153 (PDF) have damaged streams and were not used.

### 10.1 Definitions: source against Mimir

| Metric | Source definition | Mimir before (lane 1) | Now | Status |
|---|---|---|---|---|
| size n | n_PI + n_LOG + n_DFF, PO nodes and clocks not counted (T p. 46; H02 p. 928 and fn. 1) | not defined | `size` | new, follows |
| n_PI, n_PO, n_IO | T p. 25 | `n_pi` includes clocks | `n_pi` kept (Mimir); `n_io`, `size` leave clocks out; `n_po` follows | matched (clock caveat) |
| n_LOG, n_DFF, edges | T p. 46, p. 26; H02 p. 928 | `n_comb`, `n_latch`, `n_edges` | unchanged; `n_edges` also counts hard-block pins | matched |
| delay d(x), depth | longest path from a PI; PI and DFF are 0 (T p. 28, p. 45; H02 Def. 2.1) | `depth` | unchanged | matched |
| shape | nodes per delay level, level 0 holds PIs and DFFs (T p. 28, p. 30; H02 Def. 2.4) | `level_width` from level 1 | level 0 added | changed |
| edge length | d(y) - d(x) over every edge, PI edges included (T p. 31; H02 Def. 2.5-2.6) | comb-to-comb only; PI edges apart | `edge_len_*` = every pin into a comb node; the old split is `mimir_edge_len_comb_*` and `mimir_edge_len_src_*`. FF edges are left out: T p. 46 says length 1, K04 p. 14 says 0, H02 Def. 2.5 gives delay(y) - delay(x) | changed |
| fanout | edges leaving a node; a PO is a property of the node, not an edge (T p. 26) | counted PO pins | PO pins not counted; old as `mimir_fanout_po_*` | changed |
| fanout shape | total fanout per delay level (T p. 32, Table 3.4) | none | `fanout_shape` | new, follows |
| reconvergence R | cone-size-weighted mean over PIs of sum log2(fanin in cone) / cone size (T p. 33-34, eq. 3.1-3.2; HC p. 3) | window search (stems meeting within 8 levels) | `reconv_R`; the window search is `mimir_reconv_*` | changed (the lane-1 metric is Mimir-only) |
| sequential level, back and FF edges, seq. shape | T p. 45-47; H02 Def. 2.2, 2.3, 2.5 | none | `seq_levels`, `seq_shape`, `n_back_edges` | new, follows |
| sequential reconvergence R_s | determinant of the Kirchhoff minor, log_k, size-normalised (T p. 50-53) | none | not implemented | open |
| GI/GO shapes, signature, clone | T p. 48-50; H02 Def. 2.7-2.11 | none | not implemented (generation side) | out of scope |
| locality (spread, span, wirelength of an embedding) | T p. 36-42 | none | not implemented | out of scope |
| Rent exponent | not measured in T or the TCAD papers for MCNC | `rent.*` | unchanged | no comparison possible |

Counts: 5 metrics matched unchanged (`n_comb`, `n_latch`, `n_po`, `n_edges`, `depth`); 4 changed
(`level_width`, `edge_len_*`, `fanout_*`, and the reconvergence metric, replaced by `reconv_R`);
7 new and following the source (`size`, `n_io`, `fanin_max`, `fanout_shape`, `seq_levels`,
`seq_shape`, `n_back_edges`); the rest are Mimir-only (`mimir_*`, `n_hard`, `n_const`, `n_pi`,
`seq_unreached`, the bookkeeping counts), with `definition_source = mimir` in the registry.

### 10.2 Like-for-like check

The VTR checkout (commit 3c9a4d23b2) holds the whole MCNC set mapped to k-input LUTs in
`vtr_flow/benchmarks/blif/2` to `8` (the thesis p. 24 maps each circuit to k = 2 to 8 with sis and
Flowmap; the VTR README names the same tools). Measured with `mimir measure-set mcnc-k2` and
`mcnc-k4` (198 and 199 netlists): the largest `.names` width is 2 in `2/` and 4 in `4/` and in the
20 top-level circuits (`struct.fanin_max`), so the k = 4 comparisons are 4-LUT against 4-LUT and the
k = 2 comparisons 2-LUT against 2-LUT. The thesis tables on 4-LUTs are Tables 3.1-3.4 and 4.1 and the
k = 4 columns of Table 4.2 (T p. 24: most analysis on 4-LUT circuits); Table 3.5 is 2-LUT (its dsip,
0.27, equals the k = 2 column of Table 4.2). A match shows the same circuit and the same mapping;
a gap shows a different version of the circuit or of the mapper.

### 10.3 Comparison with the published values

Tables 3.1 to 3.4 (T p. 27, 30, 31, 32), 4-LUT, the ten circuits of the tables (all are in `4/`).
Size, delay and maximum fanout, then the vectors (shape, edge length, the printed part of the fanout
distribution, delay-fanout), compared entry by entry:

| circuit | size, delay, max fanout (published / Mimir) | shape | edge length | fanout dist. | delay-fanout | edges |
|---|---|---|---|---|---|---|
| cht | 102, 2, 46 / same | 2 of 3 entries differ (44 vs 46, 11 vs 9) | equal | equal | 157 vs 183 | 202 / 202 |
| 9symml | 106, 6, 34 / same | 2 differ (57 vs 58, 2 vs 1) | equal | equal | equal | 324 / 324 |
| C1355 | 115, 4, 16 / same | equal | equal | equal | equal | 280 / 280 |
| bw | 137, 4, 66 / same | equal | equal | equal | equal | 459 / 459 |
| C1908 | 178, 10, 25 / same | 2 differ (8 vs 9, 2 vs 1) | equal | equal | equal | 509 / 509 |
| C3540 | 481, 12, 66 / same | equal | equal | equal | equal | 1575 / 1575 |
| x3 | 512, 5, 122 / same | 2 differ (40 vs 43, 10 vs 7) | equal | equal | equal | 1269 / 1269 |
| ex4p | 514 / 572 (delay 5, max 26 equal) | 84 vs 128 first | 1 differs (1248 vs 1262) | 14 vs 72 first | equal | 1426 / 1440 |
| C6288 | 559, 28, 43 / same | 2 differ (first at 15: 29 vs 30) | 7 differ (66 vs 68 first, at 11) | equal | not compared | 2089 / 2023 |
| alu4 | 1536, 7, 249 / same | equal | equal | equal | equal | 5400 / 5400 |

"Edges" is the sum of the published edge-length vector: the Edges column of Tables 3.3 and 3.4 repeats
the size, not the edge count (cht: 102 in both columns, 202 edges). The fanout-distribution rows are
the printed prefix (20 entries; C1355 complete; C6288 five entries, the other zeros not counted) and
the C6288 shape and edge vectors were read from the table image with the repeated entries counted
from the row's length, so the C6288 row carries that uncertainty. Reading of the gaps: size and delay agree for nine of the ten circuits (ex4p
differs in size) and in the four circuits in which every vector agrees (C1355, bw, C3540, alu4) the
definitions and the netlists are the same, which checks size, delay, shape, edge length (with PI
pins), fanout (without PO pins), delay-fanout and max fanout. The edge-length and fanout vectors
agree for eight circuits. The gaps in shape (cht, 9symml, C1908, x3) are one or two nodes moved to an
adjacent level while the edge-length and fanout vectors agree: the table's own rows are
inconsistent there (cht: the delay-fanout entries sum to 158 and the edge-length entries to 202; Mimir's delay-fanout
entries are 183, 19, 0 and sum to 202), so a typing or tooling slip in the table is likelier than a
definition gap; not proven. ex4p and C6288 differ in size or edges, so VTR's netlists of those two
are another version from the thesis's; this is not an error of a definition (alu4, in the same
directory, is exact).

Table 4.1 (T p. 47, H02 Table I) sequential 4-LUT circuits, against the 20 top-level netlists:

| circuit | published: nodes, IOs, n_DFF, edges, n_back, levels, seq. shape | Mimir: LUTs, n_io, latches, n_edges, n_back, levels, shape |
|---|---|---|
| dsip | 1362, 425, 224, 5440, 896, 2, [1590, 224] | 1370, 425, 224, 5672, 896, 2, [1590, 232] |
| s298 | 1930, 9, 8, 6944, 2218, 2, [1636, 305] | 1930, 9, 8, 6952, 2218, 2, [1636, 305] |
| bigkey | 1699, 425, 224, 6108, 1344, 2, [1591, 560] | 1707, 459, 224, 6340, 1344, 2, [1625, 568] |
| clma | 8361, 127, 31, 30114, 5596, 3, [5810, 2640, 3] | 8380, 464, 33, 30411, 5596, 3, [6131, 2641, 3] |

Nodes in Table 4.1 are the LUT count (dsip: 1362 + 228 data PIs = 1590 at level 0). n_back, levels,
n_DFF (three of four) and the level-0 shape of dsip and s298 agree exactly, for all four circuits for
n_back: Mimir's sequential level and back-edge definitions are those of the thesis. In s298 every number agrees
except edges (6952 vs 6944): the difference is the 8 latch D pins, so the published Edges do not
count FF edges while the H02 text (p. 928, sum of fanin over all nodes) does; Mimir follows the text and
`n_edges - n_latch` is the comparable value. dsip and bigkey: VTR's circuit has 8 more LUTs, all at
sequential level 1 (shape 232 vs 224 and 568 vs 560), and bigkey has 34 more PIs (459 vs 425 IOs):
another version of the circuit, not a definition gap. clma differs in PIs, LUTs and latches
(another version; n_back is equal even so).

Reconvergence R, 2-LUT, Table 3.5 (T p. 35; 33 circuits found in `2/`; `my_adder` is `my-adder`; mult32b and
the others of the table not in `2/` are left out). R = Mimir `reconv_R` (combinational cones, T p. 53); R_seq = `mimir_reconv_R_seqcone`
(cones continue through latches); latches = number of latches:

| circuit | published | R | diff | R_seq | diff | latches |
|---|---|---|---|---|---|---|
| parity | 0.00 | 0.000 | 0.000 | 0.000 | 0.000 | 0 |
| decod | 0.00 | 0.000 | 0.000 | 0.000 | 0.000 | 0 |
| count | 0.15 | 0.057 | -0.093 | 0.057 | -0.093 | 0 |
| mux | 0.15 | 0.137 | -0.013 | 0.137 | -0.013 | 0 |
| C1355 | 0.19 | 0.251 | +0.061 | 0.251 | +0.061 | 0 |
| my-adder | 0.21 | 0.159 | -0.051 | 0.159 | -0.051 | 0 |
| C5315 | 0.26 | 0.240 | -0.020 | 0.240 | -0.020 | 0 |
| dsip | 0.27 | 0.338 | +0.068 | 0.357 | +0.087 | 224 |
| des | 0.30 | 0.327 | +0.027 | 0.327 | +0.027 | 0 |
| z4ml | 0.30 | 0.136 | -0.164 | 0.136 | -0.164 | 0 |
| 9symml | 0.31 | 0.257 | -0.053 | 0.257 | -0.053 | 0 |
| C2670 | 0.32 | 0.264 | -0.056 | 0.264 | -0.056 | 0 |
| C7552 | 0.34 | 0.375 | +0.035 | 0.375 | +0.035 | 0 |
| C880 | 0.36 | 0.331 | -0.029 | 0.331 | -0.029 | 0 |
| s208 | 0.38 | 0.087 | -0.292 | 0.489 | +0.109 | 5 |
| s838 | 0.41 | 0.133 | -0.277 | 0.551 | +0.141 | 32 |
| s1196 | 0.41 | 0.343 | -0.067 | 0.376 | -0.034 | 18 |
| C1908 | 0.44 | 0.497 | +0.057 | 0.497 | +0.057 | 0 |
| i10 | 0.47 | 0.383 | -0.087 | 0.383 | -0.087 | 0 |
| sbc | 0.47 | 0.123 | -0.347 | 0.513 | +0.043 | 27 |
| C3540 | 0.50 | 0.491 | -0.009 | 0.491 | -0.009 | 0 |
| alu2 | 0.52 | 0.526 | +0.006 | 0.526 | +0.006 | 0 |
| sqrt8ml | 0.53 | 0.558 | +0.028 | 0.558 | +0.028 | 0 |
| mult16a | 0.54 | 0.148 | -0.392 | 0.455 | -0.085 | 16 |
| C432 | 0.58 | 0.499 | -0.081 | 0.499 | -0.081 | 0 |
| C6288 | 0.63 | 0.644 | +0.014 | 0.644 | +0.014 | 0 |
| apex4 | 0.63 | 0.638 | +0.008 | 0.638 | +0.008 | 0 |
| s400 | 0.63 | 0.235 | -0.395 | 0.683 | +0.053 | 21 |
| clma | 0.63 | 0.349 | -0.281 | 0.766 | +0.136 | 33 |
| bbtas | 0.76 | 0.250 | -0.510 | 0.778 | +0.018 | 3 |
| pdc | 0.79 | 0.682 | -0.108 | 0.682 | -0.108 | 0 |
| s1488 | 0.83 | 0.127 | -0.703 | 0.825 | -0.005 | 6 |
| dk16 | 0.89 | 0.268 | -0.622 | 0.861 | -0.029 | 5 |

Reading: for the 22 circuits without latches the combinational R is within 0.1 of the table for
20, including alu2, apex4, C6288, C3540, sqrt8ml and des; the two larger gaps (z4ml -0.16, pdc -0.11) look like different netlist versions (the table gives no sizes to check), not
the definition. For the 11 circuits with latches the combinational R is 0.28 to 0.70 below the table for 9
(dsip is 0.07 above and s1196 0.07 below) while R_seq is within 0.15 for all 11 (within 0.06 for
s400, s1488, dk16, bbtas, sbc and s1196): in Tables 3.5 and 4.2 the R of sequential circuits behaves like the cone that continues through the
flip-flops, not like the "back edges removed" cone of T p. 53. The text and the table disagree, and Mimir
keeps the text in `reconv_R` and reports the table-like value apart as `mimir_reconv_R_seqcone`. The
reading with the full fanin of each cone node (`mimir_reconv_R_total_fanin`) is 0.96 to 1.00 for every 2-LUT circuit and
1.7 to 1.95 at k = 4, far from every published value, so the in-cone reading is the published one.

Table 4.2 (T p. 55), k = 4 columns (4-LUT netlists; `reconv_R` / `mimir_reconv_R_seqcone`; the k = 2
column is 2-LUT and is in the same format):

| circuit | published R_c k=2 | Mimir k=2 | published R_c k=4 | Mimir k=4 | published R_s k=4 |
|---|---|---|---|---|---|
| elliptic | 0.47 | 0.266 / 0.346 | 0.85 | 0.263 / 0.468 | 0.26 |
| dsip | 0.27 | 0.338 / 0.357 | 0.81 | 0.359 / 0.367 | 0.28 |
| bigkey | 0.53 | 0.335 / 0.655 | 0.89 | 0.356 / 0.955 | 0.83 |
| tseng | 0.49 | 0.289 / 0.731 | 0.78 | 0.303 / 1.147 | 1.04 |
| diffeq | 0.57 | 0.257 / 0.819 | 0.97 | 0.310 / 1.283 | 1.20 |
| s298 | 0.84 | 0.369 / 0.845 | 1.60 | 0.762 / 1.601 | 1.60 |

Only s298 is reproduced (both columns, to 0.01, with R_seq); elliptic, dsip, bigkey, tseng, diffeq are not, with
either value, at k = 4 (gaps 0.1 to 0.7); the 4-LUT netlists of dsip and bigkey are other versions (above) but the
others are not shown to be. Published R_s needs the spanning-tree count, which Mimir does not compute;
R_s is not compared. The table's text (p. 54) says R_c grows with k; Mimir's reconv_R is nearly flat from k = 2
to k = 4 for dsip, bigkey, tseng, elliptic and diffeq (dsip 0.338 to 0.359) and doubles only for s298. This is a gap that stays unexplained.

Sizes, Fang MASc Table 3.2 (p. 40, 4-input BLE counts) against the 20 top-level netlists (LUTs):

| circuit | published BLEs | Mimir LUTs | diff | relative | latches |
|---|---|---|---|---|---|
| clma | 8383 | 8380 | -3 | -0.04% | 33 |
| s38584.1 | 6447 | 6269 | -178 | -2.76% | 1260 |
| pdc | 4575 | 4575 | 0 | 0 | 0 |
| elliptic | 3604 | 3602 | -2 | -0.06% | 1122 |
| frisc | 3556 | 3539 | -17 | -0.48% | 886 |
| s298 | 1931 | 1930 | -1 | -0.05% | 8 |
| diffeq | 1497 | 1494 | -3 | -0.20% | 377 |
| misex3 | 1397 | 1397 | 0 | 0 | 0 |
| tseng | 1047 | 1046 | -1 | -0.10% | 385 |
| s38417 | 6406 | 6096 | -310 | -4.84% | 1463 |
| spla | 3690 | 3690 | 0 | 0 | 0 |
| apex2 | 1878 | 1878 | 0 | 0 | 0 |
| seq | 1750 | 1750 | 0 | 0 | 0 |
| alu4 | 1522 | 1522 | 0 | 0 | 0 |
| apex4 | 1262 | 1261 | -1 | -0.08% | 0 |
| ex5p | 1064 | 1064 | 0 | 0 | 0 |
| apex3 | 869 | 869 | 0 | 0 | 0 |
| apex1 | 700 | 699 | -1 | -0.14% | 0 |
| cps | 757 | 756 | -1 | -0.13% | 0 |
| misex3c | 549 | 549 | 0 | 0 | 0 |
| parker1986 | 663 | 660 | -3 | -0.45% | 161 |

The last five rows are measured on the 4-LUT directory `4/` (`mcnc-k4`), not the 20 top-level files. The published count is a BLE (a LUT, possibly with a flip-flop) and Mimir counts LUTs; the gap is
never positive for Mimir, is 0 for every circuit without latches except apex4 (-1), and is
largest in the two designs with the most latches (s38417, s38584.1); a flip-flop that has no LUT of its own
would explain the sign. Not tested. (Not compared: des_perf, des_area, rs_decoder_1 and 2, mac1, fir_scu_rtl, diffeq_paj_convert, which are
not in `4/` or the top level.)

Rent exponents: none of the sources gives one for an MCNC circuit (T p. 14-16 quotes ranges and other
authors' values, Fang p. 16 the same, H02 and K04 give none), so there is no Rent comparison.

### 10.4 MCNC result, struct and Rent (VTR 3c9a4d23b2, seeds 1-3)

| circuit | LUTs | latches | PI | PO | depth | R | R_seq | Rent p | r2 |
|---|---|---|---|---|---|---|---|---|---|
| tseng | 1046 | 385 | 52 | 122 | 13 | 0.303 | 1.147 | 0.512 | 0.999 |
| ex5p | 1064 | 0 | 8 | 63 | 7 | 1.123 | 1.123 | 0.743 | 1.000 |
| apex4 | 1261 | 0 | 9 | 19 | 6 | 0.898 | 0.898 | 0.733 | 1.000 |
| dsip | 1370 | 224 | 229 | 197 | 3 | 0.359 | 0.367 | 0.331 | 0.988 |
| misex3 | 1397 | 0 | 14 | 14 | 7 | 0.552 | 0.552 | 0.665 | 0.999 |
| diffeq | 1494 | 377 | 64 | 39 | 14 | 0.310 | 1.283 | 0.518 | 0.999 |
| alu4 | 1522 | 0 | 14 | 8 | 7 | 0.501 | 0.501 | 0.575 | 0.998 |
| des | 1591 | 0 | 256 | 245 | 6 | 0.500 | 0.500 | 0.576 | 0.998 |
| bigkey | 1707 | 224 | 263 | 197 | 3 | 0.356 | 0.955 | 0.434 | 0.992 |
| seq | 1750 | 0 | 41 | 35 | 7 | 0.485 | 0.485 | 0.680 | 0.999 |
| apex2 | 1878 | 0 | 39 | 3 | 8 | 0.475 | 0.475 | 0.678 | 0.999 |
| s298 | 1930 | 8 | 4 | 6 | 15 | 0.762 | 1.601 | 0.399 | 0.993 |
| frisc | 3539 | 886 | 20 | 116 | 23 | 0.462 | 1.370 | 0.645 | 1.000 |
| elliptic | 3602 | 1122 | 131 | 114 | 18 | 0.263 | 0.468 | 0.618 | 0.999 |
| spla | 3690 | 0 | 16 | 46 | 8 | 0.970 | 0.970 | 0.651 | 0.999 |
| pdc | 4575 | 0 | 16 | 40 | 9 | 1.006 | 1.006 | 0.690 | 0.999 |
| ex1010 | 4598 | 0 | 10 | 10 | 8 | 1.081 | 1.081 | 0.638 | 0.989 |
| s38417 | 6096 | 1463 | 29 | 106 | 11 | 0.285 | 1.055 | 0.486 | 0.999 |
| s38584.1 | 6269 | 1260 | 39 | 304 | 9 | 0.422 | 0.991 | 0.524 | 0.999 |
| clma | 8380 | 33 | 383 | 82 | 16 | 0.529 | 1.429 | 0.615 | 0.999 |

The Rent code is unchanged in lane 1b; three of the p values differ in the third decimal from the
lane-1 table (dsip 0.334, elliptic 0.620, clma 0.613 there).
