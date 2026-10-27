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

Placer family: VPR in the VTR commit used (3c9a4d23b2) runs the analytical flow by default
(analytical placement, then annealing refinement). Norns rows from the default flow are labelled
`analytic` (an agent default; see the report). Rows of flows known to be annealing from a random
start are not in the imported files.

## 5. Measurers

### 5.1 Netlist model
`mimir.blif` parses BLIF (`.model .inputs .outputs .names .latch .subckt .end`, comments,
continuations) and flattens hierarchy: a `.subckt` of a model defined in the file is inlined; a
`.subckt` of a `.blackbox` model is a hard node with the directions from its model; an undefined
model is an error and the design is skipped. Node kinds: `pi`, `const` (a `.names` with no inputs),
`comb` (a `.names`: a gate or a LUT), `latch`, `hard`.

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
- edge length: for each fanin pin of a comb node, level(sink) - level(driver) >= 1. `edge_len_hist`
  (bin = length, lengths above 32 in bin `33+`), `edge_len_mean`, `edge_len_max`.
- fanout: sinks per driving node (comb, latch and hard fanin pins, plus one per PO and one per
  latch D input counted as a pin). `fanout_hist` (bin = fanout, above 32 in `33+`), `fanout_mean`,
  `fanout_max`.
- reconvergence: a *stem* is a node with at least two distinct comb sinks. A stem is *reconvergent*
  if two of its sink branches reach a common comb node no more than `W = 8` levels above the deepest
  sink of the stem. The search is bounded by 5000 visited nodes per stem; a stem that hits the bound
  before a reconvergence is found is counted in `reconv_truncated` and not as reconvergent. `reconv_stems`, `reconv_stem_fraction`,
  `reconv_span_mean` (mean level distance from the stem to its nearest reconvergence node). A node has
  one output net, also for hard blocks with several outputs.

Unit-test constructions with known answers: a chain, a balanced tree, a diamond, a ladder mesh.

### 5.3 Rent measurer
Method: recursive bisection of the node set (comb, latch, hard; PIs and POs are the outside world)
with METIS through `pymetis`, and a pins-against-blocks curve.

- Graph for the partitioner: each net with k >= 2 non-PI pins gives a clique (k <= 8) or a star from
  the driver (k > 8); integer edge weight 840 // (k - 1). The hypergraph is only approximated for
  partitioning; terminals are counted exactly on the nets.
- Terminals of a block: the nets with a pin inside the block and a pin outside it, where a PI driver
  and a PO sink count as outside.
- Curve: at each depth the mean block size B (nodes) and mean terminals T over the blocks. Recursion
  stops when a block has fewer than 2 nodes. Seeds fixed in a list (default 1, 2, 3); each seed gives
  its own curve and fit.
- Fit: least squares of log T on log B. The fit range is `4 <= B <= N / 32` (N = nodes). The upper
  limit excludes region II, the large-partition end of the curve where T falls below the power law.
  The `4` and the `32` are Mimir choices, not taken from a source. At least 3 depths must lie in the
  range (so N >= 512), otherwise the fit is skipped and counted as skipped.
  **Disclosure:** the first choice was `N / 8`. An exploratory look at regular meshes showed that the
  curve is already rolling off at `N / 8`, so the limit was tightened to `N / 32`. The mesh validation
  therefore does not test this one parameter independently; the chain, the random graph and the
  seed test-retest do not depend on it. Exploratory fits of a 64 x 64 mesh were 0.438 (N/8), 0.462
  (N/16), 0.473 (N/32), 0.484 (N/64); a 20 x 20 x 20 mesh gave 0.589, 0.623, 0.641, 0.656.
- Metrics: `rent_p`, `rent_k` (the coefficient, T at B = 1 from the fit), `rent_r2`, `rent_points`,
  `rent_curve_T` (bin = depth, value = mean T), `rent_curve_B`, and `partitioner` provenance in the
  measurer version (`rent-1/pymetis-<version>`).
- References: the rule is Landman and Russo 1971; Christie and Stroobandt 2000 interpret it;
  METIS is Karypis and Kumar 1998. Their full texts were not read in this lane; the registry cites
  them for the rule, the interpretation and the partitioner only, not for numerical values.

## 6. Validation (gates before any measurer is trusted)

- Hutton-style: hand-built netlists with known answers as unit tests.
- Rent: a 1-D chain (p = 0, tolerance 0.05), a 2-D mesh of 64 x 64 (p = 0.5, tolerance 0.1), a 3-D
  mesh of 20 x 20 x 20 (p = 2/3, tolerance 0.1) and a random graph of 2048 nodes with 3 fanin pins
  each (near 1; require p > 0.8). The expected exponents of the regular meshes are the asymptotic
  values 1 - 1/d; a finite mesh gives a smaller fit (see the disclosure above), which the tolerances
  allow for. Plus test-retest over partitioner seeds: the standard deviation of p over 5 seeds must be
  below 0.02.
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
