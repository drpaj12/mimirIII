"""Snapshots of the SQLite store: a compressed SQL dump, a manifest, optional Parquet.

The unit of comparison is the canonical store text (spec mimir-schema-v2, section 7):
every table in sorted name order, rows in primary-key order, one JSON array per line.
"""

from __future__ import annotations

import hashlib
import json
import lzma
import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path

from mimir import blobs

DUMP_NAME = "mimir.sql.xz"
MANIFEST_NAME = "MANIFEST.json"


def _tables(db: sqlite3.Connection) -> list[str]:
    rows = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name").fetchall()
    return [r[0] for r in rows]


def _order(db: sqlite3.Connection, table: str) -> str:
    info = db.execute(f"PRAGMA table_info({table})").fetchall()
    pk = [r[1] for r in sorted(info, key=lambda r: r[5]) if r[5] > 0]
    return ", ".join(pk or [r[1] for r in info])


def _cell(x: object) -> object:
    return repr(x) if isinstance(x, float) else x


def _literal(x: object) -> str:
    if x is None:
        return "NULL"
    if isinstance(x, float):
        return "9e999" if x == float("inf") else "-9e999" if x == float("-inf") else repr(x)
    if isinstance(x, int):
        return str(x)
    if isinstance(x, bytes):
        return "X'" + x.hex() + "'"
    return "'" + str(x).replace("'", "''") + "'"


BLOB_REFS = (("partition", "assignment_blob"), ("run_artifact", "blob_sha256"),
             ("analysis_result", "labels_blob"))


def iter_dump(db: sqlite3.Connection) -> Iterator[str]:
    """SQL text that rebuilds the store: tables and rows (floats by repr, so they round-trip
    exactly), then indexes and views. Rows are in primary-key order."""
    yield "BEGIN TRANSACTION;"
    for table in _tables(db):
        ddl = db.execute("SELECT sql FROM sqlite_master WHERE name = ?", (table,)).fetchone()[0]
        yield ddl + ";"
        for row in db.execute(f"SELECT * FROM {table} ORDER BY {_order(db, table)}"):
            yield f"INSERT INTO {table} VALUES({','.join(_literal(x) for x in row)});"
    for (sql,) in db.execute(
        "SELECT sql FROM sqlite_master WHERE type IN ('index', 'view') AND sql IS NOT NULL "
        "ORDER BY type DESC, name"
    ):
        yield sql + ";"
    yield "COMMIT;"


def dump_lines(db: sqlite3.Connection) -> list[str]:
    return list(iter_dump(db))


def iter_canonical(db: sqlite3.Connection) -> Iterator[str]:
    """The canonical text: the schema (every table, index and view with its DDL, in name order),
    then every table in sorted name order with rows in primary-key order, one JSON array a line."""
    yield "#schema"
    for kind, name, tbl, sql in db.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' "
        "ORDER BY type, name"
    ):
        yield json.dumps([kind, name, tbl, sql], ensure_ascii=False)
    for table in _tables(db):
        cols = [r[1] for r in db.execute(f"PRAGMA table_info({table})")]
        yield f"#table {table} {json.dumps(cols)}"
        for row in db.execute(f"SELECT * FROM {table} ORDER BY {_order(db, table)}"):
            yield json.dumps([_cell(x) for x in row], ensure_ascii=False)


def canonical_lines(db: sqlite3.Connection) -> list[str]:
    return list(iter_canonical(db))


def canonical_sha256(db: sqlite3.Connection) -> str:
    h = hashlib.sha256()
    for line in iter_canonical(db):
        h.update(line.encode("utf-8") + b"\n")
    return h.hexdigest()


def blob_refs(db: sqlite3.Connection) -> list[str]:
    """Every blob sha256 a table refers to, sorted and distinct."""
    found: set[str] = set()
    for table, col in BLOB_REFS:
        found.update(r[0] for r in db.execute(f"SELECT {col} FROM {table} WHERE {col} != ''"))
    return sorted(found)


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _sync_rename(tmp: Path, final: Path) -> None:
    with open(tmp, "rb") as fh:
        os.fsync(fh.fileno())
    os.replace(tmp, final)


