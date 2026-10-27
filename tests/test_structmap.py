"""Needs the Odin III tree (tools/flow/name_map_v2.py) and the Loki checkout: set
MIMIR_ODIN3_TREE and MIMIR_LOKI_SRC, else these tests skip."""

from __future__ import annotations

import os
import unittest
from pathlib import Path

from mimir.blif import parse_models
from mimir.structmap import Analysis, Deps, MapView, analyse, atoms_from_blif, load_deps

FIX = Path(__file__).parent / "fixtures" / "structures"
TREE, LOKI = os.environ.get("MIMIR_ODIN3_TREE"), os.environ.get("MIMIR_LOKI_SRC")
ready = unittest.skipUnless(TREE and LOKI, "MIMIR_ODIN3_TREE and MIMIR_LOKI_SRC not set")
_DEPS: list[Deps] = []


def deps() -> Deps:
    if not _DEPS:
        assert TREE and LOKI
        _DEPS.append(load_deps(Path(TREE), Path(LOKI)))
    return _DEPS[0]


def run(name: str) -> tuple[Analysis, object]:
    d = deps()
    nm = d.nmv2.read_name_map(FIX / name / f"{name}.blif.names")
    models = parse_models((FIX / name / f"{name}.blif").read_text(encoding="utf-8"))
    atoms = atoms_from_blif(models, lambda n: nm.atom(n) is not None)
    texts = {f: (FIX / name / f"{name}.v").read_text(encoding="utf-8") for f in nm.files}
    return analyse(nm, d, atoms, texts, lambda p: p), nm


@ready
class StructMapTests(unittest.TestCase):
    def test_adders_of_a_lpm_micro(self) -> None:
        a, _ = run("bm_dag3_lpm")
        kinds = sorted(s.kind for s in a.structs)
        self.assertEqual(kinds, ["adder"] * 5)
        lut = {r.sid: r for r in a.rows if r.level == "lut"}
        self.assertEqual(set(lut), {s.sid for s in a.structs})
        self.assertTrue(all(r.n_objects == (r.n_luts or 0) + (r.n_ffs or 0) + (r.n_carry or 0)
                            for r in lut.values()))

    def test_pure_matches_a_direct_count(self) -> None:
        for name in ("bm_dag3_lpm", "bm_dag1_log_mod"):
            a, _ = run(name)
            for r in (x for x in a.rows if x.level == "lut"):
                direct = sum(1 for sids in a.atom_structs.values() if sids == {r.sid})
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

    def test_block_of_is_outermost_process(self) -> None:
        d = deps()
        nm = d.nmv2.read_name_map(FIX / "bm_dag3_lpm" / "bm_dag3_lpm.blif.names")
        v = MapView(nm, d)
        kinds = {nm.constructs[v.block_of(c.number) - 1].kind for c in nm.constructs
                 if v.block_of(c.number)}
        self.assertFalse(kinds - {"ALWAYS", "CONT_ASSIGN", "NET_ASSIGN", "INSTANCE", "GATE_DECL"})
