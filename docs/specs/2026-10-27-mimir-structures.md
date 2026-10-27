# Mimir structures: the `structure`, `structure_member` and `structure_mapping` tables (schema v3)

Date 2026-10-27, fix round 1 the same day. Lane: mimir-3 (branch `feat/structures`). Extends
`2026-10-27-mimir-schema-v2.md` additively. Status: spec written with the code; the numbers are in
the lane report.

## 1. Purpose, questions, measures

Purpose (Peter 2026-10-27, roadmap E9): the classification of structures in a design, and what each
structure maps to downstream.

- **Mi Q1.7:** which structure classes exist, and what each maps to (LUT cone, carry chain, BLE, CLB, region).
- Groundwork for **Mi Q2.3:** which parameters change the mapping (every row links to its run and flow config).

Measures:
- structure coverage: designs x structure kinds x source (HDL against detector);
- mapping coverage: structures with a mapping at each level (gate, lut, ble, clb, placed);
- the share of structures lost (joined) by level, as a cross-check against Loki L15;
- detector agreement with the HDL labels on the Odin micros: a confusion matrix (primary) and
  precision and recall per kind.

## 2. Principles

1. Additive: schema version 3 adds tables and an index. No v1 or v2 table or row is touched. A v1 or
   v2 store migrates in one transaction; a v3 store opens read only. Tested on a real v2 store
   (`tests/fixtures/v2-e6f5777.db`, made by the code of mimirIII main e6f5777, every table filled).
2. Nothing is invented: a kind comes from a rule on the construct kind and the HDL text, or from a
   detector hypothesis; each carries a confidence (NULL when no rule ran) and its label source.
3. Deterministic: rows in key order, `\n` line ends, floats by `repr`, NULL written as `\N`; two
   exports are byte identical.
4. No absolute home path in a stored text or blob: `mimir.scrub.Scrubber` replaces known roots
   (`$VTR_ROOT`, `$ODIN3`, `$ODIN3_BUILD`, `$LOKI`, `$WS`, `$OUT`) and any other `/home/<user>` by
   `$HOME`; every blob is checked before it is written.
5. A commit is stored as given only when it is a 40-hex SHA that was recorded; otherwise it is
   `unknown` (never an empty string, never the commit of the current directory).

## 3. Tables

### 3.1 `structure`
PK `(design, structure_id)`. `design` is the design slug.

| Column | Meaning |
|---|---|
| `structure_id` | block: `hdl:<file>:<L.C-EL.EC>` (file scrubbed, span of the construct); operator: the same scheme for the operator construct plus the suffix `:op`; detector: `det:<detector>:<run8>:<hypothesis id>` |
| `kind` | controlled vocabulary (3.4) |
| `hdl_span` | `file:L1-L2` of the construct; `''` for a detector structure |
| `construct_chain` | `KIND@file:span` from the construct up to its module, joined by `>` (a cycle in the parent links ends it); `''` for a detector structure |
| `label_source` | `hdl` (construct kind plus the text of the span) or `detector:<name>` (the Loki detector that proposed it) |
| `confidence` | rule confidence in (0, 1] for `hdl`, NULL when no rule ran (`unknown`); `p_comp` of the hypothesis for a detector |
| `run_id`, `config_hash` | the run that produced the row: the flow run (HDL) or the detection run (detector) |
| `granularity` | `block` (a process, assign or instance), `operator` (a `BINARY` or `TERNARY` expression inside a block) for HDL rows; `''` for a detector row |
| `parent_id` | an operator row: the `structure_id` of its block; else `''` |

### 3.2 `structure_member`
PK `(design, structure_id, run_id, atom)`. The atoms (LUT, flip-flop, carry cell or hard block of the
final BLIF, by its hash name) that belong to the structure, in the run `run_id`. It is what the
comparison and the mapping rows are computed from. Re-importing a design deletes the design's old
HDL and detector rows (structure, member, mapping) first, so no row of an earlier run stays.

### 3.3 `structure_mapping`
PK `(design, structure_id, run_id, level)`; `run_id` is the **flow run whose map** the row was
computed in (for a detector structure this differs from `structure.run_id`, which is the detection
run). `config_hash` is that run's flow config.

