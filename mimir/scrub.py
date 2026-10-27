"""Path normalisation: no absolute home path reaches a committed file, a stored text or a blob."""

from __future__ import annotations

import re
from pathlib import Path

_HOME = re.compile(r"/home/[^/\s\"':,;()<>]+")


class Scrubber:
    """Replaces known roots by short labels (longest root first), then any other home path."""

    def __init__(self, roots: dict[str, Path | None]) -> None:
        pairs = [(str(p).rstrip("/"), label) for label, p in roots.items() if p is not None]
        self.pairs = sorted(pairs, key=lambda x: -len(x[0]))

    def text(self, text: str) -> str:
        for root, label in self.pairs:
            text = text.replace(root, label)
        return _HOME.sub("$HOME", text)

    def path(self, path: str) -> str:
        """A file path as a stable, machine-independent id (`odin3:tests/...`)."""
        return self.text(path)


def check_clean(text: str) -> bool:
    """True when the text holds no `/home/` path."""
    return _HOME.search(text) is None
