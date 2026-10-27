"""Verified citations (`citations.toml`) and their rendering to docs/CITATIONS.md."""

from __future__ import annotations

import tomllib
from pathlib import Path

_FIELDS = ("id", "name", "kind", "role", "authors", "year", "title", "venue", "doi", "url",
           "license", "checked")


def load_citations(path: Path) -> dict[str, dict[str, object]]:
    """Citation entries keyed by id. Every entry needs an id, a name, a kind and a checked note."""
    items = tomllib.loads(path.read_text(encoding="utf-8")).get("item", [])
    out: dict[str, dict[str, object]] = {}
    for item in items:
        for key in ("id", "name", "kind", "checked"):
            if not item.get(key):
                raise ValueError(f"citation {item.get('id')!r}: missing {key!r}")
        if item["id"] in out:
            raise ValueError(f"duplicate citation {item['id']!r}")
        out[item["id"]] = item
    return out


def _link(item: dict[str, object]) -> str:
    if item.get("doi"):
        return f"https://doi.org/{item['doi']}"
    return str(item.get("url", ""))


def _ref(item: dict[str, object]) -> str:
    year = f" ({item['year']})" if item.get("year") else ""
    parts = [f"{item.get('authors', '')}{year}.", f"{item.get('title', '')}.",
             f"{item.get('venue', '')}."]
    return " ".join(p for p in parts if p.strip(" ."))


def render_markdown(items: dict[str, dict[str, object]]) -> str:
    """The CITATIONS.md text for the given entries (deterministic, sorted by id)."""
    lines = ["# Citations", "",
             "Every entry was checked against the record named in its `Checked` note.",
             "Source of truth: `citations.toml`; regenerate with `mimir citations`.", "",
             "| Id | Kind | Role | Reference | Link | Licence |", "|---|---|---|---|---|---|"]
    for key in sorted(items):
        it = items[key]
        row = [key, str(it["kind"]), str(it.get("role", "")), _ref(it), _link(it),
               str(it.get("license", ""))]
        lines.append("| " + " | ".join(c.replace("|", "/") for c in row) + " |")
    lines += ["", "## Checked", ""]
    for key in sorted(items):
        lines.append(f"- `{key}`: {items[key]['checked']}")
    return "\n".join(lines) + "\n"
