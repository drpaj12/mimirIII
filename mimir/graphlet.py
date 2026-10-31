"""Graphlet orbit counts of a netlist, by the Odin III `graphlets` pass (through the odin3 package).

Peter 2026-10-30: graphlets are a characteristic of a circuit, so they are a Mimir measurer like
`struct` and `rent`. The counting is Odin III's (docs/user/graphlets.md in the odin3 repository);
Mimir only runs it and stores design-level totals. Two modes are run: undirected, graphlets of 2 to
5 nodes (73 orbits) and directed, 2 to 4 nodes (129 orbits). Global signals (a net that reaches a
clock pin or has 16 or more readers) are excluded with Odin III's own rule (`--exclude-global`).

Rows: `graphlet_orbit_count` with bin `<mode>/<orbit>` (all orbits are stored, zeros too, so an
absent row means "not measured"); `graphlet_nodes`, `graphlet_edges`, `graphlet_self_loops` and
`graphlet_global_nets` with bin `<mode>`. The measurer version is
`graphlet-1/odin3-<odin3 version>/schema-<pass schema>-v<pass schema version>`.
"""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

MODES: tuple[tuple[bool, int], ...] = ((False, 5), (True, 4))  # (directed, size)
MEASURER = "graphlet"
VERSION_TAG = "graphlet-1"
TECHLIB_ENV = "MIMIR_ODIN3_TECHLIB"
TREE_ENV = "MIMIR_ODIN3_TREE"

Row = tuple[str, str, float]  # metric, bin, value


class GraphletSkip(Exception):
    """The measurer cannot run here; the message is the recorded reason."""


@dataclass
class Result:
    rows: list[Row] = field(default_factory=list)
    version: str = ""


def techlib_path() -> Path | None:
    """The tech library to read before the BLIF: $MIMIR_ODIN3_TECHLIB, else lib/vtr.o3lib of
    $MIMIR_ODIN3_TREE, else None (Odin III is run without one)."""
    env = os.environ.get(TECHLIB_ENV)
    if env:
        return Path(env)
    tree = os.environ.get(TREE_ENV)
    if tree and (Path(tree) / "lib" / "vtr.o3lib").is_file():
        return Path(tree) / "lib" / "vtr.o3lib"
    return None


def load_odin3() -> Any:
    """The odin3 module, or GraphletSkip with the reason when it or the counter is missing."""
    try:
        mod = importlib.import_module("odin3")
        lib = mod.default().lib
    except (ImportError, FileNotFoundError, OSError) as exc:
        raise GraphletSkip(f"odin3 package or libodin3 not available: {exc}") from exc
    if not hasattr(lib, "odin3_graphlets_count"):
        raise GraphletSkip("libodin3 lacks odin3_graphlets_count (needs Odin III > v1.2.0)")
    return mod


def mode_name(directed: bool, size: int) -> str:
    return f"{'directed' if directed else 'undirected'}-{size}"


def _group(result: dict[str, Any]) -> dict[str, Any]:
    groups = result.get("groups", [])
    if len(groups) != 1:
        raise GraphletSkip(f"{len(groups)} module groups; flatten the design first")
    group: dict[str, Any] = groups[0]
    return group


def rows_of(result: dict[str, Any]) -> list[Row]:
    """The records of one pass result (schema odin3-graphlets): one orbit row per orbit."""
    g = _group(result)
    mode = str(result["mode"])
    rows: list[Row] = [(f"graphlet_{k}", mode, float(g[k]))
                       for k in ("nodes", "edges", "self_loops", "global_nets")]
    rows += [("graphlet_orbit_count", f"{mode}/{o}", float(n))
             for o, n in enumerate(g["orbit_totals"])]
    return rows


def version_of(mod: Any, result: dict[str, Any]) -> str:
    return (f"{VERSION_TAG}/odin3-{mod.default().version()}"
            f"/schema-{result['schema']}-v{result['version']}")


def measure(path: Path, techlib: Path | None = None) -> Result:
    """Run both modes on a BLIF file. Raises GraphletSkip when Odin III cannot be used or fails."""
    mod = load_odin3()
    libs = [techlib] if techlib is not None else []
    out = Result()
    try:
        with mod.Design.read_blif(path, techlibs=libs) as design:
            for directed, size in MODES:
                res = design.graphlets(directed=directed, size=size, exclude_global=True)
                out.rows += rows_of(res)
                out.version = version_of(mod, res)
    except mod.Odin3Error as exc:
        raise GraphletSkip(f"odin3 failed: {exc}") from exc
    return out