def write_snapshot(db_path: Path, out_dir: Path, parquet: bool = False) -> dict[str, object]:
    """Write the xz SQL dump and the manifest into out_dir; return the manifest.

    The dump, the canonical hash, the counts and the blob list all come from one read
    transaction. Each file is written under a temp name, fsynced and renamed; the manifest is
    renamed last, so a directory with a manifest holds complete files. The database is closed
    on every path."""
    out_dir.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        db.execute("BEGIN")
        dump = out_dir / DUMP_NAME
        tmp = out_dir / (DUMP_NAME + ".tmp")
        with lzma.open(tmp, "wt", encoding="utf-8", newline="\n", preset=6) as fh:
            for line in iter_dump(db):
                fh.write(line + "\n")
        _sync_rename(tmp, dump)
        counts = {t: int(db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])
                  for t in _tables(db)}
        version = db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        refs = blob_refs(db)
        manifest: dict[str, object] = {
            "format": "xz SQL dump (mimir.snapshot.iter_dump)",
            "dump_file": DUMP_NAME,
            "dump_sha256": _file_sha256(dump),
            "dump_bytes": dump.stat().st_size,
            "canonical_sha256": canonical_sha256(db),
            "schema_version": version[0] if version else "",
            "table_rows": counts,
            "blob_refs": refs,
            "source_db_bytes": db_path.stat().st_size,
        }
        if parquet:
            manifest["parquet"] = _write_parquet(db, out_dir)
    finally:
        db.close()
    mtmp = out_dir / (MANIFEST_NAME + ".tmp")
    mtmp.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    _sync_rename(mtmp, out_dir / MANIFEST_NAME)
    return manifest


def _write_parquet(db: sqlite3.Connection, out_dir: Path) -> dict[str, str]:
    """One zstd Parquet file per table (needs pyarrow; ImportError otherwise)."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    files: dict[str, str] = {}
    for table in _tables(db):
        cols = [r[1] for r in db.execute(f"PRAGMA table_info({table})")]
        rows = db.execute(f"SELECT * FROM {table} ORDER BY {_order(db, table)}").fetchall()
        data = {c: [r[i] for r in rows] for i, c in enumerate(cols)}
        name = f"{table}.parquet"
        tmp = out_dir / (name + ".tmp")
        pq.write_table(pa.table(data), str(tmp), compression="zstd")
        _sync_rename(tmp, out_dir / name)
        files[table] = name
    return files


def restore(snapshot_dir: Path, db_path: Path) -> None:
    """Restore the dump into a new database file."""
    with lzma.open(snapshot_dir / DUMP_NAME, "rt", encoding="utf-8", newline="\n") as fh:
        script = fh.read()
    db = sqlite3.connect(db_path)
    try:
        db.executescript(script)
        db.commit()
    finally:
        db.close()


def _first_difference(a: Iterator[str], b: Iterator[str]) -> tuple[int, str, str] | None:
    sentinel = "<end>"
    for i, (x, y) in enumerate(zip(a, b, strict=False)):
        if x != y:
            return i, x[:200], y[:200]
    left, right = next(a, sentinel), next(b, sentinel)
    if left == right:
        return None
    return -1, left[:200], right[:200]


def verify_snapshot(source_db: Path, snapshot_dir: Path, tmp_db: Path,
                    blob_root: Path | None = None) -> list[str]:
    """Restore into tmp_db (a path that does not exist yet) and compare canonical text, schema
    included, byte for byte with the source store; check that every blob the manifest lists
    exists in `blob_root` (default $MIMIR_BLOBS) and is intact. Returns the problems."""
    manifest = json.loads((snapshot_dir / MANIFEST_NAME).read_text(encoding="utf-8"))
    problems = []
    if _file_sha256(snapshot_dir / DUMP_NAME) != manifest["dump_sha256"]:
        problems.append("dump sha256 differs from the manifest")
    restore(snapshot_dir, tmp_db)
    a = sqlite3.connect(f"file:{source_db}?mode=ro", uri=True)
    b = sqlite3.connect(f"file:{tmp_db}?mode=ro", uri=True)
    try:
        a.execute("BEGIN")
        diff = _first_difference(iter_canonical(a), iter_canonical(b))
        if diff is not None:
            problems.append(f"canonical text differs at line {diff[0]}: {diff[1]!r} against "
                            f"{diff[2]!r}")
        if canonical_sha256(b) != manifest["canonical_sha256"]:
            problems.append("restored canonical sha256 differs from the manifest")
        if blob_refs(b) != manifest.get("blob_refs", []):
            problems.append("blob references of the restored store differ from the manifest")
    finally:
        a.close()
        b.close()
    problems += _blob_problems(manifest.get("blob_refs", []), blob_root or blobs.default_dir())
    return problems


def _blob_problems(refs: list[str], root: Path) -> list[str]:
    out = []
    present = []
    for sha in refs:
        if blobs.blob_path(root, sha).exists():
            present.append(sha)
        else:
            out.append(f"blob {sha} missing from {root.name}")
    return out + [f"blob {p}" for p in blobs.verify(root, present)]
