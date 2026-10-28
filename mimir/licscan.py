"""Which licence rules an archive's members fall under, and the NOTICE built from them.

A design is found in a manifest by the rules of data/meta/licences.toml: a path component that
equals the benchmark name (or starts with it and a dot), or starts with the prefix of a wildcard
rule such as `micro_*`. Rules whose slug glob ends in a bare `*` name no design and are skipped."""

from __future__ import annotations

import fnmatch
import tomllib
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

from mimir.meta import Rule
from mimir.remote import Entry

DESIGN_SUFFIXES = (".v", ".sv", ".vhd", ".blif")
# One more line of the public NOTICE for a rule: what the source states, and what it does not.
NOTICE_EXTRA = {
    "verilogeval": "VerilogEval repository licence: MIT (NVIDIA); the original problem source "
                   "does not state a licence",
}


def _tokens(rules: list[Rule]) -> list[tuple[str, bool, str]]:
    """(token, is_prefix, rule id) for every glob that names designs."""
    out = []
    for rule in rules:
        for glob in rule["match"]:
            base = str(glob).rsplit("/", 1)[-1]
            if base == "*" or "*" in base[:-1] or "?" in base or "[" in base:
                continue
            out.append((base.rstrip("*"), base.endswith("*"), str(rule["id"])))
    return out


def _is_hit(comp: str, tok: str, is_prefix: bool) -> bool:
    return (comp == tok or comp.startswith((tok + ".", tok + "__"))
            or (is_prefix and comp.startswith(tok)))


def rule_hits(entries: Iterable[Entry], rules: list[Rule]) -> dict[str, list[str]]:
    """rule id -> sorted names of the designs of that rule found in the member paths."""
    toks = _tokens(rules)
    found: dict[str, set[str]] = defaultdict(set)
    for e in entries:
        for comp in e.path.split("/"):
            for tok, is_prefix, rid in toks:
                if _is_hit(comp, tok, is_prefix):
                    found[rid].add(tok if not is_prefix else comp.split(".")[0])
    return {rid: sorted(names) for rid, names in sorted(found.items())}


def unmatched_design_files(entries: Iterable[Entry], rules: list[Rule]) -> list[str]:
    """Design-like files (.v, .sv, .vhd, .blif) in no rule's design: they have no licence meta."""
    toks = _tokens(rules)
    out = []
    for e in entries:
        if e.type != "f" or not e.path.endswith(DESIGN_SUFFIXES):
            continue
        hit = any(_is_hit(comp, tok, pre) for comp in e.path.split("/") for tok, pre, _ in toks)
        if not hit:
            out.append(e.path)
    return out


def load_table(path: Path) -> tuple[dict[str, dict[str, object]], dict[str, list[str]]]:
    """(archive name -> row, rule id -> licence text files) of data/remote/licences.toml."""
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    rows = {str(r["archive"]).removesuffix(".tar.xz"): r for r in data.get("archive", [])}
    texts = {k: [str(x) for x in v] for k, v in data.get("rule_texts", {}).items()}
    return rows, texts


def texts_for(hits: dict[str, list[str]], rule_texts: dict[str, list[str]]) -> list[str]:
    names: set[str] = set()
    for rid in hits:
        names.update(rule_texts.get(rid, rule_texts.get("default", [])))
    return sorted(names)


def notice(name: str, row: dict[str, object] | None, hits: dict[str, list[str]],
           rules: list[Rule]) -> str:
    """NOTICE text of a public archive, from the archive row and the per-design rules."""
    by_id = {str(r["id"]): r for r in rules}
    lines = [f"NOTICE for {name}", "",
             "Each benchmark in this archive keeps the licence it states (or none-stated).",
             "Nothing here is relicensed. Not legal advice.", ""]
    if row:
        lines += [f"Archive verdict: {row['verdict']}", f"Notes: {row['notes']}", ""]
    for rid, names in hits.items():
        rule = by_id[rid]
        lines += [f"Designs ({rid}): {', '.join(names)}", f"  Licence: {rule['licence']}",
                  f"  Source: {rule['licence_source']}", f"  Notice: {rule['licence_notice']}"]
        if rid in NOTICE_EXTRA:
            lines.append(f"  {NOTICE_EXTRA[rid]}")
        lines.append("")
    return "\n".join(lines) + "\n"


def drop_glob(path: str, globs: Iterable[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, g) for g in globs)
