from __future__ import annotations

import json
import unittest
from pathlib import Path

from mimir.schema import Record
from mimir.store import Store
from mimir.structl15 import compare, loki_counts
from tests.helpers import tmpdir


def rec(design: str, metric: str, value: float) -> Record:
    return Record(design, "mimir-structures", "", "", "", "lut", "a", -1, "", "", metric, "",
                  value, "count", "structures", "1", "r")


class L15Tests(unittest.TestCase):
    def test_counts_and_compare(self) -> None:
        d = Path(tmpdir())
        units: list[dict[str, object]] = [
            {"status": s} for s in ("kept", "late", "lost", "born-joined", "kept")]
        units.append({"status": "lost", "loss": {"transient": True}})   # pure again later
        units.append({"status": "lost", "loss": {"transient": False}})
        (d / "micro_x.stmt.json").write_text(json.dumps({"units": units}), encoding="utf-8")
        self.assertEqual(loki_counts(d / "micro_x.stmt.json"), (7, 3, 4))
        s = Store(d / "s.db")
        s.add([rec("x", "structure.l15_units_reached", 4),
               rec("x", "structure.l15_units_separable", 2),
               rec("y", "structure.l15_units_reached", 1),
               rec("y", "structure.l15_units_separable", 1)])
        self.assertEqual(compare(s, d), [("x", 4, 2, 7, 3, 4)])  # y has no Loki file
