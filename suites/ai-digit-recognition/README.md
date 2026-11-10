# AI digit recognition (Mimir benchmark suite `ai-digit-recognition`)

One application, many Verilog implementations, two targets. The application is MNIST digit classification by
Gabe Litteken's int8 LeNet-5; every implementation is wrapped to one interface and testbench; each is scored
on accuracy, area, speed and power for the VTR k6 architecture and for Cyclone V (DE1-SoC, 5CSEMA5F31C6)
through Odin III's LPM netlist. This is a Mimir benchmark set (generic benchmark plus data), registered in
`data/benchmarks/suites.toml` as `ai-digit-recognition`. Purpose: a real, testable application with a "how good"
vector for Odin III as a graph and pattern research platform and as a bridge to VTR and to Altera.
No third-party file and no MNIST data is stored here (see `docs/DATA.md`, `pins.toml`).

| Path | Content |
|---|---|
| `docs/INTERFACE.md` | the contract: ports, protocol, initialisation, vector files, result row |
| `docs/GOLDEN.md` | where the golden network comes from and what it is |
| `docs/DATA.md` | MNIST source, hashes, licence status; Gabe's repository pin |
| `docs/I1-TPU.md` | implementation I1 (Gabe's TPU): what each size N measures, how it is built |
| `docs/RESULTS.md` | the results tables and open items |
| `pins.toml`, `tools/fetch_data.py` | pinned inputs and the verified fetch |
| `golden/`, `tools/gen_vectors.py` | numpy golden, vector files for the quick (100) and full (10,000) tiers |
| `tb/mnist_tb.v` | the testbench (iverilog, Verilator, Odin III `sim_tb` subset) |
| `rtl/i1_tpu/` | I1 wrapper `mnist_top_tpu.v` and the `altsyncram` / `scfifo` behavioural models |
| `tools/retile_program.py`, `tools/build_i1.py`, `tools/run_i1.py` | I1 program retiler, build, simulate |
| `score/`, `results/` | `vtr_leg.py`, `lpm_leg.py`, `make_table.py`; `results/*.jsonl` the rows |

## Reproduce I1 (needs the pinned checkout of Gabe's repository under `external/`)

    python3 -I tools/fetch_data.py <raw_dir>                                  # MNIST t10k, sha256 checked
    python3 -I tools/check_golden.py <usstpu_root> <raw_dir>                  # golden vs his interpreter and emulator
    python3 -I tools/gen_vectors.py <usstpu_root> <raw_dir> <vec>/quick 100   # and 10000 for <vec>/full
    python3 -I tools/run_i1.py 8 quick <work>                                 # Verilator; N = 2, 4, 8
    python3 -I score/vtr_leg.py --design i1-tpu-n8 --build <work>/i1-n8/build.json \
        --rtl-result <result.json> --vec <vec>/quick --work <w> --out vtr.jsonl
    python3 -I score/lpm_leg.py --design i1-tpu-n8 --build <work>/i1-n8/build.json \
        --rtl-result <result.json> --vec <vec>/quick --work <w> --out lpm.jsonl
    python3 -I score/make_table.py results

Tool locations come from `ODIN3_BIN`, `ODIN3_FLOW`, `VTR_ROOT`, `USS_TPU`, `AIDIGIT_DATA`, `ODIN3_WS`.
Trivial DUTs for the testbench: `rtl/trivial_const.v` (fixed class, must FAIL) and the generated oracle
(`tools/gen_oracle.py`, must PASS).

## Results (I1, bit-exact on 10,000 images; full tables in `docs/RESULTS.md`)

| N | MAC units | class / score match (10,000) | top-1 | cycles / image | LUT | CLB | mult_36 | RAM | Fmax MHz | power mW | energy mJ / image |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 8 | 64 | 10,000 / 10,000 | 98.74 % | 609,339 | 8,268 | 899 | 73 | 126 | 43.7 | 214 | 2.98 |
| 4 | 16 | 10,000 / 10,000 | 98.74 % | 853,184 | 4,796 | 527 | 25 | 150 | 47.2 | 241 | 4.36 |
| 2 | 4 | 10,000 / 10,000 | 98.74 % | 1,608,931 | 3,955 | 621 | 13 | 532 | 49.6 | 869 | 28.19 |

VTR k6 target (quick-tier legs). Cyclone V fit, Fmax and power: needs laptop Quartus.