| Column | Meaning |
|---|---|
| `level` | `gate`, `lut`, `ble`, `clb`, `placed` |
| `n_objects`, `n_pure`, `n_shared` | objects at the level that trace to the structure; those that trace to it alone (L15 pure); the rest |
| `n_gates`, `n_luts`, `n_carry`, `n_ffs`, `n_bles`, `n_clbs`, `n_sites` | the count of that kind at that level; NULL where it does not apply. `n_clbs` is set on `clb` rows only and `n_sites` on `placed` rows only (a placed row counts sites, not CLBs) |
| `joined_with` | other structure ids that share an object at this level, sorted, comma separated. An operator row does not list its own block |
| `lost_at_pass` | see 3.5 |
| `bbox_x0..y1`, `spread` | `placed` row: bounding box of the sites of the structure's CLBs (from the `site` records, `x=`, `y=`), and the root mean square distance of the sites to their centroid |
| `crit_share` | `lut` rows of a run with `--timing-attr`: the share of the critical path's data delay (`timing.critical_data_delay_ns`, path 1 of `timing/attribution.json`) carried by the structure's atoms (sum of the `delay_ns` of the path nodes whose atom is a member). Shares of structures that share atoms overlap. NULL elsewhere |

Level definitions (Odin III V1.2.0 section 2):
- `gate`: the distinct `gate`-level provenance records reached backward from the final atoms. One record
  is shared by the gates of a word cell (`lower`), so `n_gates` counts **gate records**, not gates. The
  final netlist has no gates; a true gate snapshot (Loki `audit snap`) was not run.
- `lut`: atoms. `n_luts` counts `.names` atoms, `n_ffs` `.latch`, `n_carry` `adder` subckts. A structure
  reached only by gate records has no `lut` row; those are counted in `structure.gate_only_structures`.
- `ble`, `clb`: the `ble` and `clb` records of `odin3-prov-post` that the structure's atoms sit in. A BLE
  or CLB with atoms of two structures is shared (a join by `pack`).
- `placed`: the `site` records of those CLBs; `n_objects` is the distinct sites.

### 3.4 Kind vocabulary
`adder`, `multiplier`, `shifter`, `equality`, `relational`, `mux`, `register_word`, `counter`, `fsm`,
`memory`, `logic`, `unknown` (`mimir.schema.STRUCT_KINDS`, enforced by a CHECK).
- `equality` is `==`, `!=`, `===`, `!==`; `relational` is `<`, `<=`, `>`, `>=`. The old `comparator`
  mixed the two, and a Loki `eq_const` (equality with a constant) is an equality, not a comparator.
- `logic` is the residue: bitwise logic, or a block no rule recognised.
- `unknown` is a structure whose HDL text was not available: no rule ran, confidence NULL. They are
  counted in `structure.blocks_unknown`.

Loki kinds map by `mimir.structdet.kind_of`: `ff_en`, `ff_srst`, `register`, `shift_reg`, `lfsr` to
`register_word`; `adder`, `subtractor`, `adder_cin`, `hard_add` to `adder`; `eq_const` to `equality`;
`comparator` to `equality` when its operator (`params.op`) is `eq` or `ne`, else to `relational`;
`mux`, `mux_bit`, `mux_tree` to `mux`; `hard_mul` to `multiplier`; `hard_mem` to `memory`; `counter`,
`fsm` as themselves. `bus`, `role`, `hard_group` and the units have no Mimir kind and are not stored.
A decoder (`case` on a word with constant arms) is an `equality` term for the detector and a `mux` for
the HDL rule; the confusion matrix shows that disagreement and no `decoder` kind hides it.

### 3.5 `lost_at_pass`
HDL rows at levels `gate` and `lut`:
- `''`: the structure has a pure object (separable).
- `<pass>`: no pure object, and the earliest (lowest numbered) `join` record of V1.2.0 3.3 that names
  the structure at a level of the filter below is made by that pass. A block is named by a construct
  inside it (`cons` are anchors); an operator by the statement that holds it.
