# Mimir benchmark catalogue

One row per registered design, grouped by suite (where it is from). `✓` yes, `✗` no (both measured), `-` not run, `n/a` does not apply, `fail: ...` the tool failed. Every value is in `data/benchmarks/measures.tsv` with its source; the rules are in `docs/benchmarks/catalogue-method.md`. The `vtr-blif-k2` and `vtr-blif-k4` suites hold the same circuits: they are one section, one row per circuit name present in either.

| suite | rows |
|---|---|
| brisc-v | 1 |
| itc99 | 21 |
| mcnc20 | 20 |
| verilogeval | 156 |
| vtr-blif | 199 |
| vtr-verilog | 31 |
| total | 428 |

## brisc-v

BRISC-V microcontroller (Arduino-on-RISC-V, Quartus project revert_timer). Upstream https://github.com/qiany21/Arduino-on-RISC-V.git at 1d5b591081511a8161b843d003ca7b80bad7fc45. Licence: MIT (Copyright (c) 2021 qiany21).

| design | format | top | LOC | seq | mem | mul | add | fsm | latch | hier | bbox | testbench | vectors | LUTs | blocks | FFs | pins | mult/mem | cpd ns | chan w | gates/depth | 4-LUT/depth | 6-LUT/depth | cells | core um2 | LVS | stage |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| quartus_project_revert_timer | verilog-project | single_cycle_BRAM_top | 4349 | - | - | - | - | - | - | - | - | Arduino-on-RISC-V/quartus_project_revert_timer/tb_single_cycle_BRAM_top_gcd.v | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | - | - |

## itc99

ITC'99 (RTL Verilog, b01-b22 without b16). Upstream https://github.com/ccsl-uaegean/ITC99-RTL-Verilog at 8e6a23da036b7442ef4ea410c679d4cf21830a65. Licence: GPL-3.0 (the LICENSE file of this repository); the terms of the original ITC'99 distribution were not read.

| design | format | top | LOC | seq | mem | mul | add | fsm | latch | hier | bbox | testbench | vectors | LUTs | blocks | FFs | pins | mult/mem | cpd ns | chan w | gates/depth | 4-LUT/depth | 6-LUT/depth | cells | core um2 | LVS | stage |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| b01 | verilog | b01 | 117 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | 105/10 | 18/3 | 5/1 | - | - | - | - |
| b02 | verilog | b02 | 74 | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | 26/6 | 10/2 | 9/2 | - | - | - | - |
| b03 | verilog | b03 | 133 | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | 193/10 | 56/4 | 37/3 | - | - | - | - |
| b04 | verilog | b04 | 113 | ✓ | ✗ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | 1782/54 | 133/6 | 104/4 | - | - | - | - |
| b05 | verilog | b05 | 444 | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | 20479/98 | 306/12 | 196/8 | - | - | - | - |
| b06 | verilog | b06 | 130 | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | 72/7 | 17/3 | 14/2 | - | - | - | - |
| b07 | verilog | b07 | 125 | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | 776/17 | 128/6 | 95/4 | - | - | - | - |
| b08 | verilog | b08 | 88 | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | 654/16 | 56/5 | 35/3 | - | - | - | - |
| b09 | verilog | b09 | 91 | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | 248/13 | 61/4 | 47/3 | - | - | - | - |
| b10 | verilog | b10 | 178 | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | 211/10 | 55/4 | 39/2 | - | - | - | - |
| b11 | verilog | b11 | 138 | ✓ | ✗ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | 3924/39 | 515/14 | 357/9 | - | - | - | - |
| b12 | verilog | b12 | 635 | ✓ | ✗ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | 5026/26 | 673/8 | 484/5 | - | - | - | - |
| b13 | verilog | b13 | 320 | ✓ | ✗ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | 1034/24 | 90/3 | 70/3 | - | - | - | - |
| b14 | verilog | b14 | 904 | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | 9335/105 | 1352/32 | 984/20 | - | - | - | - |
| b15 | verilog | b15 | 805 | ✓ | ✗ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | 26705/80 | 3326/19 | 2322/12 | - | - | - | - |
| b17 | verilog | - | 940 | ✓ | ✗ | ✗ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | 107358/80 | 7388/19 | 5240/12 | - | - | - | - |
| b18 | verilog | - | 1931 | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ | - | - | - | - | - | - | - | 36964/105 | 4976/0 | 3500/0 | - | - | - | - |
| b19 | verilog | - | 1993 | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ | - | - | - | - | - | - | - | 36964/105 | 4976/0 | 3500/0 | - | - | - | - |
| b20 | verilog | - | 1842 | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | 37565/105 | 5680/33 | 4108/20 | - | - | - | - |
| b21 | verilog | - | 1853 | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | 38305/105 | 5603/34 | 4058/21 | - | - | - | - |
| b22 | verilog | - | 2751 | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | - | - | - | - | - | - | - | 56695/105 | 8495/33 | 6234/20 | - | - | - | - |

## mcnc20

MCNC / LGSynth91 circuits as VTR ships them (4-LUT mapped BLIF, circuits.txt). Upstream https://github.com/verilog-to-routing/vtr-verilog-to-routing at 3c9a4d23b27d187bd67c79dc01a18ff1ffc21d9b. Licence: none-stated (data/meta/licences.toml rule mcnc); VTR LICENSE.md: MIT unless otherwise noted, in particular the benchmark circuits.

