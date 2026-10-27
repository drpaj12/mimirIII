# Mimir III foundation plan

Spec: `docs/specs/2026-10-27-mimir-foundation-design.md`. Each step ends with ruff, mypy --strict,
unittest green, then commit and push.

1. Docs and scaffold: spec, plan, pyproject, CLAUDE.md, README, NOTICE, CI, `citations.toml`,
   `docs/CITATIONS.md`, `docs/purpose-draft.md`.
2. Schema, registry, store: `mimir/schema.py`, `registry.py`, `store.py`, `data/metrics.toml`,
   CSV and Parquet export, CLI `init`, `registry`, `export`. Tests: idempotent upsert,
   byte-identical export, registry/citation consistency.
3. Importers: `mimir/importers/{norns,loki,atlas}.py`, CLI `import`. Counts per source.
4. BLIF model and Hutton measurer with known-answer tests.
5. Rent measurer with known-answer tests and seed test-retest.
6. Run on MCNC and the imported netlists (tracked background run); write rows; report tables.
7. Result appended to the brief.

Data layout note: the brief names `work/mimir-data/`; it did not exist, so importers take their
source roots from arguments or the env vars `MIMIR_NORNS`, `MIMIR_LOKI`, `VTR_ROOT`.
