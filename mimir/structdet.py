"""Detector structures: run Loki's round-5 detectors on a LUT netlist, store their structures as
`detector:<name>` rows, and compare them with the HDL rows. Loki runs as a subprocess in its own
Python (it needs the Odin III Python binding); nothing of Loki is copied.
Spec: docs/specs/2026-10-27-mimir-structures.md, sections 5 and 7.
"""

from __future__ import annotations

import json
import os
import signal
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
# Loki kind -> Mimir kind. `eq_const` is an equality with a constant (loki/re/claims.py:61); a
# Loki `comparator` carries its operator in params.op (loki/re/detectors/arith.py:341), see kind_of.
KIND_MAP = {
    "ff_en": "register_word", "ff_srst": "register_word", "register": "register_word",
    "shift_reg": "register_word", "lfsr": "register_word", "counter": "counter", "fsm": "fsm",
    "adder": "adder", "subtractor": "adder", "adder_cin": "adder", "hard_add": "adder",
    "comparator": "relational", "eq_const": "equality", "mux": "mux", "mux_bit": "mux",
    "mux_tree": "mux", "hard_mul": "multiplier", "hard_mem": "memory",
}
EQUALITY_OPS = frozenset({"eq", "ne"})
MIN_P = 0.5
WALL_LIMIT_S = 300.0  # the Loki time budget is checked between rounds only; this is the hard stop
STDERR_TAIL = 4000


def kind_of(hyp: Mapping[str, object]) -> str | None:
    """The Mimir kind of a Loki hypothesis, None when it has none. A `comparator` with operator
    `eq` or `ne` is an `equality`, any other operator `relational`."""
    kind = str(hyp["kind"])
    if kind == "comparator":
        params = hyp.get("params")
        op = params.get("op") if isinstance(params, dict) else None
        return "equality" if op in EQUALITY_OPS else "relational"
    return KIND_MAP.get(kind)


@dataclass(frozen=True)
class DetectRun:
    """One Loki invocation: its command and what it cost."""

    argv: tuple[str, ...]
    returncode: int
    time_s: float
    peak_rss_mib: float
    out_dir: Path
    timed_out: bool = False
    stderr_tail: str = ""


def loki_argv(python: Path, blif: Path, out: Path, odin3_tree: Path, seed: int = 1,
              timeout: int = 30, budget: int = 600, rounds: int = 6) -> list[str]:
    """Every option explicit, so the whole configuration is on the command line."""
    return [str(python), "-m", "loki.re.main", str(blif), "--floor", "f1-k6", "--odin3-root",
            str(odin3_tree), "--detectors", ",".join(DETECTORS), "--seed", str(seed),
            "--timeout", str(timeout), "--time-budget", str(budget), "--max-rounds", str(rounds),
            "--calib", "none", "--out", str(out)]


def run_loki(argv: Sequence[str], out: Path, odin3_tree: Path, loki_src: Path,
             build: Path, wall_limit: float = WALL_LIMIT_S) -> DetectRun:
    """Run Loki with a hard wall limit. The child is waited for without reaping (`waitid` with
    WNOWAIT) so that the watchdog never signals a reused pid: the watchdog and the main thread
    meet under one lock, and the child is reaped (`wait4`) only after `done` is set."""
    env = dict(os.environ)
    env["ODIN3_LIB"] = str(build / "libodin3.so")
    env["ODIN3_ROOT"] = str(odin3_tree)
    env["PYTHONPATH"] = os.pathsep.join([str(odin3_tree / "plugins" / "python"), str(loki_src)])
    out.parent.mkdir(parents=True, exist_ok=True)
    err_path = out.parent / (out.name + ".stderr")
    start = time.monotonic()
    state = {"done": False, "killed": False}
    lock = threading.Lock()
    with open(err_path, "wb") as err:
        proc = subprocess.Popen(list(argv), env=env, stdout=subprocess.DEVNULL, stderr=err)

        def watchdog() -> None:
            if finished.wait(wall_limit):
                return
            with lock:
                if not state["done"]:
                    state["killed"] = True
                    os.kill(proc.pid, signal.SIGKILL)

        finished = threading.Event()
        thread = threading.Thread(target=watchdog, daemon=True)
        thread.start()
        os.waitid(os.P_PID, proc.pid, os.WEXITED | os.WNOWAIT)
        with lock:
            state["done"] = True
        finished.set()
        _, status, usage = os.wait4(proc.pid, 0)
        thread.join()
    proc.returncode = os.waitstatus_to_exitcode(status)
    tail = err_path.read_bytes()[-STDERR_TAIL:].decode("utf-8", errors="replace")
    return DetectRun(tuple(argv), proc.returncode, round(time.monotonic() - start, 3),
                     round(usage.ru_maxrss / 1024.0, 1), out, state["killed"], tail)


