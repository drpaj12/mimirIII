"""The two libraries of lane 3 for the tests: the real checkouts when MIMIR_ODIN3_TREE and
MIMIR_LOKI_SRC are set, else the vendored copies of tests/fixtures/deps (stdlib only)."""

from __future__ import annotations

import os
from pathlib import Path

from mimir.structmap import Deps, load_deps

FIXTURES = Path(__file__).parent / "fixtures"
_CACHE: list[Deps] = []


def deps() -> Deps:
    if not _CACHE:
        tree, loki = os.environ.get("MIMIR_ODIN3_TREE"), os.environ.get("MIMIR_LOKI_SRC")
        if tree and loki:
            _CACHE.append(load_deps(Path(tree), Path(loki)))
        else:
            root = FIXTURES / "deps"
            _CACHE.append(load_deps(root, root))
    return _CACHE[0]
