# Mimir: host alias in recorded data

Purpose: the dataset is public, and `platform.node()` can hold a user name. Every `host` value now
records a stable alias (`host-1`, `host-2`, ...); the real name lives only in a private map.

- Map: `$MIMIR_HOST_MAP`, else `work/mimir-data/remote-private/hosts.toml` (TOML table `[hosts]`,
  lower-cased real name to alias). Never committed. An unknown name gets the next `host-<n>` and is
  appended; the same name (any case) always gets the same alias (`mimir/hostalias.py`).
- Record time: `structrun` writes the alias and `host_facts` (CPU model, core count, RAM in MiB,
  kernel) to `mimir-run.json`, each with its source. `put_run` stores the facts as `flow_param`
  rows (step `host`, key `<alias>.<fact>`, conf `given`, the source). `Scrubber.text` also maps a
  real host name of the map to its alias, so no blob written later holds it.
- `mimir host-alias [DB...] [--dir D] [--blobs B] [--index I]`: rewrites `run.host` (first token
  becomes the alias) in one transaction per store and prints the rows rewritten and the rows still
  unaliased. With `--blobs`: every referenced blob that holds a private string or a home path is
  re-blobbed scrubbed (real host to alias, then `publish.scrub_bytes`), the blob column is
  repointed, and `blob_scrub(ref_table, ref_column, ref_key, scrubbed_from, blob_sha256)` records
  the old sha (the artifact row's `scrubbed_from`). Old blobs stay on disk. With `--index`, the old
  sha becomes `withheld` in `blobs.tsv.xz` and the new one `public`. Idempotent.
- `mimir privacy-check [--db DB] [--path FILE|DIR|TAR.XZ] [--blobs DIR [--index IDX]]`: scans for
  the private strings (the map, `$MIMIR_PRIVATE_STRINGS` newline or comma separated, this
  machine's name, the login name), any case, inside one xz layer and tar members. The report names
  places and string numbers only, never a string. Exit 1 on a hit.
