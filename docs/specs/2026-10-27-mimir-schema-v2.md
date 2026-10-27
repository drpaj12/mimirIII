# Mimir schema v2: design meta, flow configuration, run, partition and the compressed store

Date 2026-10-27. Lane: mimir-2 (branch `feat/schema-v2`). Status: spec first, written before any code.

## 1. Purpose, questions, measures

Purpose (Peter 2026-10-27): the dataset, the metrics and how each value was obtained are the core of Mimir,
because they are what gets mined. Design meta and lineage are provenance. Algorithm parameters, and
clustering as algorithmic partitioning, are data. Results are kept compressed, with an off-machine copy.

| Question | Answered by |
|---|---|
| Mi Q1 (classify) | `design_meta` gives ground-truth labels (function class, suite, format) for E4 |
| Mi Q1.7 (structure classes and their mapping) | tables only here (`design`, `run`); `structure` and `structure_mapping` are lane 3 |
| Mi Q2.3 (which parameters change the mapping) | `flow_config`, `flow_param` and `run` |
| Mi Q1.8 / E11 (clustering) | `partition` (algorithmic) and `analysis_result` (data-mining, E11b, schema only) |

Measures this lane reports:
- meta coverage: designs with sourced meta, per field and confidence;
- run coverage: imported runs whose flow config is full (every parameter known) against partial;
- store size before and after compression;
- a snapshot restore test that is byte-identical.

## 2. Principles

1. Schema version 2 adds tables. It never changes a v1 table. `records` keeps its columns, its primary key
   and its meaning (one measured value). A v1 store migrates in place, losslessly.
2. Every fact keeps where it came from. Meta rows carry `source` and `conf`; flow parameters carry `conf`
   and `source`; blobs are named by their sha256.
3. Never invent. A value that no source gives is stored as `missing` (meta) or `unknown` (flow parameter),
   not guessed. A config with an unknown parameter is `partial`.
4. Deterministic: sorted keys, `\n` line ends, UTF-8. The same input gives the same rows and the same CSV.
5. No absolute home path is written into a committed file or a stored text. Sources are named relative to
   their root.

## 3. Tables

All text columns are `NOT NULL` unless a column says NULL. `conf` columns use a closed set.

### 3.1 `design`
One row per design version.

| Column | Meaning |
|---|---|
| `slug` PK | stable human key, `<suite>/<name>`: `mcnc20/alu4`, `norns/boundtop`, `loki/<dataset>/<name>` |
| `design_hash` | sha256 of the design's defining file (see `hash_kind`) |
| `hash_kind` | `blif`, `hdl`, `design.json`, or `slug` when no file is available (hash of the slug text, marked) |
| `suite` | suite label: `mcnc20`, `norns`, `loki:<dataset>` |
| `name` | the short name used in `records.design` |
| `origin` | where the file was read, relative to its root (`vtr:vtr_flow/benchmarks/blif/alu4.blif`) |

The brief keys a design by hash plus slug. The slug is the stable key every child table uses; the hash is the
current content. When a design is re-mapped its hash changes and the slug stays: the old hash is kept as the
`parent_hash` of a new `design_lineage` step. `design_hash` is indexed, so a join on the hash works too.

`design_source(source, name, slug)` PK `(source, name)`: maps the `(records.source, records.design)` pair to a
slug, so a record can reach its design.

### 3.2 `design_meta` (long form)
`(slug, field, value, source, conf)`, PK `(slug, field)`. `conf` in `primary`, `secondary`, `inferred`,
`missing`. `value` is `''` when `conf = missing`. Fields follow the research lane
(`suite`, `original_file`, `original_format`, `intent`, `function_class`, `author`, `institution`, `year`,
`lineage_gaps`, plus `vtr_file`, `vtr_rev`). The research file's `<field>_note` text for a missing field is
appended to `source` as `note: ...`, never kept as the value.

