# Data and third-party inputs

No MNIST data and no file of Gabe Litteken's repository is stored in this repository. Both are pinned in
`pins.toml` (sha256 for every file) and obtained by reference.

## MNIST test set (t10k)

| file | bytes | sha256 (uncompressed) |
|---|---|---|
| `t10k-images-idx3-ubyte` | 7,840,016 | `0fa7898d509279e482958e8ce81c8e77db3f2f8254e26661ceb7762c4d494ce7` |
| `t10k-labels-idx1-ubyte` | 10,008 | `ff7bcfd416de33731a308c3f266cc351222c34898ecbeaf847f06e48f7ec33f2` |

Fetch: `python3 -I tools/fetch_data.py <dir> [--local <dir with the files or .gz>]` downloads the `.gz` from the
first working URL of `pins.toml`, checks the sha256 of the download and of the decompressed file, and refuses a
mismatch (nothing is written). Both mirrors served byte-identical files on 2026-11-10:

- `https://ossci-datasets.s3.amazonaws.com/mnist/<file>.gz` (the PyTorch datasets bucket)
- `https://storage.googleapis.com/cvdf-datasets/mnist/<file>.gz`

The original home, `http://yann.lecun.com/exdb/mnist/`, answered on 2026-11-10 with an empty directory index
(no files, no licence text), and `.../t10k-images-idx3-ubyte.gz` there returned 404. The vectors used locally were
first read from the copy inside the NeuraLUT checkout (`datasets/mnist/mnist_data/MNIST/raw`) and have the same
hashes.

Licence: Creative Commons Attribution-ShareAlike 3.0 (CC BY-SA 3.0). Copyright holders: Yann LeCun (NYU),
Corinna Cortes (Google Labs) and Christopher J.C. Burges. Settled by Peter Jamieson on 2026-11-10: the benchmark may be
released. The original home page gave no licence text on 2026-11-10 (see above); the licence is recorded from
Peter's reading. What follows from it here:

- Credit: any release or paper using this suite cites MNIST and names the three holders above.
- Share-alike: any dataset derived from MNIST that we distribute (for example the hex vector files made by
  `tools/gen_vectors.py`) is released under CC BY-SA 3.0. The suite still ships no images: the data is fetched and
  checked by sha256 (`pins.toml`), and the vectors are made locally.
- Our code (wrapper, testbenches, generators, scoring) is our own and keeps the repository licence. LeNet-5 is a
  published architecture (LeCun et al. 1998); the trained weights used as the golden are Gabe's (MIT, below).

## The golden network

`Benchmarks/LeNet_5_TRANSMISSION.bin` of `https://github.com/littekge/USS_Tensor_Processing_Unit` at commit
`8e85de4592fc7df6fa264c06ff9ff0891536e497` (MIT, Copyright (c) 2026 Gabriel Litteken, `LICENSE:1-3`). Read by
path (`USS_TPU`, default `<workspace>/external/USS_Tensor_Processing_Unit`). Implementation I1 also reads that
repository's RTL by path. `tools/build_i1.py` writes the only generated variants (array size, widened program
memory) into a build directory outside the repository.
