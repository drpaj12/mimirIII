from __future__ import annotations

import hashlib
import shutil
import sqlite3
import unittest
from pathlib import Path
from unittest import mock

import mimir.store as store_mod
from mimir.schema import V2_DDL
from mimir.store import Store
from tests.helpers import tmpdir
from tests.test_store import rec

V2_TABLES = {
    "design", "design_source", "design_meta", "design_lineage", "flow_config", "flow_param",
    "run", "run_artifact", "partition", "analysis_result",
}


FIXTURE = Path(__file__).parent / "fixtures" / "v1-848f303.db"
# the lane-1 DDL exactly as mimirIII main 848f303 wrote it (mimir/store.py _create_sql, schema.py)
V1_RECORDS_DDL = (
    "CREATE TABLE records (design TEXT NOT NULL, source TEXT NOT NULL, input_sha256 TEXT NOT NULL, "
    "tool_commit TEXT NOT NULL, script_hash TEXT NOT NULL, level TEXT NOT NULL, arch TEXT NOT "
    "NULL, seed INTEGER NOT NULL, arm TEXT NOT NULL, family TEXT NOT NULL, metric TEXT NOT NULL, "
    "bin TEXT NOT NULL, value REAL NOT NULL, unit TEXT NOT NULL, measurer TEXT NOT NULL, "
    "measurer_version TEXT NOT NULL, origin TEXT NOT NULL, PRIMARY KEY (design, source, "
    "input_sha256, tool_commit, script_hash, level, arch, seed, arm, family, metric, bin, "
    "measurer, origin))")


def make_v1(path: Path) -> None:
    """Copy the committed v1 store: written by the lane-1 Store of main 848f303, three rows."""
    shutil.copyfile(FIXTURE, path)


def open_as_v1(path: Path) -> None:
    """What lane 1's Store(path) does (848f303 mimir/store.py, __init__ and _check_version):
    create-if-missing statements, INSERT OR IGNORE of the version, then a version check."""
    db = sqlite3.connect(path)
    try:
        db.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        db.execute(V1_RECORDS_DDL.replace("CREATE TABLE", "CREATE TABLE IF NOT EXISTS"))
        db.execute("CREATE INDEX IF NOT EXISTS records_source_origin ON records(source, origin)")
        db.execute("INSERT OR IGNORE INTO meta VALUES ('schema_version', '1')")
        db.commit()
        row = db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        if row is None or int(row[0]) != 1:
            raise ValueError(f"{path}: schema version {row} is not 1")
    finally:
        db.close()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tables(path: Path) -> set[str]:
    db = sqlite3.connect(path)
    got = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    db.close()
    return got


