# AI digit recognition results in the store (schema version 8)

Peter 2026-11-10: the AI benchmark data goes into Mimir, as a table of power, speed, area and accuracy.
Purpose: Mimir is the dataset to mine (design patterns in AI hardware). Measure: every implementation x
setting x target has one row with accuracy, area, speed, power, energy and provenance, queryable from the
store and published as a table with Pareto plots.

## 1. Why a new table

`records` is one numeric value per row, keyed by tool commit, input hash and seed; `run` holds one flow run.
A result row here mixes numbers, text (setting, method, hashes) and a reason for each missing value, and
has no seed or run id (the suite's legs are one run each, recorded as `origin` = `results/<file>:<line>`).
So version 8 adds two tables and leaves every other table unchanged. A version 1 to 7 store migrates in one
transaction (`mimir migrate`, or any write open); a version 4 to 7 store still opens read only as it is
(`aidigit.has_tables` is False there). `merge --runs` needs version 8 on both sides, as before.

## 2. Tables

`aidigit_result`, primary key (suite, design, target). Columns (`mimir/schema.py`, `AIDIGIT_COLUMNS`):

- identity: `suite`, `design` (e.g. `i1-tpu-n8`), `target` (`vtr-k6`, `cyclonev-lpm`, or `rtl` for a design
  that has only a simulation result), `impl_id` (I1 .. I8), `arch_name`, `setting`, `model_kind`
  (`reference network, bit-exact` | `other model`).
- accuracy (RTL, Verilator): `acc_tier` (full = 10,000 images, quick = 100), `acc_sim`, `acc_ref` (what class
  and score match are against: the numpy golden for I1, the design's own Python model for I6 and I8),
  `acc_n`, `acc_label_correct`, `acc_top1`, `acc_class_match`, `acc_score_match`; `acc_netlist_n`,
  `acc_netlist_class_match` (Odin III netlist simulation, quick tier). Accuracy belongs to the RTL, so every
  target row of a design carries the best RTL result: the full tier from `rtl.jsonl` or a leg's
  `rtl_verilator_full`, else the quick tier.
- area: VTR `area_lut`, `area_ff`, `area_adder`, `area_clb`, `area_mult36`, `area_ram_blocks`, `area_grid`,
  `area_min_chan_width`, `area_wirelength`; LPM `lpm_mult`, `lpm_add_sub`, `lpm_compare`, `lpm_altsyncram`,
  `lpm_scfifo`, `netlist_bytes`; Quartus `area_alm`, `area_dsp_blocks`, `area_m10k_blocks`.
- speed: `speed_fmax_mhz`, `speed_crit_path_ns`, `speed_cycles_per_img`, `speed_init_cycles`,
  `speed_latency_us`, `speed_ii_cycles` (initiation interval; set only where the source says it equals the
  cycles per image), `speed_images_per_s`.
- power: `power_total_mw`, `power_dynamic_mw`, `power_static_mw`, `power_method` (verbatim), `power_channel_width`
  (the `W=` in the method), `energy_uj_per_img`.
- provenance: `odin3_build`, `odin3_commit`, `vtr_commit`, `arch_file`, `design_source` (pin id in
  `pins.toml`), `design_source_commit`, `rtl_sha256` (text; the LUT designs have the first 16 hex digits of
  the generated files), `run_date`, `result_tier`, `origin`.

`aidigit_null` (suite, design, target, field) -> `reason`: one row for every NULL in a field the target is
expected to fill (the common fields plus the target's own). The reason is the source row's `null_reason` text
when it has one (`quartus not run here`, `odin3-flow failed (exit 1); see flow.log`), else the text of
`implementations.toml` (hashes, VTR commit, run date), else `not in the source row (<target> leg)`.

## 3. Sources and what is not invented

Input: `suites/ai-digit-recognition/results/*.jsonl` (the files listed in `implementations.toml` `[results]`)
and `implementations.toml`, which holds, copied from the suite's docs, each design's implementation id,
setting, model kind, accuracy reference, source pin and generated-RTL hash, and the Odin III build and commit
of the run. The source commit comes from `pins.toml`. The VTR commit and the run date are not in the result
rows or docs, so they are NULL with a reason. One reading rule: a cell type missing from a present `lpm_cells`
table has 0 instances.

## 4. Commands

    mimir migrate --db STORE                         # schema 7 -> 8, additive
    mimir import-aidigit --db STORE [--suite DIR]    # replaces the suite's rows; same input, same rows
    mimir aidigit-table --db STORE --out-dir suites/ai-digit-recognition/docs

`import-aidigit` refuses (exit 2, store untouched) a design in a results file without an entry in
`implementations.toml`, and two rows for one (design, target). A later implementation (I2 soft CPU, I3 dataflow,
I4 fixed weights, I7 binarised) adds its results file to `[results] files` and one `[[design]]` entry per
design, then the import is re-run. `aidigit-table` reads the store read only and writes `TABLE.md`,
`TABLE.csv` (all columns plus `null_reasons`), `TABLE.tex` (booktabs) and `plots/*.svg`.

## 5. Table and plots

One row per design and target, sorted by implementation id then design, units in the headers, `n/a` for a NULL.
A power channel width other than 100 carries a dagger (not same-W comparable). Notes state: power is ACE2
vectorless + the VPR power model (ranking estimate), area/speed/power come from quick-tier legs, Cyclone V fit,
timing and power are parked (Peter 2026-11-10). Three Pareto plots (VTR k6 rows with both values): accuracy
against energy per image, against LUTs and against latency; x on a log axis, front = no other point with
accuracy >= and cost <= (one strict); front points filled and joined by a dashed line. Plain inline SVG from
the standard library; no new dependency.

## 6. Tests

`tests/test_aidigit_results.py`: known values of I1 N=8, channel-width parse, full-tier accuracy for the LUT
designs, zero fill, null reasons, refusals, idempotent import, v7 -> v8 migration and read-only open, Pareto
known answer, table marks, LaTeX balance, CSV shape, and that the committed table equals a regeneration.
