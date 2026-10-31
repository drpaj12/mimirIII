# Mimir benchmarks: the registry of generic benchmark suites and their compiled netlists

Peter 2026-10-31: "These benchmarks should all be a mimir thing. Generic benchmarks and data. ... The made up ones we
can leave with norns." Purpose: Mimir is the dataset to mine (hub purpose; RQ Mi Q1.3, is the import complete, and the
dataset core: every value says how it was obtained, down to the raw file). One home for the third-party benchmark
suites and the netlists compiled from them, with provenance and licence, indexed and fetchable. Measures: every
registered netlist resolves to a blob that hashes to its index sha256 (target 100%); every design has a licence status;
no upstream source is copied into the repo.

## 1. What Mimir holds, and what it does not

Holds (third-party, standard): VTR Verilog benchmarks, the 20 MCNC circuits and the VTR mapped BLIF sets (2-LUT and
4-LUT: ISCAS-85, ISCAS-89, MCNC), ITC-99, VerilogEval with the Gate-Breaker netlist dataset, and the BRISC-V
microcontroller (Arduino-on-RISC-V). Also the compiled netlists of those designs (Odin III flows, a Yosys dataset).

Does not hold (made up by a tool; Peter 2026-10-31), where they live:

- Norns round 9 D' known-optimum yardsticks and round 5/6/7 synthetic designs (`n5_*`, `r5_*`, `r6_*`, `r7_*`): Norns
  (archived on the F: drive under `yggdrasil-archive`). The `norns` set no longer reads them.
