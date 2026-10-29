"""`mimir merge --runs`: copy whole runs (and what hangs off them) from one store into another.

A run is copied when its run_id is not in the target. Everything keyed by run_id comes with it, the
records the run measured (matched by the run's natural key, as the `record_run` view does) and
the flow_config / flow_param rows it references (insert or ignore). Blobs the run artifacts
reference are copied between blob directories with a sha256 check.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from mimir import blobs
from mimir.schema import COLUMNS, SCHEMA_VERSION
from mimir.store import Store

# Tables keyed by run_id, copied whole for each new run. Schema v3 to v7.
RUN_TABLES: tuple[str, ...] = (
    "run_artifact", "structure", "structure_mapping", "structure_member",
    "timing_run", "timing_path_hist", "timing_object", "timing_path", "timing_path_node",
    "hdl_graph_run", "hdl_edge", "hdl_port",
)
_RUN_KEY = ("source", "design", "arch", "seed", "arm", "config_hash", "tool_commit",
            "input_sha256")
_REC_KEY = ("source", "design", "arch", "seed", "arm", "tool_commit", "input_sha256")
BACKUP_ADVICE = ("BACKUP FIRST: copy the target store and compare sha256 before a merge "
                 "(this command does not back anything up).")


@dataclass
class RunMergeResult:
    runs: int = 0
    conflicts: list[str] = field(default_factory=list)
    rows: dict[str, int] = field(default_factory=dict)
    records: int = 0
    configs: int = 0
    blobs_copied: int = 0
    blobs_present: int = 0
    blobs_missing: list[str] = field(default_factory=list)


def stored_version(path: str | Path) -> str | None:
    """The schema version of a store file, read without writing; None for a file without one."""
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        has = db.execute("SELECT 1 FROM sqlite_master WHERE name='meta'").fetchone()
        if has is None:
            return None
        row = db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        return None if row is None else str(row[0])
    finally:
        db.close()


def check_versions(target: str | Path, source: str | Path) -> None:
    """Raise ValueError unless both stores are at the current schema version."""
    for label, path in (("target", target), ("source", source)):
        v = stored_version(path)
        if v != str(SCHEMA_VERSION):
            raise ValueError(
                f"{label} {path}: schema version {v}, merge --runs needs {SCHEMA_VERSION}; "
                f"back it up, run `mimir migrate` on it, then retry")


def _new_runs(db: sqlite3.Connection) -> tuple[list[str], list[str]]:
    """(run_ids to copy, conflicts) from attached `src` against main."""
    key = " AND ".join(f"m.{c} = s.{c}" for c in _RUN_KEY)
    todo, bad = [], []
    for rid, other in db.execute(
        f"SELECT s.run_id, (SELECT m.run_id FROM main.run m WHERE {key}) FROM src.run s "
        "WHERE s.run_id NOT IN (SELECT run_id FROM main.run) ORDER BY s.run_id"
    ).fetchall():
        if other is None:
            todo.append(rid)
        else:
            bad.append(f"{rid}: same run key as {other} already in the target")
    return todo, bad


IDS = "(SELECT run_id FROM temp.merge_ids)"  # the run_ids to copy, bound through a temp table


def _shared_cols(db: sqlite3.Connection, table: str) -> str:
    """Column list for `table`: the target's columns (in its order) that the source also has.

    ValueError when the target has a NOT NULL column without a default that the source lacks (the
    copy could not fill it), or when the table is missing from either store."""
    tgt = db.execute(f"PRAGMA main.table_info({table})").fetchall()
    src = {str(r[1]) for r in db.execute(f"PRAGMA src.table_info({table})")}
    if not tgt or not src:
        raise ValueError(f"table {table} is missing from the target or the source")
    lacking = [str(r[1]) for r in tgt if str(r[1]) not in src and r[3] and r[4] is None]
    if lacking:
        raise ValueError(f"source {table} lacks NOT NULL column(s) without a default in the "
                         f"target: {', '.join(lacking)}")
    return ", ".join(str(r[1]) for r in tgt if str(r[1]) in src)


def _insert(db: sqlite3.Connection, verb: str, table: str, where: str) -> int:
    cols = _shared_cols(db, table)
    before = db.total_changes
    db.execute(f"{verb} INTO main.{table} ({cols}) SELECT {cols} FROM src.{table} WHERE {where}")
    return db.total_changes - before


def _copy_table(db: sqlite3.Connection, table: str) -> int:
    return _insert(db, "INSERT OR IGNORE", table, f"run_id IN {IDS}")


def _copy_records(db: sqlite3.Connection) -> int:
    key = " AND ".join(f"u.{c} = r.{c}" for c in _REC_KEY)
    cols = ", ".join(f"r.{c}" for c in COLUMNS)
    before = db.total_changes
    db.execute(f"INSERT OR IGNORE INTO main.records SELECT {cols} FROM src.records r "
               f"JOIN src.run u ON {key} WHERE u.run_id IN {IDS}")
    return db.total_changes - before


def _copy_configs(db: sqlite3.Connection) -> int:
    sel = f"SELECT config_hash FROM src.run WHERE run_id IN {IDS}"
    n = _insert(db, "INSERT OR IGNORE", "flow_config", f"config_hash IN ({sel})")
    _insert(db, "INSERT OR IGNORE", "flow_param", f"config_hash IN ({sel})")
    return n


def _blob_refs(db: sqlite3.Connection) -> list[str]:
    refs = {r[0] for r in db.execute(
        f"SELECT blob_sha256 FROM src.run_artifact WHERE run_id IN {IDS}")}
    return sorted(refs)


def _copy_blobs(refs: list[str], src: Path, dst: Path, res: RunMergeResult) -> None:
    for sha in refs:
        try:
            data = blobs.get_bytes(src, sha)  # sha256 checked on read
        except (OSError, ValueError, EOFError) as exc:
            res.blobs_missing.append(f"{sha}: {exc}")
            continue
        if blobs.blob_path(dst, sha).exists() and not blobs.verify(dst, [sha]):
            res.blobs_present += 1
            continue
        if blobs.put_bytes(dst, data) != sha:
            res.blobs_missing.append(f"{sha}: written blob has another hash")
        else:
            res.blobs_copied += 1


def merge_runs(target: str | Path, source: str | Path, blobs_from: Path | None = None,
               blobs_to: Path | None = None) -> RunMergeResult:
    """Copy the runs of `source` that the target lacks; one transaction; idempotent."""
    check_versions(target, source)
    if (blobs_from is None) != (blobs_to is None):
        raise ValueError("give both --blobs-from and --blobs-to, or neither")
    store = Store(target)
    res = RunMergeResult()
    db = store.db
    try:
        db.execute("ATTACH DATABASE ? AS src", (str(source),))
        todo, res.conflicts = _new_runs(db)
        res.runs = len(todo)
        if todo:
            db.execute("CREATE TEMP TABLE merge_ids (run_id TEXT PRIMARY KEY)")
            db.executemany("INSERT INTO temp.merge_ids VALUES (?)", [(r,) for r in todo])
            db.commit()
            if blobs_from is not None and blobs_to is not None and blobs_from != blobs_to:
                _copy_blobs(_blob_refs(db), blobs_from, blobs_to, res)  # before the rows
            db.execute("BEGIN")
            _insert(db, "INSERT", "run", f"run_id IN {IDS}")
            res.configs = _copy_configs(db)
            for table in RUN_TABLES:
                res.rows[table] = _copy_table(db, table)
            res.records = _copy_records(db)
            db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.execute("DROP TABLE IF EXISTS temp.merge_ids")
        db.execute("DETACH DATABASE src")
        store.close()
    return res


def integrity(path: str | Path) -> str:
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        return str(db.execute("PRAGMA integrity_check").fetchone()[0])
    finally:
        db.close()
