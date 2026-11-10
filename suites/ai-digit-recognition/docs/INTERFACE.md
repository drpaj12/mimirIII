# Interface contract (P0)

Every implementation is wrapped to one top module, `mnist_top`, so one testbench (`tb/mnist_tb.v`) fits all.
The wrapper is part of the implementation and counts in its cost.

## Ports

| Port | Dir | Width | Meaning |
|---|---|---|---|
| `clk` | in | 1 | the only clock |
| `rst` | in | 1 | synchronous reset, active high |
| `start` | in | 1 | one-cycle pulse: begin an image. The DUT drops `done` after this edge |
| `in_valid` | in | 1 | `in_data` is valid |
| `in_data` | in | 8 | one pixel, quantised int8 (two's complement), row-major 28x28 |
| `in_ready` | out | 1 | the DUT takes `in_data` this cycle; a transfer is `in_valid & in_ready` at a clock edge |
| `done` | out | 1 | level: result valid; stays high until the next `start` |
| `pred` | out | 4 | class 0..9 (argmax of `scores`; first maximum wins on a tie) |
| `scores` | out | 80 | ten signed int8 scores, score k in bits `[8k+7:8k]` |

(`class` is a keyword in SystemVerilog, hence `pred`.) Verilog-2005 only; one clock; no hierarchical
reference to the DUT; no DUT parameter override (Odin III `sim_tb` limits).

## Protocol

1. `rst` high for 4 cycles, then low.
2. Per image: pulse `start` for one cycle; from the next cycle stream exactly 784 bytes with valid/ready
   (the testbench holds `in_valid` and `in_data` until it sees `in_ready`); wait for `done`.
3. The testbench samples `pred` and `scores` on the first clock edge where `done` is seen high.
4. Cycles per image = clock edges from the `start` edge to the edge where `done` is first seen (inclusive count
   printed as `cycles_per_img`, an integer mean over the tier). Pipelined designs: see "Pipelined designs" below.
5. A per-image cycle budget (`vec_meta.hex[1]`, 2,000,000) catches a hang: the image counts as a timeout and the
   DUT is reset.

## Initialisation and clocking (P1)

- A DUT that has to initialise itself after reset (flash weights into a programmable accelerator, fill a
  ROM) keeps `done` low until it is ready for the first `start`, then raises `done`. The testbench, built
  with `-DMNIST_INIT=<budget cycles>`, waits for that `done` before the first image and reports the wait
  as `init_cycles`; it is not part of `cycles_per_img`. Without `-DMNIST_INIT` the testbench does not wait
  (the P0 DUTs).
- The testbench drives its signals and reads the DUT only at the falling clock edge; the DUT samples at the
  rising edge. A transfer is `in_valid & in_ready` as sampled at the rising edge, so `in_ready` must not
  depend combinationally on `in_valid` (it may depend on the DUT's registers).
- `-DMNIST_TMO=<cycles>` overrides the per-image cycle budget of `vec_meta.hex` for slow designs.
- Cycles per image: rising clock edges from the edge that samples `start` to the edge after which `done` is
  seen high (the testbench reads `done` at the next falling edge).

## Input

The network input is the int8 image `clip(round(((p/255 - 0.1307)/0.3018) / S_in), -127, 127)` with
`S_in = 0.02268019` (conv1 input scale from Gabe Litteken's exported scales; the transmission file does not
carry it, see `docs/GOLDEN.md`). The quantisation is host side; `vec_images.hex` holds the int8 bytes.

## Golden

`golden/lenet_int8.py`: numpy int8 LeNet-5 using the weights and per-layer (M0, n) of
`Benchmarks/LeNet_5_TRANSMISSION.bin`. Requant: `clip((M0*acc + (1<<(n-1))) >> n, -128, 127)` (arithmetic shift),
biases dropped, as the TPU. `scores` = the fc3 int8 outputs. Bit-exact to Gabe's TPU program interpreter.

## Vector files (outside the repo, `work/ai-mnist-data/vectors/<tier>/`, `$readmemh`, one value per line)

`vec_images.hex` (N*784 bytes), `vec_labels.hex`, `vec_gclass.hex`, `vec_gscores.hex` (N*10 bytes),
`vec_meta.hex` ([0]=N, [1]=timeout). Tiers: `quick` N=100 (first 100 test images), `full` N=10000.
Generate with `tools/gen_vectors.py`. The testbench reads the files from the current directory by fixed name
and is built with `-DMNIST_N=<N>`.

## Testbench output (last line)

`MNIST_TB PASS|FAIL n= class_match= score_match= label_correct= timeouts= cycles_total= cycles_per_img=`

PASS = every class and all ten scores equal the golden on every image, no timeouts. Same-network designs must
PASS on the full tier. Different-network designs (LUT network, binarised) are scored on `label_correct / n`.

## Running

- iverilog: `iverilog -g2005 -DMNIST_N=100 -o t.vvp tb/mnist_tb.v dut.v && vvp t.vvp` (run in a directory with the vec files).
- Odin III: `odin3 -p "read_verilog dut.v; proc; opt; lower; sim_tb -D MNIST_N=100 tb/mnist_tb.v"`.
  Netlist: replace the read line by `...; lower; abc --lut 6` (the BLIF has `adder` black boxes `sim_tb` cannot run).

## Results row (one JSON line per design x target)

`score/common.py:new_row`. Fields: `design`, `target` (`vtr-k6` | `cyclonev-lpm`), `tier`, `accuracy`
(`rtl_iverilog`, `netlist_odin_sim`: testbench result dicts), `area`, `speed`, `power`, `tools`, `notes`,
and `null_reason` (a measure that is null has its cause under the same key). Axes follow the plan section 2:
VTR leg area = LUTs, FFs, CLBs, adders, mult_36, RAM blocks, min channel width, wirelength; speed = CPD, Fmax,
cycles/image, latency, images/s; power = ACE2 + VPR power (PTM 45 nm, W=100), energy/image = power x latency.
Cyclone V leg: ALM, register, DSP, M10K, Fmax, power are null until Quartus runs (laptop).

## Cyclone V 5CSEMA5 (DE1-SoC) capacity

From Altera "Cyclone V Device Overview" CV-51001 (2015.06.12), Table 10, member A5 (local copy:
`external/openmsp430/fpga/altera_de0_nano_soc/doc/Terasic/DE0_NANO_SOC/Datasheet/FPGA/Cyclone V Device Overview.pdf`;
the Intel web page could not be fetched from this machine, so the live URL is not verified): ALMs 32,075;
registers 128,300; M10K 3,970 Kb (397 blocks of 10 Kb, derived); variable-precision DSP blocks 87; 18x18
multipliers 174; MLAB 480 Kb.

## Pipelined designs (I3, I4)

A design may accept the next image before the previous result is out. `start` may be pulsed while the previous image
is in flight; the DUT latches it and raises `in_ready` when it can take pixels. `done` stays a level that drops at
`start`; a pipelined DUT also drops it at the start of each result so that every result has a rising edge, and
`pred`/`scores` hold the last result. Latency = `cycles_per_img` of `tb/mnist_tb.v` (unchanged). The initiation
interval is measured by `tb/mnist_tb_pipe.v`, which streams images back to back and collects a result at each rising
edge of `done`; its summary line is the standard line plus ` ii_cycles=<mean cycles between results>
latency_first=<cycles from the first start to the first result>`. In a result row: `speed.ii_cycles`, and
`images_per_s = 1 / (ii_cycles x critical path)`. A non-pipelined design has II = cycles per image.