- Loki round 4 families (`r4_*`, `r4t_*`) and the graphlet pattern library: Loki (agent default, controller's).
- Leman Russ Seeker v2.0 releases: Leman Russ (Mimir may index them later).
- Not yet present on this machine, so not registered: the RISC-V benchmark repository. A new suite is one entry in
  `suites.toml` plus a `mimir bench register` run.

## 2. The registry (committed, `data/benchmarks/`)

Reuses the remote-data conventions: sorted rows, `\n`, UTF-8, TSV for long tables, TOML for short records, blobs as
`<ab>/<sha256>.xz` in the existing blob store, and the `blobs.tsv.xz` format of `data/remote` (so `fetch_blob` serves
it unchanged, with `data/benchmarks` as the index dir).

- `suites.toml`, one `[[suite]]`: `id`, `title`, `format` (`verilog`, `blif`, `verilog-project`), `upstream` (URL),
  `commit` (the commit of the checkout read, or `none` for a download), `external` (directory under `$MIMIR_EXTERNAL`,
  default `<workspace>/external`) and `subdir`, `licence`, `licence_source` (file:line in the upstream), `hosting`,
  `obtained` (how Mimir obtained it), `default_flow`, `note`.
  `hosting`: `public` (licence read, redistribution allowed with the notice; netlist blobs may be hosted), `local-only`
  (licence forbids redistribution or is a restriction: registered by reference, blobs never hosted, the blob rows are
  marked `private`), `unchecked` (licence not yet read: registered by reference, no netlist blobs imported).
  No suite read here forbids redistribution; the `local-only` path exists and is tested.
- `flows.toml`, one `[[flow]]`: `id`, `tool`, `tool_version`, `tool_commit` (`not-recorded` when the data did not say),
  `binary_sha256`, `input` (`verilog`, `blif`), `arch`, `lut_k`, `script` (the command, with `<odin3>`, `<vtr>`,
  `<out>` tokens), `source` (where the flow was read), `note`.
- `designs.tsv`: `suite design slug path format top bytes lines sha256 licence_rule`. `path` is relative to the suite
  directory; `sha256` is of the source file (a project: of the sorted `name sha256` lines of its `.v` files);
  `slug` is the legacy design slug of `data/meta` (`norns/sha`, `mcnc20/alu4`) so the existing licence rules apply;
  `licence_rule` is the id of the rule that matched ("-" when none).
- `netlists.tsv`: `suite design flow sha256 raw_bytes map_sha256 flowrec_sha256 origin`. `sha256` is the netlist blob;
  `map_sha256` the Odin III name map (`.blif.names`, provenance to the HDL) or `-`; `flowrec_sha256` the flow's own
  record (`odin-meta.json`, tool commit and binary hash, params) or `-`; `origin` is a workspace-relative description
  of where the file was read. A netlist is unique per (suite, design, flow).
- `blobs.tsv.xz`: `sha256 xz_bytes raw_bytes - visibility` for every blob named in `netlists.tsv`.

## 3. Naming: how a tool refers to a benchmark

`suite:design@flow`, for example `vtr-verilog:sha@odin3-1.2.0-k6-verilog`. Without `@flow` the suite's
`default_flow` is used when the design has a netlist for it, and a design with one netlist resolves to it; otherwise
the reference is ambiguous and an error. `mimir.bench.resolve(ref)` returns the design row and the netlist row;
`mimir.bench.materialise(ref, out)` fetches the blob (local store, then `MIMIR_ARCHIVE`, cache, URL; sha256 verified)
and writes the netlist. Loki, Leman Russ and the archived Norns runs name a benchmark by this string and a sha256.

## 4. Commands

    mimir bench list [--suite S] [--netlists]      # suites, or the designs of a suite, or its netlists
    mimir bench show REF                           # design facts, licence, source, every netlist and flow
    mimir bench fetch REF [--out FILE|--kind map|flow|source]   # netlist (or its map, flow record, or source)
    mimir bench build REF --flow F --odin3 BIN     # compile a registered source, store blob, record the flow
    mimir bench register SUITE                     # rebuild the designs rows of a suite from the external checkout
    mimir bench import-odin DIR --suite S --flow F # import an Odin III netlist dir tree (`<d>/netlist/<d>.blif`)
    mimir bench check                              # index consistent, every blob present and intact

`bench build` runs the named flow's script with the given binary, hashes the output, `put`s it in the blob store and
upserts the `netlists.tsv` row; the flow record is the flow id plus the binary sha256 it ran with. It never overwrites
a different sha256 for the same (suite, design, flow): that is an error.

## 5. Flows imported

| flow id | what | read from |
|---|---|---|
| `odin3-1.2.0-k6-verilog` | Odin III 1.2.0 `b01a8034`, `read_verilog --nolatches --vtr-compat`, `proc; fsm; opt; flatten; ... abc --lut 6`, `write_blif --vtr --name-style hash --prov-map` | `odin-meta.json` of the Norns keep sweep (15 designs) |
| `odin3-1.2.0-k6-blif` | same Odin III, `read_blif ...; abc --lut 6; write_blif --vtr` | same (20 MCNC circuits) |
| `odin3-1.1.0-k6-names` | Odin III 1.1.0, header says `write_blif --vtr (K=6, names provenance)`; commit and script not recorded in the data | `mimir-sources/norns/runs/<d>/netlist` (15 designs) |
| `loki-f1-k6` | the netlist Loki's `loki.re.main --floor f1-k6` wrote (4 MCNC circuits, the mcnc-detect re-run); Odin III version not recorded | `work/mimir-data/msd/work/<d>/f1-k6/netlist.blif` |
| `yosys-0.51-vereval` | Yosys 0.51 (git `c4b51902`), as the file header states; the generating script is the upstream's `scripts/generate-netlist-dataset`, not read | `dataset_netlist-to-rtl/*_netlist.v` of the fork (150) |

## 6. Sets

`mimir/sets.py` keeps the set names. `norns` now reads the 35 registered base netlists (flow
`odin3-1.2.0-k6-*`), materialised from the blob store into `$MIMIR_CACHE/bench/<sha>.blif` (a Job needs a path); its
root variable is `MIMIR_BLOBS`. The old 264-netlist directory read stays as the set `norns-runs` (it includes the
Norns synthetic designs, which Mimir does not own). `mcnc`, `mcnc-k2`, `mcnc-k4` and `loki` are unchanged: their
sources are upstream files the registry points at.

## 7. Agent defaults (logged)

1. Source files are hashed, never copied; `.bak`, `.vmh`, Quartus `db/` and similar files of the BRISC-V directory
   are not designs. Only the 32 `.v` files form the project design.
2. VTR `verilog/*.v` at top level only; the `koios`, `koios_proxy` subdirectories are not registered yet.
3. ITC-99 licence: the clone's `LICENSE` is GPL-3.0; the original ITC'99 distribution terms were not read, so the
   suite carries the clone's licence and a note.
4. `unchecked` hosting for the VTR BLIF k2/k4 sets (ISCAS/MCNC files: licence text not read here).
5. No record in `work/mimir-data/*.db` is rewritten. The `norns` set change affects only later measurements.
6. The three `.blif.names` maps and flow records are blobs too: provenance to the HDL belongs with the netlist.

## 8. Tests

Index parse and round trip; the committed index is consistent (every design of `netlists.tsv` exists, every flow
exists, every blob row has a matching netlists/map/flow row, no `/home` text); resolve rules (explicit flow, default,
ambiguous, unknown); `local-only` marks blobs private and `fetch` refuses their download; `fetch` from a temp blob
store and from a `file://` URL with a wrong hash refused; `build` with a fake Odin III script; `register` on a tiny
fake checkout; the `norns` set builds its jobs from a fake registry; CLI smoke tests.
