"""Remote data: the committed index of the offloaded archives and blobs, and `mimir fetch`.

Spec: docs/specs/2026-10-27-mimir-remote-data.md. Standard library only. Downloaded and archived
data is untrusted: it is hashed and copied, never run. Nothing here deletes a file."""

from __future__ import annotations

import hashlib
import json
import lzma
import os
import re
import sqlite3
import tarfile
import tomllib
import urllib.parse
import urllib.request
from collections.abc import Iterable
from dataclasses import dataclass, fields
from pathlib import Path, PurePosixPath
from typing import IO, Any, NamedTuple

from mimir import blobs

DEFAULT_BASE = "https://drpeterjamieson.com/RESEARCH/MIMIR/mimir-data"
SCHEMES = ("http", "https", "file")
CHUNK = 1 << 20
_HEX = re.compile(r"[0-9a-f]{64}")
_TYPES = {"dir": "d", "d": "d", "file": "f", "f": "f", "link": "l", "l": "l"}


class FetchError(Exception):
    """A fetch that cannot be done safely or correctly."""


@dataclass(frozen=True)
class Archive:
    name: str
    date: str
    file: str
    form: str  # "tar.xz" or "dir"
    kind: str
    source: str
    manifest: str
    visibility: str  # "public" or "private"
    licence: str
    sha256: str
    size: int
    members: int
    urls: tuple[str, ...] = ()
    public_file: str = ""
    public_sha256: str = ""
    public_size: int = 0
    public_manifest: str = ""
    public_members: int = 0
    public_dropped: int = 0
    public_scrubbed: int = 0

    @property
    def private(self) -> bool:
        return self.visibility != "public"

    @property
    def served(self) -> tuple[str, str, str]:
        """(file, sha256, manifest) of what a URL serves: the repack when there is one."""
        if self.public_sha256 or (self.form == "dir" and self.public_manifest):
            return self.public_file, self.public_sha256, self.public_manifest
        return self.file, self.sha256, self.manifest


class Entry(NamedTuple):
    path: str
    type: str  # d, f or l
    size: int
    sha: str  # sha256 of a file, the target of a link, "-" for a dir


class BlobRef(NamedTuple):
    sha: str
    xz_bytes: int
    raw_bytes: int  # size of the decompressed content
    archive: str  # a blob tarball name, or "-"
    visibility: str  # public, private (traces to a private archive) or orphan (no row uses it)


def index_dir() -> Path:
    env = os.environ.get("MIMIR_INDEX")
    return Path(env) if env else Path(__file__).resolve().parents[1] / "data" / "remote"


def private_dir() -> Path | None:
    """Where the manifests of private archives live (never committed): `$MIMIR_PRIVATE_INDEX`,
    else `mimir-data/remote-private` next to the checkout (or under `work/`), when it exists."""
    env = os.environ.get("MIMIR_PRIVATE_INDEX")
    if env:
        return Path(env)
    base = Path(__file__).resolve().parents[2]
    for cand in (base / "mimir-data" / "remote-private",
                 base / "work" / "mimir-data" / "remote-private"):
        if cand.is_dir():
            return cand
    return None


def manifest_file(idx: Path, arch: Archive, priv: Path | None = None) -> Path | None:
    """The manifest file of an archive: committed for a public one, local for a private one."""
    if not arch.private:
        return idx / arch.manifest if arch.manifest else None
    base = priv if priv is not None else private_dir()
    if base is None:
        return None
    path = base / "manifests" / f"{arch.name}.tsv.xz"
    return path if path.is_file() else None


def archive_entries(idx: Path, arch: Archive, priv: Path | None = None) -> list[Entry]:
    path = manifest_file(idx, arch, priv)
    if path is None:
        raise FetchError(f"{arch.name}: no manifest here (a private archive's manifest is "
                         "local only: set MIMIR_PRIVATE_INDEX)")
    return parse_manifest_rows(read_tsv_xz(path))


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


# ---- the index files -------------------------------------------------------------------------

