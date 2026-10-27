from __future__ import annotations

import unittest

from mimir.hdlkind import array_names, classify, strip_comments
from mimir.structmap import span_slice

NO_ARRAYS: frozenset[str] = frozenset()


class ClassifyTests(unittest.TestCase):
    def kind(self, construct: str, text: str, arrays: frozenset[str] = NO_ARRAYS) -> str:
        return classify(construct, text, arrays)[0]

    def test_assigns(self) -> None:
        self.assertEqual(self.kind("CONT_ASSIGN", "assign y = s ? a : b;"), "mux")
        self.assertEqual(self.kind("CONT_ASSIGN", "assign y = a + b;"), "adder")
        self.assertEqual(self.kind("CONT_ASSIGN", "assign y = a - b;"), "adder")
        self.assertEqual(self.kind("CONT_ASSIGN", "assign y = a * b;"), "multiplier")
        self.assertEqual(self.kind("CONT_ASSIGN", "assign y = a << 2;"), "shifter")
        self.assertEqual(self.kind("CONT_ASSIGN", "assign y = a == b;"), "comparator")
        self.assertEqual(self.kind("CONT_ASSIGN", "assign y = a & b;"), "logic")

    def test_unary_minus_and_range_are_not_adders(self) -> None:
        self.assertEqual(self.kind("CONT_ASSIGN", "assign y = -a;"), "logic")
        self.assertEqual(self.kind("CONT_ASSIGN", "assign y = a[7:0];"), "logic")

    def test_always(self) -> None:
        self.assertEqual(self.kind("ALWAYS", "always @(posedge clk) q <= d;"), "register_word")
        self.assertEqual(self.kind("ALWAYS", "always @(posedge clk) c <= c + 1;"), "counter")
        self.assertEqual(self.kind("ALWAYS", "always @(*) if (s) y = a; else y = b;"), "mux")
        self.assertEqual(self.kind("ALWAYS", "always @(*) y = a + b;"), "adder")

    def test_fsm_needs_the_selector_assigned_in_the_block(self) -> None:
        fsm = ("always @(posedge clk) case (st) 0: st <= 1; 1: st <= 0; endcase")
        self.assertEqual(self.kind("ALWAYS", fsm), "fsm")
        other = "always @(posedge clk) case (sel) 0: q <= 1; 1: q <= 0; endcase"
        self.assertEqual(self.kind("ALWAYS", other), "register_word")

    def test_memory_by_array_name(self) -> None:
        arrays = array_names("reg [7:0] mem [0:15];\nreg [7:0] q;")
        self.assertEqual(arrays, frozenset({"mem"}))
        self.assertEqual(self.kind("ALWAYS", "always @(posedge c) mem[a] <= d;", arrays), "memory")
        self.assertEqual(self.kind("CONT_ASSIGN", "assign q = mem[a];", arrays), "memory")

    def test_instances(self) -> None:
        self.assertEqual(self.kind("INSTANCE", "single_port_ram r (.clk(c));"), "memory")
        self.assertEqual(self.kind("INSTANCE", "adder a (.a(x));"), "adder")
        self.assertEqual(self.kind("INSTANCE", "other_mod u (.a(x));"), "logic")

    def test_comments_are_ignored(self) -> None:
        self.assertEqual(strip_comments("a // + b\n/* * */ c"), "a \n  c")
        self.assertEqual(self.kind("CONT_ASSIGN", "assign y = a; // a + b"), "logic")


class SpanTests(unittest.TestCase):
    def test_slice(self) -> None:
        text = "abc\ndefgh\nijk"
        self.assertEqual(span_slice(text, "1.2-1.3"), "bc")
        self.assertEqual(span_slice(text, "1.2-3.2"), "bc\ndefgh\nij")
        self.assertEqual(span_slice(text, "9.1-9.2"), "")
