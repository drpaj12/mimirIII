"""BLIF reader that flattens hierarchy into a `Netlist`."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from mimir.netlist import COMB, CONST, HARD, LATCH, PI, UNDRIVEN, Netlist


class BlifError(ValueError):
    """The file cannot be turned into a flat netlist (the message says why)."""


@dataclass
class Model:
    name: str
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    blackbox: bool = False
    items: list[tuple[str, list[str]]] = field(default_factory=list)


def _logical_lines(text: str) -> list[list[str]]:
    """Token lists, one per logical line (comments dropped, continuations joined)."""
    out: list[list[str]] = []
    pending: list[str] = []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        cont = line.endswith("\\")
        pending += (line[:-1] if cont else line).split()
        if not cont:
            if pending:
                out.append(pending)
            pending = []
    if pending:
        out.append(pending)
    return out


_MIN_ARGS = {".names": 1, ".latch": 2, ".subckt": 1}


def _check_item(head: str, args: list[str], model: str) -> None:
    """Raise BlifError for a directive with too few arguments (a truncated or malformed line)."""
    if len(args) < _MIN_ARGS[head]:
        raise BlifError(f"malformed {head} in model {model}: needs {_MIN_ARGS[head]} argument(s)")


def parse_models(text: str) -> list[Model]:
    """All models in file order. Truth-table rows and unknown directives are ignored."""
    models: list[Model] = []
    cur: Model | None = None
    for toks in _logical_lines(text):
        head = toks[0]
        if head == ".model":
            cur = Model(toks[1] if len(toks) > 1 else "top")
            models.append(cur)
        elif cur is None or not head.startswith("."):
            continue
        elif head == ".inputs":
            cur.inputs += toks[1:]
        elif head == ".outputs":
            cur.outputs += toks[1:]
        elif head == ".blackbox":
            cur.blackbox = True
        elif head in (".names", ".latch", ".subckt"):
            _check_item(head, toks[1:], cur.name)
            cur.items.append((head, toks[1:]))
    if not models:
        raise BlifError("no .model found")
    return models


class _Flattener:
    def __init__(self, models: list[Model]) -> None:
        self.models = {m.name: m for m in models}
        self.prims: list[tuple[str, list[str], list[str]]] = []  # kind, input sigs, output sigs
        self.clocks: list[str] = []  # latch clock signals

    def expand(self, model: Model, prefix: str, ports: dict[str, str], depth: int) -> None:
        if depth > 64:
            raise BlifError(f"hierarchy deeper than 64 at {model.name}")

        def sig(name: str) -> str:
            return ports.get(name) or prefix + name

        for head, args in model.items:
            if head == ".names":
                self.prims.append((COMB, [sig(a) for a in args[:-1]], [sig(args[-1])]))
            elif head == ".latch":
                self.prims.append((LATCH, [sig(args[0])], [sig(args[1])]))
                if len(args) >= 4 and args[3] != "NIL":  # .latch in out type control [init]
                    self.clocks.append(sig(args[3]))
            else:
                self._subckt(model, args, prefix, sig, depth)

    def _subckt(
        self, parent: Model, args: list[str], prefix: str, sig: Callable[[str], str], depth: int
    ) -> None:
        sub = self.models.get(args[0])
        if sub is None:
            raise BlifError(f".subckt of undefined model {args[0]!r} in {parent.name}")
        pairs = [a.split("=", 1) for a in args[1:] if "=" in a]
        if sub.blackbox:
            ins = [sig(a) for f, a in pairs if f in set(sub.inputs)]
            outs = [sig(a) for f, a in pairs if f in set(sub.outputs)]
            self.prims.append((HARD, ins, outs))
            return
        inner = {f: sig(a) for f, a in pairs}
        n = len(self.prims)
        self.expand(sub, f"{prefix}{args[0]}.{n}/", inner, depth + 1)


def flatten(models: list[Model], name: str) -> Netlist:
    """Flatten the first model (the top) into a netlist."""
    top = models[0]
    flat = _Flattener(models)
    flat.expand(top, "", {}, 0)
    nl = Netlist(name)
    driver: dict[str, int] = {s: nl.add(PI) for s in top.inputs}
    pending: list[tuple[int, list[str]]] = []
    for kind, ins, outs in flat.prims:
        if kind == COMB and not ins:
            kind = CONST
        node = nl.add(kind)
        pending.append((node, ins))
        for out in outs:
            if out in driver:
                nl.multidriven += 1
            else:
                driver[out] = node

    def resolve(signal: str) -> int:
        if signal not in driver:
            driver[signal] = nl.add(UNDRIVEN)
            nl.undriven += 1
        return driver[signal]

    for node, ins in pending:
        nl.fanin[node] = tuple(resolve(s) for s in ins)
    nl.po_drivers = [resolve(s) for s in top.outputs]
    nl.clocks = {driver[s] for s in flat.clocks if s in driver and nl.kind[driver[s]] == PI}
    return nl


def read_blif(path: str | Path) -> Netlist:
    """Read and flatten a BLIF file; the netlist is named after the file stem."""
    p = Path(path)
    return flatten(parse_models(p.read_text(encoding="utf-8", errors="replace")), p.stem)
