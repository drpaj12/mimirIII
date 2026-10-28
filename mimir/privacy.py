"""`mimir privacy-check`: scan a store, its CSV export, the blob store, a snapshot or a tarball
for private strings (the real host names of the local map, `$MIMIR_PRIVATE_STRINGS`, this
machine's name and the login name). The strings are read at run time and never written to a
report: a hit is named by its place and the number of the string only."""

from __future__ import annotations

import contextlib
import getpass
import lzma
import os
import platform
import re
import sqlite3
import tarfile
from pathlib import Path

from mimir import blobs, hostalias, remote

MIN_LEN = 3


def private_strings(map_file: Path | None = None) -> list[str]:
    """Lower-cased, distinct, longest first: the local host map, `$MIMIR_PRIVATE_STRINGS`
    (newline or comma separated), the machine name and the login name."""
    found = set(hostalias.load_map(map_file))
    env = os.environ.get("MIMIR_PRIVATE_STRINGS", "")
    found.update(s.strip().lower() for s in re.split(r"[\n,]", env))
    found.add(platform.node().lower())
    with contextlib.suppress(KeyError, OSError):
        found.add(getpass.getuser().lower())
    found.add(Path.home().name.lower())
    return sorted((s for s in found if len(s) >= MIN_LEN and not hostalias.ALIAS_RE.fullmatch(s)),
                  key=lambda s: (-len(s), s))


def hits_in(data: bytes, strings: list[str]) -> list[int]:
    """Indexes (into `strings`) of the strings found in the data, any case."""
    low = data.lower()
    return [i for i, s in enumerate(strings) if s.encode() in low]


def scan_db(path: Path, strings: list[str]) -> list[str]:
    """`table.column` places of a store that hold a string (schema text included)."""
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    out: list[str] = []
    try:
        for (sql,) in db.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL"):
            out += [f"{path.name}:schema#{i}" for i in hits_in(str(sql).encode(), strings)]
        tables = [r[0] for r in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        for table in tables:
            for col in [r[1] for r in db.execute(f'PRAGMA table_info("{table}")')]:
                for i, s in enumerate(strings):
                    n = db.execute(f'SELECT COUNT(*) FROM "{table}" WHERE '
                                   f'instr(lower(CAST("{col}" AS TEXT)), ?) > 0', (s,)).fetchone()
                    if n[0]:
                        out.append(f"{path.name}:{table}.{col}#{i} ({n[0]} rows)")
    finally:
        db.close()
    return out


def _scan_tar(path: Path, strings: list[str]) -> list[str]:
    out: list[str] = []
    with tarfile.open(path, "r|xz") as tf:
        for ti in tf:
            out += [f"{path.name}!{ti.name}:name#{i}"
                    for i in hits_in(ti.name.encode(), strings)]
            src = tf.extractfile(ti) if ti.isreg() else None
            if src is None:
                continue
            data = src.read()
            if ti.name.endswith(".xz"):
                with contextlib.suppress(lzma.LZMAError):
                    data = lzma.decompress(data)
            out += [f"{path.name}!{ti.name}#{i}" for i in hits_in(data, strings)]
    return out


def scan_file(path: Path, strings: list[str]) -> list[str]:
    """Hits in a file: its name, its bytes, and the bytes inside one xz layer; a `.tar.xz` is read
    member by member."""
    if path.name.endswith(".tar.xz"):
        return _scan_tar(path, strings)
    out = [f"{path.name}:name#{i}" for i in hits_in(path.name.encode(), strings)]
    data = path.read_bytes()
    if path.suffix == ".xz":
        data = lzma.decompress(data)
    return out + [f"{path.name}#{i}" for i in hits_in(data, strings)]


def scan_tree(root: Path, strings: list[str]) -> list[str]:
    """Hits in every file under a directory (a CSV export, a snapshot dir)."""
    out: list[str] = []
    for p in sorted(root.rglob("*")):
        if p.is_file():
            out += scan_file(p, strings)
    return out


def scan_blobs(root: Path, strings: list[str], index: Path | None = None) -> tuple[int, list[str]]:
    """(blobs scanned, hits). With an index dir only the blobs it marks `public` are scanned."""
    shas = blobs.all_hashes(root)
    if index is not None:
        ref = remote.load_blob_index(index)
        shas = [s for s in shas if s in ref and ref[s].visibility == "public"]
    out: list[str] = []
    for sha in shas:
        data = blobs.get_bytes(root, sha)
        out += [f"blob {sha}#{i}" for i in hits_in(data, strings)]
    return len(shas), out