| design | format | top | LOC | seq | mem | mul | add | fsm | latch | hier | bbox | testbench | vectors | LUTs | blocks | FFs | pins | mult/mem | cpd ns | chan w | gates/depth | 4-LUT/depth | 6-LUT/depth | cells | core um2 | LVS | stage |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| alu4 | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | 818 | 68 | 0 | 22 | 0/0 | 5.0705 | 42 | - | 1522/7 | - | - | - | - | - |
| apex2 | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | 992 | 92 | 0 | 42 | 0/0 | 5.89143 | 54 | - | 1878/8 | - | - | - | - | - |
| apex4 | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | 865 | 80 | 0 | 28 | 0/0 | 5.74616 | 60 | - | 1261/6 | - | - | - | - | - |
| bigkey | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | 572 | 52 | 224 | 460 | 0/0 | 2.59891 | 38 | - | 1707/3 | - | - | - | - | - |
| clma | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | 450 | 82 | 26 | 465 | 0/0 | 5.41555 | 36 | - | 8380/16 | - | - | - | - | - |
| des | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | 901 | 77 | 0 | 501 | 0/0 | 4.68402 | 38 | - | 1591/6 | - | - | - | - | - |
| diffeq | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | 580 | 53 | 310 | 103 | 0/0 | 4.91464 | 42 | - | 1494/14 | - | - | - | - | - |
| dsip | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | 686 | 66 | 224 | 426 | 0/0 | 2.72755 | 34 | - | 1370/3 | - | - | - | - | - |
| elliptic | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | 1463 | 137 | 884 | 245 | 0/0 | 7.59909 | 58 | - | 3602/18 | - | - | - | - | - |
| ex1010 | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | 2777 | 314 | 0 | 20 | 0/0 | 9.8022 | 84 | - | 4598/8 | - | - | - | - | - |
| ex5p | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | 467 | 39 | 0 | 71 | 0/0 | 5.34702 | 48 | - | 1064/7 | - | - | - | - | - |
| frisc | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | 1668 | 153 | 814 | 136 | 0/0 | 8.694 | 66 | - | 3539/23 | - | - | - | - | - |
| misex3 | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | 714 | 62 | 0 | 28 | 0/0 | 4.81741 | 48 | - | 1397/7 | - | - | - | - | - |
| pdc | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | 1973 | 176 | 0 | 56 | 0/0 | 7.42762 | 72 | - | 4575/9 | - | - | - | - | - |
| s298 | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | 661 | 58 | 8 | 10 | 0/0 | 6.32231 | 46 | - | 1930/15 | - | - | - | - | - |
| s38417 | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | 2189 | 179 | 1345 | 135 | 0/0 | 4.96812 | 42 | - | 6096/11 | - | - | - | - | - |
| s38584.1 | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | 2190 | 182 | 1141 | 343 | 0/0 | 4.65105 | 48 | - | 6269/9 | - | - | - | - | - |
| seq | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | 855 | 75 | 0 | 76 | 0/0 | 4.95078 | 54 | - | 1750/7 | - | - | - | - | - |
| spla | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | 1445 | 131 | 0 | 62 | 0/0 | 6.39096 | 60 | - | 3690/8 | - | - | - | - | - |
| tseng | blif | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | 407 | 34 | 219 | 174 | 0/0 | 4.62879 | 48 | - | 1046/13 | - | - | - | - | - |

## verilogeval

VerilogEval problems (reference solutions of the spec-to-rtl dataset) with the Gate-Breaker Yosys netlists. Upstream https://github.com/NMSU-PEARL/verilog-eval.git at d60f0b10458746e2fefc2a98fa2455b77a32e8be. Licence: MIT (Copyright (c) 2023-2024 NVIDIA Research Projects).