`lineage_gaps` is the number of lineage steps with `conf = missing`; the conf of that row is the lineage
conf, **derived** from the steps: the weakest conf among the other steps, and `primary` only when no step is
missing. Fix round 1 changed 12 MCNC circuits from `primary` to `secondary` (one missing step each) and
`mcnc.toml` carries the derived values.

A design with no research meta gets rows written by `register_designs` (source starts `mimir-register`):
`records_source` and `repo_path` (where its defining file was found, `vtr:` or `norns:` relative path), both
`inferred`, and `suite`, `original_file` and the label fields `missing`. `suite` is never the lane label
(`norns`). A later registration refreshes those rows while they are `inferred` or `missing` (it can fill
`repo_path` when a checkout appears); `primary`, `secondary` and research-file rows are not touched.
Vocabulary: `data/meta/README.md`.

### 3.3 `design_lineage`
`(slug, step_no, tool, script, parent_hash, source, conf)`, PK `(slug, step_no)`. Ordered steps from the
original file to the measured file. `parent_hash` is `''` unless we hold the earlier artifact (then it links
the chain). A step the sources do not document has `conf = missing`; it is a known gap, not a hidden one.

### 3.4 `flow_config` and `flow_param`
`flow_config(config_hash PK, name, config_text_reconstructed, text_kind, status, origin)`:
- `config_hash`: sha256 of the canonical JSON of `(config_text_reconstructed, params)`. A `given` parameter
  counts with its value; any other counts with its key and class only, and `arch.arch_file_sha256` is left out,
  so an import with and without `$VTR_ROOT` (or the tool checkouts) gives the same hash;
- `name`: short label, for example `norns-r3/stock` (round and arm);
- `config_text_reconstructed`: the command text **rebuilt** from the scripts, not copied from a log: the
  runner command template or the Odin script lines, with paths and the design name replaced by placeholders
  (`<arch>`, `<design>`). `text_kind` is `reconstructed` (Norns: from the scripts) or `recorded-normalised`
  (Loki: the script list `meta.json` recorded, the design file name replaced);
- `status`: `full` when every parameter row is known and has a cited source, else `partial`;
- `origin`: the script files and line ranges the text and parameters came from.

`flow_param(config_hash, step, key, value, conf, source)`, PK `(config_hash, step, key)`. One row per
parameter per step. `step` in `odin`, `abc`, `pack`, `place`, `route`, `arch`. `conf`:
- `given`: a source states the value; `source` is `file:line` (script, plan or `meta.json` field). A value
  parsed from the arm token (a beta, a scale, a seed family) is `given` and cites the line that builds the token;
- `default`: the parameter was left to the tool's default. `value` is the actual default and `source` names the
  tool version and the line it was read from (for example Odin III `lib/abc/vtr.abc:1-12` at tag `v1.1.0`, or
  `read_options.cpp:2443-2450` of VTR 3c9a4d23b2);
- `default-unrecorded`: left to a default, but the tool version that ran is not recorded, or its source was
  not available at import. `value` is `''`;
- `unknown`: no source found; `value` is `''`.
`status = partial` exactly when a row is `unknown` or `default-unrecorded`, or has no source.

**Arm tables.** The arms of each Norns round are listed in `mimir/armtables.py` (`ARM_TABLES`), each with the
script line that defines it. An arm that is not in its round's table is never defaulted: the import skips its
runs and prints the count with the reason (`mimir import-runs` then exits 1).

**Odin III build.** Rounds 5 and 6 name Odin III v1.1.1 (a1cf6ffd; plans round5.md:44-46, round6.md:18-19).
For rounds 1-4 and 7 the build that wrote each BLIF is not recorded (`odin3_commit` is `unknown`, the abc
default script `default-unrecorded`). The BLIF set is `runs/<design>/netlist/<design>.blif` for every round
(`matrix.blif_of`); round 7 re-uses the BLIFs of rounds 1-5 (round7.md:11).

### 3.5 `run`
One row per (design x flow config x seed) that has records.

