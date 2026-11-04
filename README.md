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

| design | what it does | suite | link | licence | LOC | tb | vec |
|---|---|---|---|---|---|---|---|
| quartus_project_revert_timer | BRISC-V microcontroller (Arduino-on-RISC-V) | [brisc-v](#sources) | [repo](https://github.com/qiany21/Arduino-on-RISC-V.git) | MIT | 4349 | ✓ | ✓ |

<details><summary>Flow and VTR QoR</summary>

| design | iverilog | Odin sim | VTR stage | LUTs | blocks | FFs | pins | mult/mem | cpd ns | chan w |
|---|---|---|---|---|---|---|---|---|---|---|
| quartus_project_revert_timer | - | - | - | - | - | - | - | - | - | - |

</details>

<details><summary>LUT forms</summary>

| design | gates/d | 4-LUT/d | 6-LUT/d |
|---|---|---|---|
| quartus_project_revert_timer | - | - | - |

</details>

<details><summary>Properties</summary>

| design | seq | mem | mul | add | fsm | latch | hier | bbox |
|---|---|---|---|---|---|---|---|---|
| quartus_project_revert_timer | - | - | - | - | - | - | - | - |

</details>

<details><summary>Silicon</summary>

| design | cells | core um2 | LVS | Si stage |
|---|---|---|---|---|
| quartus_project_revert_timer | - | - | - | - |

</details>

</details>

<details><summary>T2 HDL + testbench, small (156 designs)</summary>

Rule: HDL with a testbench and under 200 Verilog lines.

| design | what it does | suite | link | licence | LOC | tb | vec |
|---|---|---|---|---|---|---|---|
| Prob144_conwaylife | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 37 | ✓ | ✓ |
| Prob030_popcount255 | a population count circuit for a 255-bit input vector | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 14 | ✓ | ✓ |
| Prob153_gshare | a gshare branch predictor with 7-bit pc and 7-bit global history, hashed (usi... | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 49 | ✓ | ✓ |
| Prob108_rule90 | Rule 90, a one-dimensional cellular automaton with interesting properties | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 18 | ✓ | ✓ |
| Prob124_rule110 | Rule 110, a one-dimensional cellular automaton with interesting properties (s... | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 22 | ✓ | ✓ |
| Prob021_mux256to1v | a 4-bit wide, 256-to-1 multiplexer | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 11 | ✓ | ✓ |
| Prob092_gatesv100 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 16 | ✓ | ✓ |
| Prob105_rotate100 | a 100-bit left/right rotator, with synchronous load and left/right enable | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 20 | ✓ | ✓ |
| Prob115_shift18 | a 64-bit arithmetic shift register, with synchronous load | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 24 | ✓ | ✓ |
| Prob018_mux256to1 | a 1-bit wide, 256-to-1 multiplexer | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 11 | ✓ | ✓ |
| Prob017_mux2to1v | a 2-1 multiplexer | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 12 | ✓ | ✓ |
| Prob097_mux9to1v | a 16-bit wide, 9-to-1 multiplexer | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 32 | ✓ | ✓ |
| Prob052_gates100 | a combinational circuit with 100 inputs, in[99:0] | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 14 | ✓ | ✓ |
| Prob055_conditional | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 18 | ✓ | ✓ |
| Prob141_count_clock | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 47 | ✓ | ✓ |
| Prob066_edgecapture | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 20 | ✓ | ✓ |
| Prob082_lfsr32 | a 32-bit Galois LFSR with taps at bit positions 32, 22, 2, and 1 | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 25 | ✓ | ✓ |
| Prob118_history_shift | a 32-bit global history shift register, including support for rolling back st... | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 25 | ✓ | ✓ |
| Prob154_fsm_ps2data | a finite state machine that will search for message boundaries when given an... | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 42 | ✓ | ✓ |
| Prob068_countbcd | a 4-digit BCD (binary-coded decimal) counter | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 20 | ✓ | ✓ |
| Prob123_bugs_addsubz | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 19 | ✓ | ✓ |
| Prob043_vector5 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 14 | ✓ | ✓ |
| Prob146_fsm_serialdata | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 46 | ✓ | ✓ |
| Prob080_timer | a timer that counts down for a given number of clock cycles, then asserts a s... | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 18 | ✓ | ✓ |
| Prob155_lemmings4 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 60 | ✓ | ✓ |
| Prob073_dff16e | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 22 | ✓ | ✓ |
| Prob126_circuit6 | a combinational circuit | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 20 | ✓ | ✓ |
| Prob037_review2015_count1k | a counter that counts from 0 to 999, inclusive, with a period of 1000 cycles | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 15 | ✓ | ✓ |
| Prob033_ece241_2014_q1c | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 14 | ✓ | ✓ |
| Prob114_bugs_case | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 31 | ✓ | ✓ |
| Prob143_fsm_onehot | the state transition logic and output logic portions of the state machine (bu... | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 25 | ✓ | ✓ |
| Prob076_always_case | a 6-to-1 multiplexer | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 26 | ✓ | ✓ |
| Prob137_fsm_serial | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 38 | ✓ | ✓ |
| Prob084_ece241_2013_q12 | a circuit for an 8x1 memory, where writing to the memory is accomplished by s... | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 21 | ✓ | ✓ |
| Prob140_fsm_hdlc | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 37 | ✓ | ✓ |
| Prob149_ece241_2013_q4 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 46 | ✓ | ✓ |
| Prob044_vectorgates | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 15 | ✓ | ✓ |
| Prob094_gatesv | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 18 | ✓ | ✓ |
| Prob106_always_nolatches | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 21 | ✓ | ✓ |
| Prob130_circuit5 | a combinational circuit | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 21 | ✓ | ✓ |
| Prob133_2014_q3fsm | a finite state machine with inputs s and w | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 35 | ✓ | ✓ |
| Prob139_2013_q2bfsm | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 38 | ✓ | ✓ |
| Prob041_dff8r | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 16 | ✓ | ✓ |
| Prob045_edgedetect2 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 16 | ✓ | ✓ |
| Prob047_dff8ar | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 16 | ✓ | ✓ |
| Prob054_edgedetect | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 16 | ✓ | ✓ |
| Prob062_bugs_mux2 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 13 | ✓ | ✓ |
| Prob087_gates | a combinational circuit with two inputs, a and b | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 23 | ✓ | ✓ |
| Prob136_m2014_q6 | the state machine shown below: A (0) --0--> B A (0) --1--> A B (0) --0--> C B... | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 33 | ✓ | ✓ |
| Prob138_2012_q2fsm | the state machine shown below: A (0) --1--> B A (0) --0--> A B (0) --1--> C B... | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 31 | ✓ | ✓ |
| Prob016_m2014_q4j | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 11 | ✓ | ✓ |
| Prob121_2014_q3bfsm | a finite-state machine with the state-assigned table shown below | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 31 | ✓ | ✓ |
| Prob152_lemmings3 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 48 | ✓ | ✓ |
| Prob086_lfsr5 | a 5-bit maximal-length Galois LFSR with taps at bit positions 5 and 3 | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 23 | ✓ | ✓ |
| Prob096_review2015_fsmseq | a finite-state machine that searches for the sequence 1101 in an input bit st... | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 30 | ✓ | ✓ |
| Prob148_2013_q2afsm | the FSM described by the state diagram shown below: A --r0=0,r1=0,r2=0--> A A... | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 35 | ✓ | ✓ |
| Prob150_review2015_fsmonehot | the following Moore state machine with 3 input (d, done_counting, ack) and 3... | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 30 | ✓ | ✓ |
| Prob035_count1to10 | a decade counter that counts 1 through 10, inclusive | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 15 | ✓ | ✓ |
| Prob038_count15 | a 4-bit binary counter that counts from 0 through 15, inclusive, with a perio... | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 15 | ✓ | ✓ |
| Prob040_count10 | a decade counter that counts from 0 through 9, inclusive, with a period of 10 | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 15 | ✓ | ✓ |
| Prob060_m2014_q4k | a shift register with four D flops | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 20 | ✓ | ✓ |
| Prob063_review2015_shiftcount | a four-bit shift register that also acts as a down counter | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 18 | ✓ | ✓ |
| Prob067_countslow | a decade counter that counts from 0 through 9, inclusive, with a period of 10 | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 20 | ✓ | ✓ |
| Prob079_fsm3onehot | the state transition table for a Moore state machine with one input, one outp... | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 19 | ✓ | ✓ |
| Prob085_shift4 | a 4-bit shift register (right shift), with asynchronous positive edge trigger... | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 21 | ✓ | ✓ |
| Prob095_review2015_fsmshift | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 29 | ✓ | ✓ |
| Prob120_fsm3s | a Moore state machine with the following state transition table with one inpu... | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 30 | ✓ | ✓ |
| Prob128_fsm_ps2 | a finite state machine that will search for message boundaries when given an... | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 32 | ✓ | ✓ |
| Prob142_lemmings2 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 36 | ✓ | ✓ |
| Prob051_gates4 | a combinational circuit with four inputs, in[3:0] | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 14 | ✓ | ✓ |
| Prob072_thermostat | a heating/cooling thermostat controller which controls both a heater (during... | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 17 | ✓ | ✓ |
| Prob074_ece241_2014_q4 | a finite state machine with the following behavior | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 17 | ✓ | ✓ |
| Prob089_ece241_2014_q5a | a one-input one-output serial 2's complementer Moore state machine | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 26 | ✓ | ✓ |
| Prob093_ece241_2014_q3 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 14 | ✓ | ✓ |
| Prob100_fsm3comb | the following is the state transition table for a Moore state machine with on... | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 23 | ✓ | ✓ |
| Prob117_circuit9 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 17 | ✓ | ✓ |
| Prob119_fsm3 | a Moore state machine with the following state transition table with one inpu... | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 30 | ✓ | ✓ |
| Prob129_ece241_2013_q8 | a Mealy-type finite state machine that recognizes the sequence "101" on an in... | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 37 | ✓ | ✓ |
| Prob009_popcount3 | a "population count" circuit that counts the number of '1's in the input vector | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 10 | ✓ | ✓ |
| Prob024_hadd | a half adder | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 12 | ✓ | ✓ |
| Prob025_reduction | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 10 | ✓ | ✓ |
| Prob027_fadd | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 13 | ✓ | ✓ |
| Prob036_ringer | a circuit to control a cellphone's ringer and vibration motor | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 13 | ✓ | ✓ |
| Prob058_alwaysblock2 | an XOR gate three ways, using an assign statement (output out_assign), a comb... | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 16 | ✓ | ✓ |
| Prob065_7420 | the same functionality as the 7420 chip | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 19 | ✓ | ✓ |
| Prob070_ece241_2013_q2 | a digital system with four inputs (a,b,c,d) that generates a logic-1 when 2,... | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 19 | ✓ | ✓ |
| Prob075_counter_2bc | a two-bit saturating counter | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 22 | ✓ | ✓ |
| Prob077_wire_decl | the following circuit | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 18 | ✓ | ✓ |
| Prob081_7458 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 21 | ✓ | ✓ |
| Prob088_ece241_2014_q5b | the following Mealy finite-state machine which is an implementation of the 2'... | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 25 | ✓ | ✓ |
| Prob091_2012_q2b | the state output logic for this finite-state machine | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 13 | ✓ | ✓ |
| Prob099_m2014_q6c | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 13 | ✓ | ✓ |
| Prob112_always_case2 | a priority encoder | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 30 | ✓ | ✓ |
| Prob127_lemmings1 | a simple game called Lemmings which involves critters with fairly simple brains | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 31 | ✓ | ✓ |
| Prob134_2014_q3c | the output logic and next state logic for an FSM using the table shown below | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 36 | ✓ | ✓ |
| Prob147_circuit10 | a sequential circuit | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 18 | ✓ | ✓ |
| Prob005_notgate | a NOT gate | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 10 | ✓ | ✓ |
| Prob010_mt2015_q4a | the boolean function z = (x^y) & x | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 11 | ✓ | ✓ |
| Prob011_norgate | a NOR gate | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 11 | ✓ | ✓ |
| Prob012_xnorgate | an XNOR gate | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 11 | ✓ | ✓ |
| Prob013_m2014_q4e | a 2-input NOR gate | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 11 | ✓ | ✓ |
| Prob014_andgate | a 2-input AND gate | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 11 | ✓ | ✓ |
| Prob019_m2014_q4f | the following circuit in Verilog | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 11 | ✓ | ✓ |
| Prob020_mt2015_eq2 | a circuit that has two 2-bit inputs A[1:0] and B[1:0], and produces an output z | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 11 | ✓ | ✓ |
| Prob022_mux2to1 | a one-bit wide, 2-to-1 multiplexer | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 12 | ✓ | ✓ |
| Prob026_alwaysblock1 | an AND gate using both an assign statement and a combinational always block | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 13 | ✓ | ✓ |
| Prob029_m2014_q4g | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 12 | ✓ | ✓ |
| Prob039_always_if | a 2-to-1 mux that chooses between a and b | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 15 | ✓ | ✓ |
| Prob048_m2014_q4c | a simple D flip flop with active high synchronous reset (reset output to 0) | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 17 | ✓ | ✓ |
| Prob049_m2014_q4b | a D flip flop, positive edge triggered, with an asynchronous reset "ar" | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 17 | ✓ | ✓ |
| Prob050_kmap1 | the circuit described by the Karnaugh map below | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 12 | ✓ | ✓ |
| Prob053_m2014_q4d | the following circuit: A D flip-flop takes as input the output of a two-input... | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 16 | ✓ | ✓ |
| Prob056_ece241_2013_q7 | a JK flip-flop with the following truth table | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 13 | ✓ | ✓ |
| Prob057_kmap2 | the circuit described by the Karnaugh map below | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 13 | ✓ | ✓ |
| Prob061_2014_q4a | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 18 | ✓ | ✓ |
| Prob069_truthtable1 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 15 | ✓ | ✓ |
| Prob083_mt2015_q4b | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 11 | ✓ | ✓ |
| Prob090_circuit1 | a combinational circuit | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 11 | ✓ | ✓ |
| Prob098_circuit7 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 12 | ✓ | ✓ |
| Prob101_circuit4 | a combinational circuit | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 13 | ✓ | ✓ |
| Prob102_circuit3 | a combinational circuit | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 13 | ✓ | ✓ |
| Prob103_circuit2 | a combinational circuit | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 13 | ✓ | ✓ |
| Prob104_mt2015_muxdff | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 15 | ✓ | ✓ |
| Prob107_fsm1s | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 28 | ✓ | ✓ |
| Prob109_fsm1 | a Moore machine with the diagram described below: B (1) --0--> A B (1) --1-->... | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 28 | ✓ | ✓ |
| Prob110_fsm2 | a Moore state machine with two states, two inputs, and one output according t... | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 29 | ✓ | ✓ |
| Prob111_fsm2s | a Moore state machine with two states, two inputs, and one output according t... | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 29 | ✓ | ✓ |
| Prob113_2012_q1g | the function f shown in the Karnaugh map below | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 29 | ✓ | ✓ |
| Prob116_m2014_q3 | the function f shown in the Karnaugh map below | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 29 | ✓ | ✓ |
| Prob122_kmap4 | the Karnaugh map below | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 32 | ✓ | ✓ |
| Prob125_kmap3 | the Karnaugh map below | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 32 | ✓ | ✓ |
| Prob131_mt2015_q4 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 11 | ✓ | ✓ |
| Prob132_always_if2 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 25 | ✓ | ✓ |
| Prob135_m2014_q6b | the state machine shown below: A (0) --0--> B A (0) --1--> A B (0) --0--> C B... | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 27 | ✓ | ✓ |
| Prob001_zero | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 9 | ✓ | ✓ |
| Prob002_m2014_q4i | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 9 | ✓ | ✓ |
| Prob003_step_one | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 9 | ✓ | ✓ |
| Prob004_vector2 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 10 | ✓ | ✓ |
| Prob006_vectorr | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 10 | ✓ | ✓ |
| Prob007_wire | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 10 | ✓ | ✓ |
| Prob008_m2014_q4h | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 10 | ✓ | ✓ |
| Prob015_vector1 | a combinational circuit that splits an input half-word (16 bits, [15:0] ) int... | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 11 | ✓ | ✓ |
| Prob023_vector100r | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 12 | ✓ | ✓ |
| Prob028_m2014_q4a | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 14 | ✓ | ✓ |
| Prob032_vector0 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 14 | ✓ | ✓ |
| Prob034_dff8 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 15 | ✓ | ✓ |
| Prob042_vector4 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 10 | ✓ | ✓ |
| Prob059_wire4 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 15 | ✓ | ✓ |
| Prob064_vector3 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 18 | ✓ | ✓ |
| Prob071_always_casez | a priority encoder for an 8-bit input | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 22 | ✓ | ✓ |
| Prob156_review2015_fancytimer | a timer with one input that: (1) is started when a particular input pattern (... | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 78 | ✓ | ✓ |
| Prob151_review2015_fsm | a timer that: (1) is started when a particular pattern (1101) is detected, (2... | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 56 | ✓ | ✓ |
| Prob078_dualedge | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 25 | ✓ | ✓ |
| Prob145_circuit8 | a sequential circuit | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 17 | ✓ | ✓ |
| Prob046_dff8p | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 16 | ✓ | ✓ |
| Prob031_dff | a single D flip-flop | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | MIT | 15 | ✓ | ✓ |

<details><summary>Flow and VTR QoR</summary>

| design | iverilog | Odin sim | VTR stage | LUTs | blocks | FFs | pins | mult/mem | cpd ns | chan w |
|---|---|---|---|---|---|---|---|---|---|---|
| Prob144_conwaylife | - | - | - | - | - | - | - | - | - | - |
| Prob030_popcount255 | - | - | - | - | - | - | - | - | - | - |
| Prob153_gshare | - | - | - | - | - | - | - | - | - | - |
| Prob108_rule90 | - | - | - | - | - | - | - | - | - | - |
| Prob124_rule110 | - | - | - | - | - | - | - | - | - | - |
| Prob021_mux256to1v | - | - | - | - | - | - | - | - | - | - |
| Prob092_gatesv100 | - | - | - | - | - | - | - | - | - | - |
| Prob105_rotate100 | - | - | - | - | - | - | - | - | - | - |
| Prob115_shift18 | - | - | - | - | - | - | - | - | - | - |
| Prob018_mux256to1 | - | - | - | - | - | - | - | - | - | - |
| Prob017_mux2to1v | - | - | - | - | - | - | - | - | - | - |
| Prob097_mux9to1v | - | - | - | - | - | - | - | - | - | - |
| Prob052_gates100 | - | - | - | - | - | - | - | - | - | - |
| Prob055_conditional | - | - | - | - | - | - | - | - | - | - |
| Prob141_count_clock | - | - | - | - | - | - | - | - | - | - |
| Prob066_edgecapture | - | - | - | - | - | - | - | - | - | - |
| Prob082_lfsr32 | - | - | - | - | - | - | - | - | - | - |
| Prob118_history_shift | - | - | - | - | - | - | - | - | - | - |
| Prob154_fsm_ps2data | - | - | - | - | - | - | - | - | - | - |
| Prob068_countbcd | - | - | - | - | - | - | - | - | - | - |
| Prob123_bugs_addsubz | - | - | - | - | - | - | - | - | - | - |
| Prob043_vector5 | - | - | - | - | - | - | - | - | - | - |
| Prob146_fsm_serialdata | - | - | - | - | - | - | - | - | - | - |
| Prob080_timer | - | - | - | - | - | - | - | - | - | - |
| Prob155_lemmings4 | - | - | - | - | - | - | - | - | - | - |
| Prob073_dff16e | - | - | - | - | - | - | - | - | - | - |
| Prob126_circuit6 | - | - | - | - | - | - | - | - | - | - |
| Prob037_review2015_count1k | - | - | - | - | - | - | - | - | - | - |
| Prob033_ece241_2014_q1c | - | - | - | - | - | - | - | - | - | - |
| Prob114_bugs_case | - | - | - | - | - | - | - | - | - | - |
| Prob143_fsm_onehot | - | - | - | - | - | - | - | - | - | - |
| Prob076_always_case | - | - | - | - | - | - | - | - | - | - |
| Prob137_fsm_serial | - | - | - | - | - | - | - | - | - | - |
| Prob084_ece241_2013_q12 | - | - | - | - | - | - | - | - | - | - |
| Prob140_fsm_hdlc | - | - | - | - | - | - | - | - | - | - |
| Prob149_ece241_2013_q4 | - | - | - | - | - | - | - | - | - | - |
| Prob044_vectorgates | - | - | - | - | - | - | - | - | - | - |
| Prob094_gatesv | - | - | - | - | - | - | - | - | - | - |
| Prob106_always_nolatches | - | - | - | - | - | - | - | - | - | - |
| Prob130_circuit5 | - | - | - | - | - | - | - | - | - | - |
| Prob133_2014_q3fsm | - | - | - | - | - | - | - | - | - | - |
| Prob139_2013_q2bfsm | - | - | - | - | - | - | - | - | - | - |
| Prob041_dff8r | - | - | - | - | - | - | - | - | - | - |
| Prob045_edgedetect2 | - | - | - | - | - | - | - | - | - | - |
| Prob047_dff8ar | - | - | - | - | - | - | - | - | - | - |
| Prob054_edgedetect | - | - | - | - | - | - | - | - | - | - |
| Prob062_bugs_mux2 | - | - | - | - | - | - | - | - | - | - |
| Prob087_gates | - | - | - | - | - | - | - | - | - | - |
| Prob136_m2014_q6 | - | - | - | - | - | - | - | - | - | - |
| Prob138_2012_q2fsm | - | - | - | - | - | - | - | - | - | - |
| Prob016_m2014_q4j | - | - | - | - | - | - | - | - | - | - |
| Prob121_2014_q3bfsm | - | - | - | - | - | - | - | - | - | - |
| Prob152_lemmings3 | - | - | - | - | - | - | - | - | - | - |
| Prob086_lfsr5 | - | - | - | - | - | - | - | - | - | - |
| Prob096_review2015_fsmseq | - | - | - | - | - | - | - | - | - | - |
| Prob148_2013_q2afsm | - | - | - | - | - | - | - | - | - | - |
| Prob150_review2015_fsmonehot | - | - | - | - | - | - | - | - | - | - |
| Prob035_count1to10 | - | - | - | - | - | - | - | - | - | - |
| Prob038_count15 | - | - | - | - | - | - | - | - | - | - |
| Prob040_count10 | - | - | - | - | - | - | - | - | - | - |
| Prob060_m2014_q4k | - | - | - | - | - | - | - | - | - | - |
| Prob063_review2015_shiftcount | - | - | - | - | - | - | - | - | - | - |
| Prob067_countslow | - | - | - | - | - | - | - | - | - | - |
| Prob079_fsm3onehot | - | - | - | - | - | - | - | - | - | - |
| Prob085_shift4 | - | - | - | - | - | - | - | - | - | - |
| Prob095_review2015_fsmshift | - | - | - | - | - | - | - | - | - | - |
| Prob120_fsm3s | - | - | - | - | - | - | - | - | - | - |
| Prob128_fsm_ps2 | - | - | - | - | - | - | - | - | - | - |
| Prob142_lemmings2 | - | - | - | - | - | - | - | - | - | - |
| Prob051_gates4 | - | - | - | - | - | - | - | - | - | - |
| Prob072_thermostat | - | - | - | - | - | - | - | - | - | - |
| Prob074_ece241_2014_q4 | - | - | - | - | - | - | - | - | - | - |
| Prob089_ece241_2014_q5a | - | - | - | - | - | - | - | - | - | - |
| Prob093_ece241_2014_q3 | - | - | - | - | - | - | - | - | - | - |
| Prob100_fsm3comb | - | - | - | - | - | - | - | - | - | - |
| Prob117_circuit9 | - | - | - | - | - | - | - | - | - | - |
| Prob119_fsm3 | - | - | - | - | - | - | - | - | - | - |
| Prob129_ece241_2013_q8 | - | - | - | - | - | - | - | - | - | - |
| Prob009_popcount3 | - | - | - | - | - | - | - | - | - | - |
| Prob024_hadd | - | - | - | - | - | - | - | - | - | - |
| Prob025_reduction | - | - | - | - | - | - | - | - | - | - |
| Prob027_fadd | - | - | - | - | - | - | - | - | - | - |
| Prob036_ringer | - | - | - | - | - | - | - | - | - | - |
| Prob058_alwaysblock2 | - | - | - | - | - | - | - | - | - | - |
| Prob065_7420 | - | - | - | - | - | - | - | - | - | - |
| Prob070_ece241_2013_q2 | - | - | - | - | - | - | - | - | - | - |
| Prob075_counter_2bc | - | - | - | - | - | - | - | - | - | - |
| Prob077_wire_decl | - | - | - | - | - | - | - | - | - | - |
| Prob081_7458 | - | - | - | - | - | - | - | - | - | - |
| Prob088_ece241_2014_q5b | - | - | - | - | - | - | - | - | - | - |
| Prob091_2012_q2b | - | - | - | - | - | - | - | - | - | - |
| Prob099_m2014_q6c | - | - | - | - | - | - | - | - | - | - |
| Prob112_always_case2 | - | - | - | - | - | - | - | - | - | - |
| Prob127_lemmings1 | - | - | - | - | - | - | - | - | - | - |
| Prob134_2014_q3c | - | - | - | - | - | - | - | - | - | - |
| Prob147_circuit10 | - | - | - | - | - | - | - | - | - | - |
| Prob005_notgate | - | - | - | - | - | - | - | - | - | - |
| Prob010_mt2015_q4a | - | - | - | - | - | - | - | - | - | - |
| Prob011_norgate | - | - | - | - | - | - | - | - | - | - |
| Prob012_xnorgate | - | - | - | - | - | - | - | - | - | - |
| Prob013_m2014_q4e | - | - | - | - | - | - | - | - | - | - |
| Prob014_andgate | - | - | - | - | - | - | - | - | - | - |
| Prob019_m2014_q4f | - | - | - | - | - | - | - | - | - | - |
| Prob020_mt2015_eq2 | - | - | - | - | - | - | - | - | - | - |
| Prob022_mux2to1 | - | - | - | - | - | - | - | - | - | - |
| Prob026_alwaysblock1 | - | - | - | - | - | - | - | - | - | - |
| Prob029_m2014_q4g | - | - | - | - | - | - | - | - | - | - |
| Prob039_always_if | - | - | - | - | - | - | - | - | - | - |
| Prob048_m2014_q4c | - | - | - | - | - | - | - | - | - | - |
| Prob049_m2014_q4b | - | - | - | - | - | - | - | - | - | - |
| Prob050_kmap1 | - | - | - | - | - | - | - | - | - | - |
| Prob053_m2014_q4d | - | - | - | - | - | - | - | - | - | - |
| Prob056_ece241_2013_q7 | - | - | - | - | - | - | - | - | - | - |
| Prob057_kmap2 | - | - | - | - | - | - | - | - | - | - |
| Prob061_2014_q4a | - | - | - | - | - | - | - | - | - | - |
| Prob069_truthtable1 | - | - | - | - | - | - | - | - | - | - |
| Prob083_mt2015_q4b | - | - | - | - | - | - | - | - | - | - |
| Prob090_circuit1 | - | - | - | - | - | - | - | - | - | - |
| Prob098_circuit7 | - | - | - | - | - | - | - | - | - | - |
| Prob101_circuit4 | - | - | - | - | - | - | - | - | - | - |
| Prob102_circuit3 | - | - | - | - | - | - | - | - | - | - |
| Prob103_circuit2 | - | - | - | - | - | - | - | - | - | - |
| Prob104_mt2015_muxdff | - | - | - | - | - | - | - | - | - | - |
| Prob107_fsm1s | - | - | - | - | - | - | - | - | - | - |
| Prob109_fsm1 | - | - | - | - | - | - | - | - | - | - |
| Prob110_fsm2 | - | - | - | - | - | - | - | - | - | - |
| Prob111_fsm2s | - | - | - | - | - | - | - | - | - | - |
| Prob113_2012_q1g | - | - | - | - | - | - | - | - | - | - |
| Prob116_m2014_q3 | - | - | - | - | - | - | - | - | - | - |
| Prob122_kmap4 | - | - | - | - | - | - | - | - | - | - |
| Prob125_kmap3 | - | - | - | - | - | - | - | - | - | - |
| Prob131_mt2015_q4 | - | - | - | - | - | - | - | - | - | - |
| Prob132_always_if2 | - | - | - | - | - | - | - | - | - | - |
| Prob135_m2014_q6b | - | - | - | - | - | - | - | - | - | - |
| Prob001_zero | - | - | - | - | - | - | - | - | - | - |
| Prob002_m2014_q4i | - | - | - | - | - | - | - | - | - | - |
| Prob003_step_one | - | - | - | - | - | - | - | - | - | - |
| Prob004_vector2 | - | - | - | - | - | - | - | - | - | - |
| Prob006_vectorr | - | - | - | - | - | - | - | - | - | - |
| Prob007_wire | - | - | - | - | - | - | - | - | - | - |
| Prob008_m2014_q4h | - | - | - | - | - | - | - | - | - | - |
| Prob015_vector1 | - | - | - | - | - | - | - | - | - | - |
| Prob023_vector100r | - | - | - | - | - | - | - | - | - | - |
| Prob028_m2014_q4a | - | - | - | - | - | - | - | - | - | - |
| Prob032_vector0 | - | - | - | - | - | - | - | - | - | - |
| Prob034_dff8 | - | - | - | - | - | - | - | - | - | - |
| Prob042_vector4 | - | - | - | - | - | - | - | - | - | - |
| Prob059_wire4 | - | - | - | - | - | - | - | - | - | - |
| Prob064_vector3 | - | - | - | - | - | - | - | - | - | - |
| Prob071_always_casez | - | - | - | - | - | - | - | - | - | - |
| Prob156_review2015_fancytimer | - | - | - | - | - | - | - | - | - | - |
| Prob151_review2015_fsm | - | - | - | - | - | - | - | - | - | - |
| Prob078_dualedge | - | - | - | - | - | - | - | - | - | - |
| Prob145_circuit8 | - | - | - | - | - | - | - | - | - | - |
| Prob046_dff8p | - | - | - | - | - | - | - | - | - | - |
| Prob031_dff | - | - | - | - | - | - | - | - | - | - |

</details>

<details><summary>LUT forms</summary>

| design | gates/d | 4-LUT/d | 6-LUT/d |
|---|---|---|---|
| Prob144_conwaylife | - | - | 1966/- |
| Prob030_popcount255 | - | - | 1369/- |
| Prob153_gshare | - | - | 647/- |
| Prob108_rule90 | - | - | 512/- |
| Prob124_rule110 | - | - | 512/- |
| Prob021_mux256to1v | - | - | 390/- |
| Prob092_gatesv100 | - | - | 298/- |
| Prob105_rotate100 | - | - | 201/- |
| Prob115_shift18 | - | - | 130/- |
| Prob018_mux256to1 | - | - | 105/- |
| Prob017_mux2to1v | - | - | 100/- |
| Prob097_mux9to1v | - | - | 95/- |
| Prob052_gates100 | - | - | 88/- |
| Prob055_conditional | - | - | 56/- |
| Prob141_count_clock | - | - | 41/- |
| Prob066_edgecapture | - | - | 32/- |
| Prob082_lfsr32 | - | - | 32/- |
| Prob118_history_shift | - | - | 32/- |
| Prob154_fsm_ps2data | - | - | 28/- |
| Prob068_countbcd | - | - | 22/- |
| Prob123_bugs_addsubz | - | - | 22/- |
| Prob043_vector5 | - | - | 20/- |
| Prob146_fsm_serialdata | - | - | 20/- |
| Prob080_timer | - | - | 17/- |
| Prob155_lemmings4 | - | - | 17/- |
| Prob073_dff16e | - | - | 16/- |
| Prob126_circuit6 | - | - | 16/- |
| Prob037_review2015_count1k | - | - | 14/- |
| Prob033_ece241_2014_q1c | - | - | 13/- |
| Prob114_bugs_case | - | - | 13/- |
| Prob143_fsm_onehot | - | - | 13/- |
| Prob076_always_case | - | - | 12/- |
| Prob137_fsm_serial | - | - | 12/- |
| Prob084_ece241_2013_q12 | - | - | 11/- |
| Prob140_fsm_hdlc | - | - | 11/- |
| Prob149_ece241_2013_q4 | - | - | 11/- |
| Prob044_vectorgates | - | - | 10/- |
| Prob094_gatesv | - | - | 10/- |
| Prob106_always_nolatches | - | - | 10/- |
| Prob130_circuit5 | - | - | 9/- |
| Prob133_2014_q3fsm | - | - | 9/- |
| Prob139_2013_q2bfsm | - | - | 9/- |
| Prob041_dff8r | - | - | 8/- |
| Prob045_edgedetect2 | - | - | 8/- |
| Prob047_dff8ar | - | - | 8/- |
| Prob054_edgedetect | - | - | 8/- |
| Prob062_bugs_mux2 | - | - | 8/- |
| Prob087_gates | - | - | 7/- |
| Prob136_m2014_q6 | - | - | 7/- |
| Prob138_2012_q2fsm | - | - | 7/- |
| Prob016_m2014_q4j | - | - | 6/- |
| Prob121_2014_q3bfsm | - | - | 6/- |
| Prob152_lemmings3 | - | - | 6/- |
| Prob086_lfsr5 | - | - | 5/- |
| Prob096_review2015_fsmseq | - | - | 5/- |
| Prob148_2013_q2afsm | - | - | 5/- |
| Prob150_review2015_fsmonehot | - | - | 5/- |
| Prob035_count1to10 | - | - | 4/- |
| Prob038_count15 | - | - | 4/- |
| Prob040_count10 | - | - | 4/- |
| Prob060_m2014_q4k | - | - | 4/- |
| Prob063_review2015_shiftcount | - | - | 4/- |
| Prob067_countslow | - | - | 4/- |
| Prob079_fsm3onehot | - | - | 4/- |
| Prob085_shift4 | - | - | 4/- |
| Prob095_review2015_fsmshift | - | - | 4/- |
| Prob120_fsm3s | - | - | 4/- |
| Prob128_fsm_ps2 | - | - | 4/- |
| Prob142_lemmings2 | - | - | 4/- |
| Prob051_gates4 | - | - | 3/- |
| Prob072_thermostat | - | - | 3/- |
| Prob074_ece241_2014_q4 | - | - | 3/- |
| Prob089_ece241_2014_q5a | - | - | 3/- |
| Prob093_ece241_2014_q3 | - | - | 3/- |
| Prob100_fsm3comb | - | - | 3/- |
| Prob117_circuit9 | - | - | 3/- |
| Prob119_fsm3 | - | - | 3/- |
| Prob129_ece241_2013_q8 | - | - | 3/- |
| Prob009_popcount3 | - | - | 2/- |
| Prob024_hadd | - | - | 2/- |
| Prob025_reduction | - | - | 2/- |
| Prob027_fadd | - | - | 2/- |
| Prob036_ringer | - | - | 2/- |
| Prob058_alwaysblock2 | - | - | 2/- |
| Prob065_7420 | - | - | 2/- |
| Prob070_ece241_2013_q2 | - | - | 2/- |
| Prob075_counter_2bc | - | - | 2/- |
| Prob077_wire_decl | - | - | 2/- |
| Prob081_7458 | - | - | 2/- |
| Prob088_ece241_2014_q5b | - | - | 2/- |
| Prob091_2012_q2b | - | - | 2/- |
| Prob099_m2014_q6c | - | - | 2/- |
| Prob112_always_case2 | - | - | 2/- |
| Prob127_lemmings1 | - | - | 2/- |
| Prob134_2014_q3c | - | - | 2/- |
| Prob147_circuit10 | - | - | 2/- |
| Prob005_notgate | - | - | 1/- |
| Prob010_mt2015_q4a | - | - | 1/- |
| Prob011_norgate | - | - | 1/- |
| Prob012_xnorgate | - | - | 1/- |
| Prob013_m2014_q4e | - | - | 1/- |
| Prob014_andgate | - | - | 1/- |
| Prob019_m2014_q4f | - | - | 1/- |
| Prob020_mt2015_eq2 | - | - | 1/- |
| Prob022_mux2to1 | - | - | 1/- |
| Prob026_alwaysblock1 | - | - | 1/- |
| Prob029_m2014_q4g | - | - | 1/- |
| Prob039_always_if | - | - | 1/- |
| Prob048_m2014_q4c | - | - | 1/- |
| Prob049_m2014_q4b | - | - | 1/- |
| Prob050_kmap1 | - | - | 1/- |
| Prob053_m2014_q4d | - | - | 1/- |
| Prob056_ece241_2013_q7 | - | - | 1/- |
| Prob057_kmap2 | - | - | 1/- |
| Prob061_2014_q4a | - | - | 1/- |
| Prob069_truthtable1 | - | - | 1/- |
| Prob083_mt2015_q4b | - | - | 1/- |
| Prob090_circuit1 | - | - | 1/- |
| Prob098_circuit7 | - | - | 1/- |
| Prob101_circuit4 | - | - | 1/- |
| Prob102_circuit3 | - | - | 1/- |
| Prob103_circuit2 | - | - | 1/- |
| Prob104_mt2015_muxdff | - | - | 1/- |
| Prob107_fsm1s | - | - | 1/- |
| Prob109_fsm1 | - | - | 1/- |
| Prob110_fsm2 | - | - | 1/- |
| Prob111_fsm2s | - | - | 1/- |
| Prob113_2012_q1g | - | - | 1/- |
| Prob116_m2014_q3 | - | - | 1/- |
| Prob122_kmap4 | - | - | 1/- |
| Prob125_kmap3 | - | - | 1/- |
| Prob131_mt2015_q4 | - | - | 1/- |
| Prob132_always_if2 | - | - | 1/- |
| Prob135_m2014_q6b | - | - | 1/- |
| Prob001_zero | - | - | 0/- |
| Prob002_m2014_q4i | - | - | 0/- |
| Prob003_step_one | - | - | 0/- |
| Prob004_vector2 | - | - | 0/- |
| Prob006_vectorr | - | - | 0/- |
| Prob007_wire | - | - | 0/- |
| Prob008_m2014_q4h | - | - | 0/- |
| Prob015_vector1 | - | - | 0/- |
| Prob023_vector100r | - | - | 0/- |
| Prob028_m2014_q4a | - | - | 0/- |
| Prob032_vector0 | - | - | 0/- |
| Prob034_dff8 | - | - | 0/- |
| Prob042_vector4 | - | - | 0/- |
| Prob059_wire4 | - | - | 0/- |
| Prob064_vector3 | - | - | 0/- |
| Prob071_always_casez | - | - | 0/- |
| Prob156_review2015_fancytimer | - | - | - |
| Prob151_review2015_fsm | - | - | - |
| Prob078_dualedge | - | - | - |
| Prob145_circuit8 | - | - | - |
| Prob046_dff8p | - | - | - |
| Prob031_dff | - | - | - |

</details>

<details><summary>Properties</summary>

| design | seq | mem | mul | add | fsm | latch | hier | bbox |
|---|---|---|---|---|---|---|---|---|
| Prob144_conwaylife | - | - | - | - | - | - | - | - |
| Prob030_popcount255 | - | - | - | - | - | - | - | - |
| Prob153_gshare | - | - | - | - | - | - | - | - |
| Prob108_rule90 | - | - | - | - | - | - | - | - |
| Prob124_rule110 | - | - | - | - | - | - | - | - |
| Prob021_mux256to1v | - | - | - | - | - | - | - | - |
| Prob092_gatesv100 | - | - | - | - | - | - | - | - |
| Prob105_rotate100 | - | - | - | - | - | - | - | - |
| Prob115_shift18 | - | - | - | - | - | - | - | - |
| Prob018_mux256to1 | - | - | - | - | - | - | - | - |
| Prob017_mux2to1v | - | - | - | - | - | - | - | - |
| Prob097_mux9to1v | - | - | - | - | - | - | - | - |
| Prob052_gates100 | - | - | - | - | - | - | - | - |
| Prob055_conditional | - | - | - | - | - | - | - | - |
| Prob141_count_clock | - | - | - | - | - | - | - | - |
| Prob066_edgecapture | - | - | - | - | - | - | - | - |
| Prob082_lfsr32 | - | - | - | - | - | - | - | - |
| Prob118_history_shift | - | - | - | - | - | - | - | - |
| Prob154_fsm_ps2data | - | - | - | - | - | - | - | - |
| Prob068_countbcd | - | - | - | - | - | - | - | - |
| Prob123_bugs_addsubz | - | - | - | - | - | - | - | - |
| Prob043_vector5 | - | - | - | - | - | - | - | - |
| Prob146_fsm_serialdata | - | - | - | - | - | - | - | - |
| Prob080_timer | - | - | - | - | - | - | - | - |
| Prob155_lemmings4 | - | - | - | - | - | - | - | - |
| Prob073_dff16e | - | - | - | - | - | - | - | - |
| Prob126_circuit6 | - | - | - | - | - | - | - | - |
| Prob037_review2015_count1k | - | - | - | - | - | - | - | - |
| Prob033_ece241_2014_q1c | - | - | - | - | - | - | - | - |
| Prob114_bugs_case | - | - | - | - | - | - | - | - |
| Prob143_fsm_onehot | - | - | - | - | - | - | - | - |
| Prob076_always_case | - | - | - | - | - | - | - | - |
| Prob137_fsm_serial | - | - | - | - | - | - | - | - |
| Prob084_ece241_2013_q12 | - | - | - | - | - | - | - | - |
| Prob140_fsm_hdlc | - | - | - | - | - | - | - | - |
| Prob149_ece241_2013_q4 | - | - | - | - | - | - | - | - |
| Prob044_vectorgates | - | - | - | - | - | - | - | - |
| Prob094_gatesv | - | - | - | - | - | - | - | - |
| Prob106_always_nolatches | - | - | - | - | - | - | - | - |
| Prob130_circuit5 | - | - | - | - | - | - | - | - |
| Prob133_2014_q3fsm | - | - | - | - | - | - | - | - |
| Prob139_2013_q2bfsm | - | - | - | - | - | - | - | - |
| Prob041_dff8r | - | - | - | - | - | - | - | - |
| Prob045_edgedetect2 | - | - | - | - | - | - | - | - |
| Prob047_dff8ar | - | - | - | - | - | - | - | - |
| Prob054_edgedetect | - | - | - | - | - | - | - | - |
| Prob062_bugs_mux2 | - | - | - | - | - | - | - | - |
| Prob087_gates | - | - | - | - | - | - | - | - |
| Prob136_m2014_q6 | - | - | - | - | - | - | - | - |
| Prob138_2012_q2fsm | - | - | - | - | - | - | - | - |
| Prob016_m2014_q4j | - | - | - | - | - | - | - | - |
| Prob121_2014_q3bfsm | - | - | - | - | - | - | - | - |
| Prob152_lemmings3 | - | - | - | - | - | - | - | - |
| Prob086_lfsr5 | - | - | - | - | - | - | - | - |
| Prob096_review2015_fsmseq | - | - | - | - | - | - | - | - |
| Prob148_2013_q2afsm | - | - | - | - | - | - | - | - |
| Prob150_review2015_fsmonehot | - | - | - | - | - | - | - | - |
| Prob035_count1to10 | - | - | - | - | - | - | - | - |
| Prob038_count15 | - | - | - | - | - | - | - | - |
| Prob040_count10 | - | - | - | - | - | - | - | - |
| Prob060_m2014_q4k | - | - | - | - | - | - | - | - |
| Prob063_review2015_shiftcount | - | - | - | - | - | - | - | - |
| Prob067_countslow | - | - | - | - | - | - | - | - |
| Prob079_fsm3onehot | - | - | - | - | - | - | - | - |
| Prob085_shift4 | - | - | - | - | - | - | - | - |
| Prob095_review2015_fsmshift | - | - | - | - | - | - | - | - |
| Prob120_fsm3s | - | - | - | - | - | - | - | - |
| Prob128_fsm_ps2 | - | - | - | - | - | - | - | - |
| Prob142_lemmings2 | - | - | - | - | - | - | - | - |
| Prob051_gates4 | - | - | - | - | - | - | - | - |
| Prob072_thermostat | - | - | - | - | - | - | - | - |
| Prob074_ece241_2014_q4 | - | - | - | - | - | - | - | - |
| Prob089_ece241_2014_q5a | - | - | - | - | - | - | - | - |
| Prob093_ece241_2014_q3 | - | - | - | - | - | - | - | - |
| Prob100_fsm3comb | - | - | - | - | - | - | - | - |
| Prob117_circuit9 | - | - | - | - | - | - | - | - |
| Prob119_fsm3 | - | - | - | - | - | - | - | - |
| Prob129_ece241_2013_q8 | - | - | - | - | - | - | - | - |
| Prob009_popcount3 | - | - | - | - | - | - | - | - |
| Prob024_hadd | - | - | - | - | - | - | - | - |
| Prob025_reduction | - | - | - | - | - | - | - | - |
| Prob027_fadd | - | - | - | - | - | - | - | - |
| Prob036_ringer | - | - | - | - | - | - | - | - |
| Prob058_alwaysblock2 | - | - | - | - | - | - | - | - |
| Prob065_7420 | - | - | - | - | - | - | - | - |
| Prob070_ece241_2013_q2 | - | - | - | - | - | - | - | - |
| Prob075_counter_2bc | - | - | - | - | - | - | - | - |
| Prob077_wire_decl | - | - | - | - | - | - | - | - |
| Prob081_7458 | - | - | - | - | - | - | - | - |
| Prob088_ece241_2014_q5b | - | - | - | - | - | - | - | - |
| Prob091_2012_q2b | - | - | - | - | - | - | - | - |
| Prob099_m2014_q6c | - | - | - | - | - | - | - | - |
| Prob112_always_case2 | - | - | - | - | - | - | - | - |
| Prob127_lemmings1 | - | - | - | - | - | - | - | - |
| Prob134_2014_q3c | - | - | - | - | - | - | - | - |
| Prob147_circuit10 | - | - | - | - | - | - | - | - |
| Prob005_notgate | - | - | - | - | - | - | - | - |
| Prob010_mt2015_q4a | - | - | - | - | - | - | - | - |
| Prob011_norgate | - | - | - | - | - | - | - | - |
| Prob012_xnorgate | - | - | - | - | - | - | - | - |
| Prob013_m2014_q4e | - | - | - | - | - | - | - | - |
| Prob014_andgate | - | - | - | - | - | - | - | - |
| Prob019_m2014_q4f | - | - | - | - | - | - | - | - |
| Prob020_mt2015_eq2 | - | - | - | - | - | - | - | - |
| Prob022_mux2to1 | - | - | - | - | - | - | - | - |
| Prob026_alwaysblock1 | - | - | - | - | - | - | - | - |
| Prob029_m2014_q4g | - | - | - | - | - | - | - | - |
| Prob039_always_if | - | - | - | - | - | - | - | - |
| Prob048_m2014_q4c | - | - | - | - | - | - | - | - |
| Prob049_m2014_q4b | - | - | - | - | - | - | - | - |
| Prob050_kmap1 | - | - | - | - | - | - | - | - |
| Prob053_m2014_q4d | - | - | - | - | - | - | - | - |
| Prob056_ece241_2013_q7 | - | - | - | - | - | - | - | - |
| Prob057_kmap2 | - | - | - | - | - | - | - | - |
| Prob061_2014_q4a | - | - | - | - | - | - | - | - |
| Prob069_truthtable1 | - | - | - | - | - | - | - | - |
| Prob083_mt2015_q4b | - | - | - | - | - | - | - | - |
| Prob090_circuit1 | - | - | - | - | - | - | - | - |
| Prob098_circuit7 | - | - | - | - | - | - | - | - |
| Prob101_circuit4 | - | - | - | - | - | - | - | - |
| Prob102_circuit3 | - | - | - | - | - | - | - | - |
| Prob103_circuit2 | - | - | - | - | - | - | - | - |
| Prob104_mt2015_muxdff | - | - | - | - | - | - | - | - |
| Prob107_fsm1s | - | - | - | - | - | - | - | - |
| Prob109_fsm1 | - | - | - | - | - | - | - | - |
| Prob110_fsm2 | - | - | - | - | - | - | - | - |
| Prob111_fsm2s | - | - | - | - | - | - | - | - |
| Prob113_2012_q1g | - | - | - | - | - | - | - | - |
| Prob116_m2014_q3 | - | - | - | - | - | - | - | - |
| Prob122_kmap4 | - | - | - | - | - | - | - | - |
| Prob125_kmap3 | - | - | - | - | - | - | - | - |
| Prob131_mt2015_q4 | - | - | - | - | - | - | - | - |
| Prob132_always_if2 | - | - | - | - | - | - | - | - |
| Prob135_m2014_q6b | - | - | - | - | - | - | - | - |
| Prob001_zero | - | - | - | - | - | - | - | - |
| Prob002_m2014_q4i | - | - | - | - | - | - | - | - |
| Prob003_step_one | - | - | - | - | - | - | - | - |
| Prob004_vector2 | - | - | - | - | - | - | - | - |
| Prob006_vectorr | - | - | - | - | - | - | - | - |
| Prob007_wire | - | - | - | - | - | - | - | - |
| Prob008_m2014_q4h | - | - | - | - | - | - | - | - |
| Prob015_vector1 | - | - | - | - | - | - | - | - |
| Prob023_vector100r | - | - | - | - | - | - | - | - |
| Prob028_m2014_q4a | - | - | - | - | - | - | - | - |
| Prob032_vector0 | - | - | - | - | - | - | - | - |
| Prob034_dff8 | - | - | - | - | - | - | - | - |
| Prob042_vector4 | - | - | - | - | - | - | - | - |
| Prob059_wire4 | - | - | - | - | - | - | - | - |
| Prob064_vector3 | - | - | - | - | - | - | - | - |
| Prob071_always_casez | - | - | - | - | - | - | - | - |
| Prob156_review2015_fancytimer | - | - | - | - | - | - | - | - |
| Prob151_review2015_fsm | - | - | - | - | - | - | - | - |
| Prob078_dualedge | - | - | - | - | - | - | - | - |
| Prob145_circuit8 | - | - | - | - | - | - | - | - |
| Prob046_dff8p | - | - | - | - | - | - | - | - |
| Prob031_dff | - | - | - | - | - | - | - | - |

</details>

<details><summary>Silicon</summary>

| design | cells | core um2 | LVS | Si stage |
|---|---|---|---|---|
| Prob144_conwaylife | - | - | - | - |
| Prob030_popcount255 | - | - | - | - |
| Prob153_gshare | - | - | - | - |
| Prob108_rule90 | - | - | - | - |
| Prob124_rule110 | - | - | - | - |
| Prob021_mux256to1v | - | - | - | - |
| Prob092_gatesv100 | - | 6531.3 | out of scope: stopped at pl... | equiv |
| Prob105_rotate100 | 873 | 18955.7 | match | lvs |
| Prob115_shift18 | 703 | 13934.6 | match | lvs |
| Prob018_mux256to1 | 506 | 7847.5 | match | lvs |
| Prob017_mux2to1v | - | 4144.0 | out of scope: stopped at pl... | equiv |
| Prob097_mux9to1v | 187 | 3178.0 | match | lvs |
| Prob052_gates100 | 318 | 5172.5 | match | lvs |
| Prob055_conditional | 159 | 2499.9 | match | lvs |
| Prob141_count_clock | - | - | - | - |
| Prob066_edgecapture | - | - | - | - |
| Prob082_lfsr32 | - | - | - | - |
| Prob118_history_shift | - | - | - | - |
| Prob154_fsm_ps2data | - | 2876.5 | out of scope: stopped at pl... | equiv |
| Prob068_countbcd | - | - | - | - |
| Prob123_bugs_addsubz | - | - | - | - |
| Prob043_vector5 | 25 | 420.4 | mismatch | extract |
| Prob146_fsm_serialdata | - | - | - | - |
| Prob080_timer | - | - | - | - |
| Prob155_lemmings4 | - | - | - | - |
| Prob073_dff16e | - | - | - | - |
| Prob126_circuit6 | - | - | - | - |
| Prob037_review2015_count1k | - | - | - | - |
| Prob033_ece241_2014_q1c | - | - | - | - |
| Prob114_bugs_case | - | - | - | - |
| Prob143_fsm_onehot | 23 | 300.3 | match | lvs |
| Prob076_always_case | - | - | - | - |
| Prob137_fsm_serial | - | - | - | - |
| Prob084_ece241_2013_q12 | - | - | - | - |
| Prob140_fsm_hdlc | - | - | - | - |
| Prob149_ece241_2013_q4 | - | - | - | - |
| Prob044_vectorgates | 12 | 145.1 | mismatch | extract |
| Prob094_gatesv | - | - | - | - |
| Prob106_always_nolatches | - | - | - | - |
| Prob130_circuit5 | - | - | - | - |
| Prob133_2014_q3fsm | - | - | - | - |
| Prob139_2013_q2bfsm | - | - | - | - |
| Prob041_dff8r | - | - | - | - |
| Prob045_edgedetect2 | - | 1594.0 | out of scope: stopped at pl... | equiv |
| Prob047_dff8ar | - | - | - | - |
| Prob054_edgedetect | - | 1559.0 | out of scope: stopped at pl... | equiv |
| Prob062_bugs_mux2 | - | - | - | - |
| Prob087_gates | 10 | 93.8 | mismatch | extract |
| Prob136_m2014_q6 | - | - | - | - |
| Prob138_2012_q2fsm | - | - | - | - |
| Prob016_m2014_q4j | - | - | - | - |
| Prob121_2014_q3bfsm | 21 | 402.9 | match | lvs |
| Prob152_lemmings3 | - | - | - | - |
| Prob086_lfsr5 | - | - | - | - |
| Prob096_review2015_fsmseq | - | - | - | - |
| Prob148_2013_q2afsm | - | - | - | - |
| Prob150_review2015_fsmonehot | 10 | 150.1 | mismatch | extract |
| Prob035_count1to10 | - | - | - | - |
| Prob038_count15 | - | - | - | - |
| Prob040_count10 | - | - | - | - |
| Prob060_m2014_q4k | - | - | - | - |
| Prob063_review2015_shiftcount | - | - | - | - |
| Prob067_countslow | - | - | - | - |
| Prob079_fsm3onehot | 9 | 97.6 | mismatch | extract |
| Prob085_shift4 | - | - | - | - |
| Prob095_review2015_fsmshift | - | - | - | - |
| Prob120_fsm3s | - | - | - | - |
| Prob128_fsm_ps2 | - | - | - | - |
| Prob142_lemmings2 | - | - | - | - |
| Prob051_gates4 | - | - | - | - |
| Prob072_thermostat | - | - | - | - |
| Prob074_ece241_2014_q4 | - | - | - | - |
| Prob089_ece241_2014_q5a | - | - | - | - |
| Prob093_ece241_2014_q3 | - | 42.5 | out of scope: stopped at pl... | equiv |
| Prob100_fsm3comb | 4 | 45.0 | mismatch | extract |
| Prob117_circuit9 | - | - | - | - |
| Prob119_fsm3 | - | - | - | - |
| Prob129_ece241_2013_q8 | - | - | - | - |
| Prob009_popcount3 | - | - | - | - |
| Prob024_hadd | - | - | - | - |
| Prob025_reduction | - | - | - | - |
| Prob027_fadd | - | - | - | - |
| Prob036_ringer | - | 17.5 | out of scope: stopped at pl... | equiv |
| Prob058_alwaysblock2 | - | - | - | - |
| Prob065_7420 | - | 17.5 | out of scope: stopped at pl... | equiv |
| Prob070_ece241_2013_q2 | - | - | - | - |
| Prob075_counter_2bc | - | - | - | - |
| Prob077_wire_decl | - | - | - | - |
| Prob081_7458 | 4 | 47.5 | mismatch | extract |
| Prob088_ece241_2014_q5b | - | - | - | - |
| Prob091_2012_q2b | - | 40.0 | out of scope: stopped at pl... | equiv |
| Prob099_m2014_q6c | - | - | - | - |
| Prob112_always_case2 | 5 | 50.0 | mismatch | extract |
| Prob127_lemmings1 | - | - | - | - |
| Prob134_2014_q3c | - | - | - | - |
| Prob147_circuit10 | - | - | - | - |
| Prob005_notgate | - | - | - | - |
| Prob010_mt2015_q4a | - | - | - | - |
| Prob011_norgate | - | - | - | - |
| Prob012_xnorgate | - | - | - | - |
| Prob013_m2014_q4e | - | - | - | - |
| Prob014_andgate | - | - | - | - |
| Prob019_m2014_q4f | - | - | - | - |
| Prob020_mt2015_eq2 | - | - | - | - |
| Prob022_mux2to1 | - | - | - | - |
| Prob026_alwaysblock1 | - | - | - | - |
| Prob029_m2014_q4g | - | - | - | - |
| Prob039_always_if | - | - | - | - |
| Prob048_m2014_q4c | - | - | - | - |
| Prob049_m2014_q4b | - | - | - | - |
| Prob050_kmap1 | - | - | - | - |
| Prob053_m2014_q4d | - | - | - | - |
| Prob056_ece241_2013_q7 | - | - | - | - |
| Prob057_kmap2 | - | - | - | - |
| Prob061_2014_q4a | - | - | - | - |
| Prob069_truthtable1 | - | - | - | - |
| Prob083_mt2015_q4b | - | - | - | - |
| Prob090_circuit1 | - | - | - | - |
| Prob098_circuit7 | - | - | - | - |
| Prob101_circuit4 | - | - | - | - |
| Prob102_circuit3 | - | - | - | - |
| Prob103_circuit2 | - | - | - | - |
| Prob104_mt2015_muxdff | - | - | - | - |
| Prob107_fsm1s | - | - | - | - |
| Prob109_fsm1 | - | - | - | - |
| Prob110_fsm2 | - | - | - | - |
| Prob111_fsm2s | - | - | - | - |
| Prob113_2012_q1g | - | - | - | - |
| Prob116_m2014_q3 | - | - | - | - |
| Prob122_kmap4 | - | - | - | - |
| Prob125_kmap3 | - | - | - | - |
| Prob131_mt2015_q4 | - | - | - | - |
| Prob132_always_if2 | - | - | - | - |
| Prob135_m2014_q6b | - | - | - | - |
| Prob001_zero | - | - | out of scope: stopped at pl... | equiv |
| Prob002_m2014_q4i | - | - | out of scope: stopped at pl... | equiv |
| Prob003_step_one | - | - | out of scope: stopped at pl... | equiv |
| Prob004_vector2 | - | - | out of scope: stopped at pl... | equiv |
| Prob006_vectorr | - | - | out of scope: stopped at pl... | equiv |
| Prob007_wire | - | - | out of scope: stopped at pl... | equiv |
| Prob008_m2014_q4h | - | - | out of scope: stopped at pl... | equiv |
| Prob015_vector1 | - | - | out of scope: stopped at pl... | equiv |
| Prob023_vector100r | - | - | out of scope: stopped at pl... | equiv |
| Prob028_m2014_q4a | - | - | - | - |
| Prob032_vector0 | - | - | out of scope: stopped at pl... | equiv |
| Prob034_dff8 | - | 788.3 | out of scope: stopped at pl... | equiv |
| Prob042_vector4 | - | - | out of scope: stopped at pl... | equiv |
| Prob059_wire4 | - | - | out of scope: stopped at pl... | equiv |
| Prob064_vector3 | - | - | out of scope: stopped at pl... | equiv |
| Prob071_always_casez | - | - | - | - |
| Prob156_review2015_fancytimer | - | - | - | - |
| Prob151_review2015_fsm | - | - | - | - |
| Prob078_dualedge | - | - | - | - |
| Prob145_circuit8 | - | - | - | - |
| Prob046_dff8p | - | - | out of scope: stopped at eq... | map |
| Prob031_dff | - | - | - | - |

</details>

</details>

<details><summary>T3 HDL, no testbench (52 designs)</summary>

Rule: HDL (Verilog) with no testbench file.

| design | what it does | suite | link | licence | LOC | tb | vec |
|---|---|---|---|---|---|---|---|
| stereovision2 | Computer Vision | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | per design | 1846 | ✗ | ✗ |
| bgm | Finance | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | per design | 2663 | ✗ | ✗ |
| stereovision1 | Computer Vision | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | per design | 2553 | ✗ | ✗ |
| stereovision0 | Computer Vision | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | per design | 3905 | ✗ | ✗ |
| b22 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | GPL-3.0 | 2751 | ✗ | ✗ |
| blob_merge | Image Processing | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | per design | 1617 | ✗ | ✗ |
| b17 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | GPL-3.0 | 940 | ✗ | ✗ |
| b20 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | GPL-3.0 | 1842 | ✗ | ✗ |
| b21 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | GPL-3.0 | 1853 | ✗ | ✗ |
| diffeq1 | Math | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | per design | 56 | ✗ | ✗ |
| b18 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | GPL-3.0 | 1931 | ✗ | ✗ |
| b19 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | GPL-3.0 | 1993 | ✗ | ✗ |
| or1200 | Soft Processor | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | per design | 5237 | ✗ | ✗ |
| b15 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | GPL-3.0 | 805 | ✗ | ✗ |
| mkDelayWorker32B | Packet Processing | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | per design | 6628 | ✗ | ✗ |
| sha | Cryptography | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | per design | 2171 | ✗ | ✗ |
| mkSMAdapter4B | Packet Processing | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | per design | 4348 | ✗ | ✗ |
| raygentop | Ray Tracing | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | per design | 2978 | ✗ | ✗ |
| b14 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | GPL-3.0 | 904 | ✗ | ✗ |
| boundtop | Ray Tracing | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | per design | 2825 | ✗ | ✗ |
| b12 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | GPL-3.0 | 635 | ✗ | ✗ |
| b11 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | GPL-3.0 | 138 | ✗ | ✗ |
| mkPktMerge | Packet Processing | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | per design | 1535 | ✗ | ✗ |
| b05 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | GPL-3.0 | 444 | ✗ | ✗ |
| ch_intrinsics | Memory Init | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | per design | 292 | ✗ | ✗ |
| stereovision3 | Computer Vision | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | per design | 1061 | ✗ | ✗ |
| diffeq2 | Math | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | per design | 63 | ✗ | ✗ |
| b04 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | GPL-3.0 | 113 | ✗ | ✗ |
| b07 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | GPL-3.0 | 125 | ✗ | ✗ |
| b13 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | GPL-3.0 | 320 | ✗ | ✗ |
| b09 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | GPL-3.0 | 91 | ✗ | ✗ |
| b10 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | GPL-3.0 | 178 | ✗ | ✗ |
| b03 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | GPL-3.0 | 133 | ✗ | ✗ |
| b08 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | GPL-3.0 | 88 | ✗ | ✗ |
| b06 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | GPL-3.0 | 130 | ✗ | ✗ |
| multiclock_reader_writer | - | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | per design | 61 | ✗ | ✗ |
| b02 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | GPL-3.0 | 74 | ✗ | ✗ |
| b01 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | GPL-3.0 | 117 | ✗ | ✗ |
| multiclock_output_and_latch | - | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | per design | 63 | ✗ | ✗ |
| multiclock_separate_and_latch | - | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | per design | 53 | ✗ | ✗ |
| and_latch | - | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | per design | 21 | ✗ | ✗ |
| single_ff | - | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | per design | 5 | ✗ | ✗ |
| single_wire | - | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | per design | 3 | ✗ | ✗ |
| mcml | Medical Physics | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | per design | 24507 | ✗ | ✗ |
| arm_core | - | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | per design | 8211 | ✗ | ✗ |
| LU64PEEng | - | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | per design | 6043 | ✗ | ✗ |
| LU32PEEng | Math | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | per design | 5497 | ✗ | ✗ |
| LU8PEEng | Math | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | per design | 5033 | ✗ | ✗ |
| raygentop_nolatches | - | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | per design | 3178 | ✗ | ✗ |
| spree | - | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | per design | 3072 | ✗ | ✗ |
| boundtop_nolatches | - | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | per design | 3053 | ✗ | ✗ |
| ch_intrinsics_nolatches | - | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | per design | 301 | ✗ | ✗ |

<details><summary>Flow and VTR QoR</summary>

| design | iverilog | Odin sim | VTR stage | LUTs | blocks | FFs | pins | mult/mem | cpd ns | chan w |
|---|---|---|---|---|---|---|---|---|---|---|
| stereovision2 | - | - | - | 8426 | 1689 | 15573 | 331 | 468/0 | 13.2648 | 90 |
| bgm | - | - | - | - | - | - | - | - | - | - |
| stereovision1 | - | - | - | 6462 | 758 | 10315 | 278 | 152/0 | 5.72613 | 76 |
| stereovision0 | - | - | - | 6887 | 702 | 11458 | 366 | 0/0 | 3.8277 | 52 |
| b22 | - | - | - | - | - | - | - | - | - | - |
| blob_merge | - | - | - | 6015 | 486 | 575 | 232 | 0/0 | 14.668 | 62 |
| b17 | - | - | - | - | - | - | - | - | - | - |
| b20 | - | - | - | - | - | - | - | - | - | - |
| b21 | - | - | - | - | - | - | - | - | - | - |
| diffeq1 | - | - | - | 294 | 31 | 193 | 258 | 5/0 | 17.2038 | 58 |
| b18 | - | - | - | - | - | - | - | - | - | - |
| b19 | - | - | - | - | - | - | - | - | - | - |
| or1200 | - | - | - | 2473 | 237 | 672 | 782 | 1/64 | 8.74562 | 82 |
| b15 | - | - | - | - | - | - | - | - | - | - |
| mkDelayWorker32B | - | - | - | 2057 | 63 | 34 | 1066 | 0/1336 | 6.8227 | 38 |
| sha | - | - | - | 1290 | 142 | 893 | 74 | 0/0 | 9.86096 | 64 |
| mkSMAdapter4B | - | - | - | 1200 | 118 | 639 | 403 | 0/153 | 6.19734 | 48 |
| raygentop | - | - | - | 1195 | 127 | 946 | 560 | 15/21 | 5.43116 | 56 |
| b14 | - | - | - | - | - | - | - | - | - | - |
| boundtop | - | - | - | 572 | 41 | 383 | 468 | 0/32 | 3.06393 | 40 |
| b12 | - | - | - | - | - | - | - | - | - | - |
| b11 | - | - | - | - | - | - | - | - | - | - |
| mkPktMerge | - | - | - | 329 | 19 | 18 | 467 | 0/459 | 4.09815 | 36 |
| b05 | - | - | - | - | - | - | - | - | - | - |
| ch_intrinsics | - | - | - | 192 | 12 | 82 | 229 | 0/8 | 2.12094 | 38 |
| stereovision3 | - | - | - | 171 | 15 | 120 | 53 | 0/0 | 2.63369 | 30 |
| diffeq2 | - | - | - | 198 | 22 | 96 | 162 | 5/0 | 13.5453 | 44 |
| b04 | - | - | - | - | - | - | - | - | - | - |
| b07 | - | - | - | - | - | - | - | - | - | - |
| b13 | - | - | - | - | - | - | - | - | - | - |
| b09 | - | - | - | - | - | - | - | - | - | - |
| b10 | - | - | - | - | - | - | - | - | - | - |
| b03 | - | - | - | - | - | - | - | - | - | - |
| b08 | - | - | - | - | - | - | - | - | - | - |
| b06 | - | - | - | - | - | - | - | - | - | - |
| multiclock_reader_writer | - | - | - | - | - | - | - | - | - | - |
| b02 | - | - | - | - | - | - | - | - | - | - |
| b01 | - | - | - | - | - | - | - | - | - | - |
| multiclock_output_and_latch | - | - | - | - | - | - | - | - | - | - |
| multiclock_separate_and_latch | - | - | - | - | - | - | - | - | - | - |
| and_latch | - | - | - | - | - | - | - | - | - | - |
| single_ff | - | - | - | - | - | - | - | - | - | - |
| single_wire | - | - | - | - | - | - | - | - | - | - |
| mcml | - | - | - | - | - | - | - | - | - | - |
| arm_core | - | - | - | - | - | - | - | - | - | - |
| LU64PEEng | - | - | - | - | - | - | - | - | - | - |
| LU32PEEng | - | - | - | - | - | - | - | - | - | - |
| LU8PEEng | - | - | - | - | - | - | - | - | - | - |
| raygentop_nolatches | - | - | - | - | - | - | - | - | - | - |
| spree | - | - | - | - | - | - | - | - | - | - |
| boundtop_nolatches | - | - | - | - | - | - | - | - | - | - |
| ch_intrinsics_nolatches | - | - | - | - | - | - | - | - | - | - |

</details>

<details><summary>LUT forms</summary>

| design | gates/d | 4-LUT/d | 6-LUT/d |
|---|---|---|---|
| stereovision2 | 431409/79 | 69596/24 | 48816/15 |
| bgm | 327394/126 | 62083/31 | 46209/21 |
| stereovision1 | 139252/27 | 38630/12 | 27709/7 |
| stereovision0 | 42435/26 | 16352/7 | 14355/5 |
| b22 | 56695/105 | 8495/33 | 6234/20 |
| blob_merge | 61064/78 | 8741/30 | 5264/18 |
| b17 | 107358/80 | 7388/19 | 5240/12 |
| b20 | 37565/105 | 5680/33 | 4108/20 |
| b21 | 38305/105 | 5603/34 | 4058/21 |
| diffeq1 | 14398/101 | 4897/34 | 3585/23 |
| b18 | 36964/105 | 4976/0 | 3500/0 |
| b19 | 36964/105 | 4976/0 | 3500/0 |
| or1200 | fail: or1200.v:3101:1: erro... | fail: or1200.v:3101:1: erro... | fail: or1200.v:3101:1: erro... |
| b15 | 26705/80 | 3326/19 | 2322/12 |
| mkDelayWorker32B | fail: mkDelayWorker32B.v:15... | fail: mkDelayWorker32B.v:15... | fail: mkDelayWorker32B.v:15... |
| sha | 8125/79 | 2788/30 | 1583/20 |
| mkSMAdapter4B | fail: mkSMAdapter4B.v:3391:... | fail: mkSMAdapter4B.v:3391:... | fail: mkSMAdapter4B.v:3391:... |
| raygentop | fail: raygentop.v:571:1: er... | fail: raygentop.v:571:1: er... | fail: raygentop.v:571:1: er... |
| b14 | 9335/105 | 1352/32 | 984/20 |
| boundtop | fail: boundtop.v:1653:1: er... | fail: boundtop.v:1653:1: er... | fail: boundtop.v:1653:1: er... |
| b12 | 5026/26 | 673/8 | 484/5 |
| b11 | 3924/39 | 515/14 | 357/9 |
| mkPktMerge | fail: mkPktMerge.v:566:1: e... | fail: mkPktMerge.v:566:1: e... | fail: mkPktMerge.v:566:1: e... |
| b05 | 20479/98 | 306/12 | 196/8 |
| ch_intrinsics | fail: ch_intrinsics.v:34:1:... | fail: ch_intrinsics.v:34:1:... | fail: ch_intrinsics.v:34:1:... |
| stereovision3 | 2042/17 | 233/5 | 175/4 |
| diffeq2 | 14387/93 | 162/22 | 105/13 |
| b04 | 1782/54 | 133/6 | 104/4 |
| b07 | 776/17 | 128/6 | 95/4 |
| b13 | 1034/24 | 90/3 | 70/3 |
| b09 | 248/13 | 61/4 | 47/3 |
| b10 | 211/10 | 55/4 | 39/2 |
| b03 | 193/10 | 56/4 | 37/3 |
| b08 | 654/16 | 56/5 | 35/3 |
| b06 | 72/7 | 17/3 | 14/2 |
| multiclock_reader_writer | 118/9 | 16/2 | 10/1 |
| b02 | 26/6 | 10/2 | 9/2 |
| b01 | 105/10 | 18/3 | 5/1 |
| multiclock_output_and_latch | 9/3 | 5/1 | 5/1 |
| multiclock_separate_and_latch | 3/1 | 3/1 | 3/1 |
| and_latch | 1/1 | 1/1 | 1/1 |
| single_ff | 0/0 | 0/0 | 0/0 |
| single_wire | 0/0 | 0/0 | 0/0 |
| mcml | fail: mcml.v:1676:1: error:... | fail: mcml.v:1676:1: error:... | fail: mcml.v:1676:1: error:... |
| arm_core | fail: timeout 900 s/fail: t... | fail: timeout 900 s/fail: t... | fail: timeout 900 s/fail: t... |
| LU64PEEng | fail: LU64PEEng.v:3091:1: e... | fail: LU64PEEng.v:3091:1: e... | fail: LU64PEEng.v:3091:1: e... |
| LU32PEEng | fail: LU32PEEng.v:2609:1: e... | fail: LU32PEEng.v:2609:1: e... | fail: LU32PEEng.v:2609:1: e... |
| LU8PEEng | fail: LU8PEEng.v:2250:1: er... | fail: LU8PEEng.v:2250:1: er... | fail: LU8PEEng.v:2250:1: er... |
| raygentop_nolatches | fail: raygentop_nolatches.v... | fail: raygentop_nolatches.v... | fail: raygentop_nolatches.v... |
| spree | fail: spree.v:1720:1: error... | fail: spree.v:1720:1: error... | fail: spree.v:1720:1: error... |
| boundtop_nolatches | fail: boundtop_nolatches.v:... | fail: boundtop_nolatches.v:... | fail: boundtop_nolatches.v:... |
| ch_intrinsics_nolatches | fail: ch_intrinsics_nolatch... | fail: ch_intrinsics_nolatch... | fail: ch_intrinsics_nolatch... |

</details>

<details><summary>Properties</summary>

| design | seq | mem | mul | add | fsm | latch | hier | bbox |
|---|---|---|---|---|---|---|---|---|
| stereovision2 | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ |
| bgm | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ |
| stereovision1 | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| stereovision0 | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ | ✓ | ✓ |
| b22 | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ |
| blob_merge | ✓ | ✗ | ✗ | ✓ | ✓ | ✗ | ✓ | ✗ |
| b17 | ✓ | ✗ | ✗ | ✓ | ✓ | ✗ | ✓ | ✗ |
| b20 | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ |
| b21 | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ |
| diffeq1 | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| b18 | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| b19 | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| or1200 | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ |
| b15 | ✓ | ✗ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ |
| mkDelayWorker32B | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✓ |
| sha | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| mkSMAdapter4B | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✓ |
| raygentop | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| b14 | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| boundtop | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✓ | ✓ |
| b12 | ✓ | ✗ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ |
| b11 | ✓ | ✗ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ |
| mkPktMerge | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✓ |
| b05 | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| ch_intrinsics | ✓ | ✓ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ |
| stereovision3 | ✓ | ✗ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ |
| diffeq2 | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| b04 | ✓ | ✗ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ |
| b07 | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ |
| b13 | ✓ | ✗ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ |
| b09 | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ |
| b10 | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ |
| b03 | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ |
| b08 | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ |
| b06 | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ |
| multiclock_reader_writer | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| b02 | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ |
| b01 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| multiclock_output_and_latch | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ |
| multiclock_separate_and_latch | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ |
| and_latch | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| single_ff | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| single_wire | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| mcml | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| arm_core | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✓ |
| LU64PEEng | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| LU32PEEng | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| LU8PEEng | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| raygentop_nolatches | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| spree | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| boundtop_nolatches | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✓ | ✓ |
| ch_intrinsics_nolatches | ✓ | ✓ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ |

</details>

<details><summary>Silicon</summary>

| design | cells | core um2 | LVS | Si stage |
|---|---|---|---|---|
| stereovision2 | - | - | - | - |
| bgm | - | - | - | - |
| stereovision1 | - | - | - | - |
| stereovision0 | - | - | - | - |
| b22 | - | - | - | - |
| blob_merge | - | - | - | - |
| b17 | - | - | - | - |
| b20 | - | - | - | - |
| b21 | - | - | - | - |
| diffeq1 | - | - | - | - |
| b18 | - | - | - | - |
| b19 | - | - | - | - |
| or1200 | - | - | - | - |
| b15 | - | - | - | - |
| mkDelayWorker32B | - | - | - | - |
| sha | - | - | - | - |
| mkSMAdapter4B | - | - | - | - |
| raygentop | - | - | - | - |
| b14 | - | - | - | - |
| boundtop | - | - | - | - |
| b12 | - | - | - | - |
| b11 | - | - | - | - |
| mkPktMerge | - | - | - | - |
| b05 | - | - | - | - |
| ch_intrinsics | - | - | - | - |
| stereovision3 | - | - | - | - |
| diffeq2 | - | - | - | - |
| b04 | - | - | - | - |
| b07 | - | - | - | - |
| b13 | - | - | - | - |
| b09 | - | - | - | - |
| b10 | - | - | - | - |
| b03 | - | - | - | - |
| b08 | - | - | - | - |
| b06 | - | - | - | - |
| multiclock_reader_writer | - | - | - | - |
| b02 | - | - | - | - |
| b01 | - | - | - | - |
| multiclock_output_and_latch | - | - | - | - |
| multiclock_separate_and_latch | - | - | - | - |
| and_latch | - | - | - | - |
| single_ff | - | - | - | - |
| single_wire | - | - | - | - |
| mcml | - | - | - | - |
| arm_core | - | - | - | - |
| LU64PEEng | - | - | - | - |
| LU32PEEng | - | - | - | - |
| LU8PEEng | - | - | - | - |
| raygentop_nolatches | - | - | - | - |
| spree | - | - | - | - |
| boundtop_nolatches | - | - | - | - |
| ch_intrinsics_nolatches | - | - | - | - |

</details>

</details>

<details><summary>T4 netlist only (219 designs)</summary>

Rule: BLIF netlist, no HDL.

| design | what it does | suite | link | licence | LOC | tb | vec |
|---|---|---|---|---|---|---|---|
| clma | Bus interface | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| s38584.1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| s38417 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| ex1010 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| pdc | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| spla | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| elliptic | Fifth Order Elliptic Filter | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| frisc | RISC Microprocessor | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| ex1010 | - | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | none-stated | - | ✗ | ✗ |
| s38584.1 | - | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | none-stated | - | ✗ | ✗ |
| s38417 | - | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | none-stated | - | ✗ | ✗ |
| pdc | - | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | none-stated | - | ✗ | ✗ |
| s298 | Finite state machine "from a PLD" | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| apex2 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| seq | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| bigkey | Key encryption circuit | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| frisc | RISC Microprocessor | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | none-stated | - | ✗ | ✗ |
| des | DES data encryption circuit | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| alu4 | ALU | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| diffeq | Differential Equation Solver | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| elliptic | Fifth Order Elliptic Filter | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | none-stated | - | ✗ | ✗ |
| spla | - | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | none-stated | - | ✗ | ✗ |
| misex3 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| dsip | Encryption circuit | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| apex4 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| ex5p | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| tseng | Bus controller | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| i10 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| apex2 | - | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | none-stated | - | ✗ | ✗ |
| des | DES data encryption circuit | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | none-stated | - | ✗ | ✗ |
| apex3 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| apex4 | - | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | none-stated | - | ✗ | ✗ |
| seq | - | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | none-stated | - | ✗ | ✗ |
| alu4 | ALU | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | none-stated | - | ✗ | ✗ |
| cps | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| C7552 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| misex3 | - | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | none-stated | - | ✗ | ✗ |
| apex1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| dsip | Encryption circuit | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | none-stated | - | ✗ | ✗ |
| s298 | Finite state machine "from a PLD" | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | none-stated | - | ✗ | ✗ |
| parker1986 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| pair | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| C5315 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| diffeq | Differential Equation Solver | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | none-stated | - | ✗ | ✗ |
| bigkey | Key encryption circuit | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | none-stated | - | ✗ | ✗ |
| s5378 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| misex3c | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| apex5 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| C6288 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| k2 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| dalu | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| table5 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| i8 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| table3 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| ex5p | - | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | none-stated | - | ✗ | ✗ |
| mm30a | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| cordic | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| s9234.1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| clma | Bus interface | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | none-stated | - | ✗ | ✗ |
| ex4p | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| C3540 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| scf | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| tseng | Bus controller | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | none-stated | - | ✗ | ✗ |
| bbrtas | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| apex6 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| sbc | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| frg2 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| x3 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| i9 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| ecc | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| daio-rec | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| rot | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| s1488 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| s1238 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| s1494 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| vda | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| e64 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| planet | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| planet1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| s1196 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| C2670 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| duke2 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| sand | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| styr | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| s1423 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| ph-decod | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| gcd | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| s953 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| t481 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| mm9b | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| i7 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| alu2 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| s1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| x4 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| too-lrg | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| i6 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| C880 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| s838 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| rd84 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| C1908 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| s832 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| 9sym | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| x1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| mm9a | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| clip | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| example2 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| bw | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| C432 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| ex1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| s820 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| mult32a | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| dk16 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| keyb | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| apex7 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| s510 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| i4 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| 9symml | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| s838.1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| cse | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| sao2 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| i5 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| s713 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| term1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| s641 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| pma | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| tbk | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| rd73 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| mm4a | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| ttt2 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| C1355 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| C499 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| i2 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| s400 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| s344 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| s349 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| vg2 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| bbsse | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| inc | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| sse | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| s444 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| ex6 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| s382 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| s526n | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| 5xp1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| mult16a | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| b12 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| s386 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| cht | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| f51m | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| s526 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| opus | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| frg1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| misex2 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| unreg | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| my-adder | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| s420.1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| b9 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| i3 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| o64 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| dk14 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| comp | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| c8 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| count | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| ldd | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| ex4 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| pcler8 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| traffic | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| lal | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| mark1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| squar5 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| bbara | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| mult16b | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| sqrt8ml | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| sqrt8 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| cc | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| dk15 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| s208.1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| s420 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| sct | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| cu | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| i1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| misex1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| pcle | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| decod | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| pm1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| cm162a | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| s208 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| cmb | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| x2 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| tcon | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| dk17 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| mux | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| beecount | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| cm150a | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| dk512 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| rd53 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| cm163a | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| cm85a | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| cm138a | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| cm42a | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| tav | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| cm151a | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| z4ml | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| mc | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| bbtas | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| cm152a | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| s27 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| con1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| dk27 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| parity | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| b1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| cm82a | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| daio | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| lion | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| majority | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| C17 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| xor5 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| chain_cout_fanout | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |
| shiftreg | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | not read | - | ✗ | ✗ |

<details><summary>Flow and VTR QoR</summary>

| design | iverilog | Odin sim | VTR stage | LUTs | blocks | FFs | pins | mult/mem | cpd ns | chan w |
|---|---|---|---|---|---|---|---|---|---|---|
| clma | - | - | - | - | - | - | - | - | - | - |
| s38584.1 | - | - | - | - | - | - | - | - | - | - |
| s38417 | - | - | - | - | - | - | - | - | - | - |
| ex1010 | - | - | - | - | - | - | - | - | - | - |
| pdc | - | - | - | - | - | - | - | - | - | - |
| spla | - | - | - | - | - | - | - | - | - | - |
| elliptic | - | - | - | - | - | - | - | - | - | - |
| frisc | - | - | - | - | - | - | - | - | - | - |
| ex1010 | - | - | - | 2777 | 314 | 0 | 20 | 0/0 | 9.8022 | 84 |
| s38584.1 | - | - | - | 2190 | 182 | 1141 | 343 | 0/0 | 4.65105 | 48 |
| s38417 | - | - | - | 2189 | 179 | 1345 | 135 | 0/0 | 4.96812 | 42 |
| pdc | - | - | - | 1973 | 176 | 0 | 56 | 0/0 | 7.42762 | 72 |
| s298 | - | - | - | - | - | - | - | - | - | - |
| apex2 | - | - | - | - | - | - | - | - | - | - |
| seq | - | - | - | - | - | - | - | - | - | - |
| bigkey | - | - | - | - | - | - | - | - | - | - |
| frisc | - | - | - | 1668 | 153 | 814 | 136 | 0/0 | 8.694 | 66 |
| des | - | - | - | - | - | - | - | - | - | - |
| alu4 | - | - | - | - | - | - | - | - | - | - |
| diffeq | - | - | - | - | - | - | - | - | - | - |
| elliptic | - | - | - | 1463 | 137 | 884 | 245 | 0/0 | 7.59909 | 58 |
| spla | - | - | - | 1445 | 131 | 0 | 62 | 0/0 | 6.39096 | 60 |
| misex3 | - | - | - | - | - | - | - | - | - | - |
| dsip | - | - | - | - | - | - | - | - | - | - |
| apex4 | - | - | - | - | - | - | - | - | - | - |
| ex5p | - | - | - | - | - | - | - | - | - | - |
| tseng | - | - | - | - | - | - | - | - | - | - |
| i10 | - | - | - | - | - | - | - | - | - | - |
| apex2 | - | - | - | 992 | 92 | 0 | 42 | 0/0 | 5.89143 | 54 |
| des | - | - | - | 901 | 77 | 0 | 501 | 0/0 | 4.68402 | 38 |
| apex3 | - | - | - | - | - | - | - | - | - | - |
| apex4 | - | - | - | 865 | 80 | 0 | 28 | 0/0 | 5.74616 | 60 |
| seq | - | - | - | 855 | 75 | 0 | 76 | 0/0 | 4.95078 | 54 |
| alu4 | - | - | - | 818 | 68 | 0 | 22 | 0/0 | 5.0705 | 42 |
| cps | - | - | - | - | - | - | - | - | - | - |
| C7552 | - | - | - | - | - | - | - | - | - | - |
| misex3 | - | - | - | 714 | 62 | 0 | 28 | 0/0 | 4.81741 | 48 |
| apex1 | - | - | - | - | - | - | - | - | - | - |
| dsip | - | - | - | 686 | 66 | 224 | 426 | 0/0 | 2.72755 | 34 |
| s298 | - | - | - | 661 | 58 | 8 | 10 | 0/0 | 6.32231 | 46 |
| parker1986 | - | - | - | - | - | - | - | - | - | - |
| pair | - | - | - | - | - | - | - | - | - | - |
| C5315 | - | - | - | - | - | - | - | - | - | - |
| diffeq | - | - | - | 580 | 53 | 310 | 103 | 0/0 | 4.91464 | 42 |
| bigkey | - | - | - | 572 | 52 | 224 | 460 | 0/0 | 2.59891 | 38 |
| s5378 | - | - | - | - | - | - | - | - | - | - |
| misex3c | - | - | - | - | - | - | - | - | - | - |
| apex5 | - | - | - | - | - | - | - | - | - | - |
| C6288 | - | - | - | - | - | - | - | - | - | - |
| k2 | - | - | - | - | - | - | - | - | - | - |
| dalu | - | - | - | - | - | - | - | - | - | - |
| table5 | - | - | - | - | - | - | - | - | - | - |
| i8 | - | - | - | - | - | - | - | - | - | - |
| table3 | - | - | - | - | - | - | - | - | - | - |
| ex5p | - | - | - | 467 | 39 | 0 | 71 | 0/0 | 5.34702 | 48 |
| mm30a | - | - | - | - | - | - | - | - | - | - |
| cordic | - | - | - | - | - | - | - | - | - | - |
| s9234.1 | - | - | - | - | - | - | - | - | - | - |
| clma | - | - | - | 450 | 82 | 26 | 465 | 0/0 | 5.41555 | 36 |
| ex4p | - | - | - | - | - | - | - | - | - | - |
| C3540 | - | - | - | - | - | - | - | - | - | - |
| scf | - | - | - | - | - | - | - | - | - | - |
| tseng | - | - | - | 407 | 34 | 219 | 174 | 0/0 | 4.62879 | 48 |
| bbrtas | - | - | - | - | - | - | - | - | - | - |
| apex6 | - | - | - | - | - | - | - | - | - | - |
| sbc | - | - | - | - | - | - | - | - | - | - |
| frg2 | - | - | - | - | - | - | - | - | - | - |
| x3 | - | - | - | - | - | - | - | - | - | - |
| i9 | - | - | - | - | - | - | - | - | - | - |
| ecc | - | - | - | - | - | - | - | - | - | - |
| daio-rec | - | - | - | - | - | - | - | - | - | - |
| rot | - | - | - | - | - | - | - | - | - | - |
| s1488 | - | - | - | - | - | - | - | - | - | - |
| s1238 | - | - | - | - | - | - | - | - | - | - |
| s1494 | - | - | - | - | - | - | - | - | - | - |
| vda | - | - | - | - | - | - | - | - | - | - |
| e64 | - | - | - | - | - | - | - | - | - | - |
| planet | - | - | - | - | - | - | - | - | - | - |
| planet1 | - | - | - | - | - | - | - | - | - | - |
| s1196 | - | - | - | - | - | - | - | - | - | - |
| C2670 | - | - | - | - | - | - | - | - | - | - |
| duke2 | - | - | - | - | - | - | - | - | - | - |
| sand | - | - | - | - | - | - | - | - | - | - |
| styr | - | - | - | - | - | - | - | - | - | - |
| s1423 | - | - | - | - | - | - | - | - | - | - |
| ph-decod | - | - | - | - | - | - | - | - | - | - |
| gcd | - | - | - | - | - | - | - | - | - | - |
| s953 | - | - | - | - | - | - | - | - | - | - |
| t481 | - | - | - | - | - | - | - | - | - | - |
| mm9b | - | - | - | - | - | - | - | - | - | - |
| i7 | - | - | - | - | - | - | - | - | - | - |
| alu2 | - | - | - | - | - | - | - | - | - | - |
| s1 | - | - | - | - | - | - | - | - | - | - |
| x4 | - | - | - | - | - | - | - | - | - | - |
| too-lrg | - | - | - | - | - | - | - | - | - | - |
| i6 | - | - | - | - | - | - | - | - | - | - |
| C880 | - | - | - | - | - | - | - | - | - | - |
| s838 | - | - | - | - | - | - | - | - | - | - |
| rd84 | - | - | - | - | - | - | - | - | - | - |
| C1908 | - | - | - | - | - | - | - | - | - | - |
| s832 | - | - | - | - | - | - | - | - | - | - |
| 9sym | - | - | - | - | - | - | - | - | - | - |
| x1 | - | - | - | - | - | - | - | - | - | - |
| mm9a | - | - | - | - | - | - | - | - | - | - |
| clip | - | - | - | - | - | - | - | - | - | - |
| example2 | - | - | - | - | - | - | - | - | - | - |
| bw | - | - | - | - | - | - | - | - | - | - |
| C432 | - | - | - | - | - | - | - | - | - | - |
| ex1 | - | - | - | - | - | - | - | - | - | - |
| s820 | - | - | - | - | - | - | - | - | - | - |
| mult32a | - | - | - | - | - | - | - | - | - | - |
| dk16 | - | - | - | - | - | - | - | - | - | - |
| keyb | - | - | - | - | - | - | - | - | - | - |
| apex7 | - | - | - | - | - | - | - | - | - | - |
| s510 | - | - | - | - | - | - | - | - | - | - |
| i4 | - | - | - | - | - | - | - | - | - | - |
| 9symml | - | - | - | - | - | - | - | - | - | - |
| s838.1 | - | - | - | - | - | - | - | - | - | - |
| cse | - | - | - | - | - | - | - | - | - | - |
| sao2 | - | - | - | - | - | - | - | - | - | - |
| i5 | - | - | - | - | - | - | - | - | - | - |
| s713 | - | - | - | - | - | - | - | - | - | - |
| term1 | - | - | - | - | - | - | - | - | - | - |
| s641 | - | - | - | - | - | - | - | - | - | - |
| pma | - | - | - | - | - | - | - | - | - | - |
| tbk | - | - | - | - | - | - | - | - | - | - |
| rd73 | - | - | - | - | - | - | - | - | - | - |
| mm4a | - | - | - | - | - | - | - | - | - | - |
| ttt2 | - | - | - | - | - | - | - | - | - | - |
| C1355 | - | - | - | - | - | - | - | - | - | - |
| C499 | - | - | - | - | - | - | - | - | - | - |
| i2 | - | - | - | - | - | - | - | - | - | - |
| s400 | - | - | - | - | - | - | - | - | - | - |
| s344 | - | - | - | - | - | - | - | - | - | - |
| s349 | - | - | - | - | - | - | - | - | - | - |
| vg2 | - | - | - | - | - | - | - | - | - | - |
| bbsse | - | - | - | - | - | - | - | - | - | - |
| inc | - | - | - | - | - | - | - | - | - | - |
| sse | - | - | - | - | - | - | - | - | - | - |
| s444 | - | - | - | - | - | - | - | - | - | - |
| ex6 | - | - | - | - | - | - | - | - | - | - |
| s382 | - | - | - | - | - | - | - | - | - | - |
| s526n | - | - | - | - | - | - | - | - | - | - |
| 5xp1 | - | - | - | - | - | - | - | - | - | - |
| mult16a | - | - | - | - | - | - | - | - | - | - |
| b12 | - | - | - | - | - | - | - | - | - | - |
| s386 | - | - | - | - | - | - | - | - | - | - |
| cht | - | - | - | - | - | - | - | - | - | - |
| f51m | - | - | - | - | - | - | - | - | - | - |
| s526 | - | - | - | - | - | - | - | - | - | - |
| opus | - | - | - | - | - | - | - | - | - | - |
| frg1 | - | - | - | - | - | - | - | - | - | - |
| misex2 | - | - | - | - | - | - | - | - | - | - |
| unreg | - | - | - | - | - | - | - | - | - | - |
| my-adder | - | - | - | - | - | - | - | - | - | - |
| s420.1 | - | - | - | - | - | - | - | - | - | - |
| b9 | - | - | - | - | - | - | - | - | - | - |
| i3 | - | - | - | - | - | - | - | - | - | - |
| o64 | - | - | - | - | - | - | - | - | - | - |
| dk14 | - | - | - | - | - | - | - | - | - | - |
| comp | - | - | - | - | - | - | - | - | - | - |
| c8 | - | - | - | - | - | - | - | - | - | - |
| count | - | - | - | - | - | - | - | - | - | - |
| ldd | - | - | - | - | - | - | - | - | - | - |
| ex4 | - | - | - | - | - | - | - | - | - | - |
| pcler8 | - | - | - | - | - | - | - | - | - | - |
| traffic | - | - | - | - | - | - | - | - | - | - |
| lal | - | - | - | - | - | - | - | - | - | - |
| mark1 | - | - | - | - | - | - | - | - | - | - |
| squar5 | - | - | - | - | - | - | - | - | - | - |
| bbara | - | - | - | - | - | - | - | - | - | - |
| mult16b | - | - | - | - | - | - | - | - | - | - |
| sqrt8ml | - | - | - | - | - | - | - | - | - | - |
| sqrt8 | - | - | - | - | - | - | - | - | - | - |
| cc | - | - | - | - | - | - | - | - | - | - |
| dk15 | - | - | - | - | - | - | - | - | - | - |
| s208.1 | - | - | - | - | - | - | - | - | - | - |
| s420 | - | - | - | - | - | - | - | - | - | - |
| sct | - | - | - | - | - | - | - | - | - | - |
| cu | - | - | - | - | - | - | - | - | - | - |
| i1 | - | - | - | - | - | - | - | - | - | - |
| misex1 | - | - | - | - | - | - | - | - | - | - |
| pcle | - | - | - | - | - | - | - | - | - | - |
| decod | - | - | - | - | - | - | - | - | - | - |
| pm1 | - | - | - | - | - | - | - | - | - | - |
| cm162a | - | - | - | - | - | - | - | - | - | - |
| s208 | - | - | - | - | - | - | - | - | - | - |
| cmb | - | - | - | - | - | - | - | - | - | - |
| x2 | - | - | - | - | - | - | - | - | - | - |
| tcon | - | - | - | - | - | - | - | - | - | - |
| dk17 | - | - | - | - | - | - | - | - | - | - |
| mux | - | - | - | - | - | - | - | - | - | - |
| beecount | - | - | - | - | - | - | - | - | - | - |
| cm150a | - | - | - | - | - | - | - | - | - | - |
| dk512 | - | - | - | - | - | - | - | - | - | - |
| rd53 | - | - | - | - | - | - | - | - | - | - |
| cm163a | - | - | - | - | - | - | - | - | - | - |
| cm85a | - | - | - | - | - | - | - | - | - | - |
| cm138a | - | - | - | - | - | - | - | - | - | - |
| cm42a | - | - | - | - | - | - | - | - | - | - |
| tav | - | - | - | - | - | - | - | - | - | - |
| cm151a | - | - | - | - | - | - | - | - | - | - |
| z4ml | - | - | - | - | - | - | - | - | - | - |
| mc | - | - | - | - | - | - | - | - | - | - |
| bbtas | - | - | - | - | - | - | - | - | - | - |
| cm152a | - | - | - | - | - | - | - | - | - | - |
| s27 | - | - | - | - | - | - | - | - | - | - |
| con1 | - | - | - | - | - | - | - | - | - | - |
| dk27 | - | - | - | - | - | - | - | - | - | - |
| parity | - | - | - | - | - | - | - | - | - | - |
| b1 | - | - | - | - | - | - | - | - | - | - |
| cm82a | - | - | - | - | - | - | - | - | - | - |
| daio | - | - | - | - | - | - | - | - | - | - |
| lion | - | - | - | - | - | - | - | - | - | - |
| majority | - | - | - | - | - | - | - | - | - | - |
| C17 | - | - | - | - | - | - | - | - | - | - |
| xor5 | - | - | - | - | - | - | - | - | - | - |
| chain_cout_fanout | - | - | - | - | - | - | - | - | - | - |
| shiftreg | - | - | - | - | - | - | - | - | - | - |

</details>

<details><summary>LUT forms</summary>

| design | gates/d | 4-LUT/d | 6-LUT/d |
|---|---|---|---|
| clma | - | 8380/16 | - |
| s38584.1 | - | 6269/9 | - |
| s38417 | - | 6096/11 | - |
| ex1010 | - | 4598/8 | - |
| pdc | - | 4575/9 | - |
| spla | - | 3690/8 | - |
| elliptic | - | 3602/18 | - |
| frisc | - | 3539/23 | - |
| ex1010 | - | 4598/8 | - |
| s38584.1 | - | 6269/9 | - |
| s38417 | - | 6096/11 | - |
| pdc | - | 4575/9 | - |
| s298 | - | 1930/15 | - |
| apex2 | - | 1878/8 | - |
| seq | - | 1750/7 | - |
| bigkey | - | 1707/3 | - |
| frisc | - | 3539/23 | - |
| des | - | 1591/6 | - |
| alu4 | - | 1522/7 | - |
| diffeq | - | 1494/14 | - |
| elliptic | - | 3602/18 | - |
| spla | - | 3690/8 | - |
| misex3 | - | 1397/7 | - |
| dsip | - | 1370/3 | - |
| apex4 | - | 1261/6 | - |
| ex5p | - | 1064/7 | - |
| tseng | - | 1046/13 | - |
| i10 | - | 995/13 | - |
| apex2 | - | 1878/8 | - |
| des | - | 1591/6 | - |
| apex3 | - | 869/6 | - |
| apex4 | - | 1261/6 | - |
| seq | - | 1750/7 | - |
| alu4 | - | 1522/7 | - |
| cps | - | 756/5 | - |
| C7552 | - | 739/10 | - |
| misex3 | - | 1397/7 | - |
| apex1 | - | 699/7 | - |
| dsip | - | 1370/3 | - |
| s298 | - | 1930/15 | - |
| parker1986 | - | 660/13 | - |
| pair | - | 647/7 | - |
| C5315 | - | 620/10 | - |
| diffeq | - | 1494/14 | - |
| bigkey | - | 1707/3 | - |
| s5378 | - | 571/6 | - |
| misex3c | - | 549/6 | - |
| apex5 | - | 534/5 | - |
| C6288 | - | 527/28 | - |
| k2 | - | 518/7 | - |
| dalu | - | 500/6 | - |
| table5 | - | 485/6 | - |
| i8 | - | 481/5 | - |
| table3 | - | 480/6 | - |
| ex5p | - | 1064/7 | - |
| mm30a | - | 467/58 | - |
| cordic | - | 466/9 | - |
| s9234.1 | - | 459/8 | - |
| clma | - | 8380/16 | - |
| ex4p | - | 444/5 | - |
| C3540 | - | 431/12 | - |
| scf | - | 416/5 | - |
| tseng | - | 1046/13 | - |
| bbrtas | - | 406/18 | - |
| apex6 | - | 393/6 | - |
| sbc | - | 384/5 | - |
| frg2 | - | 379/6 | - |
| x3 | - | 377/5 | - |
| i9 | - | 376/5 | - |
| ecc | - | 330/5 | - |
| daio-rec | - | 311/7 | - |
| rot | - | 307/8 | - |
| s1488 | - | 296/4 | - |
| s1238 | - | 292/8 | - |
| s1494 | - | 292/5 | - |
| vda | - | 291/6 | - |
| e64 | - | 274/4 | - |
| planet | - | 266/4 | - |
| planet1 | - | 266/4 | - |
| s1196 | - | 264/7 | - |
| C2670 | - | 258/7 | - |
| duke2 | - | 251/5 | - |
| sand | - | 243/5 | - |
| styr | - | 238/5 | - |
| s1423 | - | 221/15 | - |
| ph-decod | - | 219/6 | - |
| gcd | - | 218/11 | - |
| s953 | - | 214/5 | - |
| t481 | - | 214/7 | - |
| mm9b | - | 204/20 | - |
| i7 | - | 203/2 | - |
| alu2 | - | 197/10 | - |
| s1 | - | 195/10 | - |
| x4 | - | 194/3 | - |
| too-lrg | - | 187/7 | - |
| i6 | - | 182/2 | - |
| C880 | - | 174/9 | - |
| s838 | - | 167/8 | - |
| rd84 | - | 157/6 | - |
| C1908 | - | 145/10 | - |
| s832 | - | 145/5 | - |
| 9sym | - | 144/6 | - |
| x1 | - | 143/4 | - |
| mm9a | - | 142/17 | - |
| clip | - | 140/5 | - |
| example2 | - | 138/4 | - |
| bw | - | 132/4 | - |
| C432 | - | 124/11 | - |
| ex1 | - | 124/4 | - |
| s820 | - | 120/5 | - |
| mult32a | - | 116/24 | - |
| dk16 | - | 105/4 | - |
| keyb | - | 103/5 | - |
| apex7 | - | 102/5 | - |
| s510 | - | 101/5 | - |
| i4 | - | 98/5 | - |
| 9symml | - | 97/6 | - |
| s838.1 | - | 95/9 | - |
| cse | - | 90/4 | - |
| sao2 | - | 90/5 | - |
| i5 | - | 88/6 | - |
| s713 | - | 88/8 | - |
| term1 | - | 88/5 | - |
| s641 | - | 87/9 | - |
| pma | - | 85/4 | - |
| tbk | - | 84/8 | - |
| rd73 | - | 83/5 | - |
| mm4a | - | 78/10 | - |
| ttt2 | - | 75/4 | - |
| C1355 | - | 74/4 | - |
| C499 | - | 74/4 | - |
| i2 | - | 74/5 | - |
| s400 | - | 69/4 | - |
| s344 | - | 67/4 | - |
| s349 | - | 67/4 | - |
| vg2 | - | 67/4 | - |
| bbsse | - | 64/6 | - |
| inc | - | 64/4 | - |
| sse | - | 64/6 | - |
| s444 | - | 62/4 | - |
| ex6 | - | 60/7 | - |
| s382 | - | 60/4 | - |
| s526n | - | 60/4 | - |
| 5xp1 | - | 57/4 | - |
| mult16a | - | 57/12 | - |
| b12 | - | 56/4 | - |
| s386 | - | 56/3 | - |
| cht | - | 55/2 | - |
| f51m | - | 54/4 | - |
| s526 | - | 52/4 | - |
| opus | - | 50/5 | - |
| frg1 | - | 49/6 | - |
| misex2 | - | 49/3 | - |
| unreg | - | 48/2 | - |
| my-adder | - | 47/16 | - |
| s420.1 | - | 47/5 | - |
| b9 | - | 46/3 | - |
| i3 | - | 46/3 | - |
| o64 | - | 46/4 | - |
| dk14 | - | 43/7 | - |
| comp | - | 40/5 | - |
| c8 | - | 39/4 | - |
| count | - | 39/5 | - |
| ldd | - | 37/5 | - |
| ex4 | - | 35/4 | - |
| pcler8 | - | 35/4 | - |
| traffic | - | 35/3 | - |
| lal | - | 34/3 | - |
| mark1 | - | 34/3 | - |
| squar5 | - | 34/3 | - |
| bbara | - | 33/3 | - |
| mult16b | - | 31/1 | - |
| sqrt8ml | - | 31/6 | - |
| sqrt8 | - | 29/4 | - |
| cc | - | 26/3 | - |
| dk15 | - | 24/3 | - |
| s208.1 | - | 24/4 | - |
| s420 | - | 23/3 | - |
| sct | - | 23/3 | - |
| cu | - | 22/3 | - |
| i1 | - | 21/3 | - |
| misex1 | - | 21/3 | - |
| pcle | - | 21/3 | - |
| decod | - | 20/2 | - |
| pm1 | - | 19/3 | - |
| cm162a | - | 18/3 | - |
| s208 | - | 18/3 | - |
| cmb | - | 17/3 | - |
| x2 | - | 17/3 | - |
| tcon | - | 16/1 | - |
| dk17 | - | 15/2 | - |
| mux | - | 15/4 | - |
| beecount | - | 14/2 | - |
| cm150a | - | 14/3 | - |
| dk512 | - | 14/2 | - |
| rd53 | - | 12/4 | - |
| cm163a | - | 11/3 | - |
| cm85a | - | 11/3 | - |
| cm138a | - | 10/2 | - |
| cm42a | - | 10/1 | - |
| tav | - | 9/2 | - |
| cm151a | - | 8/3 | - |
| z4ml | - | 8/3 | - |
| mc | - | 7/2 | - |
| bbtas | - | 6/2 | - |
| cm152a | - | 6/3 | - |
| s27 | - | 6/2 | - |
| con1 | - | 5/2 | - |
| dk27 | - | 5/1 | - |
| parity | - | 5/2 | - |
| b1 | - | 4/1 | - |
| cm82a | - | 4/2 | - |
| daio | - | 3/1 | - |
| lion | - | 3/1 | - |
| majority | - | 3/2 | - |
| C17 | - | 2/1 | - |
| xor5 | - | 2/2 | - |
| chain_cout_fanout | - | 1/1 | - |
| shiftreg | - | 0/0 | - |

</details>

<details><summary>Properties</summary>

| design | seq | mem | mul | add | fsm | latch | hier | bbox |
|---|---|---|---|---|---|---|---|---|
| clma | - | - | - | - | - | - | - | - |
| s38584.1 | - | - | - | - | - | - | - | - |
| s38417 | - | - | - | - | - | - | - | - |
| ex1010 | - | - | - | - | - | - | - | - |
| pdc | - | - | - | - | - | - | - | - |
| spla | - | - | - | - | - | - | - | - |
| elliptic | - | - | - | - | - | - | - | - |
| frisc | - | - | - | - | - | - | - | - |
| ex1010 | - | - | - | - | - | - | - | - |
| s38584.1 | - | - | - | - | - | - | - | - |
| s38417 | - | - | - | - | - | - | - | - |
| pdc | - | - | - | - | - | - | - | - |
| s298 | - | - | - | - | - | - | - | - |
| apex2 | - | - | - | - | - | - | - | - |
| seq | - | - | - | - | - | - | - | - |
| bigkey | - | - | - | - | - | - | - | - |
| frisc | - | - | - | - | - | - | - | - |
| des | - | - | - | - | - | - | - | - |
| alu4 | - | - | - | - | - | - | - | - |
| diffeq | - | - | - | - | - | - | - | - |
| elliptic | - | - | - | - | - | - | - | - |
| spla | - | - | - | - | - | - | - | - |
| misex3 | - | - | - | - | - | - | - | - |
| dsip | - | - | - | - | - | - | - | - |
| apex4 | - | - | - | - | - | - | - | - |
| ex5p | - | - | - | - | - | - | - | - |
| tseng | - | - | - | - | - | - | - | - |
| i10 | - | - | - | - | - | - | - | - |
| apex2 | - | - | - | - | - | - | - | - |
| des | - | - | - | - | - | - | - | - |
| apex3 | - | - | - | - | - | - | - | - |
| apex4 | - | - | - | - | - | - | - | - |
| seq | - | - | - | - | - | - | - | - |
| alu4 | - | - | - | - | - | - | - | - |
| cps | - | - | - | - | - | - | - | - |
| C7552 | - | - | - | - | - | - | - | - |
| misex3 | - | - | - | - | - | - | - | - |
| apex1 | - | - | - | - | - | - | - | - |
| dsip | - | - | - | - | - | - | - | - |
| s298 | - | - | - | - | - | - | - | - |
| parker1986 | - | - | - | - | - | - | - | - |
| pair | - | - | - | - | - | - | - | - |
| C5315 | - | - | - | - | - | - | - | - |
| diffeq | - | - | - | - | - | - | - | - |
| bigkey | - | - | - | - | - | - | - | - |
| s5378 | - | - | - | - | - | - | - | - |
| misex3c | - | - | - | - | - | - | - | - |
| apex5 | - | - | - | - | - | - | - | - |
| C6288 | - | - | - | - | - | - | - | - |
| k2 | - | - | - | - | - | - | - | - |
| dalu | - | - | - | - | - | - | - | - |
| table5 | - | - | - | - | - | - | - | - |
| i8 | - | - | - | - | - | - | - | - |
| table3 | - | - | - | - | - | - | - | - |
| ex5p | - | - | - | - | - | - | - | - |
| mm30a | - | - | - | - | - | - | - | - |
| cordic | - | - | - | - | - | - | - | - |
| s9234.1 | - | - | - | - | - | - | - | - |
| clma | - | - | - | - | - | - | - | - |
| ex4p | - | - | - | - | - | - | - | - |
| C3540 | - | - | - | - | - | - | - | - |
| scf | - | - | - | - | - | - | - | - |
| tseng | - | - | - | - | - | - | - | - |
| bbrtas | - | - | - | - | - | - | - | - |
| apex6 | - | - | - | - | - | - | - | - |
| sbc | - | - | - | - | - | - | - | - |
| frg2 | - | - | - | - | - | - | - | - |
| x3 | - | - | - | - | - | - | - | - |
| i9 | - | - | - | - | - | - | - | - |
| ecc | - | - | - | - | - | - | - | - |
| daio-rec | - | - | - | - | - | - | - | - |
| rot | - | - | - | - | - | - | - | - |
| s1488 | - | - | - | - | - | - | - | - |
| s1238 | - | - | - | - | - | - | - | - |
| s1494 | - | - | - | - | - | - | - | - |
| vda | - | - | - | - | - | - | - | - |
| e64 | - | - | - | - | - | - | - | - |
| planet | - | - | - | - | - | - | - | - |
| planet1 | - | - | - | - | - | - | - | - |
| s1196 | - | - | - | - | - | - | - | - |
| C2670 | - | - | - | - | - | - | - | - |
| duke2 | - | - | - | - | - | - | - | - |
| sand | - | - | - | - | - | - | - | - |
| styr | - | - | - | - | - | - | - | - |
| s1423 | - | - | - | - | - | - | - | - |
| ph-decod | - | - | - | - | - | - | - | - |
| gcd | - | - | - | - | - | - | - | - |
| s953 | - | - | - | - | - | - | - | - |
| t481 | - | - | - | - | - | - | - | - |
| mm9b | - | - | - | - | - | - | - | - |
| i7 | - | - | - | - | - | - | - | - |
| alu2 | - | - | - | - | - | - | - | - |
| s1 | - | - | - | - | - | - | - | - |
| x4 | - | - | - | - | - | - | - | - |
| too-lrg | - | - | - | - | - | - | - | - |
| i6 | - | - | - | - | - | - | - | - |
| C880 | - | - | - | - | - | - | - | - |
| s838 | - | - | - | - | - | - | - | - |
| rd84 | - | - | - | - | - | - | - | - |
| C1908 | - | - | - | - | - | - | - | - |
| s832 | - | - | - | - | - | - | - | - |
| 9sym | - | - | - | - | - | - | - | - |
| x1 | - | - | - | - | - | - | - | - |
| mm9a | - | - | - | - | - | - | - | - |
| clip | - | - | - | - | - | - | - | - |
| example2 | - | - | - | - | - | - | - | - |
| bw | - | - | - | - | - | - | - | - |
| C432 | - | - | - | - | - | - | - | - |
| ex1 | - | - | - | - | - | - | - | - |
| s820 | - | - | - | - | - | - | - | - |
| mult32a | - | - | - | - | - | - | - | - |
| dk16 | - | - | - | - | - | - | - | - |
| keyb | - | - | - | - | - | - | - | - |
| apex7 | - | - | - | - | - | - | - | - |
| s510 | - | - | - | - | - | - | - | - |
| i4 | - | - | - | - | - | - | - | - |
| 9symml | - | - | - | - | - | - | - | - |
| s838.1 | - | - | - | - | - | - | - | - |
| cse | - | - | - | - | - | - | - | - |
| sao2 | - | - | - | - | - | - | - | - |
| i5 | - | - | - | - | - | - | - | - |
| s713 | - | - | - | - | - | - | - | - |
| term1 | - | - | - | - | - | - | - | - |
| s641 | - | - | - | - | - | - | - | - |
| pma | - | - | - | - | - | - | - | - |
| tbk | - | - | - | - | - | - | - | - |
| rd73 | - | - | - | - | - | - | - | - |
| mm4a | - | - | - | - | - | - | - | - |
| ttt2 | - | - | - | - | - | - | - | - |
| C1355 | - | - | - | - | - | - | - | - |
| C499 | - | - | - | - | - | - | - | - |
| i2 | - | - | - | - | - | - | - | - |
| s400 | - | - | - | - | - | - | - | - |
| s344 | - | - | - | - | - | - | - | - |
| s349 | - | - | - | - | - | - | - | - |
| vg2 | - | - | - | - | - | - | - | - |
| bbsse | - | - | - | - | - | - | - | - |
| inc | - | - | - | - | - | - | - | - |
| sse | - | - | - | - | - | - | - | - |
| s444 | - | - | - | - | - | - | - | - |
| ex6 | - | - | - | - | - | - | - | - |
| s382 | - | - | - | - | - | - | - | - |
| s526n | - | - | - | - | - | - | - | - |
| 5xp1 | - | - | - | - | - | - | - | - |
| mult16a | - | - | - | - | - | - | - | - |
| b12 | - | - | - | - | - | - | - | - |
| s386 | - | - | - | - | - | - | - | - |
| cht | - | - | - | - | - | - | - | - |
| f51m | - | - | - | - | - | - | - | - |
| s526 | - | - | - | - | - | - | - | - |
| opus | - | - | - | - | - | - | - | - |
| frg1 | - | - | - | - | - | - | - | - |
| misex2 | - | - | - | - | - | - | - | - |
| unreg | - | - | - | - | - | - | - | - |
| my-adder | - | - | - | - | - | - | - | - |
| s420.1 | - | - | - | - | - | - | - | - |
| b9 | - | - | - | - | - | - | - | - |
| i3 | - | - | - | - | - | - | - | - |
| o64 | - | - | - | - | - | - | - | - |
| dk14 | - | - | - | - | - | - | - | - |
| comp | - | - | - | - | - | - | - | - |
| c8 | - | - | - | - | - | - | - | - |
| count | - | - | - | - | - | - | - | - |
| ldd | - | - | - | - | - | - | - | - |
| ex4 | - | - | - | - | - | - | - | - |
| pcler8 | - | - | - | - | - | - | - | - |
| traffic | - | - | - | - | - | - | - | - |
| lal | - | - | - | - | - | - | - | - |
| mark1 | - | - | - | - | - | - | - | - |
| squar5 | - | - | - | - | - | - | - | - |
| bbara | - | - | - | - | - | - | - | - |
| mult16b | - | - | - | - | - | - | - | - |
| sqrt8ml | - | - | - | - | - | - | - | - |
| sqrt8 | - | - | - | - | - | - | - | - |
| cc | - | - | - | - | - | - | - | - |
| dk15 | - | - | - | - | - | - | - | - |
| s208.1 | - | - | - | - | - | - | - | - |
| s420 | - | - | - | - | - | - | - | - |
| sct | - | - | - | - | - | - | - | - |
| cu | - | - | - | - | - | - | - | - |
| i1 | - | - | - | - | - | - | - | - |
| misex1 | - | - | - | - | - | - | - | - |
| pcle | - | - | - | - | - | - | - | - |
| decod | - | - | - | - | - | - | - | - |
| pm1 | - | - | - | - | - | - | - | - |
| cm162a | - | - | - | - | - | - | - | - |
| s208 | - | - | - | - | - | - | - | - |
| cmb | - | - | - | - | - | - | - | - |
| x2 | - | - | - | - | - | - | - | - |
| tcon | - | - | - | - | - | - | - | - |
| dk17 | - | - | - | - | - | - | - | - |
| mux | - | - | - | - | - | - | - | - |
| beecount | - | - | - | - | - | - | - | - |
| cm150a | - | - | - | - | - | - | - | - |
| dk512 | - | - | - | - | - | - | - | - |
| rd53 | - | - | - | - | - | - | - | - |
| cm163a | - | - | - | - | - | - | - | - |
| cm85a | - | - | - | - | - | - | - | - |
| cm138a | - | - | - | - | - | - | - | - |
| cm42a | - | - | - | - | - | - | - | - |
| tav | - | - | - | - | - | - | - | - |
| cm151a | - | - | - | - | - | - | - | - |
| z4ml | - | - | - | - | - | - | - | - |
| mc | - | - | - | - | - | - | - | - |
| bbtas | - | - | - | - | - | - | - | - |
| cm152a | - | - | - | - | - | - | - | - |
| s27 | - | - | - | - | - | - | - | - |
| con1 | - | - | - | - | - | - | - | - |
| dk27 | - | - | - | - | - | - | - | - |
| parity | - | - | - | - | - | - | - | - |
| b1 | - | - | - | - | - | - | - | - |
| cm82a | - | - | - | - | - | - | - | - |
| daio | - | - | - | - | - | - | - | - |
| lion | - | - | - | - | - | - | - | - |
| majority | - | - | - | - | - | - | - | - |
| C17 | - | - | - | - | - | - | - | - |
| xor5 | - | - | - | - | - | - | - | - |
| chain_cout_fanout | - | - | - | - | - | - | - | - |
| shiftreg | - | - | - | - | - | - | - | - |

</details>

<details><summary>Silicon</summary>

| design | cells | core um2 | LVS | Si stage |
|---|---|---|---|---|
| clma | - | - | - | - |
| s38584.1 | - | - | - | - |
| s38417 | - | - | - | - |
| ex1010 | - | - | - | - |
| pdc | - | - | - | - |
| spla | - | - | - | - |
| elliptic | - | - | - | - |
| frisc | - | - | - | - |
| ex1010 | - | - | - | - |
| s38584.1 | - | - | - | - |
| s38417 | - | - | - | - |
| pdc | - | - | - | - |
| s298 | - | - | - | - |
| apex2 | - | - | - | - |
| seq | - | - | - | - |
| bigkey | - | - | - | - |
| frisc | - | - | - | - |
| des | - | - | - | - |
| alu4 | - | - | - | - |
| diffeq | - | - | - | - |
| elliptic | - | - | - | - |
| spla | - | - | - | - |
| misex3 | - | - | - | - |
| dsip | - | - | - | - |
| apex4 | - | - | - | - |
| ex5p | - | - | - | - |
| tseng | - | - | - | - |
| i10 | - | - | - | - |
| apex2 | - | - | - | - |
| des | - | - | - | - |
| apex3 | - | - | - | - |
| apex4 | - | - | - | - |
| seq | - | - | - | - |
| alu4 | - | - | - | - |
| cps | - | - | - | - |
| C7552 | - | - | - | - |
| misex3 | - | - | - | - |
| apex1 | - | - | - | - |
| dsip | - | - | - | - |
| s298 | - | - | - | - |
| parker1986 | - | - | - | - |
| pair | - | - | - | - |
| C5315 | - | - | - | - |
| diffeq | - | - | - | - |
| bigkey | - | - | - | - |
| s5378 | - | - | - | - |
| misex3c | - | - | - | - |
| apex5 | - | - | - | - |
| C6288 | - | - | - | - |
| k2 | - | - | - | - |
| dalu | - | - | - | - |
| table5 | - | - | - | - |
| i8 | - | - | - | - |
| table3 | - | - | - | - |
| ex5p | - | - | - | - |
| mm30a | - | - | - | - |
| cordic | - | - | - | - |
| s9234.1 | - | - | - | - |
| clma | - | - | - | - |
| ex4p | - | - | - | - |
| C3540 | - | - | - | - |
| scf | - | - | - | - |
| tseng | - | - | - | - |
| bbrtas | - | - | - | - |
| apex6 | - | - | - | - |
| sbc | - | - | - | - |
| frg2 | - | - | - | - |
| x3 | - | - | - | - |
| i9 | - | - | - | - |
| ecc | - | - | - | - |
| daio-rec | - | - | - | - |
| rot | - | - | - | - |
| s1488 | - | - | - | - |
| s1238 | - | - | - | - |
| s1494 | - | - | - | - |
| vda | - | - | - | - |
| e64 | - | - | - | - |
| planet | - | - | - | - |
| planet1 | - | - | - | - |
| s1196 | - | - | - | - |
| C2670 | - | - | - | - |
| duke2 | - | - | - | - |
| sand | - | - | - | - |
| styr | - | - | - | - |
| s1423 | - | - | - | - |
| ph-decod | - | - | - | - |
| gcd | - | - | - | - |
| s953 | - | - | - | - |
| t481 | - | - | - | - |
| mm9b | - | - | - | - |
| i7 | - | - | - | - |
| alu2 | - | - | - | - |
| s1 | - | - | - | - |
| x4 | - | - | - | - |
| too-lrg | - | - | - | - |
| i6 | - | - | - | - |
| C880 | - | - | - | - |
| s838 | - | - | - | - |
| rd84 | - | - | - | - |
| C1908 | - | - | - | - |
| s832 | - | - | - | - |
| 9sym | - | - | - | - |
| x1 | - | - | - | - |
| mm9a | - | - | - | - |
| clip | - | - | - | - |
| example2 | - | - | - | - |
| bw | - | - | - | - |
| C432 | - | - | - | - |
| ex1 | - | - | - | - |
| s820 | - | - | - | - |
| mult32a | - | - | - | - |
| dk16 | - | - | - | - |
| keyb | - | - | - | - |
| apex7 | - | - | - | - |
| s510 | - | - | - | - |
| i4 | - | - | - | - |
| 9symml | - | - | - | - |
| s838.1 | - | - | - | - |
| cse | - | - | - | - |
| sao2 | - | - | - | - |
| i5 | - | - | - | - |
| s713 | - | - | - | - |
| term1 | - | - | - | - |
| s641 | - | - | - | - |
| pma | - | - | - | - |
| tbk | - | - | - | - |
| rd73 | - | - | - | - |
| mm4a | - | - | - | - |
| ttt2 | - | - | - | - |
| C1355 | - | - | - | - |
| C499 | - | - | - | - |
| i2 | - | - | - | - |
| s400 | - | - | - | - |
| s344 | - | - | - | - |
| s349 | - | - | - | - |
| vg2 | - | - | - | - |
| bbsse | - | - | - | - |
| inc | - | - | - | - |
| sse | - | - | - | - |
| s444 | - | - | - | - |
| ex6 | - | - | - | - |
| s382 | - | - | - | - |
| s526n | - | - | - | - |
| 5xp1 | - | - | - | - |
| mult16a | - | - | - | - |
| b12 | - | - | - | - |
| s386 | - | - | - | - |
| cht | - | - | - | - |
| f51m | - | - | - | - |
| s526 | - | - | - | - |
| opus | - | - | - | - |
| frg1 | - | - | - | - |
| misex2 | - | - | - | - |
| unreg | - | - | - | - |
| my-adder | - | - | - | - |
| s420.1 | - | - | - | - |
| b9 | - | - | - | - |
| i3 | - | - | - | - |
| o64 | - | - | - | - |
| dk14 | - | - | - | - |
| comp | - | - | - | - |
| c8 | - | - | - | - |
| count | - | - | - | - |
| ldd | - | - | - | - |
| ex4 | - | - | - | - |
| pcler8 | - | - | - | - |
| traffic | - | - | - | - |
| lal | - | - | - | - |
| mark1 | - | - | - | - |
| squar5 | - | - | - | - |
| bbara | - | - | - | - |
| mult16b | - | - | - | - |
| sqrt8ml | - | - | - | - |
| sqrt8 | - | - | - | - |
| cc | - | - | - | - |
| dk15 | - | - | - | - |
| s208.1 | - | - | - | - |
| s420 | - | - | - | - |
| sct | - | - | - | - |
| cu | - | - | - | - |
| i1 | - | - | - | - |
| misex1 | - | - | - | - |
| pcle | - | - | - | - |
| decod | - | - | - | - |
| pm1 | - | - | - | - |
| cm162a | - | - | - | - |
| s208 | - | - | - | - |
| cmb | - | - | - | - |
| x2 | - | - | - | - |
| tcon | - | - | - | - |
| dk17 | - | - | - | - |
| mux | - | - | - | - |
| beecount | - | - | - | - |
| cm150a | - | - | - | - |
| dk512 | - | - | - | - |
| rd53 | - | - | - | - |
| cm163a | - | - | - | - |
| cm85a | - | - | - | - |
| cm138a | - | - | - | - |
| cm42a | - | - | - | - |
| tav | - | - | - | - |
| cm151a | - | - | - | - |
| z4ml | - | - | - | - |
| mc | - | - | - | - |
| bbtas | - | - | - | - |
| cm152a | - | - | - | - |
| s27 | - | - | - | - |
| con1 | - | - | - | - |
| dk27 | - | - | - | - |
| parity | - | - | - | - |
| b1 | - | - | - | - |
| cm82a | - | - | - | - |
| daio | - | - | - | - |
| lion | - | - | - | - |
| majority | - | - | - | - |
| C17 | - | - | - | - |
| xor5 | - | - | - | - |
| chain_cout_fanout | - | - | - | - |
| shiftreg | - | - | - | - |

</details>

</details>

<a id="sources"></a>

### Sources

- **brisc-v**: BRISC-V microcontroller (Arduino-on-RISC-V, Quartus project revert_timer). Upstream https://github.com/qiany21/Arduino-on-RISC-V.git at 1d5b591081511a8161b843d003ca7b80bad7fc45. Licence: MIT (Copyright (c) 2021 qiany21).
- **itc99**: ITC'99 (RTL Verilog, b01-b22 without b16). Upstream https://github.com/ccsl-uaegean/ITC99-RTL-Verilog at 8e6a23da036b7442ef4ea410c679d4cf21830a65. Licence: GPL-3.0 (the LICENSE file of this repository); the terms of the original ITC'99 distribution were not read.
- **mcnc20**: MCNC / LGSynth91 circuits as VTR ships them (4-LUT mapped BLIF, circuits.txt). Upstream https://github.com/verilog-to-routing/vtr-verilog-to-routing at 3c9a4d23b27d187bd67c79dc01a18ff1ffc21d9b. Licence: none-stated (data/meta/licences.toml rule mcnc); VTR LICENSE.md: MIT unless otherwise noted, in particular the benchmark circuits.
- **verilogeval**: VerilogEval problems (reference solutions of the spec-to-rtl dataset) with the Gate-Breaker Yosys netlists. Upstream https://github.com/NMSU-PEARL/verilog-eval.git at d60f0b10458746e2fefc2a98fa2455b77a32e8be. Licence: MIT (Copyright (c) 2023-2024 NVIDIA Research Projects).
- **vtr-blif**: VTR blif/2 and blif/4: ISCAS-85, ISCAS-89 and MCNC mapped to 2-input and 4-input LUTs. Upstream https://github.com/verilog-to-routing/vtr-verilog-to-routing at 3c9a4d23b27d187bd67c79dc01a18ff1ffc21d9b. Licence: not read: the licence of the individual ISCAS/MCNC files has not been checked.
- **vtr-verilog**: VTR Verilog benchmarks (top-level files of vtr_flow/benchmarks/verilog). Upstream https://github.com/verilog-to-routing/vtr-verilog-to-routing at 3c9a4d23b27d187bd67c79dc01a18ff1ffc21d9b. Licence: per design, as each file states (see licence_rule in designs.tsv and data/meta/licences.toml); VTR LICENSE.md: MIT unless otherwise noted, in particular the benchmark circuits.

Sortable, filterable single-table page: [catalogue.html](https://drpaj12.github.io/mimirIII/benchmarks/catalogue.html) (GitHub Pages; the file is docs/benchmarks/catalogue.html). Same tables: [docs/benchmarks/catalogue.md](docs/benchmarks/catalogue.md); method: [docs/benchmarks/catalogue-method.md](docs/benchmarks/catalogue-method.md).
<!-- catalogue:end -->