def read_structs(overlay: Path, atoms: Mapping[str, str], run_tag: str
                 ) -> tuple[list[Struct], dict[str, set[str]]]:
    """Top-level hypotheses of a Loki overlay with a kind in `KIND_MAP` and p_comp >= MIN_P, as
    Structs and their atom sets (the atoms whose output net the hypothesis names)."""
    data = json.loads(overlay.read_text(encoding="utf-8"))
    structs: list[Struct] = []
    members: dict[str, set[str]] = defaultdict(set)
    for h in data["hypotheses"]:
        kind = kind_of(h)
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


Hdl = Mapping[str, tuple[str, set[str], str]]  # sid -> (kind, atoms, granularity)
Det = Mapping[str, tuple[str, set[str]]]          # sid -> (kind, atoms)
NONE = "none"


def scoring_set(structs: Mapping[str, tuple[str, set[str], str, str]]
                ) -> dict[str, tuple[str, set[str], str]]:
    """The HDL structures a detector is scored against. `structs` maps sid -> (kind, atoms,
    granularity, parent sid). Operator structures are all in. A block that has operator structures
    stays in with the atoms no operator of it holds (its residue: the registers of an adder
    feeding a register); a block with no operator structure stays whole. Structures with no atoms
    are left out."""
    held: dict[str, set[str]] = defaultdict(set)
    for _sid, (_k, atoms, gran, parent) in structs.items():
        if gran == "operator":
            held[parent] |= atoms
    out: dict[str, tuple[str, set[str], str]] = {}
    for sid, (kind, atoms, gran, _parent) in structs.items():
        use = atoms - held[sid] if gran == "block" else atoms
        if use:
            out[sid] = (kind, set(use), gran)
    return out


def match(hdl: Hdl, det: Det) -> dict[str, str | None]:
    """Detector structure -> the HDL structure that holds most of its atoms (ties to the smaller
    id), or None: no match when the best holds less than half of the detector's atoms, and a
    detector structure with no atoms is skipped (it matches nothing)."""
    out: dict[str, str | None] = {}
    for sid, (_kind, atoms) in sorted(det.items()):
        best = max(sorted(hdl), key=lambda h: len(atoms & hdl[h][1]), default=None)
        ok = best is not None and bool(atoms) and 2 * len(atoms & hdl[best][1]) >= len(atoms)
        out[sid] = best if ok else None
    return out


def confusion(hdl: Hdl, det: Det) -> dict[tuple[str, str], int]:
    """(HDL kind, detector kind) -> count of pairs. Each detector structure is paired with the HDL
    structure it matches (`NONE` as the HDL kind when it matches none); each HDL structure that
    no detector structure matches is paired with `NONE` as the detector kind."""
    out: dict[tuple[str, str], int] = defaultdict(int)
    hit: set[str] = set()
    for sid, target in match(hdl, det).items():
        if target is None:
            out[(NONE, det[sid][0])] += 1
        else:
            hit.add(target)
            out[(hdl[target][0], det[sid][0])] += 1
    for sid, (kind, _a, _g) in hdl.items():
        if sid not in hit:
            out[(kind, NONE)] += 1
    return dict(out)


@dataclass(frozen=True)
class KindScore:
    kind: str
    detected: int
    correct: int
    hdl: int
    found: int
    hdl_operator: int = 0
    hdl_block: int = 0

    @property
    def precision(self) -> float | None:
        return self.correct / self.detected if self.detected else None

    @property
    def recall(self) -> float | None:
        return self.found / self.hdl if self.hdl else None


def compare(hdl: Hdl, det: Det) -> list[KindScore]:
    """Precision and recall per kind against the scoring set `hdl` (operator-level structures
    where they exist, block-level otherwise: see `scoring_set`). A detector structure is correct
    when the HDL structure it matches has its kind. Precision = correct / detected. Recall = HDL
    structures of the kind (with atoms) that a correct detector structure matched / HDL
    structures of the kind. `hdl_operator` and `hdl_block` split the recall denominator."""
    detected: dict[str, int] = defaultdict(int)
    correct: dict[str, int] = defaultdict(int)
    found: dict[str, set[str]] = defaultdict(set)
    for sid, target in match(hdl, det).items():
        kind = det[sid][0]
        detected[kind] += 1
        if target is not None and hdl[target][0] == kind:
            correct[kind] += 1
            found[kind].add(target)
    totals: dict[str, int] = defaultdict(int)
    split: dict[tuple[str, str], int] = defaultdict(int)
    for kind, _a, gran in hdl.values():
        totals[kind] += 1
        split[(kind, gran)] += 1
    kinds = sorted(set(detected) | set(totals))
    return [KindScore(k, detected[k], correct[k], totals[k], len(found[k]),
                      split[(k, "operator")], split[(k, "block")]) for k in kinds]