| Column | Meaning |
|---|---|
| `run_id` PK | sha256 of the key `(source, design, arch, seed, arm, config_hash, tool_commit, input_sha256)`, each part escaped (`\` and `\|`), joined with `|`, first 16 hex |
| `slug` | the design |
| `config_hash` | the flow config |
| `source`, `design`, `arch`, `seed`, `arm`, `family` | the record identity columns (see 4); `design` is the short name |
| `tool_commit`, `input_sha256` | the record columns of the same name; part of the key |
| `tool_commits` | `name=sha;...`, `''` when the importer had none |
| `command_line` NULL | the actual command line; NULL when the source did not keep it |
| `time_s` NULL, `peak_rss_mib` NULL | `vpr.flow_time` and `vpr.max_rss` of level `routed`, bin `''`; NULL when absent or when the run has more than one such row (the same run stored twice: the value is ambiguous and is counted, not picked) |
| `host` NULL | NULL when not recorded |
| `origin` | the source file the run came from |

`UNIQUE(source, design, arch, seed, arm, config_hash, tool_commit, input_sha256)` matches the key. `level` is
not part of it: one run has records at several levels. Records with the same run columns but a different
`family`, `tool_commit` or `input_sha256` are different runs. Re-import is an UPSERT that rewrites only the
derived columns, so `command_line`, `host` and `run_artifact` rows a runner filled in stay. `flow_config` and
`flow_param` rows that no run uses are removed in the import transaction.

`run_artifact(run_id, kind, blob_sha256)`, PK `(run_id, kind)`: the artifacts of a run by blob hash
(`blif`, `map`, `net`, `place`, `route`, `log`). Imported runs have no stored artifact yet; the table is
filled when a runner calls `mimir blob put`.

### 3.6 `partition`
Algorithmic partitioning (Peter 2026-10-27: "clustering" means packing and partitioning algorithms).

| Column | Meaning |
|---|---|
| `partition_id` PK | sha256 over `(algorithm, algorithm_version, params, seed, slug, input_hash, assignment_blob)`, first 16 hex |
| `algorithm`, `algorithm_version` | for example `norns-recluster`, `aapack`, `hmetis`, `pymetis`; the version is the commit the data records, else the importer's checkout (see `version_kind`) |
| `params` | canonical JSON of every parameter |
| `seed` | -1 when none |
| `version_kind`, `dirty` | `recorded` (the source stored the commit) or `importer-checkout` (the version is the checkout the importer read, with `dirty = 1` when the scripts differ from that commit) |
| `seed_conf` | `confirmed-data`, `confirmed-script` (the script calls the clusterer with its default seed) or `default-unconfirmed` |
| `slug` | the design partitioned |
| `input_hash` | sha256 of the netlist or the run output the partition was computed from; `missing:<file>` when that file is not available |
| `n_objects`, `n_clusters` | counts |
| `assignment_blob` | sha256 of the xz blob holding `object<TAB>cluster` lines, sorted by object. Object names are normalised first: an absolute path after `@` (`x@/home/u/vtr/vtr_flow/a.v:3`) becomes its `vtr_flow/...` tail, so the blob and the ids are machine independent and hold no home path |
| `origin` | the source it was imported from |

Quality metrics are **records**: `records.source = 'partition:<partition_id>'`, `records.design` = the short
design name, metric keys `partition.*` in `metrics.toml`, level `clb` for a packing and `placed`/`lut`
otherwise. The downstream QoR of a partition is a record with the same source (for example the median
objective of the arm that used it).

### 3.7 `analysis_result` (E11b, schema only)
`(analysis_id PK, algorithm, params, feature_set_hash, input_selection, seed, script_hash, script_version,
labels_blob, origin)`. A data-mining clustering or classification run. Per-item labels live in the xz blob
`labels_blob`; the quality (silhouette, ARI, NMI, CV accuracy) is records with source `analysis:<id>`.
No importer in this lane.

## 4. How `records` links to `run` and `partition`

`records` is unchanged. A record reaches its run by the identity subset
`(source, design, arch, seed, arm)`. The view `record_run` does the join:

    CREATE VIEW record_run AS
    SELECT r.rowid AS record_rowid, u.run_id, u.slug, u.config_hash
    FROM records r JOIN run u ON u.source=r.source AND u.design=r.design AND u.arch=r.arch
                              AND u.seed=r.seed AND u.arm=r.arm

A record with no matching run (the measured sets `mcnc`, `norns-netlist`, and Loki counts of floors without
a config) has no row in the view; it still reaches its design through `design_source`. A record reaches a
partition or analysis result by `source = 'partition:<id>'` or `'analysis:<id>'`.

`input_sha256`, `tool_commit` and `script_hash` of a record stay as they are; the run's `tool_commits` repeats
the commit for joins on the run.

## 5. Migration v1 to v2

`meta.schema_version` is `'1'` in a v1 store. Opening a store with `Store(path)` reads the version **before
any write**:
1. version `'2'`: nothing is written; `Store(path, readonly=True)` opens it with `mode=ro`;
2. version `'1'`: in one transaction create every v2 table and the view, then set `schema_version = '2'`.
   No v1 row is touched. If anything fails the transaction is rolled back and the file stays v1 (tested by a
   migration that fails on its fifth statement). A v1 store cannot be opened read only;
3. no `meta` table (a new file): one transaction creates `meta`, `records` and the v2 tables;
4. any other version: `ValueError`, the file untouched, the connection closed.

Lane 1's code (`Store` of main 848f303) refuses a v2 store with `ValueError` and does not change the file
(its create-if-missing statements find the tables). Tests: `tests/fixtures/v1-848f303.db` is a v1 store
written by the lane-1 code (three rows); the lossless test migrates a copy, exports CSV and compares it
byte for byte with a store that was v2 from the start.

## 6. Importers (read only sources)

- **MCNC meta**: `data/meta/mcnc.toml` and `data/meta/mcnc-sources.md` (copies of the research lane's
  files). `mimir import-meta` reads them and writes `design`, `design_meta`, `design_lineage` for the 20
  circuits. The design hash is the sha256 of the VTR BLIF when `$VTR_ROOT` is set, else `hash_kind = slug`.
- **Designs already in the store**: every `(source, design)` pair in `records` is registered with a slug
  (`mcnc20/<n>`, `norns/<n>`, `loki/<dataset>/<n>`), with the rows described in 3.2.
- **Norns configs and runs**: `mimir/armtables.py` builds one config per (round, arm, design kind) from the
  explicit arm tables (3.4), with the reconstructed command template, the script lines it came from, and the
  parameters. Arm tokens give the parameters that vary (affinity weight, annealing scale, start kind, seed family).
  `mimir import-runs` reads the records already stored, groups them by the run key (3.5), and creates one `run`
  per group in one transaction. Tool defaults are read from the checkouts named by `$MIMIR_ODIN3`,
  `$VTR_ROOT` and `$MIMIR_NORNS_SRC` (git objects at the named versions); without them the parameter is
  `default-unrecorded`. No jsonl is re-read.
- **Loki configs and runs**: from the `script` list of each `meta.json` (recorded, the design file name
  replaced by `<design>`). One config per distinct script text; parameters parsed from the script (arch,
  `abc --lut K` or `--gates`, the pass list). `odin3_version` and `abi_version` are `given`; the Odin III
  commit is `unknown` (`meta.json` holds versions). The abc default script and the `lut_k` default of a floor
  with no `--lut` are read from the Odin III tag of that version (`v1.1.0`: `lib/abc/vtr.abc`,
  `src/passes/abc/args.c:114`) and are `default`; without the checkout they are `default-unrecorded`. The
  Loki configs are `partial` because the commit is unknown.

## 7. Compressed blob store and snapshots

- `mimir blob put FILE` stores `FILE` content-addressed: path `$MIMIR_BLOBS/<ab>/<sha256>.xz`, where `<ab>` is
  the first two hex characters. `$MIMIR_BLOBS` defaults to `work/mimir-data/blobs` under the workspace
  (given as an argument `--blobs` in tests). Compression is `lzma` preset 6 with CRC64. The name is the sha256 of the
  uncompressed bytes. `put` of an existing hash checks the stored file and rewrites it when its content does
  not match the name; a write goes to a temp file, is fsynced, then renamed (the temp is unlinked in a `finally`).
  `verify` of an empty list checks nothing; no argument checks every blob.
- `mimir blob get SHA OUT` decompresses and checks the hash. `mimir blob verify [SHA...]` re-reads each blob,
  decompresses it and compares the hash; non-zero exit on any mismatch.
- `mimir snapshot DB DIR` writes the store as a compressed SQL dump (`mimir.sql.xz`, written by `mimir.snapshot.dump_lines`: DDL, rows in primary-key order, floats
  by `repr` so they round-trip exactly) plus `MANIFEST.json`
  (`schema_version`, per-table row counts, sha256 of the dump, sha256 of the canonical store text, and
  `blob_refs`: every blob sha256 the tables refer to). The dump, the hashes, the counts and the refs come from
  one read transaction; each file is written under a temp name, fsynced and renamed, the manifest last. Parquet
  needs `pyarrow` (extra `parquet`) and is optional: `--parquet` writes one zstd file per table when
  pyarrow is installed. The default snapshot is the xz SQL dump.
- The **canonical store text** is a deterministic dump of the schema (every table, index and view with its
  DDL, `sqlite_master` in type and name order) and of every table, written table by table in sorted
  table-name order, rows in primary-key order, as `\n`-ended lines of JSON arrays (floats by `repr`). It does
  not depend on the order SQLite stores rows. The SQL dump is for restoring; the canonical text is what is
  compared.
- `mimir snapshot DB DIR --verify` restores the dump into a temporary database, regenerates the canonical
  text and compares it byte for byte with the canonical text of the source store, and checks that every blob
  in `blob_refs` exists in `$MIMIR_BLOBS` (or `--blobs`) and is intact. It exits non-zero on any difference and
  names each missing blob.

Off-machine copy (F: drive): after the gates, one snapshot of the rebuilt store goes to
`/mnt/f/yggdrasil-archive/<date>/mimir-snapshot-<date>/` with the manifest, its sha256 appended to that
date's `SHA256SUMS` and verified with `sha256sum -c`, and a dated section in the archive README. Nothing
else on that drive is touched, nothing there is deleted, and no live SQLite database is kept there.

## 8. The partition worked example

Source: the Norns round 7 hindsight clustering of `ch_intrinsics`, round `h1`: `runs/r7/ch_intrinsics/h1.affinity.tsv`
is a cluster assignment (atom name, group id) and `h1.recluster.json` holds the clustering statistics
(`cost_before`, `cost_after`, `moves`, `clbs_after`, source arm and seed). Import:
- `partition`: algorithm `norns-recluster`, params from `recluster.json` (source arm, source seed), input hash
  = sha256 of the source run's `.net.gz`, the assignment as a blob;
- records (source `partition:<id>`): `partition.n_objects`, `partition.n_clusters`, cluster-size stats,
  `partition.cost_before`, `partition.cost_after`, `partition.atoms_moved`, and the downstream median objective
  of the `h1` arm and of `stock` from `rounds.json`.

## 9. Gates

ruff, `mypy --strict`, `unittest`, CI green. The v1 to v2 migration tested on a v1 store. Two-run
byte-identical CSV export. The snapshot restore identical. No `/home/` in committed files.

## 10. Agent defaults (to be listed in the report)

- Slugs use the suite label of the source (`mcnc20`, `norns`, `loki/<dataset>`); a Norns design that is also
  an MCNC name still gets its own slug.
- `run_id` is a hash of the run key (3.5), so reimports do not create a second run.
- Quality metrics of a partition are records with source `partition:<id>`, not a separate metric table.
- The canonical store text, not the SQL dump bytes, is the unit of the byte-identical comparison.
