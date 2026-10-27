# mimirIII

Mimir III: the circuit knowledge base of Yggdrasil III (design characteristics, Rent, provenance relationships, QoR).

One tidy table of records (`schema` 1): design, version, level, arch, seed, placer arm and family, metric,
value, unit and the measurer that computed it. Storage is SQLite with CSV and Parquet export.

    python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
    .venv/bin/mimir init mimir.db
    .venv/bin/mimir import norns mimir.db --root "$MIMIR_NORNS"
    .venv/bin/mimir measure mimir.db --blif path/to/design.blif --source mcnc --level lut
    .venv/bin/mimir export mimir.db --csv out.csv

Measurers: the structural characterisation of Hutton (thesis and TCAD 2002) and Rent's rule by recursive bisection (METIS through
pymetis). See `docs/specs/` for the definitions and what each is validated against. Credits:
`docs/CITATIONS.md`. Licence: MIT.
