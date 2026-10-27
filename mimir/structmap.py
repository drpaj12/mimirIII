"""Structures of a design and their mapping through the flow, from an Odin III v2 name map.

Inputs: the parsed map (`name_map_v2`, the stdlib parser of Odin III), the BLIF VPR read (the
atoms: LUTs, flip-flops, carry cells and hard blocks) and the HDL texts of the map's files.
A structure is the outermost process-level construct (ALWAYS, CONT_ASSIGN, NET_ASSIGN, INSTANCE)
above a source leaf of an atom's record chain. Separable and lost follow Loki's L15 audit
(`loki.audit`), imported as a library. Spec: docs/specs/2026-10-27-mimir-structures.md.
"""

from __future__ import annotations

import importlib
import math
import re
import sys
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mimir.blif import Model
from mimir.hdlkind import array_names, classify, is_block_kind

LUT, FF, CARRY, HARD = "lut", "ff", "carry", "hard"
_PROCESS_KINDS = frozenset({"ALWAYS", "CONT_ASSIGN", "NET_ASSIGN", "INSTANCE", "GATE_DECL"})
_SPAN = re.compile(r"(\d+)\.\d+-(\d+)\.\d+")
_XY = re.compile(r"(x|y)=(-?\d+)")


@dataclass
class Deps:
    """The two libraries that live outside Mimir: Odin III's map parser and Loki's L15 audit."""

    nmv2: Any
    units: Any
    loss: Any


def load_deps(odin3_tree: Path, loki_src: Path) -> Deps:
    """Import `name_map_v2` (from `<odin3_tree>/tools/flow`) and `loki.audit` (from `loki_src`)."""
    for p in (odin3_tree / "tools" / "flow", loki_src):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    return Deps(importlib.import_module("name_map_v2"),
                importlib.import_module("loki.audit.units"),
                importlib.import_module("loki.audit.loss"))


@dataclass(frozen=True)
class Struct:
    sid: str
    kind: str
    span: str
    chain: str
    source: str
    conf: float


@dataclass
class MapRow:
    sid: str
    level: str
    n_objects: int = 0
    n_pure: int = 0
    n_shared: int = 0
    n_gates: int | None = None
    n_luts: int | None = None
    n_carry: int | None = None
    n_ffs: int | None = None
    n_bles: int | None = None
    n_clbs: int | None = None
    joined_with: str = ""
    lost_at_pass: str = ""
    bbox: tuple[int, int, int, int] | None = None
    spread: float | None = None
    crit_share: float | None = None


@dataclass
class Analysis:
    structs: list[Struct] = field(default_factory=list)
    rows: list[MapRow] = field(default_factory=list)
    atom_structs: dict[str, frozenset[str]] = field(default_factory=dict)
    unattributed: int = 0
    l15_units: int = 0
    l15_separable: int = 0


# ---------------------------------------------------------------- atoms from the BLIF

def atoms_from_blif(models: list[Model], resolve: Callable[[str], bool]) -> dict[str, str]:
    """Atom name -> class (lut, ff, carry, hard) for the top model's primitives. The name is the
    first output net `resolve` accepts (VPR names an atom after its first output); constant
    `.names` (no inputs) are not atoms."""
    outs = {m.name: set(m.outputs) for m in models}
    atoms: dict[str, str] = {}
    for head, args in models[0].items:
        if head == ".names" and len(args) >= 2:
            cands, cls = [args[-1]], LUT
        elif head == ".latch":
            cands, cls = [args[1]], FF
        elif head == ".subckt":
            pins = [a.split("=", 1) for a in args[1:] if "=" in a]
            wanted = outs.get(args[0], set())
            cands = [net for pin, net in pins if pin.split("[")[0] in wanted
                     or pin in wanted] or [net for _, net in pins]
            cls = CARRY if args[0] == "adder" else HARD
        else:
            continue
        name = next((c for c in cands if resolve(c)), None)
        if name is not None:
            atoms[name] = cls
    return atoms


# ---------------------------------------------------------------- the map

