# Results: implementation I1 (Gabe Litteken's TPU), N = 2, 4, 8

Rows are in `results/` (`rtl.jsonl`, `vtr.jsonl`, `lpm.jsonl`; schema 1, one row per design x target, `null_reason`
where a field was not measured). The tables below are `python3 -I score/make_table.py results`. Tools: Odin III
1.6.1 pre-release (origin/main 59349797), Verilator, VTR from the workspace checkout, architecture
`k6_frac_N10_frac_chain_mem32K_40nm`. The VTR and LPM legs ran on the quick tier (100 images); the RTL simulation
ran on both tiers.

## Accuracy: bit-exact on 10,000 images

Class and all ten scores of every image equal the numpy golden (`docs/GOLDEN.md`) for N = 2, 4 and 8: class match
10,000 / 10,000, score match 10,000 / 10,000, timeouts 0. Top-1 against the MNIST labels is 98.74 % (9,874 of
10,000), the golden's own accuracy; the quick tier gives 98 / 100. No difference to the golden exists, so there is
no cause to report.

## Accuracy and cycles (Verilator, RTL)

| design | tier | images | class match | score match | top-1 vs label | cycles / image | init cycles | simulator | verdict |
|---|---|---|---|---|---|---|---|---|---|
| i1-tpu-n2 | quick | 100 | 100 | 100 | 98.00 % | 1,608,931 | 42,705,940 | verilator | PASS |
| i1-tpu-n2 | full | 10,000 | 10,000 | 10,000 | 98.74 % | 1,608,931 | 42,705,940 | verilator | PASS |
| i1-tpu-n4 | quick | 100 | 100 | 100 | 98.00 % | 853,184 | 12,180,167 | verilator | PASS |
| i1-tpu-n4 | full | 10,000 | 10,000 | 10,000 | 98.74 % | 853,184 | 12,180,167 | verilator | PASS |
| i1-tpu-n8 | quick | 100 | 100 | 100 | 98.00 % | 609,339 | 6,037,968 | verilator | PASS |
| i1-tpu-n8 | full | 10,000 | 10,000 | 10,000 | 98.74 % | 609,339 | 6,037,968 | verilator | PASS |

## VTR k6 target (k6_frac_N10_frac_chain_mem32K_40nm, route + STA + power)

| N | LUT | FF | adder | CLB | mult_36 | RAM block | min W | wirelength | Fmax MHz | crit path ns | power mW | latency ms | images/s | energy mJ/image |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 8 | 8,268 | 5,267 | 3,111 | 899 | 73 | 126 | 88 | 174,784 | 43.7 | 22.88 | 214 | 13.9 | 71.7 | 2.98 |
| 4 | 4,796 | 2,836 | 1,399 | 527 | 25 | 150 | 60 | 109,375 | 47.2 | 21.17 | 241 | 18.1 | 55.4 | 4.36 |
| 2 | 3,955 | 2,226 | 957 | 621 | 13 | 532 | 64 | 184,123 | 49.6 | 20.16 | 869 | 32.4 | 30.8 | 28.19 |

## Cyclone V target (Odin III LPM netlist, instance counts)

| N | lpm_mult | lpm_add_sub | lpm_compare | altsyncram | scfifo | netlist bytes | purity | read-back | Quartus fit / timing / power |
|---|---|---|---|---|---|---|---|---|---|
| 8 | 81 | 144 | 344 | 4 | 18 | 4,944,336 | pass | pass | needs laptop Quartus |
| 4 | 33 | 96 | 333 | 4 | 10 | 8,455,764 | pass | pass | needs laptop Quartus |
| 2 | 21 | 84 | 327 | 4 | 6 | 26,173,053 | pass | pass | needs laptop Quartus |

## Reading the tables

- Cycles per image (RTL, identical for every image) fall as N grows: 1,608,931 (N=2), 853,184 (N=4), 609,339 (N=8).
  About 51,000 cycles of each are the SPI input of 784 bytes.