def _archive_from(d: dict[str, Any]) -> Archive:
    names = {f.name: f for f in fields(Archive)}
    extra = set(d) - set(names)
    if extra:
        raise ValueError(f"archive {d.get('name')}: unknown fields {sorted(extra)}")
    kw: dict[str, Any] = {}
    for key, value in d.items():
        kw[key] = tuple(str(u) for u in value) if key == "urls" else value
    return Archive(**kw)


def load_archives(idx: Path | None = None) -> dict[str, Archive]:
    path = (idx or index_dir()) / "archives.toml"
    rows = tomllib.loads(path.read_text(encoding="utf-8")).get("archive", [])
    out: dict[str, Archive] = {}
    for row in rows:
        arch = _archive_from(row)
        if arch.name in out:
            raise ValueError(f"duplicate archive {arch.name}")
        out[arch.name] = arch
    return out


def _toml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, (tuple, list)):
        return "[" + ", ".join(json.dumps(str(v)) for v in value) + "]"
    return json.dumps(str(value))


def dump_archives(archives: Iterable[Archive]) -> str:
    """Deterministic TOML text: archives sorted by name, fields in dataclass order."""
    blocks = ["# Generated by `mimir remote index`; repack fields by `publish-plan --record`.\n"]
    for arch in sorted(archives, key=lambda a: a.name):
        lines = ["[[archive]]"]
        for f in fields(Archive):
            lines.append(f"{f.name} = {_toml_value(getattr(arch, f.name))}")
        blocks.append("\n".join(lines) + "\n")
    return "\n".join(blocks)


MAX_INDEX_FILE = 1 << 31  # an index file of the repo is trusted, but still bounded


def unxz(data: bytes, limit: int) -> bytes:
    """Decompress one xz stream to at most `limit` bytes; FetchError when it is longer, is not
    xz, is cut short or has trailing data. Never decompresses past limit + 1 bytes."""
    dec = lzma.LZMADecompressor(format=lzma.FORMAT_XZ)
    try:
        out = dec.decompress(data, max_length=limit + 1)
    except (lzma.LZMAError, EOFError) as exc:
        raise FetchError(f"not valid xz: {exc}") from exc
    if len(out) > limit:
        raise FetchError(f"decompresses to more than the indexed {limit} bytes")
    if not dec.eof or dec.unused_data:
        raise FetchError("xz stream cut short or followed by extra data")
    return out


def read_tsv_xz(path: Path) -> list[list[str]]:
    text = unxz(path.read_bytes(), MAX_INDEX_FILE).decode("utf-8")
    return [line.split("\t") for line in text.split("\n") if line]


def parse_manifest_rows(rows: Iterable[list[str]]) -> list[Entry]:
    """Rows of a F: or committed manifest; both type spellings (d/f/l and dir/file/link)."""
    out = []
    for row in rows:
        if len(row) != 4 or row[1] not in _TYPES:
            raise ValueError(f"bad manifest row: {row!r}")
        out.append(Entry(row[0], _TYPES[row[1]], int(row[2]), row[3]))
    return out


def read_manifest(idx: Path, rel: str) -> list[Entry]:
    return parse_manifest_rows(read_tsv_xz(idx / rel))


def manifest_text(entries: Iterable[Entry]) -> bytes:
    rows = sorted(entries, key=lambda e: e.path.encode())
    return "".join(f"{e.path}\t{e.type}\t{e.size}\t{e.sha}\n" for e in rows).encode("utf-8")


