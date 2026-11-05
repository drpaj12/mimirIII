"""Tests for the dblclockfft testbench generator (data/benchmarks/opencores-tb/dblclockfft)."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from types import ModuleType

from tests.helpers import skip_without

DIR = Path(__file__).resolve().parent.parent / "data/benchmarks/opencores-tb/dblclockfft"

FFTMAIN = """
	localparam	IWIDTH=15, OWIDTH=21, LGWIDTH=3;
	fftstage	#(IWIDTH,IWIDTH+4,16,2,0,
			0, 1, "cmem_8.hex")
		stage_8(i_clk, i_reset, i_ce, (!i_reset), i_sample, w_d8, w_s8);
	fftstage	#(16,20,17,1,0,
			0, 1, "cmem_4.hex")
		stage_4(i_clk, i_reset, i_ce, w_s8, w_d8, w_d4, w_s4);
"""


def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("gen_fft_vectors", DIR / "gen_fft_vectors.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FftVectors(unittest.TestCase):
    def test_parse_core(self) -> None:
        g = load()
        self.assertEqual(g.parse_core(FFTMAIN), (15, 21, 3, [(8, 19), (4, 20)]))
        with self.assertRaises(ValueError):
            g.parse_core("nothing")

    def test_twiddles_match_the_project_c_generator(self) -> None:
        # lines of gen_coeffs() of sw/fftlib.cpp compiled with g++ (stage 8, 24 bits; stage 16, 23)
        g = load()
        self.assertEqual(
            g.coeff_lines(8, 24),
            ["400000000000", "2d413dd2bec3", "000000c00000", "d2bec3d2bec3"],
        )
        self.assertEqual(
            g.coeff_lines(16, 23)[:3], ["100000000000", "0ec83673c10f", "0b504f695f62"]
        )

    def test_llround_halves_away_from_zero(self) -> None:
        g = load()
        self.assertEqual([g.llround(x) for x in (0.5, -0.5, 1.5, -1.5, 0.4)], [1, -1, 2, -2, 0])

    def test_frames_fit_the_input_width_with_headroom(self) -> None:
        g = load()
        frames = g.input_frames(64, 15)
        self.assertEqual(len(frames), g.FRAMES)
        # dense frames (tone, random) stay below 2**15 / (2 * sqrt(2)): the first stage output is
        # 16 bits and a complex difference rotated by a twiddle can reach |d| * sqrt(2)
        peak = max(abs(v) for fr in frames[3:] for s in fr for v in s)
        self.assertLessEqual(peak, 11585)
        self.assertEqual(sum(1 for s in frames[0] if s != (0, 0)), 1)  # impulse frame

    def test_pack_in(self) -> None:
        g = load()
        self.assertEqual(g.pack_in(8000, 0, 15), "0fa00000\n")
        self.assertEqual(g.pack_in(-1, -1, 15), "3fffffff\n")

    @skip_without("numpy")
    def test_impulse_frame_is_flat_at_the_core_scale(self) -> None:
        g = load()
        exp = g.expected_frames([[(8000, 0)] + [(0, 0)] * 63], 5)
        self.assertEqual(set(exp[0]), {(250, 0)})

    @skip_without("numpy")
    def test_committed_vectors_equal_the_generator(self) -> None:
        g = load()
        text = (DIR / "fftmain_stages.txt").read_text(encoding="utf-8")
        files = g.build(text)
        self.assertEqual(files, g.build(text))
        for name in ("in.hex", "exp.hex", "cmem_2048.hex", "cmem_8.hex"):
            self.assertEqual((DIR / name).read_text(encoding="utf-8"), files[name], name)

    def test_odin_variant_differs_only_by_the_forces(self) -> None:
        a = (DIR / "tb_fft.v").read_text(encoding="utf-8").splitlines()
        b = (DIR / "tb_fft_odin.v").read_text(encoding="utf-8").splitlines()
        only_a = [x for x in a if x not in b]
        self.assertTrue(only_a)
        self.assertTrue(all(("force" in x or x.lstrip().startswith("//")) for x in only_a))
        self.assertEqual([x for x in b if x not in a], [])


if __name__ == "__main__":
    unittest.main()