- VTR speed is `images/s = 1 / latency`, latency = cycles per image x critical path; the TPU is not pipelined
  across images. Energy per image = total power x latency. Power is ACE2 vectorless activity plus VPR power, so it
  is an estimate for ranking, not a measurement.
- N=2 is the odd point: the retiled program has 33,140 instructions, so the program memory is widened to 16
  address bits. That adds 532 RAM blocks and a 164 x 164 grid, which dominates its power (869 mW) and energy.
  Its critical path is the shortest (20.2 ns) because the array is smallest.
- LPM counts are library cells per instance of the top module, hierarchy expanded (a module instantiated 64 times
  counts 64 times). The 81 `lpm_mult` at N=8 are 64 MAC multipliers plus 17 in the controller and vector
  processors. VTR reports 73 `mult_36` for N=8 (fewer; cause not investigated). `scfifo` and
  `altsyncram` stay megafunction instances; the behavioural models are used only in simulation and in the VTR leg.
- `purity` = the netlist has no non-LPM primitive; `read-back` = the netlist reads back through Odin III.
- Cyclone V fit, ALM, M10K, Fmax and power: null, "needs laptop Quartus" (not installed here).

## Not measured, with cause

| Item | Cause |
|---|---|
| N = 16 | not encodable: ISA dimension fields are 4 bits (max 15) and array row/column selects are 4 bits |
| Odin III `sim_tb` on the RTL (quick tier) | see below |
| Odin III `sim_tb` on the mapped netlist | same cause; the VTR leg records `accuracy.netlist_odin_sim: "disabled"` |
| LPM netlist simulation | needs Altera `lpm_*` / `altera_mf` simulation models; the stubs in `<top>_lpm_sim.v` are empty |
| Cyclone V fit / timing / power | Quartus not installed here |
| VTR and LPM legs on the full tier | area, speed and power do not depend on the tier; RTL accuracy covers both tiers |

### Odin III `sim_tb` on the quick tier: not feasible

One attempt, N = 8, build `rel-v161pre`, 4 GB cap, 900 s limit: the project reads and `lower` completes (about
12 s, 3.0 M bit cells for the 64K x 8 data memories), then `sim_tb` ran to the limit without reaching the end of
initialisation (6,037,968 cycles for N = 8, 42.7 M for N = 2). Before `lower`, `sim_tb` refuses a `$mem` cell
("cannot simulate `$mem`; run `lower` first"). The simulator is a cell-level interpreter, and this design needs
over 6 M cycles before the first image on a netlist with millions of bit cells (the memories lower to flip-flops),
so a 100-image run (about 61 M cycles at N = 8) is out of reach. Verilator (RTL) covers both tiers.
A small-memory variant of the wrapper would fit `sim_tb` but would not be the same design;
not built.

## Open items for Gabe Litteken

1. `S_in`, the input scale for the network input, is not in `LeNet_5_TRANSMISSION.bin`. We use 0.02268019 (the
   conv1 input scale of `LeNet_5_Recent.weights.npz`); it gives 98.74 %. Please confirm the value used when the
   bin was made.
2. The bin's weights and (M0, n) differ from the npz that `Emulator.py` loads. Which one is the reference?
3. N = 16 is not encodable (4-bit ISA fields). Is a wider ISA planned?
4. Licence: MIT (Copyright (c) 2026 Gabriel Litteken, `LICENSE:1-3`); we read the repository by path and pin
   commit `8e85de4592fc7df6fa264c06ff9ff0891536e497`. Is it fine to publish results for his design?
5. Our wrapper replaces his Arduino (SPI master plus flash ROM); is that the intended way to drive the TPU?

## Licence notes

- Gabe's TPU: MIT, not copied into this repository.
- MNIST test set: not stored; fetched and checked by sha256 (`pins.toml`). Licence text could not be read from the
  original source; recorded as unconfirmed in `docs/DATA.md`. Peter settles it before a public release that embeds
  images.
