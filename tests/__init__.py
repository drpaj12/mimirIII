"""Tests never touch the real private host map: point it at a temp file before any import."""

import os
import tempfile

if "MIMIR_HOST_MAP" not in os.environ:
    _base = "/tmp/claude-1000"
    os.environ["MIMIR_HOST_MAP"] = os.path.join(
        tempfile.mkdtemp(prefix="mhost-test-", dir=_base if os.path.isdir(_base) else None),
        "hosts.toml")
