"""The structure kind of one HDL block, from its construct kind and its source text.

The v2 name map holds the construct kind (`ALWAYS`, `CONT_ASSIGN`, `INSTANCE`, `BINARY`, ...) and
the span, not the operator, so the kind rests on the construct kind plus the text of the span
(comments removed). The rules are syntactic and each has a confidence; the order of the rules is
the precedence (spec section 5). Two levels: `classify` gives the kind of a whole block (a process,
an assign, an instance) and `classify_operator` the kind of one operator construct (a `BINARY` or
`TERNARY` expression). Vocabulary: `mimir.schema.STRUCT_KINDS`.
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
# The hard-block primitives of Odin III, by exact module name:
# src/frontends/verilog/soft_blocks.c:13-14 (`k_names`) and
# src/passes/partial_map/hm_kit.c:36-43 (`k_shapes`).
_PRIMITIVE_KIND = {"single_port_ram": "memory", "dual_port_ram": "memory",
                   "multiply": "multiplier", "adder": "adder"}
_WORD = re.compile(r"\s*(\w+)")
_ARITH = re.compile(r"[\w\])]\s*[+-]\s*[\w(\[{']")
_RELATIONAL = re.compile(r"<=|>=|(?<![<=])<(?![<=])|(?<![>=])>(?![>=])")
_EQUALITY = re.compile(r"==|!=")
_SHIFT = re.compile(r"<<|>>")
_MUL = re.compile(r"(?<!\*)\*(?!\*)")
_SENS = re.compile(r"@\s*\*|@\s*\([^)]*\)")
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
    """The kind of a module instance, from the module name (the first word of the instance).
    Rule 1 (confidence 0.9): the name is exactly one of Odin III's hard-block primitives
    (`_PRIMITIVE_KIND`). Rule 2 (confidence 0.4, a name pattern, not a fact): a name ending in
    `_ram` is a `memory`. Any other module is not a structure kind of its own (None)."""
    m = _WORD.match(text)
    word = m.group(1) if m else ""
    if word in _PRIMITIVE_KIND:
        return _PRIMITIVE_KIND[word], 0.9
    if word.endswith("_ram"):
        return "memory", 0.4
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
    """A combinational right-hand side or block, by the operators present. The first rule that
    matches wins, so a block that has both a `?:` and a `+` is a `mux`: the selection sets the
    shape of the block and the arithmetic sits in its arms (the operator-level rows of the same
    block name the `+`)."""
    if _TERNARY.search(text) or re.search(r"\bcase[xz]?\b|\bif\b", text):
        return "mux", 0.8
    if _MUL.search(text):
        return "multiplier", 0.85
    if _SHIFT.search(text):
        return "shifter", 0.8
    if _ARITH.search(text):
        return "adder", 0.85
    if _RELATIONAL.search(text):
        return "relational", 0.8
    if _EQUALITY.search(text):
        return "equality", 0.8
    return "logic", 0.6


def classify(construct_kind: str, text: str, arrays: frozenset[str]) -> tuple[str, float | None]:
    """(kind, confidence) of a block construct of kind `construct_kind` with source `text`. An
    empty text (the source file was not available) gives `("unknown", None)`: no rule ran."""
    body = strip_comments(text)
    if not body.strip():
        return "unknown", None
    if construct_kind in ("INSTANCE", "GATE_DECL"):
        return _instance_kind(body) or ("logic", 0.3)
    if construct_kind == "ALWAYS":
        if _EDGE.search(body):
            return _sequential(body, arrays)
        if any(re.search(rf"\b{re.escape(a)}\s*\[", body) for a in arrays):
            return "memory", 0.7
        return _expression(_SENS.sub(" ", body))
    rhs = body.split("=", 1)[1] if "=" in body else body
    if any(re.search(rf"\b{re.escape(a)}\s*\[", rhs) for a in arrays):
        return "memory", 0.7
    return _expression(rhs)


# ---------------------------------------------------------------- operator constructs

# Binary operators by precedence, lowest first (IEEE 1800 table 11-2; `**` is not a structure).
_BIN_PREC = (("||",), ("&&",), ("|",), ("^", "~^", "^~"), ("&",), ("==", "!=", "===", "!=="),
             ("<", "<=", ">", ">="), ("<<", ">>", "<<<", ">>>"), ("+", "-"), ("*", "/", "%"),
             ("**",))
_OPS_LONGEST_FIRST = sorted({o for level in _BIN_PREC for o in level}, key=len, reverse=True)
_OPERATOR_KIND = {"+": "adder", "-": "adder", "*": "multiplier", "<<": "shifter",
                  ">>": "shifter", "<<<": "shifter", ">>>": "shifter", "<": "relational",
                  "<=": "relational", ">": "relational", ">=": "relational", "==": "equality",
                  "!=": "equality", "===": "equality", "!==": "equality"}
OPERATOR_CONSTRUCTS = frozenset({"BINARY", "TERNARY"})


def _depth0_operators(text: str) -> list[tuple[int, str]]:
    """(position, operator) of each binary operator of `text` outside brackets. An operator is
    binary when the text before it ends an operand (a name, a number, `)`, `]`, `}`)."""
    found: list[tuple[int, str]] = []
    depth, i, prev = 0, 0, ""
    while i < len(text):
        ch = text[i]
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif depth == 0 and not ch.isspace():
            op = next((o for o in _OPS_LONGEST_FIRST if text.startswith(o, i)), None)
            if op is not None and prev != "" and (prev.isalnum() or prev in ")]}_'"):
                found.append((i, op))
                i += len(op)
                prev = op[-1]
                continue
        if not ch.isspace():
            prev = ch
        i += 1
    return found


def _unwrap(text: str) -> str:
    """The text without the outer parentheses that wrap all of it."""
    t = text.strip()
    while t.startswith("(") and t.endswith(")"):
        depth = 0
        for i, ch in enumerate(t):
            depth += (ch == "(") - (ch == ")")
            if depth == 0 and i < len(t) - 1:
                return t
        t = t[1:-1].strip()
    return t


def binary_operator(text: str) -> str:
    """The operator of the root of a binary expression `text`: the last one of the lowest
    precedence outside brackets (the operators of Verilog are left associative). '' when none."""
    ops = _depth0_operators(_unwrap(strip_comments(text)))
    for level in _BIN_PREC:
        hits = [op for _, op in ops if op in level]
        if hits:
            return hits[-1]
    return ""


def classify_operator(construct_kind: str, text: str) -> tuple[str, float] | None:
    """(kind, confidence) of an operator construct, or None when it is not a structure of its own:
    a `TERNARY` is a `mux`; a `BINARY` is an `adder` (`+`, `-`), `multiplier` (`*`), `shifter`
    (`<<`, `>>`, `<<<`, `>>>`), `relational` (`<`, `<=`, `>`, `>=`) or `equality` (`==`, `!=`,
    `===`, `!==`). Bitwise and logical operators, `/`, `%` and `**` give None: they stay in the
    `logic` residue of their block."""
    if construct_kind == "TERNARY":
        return "mux", 0.9
    if construct_kind != "BINARY":
        return None
    kind = _OPERATOR_KIND.get(binary_operator(text))
    return (kind, 0.9) if kind else None
