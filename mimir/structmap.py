"""Structures of a design and their mapping through the flow, from an Odin III v2 name map.

Inputs: the parsed map (`name_map_v2`, the stdlib parser of Odin III), the BLIF VPR read (the
atoms: LUTs, flip-flops, carry cells and hard blocks) and the HDL texts of the map's files.
A block structure is the outermost process-level construct (ALWAYS, CONT_ASSIGN, NET_ASSIGN,
INSTANCE) above a source leaf of an atom's record chain; an operator structure is a `BINARY` or
`TERNARY` expression construct that is itself such a leaf (or holds one) and has a kind of its own.
Separable and lost follow Loki's L15 audit (`loki.audit`), imported as a library.
Spec: docs/specs/2026-10-27-mimir-structures.md.
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
from mimir.hdlkind import (
    OPERATOR_CONSTRUCTS,
    array_names,
    classify,
    classify_operator,
    is_block_kind,
)

LUT, FF, CARRY, HARD = "lut", "ff", "carry", "hard"
_PROCESS_KINDS = frozenset({"ALWAYS", "CONT_ASSIGN", "NET_ASSIGN", "INSTANCE", "GATE_DECL"})
_SPAN = re.compile(r"(\d+)\.\d+-(\d+)\.\d+")
_XY = re.compile(r"(x|y)=(-?\d+)")
LUT_LEVELS = frozenset({"word", "gate", "lut", "ble"})  # a join at these levels is a loss at lut
GATE_LEVELS = frozenset({"word", "gate"})


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
    conf: float | None
    granularity: str = "block"
    parent: str = ""


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
    n_sites: int | None = None
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
    unknown_structs: int = 0      # structures whose HDL text was not available (kind unknown)
    gate_only: int = 0            # structures reached by gate records but by no final atom
    l15_units: int = 0
    l15_separable: int = 0


# ---------------------------------------------------------------- atoms from the BLIF

def atom_candidates(head: str, args: list[str], outs: Mapping[str, set[str]]
                    ) -> tuple[list[str], str] | None:
    """(candidate output nets, class) of one primitive of the top model, None for a directive
    that is not an atom. `outs` maps a model name to its output names."""
    if head == ".names" and len(args) >= 2:
        return [args[-1]], LUT
    if head == ".latch":
        return [args[1]], FF
    if head == ".subckt":
        pins = [a.split("=", 1) for a in args[1:] if "=" in a]
        wanted = outs.get(args[0], set())
        cands = [net for pin, net in pins if pin.split("[")[0] in wanted
                 or pin in wanted] or [net for _, net in pins]
        return cands, CARRY if args[0] == "adder" else HARD
    return None


def atoms_from_blif(models: list[Model], resolve: Callable[[str], bool]) -> dict[str, str]:
    """Atom name -> class (lut, ff, carry, hard) for the top model's primitives. The name is the
    first output net `resolve` accepts (VPR names an atom after its first output); when none is
    accepted the first candidate is kept, so the atom is counted (as unattributed by `analyse`)
    and never dropped. Constant `.names` (no inputs) are not atoms."""
    outs = {m.name: set(m.outputs) for m in models}
    atoms: dict[str, str] = {}
    for head, args in models[0].items:
        got = atom_candidates(head, args, outs)
        if got is not None and got[0]:
            cands, cls = got
            atoms[next((c for c in cands if resolve(c)), cands[0])] = cls
    return atoms


# ---------------------------------------------------------------- the map

@dataclass(frozen=True)
class JoinRec:
    """A record that joins: its number, level, pass label and the constructs it names."""

    number: int
    level: str
    label: str
    constructs: frozenset[int]


class MapView:
    """View of a name map: which block and which operator each source leaf belongs to."""

    def __init__(self, nm: Any, deps: Deps) -> None:
        self.nm, self.d = nm, deps
        self.records = {r.number: r for r in nm.records}
        self._block: dict[int, int] = {}
        self._leaf: dict[int, frozenset[int]] = {}
        self._capped: dict[int, bool] = {}

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

    def leaves(self, rec: int) -> frozenset[int]:
        """The construct leaves behind record `rec` (0 never among them)."""
        if rec not in self._leaf:
            self._leaf[rec] = frozenset(
                c for c in self.d.units.leaf_constructs(self.nm, self.records, rec) if c)
        return self._leaf[rec]

    def blocks_of_record(self, rec: int) -> frozenset[int]:
        return frozenset(b for b in (self.block_of(c) for c in self.leaves(rec)) if b)

    def key(self, unit: int) -> Any:
        return self.d.units.construct_key(self.nm, unit)

    def is_ancestor_or_self(self, anc: int, c: int) -> bool:
        cur, seen = c, 0
        while cur and seen <= len(self.nm.constructs):
            if cur == anc:
                return True
            cur = self.nm.constructs[cur - 1].parent
            seen += 1
        return False

    def _path(self, con: Any) -> str:
        return str(self.nm.files[con.file - 1]) if con.file else ""

    def span_text(self, c: int, norm: Callable[[str], str]) -> str:
        con = self.nm.constructs[c - 1]
        m = _SPAN.fullmatch(con.span)
        lines = f"{m.group(1)}-{m.group(2)}" if m else con.span
        return f"{norm(self._path(con))}:{lines}"

    def chain_text(self, c: int, norm: Callable[[str], str]) -> str:
        """Construct chain from `c` up to its module: `KIND@file:span` joined by `>`. A cycle in
        the parent links ends the chain."""
        parts, cur, seen = [], c, set()
        while cur and cur not in seen:
            seen.add(cur)
            con = self.nm.constructs[cur - 1]
            parts.append(f"{con.kind}@{norm(self._path(con))}:{con.span}")
            cur = con.parent
        return ">".join(parts)

    def pass_of(self, rec: Any) -> str:
        m = re.match(r"t(\d+)\.", rec.step)
        if not m or not 1 <= int(m.group(1)) <= len(self.nm.runs):
            return "unknown"
        return str(self.nm.runs[int(m.group(1)) - 1][0])

    def join_records(self) -> list[JoinRec]:
        """The records that join (V1.2.0 3.3): `join` (distinct constructs, named by `cons`) and
        `join=instance` (the same construct reached through two instances: named by the record's
        own leaves, since `cons` never holds instance members). An instance join's label is
        `instance:<pass>`. A record with both flags gives two entries."""
        out: list[JoinRec] = []
        for rec in self.nm.records:
            if rec.kind != "D":
                continue
            if "join" in rec.flags:
                cons = frozenset(c for c in rec.constructs if c)
                out.append(JoinRec(rec.number, rec.level, self.pass_of(rec), cons))
            if "join=instance" in rec.flags:
                out.append(JoinRec(rec.number, rec.level, "instance:" + self.pass_of(rec),
                                   self.leaves(rec.number)))
        return out

    def capped_reach(self, rec: int) -> bool:
        """True when a record reachable from `rec` has `lossy=cap`: its `cons` lists only 16 of
        the constructs it joined, so a construct may have been joined without being named."""
        if rec not in self._capped:
            self._capped[rec] = any("lossy=cap" in r.flags for r in
                                    self.d.units.provenance_records(self.nm, self.records, rec))
        return self._capped[rec]


# ---------------------------------------------------------------- HDL structures

def hdl_structs(view: MapView, blocks: Iterable[int], texts: Mapping[str, str],
                norm: Callable[[str], str]) -> dict[int, Struct]:
    """A block Struct per block, classified from its construct kind and source text. A block whose
    text is not available has kind `unknown` and no confidence."""
    nm, out = view.nm, {}
    arrays = {p: array_names(t) for p, t in texts.items()}
    for b in sorted(blocks):
        con = nm.constructs[b - 1]
        path = nm.files[con.file - 1] if con.file else ""
        if not is_block_kind(con.kind):
            continue
        text = span_slice(texts.get(path, ""), con.span)
        kind, conf = classify(con.kind, text, arrays.get(path, frozenset()))
        sid = f"hdl:{norm(path)}:{con.span}"
        out[b] = Struct(sid, kind, view.span_text(b, norm), view.chain_text(b, norm), "hdl", conf)
    return out


def operator_structs(view: MapView, leaves: Iterable[int], blocks: Mapping[int, Struct],
                     texts: Mapping[str, str], norm: Callable[[str], str]) -> dict[int, Struct]:
    """An operator Struct per `BINARY` or `TERNARY` construct among `leaves` whose operator has a
    kind (`classify_operator`) and whose block is a structure. Its id is the block's id scheme
    with the suffix `:op`; its parent is the block's id."""
    nm, out = view.nm, {}
    for c in sorted(set(leaves)):
        con = nm.constructs[c - 1]
        block = view.block_of(c)
        if con.kind not in OPERATOR_CONSTRUCTS or block not in blocks:
            continue
        path = nm.files[con.file - 1] if con.file else ""
        got = classify_operator(con.kind, span_slice(texts.get(path, ""), con.span))
        if got is None:
            continue
        out[c] = Struct(f"hdl:{norm(path)}:{con.span}:op", got[0], view.span_text(c, norm),
                        view.chain_text(c, norm), "hdl", got[1], "operator", blocks[block].sid)
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
    with no atom in the `A` lines gets no row at these levels. A `placed` row counts sites
    (`n_sites`); `n_clbs` is NULL there."""
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
            elif lv == "clb":
                row.n_clbs = row.n_objects
            else:
                row.n_sites = row.n_objects
                pts = sorted({p for r in objs if (p := site_xy.get(int(r[1:]))) is not None})
                if pts:
                    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
                    row.bbox = (min(xs), min(ys), max(xs), max(ys))
                    row.spread = _spread(pts)
            rows.append(row)
    return rows


def _views(view: MapView, names: Mapping[str, frozenset[int]], typ: str) -> list[Any]:
    """Loki `ObjView` values (units = the keys of the unit constructs) for `separable`."""
    cls = view.d.units.ObjView
    return [cls(n, typ, frozenset(view.key(b) for b in bs), frozenset(), False)
            for n, bs in sorted(names.items())]


def _named_by(view: MapView, unit: int, joins: list[JoinRec], levels: frozenset[str],
              kind: str) -> list[tuple[int, str]]:
    """(record number, label) of the join records at `levels` that name the structure `unit`: a
    block is named by a construct inside it (join `cons` are anchors, inside their block); an
    operator by the construct that contains it, or itself."""
    hits = []
    for j in joins:
        if j.level not in levels:
            continue
        if kind == "block":
            named = any(view.block_of(c) == unit for c in j.constructs)
        else:
            named = any(view.is_ancestor_or_self(c, unit) for c in j.constructs)
        if named:
            hits.append((j.number, j.label))
    return sorted(hits)


def lost_label(n_pure: int, named: list[tuple[int, str]], capped: bool, kind: str) -> str:
    """'' when the structure has a pure object; else the label of the earliest (lowest numbered)
    join record that names it; else `capped` when a record behind its objects lists only 16 of
    the constructs it joined (V1.2.0 3.3, `lossy=cap`); else `born-joined` for a block (L15's
    name) or `intra-statement` for an operator (merged with a construct of its own statement,
    which V1.2.0 3.3 does not call a join)."""
    if n_pure:
        return ""
    if named:
        return min(named)[1]
    if capped:
        return "capped"
    return "born-joined" if kind == "block" else "intra-statement"


def _rows(view: MapView, structs: Mapping[int, Struct], obj_units: Mapping[str, frozenset[int]],
          level: str, typ: str, joins: list[JoinRec], levels: frozenset[str],
          capped: Mapping[str, bool], kind: str) -> list[tuple[MapRow, list[str]]]:
    """Mapping rows (and the member objects) of the structures `structs` (keyed by unit construct)
    over the objects `obj_units` (object -> unit constructs it traces to)."""
    pure = view.d.loss.separable(_views(view, obj_units, typ))
    rows = []
    for u, st in sorted(structs.items()):
        mine = sorted(o for o, us in obj_units.items() if u in us)
        if not mine:
            continue
        row = MapRow(st.sid, level, len(mine), len(pure.get(view.key(u), [])))
        row.n_shared = row.n_objects - row.n_pure
        row.joined_with = _join_text(structs[o].sid for n in mine for o in obj_units[n]
                                     if o != u and o in structs and structs[o].sid != st.parent)
        row.lost_at_pass = lost_label(row.n_pure, _named_by(view, u, joins, levels, kind),
                                      any(capped.get(n, False) for n in mine), kind)
        rows.append((row, mine))
    return rows


def unit_sets(view: MapView, leaves: Mapping[str, frozenset[int]], blocks: Mapping[int, Struct],
              ops: Mapping[int, Struct]) -> tuple[dict[str, frozenset[int]],
                                                  dict[str, frozenset[int]]]:
    """For each object its block units and its operator units. Block units: the structure blocks
    of its leaves. Operator units: a leaf is mapped to the nearest operator structure at or above
    it, else to its block; a block unit is dropped when the object also has an operator unit
    inside it (a construct and its own parent are not distinct, as in L15's `reduce_units`)."""
    by_block: dict[str, frozenset[int]] = {}
    by_op: dict[str, frozenset[int]] = {}
    for name, cs in leaves.items():
        by_block[name] = frozenset(b for b in (view.block_of(c) for c in cs) if b in blocks)
        units: set[int] = set()
        for c in cs:
            cur, seen, hit = c, 0, 0
            while cur and seen <= len(view.nm.constructs):
                if cur in ops:
                    hit = cur
                    break
                cur = view.nm.constructs[cur - 1].parent
                seen += 1
            b = view.block_of(c)
            if hit:
                units.add(hit)
            elif b in blocks:
                units.add(b)
        op_units = {u for u in units if u in ops}
        by_op[name] = frozenset(u for u in units if u in ops or not any(
            view.block_of(o) == u for o in op_units))
    return by_block, by_op


def analyse(nm: Any, deps: Deps, atoms: Mapping[str, str], texts: Mapping[str, str],
            norm: Callable[[str], str]) -> Analysis:
    """Structures from the HDL (block and operator level), their mapping at gate, lut, ble, clb and
    placed level, and the L15 cross-check counts, for one run's map."""
    view, res = MapView(nm, deps), Analysis()
    atom_rec: dict[str, int] = {}
    atom_leaves: dict[str, frozenset[int]] = {}
    for a in sorted(atoms):
        obj = nm.atom(a)
        if obj is None or not obj.records or not view.leaves(obj.records[0]):
            res.unattributed += 1
            continue
        atom_rec[a] = obj.records[0]
        atom_leaves[a] = view.leaves(obj.records[0])
    gate_rec: dict[int, Any] = {}
    for rec in atom_rec.values():
        for r in deps.units.provenance_records(nm, view.records, rec):
            if r.level == "gate" and r.number not in gate_rec:
                gate_rec[r.number] = r
    gate_leaves = {f"r{n}": view.leaves(n) for n in sorted(gate_rec)}
    all_leaves = {c for cs in (*atom_leaves.values(), *gate_leaves.values()) for c in cs}
    blocks = hdl_structs(view, {view.block_of(c) for c in all_leaves} - {0}, texts, norm)
    ops = operator_structs(view, all_leaves, blocks, texts, norm)
    joins = view.join_records()
    a_block, a_op = unit_sets(view, atom_leaves, blocks, ops)
    g_block, g_op = unit_sets(view, gate_leaves, blocks, ops)
    g_block = {n: u for n, u in g_block.items() if u}
    g_op = {n: u for n, u in g_op.items() if u}
    atom_cap = {a: view.capped_reach(r) for a, r in atom_rec.items()}
    gate_cap = {n: view.capped_reach(int(n[1:])) for n in gate_leaves}
    res.structs = [*(blocks[b] for b in sorted(blocks)), *(ops[c] for c in sorted(ops))]
    res.unknown_structs = sum(1 for s in res.structs if s.kind == "unknown")
    members: dict[str, set[str]] = {}
    lut_rows: list[MapRow] = []
    for structs, units, kind in ((blocks, a_block, "block"), (ops, a_op, "operator")):
        for row, mine in _rows(view, structs, units, "lut", "atom", joins, LUT_LEVELS, atom_cap,
                               kind):
            row.n_luts = sum(atoms[a] == LUT for a in mine)
            row.n_ffs = sum(atoms[a] == FF for a in mine)
            row.n_carry = sum(atoms[a] == CARRY for a in mine)
            lut_rows.append(row)
            members[row.sid] = set(mine)
    gate_rows: list[MapRow] = []
    for structs, units, kind in ((blocks, g_block, "block"), (ops, g_op, "operator")):
        for row, mine in _rows(view, structs, units, "gate", "gate", joins, GATE_LEVELS, gate_cap,
                               kind):
            row.n_gates = len(mine)
            gate_rows.append(row)
    in_lut = {r.sid for r in lut_rows}
    res.gate_only = len({r.sid for r in gate_rows} - in_lut)
    res.rows = gate_rows + lut_rows
    for sid, held in members.items():
        for a in held:
            res.atom_structs[a] = res.atom_structs.get(a, frozenset()) | {sid}
    res.rows += post_levels(nm, members)
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