| design | format | top | LOC | seq | mem | mul | add | fsm | latch | hier | bbox | testbench | vectors | LUTs | blocks | FFs | pins | mult/mem | cpd ns | chan w | gates/depth | 4-LUT/depth | 6-LUT/depth | cells | core um2 | LVS | stage |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Prob001_zero | verilog | RefModule | 9 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob001_zero_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 0/- | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob002_m2014_q4i | verilog | RefModule | 9 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob002_m2014_q4i_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 0/- | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob003_step_one | verilog | RefModule | 9 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob003_step_one_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 0/- | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob004_vector2 | verilog | RefModule | 10 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob004_vector2_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 0/- | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob005_notgate | verilog | RefModule | 10 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob005_notgate_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob006_vectorr | verilog | RefModule | 10 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob006_vectorr_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 0/- | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob007_wire | verilog | RefModule | 10 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob007_wire_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 0/- | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob008_m2014_q4h | verilog | RefModule | 10 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob008_m2014_q4h_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 0/- | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob009_popcount3 | verilog | RefModule | 10 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob009_popcount3_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 2/- | - | - | - | - |
| Prob010_mt2015_q4a | verilog | RefModule | 11 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob010_mt2015_q4a_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob011_norgate | verilog | RefModule | 11 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob011_norgate_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob012_xnorgate | verilog | RefModule | 11 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob012_xnorgate_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob013_m2014_q4e | verilog | RefModule | 11 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob013_m2014_q4e_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob014_andgate | verilog | RefModule | 11 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob014_andgate_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob015_vector1 | verilog | RefModule | 11 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob015_vector1_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 0/- | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob016_m2014_q4j | verilog | RefModule | 11 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob016_m2014_q4j_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 6/- | - | - | - | - |
| Prob017_mux2to1v | verilog | RefModule | 12 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob017_mux2to1v_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 100/- | - | 4144.0 | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob018_mux256to1 | verilog | RefModule | 11 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob018_mux256to1_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 105/- | 506 | 7847.5 | match | lvs |
| Prob019_m2014_q4f | verilog | RefModule | 11 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob019_m2014_q4f_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob020_mt2015_eq2 | verilog | RefModule | 11 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob020_mt2015_eq2_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob021_mux256to1v | verilog | RefModule | 11 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob021_mux256to1v_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 390/- | - | - | - | - |
| Prob022_mux2to1 | verilog | RefModule | 12 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob022_mux2to1_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob023_vector100r | verilog | RefModule | 12 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob023_vector100r_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 0/- | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob024_hadd | verilog | RefModule | 12 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob024_hadd_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 2/- | - | - | - | - |
| Prob025_reduction | verilog | RefModule | 10 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob025_reduction_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 2/- | - | - | - | - |
| Prob026_alwaysblock1 | verilog | RefModule | 13 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob026_alwaysblock1_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob027_fadd | verilog | RefModule | 13 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob027_fadd_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 2/- | - | - | - | - |
| Prob028_m2014_q4a | verilog | RefModule | 14 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob028_m2014_q4a_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 0/- | - | - | - | - |
| Prob029_m2014_q4g | verilog | RefModule | 12 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob029_m2014_q4g_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob030_popcount255 | verilog | RefModule | 14 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob030_popcount255_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1369/- | - | - | - | - |
| Prob031_dff | verilog | RefModule | 15 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob031_dff_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob032_vector0 | verilog | RefModule | 14 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob032_vector0_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 0/- | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob033_ece241_2014_q1c | verilog | RefModule | 14 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob033_ece241_2014_q1c_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 13/- | - | - | - | - |
| Prob034_dff8 | verilog | RefModule | 15 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob034_dff8_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 0/- | - | 788.3 | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob035_count1to10 | verilog | RefModule | 15 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob035_count1to10_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 4/- | - | - | - | - |
| Prob036_ringer | verilog | RefModule | 13 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob036_ringer_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 2/- | - | 17.5 | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob037_review2015_count1k | verilog | RefModule | 15 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob037_review2015_count1k_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 14/- | - | - | - | - |
| Prob038_count15 | verilog | RefModule | 15 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob038_count15_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 4/- | - | - | - | - |
| Prob039_always_if | verilog | RefModule | 15 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob039_always_if_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob040_count10 | verilog | RefModule | 15 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob040_count10_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 4/- | - | - | - | - |
| Prob041_dff8r | verilog | RefModule | 16 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob041_dff8r_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 8/- | - | - | - | - |
| Prob042_vector4 | verilog | RefModule | 10 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob042_vector4_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 0/- | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob043_vector5 | verilog | RefModule | 14 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob043_vector5_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 20/- | 25 | 420.4 | mismatch | extract |
| Prob044_vectorgates | verilog | RefModule | 15 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob044_vectorgates_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 10/- | 12 | 145.1 | mismatch | extract |
| Prob045_edgedetect2 | verilog | RefModule | 16 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob045_edgedetect2_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 8/- | - | 1594.0 | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob046_dff8p | verilog | RefModule | 16 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob046_dff8p_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | out of scope: stopped at equiv (equiv header.check.detail: absolute or home path in 'equiv-c) | map |
| Prob047_dff8ar | verilog | RefModule | 16 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob047_dff8ar_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 8/- | - | - | - | - |
| Prob048_m2014_q4c | verilog | RefModule | 17 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob048_m2014_q4c_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob049_m2014_q4b | verilog | RefModule | 17 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob049_m2014_q4b_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob050_kmap1 | verilog | RefModule | 12 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob050_kmap1_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob051_gates4 | verilog | RefModule | 14 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob051_gates4_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 3/- | - | - | - | - |
| Prob052_gates100 | verilog | RefModule | 14 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob052_gates100_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 88/- | 318 | 5172.5 | match | lvs |
| Prob053_m2014_q4d | verilog | RefModule | 16 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob053_m2014_q4d_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob054_edgedetect | verilog | RefModule | 16 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob054_edgedetect_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 8/- | - | 1559.0 | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob055_conditional | verilog | RefModule | 18 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob055_conditional_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 56/- | 159 | 2499.9 | match | lvs |
| Prob056_ece241_2013_q7 | verilog | RefModule | 13 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob056_ece241_2013_q7_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob057_kmap2 | verilog | RefModule | 13 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob057_kmap2_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob058_alwaysblock2 | verilog | RefModule | 16 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob058_alwaysblock2_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 2/- | - | - | - | - |
| Prob059_wire4 | verilog | RefModule | 15 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob059_wire4_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 0/- | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob060_m2014_q4k | verilog | RefModule | 20 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob060_m2014_q4k_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 4/- | - | - | - | - |
| Prob061_2014_q4a | verilog | RefModule | 18 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob061_2014_q4a_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob062_bugs_mux2 | verilog | RefModule | 13 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob062_bugs_mux2_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 8/- | - | - | - | - |
| Prob063_review2015_shiftcount | verilog | RefModule | 18 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob063_review2015_shiftcount_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 4/- | - | - | - | - |
| Prob064_vector3 | verilog | RefModule | 18 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob064_vector3_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 0/- | - | - | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob065_7420 | verilog | RefModule | 19 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob065_7420_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 2/- | - | 17.5 | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob066_edgecapture | verilog | RefModule | 20 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob066_edgecapture_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 32/- | - | - | - | - |
| Prob067_countslow | verilog | RefModule | 20 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob067_countslow_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 4/- | - | - | - | - |
| Prob068_countbcd | verilog | RefModule | 20 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob068_countbcd_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 22/- | - | - | - | - |
| Prob069_truthtable1 | verilog | RefModule | 15 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob069_truthtable1_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob070_ece241_2013_q2 | verilog | RefModule | 19 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob070_ece241_2013_q2_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 2/- | - | - | - | - |
| Prob071_always_casez | verilog | RefModule | 22 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob071_always_casez_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 0/- | - | - | - | - |
| Prob072_thermostat | verilog | RefModule | 17 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob072_thermostat_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 3/- | - | - | - | - |
| Prob073_dff16e | verilog | RefModule | 22 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob073_dff16e_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 16/- | - | - | - | - |
| Prob074_ece241_2014_q4 | verilog | RefModule | 17 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob074_ece241_2014_q4_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 3/- | - | - | - | - |
| Prob075_counter_2bc | verilog | RefModule | 22 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob075_counter_2bc_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 2/- | - | - | - | - |
| Prob076_always_case | verilog | RefModule | 26 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob076_always_case_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 12/- | - | - | - | - |
| Prob077_wire_decl | verilog | RefModule | 18 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob077_wire_decl_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 2/- | - | - | - | - |
| Prob078_dualedge | verilog | RefModule | 25 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob078_dualedge_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob079_fsm3onehot | verilog | RefModule | 19 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob079_fsm3onehot_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 4/- | 9 | 97.6 | mismatch | extract |
| Prob080_timer | verilog | RefModule | 18 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob080_timer_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 17/- | - | - | - | - |
| Prob081_7458 | verilog | RefModule | 21 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob081_7458_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 2/- | 4 | 47.5 | mismatch | extract |
| Prob082_lfsr32 | verilog | RefModule | 25 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob082_lfsr32_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 32/- | - | - | - | - |
| Prob083_mt2015_q4b | verilog | RefModule | 11 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob083_mt2015_q4b_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob084_ece241_2013_q12 | verilog | RefModule | 21 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob084_ece241_2013_q12_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 11/- | - | - | - | - |
| Prob085_shift4 | verilog | RefModule | 21 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob085_shift4_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 4/- | - | - | - | - |
| Prob086_lfsr5 | verilog | RefModule | 23 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob086_lfsr5_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 5/- | - | - | - | - |
| Prob087_gates | verilog | RefModule | 23 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob087_gates_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 7/- | 10 | 93.8 | mismatch | extract |
| Prob088_ece241_2014_q5b | verilog | RefModule | 25 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob088_ece241_2014_q5b_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 2/- | - | - | - | - |
| Prob089_ece241_2014_q5a | verilog | RefModule | 26 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob089_ece241_2014_q5a_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 3/- | - | - | - | - |
| Prob090_circuit1 | verilog | RefModule | 11 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob090_circuit1_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob091_2012_q2b | verilog | RefModule | 13 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob091_2012_q2b_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 2/- | - | 40.0 | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob092_gatesv100 | verilog | RefModule | 16 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob092_gatesv100_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 298/- | - | 6531.3 | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob093_ece241_2014_q3 | verilog | RefModule | 14 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob093_ece241_2014_q3_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 3/- | - | 42.5 | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob094_gatesv | verilog | RefModule | 18 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob094_gatesv_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 10/- | - | - | - | - |
| Prob095_review2015_fsmshift | verilog | RefModule | 29 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob095_review2015_fsmshift_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 4/- | - | - | - | - |
| Prob096_review2015_fsmseq | verilog | RefModule | 30 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob096_review2015_fsmseq_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 5/- | - | - | - | - |
| Prob097_mux9to1v | verilog | RefModule | 32 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob097_mux9to1v_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 95/- | 187 | 3178.0 | match | lvs |
| Prob098_circuit7 | verilog | RefModule | 12 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob098_circuit7_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob099_m2014_q6c | verilog | RefModule | 13 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob099_m2014_q6c_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 2/- | - | - | - | - |
| Prob100_fsm3comb | verilog | RefModule | 23 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob100_fsm3comb_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 3/- | 4 | 45.0 | mismatch | extract |
| Prob101_circuit4 | verilog | RefModule | 13 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob101_circuit4_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob102_circuit3 | verilog | RefModule | 13 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob102_circuit3_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob103_circuit2 | verilog | RefModule | 13 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob103_circuit2_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob104_mt2015_muxdff | verilog | RefModule | 15 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob104_mt2015_muxdff_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob105_rotate100 | verilog | RefModule | 20 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob105_rotate100_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 201/- | 873 | 18955.7 | match | lvs |
| Prob106_always_nolatches | verilog | RefModule | 21 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob106_always_nolatches_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 10/- | - | - | - | - |
| Prob107_fsm1s | verilog | RefModule | 28 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob107_fsm1s_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob108_rule90 | verilog | RefModule | 18 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob108_rule90_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 512/- | - | - | - | - |
| Prob109_fsm1 | verilog | RefModule | 28 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob109_fsm1_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob110_fsm2 | verilog | RefModule | 29 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob110_fsm2_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob111_fsm2s | verilog | RefModule | 29 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob111_fsm2s_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob112_always_case2 | verilog | RefModule | 30 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob112_always_case2_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 2/- | 5 | 50.0 | mismatch | extract |
| Prob113_2012_q1g | verilog | RefModule | 29 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob113_2012_q1g_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob114_bugs_case | verilog | RefModule | 31 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob114_bugs_case_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 13/- | - | - | - | - |
| Prob115_shift18 | verilog | RefModule | 24 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob115_shift18_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 130/- | 703 | 13934.6 | match | lvs |
| Prob116_m2014_q3 | verilog | RefModule | 29 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob116_m2014_q3_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob117_circuit9 | verilog | RefModule | 17 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob117_circuit9_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 3/- | - | - | - | - |
| Prob118_history_shift | verilog | RefModule | 25 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob118_history_shift_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 32/- | - | - | - | - |
| Prob119_fsm3 | verilog | RefModule | 30 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob119_fsm3_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 3/- | - | - | - | - |
| Prob120_fsm3s | verilog | RefModule | 30 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob120_fsm3s_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 4/- | - | - | - | - |
| Prob121_2014_q3bfsm | verilog | RefModule | 31 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob121_2014_q3bfsm_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 6/- | 21 | 402.9 | match | lvs |
| Prob122_kmap4 | verilog | RefModule | 32 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob122_kmap4_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob123_bugs_addsubz | verilog | RefModule | 19 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob123_bugs_addsubz_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 22/- | - | - | - | - |
| Prob124_rule110 | verilog | RefModule | 22 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob124_rule110_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 512/- | - | - | - | - |
| Prob125_kmap3 | verilog | RefModule | 32 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob125_kmap3_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob126_circuit6 | verilog | RefModule | 20 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob126_circuit6_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 16/- | - | - | - | - |
| Prob127_lemmings1 | verilog | RefModule | 31 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob127_lemmings1_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 2/- | - | - | - | - |
| Prob128_fsm_ps2 | verilog | RefModule | 32 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob128_fsm_ps2_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 4/- | - | - | - | - |
| Prob129_ece241_2013_q8 | verilog | RefModule | 37 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob129_ece241_2013_q8_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 3/- | - | - | - | - |
| Prob130_circuit5 | verilog | RefModule | 21 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob130_circuit5_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 9/- | - | - | - | - |
| Prob131_mt2015_q4 | verilog | RefModule | 11 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob131_mt2015_q4_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob132_always_if2 | verilog | RefModule | 25 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob132_always_if2_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob133_2014_q3fsm | verilog | RefModule | 35 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob133_2014_q3fsm_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 9/- | - | - | - | - |
| Prob134_2014_q3c | verilog | RefModule | 36 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob134_2014_q3c_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 2/- | - | - | - | - |
| Prob135_m2014_q6b | verilog | RefModule | 27 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob135_m2014_q6b_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1/- | - | - | - | - |
| Prob136_m2014_q6 | verilog | RefModule | 33 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob136_m2014_q6_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 7/- | - | - | - | - |
| Prob137_fsm_serial | verilog | RefModule | 38 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob137_fsm_serial_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 12/- | - | - | - | - |
| Prob138_2012_q2fsm | verilog | RefModule | 31 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob138_2012_q2fsm_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 7/- | - | - | - | - |
| Prob139_2013_q2bfsm | verilog | RefModule | 38 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob139_2013_q2bfsm_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 9/- | - | - | - | - |
| Prob140_fsm_hdlc | verilog | RefModule | 37 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob140_fsm_hdlc_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 11/- | - | - | - | - |
| Prob141_count_clock | verilog | RefModule | 47 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob141_count_clock_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 41/- | - | - | - | - |
| Prob142_lemmings2 | verilog | RefModule | 36 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob142_lemmings2_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 4/- | - | - | - | - |
| Prob143_fsm_onehot | verilog | RefModule | 25 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob143_fsm_onehot_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 13/- | 23 | 300.3 | match | lvs |
| Prob144_conwaylife | verilog | RefModule | 37 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob144_conwaylife_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 1966/- | - | - | - | - |
| Prob145_circuit8 | verilog | RefModule | 17 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob145_circuit8_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob146_fsm_serialdata | verilog | RefModule | 46 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob146_fsm_serialdata_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 20/- | - | - | - | - |
| Prob147_circuit10 | verilog | RefModule | 18 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob147_circuit10_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 2/- | - | - | - | - |
| Prob148_2013_q2afsm | verilog | RefModule | 35 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob148_2013_q2afsm_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 5/- | - | - | - | - |
| Prob149_ece241_2013_q4 | verilog | RefModule | 46 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob149_ece241_2013_q4_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 11/- | - | - | - | - |
| Prob150_review2015_fsmonehot | verilog | RefModule | 30 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob150_review2015_fsmonehot_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 5/- | 10 | 150.1 | mismatch | extract |
| Prob151_review2015_fsm | verilog | RefModule | 56 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob151_review2015_fsm_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| Prob152_lemmings3 | verilog | RefModule | 48 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob152_lemmings3_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 6/- | - | - | - | - |
| Prob153_gshare | verilog | RefModule | 49 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob153_gshare_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 647/- | - | - | - | - |
| Prob154_fsm_ps2data | verilog | RefModule | 42 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob154_fsm_ps2data_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 28/- | - | 2876.5 | out of scope: stopped at place (openroad failed (rc 1); see openroad.log) | equiv |
| Prob155_lemmings4 | verilog | RefModule | 60 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob155_lemmings4_test.sv | ✓ | - | - | - | - | - | - | - | - | - | 17/- | - | - | - | - |
| Prob156_review2015_fancytimer | verilog | RefModule | 78 | - | - | - | - | - | - | - | - | Gate-Breaker-verilog-eval/dataset_spec-to-rtl/Prob156_review2015_fancytimer_test.sv | ✓ | - | - | - | - | - | - | - | - | - | - | - | - | - | - |

## vtr-blif

VTR blif/2 and blif/4: ISCAS-85, ISCAS-89 and MCNC mapped to 2-input and 4-input LUTs. Upstream https://github.com/verilog-to-routing/vtr-verilog-to-routing at 3c9a4d23b27d187bd67c79dc01a18ff1ffc21d9b. Licence: not read: the licence of the individual ISCAS/MCNC files has not been checked.

| design | format | top | LOC | seq | mem | mul | add | fsm | latch | hier | bbox | testbench | vectors | LUTs | blocks | FFs | pins | mult/mem | cpd ns | chan w | gates/depth | 4-LUT/depth | 6-LUT/depth | cells | core um2 | LVS | stage |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 5xp1 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 57/4 | - | - | - | - | - |
| 9sym | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 144/6 | - | - | - | - | - |
| 9symml | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 97/6 | - | - | - | - | - |
| C1355 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 74/4 | - | - | - | - | - |
| C17 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 2/1 | - | - | - | - | - |
| C1908 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 145/10 | - | - | - | - | - |
| C2670 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 258/7 | - | - | - | - | - |
| C3540 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 431/12 | - | - | - | - | - |
| C432 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 124/11 | - | - | - | - | - |
| C499 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 74/4 | - | - | - | - | - |
| C5315 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 620/10 | - | - | - | - | - |
| C6288 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 527/28 | - | - | - | - | - |
| C7552 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 739/10 | - | - | - | - | - |
| C880 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 174/9 | - | - | - | - | - |
| alu2 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 197/10 | - | - | - | - | - |
| alu4 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 1522/7 | - | - | - | - | - |
| apex1 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 699/7 | - | - | - | - | - |
| apex2 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 1878/8 | - | - | - | - | - |
| apex3 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 869/6 | - | - | - | - | - |
| apex4 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 1261/6 | - | - | - | - | - |
| apex5 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 534/5 | - | - | - | - | - |
| apex6 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 393/6 | - | - | - | - | - |
| apex7 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 102/5 | - | - | - | - | - |
| b1 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 4/1 | - | - | - | - | - |
| b12 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 56/4 | - | - | - | - | - |
| b9 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 46/3 | - | - | - | - | - |
| bbara | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 33/3 | - | - | - | - | - |
| bbrtas | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 406/18 | - | - | - | - | - |
| bbsse | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 64/6 | - | - | - | - | - |
| bbtas | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 6/2 | - | - | - | - | - |
| beecount | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 14/2 | - | - | - | - | - |
| bigkey | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 1707/3 | - | - | - | - | - |
| bw | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 132/4 | - | - | - | - | - |
| c8 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 39/4 | - | - | - | - | - |
| cc | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 26/3 | - | - | - | - | - |
| chain_cout_fanout | blif (k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 1/1 | - | - | - | - | - |
| cht | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 55/2 | - | - | - | - | - |
| clip | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 140/5 | - | - | - | - | - |
| clma | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 8380/16 | - | - | - | - | - |
| cm138a | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 10/2 | - | - | - | - | - |
| cm150a | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 14/3 | - | - | - | - | - |
| cm151a | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 8/3 | - | - | - | - | - |
| cm152a | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 6/3 | - | - | - | - | - |
| cm162a | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 18/3 | - | - | - | - | - |
| cm163a | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 11/3 | - | - | - | - | - |
| cm42a | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 10/1 | - | - | - | - | - |
| cm82a | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 4/2 | - | - | - | - | - |
| cm85a | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 11/3 | - | - | - | - | - |
| cmb | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 17/3 | - | - | - | - | - |
| comp | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 40/5 | - | - | - | - | - |
| con1 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 5/2 | - | - | - | - | - |
| cordic | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 466/9 | - | - | - | - | - |
| count | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 39/5 | - | - | - | - | - |
| cps | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 756/5 | - | - | - | - | - |
| cse | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 90/4 | - | - | - | - | - |
| cu | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 22/3 | - | - | - | - | - |
| daio | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 3/1 | - | - | - | - | - |
| daio-rec | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 311/7 | - | - | - | - | - |
| dalu | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 500/6 | - | - | - | - | - |
| decod | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 20/2 | - | - | - | - | - |
| des | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 1591/6 | - | - | - | - | - |
| diffeq | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 1494/14 | - | - | - | - | - |
| dk14 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 43/7 | - | - | - | - | - |
| dk15 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 24/3 | - | - | - | - | - |
| dk16 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 105/4 | - | - | - | - | - |
| dk17 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 15/2 | - | - | - | - | - |
| dk27 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 5/1 | - | - | - | - | - |
| dk512 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 14/2 | - | - | - | - | - |
| dsip | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 1370/3 | - | - | - | - | - |
| duke2 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 251/5 | - | - | - | - | - |
| e64 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 274/4 | - | - | - | - | - |
| ecc | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 330/5 | - | - | - | - | - |
| elliptic | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 3602/18 | - | - | - | - | - |
| ex1 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 124/4 | - | - | - | - | - |
| ex1010 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 4598/8 | - | - | - | - | - |
| ex4 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 35/4 | - | - | - | - | - |
| ex4p | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 444/5 | - | - | - | - | - |
| ex5p | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 1064/7 | - | - | - | - | - |
| ex6 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 60/7 | - | - | - | - | - |
| example2 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 138/4 | - | - | - | - | - |
| f51m | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 54/4 | - | - | - | - | - |
| frg1 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 49/6 | - | - | - | - | - |
| frg2 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 379/6 | - | - | - | - | - |
| frisc | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 3539/23 | - | - | - | - | - |
| gcd | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 218/11 | - | - | - | - | - |
| i1 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 21/3 | - | - | - | - | - |
| i10 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 995/13 | - | - | - | - | - |
| i2 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 74/5 | - | - | - | - | - |
| i3 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 46/3 | - | - | - | - | - |
| i4 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 98/5 | - | - | - | - | - |
| i5 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 88/6 | - | - | - | - | - |
| i6 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 182/2 | - | - | - | - | - |
| i7 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 203/2 | - | - | - | - | - |
| i8 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 481/5 | - | - | - | - | - |
| i9 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 376/5 | - | - | - | - | - |
| inc | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 64/4 | - | - | - | - | - |
| k2 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 518/7 | - | - | - | - | - |
| keyb | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 103/5 | - | - | - | - | - |
| lal | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 34/3 | - | - | - | - | - |
| ldd | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 37/5 | - | - | - | - | - |
| lion | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 3/1 | - | - | - | - | - |
| majority | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 3/2 | - | - | - | - | - |
| mark1 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 34/3 | - | - | - | - | - |
| mc | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 7/2 | - | - | - | - | - |
| misex1 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 21/3 | - | - | - | - | - |
| misex2 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 49/3 | - | - | - | - | - |
| misex3 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 1397/7 | - | - | - | - | - |
| misex3c | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 549/6 | - | - | - | - | - |
| mm30a | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 467/58 | - | - | - | - | - |
| mm4a | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 78/10 | - | - | - | - | - |
| mm9a | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 142/17 | - | - | - | - | - |
| mm9b | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 204/20 | - | - | - | - | - |
| mult16a | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 57/12 | - | - | - | - | - |
| mult16b | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 31/1 | - | - | - | - | - |
| mult32a | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 116/24 | - | - | - | - | - |
| mux | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 15/4 | - | - | - | - | - |
| my-adder | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 47/16 | - | - | - | - | - |
| o64 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 46/4 | - | - | - | - | - |
| opus | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 50/5 | - | - | - | - | - |
| pair | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 647/7 | - | - | - | - | - |
| parity | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 5/2 | - | - | - | - | - |
| parker1986 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 660/13 | - | - | - | - | - |
| pcle | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 21/3 | - | - | - | - | - |
| pcler8 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 35/4 | - | - | - | - | - |
| pdc | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 4575/9 | - | - | - | - | - |
| ph-decod | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 219/6 | - | - | - | - | - |
| planet | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 266/4 | - | - | - | - | - |
| planet1 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 266/4 | - | - | - | - | - |
| pm1 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 19/3 | - | - | - | - | - |
| pma | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 85/4 | - | - | - | - | - |
| rd53 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 12/4 | - | - | - | - | - |
| rd73 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 83/5 | - | - | - | - | - |
| rd84 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 157/6 | - | - | - | - | - |
| rot | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 307/8 | - | - | - | - | - |
| s1 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 195/10 | - | - | - | - | - |
| s1196 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 264/7 | - | - | - | - | - |
| s1238 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 292/8 | - | - | - | - | - |
| s1423 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 221/15 | - | - | - | - | - |
| s1488 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 296/4 | - | - | - | - | - |
| s1494 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 292/5 | - | - | - | - | - |
| s208 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 18/3 | - | - | - | - | - |
| s208.1 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 24/4 | - | - | - | - | - |
| s27 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 6/2 | - | - | - | - | - |
| s298 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 1930/15 | - | - | - | - | - |
| s344 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 67/4 | - | - | - | - | - |
| s349 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 67/4 | - | - | - | - | - |
| s382 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 60/4 | - | - | - | - | - |
| s38417 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 6096/11 | - | - | - | - | - |
| s38584.1 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 6269/9 | - | - | - | - | - |
| s386 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 56/3 | - | - | - | - | - |
| s400 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 69/4 | - | - | - | - | - |
| s420 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 23/3 | - | - | - | - | - |
| s420.1 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 47/5 | - | - | - | - | - |
| s444 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 62/4 | - | - | - | - | - |
| s510 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 101/5 | - | - | - | - | - |
| s526 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 52/4 | - | - | - | - | - |
| s526n | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 60/4 | - | - | - | - | - |
| s5378 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 571/6 | - | - | - | - | - |
| s641 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 87/9 | - | - | - | - | - |
| s713 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 88/8 | - | - | - | - | - |
| s820 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 120/5 | - | - | - | - | - |
| s832 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 145/5 | - | - | - | - | - |
| s838 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 167/8 | - | - | - | - | - |
| s838.1 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 95/9 | - | - | - | - | - |
| s9234.1 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 459/8 | - | - | - | - | - |
| s953 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 214/5 | - | - | - | - | - |
| sand | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 243/5 | - | - | - | - | - |
| sao2 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 90/5 | - | - | - | - | - |
| sbc | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 384/5 | - | - | - | - | - |
| scf | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 416/5 | - | - | - | - | - |
| sct | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 23/3 | - | - | - | - | - |
| seq | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 1750/7 | - | - | - | - | - |
| shiftreg | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 0/0 | - | - | - | - | - |
| spla | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 3690/8 | - | - | - | - | - |
| sqrt8 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 29/4 | - | - | - | - | - |
| sqrt8ml | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 31/6 | - | - | - | - | - |
| squar5 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 34/3 | - | - | - | - | - |
| sse | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 64/6 | - | - | - | - | - |
| styr | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 238/5 | - | - | - | - | - |
| t481 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 214/7 | - | - | - | - | - |
| table3 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 480/6 | - | - | - | - | - |
| table5 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 485/6 | - | - | - | - | - |
| tav | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 9/2 | - | - | - | - | - |
| tbk | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 84/8 | - | - | - | - | - |
| tcon | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 16/1 | - | - | - | - | - |
| term1 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 88/5 | - | - | - | - | - |
| too-lrg | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 187/7 | - | - | - | - | - |
| traffic | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 35/3 | - | - | - | - | - |
| tseng | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 1046/13 | - | - | - | - | - |
| ttt2 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 75/4 | - | - | - | - | - |
| unreg | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 48/2 | - | - | - | - | - |
| vda | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 291/6 | - | - | - | - | - |
| vg2 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 67/4 | - | - | - | - | - |
| x1 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 143/4 | - | - | - | - | - |
| x2 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 17/3 | - | - | - | - | - |
| x3 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 377/5 | - | - | - | - | - |
| x4 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 194/3 | - | - | - | - | - |
| xor5 | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 2/2 | - | - | - | - | - |
| z4ml | blif (k2,k4) | - | - | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | 8/3 | - | - | - | - | - |

## vtr-verilog

VTR Verilog benchmarks (top-level files of vtr_flow/benchmarks/verilog). Upstream https://github.com/verilog-to-routing/vtr-verilog-to-routing at 3c9a4d23b27d187bd67c79dc01a18ff1ffc21d9b. Licence: per design, as each file states (see licence_rule in designs.tsv and data/meta/licences.toml); VTR LICENSE.md: MIT unless otherwise noted, in particular the benchmark circuits.

| design | format | top | LOC | seq | mem | mul | add | fsm | latch | hier | bbox | testbench | vectors | LUTs | blocks | FFs | pins | mult/mem | cpd ns | chan w | gates/depth | 4-LUT/depth | 6-LUT/depth | cells | core um2 | LVS | stage |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LU32PEEng | verilog | - | 5497 | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| LU64PEEng | verilog | - | 6043 | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| LU8PEEng | verilog | - | 5033 | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| and_latch | verilog | and_latch | 21 | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| arm_core | verilog | - | 8211 | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| bgm | verilog | - | 2663 | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| blob_merge | verilog | RLE_BlobMerging | 1617 | - | - | - | - | - | - | - | - | ✗ | ✗ | 6015 | 486 | 575 | 232 | 0/0 | 14.668 | 62 | - | - | - | - | - | - | - |
| boundtop | verilog | paj_boundtop_hierarchy_no_mem | 2825 | - | - | - | - | - | - | - | - | ✗ | ✗ | 572 | 41 | 383 | 468 | 0/32 | 3.06393 | 40 | - | - | - | - | - | - | - |
| boundtop_nolatches | verilog | - | 3053 | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| ch_intrinsics | verilog | memset | 292 | - | - | - | - | - | - | - | - | ✗ | ✗ | 192 | 12 | 82 | 229 | 0/8 | 2.12094 | 38 | - | - | - | - | - | - | - |
| ch_intrinsics_nolatches | verilog | - | 301 | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| diffeq1 | verilog | diffeq_paj_convert | 56 | - | - | - | - | - | - | - | - | ✗ | ✗ | 294 | 31 | 193 | 258 | 5/0 | 17.2038 | 58 | - | - | - | - | - | - | - |
| diffeq2 | verilog | diffeq_f_systemC | 63 | - | - | - | - | - | - | - | - | ✗ | ✗ | 198 | 22 | 96 | 162 | 5/0 | 13.5453 | 44 | - | - | - | - | - | - | - |
| mcml | verilog | - | 24507 | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| mkDelayWorker32B | verilog | mkDelayWorker32B | 6628 | - | - | - | - | - | - | - | - | ✗ | ✗ | 2057 | 63 | 34 | 1066 | 0/1336 | 6.8227 | 38 | - | - | - | - | - | - | - |
| mkPktMerge | verilog | mkPktMerge | 1535 | - | - | - | - | - | - | - | - | ✗ | ✗ | 329 | 19 | 18 | 467 | 0/459 | 4.09815 | 36 | - | - | - | - | - | - | - |
| mkSMAdapter4B | verilog | mkSMAdapter4B | 4348 | - | - | - | - | - | - | - | - | ✗ | ✗ | 1200 | 118 | 639 | 403 | 0/153 | 6.19734 | 48 | - | - | - | - | - | - | - |
| multiclock_output_and_latch | verilog | - | 63 | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| multiclock_reader_writer | verilog | multiclock_reader_writer | 61 | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| multiclock_separate_and_latch | verilog | - | 53 | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| or1200 | verilog | or1200_flat | 5237 | - | - | - | - | - | - | - | - | ✗ | ✗ | 2473 | 237 | 672 | 782 | 1/64 | 8.74562 | 82 | - | - | - | - | - | - | - |
| raygentop | verilog | paj_raygentop_hierarchy_no_mem | 2978 | - | - | - | - | - | - | - | - | ✗ | ✗ | 1195 | 127 | 946 | 560 | 15/21 | 5.43116 | 56 | - | - | - | - | - | - | - |
| raygentop_nolatches | verilog | - | 3178 | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| sha | verilog | sha1 | 2171 | - | - | - | - | - | - | - | - | ✗ | ✗ | 1290 | 142 | 893 | 74 | 0/0 | 9.86096 | 64 | - | - | - | - | - | - | - |
| single_ff | verilog | top | 5 | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| single_wire | verilog | top | 3 | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| spree | verilog | - | 3072 | - | - | - | - | - | - | - | - | ✗ | ✗ | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| stereovision0 | verilog | sv_chip0_hierarchy_no_mem | 3905 | - | - | - | - | - | - | - | - | ✗ | ✗ | 6887 | 702 | 11458 | 366 | 0/0 | 3.8277 | 52 | - | - | - | - | - | - | - |
| stereovision1 | verilog | sv_chip1_hierarchy_no_mem | 2553 | - | - | - | - | - | - | - | - | ✗ | ✗ | 6462 | 758 | 10315 | 278 | 152/0 | 5.72613 | 76 | - | - | - | - | - | - | - |
| stereovision2 | verilog | sv_chip2_hierarchy_no_mem | 1846 | - | - | - | - | - | - | - | - | ✗ | ✗ | 8426 | 1689 | 15573 | 331 | 468/0 | 13.2648 | 90 | - | - | - | - | - | - | - |
| stereovision3 | verilog | sv_chip3_hierarchy_no_mem | 1061 | - | - | - | - | - | - | - | - | ✗ | ✗ | 171 | 15 | 120 | 53 | 0/0 | 2.63369 | 30 | - | - | - | - | - | - | - |
