# I6: NeuraLUT-Assemble (LUT network)

Source: `https://github.com/MartaAndronic/NeuraLUT` at commit `650c4f4ebcd9c6e47c7229c6a0786a5b4d8696c7`
(Apache-2.0, Copyright (c) 2021 Xilinx; `datasets/mnist` is the NeuraLUT-Assemble MNIST config). Read by path,
pip-installed from the checkout, never copied. A different model from the reference LeNet-5: a network of
truth-table neurons. Training learns, per neuron, a small sub-network over 6 selected inputs; conversion
enumerates the sub-network over all input codes and writes it as a `case` table (one Verilog module per
neuron, a layer module, a top module `neuralut`, optional `myreg` registers between layers). Scored on top-1
against the MNIST labels, not against Gabe's golden. Python model and Verilog must agree; both are counted.

## Settings (all three trained here, CPU)

Structure of their `hdr-5l-0.1` cut to one normal layer (6-input neurons, each a learned sub-network of width
`width_n`) followed by support layers that each combine `support_fanin` neurons of the layer before.
Their own config (2160-360-2160-360-60, width_n 64, 25 dense + 500 sparse epochs, GPU) was not run: its dense
phase alone is 260 M parameters and 500 epochs on this CPU/4 GB budget is days. Deviations from their config:
`width_n` 16, batch 64 (theirs 32), 10 dense epochs and 60 sparse epochs, three hidden layers instead of five.

| setting | neurons per layer | bits (in / hidden / support / out) | input fan-in | support fan-in | table address bits | width_n | pixels read |
|---|---|---|---|---|---|---|---|
| A (their structure, smaller) | 2160, 360, 60, 10 | 1 / 1 / 1 / 6 | 6 | 6 | 6 | 16 | 388 |
| B (smaller) | 640, 160, 40, 10 | 1 / 1 / 1 / 6 | 6 | 4 | 6 then 4 | 16 | 374 |
| C (B with 2-bit codes) | 640, 160, 40, 10 | 1 / 2 / 2 / 6 | 6 | 4 | 6 then 8 | 16 | 399 |

Training (CPU, 4 threads, 4 GB cap, `tools/neuralut_train.py`; AdamW lr 0.002, cosine schedule, seed 400,
dense phase picks the connections by top-|w| as their `train.py`, sparse phase trains from scratch with them):

| setting | dense phase | total | float model top-1 (10,000) | LUT model top-1 | numpy table model top-1 | Verilog top-1 (Verilator, 10,000) |
|---|---|---|---|---|---|---|
| A | 2,189 s | 6,308 s | 95.54 % | 95.55 % | 95.55 % | 95.55 % |
| B | 621 s | 1,775 s | 91.63 % | 91.63 % | 91.63 % | 91.63 % |
| C | 597 s | 1,599 s | 96.15 % | 96.14 % | 96.14 % | 96.14 % |

The checkpoint is the last epoch (no selection on test). "LUT model" is the library's own `lut_inference`; the
"numpy table model" is ours (`tools/neuralut_gen.py`, reads the same truth tables) and equals the library's class
on 10,000 / 10,000 images for A, B and C. The Verilog agrees with the numpy model on class and on all ten scores
for 10,000 / 10,000 images (Verilator) and 100 / 100 (quick tier; Odin III netlist sim for B). The float model
differs from the LUT model by 0 to 1 image (rounding in the table fill). Test accuracy is read from the 10,000 test
images only after training; the training loop evaluates on them each epoch for the log, and uses no selection.

`nl-B-reg` is B generated with the library's `add_registers` (a register stage before every layer): same
tables, 790 cycles per image, a shorter combinational path.

## Input transform and wrapper (ours, `tools/neuralut_gen.py`)

Train and test see the testbench's pixels: `x = q * S_IN`, `q` the int8 of `docs/INTERFACE.md`; the first
layer's input quantiser (batch norm, bias, 1-bit hard tanh) is a per-pixel threshold on `q`. The wrapper
`mnist_top` evaluates it on arrival with a 784-entry ROM (threshold `T` on `q + 128`, code below `T`; every
pixel's code is asserted to be a single step), stores one bit per pixel the first layer reads in a shift
register that shifts only for those pixels (374 to 399 of 784), drives `neuralut` (the other inputs are tied
to 0), takes the first-maximum argmax of the ten 6-bit output codes and registers `pred` and `scores`. All of
this counts in the cost. `scores[8k+7:8k]` = the model's integer output of class k (`code - 32`, a signed value in
-32..31, exact). Cycles per image: 786 (combinational core), 790 with registers.

## Install (one venv, exactly this)

