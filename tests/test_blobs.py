from __future__ import annotations

import hashlib
import json
import lzma
import os
import sqlite3
import unittest
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest import mock

from mimir import blobs, snapshot
from mimir.store import Store
from tests.helpers import skip_without, tmpdir
from tests.test_store import rec

PathArg = str | os.PathLike[str]


class BlobTests(unittest.TestCase):
    def test_put_get_verify(self) -> None:
        root = Path(tmpdir())
        data = b"hello blob\n" * 100
        sha = blobs.put_bytes(root, data)
        self.assertEqual(sha, hashlib.sha256(data).hexdigest())
        self.assertEqual(blobs.put_bytes(root, data), sha)
        path = blobs.blob_path(root, sha)
        self.assertEqual(path, root / sha[:2] / f"{sha}.xz")
        self.assertLess(path.stat().st_size, len(data))
        self.assertEqual(blobs.get_bytes(root, sha), data)
        self.assertEqual(blobs.verify(root), [])
        self.assertEqual(blobs.all_hashes(root), [sha])

    def test_corrupt_blob_is_found(self) -> None:
        root = Path(tmpdir())
        sha = blobs.put_bytes(root, b"abc")
        other = blobs.put_bytes(root, b"abd")
        blobs.blob_path(root, sha).write_bytes(lzma.compress(b"abd"))  # wrong content for name
        problems = blobs.verify(root)
        self.assertEqual(len(problems), 1)
        self.assertTrue(problems[0].startswith(sha))
        self.assertEqual(blobs.verify(root, [other]), [])

    def test_put_repairs_a_corrupt_existing_blob(self) -> None:
        root = Path(tmpdir())
        sha = blobs.put_bytes(root, b"abc")
        blobs.blob_path(root, sha).write_bytes(lzma.compress(b"not abc"))
        self.assertEqual(len(blobs.verify(root)), 1)
        self.assertEqual(blobs.put_bytes(root, b"abc"), sha)
        self.assertEqual(blobs.verify(root), [])
        blobs.blob_path(root, sha).write_bytes(b"garbage")
        blobs.put_bytes(root, b"abc")
        self.assertEqual(blobs.get_bytes(root, sha), b"abc")

    def test_name_must_fully_match(self) -> None:
        sha = "a" * 64
        with self.assertRaises(ValueError):
            blobs.blob_path(Path("/x"), sha + "\n")
        self.assertEqual(blobs.blob_path(Path("/x"), sha).name, f"{sha}.xz")

    def test_temp_file_is_removed_when_the_rename_fails(self) -> None:
        root = Path(tmpdir())
        with mock.patch.object(os, "replace", side_effect=OSError("disk")), \
                self.assertRaises(OSError):
            blobs.put_bytes(root, b"abc")
        self.assertEqual([p.name for p in root.glob("*/.put-*")], [])
        self.assertEqual(blobs.put_bytes(root, b"abc"), hashlib.sha256(b"abc").hexdigest())
        self.assertEqual([p.name for p in root.glob("*/.put-*")], [])

    def test_fsync_before_rename(self) -> None:
        root = Path(tmpdir())
        order: list[str] = []
        real_fsync, real_replace = os.fsync, os.replace

        def fsync(fd: int) -> None:
            order.append("fsync")
            real_fsync(fd)

        def replace(a: PathArg, b: PathArg) -> None:
            order.append("replace")
            real_replace(a, b)

        with mock.patch.object(os, "fsync", fsync), mock.patch.object(os, "replace", replace):
            blobs.put_bytes(root, b"abc")
        self.assertEqual(order, ["fsync", "replace"])

    def test_verify_empty_list_checks_none_and_none_checks_all(self) -> None:
        root = Path(tmpdir())
        sha = blobs.put_bytes(root, b"abc")
        blobs.blob_path(root, sha).write_bytes(lzma.compress(b"zzz"))
        self.assertEqual(blobs.verify(root, []), [])
        self.assertEqual(len(blobs.verify(root, None)), 1)
        self.assertEqual(len(blobs.verify(root)), 1)

    def test_bad_name(self) -> None:
        with self.assertRaises(ValueError):
            blobs.blob_path(Path("/x"), "../etc")


def make_store(path: Path) -> Store:
    s = Store(path)
    s.add([rec("a", "m", 0.1 + 0.2), rec("b", "m", 1e-300), rec("it's", "m", 3.0, "q'x")])
    s.db.execute("INSERT INTO design_meta VALUES ('s/a','f','v\\n''x','src','primary')")
    s.db.execute("INSERT INTO run (run_id, slug, config_hash, source, design, arch, seed, arm, "
                 "family, tool_commits, time_s, origin) "
                 "VALUES ('r','s/a','c','t','a','',-1,'','','',2.5,'o')")
    s.db.commit()
    return s


