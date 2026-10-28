"""Tests never touch the real private host map: point it at a fresh, initialised temp map,
whatever the shell has set (the map is read at call time, so this runs before any use)."""

import os
import tempfile

from mimir import hostalias

_base = "/tmp/claude-1000"
_dir = tempfile.mkdtemp(prefix="mhost-test-", dir=_base if os.path.isdir(_base) else None)
os.environ["MIMIR_HOST_MAP"] = os.path.join(_dir, "hosts.toml")
hostalias.init_map()