`python3 -m venv work/nnlut-env`; pip only, CPU wheels. torch 2.4.0 and torchvision 0.19.0 from
`https://download.pytorch.org/whl/cpu`; Brevitas from git (see deviation); `pip install -r` NeuraLUT
`requirements.txt`; `pip install --no-build-isolation --no-deps` of NeuraLUT and TreeLUT from their checkouts;
`xgboost-cpu` 3.4.1 (satisfies `xgboost>=2.1.1`; TreeLUT is installed `--no-deps` so pip does not pull the
CUDA wheel). No wandb, conda, apt. Disk: the venv is 1.3 GB (`du -sh`); generated Verilog and checkpoints of
this run 2.9 GB in the run root (outside the repository). Python 3.12.3. `pip freeze`:

```
brevitas @ git+https://github.com/Xilinx/brevitas.git@32cc847fc7cd6ca4c0201fd6b7d185c1103ae088   (tag v0.7.1)
cloudpickle==3.1.2
dependencies==2.0.1
docrep==0.3.2
filelock==4.2.4
fsspec==2026.9.0
h5py==3.12.1
Jinja2==3.1.6
joblib==1.6.0
MarkupSafe==3.0.3
mpmath==1.3.0
networkx==3.7
neuralut @ file://<workspace>/external/NeuraLUT
numpy==1.26.4
packaging==26.3
pandas==2.2.3
pillow==13.0.0
pyparsing==3.3.3
python-dateutil==4.0.0
pytz==2026.6
PyVerilator==0.7.0
PyYAML==6.0.1
scikit-learn==1.5.2
scipy==1.17.1
setuptools==78.1.0
six==1.17.0
sympy==1.14.0
tclwrapper==0.0.1
threadpoolctl==3.8.0
torch==2.4.0+cpu
torchvision==0.19.0+cpu
treelut @ file://<workspace>/external/TreeLUT
typing_extensions==4.16.0
tzdata==2026.6
xgboost-cpu==3.4.1
```

Deviations and findings during install:

- The Brevitas commit named in the NeuraLUT README (`67be9b58`) is a 2020 version (0.2.0a0) that lacks
  `ParameterScaling` and imports the removed `imp` module on Python 3.12, so `datasets/mnist/models.py` does not
  import. Tag v0.7.1 (`32cc847f`) does, with `dependencies==2.0.1` (the version its `requirements` pin). Brevitas
  v0.7.1 was the first tag tried; no other version was tested.
- `pyverilator` (a NeuraLUT requirement) imports `tkinter`, which is not installed (apt is out of scope). Our
  tools stub the module before importing `models.py`; it is only used by their Verilator co-simulation, which
  we replace with our testbench.
- Their `train.py` needs CUDA and wandb; `tools/neuralut_train.py` is our loop around their model class.
- `pip install` from the checkouts left `build/` and `*.egg-info` directories inside `external/NeuraLUT` and
  `external/TreeLUT` (untracked build products, not removed).

## Odin III gaps (build `rel-v161pre`, 4 GB cap)

- `odin3-flow --target vtr` fails for settings A and C at the `abc` pass:
  `odin3: error: abc needs more than 4294967296 bytes (the design's budget is 4294967296 bytes: the smaller of 60%
  of physical memory and the cgroup's memory.max)` (log `flow/odin3/odin3.log`, after `lower`; the pass budget is
  declared in `src/passes/budget.h`). A has 2,590 neuron modules (5.2 MB of Verilog) and C 850 (3.0 MB, 8-input tables in the
  support layers); B has 850 modules (1.4 MB) and fits, as do the TreeLUT designs up to 17,428 LUTs. The VTR rows of A and C are null with
  this cause; their LPM netlists were written and pass the purity and read-back checks.
- `odin3-flow` and `score/vtr_leg.py` need the design in one file here: two `read_verilog` commands do not resolve
  a module defined by the first from the second (`unresolved_module: module 'TreeLUT' is not defined` for the
  second file). `tools/lut_legs.py` flattens the sources into one file. Not investigated in the Odin source.
- `odin3-flow` rejects a file with an unused extra module (`more than one top module (myreg, mnist_top): give
  --top`); the library writes `myreg.v` even without registers, so `tools/neuralut_gen.py` leaves it out then.
- `score/vtr_leg.py` ran VPR power at W = 100; T1 (min W 138) and T3 (min W 192) failed to route there, so the
  script now uses 1.3 x the minimum channel width rounded up to 10 when that exceeds 100 (T1 W = 180, T3 W = 250;
  the method string of each row names it). T3's power was re-run on the existing BLIF with W = 250.

Regenerate: `tools/neuralut_train.py <A|B|C> <train_dir> --dense-epochs 10 --epochs 60`, then
`tools/neuralut_gen.py <setting> <train_dir> <build_dir> [--registers]`; simulate with `tools/run_lut.py`, score with
`tools/lut_legs.py`. The sha256 of the generated files of this run are in `RESULTS-LUT.md`; a retrain on another
machine may give different weights (torch CPU kernels are not bit-reproducible across hardware).
