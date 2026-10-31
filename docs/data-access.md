# Getting the raw files

The raw data behind Mimir (Norns runs, Loki experiment data, snapshots, blobs) is offloaded: it lives in
xz archives on a private drive, and the public repacks are on a static web host
(`https://drpeterjamieson.com/RESEARCH/MIMIR/mimir-data`, uploaded 2026-10-28). The repo holds an index of all of it
(`data/remote/`), so one file can be fetched with `mimir fetch`. Spec:
`docs/specs/2026-10-27-mimir-remote-data.md`.

## Where files come from

`mimir fetch` looks, in this order: the local blob store (`MIMIR_BLOBS`), the archive dir
(`MIMIR_ARCHIVE`, any dir that holds the archives, for example the off-machine drive), the cache
(`MIMIR_CACHE`, default `~/.cache/mimir`), then the URL (`MIMIR_DATA_URL`, or the `urls` of
`data/remote/archives.toml`; `--online` uses
`https://drpeterjamieson.com/RESEARCH/MIMIR/mimir-data`). Private archives (copyrighted papers, the MCNC
originals, the superseded snapshot and the Odin development intermediates) are never downloaded; they
are read only from `MIMIR_ARCHIVE`. The committed index holds only a row for each (name, date, sha256,
size, kind, `visibility = "private"`); their member manifests are local files in
`$MIMIR_PRIVATE_INDEX/manifests/` (default `mimir-data/remote-private/`), never committed.

## Commands

    mimir fetch ARCHIVE:MEMBER [--out FILE]     # one file of an archive; see data/remote/manifests/
    mimir fetch --sha SHA256 [--out FILE]       # a blob, or any manifest file, by hash
    mimir fetch --run RUN_ID --db DB --out DIR  # every artifact of a run
    mimir remote check DB                       # every blob a row refers to is in the index
    mimir remote publish-plan [--only A,B] [--stage DIR] [--with-blobs] [--record]

The archive sha256 is checked before use and the member sha256 after extraction; a mismatch is an
error and nothing is written. Only one member is read; absolute paths, `..`, links and devices are
refused. A URL download is hashed and copied, never run. Every download stops at the indexed size
plus one byte (archive `size` or `public_size`, member `size`, blob `xz_bytes`), and a blob is decompressed
in memory with a bound from the index (`raw_bytes`), so a long stream or an xz bomb fails.

## Index

`manifests/<archive>.tsv.xz` lists every member (`path type size sha256`; a link's last field is its
target, with the home dir as `$HOME`). `blobs.tsv.xz` lists the content-addressed blobs
(`sha256 xz_bytes raw_bytes archive visibility`); `visibility` is `public`, `withheld` (its content holds a home path or identity string), `private` (the blob traces to a
private archive) or `orphan` (no store row uses it). Only `public` blobs are staged or downloaded. `licences.toml`
holds the per-archive hosting verdicts; the per-design licence of a benchmark is in the Mimir meta
(`data/meta/licences.toml`). Public archives on the web are repacks of the private masters: links,
virtual envs, caches, pickles, databases, locks and shell scripts are removed and home paths are
replaced by `$WS`/`$HOME`; their manifests are `<archive>.public.tsv.xz`.

## Merging stores

`mimir merge DB OTHER...` copies the `records` rows of the other stores into `DB` (insert or replace).
`mimir merge --runs DB OTHER...` copies whole runs: every run of OTHER whose `run_id` is not in `DB`,
with its `run_artifact`, `structure`, `structure_mapping` and `structure_member` rows, its timing tables
(`timing_run`, `timing_path_hist`, `timing_object`, `timing_path`, `timing_path_node`), its HDL graph
tables (`hdl_graph_run`, `hdl_edge`, `hdl_port`), the records it measured (matched on the run key, as
the `record_run` view does), and the `flow_config` / `flow_param` rows it references (insert or ignore).
`--blobs-from DIR --blobs-to DIR` also copies the blobs the run artifacts name, sha256 checked on read
and on write; a blob missing in the source is reported and the exit status is 1. A run with the same
run key as a different `run_id` already in `DB` is reported and skipped. Both stores must be at the
current schema version (`mimir migrate` first), otherwise the command refuses. It backs nothing up:
copy `DB` and compare sha256 first. A second run copies 0. `PRAGMA integrity_check` runs at the end. A
test fails when a table with a `run_id` column is added to the schema and not handled.

## Benchmarks

`mimir bench fetch suite:design@flow` writes one registered netlist (or its name map, flow record or checked source).
The registry `data/benchmarks/` has its own `blobs.tsv.xz` in the format above (archive `-`; `private` for a
`local-only` suite), so the same order applies: local blob store, `MIMIR_ARCHIVE`, cache, then `MIMIR_DATA_URL/blobs/<ab>/<sha>.xz`, sha256 verified. The blobs are
not uploaded yet (hosting is Peter's call). Spec: `docs/specs/2026-10-31-benchmarks-design.md`.
