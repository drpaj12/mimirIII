"""Content-addressed compressed blob store: `<dir>/<ab>/<sha256>.xz` (xz via stdlib lzma)."""

from __future__ import annotations

import hashlib
import lzma
import os
import re
import tempfile
from pathlib import Path

PRESET = 6
_HEX = re.compile(r"^[0-9a-f]{64}$")


def default_dir() -> Path:
    """$MIMIR_BLOBS, else work/mimir-data/blobs of the workspace (~/odin3-ws)."""
    env = os.environ.get("MIMIR_BLOBS")
    return Path(env) if env else Path.home() / "odin3-ws" / "work" / "mimir-data" / "blobs"


def blob_path(root: Path, sha: str) -> Path:
    if not _HEX.match(sha):
        raise ValueError(f"not a sha256 hex digest: {sha!r}")
    return root / sha[:2] / f"{sha}.xz"


def put_bytes(root: Path, data: bytes) -> str:
    """Store data; return its sha256. An existing blob is left alone."""
    sha = hashlib.sha256(data).hexdigest()
    path = blob_path(root, sha)
    if path.exists():
        return sha
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".put-", suffix=".tmp")
    with os.fdopen(fd, "wb") as fh:
        fh.write(lzma.compress(data, format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64, preset=PRESET))
    os.replace(tmp, path)
    return sha


def put_file(root: Path, path: Path) -> str:
    return put_bytes(root, path.read_bytes())


def get_bytes(root: Path, sha: str) -> bytes:
    """The blob's bytes; ValueError when their sha256 is not the name."""
    data = lzma.decompress(blob_path(root, sha).read_bytes())
    if hashlib.sha256(data).hexdigest() != sha:
        raise ValueError(f"blob {sha}: content does not match its name")
    return data


def all_hashes(root: Path) -> list[str]:
    return sorted(p.stem for p in root.glob("??/*.xz") if _HEX.match(p.stem))


def verify(root: Path, shas: list[str] | None = None) -> list[str]:
    """Check each blob (all when none given); return the problems, one string per bad blob."""
    problems = []
    for sha in shas if shas else all_hashes(root):
        try:
            get_bytes(root, sha)
        except (OSError, ValueError, lzma.LZMAError) as exc:
            problems.append(f"{sha}: {exc}")
    return problems