class MigrationTests(unittest.TestCase):
    def test_v1_to_v2_is_lossless(self) -> None:
        d = Path(tmpdir())
        make_v1(d / "v1.db")
        before = tables(d / "v1.db")
        self.assertFalse(V2_TABLES & before)
        raw = sqlite3.connect(d / "v1.db")
        rows_before = raw.execute("SELECT * FROM records ORDER BY rowid").fetchall()
        raw.close()
        s = Store(d / "v1.db")
        s.export_csv(d / "after.csv")
        v = s.db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]
        self.assertEqual(v, "2")
        self.assertEqual(s.db.execute("SELECT * FROM records ORDER BY rowid").fetchall(),
                         rows_before)
        s.close()
        self.assertTrue(tables(d / "v1.db").issuperset(V2_TABLES))
        # same rows as a store that was v2 from the start
        fresh = Store(d / "fresh.db")
        fresh.add([rec("a", "m", 1.5), rec("b", "m", 2.0), rec("a", "n", 0.1, "x")])
        fresh.export_csv(d / "fresh.csv")
        self.assertEqual((d / "after.csv").read_bytes(), (d / "fresh.csv").read_bytes())

    def test_fixture_is_the_v1_ddl(self) -> None:
        db = sqlite3.connect(FIXTURE)
        ddl = db.execute("SELECT sql FROM sqlite_master WHERE name='records'").fetchone()[0]
        version = db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]
        db.close()
        self.assertEqual((ddl, version), (V1_RECORDS_DDL, "1"))

    def test_crash_mid_migration_rolls_back(self) -> None:
        d = Path(tmpdir())
        make_v1(d / "v1.db")
        before = sha(d / "v1.db")
        bad = (*V2_DDL[:4], "CREATE TABLE broken (")
        with mock.patch.object(store_mod, "V2_DDL", bad), self.assertRaises(sqlite3.Error):
            Store(d / "v1.db")
        self.assertEqual(sha(d / "v1.db"), before)  # nothing written
        self.assertFalse(V2_TABLES & tables(d / "v1.db"))
        db = sqlite3.connect(d / "v1.db")
        self.assertEqual(db.execute("SELECT value FROM meta WHERE key='schema_version'")
                         .fetchone()[0], "1")
        self.assertEqual(db.execute("SELECT COUNT(*) FROM records").fetchone()[0], 3)
        db.close()
        Store(d / "v1.db").close()  # and the real migration still works afterwards
        self.assertTrue(tables(d / "v1.db").issuperset(V2_TABLES))

    def test_v2_store_opened_by_v1_code_is_refused_and_not_written(self) -> None:
        d = Path(tmpdir())
        s = Store(d / "x.db")
        s.add([rec("a", "m", 1.0)])
        s.close()
        before = sha(d / "x.db")
        with self.assertRaises(ValueError):
            open_as_v1(d / "x.db")
        self.assertEqual(sha(d / "x.db"), before)

    def test_v2_opens_read_only_and_writes_nothing(self) -> None:
        d = Path(tmpdir())
        s = Store(d / "x.db")
        s.add([rec("a", "m", 1.0)])
        s.close()
        before = sha(d / "x.db")
        ro = Store(d / "x.db", readonly=True)
        self.assertEqual(ro.count(), 1)
        with self.assertRaises(sqlite3.OperationalError):
            ro.db.execute("DELETE FROM records")
        ro.close()
        self.assertEqual(sha(d / "x.db"), before)

    def test_v1_cannot_be_opened_read_only_and_stays_v1(self) -> None:
        d = Path(tmpdir())
        make_v1(d / "v1.db")
        before = sha(d / "v1.db")
        with self.assertRaises(ValueError):
            Store(d / "v1.db", readonly=True)
        self.assertEqual(sha(d / "v1.db"), before)

    def test_bad_version_is_refused_before_any_write(self) -> None:
        d = Path(tmpdir())
        Store(d / "x.db").close()
        db = sqlite3.connect(d / "x.db")
        db.execute("UPDATE meta SET value='9' WHERE key='schema_version'")
        db.commit()
        db.close()
        before = sha(d / "x.db")
        with self.assertRaises(ValueError):
            Store(d / "x.db")
        self.assertEqual(sha(d / "x.db"), before)

    def test_reopen_and_bad_version(self) -> None:
        d = Path(tmpdir())
        Store(d / "x.db").close()
        Store(d / "x.db").close()
        db = sqlite3.connect(d / "x.db")
        db.execute("UPDATE meta SET value='9' WHERE key='schema_version'")
        db.commit()
        db.close()
        with self.assertRaises(ValueError):
            Store(d / "x.db")

    def test_conf_check(self) -> None:
        s = Store(Path(tmpdir()) / "x.db")
        with self.assertRaises(sqlite3.IntegrityError):
            s.db.execute("INSERT INTO design_meta VALUES ('a','f','v','s','guess')")

    def test_record_run_view(self) -> None:
        s = Store(Path(tmpdir()) / "x.db")
        s.add([rec("a", "m", 1.0)])
        s.db.execute("INSERT INTO run (run_id, slug, config_hash, source, design, arch, seed, arm, "
                     "family, tool_commits, origin) "
                     "VALUES ('r1','t/a','c1','t','a','',-1,'','','','o')")
        row = s.db.execute("SELECT run_id, slug FROM record_run").fetchall()
        self.assertEqual(row, [("r1", "t/a")])


if __name__ == "__main__":
    unittest.main()
