"""Per-path tables (schema 6): import, backfill, v5 read only."""

from __future__ import annotations

import contextlib
import io
import json
import sqlite3
import unittest
from pathlib import Path

from mimir import blobs, timing
from mimir.cli import main
from mimir.scrub import Scrubber
from mimir.store import Store
from tests.helpers import tmpdir

ATTR = {
    "schema_version": 1, "timing": {"cpd_ns": 5.0, "paths_requested": 100, "paths_in_report": 2},
    "paths": [
        {"index": 1, "slack_ns": -2.0, "arrival_ns": 5.0, "required_ns": 3.0,
         "startpoint": "a (.latch clocked by clk)", "endpoint": "b (.latch clocked by clk)",
         "nodes": [
             {"atom": "n1", "block_type": ".names", "pins": ["in[0]", "out[0]"],
              "cell_delay_ns": 0.5, "net_delay_in_ns": 0.25, "delay_ns": 1.0,
              "category": "matched", "span": "/home/x/d.v:10", "module": "m", "word": "w",
              "bit": 3, "word_via": "name", "loc": "d.v:10.1-10.9"},
             {"atom": "n2", "block_type": ".latch", "pins": ["D"], "delay_ns": 0.5,
              "span": "d.v:20", "module": "m", "word": "z", "word_via": "declarator"}]},
        {"index": 2, "slack_ns": -1.0, "arrival_ns": 4.0, "required_ns": 3.0,
         "startpoint": "a (.latch clocked by clk)", "endpoint": "c (.latch clocked by clk)",
         "nodes": [{"atom": "n1", "block_type": ".names", "pins": [], "delay_ns": 1.0,
                    "span": "d.v:10", "module": "m", "word": "w", "bit": 3,
                    "word_via": "name"}]},
    ],
}


def make() -> tuple[Store, Path, str]:
    d = Path(tmpdir())
    s = Store(d / "t.db")
    s.db.execute("INSERT INTO run VALUES ('r1', 'slug', 'cfg', 'src', 'des', 'arch', 1, 'a', '', "
                 "'', NULL, NULL, NULL, NULL, 'o', 'tc', 'in')")
    data = json.dumps(ATTR).encode()
    sha = blobs.put_bytes(d / "blobs", data)
    s.db.execute("INSERT INTO run_artifact (run_id, kind, blob_sha256) VALUES ('r1', 'timing', ?)",
                 (sha,))
    s.db.commit()
    return s, d, sha


class Paths(unittest.TestCase):
    def test_import_writes_paths_and_nodes(self) -> None:
        s, _, _ = make()
        timing.import_run(s, "r1", timing.load_attribution_bytes(json.dumps(ATTR).encode()),
                          Scrubber({}))
        p = s.db.execute("SELECT path_index, slack_ns, arrival_ns, crit, n_nodes FROM timing_path "
                         "ORDER BY 1").fetchall()
        self.assertEqual(p, [(1, -2.0, 5.0, 1.0, 2), (2, -1.0, 4.0, 0.8, 1)])
        n = s.db.execute("SELECT step, atom, pins, span, bit, cell_delay_ns FROM timing_path_node "
                         "WHERE path_index = 1 ORDER BY step").fetchall()
        self.assertEqual(n[0], (1, "n1", '["in[0]","out[0]"]', "$HOME/d.v:10", 3, 0.5))
        self.assertEqual(n[1][4], -1)
        # crit equals the histogram's input: same relaxed criticality
        self.assertEqual(s.db.execute("SELECT SUM(n) FROM timing_path_hist").fetchone()[0], 2)

    def test_reimport_replaces(self) -> None:
        s, _, _ = make()
        inp = timing.load_attribution_bytes(json.dumps(ATTR).encode())
        timing.import_run(s, "r1", inp, Scrubber({}))
        timing.import_run(s, "r1", inp, Scrubber({}))
        self.assertEqual(s.db.execute("SELECT COUNT(*) FROM timing_path_node").fetchone()[0], 3)

    def test_backfill_idempotent_and_only_path_tables(self) -> None:
        s, d, _ = make()
        inp = timing.load_attribution_bytes(json.dumps(ATTR).encode())
        timing.import_run(s, "r1", inp, Scrubber({}))
        for t in timing.PATH_TABLES:
            s.db.execute(f"DELETE FROM {t}")
        s.db.commit()
        obj = s.db.execute("SELECT * FROM timing_object ORDER BY 2,3,4").fetchall()
        rows = timing.backfill_paths(s, d / "blobs", Scrubber({}))
        self.assertEqual(rows, [("r1", "ok")])
        self.assertEqual(s.db.execute("SELECT COUNT(*) FROM timing_path_node").fetchone()[0], 3)
        self.assertEqual(timing.backfill_paths(s, d / "blobs", Scrubber({})), [])
        self.assertEqual(s.db.execute("SELECT * FROM timing_object ORDER BY 2,3,4").fetchall(),
                         obj)

    def test_backfill_skips_when_source_differs(self) -> None:
        s, d, _ = make()
        timing.import_run(s, "r1", timing.load_attribution_bytes(json.dumps(ATTR).encode()),
                          Scrubber({}))
        s.db.execute("DELETE FROM timing_path")
        s.db.execute("UPDATE timing_run SET source_sha256 = 'ff'")
        s.db.commit()
        rows = timing.backfill_paths(s, d / "blobs", Scrubber({}))
        self.assertTrue(rows[0][1].startswith("skipped"))
        self.assertEqual(s.db.execute("SELECT COUNT(*) FROM timing_path").fetchone()[0], 0)

    def test_backfill_cli(self) -> None:
        s, d, _ = make()
        timing.import_run(s, "r1", timing.load_attribution_bytes(json.dumps(ATTR).encode()),
                          Scrubber({}))
        s.db.execute("DELETE FROM timing_path")
        s.db.commit()
        s.close()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = main(["import-timing", str(d / "t.db"), "--paths-from-blobs",
                       "--blobs", str(d / "blobs")])
        self.assertEqual(rc, 0)
        self.assertIn("filled 1", out.getvalue())

    def test_v5_store_reads_as_is_and_migrates(self) -> None:
        d = Path(tmpdir())
        Store(d / "x.db").close()
        db = sqlite3.connect(d / "x.db")
        for t in timing.PATH_TABLES:
            db.execute(f"DROP TABLE {t}")
        db.execute("UPDATE meta SET value='5' WHERE key='schema_version'")
        db.commit()
        db.close()
        r = Store(d / "x.db", readonly=True)
        self.assertFalse(timing.has_path_tables(r))
        r.close()
        s = Store(d / "x.db")
        self.assertTrue(timing.has_path_tables(s))
        s.close()


if __name__ == "__main__":
    unittest.main()
