from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path

from mimir.schema import COLUMNS, KEY_COLUMNS
from mimir.store import Store
from tests.helpers import tmpdir
from tests.test_store import rec

V2_TABLES = {
    "design", "design_source", "design_meta", "design_lineage", "flow_config", "flow_param",
    "run", "run_artifact", "partition", "analysis_result",
}


def make_v1(path: Path) -> None:
    """A version 1 store: the v1 DDL (records, meta) with schema_version 1, as lane 1 wrote it."""
    cols = ", ".join(f"{c} {'INTEGER' if c == 'seed' else 'REAL' if c == 'value' else 'TEXT'}"
                     " NOT NULL" for c in COLUMNS)
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    db.execute(f"CREATE TABLE records ({cols}, PRIMARY KEY ({', '.join(KEY_COLUMNS)}))")
    db.execute("INSERT INTO meta VALUES ('schema_version', '1')")
    marks = ", ".join("?" for _ in COLUMNS)
    for r in (rec("a", "m", 1.5), rec("b", "m", 2.0), rec("a", "n", 0.1, "x")):
        db.execute(f"INSERT INTO records VALUES ({marks})", r.as_tuple())
    db.commit()
    db.close()


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
        s.db.execute("INSERT INTO run VALUES ('r1','t/a','c1','t','a','',-1,'','','',NULL,NULL,"
                     "NULL,NULL,'o')")
        row = s.db.execute("SELECT run_id, slug FROM record_run").fetchall()
        self.assertEqual(row, [("r1", "t/a")])


if __name__ == "__main__":
    unittest.main()
