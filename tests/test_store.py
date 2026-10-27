from __future__ import annotations

import unittest
from pathlib import Path

from mimir.schema import COLUMNS, Record
from mimir.store import Store
from tests.helpers import skip_without, tmpdir


def rec(design: str, metric: str, value: float, bin_: str = "") -> Record:
    return Record(design=design, source="t", input_sha256="", tool_commit="", script_hash="",
                  level="lut", arch="", seed=-1, arm="", family="", metric=metric, bin=bin_,
                  value=value, unit="nodes", measurer="m", measurer_version="1", origin="o")


class StoreTests(unittest.TestCase):
    def test_idempotent_and_ordered(self) -> None:
        d = Path(tmpdir())
        rows = [rec("b", "struct.n_comb", 2), rec("a", "struct.n_comb", 1),
                rec("a", "struct.level_width", 3, "1")]
        s1, s2 = Store(d / "1.db"), Store(d / "2.db")
        s1.add(rows)
        s1.add(rows)  # second import replaces, does not duplicate
        s2.add(list(reversed(rows)))
        self.assertEqual(s1.count(), 3)
        s1.export_csv(d / "1.csv")
        s2.export_csv(d / "2.csv")
        self.assertEqual((d / "1.csv").read_bytes(), (d / "2.csv").read_bytes())
        first = (d / "1.csv").read_text().splitlines()
        self.assertEqual(first[0].split(",")[0], "design")
        self.assertTrue(first[1].startswith("a,"))

    def test_merge(self) -> None:
        d = Path(tmpdir())
        a, b = Store(d / "a.db"), Store(d / "b.db")
        a.add([rec("a", "m", 1)])
        b.add([rec("a", "m", 2), rec("b", "m", 3)])
        b.close()
        self.assertEqual(a.merge(d / "b.db"), 2)
        self.assertEqual(a.count(), 2)

    def test_replace_updates_value(self) -> None:
        s = Store(Path(tmpdir()) / "x.db")
        s.add([rec("a", "m", 1)])
        s.add([rec("a", "m", 5)])
        self.assertEqual([r[COLUMNS.index("value")] for r in s.rows()], [5.0])

    def test_bad_level_rejected(self) -> None:
        s = Store(Path(tmpdir()) / "x.db")
        bad = rec("a", "m", 1)
        object.__setattr__(bad, "level", "nope")
        with self.assertRaises(ValueError):
            s.add([bad])

    @skip_without("pyarrow")
    def test_parquet(self) -> None:
        d = Path(tmpdir())
        s = Store(d / "x.db")
        s.add([rec("a", "m", 1)])
        self.assertEqual(s.export_parquet(d / "x.parquet"), 1)


if __name__ == "__main__":
    unittest.main()
