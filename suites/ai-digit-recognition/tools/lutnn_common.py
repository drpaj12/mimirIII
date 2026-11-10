"""Shared pieces of the I6 (NeuraLUT) and I8 (TreeLUT) flows: settings, the MNIST data in the
testbench's int8 domain, paths. Imported by the tools in this directory."""
import hashlib
import os
from pathlib import Path

import numpy as np

WS = Path(os.environ.get("ODIN3_WS", Path.home() / "odin3-ws"))
NEURALUT_ROOT = Path(os.environ.get("NEURALUT_ROOT", WS / "external/NeuraLUT"))
TREELUT_ROOT = Path(os.environ.get("TREELUT_ROOT", WS / "external/TreeLUT"))
# t10k: the verified copy of the suite (tools/fetch_data.py); train: the copy inside the NeuraLUT
# checkout (training only, never shipped; sha256 in pins.toml).
MNIST_T10K = Path(os.environ.get("MNIST_RAW", WS / "work/ai-mnist-data/raw"))
MNIST_TRAIN = Path(os.environ.get(
    "MNIST_TRAIN_RAW", NEURALUT_ROOT / "datasets/mnist/mnist_data/MNIST/raw"))

MEAN, STD = 0.1307, 0.3018
S_IN = 0.02268019  # golden conv1 input scale (docs/GOLDEN.md); the testbench streams q = round(x / S_IN)

# NeuraLUT-Assemble settings. `model` keys are the ones models.py reads; `train` the loop's.
_TRAIN = {"weight_decay": 0, "learning_rate": 0.002, "seed": 400, "dense_epochs": 25, "epochs": 500,
          "wd": 0.00008, "wd1": 0.03}
SETTINGS = {
    # A: the structure of their hdr-5l-0.1 (6-input neurons, 1-bit codes, 6-bit scores) cut to
    # three trees of support layers; sub-network width 16 instead of 64 (CPU budget).
    "A": {"model": {"hidden_layers": [2160, 360, 60], "support_layers": [0, 1, 1, 1],
                    "input_bitwidth": 1, "hidden_bitwidth": 1, "output_bitwidth": 6,
                    "support_bitwidth": 1, "input_fanin": 6, "hidden_fanin": 6, "output_fanin": 6,
                    "support_fanin": 6, "width_n": 16}, "train": dict(_TRAIN)},
    # B: smaller: support fan-in 4, 640/160/40 neurons.
    "B": {"model": {"hidden_layers": [640, 160, 40], "support_layers": [0, 1, 1, 1],
                    "input_bitwidth": 1, "hidden_bitwidth": 1, "output_bitwidth": 6,
                    "support_bitwidth": 1, "input_fanin": 6, "hidden_fanin": 6, "output_fanin": 6,
                    "support_fanin": 4, "width_n": 16}, "train": dict(_TRAIN)},
    # C: as B with 2-bit codes between layers (8-input tables instead of 4).
    "C": {"model": {"hidden_layers": [640, 160, 40], "support_layers": [0, 1, 1, 1],
                    "input_bitwidth": 1, "hidden_bitwidth": 2, "output_bitwidth": 6,
                    "support_bitwidth": 2, "input_fanin": 6, "hidden_fanin": 6, "output_fanin": 6,
                    "support_fanin": 4, "width_n": 16}, "train": dict(_TRAIN)},
}


def read_idx(images, labels):
    im = Path(images).read_bytes()
    lb = Path(labels).read_bytes()
    assert int.from_bytes(im[:4], "big") == 0x803 and int.from_bytes(lb[:4], "big") == 0x801
    n = int.from_bytes(im[4:8], "big")
    return (np.frombuffer(im, np.uint8, offset=16).reshape(n, 784),
            np.frombuffer(lb, np.uint8, offset=8))


def quant_pixels(u8):
    """Same arithmetic as golden/lenet_int8.py:quant_image, on a flat (n, 784) array -> int64 q."""
    x = (u8.astype(np.float64) / 255.0 - MEAN) / STD
    return np.clip(np.round(x / S_IN), -127, 127).astype(np.int64)


def load(split):
    d = MNIST_T10K if split == "test" else MNIST_TRAIN
    pre = "t10k" if split == "test" else "train"
    x, y = read_idx(d / f"{pre}-images-idx3-ubyte", d / f"{pre}-labels-idx1-ubyte")
    return quant_pixels(x), y.astype(np.int64)


def torch_data():
    import torch
    xq, y = load("train")
    xtq, yt = load("test")
    f = lambda q: torch.from_numpy((q * S_IN).astype(np.float32))  # noqa: E731
    return f(xq), torch.from_numpy(y), f(xtq), torch.from_numpy(yt)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# TreeLUT settings (xgboost params + TreeLUTClassifier params). T1 = the values of their MNIST example.
TREE_SETTINGS = {
    "T1": {"xgb": {"objective": "multi:softmax", "num_class": 10, "n_estimators": 30, "max_depth": 5,
                   "eta": 0.8},
           "treelut": {"w_feature": 4, "w_tree": 3, "pipeline": [0, 1, 1]}},
    "T2": {"xgb": {"objective": "multi:softmax", "num_class": 10, "n_estimators": 15, "max_depth": 4,
                   "eta": 0.8},
           "treelut": {"w_feature": 3, "w_tree": 2, "pipeline": [0, 0, 0]}},
    "T3": {"xgb": {"objective": "multi:softmax", "num_class": 10, "n_estimators": 60, "max_depth": 6,
                   "eta": 0.6},
           "treelut": {"w_feature": 4, "w_tree": 4, "pipeline": [0, 1, 1]}},
}
