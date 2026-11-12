# AI digit recognition: device size columns (schema version 9)

Peter 2026-11-10. Purpose: the area numbers of the AI digit results (spec 2026-11-10-ai-digit-results.md)
are only readable next to the device they were routed on. Measure: grid W x H, tiles, the channel
width and how full the CLB fabric is, per VTR k6 row.

## 1. Schema 9 (additive)

`aidigit_result` gains `grid_w`, `grid_h` (INTEGER, from the source row's `area.grid` = [W, H]),
`grid_tiles` (W x H), `clb_tiles` (INTEGER) and `clb_util_pct` (REAL, `area_clb` / `clb_tiles` x 100).
`area_grid` (text "WxH") and `area_min_chan_width` (the minimum channel width; the "min_chan_width"
of the request) stay as they were. A version 1 to 8 store migrates in one transaction (`ALTER TABLE
ADD COLUMN`, no row touched; the controller re-imports to fill the new columns). A version 4 to 8
store still opens read only. The new columns are NULL with a reason in `aidigit_null` where absent
(nl-A, nl-C: no VPR result, the `area` reason of the source row).

## 2. How clb tiles are counted

`grid_w` x `grid_h` is VPR's grid including the IO ring ("FPGA sized to W x H"). For the arch
`k6_frac_N10_frac_chain_mem32K_40nm.xml` the `auto_layout` is: `io` perimeter (corners EMPTY), `clb`
fill, `mult_36` columns at x = 6 + 8k and `memory` columns at x = 2 + 8k, both from y = 1, with EMPTY
wherever a block does not fit. So a hard-block column removes the whole interior height from the clb
count: clb tiles = (H - 2) x (W - 2 - number of hard-block columns with x <= W - 2). The layout is
copied into `implementations.toml` (`[arch_layout."<arch file>"]`); `mimir.aidigit.clb_tiles` applies it.
A test compares the copied `startx` / `repeatx` with the arch file when `$VTR_ROOT` is set.

Verification: the formula equals the clb count VPR prints ("Resource usage ... Architecture ... blocks
of type: clb") in the stored run logs under `work/rt-run-aidigit*/` for all 18 distinct grids found
there (18x18 to 164x164, 0 mismatches); the test holds six of them (18, 21, 47, 78, 80, 86).

## 3. Table

`mimir aidigit-table` adds `Grid` (W x H) and `CLB use %` to the VTR k6 table in TABLE.md, TABLE.csv
(all columns) and TABLE.tex; `min W` was already there. Footnote: VPR auto-sized square grid for
k6_frac_N10 (10 BLEs per CLB); the largest resource column (RAM, DSP or CLB) sets the size.
