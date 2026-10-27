from __future__ import annotations

import hashlib
import json
import lzma
import sqlite3
import unittest
from pathlib import Path

from mimir import blobs, snapshot
from mimir.store import Store
from tests.helpers import skip_without, tmpdir
from tests.test_store import rec


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

    def test_bad_name(self) -> None:
        with self.assertRaises(ValueError):
            blobs.blob_path(Path("/x"), "../etc")


def make_store(path: Path) -> Store:
    s = Store(path)
    s.add([rec("a", "m", 0.1 + 0.2), rec("b", "m", 1e-300), rec("it's", "m", 3.0, "q'x")])
    s.db.execute("INSERT INTO design_meta VALUES ('s/a','f','v\\n''x','src','primary')")
    s.db.execute("INSERT INTO run VALUES ('r','s/a','c','t','a','',-1,'','','',NULL,2.5,NULL,NULL,"
                 "'o')")
    s.db.commit()
    return s


class SnapshotTests(unittest.TestCase):
    def test_restore_is_identical(self) -> None:
        d = Path(tmpdir())
        make_store(d / "x.db").close()
        man = snapshot.write_snapshot(d / "x.db", d / "snap")
        self.assertEqual(man["schema_version"], "2")
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
