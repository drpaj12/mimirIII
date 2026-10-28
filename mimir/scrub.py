"""Path normalisation: no absolute home path reaches a committed file, a stored text or a blob."""

from __future__ import annotations

import re
from pathlib import Path

from mimir import hostalias, publish

_HOME = re.compile(r"/home/[^/\s\"':,;()<>]+")


class Scrubber:
    """Replaces known roots by short labels (longest root first), then any other home path, then
    a real host name of the private host map by its alias, then the user name, the person's name
    and the e-mail (`publish.scrub_bytes`), so a bare login name never reaches a stored text or a
    blob. HostMapError when the host map is missing: the record fails, the text is not passed on."""

    def __init__(self, roots: dict[str, Path | None]) -> None:
        pairs = [(str(p).rstrip("/"), label) for label, p in roots.items() if p is not None]
        self.pairs = sorted(pairs, key=lambda x: -len(x[0]))

    def text(self, text: str) -> str:
        for root, label in self.pairs:
            text = text.replace(root, label)
        text = hostalias.scrub_text(_HOME.sub("$HOME", text))
        return publish.scrub_bytes(text.encode("utf-8")).decode("utf-8")

    def path(self, path: str) -> str:
        """A file path as a stable, machine-independent id (`odin3:tests/...`)."""
        return self.text(path)


def check_clean(text: str) -> bool:
    """True when the text holds no `/home/` path."""
    return _HOME.search(text) is None
