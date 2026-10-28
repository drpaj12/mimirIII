# Mimir: host alias in recorded data

Purpose: the dataset is public, and `platform.node()` can hold a user name. Every `host` value
records a stable alias (`host-1`, `host-2`, ...); the real name lives only in a private map. Measure:
`mimir privacy-check` finds 0 on every store, export, blob and snapshot, with a check that cannot
report a false 0.

## The map file (for every writer)

Any program that records a host (the Mimir code, and the Norns run-record writer, which reads
`MIMIR_HOST_MAP` too) uses the same file the same way:

- Path: `$MIMIR_HOST_MAP`, else `work/mimir-data/remote-private/hosts.toml`. Never committed. Mode 600.
- Format: a TOML table `[hosts]`; one line per host, key = the real name lower-cased (written as a
  TOML basic string, `"` and `\` escaped), value = `host-<n>`.
  `# comment` lines are allowed. The header written by `--init` is the comment line plus `[hosts]`.
- Append-only: a line is never edited or removed. A name never changes its alias.
- Lock: `<map>.lock` (the map path plus `.lock`, mode 600) beside the map. A writer takes an
  exclusive `flock` on it, re-reads the map inside the lock, looks the name up (any case), and only
  when it is absent numbers it `host-<max+1>` and appends one line (`O_APPEND`, `fsync`), then
  releases the lock. A reader takes a shared `flock` when the lock file exists. `alias_of` does this.
- Creation: only by `mimir host-alias --init` (`hostalias.init_map`). A missing map is an error
  (`HostMapError`), never an empty map: `alias_of`, `scrub_text`, `scrub_bytes`, `Scrubber.text` and
  `privacy-check` all raise, so a run record fails instead of storing an unscrubbed text, and a check
  never reports 0 for want of a map. `--init` refuses (exit 2) when a given store already holds
  `host-<n>` values: the numbering must not restart, so restore the original map instead.

## Record time

`structrun` writes the alias and `host_facts` (CPU model, core count, RAM in MiB, kernel) to
`mimir-run.json`, each with its source. `import_flow_dir` registers the alias of `info["host"]` before
`build_spec` scrubs anything, so the real name is in the map when the first text is scrubbed.
`put_run` stores the facts as `flow_param` rows (step `host`, key `<alias>.<fact>`, conf `given`, the
source). `Scrubber.text` maps a real host name of the map to its alias, then applies the user-name,
person-name and e-mail patterns of `publish.scrub_bytes`, so a bare login name never reaches a stored
text or a blob. The environment given to the Loki child (`structdet.run_loki`) is never written to a
log or blob (stdout is discarded; the stderr tail goes through the Scrubber).

## Schema version 4

`blob_scrub(ref_table, ref_column, ref_key, scrubbed_from, blob_sha256)` extends the artifact row
(`scrubbed_from` is the sha before the scrub). `ref_key` is `run_id:kind` for `run_artifact`,
`partition_id` for `partition`, `analysis_id` for `analysis_result`. It is added by an additive
migration from version 1, 2 or 3 (`Store`, one transaction, no row touched); a version 3 reader
refuses a version 4 store.

## Commands

- `mimir host-alias [DB...] [--dir D] [--init] [--blobs B] [--index I]`: per store, in order:
  migrate to the current schema; rewrite `run.host` (first token becomes the alias); rewrite every
  cell of the free-text columns (`hostscrub.TEXT_COLUMNS`: command lines, origins, flow parameter
  values and sources, flow config text, parameters, spans, chains and so on) so that a host name of the
  map, a private string, a home path, the user name or an e-mail is replaced; with `--blobs`, re-blob
  every referenced blob of the `BLOB_REFS` columns that holds a private string or a home path (real
  host to alias, then `publish.scrub_bytes`, then `redacted`), repoint the column and record
  `blob_scrub`; report the referenced blobs missing on disk; with `--index`, the old sha becomes
  `withheld` in `blobs.tsv.xz` and the new one, and any other referenced sha the index lacks, is scanned
  first and added `public` only when clean (a hit is `withheld`); finally `VACUUM` each store, so no
  free page keeps the old text. Idempotent. A test fails when a text column is in neither list of
  `hostscrub`.
- `mimir privacy-check [--db DB] [--path FILE|DIR|TAR.XZ] [--blobs DIR [--index IDX]]`: scans for the
  private strings (the map, `$MIMIR_PRIVATE_STRINGS` newline or comma separated, this machine's name,
  the login name; a name under 3 letters as a whole word) and for what `publish.has_home` finds (home
  path, user name, person's name, e-mail), any case. A store is scanned cell by cell, in its schema, and
  as raw bytes (the `.db` file and its `-wal`, so free pages are covered). A file is read inside xz, gz,
  zip, npz, tar, nested; a `.tar.xz` member by member. Something that cannot be decoded (a damaged
  xz, gz or zip) is a hit `undecodable`; a Parquet file is read with pyarrow, and without pyarrow is a
  hit `not scanned`, never clean. The report names places and string numbers only, never a string.
  Exit 1 on a hit, 2 when the map is missing.

## Result of the fix round (2026-10-28)

Stores after `mimir host-alias --dir work/mimir-data --blobs ... --index data/remote`: no cell needed a
rewrite (the earlier lanes had aliased them), 0 referenced blobs needed a re-blob, every store was
VACUUMed. The lane-2 main store (11,114 runs) was restored from `2026-10-27/mimir-snapshot-2026-10-27b`
(canonical sha256 `3105e73e...1152`, equal to its manifest), migrated v2 to v4; its one partition blob,
missing from the local blob dir, was restored from the 10-27b blob tarball.

`mimir privacy-check` (2 private strings: the host map and the login name; has_home on every unit):

| Scanned | Units | Hits |
|---|---|---|
| mimir-main.db (cells, schema, raw bytes) | 585,384 records, 11,114 runs | 0 |
| lane3-structures.db | 183 runs | 0 |
| mimir-structures.db | 164 runs | 0 |
| structures.db | 164 runs | 0 |
| CSV exports of the four stores | 4 files | 0 |
| public blobs (index `public` only) | 816 | 0 |
| snapshot dir `mimir-snapshot-2026-10-28b` (4 dumps, 4 manifests) | 8 files | 0 |
| public blob tarball `mimir-snapshot-2026-10-28b-blobs.tar.xz` | 816 members | 0 |

`mimir remote check`: every blob reference of the four stores resolves in the index (100%).

Snapshot `2026-10-28/mimir-snapshot-2026-10-28b` on F: (schema 4, `--verify` identical for each):
`lane2/` dump 3,345,416 B, `main/` 1,296,932 B, `lane3/` 2,134,716 B, `structures/` 1,298,784 B; blob tarball
15,983,080 B, sha256 `0cada7e6...7697`, 816 members, public blobs only. The earlier
`mimir-snapshot-2026-10-28` pair is marked SUPERSEDED in the index and kept. Licence verdict of all the
2026-10-28 snapshot archives: `host-with-notices` (controller, per Peter's rule: each benchmark carries
its own licence and notice).
