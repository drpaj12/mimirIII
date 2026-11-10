import numpy as np


def load_idx(images_path, labels_path):
    im = open(images_path, "rb").read()
    lb = open(labels_path, "rb").read()
    assert int.from_bytes(im[:4], "big") == 0x803 and int.from_bytes(lb[:4], "big") == 0x801
    n = int.from_bytes(im[4:8], "big")
    X = np.frombuffer(im, dtype=np.uint8, offset=16).reshape(n, 28, 28)
    y = np.frombuffer(lb, dtype=np.uint8, offset=8)
    assert len(y) == n
    return X, y
