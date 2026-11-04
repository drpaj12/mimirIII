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

<!-- catalogue:start (generated by `mimir bench catalogue`; do not edit) -->
## Benchmark catalogue

One row per registered design, in tiers: best first (HDL with testbench and the whole flow), down to BLIF netlists only; each tier states its rule. `✓` yes, `✗` no (both measured), `-` not run, `n/a` does not apply, `fail: ...` the tool failed. Every value is in `data/benchmarks/measures.tsv` with its source; the rules are in `docs/benchmarks/catalogue-method.md`. The `vtr-blif-k2` and `vtr-blif-k4` suites hold the same circuits: one row per circuit name present in either.

| tier | rule | designs |
|---|---|---|
| T0 whole flow | HDL with its own testbench, 200+ Verilog lines, the testbench passes in iverilog (`sim_iverilog`=1) and in Odin III simulation (`sim_odin`=1), and the VTR flow reaches `route` with timing (`vtr_stage`) | 0 |
| T1 HDL + testbench, larger | HDL with a testbench and 200+ Verilog lines (and not T0) | 1 |
| T2 HDL + testbench, small | HDL with a testbench and under 200 Verilog lines | 156 |
| T3 HDL, no testbench | HDL (Verilog) with no testbench file | 52 |
| T4 netlist only | BLIF netlist, no HDL | 219 |

| suite | designs |
|---|---|
| brisc-v | 1 |
| itc99 | 21 |
| mcnc20 | 20 |
| verilogeval | 156 |
| vtr-blif | 199 |
| vtr-verilog | 31 |
| total | 428 |

<details><summary>T1 HDL + testbench, larger (1 designs)</summary>

Rule: HDL with a testbench and 200+ Verilog lines (and not T0).

