from __future__ import annotations

import re
import unittest
from pathlib import Path

from mimir.citations import load_citations, render_markdown
from mimir.registry import load_registry
from mimir.schema import LEVELS

ROOT = Path(__file__).resolve().parent.parent


class Registry(unittest.TestCase):
    def test_entries_are_consistent(self) -> None:
        cites = load_citations(ROOT / "citations.toml")
        for key, m in load_registry().items():
            for c in m.citations:
                self.assertIn(c, cites, f"{key} cites unknown {c}")
            for lv in m.levels:
                self.assertIn(lv, LEVELS)
            if m.kind == "measured":
                self.assertIn("test", m.validation.lower(), key)

    def test_every_code_metric_is_registered(self) -> None:
        reg = load_registry()
        pattern = re.compile(r'"((?:struct|rent|vpr|norns|atlas|loki)\.[a-z_.0-9]+)"')
        for rel in ("mimir/hutton.py", "mimir/rent.py", "mimir/importers/norns.py",
                    "mimir/importers/atlas.py", "mimir/importers/loki.py"):
            for name in pattern.findall((ROOT / rel).read_text()):
                self.assertIn(name, reg, f"{name} in {rel}")

    def test_citations_have_checked_notes_and_doc_is_current(self) -> None:
        items = load_citations(ROOT / "citations.toml")
        for key, it in items.items():
            self.assertTrue(str(it["checked"]).startswith("2026-"), key)
        doc = (ROOT / "docs" / "CITATIONS.md").read_text(encoding="utf-8")
        self.assertEqual(doc, render_markdown(items))

    def test_no_home_paths_committed(self) -> None:
        needle = "/home/" + "jamiespa"
        for path in ROOT.rglob("*"):
            skip = {".git", ".venv", ".mypy_cache", ".ruff_cache", "__pycache__"}
            if path.is_file() and not skip & set(path.parts) and path.suffix in (
                ".py", ".md", ".toml", ".yml", ".txt", ""
            ):
                self.assertNotIn(needle, path.read_text(encoding="utf-8", errors="ignore"),
                                 str(path))


if __name__ == "__main__":
    unittest.main()