class MapView:
    """Block-level view of a name map: which structure each source leaf belongs to."""

    def __init__(self, nm: Any, deps: Deps) -> None:
        self.nm, self.d = nm, deps
        self.records = {r.number: r for r in nm.records}
        self._block: dict[int, int] = {}
        self._leaf: dict[int, frozenset[int]] = {}

    def block_of(self, c: int) -> int:
        """The outermost process-level construct at or above construct `c`, 0 when none."""
        if c not in self._block:
            best, cur, seen = 0, c, 0
            while cur and seen <= len(self.nm.constructs):
                seen += 1
                con = self.nm.constructs[cur - 1]
                if con.kind in _PROCESS_KINDS:
                    best = cur
                cur = con.parent
            self._block[c] = best
        return self._block[c]

    def blocks_of_record(self, rec: int) -> frozenset[int]:
        if rec not in self._leaf:
            leaves = self.d.units.leaf_constructs(self.nm, self.records, rec)
            self._leaf[rec] = frozenset(b for b in (self.block_of(c) for c in leaves) if b)
        return self._leaf[rec]

    def key(self, block: int) -> Any:
        return self.d.units.construct_key(self.nm, block)

    def span_text(self, block: int, norm: Callable[[str], str]) -> str:
        con = self.nm.constructs[block - 1]
        path = self.nm.files[con.file - 1] if con.file else ""
        m = _SPAN.fullmatch(con.span)
        lines = f"{m.group(1)}-{m.group(2)}" if m else con.span
        return f"{norm(path)}:{lines}"

    def chain_text(self, block: int, norm: Callable[[str], str]) -> str:
        """Construct chain from the block up to its module: `KIND@file:span` joined by `>`."""
        parts, cur = [], block
        while cur:
            con = self.nm.constructs[cur - 1]
            path = self.nm.files[con.file - 1] if con.file else ""
            parts.append(f"{con.kind}@{norm(path)}:{con.span}")
            cur = con.parent
        return ">".join(parts)

    def pass_of(self, rec: Any) -> str:
        m = re.match(r"t(\d+)\.", rec.step)
        if not m or not 1 <= int(m.group(1)) <= len(self.nm.runs):
            return "unknown"
        return str(self.nm.runs[int(m.group(1)) - 1][0])

    def join_index(self) -> dict[int, list[tuple[int, str, str]]]:
        """block -> [(record number, record level, pass)] of the join records that name it."""
        out: dict[int, list[tuple[int, str, str]]] = {}
        for rec in self.nm.records:
            if rec.kind != "D" or "join" not in rec.flags:
                continue
            for c in rec.constructs:
                b = self.block_of(c) if c else 0
                if b:
                    out.setdefault(b, []).append((rec.number, rec.level, self.pass_of(rec)))
        return out


# ---------------------------------------------------------------- HDL structures

def hdl_structs(view: MapView, blocks: Iterable[int], texts: Mapping[str, str],
                norm: Callable[[str], str]) -> dict[int, Struct]:
    """A Struct per block, classified from its construct kind and source text."""
    nm, out = view.nm, {}
    arrays = {p: array_names(t) for p, t in texts.items()}
    for b in sorted(blocks):
        con = nm.constructs[b - 1]
        path = nm.files[con.file - 1] if con.file else ""
        text = span_slice(texts.get(path, ""), con.span)
        if not is_block_kind(con.kind):
            continue
        kind, conf = classify(con.kind, text, arrays.get(path, frozenset()))
        sid = f"hdl:{norm(path)}:{con.span}"
        out[b] = Struct(sid, kind, view.span_text(b, norm), view.chain_text(b, norm), "hdl", conf)
    return out


def span_slice(text: str, span: str) -> str:
    """The source text of a span `L.C-EL.EC` (1-based line and column; the end is inclusive)."""
    m = re.fullmatch(r"(\d+)\.(\d+)-(\d+)\.(\d+)", span)
    if not m or not text:
        return ""
    l0, c0, l1, c1 = (int(g) for g in m.groups())
    lines = text.split("\n")
    if not 1 <= l0 <= l1 <= len(lines):
        return ""
    if l0 == l1:
        return lines[l0 - 1][c0 - 1:c1]
    mid = lines[l0:l1 - 1]
    return "\n".join([lines[l0 - 1][c0 - 1:], *mid, lines[l1 - 1][:c1]])


# ---------------------------------------------------------------- mapping

def _join_text(others: Iterable[str]) -> str:
    return ",".join(sorted(set(others)))


def _site_xy(rec: Any) -> tuple[int, int] | None:
    vals = {k: int(v) for k, v in _XY.findall(",".join(rec.flags))}
    return (vals["x"], vals["y"]) if "x" in vals and "y" in vals else None


