# Getting the raw files

The raw data behind Mimir (Norns runs, Loki experiment data, snapshots, blobs) is offloaded: it lives in
xz archives on a private drive, and later on a static web host. The repo holds an index of all of it
(`data/remote/`), so one file can be fetched with `mimir fetch`. Spec:
`docs/specs/2026-10-27-mimir-remote-data.md`.

## Where files come from

`mimir fetch` looks, in this order: the local blob store (`MIMIR_BLOBS`), the archive dir
(`MIMIR_ARCHIVE`, any dir that holds the archives, for example the off-machine drive), the cache
(`MIMIR_CACHE`, default `~/.cache/mimir`), then the URL (`MIMIR_DATA_URL`, or the `urls` of
`data/remote/archives.toml`; `--online` uses
`https://drpeterjamieson.com/RESEARCH/MIMIR/mimir-data`). Private archives (copyrighted papers, the MCNC
originals) are never downloaded; they are read only from `MIMIR_ARCHIVE`.

## Commands

    mimir fetch ARCHIVE:MEMBER [--out FILE]     # one file of an archive; see data/remote/manifests/
    mimir fetch --sha SHA256 [--out FILE]       # a blob, or any manifest file, by hash
    mimir fetch --run RUN_ID --db DB --out DIR  # every artifact of a run
    mimir remote check DB                       # every blob a row refers to is in the index
    mimir remote publish-plan [--only A,B] [--stage DIR] [--with-blobs] [--record]

The archive sha256 is checked before use and the member sha256 after extraction; a mismatch is an
error and nothing is written. Only one member is read; absolute paths, `..`, links and devices are
refused. A URL download is hashed and copied, never run.

## Index

`manifests/<archive>.tsv.xz` lists every member (`path type size sha256`; a link's last field is its
target, with the home dir as `$HOME`). `blobs.tsv.xz` lists the content-addressed blobs. `licences.toml`
holds the per-archive hosting verdicts; the per-design licence of a benchmark is in the Mimir meta
(`data/meta/licences.toml`). Public archives on the web are repacks of the private masters: links,
virtual envs, caches, pickles, databases, locks and shell scripts are removed and home paths are
replaced by `$WS`/`$HOME`; their manifests are `<archive>.public.tsv.xz`.
