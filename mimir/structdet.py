"""Detector structures: run Loki's round-5 detectors on a LUT netlist, store their structures as
`detector:<name>` rows, and compare them with the HDL rows. Loki runs as a subprocess in its own
Python (it needs the Odin III Python binding); nothing of Loki is copied.
Spec: docs/specs/2026-10-27-mimir-structures.md, sections 5 and 7.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from mimir.structmap import Struct

DETECTORS = ("wordfirst", "hard", "ff_pattern", "mux", "arith", "seqfn", "fsm", "bus", "unit",
             "role", "wordgroup")
KIND_MAP = {
    "ff_en": "register_word", "ff_srst": "register_word", "register": "register_word",
    "shift_reg": "register_word", "lfsr": "register_word", "counter": "counter", "fsm": "fsm",
    "adder": "adder", "subtractor": "adder", "adder_cin": "adder", "hard_add": "adder",
    "comparator": "comparator", "eq_const": "comparator", "mux": "mux", "mux_bit": "mux",
    "mux_tree": "mux", "hard_mul": "multiplier", "hard_mem": "memory",
}
MIN_P = 0.5
WALL_LIMIT_S = 300.0  # the Loki time budget is checked between rounds only; this is the hard stop


@dataclass(frozen=True)
class DetectRun:
    """One Loki invocation: its command and what it cost."""

    argv: tuple[str, ...]
    returncode: int
    time_s: float
    peak_rss_mib: float
    out_dir: Path


def loki_argv(python: Path, blif: Path, out: Path, odin3_tree: Path, seed: int = 1,
              timeout: int = 30, budget: int = 600, rounds: int = 6) -> list[str]:
    """Every option explicit, so the whole configuration is on the command line."""
    return [str(python), "-m", "loki.re.main", str(blif), "--floor", "f1-k6", "--odin3-root",
            str(odin3_tree), "--detectors", ",".join(DETECTORS), "--seed", str(seed),
            "--timeout", str(timeout), "--time-budget", str(budget), "--max-rounds", str(rounds),
            "--calib", "none", "--out", str(out)]


def run_loki(argv: Sequence[str], out: Path, odin3_tree: Path, loki_src: Path,
             build: Path) -> DetectRun:
    env = dict(os.environ)
    env["ODIN3_LIB"] = str(build / "libodin3.so")
    env["ODIN3_ROOT"] = str(odin3_tree)
    env["PYTHONPATH"] = os.pathsep.join([str(odin3_tree / "plugins" / "python"), str(loki_src)])
    start = time.monotonic()
    proc = subprocess.Popen(list(argv), env=env, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    timer = threading.Timer(WALL_LIMIT_S, proc.kill)
    timer.start()
    try:
        _, status, usage = os.wait4(proc.pid, 0)
    finally:
        timer.cancel()
    code = os.waitstatus_to_exitcode(status)
    return DetectRun(tuple(argv), code, round(time.monotonic() - start, 3),
                     round(usage.ru_maxrss / 1024.0, 1), out)


def read_structs(overlay: Path, atoms: Mapping[str, str], run_tag: str
                 ) -> tuple[list[Struct], dict[str, set[str]]]:
    """Top-level hypotheses of a Loki overlay with a kind in `KIND_MAP` and p_comp >= MIN_P, as
    Structs and their atom sets (the atoms whose output net the hypothesis names)."""
    data = json.loads(overlay.read_text(encoding="utf-8"))
    structs: list[Struct] = []
    members: dict[str, set[str]] = defaultdict(set)
    for h in data["hypotheses"]:
        kind = KIND_MAP.get(h["kind"])
        if kind is None or h["parents"] or h["p_comp"] < MIN_P:
            continue
        nets = {n for names in h["nets"].values() for n in names}
        found = {n for n in nets if n in atoms}
        if not found:
            continue
        sid = f"det:{h['detector']}:{run_tag}:{h['id']}"
        structs.append(Struct(sid, kind, "", "", f"detector:{h['detector']}", float(h["p_comp"])))
        members[sid] = found
    return structs, members


@dataclass(frozen=True)
class KindScore:
    kind: str
    detected: int
    correct: int
    hdl: int
    found: int

    @property
    def precision(self) -> float | None:
        return self.correct / self.detected if self.detected else None

    @property
    def recall(self) -> float | None:
        return self.found / self.hdl if self.hdl else None


def compare(hdl: Mapping[str, tuple[str, set[str]]], det: Mapping[str, tuple[str, set[str]]]
            ) -> list[KindScore]:
    """Precision and recall per kind. `hdl` and `det` map a structure id to (kind, atom set).
    A detector structure matches the HDL structure that holds most of its atoms (at least half
    of the detector's atoms; ties go to the smaller id); it is correct when the kinds agree. An
    HDL structure is found when a correct detector structure matches it."""
    detected: dict[str, int] = defaultdict(int)
    correct: dict[str, int] = defaultdict(int)
    found: dict[str, set[str]] = defaultdict(set)
    for _sid, (kind, atoms) in sorted(det.items()):
        detected[kind] += 1
        best = max(sorted(hdl), key=lambda h: len(atoms & hdl[h][1]), default=None)
        if best is None or 2 * len(atoms & hdl[best][1]) < len(atoms):
            continue
        if hdl[best][0] == kind:
            correct[kind] += 1
            found[kind].add(best)
    totals: dict[str, int] = defaultdict(int)
    for kind, _ in hdl.values():
        totals[kind] += 1
    kinds = sorted(set(detected) | set(totals))
    return [KindScore(k, detected[k], correct[k], totals[k], len(found[k])) for k in kinds]
