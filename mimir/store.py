"""SQLite store with deterministic CSV and optional Parquet export."""

from __future__ import annotations

import csv
import re
import sqlite3
from collections.abc import Iterable, Iterator
from pathlib import Path

from mimir.schema import COLUMNS, KEY_COLUMNS, SCHEMA_VERSION, Record, check_record

_SQL_TYPES = {"seed": "INTEGER", "value": "REAL"}
_LINE_SUFFIX = re.compile(r":\d+$")


def origin_file(origin: str) -> str:
    """The file part of an origin ("path:12" gives "path"; an origin without a line is itself)."""
    return _LINE_SUFFIX.sub("", origin)


def _create_sql() -> str:
    cols = ", ".join(f"{c} {_SQL_TYPES.get(c, 'TEXT')} NOT NULL" for c in COLUMNS)
    return f"CREATE TABLE IF NOT EXISTS records ({cols}, PRIMARY KEY ({', '.join(KEY_COLUMNS)}))"


class Store:
    """A Mimir database. A write replaces rows with the same identity, so imports are idempotent."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self.db = sqlite3.connect(self.path)
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        self.db.execute(_create_sql())
        self.db.execute(
            "CREATE INDEX IF NOT EXISTS records_source_origin ON records(source, origin)"
        )
        self.db.execute(
            "INSERT OR IGNORE INTO meta VALUES ('schema_version', ?)", (str(SCHEMA_VERSION),)
        )
        self.db.commit()
        self._check_version()

    def _check_version(self) -> None:
        row = self.db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        if row is None or int(row[0]) != SCHEMA_VERSION:
            raise ValueError(f"{self.path}: schema version {row} is not {SCHEMA_VERSION}")

    def close(self) -> None:
        self.db.close()

    def add(self, records: Iterable[Record]) -> int:
        """Insert or replace records; return the number written."""
        rows = []
        for rec in records:
            check_record(rec)
            rows.append(rec.as_tuple())
        marks = ", ".join("?" for _ in COLUMNS)
        self.db.executemany(f"INSERT OR REPLACE INTO records VALUES ({marks})", rows)
        self.db.commit()
        return len(rows)

    def replace_origins(self, records: Iterable[Record]) -> tuple[int, int]:
        """Import records so that the result equals a fresh import of the same source files.

        In one transaction: delete the rows already stored for the (source, origin file) pairs the
        records come from, then insert the records. Rows of a reordered or rewritten file are
        replaced, not added next to the old ones (the line number in `origin` can move). Returns
        (rows deleted, rows written)."""
        batch = list(records)
        for rec in batch:
            check_record(rec)
        pairs: dict[str, set[str]] = {}
        for rec in batch:
            pairs.setdefault(rec.source, set()).add(origin_file(rec.origin))
        marks = ", ".join("?" for _ in COLUMNS)
        try:
            stale = [
                (source, origin)
                for source, files in sorted(pairs.items())
                for (origin,) in self.db.execute(
                    "SELECT DISTINCT origin FROM records WHERE source = ?", (source,)
                ).fetchall()
                if origin_file(origin) in files
            ]
            before = self.db.total_changes
            self.db.executemany("DELETE FROM records WHERE source = ? AND origin = ?", stale)
            deleted = self.db.total_changes - before
            self.db.executemany(
                f"INSERT OR REPLACE INTO records VALUES ({marks})", [r.as_tuple() for r in batch]
            )
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise
        return deleted, len(batch)

    def replace_measured(self, records: Iterable[Record]) -> tuple[int, int]:
        """Store a re-measurement so that no row of an older measurer version stays behind.

        In one transaction: delete every row of each (source, design, arch, measurer) the records
        come from, whatever its measurer_version, then insert the records. Same pattern as
        `replace_origins`. Returns (rows deleted, rows written)."""
        batch = list(records)
        for rec in batch:
            check_record(rec)
        groups = sorted({(r.source, r.design, r.arch, r.measurer) for r in batch})
        marks = ", ".join("?" for _ in COLUMNS)
        try:
            before = self.db.total_changes
            self.db.executemany(
                "DELETE FROM records WHERE source = ? AND design = ? AND arch = ? AND measurer = ?",
                groups,
            )
            deleted = self.db.total_changes - before
            self.db.executemany(
                f"INSERT OR REPLACE INTO records VALUES ({marks})", [r.as_tuple() for r in batch]
            )
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise
        return deleted, len(batch)

    def mixed_versions(self) -> list[tuple[str, list[str]]]:
        """Measurers that have more than one measurer_version in the store: (measurer, versions)."""
        found: dict[str, list[str]] = {}
        for measurer, version in self.db.execute(
            "SELECT DISTINCT measurer, measurer_version FROM records ORDER BY 1, 2"
        ):
            found.setdefault(measurer, []).append(version)
        return [(m, v) for m, v in found.items() if len(v) > 1]

    def merge(self, other: str | Path) -> int:
        """Copy every row of another Mimir database in (same schema version); return its rows."""
        other_store = Store(other)
        other_store.close()
        self.db.execute("ATTACH DATABASE ? AS other", (str(other),))
        self.db.execute("INSERT OR REPLACE INTO records SELECT * FROM other.records")
        n = int(self.db.execute("SELECT COUNT(*) FROM other.records").fetchone()[0])
        self.db.commit()
        self.db.execute("DETACH DATABASE other")
        return n

    def count(self, where: str = "1", args: tuple[str, ...] = ()) -> int:
        row = self.db.execute(f"SELECT COUNT(*) FROM records WHERE {where}", args).fetchone()
        return int(row[0])

    def rows(self) -> Iterator[tuple[str | int | float, ...]]:
        """All rows in identity order (the order every export uses)."""
        order = ", ".join(KEY_COLUMNS)
        yield from self.db.execute(f"SELECT {', '.join(COLUMNS)} FROM records ORDER BY {order}")

    def export_csv(self, path: str | Path) -> int:
        n = 0
        with open(path, "w", newline="", encoding="utf-8") as fh:
            out = csv.writer(fh, lineterminator="\n")
            out.writerow(COLUMNS)
            for row in self.rows():
                out.writerow([repr(x) if isinstance(x, float) else x for x in row])
                n += 1
        return n

    def export_parquet(self, path: str | Path) -> int:
        """Write Parquet; raises ImportError when the `parquet` extra (pyarrow) is not installed."""
        import pyarrow as pa
        import pyarrow.parquet as pq

        data = list(self.rows())
        cols = {c: [r[i] for r in data] for i, c in enumerate(COLUMNS)}
        pq.write_table(pa.table(cols), str(path))
        return len(data)
