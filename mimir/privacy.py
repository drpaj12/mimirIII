"""`mimir privacy-check`: scan a store, its CSV export, the blob store, a snapshot or a tarball
for private strings (the real host names of the local map, `$MIMIR_PRIVATE_STRINGS`, this
machine's name and the login name) and for what `publish.has_home` finds (a home path, the user
name, the person's name, an e-mail). The strings are read at run time and never written to a
report: a hit is named by its place and the number of the string only.

A check that cannot look inside something reports it as a hit, never as clean: an undecodable
compressed member, a zip that cannot be read, a Parquet file when pyarrow is missing."""

from __future__ import annotations

import contextlib
import getpass
import io
import os
import platform
import re
import sqlite3
import tarfile
import zipfile
from pathlib import Path

from mimir import blobs, hostalias, publish, remote

MIN_LEN = 3
MAX_DEPTH = 6
HOME_TAG = "home"  # the place suffix of a `publish.has_home` hit
XZ_MAGIC, GZ_MAGIC, ZIP_MAGIC = b"\xfd7zXZ\x00", b"\x1f\x8b", b"PK\x03\x04"
CHUNK = 1 << 24


def private_strings(map_file: Path | None = None) -> list[str]:
    """Lower-cased, distinct, longest first: the local host map (HostMapError when it is missing:
    a check without it could report a false 0),
    `$MIMIR_PRIVATE_STRINGS` (newline or comma separated), the machine name and the login name.
    A name shorter than MIN_LEN is kept; `hits_in` looks for it as a whole word."""
    found = set(hostalias.load_map(map_file))
    env = os.environ.get("MIMIR_PRIVATE_STRINGS", "")
    found.update(s.strip().lower() for s in re.split(r"[\n,]", env))
    found.add(platform.node().lower())
    with contextlib.suppress(KeyError, OSError):
        found.add(getpass.getuser().lower())
    found.add(Path.home().name.lower())
    return sorted((s for s in found if s and not hostalias.ALIAS_RE.fullmatch(s)),
                  key=lambda s: (-len(s), s))


def _word(s: str) -> re.Pattern[bytes]:
    return re.compile(rb"(?<![A-Za-z0-9])" + re.escape(s.encode()) + rb"(?![A-Za-z0-9])",
                      re.IGNORECASE)


def hits_in(data: bytes, strings: list[str]) -> list[int]:
    """Indexes (into `strings`) of the strings found in the data, any case. A string shorter
    than MIN_LEN counts only as a whole word."""
    low = data.lower()
    out = []
    for i, s in enumerate(strings):
        if len(s) < MIN_LEN:
            if _word(s).search(data):
                out.append(i)
        elif s.encode() in low:
            out.append(i)
    return out


def unit_hits(place: str, data: bytes, strings: list[str]) -> list[str]:
    """Hits in one plain unit: the private strings, and a home path, user name, person or
    e-mail."""
    out = [f"{place}#{i}" for i in hits_in(data, strings)]
    if publish.has_home(data):
        out.append(f"{place}#{HOME_TAG}")
    return out


def _kind(name: str, data: bytes) -> str:
    """How to look inside a member: by its name, and by its magic bytes."""
    low = name.lower()
    if low.endswith(".gz") or data[:2] == GZ_MAGIC:
        return "gz"
    if low.endswith(".xz") or data[:6] == XZ_MAGIC:
        return "xz"
    if low.endswith(publish.ZIP_SUFFIXES) or data[:4] == ZIP_MAGIC:
        return "zip"
    if low.endswith(".tar"):
        return "tar"
    if low.endswith(".parquet"):
        return "parquet"
    return ""


def scan_member(place: str, name: str, data: bytes, strings: list[str], depth: int = 0
                ) -> list[str]:
    """Hits in a named member: its name, its bytes, and (recursively) everything inside it when it
    is xz, gz, zip, npz or tar. What cannot be decoded is a hit (`undecodable`)."""
    out = unit_hits(f"{place}:name", name.encode("utf-8", "replace"), strings)
    out += unit_hits(place, data, strings)
    kind = _kind(name, data)
    if not kind:
        return out
    if depth >= MAX_DEPTH:
        return [*out, f"{place}:undecodable (nested too deep)"]
    inner = _inner(place, name, data, kind, strings, depth)
    return out + inner


def _inner(place: str, name: str, data: bytes, kind: str, strings: list[str], depth: int
           ) -> list[str]:
    if kind in ("gz", "xz"):
        got = publish._bounded_inflate(data, kind)
        if got is None:
            return [f"{place}:undecodable ({kind})"]
        stem = name[:-3] if name.lower().endswith((".gz", ".xz")) else name
        return scan_member(f"{place}>{kind}", stem, got, strings, depth + 1)
    if kind == "zip":
        return _scan_zip(place, data, strings, depth)
    if kind == "tar":
        return _scan_tar_bytes(place, data, strings, depth)
    return _scan_parquet(place, data, strings)


