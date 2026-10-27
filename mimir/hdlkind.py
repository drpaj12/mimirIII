"""The structure kind of one HDL block, from its construct kind and its source text.

The v2 name map holds the construct kind (`ALWAYS`, `CONT_ASSIGN`, `INSTANCE`, ...) and the span,
not the operator, so the kind rests on the construct kind plus the text of the span (comments
removed). The rules are syntactic and each has a confidence; the order of the rules is the
precedence. Vocabulary: `mimir.schema.STRUCT_KINDS`, spec docs/specs/2026-10-27-mimir-structures.md.
"""

from __future__ import annotations

import re

_LINE_COMMENT = re.compile(r"//[^\n]*")
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_EDGE = re.compile(r"@\s*\(\s*(?:\w+\s+)?(?:posedge|negedge)\b|\b(?:posedge|negedge)\b")
_CASE = re.compile(r"\bcase[xz]?\s*\(\s*(\w+)")
_ARRAY_DECL = re.compile(r"\b(?:reg|wire|logic)\b[^;\[]*(?:\[[^\]]*\]\s*)?(\w+)\s*\[[^\]]+\]\s*;")
_ASSIGN_LHS = re.compile(r"(\w+)\s*(?:\[[^\]]*\]\s*)*<?=(?!=)")
_COUNTER = re.compile(r"(\w+)\s*(?:\[[^\]]*\])?\s*<=\s*\1\s*(?:\[[^\]]*\])?\s*[+-]\s*"
                      r"(?:\d+'[sS]?[bBdDhHoO][0-9a-fA-F_xXzZ]+|\d+)\b")
_MEM_WORDS = ("single_port_ram", "dual_port_ram", "spram", "dpram", "ram")
_MULT_WORDS = ("multiply", "mult")
_ADD_WORDS = ("adder",)
_ARITH = re.compile(r"(?<![\w\])'])\s*[+-]\s*(?=[\w(\[{'])|(?<=[\w\])])\s*[+-]\s*(?=[\w(\[{'])")
_COMPARE = re.compile(r"==|!=|<=|>=|<(?!<)|>(?!>)")
_SHIFT = re.compile(r"<<|>>")
_MUL = re.compile(r"(?<!\*)\*(?!\*)")
_TERNARY = re.compile(r"\?")
_BLOCK_KINDS = frozenset({"ALWAYS", "CONT_ASSIGN", "NET_ASSIGN", "INSTANCE", "GATE_DECL"})


def strip_comments(text: str) -> str:
    """The text without `/* */` and `//` comments (string literals are not specially handled:
    an unquoted `//` in a string is rare in synthesizable code)."""
    return _LINE_COMMENT.sub("", _BLOCK_COMMENT.sub(" ", text))


def array_names(file_text: str) -> frozenset[str]:
    """Names declared as arrays (`reg [7:0] mem [0:255];`), the memories of a file."""
    return frozenset(_ARRAY_DECL.findall(strip_comments(file_text)))


def is_block_kind(construct_kind: str) -> bool:
    return construct_kind in _BLOCK_KINDS


def _instance_kind(text: str) -> tuple[str, float] | None:
    """A module instance is a structure only when it is a known primitive/hard block."""
    word = text.split(None, 1)[0] if text.split() else ""
    if word in _MEM_WORDS or word.endswith("_ram"):
        return "memory", 0.9
    if word in _MULT_WORDS or word.startswith("mult"):
        return "multiplier", 0.9
    if word in _ADD_WORDS:
        return "adder", 0.9
    return None


def _assigned(text: str) -> set[str]:
    return set(_ASSIGN_LHS.findall(text))


def _sequential(text: str, arrays: frozenset[str]) -> tuple[str, float]:
    if any(re.search(rf"\b{re.escape(a)}\s*\[", text) for a in arrays):
        return "memory", 0.8
    assigned = _assigned(text)
    for sel in _CASE.findall(text):
        if sel in assigned and len(re.findall(r"\bcase[xz]?\b", text)) >= 1:
            return "fsm", 0.7
    if _COUNTER.search(text):
        return "counter", 0.8
    return "register_word", 0.9


def _expression(text: str) -> tuple[str, float]:
    """A combinational right-hand side or block, by the operators present."""
    if _TERNARY.search(text) or re.search(r"\bcase[xz]?\b|\bif\b", text):
        return "mux", 0.8
    if _MUL.search(text):
        return "multiplier", 0.85
    if _SHIFT.search(text):
        return "shifter", 0.8
    if _ARITH.search(text):
        return "adder", 0.85
    if _COMPARE.search(text):
        return "comparator", 0.8
    return "logic", 0.6


def classify(construct_kind: str, text: str, arrays: frozenset[str]) -> tuple[str, float]:
    """(kind, confidence) of a block construct of kind `construct_kind` with source `text`."""
    body = strip_comments(text)
    if construct_kind in ("INSTANCE", "GATE_DECL"):
        return _instance_kind(body) or ("logic", 0.3)
    if construct_kind == "ALWAYS":
        if _EDGE.search(body):
            return _sequential(body, arrays)
        if any(re.search(rf"\b{re.escape(a)}\s*\[", body) for a in arrays):
            return "memory", 0.7
        return _expression(body)
    rhs = body.split("=", 1)[1] if "=" in body else body
    if any(re.search(rf"\b{re.escape(a)}\s*\[", rhs) for a in arrays):
        return "memory", 0.7
    return _expression(rhs)
