# mimir

Mimir III: the circuit knowledge base of Yggdrasil III. Holds the characteristics of designs
(structure, Hutton-style statistics, Rent's rule), the provenance relationships and the outcomes (QoR
per placer family) in one tidy table, so that circuits can be classified over time.

Spec: `docs/specs/2026-10-27-mimir-foundation-design.md`. Plan: `docs/plans/2026-10-27-mimir-foundation-plan.md`.
Research questions (draft for the hub): `docs/purpose-draft.md`. Citations: `citations.toml` and `docs/CITATIONS.md`.

## Setup

    python3 -m venv .venv && .venv/bin/pip install -e ".[dev]" ruff mypy

The base install is stdlib only. `partition` (pymetis, for the Rent measurer), `parquet` (pyarrow) and
`analysis` (numpy) are extras; tests that need one skip through `tests.helpers.skip_without`.

## Build, test, lint

    .venv/bin/python -m unittest discover -s tests -t . -v
    .venv/bin/ruff check .
    .venv/bin/mypy --strict mimir tests

Data sources are read only and come from arguments or env vars (`MIMIR_NORNS`, `MIMIR_LOKI`,
`VTR_ROOT`); never write an absolute home path into a committed file.

## Rules

- Python 3.11+, no 3.12-only syntax. Runtime dependencies: none.
- ruff and `mypy --strict` clean. No `# noqa`, `# type: ignore` or similar suppressions without Peter's approval.
  Line length 100. Small functions. Tests are `unittest` under `tests/`.
- Never commit to `main`. Branch, PR, squash merge on green CI. Commit and push after each green step.
- Outputs are deterministic: sorted keys, `\n` line ends, UTF-8, `schema` = 1. The same input gives the same rows.
- Never invent a reference value or a citation. A value compared with a source needs the source page;
  a source that was not read is said to be unread. Every metric and every source has an entry in
  `mimir/data/metrics.toml` and `citations.toml`.