def _scan_zip(place: str, data: bytes, strings: list[str], depth: int) -> list[str]:
    out: list[str] = []
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    out += unit_hits(f"{place}>{info.filename}:name",
                                     info.filename.encode("utf-8", "replace"), strings)
                    continue
                with zf.open(info) as fh:
                    inner = fh.read(publish.MAX_MEMBER + 1)
                if len(inner) > publish.MAX_MEMBER:
                    out.append(f"{place}>{info.filename}:undecodable (too long)")
                    continue
                out += scan_member(f"{place}>{info.filename}", info.filename, inner, strings,
                                   depth + 1)
    except (zipfile.BadZipFile, OSError, NotImplementedError, RuntimeError, EOFError,
            ValueError):
        out.append(f"{place}:undecodable (zip)")
    except Exception as exc:  # zlib.error, lzma.LZMAError, bz2 errors: all undecodable
        out.append(f"{place}:undecodable (zip: {type(exc).__name__})")
    return out


def _scan_tar_bytes(place: str, data: bytes, strings: list[str], depth: int) -> list[str]:
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as tf:
            return _scan_tar_members(place, tf, strings, depth)
    except (tarfile.TarError, OSError, EOFError):
        return [f"{place}:undecodable (tar)"]


def _scan_tar_members(place: str, tf: tarfile.TarFile, strings: list[str], depth: int
                      ) -> list[str]:
    out: list[str] = []
    for ti in tf:
        out += unit_hits(f"{place}!{ti.name}:name", ti.name.encode("utf-8", "replace"), strings)
        out += unit_hits(f"{place}!{ti.name}:link", ti.linkname.encode("utf-8", "replace"),
                         strings)
        src = tf.extractfile(ti) if ti.isreg() else None
        if src is None:
            continue
        member = src.read()
        out += scan_member(f"{place}!{ti.name}", ti.name, member, strings, depth + 1)
    return out


def _scan_parquet(place: str, data: bytes, strings: list[str]) -> list[str]:
    try:
        import pyarrow.parquet as pq
    except ImportError:
        return [f"{place}:not scanned (parquet, pyarrow is not installed)"]
    out: list[str] = []
    try:
        table = pq.read_table(io.BytesIO(data))
    except Exception as exc:  # any reader failure: the file was not looked into
        return [f"{place}:undecodable (parquet: {type(exc).__name__})"]
    out += unit_hits(f"{place}:schema", str(table.schema).encode("utf-8", "replace"), strings)
    for col in table.column_names:
        text = "\n".join(str(v) for v in table.column(col).to_pylist()).encode("utf-8", "replace")
        out += unit_hits(f"{place}.{col}", text, strings)
    return out


def _raw_hits(path: Path, strings: list[str]) -> list[str]:
    """Hits in the raw bytes of a file, read in chunks (a store is large); the chunks overlap by
    the longest string, so a string split by a chunk edge is still found."""
    keep = max((len(s) for s in strings), default=0) + 64
    seen: set[int] = set()
    home = False
    tail = b""
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(CHUNK)
            if not chunk:
                break
            buf = tail + chunk
            seen.update(hits_in(buf, strings))
            home = home or publish.has_home(buf)
            tail = buf[-keep:]
    out = [f"{path.name}:raw#{i}" for i in sorted(seen)]
    return out + ([f"{path.name}:raw#{HOME_TAG}"] if home else [])


def _scan_rows(db: sqlite3.Connection, path: Path, table: str, strings: list[str]) -> list[str]:
    cols = [r[1] for r in db.execute(f'PRAGMA table_info("{table}")')]
    count: dict[str, int] = {}
    for row in db.execute(f'SELECT * FROM "{table}"'):
        for col, value in zip(cols, row, strict=True):
            if value is None or isinstance(value, int | float):
                continue
            data = value if isinstance(value, bytes) else str(value).encode("utf-8", "replace")
            for h in scan_member(f"{table}.{col}", "", data, strings):
                count[h] = count.get(h, 0) + 1
    return [f"{path.name}:{k} ({n} cells)" for k, n in sorted(count.items())]


def scan_db(path: Path, strings: list[str]) -> list[str]:
    """Places of a store that hold a string: schema text, every cell of every table (compressed
    or archive cells looked into), and the raw bytes of the `.db` file and its `-wal` (free pages
    and old versions of a row are there)."""
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    out: list[str] = []
    try:
        for (sql,) in db.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL"):
            out += unit_hits(f"{path.name}:schema", str(sql).encode("utf-8", "replace"), strings)
        tables = [r[0] for r in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        for table in tables:
            out += _scan_rows(db, path, table, strings)
    finally:
        db.close()
    out += _raw_hits(path, strings)
    wal = path.with_name(path.name + "-wal")
    if wal.is_file():
        out += _raw_hits(wal, strings)
    return out


def _scan_tar(path: Path, strings: list[str]) -> list[str]:
    with tarfile.open(path, "r|xz") as tf:
        return _scan_tar_members(path.name, tf, strings, 0)


def scan_file(path: Path, strings: list[str]) -> list[str]:
    """Hits in a file: its name, its bytes, and everything inside it (xz, gz, zip, npz, tar,
    nested); a `.tar.xz` is read member by member, a store (`.db`) as `scan_db` does."""
    try:
        if path.name.endswith(".tar.xz"):
            return _scan_tar(path, strings)
    except (tarfile.TarError, OSError, EOFError) as exc:
        return [f"{path.name}:undecodable (tar.xz: {type(exc).__name__})"]
    if path.suffix == ".db":
        return scan_db(path, strings)
    return scan_member(path.name, path.name, path.read_bytes(), strings)


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
        out += scan_member(f"blob {sha}", "", blobs.get_bytes(root, sha), strings)
    return len(shas), out