def _spread(points: list[tuple[int, int]]) -> float:
    cx = sum(p[0] for p in points) / len(points)
    cy = sum(p[1] for p in points) / len(points)
    return round(math.sqrt(sum((p[0] - cx) ** 2 + (p[1] - cy) ** 2 for p in points)
                           / len(points)), 6)


def post_levels(nm: Any, sid_atoms: Mapping[str, set[str]]) -> list[MapRow]:
    """ble, clb and placed rows of each structure, from the `A` lines of prov-post. A structure
    with no atom in the `A` lines gets no row at these levels."""
    by_atom = {a[0]: [r for r in a[1].split(",") if r] for a in nm.atoms if len(a) >= 2}
    level_of = {r.number: r.level for r in nm.records}
    site_xy = {r.number: _site_xy(r) for r in nm.records if r.level == "site"}
    rows: list[MapRow] = []
    groups: dict[str, dict[str, set[str]]] = {"ble": {}, "clb": {}, "site": {}}
    for sid, atoms in sid_atoms.items():
        for a in atoms:
            for ref in by_atom.get(a, []):
                n = int(ref[1:])
                lv = level_of.get(n)
                if lv in groups:
                    groups[lv].setdefault(ref, set()).add(sid)
    for sid in sorted(sid_atoms):
        for lv, out in (("ble", "ble"), ("clb", "clb"), ("site", "placed")):
            objs = {r: s for r, s in groups[lv].items() if sid in s}
            if not objs:
                continue
            row = MapRow(sid, out, len(objs), sum(1 for s in objs.values() if s == {sid}))
            row.n_shared = row.n_objects - row.n_pure
            row.joined_with = _join_text(o for s in objs.values() for o in s if o != sid)
            if lv == "ble":
                row.n_bles = row.n_objects
            else:
                row.n_clbs = row.n_objects
            if lv == "site":
                pts = sorted({p for r in objs if (p := site_xy.get(int(r[1:]))) is not None})
                if pts:
                    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
                    row.bbox = (min(xs), min(ys), max(xs), max(ys))
                    row.spread = _spread(pts)
            rows.append(row)
    return rows


def _views(view: MapView, names: Mapping[str, frozenset[int]], typ: str) -> list[Any]:
    """Loki `ObjView` values (units = the keys of the blocks) for `separable`."""
    cls = view.d.units.ObjView
    return [cls(n, typ, frozenset(view.key(b) for b in bs), frozenset(), False)
            for n, bs in sorted(names.items())]


def _lost(structs_pure: int, sid_block: int, jidx: Mapping[int, list[tuple[int, str, str]]],
          levels: frozenset[str]) -> str:
    """'' when separable; else the pass of the earliest join record naming the block at one of
    `levels`, or `born-joined` when no record names it (V1.2.0 7.1 item 4, L15 status names)."""
    if structs_pure:
        return ""
    hits = sorted(h for h in jidx.get(sid_block, []) if h[1] in levels)
    return hits[0][2] if hits else "born-joined"


def _lut_rows(view: MapView, structs: Mapping[int, Struct], atoms: Mapping[str, str],
              atom_blocks: Mapping[str, frozenset[int]]) -> list[MapRow]:
    pure = view.d.loss.separable(_views(view, atom_blocks, "atom"))
    jidx = view.join_index()
    rows = []
    for b, st in sorted(structs.items()):
        members = sorted(a for a, bs in atom_blocks.items() if b in bs)
        row = MapRow(st.sid, "lut", len(members), len(pure.get(view.key(b), [])))
        row.n_shared = row.n_objects - row.n_pure
        row.n_luts = sum(atoms[a] == LUT for a in members)
        row.n_ffs = sum(atoms[a] == FF for a in members)
        row.n_carry = sum(atoms[a] == CARRY for a in members)
        row.joined_with = _join_text(structs[o].sid for a in members for o in atom_blocks[a]
                                     if o != b and o in structs)
        row.lost_at_pass = _lost(row.n_pure, b, jidx, frozenset(
            {"word", "gate", "lut", "ble"}))
        rows.append(row)
    return rows


def _gate_records(view: MapView, atom_recs: Mapping[str, int]) -> dict[int, frozenset[int]]:
    """Gate-level records reachable from the atoms' records -> their blocks."""
    out: dict[int, frozenset[int]] = {}
    for rec in atom_recs.values():
        for r in view.d.units.provenance_records(view.nm, view.records, rec):
            if r.level == "gate" and r.number not in out:
                out[r.number] = view.blocks_of_record(r.number)
    return out


