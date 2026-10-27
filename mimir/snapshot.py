"""Snapshots of the SQLite store: a compressed SQL dump, a manifest, optional Parquet.

The unit of comparison is the canonical store text (spec mimir-schema-v2, section 7):
every table in sorted name order, rows in primary-key order, one JSON array per line.
"""

from __future__ import annotations

import hashlib
import json
import lzma
import sqlite3
from pathlib import Path

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


def dump_lines(db: sqlite3.Connection) -> list[str]:
    """SQL text that rebuilds the store: tables and rows (floats by repr, so they round-trip
    exactly), then indexes and views. Rows are in primary-key order."""
    out = ["BEGIN TRANSACTION;"]
    for table in _tables(db):
        ddl = db.execute("SELECT sql FROM sqlite_master WHERE name = ?", (table,)).fetchone()[0]
        out.append(ddl + ";")
        for row in db.execute(f"SELECT * FROM {table} ORDER BY {_order(db, table)}"):
            out.append(f"INSERT INTO {table} VALUES({','.join(_literal(x) for x in row)});")
    for (sql,) in db.execute(
        "SELECT sql FROM sqlite_master WHERE type IN ('index', 'view') AND sql IS NOT NULL "
        "ORDER BY type DESC, name"
    ):
        out.append(sql + ";")
    out.append("COMMIT;")
    return out


def canonical_lines(db: sqlite3.Connection) -> list[str]:
    out: list[str] = []
    for table in _tables(db):
        cols = [r[1] for r in db.execute(f"PRAGMA table_info({table})")]
        out.append(f"#table {table} {json.dumps(cols)}")
        for row in db.execute(f"SELECT * FROM {table} ORDER BY {_order(db, table)}"):
            out.append(json.dumps([_cell(x) for x in row], ensure_ascii=False))
    return out


def canonical_sha256(db: sqlite3.Connection) -> str:
    h = hashlib.sha256()
    for line in canonical_lines(db):
        h.update(line.encode("utf-8") + b"\n")
    return h.hexdigest()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_snapshot(db_path: Path, out_dir: Path, parquet: bool = False) -> dict[str, object]:
    """Write the xz SQL dump and the manifest into out_dir; return the manifest."""
    out_dir.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    dump = out_dir / DUMP_NAME
    with lzma.open(dump, "wt", encoding="utf-8", newline="\n", preset=6) as fh:
        for line in dump_lines(db):
            fh.write(line + "\n")
    counts = {t: int(db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]) for t in _tables(db)}
    version = db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    manifest: dict[str, object] = {
        "format": "xz SQL dump (mimir.snapshot.dump_lines)",
        "dump_file": DUMP_NAME,
        "dump_sha256": _file_sha256(dump),
        "dump_bytes": dump.stat().st_size,
        "canonical_sha256": canonical_sha256(db),
        "schema_version": version[0] if version else "",
        "table_rows": counts,
        "source_db_bytes": db_path.stat().st_size,
    }
    if parquet:
        manifest["parquet"] = _write_parquet(db, out_dir)
    db.close()
    (out_dir / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=1, sort_keys=True) + "\n", encoding="utf-8")
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
        pq.write_table(pa.table(data), str(out_dir / name), compression="zstd")
        files[table] = name
    return files


def restore(snapshot_dir: Path, db_path: Path) -> None:
    """Restore the dump into a new database file."""
    with lzma.open(snapshot_dir / DUMP_NAME, "rt", encoding="utf-8", newline="\n") as fh:
        script = fh.read()
    db = sqlite3.connect(db_path)
    db.executescript(script)
    db.commit()
    db.close()


def verify_snapshot(source_db: Path, snapshot_dir: Path, tmp_db: Path) -> list[str]:
    """Restore into tmp_db (a path that does not exist yet) and compare canonical text byte for
    byte with the source store. Returns the differences (empty when identical)."""
    manifest = json.loads((snapshot_dir / MANIFEST_NAME).read_text(encoding="utf-8"))
    problems = []
    if _file_sha256(snapshot_dir / DUMP_NAME) != manifest["dump_sha256"]:
        problems.append("dump sha256 differs from the manifest")
    restore(snapshot_dir, tmp_db)
    a = sqlite3.connect(f"file:{source_db}?mode=ro", uri=True)
    b = sqlite3.connect(tmp_db)
    la, lb = canonical_lines(a), canonical_lines(b)
    a.close()
    b.close()
    if la != lb:
        first = next((i for i, (x, y) in enumerate(zip(la, lb, strict=False)) if x != y),
                     min(len(la), len(lb)))
        problems.append(f"canonical text differs at line {first} ({len(la)} against {len(lb)})")
    if hashlib.sha256(("\n".join(lb) + "\n").encode()).hexdigest() != manifest["canonical_sha256"]:
        problems.append("restored canonical sha256 differs from the manifest")
    return problems
