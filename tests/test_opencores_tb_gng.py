"""Tests for the gng testbench vector generator (data/benchmarks/opencores-tb/gng)."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from types import ModuleType

GEN = Path(__file__).resolve().parent.parent / "data/benchmarks/opencores-tb/gng/gen_gng_vectors.py"


def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("gen_gng_vectors", GEN)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fake_icdf_c() -> str:
    """A text shaped like the upstream icdf.c with 248-entry tables of in-range numbers."""
    parts = []
    for name, base in (("C0", 1000), ("C1", -500), ("C2", 2000)):
        vals = ", ".join(str(base + 7 * i) for i in range(248))
        parts.append(f"static const long {name}[248] = {{\n    {vals}\n}};\n")
    return "\n".join(parts)


class GngVectors(unittest.TestCase):
    def test_taus_matches_the_project_c_model(self) -> None:
        # values from the project's taus176.c compiled with gcc, same initial state
        g = load()
        z = list(g.INIT_Z)
        got = [g.taus_get(z) for _ in range(3)]
        self.assertEqual(got, [9591131212184117239, 8637903559624331643, 17275325125578610])
        self.assertEqual(z, [11546666511291908119, 914795016486272, 11529250036092678885])

    def test_parse_tables_and_errors(self) -> None:
        g = load()
        t = g.parse_tables(fake_icdf_c())
        self.assertEqual(len(t["C1"]), 248)
        self.assertEqual(t["C1"][0], -500)
        with self.assertRaises(ValueError):
            g.parse_tables("static const long C0[2] = { 1, 2, 3 };")
        with self.assertRaises(ValueError):
            g.parse_tables("nothing here")

    def test_icdf_hand_example(self) -> None:
        # n = 0x90: 56 leading zeros, address 224; with the fake tables x = 8192, sign bit 0
        g = load()
        t = g.parse_tables(fake_icdf_c())
        c0, c1, c2 = t["C0"][224], t["C1"][224], t["C2"][224]
        y = (c2 * 8192 + (c1 << 19)) >> 20
        y = ((y * 8192) >> 19) + c0
        y = (y >> 3) + (1 if y & 4 else 0)
        self.assertEqual(g.icdf(0x90, t), y)
        self.assertEqual(g.icdf(0x91, t), -y)

    def test_interp_inputs_cover_every_group(self) -> None:
        g = load()
        words, flags = g.interp_inputs()
        self.assertEqual(len(words), 62 * 25)
        self.assertEqual(flags.count(0), 62)
        self.assertEqual(words, g.interp_inputs()[0])
        seen = set()
        for w in words:
            lz = 0
            while lz < 61 and not (w >> (63 - lz)) & 1:
                lz += 1
            seen.add(lz)
        self.assertEqual(seen, set(range(62)))

    def test_build_is_deterministic_and_in_range(self) -> None:
        g = load()
        a = g.build(fake_icdf_c())
        self.assertEqual(a, g.build(fake_icdf_c()))
        self.assertEqual(
            set(a),
            {"gng_coef.v", "stream_exp.hex", "interp_in.hex", "interp_exp.hex", "interp_chk.hex"},
        )
        self.assertEqual(len(a["stream_exp.hex"].split()), g.STREAM_N)
        self.assertEqual(a["interp_in.hex"].count("\n"), a["interp_exp.hex"].count("\n"))
        self.assertIn("8'd247:", a["gng_coef.v"])
        self.assertTrue(all(len(x) == 4 for x in a["stream_exp.hex"].split()))


if __name__ == "__main__":
    unittest.main()
