# Mimir structures: the `structure`, `structure_member` and `structure_mapping` tables (schema v3)

Date 2026-10-27. Lane: mimir-3 (branch `feat/structures`). Extends `2026-10-27-mimir-schema-v2.md`
additively. Status: spec written with the code; the numbers are in the lane report.

## 1. Purpose, questions, measures

Purpose (Peter 2026-10-27, roadmap E9): the classification of structures in a design, and what each
structure maps to downstream.

- **Mi Q1.7:** which structure classes exist, and what each maps to (LUT cone, carry chain, BLE, CLB, region).
- Groundwork for **Mi Q2.3:** which parameters change the mapping (every row links to its run and flow config).

Measures:
- structure coverage: designs x structure kinds, ground truth (HDL) against detector;
- mapping coverage: structures with a mapping at each level (gate, lut, ble, clb, placed);
- the share of structures lost (joined) by level, as a cross-check against Loki L15;
- detector precision and recall per kind on the Odin micros.

## 2. Principles

1. Additive: schema version 3 adds tables and an index. No v1 or v2 table or row is touched. A v1 or
   v2 store migrates in one transaction; a v3 store opens read only. Tested on a v2 store.
2. Nothing is invented: a kind comes from a rule on the construct kind and the HDL text, or from a
   detector hypothesis; each carries a confidence and its label source.
3. Deterministic: rows in key order, `\n` line ends, floats by `repr`; two exports are byte identical.
4. No absolute home path in a stored text or blob: `mimir.scrub.Scrubber` replaces known roots
   (`$VTR_ROOT`, `$ODIN3`, `$ODIN3_BUILD`, `$LOKI`, `$WS`, `$OUT`) and any other `/home/<user>` by `$HOME`.

## 3. Tables

### 3.1 `structure`
PK `(design, structure_id)`. `design` is the design slug.

| Column | Meaning |
|---|---|
| `structure_id` | HDL: `hdl:<file>:<L.C-EL.EC>` (file scrubbed, span of the construct); detector: `det:<detector>:<run8>:<hypothesis id>` |
| `kind` | controlled vocabulary (3.4) |
| `hdl_span` | `file:L1-L2` of the construct; `''` for a detector structure |
| `construct_chain` | `KIND@file:span` from the block up to its module, joined by `>`; `''` for a detector structure |
| `label_source` | `hdl` (construct kind plus the text of the span) or `detector:<name>` (the Loki detector that proposed it) |
| `confidence` | rule confidence in (0, 1] for `hdl`; `p_comp` of the hypothesis for a detector |
| `run_id`, `config_hash` | the run that produced the row: the flow run (HDL) or the detection run (detector) |

### 3.2 `structure_member`
PK `(design, structure_id, atom)`. The atoms (LUT, flip-flop, carry cell or hard block of the final
BLIF, by its hash name) that belong to the structure. It is what the comparison and the mapping rows
are computed from, and it lets a later analysis recompute them.

### 3.3 `structure_mapping`
PK `(design, structure_id, run_id, level)`; `run_id` is the **flow run whose map** the row was
computed in (for a detector structure this differs from `structure.run_id`, which is the detection
run). `config_hash` is that run's flow config.

| Column | Meaning |
|---|---|
| `level` | `gate`, `lut`, `ble`, `clb`, `placed` |
| `n_objects`, `n_pure`, `n_shared` | objects at the level that trace to the structure; those that trace to it alone (L15 pure); the rest |
| `n_gates`, `n_luts`, `n_carry`, `n_ffs`, `n_bles`, `n_clbs` | the count of that kind at that level; NULL where it does not apply |
| `joined_with` | other structure ids that share an object at this level, sorted, comma separated |
| `lost_at_pass` | gate and lut rows of HDL structures: `''` when the structure has a pure object; else the pass of the earliest join record that names it; `born-joined` when no record names it |
| `bbox_x0..y1`, `spread` | `placed` row: bounding box of the sites of the structure's CLBs (from the `site` records, `x=`, `y=`), and the root mean square distance of the sites to their centroid |
| `crit_share` | NULL: the flows were not run with `--timing-attr` (see leftovers) |

Level definitions (Odin III V1.2.0 section 2):
- `gate`: the distinct `gate`-level provenance records reached backward from the final atoms. One record
  is shared by the gates of a word cell (`lower`), so `n_gates` counts **gate records**, not gates. The
  final netlist has no gates; a true gate snapshot (Loki `audit snap`) was not run.
- `lut`: atoms. `n_luts` counts `.names` atoms, `n_ffs` `.latch`, `n_carry` `adder` subckts.
- `ble`, `clb`: the `ble` and `clb` records of `odin3-prov-post` that the structure's atoms sit in. A BLE
  or CLB with atoms of two structures is shared (a join by `pack`).
- `placed`: the `site` records of those CLBs; `n_objects` is the distinct sites.

### 3.4 Kind vocabulary
`adder`, `multiplier`, `shifter`, `comparator`, `mux`, `register_word`, `counter`, `fsm`, `memory`, `logic`
(`mimir.schema.STRUCT_KINDS`, enforced by a CHECK). `logic` is the residue: bitwise logic, or a block no
rule recognised. Loki kinds map to it by `mimir.structdet.KIND_MAP` (for example `ff_en`, `register`,
`shift_reg` to `register_word`; `adder`, `subtractor`, `adder_cin`, `hard_add` to `adder`; `eq_const` to
`comparator`; `mux_bit`, `mux_tree` to `mux`). `bus`, `role`, `hard_group` and the units have no Mimir kind
and are not stored.

