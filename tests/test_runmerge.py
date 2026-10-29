from __future__ import annotations

import argparse
import contextlib
import io
import os
import sqlite3
import unittest
from pathlib import Path
from unittest import mock

from mimir import blobs, privacy, runmerge
from mimir.hostcli import _cmd_privacy_check
from mimir.schema import SCHEMA_VERSION
from mimir.store import Store
from tests.helpers import tmpdir

_CHECKED = {"kind": "adder", "level": "gate", "source_kind": "report", "granularity": "block",
            "conf": "primary", "text_kind": "reconstructed", "status": "full"}
_OVERRIDE = {
    "timing_object": {"kind": "module"}, "hdl_port": {"kind": "PI"},
    "structure_mapping": {"level": "gate"}, "structure": {"kind": "adder", "granularity": "block"},
}


def _row(db: sqlite3.Connection, table: str, rid: str, **fixed: object) -> None:
    cols = list(db.execute(f"PRAGMA table_info({table})"))
    vals: list[object] = []
    for c in cols:
        name, typ = str(c[1]), str(c[2]).upper()
        if name in fixed:
            vals.append(fixed[name])
        elif name == "run_id":
            vals.append(rid)
        elif name in _OVERRIDE.get(table, {}):
            vals.append(_OVERRIDE[table][name])
        elif table == "timing_run" and name == "source_kind":
            vals.append("report")
        elif typ == "INTEGER":
            vals.append(1)
        elif typ == "REAL":
            vals.append(1.5)
        else:
            vals.append(f"{table}.{name}.{rid}")
    marks = ", ".join("?" for _ in cols)
    db.execute(f"INSERT OR REPLACE INTO {table} VALUES ({marks})", vals)


def add_run(db: sqlite3.Connection, rid: str, cfg: str, blob: str, design: str = "d1") -> None:
    db.execute("INSERT OR IGNORE INTO flow_config VALUES (?, 'n', 't', 'reconstructed', 'full', "
               "'o')", (cfg,))
    db.execute("INSERT OR IGNORE INTO flow_param VALUES (?, 's', 'k', 'v', 'given', 'x')", (cfg,))
    db.execute("INSERT INTO run (run_id, slug, config_hash, source, design, arch, seed, arm, "
               "family, tool_commits, origin, tool_commit, input_sha256) VALUES "
               "(?, 's', ?, 'src', ?, 'a', 1, '', '', '', 'o', 'tc', 'in')", (rid, cfg, design))
    for table in runmerge.RUN_TABLES:
        extra = {"blob_sha256": blob} if table == "run_artifact" else {}
        if table == "structure":
            extra = {"design": design, "structure_id": rid}
        if table in ("structure_mapping", "structure_member"):
            extra = {"design": design, "structure_id": rid}
        _row(db, table, rid, **extra)
    db.execute("INSERT INTO records VALUES ('d1','src','in','tc','', 'gate','a',1,'','','m','b',"
                "2.0,'u','me','1','o:1')".replace("'d1'", repr(design)))
    db.commit()


def make(path: Path, rids: list[str], blob_root: Path | None = None) -> Path:
    s = Store(path)
    for rid in rids:
        sha = blobs.put_bytes(blob_root, rid.encode()) if blob_root else "0" * 64
        add_run(s.db, rid, "cfg-" + rid[0], sha, design="d" + rid)
    s.close()
    return path


