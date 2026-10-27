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
`lineage_gaps`, plus `vtr_file`, `vtr_rev`). A design with no meta gets rows for what its source states
(`suite`, `origin`, `path`) marked `inferred`, and rows `missing` for the fields that matter for labels.
Vocabulary: `data/meta/README.md`.

### 3.3 `design_lineage`
`(slug, step_no, tool, script, parent_hash, source, conf)`, PK `(slug, step_no)`. Ordered steps from the
original file to the measured file. `parent_hash` is `''` unless we hold the earlier artifact (then it links
the chain). A step the sources do not document has `conf = missing`; it is a known gap, not a hidden one.

### 3.4 `flow_config` and `flow_param`
`flow_config(config_hash PK, name, config_text, status, origin)`:
- `config_hash`: sha256 of the canonical JSON of `(config_text, params)`;
- `name`: short label, for example `norns-r3/stock` (round and arm);
- `config_text`: verbatim text of the flow: the runner command template or the Odin script lines, with
  paths and the design name replaced by placeholders (`<arch>`, `<design>`);
- `status`: `full` when every parameter row is known, else `partial`;
- `origin`: the file and lines the text came from, relative to the source root.

`flow_param(config_hash, step, key, value, conf, source)`, PK `(config_hash, step, key)`. One row per
parameter per step. `step` in `odin`, `abc`, `pack`, `place`, `route`, `arch`. `conf` in `given` (stated in
the config text), `default` (the tool default, stated by its documentation or source), `unknown` (no source
found; `value` is `''`). `status = partial` exactly when a row has `conf = unknown`.

### 3.5 `run`
One row per (design x flow config x seed) that has records.

| Column | Meaning |
|---|---|
| `run_id` PK | sha256 of the key `(source, design, arch, seed, arm)` joined with `|`, first 16 hex |
| `slug` | the design |
| `config_hash` | the flow config |
| `source`, `design`, `arch`, `seed`, `arm`, `family` | the record identity columns (see 4); `design` is the short name |
| `tool_commits` | `name=sha;...`, `''` when the importer had none |
| `command_line` NULL | the actual command line; NULL when the source did not keep it |
| `time_s` NULL, `peak_rss_mib` NULL | taken from `vpr.flow_time` and `vpr.max_rss` when the source records them, else NULL |
| `host` NULL | NULL when not recorded |
| `origin` | the source file the run came from |

`run_artifact(run_id, kind, blob_sha256)`, PK `(run_id, kind)`: the artifacts of a run by blob hash
(`blif`, `map`, `net`, `place`, `route`, `log`). Imported runs have no stored artifact yet; the table is
filled when a runner calls `mimir blob put`.

### 3.6 `partition`
Algorithmic partitioning (Peter 2026-10-27: "clustering" means packing and partitioning algorithms).

| Column | Meaning |
|---|---|
| `partition_id` PK | sha256 over `(algorithm, params, seed, input_hash, assignment_blob)`, first 16 hex |
| `algorithm`, `algorithm_version` | for example `norns-recluster`, `aapack`, `hmetis`, `pymetis` |
| `params` | canonical JSON of every parameter |
| `seed` | -1 when none |
| `slug` | the design partitioned |
| `input_hash` | sha256 of the netlist or the run output the partition was computed from |
| `n_objects`, `n_clusters` | counts |
| `assignment_blob` | sha256 of the xz blob holding `object<TAB>cluster` lines, sorted by object |
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

`meta.schema_version` is `'1'` in a v1 store. Opening a store with `Store(path)`:
1. version `'2'`: nothing to do;
2. version `'1'`: in one transaction create every v2 table and the view, then set `schema_version = '2'`.
   No v1 row is touched. If anything fails the transaction is rolled back and the file stays v1;
3. any other version: `ValueError`.

Lossless test: build a v1 store (the v1 DDL, reproduced in the test), add rows, export CSV, open with the
v2 code, export CSV again, compare bytes; count and list the tables before and after.

## 6. Importers (read only sources)

- **MCNC meta**: `data/meta/mcnc.toml` and `data/meta/mcnc-sources.md` (copies of the research lane's
  files). `mimir import meta` reads them and writes `design`, `design_meta`, `design_lineage` for the 20
  circuits. The design hash is the sha256 of the VTR BLIF when `$VTR_ROOT` is set, else `hash_kind = slug`.
- **Designs already in the store**: every `(source, design)` pair in `records` is registered with a slug
  (`mcnc20/<n>`, `norns/<n>`, `loki/<dataset>/<n>`). A design without sourced meta gets rows from its
  source only (`suite`, `origin`) with `conf = inferred`, and `function_class` etc. `missing`.
- **Norns configs and runs**: `mimir/data/flow_configs.toml` holds one entry per (round, arm family) with
  the verbatim command template, the file and lines it came from under the Norns checkout, and the parameters.
  A parameter that no script or plan states is listed `unknown`. `mimir import runs` reads the records already
  stored, groups them by `(source, design, arch, seed, arm)`, and creates one `run` per group, linked to the
  config by `source` and arm pattern. No jsonl is re-read.
- **Loki configs and runs**: from the `script` list of each `meta.json` (verbatim, the design file name
  replaced by `<design>`). One config per distinct script text; parameters parsed from the script (arch,
  `abc --lut K`, `read_verilog` options, the pass list). The Odin commit and the ABC script text are not in
  `meta.json` and are `unknown`; the Loki config is therefore `partial`.

## 7. Compressed blob store and snapshots

- `mimir blob put FILE` stores `FILE` content-addressed: path `$MIMIR_BLOBS/<ab>/<sha256>.xz`, where `<ab>` is
  the first two hex characters. `$MIMIR_BLOBS` defaults to `work/mimir-data/blobs` under the workspace
  (given as an argument `--blobs` in tests). Compression is `lzma` preset 6 with CRC64. The name is the sha256 of the
  uncompressed bytes. `put` of an existing hash is a no-op.
- `mimir blob get SHA OUT` decompresses and checks the hash. `mimir blob verify [SHA...]` re-reads each blob,
  decompresses it and compares the hash; non-zero exit on any mismatch.
- `mimir snapshot DB DIR` writes the store as a compressed SQL dump (`mimir-<version>.sql.xz`, from
  `sqlite3.Connection.iterdump` with `ORDER BY` rowid-free logic as below) plus `MANIFEST.json`
  (`schema_version`, per-table row counts, sha256 of the dump, sha256 of the canonical store text). Parquet
  needs `pyarrow` (extra `parquet`) and is optional: `--parquet` writes one zstd file per table when
  pyarrow is installed. The default snapshot is the xz SQL dump.
- The **canonical store text** is a deterministic dump of every table, written table by table in sorted
  table-name order, rows in primary-key order, as `\n`-ended lines of JSON arrays (floats by `repr`). It does
  not depend on the order SQLite stores rows. The SQL dump is for restoring; the canonical text is what is
  compared.
- `mimir snapshot DB DIR --verify` restores the dump into a temporary database, regenerates the canonical
  text and compares it byte for byte with the canonical text of the source store. It exits non-zero on any
  difference.

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
- `run_id` is a hash of the record identity subset, so reimports do not create a second run.
- Quality metrics of a partition are records with source `partition:<id>`, not a separate metric table.
- The canonical store text, not the SQL dump bytes, is the unit of the byte-identical comparison.