- `instance:<pass>`: the same, for a `join=instance` record (the same construct reached through two
  instances; named by the record's own leaves, since `cons` never holds instance members).
- `capped`: no pure object and no record names it, but a record behind its objects has `lossy=cap`
  (`cons` lists 16 of the constructs it joined), so it may have been joined unseen. Not `born-joined`.
- `born-joined`: a block with no pure object that no record names (L15's status name).
- `intra-statement`: an operator with no pure object that no record names: merged with a construct of
  its own statement, which V1.2.0 3.3 does not call a join.

Level filter: a `lut` row looks at join records of level `word`, `gate`, `lut` and `ble`; a `gate`
row at `word` and `gate`. A join after packing (`clb`, `site`) is not a loss of the LUT-level
structure (the LUT cone is intact), so it is not counted; the `clb` and `placed` rows show it through
`n_pure` and `joined_with`.

## 4. Runs (how obtained)

`mimir.structrun` is the command a `tools/heavy-run` call wraps. It requires `VTR_ROOT` (a git
checkout; the VTR commit is that checkout's HEAD) and refuses to start when either commit is empty.
For each design it runs `odin3-flow DESIGN --top T --vpr --prov --keep-results --timing-attr
--odin3 BIN --out DIR` (under the Norns VPR lock, which is held for the flow step: Odin III runs for
seconds inside it and then VPR; VPR cannot be locked alone from outside the flow), then
`odin3-prov-post DIR --top T` (no lock), and writes `mimir-run.json`: both command lines, exit
codes, per-step and total time, `ru_maxrss` of the largest child (VPR in practice), host and kernel,
start time, the Odin III commit and the VTR commit, the design files and their sha256, the sha256 of
every source file the name map lists, the top, and the build facts of the Odin III binary.

Odin III commit. It is the HEAD of `--tree`, not of the binary. The run records the binary's
`--version` text and sha256 and three checks: the tree has no change, the build directory's
`CMAKE_HOME_DIRECTORY` is the tree, the binary is newer than the HEAD commit. The commit is `given`
only when all three hold; otherwise the parameter is `unknown` with the source "inferred: ..." and
the config is `partial`.

`flow_config` is `full` only when every parameter has a value and a cited source. It holds: the
Odin III commit and binary, the script (first line of `odin3.log`), the flow options, the abc script
name, sha256, commit and K (BLIF header), the architecture file (the driver command, `vpr.log` line
1), the VTR commit, the VPR driver command, the VPR command line and **every option of VPR's own
"options" block** (`vpr/run/vpr_stdout.log`, each with its line; this includes the placement seed
`placer_opts.seed`, the packer, placer and router options VPR ran with). The two options that hold the
channel width the run settled on are left out of the config hash. The seed is also cross-checked with
the VTR default read from `$VTR_ROOT` at the recorded VTR commit (`place.seed_default`,
`vpr/src/base/read_options.cpp:2645-2647`); without the checkout that parameter is
`default-unrecorded` and the config is `partial`, and the import refuses. Paths and the design name are
placeholders, so every run of the setup shares one `config_hash`.

The `run` row's `arch` is read from the driver command and `seed` from the options block; an import
fails when either is not recorded. Detection runs (`source = mimir-detect`) have their own config: the
Loki command with every option explicit, the wall limit, the Loki and Odin III commits. A detection
run's `arch` is the flow run's, or `''` for an MCNC BLIF (no flow, no architecture). Its `origin`
starts with `status=<ok|differs|timeout|failed>; exit=<n>; final_equiv=<status>;`. Loki exits 1 when
its rebuilt netlist is not equivalent (`final_equiv = differs`, loki/re/main.py:104-107) and also on an
internal error: exit 1 is accepted (`differs`) only with an `overlay.json` and `report.json` whose
`final_equiv.status` is `differs`; every other non-zero exit, and a wall-limit kill, is a recorded
`failed` or `timeout` run that stores no structure. The stderr tail and the exit status are the
`detect_log` artifact.

Locks. Odin III and Loki run inside `tools/heavy-run`, one design per call. The caller sets
`ODIN3_HEAVY_OK=1` (heavy-run exits 77 without it; `structbatch` refuses to start without it).

Artifacts in `run_artifact` (scrubbed, xz blobs): `blif`, `map`, `net`, `place`, `route`, `timing`
(`attribution.json`, when the run had `--timing-attr`), `log` (odin3 log, prov-post log, VPR driver
log, VPR stdout log, `summary.json`, `mimir-run.json`, `timing.log`), `hdl` (the design files), and
for a detection run `detect_log`. An import reads the HDL texts from the files on disk only after
their sha256 equals the one recorded when the run ended; a changed file is refused.

## 5. Method

HDL structures. In the v2 map, every atom's naming record leads back through `R` lines to source
leaves, each with a construct `C`.

- **Block structure.** A leaf's block is the outermost construct of kind `ALWAYS`, `CONT_ASSIGN`,
  `NET_ASSIGN`, `INSTANCE` or `GATE_DECL` on its chain (so an `assign` is one structure, not its
  `NET_ASSIGN` child). The kind is `mimir.hdlkind.classify(construct kind, text of the span)`. Rules in
  order, the first match wins: an instance of an Odin III primitive (`single_port_ram`,
  `dual_port_ram` memory; `multiply` multiplier; `adder` adder; exact module names, Odin III
  `src/frontends/verilog/soft_blocks.c:13-14` and `src/passes/partial_map/hm_kit.c:36-43`; confidence
  0.9) or a module name ending in `_ram` (memory, 0.4, a name pattern); a sequential `always` is
  `memory` (indexes a declared array), `fsm` (a `case` whose selector is assigned in the block),
  `counter` (`x <= x +- const`) or `register_word`; a combinational block or an `assign` is `mux` (`?:`,
  `case`, `if`), `multiplier`, `shifter`, `adder` (binary `+`/`-`), `relational`, `equality` or `logic`
  in that precedence. The precedence is why a block with a `?:` and a `+` is a `mux`: the selection
  shapes the block, and the arithmetic is named by its operator row. A block with no text is
  `unknown`, confidence NULL. Confidences are fixed per rule (0.3 to 0.9) and are rule-confidence, not
  probabilities.
- **Operator structure.** A `BINARY` or `TERNARY` construct that is a leaf of an atom or a gate
  record, in a block that is a structure, and whose kind is not `logic`: `TERNARY` is `mux`; a `BINARY`
  is classified by the root operator of its span text (`hdlkind.binary_operator`: the last operator of
  the lowest precedence outside brackets; `+ -` adder, `*` multiplier, `<< >> <<< >>>` shifter,
  `< <= > >=` relational, `== != === !==` equality; confidence 0.9). Bitwise and logical operators,
  `/`, `%` and `**` have no operator row; they stay in the block's residue. Operator rows are kept
  beside the block rows (`granularity` says which); a block with an adder in its D input is still a
  `register_word` row and has an `adder` operator row under it.
- **Atoms of a structure.** Block: the atoms with a leaf in the block. Operator: a leaf is mapped to
  the nearest operator structure at or above it, else to its block; a block unit is dropped when the
  atom has an operator unit inside it (a construct and its own parent are not distinct, as in L15).

Chains come from `name_map_v2.read_name_map` (Odin III's stdlib parser) and `loki.audit.units`
(`leaf_constructs`, `construct_key`) as libraries. Context parents (`ctx=`) are skipped as Loki does.
Atoms whose name the map does not know, or with no HDL leaf, are counted in
`structure.atoms_unattributed` and belong to no structure.

Separable and lost follow `loki.audit.loss.separable`: an object is pure when its unit set has one
member; a structure is separable when it has a pure object. With a single final map the audit's
pass-by-pass `first loss` is replaced by V1.2.0 7.1 item 4 (see 3.5). The L15 cross-check counts
stmt-level units with `loki.audit.units` (`anchor`, `reduce_units`) and `separable`/`reached` on the
same atoms; they are records `structure.l15_units_reached` and `structure.l15_units_separable` at level
`lut`. The audit files do not hold Loki's final-snapshot separable count, so the comparison gives a
lower bound (`kept`, `late`) and an upper bound (plus the `lost` units that are pure again later).

Detectors. `loki re --floor f1-k6 --detectors wordfirst,hard,ff_pattern,mux,arith,seqfn,fsm,bus,unit,role,wordgroup`
runs on the run's BLIF (hash names; its nets are the atom names). Top-level hypotheses (no parent) with
`p_comp >= 0.5` and a kind of the map in 3.4 are stored; their atoms are the atoms named by their nets.
MCNC has no HDL: detector rows only, `lut` level (no map, no ble/clb/placed).

Comparison (`mimir.structdet`). The HDL side is the **scoring set**: all operator rows, plus each block
row with the atoms no operator of it holds (its residue; a block with no operator row is whole).
Structures with no atoms are left out. A detector structure matches the scoring-set structure that
holds most of its atoms, at least half of the detector's atoms, ties to the smaller id; a detector
structure with no atoms matches nothing. It is correct when the kinds agree.
- Confusion matrix (primary): HDL kind x detector kind, one pair per detector structure (HDL kind
  `none` when it matches nothing) and one `(kind, none)` pair per HDL structure no detector matched.
- Precision of a kind = correct / detected. Recall of a kind = scoring-set structures of the kind that a
  correct detector structure matched / scoring-set structures of the kind. The report prints how many of
  those are operator-level and how many block-level.

## 6. Metrics (records, `source = mimir-structures`, level `lut`)

`structure.blocks_reached`, `structure.blocks_separable` (blocks only), `structure.operators_reached`,
`structure.blocks_unknown`, `structure.gate_only_structures`, `structure.l15_units_reached`,
`structure.l15_units_separable`, `structure.atoms_unattributed`; all in `mimir/data/metrics.toml`.

## 7. Gates

ruff, `mypy --strict`, `unittest` (no environment variable needed: the tests use vendored copies of
the two libraries when the checkouts are not set, `tests/fixtures/deps/README.md`), CI green. Additive
migration tested on a real v2 store. Two-run byte-identical CSV export of the three tables. Every new
run's flow config is `full` only if every parameter has a cited value. No `/home/` in committed files
or blobs.

## 8. Agent defaults

- Schema version 3, not "2 with extra tables": the version number is what tells a lane-2 reader to
  refuse the store, and the migration is additive.
- The structure unit is the process-level block, plus an operator row under it; the L15 stmt-unit
  counts are stored beside them for the cross-check.
- One kind per block, by a fixed precedence; confidences are rule constants.
- Gate level counts gate records (section 3.3).
- `crit_share` is the critical-path delay share of path 1 (3.3).
- The Norns lock is held for the flow step, not for VPR alone (section 4).
