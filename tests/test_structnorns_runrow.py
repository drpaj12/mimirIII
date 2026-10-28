from __future__ import annotations

import unittest
from pathlib import Path

from mimir.store import Store
from mimir.structnorns import run_row
from tests.helpers import tmpdir


def _put(store: Store, rid: str, cfg: str, arm: str, seed: int) -> None:
    vals = {"run_id": rid, "slug": "", "config_hash": cfg, "source": "src", "design": "d",
            "arch": "A", "seed": seed, "arm": arm, "family": "f", "input_sha256": "x",
            "tool_commit": "c", "tool_commits": "", "command_line": "", "time_s": 1.0,
            "peak_rss_mib": 1.0, "host": "h", "origin": "o"}
    cols = ",".join(vals)
    marks = ",".join("?" * len(vals))
    store.db.execute(f"insert into run ({cols}) values ({marks})", tuple(vals.values()))


class RunRow(unittest.TestCase):
    def test_picks_the_one_matching_row_among_several(self) -> None:
        store = Store(Path(tmpdir()) / "t.db")
        for i, (arm, seed) in enumerate([("vpr_sa", 1), ("vpr_sa", 2), ("vpr_ap", 1)]):
            _put(store, f"r{i}", f"h{i}", arm, seed)
        store.db.commit()
        job = {"source": "src", "design": "d", "arch": "A", "seed": 2, "arm": "vpr_sa"}
        self.assertEqual(run_row(store, job), ("r1", "h1"))

    def test_no_row_and_two_rows_are_errors(self) -> None:
        store = Store(Path(tmpdir()) / "t.db")
        _put(store, "r0", "h0", "vpr_sa", 1)
        _put(store, "r1", "h1", "vpr_sa", 1)  # same key, two configurations
        store.db.commit()
        job = {"source": "src", "design": "d", "arch": "A", "seed": 1, "arm": "vpr_sa"}
        with self.assertRaises(ValueError):
            run_row(store, job)
        job["seed"] = 9
        with self.assertRaises(ValueError):
            run_row(store, job)