| design | suite | what it does | format | top | LOC | seq | mem | mul | add | fsm | latch | hier | bbox | testbench | vectors | iverilog | Odin sim | VTR stage | LUTs | blocks | FFs | pins | mult/mem | cpd ns | chan w | gates/depth | 4-LUT/depth | 6-LUT/depth | cells | core um2 | LVS | stage |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| quartus_project_revert_timer | [brisc-v](#sources) | BRISC-V microcontroller (Arduino-on-RISC-V) | verilog-project | single_cycle_BRAM_top | 4349 | - | - | - | - | - | - | - | - | Arduino-on-RISC-V/quartus_project_revert_timer/tb_single_cycle_BRAM_top_gcd.v | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - |

</details>

<details><summary>T2 HDL + testbench, small (156 designs)</summary>

Rule: HDL with a testbench and under 200 Verilog lines.

| design | suite | what it does | format | top | LOC | seq | mem | mul | add | fsm | latch | hier | bbox | testbench | vectors | iverilog | Odin sim | VTR stage | LUTs | blocks | FFs | pins | mult/mem | cpd ns | chan w | gates/depth | 4-LUT/depth | 6-LUT/depth | cells | core um2 | LVS | stage |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Prob144_conwaylife | [verilogeval](#sources) | - | verilog | RefModule | 37 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob144_conwaylife_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1966/- | - | - | - | - |
| Prob030_popcount255 | [verilogeval](#sources) | a population count circuit for a 255-bit input vector | verilog | RefModule | 14 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob030_popcount255_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1369/- | - | - | - | - |
| Prob153_gshare | [verilogeval](#sources) | a gshare branch predictor with 7-bit pc and 7-bit global history, hashed (usi... | verilog | RefModule | 49 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob153_gshare_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 647/- | - | - | - | - |
| Prob108_rule90 | [verilogeval](#sources) | Rule 90, a one-dimensional cellular automaton with interesting properties | verilog | RefModule | 18 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob108_rule90_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 512/- | - | - | - | - |
| Prob124_rule110 | [verilogeval](#sources) | Rule 110, a one-dimensional cellular automaton with interesting properties (s... | verilog | RefModule | 22 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob124_rule110_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 512/- | - | - | - | - |
| Prob021_mux256to1v | [verilogeval](#sources) | a 4-bit wide, 256-to-1 multiplexer | verilog | RefModule | 11 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob021_mux256to1v_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 390/- | - | - | - | - |
| Prob092_gatesv100 | [verilogeval](#sources) | - | verilog | RefModule | 16 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob092_gatesv100_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 298/- | - | 6531.3 | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob105_rotate100 | [verilogeval](#sources) | a 100-bit left/right rotator, with synchronous load and left/right enable | verilog | RefModule | 20 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob105_rotate100_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 201/- | 873 | 18955.7 | match | lvs |
| Prob115_shift18 | [verilogeval](#sources) | a 64-bit arithmetic shift register, with synchronous load | verilog | RefModule | 24 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob115_shift18_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 130/- | 703 | 13934.6 | match | lvs |
| Prob018_mux256to1 | [verilogeval](#sources) | a 1-bit wide, 256-to-1 multiplexer | verilog | RefModule | 11 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob018_mux256to1_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 105/- | 506 | 7847.5 | match | lvs |
| Prob017_mux2to1v | [verilogeval](#sources) | a 2-1 multiplexer | verilog | RefModule | 12 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob017_mux2to1v_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 100/- | - | 4144.0 | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob097_mux9to1v | [verilogeval](#sources) | a 16-bit wide, 9-to-1 multiplexer | verilog | RefModule | 32 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob097_mux9to1v_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 95/- | 187 | 3178.0 | match | lvs |
| Prob052_gates100 | [verilogeval](#sources) | a combinational circuit with 100 inputs, in[99:0] | verilog | RefModule | 14 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob052_gates100_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 88/- | 318 | 5172.5 | match | lvs |
| Prob055_conditional | [verilogeval](#sources) | - | verilog | RefModule | 18 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob055_conditional_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 56/- | 159 | 2499.9 | match | lvs |
| Prob141_count_clock | [verilogeval](#sources) | - | verilog | RefModule | 47 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob141_count_clock_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 41/- | - | - | - | - |
| Prob066_edgecapture | [verilogeval](#sources) | - | verilog | RefModule | 20 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob066_edgecapture_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 32/- | - | - | - | - |
| Prob082_lfsr32 | [verilogeval](#sources) | a 32-bit Galois LFSR with taps at bit positions 32, 22, 2, and 1 | verilog | RefModule | 25 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob082_lfsr32_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 32/- | - | - | - | - |
| Prob118_history_shift | [verilogeval](#sources) | a 32-bit global history shift register, including support for rolling back st... | verilog | RefModule | 25 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob118_history_shift_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 32/- | - | - | - | - |
| Prob154_fsm_ps2data | [verilogeval](#sources) | a finite state machine that will search for message boundaries when given an... | verilog | RefModule | 42 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob154_fsm_ps2data_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 28/- | - | 2876.5 | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob068_countbcd | [verilogeval](#sources) | a 4-digit BCD (binary-coded decimal) counter | verilog | RefModule | 20 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob068_countbcd_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 22/- | - | - | - | - |
| Prob123_bugs_addsubz | [verilogeval](#sources) | - | verilog | RefModule | 19 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob123_bugs_addsubz_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 22/- | - | - | - | - |
| Prob043_vector5 | [verilogeval](#sources) | - | verilog | RefModule | 14 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob043_vector5_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 20/- | 25 | 420.4 | mismatch | extract |
| Prob146_fsm_serialdata | [verilogeval](#sources) | - | verilog | RefModule | 46 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob146_fsm_serialdata_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 20/- | - | - | - | - |
| Prob080_timer | [verilogeval](#sources) | a timer that counts down for a given number of clock cycles, then asserts a s... | verilog | RefModule | 18 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob080_timer_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 17/- | - | - | - | - |
| Prob155_lemmings4 | [verilogeval](#sources) | - | verilog | RefModule | 60 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob155_lemmings4_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 17/- | - | - | - | - |
| Prob073_dff16e | [verilogeval](#sources) | - | verilog | RefModule | 22 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob073_dff16e_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 16/- | - | - | - | - |
| Prob126_circuit6 | [verilogeval](#sources) | a combinational circuit | verilog | RefModule | 20 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob126_circuit6_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 16/- | - | - | - | - |
| Prob037_review2015_count1k | [verilogeval](#sources) | a counter that counts from 0 to 999, inclusive, with a period of 1000 cycles | verilog | RefModule | 15 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob037_review2015_count1k_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 14/- | - | - | - | - |
| Prob033_ece241_2014_q1c | [verilogeval](#sources) | - | verilog | RefModule | 14 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob033_ece241_2014_q1c_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 13/- | - | - | - | - |
| Prob114_bugs_case | [verilogeval](#sources) | - | verilog | RefModule | 31 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob114_bugs_case_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 13/- | - | - | - | - |
| Prob143_fsm_onehot | [verilogeval](#sources) | the state transition logic and output logic portions of the state machine (bu... | verilog | RefModule | 25 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob143_fsm_onehot_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 13/- | 23 | 300.3 | match | lvs |
| Prob076_always_case | [verilogeval](#sources) | a 6-to-1 multiplexer | verilog | RefModule | 26 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob076_always_case_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 12/- | - | - | - | - |
| Prob137_fsm_serial | [verilogeval](#sources) | - | verilog | RefModule | 38 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob137_fsm_serial_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 12/- | - | - | - | - |
| Prob084_ece241_2013_q12 | [verilogeval](#sources) | a circuit for an 8x1 memory, where writing to the memory is accomplished by s... | verilog | RefModule | 21 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob084_ece241_2013_q12_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 11/- | - | - | - | - |
| Prob140_fsm_hdlc | [verilogeval](#sources) | - | verilog | RefModule | 37 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob140_fsm_hdlc_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 11/- | - | - | - | - |
| Prob149_ece241_2013_q4 | [verilogeval](#sources) | - | verilog | RefModule | 46 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob149_ece241_2013_q4_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 11/- | - | - | - | - |
| Prob044_vectorgates | [verilogeval](#sources) | - | verilog | RefModule | 15 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob044_vectorgates_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 10/- | 12 | 145.1 | mismatch | extract |
| Prob094_gatesv | [verilogeval](#sources) | - | verilog | RefModule | 18 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob094_gatesv_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 10/- | - | - | - | - |
| Prob106_always_nolatches | [verilogeval](#sources) | - | verilog | RefModule | 21 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob106_always_nolatches_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 10/- | - | - | - | - |
| Prob130_circuit5 | [verilogeval](#sources) | a combinational circuit | verilog | RefModule | 21 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob130_circuit5_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 9/- | - | - | - | - |
| Prob133_2014_q3fsm | [verilogeval](#sources) | a finite state machine with inputs s and w | verilog | RefModule | 35 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob133_2014_q3fsm_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 9/- | - | - | - | - |
| Prob139_2013_q2bfsm | [verilogeval](#sources) | - | verilog | RefModule | 38 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob139_2013_q2bfsm_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 9/- | - | - | - | - |
| Prob041_dff8r | [verilogeval](#sources) | - | verilog | RefModule | 16 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob041_dff8r_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 8/- | - | - | - | - |
| Prob045_edgedetect2 | [verilogeval](#sources) | - | verilog | RefModule | 16 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob045_edgedetect2_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 8/- | - | 1594.0 | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob047_dff8ar | [verilogeval](#sources) | - | verilog | RefModule | 16 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob047_dff8ar_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 8/- | - | - | - | - |
| Prob054_edgedetect | [verilogeval](#sources) | - | verilog | RefModule | 16 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob054_edgedetect_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 8/- | - | 1559.0 | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob062_bugs_mux2 | [verilogeval](#sources) | - | verilog | RefModule | 13 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob062_bugs_mux2_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 8/- | - | - | - | - |
| Prob087_gates | [verilogeval](#sources) | a combinational circuit with two inputs, a and b | verilog | RefModule | 23 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob087_gates_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 7/- | 10 | 93.8 | mismatch | extract |
| Prob136_m2014_q6 | [verilogeval](#sources) | the state machine shown below: A (0) --0--> B A (0) --1--> A B (0) --0--> C B... | verilog | RefModule | 33 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob136_m2014_q6_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 7/- | - | - | - | - |
| Prob138_2012_q2fsm | [verilogeval](#sources) | the state machine shown below: A (0) --1--> B A (0) --0--> A B (0) --1--> C B... | verilog | RefModule | 31 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob138_2012_q2fsm_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 7/- | - | - | - | - |
| Prob016_m2014_q4j | [verilogeval](#sources) | - | verilog | RefModule | 11 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob016_m2014_q4j_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 6/- | - | - | - | - |
| Prob121_2014_q3bfsm | [verilogeval](#sources) | a finite-state machine with the state-assigned table shown below | verilog | RefModule | 31 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob121_2014_q3bfsm_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 6/- | 21 | 402.9 | match | lvs |
| Prob152_lemmings3 | [verilogeval](#sources) | - | verilog | RefModule | 48 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob152_lemmings3_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 6/- | - | - | - | - |
| Prob086_lfsr5 | [verilogeval](#sources) | a 5-bit maximal-length Galois LFSR with taps at bit positions 5 and 3 | verilog | RefModule | 23 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob086_lfsr5_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 5/- | - | - | - | - |
| Prob096_review2015_fsmseq | [verilogeval](#sources) | a finite-state machine that searches for the sequence 1101 in an input bit st... | verilog | RefModule | 30 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob096_review2015_fsmseq_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 5/- | - | - | - | - |
| Prob148_2013_q2afsm | [verilogeval](#sources) | the FSM described by the state diagram shown below: A --r0=0,r1=0,r2=0--> A A... | verilog | RefModule | 35 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob148_2013_q2afsm_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 5/- | - | - | - | - |
| Prob150_review2015_fsmonehot | [verilogeval](#sources) | the following Moore state machine with 3 input (d, done_counting, ack) and 3... | verilog | RefModule | 30 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob150_review2015_fsmonehot_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 5/- | 10 | 150.1 | mismatch | extract |
| Prob035_count1to10 | [verilogeval](#sources) | a decade counter that counts 1 through 10, inclusive | verilog | RefModule | 15 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob035_count1to10_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 4/- | - | - | - | - |
| Prob038_count15 | [verilogeval](#sources) | a 4-bit binary counter that counts from 0 through 15, inclusive, with a perio... | verilog | RefModule | 15 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob038_count15_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 4/- | - | - | - | - |
| Prob040_count10 | [verilogeval](#sources) | a decade counter that counts from 0 through 9, inclusive, with a period of 10 | verilog | RefModule | 15 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob040_count10_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 4/- | - | - | - | - |
| Prob060_m2014_q4k | [verilogeval](#sources) | a shift register with four D flops | verilog | RefModule | 20 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob060_m2014_q4k_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 4/- | - | - | - | - |
| Prob063_review2015_shiftcount | [verilogeval](#sources) | a four-bit shift register that also acts as a down counter | verilog | RefModule | 18 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob063_review2015_shiftcount_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 4/- | - | - | - | - |
| Prob067_countslow | [verilogeval](#sources) | a decade counter that counts from 0 through 9, inclusive, with a period of 10 | verilog | RefModule | 20 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob067_countslow_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 4/- | - | - | - | - |
| Prob079_fsm3onehot | [verilogeval](#sources) | the state transition table for a Moore state machine with one input, one outp... | verilog | RefModule | 19 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob079_fsm3onehot_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 4/- | 9 | 97.6 | mismatch | extract |
| Prob085_shift4 | [verilogeval](#sources) | a 4-bit shift register (right shift), with asynchronous positive edge trigger... | verilog | RefModule | 21 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob085_shift4_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 4/- | - | - | - | - |
| Prob095_review2015_fsmshift | [verilogeval](#sources) | - | verilog | RefModule | 29 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob095_review2015_fsmshift_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 4/- | - | - | - | - |
| Prob120_fsm3s | [verilogeval](#sources) | a Moore state machine with the following state transition table with one inpu... | verilog | RefModule | 30 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob120_fsm3s_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 4/- | - | - | - | - |
| Prob128_fsm_ps2 | [verilogeval](#sources) | a finite state machine that will search for message boundaries when given an... | verilog | RefModule | 32 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob128_fsm_ps2_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 4/- | - | - | - | - |
| Prob142_lemmings2 | [verilogeval](#sources) | - | verilog | RefModule | 36 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob142_lemmings2_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 4/- | - | - | - | - |
| Prob051_gates4 | [verilogeval](#sources) | a combinational circuit with four inputs, in[3:0] | verilog | RefModule | 14 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob051_gates4_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 3/- | - | - | - | - |
| Prob072_thermostat | [verilogeval](#sources) | a heating/cooling thermostat controller which controls both a heater (during... | verilog | RefModule | 17 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob072_thermostat_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 3/- | - | - | - | - |
| Prob074_ece241_2014_q4 | [verilogeval](#sources) | a finite state machine with the following behavior | verilog | RefModule | 17 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob074_ece241_2014_q4_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 3/- | - | - | - | - |
| Prob089_ece241_2014_q5a | [verilogeval](#sources) | a one-input one-output serial 2's complementer Moore state machine | verilog | RefModule | 26 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob089_ece241_2014_q5a_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 3/- | - | - | - | - |
| Prob093_ece241_2014_q3 | [verilogeval](#sources) | - | verilog | RefModule | 14 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob093_ece241_2014_q3_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 3/- | - | 42.5 | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob100_fsm3comb | [verilogeval](#sources) | the following is the state transition table for a Moore state machine with on... | verilog | RefModule | 23 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob100_fsm3comb_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 3/- | 4 | 45.0 | mismatch | extract |
| Prob117_circuit9 | [verilogeval](#sources) | - | verilog | RefModule | 17 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob117_circuit9_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 3/- | - | - | - | - |
| Prob119_fsm3 | [verilogeval](#sources) | a Moore state machine with the following state transition table with one inpu... | verilog | RefModule | 30 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob119_fsm3_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 3/- | - | - | - | - |
| Prob129_ece241_2013_q8 | [verilogeval](#sources) | a Mealy-type finite state machine that recognizes the sequence "101" on an in... | verilog | RefModule | 37 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob129_ece241_2013_q8_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 3/- | - | - | - | - |
| Prob009_popcount3 | [verilogeval](#sources) | a "population count" circuit that counts the number of '1's in the input vector | verilog | RefModule | 10 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob009_popcount3_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 2/- | - | - | - | - |
| Prob024_hadd | [verilogeval](#sources) | a half adder | verilog | RefModule | 12 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob024_hadd_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 2/- | - | - | - | - |
| Prob025_reduction | [verilogeval](#sources) | - | verilog | RefModule | 10 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob025_reduction_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 2/- | - | - | - | - |
| Prob027_fadd | [verilogeval](#sources) | - | verilog | RefModule | 13 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob027_fadd_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 2/- | - | - | - | - |
| Prob036_ringer | [verilogeval](#sources) | a circuit to control a cellphone's ringer and vibration motor | verilog | RefModule | 13 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob036_ringer_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 2/- | - | 17.5 | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob058_alwaysblock2 | [verilogeval](#sources) | an XOR gate three ways, using an assign statement (output out_assign), a comb... | verilog | RefModule | 16 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob058_alwaysblock2_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 2/- | - | - | - | - |
| Prob065_7420 | [verilogeval](#sources) | the same functionality as the 7420 chip | verilog | RefModule | 19 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob065_7420_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 2/- | - | 17.5 | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob070_ece241_2013_q2 | [verilogeval](#sources) | a digital system with four inputs (a,b,c,d) that generates a logic-1 when 2,... | verilog | RefModule | 19 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob070_ece241_2013_q2_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 2/- | - | - | - | - |
| Prob075_counter_2bc | [verilogeval](#sources) | a two-bit saturating counter | verilog | RefModule | 22 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob075_counter_2bc_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 2/- | - | - | - | - |
| Prob077_wire_decl | [verilogeval](#sources) | the following circuit | verilog | RefModule | 18 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob077_wire_decl_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 2/- | - | - | - | - |
| Prob081_7458 | [verilogeval](#sources) | - | verilog | RefModule | 21 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob081_7458_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 2/- | 4 | 47.5 | mismatch | extract |
| Prob088_ece241_2014_q5b | [verilogeval](#sources) | the following Mealy finite-state machine which is an implementation of the 2'... | verilog | RefModule | 25 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob088_ece241_2014_q5b_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 2/- | - | - | - | - |
| Prob091_2012_q2b | [verilogeval](#sources) | the state output logic for this finite-state machine | verilog | RefModule | 13 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob091_2012_q2b_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 2/- | - | 40.0 | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob099_m2014_q6c | [verilogeval](#sources) | - | verilog | RefModule | 13 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob099_m2014_q6c_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 2/- | - | - | - | - |
| Prob112_always_case2 | [verilogeval](#sources) | a priority encoder | verilog | RefModule | 30 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob112_always_case2_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 2/- | 5 | 50.0 | mismatch | extract |
| Prob127_lemmings1 | [verilogeval](#sources) | a simple game called Lemmings which involves critters with fairly simple brains | verilog | RefModule | 31 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob127_lemmings1_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 2/- | - | - | - | - |
| Prob134_2014_q3c | [verilogeval](#sources) | the output logic and next state logic for an FSM using the table shown below | verilog | RefModule | 36 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob134_2014_q3c_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 2/- | - | - | - | - |
| Prob147_circuit10 | [verilogeval](#sources) | a sequential circuit | verilog | RefModule | 18 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob147_circuit10_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 2/- | - | - | - | - |
| Prob005_notgate | [verilogeval](#sources) | a NOT gate | verilog | RefModule | 10 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob005_notgate_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob010_mt2015_q4a | [verilogeval](#sources) | the boolean function z = (x^y) & x | verilog | RefModule | 11 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob010_mt2015_q4a_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob011_norgate | [verilogeval](#sources) | a NOR gate | verilog | RefModule | 11 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob011_norgate_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob012_xnorgate | [verilogeval](#sources) | an XNOR gate | verilog | RefModule | 11 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob012_xnorgate_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob013_m2014_q4e | [verilogeval](#sources) | a 2-input NOR gate | verilog | RefModule | 11 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob013_m2014_q4e_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob014_andgate | [verilogeval](#sources) | a 2-input AND gate | verilog | RefModule | 11 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob014_andgate_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob019_m2014_q4f | [verilogeval](#sources) | the following circuit in Verilog | verilog | RefModule | 11 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob019_m2014_q4f_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob020_mt2015_eq2 | [verilogeval](#sources) | a circuit that has two 2-bit inputs A[1:0] and B[1:0], and produces an output z | verilog | RefModule | 11 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob020_mt2015_eq2_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob022_mux2to1 | [verilogeval](#sources) | a one-bit wide, 2-to-1 multiplexer | verilog | RefModule | 12 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob022_mux2to1_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob026_alwaysblock1 | [verilogeval](#sources) | an AND gate using both an assign statement and a combinational always block | verilog | RefModule | 13 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob026_alwaysblock1_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob029_m2014_q4g | [verilogeval](#sources) | - | verilog | RefModule | 12 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob029_m2014_q4g_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob039_always_if | [verilogeval](#sources) | a 2-to-1 mux that chooses between a and b | verilog | RefModule | 15 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob039_always_if_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob048_m2014_q4c | [verilogeval](#sources) | a simple D flip flop with active high synchronous reset (reset output to 0) | verilog | RefModule | 17 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob048_m2014_q4c_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob049_m2014_q4b | [verilogeval](#sources) | a D flip flop, positive edge triggered, with an asynchronous reset "ar" | verilog | RefModule | 17 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob049_m2014_q4b_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob050_kmap1 | [verilogeval](#sources) | the circuit described by the Karnaugh map below | verilog | RefModule | 12 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob050_kmap1_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob053_m2014_q4d | [verilogeval](#sources) | the following circuit: A D flip-flop takes as input the output of a two-input... | verilog | RefModule | 16 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob053_m2014_q4d_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob056_ece241_2013_q7 | [verilogeval](#sources) | a JK flip-flop with the following truth table | verilog | RefModule | 13 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob056_ece241_2013_q7_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob057_kmap2 | [verilogeval](#sources) | the circuit described by the Karnaugh map below | verilog | RefModule | 13 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob057_kmap2_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob061_2014_q4a | [verilogeval](#sources) | - | verilog | RefModule | 18 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob061_2014_q4a_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob069_truthtable1 | [verilogeval](#sources) | - | verilog | RefModule | 15 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob069_truthtable1_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob083_mt2015_q4b | [verilogeval](#sources) | - | verilog | RefModule | 11 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob083_mt2015_q4b_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob090_circuit1 | [verilogeval](#sources) | a combinational circuit | verilog | RefModule | 11 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob090_circuit1_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob098_circuit7 | [verilogeval](#sources) | - | verilog | RefModule | 12 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob098_circuit7_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob101_circuit4 | [verilogeval](#sources) | a combinational circuit | verilog | RefModule | 13 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob101_circuit4_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob102_circuit3 | [verilogeval](#sources) | a combinational circuit | verilog | RefModule | 13 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob102_circuit3_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob103_circuit2 | [verilogeval](#sources) | a combinational circuit | verilog | RefModule | 13 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob103_circuit2_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob104_mt2015_muxdff | [verilogeval](#sources) | - | verilog | RefModule | 15 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob104_mt2015_muxdff_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob107_fsm1s | [verilogeval](#sources) | - | verilog | RefModule | 28 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob107_fsm1s_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob109_fsm1 | [verilogeval](#sources) | a Moore machine with the diagram described below: B (1) --0--> A B (1) --1-->... | verilog | RefModule | 28 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob109_fsm1_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob110_fsm2 | [verilogeval](#sources) | a Moore state machine with two states, two inputs, and one output according t... | verilog | RefModule | 29 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob110_fsm2_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob111_fsm2s | [verilogeval](#sources) | a Moore state machine with two states, two inputs, and one output according t... | verilog | RefModule | 29 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob111_fsm2s_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob113_2012_q1g | [verilogeval](#sources) | the function f shown in the Karnaugh map below | verilog | RefModule | 29 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob113_2012_q1g_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob116_m2014_q3 | [verilogeval](#sources) | the function f shown in the Karnaugh map below | verilog | RefModule | 29 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob116_m2014_q3_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob122_kmap4 | [verilogeval](#sources) | the Karnaugh map below | verilog | RefModule | 32 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob122_kmap4_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob125_kmap3 | [verilogeval](#sources) | the Karnaugh map below | verilog | RefModule | 32 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob125_kmap3_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob131_mt2015_q4 | [verilogeval](#sources) | - | verilog | RefModule | 11 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob131_mt2015_q4_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob132_always_if2 | [verilogeval](#sources) | - | verilog | RefModule | 25 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob132_always_if2_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob135_m2014_q6b | [verilogeval](#sources) | the state machine shown below: A (0) --0--> B A (0) --1--> A B (0) --0--> C B... | verilog | RefModule | 27 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob135_m2014_q6b_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob001_zero | [verilogeval](#sources) | - | verilog | RefModule | 9 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob001_zero_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 0/- | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob002_m2014_q4i | [verilogeval](#sources) | - | verilog | RefModule | 9 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob002_m2014_q4i_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 0/- | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob003_step_one | [verilogeval](#sources) | - | verilog | RefModule | 9 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob003_step_one_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 0/- | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob004_vector2 | [verilogeval](#sources) | - | verilog | RefModule | 10 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob004_vector2_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 0/- | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob006_vectorr | [verilogeval](#sources) | - | verilog | RefModule | 10 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob006_vectorr_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 0/- | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob007_wire | [verilogeval](#sources) | - | verilog | RefModule | 10 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob007_wire_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 0/- | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob008_m2014_q4h | [verilogeval](#sources) | - | verilog | RefModule | 10 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob008_m2014_q4h_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 0/- | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob015_vector1 | [verilogeval](#sources) | a combinational circuit that splits an input half-word (16 bits, [15:0] ) int... | verilog | RefModule | 11 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob015_vector1_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 0/- | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob023_vector100r | [verilogeval](#sources) | - | verilog | RefModule | 12 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob023_vector100r_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 0/- | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob028_m2014_q4a | [verilogeval](#sources) | - | verilog | RefModule | 14 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob028_m2014_q4a_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 0/- | - | - | - | - |
| Prob032_vector0 | [verilogeval](#sources) | - | verilog | RefModule | 14 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob032_vector0_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 0/- | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob034_dff8 | [verilogeval](#sources) | - | verilog | RefModule | 15 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob034_dff8_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 0/- | - | 788.3 | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob042_vector4 | [verilogeval](#sources) | - | verilog | RefModule | 10 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob042_vector4_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 0/- | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob059_wire4 | [verilogeval](#sources) | - | verilog | RefModule | 15 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob059_wire4_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 0/- | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob064_vector3 | [verilogeval](#sources) | - | verilog | RefModule | 18 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob064_vector3_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 0/- | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob071_always_casez | [verilogeval](#sources) | a priority encoder for an 8-bit input | verilog | RefModule | 22 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob071_always_casez_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | 0/- | - | - | - | - |
| Prob156_review2015_fancytimer | [verilogeval](#sources) | a timer with one input that: (1) is started when a particular input pattern (... | verilog | RefModule | 78 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob156_review2015_fancytimer_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob151_review2015_fsm | [verilogeval](#sources) | a timer that: (1) is started when a particular pattern (1101) is detected, (2... | verilog | RefModule | 56 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob151_review2015_fsm_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob078_dualedge | [verilogeval](#sources) | - | verilog | RefModule | 25 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob078_dualedge_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob145_circuit8 | [verilogeval](#sources) | a sequential circuit | verilog | RefModule | 17 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob145_circuit8_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob046_dff8p | [verilogeval](#sources) | - | verilog | RefModule | 16 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob046_dff8p_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | out of scope: stopped at equiv (equiv header.check.detail: absolute or home path in 'equiv-c) | map |
| Prob031_dff | [verilogeval](#sources) | a single D flip-flop | verilog | RefModule | 15 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob031_dff_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - |

</details>

<details><summary>T3 HDL, no testbench (52 designs)</summary>

Rule: HDL (Verilog) with no testbench file.

| design | suite | what it does | format | top | LOC | seq | mem | mul | add | fsm | latch | hier | bbox | testbench | vectors | iverilog | Odin sim | VTR stage | LUTs | blocks | FFs | pins | mult/mem | cpd ns | chan w | gates/depth | 4-LUT/depth | 6-LUT/depth | cells | core um2 | LVS | stage |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| stereovision2 | [vtr-verilog](#sources) | Computer Vision | verilog | sv_chip2_hierarchy_no_mem | 1846 | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | 8426 | 1689 | 15573 | 331 | 468/0 | 13.2648 | 90 | - | - | - | - | - | - | - |
| stereovision0 | [vtr-verilog](#sources) | Computer Vision | verilog | sv_chip0_hierarchy_no_mem | 3905 | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | 6887 | 702 | 11458 | 366 | 0/0 | 3.8277 | 52 | - | - | - | - | - | - | - |
| stereovision1 | [vtr-verilog](#sources) | Computer Vision | verilog | sv_chip1_hierarchy_no_mem | 2553 | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | 6462 | 758 | 10315 | 278 | 152/0 | 5.72613 | 76 | - | - | - | - | - | - | - |
| b22 | [itc99](#sources) | - | verilog | - | 2751 | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | 56695/105 | 8495/33 | 6234/20 | - | - | - | - |
| blob_merge | [vtr-verilog](#sources) | Image Processing | verilog | RLE_BlobMerging | 1617 | ✓ | ✗ | ✗ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | - | - | - | 6015 | 486 | 575 | 232 | 0/0 | 14.668 | 62 | 61064/78 | 8741/30 | 5264/18 | - | - | - | - |
| b17 | [itc99](#sources) | - | verilog | - | 940 | ✓ | ✗ | ✗ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | 107358/80 | 7388/19 | 5240/12 | - | - | - | - |
| b20 | [itc99](#sources) | - | verilog | - | 1842 | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | 37565/105 | 5680/33 | 4108/20 | - | - | - | - |
| b21 | [itc99](#sources) | - | verilog | - | 1853 | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | 38305/105 | 5603/34 | 4058/21 | - | - | - | - |
| diffeq1 | [vtr-verilog](#sources) | Math | verilog | diffeq_paj_convert | 56 | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | 294 | 31 | 193 | 258 | 5/0 | 17.2038 | 58 | 14398/101 | 4897/34 | 3585/23 | - | - | - | - |
| b18 | [itc99](#sources) | - | verilog | - | 1931 | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | 36964/105 | 4976/0 | 3500/0 | - | - | - | - |
| b19 | [itc99](#sources) | - | verilog | - | 1993 | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | 36964/105 | 4976/0 | 3500/0 | - | - | - | - |
| or1200 | [vtr-verilog](#sources) | Soft Processor | verilog | or1200_flat | 5237 | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | 2473 | 237 | 672 | 782 | 1/64 | 8.74562 | 82 | - | - | - | - | - | - | - |
| b15 | [itc99](#sources) | - | verilog | b15 | 805 | ✓ | ✗ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | 26705/80 | 3326/19 | 2322/12 | - | - | - | - |
| mkDelayWorker32B | [vtr-verilog](#sources) | Packet Processing | verilog | mkDelayWorker32B | 6628 | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | 2057 | 63 | 34 | 1066 | 0/1336 | 6.8227 | 38 | - | - | - | - | - | - | - |
| sha | [vtr-verilog](#sources) | Cryptography | verilog | sha1 | 2171 | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | 1290 | 142 | 893 | 74 | 0/0 | 9.86096 | 64 | 8125/79 | 2788/30 | 1583/20 | - | - | - | - |
| mkSMAdapter4B | [vtr-verilog](#sources) | Packet Processing | verilog | mkSMAdapter4B | 4348 | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | 1200 | 118 | 639 | 403 | 0/153 | 6.19734 | 48 | - | - | - | - | - | - | - |
| raygentop | [vtr-verilog](#sources) | Ray Tracing | verilog | paj_raygentop_hierarchy_no_mem | 2978 | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | 1195 | 127 | 946 | 560 | 15/21 | 5.43116 | 56 | - | - | - | - | - | - | - |
| b14 | [itc99](#sources) | - | verilog | b14 | 904 | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | 9335/105 | 1352/32 | 984/20 | - | - | - | - |
| boundtop | [vtr-verilog](#sources) | Ray Tracing | verilog | paj_boundtop_hierarchy_no_mem | 2825 | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | 572 | 41 | 383 | 468 | 0/32 | 3.06393 | 40 | - | - | - | - | - | - | - |
| b12 | [itc99](#sources) | - | verilog | b12 | 635 | ✓ | ✗ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | 5026/26 | 673/8 | 484/5 | - | - | - | - |
| b11 | [itc99](#sources) | - | verilog | b11 | 138 | ✓ | ✗ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | 3924/39 | 515/14 | 357/9 | - | - | - | - |
| mkPktMerge | [vtr-verilog](#sources) | Packet Processing | verilog | mkPktMerge | 1535 | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✓ | ✗ | ✗ | - | - | - | 329 | 19 | 18 | 467 | 0/459 | 4.09815 | 36 | fail: mkPktMerge.v:566:1: error: unresolved_module: module 'dual_port_ram' is not defined; if you meant th/fail: mkPktMerge.v:566:1: error: unresolved_module: module 'dual_port_ram' is not defined; if you meant th | fail: mkPktMerge.v:566:1: error: unresolved_module: module 'dual_port_ram' is not defined; if you meant th/fail: mkPktMerge.v:566:1: error: unresolved_module: module 'dual_port_ram' is not defined; if you meant th | fail: mkPktMerge.v:566:1: error: unresolved_module: module 'dual_port_ram' is not defined; if you meant th/fail: mkPktMerge.v:566:1: error: unresolved_module: module 'dual_port_ram' is not defined; if you meant th | - | - | - | - |
| b05 | [itc99](#sources) | - | verilog | b05 | 444 | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | 20479/98 | 306/12 | 196/8 | - | - | - | - |
| ch_intrinsics | [vtr-verilog](#sources) | Memory Init | verilog | memset | 292 | ✓ | ✓ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | - | - | - | 192 | 12 | 82 | 229 | 0/8 | 2.12094 | 38 | fail: ch_intrinsics.v:34:1: error: unresolved_module: module 'single_port_ram' is not defined; if you mean/fail: ch_intrinsics.v:34:1: error: unresolved_module: module 'single_port_ram' is not defined; if you mean | fail: ch_intrinsics.v:34:1: error: unresolved_module: module 'single_port_ram' is not defined; if you mean/fail: ch_intrinsics.v:34:1: error: unresolved_module: module 'single_port_ram' is not defined; if you mean | fail: ch_intrinsics.v:34:1: error: unresolved_module: module 'single_port_ram' is not defined; if you mean/fail: ch_intrinsics.v:34:1: error: unresolved_module: module 'single_port_ram' is not defined; if you mean | - | - | - | - |
| stereovision3 | [vtr-verilog](#sources) | Computer Vision | verilog | sv_chip3_hierarchy_no_mem | 1061 | ✓ | ✗ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | 171 | 15 | 120 | 53 | 0/0 | 2.63369 | 30 | 2042/17 | 233/5 | 175/4 | - | - | - | - |
| diffeq2 | [vtr-verilog](#sources) | Math | verilog | diffeq_f_systemC | 63 | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | 198 | 22 | 96 | 162 | 5/0 | 13.5453 | 44 | 14387/93 | 162/22 | 105/13 | - | - | - | - |
| b04 | [itc99](#sources) | - | verilog | b04 | 113 | ✓ | ✗ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | 1782/54 | 133/6 | 104/4 | - | - | - | - |
| b07 | [itc99](#sources) | - | verilog | b07 | 125 | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | 776/17 | 128/6 | 95/4 | - | - | - | - |
| b13 | [itc99](#sources) | - | verilog | b13 | 320 | ✓ | ✗ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | 1034/24 | 90/3 | 70/3 | - | - | - | - |
| b09 | [itc99](#sources) | - | verilog | b09 | 91 | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | 248/13 | 61/4 | 47/3 | - | - | - | - |
| b10 | [itc99](#sources) | - | verilog | b10 | 178 | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | 211/10 | 55/4 | 39/2 | - | - | - | - |
| b03 | [itc99](#sources) | - | verilog | b03 | 133 | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | 193/10 | 56/4 | 37/3 | - | - | - | - |
| b08 | [itc99](#sources) | - | verilog | b08 | 88 | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | 654/16 | 56/5 | 35/3 | - | - | - | - |
| b06 | [itc99](#sources) | - | verilog | b06 | 130 | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | 72/7 | 17/3 | 14/2 | - | - | - | - |
| multiclock_reader_writer | [vtr-verilog](#sources) | - | verilog | multiclock_reader_writer | 61 | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | 118/9 | 16/2 | 10/1 | - | - | - | - |
| b02 | [itc99](#sources) | - | verilog | b02 | 74 | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | 26/6 | 10/2 | 9/2 | - | - | - | - |
| b01 | [itc99](#sources) | - | verilog | b01 | 117 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | 105/10 | 18/3 | 5/1 | - | - | - | - |
| multiclock_output_and_latch | [vtr-verilog](#sources) | - | verilog | - | 63 | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | 9/3 | 5/1 | 5/1 | - | - | - | - |
| multiclock_separate_and_latch | [vtr-verilog](#sources) | - | verilog | - | 53 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | 3/1 | 3/1 | 3/1 | - | - | - | - |
| and_latch | [vtr-verilog](#sources) | - | verilog | and_latch | 21 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | 1/1 | 1/1 | 1/1 | - | - | - | - |
| single_ff | [vtr-verilog](#sources) | - | verilog | top | 5 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | 0/0 | 0/0 | 0/0 | - | - | - | - |
| single_wire | [vtr-verilog](#sources) | - | verilog | top | 3 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | 0/0 | 0/0 | 0/0 | - | - | - | - |
| mcml | [vtr-verilog](#sources) | Medical Physics | verilog | - | 24507 | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| arm_core | [vtr-verilog](#sources) | - | verilog | - | 8211 | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| LU64PEEng | [vtr-verilog](#sources) | - | verilog | - | 6043 | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| LU32PEEng | [vtr-verilog](#sources) | Math | verilog | - | 5497 | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| LU8PEEng | [vtr-verilog](#sources) | Math | verilog | - | 5033 | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| raygentop_nolatches | [vtr-verilog](#sources) | - | verilog | - | 3178 | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| spree | [vtr-verilog](#sources) | - | verilog | - | 3072 | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| boundtop_nolatches | [vtr-verilog](#sources) | - | verilog | - | 3053 | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| bgm | [vtr-verilog](#sources) | Finance | verilog | - | 2663 | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| ch_intrinsics_nolatches | [vtr-verilog](#sources) | - | verilog | - | 301 | ✓ | ✓ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | fail: ch_intrinsics_nolatches.v:31:1: error: unresolved_module: module 'single_port_ram' is not defined; i/fail: ch_intrinsics_nolatches.v:31:1: error: unresolved_module: module 'single_port_ram' is not defined; i | fail: ch_intrinsics_nolatches.v:31:1: error: unresolved_module: module 'single_port_ram' is not defined; i/fail: ch_intrinsics_nolatches.v:31:1: error: unresolved_module: module 'single_port_ram' is not defined; i | fail: ch_intrinsics_nolatches.v:31:1: error: unresolved_module: module 'single_port_ram' is not defined; i/fail: ch_intrinsics_nolatches.v:31:1: error: unresolved_module: module 'single_port_ram' is not defined; i | - | - | - | - |

</details>

<details><summary>T4 netlist only (219 designs)</summary>

Rule: BLIF netlist, no HDL.

| design | suite | what it does | format | top | LOC | seq | mem | mul | add | fsm | latch | hier | bbox | testbench | vectors | iverilog | Odin sim | VTR stage | LUTs | blocks | FFs | pins | mult/mem | cpd ns | chan w | gates/depth | 4-LUT/depth | 6-LUT/depth | cells | core um2 | LVS | stage |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| clma | [vtr-blif](#sources) | Bus interface | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 8380/16 | - | - | - | - | - |
| s38584.1 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 6269/9 | - | - | - | - | - |
| s38417 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 6096/11 | - | - | - | - | - |
| ex1010 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 4598/8 | - | - | - | - | - |
| pdc | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 4575/9 | - | - | - | - | - |
| spla | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 3690/8 | - | - | - | - | - |
| elliptic | [vtr-blif](#sources) | Fifth Order Elliptic Filter | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 3602/18 | - | - | - | - | - |
| frisc | [vtr-blif](#sources) | RISC Microprocessor | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 3539/23 | - | - | - | - | - |
| ex1010 | [mcnc20](#sources) | - | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | 2777 | 314 | 0 | 20 | 0/0 | 9.8022 | 84 | - | 4598/8 | - | - | - | - | - |
| s38584.1 | [mcnc20](#sources) | - | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | 2190 | 182 | 1141 | 343 | 0/0 | 4.65105 | 48 | - | 6269/9 | - | - | - | - | - |
| s38417 | [mcnc20](#sources) | - | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | 2189 | 179 | 1345 | 135 | 0/0 | 4.96812 | 42 | - | 6096/11 | - | - | - | - | - |
| pdc | [mcnc20](#sources) | - | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | 1973 | 176 | 0 | 56 | 0/0 | 7.42762 | 72 | - | 4575/9 | - | - | - | - | - |
| s298 | [vtr-blif](#sources) | Finite state machine "from a PLD" | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 1930/15 | - | - | - | - | - |
| apex2 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 1878/8 | - | - | - | - | - |
| seq | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 1750/7 | - | - | - | - | - |
| bigkey | [vtr-blif](#sources) | Key encryption circuit | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 1707/3 | - | - | - | - | - |
| frisc | [mcnc20](#sources) | RISC Microprocessor | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | 1668 | 153 | 814 | 136 | 0/0 | 8.694 | 66 | - | 3539/23 | - | - | - | - | - |
| des | [vtr-blif](#sources) | DES data encryption circuit | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 1591/6 | - | - | - | - | - |
| alu4 | [vtr-blif](#sources) | ALU | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 1522/7 | - | - | - | - | - |
| diffeq | [vtr-blif](#sources) | Differential Equation Solver | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 1494/14 | - | - | - | - | - |
| elliptic | [mcnc20](#sources) | Fifth Order Elliptic Filter | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | 1463 | 137 | 884 | 245 | 0/0 | 7.59909 | 58 | - | 3602/18 | - | - | - | - | - |
| spla | [mcnc20](#sources) | - | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | 1445 | 131 | 0 | 62 | 0/0 | 6.39096 | 60 | - | 3690/8 | - | - | - | - | - |
| misex3 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 1397/7 | - | - | - | - | - |
| dsip | [vtr-blif](#sources) | Encryption circuit | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 1370/3 | - | - | - | - | - |
| apex4 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 1261/6 | - | - | - | - | - |
| ex5p | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 1064/7 | - | - | - | - | - |
| tseng | [vtr-blif](#sources) | Bus controller | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 1046/13 | - | - | - | - | - |
| i10 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 995/13 | - | - | - | - | - |
| apex2 | [mcnc20](#sources) | - | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | 992 | 92 | 0 | 42 | 0/0 | 5.89143 | 54 | - | 1878/8 | - | - | - | - | - |
| des | [mcnc20](#sources) | DES data encryption circuit | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | 901 | 77 | 0 | 501 | 0/0 | 4.68402 | 38 | - | 1591/6 | - | - | - | - | - |
| apex3 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 869/6 | - | - | - | - | - |
| apex4 | [mcnc20](#sources) | - | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | 865 | 80 | 0 | 28 | 0/0 | 5.74616 | 60 | - | 1261/6 | - | - | - | - | - |
| seq | [mcnc20](#sources) | - | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | 855 | 75 | 0 | 76 | 0/0 | 4.95078 | 54 | - | 1750/7 | - | - | - | - | - |
| alu4 | [mcnc20](#sources) | ALU | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | 818 | 68 | 0 | 22 | 0/0 | 5.0705 | 42 | - | 1522/7 | - | - | - | - | - |
| cps | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 756/5 | - | - | - | - | - |
| C7552 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 739/10 | - | - | - | - | - |
| misex3 | [mcnc20](#sources) | - | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | 714 | 62 | 0 | 28 | 0/0 | 4.81741 | 48 | - | 1397/7 | - | - | - | - | - |
| apex1 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 699/7 | - | - | - | - | - |
| dsip | [mcnc20](#sources) | Encryption circuit | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | 686 | 66 | 224 | 426 | 0/0 | 2.72755 | 34 | - | 1370/3 | - | - | - | - | - |
| s298 | [mcnc20](#sources) | Finite state machine "from a PLD" | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | 661 | 58 | 8 | 10 | 0/0 | 6.32231 | 46 | - | 1930/15 | - | - | - | - | - |
| parker1986 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 660/13 | - | - | - | - | - |
| pair | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 647/7 | - | - | - | - | - |
| C5315 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 620/10 | - | - | - | - | - |
| diffeq | [mcnc20](#sources) | Differential Equation Solver | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | 580 | 53 | 310 | 103 | 0/0 | 4.91464 | 42 | - | 1494/14 | - | - | - | - | - |
| bigkey | [mcnc20](#sources) | Key encryption circuit | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | 572 | 52 | 224 | 460 | 0/0 | 2.59891 | 38 | - | 1707/3 | - | - | - | - | - |
| s5378 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 571/6 | - | - | - | - | - |
| misex3c | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 549/6 | - | - | - | - | - |
| apex5 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 534/5 | - | - | - | - | - |
| C6288 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 527/28 | - | - | - | - | - |
| k2 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 518/7 | - | - | - | - | - |
| dalu | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 500/6 | - | - | - | - | - |
| table5 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 485/6 | - | - | - | - | - |
| i8 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 481/5 | - | - | - | - | - |
| table3 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 480/6 | - | - | - | - | - |
| ex5p | [mcnc20](#sources) | - | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | 467 | 39 | 0 | 71 | 0/0 | 5.34702 | 48 | - | 1064/7 | - | - | - | - | - |
| mm30a | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 467/58 | - | - | - | - | - |
| cordic | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 466/9 | - | - | - | - | - |
| s9234.1 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 459/8 | - | - | - | - | - |
| clma | [mcnc20](#sources) | Bus interface | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | 450 | 82 | 26 | 465 | 0/0 | 5.41555 | 36 | - | 8380/16 | - | - | - | - | - |
| ex4p | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 444/5 | - | - | - | - | - |
| C3540 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 431/12 | - | - | - | - | - |
| scf | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 416/5 | - | - | - | - | - |
| tseng | [mcnc20](#sources) | Bus controller | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | 407 | 34 | 219 | 174 | 0/0 | 4.62879 | 48 | - | 1046/13 | - | - | - | - | - |
| bbrtas | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 406/18 | - | - | - | - | - |
| apex6 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 393/6 | - | - | - | - | - |
| sbc | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 384/5 | - | - | - | - | - |
| frg2 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 379/6 | - | - | - | - | - |
| x3 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 377/5 | - | - | - | - | - |
| i9 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 376/5 | - | - | - | - | - |
| ecc | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 330/5 | - | - | - | - | - |
| daio-rec | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 311/7 | - | - | - | - | - |
| rot | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 307/8 | - | - | - | - | - |
| s1488 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 296/4 | - | - | - | - | - |
| s1238 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 292/8 | - | - | - | - | - |
| s1494 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 292/5 | - | - | - | - | - |
| vda | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 291/6 | - | - | - | - | - |
| e64 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 274/4 | - | - | - | - | - |
| planet | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 266/4 | - | - | - | - | - |
| planet1 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 266/4 | - | - | - | - | - |
| s1196 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 264/7 | - | - | - | - | - |
| C2670 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 258/7 | - | - | - | - | - |
| duke2 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 251/5 | - | - | - | - | - |
| sand | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 243/5 | - | - | - | - | - |
| styr | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 238/5 | - | - | - | - | - |
| s1423 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 221/15 | - | - | - | - | - |
| ph-decod | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 219/6 | - | - | - | - | - |
| gcd | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 218/11 | - | - | - | - | - |
| s953 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 214/5 | - | - | - | - | - |
| t481 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 214/7 | - | - | - | - | - |
| mm9b | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 204/20 | - | - | - | - | - |
| i7 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 203/2 | - | - | - | - | - |
| alu2 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 197/10 | - | - | - | - | - |
| s1 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 195/10 | - | - | - | - | - |
| x4 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 194/3 | - | - | - | - | - |
| too-lrg | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 187/7 | - | - | - | - | - |
| i6 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 182/2 | - | - | - | - | - |
| C880 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 174/9 | - | - | - | - | - |
| s838 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 167/8 | - | - | - | - | - |
| rd84 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 157/6 | - | - | - | - | - |
| C1908 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 145/10 | - | - | - | - | - |
| s832 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 145/5 | - | - | - | - | - |
| 9sym | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 144/6 | - | - | - | - | - |
| x1 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 143/4 | - | - | - | - | - |
| mm9a | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 142/17 | - | - | - | - | - |
| clip | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 140/5 | - | - | - | - | - |
| example2 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 138/4 | - | - | - | - | - |
| bw | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 132/4 | - | - | - | - | - |
| C432 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 124/11 | - | - | - | - | - |
| ex1 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 124/4 | - | - | - | - | - |
| s820 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 120/5 | - | - | - | - | - |
| mult32a | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 116/24 | - | - | - | - | - |
| dk16 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 105/4 | - | - | - | - | - |
| keyb | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 103/5 | - | - | - | - | - |
| apex7 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 102/5 | - | - | - | - | - |
| s510 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 101/5 | - | - | - | - | - |
| i4 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 98/5 | - | - | - | - | - |
| 9symml | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 97/6 | - | - | - | - | - |
| s838.1 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 95/9 | - | - | - | - | - |
| cse | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 90/4 | - | - | - | - | - |
| sao2 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 90/5 | - | - | - | - | - |
| i5 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 88/6 | - | - | - | - | - |
| s713 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 88/8 | - | - | - | - | - |
| term1 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 88/5 | - | - | - | - | - |
| s641 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 87/9 | - | - | - | - | - |
| pma | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 85/4 | - | - | - | - | - |
| tbk | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 84/8 | - | - | - | - | - |
| rd73 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 83/5 | - | - | - | - | - |
| mm4a | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 78/10 | - | - | - | - | - |
| ttt2 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 75/4 | - | - | - | - | - |
| C1355 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 74/4 | - | - | - | - | - |
| C499 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 74/4 | - | - | - | - | - |
| i2 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 74/5 | - | - | - | - | - |
| s400 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 69/4 | - | - | - | - | - |
| s344 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 67/4 | - | - | - | - | - |
| s349 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 67/4 | - | - | - | - | - |
| vg2 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 67/4 | - | - | - | - | - |
| bbsse | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 64/6 | - | - | - | - | - |
| inc | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 64/4 | - | - | - | - | - |
| sse | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 64/6 | - | - | - | - | - |
| s444 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 62/4 | - | - | - | - | - |
| ex6 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 60/7 | - | - | - | - | - |
| s382 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 60/4 | - | - | - | - | - |
| s526n | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 60/4 | - | - | - | - | - |
| 5xp1 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 57/4 | - | - | - | - | - |
| mult16a | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 57/12 | - | - | - | - | - |
| b12 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 56/4 | - | - | - | - | - |
| s386 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 56/3 | - | - | - | - | - |
| cht | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 55/2 | - | - | - | - | - |
| f51m | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 54/4 | - | - | - | - | - |
| s526 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 52/4 | - | - | - | - | - |
| opus | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 50/5 | - | - | - | - | - |
| frg1 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 49/6 | - | - | - | - | - |
| misex2 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 49/3 | - | - | - | - | - |
| unreg | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 48/2 | - | - | - | - | - |
| my-adder | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 47/16 | - | - | - | - | - |
| s420.1 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 47/5 | - | - | - | - | - |
| b9 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 46/3 | - | - | - | - | - |
| i3 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 46/3 | - | - | - | - | - |
| o64 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 46/4 | - | - | - | - | - |
| dk14 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 43/7 | - | - | - | - | - |
| comp | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 40/5 | - | - | - | - | - |
| c8 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 39/4 | - | - | - | - | - |
| count | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 39/5 | - | - | - | - | - |
| ldd | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 37/5 | - | - | - | - | - |
| ex4 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 35/4 | - | - | - | - | - |
| pcler8 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 35/4 | - | - | - | - | - |
| traffic | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 35/3 | - | - | - | - | - |
| lal | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 34/3 | - | - | - | - | - |
| mark1 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 34/3 | - | - | - | - | - |
| squar5 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 34/3 | - | - | - | - | - |
| bbara | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 33/3 | - | - | - | - | - |
| mult16b | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 31/1 | - | - | - | - | - |
| sqrt8ml | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 31/6 | - | - | - | - | - |
| sqrt8 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 29/4 | - | - | - | - | - |
| cc | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 26/3 | - | - | - | - | - |
| dk15 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 24/3 | - | - | - | - | - |
| s208.1 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 24/4 | - | - | - | - | - |
| s420 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 23/3 | - | - | - | - | - |
| sct | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 23/3 | - | - | - | - | - |
| cu | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 22/3 | - | - | - | - | - |
| i1 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 21/3 | - | - | - | - | - |
| misex1 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 21/3 | - | - | - | - | - |
| pcle | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 21/3 | - | - | - | - | - |
| decod | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 20/2 | - | - | - | - | - |
| pm1 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 19/3 | - | - | - | - | - |
| cm162a | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 18/3 | - | - | - | - | - |
| s208 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 18/3 | - | - | - | - | - |
| cmb | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 17/3 | - | - | - | - | - |
| x2 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 17/3 | - | - | - | - | - |
| tcon | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 16/1 | - | - | - | - | - |
| dk17 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 15/2 | - | - | - | - | - |
| mux | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 15/4 | - | - | - | - | - |
| beecount | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 14/2 | - | - | - | - | - |
| cm150a | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 14/3 | - | - | - | - | - |
| dk512 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 14/2 | - | - | - | - | - |
| rd53 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 12/4 | - | - | - | - | - |
| cm163a | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 11/3 | - | - | - | - | - |
| cm85a | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 11/3 | - | - | - | - | - |
| cm138a | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 10/2 | - | - | - | - | - |
| cm42a | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 10/1 | - | - | - | - | - |
| tav | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 9/2 | - | - | - | - | - |
| cm151a | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 8/3 | - | - | - | - | - |
| z4ml | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 8/3 | - | - | - | - | - |
| mc | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 7/2 | - | - | - | - | - |
| bbtas | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 6/2 | - | - | - | - | - |
| cm152a | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 6/3 | - | - | - | - | - |
| s27 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 6/2 | - | - | - | - | - |
| con1 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 5/2 | - | - | - | - | - |
| dk27 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 5/1 | - | - | - | - | - |
| parity | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 5/2 | - | - | - | - | - |
| b1 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 4/1 | - | - | - | - | - |
| cm82a | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 4/2 | - | - | - | - | - |
| daio | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 3/1 | - | - | - | - | - |
| lion | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 3/1 | - | - | - | - | - |
| majority | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 3/2 | - | - | - | - | - |
| C17 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 2/1 | - | - | - | - | - |
| xor5 | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 2/2 | - | - | - | - | - |
| chain_cout_fanout | [vtr-blif](#sources) | - | blif (k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 1/1 | - | - | - | - | - |
| shiftreg | [vtr-blif](#sources) | - | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | 0/0 | - | - | - | - | - |

</details>

<a id="sources"></a>

### Sources

- **brisc-v**: BRISC-V microcontroller (Arduino-on-RISC-V, Quartus project revert_timer). Upstream https://github.com/qiany21/Arduino-on-RISC-V.git at 1d5b591081511a8161b843d003ca7b80bad7fc45. Licence: MIT (Copyright (c) 2021 qiany21).
- **itc99**: ITC'99 (RTL Verilog, b01-b22 without b16). Upstream https://github.com/ccsl-uaegean/ITC99-RTL-Verilog at 8e6a23da036b7442ef4ea410c679d4cf21830a65. Licence: GPL-3.0 (the LICENSE file of this repository); the terms of the original ITC'99 distribution were not read.
- **mcnc20**: MCNC / LGSynth91 circuits as VTR ships them (4-LUT mapped BLIF, circuits.txt). Upstream https://github.com/verilog-to-routing/vtr-verilog-to-routing at 3c9a4d23b27d187bd67c79dc01a18ff1ffc21d9b. Licence: none-stated (data/meta/licences.toml rule mcnc); VTR LICENSE.md: MIT unless otherwise noted, in particular the benchmark circuits.
- **verilogeval**: VerilogEval problems (reference solutions of the spec-to-rtl dataset) with the Gate-Breaker Yosys netlists. Upstream https://github.com/NMSU-PEARL/verilog-eval.git at d60f0b10458746e2fefc2a98fa2455b77a32e8be. Licence: MIT (Copyright (c) 2023-2024 NVIDIA Research Projects).
- **vtr-blif**: VTR blif/2 and blif/4: ISCAS-85, ISCAS-89 and MCNC mapped to 2-input and 4-input LUTs. Upstream https://github.com/verilog-to-routing/vtr-verilog-to-routing at 3c9a4d23b27d187bd67c79dc01a18ff1ffc21d9b. Licence: not read: the licence of the individual ISCAS/MCNC files has not been checked.
- **vtr-verilog**: VTR Verilog benchmarks (top-level files of vtr_flow/benchmarks/verilog). Upstream https://github.com/verilog-to-routing/vtr-verilog-to-routing at 3c9a4d23b27d187bd67c79dc01a18ff1ffc21d9b. Licence: per design, as each file states (see licence_rule in designs.tsv and data/meta/licences.toml); VTR LICENSE.md: MIT unless otherwise noted, in particular the benchmark circuits.

Same table: [docs/benchmarks/catalogue.md](docs/benchmarks/catalogue.md); method: [docs/benchmarks/catalogue-method.md](docs/benchmarks/catalogue-method.md).
<!-- catalogue:end -->
