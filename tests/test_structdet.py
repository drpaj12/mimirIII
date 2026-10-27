from __future__ import annotations

import json
import unittest
from pathlib import Path

from mimir.scrub import Scrubber, check_clean
from mimir.structdet import compare, read_structs
from tests.helpers import tmpdir


class CompareTests(unittest.TestCase):
    def test_precision_and_recall(self) -> None:
        hdl = {"h1": ("adder", {"a", "b", "c"}), "h2": ("mux", {"d"}), "h3": ("fsm", {"e", "f"})}
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

    def test_tie_goes_to_the_smaller_id(self) -> None:
        hdl = {"h2": ("mux", {"a"}), "h1": ("adder", {"a"})}
        got = {s.kind: s for s in compare(hdl, {"d": ("adder", {"a"})})}
        self.assertEqual(got["adder"].correct, 1)


class ReadStructsTests(unittest.TestCase):
    def test_filters(self) -> None:
        def hyp(hid: str, kind: str, p: float, parents: list[str], net: str) -> dict[str, object]:
            return {"id": hid, "kind": kind, "p_comp": p, "parents": parents, "detector": "mux",
                    "nets": {"Y": [net]}}

        data = {"hypotheses": [
            hyp("h1", "mux", 0.9, [], "f"), hyp("h2", "mux_bit", 0.9, ["h1"], "f"),
            hyp("h3", "mux", 0.2, [], "f"), hyp("h4", "bus", 0.9, [], "f"),
            hyp("h5", "mux", 0.9, [], "nope")]}
        path = Path(tmpdir()) / "overlay.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        structs, members = read_structs(path, {"f": "lut"}, "abcd")
        self.assertEqual([s.sid for s in structs], ["det:mux:abcd:h1"])
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
