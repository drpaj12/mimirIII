"""AI digit recognition suite (suites/ai-digit-recognition): pins, fetch, retiler, testbench."""

from __future__ import annotations

import gzip
import hashlib
import importlib
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from types import ModuleType

from mimir import bench

SUITE = Path(__file__).resolve().parents[1] / "suites" / "ai-digit-recognition"


def _load(name: str) -> ModuleType:
    for sub in ("tools", "."):
        p = str(SUITE / sub)
        if p not in sys.path:
            sys.path.insert(0, p)
    sys.dont_write_bytecode = True
    return importlib.import_module(name)


class Pins(unittest.TestCase):
    def test_pins_are_well_formed_and_match_the_registry(self) -> None:
        pins = tomllib.loads((SUITE / "pins.toml").read_text(encoding="utf-8"))
        for d in pins["data"]:
            self.assertEqual(len(d["sha256"]), 64, d["id"])
            self.assertEqual(len(d["gz_sha256"]), 64, d["id"])
            self.assertTrue(all(u.startswith("https://") for u in d["urls"]), d["id"])
            self.assertGreater(d["bytes"], 0)
        src = pins["source"][0]
        self.assertEqual(len(src["commit"]), 40)
        suite = bench.load_suites()["ai-digit-recognition"]
        self.assertEqual(suite.commit, src["commit"])
        self.assertEqual(suite.upstream, src["repo"])

    def test_no_home_path_or_mnist_data_in_the_suite(self) -> None:
        for p in SUITE.rglob("*"):
            if p.is_file() and p.suffix in (".py", ".v", ".md", ".toml"):
                self.assertNotIn("/home/", p.read_text(encoding="utf-8"), str(p))
            self.assertNotIn("idx3-ubyte", p.name)


class Fetch(unittest.TestCase):
    def test_local_copy_is_verified_and_a_wrong_hash_refused(self) -> None:
        fd = _load("fetch_data")
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            payload = b"abc" * 10
            (tmp / "local").mkdir()
            (tmp / "local" / "f-ubyte.gz").write_bytes(gzip.compress(payload))
            pins = tmp / "pins.toml"
            sha = hashlib.sha256(payload).hexdigest()
            entry = f'[[data]]\nid = "x"\nfile = "f-ubyte"\nbytes = {len(payload)}\n'
            pins.write_text(entry + f'sha256 = "{sha}"\ngz_sha256 = "0"\nurls = []\n')
            old = fd.PINS
            fd.PINS = pins
            try:
                out = fd.fetch(tmp / "out", tmp / "local")
                self.assertEqual(out[0].read_bytes(), payload)
                pins.write_text(entry + f'sha256 = "{"0" * 64}"\ngz_sha256 = "0"\nurls = []\n')
                with self.assertRaises(SystemExit):
                    fd.fetch(tmp / "out2", tmp / "local")
                self.assertFalse((tmp / "out2" / "f-ubyte").exists())
            finally:
                fd.PINS = old


class Retile(unittest.TestCase):
    def test_a_long_contraction_splits_into_multip_then_mult(self) -> None:
        rp = _load("retile_program")
        instr = rp.enc_mul({"src1": 100, "m": 3, "k": 8, "src2": 200, "k2": 8, "n": 5,
                            "dest": 300, "m0": 7, "sh": 4, "f3": 0})
        out = rp.retile([instr], 4)
        muls = [rp.dec_mul(x) for x in out if rp.opcode(x) == rp.OP_MUL]
        # 3x8 times 8x5 on a 4x4 array: 1 row tile x 2 column tiles x 2 K chunks
        self.assertEqual(len(muls), 4)
        self.assertEqual([m["f3"] for m in muls], [1, 0, 1, 0])
        self.assertEqual([m["n"] for m in muls], [4, 4, 1, 1])
        self.assertTrue(all(m["k"] == 4 and m["m"] == 3 for m in muls))
        self.assertEqual(muls[2]["dest"], 300 + 4)

    def test_n8_program_is_unchanged_in_instruction_count_for_small_tiles(self) -> None:
        rp = _load("retile_program")
        instr = rp.enc_mul({"src1": 5, "m": 2, "k": 2, "src2": 9, "k2": 2, "n": 2,
                            "dest": 20, "m0": 1, "sh": 0, "f3": 0})
        self.assertEqual(sum(rp.opcode(x) == rp.OP_MUL for x in rp.retile([instr], 8)), 1)


class Testbench(unittest.TestCase):
    @unittest.skipUnless(shutil.which("iverilog"), "iverilog not installed")
    def test_init_wait_and_pass_on_a_two_image_tier(self) -> None:
        dut = """
module mnist_top (input clk, input rst, input start, input in_valid, input [7:0] in_data,
  output in_ready, output reg done, output [3:0] pred, output [79:0] scores);
  reg [9:0] cnt; reg busy; reg [4:0] init;
  assign in_ready = busy;
  assign pred = 4'd3;
  assign scores = 80'h0102030405060708090a;
  always @(posedge clk) begin
    if (rst) begin cnt <= 0; busy <= 0; done <= 0; init <= 0; end
    else if (init != 5'd20) begin init <= init + 1'b1; if (init == 5'd19) done <= 1; end
    else if (start) begin cnt <= 0; busy <= 1; done <= 0; end
    else if (busy && in_valid) begin
      if (cnt == 10'd783) begin busy <= 0; done <= 1; end
      cnt <= cnt + 10'd1;
    end
  end
endmodule
"""
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "dut.v").write_text(dut)
            (t / "vec_images.hex").write_text("00\n" * (2 * 784))
            (t / "vec_labels.hex").write_text("3\n3\n")
            (t / "vec_gclass.hex").write_text("3\n3\n")
            (t / "vec_gscores.hex").write_text("\n".join(
                f"{v:02x}" for _ in range(2) for v in range(10, 0, -1)) + "\n")
            (t / "vec_meta.hex").write_text("2\n100000\n")
            tb = str(SUITE / "tb" / "mnist_tb.v")
            subprocess.run(["iverilog", "-g2005", "-DMNIST_N=2", "-DMNIST_INIT=1000", "-o",
                            "t.vvp", tb, "dut.v"], cwd=t, check=True, capture_output=True)
            out = subprocess.run(["vvp", "t.vvp"], cwd=t, check=True, capture_output=True,
                                 text=True).stdout
            self.assertIn("MNIST_TB PASS n=2 class_match=2 score_match=2", out)
            self.assertIn("init_cycles=", out)


if __name__ == "__main__":
    unittest.main()
