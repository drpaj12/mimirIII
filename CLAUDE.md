# mimir

Mimir III: the circuit knowledge base of Yggdrasil III. Holds the characteristics of designs
(structure, Hutton-style statistics, Rent's rule), the provenance relationships and the outcomes (QoR
per placer family) in one tidy table, so that circuits can be classified over time.

Spec: `docs/specs/2026-10-27-mimir-foundation-design.md`. Plan: `docs/plans/2026-10-27-mimir-foundation-plan.md`.
Near-critical timing (schema v5, `mimir import-timing`): `docs/specs/2026-10-28-near-critical.md`. Per-path tables (schema v6, `mimir import-timing --paths-from-blobs`): `docs/specs/2026-10-28-timing-paths.md`. HDL graph (schema v7, `mimir hdl-graph`): `docs/specs/2026-10-28-hdl-graph.md`. Schema v2 spec: `docs/specs/2026-10-27-mimir-schema-v2.md`. Structures and their mapping (schema v3): `docs/specs/2026-10-27-mimir-structures.md`. Research questions (draft for the hub): `docs/purpose-draft.md`. Citations: `citations.toml` and `docs/CITATIONS.md`.

## Setup

    python3 -m venv .venv && .venv/bin/pip install -e ".[dev]" ruff mypy

The base install is stdlib only. `partition` (pymetis, for the Rent measurer), `parquet` (pyarrow) and
`analysis` (numpy) are extras; tests that need one skip through `tests.helpers.skip_without`.

## Build, test, lint

    .venv/bin/python -m unittest discover -s tests -t . -v
    .venv/bin/ruff check .
    .venv/bin/mypy --strict mimir tests

Data sources are read only and come from arguments or env vars (`MIMIR_NORNS`, `MIMIR_LOKI`,
`VTR_ROOT`, and for tool defaults `MIMIR_ODIN3`, `MIMIR_NORNS_SRC`; for lane 3 `MIMIR_ODIN3_TREE` (an Odin III checkout with `tools/flow`), `MIMIR_LOKI_SRC`, `MIMIR_LOKI_PYTHON`); the structure tests use vendored copies of the Odin III map parser and Loki's audit (`tests/fixtures/deps`) when `MIMIR_ODIN3_TREE` and `MIMIR_LOKI_SRC` are not set, so they run in CI; lane 3 runs need `VTR_ROOT` and `ODIN3_HEAVY_OK=1`; never write an absolute home path into a committed file.

Host names: a `host` value is always an alias (`host-1`); the real name lives only in the private map `$MIMIR_HOST_MAP` (default `work/mimir-data/remote-private/hosts.toml`), never committed. The map is created only by `mimir host-alias --init` and a missing map is an error, never an empty map (no alias is invented, no text passes unscrubbed). `mimir host-alias` rewrites a store (schema 4), `mimir privacy-check` gates it (`$MIMIR_PRIVATE_STRINGS` adds strings; it looks inside xz, gz, zip, npz, tar and Parquet, and reads the raw `.db` bytes). Spec: `docs/specs/2026-10-28-mimir-host-alias.md`.

## Rules

- Python 3.11+, no 3.12-only syntax. Runtime dependencies: none.
- ruff and `mypy --strict` clean. No `# noqa`, `# type: ignore` or similar suppressions without Peter's approval.
  Line length 100. Small functions. Tests are `unittest` under `tests/`.
- Never commit to `main`. Branch, PR, squash merge on green CI. Commit and push after each green step.
- Outputs are deterministic: sorted keys, `\n` line ends, UTF-8, `schema` = 1. The same input gives the same rows.
- Never invent a reference value or a citation. A value compared with a source needs the source page;
  a source that was not read is said to be unread. Every metric and every source has an entry in
  `mimir/data/metrics.toml` and `citations.toml`.