def count(path: Path, table: str) -> int:
    c = sqlite3.connect(path)
    try:
        return int(c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    finally:
        c.close()


class MergeRunsTests(unittest.TestCase):
    def test_every_run_id_table_is_handled(self) -> None:
        s = Store(Path(tmpdir()) / "x.db")
        keyed = set()
        for (name,) in s.db.execute("SELECT name FROM sqlite_master WHERE type='table'"):
            cols = {r[1] for r in s.db.execute(f"PRAGMA table_info({name})")}
            if "run_id" in cols:
                keyed.add(name)
        self.assertEqual(keyed - {"run"}, set(runmerge.RUN_TABLES))

    def test_copies_all_tables_and_is_idempotent(self) -> None:
        tmp = Path(tmpdir())
        a = make(tmp / "a.db", ["a1", "a2"])
        b = make(tmp / "b.db", ["a2", "b1", "b2"])
        r = runmerge.merge_runs(a, b)
        self.assertEqual((r.runs, r.records), (2, 2))
        self.assertEqual(count(a, "run"), 4)
        for t in runmerge.RUN_TABLES:
            self.assertEqual(r.rows[t], 2, t)
            self.assertEqual(count(a, t), 4, t)
        self.assertEqual(count(a, "records"), 4)
        self.assertEqual(count(a, "flow_config"), 2)  # cfg-a and cfg-b
        self.assertEqual(runmerge.integrity(a), "ok")
        r2 = runmerge.merge_runs(a, b)
        self.assertEqual((r2.runs, r2.records, sum(r2.rows.values())), (0, 0, 0))
        self.assertEqual(count(a, "run"), 4)

    def test_structure_rows_follow_the_run(self) -> None:
        tmp = Path(tmpdir())
        a = make(tmp / "a.db", ["a1"])
        b = make(tmp / "b.db", ["b1"])
        runmerge.merge_runs(a, b)
        c = sqlite3.connect(a)
        got = c.execute("SELECT design, run_id FROM structure ORDER BY 2").fetchall()
        c.close()
        self.assertEqual(got, [("da1", "a1"), ("db1", "b1")])

    def test_run_key_conflict_is_reported_not_copied(self) -> None:
        tmp = Path(tmpdir())
        a = make(tmp / "a.db", ["a1"])
        b = make(tmp / "b.db", ["a1"])
        c = sqlite3.connect(b)
        c.execute("UPDATE run SET run_id='zz'")
        c.commit()
        c.close()
        r = runmerge.merge_runs(a, b)
        self.assertEqual((r.runs, len(r.conflicts)), (0, 1))

    def test_blobs_copied_and_checked(self) -> None:
        tmp = Path(tmpdir())
        src, dst = tmp / "bs", tmp / "bd"
        a = make(tmp / "a.db", ["a1"], dst)
        b = make(tmp / "b.db", ["b1", "b2"], src)
        r = runmerge.merge_runs(a, b, src, dst)
        self.assertEqual((r.blobs_copied, r.blobs_missing), (2, []))
        self.assertEqual(blobs.verify(dst), [])
        self.assertEqual(len(blobs.all_hashes(dst)), 3)

    def test_missing_source_blob_is_reported(self) -> None:
        tmp = Path(tmpdir())
        a = make(tmp / "a.db", ["a1"])
        b = make(tmp / "b.db", ["b1"])
        r = runmerge.merge_runs(a, b, tmp / "none", tmp / "dst")
        self.assertEqual(len(r.blobs_missing), 1)

    def test_older_schema_is_refused(self) -> None:
        tmp = Path(tmpdir())
        a = make(tmp / "a.db", ["a1"])
        b = make(tmp / "b.db", ["b1"])
        c = sqlite3.connect(b)
        c.execute("UPDATE meta SET value='6' WHERE key='schema_version'")
        c.commit()
        c.close()
        with self.assertRaises(ValueError) as ctx:
            runmerge.merge_runs(a, b)
        self.assertIn(f"needs {SCHEMA_VERSION}", str(ctx.exception))
        self.assertEqual(count(a, "run"), 1)

    def test_cli(self) -> None:
        from mimir.cli import main

        tmp = Path(tmpdir())
        a = make(tmp / "a.db", ["a1"])
        b = make(tmp / "b.db", ["b1"])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(main(["merge", "--runs", str(a), str(b)]), 0)
        self.assertIn("runs copied 1", buf.getvalue())
        self.assertIn("integrity_check: ok", buf.getvalue())
        self.assertIn("BACKUP", buf.getvalue())


class WithheldTests(unittest.TestCase):
    def _setup(self) -> tuple[Path, Path, str, str]:
        tmp = Path(tmpdir())
        root = tmp / "blobs"
        orig = blobs.put_bytes(root, b"original has SECRETNAME")
        other = blobs.put_bytes(root, b"stray has SECRETNAME")
        db = make(tmp / "a.db", ["a1"])
        c = sqlite3.connect(db)
        c.execute("INSERT INTO blob_scrub VALUES ('run_artifact','blob_sha256','a1/log',?,?)",
                  (orig, "1" * 64))
        c.commit()
        c.close()
        return db, root, orig, other

    def _check(self, db: Path | None, root: Path) -> tuple[int, str]:
        m = root.parent / "hosts.toml"
        m.write_text('[hosts]\n')
        ns = argparse.Namespace(db=[str(db)] if db else [], path=[], blobs=str(root), index=None,
                                map=str(m), max_list=50)
        buf = io.StringIO()
        env = mock.patch.dict(os.environ, {"MIMIR_PRIVATE_STRINGS": "SECRETNAME"})
        with env, contextlib.redirect_stdout(buf):
            code = _cmd_privacy_check(ns)
        return code, buf.getvalue()

    def test_scrubbed_originals_are_withheld_not_hits(self) -> None:
        db, root, orig, other = self._setup()
        self.assertEqual(privacy.scrubbed_originals([db]), {orig})
        code, out = self._check(db, root)
        self.assertEqual(code, 1)  # the stray blob is still a hit
        self.assertIn("withheld (scrubbed original, expected): 1", out)
        self.assertIn(other, out)
        self.assertNotIn(f"hit\tblob {orig}", out)
        self.assertIn("blobs 1", out)

    def test_clean_exit_when_only_withheld(self) -> None:
        db, root, orig, other = self._setup()
        c = sqlite3.connect(db)
        c.execute("UPDATE blob_scrub SET scrubbed_from=? ", (orig,))
        c.execute("INSERT INTO blob_scrub VALUES ('x','y','z',?,?)", (other, "2" * 64))
        c.commit()
        c.close()
        code, out = self._check(db, root)
        self.assertEqual(code, 0)
        self.assertIn("withheld (scrubbed original, expected): 2", out)
        self.assertIn("hits: 0", out)

    def test_without_db_behaviour_is_unchanged(self) -> None:
        _, root, orig, other = self._setup()
        code, out = self._check(None, root)
        self.assertEqual(code, 1)
        self.assertNotIn("withheld", out)
        self.assertIn("hits: 2", out)
