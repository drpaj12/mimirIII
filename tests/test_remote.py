from __future__ import annotations

import hashlib
import io
import lzma
import sqlite3
import tarfile
import unittest
from pathlib import Path

from mimir import blobs, publish, remote
from mimir.licscan import load_table
from mimir.meta import load_licence_rules
from mimir.remote import Archive, Entry, FetchError, Locations
from tests.helpers import tmpdir

FILES = {
    "d/a.txt": b"alpha\n",
    "d/b.v": b"module b; // /home/someone/odin3-ws/x\nendmodule\n",
    "d/c.pdf": b"%PDF paper",
    "d/run.sh": b"echo hi\n",
    "d/net.gz": b"",
}
BLOB = b"blob content\n" * 10
SHA = hashlib.sha256


def make_tar(path: Path, link: bool = False) -> None:
    with tarfile.open(path, "w:xz") as tf:
        for name, data in FILES.items():
            if name == "d/net.gz":
                import gzip

                data = gzip.compress(b"path /home/someone/x\n")
            ti = tarfile.TarInfo(name)
            ti.size = len(data)
            tf.addfile(ti, io.BytesIO(data))
        if link:
            ln = tarfile.TarInfo("d/link")
            ln.type, ln.linkname = tarfile.SYMTYPE, "/etc/passwd"
            tf.addfile(ln)
        blob = lzma.compress(BLOB)
        bi = tarfile.TarInfo(remote.blob_member(SHA(BLOB).hexdigest()))
        bi.size = len(blob)
        tf.addfile(bi, io.BytesIO(blob))


def entries(path: Path, extra: list[Entry] | None = None) -> list[Entry]:
    out = []
    with tarfile.open(path, "r:xz") as tf:
        for ti in tf:
            if ti.isreg():
                f = tf.extractfile(ti)
                assert f is not None
                out.append(Entry(ti.name, "f", ti.size, SHA(f.read()).hexdigest()))
            else:
                out.append(Entry(ti.name, "l", 0, ti.linkname))
    return out + (extra or [])


def make_index(root: Path, tar: Path, private: bool = False, urls: tuple[str, ...] = (),
               bad_sha: bool = False, link: bool = False) -> Path:
    idx = root / "idx"
    (idx / "manifests").mkdir(parents=True)
    ents = entries(tar)
    remote.write_xz(idx / "manifests" / "t.tsv.xz", remote.manifest_text(ents))
    sha = remote.sha256_path(tar)
    arch = Archive("t", "2026-10-27", tar.name, "tar.xz", "norns-runs", "src", "manifests/t.tsv.xz",
                   "private" if private else "public", "host", "0" * 64 if bad_sha else sha,
                   tar.stat().st_size, len(ents), urls)
    (idx / "archives.toml").write_text(remote.dump_archives([arch]), encoding="utf-8")
    bsha = SHA(BLOB).hexdigest()
    remote.write_xz(idx / "blobs.tsv.xz", f"{bsha}\t10\tt\n".encode())
    return idx


def loc(root: Path, archive_dir: Path | None = None, url: str | None = None) -> Locations:
    return Locations(root / "blobs", archive_dir, url, root / "cache")


class FetchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tmpdir())
        self.arch = self.root / "arch"
        self.arch.mkdir()
        self.tar = self.arch / "t.tar.xz"
        make_tar(self.tar)

    def test_member_from_local_archive(self) -> None:
        idx = make_index(self.root, self.tar)
        out = remote.fetch_member(idx, loc(self.root, self.arch), "t", "d/a.txt",
                                  self.root / "o.txt")
        self.assertEqual(out.read_bytes(), b"alpha\n")
        cached = remote.fetch_member(idx, loc(self.root, self.arch), "t", "d/a.txt")
        self.assertIn("cache", str(cached))

    def test_mismatch_refused(self) -> None:
        idx = make_index(self.root, self.tar, bad_sha=True)
        out = self.root / "o.txt"
        with self.assertRaises(FetchError):
            remote.fetch_member(idx, loc(self.root, self.arch), "t", "d/a.txt", out)
        self.assertFalse(out.exists())

    def test_member_sha_mismatch_refused(self) -> None:
        idx = make_index(self.root, self.tar)
        rows = remote.read_manifest(idx, "manifests/t.tsv.xz")
        rows = [e._replace(sha="1" * 64) if e.path == "d/a.txt" else e for e in rows]
        remote.write_xz(idx / "manifests" / "t.tsv.xz", remote.manifest_text(rows))
        out = self.root / "o.txt"
        with self.assertRaises(FetchError):
            remote.fetch_member(idx, loc(self.root, self.arch), "t", "d/a.txt", out)
        self.assertFalse(out.exists())

    def test_blob_from_store_archive_and_sha(self) -> None:
        idx = make_index(self.root, self.tar)
        sha = SHA(BLOB).hexdigest()
        store = self.root / "blobs"
        blobs.put_bytes(store, BLOB)
        out = remote.fetch_sha(idx, loc(self.root), sha, self.root / "b1")
        self.assertEqual(out.read_bytes(), BLOB)
        out = remote.fetch_sha(idx, Locations(self.root / "none", self.arch, None,
                                              self.root / "cache"), sha, self.root / "b2")
        self.assertEqual(out.read_bytes(), BLOB)
        found = remote.fetch_sha(idx, loc(self.root, self.arch), SHA(b"alpha\n").hexdigest(),
                                 self.root / "b3")
        self.assertEqual(found.read_bytes(), b"alpha\n")

    def test_file_url(self) -> None:
        site = self.root / "site" / "2026-10-27"
        site.mkdir(parents=True)
        pub = site / "t.tar.xz"
        pub.write_bytes(self.tar.read_bytes())
        idx = make_index(self.root, pub)
        base = (self.root / "site").as_uri()
        out = remote.fetch_member(idx, loc(self.root, None, base), "t", "d/a.txt",
                                  self.root / "u.txt")
        self.assertEqual(out.read_bytes(), b"alpha\n")
        bs = self.root / "site" / "blobs"
        bsha = SHA(BLOB).hexdigest()
        (bs / bsha[:2]).mkdir(parents=True)
        (bs / bsha[:2] / f"{bsha}.xz").write_bytes(lzma.compress(BLOB))
        got = remote.fetch_sha(idx, loc(self.root, None, base), bsha, self.root / "ub")
        self.assertEqual(got.read_bytes(), BLOB)

    def test_file_url_corrupt_refused(self) -> None:
        site = self.root / "site" / "2026-10-27"
        site.mkdir(parents=True)
        (site / "t.tar.xz").write_bytes(b"not the archive")
        idx = make_index(self.root, self.tar)
        with self.assertRaises(FetchError):
            remote.fetch_member(idx, loc(self.root, None, (self.root / "site").as_uri()), "t",
                                "d/a.txt", self.root / "u.txt")

    def test_private_never_downloaded(self) -> None:
        idx = make_index(self.root, self.tar, private=True, urls=("file:///x/t.tar.xz",))
        with self.assertRaises(FetchError) as cm:
            remote.fetch_member(idx, loc(self.root, None, (self.root / "site").as_uri()), "t",
                                "d/a.txt")
        self.assertIn("private", str(cm.exception))

    def test_traversal_and_link_refused(self) -> None:
        link_tar = self.arch / "l.tar.xz"
        make_tar(link_tar, link=True)
        idx = make_index(self.root, link_tar, link=True)
        for bad in ("../x", "/etc/passwd", "d/../../x", ""):
            with self.assertRaises(FetchError):
                remote.fetch_member(idx, loc(self.root, self.arch), "t", bad)
        with self.assertRaises(FetchError):
            remote.fetch_member(idx, loc(self.root, self.arch), "t", "d/link")


class CheckTests(unittest.TestCase):
    def test_coverage_and_miss(self) -> None:
        root = Path(tmpdir())
        idx = make_index(root, self._tar(root))
        good = SHA(BLOB).hexdigest()
        db = sqlite3.connect(":memory:")
        db.execute("CREATE TABLE run_artifact (run_id TEXT, kind TEXT, blob_sha256 TEXT)")
        db.execute("CREATE TABLE partition (id TEXT, assignment_blob TEXT)")
        db.executemany("INSERT INTO run_artifact VALUES (?,?,?)",
                       [("r", "a", good), ("r", "b", "f" * 64)])
        db.execute("INSERT INTO partition VALUES ('p', '')")
        rows = {r.table: r for r in remote.remote_check(db, remote.load_blob_index(idx))}
        self.assertEqual((rows["run_artifact"].refs, rows["run_artifact"].resolved), (2, 1))
        self.assertEqual(rows["run_artifact"].missing, ("f" * 64,))
        self.assertEqual(rows["partition"].refs, 0)

    @staticmethod
    def _tar(root: Path) -> Path:
        (root / "a").mkdir()
        t = root / "a" / "t.tar.xz"
        make_tar(t)
        return t


class PublishTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tmpdir())
        (self.root / "a").mkdir()
        self.tar = self.root / "a" / "t.tar.xz"
        make_tar(self.tar)

    def test_scrub_and_drop(self) -> None:
        out = self.root / "pub.tar.xz"
        stats = publish.repack_tar(self.tar, out, [], {"NOTICE-t.txt": b"n"}, True)
        names = {e.path for e in stats.members}
        self.assertNotIn("d/c.pdf", names)
        self.assertNotIn("d/run.sh", names)
        self.assertIn("NOTICE-t.txt", names)
        self.assertEqual(sorted(stats.scrubbed), ["d/b.v", "d/net.gz"])
        with tarfile.open(out, "r:xz") as tf:
            f = tf.extractfile("d/b.v")
            assert f is not None
            text = f.read()
            self.assertIn(b"$WS/x", text)
            self.assertNotIn(b"/home/", text)
            self.assertEqual(tf.getmember("d/b.v").uname, "")

    def test_binary_with_home_dropped(self) -> None:
        new, note = publish.process_bytes("x.bin", b"\x00\x01/home/bob/x", True)
        self.assertIsNone(new)
        self.assertIn("binary", note)

    def test_plan_findings_and_refusals(self) -> None:
        idx = make_index(self.root, self.tar)
        rules = load_licence_rules(Path(__file__).resolve().parents[1] / "data/meta/licences.toml")
        arch = remote.load_archives(idx)["t"]
        ents = remote.read_manifest(idx, arch.manifest) + [Entry("d/l", "l", 0, "$HOME/x")]
        remote.write_xz(idx / arch.manifest, remote.manifest_text(ents))
        plans = publish.build_plans(idx, rules, {})
        self.assertEqual((plans[0].pdfs, plans[0].homes, plans[0].links), (1, 1, 1))
        self.assertEqual(plans[0].would_drop, 3)  # the pdf, the .sh and the link
        priv = make_index(self.root / "a", self.tar, private=True)
        pp = publish.build_plans(priv, rules, {})
        with self.assertRaises(publish.PlanError):
            publish.select(pp, ["t"], False)
        self.assertEqual(publish.select(pp, [], False), [])

    def test_pending_refused_without_flag(self) -> None:
        idx = make_index(self.root, self.tar)
        rules = load_licence_rules(Path(__file__).resolve().parents[1] / "data/meta/licences.toml")
        arch = remote.load_archives(idx)["t"]
        ents = remote.read_manifest(idx, arch.manifest) + [Entry("d/x.blif", "f", 1, "0" * 64)]
        remote.write_xz(idx / arch.manifest, remote.manifest_text(ents))
        plans = publish.build_plans(idx, rules, {})
        self.assertEqual(plans[0].licence, "pending")
        with self.assertRaises(publish.PlanError):
            publish.select(plans, ["t"], False)
        self.assertEqual(len(publish.select(plans, ["t"], True)), 1)

    def test_stage_tree(self) -> None:
        idx = make_index(self.root, self.tar)
        rdir = Path(__file__).resolve().parents[1] / "data" / "remote"
        for name in ("licences.toml",):
            (idx / name).write_bytes((rdir / name).read_bytes())
        (idx / "licence-texts").mkdir()
        for p in (rdir / "licence-texts").iterdir():
            (idx / "licence-texts" / p.name).write_bytes(p.read_bytes())
        meta = idx.parent / "meta"
        meta.mkdir()
        (meta / "licences.toml").write_bytes(
            (rdir.parent / "meta" / "licences.toml").read_bytes())
        rules = load_licence_rules(meta / "licences.toml")
        rows, _ = load_table(idx / "licences.toml")
        plans = publish.build_plans(idx, rules, rows)
        stage = self.root / "stage"
        store = self.root / "store"
        blobs.put_bytes(store, BLOB)
        blobs.put_bytes(store, b"leak /home/bob/x")
        lines = publish.run_stage(stage, self.root / "a", plans, idx, store, "https://x", True,
                                  False)
        self.assertTrue((stage / "README.txt").exists())
        self.assertTrue((stage / "2026-10-27" / "t.tar.xz").exists())
        self.assertTrue((stage / "index" / "archives.toml").exists())
        sums = (stage / "2026-10-27" / "SHA256SUMS").read_text()
        self.assertIn("t.tar.xz", sums)
        self.assertTrue(any("left out" in x for x in lines))
        shas = {p.stem for p in (stage / "blobs").glob("??/*.xz")}
        self.assertEqual(shas, {SHA(BLOB).hexdigest()})
        pub = remote.load_archives(stage / "index")["t"]
        self.assertEqual(pub.public_sha256,
                         remote.sha256_path(stage / "2026-10-27" / "t.tar.xz"))
        self.assertEqual(pub.public_dropped, 2)
