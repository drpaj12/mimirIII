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


if __name__ == "__main__":
    unittest.main()
