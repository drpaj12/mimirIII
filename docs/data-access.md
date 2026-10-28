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
