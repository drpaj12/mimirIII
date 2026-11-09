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

One row per registered design, in tiers: best first (HDL with testbench and the whole flow), down to BLIF netlists only; each tier states its rule. `✓` yes, `✗` no (both measured), `-` not run, `n/a` does not apply, `fail: ...` the tool failed. Every value is in `data/benchmarks/measures.tsv` with its source; the rules are in `docs/benchmarks/catalogue-method.md`. The `vtr-blif-k2` and `vtr-blif-k4` suites hold the same circuits: one row per circuit name present in either. `status` = `provisional` marks a row whose values were not all re-measured with the 2026-11-05 Odin III main binary; the text after it says what produced them.

| tier | rule | designs |
|---|---|---|
| T0 whole flow | HDL with its own testbench, 200+ Verilog lines, the testbench passes in iverilog (`sim_iverilog`=1) and in Odin III simulation (`sim_odin`=1), and the VTR flow reaches `route` with timing (`vtr_stage`) | 0 |
| T1 HDL + testbench, larger | HDL with a testbench and 200+ Verilog lines (and not T0) | 25 |
| T2 HDL + testbench, small | HDL with a testbench and under 200 Verilog lines | 156 |
| T3 HDL, no testbench | HDL (Verilog) with no testbench file | 55 |
| T4 netlist only | BLIF netlist, no HDL | 219 |

| suite | designs |
|---|---|
| brisc-v | 1 |
| itc99 | 21 |
| mcnc20 | 20 |
| opencores | 27 |
| verilogeval | 156 |
| vtr-blif | 199 |
| vtr-verilog | 31 |
| total | 455 |

<details><summary>T1 HDL + testbench, larger (25 designs)</summary>

Rule: HDL with a testbench and 200+ Verilog lines (and not T0).