class SnapshotTests(unittest.TestCase):
    def test_restore_is_identical(self) -> None:
        d = Path(tmpdir())
        make_store(d / "x.db").close()
        man = snapshot.write_snapshot(d / "x.db", d / "snap")
        self.assertEqual(man["schema_version"], "7")
        self.assertEqual(snapshot.verify_snapshot(d / "x.db", d / "snap", d / "r.db"), [])
        a, b = sqlite3.connect(d / "x.db"), sqlite3.connect(d / "r.db")
        self.assertEqual(snapshot.canonical_lines(a), snapshot.canonical_lines(b))
        self.assertEqual(b.execute("SELECT value FROM records WHERE design='a'").fetchone()[0],
                         0.1 + 0.2)

    def test_two_snapshots_have_same_manifest_hashes(self) -> None:
        d = Path(tmpdir())
        make_store(d / "x.db").close()
        m1 = snapshot.write_snapshot(d / "x.db", d / "s1")
        m2 = snapshot.write_snapshot(d / "x.db", d / "s2")
        self.assertEqual(m1["canonical_sha256"], m2["canonical_sha256"])

    def test_difference_is_reported(self) -> None:
        d = Path(tmpdir())
        s = make_store(d / "x.db")
        snapshot.write_snapshot(d / "x.db", d / "snap")
        s.add([rec("zz", "m", 9.0)])
        s.close()
        problems = snapshot.verify_snapshot(d / "x.db", d / "snap", d / "r.db")
        self.assertTrue(problems)

    def test_manifest_lists_blobs_and_verify_reports_missing_ones(self) -> None:
        d = Path(tmpdir())
        s = make_store(d / "x.db")
        sha = blobs.put_bytes(d / "blobs", b"assignment")
        s.db.execute("INSERT INTO partition (partition_id, algorithm, algorithm_version, params, "
                     "seed, slug, input_hash, n_objects, n_clusters, assignment_blob, origin) "
                     "VALUES ('p','a','1','{}',1,'s/a','h',1,1,?, 'o')", (sha,))
        s.db.commit()
        s.close()
        man = snapshot.write_snapshot(d / "x.db", d / "snap")
        self.assertEqual(man["blob_refs"], [sha])
        ok = snapshot.verify_snapshot(d / "x.db", d / "snap", d / "r1.db", d / "blobs")
        self.assertEqual(ok, [])
        empty = Path(tmpdir())
        bad = snapshot.verify_snapshot(d / "x.db", d / "snap", d / "r2.db", empty)
        self.assertEqual(len(bad), 1)
        self.assertIn(f"blob {sha} missing", bad[0])

    def test_schema_is_part_of_the_canonical_text(self) -> None:
        d = Path(tmpdir())
        s = make_store(d / "x.db")
        snapshot.write_snapshot(d / "x.db", d / "snap")
        s.db.execute("CREATE INDEX extra_idx ON design_meta(value)")
        s.db.commit()
        s.close()
        problems = snapshot.verify_snapshot(d / "x.db", d / "snap", d / "r.db", d / "none")
        self.assertTrue(any("canonical text differs" in p for p in problems), problems)

    def test_one_read_transaction_covers_the_dump(self) -> None:
        d = Path(tmpdir())
        make_store(d / "x.db").close()
        outcome: list[str] = []
        real = snapshot.iter_dump

        def spying(db: sqlite3.Connection) -> Iterator[str]:
            for i, line in enumerate(real(db)):
                if i == 5:  # in the middle of the dump, another connection tries to write
                    other = sqlite3.connect(d / "x.db", timeout=0.05)
                    try:
                        other.execute("UPDATE meta SET value = value")
                        other.commit()
                        outcome.append("wrote")
                    except sqlite3.OperationalError:
                        outcome.append("locked")
                    finally:
                        other.close()
                yield line

        with mock.patch.object(snapshot, "iter_dump", spying):
            snapshot.write_snapshot(d / "x.db", d / "snap")
        self.assertEqual(outcome, ["locked"])

    def test_failure_leaves_no_manifest_and_closes_the_db(self) -> None:
        d = Path(tmpdir())
        make_store(d / "x.db").close()
        closed: list[bool] = []
        real = sqlite3.connect

        class Spy(sqlite3.Connection):
            def close(self) -> None:
                closed.append(True)
                super().close()

        def connect(database: str, **kw: Any) -> sqlite3.Connection:
            return real(database, factory=Spy, **kw)

        with mock.patch("sqlite3.connect", connect), \
                mock.patch.object(snapshot, "canonical_sha256", side_effect=RuntimeError("x")), \
                self.assertRaises(RuntimeError):
            snapshot.write_snapshot(d / "x.db", d / "snap")
        self.assertEqual(closed, [True])
        self.assertFalse((d / "snap" / "MANIFEST.json").exists())

    def test_manifest_is_the_last_file_written(self) -> None:
        d = Path(tmpdir())
        make_store(d / "x.db").close()
        seen: list[str] = []
        real = os.replace

        def replace(a: PathArg, b: PathArg) -> None:
            seen.append(Path(b).name)
            real(a, b)

        with mock.patch.object(os, "replace", replace):
            snapshot.write_snapshot(d / "x.db", d / "snap")
        self.assertEqual(seen, ["mimir.sql.xz", "MANIFEST.json"])

    @skip_without("pyarrow")
    def test_parquet(self) -> None:
        d = Path(tmpdir())
        make_store(d / "x.db").close()
        man = snapshot.write_snapshot(d / "x.db", d / "snap", parquet=True)
        files = man["parquet"]
        assert isinstance(files, dict)
        self.assertTrue((d / "snap" / files["records"]).is_file())
        json.loads((d / "snap" / "MANIFEST.json").read_text())


if __name__ == "__main__":
    unittest.main()