## 4. Runs (how obtained)

`mimir.structrun` is the command a `tools/heavy-run` call wraps. For each design it runs
`odin3-flow DESIGN --top T --vpr --prov --keep-results --odin3 BIN --out DIR`, then
`odin3-prov-post DIR --top T`, and writes `mimir-run.json`: both command lines, exit codes, per-step
and total time, `ru_maxrss` of the largest child (VPR in practice), host and kernel, start time, the
Odin III commit (997cb609), the VTR commit, the design files and the top. `flow_config` (status `full`
only: every parameter is `given` with a cited recorded line) holds: the Odin III commit, the script
(first line of `odin3.log`), the flow options, the abc script name, sha256, commit and K (BLIF header),
the architecture file, the VTR commit and the VPR driver command (`vpr.log` line 1). Paths and the
design name are placeholders, so every run of the setup shares one `config_hash`. VPR options beyond
that command line are VPR's defaults and are not enumerated. The seed is stored as -1 (not set; VPR's
own default applies). Detection runs (`source = mimir-detect`) have their own config: the Loki command
with every option explicit, the Loki and Odin III commits.

Artifacts in `run_artifact` (scrubbed, xz blobs): `blif`, `map`, `net`, `place`, `route`, `log` (odin3
log, prov-post log, VPR driver log, `summary.json`, `mimir-run.json`).

## 5. Method

HDL structure. In the v2 map, every atom's naming record leads back through `R` lines to source
leaves, each with a construct `C`. A leaf's **structure** is the outermost construct of kind `ALWAYS`,
`CONT_ASSIGN`, `NET_ASSIGN`, `INSTANCE` or `GATE_DECL` on its chain (so an `assign` is one structure, not
its `NET_ASSIGN` child). The kind is `mimir.hdlkind.classify(construct kind, text of the span)`:
sequential `always` is `memory` (indexes a declared array), `fsm` (a `case` whose selector is assigned in
the block), `counter` (`x <= x +- const`) or `register_word`; a combinational block or an `assign` is
`mux` (`?:`, `case`, `if`), `multiplier`, `shifter`, `adder` (binary `+`/`-`), `comparator` or `logic`,
in that precedence; an instance of a RAM or multiplier or `adder` primitive is `memory`, `multiplier`,
`adder`. A block has one kind: a register with an adder in its D input is a `register_word`. Confidences
are fixed per rule (0.3 to 0.9) and are rule-confidence, not probabilities.

Chains come from `name_map_v2.read_name_map` (Odin III's stdlib parser) and `loki.audit.units`
(`leaf_constructs`, `construct_key`) as libraries. Context parents (`ctx=`) are skipped as Loki does.

Separable and lost follow `loki.audit.loss.separable`: an object is pure when its unit set has one
member; a structure is separable when it has a pure object. With a single final map the audit's
pass-by-pass `first loss` is replaced by V1.2.0 7.1 item 4: the first (lowest-numbered) `join` record
whose `cons` names the structure. `born-joined` (L15's status name) is a structure that never had a pure
object and no record names. The L15 cross-check counts stmt-level units with `loki.audit.units`
(`anchor`, `reduce_units`) and `separable`/`reached` on the same atoms; they are records
`structure.l15_units_reached` and `structure.l15_units_separable` (and the block counts) at level `lut`.

Detectors. `loki re --floor f1-k6 --detectors wordfirst,hard,ff_pattern,mux,arith,seqfn,fsm,bus,unit,role,wordgroup`
runs on the run's BLIF (hash names; its nets are the atom names). Top-level hypotheses (no parent) with
`p_comp >= 0.5` and a kind in `KIND_MAP` are stored; their atoms are the atoms named by their nets.
MCNC has no HDL: detector rows only, `lut` level (no map, no ble/clb/placed).

Comparison (`mimir.structdet.compare`). A detector structure matches the HDL structure that holds most
of its atoms (at least half of its atoms; ties to the smaller id). It is correct when the kinds agree.
Precision of a kind = correct / detected. Recall of a kind = HDL structures of that kind that a correct
detector structure matched / HDL structures of that kind that have atoms.

## 6. Metrics (records, `source = mimir-structures`, level `lut`)

`structure.blocks_reached`, `structure.blocks_separable`, `structure.l15_units_reached`,
`structure.l15_units_separable`, `structure.atoms_unattributed`; all in `mimir/data/metrics.toml`.

## 7. Gates

ruff, `mypy --strict`, `unittest`, CI green. Additive migration tested (v2 to v3). Two-run
byte-identical CSV export of the three tables. Every new run's flow config is `full`. No `/home/` in
committed files or blobs.

## 8. Agent defaults

- Schema version 3, not "2 with extra tables": the version number is what tells a lane-2 reader to
  refuse the store, and the migration is additive.
- The structure unit is the process-level block, not the L15 stmt unit; the L15 stmt-unit counts are
  stored beside it for the cross-check.
- One kind per block, by a fixed precedence; confidences are rule constants.
- Gate level counts gate records (section 3.3).
- `crit_share` stays NULL (no `--timing-attr` run).
- Seed -1, VPR defaults not enumerated (section 4).
