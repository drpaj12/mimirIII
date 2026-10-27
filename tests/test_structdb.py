from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path
from types import SimpleNamespace

from mimir.store import Store
from mimir.structcli import export_tables
from mimir.structdb import put_structures
from mimir.structmap import MapRow, Struct, post_levels, set_rows
from tests.helpers import tmpdir

V3_TABLES = {"structure", "structure_mapping", "structure_member"}


def tables(path: Path) -> set[str]:
    db = sqlite3.connect(path)
    got = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    db.close()
    return got


def make_v2(path: Path) -> None:
    """A store as lane 2 wrote it: v2 tables, schema_version 2, one record row."""
    s = Store(path)
    s.db.execute("UPDATE meta SET value='2'")
    for t in V3_TABLES:
        s.db.execute(f"DROP TABLE {t}")
    s.db.execute("INSERT INTO design VALUES ('x/a','h','hdl','x','a','o')")
    s.db.commit()
    s.close()


class MigrationV3Tests(unittest.TestCase):
    def test_v2_to_v3_is_additive(self) -> None:
        d = Path(tmpdir())
        make_v2(d / "v2.db")
        self.assertFalse(V3_TABLES & tables(d / "v2.db"))
        s = Store(d / "v2.db")
        v = s.db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]
        self.assertEqual(v, "3")
        self.assertEqual(s.db.execute("SELECT slug FROM design").fetchall(), [("x/a",)])
        s.close()
        self.assertTrue(tables(d / "v2.db") >= V3_TABLES)

    def test_v3_opens_read_only(self) -> None:
        d = Path(tmpdir())
        Store(d / "x.db").close()
        Store(d / "x.db", readonly=True).close()

    def test_kind_check(self) -> None:
        s = Store(Path(tmpdir()) / "x.db")
        with self.assertRaises(sqlite3.IntegrityError):
            s.db.execute("INSERT INTO structure VALUES ('d','s','blob','','','hdl',1.0,'r','c')")


def fake_map() -> SimpleNamespace:
    def rec(n: int, lv: str, flags: tuple[str, ...] = ()) -> SimpleNamespace:
        return SimpleNamespace(number=n, level=lv, flags=flags)

    return SimpleNamespace(
        records=[rec(1, "ble"), rec(2, "clb"), rec(3, "site", ("x=1", "y=2", "sub=0")),
                 rec(4, "ble"), rec(5, "clb"), rec(6, "site", ("x=3", "y=2", "sub=0"))],
        atoms=[("a", "r1,r2,r3", "-"), ("b", "r1,r2,r3", "-"), ("c", "r4,r5,r6", "-")])


class MappingRowTests(unittest.TestCase):
    def test_post_levels_joins_and_bbox(self) -> None:
        rows = post_levels(fake_map(), {"s1": {"a", "c"}, "s2": {"b"}})
        by = {(r.sid, r.level): r for r in rows}
        self.assertEqual(by[("s1", "ble")].n_bles, 2)
        self.assertEqual(by[("s1", "ble")].joined_with, "s2")  # a and b share the ble r1
        self.assertEqual(by[("s2", "ble")].n_pure, 0)
        self.assertEqual(by[("s1", "clb")].n_pure, 1)
        placed = by[("s1", "placed")]
        self.assertEqual(placed.bbox, (1, 2, 3, 2))
        self.assertEqual(placed.spread, 1.0)
        self.assertEqual(by[("s2", "placed")].spread, 0.0)

    def test_set_rows_without_a_map(self) -> None:
        atoms = {"a": "lut", "b": "ff", "c": "carry"}
        rows = set_rows({"s1": {"a", "b"}, "s2": {"b", "c"}}, atoms, None)
        by = {r.sid: r for r in rows}
        self.assertEqual((by["s1"].n_luts, by["s1"].n_ffs, by["s1"].n_pure), (1, 1, 1))
        self.assertEqual(by["s1"].joined_with, "s2")
        self.assertEqual(by["s2"].n_carry, 1)
        self.assertTrue(all(r.level == "lut" for r in rows))


class ExportTests(unittest.TestCase):
    def build(self, path: Path) -> None:
        s = Store(path)
        structs = [Struct("hdl:f:1.1-1.5", "adder", "f:1-1", "ALWAYS@f:1.1-1.5", "hdl", 0.85)]
        rows = [MapRow("hdl:f:1.1-1.5", "lut", 2, 1, 1, n_luts=2, joined_with="x", spread=None),
                MapRow("hdl:f:1.1-1.5", "placed", 1, 1, 0, n_clbs=1, bbox=(1, 1, 2, 2),
                       spread=0.5)]
        put_structures(s, "micro/f", "run1", "cfg1", structs, rows,
                       {"hdl:f:1.1-1.5": {"b", "a"}})
        s.db.commit()
        s.close()

    def test_two_exports_are_byte_identical(self) -> None:
        d = Path(tmpdir())
        self.build(d / "a.db")
        self.build(d / "b.db")
        for name in ("a", "b"):
            export_tables(Store(d / f"{name}.db", readonly=True), d / name)
        for t in V3_TABLES:
            self.assertEqual((d / "a" / f"{t}.csv").read_bytes(),
                             (d / "b" / f"{t}.csv").read_bytes())
        text = (d / "a" / "structure_mapping.csv").read_text(encoding="utf-8")
        self.assertIn("0.5", text)
        self.assertNotIn("\r", text)
