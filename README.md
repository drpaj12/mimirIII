# mimirIII

Mímir III: the circuit knowledge base of Yggdrasil III (design characteristics, Rent, provenance relationships, QoR).

What it is today: a SQLite knowledge base (one tidy `records` table plus design, meta, lineage, flow, run, partition, timing,
per-path timing and HDL-graph tables, schema v7) and a benchmark registry with content-addressed blobs, so that circuits can be
characterised, compared and mined over time. Stages: **import** (Norns runs, Loki runs, Odin III flow output and run records),
**measure** (Hutton-style structure, Rent's rule, opt-in graphlet orbit totals), **register** (third-party suites and the
netlists compiled from them, keyed `suite:design@flow`, sources referenced and never copied), **fetch** (a local blob store, then
archives, then the hosted URL, sha256 verified) and **report** (coverage, Loki detector precision and recall, privacy checks).
Mímir III holds the data; it reports no research finding of its own and has no paper. The papers that use its data are those of
[Loki III](https://github.com/drpaj12/loki/tree/main/docs/paper), [The Norns III](https://github.com/drpaj12/nornsIII/tree/main/docs/paper)
and [Odin III](https://github.com/drpaj12/odin3/tree/main/docs/paper). The hub is <https://github.com/drpaj12/YggdrasilIII>.

Mímir III is part of **Yggdrasil III**, the suite of Odin III (<https://github.com/drpaj12/odin3>, the trunk), Wyrd III (<https://github.com/drpaj12/wyrd>, the canopy, with Bifrost III and Midgard III), Loki III (<https://github.com/drpaj12/loki>), The Norns III (<https://github.com/drpaj12/nornsIII>) and Verdandi III (<https://github.com/drpaj12/verdandiIII>) on side branches, and Mímir III (<https://github.com/drpaj12/mimirIII>, the fruit). Mímir III is the fruit of the tree: the dataset harvested from the runs of the trunk and the branches (Odin III, VTR, The Norns III, Loki III). Version 0.1.0 (`pyproject.toml`; in the Yggdrasil III hub snapshot [v1.4.0](https://github.com/drpaj12/YggdrasilIII/blob/v1.4.0/docs/versions.md)); Odin III 1.4.0. The hub is <https://github.com/drpaj12/YggdrasilIII> (documentation: <https://drpaj12.github.io/YggdrasilIII/>, versions of every piece: <https://drpaj12.github.io/YggdrasilIII/versions.html>) and its picture of the tree is <https://github.com/drpaj12/YggdrasilIII/blob/main/images/yggdrasil-tree.png>.

Its data is hosted at <https://drpeterjamieson.com/RESEARCH/MIMIR/mimir-data>. The repository holds an index of it; fetch a file with `mimir fetch ARCHIVE:MEMBER`, or add `--online` to read it from that URL (see [`docs/data-access.md`](docs/data-access.md)).

## Features

Status: **works** = a `mimir` command with tests on `main`; **opt-in** = needs an extra or an external tool; **hosting** = depends on files uploaded to the web host.

| Feature | Status | Where |
|---|---|---|
| Circuit knowledge base: one tidy `records` table (design, version, level, arch, seed, placer arm and family, metric, value, unit, measurer) in SQLite, with CSV and Parquet export | works | `mimir init`, `export`; `docs/specs/2026-10-27-mimir-foundation-design.md` |
| Schema v7 with design, meta, lineage, flow config, run, partition, timing, per-path timing, HDL graph and structure tables; older stores migrate when opened | works | `mimir migrate`; `docs/specs/2026-10-27-mimir-schema-v2.md` and the later specs in `docs/specs/` |
| Importers for Norns runs, Loki runs and Odin III flow output, and run records from Odin III flow and Loki (`loki re` writes one) | works | `mimir import`, `import-runs`, `import-flow`, `import-runrecords`, `import-meta` |
| Measurers: Hutton-style structural characterisation, Rent's rule (METIS via pymetis), and the graphlet measurer (Odin III `graphlets` pass, per-orbit totals) | works; Rent needs the `partition` extra, graphlet is opt-in (`--graphlet`) | `mimir measure`, `measure-set`; `docs/specs/` |
| Near-critical timing and per-path timing tables, imported from stored runs | works | `mimir import-timing`; `docs/specs/2026-10-28-near-critical.md`, `2026-10-28-timing-paths.md` |
| Line-level HDL graph of runs (links netlist objects to source lines) | works | `mimir hdl-graph`; `docs/specs/2026-10-28-hdl-graph.md` |
| Structures and their mapping (Loki detectors run on stored BLIFs, precision and recall report) | works | `mimir detect`, `detect-mcnc`, `report`; `docs/specs/2026-10-27-mimir-structures.md` |
| Benchmark registry: generic suites, designs and the netlists compiled from them, keyed `suite:design@flow`, with upstream URL, commit and licence per suite, sources referenced and never copied | works | `mimir bench list\|show\|fetch\|build\|register\|import\|check`; `data/benchmarks/`; `docs/specs/2026-10-31-benchmarks-design.md` |
| Blob store: content-addressed xz blobs by sha256, with snapshot (xz SQL dump, restore compared byte for byte) | works | `mimir blob`, `mimir snapshot` |
| `mimir fetch`: one archive member, blob or every artifact of a run, looked up in the local blob store, then the archive dir, then the cache, then the URL; archive and member sha256 verified, size bounded, private archives never downloaded | works; the URL step needs the hosted files | `mimir fetch`, `mimir remote check\|index\|publish-plan`; `docs/data-access.md` |
| Online data at <https://drpeterjamieson.com/RESEARCH/MIMIR/mimir-data> (public repacks of the archives; the benchmark registry index was put online on 2026-11-02; `--online` reads from it) | hosting | `docs/data-access.md` |
| Privacy tools: host aliases, scrubbing and `mimir privacy-check` over stores, CSV, blobs and snapshots | works | `mimir host-alias`, `privacy-check`; `docs/specs/2026-10-28-mimir-host-alias.md` |
| Merging stores and run coverage reports | works | `mimir merge [--runs]`, `meta-coverage`, `run-coverage`, `timing-coverage` |
| Metric registry and citations (every metric and source has an entry) | works | `mimir registry`, `mimir citations`; `docs/CITATIONS.md` |

Made-up benchmarks (Norns synthetic and known-optimum sets, Loki round 4 families, Leman Russ Seeker releases) are not Mimir's. Mimir has no manual index page yet; the specs in `docs/specs/` are the reference.

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