def write_xz(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    part.write_bytes(lzma.compress(data, format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64, preset=9))
    os.replace(part, path)


def load_blob_index(idx: Path | None = None) -> dict[str, BlobRef]:
    path = (idx or index_dir()) / "blobs.tsv.xz"
    out: dict[str, BlobRef] = {}
    for sha, nbytes, raw, arch, vis in read_tsv_xz(path):
        out[sha] = BlobRef(sha, int(nbytes), int(raw), arch, vis)
    return out


# ---- locations ---------------------------------------------------------------------------------

@dataclass(frozen=True)
class Locations:
    blobs: Path
    archive_dir: Path | None
    data_url: str | None
    cache: Path
    private_index: Path | None = None  # dir with manifests/<private archive>.tsv.xz (local only)

    @classmethod
    def from_env(cls, online: bool = False) -> Locations:
        env = os.environ
        arch = env.get("MIMIR_ARCHIVE")
        url = env.get("MIMIR_DATA_URL") or (DEFAULT_BASE if online else None)
        cache = env.get("MIMIR_CACHE")
        if not cache:
            xdg = env.get("XDG_CACHE_HOME")
            cache = str(Path(xdg) / "mimir") if xdg else str(Path.home() / ".cache" / "mimir")
        priv = env.get("MIMIR_PRIVATE_INDEX")
        return cls(blobs.default_dir(), Path(arch) if arch else None, url, Path(cache),
                   Path(priv) if priv else private_dir())


def safe_member(member: str) -> str:
    """The member path, normalised; FetchError when it is absolute, has `..` or is empty."""
    if not member or member.startswith("/") or "\\" in member or "\x00" in member:
        raise FetchError(f"refused member path {member!r}")
    parts = PurePosixPath(member).parts
    if not parts or any(p in ("..", "") for p in parts):
        raise FetchError(f"refused member path {member!r}")
    return "/".join(p for p in parts if p != ".")


def _norm(name: str) -> str:
    return "/".join(p for p in PurePosixPath(name).parts if p != ".")


# ---- hashing, copying, downloading -------------------------------------------------------------

def _copy_checked(src: IO[bytes], part: Path, dest: Path, sha: str, size: int | None,
                  limit: int | None = None) -> None:
    """Copy src to `part`, then rename onto dest when sha256 (and size) match; otherwise
    truncate `part` and raise, leaving dest alone. With `limit` (the indexed size) the read
    stops at limit + 1 bytes and fails."""
    if limit is None:
        limit = size
    h = hashlib.sha256()
    n = 0
    dest.parent.mkdir(parents=True, exist_ok=True)
    too_long = False
    with part.open("wb") as out:
        while True:
            want = CHUNK if limit is None else min(CHUNK, limit + 1 - n)
            chunk = src.read(want)
            if not chunk:
                break
            h.update(chunk)
            n += len(chunk)
            out.write(chunk)
            if limit is not None and n > limit:
                too_long = True
                break
    if too_long:
        part.open("wb").close()
        raise FetchError(f"{dest.name}: longer than the indexed {limit} bytes, stopped")
    if h.hexdigest() != sha or (size is not None and n != size):
        part.open("wb").close()
        raise FetchError(f"sha256 mismatch for {dest.name}: got {h.hexdigest()}, want {sha}")
    os.replace(part, dest)


def _marker(cache: Path, path: Path, sha: str) -> Path:
    st = path.stat()
    return cache / "verified" / f"{sha}-{st.st_size}-{st.st_mtime_ns}"


def verified_archive(path: Path, sha: str, cache: Path) -> None:
    """Hash the archive once (a marker in the cache keyed by sha, size and mtime skips repeats)."""
    mark = _marker(cache, path, sha)
    if mark.exists():
        return
    got = sha256_path(path)
    if got != sha:
        raise FetchError(f"archive {path.name}: sha256 {got}, index says {sha}")
    mark.parent.mkdir(parents=True, exist_ok=True)
    mark.write_text(sha + "\n", encoding="ascii")


def download(url: str, dest: Path, sha: str, limit: int) -> None:
    """Download url to dest (verified by sha256); never more than `limit` (the indexed size)."""
    scheme = url.split(":", 1)[0].lower()
    if scheme not in SCHEMES:
        raise FetchError(f"refused URL scheme {scheme!r}")
    part = dest.with_name(dest.name + ".part")
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:
            _copy_checked(resp, part, dest, sha, None, limit)
    except OSError as exc:
        raise FetchError(f"download failed: {url}: {exc}") from exc


def _extract_member(archive: Path, member: str, entry: Entry, dest: Path) -> None:
    with tarfile.open(archive, "r|xz") as tf:
        for ti in tf:
            if _norm(ti.name) != member:
                continue
            if not ti.isreg():
                raise FetchError(f"{member}: not a regular file (link, device or directory)")
            try:
                # Only the filter's verdict and normalised header are used: the bytes are
                # read through extractfile, nothing is extracted by name.
                safe = tarfile.data_filter(ti, str(dest.parent.resolve()))
            except tarfile.FilterError as exc:
                raise FetchError(f"{member}: refused by the tar data filter: {exc}") from exc
            src = tf.extractfile(safe)
            if src is None:
                raise FetchError(f"{member}: cannot be read")
            _copy_checked(src, dest.with_name(dest.name + ".part"), dest, entry.sha, entry.size)
            return
    raise FetchError(f"{member}: not in {archive.name}")


# ---- fetch -------------------------------------------------------------------------------------

def _hex(sha: str) -> str:
    """A sha256 hex digest, or FetchError: it is used as a path part, so it must be plain."""
    if not _HEX.fullmatch(sha):
        raise FetchError(f"not a sha256 hex digest: {sha!r}")
    return sha


def _plain_name(name: str) -> str:
    if not name or "/" in name or "\\" in name or name in (".", "..") or "\x00" in name:
        raise FetchError(f"refused file name {name!r}")
    return name


def _local_archive(loc: Locations, arch: Archive) -> Path | None:
    if loc.archive_dir is None:
        return None
    for cand in (loc.archive_dir / arch.file, loc.archive_dir / arch.date / arch.file):
        if cand.exists():
            return cand
    return None


def _base_for(loc: Locations, arch: Archive) -> str | None:
    return loc.data_url.rstrip("/") if loc.data_url else None


def _urls(loc: Locations, arch: Archive, suffix: str = "") -> list[str]:
    """Candidate URLs; every path part is percent-encoded."""
    base = _base_for(loc, arch)
    file = arch.served[0]
    if base:
        date = urllib.parse.quote(arch.date, safe="")
        return [f"{base}/{date}/{urllib.parse.quote(file, safe='')}{suffix}"]
    return [u + suffix for u in arch.urls]


def _out_path(loc: Locations, sha: str, out: Path | None) -> Path:
    _hex(sha)
    if out is None:
        return loc.cache / "files" / sha[:2] / sha
    return out / sha if out.is_dir() else out


def _find(entries: list[Entry], member: str) -> Entry:
    for e in entries:
        if e.path == member:
            if e.type != "f":
                raise FetchError(f"{member}: a {'link' if e.type == 'l' else 'directory'}, "
                                 "not a file")
            return e
    raise FetchError(f"{member}: not in the manifest")


def _served_size(arch: Archive) -> int:
    return arch.public_size if (arch.public_sha256 or arch.public_file) else arch.size


def fetch_member(idx: Path, loc: Locations, name: str, member: str, out: Path | None = None
                 ) -> Path:
    """Fetch one member of an archive; returns the path written. Order: MIMIR_ARCHIVE, the
    cache, the URL (never for a private archive, which also needs its local manifest)."""
    archives = load_archives(idx)
    if name not in archives:
        raise FetchError(f"unknown archive {name!r}")
    arch = archives[name]
    member = safe_member(member)
    local = _local_archive(loc, arch)
    if local is not None:
        entry = _find(archive_entries(idx, arch, loc.private_index), member)
        return _from_file(loc, arch, local, arch.sha256, member, entry, out)
    if arch.private:
        raise FetchError(f"{name} is private: it is never downloaded; set MIMIR_ARCHIVE to a dir "
                         "that holds it")
    file, sha, manifest = arch.served
    entry = _find(parse_manifest_rows(read_tsv_xz(idx / manifest)), member)
    if arch.form == "tar.xz":
        _hex(sha)
        cached = loc.cache / "archives" / f"{sha}-{_plain_name(file)}"
        if cached.exists():
            return _from_file(loc, arch, cached, sha, member, entry, out)
        for url in _urls(loc, arch):
            download(url, cached, sha, _served_size(arch))
            return _from_file(loc, arch, cached, sha, member, entry, out)
    else:
        for url in _urls(loc, arch, "/" + urllib.parse.quote(member)):
            dest = _out_path(loc, entry.sha, out)
            download(url, dest, entry.sha, entry.size)
            return dest
    raise FetchError(f"{name}: not found locally and no URL is known (not uploaded yet?)")


def _from_file(loc: Locations, arch: Archive, path: Path, sha: str, member: str,
               entry: Entry, out: Path | None) -> Path:
    dest = _out_path(loc, entry.sha, out)
    if arch.form == "dir":
        src = path / member
        if not src.is_file() or src.is_symlink():
            raise FetchError(f"{member}: not in {arch.name}")
        with src.open("rb") as fh:
            _copy_checked(fh, dest.with_name(dest.name + ".part"), dest, entry.sha, entry.size)
        return dest
    verified_archive(path, _hex(sha), loc.cache)
    _extract_member(path, member, entry, dest)
    return dest


def blob_member(sha: str) -> str:
    return f"blobs/{sha[:2]}/{sha}.xz"


MAX_BLOB_RAW = 1 << 30  # bound for a blob the index does not list (a local store file)


def _unpack_blob(data: bytes, sha: str, dest: Path, raw_limit: int) -> Path:
    """Decompress a blob (at most raw_limit bytes), check it hashes to its name, write it."""
    try:
        raw = unxz(data, raw_limit)
    except FetchError as exc:
        raise FetchError(f"blob {sha}: {exc}") from exc
    if hashlib.sha256(raw).hexdigest() != sha:
        raise FetchError(f"blob {sha}: content does not match its name")
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    part.write_bytes(raw)
    os.replace(part, dest)
    return dest


def _blob_bytes_from_archive(idx: Path, loc: Locations, ref: BlobRef) -> bytes | None:
    if ref.archive == "-":
        return None
    tmp = loc.cache / "blob-members"
    try:
        path = fetch_member(idx, loc, ref.archive, blob_member(ref.sha), tmp / ref.sha)
    except FetchError:
        return None
    return path.read_bytes()


def fetch_blob(idx: Path, loc: Locations, sha: str, out: Path | None = None) -> Path:
    """Fetch a blob by hash and write its decompressed bytes. Order: the local blob store,
    MIMIR_ARCHIVE (a blob dir or the blob tarball), the cache, the URL (public blobs only)."""
    _hex(sha)
    dest = _out_path(loc, sha, out)
    ref = load_blob_index(idx).get(sha)
    limit = ref.raw_bytes if ref is not None else MAX_BLOB_RAW
    local = blobs.blob_path(loc.blobs, sha)
    if local.is_file():
        return _unpack_blob(local.read_bytes(), sha, dest, limit)
    if ref is None:
        raise FetchError(f"blob {sha}: not in the index")
    if loc.archive_dir is not None:
        for root in (loc.archive_dir, loc.archive_dir / "blobs"):
            cand = root / sha[:2] / f"{sha}.xz"
            if cand.is_file():
                return _unpack_blob(cand.read_bytes(), sha, dest, limit)
        data = _blob_bytes_from_archive(idx, loc, ref)
        if data is not None:
            return _unpack_blob(data, sha, dest, limit)
    cached = loc.cache / "blobs" / sha[:2] / f"{sha}.xz"
    if cached.is_file():
        return _unpack_blob(cached.read_bytes(), sha, dest, limit)
    if loc.data_url:
        if ref.visibility != "public":
            raise FetchError(f"blob {sha}: {ref.visibility}, never downloaded")
        try:
            download_blob(loc.data_url.rstrip("/"), ref, cached)
            return _unpack_blob(cached.read_bytes(), sha, dest, limit)
        except FetchError:
            if ref.archive == "-":
                raise
        data = _blob_bytes_from_archive(idx, loc, ref)
        if data is not None:
            return _unpack_blob(data, sha, dest, limit)
    raise FetchError(f"blob {sha}: not found locally and no URL is known (not uploaded yet?)")


def download_blob(base: str, ref: BlobRef, cached: Path) -> None:
    """Download `<base>/blobs/<ab>/<sha>.xz` (at most ref.xz_bytes). The bytes are checked in
    memory (they must decompress, within ref.raw_bytes, to ref.sha) before the cache file is
    written."""
    url = f"{base}/{blob_member(_hex(ref.sha))}"
    scheme = url.split(":", 1)[0].lower()
    if scheme not in SCHEMES:
        raise FetchError(f"refused URL scheme {scheme!r}")
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:
            data = resp.read(ref.xz_bytes + 1)
    except OSError as exc:
        raise FetchError(f"download failed: {url}: {exc}") from exc
    if len(data) > ref.xz_bytes:
        raise FetchError(f"blob {ref.sha}: longer than the indexed {ref.xz_bytes} bytes, stopped")
    try:
        raw = unxz(data, ref.raw_bytes)
    except FetchError as exc:
        raise FetchError(f"blob {ref.sha}: {exc}") from exc
    if hashlib.sha256(raw).hexdigest() != ref.sha:
        raise FetchError(f"blob {ref.sha}: content does not match its name")
    cached.parent.mkdir(parents=True, exist_ok=True)
    part = cached.with_name(cached.name + ".part")
    part.write_bytes(data)
    os.replace(part, cached)


def find_by_sha(idx: Path, sha: str, priv: Path | None = None) -> list[tuple[str, Entry]]:
    """Every (archive, entry) of the manifests whose file has this sha256 (a private archive's
    manifest counts only when it is present locally)."""
    hits = []
    for name, arch in sorted(load_archives(idx).items()):
        path = manifest_file(idx, arch, priv)
        if path is None or not path.exists():
            continue
        for e in parse_manifest_rows(read_tsv_xz(path)):
            if e.type == "f" and e.sha == sha:
                hits.append((name, e))
    return hits


def fetch_sha(idx: Path, loc: Locations, sha: str, out: Path | None = None) -> Path:
    if not _HEX.fullmatch(sha):
        raise FetchError(f"not a sha256 hex digest: {sha!r}")
    if sha in load_blob_index(idx) or blobs.blob_path(loc.blobs, sha).is_file():
        return fetch_blob(idx, loc, sha, out)
    hits = find_by_sha(idx, sha, loc.private_index)
    if not hits:
        raise FetchError(f"{sha}: no blob or manifest member has this hash")
    errors = []
    for name, entry in hits:
        try:
            return fetch_member(idx, loc, name, entry.path, out)
        except FetchError as exc:
            errors.append(str(exc))
    raise FetchError("; ".join(errors))


def run_blobs(db: sqlite3.Connection, run_id: str) -> list[tuple[str, str]]:
    rows = db.execute("SELECT kind, blob_sha256 FROM run_artifact WHERE run_id = ? ORDER BY kind",
                      (run_id,)).fetchall()
    return [(str(k), str(s)) for k, s in rows]


def fetch_run(idx: Path, loc: Locations, db: sqlite3.Connection, run_id: str, out: Path | None
              ) -> list[tuple[str, Path]]:
    arts = run_blobs(db, run_id)
    if not arts:
        raise FetchError(f"run {run_id}: no artifacts in the store")
    done = []
    for kind, sha in arts:
        dest = out / kind if out is not None else None
        if dest is not None:
            out_dir = out
            assert out_dir is not None
            out_dir.mkdir(parents=True, exist_ok=True)
        done.append((kind, fetch_sha(idx, loc, sha, dest)))
    return done


# ---- remote check ------------------------------------------------------------------------------

class CheckRow(NamedTuple):
    table: str
    column: str
    refs: int
    resolved: int
    missing: tuple[str, ...]


def blob_columns(db: sqlite3.Connection) -> list[tuple[str, str]]:
    cols = []
    tables = db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    for (table,) in tables.fetchall():
        for col in db.execute(f'PRAGMA table_info("{table}")').fetchall():
            if "blob" in str(col[1]).lower():
                cols.append((str(table), str(col[1])))
    return cols


def remote_check(db: sqlite3.Connection, index: dict[str, BlobRef]) -> list[CheckRow]:
    rows = []
    for table, col in blob_columns(db):
        sql = (f'SELECT DISTINCT "{col}" FROM "{table}" '
               f"WHERE \"{col}\" IS NOT NULL AND \"{col}\" != ''")
        refs = sorted({str(v) for (v,) in db.execute(sql)})
        miss = tuple(r for r in refs if r not in index)
        rows.append(CheckRow(table, col, len(refs), len(refs) - len(miss), miss))
    return rows
