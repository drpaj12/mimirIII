from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

from mimir.scrub import Scrubber, check_clean
from mimir.structdet import (
    DetectRun,
    compare,
    confusion,
    kind_of,
    read_structs,
    run_loki,
    scoring_set,
)
from tests.helpers import tmpdir


def hd(kind: str, atoms: set[str], gran: str = "operator") -> tuple[str, set[str], str]:
    return kind, atoms, gran


class CompareTests(unittest.TestCase):
    def test_precision_and_recall(self) -> None:
        hdl = {"h1": hd("adder", {"a", "b", "c"}), "h2": hd("mux", {"d"}),
               "h3": hd("fsm", {"e", "f"}, "block")}
        det = {"d1": ("adder", {"a", "b"}),       # correct, finds h1
               "d2": ("mux", {"a"}),              # lands on h1 (adder): wrong
               "d3": ("counter", {"e"}),          # lands on h3 (fsm): wrong
               "d4": ("mux", {"zz"})}             # no overlap: not matched
        got = {s.kind: s for s in compare(hdl, det)}
        self.assertEqual((got["adder"].detected, got["adder"].correct, got["adder"].found),
                         (1, 1, 1))
        self.assertEqual(got["adder"].precision, 1.0)
        self.assertEqual(got["adder"].recall, 1.0)
        self.assertEqual((got["mux"].detected, got["mux"].correct), (2, 0))
        self.assertEqual(got["mux"].recall, 0.0)
        self.assertIsNone(got["counter"].recall)  # no HDL counter
        self.assertEqual(got["fsm"].recall, 0.0)
        self.assertEqual((got["fsm"].hdl_operator, got["fsm"].hdl_block), (0, 1))
        self.assertEqual((got["adder"].hdl_operator, got["adder"].hdl_block), (1, 0))

    def test_tie_goes_to_the_smaller_id(self) -> None:
        hdl = {"h2": hd("mux", {"a"}), "h1": hd("adder", {"a"})}
        got = {s.kind: s for s in compare(hdl, {"d": ("adder", {"a"})})}
        self.assertEqual(got["adder"].correct, 1)

    def test_empty_detector_structure_matches_nothing(self) -> None:
        got = {s.kind: s for s in compare({"h": hd("adder", {"a"})}, {"d": ("adder", set())})}
        self.assertEqual((got["adder"].detected, got["adder"].correct), (1, 0))

    def test_confusion_matrix(self) -> None:
        hdl = {"h1": hd("adder", {"a", "b"}), "h2": hd("relational", {"c"}),
               "h3": hd("mux", {"m"})}
        det = {"d1": ("adder", {"a", "b"}), "d2": ("equality", {"c"}), "d3": ("fsm", {"q"})}
        self.assertEqual(confusion(hdl, det), {
            ("adder", "adder"): 1, ("relational", "equality"): 1, ("none", "fsm"): 1,
            ("mux", "none"): 1})

    def test_scoring_set_uses_operators_and_the_residue_of_a_block(self) -> None:
        structs = {
            "blk1": ("register_word", {"ff1", "ff2", "l1", "l2"}, "block", ""),
            "op1": ("adder", {"l1", "l2"}, "operator", "blk1"),
            "blk2": ("mux", {"m1"}, "block", ""),       # no operator: whole
            "blk3": ("logic", set(), "block", "")}      # no atoms: left out
        got = scoring_set(structs)
        self.assertEqual(got["blk1"], ("register_word", {"ff1", "ff2"}, "block"))
        self.assertEqual(got["op1"][2], "operator")
        self.assertEqual(got["blk2"][1], {"m1"})
        self.assertNotIn("blk3", got)


class KindOfTests(unittest.TestCase):
    def hyp(self, kind: str, **params: object) -> dict[str, object]:
        return {"kind": kind, "params": dict(params)}

    def test_eq_const_is_equality(self) -> None:
        self.assertEqual(kind_of(self.hyp("eq_const", op="eq")), "equality")
        self.assertEqual(kind_of(self.hyp("eq_const", op="ne")), "equality")

    def test_comparator_by_operator(self) -> None:
        self.assertEqual(kind_of(self.hyp("comparator", op="eq")), "equality")
        self.assertEqual(kind_of(self.hyp("comparator", op="ne")), "equality")
        for op in ("lt", "le", "gt", "ge"):
            self.assertEqual(kind_of(self.hyp("comparator", op=op)), "relational")

    def test_others(self) -> None:
        self.assertEqual(kind_of(self.hyp("subtractor")), "adder")
        self.assertIsNone(kind_of(self.hyp("bus")))


class RunLokiTests(unittest.TestCase):
    def run_py(self, code: str, limit: float = 30.0) -> DetectRun:
        d = Path(tmpdir())
        return run_loki([sys.executable, "-c", code], d / "out", d, d, d, limit)

    def test_exit_code_and_stderr_tail_are_kept(self) -> None:
        run = self.run_py("import sys; sys.stderr.write('boom'); sys.exit(3)")
        self.assertEqual((run.returncode, run.timed_out, run.stderr_tail), (3, False, "boom"))
        self.assertGreater(run.peak_rss_mib, 0)

    def test_wall_limit_kills_the_child(self) -> None:
        run = self.run_py("import time; time.sleep(60)", 0.5)
        self.assertTrue(run.timed_out)
        self.assertEqual(run.returncode, -9)
        self.assertLess(run.time_s, 30)


class ReadStructsTests(unittest.TestCase):
    def test_filters(self) -> None:
        def hyp(hid: str, kind: str, p: float, parents: list[str], net: str) -> dict[str, object]:
            return {"id": hid, "kind": kind, "p_comp": p, "parents": parents, "detector": "mux",
                    "nets": {"Y": [net]}}

        data = {"hypotheses": [
            hyp("h1", "mux", 0.9, [], "f"), hyp("h2", "mux_bit", 0.9, ["h1"], "f"),
            hyp("h3", "mux", 0.2, [], "f"), hyp("h4", "bus", 0.9, [], "f"),
            hyp("h5", "mux", 0.9, [], "nope"), hyp("h6", "eq_const", 0.9, [], "f")]}
        path = Path(tmpdir()) / "overlay.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        structs, members = read_structs(path, {"f": "lut"}, "abcd")
        self.assertEqual([s.sid for s in structs], ["det:mux:abcd:h1", "det:mux:abcd:h6"])
        self.assertEqual(structs[1].kind, "equality")
        self.assertEqual(structs[0].source, "detector:mux")
        self.assertEqual(members["det:mux:abcd:h1"], {"f"})


class ScrubTests(unittest.TestCase):
    def test_roots_then_home(self) -> None:
        sc = Scrubber({"$VTR": Path("/home/u/vtr"), "$WS": Path("/home/u/ws"), "$X": None})
        text = "/home/u/vtr/a.v /home/u/ws/b /home/other/c"
        out = sc.text(text)
        self.assertEqual(out, "$VTR/a.v $WS/b $HOME/c")
        self.assertTrue(check_clean(out))
        self.assertFalse(check_clean(text))
