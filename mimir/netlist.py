"""A flat netlist: nodes with kinds and fanin, the input of every structural measurer."""

from __future__ import annotations

from dataclasses import dataclass, field

PI, CONST, COMB, LATCH, HARD = "pi", "const", "comb", "latch", "hard"
UNDRIVEN = "undriven"  # a signal that is read but never driven; a source, counted in no n_*
KINDS = (PI, CONST, COMB, LATCH, HARD, UNDRIVEN)


@dataclass
class Netlist:
    """Nodes are numbered from 0. `fanin[i]` lists the driver node of each input pin of node i
    (one entry per pin, so a driver may repeat). A node has one output net. `po_drivers` has
    one driver node per primary output. `undriven` and `multidriven` count the signals that were
    read without a driver and the signals with more than one driver (the first driver is kept);
    `clocks` holds the PI nodes that are used as a latch clock (they have no fanout pins)."""

    name: str
    kind: list[str] = field(default_factory=list)
    fanin: list[tuple[int, ...]] = field(default_factory=list)
    po_drivers: list[int] = field(default_factory=list)
    undriven: int = 0
    multidriven: int = 0
    clocks: set[int] = field(default_factory=set)

    def add(self, kind: str, fanin: tuple[int, ...] = ()) -> int:
        self.kind.append(kind)
        self.fanin.append(fanin)
        return len(self.kind) - 1

    def count(self, kind: str) -> int:
        return sum(1 for k in self.kind if k == kind)

    def __len__(self) -> int:
        return len(self.kind)

    def sinks(self) -> list[list[int]]:
        """Per node, the list of sink nodes (one entry per pin, in node order)."""
        out: list[list[int]] = [[] for _ in self.kind]
        for v, drivers in enumerate(self.fanin):
            for u in drivers:
                out[u].append(v)
        return out
