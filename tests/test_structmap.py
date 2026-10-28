"""Extraction tests on two committed micro maps (tests/fixtures/structures). They need Odin III's
`name_map_v2` and Loki's `loki.audit`: the real checkouts when MIMIR_ODIN3_TREE and MIMIR_LOKI_SRC
are set, else the vendored copies of tests/fixtures/deps (see its README)."""

from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from mimir.blif import parse_models
from mimir.structmap import (
    Analysis,
    MapView,
    analyse,
    atoms_from_blif,
    lost_label,
)
from tests.depsfix import FIXTURES, deps

FIX = FIXTURES / "structures"


def run(name: str, with_text: bool = True) -> tuple[Analysis, Any]:
    d = deps()
    nm = d.nmv2.read_name_map(FIX / name / f"{name}.blif.names")
    models = parse_models((FIX / name / f"{name}.blif").read_text(encoding="utf-8"))
    atoms = atoms_from_blif(models, lambda n: nm.atom(n) is not None)
    text = (FIX / name / f"{name}.v").read_text(encoding="utf-8")
    texts = {f: text for f in nm.files} if with_text else {}
    return analyse(nm, d, atoms, texts, lambda p: Path(p).name), nm


class StructMapTests(unittest.TestCase):
    def test_adders_of_a_lpm_micro(self) -> None:
        a, _ = run("bm_dag3_lpm")
        blocks = [s for s in a.structs if s.granularity == "block"]
        ops = [s for s in a.structs if s.granularity == "operator"]
        self.assertEqual(sorted(s.kind for s in blocks), ["adder"] * 5)
        self.assertEqual(sorted(s.kind for s in ops), ["adder"] * 7)
        self.assertTrue(all(s.sid.endswith(":op") and s.parent for s in ops))
        lut = {r.sid for r in a.rows if r.level == "lut"}
        self.assertEqual(lut, {s.sid for s in a.structs})
        for r in (x for x in a.rows if x.level == "lut"):
            self.assertEqual(r.n_objects, (r.n_luts or 0) + (r.n_ffs or 0) + (r.n_carry or 0))

    def test_pure_matches_a_direct_count(self) -> None:
        for name in ("bm_dag3_lpm", "bm_dag1_log_mod"):
            a, _ = run(name)
            for r in (x for x in a.rows if x.level == "lut" and not x.sid.endswith(":op")):
                direct = sum(1 for sids in a.atom_structs.values()
                             if {s for s in sids if not s.endswith(":op")} == {r.sid})
                self.assertEqual(r.n_pure, direct, (name, r.sid))
                self.assertEqual(r.lost_at_pass == "", r.n_pure > 0)

    def test_registers_and_logic(self) -> None:
        a, _ = run("bm_dag1_log_mod")
        kinds = sorted(s.kind for s in a.structs)
        self.assertEqual(kinds.count("register_word"), 3)
        self.assertEqual(kinds.count("logic"), 2)

    def test_no_home_path_in_ids(self) -> None:
        a, _ = run("bm_dag1_log_mod")
        self.assertTrue(all("/home/" not in s.sid + s.chain for s in a.structs))

    def test_l15_counts_are_consistent(self) -> None:
        a, _ = run("bm_dag3_lpm")
        self.assertGreaterEqual(a.l15_units, a.l15_separable)
        self.assertGreater(a.l15_units, 0)

    def test_unresolved_atoms_are_counted_not_dropped(self) -> None:
        a, nm = run("bm_dag3_lpm")
        models = parse_models((FIX / "bm_dag3_lpm" / "bm_dag3_lpm.blif").read_text(
            encoding="utf-8"))
        every = atoms_from_blif(models, lambda n: True)
        none = atoms_from_blif(models, lambda n: False)
        self.assertEqual(len(every), len(none))  # the unresolved are kept (first candidate)
        attributed = len({atom for atom in a.atom_structs})
        self.assertEqual(attributed + a.unattributed, len(every))
        self.assertGreater(a.unattributed, 0)

    def test_missing_text_gives_unknown_kind(self) -> None:
        a, _ = run("bm_dag3_lpm", with_text=False)
        blocks = [s for s in a.structs if s.granularity == "block"]
        self.assertTrue(blocks)
        self.assertTrue(all(s.kind == "unknown" and s.conf is None for s in blocks))
        self.assertEqual(a.unknown_structs, len(a.structs))
        self.assertFalse([s for s in a.structs if s.granularity == "operator"])

    def test_no_lut_row_without_atoms(self) -> None:
        a, _ = run("bm_dag3_lpm")
        self.assertTrue(all(r.n_objects > 0 for r in a.rows))

    def test_block_of_is_outermost_process(self) -> None:
        d = deps()
        nm = d.nmv2.read_name_map(FIX / "bm_dag3_lpm" / "bm_dag3_lpm.blif.names")
        v = MapView(nm, d)
        kinds = {nm.constructs[v.block_of(c.number) - 1].kind for c in nm.constructs
                 if v.block_of(c.number)}
        self.assertFalse(kinds - {"ALWAYS", "CONT_ASSIGN", "NET_ASSIGN", "INSTANCE", "GATE_DECL"})

    def test_chain_text_stops_on_a_cycle(self) -> None:
        cons = [SimpleNamespace(kind="A", file=0, span="1.1-1.2", parent=2),
                SimpleNamespace(kind="B", file=0, span="1.1-1.2", parent=1)]
        nm = SimpleNamespace(constructs=cons, files=[], records=[])
        text = MapView(nm, deps()).chain_text(1, lambda p: p)
        self.assertEqual(text, "A@:1.1-1.2>B@:1.1-1.2")


class JoinTests(unittest.TestCase):
    def rec(self, n: int, flags: tuple[str, ...], cons: tuple[int, ...], step: str = "t1.1"
            ) -> SimpleNamespace:
        return SimpleNamespace(number=n, kind="D", flags=flags, constructs=cons, level="lut",
                               step=step, parents=(), origins=())

    def view(self, records: list[SimpleNamespace]) -> MapView:
        nm = SimpleNamespace(records=records, runs=[("abc", "")], constructs=[], files=[])
        return MapView(nm, deps())

    def test_instance_and_plain_joins_are_labelled(self) -> None:
        v = self.view([self.rec(1, ("join",), (3,)), self.rec(2, ("join=instance",), ()),
                       self.rec(3, ("lossy=cap",), ())])
        got = {(j.number, j.label) for j in v.join_records()}
        self.assertEqual(got, {(1, "abc"), (2, "instance:abc")})

    def test_capped_reach(self) -> None:
        v = self.view([self.rec(1, ("lossy=cap",), ()), self.rec(2, (), ())])
        self.assertTrue(v.capped_reach(1))
        self.assertFalse(v.capped_reach(2))

    def test_lost_label_rules(self) -> None:
        self.assertEqual(lost_label(2, [(1, "abc")], True, "block"), "")
        self.assertEqual(lost_label(0, [(4, "abc"), (2, "opt")], False, "block"), "opt")
        self.assertEqual(lost_label(0, [], True, "block"), "capped")
        self.assertEqual(lost_label(0, [], False, "block"), "born-joined")
        self.assertEqual(lost_label(0, [], False, "operator"), "intra-statement")
