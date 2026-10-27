from __future__ import annotations

import unittest
from pathlib import Path

from mimir.blif import BlifError, read_blif
from mimir.hutton import characterise
from tests.helpers import tmpdir

FLAT = """\
# comment
.model top
.inputs a b \\
  c
.outputs y z
.names a b n1
11 1
.names n1 c y
1- 1
-1 1
.latch n1 q re clk 0
.names q z
1 1
.names k
1
.end
"""

HIER = """\
.model top
.inputs a b
.outputs y
.subckt inner x=a z=m
.subckt inner x=m z=y
.subckt adder a=a b=b cin=m cout=c1 sumout=s1
.end
.model inner
.inputs x
.outputs z
.names x t
0 1
.names t z
1 1
.end
.model adder
.inputs a b cin
.outputs cout sumout
.blackbox
.end
"""


def write(text: str) -> Path:
    d = Path(tmpdir())
    p = d / "x.blif"
    p.write_text(text, encoding="utf-8")
    return p


class Parse(unittest.TestCase):
    def test_flat(self) -> None:
        nl = read_blif(write(FLAT))
        kinds = sorted(nl.kind)
        self.assertEqual(kinds.count("pi"), 3)
        self.assertEqual(kinds.count("comb"), 3)
        self.assertEqual(kinds.count("latch"), 1)
        self.assertEqual(kinds.count("const"), 1)
        self.assertEqual(len(nl.po_drivers), 2)

    def test_hierarchy_and_hard(self) -> None:
        nl = read_blif(write(HIER))
        self.assertEqual(nl.count("comb"), 4)
        self.assertEqual(nl.count("hard"), 1)
        rows = {(m, b): v for m, b, v in characterise(nl)}
        self.assertEqual(rows[("struct.depth", "")], 4)

    def test_undefined_model(self) -> None:
        with self.assertRaises(BlifError):
            read_blif(write(".model t\n.inputs a\n.outputs y\n.subckt nope p=a q=y\n.end\n"))

    def test_malformed_directives_raise(self) -> None:
        head = ".model t\n.inputs a\n.outputs y\n"
        for bad in (".latch a\n", ".names\n", ".subckt\n"):
            with self.assertRaises(BlifError, msg=bad):
                read_blif(write(head + bad + ".end\n"))

    def test_undriven_and_multidriven_are_counted_not_constants(self) -> None:
        text = (".model t\n.inputs a\n.outputs y\n.names a x y\n11 1\n"
                ".names a y\n1 1\n.end\n")  # x is read but never driven; y has two drivers
        nl = read_blif(write(text))
        self.assertEqual(nl.undriven, 1)
        self.assertEqual(nl.multidriven, 1)
        self.assertEqual(nl.count("const"), 0)
        rows = {(m, b): v for m, b, v in characterise(nl)}
        self.assertEqual(rows[("struct.n_const", "")], 0)
        self.assertEqual(rows[("struct.n_undriven", "")], 1)
        self.assertEqual(rows[("struct.n_multidriven", "")], 1)

    def test_clock_pi_is_flagged_and_not_dangling(self) -> None:
        text = (".model t\n.inputs a clk\n.outputs q\n.latch a q re clk 0\n.end\n")
        nl = read_blif(write(text))
        rows = {(m, b): v for m, b, v in characterise(nl)}
        self.assertEqual(rows[("struct.n_clock_pi", "")], 1)
        self.assertEqual(rows[("struct.n_pi", "")], 2)
        # the clock is not a node of the fanout distribution: a (1 sink) and the latch (0, PO only)
        self.assertEqual(rows[("struct.fanout_hist", "1")], 1)
        self.assertEqual(rows[("struct.fanout_hist", "0")], 1)
        self.assertEqual(rows[("struct.size", "")], 2)  # PI a and the latch; no node for the clock
        self.assertEqual(rows[("struct.n_io", "")], 2)


if __name__ == "__main__":
    unittest.main()
