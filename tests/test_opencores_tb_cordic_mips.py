"""Tests for the verilog_cordic_core and mips_16 testbench generators."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from types import ModuleType

BASE = Path(__file__).resolve().parent.parent / "data/benchmarks/opencores-tb"


def load(project: str, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, BASE / project / f"{name}.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class CordicVectors(unittest.TestCase):
    def test_known_values(self) -> None:
        g = load("verilog_cordic_core", "gen_cordic_vectors")
        codes = g.angle_codes()
        self.assertEqual(len(codes), 200)
        self.assertEqual(codes[:3], [0, 572, 1144])
        self.assertEqual(g.expected(0), (0, 32768))
        self.assertEqual(g.expected(51471)[0], 32768)  # 90 degrees: sin = 1 (rounded)
        self.assertLessEqual(max(codes), 51472)  # 90 degrees rounds to 51472

    def test_build_matches_committed_files(self) -> None:
        g = load("verilog_cordic_core", "gen_cordic_vectors")
        files = g.build()
        self.assertEqual(files, g.build())
        for name, text in files.items():
            path = BASE / "verilog_cordic_core" / name
            self.assertEqual(path.read_text(encoding="utf-8"), text, name)


class MipsPrograms(unittest.TestCase):
    def test_encoding_matches_the_project_test2_prog(self) -> None:
        # first two lines of the project's test2.prog: ADDI R1,R0,28 and ADDI R2,R0,17
        g = load("mips_16", "gen_mips_programs")
        self.assertEqual(g.enc_i("ADDI", 1, 0, 28), 0b1001001000011100)
        self.assertEqual(g.enc_i("ADDI", 2, 0, 17), 0b1001010000010001)
        self.assertEqual(g.enc_r("ADD", 3, 3, 1), 0b0001011011001000)  # test2.prog line 10

    def test_model_values(self) -> None:
        g = load("mips_16", "gen_mips_programs")
        regs, mem = g.run_model(g.PROGRAMS["shift_mem"])
        self.assertEqual(regs[3], 0xFFF4)
        self.assertEqual(regs[4], 0xFFFF)
        self.assertEqual(regs[5], 0x3FFF)
        self.assertEqual(regs[6], 0xFFF5)
        self.assertEqual(mem, {4: 0xFFF4, 5: 0xFFFF})
        regs, _ = g.run_model(g.PROGRAMS["alu"])
        self.assertEqual(regs[1:], [12, 5, 17, 7, 4, 13, 0xFFF9])

    def test_immediate_range(self) -> None:
        g = load("mips_16", "gen_mips_programs")
        with self.assertRaises(ValueError):
            g.enc_i("ADDI", 1, 0, 32)

    def test_build_matches_committed_files(self) -> None:
        g = load("mips_16", "gen_mips_programs")
        for name, text in g.build().items():
            self.assertEqual((BASE / "mips_16" / name).read_text(encoding="utf-8"), text, name)


if __name__ == "__main__":
    unittest.main()