def _gate_rows(view: MapView, structs: Mapping[int, Struct],
               gates: Mapping[int, frozenset[int]]) -> list[MapRow]:
    names = {f"r{n}": bs for n, bs in gates.items() if bs}
    pure = view.d.loss.separable(_views(view, names, "gate"))
    jidx = view.join_index()
    rows = []
    for b, st in sorted(structs.items()):
        mine = [n for n, bs in names.items() if b in bs]
        if not mine:
            continue
        row = MapRow(st.sid, "gate", len(mine), len(pure.get(view.key(b), [])))
        row.n_shared = row.n_objects - row.n_pure
        row.n_gates = len(mine)
        row.joined_with = _join_text(structs[o].sid for n in mine for o in names[n]
                                     if o != b and o in structs)
        row.lost_at_pass = _lost(row.n_pure, b, jidx, frozenset({"word", "gate"}))
        rows.append(row)
    return rows


def analyse(nm: Any, deps: Deps, atoms: Mapping[str, str], texts: Mapping[str, str],
            norm: Callable[[str], str]) -> Analysis:
    """Structures from the HDL, their mapping at gate, lut, ble, clb and placed level, and the L15
    cross-check counts, for one run's map."""
    view, res = MapView(nm, deps), Analysis()
    atom_rec: dict[str, int] = {}
    atom_blocks: dict[str, frozenset[int]] = {}
    for a in sorted(atoms):
        obj = nm.atom(a)
        if obj is None or not obj.records:
            res.unattributed += 1
            continue
        atom_rec[a] = obj.records[0]
        atom_blocks[a] = view.blocks_of_record(obj.records[0])
        if not atom_blocks[a]:
            res.unattributed += 1
    used = {b for bs in atom_blocks.values() for b in bs}
    gates = _gate_records(view, atom_rec)
    used |= {b for bs in gates.values() for b in bs}
    structs = hdl_structs(view, used, texts, norm)
    res.structs = [structs[b] for b in sorted(structs)]
    atom_blocks = {a: frozenset(b for b in bs if b in structs) for a, bs in atom_blocks.items()}
    res.atom_structs = {a: frozenset(structs[b].sid for b in bs) for a, bs in atom_blocks.items()}
    res.rows = _gate_rows(view, structs, gates) + _lut_rows(view, structs, atoms, atom_blocks)
    sid_atoms = {structs[b].sid: {a for a, bs in atom_blocks.items() if b in bs}
                 for b in structs}
    res.rows += post_levels(nm, sid_atoms)
    res.l15_units, res.l15_separable = l15_counts(view, atom_rec)
    return res


def l15_counts(view: MapView, atom_rec: Mapping[str, int]) -> tuple[int, int]:
    """(units reached, units separable) at the final snapshot by Loki's own definitions: a unit
    is a stmt-level anchor reduced as `view_map` does; separable has a pure object."""
    u = view.d.units
    objs = []
    for a, rec in sorted(atom_rec.items()):
        leaves = u.leaf_constructs(view.nm, view.records, rec)
        units = u.reduce_units(view.nm, {u.anchor(view.nm, c) for c in leaves if c})
        objs.append(u.ObjView(a, "atom", frozenset(u.construct_key(view.nm, c)
                                                   for c in units if c), frozenset(), False))
    reached = view.d.loss.reached(objs)
    return len(reached), len(view.d.loss.separable(objs))


def set_rows(sid_atoms: Mapping[str, set[str]], atoms: Mapping[str, str],
             nm: Any | None) -> list[MapRow]:
    """Mapping rows for structures given as atom sets (detectors): lut level always, and ble, clb
    and placed when the map holds prov-post `A` lines. Purity and joins are among these sets."""
    owners: dict[str, set[str]] = {}
    for sid, held in sid_atoms.items():
        for a in held:
            owners.setdefault(a, set()).add(sid)
    rows = []
    for sid in sorted(sid_atoms):
        members = sorted(sid_atoms[sid])
        pure = sum(owners[a] == {sid} for a in members)
        row = MapRow(sid, "lut", len(members), pure, len(members) - pure)
        row.n_luts = sum(atoms.get(a) == LUT for a in members)
        row.n_ffs = sum(atoms.get(a) == FF for a in members)
        row.n_carry = sum(atoms.get(a) == CARRY for a in members)
        row.joined_with = _join_text(o for a in members for o in owners[a] if o != sid)
        rows.append(row)
    return rows + (post_levels(nm, sid_atoms) if nm is not None else [])