| design | what it does | suite | link | view | licence | LOC | tb | vec |
|---|---|---|---|---|---|---|---|---|
| dblclockfft | Double Clocked FFT Core | [opencores](#sources) | [repo](https://opencores.org/projects) | [view](https://drpeterjamieson.com/RESEARCH/HEIMDALL/opencores-dblclockfft/) | per project | 3790 | ✓ | ✗ |
| vga_lcd | VGA/LCD Controller | [opencores](#sources) | [repo](https://opencores.org/projects) | [view](https://drpeterjamieson.com/RESEARCH/HEIMDALL/opencores-vga_lcd/) | per project | 4900 | ✓ | ✗ |
| ethmac | Ethernet MAC 10/100 | [opencores](#sources) | [repo](https://opencores.org/projects) | [view](https://drpeterjamieson.com/RESEARCH/HEIMDALL/opencores-ethmac/) | per project | 12270 | ✓ | ✗ |
| usbhostslave | USB 1.1 Host and Function IP core | [opencores](#sources) | [repo](https://opencores.org/projects) | [view](https://drpeterjamieson.com/RESEARCH/HEIMDALL/opencores-usbhostslave/) | per project | 12433 | ✓ | ✗ |
| sha3_high | SHA-3 (Keccak) high-throughput core, two rounds per cycle | [opencores](#sources) | [repo](https://opencores.org/projects) | [view](https://drpeterjamieson.com/RESEARCH/HEIMDALL/opencores-sha3_high/) | per project | 618 | ✓ | ✗ |
| sha3_low | SHA-3 (Keccak) low-throughput core | [opencores](#sources) | [repo](https://opencores.org/projects) | [view](https://drpeterjamieson.com/RESEARCH/HEIMDALL/opencores-sha3_low/) | per project | 499 | ✓ | ✗ |
| reed_solomon_decoder | Reed Solomon Decoder (204,188) | [opencores](#sources) | [repo](https://opencores.org/projects) | [view](https://drpeterjamieson.com/RESEARCH/HEIMDALL/opencores-reed_solomon_decoder/) | per project | 4366 | ✓ | ✗ |
| a-z80-modified | A-Z80 CPU (modified: mux-driven internal data bus, no tri-state) | [opencores](#sources) | [repo](https://opencores.org/projects) | - | per project | 5649 | ✓ | ✗ |
| des | DES/Triple DES IP Cores | [opencores](#sources) | [repo](https://opencores.org/projects) | [view](https://drpeterjamieson.com/RESEARCH/HEIMDALL/opencores-des/) | per project | 2061 | ✓ | ✗ |
| sdr_ctrl | SDRAM controller (32-bit configuration read) | [opencores](#sources) | [repo](https://opencores.org/projects) | [view](https://drpeterjamieson.com/RESEARCH/HEIMDALL/opencores-sdr_ctrl/) | per project | 3929 | ✓ | ✗ |
| verilog_cordic_core | configurable CORDIC core in Verilog (first quadrant) | [opencores](#sources) | [repo](https://opencores.org/projects) | [view](https://drpeterjamieson.com/RESEARCH/HEIMDALL/opencores-verilog_cordic_core/) | per project | 379 | ✓ | ✗ |
| wb_lcd | WB LCD Character Display Controller | [opencores](#sources) | [repo](https://opencores.org/projects) | [view](https://drpeterjamieson.com/RESEARCH/HEIMDALL/opencores-wb_lcd/) | per project | 695 | ✓ | ✗ |
| uart2spi | UART to SPI bridge (flash commands over a UART) | [opencores](#sources) | [repo](https://opencores.org/projects) | [view](https://drpeterjamieson.com/RESEARCH/HEIMDALL/opencores-uart2spi/) | per project | 2583 | ✓ | ✗ |
| mips_16_noxarm | Educational 16-bit MIPS Processor (variant without the ALU_NC x arm) | [opencores](#sources) | [repo](https://opencores.org/projects) | [view](https://drpeterjamieson.com/RESEARCH/HEIMDALL/opencores-mips_16_noxarm/) | per project | 945 | ✓ | ✗ |
| spi | SPI core, Wishbone master | [opencores](#sources) | [repo](https://opencores.org/projects) | [view](https://drpeterjamieson.com/RESEARCH/HEIMDALL/opencores-spi/) | per project | 633 | ✓ | ✗ |
| i2c | I2C core, Wishbone master | [opencores](#sources) | [repo](https://opencores.org/projects) | [view](https://drpeterjamieson.com/RESEARCH/HEIMDALL/opencores-i2c/) | per project | 1556 | ✓ | ✗ |
| sdram_16bit | 16-bit SDRAM Controller | [opencores](#sources) | [repo](https://opencores.org/projects) | [view](https://drpeterjamieson.com/RESEARCH/HEIMDALL/opencores-sdram_16bit/) | per project | 741 | ✓ | ✗ |
| i2cslave | I2C Slave | [opencores](#sources) | [repo](https://opencores.org/projects) | [view](https://drpeterjamieson.com/RESEARCH/HEIMDALL/opencores-i2cslave/) | per project | 769 | ✓ | ✗ |
| simple_spi | SPI core | [opencores](#sources) | [repo](https://opencores.org/projects) | [view](https://drpeterjamieson.com/RESEARCH/HEIMDALL/opencores-simple_spi/) | per project | 456 | ✓ | ✗ |
| ca_prng | Cellular Automata PRNG | [opencores](#sources) | [repo](https://opencores.org/projects) | [view](https://drpeterjamieson.com/RESEARCH/HEIMDALL/opencores-ca_prng/) | per project | 1311 | ✓ | ✗ |
| mmuart | Simple RS232 UART | [opencores](#sources) | [repo](https://opencores.org/projects) | [view](https://drpeterjamieson.com/RESEARCH/HEIMDALL/opencores-mmuart/) | per project | 253 | ✓ | ✗ |
| mips_16 | Educational 16-bit MIPS Processor | [opencores](#sources) | [repo](https://opencores.org/projects) | [view](https://drpeterjamieson.com/RESEARCH/HEIMDALL/opencores-mips_16/) | per project | 945 | ✓ | ✗ |
| quartus_project_revert_timer | BRISC-V microcontroller (Arduino-on-RISC-V) | [brisc-v](#sources) | [repo](https://github.com/qiany21/Arduino-on-RISC-V.git) | - | MIT | 4349 | ✓ | ✓ |
| pipelined_fft_256 | 256-point pipelined FFT/IFFT | [opencores](#sources) | [repo](https://opencores.org/projects) | [view](https://drpeterjamieson.com/RESEARCH/HEIMDALL/opencores-pipelined_fft_256/) | per project | 2055 | ✓ | ✗ |
| tiny_aes | AES | [opencores](#sources) | [repo](https://opencores.org/projects) | - | per project | 764 | ✓ | ✗ |

<details><summary>Flow and VTR QoR</summary>

| design | iverilog | Odin sim | VTR stage | LUTs | blocks | FFs | pins | mult/mem | cpd ns | chan w | status | note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dblclockfft | pass | fail | timing | 43969 | 4009 | 30280 | 76 | 0/59 | 5.19941 | 72 | sim re-run 2026-11-05; VTR provisional (rel-main2) | sim_odin: parses and elaborates, did not finish within the sim time limit |
| vga_lcd | pass | refused | timing | 24862 | 2023 | 16529 | 4 | 0/32 | 8.47413 | 58 | sim re-run 2026-11-05; VTR provisional (rel-main2) | sim_odin: test_bench_top.v:558: unsupported: real number |
| ethmac | fail | refused | timing | 16463 | 1172 | 10543 | 66 | 0/0 | 7.71791 | 62 | sim re-run 2026-11-05; VTR provisional (rel-main2) | sim_odin: tb_ethernet.v:1071: unsupported: x/z literal (the simulator is 2-state) |
| usbhostslave | pass | refused | timing | 10498 | 877 | 7079 | 51 | 0/0 | 5.49712 | 50 | sim re-run 2026-11-05; VTR provisional (rel-main2) | sim_odin: sepHostSlaveTestHarness.v:60: unsupported: x/z literal (the simulator is 2-state) |
| sha3_high | pass | refused | timing | 7824 | 763 | 2211 | 585 | 0/0 | 9.22457 | 148 | sim re-run 2026-11-05; VTR provisional (rel-main2) | sim_odin: test_keccak.v:32: unsupported: signal wider than 64 bits |
| sha3_low | pass | refused | timing | 5035 | 463 | 2244 | 552 | 0/0 | 4.44096 | 114 | sim re-run 2026-11-05; VTR provisional (rel-main2) | sim_odin: test_keccak.v:32: unsupported: signal wider than 64 bits |
| reed_solomon_decoder | pass | fail | timing | 4690 | 526 | 2882 | 21 | 0/120 | 6.14868 | 64 | sim re-run 2026-11-05; VTR provisional (rel-main2) | sim_odin: parses and elaborates, did not finish within the sim time limit |
| a-z80-modified | pass | none | timing | 2016 | 193 | 365 | 48 | 0/0 | 11.3704 | 68 | 2026-11-08 (rel-v150) | modified: mux-driven internal data bus; bidirectional nets split into one-way signals, D split into D_in/D_out/D_oe, pins_oe exported; every changed line commented; matches upstream a-z80 under iverilog on 5 programs |
| des | pass | refused | timing | 1877 | 222 | 1984 | - | 0/0 | 3.70378 | 54 | sim re-run 2026-11-05; VTR provisional (rel-main2) | sim_odin: des_test_po.v:426: unsupported: x/z literal (the simulator is 2-state) |
| sdr_ctrl | pass | refused | timing | 1710 | 170 | 1130 | 8 | 0/0 | 5.57435 | 50 | re-run 2026-11-05 (VTR, sim) | tri-state pass converts sdr_dq (split _i/_o/_oe); sim_odin: tb_top.sv:105: unsupported: real number |
| verilog_cordic_core | pass | pass | timing | 1153 | 133 | 765 | 104 | 0/0 | 4.1275 | 54 | sim re-run 2026-11-05; VTR provisional (rel-main2) | - |
| wb_lcd | pass | pass | timing | 1049 | 77 | 636 | 66 | 0/0 | 4.29499 | 48 | sim re-run 2026-11-05; VTR provisional (rel-main2) | - |
| uart2spi | - | refused | timing | 685 | 67 | 422 | 22 | 0/0 | 3.30854 | 36 | re-run 2026-11-05 (VTR, sim) | upstream bench (upstream-fixed) with flash model; sim_odin: tb_top.v:51: unsupported: real number |
| mips_16_noxarm | - | - | timing | 639 | 54 | 247 | 68 | 0/0 | 5.72277 | 42 | re-run 2026-11-05 (VTR) | mips_16 variant without the ALU_NC x arm; datapath no longer folds; no testbench run on the variant |
| spi | pass | refused | timing | 612 | 61 | 229 | 71 | 0/0 | 6.56467 | 46 | sim re-run 2026-11-05; VTR provisional (rel-main2) | sim_odin: tb_spi_top.v:417: unsupported: x/z literal (the simulator is 2-state) |
| i2c | pass | refused | timing | 316 | 31 | 200 | 22 | 0/0 | 2.80648 | 36 | sim re-run 2026-11-05; VTR provisional (rel-main2) | sim_odin: tst_bench_top.v:194: unsupported: x/z literal (the simulator is 2-state) |
| sdram_16bit | pass | fail | timing | 281 | 24 | 182 | 130 | 0/0 | 4.01425 | 44 | re-run 2026-11-05 (VTR, sim) | --vendor-prims: IOBUF/ODDR2 built as soft logic, data_io split to _i/_o/_oe; VPR done. sim_odin: simulation.svh:19:37: error: syntax: '`__FILE__' is a SystemVerilog macro operator; not Verilog-2005 (Phase 5) |
| i2cslave | fail | refused | timing | 198 | 18 | 139 | 11 | 0/0 | 2.21504 | 32 | re-run 2026-11-05 (VTR, sim) | tri-state pass converts sda; iverilog testbench fails (timeout); sim_odin: testHarness.v:89: unsupported: x/z literal (the simulator is 2-state) |
| simple_spi | pass | refused | timing | 189 | 19 | 131 | 27 | 0/0 | 2.37109 | 30 | sim re-run 2026-11-05; VTR provisional (rel-main2) | sim_odin: tst_bench_top.v:305: unsupported: x/z literal (the simulator is 2-state) |
| ca_prng | pass | refused | timing | 158 | 16 | 40 | 77 | 0/0 | 2.38342 | 34 | sim re-run 2026-11-05; VTR provisional (rel-main2) | sim_odin: tb_ca_prng.v:147: unsupported: task |
| mmuart | pass | pass | timing | 126 | 14 | 96 | 83 | 0/0 | 2.31268 | 36 | sim re-run 2026-11-05; VTR provisional (rel-main2) | - |
| mips_16 | pass | refused | timing | 71 | 7 | 36 | 68 | 0/0 | 4.03484 | 26 | sim re-run 2026-11-05; VTR provisional (rel-main2) | 71 LUTs: ALU_NC 3'bxxx first arm is a wildcard so the datapath folds (Odin III matches Yosys/Parmys); see mips_16_noxarm |
| quartus_project_revert_timer | - | - | - | - | - | - | - | - | - | - | - | - |
| pipelined_fft_256 | pass | fail | none | - | - | - | - | - | - | - | sim re-run 2026-11-05; VTR provisional (rel-main2) | VTR: odin3_ast_comment_add: end is not 0 or a later loc of loc's buffer; sim_odin: odin3_ast_comment_add: end is not 0 or a later loc of loc's buffer |
| tiny_aes | pass | refused | elab | - | - | - | - | - | - | - | sim re-run 2026-11-05; VTR provisional (rel-main2) | VTR: abc needs more than 6442450944 bytes (the design's budget is 6442450944 bytes: the smaller of 60% of physical ; sim_odin: test_aes_128.v:23: unsupported: signal wider than 64 bits; too big for now (6 GB abc budget) |

</details>

<details><summary>LUT forms</summary>

| design | gates/d | 4-LUT/d | 6-LUT/d |
|---|---|---|---|
| dblclockfft | - | - | - |
| vga_lcd | - | - | - |
| ethmac | - | - | - |
| usbhostslave | - | - | - |
| sha3_high | - | - | - |
| sha3_low | - | - | - |
| reed_solomon_decoder | - | - | - |
| a-z80-modified | - | - | - |
| des | - | - | - |
| sdr_ctrl | - | - | - |
| verilog_cordic_core | - | - | - |
| wb_lcd | - | - | - |
| uart2spi | - | - | - |
| mips_16_noxarm | - | - | - |
| spi | - | - | - |
| i2c | - | - | - |
| sdram_16bit | - | - | - |
| i2cslave | - | - | - |
| simple_spi | - | - | - |
| ca_prng | - | - | - |
| mmuart | - | - | - |
| mips_16 | - | - | - |
| quartus_project_revert_timer | fail: too big for now (timeout 900 s, last finished pass levelize)/fail: too big for now (timeout 900 s, last finished pass levelize) | fail: too big for now (timeout 900 s, last finished pass levelize)/fail: too big for now (timeout 900 s, last finished pass levelize) | fail: too big for now (timeout 900 s, last finished pass levelize)/fail: too big for now (timeout 900 s, last finished pass levelize) |
| pipelined_fft_256 | - | - | - |
| tiny_aes | - | - | - |

</details>

<details><summary>Properties</summary>

| design | seq | mem | mul | add | fsm | latch | hier | bbox |
|---|---|---|---|---|---|---|---|---|
| dblclockfft | - | - | - | - | - | - | - | - |
| vga_lcd | - | - | - | - | - | - | - | - |
| ethmac | - | - | - | - | - | - | - | - |
| usbhostslave | - | - | - | - | - | - | - | - |
| sha3_high | - | - | - | - | - | - | - | - |
| sha3_low | - | - | - | - | - | - | - | - |
| reed_solomon_decoder | - | - | - | - | - | - | - | - |
| a-z80-modified | - | - | - | - | - | - | - | - |
| des | - | - | - | - | - | - | - | - |
| sdr_ctrl | - | - | - | - | - | - | - | - |
| verilog_cordic_core | - | - | - | - | - | - | - | - |
| wb_lcd | - | - | - | - | - | - | - | - |
| uart2spi | - | - | - | - | - | - | - | - |
| mips_16_noxarm | - | - | - | - | - | - | - | - |
| spi | - | - | - | - | - | - | - | - |
| i2c | - | - | - | - | - | - | - | - |
| sdram_16bit | - | - | - | - | - | - | - | - |
| i2cslave | - | - | - | - | - | - | - | - |
| simple_spi | - | - | - | - | - | - | - | - |
| ca_prng | - | - | - | - | - | - | - | - |
| mmuart | - | - | - | - | - | - | - | - |
| mips_16 | - | - | - | - | - | - | - | - |
| quartus_project_revert_timer | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✓ |
| pipelined_fft_256 | - | - | - | - | - | - | - | - |
| tiny_aes | - | - | - | - | - | - | - | - |

</details>

<details><summary>Silicon</summary>

| design | cells | core um2 | LVS | Si stage |
|---|---|---|---|---|
| dblclockfft | - | - | - | - |
| vga_lcd | - | - | - | - |
| ethmac | - | - | - | - |
| usbhostslave | - | - | - | - |
| sha3_high | - | - | - | - |
| sha3_low | running | running | running | running |
| reed_solomon_decoder | - | - | - | - |
| a-z80-modified | - | - | - | - |
| des | 26124 | 516945.8 | match | lvs |
| sdr_ctrl | - | - | - | - |
| verilog_cordic_core | 10158 | 188396.9 | match | lvs |
| wb_lcd | 4428 | 98994.9 | match | lvs |
| uart2spi | - | - | - | - |
| mips_16_noxarm | - | - | - | - |
| spi | - | - | - | - |
| i2c | 1397 | 30669.4 | match | lvs |
| sdram_16bit | - | - | - | - |
| i2cslave | - | - | - | - |
| simple_spi | 974 | 20364.5 | match | lvs |
| ca_prng | - | - | - | - |
| mmuart | 681 | 14589.0 | match | lvs |
| mips_16 | - | - | - | - |
| quartus_project_revert_timer | - | - | - | - |
| pipelined_fft_256 | - | - | - | - |
| tiny_aes | - | - | - | - |

</details>

<details><summary>Power</summary>

| design | activity | FPGA pJ/cycle | ASIC pJ/cycle | FPGA MHz | power note |
|---|---|---|---|---|---|
| dblclockfft | ace2 | 3355 | - | 194.4 | matched 0.715; ACE2 vectorless, primary inputs p=0.5 activity=0.2 |
| vga_lcd | - | - | - | - | - |
| ethmac | - | - | - | - | - |
| usbhostslave | ace2 | 245.8 | - | 195.9 | matched 0.627; ACE2 vectorless, primary inputs p=0.5 activity=0.2 |
| sha3_high | - | - | - | - | - |
| sha3_low | - | - | - | - | - |
| reed_solomon_decoder | ace2 | 383.6 | - | 181.8 | matched 0.731; ACE2 vectorless, primary inputs p=0.5 activity=0.2 |
| a-z80-modified | - | - | - | - | - |
| des | ace2 | 211.9 | - | 266.1 | matched 0.871; ACE2 vectorless, primary inputs p=0.5 activity=0.2 |
| sdr_ctrl | ace2 | 74.81 | - | 167.2 | matched 0.698; ACE2 vectorless, primary inputs p=0.5 activity=0.2 |
| verilog_cordic_core | iverilog-gate | 126.9 | 72.5 | 228.3 | matched 1.000; 220 testbench cycles; ASIC sky130 tt 1.8 V at 100 MHz |
| wb_lcd | iverilog-gate | 19.35 | 35.8 | 269.3 | matched 1.000; 1295076 testbench cycles; ASIC sky130 tt 1.8 V at 50 MHz |
| uart2spi | ace2 | 22.81 | - | 313.4 | matched 0.687; ACE2 vectorless, primary inputs p=0.5 activity=0.2 |
| mips_16_noxarm | ace2 | 26.02 | - | 177.4 | matched 0.736; ACE2 vectorless, primary inputs p=0.5 activity=0.2 |
| spi | ace2 | 31.11 | - | 151.8 | matched 0.770; ACE2 vectorless, primary inputs p=0.5 activity=0.2 |
| i2c | ace2 | 12.54 | - | 354.5 | matched 0.679; ACE2 vectorless, primary inputs p=0.5 activity=0.2 |
| sdram_16bit | ace2 | 14.92 | - | 255.5 | matched 0.710; ACE2 vectorless, primary inputs p=0.5 activity=0.2 |
| i2cslave | ace2 | 4.717 | - | 424.6 | matched 0.627; ACE2 vectorless, primary inputs p=0.5 activity=0.2 |
| simple_spi | ace2 | 5.936 | - | 403.6 | matched 0.678; ACE2 vectorless, primary inputs p=0.5 activity=0.2 |
| ca_prng | ace2 | 9.149 | - | 444.8 | matched 0.835; ACE2 vectorless, primary inputs p=0.5 activity=0.2 |
| mmuart | iverilog-gate | 4.713 | 5.14 | 438.4 | matched 1.000; 94433 testbench cycles; ASIC sky130 tt 1.8 V at 100 MHz |
| mips_16 | ace2 | 4.934 | - | 248.7 | matched 0.787; ACE2 vectorless, primary inputs p=0.5 activity=0.2 |
| quartus_project_revert_timer | - | - | - | - | - |
| pipelined_fft_256 | ace2 | 530.5 | - | 145.8 | matched 0.729; ACE2 vectorless, primary inputs p=0.5 activity=0.2 |
| tiny_aes | - | - | - | - | - |

</details>

</details>

<details><summary>T2 HDL + testbench, small (156 designs)</summary>

Rule: HDL with a testbench and under 200 Verilog lines.

| design | what it does | suite | link | view | licence | LOC | tb | vec |
|---|---|---|---|---|---|---|---|---|
| Prob144_conwaylife | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 37 | ✓ | ✓ |
| Prob030_popcount255 | a population count circuit for a 255-bit input vector | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 14 | ✓ | ✓ |
| Prob153_gshare | a gshare branch predictor with 7-bit pc and 7-bit global history, hashed (using xor) into a 7-bit index | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 49 | ✓ | ✓ |
| Prob108_rule90 | Rule 90, a one-dimensional cellular automaton with interesting properties | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 18 | ✓ | ✓ |
| Prob124_rule110 | Rule 110, a one-dimensional cellular automaton with interesting properties (such as being Turing-complete) | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 22 | ✓ | ✓ |
| Prob021_mux256to1v | a 4-bit wide, 256-to-1 multiplexer | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 11 | ✓ | ✓ |
| Prob092_gatesv100 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 16 | ✓ | ✓ |
| Prob105_rotate100 | a 100-bit left/right rotator, with synchronous load and left/right enable | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 20 | ✓ | ✓ |
| Prob115_shift18 | a 64-bit arithmetic shift register, with synchronous load | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 24 | ✓ | ✓ |
| Prob018_mux256to1 | a 1-bit wide, 256-to-1 multiplexer | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 11 | ✓ | ✓ |
| Prob017_mux2to1v | a 2-1 multiplexer | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 12 | ✓ | ✓ |
| Prob097_mux9to1v | a 16-bit wide, 9-to-1 multiplexer | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 32 | ✓ | ✓ |
| Prob052_gates100 | a combinational circuit with 100 inputs, in[99:0] | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 14 | ✓ | ✓ |
| Prob055_conditional | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 18 | ✓ | ✓ |
| Prob141_count_clock | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | [view](https://drpeterjamieson.com/RESEARCH/HEIMDALL/verilogeval-Prob141_count_clock/) | MIT | 47 | ✓ | ✓ |
| Prob066_edgecapture | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 20 | ✓ | ✓ |
| Prob082_lfsr32 | a 32-bit Galois LFSR with taps at bit positions 32, 22, 2, and 1 | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 25 | ✓ | ✓ |
| Prob118_history_shift | a 32-bit global history shift register, including support for rolling back state in response to a pipeline flush caused by a branch misprediction | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 25 | ✓ | ✓ |
| Prob154_fsm_ps2data | a finite state machine that will search for message boundaries when given an input byte stream | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 42 | ✓ | ✓ |
| Prob068_countbcd | a 4-digit BCD (binary-coded decimal) counter | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 20 | ✓ | ✓ |
| Prob123_bugs_addsubz | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | [view](https://drpeterjamieson.com/RESEARCH/HEIMDALL/verilogeval-Prob123_bugs_addsubz/) | MIT | 19 | ✓ | ✓ |
| Prob043_vector5 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | [view](https://drpeterjamieson.com/RESEARCH/HEIMDALL/verilogeval-Prob043_vector5/) | MIT | 14 | ✓ | ✓ |
| Prob146_fsm_serialdata | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 46 | ✓ | ✓ |
| Prob080_timer | a timer that counts down for a given number of clock cycles, then asserts a signal to indicate that the given duration has elapsed | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 18 | ✓ | ✓ |
| Prob155_lemmings4 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 60 | ✓ | ✓ |
| Prob073_dff16e | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 22 | ✓ | ✓ |
| Prob126_circuit6 | a combinational circuit | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 20 | ✓ | ✓ |
| Prob037_review2015_count1k | a counter that counts from 0 to 999, inclusive, with a period of 1000 cycles | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 15 | ✓ | ✓ |
| Prob033_ece241_2014_q1c | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 14 | ✓ | ✓ |
| Prob114_bugs_case | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 31 | ✓ | ✓ |
| Prob143_fsm_onehot | the state transition logic and output logic portions of the state machine (but not the state flip-flops) | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 25 | ✓ | ✓ |
| Prob076_always_case | a 6-to-1 multiplexer | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 26 | ✓ | ✓ |
| Prob137_fsm_serial | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 38 | ✓ | ✓ |
| Prob084_ece241_2013_q12 | a circuit for an 8x1 memory, where writing to the memory is accomplished by shifting-in bits, and reading is "random access", as in a typical RAM | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 21 | ✓ | ✓ |
| Prob140_fsm_hdlc | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 37 | ✓ | ✓ |
| Prob149_ece241_2013_q4 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 46 | ✓ | ✓ |
| Prob044_vectorgates | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 15 | ✓ | ✓ |
| Prob094_gatesv | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 18 | ✓ | ✓ |
| Prob106_always_nolatches | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 21 | ✓ | ✓ |
| Prob046_dff8p | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 16 | ✓ | ✓ |
| Prob130_circuit5 | a combinational circuit | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 21 | ✓ | ✓ |
| Prob133_2014_q3fsm | a finite state machine with inputs s and w | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 35 | ✓ | ✓ |
| Prob139_2013_q2bfsm | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 38 | ✓ | ✓ |
| Prob041_dff8r | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 16 | ✓ | ✓ |
| Prob045_edgedetect2 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 16 | ✓ | ✓ |
| Prob047_dff8ar | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 16 | ✓ | ✓ |
| Prob054_edgedetect | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 16 | ✓ | ✓ |
| Prob062_bugs_mux2 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 13 | ✓ | ✓ |
| Prob087_gates | a combinational circuit with two inputs, a and b | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 23 | ✓ | ✓ |
| Prob136_m2014_q6 | the state machine shown below: A (0) --0--> B A (0) --1--> A B (0) --0--> C B (0) --1--> D C (0) --0--> E C (0) --1--> D D (0) --0--> F D (0) --1--> A E (1) --0--> E E (1) --1--> D F (1) --0--> C F (1) --1--> D Assume all sequential logic is triggered on the positive edge of the clock | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 33 | ✓ | ✓ |
| Prob138_2012_q2fsm | the state machine shown below: A (0) --1--> B A (0) --0--> A B (0) --1--> C B (0) --0--> D C (0) --1--> E C (0) --0--> D D (0) --1--> F D (0) --0--> A E (1) --1--> E E (1) --0--> D F (1) --1--> C F (1) --0--> D Reset resets into state A and is synchronous active-high | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 31 | ✓ | ✓ |
| Prob016_m2014_q4j | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | [view](https://drpeterjamieson.com/RESEARCH/HEIMDALL/verilogeval-Prob016_m2014_q4j/) | MIT | 11 | ✓ | ✓ |
| Prob121_2014_q3bfsm | a finite-state machine with the state-assigned table shown below | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 31 | ✓ | ✓ |
| Prob152_lemmings3 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 48 | ✓ | ✓ |
| Prob086_lfsr5 | a 5-bit maximal-length Galois LFSR with taps at bit positions 5 and 3 | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 23 | ✓ | ✓ |
| Prob096_review2015_fsmseq | a finite-state machine that searches for the sequence 1101 in an input bit stream | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 30 | ✓ | ✓ |
| Prob148_2013_q2afsm | the FSM described by the state diagram shown below: A --r0=0,r1=0,r2=0--> A A -------r0=1-------> B A -----r0=0,r1=1----> C A --r0=0,r1=0,r2=0--> D B (g0=1) -------r0=1-------> B B (g0=1) -------r0=0-------> A C (g1=1) -------r1=1-------> C C (g1=1) -------r1=0-------> A Resetn is an active-low synchronous reset that resets into state A | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 35 | ✓ | ✓ |
| Prob150_review2015_fsmonehot | the following Moore state machine with 3 input (d, done_counting, ack) and 3 outputs (shift_ena, counting, done) | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | [view](https://drpeterjamieson.com/RESEARCH/HEIMDALL/verilogeval-Prob150_review2015_fsmonehot/) | MIT | 30 | ✓ | ✓ |
| Prob035_count1to10 | a decade counter that counts 1 through 10, inclusive | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 15 | ✓ | ✓ |
| Prob038_count15 | a 4-bit binary counter that counts from 0 through 15, inclusive, with a period of 16 | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 15 | ✓ | ✓ |
| Prob040_count10 | a decade counter that counts from 0 through 9, inclusive, with a period of 10 | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 15 | ✓ | ✓ |
| Prob060_m2014_q4k | a shift register with four D flops | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 20 | ✓ | ✓ |
| Prob063_review2015_shiftcount | a four-bit shift register that also acts as a down counter | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 18 | ✓ | ✓ |
| Prob067_countslow | a decade counter that counts from 0 through 9, inclusive, with a period of 10 | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 20 | ✓ | ✓ |
| Prob079_fsm3onehot | the state transition table for a Moore state machine with one input, one output, and four states | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 19 | ✓ | ✓ |
| Prob085_shift4 | a 4-bit shift register (right shift), with asynchronous positive edge triggered areset, synchronous active high signals load, and enable | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | [view](https://drpeterjamieson.com/RESEARCH/HEIMDALL/verilogeval-Prob085_shift4/) | MIT | 21 | ✓ | ✓ |
| Prob095_review2015_fsmshift | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 29 | ✓ | ✓ |
| Prob120_fsm3s | a Moore state machine with the following state transition table with one input, one output, and four states | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 30 | ✓ | ✓ |
| Prob128_fsm_ps2 | a finite state machine that will search for message boundaries when given an input byte stream | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 32 | ✓ | ✓ |
| Prob142_lemmings2 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 36 | ✓ | ✓ |
| Prob051_gates4 | a combinational circuit with four inputs, in[3:0] | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 14 | ✓ | ✓ |
| Prob072_thermostat | a heating/cooling thermostat controller which controls both a heater (during winter) and an air conditioner (during summer) | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 17 | ✓ | ✓ |
| Prob074_ece241_2014_q4 | a finite state machine with the following behavior | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 17 | ✓ | ✓ |
| Prob089_ece241_2014_q5a | a one-input one-output serial 2's complementer Moore state machine | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 26 | ✓ | ✓ |
| Prob093_ece241_2014_q3 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 14 | ✓ | ✓ |
| Prob100_fsm3comb | the following is the state transition table for a Moore state machine with one input, one output, and four states | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 23 | ✓ | ✓ |
| Prob117_circuit9 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 17 | ✓ | ✓ |
| Prob119_fsm3 | a Moore state machine with the following state transition table with one input, one output, and four states | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 30 | ✓ | ✓ |
| Prob129_ece241_2013_q8 | a Mealy-type finite state machine that recognizes the sequence "101" on an input signal named x | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 37 | ✓ | ✓ |
| Prob009_popcount3 | a "population count" circuit that counts the number of '1's in the input vector | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | [view](https://drpeterjamieson.com/RESEARCH/HEIMDALL/verilogeval-Prob009_popcount3/) | MIT | 10 | ✓ | ✓ |
| Prob024_hadd | a half adder | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | [view](https://drpeterjamieson.com/RESEARCH/HEIMDALL/verilogeval-Prob024_hadd/) | MIT | 12 | ✓ | ✓ |
| Prob025_reduction | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | [view](https://drpeterjamieson.com/RESEARCH/HEIMDALL/verilogeval-Prob025_reduction/) | MIT | 10 | ✓ | ✓ |
| Prob027_fadd | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 13 | ✓ | ✓ |
| Prob036_ringer | a circuit to control a cellphone's ringer and vibration motor | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 13 | ✓ | ✓ |
| Prob058_alwaysblock2 | an XOR gate three ways, using an assign statement (output out_assign), a combinational always block (output out_always_comb), and a clocked always block (output out_always_ff) | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 16 | ✓ | ✓ |
| Prob065_7420 | the same functionality as the 7420 chip | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 19 | ✓ | ✓ |
| Prob070_ece241_2013_q2 | a digital system with four inputs (a,b,c,d) that generates a logic-1 when 2, 7, or 15 appears on the inputs, and a logic-0 when 0, 1, 4, 5, 6, 9, 10, 13, or 14 appears | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 19 | ✓ | ✓ |
| Prob075_counter_2bc | a two-bit saturating counter | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 22 | ✓ | ✓ |
| Prob077_wire_decl | the following circuit | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 18 | ✓ | ✓ |
| Prob078_dualedge | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 25 | ✓ | ✓ |
| Prob081_7458 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 21 | ✓ | ✓ |
| Prob088_ece241_2014_q5b | the following Mealy finite-state machine which is an implementation of the 2's complementer | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 25 | ✓ | ✓ |
| Prob091_2012_q2b | the state output logic for this finite-state machine | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 13 | ✓ | ✓ |
| Prob099_m2014_q6c | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 13 | ✓ | ✓ |
| Prob112_always_case2 | a priority encoder | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 30 | ✓ | ✓ |
| Prob127_lemmings1 | a simple game called Lemmings which involves critters with fairly simple brains | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 31 | ✓ | ✓ |
| Prob134_2014_q3c | the output logic and next state logic for an FSM using the table shown below | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 36 | ✓ | ✓ |
| Prob147_circuit10 | a sequential circuit | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 18 | ✓ | ✓ |
| Prob005_notgate | a NOT gate | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 10 | ✓ | ✓ |
| Prob010_mt2015_q4a | the boolean function z = (x^y) & x | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | [view](https://drpeterjamieson.com/RESEARCH/HEIMDALL/verilogeval-Prob010_mt2015_q4a/) | MIT | 11 | ✓ | ✓ |
| Prob011_norgate | a NOR gate | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | [view](https://drpeterjamieson.com/RESEARCH/HEIMDALL/verilogeval-Prob011_norgate/) | MIT | 11 | ✓ | ✓ |
| Prob012_xnorgate | an XNOR gate | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | [view](https://drpeterjamieson.com/RESEARCH/HEIMDALL/verilogeval-Prob012_xnorgate/) | MIT | 11 | ✓ | ✓ |
| Prob013_m2014_q4e | a 2-input NOR gate | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 11 | ✓ | ✓ |
| Prob014_andgate | a 2-input AND gate | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 11 | ✓ | ✓ |
| Prob019_m2014_q4f | the following circuit in Verilog | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 11 | ✓ | ✓ |
| Prob020_mt2015_eq2 | a circuit that has two 2-bit inputs A[1:0] and B[1:0], and produces an output z | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 11 | ✓ | ✓ |
| Prob022_mux2to1 | a one-bit wide, 2-to-1 multiplexer | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 12 | ✓ | ✓ |
| Prob026_alwaysblock1 | an AND gate using both an assign statement and a combinational always block | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 13 | ✓ | ✓ |
| Prob029_m2014_q4g | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 12 | ✓ | ✓ |
| Prob039_always_if | a 2-to-1 mux that chooses between a and b | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 15 | ✓ | ✓ |
| Prob048_m2014_q4c | a simple D flip flop with active high synchronous reset (reset output to 0) | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 17 | ✓ | ✓ |
| Prob049_m2014_q4b | a D flip flop, positive edge triggered, with an asynchronous reset "ar" | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 17 | ✓ | ✓ |
| Prob050_kmap1 | the circuit described by the Karnaugh map below | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 12 | ✓ | ✓ |
| Prob053_m2014_q4d | the following circuit: A D flip-flop takes as input the output of a two-input XOR | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 16 | ✓ | ✓ |
| Prob056_ece241_2013_q7 | a JK flip-flop with the following truth table | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 13 | ✓ | ✓ |
| Prob057_kmap2 | the circuit described by the Karnaugh map below | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 13 | ✓ | ✓ |
| Prob061_2014_q4a | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 18 | ✓ | ✓ |
| Prob069_truthtable1 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 15 | ✓ | ✓ |
| Prob083_mt2015_q4b | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 11 | ✓ | ✓ |
| Prob090_circuit1 | a combinational circuit | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 11 | ✓ | ✓ |
| Prob098_circuit7 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 12 | ✓ | ✓ |
| Prob101_circuit4 | a combinational circuit | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 13 | ✓ | ✓ |
| Prob102_circuit3 | a combinational circuit | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 13 | ✓ | ✓ |
| Prob103_circuit2 | a combinational circuit | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 13 | ✓ | ✓ |
| Prob104_mt2015_muxdff | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 15 | ✓ | ✓ |
| Prob107_fsm1s | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 28 | ✓ | ✓ |
| Prob109_fsm1 | a Moore machine with the diagram described below: B (1) --0--> A B (1) --1--> B A (0) --0--> B A (0) --1--> A It should asynchronously reset into state B if reset if high | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 28 | ✓ | ✓ |
| Prob110_fsm2 | a Moore state machine with two states, two inputs, and one output according to diagram described below | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 29 | ✓ | ✓ |
| Prob111_fsm2s | a Moore state machine with two states, two inputs, and one output according to diagram described below | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 29 | ✓ | ✓ |
| Prob113_2012_q1g | the function f shown in the Karnaugh map below | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 29 | ✓ | ✓ |
| Prob116_m2014_q3 | the function f shown in the Karnaugh map below | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 29 | ✓ | ✓ |
| Prob122_kmap4 | the Karnaugh map below | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 32 | ✓ | ✓ |
| Prob125_kmap3 | the Karnaugh map below | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 32 | ✓ | ✓ |
| Prob131_mt2015_q4 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 11 | ✓ | ✓ |
| Prob132_always_if2 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 25 | ✓ | ✓ |
| Prob135_m2014_q6b | the state machine shown below: A (0) --0--> B A (0) --1--> A B (0) --0--> C B (0) --1--> D C (0) --0--> E C (0) --1--> D D (0) --0--> F D (0) --1--> A E (1) --0--> E E (1) --1--> D F (1) --0--> C F (1) --1--> D The FSM should be implemented using three flip-flops and state codes y = 000, 001, ..., 101 for states A, B, ..., F, respectively | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 27 | ✓ | ✓ |
| Prob145_circuit8 | a sequential circuit | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 17 | ✓ | ✓ |
| Prob001_zero | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 9 | ✓ | ✓ |
| Prob002_m2014_q4i | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 9 | ✓ | ✓ |
| Prob003_step_one | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 9 | ✓ | ✓ |
| Prob004_vector2 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 10 | ✓ | ✓ |
| Prob006_vectorr | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 10 | ✓ | ✓ |
| Prob007_wire | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 10 | ✓ | ✓ |
| Prob008_m2014_q4h | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 10 | ✓ | ✓ |
| Prob015_vector1 | a combinational circuit that splits an input half-word (16 bits, [15:0] ) into lower [7:0] and upper [15:8] bytes | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 11 | ✓ | ✓ |
| Prob023_vector100r | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 12 | ✓ | ✓ |
| Prob028_m2014_q4a | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 14 | ✓ | ✓ |
| Prob031_dff | a single D flip-flop | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 15 | ✓ | ✓ |
| Prob032_vector0 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 14 | ✓ | ✓ |
| Prob034_dff8 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 15 | ✓ | ✓ |
| Prob042_vector4 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 10 | ✓ | ✓ |
| Prob059_wire4 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 15 | ✓ | ✓ |
| Prob064_vector3 | - | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 18 | ✓ | ✓ |
| Prob071_always_casez | a priority encoder for an 8-bit input | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 22 | ✓ | ✓ |
| Prob156_review2015_fancytimer | a timer with one input that: (1) is started when a particular input pattern (1101) is detected, (2) shifts in 4 more bits to determine the duration to delay, (3) waits for the counters to finish counting, and (4) notifies the user and waits for the user to acknowledge the timer | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 78 | ✓ | ✓ |
| Prob151_review2015_fsm | a timer that: (1) is started when a particular pattern (1101) is detected, (2) shifts in 4 more bits to determine the duration to delay, (3) waits for the counters to finish counting, and (4) notifies the user and waits for the user to acknowledge the timer | [verilogeval](#sources) | [repo](https://github.com/NMSU-PEARL/verilog-eval.git) | - | MIT | 56 | ✓ | ✓ |

<details><summary>Flow and VTR QoR</summary>

| design | iverilog | Odin sim | VTR stage | LUTs | blocks | FFs | pins | mult/mem | cpd ns | chan w | status | note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Prob144_conwaylife | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob030_popcount255 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob153_gshare | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob108_rule90 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob124_rule110 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob021_mux256to1v | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob092_gatesv100 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob105_rotate100 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob115_shift18 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob018_mux256to1 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob017_mux2to1v | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob097_mux9to1v | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob052_gates100 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob055_conditional | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob141_count_clock | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob066_edgecapture | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob082_lfsr32 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob118_history_shift | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob154_fsm_ps2data | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob068_countbcd | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob123_bugs_addsubz | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob043_vector5 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob146_fsm_serialdata | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob080_timer | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob155_lemmings4 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob073_dff16e | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob126_circuit6 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob037_review2015_count1k | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob033_ece241_2014_q1c | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob114_bugs_case | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob143_fsm_onehot | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob076_always_case | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob137_fsm_serial | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob084_ece241_2013_q12 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob140_fsm_hdlc | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob149_ece241_2013_q4 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob044_vectorgates | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob094_gatesv | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob106_always_nolatches | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob046_dff8p | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob130_circuit5 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob133_2014_q3fsm | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob139_2013_q2bfsm | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob041_dff8r | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob045_edgedetect2 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob047_dff8ar | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob054_edgedetect | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob062_bugs_mux2 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob087_gates | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob136_m2014_q6 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob138_2012_q2fsm | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob016_m2014_q4j | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob121_2014_q3bfsm | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob152_lemmings3 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob086_lfsr5 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob096_review2015_fsmseq | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob148_2013_q2afsm | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob150_review2015_fsmonehot | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob035_count1to10 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob038_count15 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob040_count10 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob060_m2014_q4k | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob063_review2015_shiftcount | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob067_countslow | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob079_fsm3onehot | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob085_shift4 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob095_review2015_fsmshift | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob120_fsm3s | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob128_fsm_ps2 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob142_lemmings2 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob051_gates4 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob072_thermostat | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob074_ece241_2014_q4 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob089_ece241_2014_q5a | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob093_ece241_2014_q3 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob100_fsm3comb | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob117_circuit9 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob119_fsm3 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob129_ece241_2013_q8 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob009_popcount3 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob024_hadd | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob025_reduction | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob027_fadd | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob036_ringer | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob058_alwaysblock2 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob065_7420 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob070_ece241_2013_q2 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob075_counter_2bc | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob077_wire_decl | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob078_dualedge | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob081_7458 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob088_ece241_2014_q5b | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob091_2012_q2b | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob099_m2014_q6c | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob112_always_case2 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob127_lemmings1 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob134_2014_q3c | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob147_circuit10 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob005_notgate | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob010_mt2015_q4a | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob011_norgate | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob012_xnorgate | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob013_m2014_q4e | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob014_andgate | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob019_m2014_q4f | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob020_mt2015_eq2 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob022_mux2to1 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob026_alwaysblock1 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob029_m2014_q4g | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob039_always_if | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob048_m2014_q4c | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob049_m2014_q4b | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob050_kmap1 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob053_m2014_q4d | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob056_ece241_2013_q7 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob057_kmap2 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob061_2014_q4a | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob069_truthtable1 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob083_mt2015_q4b | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob090_circuit1 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob098_circuit7 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob101_circuit4 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob102_circuit3 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob103_circuit2 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob104_mt2015_muxdff | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob107_fsm1s | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob109_fsm1 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob110_fsm2 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob111_fsm2s | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob113_2012_q1g | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob116_m2014_q3 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob122_kmap4 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob125_kmap3 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob131_mt2015_q4 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob132_always_if2 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob135_m2014_q6b | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob145_circuit8 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob001_zero | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob002_m2014_q4i | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob003_step_one | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob004_vector2 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob006_vectorr | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob007_wire | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob008_m2014_q4h | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob015_vector1 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob023_vector100r | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob028_m2014_q4a | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob031_dff | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob032_vector0 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob034_dff8 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob042_vector4 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob059_wire4 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob064_vector3 | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob071_always_casez | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob156_review2015_fancytimer | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob151_review2015_fsm | - | - | - | - | - | - | - | - | - | - | - | - |

</details>

<details><summary>LUT forms</summary>

| design | gates/d | 4-LUT/d | 6-LUT/d |
|---|---|---|---|
| Prob144_conwaylife | 30976/22 | 3280/5 | 1966/3 |
| Prob030_popcount255 | 14806/527 | 1822/130 | 1369/67 |
| Prob153_gshare | 6984/31 | 930/10 | 647/7 |
| Prob108_rule90 | 1022/2 | 512/1 | 512/1 |
| Prob124_rule110 | 6643/7 | 1022/2 | 512/1 |
| Prob021_mux256to1v | 90112/11 | 887/7 | 390/5 |
| Prob092_gatesv100 | 298/1 | 298/1 | 298/1 |
| Prob105_rotate100 | 310/6 | 300/2 | 201/2 |
| Prob115_shift18 | 539/9 | 356/3 | 130/2 |
| Prob018_mux256to1 | 2048/8 | 223/7 | 105/5 |
| Prob017_mux2to1v | 100/1 | 100/1 | 100/1 |
| Prob097_mux9to1v | 364/10 | 123/4 | 95/2 |
| Prob052_gates100 | 297/7 | 102/4 | 88/3 |
| Prob055_conditional | 231/40 | 60/12 | 56/9 |
| Prob141_count_clock | 468/12 | 60/5 | 41/4 |
| Prob066_edgecapture | 128/4 | 32/1 | 32/1 |
| Prob082_lfsr32 | 35/2 | 32/1 | 32/1 |
| Prob118_history_shift | 97/3 | 65/2 | 32/1 |
| Prob154_fsm_ps2data | 37/4 | 28/1 | 28/1 |
| Prob068_countbcd | 211/10 | 32/5 | 22/3 |
| Prob123_bugs_addsubz | 150/24 | 30/7 | 22/4 |
| Prob043_vector5 | 30/2 | 20/1 | 20/1 |
| Prob146_fsm_serialdata | 32/5 | 21/2 | 20/1 |
| Prob080_timer | 124/15 | 22/4 | 17/3 |
| Prob155_lemmings4 | 220/22 | 21/3 | 17/2 |
| Prob073_dff16e | 32/2 | 16/1 | 16/1 |
| Prob126_circuit6 | 272/9 | 16/1 | 16/1 |
| Prob037_review2015_count1k | 105/13 | 18/3 | 14/3 |
| Prob033_ece241_2014_q1c | 63/14 | 17/5 | 13/3 |
| Prob114_bugs_case | 249/11 | 18/4 | 13/3 |
| Prob143_fsm_onehot | 23/7 | 15/2 | 13/2 |
| Prob076_always_case | 86/9 | 25/3 | 12/2 |
| Prob137_fsm_serial | 24/5 | 13/2 | 12/1 |
| Prob084_ece241_2013_q12 | 32/3 | 14/3 | 11/2 |
| Prob140_fsm_hdlc | 29/5 | 14/2 | 11/2 |
| Prob149_ece241_2013_q4 | 101/6 | 17/2 | 11/2 |
| Prob044_vectorgates | 14/3 | 10/2 | 10/1 |
| Prob094_gatesv | 10/1 | 10/1 | 10/1 |
| Prob106_always_nolatches | 128/6 | 12/3 | 10/2 |
| Prob046_dff8p | 9/1 | 9/1 | 9/1 |
| Prob130_circuit5 | 63/8 | 16/3 | 9/2 |
| Prob133_2014_q3fsm | 33/6 | 10/2 | 9/2 |
| Prob139_2013_q2bfsm | 37/5 | 10/2 | 9/1 |
| Prob041_dff8r | 8/1 | 8/1 | 8/1 |
| Prob045_edgedetect2 | 8/1 | 8/1 | 8/1 |
| Prob047_dff8ar | 8/1 | 8/1 | 8/1 |
| Prob054_edgedetect | 16/2 | 8/1 | 8/1 |
| Prob062_bugs_mux2 | 8/1 | 8/1 | 8/1 |
| Prob087_gates | 8/2 | 7/1 | 7/1 |
| Prob136_m2014_q6 | 22/5 | 8/2 | 7/1 |
| Prob138_2012_q2fsm | 22/4 | 8/2 | 7/1 |
| Prob016_m2014_q4j | 32/9 | 7/3 | 6/2 |
| Prob121_2014_q3bfsm | 22/5 | 8/2 | 6/1 |
| Prob152_lemmings3 | 86/10 | 8/3 | 6/2 |
| Prob086_lfsr5 | 6/2 | 5/1 | 5/1 |
| Prob096_review2015_fsmseq | 18/5 | 6/2 | 5/1 |
| Prob148_2013_q2afsm | 62/7 | 8/2 | 5/2 |
| Prob150_review2015_fsmonehot | 19/5 | 6/2 | 5/1 |
| Prob035_count1to10 | 39/9 | 7/2 | 4/1 |
| Prob038_count15 | 30/9 | 5/2 | 4/1 |
| Prob040_count10 | 39/9 | 7/2 | 4/1 |
| Prob060_m2014_q4k | 4/1 | 4/1 | 4/1 |
| Prob063_review2015_shiftcount | 39/11 | 5/2 | 4/1 |
| Prob067_countslow | 46/11 | 7/3 | 4/1 |
| Prob079_fsm3onehot | 9/3 | 4/1 | 4/1 |
| Prob085_shift4 | 13/3 | 9/2 | 4/1 |
| Prob095_review2015_fsmshift | 9/3 | 4/1 | 4/1 |
| Prob120_fsm3s | 15/4 | 5/2 | 4/1 |
| Prob128_fsm_ps2 | 13/4 | 4/1 | 4/1 |
| Prob142_lemmings2 | 37/8 | 6/2 | 4/1 |
| Prob051_gates4 | 9/2 | 3/1 | 3/1 |
| Prob072_thermostat | 5/2 | 3/1 | 3/1 |
| Prob074_ece241_2014_q4 | 8/3 | 3/1 | 3/1 |
| Prob089_ece241_2014_q5a | 10/4 | 4/2 | 3/1 |
| Prob093_ece241_2014_q3 | 3/1 | 3/1 | 3/1 |
| Prob100_fsm3comb | 24/7 | 3/1 | 3/1 |
| Prob117_circuit9 | 30/8 | 3/1 | 3/1 |
| Prob119_fsm3 | 26/8 | 3/1 | 3/1 |
| Prob129_ece241_2013_q8 | 30/8 | 3/1 | 3/1 |
| Prob009_popcount3 | 22/7 | 2/1 | 2/1 |
| Prob024_hadd | 11/5 | 2/1 | 2/1 |
| Prob025_reduction | 7/3 | 3/2 | 2/2 |
| Prob027_fadd | 22/7 | 2/1 | 2/1 |
| Prob036_ringer | 3/2 | 2/1 | 2/1 |
| Prob058_alwaysblock2 | 1/1 | 2/1 | 2/1 |
| Prob065_7420 | 8/3 | 2/1 | 2/1 |
| Prob070_ece241_2013_q2 | 15/7 | 2/1 | 2/1 |
| Prob075_counter_2bc | 62/14 | 4/2 | 2/1 |
| Prob077_wire_decl | 4/3 | 2/1 | 2/1 |
| Prob078_dualedge | 2/1 | 2/1 | 2/1 |
| Prob081_7458 | 8/3 | 3/2 | 2/1 |
| Prob088_ece241_2014_q5b | 7/3 | 2/1 | 2/1 |
| Prob091_2012_q2b | 6/4 | 3/2 | 2/1 |
| Prob099_m2014_q6c | 6/4 | 3/2 | 2/1 |
| Prob112_always_case2 | 142/12 | 2/1 | 2/1 |
| Prob127_lemmings1 | 4/3 | 2/1 | 2/1 |
| Prob134_2014_q3c | 59/8 | 2/1 | 2/1 |
| Prob147_circuit10 | 7/3 | 2/1 | 2/1 |
| Prob005_notgate | 1/1 | 1/1 | 1/1 |
| Prob010_mt2015_q4a | 2/2 | 1/1 | 1/1 |
| Prob011_norgate | 2/2 | 1/1 | 1/1 |
| Prob012_xnorgate | 2/2 | 1/1 | 1/1 |
| Prob013_m2014_q4e | 2/2 | 1/1 | 1/1 |
| Prob014_andgate | 1/1 | 1/1 | 1/1 |
| Prob019_m2014_q4f | 2/2 | 1/1 | 1/1 |
| Prob020_mt2015_eq2 | 4/3 | 1/1 | 1/1 |
| Prob022_mux2to1 | 1/1 | 1/1 | 1/1 |
| Prob026_alwaysblock1 | 1/1 | 1/1 | 1/1 |
| Prob029_m2014_q4g | 3/3 | 1/1 | 1/1 |
| Prob039_always_if | 2/2 | 1/1 | 1/1 |
| Prob048_m2014_q4c | 1/1 | 1/1 | 1/1 |
| Prob049_m2014_q4b | 1/1 | 1/1 | 1/1 |
| Prob050_kmap1 | 2/2 | 1/1 | 1/1 |
| Prob053_m2014_q4d | 1/1 | 1/1 | 1/1 |
| Prob056_ece241_2013_q7 | 5/3 | 1/1 | 1/1 |
| Prob057_kmap2 | 13/5 | 1/1 | 1/1 |
| Prob061_2014_q4a | 3/2 | 2/2 | 1/1 |
| Prob069_truthtable1 | 13/6 | 1/1 | 1/1 |
| Prob083_mt2015_q4b | 2/2 | 1/1 | 1/1 |
| Prob090_circuit1 | 1/1 | 1/1 | 1/1 |
| Prob098_circuit7 | 1/1 | 1/1 | 1/1 |
| Prob101_circuit4 | 1/1 | 1/1 | 1/1 |
| Prob102_circuit3 | 3/2 | 1/1 | 1/1 |
| Prob103_circuit2 | 4/4 | 1/1 | 1/1 |
| Prob104_mt2015_muxdff | 1/1 | 1/1 | 1/1 |
| Prob107_fsm1s | 3/3 | 1/1 | 1/1 |
| Prob109_fsm1 | 3/3 | 1/1 | 1/1 |
| Prob110_fsm2 | 3/3 | 1/1 | 1/1 |
| Prob111_fsm2s | 3/3 | 1/1 | 1/1 |
| Prob113_2012_q1g | 67/7 | 1/1 | 1/1 |
| Prob116_m2014_q3 | 103/8 | 1/1 | 1/1 |
| Prob122_kmap4 | 68/8 | 1/1 | 1/1 |
| Prob125_kmap3 | 98/8 | 1/1 | 1/1 |
| Prob131_mt2015_q4 | 2/2 | 1/1 | 1/1 |
| Prob132_always_if2 | 2/2 | 1/1 | 1/1 |
| Prob135_m2014_q6b | 50/8 | 1/1 | 1/1 |
| Prob145_circuit8 | 1/1 | 1/1 | 1/1 |
| Prob001_zero | 0/0 | 0/0 | 0/0 |
| Prob002_m2014_q4i | 0/0 | 0/0 | 0/0 |
| Prob003_step_one | 0/0 | 0/0 | 0/0 |
| Prob004_vector2 | 0/0 | 0/0 | 0/0 |
| Prob006_vectorr | 0/0 | 0/0 | 0/0 |
| Prob007_wire | 0/0 | 0/0 | 0/0 |
| Prob008_m2014_q4h | 0/0 | 0/0 | 0/0 |
| Prob015_vector1 | 0/0 | 0/0 | 0/0 |
| Prob023_vector100r | 0/0 | 0/0 | 0/0 |
| Prob028_m2014_q4a | 0/0 | 0/0 | 0/0 |
| Prob031_dff | 0/0 | 0/0 | 0/0 |
| Prob032_vector0 | 0/0 | 0/0 | 0/0 |
| Prob034_dff8 | 0/0 | 0/0 | 0/0 |
| Prob042_vector4 | 0/0 | 0/0 | 0/0 |
| Prob059_wire4 | 0/0 | 0/0 | 0/0 |
| Prob064_vector3 | 0/0 | 0/0 | 0/0 |
| Prob071_always_casez | 0/0 | 0/0 | 0/0 |
| Prob156_review2015_fancytimer | fail: read_slang: ..Prob156_review2015_fancytimer_ref.sv:25:17: an explicit 4-bit cast is not supported/fail: read_slang: ..Prob156_review2015_fancytimer_ref.sv:25:17: an explicit 4-bit cast is not supported | fail: read_slang: ..Prob156_review2015_fancytimer_ref.sv:25:17: an explicit 4-bit cast is not supported/fail: read_slang: ..Prob156_review2015_fancytimer_ref.sv:25:17: an explicit 4-bit cast is not supported | fail: read_slang: ..Prob156_review2015_fancytimer_ref.sv:25:17: an explicit 4-bit cast is not supported/fail: read_slang: ..Prob156_review2015_fancytimer_ref.sv:25:17: an explicit 4-bit cast is not supported |
| Prob151_review2015_fsm | fail: read_slang: ..Prob151_review2015_fsm_ref.sv:21:17: an explicit 4-bit cast is not supported/fail: read_slang: ..Prob151_review2015_fsm_ref.sv:21:17: an explicit 4-bit cast is not supported | fail: read_slang: ..Prob151_review2015_fsm_ref.sv:21:17: an explicit 4-bit cast is not supported/fail: read_slang: ..Prob151_review2015_fsm_ref.sv:21:17: an explicit 4-bit cast is not supported | fail: read_slang: ..Prob151_review2015_fsm_ref.sv:21:17: an explicit 4-bit cast is not supported/fail: read_slang: ..Prob151_review2015_fsm_ref.sv:21:17: an explicit 4-bit cast is not supported |

</details>

<details><summary>Properties</summary>

| design | seq | mem | mul | add | fsm | latch | hier | bbox |
|---|---|---|---|---|---|---|---|---|
| Prob144_conwaylife | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Prob030_popcount255 | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Prob153_gshare | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Prob108_rule90 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob124_rule110 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob021_mux256to1v | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob092_gatesv100 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob105_rotate100 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob115_shift18 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob018_mux256to1 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob017_mux2to1v | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob097_mux9to1v | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob052_gates100 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob055_conditional | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob141_count_clock | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Prob066_edgecapture | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob082_lfsr32 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob118_history_shift | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob154_fsm_ps2data | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Prob068_countbcd | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Prob123_bugs_addsubz | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Prob043_vector5 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob146_fsm_serialdata | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Prob080_timer | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Prob155_lemmings4 | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Prob073_dff16e | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob126_circuit6 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob037_review2015_count1k | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Prob033_ece241_2014_q1c | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Prob114_bugs_case | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob143_fsm_onehot | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob076_always_case | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob137_fsm_serial | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Prob084_ece241_2013_q12 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob140_fsm_hdlc | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Prob149_ece241_2013_q4 | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Prob044_vectorgates | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob094_gatesv | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob106_always_nolatches | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob046_dff8p | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob130_circuit5 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob133_2014_q3fsm | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Prob139_2013_q2bfsm | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Prob041_dff8r | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob045_edgedetect2 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob047_dff8ar | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob054_edgedetect | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob062_bugs_mux2 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob087_gates | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob136_m2014_q6 | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Prob138_2012_q2fsm | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Prob016_m2014_q4j | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Prob121_2014_q3bfsm | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Prob152_lemmings3 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob086_lfsr5 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob096_review2015_fsmseq | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Prob148_2013_q2afsm | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Prob150_review2015_fsmonehot | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob035_count1to10 | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Prob038_count15 | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Prob040_count10 | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Prob060_m2014_q4k | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob063_review2015_shiftcount | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Prob067_countslow | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Prob079_fsm3onehot | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob085_shift4 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob095_review2015_fsmshift | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Prob120_fsm3s | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Prob128_fsm_ps2 | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Prob142_lemmings2 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob051_gates4 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob072_thermostat | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob074_ece241_2014_q4 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob089_ece241_2014_q5a | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Prob093_ece241_2014_q3 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob100_fsm3comb | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob117_circuit9 | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Prob119_fsm3 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob129_ece241_2013_q8 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob009_popcount3 | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Prob024_hadd | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Prob025_reduction | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob027_fadd | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Prob036_ringer | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob058_alwaysblock2 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob065_7420 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob070_ece241_2013_q2 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob075_counter_2bc | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Prob077_wire_decl | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob078_dualedge | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob081_7458 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob088_ece241_2014_q5b | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob091_2012_q2b | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob099_m2014_q6c | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob112_always_case2 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob127_lemmings1 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob134_2014_q3c | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob147_circuit10 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob005_notgate | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob010_mt2015_q4a | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob011_norgate | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob012_xnorgate | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob013_m2014_q4e | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob014_andgate | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob019_m2014_q4f | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob020_mt2015_eq2 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob022_mux2to1 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob026_alwaysblock1 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob029_m2014_q4g | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob039_always_if | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob048_m2014_q4c | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob049_m2014_q4b | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob050_kmap1 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob053_m2014_q4d | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob056_ece241_2013_q7 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob057_kmap2 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob061_2014_q4a | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob069_truthtable1 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob083_mt2015_q4b | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob090_circuit1 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob098_circuit7 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob101_circuit4 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob102_circuit3 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob103_circuit2 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob104_mt2015_muxdff | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob107_fsm1s | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob109_fsm1 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob110_fsm2 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob111_fsm2s | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob113_2012_q1g | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob116_m2014_q3 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob122_kmap4 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob125_kmap3 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob131_mt2015_q4 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob132_always_if2 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob135_m2014_q6b | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob145_circuit8 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob001_zero | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob002_m2014_q4i | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob003_step_one | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob004_vector2 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob006_vectorr | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob007_wire | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob008_m2014_q4h | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob015_vector1 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob023_vector100r | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob028_m2014_q4a | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob031_dff | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob032_vector0 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob034_dff8 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob042_vector4 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob059_wire4 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob064_vector3 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob071_always_casez | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Prob156_review2015_fancytimer | fail: read_slang: ..Prob156_review2015_fancytimer_ref.sv:25:17: an explicit 4-bit cast is not supported | fail: read_slang: ..Prob156_review2015_fancytimer_ref.sv:25:17: an explicit 4-bit cast is not supported | fail: read_slang: ..Prob156_review2015_fancytimer_ref.sv:25:17: an explicit 4-bit cast is not supported | fail: read_slang: ..Prob156_review2015_fancytimer_ref.sv:25:17: an explicit 4-bit cast is not supported | fail: read_slang: ..Prob156_review2015_fancytimer_ref.sv:25:17: an explicit 4-bit cast is not supported | fail: read_slang: ..Prob156_review2015_fancytimer_ref.sv:25:17: an explicit 4-bit cast is not supported | fail: read_slang: ..Prob156_review2015_fancytimer_ref.sv:25:17: an explicit 4-bit cast is not supported | fail: read_slang: ..Prob156_review2015_fancytimer_ref.sv:25:17: an explicit 4-bit cast is not supported |
| Prob151_review2015_fsm | fail: read_slang: ..Prob151_review2015_fsm_ref.sv:21:17: an explicit 4-bit cast is not supported | fail: read_slang: ..Prob151_review2015_fsm_ref.sv:21:17: an explicit 4-bit cast is not supported | fail: read_slang: ..Prob151_review2015_fsm_ref.sv:21:17: an explicit 4-bit cast is not supported | fail: read_slang: ..Prob151_review2015_fsm_ref.sv:21:17: an explicit 4-bit cast is not supported | fail: read_slang: ..Prob151_review2015_fsm_ref.sv:21:17: an explicit 4-bit cast is not supported | fail: read_slang: ..Prob151_review2015_fsm_ref.sv:21:17: an explicit 4-bit cast is not supported | fail: read_slang: ..Prob151_review2015_fsm_ref.sv:21:17: an explicit 4-bit cast is not supported | fail: read_slang: ..Prob151_review2015_fsm_ref.sv:21:17: an explicit 4-bit cast is not supported |

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
| Prob092_gatesv100 | - | 6531.3 | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob105_rotate100 | 873 | 18955.7 | match | lvs |
| Prob115_shift18 | 703 | 13934.6 | match | lvs |
| Prob018_mux256to1 | 506 | 7847.5 | match | lvs |
| Prob017_mux2to1v | - | 4144.0 | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob097_mux9to1v | 187 | 3178.0 | match | lvs |
| Prob052_gates100 | 318 | 5172.5 | match | lvs |
| Prob055_conditional | 159 | 2499.9 | match | lvs |
| Prob141_count_clock | - | - | - | - |
| Prob066_edgecapture | - | - | - | - |
| Prob082_lfsr32 | - | - | - | - |
| Prob118_history_shift | - | - | - | - |
| Prob154_fsm_ps2data | - | 2876.5 | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
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
| Prob046_dff8p | - | - | out of scope: stopped at equiv (equiv header.check.detail: absolute or home path in 'equiv-c) | map |
| Prob130_circuit5 | - | - | - | - |
| Prob133_2014_q3fsm | - | - | - | - |
| Prob139_2013_q2bfsm | - | - | - | - |
| Prob041_dff8r | - | - | - | - |
| Prob045_edgedetect2 | - | 1594.0 | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob047_dff8ar | - | - | - | - |
| Prob054_edgedetect | - | 1559.0 | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
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
| Prob093_ece241_2014_q3 | - | 42.5 | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob100_fsm3comb | 4 | 45.0 | mismatch | extract |
| Prob117_circuit9 | - | - | - | - |
| Prob119_fsm3 | - | - | - | - |
| Prob129_ece241_2013_q8 | - | - | - | - |
| Prob009_popcount3 | - | - | - | - |
| Prob024_hadd | - | - | - | - |
| Prob025_reduction | - | - | - | - |
| Prob027_fadd | - | - | - | - |
| Prob036_ringer | - | 17.5 | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob058_alwaysblock2 | - | - | - | - |
| Prob065_7420 | - | 17.5 | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob070_ece241_2013_q2 | - | - | - | - |
| Prob075_counter_2bc | - | - | - | - |
| Prob077_wire_decl | - | - | - | - |
| Prob078_dualedge | - | - | - | - |
| Prob081_7458 | 4 | 47.5 | mismatch | extract |
| Prob088_ece241_2014_q5b | - | - | - | - |
| Prob091_2012_q2b | - | 40.0 | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
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
| Prob145_circuit8 | - | - | - | - |
| Prob001_zero | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob002_m2014_q4i | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob003_step_one | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob004_vector2 | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob006_vectorr | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob007_wire | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob008_m2014_q4h | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob015_vector1 | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob023_vector100r | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob028_m2014_q4a | - | - | - | - |
| Prob031_dff | - | - | - | - |
| Prob032_vector0 | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob034_dff8 | - | 788.3 | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob042_vector4 | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob059_wire4 | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob064_vector3 | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob071_always_casez | - | - | - | - |
| Prob156_review2015_fancytimer | - | - | - | - |
| Prob151_review2015_fsm | - | - | - | - |

</details>

<details><summary>Power</summary>

| design | activity | FPGA pJ/cycle | ASIC pJ/cycle | FPGA MHz | power note |
|---|---|---|---|---|---|
| Prob144_conwaylife | - | - | - | - | - |
| Prob030_popcount255 | - | - | - | - | - |
| Prob153_gshare | - | - | - | - | - |
| Prob108_rule90 | - | - | - | - | - |
| Prob124_rule110 | - | - | - | - | - |
| Prob021_mux256to1v | - | - | - | - | - |
| Prob092_gatesv100 | - | - | - | - | - |
| Prob105_rotate100 | - | - | - | - | - |
| Prob115_shift18 | - | - | - | - | - |
| Prob018_mux256to1 | - | - | - | - | - |
| Prob017_mux2to1v | - | - | - | - | - |
| Prob097_mux9to1v | - | - | - | - | - |
| Prob052_gates100 | - | - | - | - | - |
| Prob055_conditional | - | - | - | - | - |
| Prob141_count_clock | ace2 | 2.054 | - | 471.7 | matched 0.807; ACE2 vectorless, primary inputs p=0.5 activity=0.2 |
| Prob066_edgecapture | - | - | - | - | - |
| Prob082_lfsr32 | - | - | - | - | - |
| Prob118_history_shift | - | - | - | - | - |
| Prob154_fsm_ps2data | - | - | - | - | - |
| Prob068_countbcd | - | - | - | - | - |
| Prob123_bugs_addsubz | ace2 | 1.528 | - | 387.7 | matched 0.935; ACE2 vectorless, primary inputs p=0.5 activity=0.2 |
| Prob043_vector5 | ace2 | 1.707 | - | 857.2 | matched 1.000; ACE2 vectorless, primary inputs p=0.5 activity=0.2 |
| Prob146_fsm_serialdata | - | - | - | - | - |
| Prob080_timer | - | - | - | - | - |
| Prob155_lemmings4 | - | - | - | - | - |
| Prob073_dff16e | - | - | - | - | - |
| Prob126_circuit6 | - | - | - | - | - |
| Prob037_review2015_count1k | - | - | - | - | - |
| Prob033_ece241_2014_q1c | - | - | - | - | - |
| Prob114_bugs_case | - | - | - | - | - |
| Prob143_fsm_onehot | - | - | - | - | - |
| Prob076_always_case | - | - | - | - | - |
| Prob137_fsm_serial | - | - | - | - | - |
| Prob084_ece241_2013_q12 | - | - | - | - | - |
| Prob140_fsm_hdlc | - | - | - | - | - |
| Prob149_ece241_2013_q4 | - | - | - | - | - |
| Prob044_vectorgates | - | - | - | - | - |
| Prob094_gatesv | - | - | - | - | - |
| Prob106_always_nolatches | - | - | - | - | - |
| Prob046_dff8p | - | - | - | - | - |
| Prob130_circuit5 | - | - | - | - | - |
| Prob133_2014_q3fsm | - | - | - | - | - |
| Prob139_2013_q2bfsm | - | - | - | - | - |
| Prob041_dff8r | - | - | - | - | - |
| Prob045_edgedetect2 | - | - | - | - | - |
| Prob047_dff8ar | - | - | - | - | - |
| Prob054_edgedetect | - | - | - | - | - |
| Prob062_bugs_mux2 | - | - | - | - | - |
| Prob087_gates | - | - | - | - | - |
| Prob136_m2014_q6 | - | - | - | - | - |
| Prob138_2012_q2fsm | - | - | - | - | - |
| Prob016_m2014_q4j | ace2 | 0.6545 | - | 653.3 | matched 0.900; ACE2 vectorless, primary inputs p=0.5 activity=0.2 |
| Prob121_2014_q3bfsm | - | - | - | - | - |
| Prob152_lemmings3 | - | - | - | - | - |
| Prob086_lfsr5 | - | - | - | - | - |
| Prob096_review2015_fsmseq | - | - | - | - | - |
| Prob148_2013_q2afsm | - | - | - | - | - |
| Prob150_review2015_fsmonehot | ace2 | 0.7253 | - | 958.9 | matched 1.000; ACE2 vectorless, primary inputs p=0.5 activity=0.2 |
| Prob035_count1to10 | - | - | - | - | - |
| Prob038_count15 | - | - | - | - | - |
| Prob040_count10 | - | - | - | - | - |
| Prob060_m2014_q4k | - | - | - | - | - |
| Prob063_review2015_shiftcount | - | - | - | - | - |
| Prob067_countslow | - | - | - | - | - |
| Prob079_fsm3onehot | - | - | - | - | - |
| Prob085_shift4 | ace2 | 0.6309 | - | 1650.0 | matched 0.733; ACE2 vectorless, primary inputs p=0.5 activity=0.2 |
| Prob095_review2015_fsmshift | - | - | - | - | - |
| Prob120_fsm3s | - | - | - | - | - |
| Prob128_fsm_ps2 | - | - | - | - | - |
| Prob142_lemmings2 | - | - | - | - | - |
| Prob051_gates4 | - | - | - | - | - |
| Prob072_thermostat | - | - | - | - | - |
| Prob074_ece241_2014_q4 | - | - | - | - | - |
| Prob089_ece241_2014_q5a | - | - | - | - | - |
| Prob093_ece241_2014_q3 | - | - | - | - | - |
| Prob100_fsm3comb | - | - | - | - | - |
| Prob117_circuit9 | - | - | - | - | - |
| Prob119_fsm3 | - | - | - | - | - |
| Prob129_ece241_2013_q8 | - | - | - | - | - |
| Prob009_popcount3 | ace2 | 0.9534 | - | 453.3 | matched 0.875; ACE2 vectorless, primary inputs p=0.5 activity=0.2 |
| Prob024_hadd | ace2 | 0.4248 | - | 743.6 | matched 0.923; ACE2 vectorless, primary inputs p=0.5 activity=0.2 |
| Prob025_reduction | ace2 | 0.5859 | - | 834.9 | matched 1.000; ACE2 vectorless, primary inputs p=0.5 activity=0.2 |
| Prob027_fadd | - | - | - | - | - |
| Prob036_ringer | - | - | - | - | - |
| Prob058_alwaysblock2 | - | - | - | - | - |
| Prob065_7420 | - | - | - | - | - |
| Prob070_ece241_2013_q2 | - | - | - | - | - |
| Prob075_counter_2bc | - | - | - | - | - |
| Prob077_wire_decl | - | - | - | - | - |
| Prob078_dualedge | - | - | - | - | - |
| Prob081_7458 | - | - | - | - | - |
| Prob088_ece241_2014_q5b | - | - | - | - | - |
| Prob091_2012_q2b | - | - | - | - | - |
| Prob099_m2014_q6c | - | - | - | - | - |
| Prob112_always_case2 | - | - | - | - | - |
| Prob127_lemmings1 | - | - | - | - | - |
| Prob134_2014_q3c | - | - | - | - | - |
| Prob147_circuit10 | - | - | - | - | - |
| Prob005_notgate | - | - | - | - | - |
| Prob010_mt2015_q4a | ace2 | 0.3853 | - | 1160.3 | matched 1.000; ACE2 vectorless, primary inputs p=0.5 activity=0.2 |
| Prob011_norgate | ace2 | 0.3853 | - | 1160.3 | matched 1.000; ACE2 vectorless, primary inputs p=0.5 activity=0.2 |
| Prob012_xnorgate | ace2 | 0.3922 | - | 1160.3 | matched 1.000; ACE2 vectorless, primary inputs p=0.5 activity=0.2 |
| Prob013_m2014_q4e | - | - | - | - | - |
| Prob014_andgate | - | - | - | - | - |
| Prob019_m2014_q4f | - | - | - | - | - |
| Prob020_mt2015_eq2 | - | - | - | - | - |
| Prob022_mux2to1 | - | - | - | - | - |
| Prob026_alwaysblock1 | - | - | - | - | - |
| Prob029_m2014_q4g | - | - | - | - | - |
| Prob039_always_if | - | - | - | - | - |
| Prob048_m2014_q4c | - | - | - | - | - |
| Prob049_m2014_q4b | - | - | - | - | - |
| Prob050_kmap1 | - | - | - | - | - |
| Prob053_m2014_q4d | - | - | - | - | - |
| Prob056_ece241_2013_q7 | - | - | - | - | - |
| Prob057_kmap2 | - | - | - | - | - |
| Prob061_2014_q4a | - | - | - | - | - |
| Prob069_truthtable1 | - | - | - | - | - |
| Prob083_mt2015_q4b | - | - | - | - | - |
| Prob090_circuit1 | - | - | - | - | - |
| Prob098_circuit7 | - | - | - | - | - |
| Prob101_circuit4 | - | - | - | - | - |
| Prob102_circuit3 | - | - | - | - | - |
| Prob103_circuit2 | - | - | - | - | - |
| Prob104_mt2015_muxdff | - | - | - | - | - |
| Prob107_fsm1s | - | - | - | - | - |
| Prob109_fsm1 | - | - | - | - | - |
| Prob110_fsm2 | - | - | - | - | - |
| Prob111_fsm2s | - | - | - | - | - |
| Prob113_2012_q1g | - | - | - | - | - |
| Prob116_m2014_q3 | - | - | - | - | - |
| Prob122_kmap4 | - | - | - | - | - |
| Prob125_kmap3 | - | - | - | - | - |
| Prob131_mt2015_q4 | - | - | - | - | - |
| Prob132_always_if2 | - | - | - | - | - |
| Prob135_m2014_q6b | - | - | - | - | - |
| Prob145_circuit8 | - | - | - | - | - |
| Prob001_zero | - | - | - | - | - |
| Prob002_m2014_q4i | - | - | - | - | - |
| Prob003_step_one | - | - | - | - | - |
| Prob004_vector2 | - | - | - | - | - |
| Prob006_vectorr | - | - | - | - | - |
| Prob007_wire | - | - | - | - | - |
| Prob008_m2014_q4h | - | - | - | - | - |
| Prob015_vector1 | - | - | - | - | - |
| Prob023_vector100r | - | - | - | - | - |
| Prob028_m2014_q4a | - | - | - | - | - |
| Prob031_dff | - | - | - | - | - |
| Prob032_vector0 | - | - | - | - | - |
| Prob034_dff8 | - | - | - | - | - |
| Prob042_vector4 | - | - | - | - | - |
| Prob059_wire4 | - | - | - | - | - |
| Prob064_vector3 | - | - | - | - | - |
| Prob071_always_casez | - | - | - | - | - |
| Prob156_review2015_fancytimer | - | - | - | - | - |
| Prob151_review2015_fsm | - | - | - | - | - |

</details>

</details>

<details><summary>T3 HDL, no testbench (55 designs)</summary>

Rule: HDL (Verilog) with no testbench file.

| design | what it does | suite | link | view | licence | LOC | tb | vec |
|---|---|---|---|---|---|---|---|---|
| LU64PEEng | - | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | per design | 6043 | ✗ | ✗ |
| mcml | Medical Physics | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | per design | 24507 | ✗ | ✗ |
| LU32PEEng | Math | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | per design | 5497 | ✗ | ✗ |
| stereovision2 | Computer Vision | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | per design | 1846 | ✗ | ✗ |
| bgm | Finance | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | per design | 2663 | ✗ | ✗ |
| LU8PEEng | Math | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | per design | 5033 | ✗ | ✗ |
| stereovision1 | Computer Vision | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | per design | 2553 | ✗ | ✗ |
| stereovision0 | Computer Vision | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | per design | 3905 | ✗ | ✗ |
| raygentop_nolatches | - | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | per design | 3178 | ✗ | ✗ |
| arm_core | - | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | per design | 8211 | ✗ | ✗ |
| or1200 | Soft Processor | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | per design | 5237 | ✗ | ✗ |
| raygentop | Ray Tracing | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | per design | 2978 | ✗ | ✗ |
| b22 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | - | GPL-3.0 | 2751 | ✗ | ✗ |
| blob_merge | Image Processing | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | per design | 1617 | ✗ | ✗ |
| b17 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | - | GPL-3.0 | 940 | ✗ | ✗ |
| b20 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | - | GPL-3.0 | 1842 | ✗ | ✗ |
| b21 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | - | GPL-3.0 | 1853 | ✗ | ✗ |
| diffeq1 | Math | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | per design | 56 | ✗ | ✗ |
| b18 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | - | GPL-3.0 | 1931 | ✗ | ✗ |
| b19 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | - | GPL-3.0 | 1993 | ✗ | ✗ |
| boundtop | Ray Tracing | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | per design | 2825 | ✗ | ✗ |
| boundtop_nolatches | - | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | per design | 3053 | ✗ | ✗ |
| b15 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | - | GPL-3.0 | 805 | ✗ | ✗ |
| spree | - | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | per design | 3072 | ✗ | ✗ |
| attiny_atmega_xmega_core | Attiny Atmega Xmega core | [opencores](#sources) | [repo](https://opencores.org/projects) | [view](https://drpeterjamieson.com/RESEARCH/HEIMDALL/opencores-attiny_atmega_xmega_core/) | per project | 3352 | ✗ | ✗ |
| mkDelayWorker32B | Packet Processing | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | per design | 6628 | ✗ | ✗ |
| sha | Cryptography | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | [view](https://drpeterjamieson.com/RESEARCH/HEIMDALL/vtr-verilog-sha/) | per design | 2171 | ✗ | ✗ |
| mkSMAdapter4B | Packet Processing | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | per design | 4348 | ✗ | ✗ |
| b14 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | - | GPL-3.0 | 904 | ✗ | ✗ |
| b12 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | - | GPL-3.0 | 635 | ✗ | ✗ |
| b11 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | - | GPL-3.0 | 138 | ✗ | ✗ |
| mkPktMerge | Packet Processing | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | per design | 1535 | ✗ | ✗ |
| ch_intrinsics_nolatches | - | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | per design | 301 | ✗ | ✗ |
| b05 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | - | GPL-3.0 | 444 | ✗ | ✗ |
| stereovision3 | Computer Vision | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | per design | 1061 | ✗ | ✗ |
| ch_intrinsics | Memory Init | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | [view](https://drpeterjamieson.com/RESEARCH/HEIMDALL/vtr-verilog-ch_intrinsics/) | per design | 292 | ✗ | ✗ |
| diffeq2 | Math | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | per design | 63 | ✗ | ✗ |
| b04 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | - | GPL-3.0 | 113 | ✗ | ✗ |
| b07 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | - | GPL-3.0 | 125 | ✗ | ✗ |
| b13 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | - | GPL-3.0 | 320 | ✗ | ✗ |
| b09 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | - | GPL-3.0 | 91 | ✗ | ✗ |
| b10 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | - | GPL-3.0 | 178 | ✗ | ✗ |
| b03 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | - | GPL-3.0 | 133 | ✗ | ✗ |
| b08 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | - | GPL-3.0 | 88 | ✗ | ✗ |
| b06 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | - | GPL-3.0 | 130 | ✗ | ✗ |
| multiclock_reader_writer | - | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | per design | 61 | ✗ | ✗ |
| b02 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | - | GPL-3.0 | 74 | ✗ | ✗ |
| b01 | - | [itc99](#sources) | [repo](https://github.com/ccsl-uaegean/ITC99-RTL-Verilog) | - | GPL-3.0 | 117 | ✗ | ✗ |
| multiclock_output_and_latch | - | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | per design | 63 | ✗ | ✗ |
| multiclock_separate_and_latch | - | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | per design | 53 | ✗ | ✗ |
| and_latch | - | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | per design | 21 | ✗ | ✗ |
| single_ff | - | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | per design | 5 | ✗ | ✗ |
| single_wire | - | [vtr-verilog](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | per design | 3 | ✗ | ✗ |
| a-z80 | A-Z80 CPU | [opencores](#sources) | [repo](https://opencores.org/projects) | - | per project | 5649 | ✗ | ✗ |
| amber | Amber ARM-compatible core | [opencores](#sources) | [repo](https://opencores.org/projects) | - | per project | 5419 | ✗ | ✗ |

<details><summary>Flow and VTR QoR</summary>

| design | iverilog | Odin sim | VTR stage | LUTs | blocks | FFs | pins | mult/mem | cpd ns | chan w | status | note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LU64PEEng | - | - | route | 131211 | 15299 | 37270 | 216 | 64/10372 | 71.2027 | 118 | - | - |
| mcml | - | - | route | 75336 | 7421 | 51494 | 392 | 27/348 | 46.605 | 124 | - | - |
| LU32PEEng | - | - | route | 66933 | 7915 | 19668 | 216 | 32/5251 | 70.3903 | 100 | - | - |
| stereovision2 | - | - | - | 7914 | 1689 | 15573 | 331 | 468/0 | 13.2648 | 90 | - | - |
| bgm | - | - | route | 25388 | 3074 | 5105 | 290 | 11/0 | 23.8936 | 90 | - | - |
| LU8PEEng | - | - | route | 19051 | 2400 | 6224 | 216 | 8/1409 | 76.1243 | 84 | - | - |
| stereovision1 | - | - | - | 6305 | 758 | 10315 | 278 | 152/0 | 5.72613 | 76 | - | - |
| stereovision0 | - | - | - | 6801 | 702 | 11458 | 366 | 0/0 | 3.8277 | 52 | - | - |
| raygentop_nolatches | - | - | route | 1693 | 758 | 1398 | 560 | 18/21 | 4.86647 | 58 | - | - |
| arm_core | - | - | route | 10707 | 1310 | 3943 | 313 | 0/1192 | 24.503 | 98 | - | - |
| or1200 | - | - | - | 2204 | 237 | 672 | 782 | 1/64 | 8.74562 | 82 | - | - |
| raygentop | - | - | - | 1069 | 127 | 946 | 560 | 15/21 | 5.43116 | 56 | - | - |
| b22 | - | - | - | - | - | - | - | - | - | - | - | - |
| blob_merge | - | - | - | 3140 | 486 | 575 | 232 | 0/0 | 14.668 | 62 | - | - |
| b17 | - | - | - | - | - | - | - | - | - | - | - | - |
| b20 | - | - | - | - | - | - | - | - | - | - | - | - |
| b21 | - | - | - | - | - | - | - | - | - | - | - | - |
| diffeq1 | - | - | - | 230 | 31 | 193 | 258 | 5/0 | 17.2038 | 58 | - | - |
| b18 | - | - | - | - | - | - | - | - | - | - | - | - |
| b19 | - | - | - | - | - | - | - | - | - | - | - | - |
| boundtop | - | - | - | 538 | 41 | 383 | 468 | 0/32 | 3.06393 | 40 | - | - |
| boundtop_nolatches | - | - | route | 378 | 378 | 209 | 468 | 0/32 | 2.3407 | 40 | - | - |
| b15 | - | - | - | - | - | - | - | - | - | - | - | - |
| spree | - | - | route | 669 | 144 | 200 | 164 | 1/128 | 12.1663 | 58 | - | - |
| attiny_atmega_xmega_core | none | none | timing | 1973 | 186 | 373 | 2 | 1/0 | 14.924 | 66 | provisional (rel-main2) | - |
| mkDelayWorker32B | - | - | - | 436 | 63 | 34 | 1066 | 0/1336 | 6.8227 | 38 | - | - |
| sha | - | - | - | 1289 | 142 | 893 | 74 | 0/0 | 9.86096 | 64 | - | - |
| mkSMAdapter4B | - | - | - | 1045 | 118 | 639 | 403 | 0/153 | 6.19734 | 48 | - | - |
| b14 | - | - | - | - | - | - | - | - | - | - | - | - |
| b12 | - | - | - | - | - | - | - | - | - | - | - | - |
| b11 | - | - | - | - | - | - | - | - | - | - | - | - |
| mkPktMerge | - | - | - | 176 | 19 | 18 | 467 | 0/459 | 4.09815 | 36 | - | - |
| ch_intrinsics_nolatches | - | - | route | 128 | 245 | 82 | 229 | 0/8 | 2.09608 | 38 | - | - |
| b05 | - | - | - | - | - | - | - | - | - | - | - | - |
| stereovision3 | - | - | - | 169 | 15 | 120 | 53 | 0/0 | 2.63369 | 30 | - | - |
| ch_intrinsics | - | - | - | 95 | 12 | 82 | 229 | 0/8 | 2.12094 | 38 | - | - |
| diffeq2 | - | - | - | 134 | 22 | 96 | 162 | 5/0 | 13.5453 | 44 | - | - |
| b04 | - | - | - | - | - | - | - | - | - | - | - | - |
| b07 | - | - | - | - | - | - | - | - | - | - | - | - |
| b13 | - | - | - | - | - | - | - | - | - | - | - | - |
| b09 | - | - | - | - | - | - | - | - | - | - | - | - |
| b10 | - | - | - | - | - | - | - | - | - | - | - | - |
| b03 | - | - | - | - | - | - | - | - | - | - | - | - |
| b08 | - | - | - | - | - | - | - | - | - | - | - | - |
| b06 | - | - | - | - | - | - | - | - | - | - | - | - |
| multiclock_reader_writer | - | - | route | 11 | 6 | 11 | 4 | 0/0 | 1.45 | 18 | - | - |
| b02 | - | - | - | - | - | - | - | - | - | - | - | - |
| b01 | - | - | - | - | - | - | - | - | - | - | - | - |
| multiclock_output_and_latch | - | - | route | 3 | 9 | 3 | 7 | 0/0 | 1.25967 | 20 | - | - |
| multiclock_separate_and_latch | - | - | route | 2 | 10 | 2 | 8 | 0/0 | 0.807175 | 20 | - | - |
| and_latch | - | - | route | 1 | 5 | 1 | 4 | 0/0 | 1.52719 | 20 | - | - |
| single_ff | - | - | route | 0 | 4 | 1 | 3 | 0/0 | 1.45102 | 26 | - | - |
| single_wire | - | - | route | 0 | 2 | 0 | 2 | 0/0 | 0.20678 | 26 | - | - |
| a-z80 | none | none | none | - | - | - | - | - | - | - | provisional (rel-main2) | needs a bus patch: db0/db1/db2 segments joined by data_switch (bidirectional switch, tristate pass leaves them); see a-z80-modified (mux-driven bus variant, same flow, runs) |
| amber | none | none | map | - | - | - | - | - | - | - | re-run 2026-11-05 (VTR) | generic_sram_byte_en fixed (#345); next stop: lower: module 'a23_core': '$mem' '$c2032' would create 28238599 nodes (cap 16777216) |

</details>

<details><summary>LUT forms</summary>

| design | gates/d | 4-LUT/d | 6-LUT/d |
|---|---|---|---|
| LU64PEEng | fail: too big for now (timeout 900 s, last finished pass levelize)/fail: too big for now (timeout 900 s, last finished pass levelize) | fail: too big for now (timeout 900 s, last finished pass levelize)/fail: too big for now (timeout 900 s, last finished pass levelize) | fail: too big for now (timeout 900 s, last finished pass levelize)/fail: too big for now (timeout 900 s, last finished pass levelize) |
| mcml | fail: too big for now (timeout 900 s, last finished pass levelize)/fail: too big for now (timeout 900 s, last finished pass levelize) | fail: too big for now (timeout 900 s, last finished pass levelize)/fail: too big for now (timeout 900 s, last finished pass levelize) | fail: too big for now (timeout 900 s, last finished pass levelize)/fail: too big for now (timeout 900 s, last finished pass levelize) |
| LU32PEEng | fail: too big for now (timeout 900 s, last finished pass levelize)/fail: too big for now (timeout 900 s, last finished pass levelize) | fail: too big for now (timeout 900 s, last finished pass levelize)/fail: too big for now (timeout 900 s, last finished pass levelize) | fail: too big for now (timeout 900 s, last finished pass levelize)/fail: too big for now (timeout 900 s, last finished pass levelize) |
| stereovision2 | 431409/79 | 69596/24 | 48816/15 |
| bgm | 327394/126 | 62083/31 | 46209/21 |
| LU8PEEng | 245206/475 | 58986/161 | 43631/102 |
| stereovision1 | 139252/27 | 38630/12 | 27709/7 |
| stereovision0 | 42435/26 | 16352/7 | 14355/5 |
| raygentop_nolatches | 66497/35 | 17928/19 | 12895/12 |
| arm_core | fail: too big for now (timeout 900 s, last finished pass levelize)/fail: too big for now (timeout 900 s, last finished pass levelize) | fail: too big for now (timeout 900 s, last finished pass levelize)/fail: too big for now (timeout 900 s, last finished pass levelize) | fail: too big for now (timeout 900 s, last finished pass levelize)/fail: too big for now (timeout 900 s, last finished pass levelize) |
| or1200 | 53698/69 | 14002/44 | 10160/27 |
| raygentop | 55714/35 | 12480/19 | 8947/12 |
| b22 | 56695/105 | 8495/33 | 6234/20 |
| blob_merge | 61064/78 | 8741/30 | 5264/18 |
| b17 | 107358/80 | 7388/19 | 5240/12 |
| b20 | 37565/105 | 5680/33 | 4108/20 |
| b21 | 38305/105 | 5603/34 | 4058/21 |
| diffeq1 | 14398/101 | 4897/34 | 3585/23 |
| b18 | 36964/105 | 4976/0 | 3500/0 |
| b19 | 36964/105 | 4976/0 | 3500/0 |
| boundtop | 14741/35 | 3101/7 | 2426/4 |
| boundtop_nolatches | 18011/35 | 3235/7 | 2421/4 |
| b15 | 26705/80 | 3326/19 | 2322/12 |
| spree | 11441/103 | 3289/29 | 2321/17 |
| attiny_atmega_xmega_core | - | - | - |
| mkDelayWorker32B | 28203/41 | 1812/6 | 1633/5 |
| sha | 8125/79 | 2788/30 | 1583/20 |
| mkSMAdapter4B | 11046/34 | 1929/12 | 1372/7 |
| b14 | 9335/105 | 1352/32 | 984/20 |
| b12 | 5026/26 | 673/8 | 484/5 |
| b11 | 3924/39 | 515/14 | 357/9 |
| mkPktMerge | 1460/19 | 346/2 | 274/2 |
| ch_intrinsics_nolatches | 639/8 | 225/3 | 213/3 |
| b05 | 20479/98 | 306/12 | 196/8 |
| stereovision3 | 2042/17 | 233/5 | 175/4 |
| ch_intrinsics | 405/8 | 139/3 | 127/3 |
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
| a-z80 | - | - | - |
| amber | - | - | - |

</details>

<details><summary>Properties</summary>

| design | seq | mem | mul | add | fsm | latch | hier | bbox |
|---|---|---|---|---|---|---|---|---|
| LU64PEEng | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| mcml | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| LU32PEEng | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| stereovision2 | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ |
| bgm | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ |
| LU8PEEng | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| stereovision1 | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| stereovision0 | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ | ✓ | ✓ |
| raygentop_nolatches | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| arm_core | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✓ |
| or1200 | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ |
| raygentop | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| b22 | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ |
| blob_merge | ✓ | ✗ | ✗ | ✓ | ✓ | ✗ | ✓ | ✗ |
| b17 | ✓ | ✗ | ✗ | ✓ | ✓ | ✗ | ✓ | ✗ |
| b20 | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ |
| b21 | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ |
| diffeq1 | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| b18 | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| b19 | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| boundtop | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✓ | ✓ |
| boundtop_nolatches | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✓ | ✓ |
| b15 | ✓ | ✗ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ |
| spree | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| attiny_atmega_xmega_core | - | - | - | - | - | - | - | - |
| mkDelayWorker32B | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✓ |
| sha | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| mkSMAdapter4B | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✓ |
| b14 | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| b12 | ✓ | ✗ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ |
| b11 | ✓ | ✗ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ |
| mkPktMerge | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✓ |
| ch_intrinsics_nolatches | ✓ | ✓ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ |
| b05 | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| stereovision3 | ✓ | ✗ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ |
| ch_intrinsics | ✓ | ✓ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ |
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
| a-z80 | - | - | - | - | - | - | - | - |
| amber | - | - | - | - | - | - | - | - |

</details>

<details><summary>Silicon</summary>

| design | cells | core um2 | LVS | Si stage |
|---|---|---|---|---|
| LU64PEEng | - | - | - | - |
| mcml | - | - | - | - |
| LU32PEEng | - | - | - | - |
| stereovision2 | - | - | - | - |
| bgm | - | - | - | - |
| LU8PEEng | - | - | - | - |
| stereovision1 | - | - | - | - |
| stereovision0 | - | - | - | - |
| raygentop_nolatches | - | - | - | - |
| arm_core | - | - | - | - |
| or1200 | - | - | - | - |
| raygentop | - | - | - | - |
| b22 | - | - | - | - |
| blob_merge | - | - | - | - |
| b17 | - | - | - | - |
| b20 | - | - | - | - |
| b21 | - | - | - | - |
| diffeq1 | - | - | - | - |
| b18 | - | - | - | - |
| b19 | - | - | - | - |
| boundtop | - | - | - | - |
| boundtop_nolatches | - | - | - | - |
| b15 | - | - | - | - |
| spree | - | - | - | - |
| attiny_atmega_xmega_core | - | - | - | - |
| mkDelayWorker32B | - | - | - | - |
| sha | - | - | - | - |
| mkSMAdapter4B | - | - | - | - |
| b14 | - | - | - | - |
| b12 | - | - | - | - |
| b11 | - | - | - | - |
| mkPktMerge | - | - | - | - |
| ch_intrinsics_nolatches | - | - | - | - |
| b05 | - | - | - | - |
| stereovision3 | - | - | - | - |
| ch_intrinsics | - | - | - | - |
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
| a-z80 | - | - | - | - |
| amber | - | - | - | - |

</details>

<details><summary>Power</summary>

| design | activity | FPGA pJ/cycle | ASIC pJ/cycle | FPGA MHz | power note |
|---|---|---|---|---|---|
| LU64PEEng | - | - | - | - | - |
| mcml | - | - | - | - | - |
| LU32PEEng | - | - | - | - | - |
| stereovision2 | - | - | - | - | - |
| bgm | - | - | - | - | - |
| LU8PEEng | - | - | - | - | - |
| stereovision1 | - | - | - | - | - |
| stereovision0 | - | - | - | - | - |
| raygentop_nolatches | - | - | - | - | - |
| arm_core | - | - | - | - | - |
| or1200 | - | - | - | - | - |
| raygentop | - | - | - | - | - |
| b22 | - | - | - | - | - |
| blob_merge | - | - | - | - | - |
| b17 | - | - | - | - | - |
| b20 | - | - | - | - | - |
| b21 | - | - | - | - | - |
| diffeq1 | - | - | - | - | - |
| b18 | - | - | - | - | - |
| b19 | - | - | - | - | - |
| boundtop | - | - | - | - | - |
| boundtop_nolatches | - | - | - | - | - |
| b15 | - | - | - | - | - |
| spree | - | - | - | - | - |
| attiny_atmega_xmega_core | ace2 | 147.7 | - | 62.0 | matched 0.848; ACE2 vectorless, primary inputs p=0.5 activity=0.2 |
| mkDelayWorker32B | - | - | - | - | - |
| sha | ace2 | 94.86 | - | 97.9 | matched 0.687; ACE2 vectorless, primary inputs p=0.5 activity=0.2 |
| mkSMAdapter4B | - | - | - | - | - |
| b14 | - | - | - | - | - |
| b12 | - | - | - | - | - |
| b11 | - | - | - | - | - |
| mkPktMerge | - | - | - | - | - |
| ch_intrinsics_nolatches | - | - | - | - | - |
| b05 | - | - | - | - | - |
| stereovision3 | - | - | - | - | - |
| ch_intrinsics | ace2 | 4.822 | - | 634.8 | matched 0.745; ACE2 vectorless, primary inputs p=0.5 activity=0.2 |
| diffeq2 | - | - | - | - | - |
| b04 | - | - | - | - | - |
| b07 | - | - | - | - | - |
| b13 | - | - | - | - | - |
| b09 | - | - | - | - | - |
| b10 | - | - | - | - | - |
| b03 | - | - | - | - | - |
| b08 | - | - | - | - | - |
| b06 | - | - | - | - | - |
| multiclock_reader_writer | - | - | - | - | - |
| b02 | - | - | - | - | - |
| b01 | - | - | - | - | - |
| multiclock_output_and_latch | - | - | - | - | - |
| multiclock_separate_and_latch | - | - | - | - | - |
| and_latch | - | - | - | - | - |
| single_ff | - | - | - | - | - |
| single_wire | - | - | - | - | - |
| a-z80 | - | - | - | - | - |
| amber | - | - | - | - | - |

</details>

</details>

<details><summary>T4 netlist only (219 designs)</summary>

Rule: BLIF netlist, no HDL.

| design | what it does | suite | link | view | licence | LOC | tb | vec |
|---|---|---|---|---|---|---|---|---|
| ex1010 | - | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | none-stated | - | ✗ | ✗ |
| ex1010 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| s38584.1 | - | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | none-stated | - | ✗ | ✗ |
| s38584.1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| s38417 | - | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | none-stated | - | ✗ | ✗ |
| s38417 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| pdc | - | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | none-stated | - | ✗ | ✗ |
| pdc | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| frisc | RISC Microprocessor | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | none-stated | - | ✗ | ✗ |
| frisc | RISC Microprocessor | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| elliptic | Fifth Order Elliptic Filter | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | none-stated | - | ✗ | ✗ |
| elliptic | Fifth Order Elliptic Filter | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| spla | - | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | none-stated | - | ✗ | ✗ |
| spla | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| apex2 | - | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | none-stated | - | ✗ | ✗ |
| apex2 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| des | DES data encryption circuit | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | none-stated | - | ✗ | ✗ |
| des | DES data encryption circuit | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| apex4 | - | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | none-stated | - | ✗ | ✗ |
| apex4 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| seq | - | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | none-stated | - | ✗ | ✗ |
| seq | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| alu4 | ALU | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | none-stated | - | ✗ | ✗ |
| alu4 | ALU | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| misex3 | - | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | none-stated | - | ✗ | ✗ |
| misex3 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| dsip | Encryption circuit | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | none-stated | - | ✗ | ✗ |
| dsip | Encryption circuit | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| s298 | Finite state machine "from a PLD" | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | none-stated | - | ✗ | ✗ |
| s298 | Finite state machine "from a PLD" | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| diffeq | Differential Equation Solver | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | none-stated | - | ✗ | ✗ |
| diffeq | Differential Equation Solver | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| bigkey | Key encryption circuit | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | none-stated | - | ✗ | ✗ |
| bigkey | Key encryption circuit | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| apex3 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| i10 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| C6288 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| ex5p | - | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | none-stated | - | ✗ | ✗ |
| ex5p | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| clma | Bus interface | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | none-stated | - | ✗ | ✗ |
| clma | Bus interface | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| apex1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| tseng | Bus controller | [mcnc20](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | none-stated | - | ✗ | ✗ |
| tseng | Bus controller | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| cps | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| C7552 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| pair | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| parker1986 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| table5 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| table3 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| k2 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| C5315 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| mm30a | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| i8 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| s5378 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| C3540 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| misex3c | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| s9234.1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| scf | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| apex5 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| sbc | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| dalu | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| rot | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| frg2 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| vda | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| ecc | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| e64 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| apex6 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| ex4p | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| x3 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| s1494 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| s1488 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| s1423 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| bbrtas | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| i9 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| duke2 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| C2670 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| styr | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| planet | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| planet1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| s1238 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| daio-rec | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| s1196 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| s953 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| sand | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| too-lrg | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| C499 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| ph-decod | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| alu2 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| C1908 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| mm9b | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| example2 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| gcd | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| C1355 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| x1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| x4 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| mm9a | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| s1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| s832 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| t481 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| C880 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| mult32a | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| 9sym | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| s820 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| ex1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| i5 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| i6 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| i7 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| s838.1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| clip | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| keyb | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| i2 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| rd84 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| sao2 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| s641 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| s713 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| apex7 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| s510 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| C432 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| pma | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| cse | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| i4 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| 9symml | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| dk16 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| mult16a | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| i3 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| tbk | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| cht | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| s344 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| s349 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| mm4a | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| o64 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| s386 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| b9 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| mult16b | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| s420.1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| ttt2 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| sse | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| misex2 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| s444 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| bw | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| c8 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| count | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| ldd | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| s400 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| frg1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| rd73 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| s382 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| bbsse | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| s526n | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| lal | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| s526 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| vg2 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| my-adder | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| pcler8 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| cc | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| comp | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| inc | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| term1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| ex6 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| mark1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| opus | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| sct | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| b12 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| bbara | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| ex4 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| decod | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| pm1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| s208.1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| tcon | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| unreg | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| i1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| cordic | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| cu | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| f51m | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| pcle | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| 5xp1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| s420 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| x2 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| sqrt8 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| traffic | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| cm162a | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| cm42a | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| cmb | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| s208 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| cm150a | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| sqrt8ml | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| cm138a | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| cm163a | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| dk14 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| misex1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| s838 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| squar5 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| beecount | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| dk15 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| dk512 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| cm85a | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| dk17 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| mc | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| mux | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| tav | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| bbtas | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| dk27 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| parity | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| z4ml | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| b1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| cm151a | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| s27 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| cm152a | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| cm82a | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| daio | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| lion | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| rd53 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| C17 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| con1 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| chain_cout_fanout | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| majority | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| xor5 | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |
| shiftreg | - | [vtr-blif](#sources) | [repo](https://github.com/verilog-to-routing/vtr-verilog-to-routing) | - | not read | - | ✗ | ✗ |

<details><summary>Flow and VTR QoR</summary>

| design | iverilog | Odin sim | VTR stage | LUTs | blocks | FFs | pins | mult/mem | cpd ns | chan w | status | note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ex1010 | - | - | - | 2777 | 314 | 0 | 20 | 0/0 | 9.8022 | 84 | - | - |
| ex1010 | - | - | - | - | - | - | - | - | - | - | - | - |
| s38584.1 | - | - | - | 2037 | 182 | 1141 | 343 | 0/0 | 4.65105 | 48 | - | - |
| s38584.1 | - | - | - | - | - | - | - | - | - | - | - | - |
| s38417 | - | - | - | 2066 | 179 | 1345 | 135 | 0/0 | 4.96812 | 42 | - | - |
| s38417 | - | - | - | - | - | - | - | - | - | - | - | - |
| pdc | - | - | - | 1973 | 176 | 0 | 56 | 0/0 | 7.42762 | 72 | - | - |
| pdc | - | - | - | - | - | - | - | - | - | - | - | - |
| frisc | - | - | - | 1668 | 153 | 814 | 136 | 0/0 | 8.694 | 66 | - | - |
| frisc | - | - | - | - | - | - | - | - | - | - | - | - |
| elliptic | - | - | - | 1462 | 137 | 884 | 245 | 0/0 | 7.59909 | 58 | - | - |
| elliptic | - | - | - | - | - | - | - | - | - | - | - | - |
| spla | - | - | - | 1444 | 131 | 0 | 62 | 0/0 | 6.39096 | 60 | - | - |
| spla | - | - | - | - | - | - | - | - | - | - | - | - |
| apex2 | - | - | - | 992 | 92 | 0 | 42 | 0/0 | 5.89143 | 54 | - | - |
| apex2 | - | - | - | - | - | - | - | - | - | - | - | - |
| des | - | - | - | 901 | 77 | 0 | 501 | 0/0 | 4.68402 | 38 | - | - |
| des | - | - | - | - | - | - | - | - | - | - | - | - |
| apex4 | - | - | - | 865 | 80 | 0 | 28 | 0/0 | 5.74616 | 60 | - | - |
| apex4 | - | - | - | - | - | - | - | - | - | - | - | - |
| seq | - | - | - | 855 | 75 | 0 | 76 | 0/0 | 4.95078 | 54 | - | - |
| seq | - | - | - | - | - | - | - | - | - | - | - | - |
| alu4 | - | - | - | 817 | 68 | 0 | 22 | 0/0 | 5.0705 | 42 | - | - |
| alu4 | - | - | - | - | - | - | - | - | - | - | - | - |
| misex3 | - | - | - | 714 | 62 | 0 | 28 | 0/0 | 4.81741 | 48 | - | - |
| misex3 | - | - | - | - | - | - | - | - | - | - | - | - |
| dsip | - | - | - | 682 | 66 | 224 | 426 | 0/0 | 2.72755 | 34 | - | - |
| dsip | - | - | - | - | - | - | - | - | - | - | - | - |
| s298 | - | - | - | 661 | 58 | 8 | 10 | 0/0 | 6.32231 | 46 | - | - |
| s298 | - | - | - | - | - | - | - | - | - | - | - | - |
| diffeq | - | - | - | 580 | 53 | 310 | 103 | 0/0 | 4.91464 | 42 | - | - |
| diffeq | - | - | - | - | - | - | - | - | - | - | - | - |
| bigkey | - | - | - | 568 | 52 | 224 | 460 | 0/0 | 2.59891 | 38 | - | - |
| bigkey | - | - | - | - | - | - | - | - | - | - | - | - |
| apex3 | - | - | - | - | - | - | - | - | - | - | - | - |
| i10 | - | - | - | - | - | - | - | - | - | - | - | - |
| C6288 | - | - | - | - | - | - | - | - | - | - | - | - |
| ex5p | - | - | - | 465 | 39 | 0 | 71 | 0/0 | 5.34702 | 48 | - | - |
| ex5p | - | - | - | - | - | - | - | - | - | - | - | - |
| clma | - | - | - | 445 | 82 | 26 | 465 | 0/0 | 5.41555 | 36 | - | - |
| clma | - | - | - | - | - | - | - | - | - | - | - | - |
| apex1 | - | - | - | - | - | - | - | - | - | - | - | - |
| tseng | - | - | - | 391 | 34 | 219 | 174 | 0/0 | 4.62879 | 48 | - | - |
| tseng | - | - | - | - | - | - | - | - | - | - | - | - |
| cps | - | - | - | - | - | - | - | - | - | - | - | - |
| C7552 | - | - | - | - | - | - | - | - | - | - | - | - |
| pair | - | - | - | - | - | - | - | - | - | - | - | - |
| parker1986 | - | - | - | - | - | - | - | - | - | - | - | - |
| table5 | - | - | - | - | - | - | - | - | - | - | - | - |
| table3 | - | - | - | - | - | - | - | - | - | - | - | - |
| k2 | - | - | - | - | - | - | - | - | - | - | - | - |
| C5315 | - | - | - | - | - | - | - | - | - | - | - | - |
| mm30a | - | - | - | - | - | - | - | - | - | - | - | - |
| i8 | - | - | - | - | - | - | - | - | - | - | - | - |
| s5378 | - | - | - | - | - | - | - | - | - | - | - | - |
| C3540 | - | - | - | - | - | - | - | - | - | - | - | - |
| misex3c | - | - | - | - | - | - | - | - | - | - | - | - |
| s9234.1 | - | - | - | - | - | - | - | - | - | - | - | - |
| scf | - | - | - | - | - | - | - | - | - | - | - | - |
| apex5 | - | - | - | - | - | - | - | - | - | - | - | - |
| sbc | - | - | - | - | - | - | - | - | - | - | - | - |
| dalu | - | - | - | - | - | - | - | - | - | - | - | - |
| rot | - | - | - | - | - | - | - | - | - | - | - | - |
| frg2 | - | - | - | - | - | - | - | - | - | - | - | - |
| vda | - | - | - | - | - | - | - | - | - | - | - | - |
| ecc | - | - | - | - | - | - | - | - | - | - | - | - |
| e64 | - | - | - | - | - | - | - | - | - | - | - | - |
| apex6 | - | - | - | - | - | - | - | - | - | - | - | - |
| ex4p | - | - | - | - | - | - | - | - | - | - | - | - |
| x3 | - | - | - | - | - | - | - | - | - | - | - | - |
| s1494 | - | - | - | - | - | - | - | - | - | - | - | - |
| s1488 | - | - | - | - | - | - | - | - | - | - | - | - |
| s1423 | - | - | - | - | - | - | - | - | - | - | - | - |
| bbrtas | - | - | - | - | - | - | - | - | - | - | - | - |
| i9 | - | - | - | - | - | - | - | - | - | - | - | - |
| duke2 | - | - | - | - | - | - | - | - | - | - | - | - |
| C2670 | - | - | - | - | - | - | - | - | - | - | - | - |
| styr | - | - | - | - | - | - | - | - | - | - | - | - |
| planet | - | - | - | - | - | - | - | - | - | - | - | - |
| planet1 | - | - | - | - | - | - | - | - | - | - | - | - |
| s1238 | - | - | - | - | - | - | - | - | - | - | - | - |
| daio-rec | - | - | - | - | - | - | - | - | - | - | - | - |
| s1196 | - | - | - | - | - | - | - | - | - | - | - | - |
| s953 | - | - | - | - | - | - | - | - | - | - | - | - |
| sand | - | - | - | - | - | - | - | - | - | - | - | - |
| too-lrg | - | - | - | - | - | - | - | - | - | - | - | - |
| C499 | - | - | - | - | - | - | - | - | - | - | - | - |
| ph-decod | - | - | - | - | - | - | - | - | - | - | - | - |
| alu2 | - | - | - | - | - | - | - | - | - | - | - | - |
| C1908 | - | - | - | - | - | - | - | - | - | - | - | - |
| mm9b | - | - | - | - | - | - | - | - | - | - | - | - |
| example2 | - | - | - | - | - | - | - | - | - | - | - | - |
| gcd | - | - | - | - | - | - | - | - | - | - | - | - |
| C1355 | - | - | - | - | - | - | - | - | - | - | - | - |
| x1 | - | - | - | - | - | - | - | - | - | - | - | - |
| x4 | - | - | - | - | - | - | - | - | - | - | - | - |
| mm9a | - | - | - | - | - | - | - | - | - | - | - | - |
| s1 | - | - | - | - | - | - | - | - | - | - | - | - |
| s832 | - | - | - | - | - | - | - | - | - | - | - | - |
| t481 | - | - | - | - | - | - | - | - | - | - | - | - |
| C880 | - | - | - | - | - | - | - | - | - | - | - | - |
| mult32a | - | - | - | - | - | - | - | - | - | - | - | - |
| 9sym | - | - | - | - | - | - | - | - | - | - | - | - |
| s820 | - | - | - | - | - | - | - | - | - | - | - | - |
| ex1 | - | - | - | - | - | - | - | - | - | - | - | - |
| i5 | - | - | - | - | - | - | - | - | - | - | - | - |
| i6 | - | - | - | - | - | - | - | - | - | - | - | - |
| i7 | - | - | - | - | - | - | - | - | - | - | - | - |
| s838.1 | - | - | - | - | - | - | - | - | - | - | - | - |
| clip | - | - | - | - | - | - | - | - | - | - | - | - |
| keyb | - | - | - | - | - | - | - | - | - | - | - | - |
| i2 | - | - | - | - | - | - | - | - | - | - | - | - |
| rd84 | - | - | - | - | - | - | - | - | - | - | - | - |
| sao2 | - | - | - | - | - | - | - | - | - | - | - | - |
| s641 | - | - | - | - | - | - | - | - | - | - | - | - |
| s713 | - | - | - | - | - | - | - | - | - | - | - | - |
| apex7 | - | - | - | - | - | - | - | - | - | - | - | - |
| s510 | - | - | - | - | - | - | - | - | - | - | - | - |
| C432 | - | - | - | - | - | - | - | - | - | - | - | - |
| pma | - | - | - | - | - | - | - | - | - | - | - | - |
| cse | - | - | - | - | - | - | - | - | - | - | - | - |
| i4 | - | - | - | - | - | - | - | - | - | - | - | - |
| 9symml | - | - | - | - | - | - | - | - | - | - | - | - |
| dk16 | - | - | - | - | - | - | - | - | - | - | - | - |
| mult16a | - | - | - | - | - | - | - | - | - | - | - | - |
| i3 | - | - | - | - | - | - | - | - | - | - | - | - |
| tbk | - | - | - | - | - | - | - | - | - | - | - | - |
| cht | - | - | - | - | - | - | - | - | - | - | - | - |
| s344 | - | - | - | - | - | - | - | - | - | - | - | - |
| s349 | - | - | - | - | - | - | - | - | - | - | - | - |
| mm4a | - | - | - | - | - | - | - | - | - | - | - | - |
| o64 | - | - | - | - | - | - | - | - | - | - | - | - |
| s386 | - | - | - | - | - | - | - | - | - | - | - | - |
| b9 | - | - | - | - | - | - | - | - | - | - | - | - |
| mult16b | - | - | - | - | - | - | - | - | - | - | - | - |
| s420.1 | - | - | - | - | - | - | - | - | - | - | - | - |
| ttt2 | - | - | - | - | - | - | - | - | - | - | - | - |
| sse | - | - | - | - | - | - | - | - | - | - | - | - |
| misex2 | - | - | - | - | - | - | - | - | - | - | - | - |
| s444 | - | - | - | - | - | - | - | - | - | - | - | - |
| bw | - | - | - | - | - | - | - | - | - | - | - | - |
| c8 | - | - | - | - | - | - | - | - | - | - | - | - |
| count | - | - | - | - | - | - | - | - | - | - | - | - |
| ldd | - | - | - | - | - | - | - | - | - | - | - | - |
| s400 | - | - | - | - | - | - | - | - | - | - | - | - |
| frg1 | - | - | - | - | - | - | - | - | - | - | - | - |
| rd73 | - | - | - | - | - | - | - | - | - | - | - | - |
| s382 | - | - | - | - | - | - | - | - | - | - | - | - |
| bbsse | - | - | - | - | - | - | - | - | - | - | - | - |
| s526n | - | - | - | - | - | - | - | - | - | - | - | - |
| lal | - | - | - | - | - | - | - | - | - | - | - | - |
| s526 | - | - | - | - | - | - | - | - | - | - | - | - |
| vg2 | - | - | - | - | - | - | - | - | - | - | - | - |
| my-adder | - | - | - | - | - | - | - | - | - | - | - | - |
| pcler8 | - | - | - | - | - | - | - | - | - | - | - | - |
| cc | - | - | - | - | - | - | - | - | - | - | - | - |
| comp | - | - | - | - | - | - | - | - | - | - | - | - |
| inc | - | - | - | - | - | - | - | - | - | - | - | - |
| term1 | - | - | - | - | - | - | - | - | - | - | - | - |
| ex6 | - | - | - | - | - | - | - | - | - | - | - | - |
| mark1 | - | - | - | - | - | - | - | - | - | - | - | - |
| opus | - | - | - | - | - | - | - | - | - | - | - | - |
| sct | - | - | - | - | - | - | - | - | - | - | - | - |
| b12 | - | - | - | - | - | - | - | - | - | - | - | - |
| bbara | - | - | - | - | - | - | - | - | - | - | - | - |
| ex4 | - | - | - | - | - | - | - | - | - | - | - | - |
| decod | - | - | - | - | - | - | - | - | - | - | - | - |
| pm1 | - | - | - | - | - | - | - | - | - | - | - | - |
| s208.1 | - | - | - | - | - | - | - | - | - | - | - | - |
| tcon | - | - | - | - | - | - | - | - | - | - | - | - |
| unreg | - | - | - | - | - | - | - | - | - | - | - | - |
| i1 | - | - | - | - | - | - | - | - | - | - | - | - |
| cordic | - | - | - | - | - | - | - | - | - | - | - | - |
| cu | - | - | - | - | - | - | - | - | - | - | - | - |
| f51m | - | - | - | - | - | - | - | - | - | - | - | - |
| pcle | - | - | - | - | - | - | - | - | - | - | - | - |
| 5xp1 | - | - | - | - | - | - | - | - | - | - | - | - |
| s420 | - | - | - | - | - | - | - | - | - | - | - | - |
| x2 | - | - | - | - | - | - | - | - | - | - | - | - |
| sqrt8 | - | - | - | - | - | - | - | - | - | - | - | - |
| traffic | - | - | - | - | - | - | - | - | - | - | - | - |
| cm162a | - | - | - | - | - | - | - | - | - | - | - | - |
| cm42a | - | - | - | - | - | - | - | - | - | - | - | - |
| cmb | - | - | - | - | - | - | - | - | - | - | - | - |
| s208 | - | - | - | - | - | - | - | - | - | - | - | - |
| cm150a | - | - | - | - | - | - | - | - | - | - | - | - |
| sqrt8ml | - | - | - | - | - | - | - | - | - | - | - | - |
| cm138a | - | - | - | - | - | - | - | - | - | - | - | - |
| cm163a | - | - | - | - | - | - | - | - | - | - | - | - |
| dk14 | - | - | - | - | - | - | - | - | - | - | - | - |
| misex1 | - | - | - | - | - | - | - | - | - | - | - | - |
| s838 | - | - | - | - | - | - | - | - | - | - | - | - |
| squar5 | - | - | - | - | - | - | - | - | - | - | - | - |
| beecount | - | - | - | - | - | - | - | - | - | - | - | - |
| dk15 | - | - | - | - | - | - | - | - | - | - | - | - |
| dk512 | - | - | - | - | - | - | - | - | - | - | - | - |
| cm85a | - | - | - | - | - | - | - | - | - | - | - | - |
| dk17 | - | - | - | - | - | - | - | - | - | - | - | - |
| mc | - | - | - | - | - | - | - | - | - | - | - | - |
| mux | - | - | - | - | - | - | - | - | - | - | - | - |
| tav | - | - | - | - | - | - | - | - | - | - | - | - |
| bbtas | - | - | - | - | - | - | - | - | - | - | - | - |
| dk27 | - | - | - | - | - | - | - | - | - | - | - | - |
| parity | - | - | - | - | - | - | - | - | - | - | - | - |
| z4ml | - | - | - | - | - | - | - | - | - | - | - | - |
| b1 | - | - | - | - | - | - | - | - | - | - | - | - |
| cm151a | - | - | - | - | - | - | - | - | - | - | - | - |
| s27 | - | - | - | - | - | - | - | - | - | - | - | - |
| cm152a | - | - | - | - | - | - | - | - | - | - | - | - |
| cm82a | - | - | - | - | - | - | - | - | - | - | - | - |
| daio | - | - | - | - | - | - | - | - | - | - | - | - |
| lion | - | - | - | - | - | - | - | - | - | - | - | - |
| rd53 | - | - | - | - | - | - | - | - | - | - | - | - |
| C17 | - | - | - | - | - | - | - | - | - | - | - | - |
| con1 | - | - | - | - | - | - | - | - | - | - | - | - |
| chain_cout_fanout | - | - | - | - | - | - | - | - | - | - | - | - |
| majority | - | - | - | - | - | - | - | - | - | - | - | - |
| xor5 | - | - | - | - | - | - | - | - | - | - | - | - |
| shiftreg | - | - | - | - | - | - | - | - | - | - | - | - |

</details>

<details><summary>LUT forms</summary>

| design | gates/d | 4-LUT/d | 6-LUT/d |
|---|---|---|---|
| ex1010 | 4598/8 | 4598/8 | 2777/6 |
| ex1010 | 4598/8 | 4598/8 | 2777/6 |
| s38584.1 | 6281/9 | 6269/9 | 2190/6 |
| s38584.1 | 6281/9 | 6269/9 | 2190/6 |
| s38417 | 6096/11 | 6096/11 | 2189/6 |
| s38417 | 6096/11 | 6096/11 | 2189/6 |
| pdc | 4575/9 | 4575/9 | 1973/7 |
| pdc | 4575/9 | 4575/9 | 1973/7 |
| frisc | 3539/23 | 3539/23 | 1668/12 |
| frisc | 3539/23 | 3539/23 | 1668/12 |
| elliptic | 3602/18 | 3602/18 | 1463/10 |
| elliptic | 3602/18 | 3602/18 | 1463/10 |
| spla | 3690/8 | 3690/8 | 1445/6 |
| spla | 3690/8 | 3690/8 | 1445/6 |
| apex2 | 1878/8 | 1878/8 | 992/6 |
| apex2 | 1878/8 | 1878/8 | 992/6 |
| des | 1591/6 | 1591/6 | 901/5 |
| des | 1591/6 | 1591/6 | 901/5 |
| apex4 | 1262/6 | 1261/6 | 865/5 |
| apex4 | 1262/6 | 1261/6 | 865/5 |
| seq | 1750/7 | 1750/7 | 855/5 |
| seq | 1750/7 | 1750/7 | 855/5 |
| alu4 | 1522/7 | 1522/7 | 818/5 |
| alu4 | 1522/7 | 1522/7 | 818/5 |
| misex3 | 1397/7 | 1397/7 | 714/5 |
| misex3 | 1397/7 | 1397/7 | 714/5 |
| dsip | 1370/3 | 1370/3 | 686/3 |
| dsip | 1370/3 | 1370/3 | 686/3 |
| s298 | 1930/15 | 1930/15 | 661/8 |
| s298 | 1930/15 | 1930/15 | 661/8 |
| diffeq | 1494/14 | 1494/14 | 580/8 |
| diffeq | 1494/14 | 1494/14 | 580/8 |
| bigkey | 1707/3 | 1707/3 | 572/3 |
| bigkey | 1707/3 | 1707/3 | 572/3 |
| apex3 | 869/6 | 869/6 | 540/5 |
| i10 | 995/13 | 995/13 | 540/9 |
| C6288 | 527/28 | 527/28 | 538/16 |
| ex5p | 1064/7 | 1064/7 | 467/5 |
| ex5p | 1064/7 | 1064/7 | 467/5 |
| clma | 8381/16 | 8380/16 | 450/7 |
| clma | 8381/16 | 8380/16 | 450/7 |
| apex1 | 700/7 | 699/7 | 429/5 |
| tseng | 1046/13 | 1046/13 | 407/7 |
| tseng | 1046/13 | 1046/13 | 407/7 |
| cps | 757/5 | 756/5 | 404/4 |
| C7552 | 739/10 | 739/10 | 393/7 |
| pair | 647/7 | 647/7 | 343/5 |
| parker1986 | 660/13 | 660/13 | 339/8 |
| table5 | 485/6 | 485/6 | 320/5 |
| table3 | 480/6 | 480/6 | 297/5 |
| k2 | 519/7 | 518/7 | 291/5 |
| C5315 | 620/10 | 620/10 | 287/6 |
| mm30a | 467/58 | 467/58 | 287/22 |
| i8 | 481/5 | 481/5 | 272/4 |
| s5378 | 576/6 | 571/6 | 261/3 |
| C3540 | 431/12 | 431/12 | 259/8 |
| misex3c | 549/6 | 549/6 | 239/5 |
| s9234.1 | 461/8 | 459/8 | 238/5 |
| scf | 418/5 | 416/5 | 235/4 |
| apex5 | 535/5 | 534/5 | 203/4 |
| sbc | 384/5 | 384/5 | 194/3 |
| dalu | 500/6 | 500/6 | 188/4 |
| rot | 307/8 | 307/8 | 187/5 |
| frg2 | 379/6 | 379/6 | 186/4 |
| vda | 291/6 | 291/6 | 180/4 |
| ecc | 330/5 | 330/5 | 165/4 |
| e64 | 274/4 | 274/4 | 153/3 |
| apex6 | 393/6 | 393/6 | 152/4 |
| ex4p | 445/5 | 444/5 | 151/4 |
| x3 | 377/5 | 377/5 | 149/4 |
| s1494 | 292/5 | 292/5 | 148/3 |
| s1488 | 296/4 | 296/4 | 146/3 |
| s1423 | 221/15 | 221/15 | 142/10 |
| bbrtas | 406/18 | 406/18 | 135/9 |
| i9 | 376/5 | 376/5 | 131/4 |
| duke2 | 251/5 | 251/5 | 130/4 |
| C2670 | 259/7 | 258/7 | 129/5 |
| styr | 238/5 | 238/5 | 128/4 |
| planet | 266/4 | 266/4 | 127/3 |
| planet1 | 266/4 | 266/4 | 127/3 |
| s1238 | 292/8 | 292/8 | 127/5 |
| daio-rec | 311/7 | 311/7 | 123/4 |
| s1196 | 264/7 | 264/7 | 123/5 |
| s953 | 214/5 | 214/5 | 122/3 |
| sand | 243/5 | 243/5 | 122/4 |
| too-lrg | 187/7 | 187/7 | 105/4 |
| C499 | 74/4 | 74/4 | 103/4 |
| ph-decod | 219/6 | 219/6 | 101/4 |
| alu2 | 197/10 | 197/10 | 98/7 |
| C1908 | 145/10 | 145/10 | 93/6 |
| mm9b | 204/20 | 204/20 | 92/9 |
| example2 | 138/4 | 138/4 | 90/3 |
| gcd | 218/11 | 218/11 | 90/5 |
| C1355 | 74/4 | 74/4 | 86/4 |
| x1 | 143/4 | 143/4 | 86/3 |
| x4 | 194/3 | 194/3 | 86/3 |
| mm9a | 142/17 | 142/17 | 84/8 |
| s1 | 195/10 | 195/10 | 83/6 |
| s832 | 145/5 | 145/5 | 81/3 |
| t481 | 214/7 | 214/7 | 81/5 |
| C880 | 174/9 | 174/9 | 78/6 |
| mult32a | 116/24 | 116/24 | 76/14 |
| 9sym | 144/6 | 144/6 | 75/4 |
| s820 | 120/5 | 120/5 | 69/3 |
| ex1 | 124/4 | 124/4 | 68/3 |
| i5 | 88/6 | 88/6 | 67/4 |
| i6 | 182/2 | 182/2 | 67/1 |
| i7 | 203/2 | 203/2 | 67/1 |
| s838.1 | 95/9 | 95/9 | 64/7 |
| clip | 140/5 | 140/5 | 59/4 |
| keyb | 103/5 | 103/5 | 58/4 |
| i2 | 74/5 | 74/5 | 57/4 |
| rd84 | 157/6 | 157/6 | 54/4 |
| sao2 | 90/5 | 90/5 | 52/3 |
| s641 | 87/9 | 87/9 | 51/4 |
| s713 | 88/8 | 88/8 | 51/4 |
| apex7 | 102/5 | 102/5 | 50/3 |
| s510 | 101/5 | 101/5 | 49/3 |
| C432 | 124/11 | 124/11 | 48/8 |
| pma | 85/4 | 85/4 | 44/3 |
| cse | 90/4 | 90/4 | 42/3 |
| i4 | 98/5 | 98/5 | 42/3 |
| 9symml | 97/6 | 97/6 | 40/4 |
| dk16 | 105/4 | 105/4 | 39/3 |
| mult16a | 57/12 | 57/12 | 39/7 |
| i3 | 46/3 | 46/3 | 38/3 |
| tbk | 84/8 | 84/8 | 38/6 |
| cht | 55/2 | 55/2 | 36/1 |
| s344 | 67/4 | 67/4 | 36/2 |
| s349 | 67/4 | 67/4 | 36/2 |
| mm4a | 78/10 | 78/10 | 35/5 |
| o64 | 46/4 | 46/4 | 34/3 |
| s386 | 56/3 | 56/3 | 33/2 |
| b9 | 46/3 | 46/3 | 32/2 |
| mult16b | 31/1 | 31/1 | 31/1 |
| s420.1 | 47/5 | 47/5 | 31/4 |
| ttt2 | 75/4 | 75/4 | 31/3 |
| sse | 64/6 | 64/6 | 30/4 |
| misex2 | 49/3 | 49/3 | 29/2 |
| s444 | 62/4 | 62/4 | 29/3 |
| bw | 132/4 | 132/4 | 28/1 |
| c8 | 39/4 | 39/4 | 28/2 |
| count | 39/5 | 39/5 | 28/4 |
| ldd | 37/5 | 37/5 | 28/3 |
| s400 | 69/4 | 69/4 | 28/3 |
| frg1 | 49/6 | 49/6 | 27/4 |
| rd73 | 83/5 | 83/5 | 27/3 |
| s382 | 60/4 | 60/4 | 27/3 |
| bbsse | 64/6 | 64/6 | 26/4 |
| s526n | 60/4 | 60/4 | 26/3 |
| lal | 34/3 | 34/3 | 25/2 |
| s526 | 52/4 | 52/4 | 25/3 |
| vg2 | 67/4 | 67/4 | 25/3 |
| my-adder | 47/16 | 47/16 | 24/8 |
| pcler8 | 35/4 | 35/4 | 24/3 |
| cc | 26/3 | 26/3 | 21/2 |
| comp | 40/5 | 40/5 | 21/4 |
| inc | 64/4 | 64/4 | 21/2 |
| term1 | 88/5 | 88/5 | 20/3 |
| ex6 | 60/7 | 60/7 | 19/3 |
| mark1 | 37/3 | 34/3 | 19/2 |
| opus | 50/5 | 50/5 | 19/3 |
| sct | 23/3 | 23/3 | 19/2 |
| b12 | 56/4 | 56/4 | 18/2 |
| bbara | 33/3 | 33/3 | 18/2 |
| ex4 | 35/4 | 35/4 | 17/2 |
| decod | 20/2 | 20/2 | 16/1 |
| pm1 | 19/3 | 19/3 | 16/2 |
| s208.1 | 24/4 | 24/4 | 16/3 |
| tcon | 16/1 | 16/1 | 16/1 |
| unreg | 48/2 | 48/2 | 16/1 |
| i1 | 21/3 | 21/3 | 15/2 |
| cordic | 466/9 | 466/9 | 14/6 |
| cu | 22/3 | 22/3 | 14/2 |
| f51m | 54/4 | 54/4 | 14/3 |
| pcle | 21/3 | 21/3 | 14/2 |
| 5xp1 | 57/4 | 57/4 | 13/2 |
| s420 | 23/3 | 23/3 | 13/2 |
| x2 | 17/3 | 17/3 | 13/2 |
| sqrt8 | 29/4 | 29/4 | 12/3 |
| traffic | 35/3 | 35/3 | 11/2 |
| cm162a | 18/3 | 18/3 | 10/2 |
| cm42a | 10/1 | 10/1 | 10/1 |
| cmb | 17/3 | 17/3 | 10/2 |
| s208 | 18/3 | 18/3 | 10/2 |
| cm150a | 14/3 | 14/3 | 9/3 |
| sqrt8ml | 31/6 | 31/6 | 9/2 |
| cm138a | 10/2 | 10/2 | 8/1 |
| cm163a | 11/3 | 11/3 | 8/2 |
| dk14 | 43/7 | 43/7 | 8/1 |
| misex1 | 21/3 | 21/3 | 8/2 |
| s838 | 167/8 | 167/8 | 8/2 |
| squar5 | 34/3 | 34/3 | 8/1 |
| beecount | 14/2 | 14/2 | 7/1 |
| dk15 | 24/3 | 24/3 | 7/1 |
| dk512 | 14/2 | 14/2 | 7/1 |
| cm85a | 11/3 | 11/3 | 6/2 |
| dk17 | 15/2 | 15/2 | 6/1 |
| mc | 7/2 | 7/2 | 6/1 |
| mux | 15/4 | 15/4 | 6/3 |
| tav | 9/2 | 9/2 | 6/1 |
| bbtas | 6/2 | 6/2 | 5/1 |
| dk27 | 5/1 | 5/1 | 5/1 |
| parity | 5/2 | 5/2 | 5/2 |
| z4ml | 8/3 | 8/3 | 5/2 |
| b1 | 4/1 | 4/1 | 4/1 |
| cm151a | 8/3 | 8/3 | 4/2 |
| s27 | 6/2 | 6/2 | 4/1 |
| cm152a | 6/3 | 6/3 | 3/2 |
| cm82a | 4/2 | 4/2 | 3/1 |
| daio | 3/1 | 3/1 | 3/1 |
| lion | 3/1 | 3/1 | 3/1 |
| rd53 | 12/4 | 12/4 | 3/1 |
| C17 | 2/1 | 2/1 | 2/1 |
| con1 | 5/2 | 5/2 | 2/1 |
| chain_cout_fanout | 2/18 | 1/1 | 1/1 |
| majority | 3/2 | 3/2 | 1/1 |
| xor5 | 2/2 | 2/2 | 1/1 |
| shiftreg | 0/0 | 0/0 | 0/0 |

</details>

<details><summary>Properties</summary>

| design | seq | mem | mul | add | fsm | latch | hier | bbox |
|---|---|---|---|---|---|---|---|---|
| ex1010 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| ex1010 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| s38584.1 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| s38584.1 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| s38417 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| s38417 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| pdc | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| pdc | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| frisc | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| frisc | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| elliptic | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| elliptic | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| spla | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| spla | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| apex2 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| apex2 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| des | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| des | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| apex4 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| apex4 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| seq | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| seq | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| alu4 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| alu4 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| misex3 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| misex3 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| dsip | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| dsip | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| s298 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| s298 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| diffeq | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| diffeq | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| bigkey | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| bigkey | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| apex3 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| i10 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| C6288 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| ex5p | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| ex5p | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| clma | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| clma | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| apex1 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| tseng | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| tseng | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| cps | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| C7552 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| pair | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| parker1986 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| table5 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| table3 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| k2 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| C5315 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| mm30a | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| i8 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| s5378 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| C3540 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| misex3c | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| s9234.1 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| scf | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| apex5 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| sbc | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| dalu | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| rot | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| frg2 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| vda | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| ecc | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| e64 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| apex6 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| ex4p | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| x3 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| s1494 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| s1488 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| s1423 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| bbrtas | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| i9 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| duke2 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| C2670 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| styr | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| planet | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| planet1 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| s1238 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| daio-rec | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| s1196 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| s953 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| sand | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| too-lrg | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| C499 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| ph-decod | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| alu2 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| C1908 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| mm9b | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| example2 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| gcd | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| C1355 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| x1 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| x4 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| mm9a | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| s1 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| s832 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| t481 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| C880 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| mult32a | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| 9sym | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| s820 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| ex1 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| i5 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| i6 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| i7 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| s838.1 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| clip | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| keyb | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| i2 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| rd84 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| sao2 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| s641 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| s713 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| apex7 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| s510 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| C432 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| pma | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| cse | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| i4 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| 9symml | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| dk16 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| mult16a | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| i3 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| tbk | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| cht | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| s344 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| s349 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| mm4a | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| o64 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| s386 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| b9 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| mult16b | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| s420.1 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| ttt2 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| sse | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| misex2 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| s444 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| bw | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| c8 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| count | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| ldd | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| s400 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| frg1 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| rd73 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| s382 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| bbsse | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| s526n | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| lal | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| s526 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| vg2 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| my-adder | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| pcler8 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| cc | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| comp | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| inc | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| term1 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| ex6 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| mark1 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| opus | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| sct | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| b12 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| bbara | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| ex4 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| decod | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| pm1 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| s208.1 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| tcon | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| unreg | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| i1 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| cordic | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| cu | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| f51m | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| pcle | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| 5xp1 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| s420 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| x2 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| sqrt8 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| traffic | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| cm162a | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| cm42a | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| cmb | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| s208 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| cm150a | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| sqrt8ml | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| cm138a | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| cm163a | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| dk14 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| misex1 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| s838 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| squar5 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| beecount | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| dk15 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| dk512 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| cm85a | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| dk17 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| mc | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| mux | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| tav | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| bbtas | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| dk27 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| parity | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| z4ml | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| b1 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| cm151a | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| s27 | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| cm152a | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| cm82a | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| daio | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| lion | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| rd53 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| C17 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| con1 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| chain_cout_fanout | ✓ | ✗ | ✗ | ✓ | n/a | n/a | ✗ | ✗ |
| majority | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| xor5 | ✗ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| shiftreg | ✓ | ✗ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |

</details>

<details><summary>Silicon</summary>

| design | cells | core um2 | LVS | Si stage |
|---|---|---|---|---|
| ex1010 | - | - | - | - |
| ex1010 | - | - | - | - |
| s38584.1 | - | - | - | - |
| s38584.1 | - | - | - | - |
| s38417 | - | - | - | - |
| s38417 | - | - | - | - |
| pdc | - | - | - | - |
| pdc | - | - | - | - |
| frisc | - | - | - | - |
| frisc | - | - | - | - |
| elliptic | - | - | - | - |
| elliptic | - | - | - | - |
| spla | - | - | - | - |
| spla | - | - | - | - |
| apex2 | - | - | - | - |
| apex2 | - | - | - | - |
| des | - | - | - | - |
| des | - | - | - | - |
| apex4 | - | - | - | - |
| apex4 | - | - | - | - |
| seq | - | - | - | - |
| seq | - | - | - | - |
| alu4 | - | - | - | - |
| alu4 | - | - | - | - |
| misex3 | - | - | - | - |
| misex3 | - | - | - | - |
| dsip | - | - | - | - |
| dsip | - | - | - | - |
| s298 | - | - | - | - |
| s298 | - | - | - | - |
| diffeq | - | - | - | - |
| diffeq | - | - | - | - |
| bigkey | - | - | - | - |
| bigkey | - | - | - | - |
| apex3 | - | - | - | - |
| i10 | - | - | - | - |
| C6288 | - | - | - | - |
| ex5p | - | - | - | - |
| ex5p | - | - | - | - |
| clma | - | - | - | - |
| clma | - | - | - | - |
| apex1 | - | - | - | - |
| tseng | - | - | - | - |
| tseng | - | - | - | - |
| cps | - | - | - | - |
| C7552 | - | - | - | - |
| pair | - | - | - | - |
| parker1986 | - | - | - | - |
| table5 | - | - | - | - |
| table3 | - | - | - | - |
| k2 | - | - | - | - |
| C5315 | - | - | - | - |
| mm30a | - | - | - | - |
| i8 | - | - | - | - |
| s5378 | - | - | - | - |
| C3540 | - | - | - | - |
| misex3c | - | - | - | - |
| s9234.1 | - | - | - | - |
| scf | - | - | - | - |
| apex5 | - | - | - | - |
| sbc | - | - | - | - |
| dalu | - | - | - | - |
| rot | - | - | - | - |
| frg2 | - | - | - | - |
| vda | - | - | - | - |
| ecc | - | - | - | - |
| e64 | - | - | - | - |
| apex6 | - | - | - | - |
| ex4p | - | - | - | - |
| x3 | - | - | - | - |
| s1494 | - | - | - | - |
| s1488 | - | - | - | - |
| s1423 | - | - | - | - |
| bbrtas | - | - | - | - |
| i9 | - | - | - | - |
| duke2 | - | - | - | - |
| C2670 | - | - | - | - |
| styr | - | - | - | - |
| planet | - | - | - | - |
| planet1 | - | - | - | - |
| s1238 | - | - | - | - |
| daio-rec | - | - | - | - |
| s1196 | - | - | - | - |
| s953 | - | - | - | - |
| sand | - | - | - | - |
| too-lrg | - | - | - | - |
| C499 | - | - | - | - |
| ph-decod | - | - | - | - |
| alu2 | - | - | - | - |
| C1908 | - | - | - | - |
| mm9b | - | - | - | - |
| example2 | - | - | - | - |
| gcd | - | - | - | - |
| C1355 | - | - | - | - |
| x1 | - | - | - | - |
| x4 | - | - | - | - |
| mm9a | - | - | - | - |
| s1 | - | - | - | - |
| s832 | - | - | - | - |
| t481 | - | - | - | - |
| C880 | - | - | - | - |
| mult32a | - | - | - | - |
| 9sym | - | - | - | - |
| s820 | - | - | - | - |
| ex1 | - | - | - | - |
| i5 | - | - | - | - |
| i6 | - | - | - | - |
| i7 | - | - | - | - |
| s838.1 | - | - | - | - |
| clip | - | - | - | - |
| keyb | - | - | - | - |
| i2 | - | - | - | - |
| rd84 | - | - | - | - |
| sao2 | - | - | - | - |
| s641 | - | - | - | - |
| s713 | - | - | - | - |
| apex7 | - | - | - | - |
| s510 | - | - | - | - |
| C432 | - | - | - | - |
| pma | - | - | - | - |
| cse | - | - | - | - |
| i4 | - | - | - | - |
| 9symml | - | - | - | - |
| dk16 | - | - | - | - |
| mult16a | - | - | - | - |
| i3 | - | - | - | - |
| tbk | - | - | - | - |
| cht | - | - | - | - |
| s344 | - | - | - | - |
| s349 | - | - | - | - |
| mm4a | - | - | - | - |
| o64 | - | - | - | - |
| s386 | - | - | - | - |
| b9 | - | - | - | - |
| mult16b | - | - | - | - |
| s420.1 | - | - | - | - |
| ttt2 | - | - | - | - |
| sse | - | - | - | - |
| misex2 | - | - | - | - |
| s444 | - | - | - | - |
| bw | - | - | - | - |
| c8 | - | - | - | - |
| count | - | - | - | - |
| ldd | - | - | - | - |
| s400 | - | - | - | - |
| frg1 | - | - | - | - |
| rd73 | - | - | - | - |
| s382 | - | - | - | - |
| bbsse | - | - | - | - |
| s526n | - | - | - | - |
| lal | - | - | - | - |
| s526 | - | - | - | - |
| vg2 | - | - | - | - |
| my-adder | - | - | - | - |
| pcler8 | - | - | - | - |
| cc | - | - | - | - |
| comp | - | - | - | - |
| inc | - | - | - | - |
| term1 | - | - | - | - |
| ex6 | - | - | - | - |
| mark1 | - | - | - | - |
| opus | - | - | - | - |
| sct | - | - | - | - |
| b12 | - | - | - | - |
| bbara | - | - | - | - |
| ex4 | - | - | - | - |
| decod | - | - | - | - |
| pm1 | - | - | - | - |
| s208.1 | - | - | - | - |
| tcon | - | - | - | - |
| unreg | - | - | - | - |
| i1 | - | - | - | - |
| cordic | - | - | - | - |
| cu | - | - | - | - |
| f51m | - | - | - | - |
| pcle | - | - | - | - |
| 5xp1 | - | - | - | - |
| s420 | - | - | - | - |
| x2 | - | - | - | - |
| sqrt8 | - | - | - | - |
| traffic | - | - | - | - |
| cm162a | - | - | - | - |
| cm42a | - | - | - | - |
| cmb | - | - | - | - |
| s208 | - | - | - | - |
| cm150a | - | - | - | - |
| sqrt8ml | - | - | - | - |
| cm138a | - | - | - | - |
| cm163a | - | - | - | - |
| dk14 | - | - | - | - |
| misex1 | - | - | - | - |
| s838 | - | - | - | - |
| squar5 | - | - | - | - |
| beecount | - | - | - | - |
| dk15 | - | - | - | - |
| dk512 | - | - | - | - |
| cm85a | - | - | - | - |
| dk17 | - | - | - | - |
| mc | - | - | - | - |
| mux | - | - | - | - |
| tav | - | - | - | - |
| bbtas | - | - | - | - |
| dk27 | - | - | - | - |
| parity | - | - | - | - |
| z4ml | - | - | - | - |
| b1 | - | - | - | - |
| cm151a | - | - | - | - |
| s27 | - | - | - | - |
| cm152a | - | - | - | - |
| cm82a | - | - | - | - |
| daio | - | - | - | - |
| lion | - | - | - | - |
| rd53 | - | - | - | - |
| C17 | - | - | - | - |
| con1 | - | - | - | - |
| chain_cout_fanout | - | - | - | - |
| majority | - | - | - | - |
| xor5 | - | - | - | - |
| shiftreg | - | - | - | - |

</details>

</details>

<a id="sources"></a>

### Sources

- **brisc-v**: BRISC-V microcontroller (Arduino-on-RISC-V, Quartus project revert_timer). Upstream https://github.com/qiany21/Arduino-on-RISC-V.git at 1d5b591081511a8161b843d003ca7b80bad7fc45. Licence: MIT (Copyright (c) 2021 qiany21).
- **itc99**: ITC'99 (RTL Verilog, b01-b22 without b16). Upstream https://github.com/ccsl-uaegean/ITC99-RTL-Verilog at 8e6a23da036b7442ef4ea410c679d4cf21830a65. Licence: GPL-3.0 (the LICENSE file of this repository); the terms of the original ITC'99 distribution were not read.
- **mcnc20**: MCNC / LGSynth91 circuits as VTR ships them (4-LUT mapped BLIF, circuits.txt). Upstream https://github.com/verilog-to-routing/vtr-verilog-to-routing at 3c9a4d23b27d187bd67c79dc01a18ff1ffc21d9b. Licence: none-stated (data/meta/licences.toml rule mcnc); VTR LICENSE.md: MIT unless otherwise noted, in particular the benchmark circuits.
- **opencores**: OpenCores stable Verilog projects (24 designs: Peter's 2026-11-04 list without gng, DES, survey additions, verilog_cordic_core, mips_16). Upstream https://opencores.org/projects at none. Licence: per project, as the source files and the OpenCores project page state (see the licence rows of measures.tsv and docs/benchmarks/opencores.md); LGPL, GPL, Apache-2.0, BSD-style and none-stated all occur.
- **verilogeval**: VerilogEval problems (reference solutions of the spec-to-rtl dataset) with the Gate-Breaker Yosys netlists. Upstream https://github.com/NMSU-PEARL/verilog-eval.git at d60f0b10458746e2fefc2a98fa2455b77a32e8be. Licence: MIT (Copyright (c) 2023-2024 NVIDIA Research Projects).
- **vtr-blif**: VTR blif/2 and blif/4: ISCAS-85, ISCAS-89 and MCNC mapped to 2-input and 4-input LUTs. Upstream https://github.com/verilog-to-routing/vtr-verilog-to-routing at 3c9a4d23b27d187bd67c79dc01a18ff1ffc21d9b. Licence: not read: the licence of the individual ISCAS/MCNC files has not been checked.
- **vtr-verilog**: VTR Verilog benchmarks (top-level files of vtr_flow/benchmarks/verilog). Upstream https://github.com/verilog-to-routing/vtr-verilog-to-routing at 3c9a4d23b27d187bd67c79dc01a18ff1ffc21d9b. Licence: per design, as each file states (see licence_rule in designs.tsv and data/meta/licences.toml); VTR LICENSE.md: MIT unless otherwise noted, in particular the benchmark circuits.

Sortable, filterable single-table page: [catalogue.html](https://drpaj12.github.io/mimirIII/benchmarks/catalogue.html) (GitHub Pages; the file is docs/benchmarks/catalogue.html). Same tables: [docs/benchmarks/catalogue.md](docs/benchmarks/catalogue.md); method: [docs/benchmarks/catalogue-method.md](docs/benchmarks/catalogue-method.md).
<!-- catalogue:end -->
