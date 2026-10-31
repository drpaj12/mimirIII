# mimirIII

Mímir III: the circuit knowledge base of Yggdrasil III (design characteristics, Rent, provenance relationships, QoR).

Mímir III is part of **Yggdrasil III**, the suite of Odin III (<https://github.com/drpaj12/odin3>, the trunk), Wyrd III (<https://github.com/drpaj12/wyrd>, the canopy, with Bifrost III and Midgard III), Loki III (<https://github.com/drpaj12/loki>), The Norns III (<https://github.com/drpaj12/nornsIII>) and Verdandi III (<https://github.com/drpaj12/verdandiIII>) on side branches, and Mímir III (<https://github.com/drpaj12/mimirIII>, the fruit). Mímir III is the fruit of the tree: the dataset harvested from the runs of the trunk and the branches (Odin III, VTR, The Norns III, Loki III). Version 0.1.0 (`pyproject.toml`). The hub is <https://github.com/drpaj12/YggdrasilIII> (documentation: <https://drpaj12.github.io/YggdrasilIII/>, versions of every piece: <https://drpaj12.github.io/YggdrasilIII/versions.html>) and its picture of the tree is <https://github.com/drpaj12/YggdrasilIII/blob/main/images/yggdrasil-tree.png>.

Its data is hosted at <https://drpeterjamieson.com/RESEARCH/MIMIR/mimir-data>. The repository holds an index of it; fetch a file with `mimir fetch ARCHIVE:MEMBER`, or add `--online` to read it from that URL (see [`docs/data-access.md`](docs/data-access.md)).

One tidy table of records (the `records` table, from schema 1): design, version, level, arch, seed, placer arm and family, metric,
value, unit and the measurer that computed it. Storage is SQLite with CSV and Parquet export.

    python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
    .venv/bin/mimir init mimir.db
    .venv/bin/mimir import norns mimir.db --root "$MIMIR_NORNS"
    .venv/bin/mimir measure mimir.db --blif path/to/design.blif --source mcnc --level lut
    .venv/bin/mimir export mimir.db --csv out.csv

Schema version 2 (`docs/specs/2026-10-27-mimir-schema-v2.md`) adds the tables `design`, `design_meta`,
`design_lineage`, `flow_config`, `flow_param`, `run`, `partition` and `analysis_result`; `records` is unchanged and a
v1 store migrates when opened.

    .venv/bin/mimir import-meta mimir.db         # MCNC meta from data/meta/mcnc.toml, then register designs
    .venv/bin/mimir import-runs mimir.db         # flow_config and run rows from the stored records; defaults are read
                                                 # from $MIMIR_ODIN3, $VTR_ROOT, $MIMIR_NORNS_SRC (git checkouts)
    .venv/bin/mimir meta-coverage mimir.db       # design_meta rows per field and confidence
    .venv/bin/mimir run-coverage mimir.db        # full against partial flow configs, parameter conf counts, run-key collisions
    .venv/bin/mimir blob put FILE                # xz blob at $MIMIR_BLOBS/<ab>/<sha256>.xz
    .venv/bin/mimir snapshot mimir.db DIR --verify   # xz SQL dump + manifest, restore compared byte for byte,
                                                     # schema and blob references checked ($MIMIR_BLOBS or --blobs)

Benchmarks: Mimir is the home of the generic (third-party) benchmark suites and the netlists compiled from them; the registry is
committed under `data/benchmarks/` (suites with upstream URL, commit and licence; flows with tool commit and script; designs with source
hash and licence rule; netlists keyed by sha256 in the blob store). Sources are referenced under `$MIMIR_EXTERNAL` (default
`<workspace>/external`), never copied. A benchmark is named `suite:design@flow`:

    .venv/bin/mimir bench list [--suite S [--netlists]]    # suites, designs, or suite:design@flow lines
    .venv/bin/mimir bench show vtr-verilog:sha@odin3-1.2.0-k6-verilog
    .venv/bin/mimir bench fetch mcnc20:alu4@odin3-1.2.0-k6-blif --out alu4.blif   # --kind map|flow|source
    .venv/bin/mimir bench build vtr-verilog:sha --flow odin3-1.2.0-k6-verilog --odin3 BIN --arch-dir DIR
    .venv/bin/mimir bench register SUITE...                 # rebuild designs.tsv rows from the checkout
    .venv/bin/mimir bench import DIR --suite S --flow F     # import the netlists of a flow layout
    .venv/bin/mimir bench check [--local --verify]          # index consistent; blobs present and intact

Made-up designs (Norns synthetic and known-optimum sets, Loki round 4 families, Leman Russ Seeker releases) are not Mimir's. The `norns`
set of `measure-set` reads the 35 registered base netlists; the old directory read is `norns-runs`. Spec:
`docs/specs/2026-10-31-benchmarks-design.md`.

Measurers: the structural characterisation of Hutton (thesis and TCAD 2002) and Rent's rule by recursive bisection (METIS through
pymetis). A third, opt-in measurer, `graphlet` (`mimir measure-set ... --graphlet`), runs the Odin III `graphlets` pass through the
`odin3` package (undirected size 5 and directed size 4, global signals excluded) and stores per-orbit design totals (`graphlet_orbit_count`, bin
`<mode>/<orbit>`) with node and edge counts; it is skipped with a recorded note when `odin3` or `odin3_graphlets_count` is missing. It reads the
tech library from `$MIMIR_ODIN3_TECHLIB` or `$MIMIR_ODIN3_TREE/lib/vtr.o3lib`. Do not store real values until the Odin III fix for `$sop`/`$lut`
cells being dropped from the graph (branch fix/graphlets-sop) is on main. See `docs/specs/` for the definitions and what each is validated against. Credits:
`docs/CITATIONS.md`. Licence: MIT.
