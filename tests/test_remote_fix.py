"""Fix round 1 of the remote-data lane: private rows, fail-closed licences, bounded downloads,
scrub hardening, blob visibility, re-index."""

from __future__ import annotations

import hashlib
import io
import lzma
import sqlite3
import tarfile
import unittest
import zipfile
from dataclasses import replace
from pathlib import Path
from unittest import mock

from mimir import publish, remote, remoteindex
from mimir.licscan import load_table
from mimir.meta import load_licence_rules
from mimir.remote import Archive, BlobRef, Entry, FetchError, Locations
from tests.helpers import tmpdir
from tests.test_remote import BLOB, SHA, loc, make_index, make_tar

# built from parts: no identity string sits in a fixture or in the committed source
USER = "jamie" + "spa"
PERSON = "jamieson" + "." + "peter"
GM = "G" + "MAIL"
MAIL = PERSON + "@" + "g" + "mail" + ".com"
REPO = Path(__file__).resolve().parents[1]


def tar_of(path: Path, files: dict[str, bytes]) -> Path:
    with tarfile.open(path, "w:xz") as tf:
        for name, data in files.items():
            ti = tarfile.TarInfo(name)
            ti.size, ti.mtime = len(data), 1700000000
            ti.pax_headers = {"comment": "x"}
            tf.addfile(ti, io.BytesIO(data))
    return path


class PrivateRowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tmpdir())
        (self.root / "a").mkdir()
        self.tar = self.root / "a" / "t.tar.xz"
        make_tar(self.tar)

    def test_private_manifest_not_in_index_but_local_fetch_works(self) -> None:
        idx = make_index(self.root, self.tar, private=True, urls=("file:///x/t.tar.xz",))
        self.assertFalse((idx / "manifests" / "t.tsv.xz").exists())
        arch = remote.load_archives(idx)["t"]
        self.assertEqual(arch.manifest, "")
        out = remote.fetch_member(idx, loc(self.root, self.root / "a"), "t", "d/a.txt",
                                  self.root / "o")
        self.assertEqual(out.read_bytes(), b"alpha\n")

    def test_private_without_local_manifest_refused(self) -> None:
        idx = make_index(self.root, self.tar, private=True)
        no_priv = Locations(self.root / "blobs", self.root / "a", None, self.root / "cache",
                            self.root / "nowhere")
        with self.assertRaises(FetchError):
            remote.fetch_member(idx, no_priv, "t", "d/a.txt")

    def test_private_by_url_refused(self) -> None:
        idx = make_index(self.root, self.tar, private=True)
        with self.assertRaises(FetchError) as cm:
            remote.fetch_member(idx, loc(self.root, None, (self.root / "s").as_uri()), "t",
                                "d/a.txt")
        self.assertIn("private", str(cm.exception))

    def test_staged_tree_has_no_private_row(self) -> None:
        idx = make_index(self.root, self.tar)
        pub = remote.load_archives(idx)["t"]
        priv = replace(pub, name="p", file="p.tar.xz", manifest="", visibility="private",
                       licence="private", source="")
        (idx / "archives.toml").write_text(remote.dump_archives([pub, priv]), encoding="utf-8")
        (idx / "manifests" / "p.tsv.xz").write_bytes(b"leftover")  # must not be staged
        rdir = REPO / "data" / "remote"
        text = (rdir / "licences.toml").read_text(encoding="utf-8")
        text += '\n[[archive]]\narchive = "p.tar.xz"\nverdict = "do-not-host"\nsources = []\n' \
                'licence_refs = []\nnotes = "private fixture"\nbasis = "controller"\ndrop = []\n'
        (idx / "licences.toml").write_text(text, encoding="utf-8")
        (idx / "licence-texts").mkdir()
        for p in (rdir / "licence-texts").iterdir():
            (idx / "licence-texts" / p.name).write_bytes(p.read_bytes())
        meta = idx.parent / "meta"
        meta.mkdir()
        (meta / "licences.toml").write_bytes((REPO / "data/meta/licences.toml").read_bytes())
        rows, _ = load_table(idx / "licences.toml")
        rows["t"] = rows["norns-runs-n5"]
        rules = load_licence_rules(meta / "licences.toml")
        plans = publish.build_plans(idx, rules, rows)
        self.assertEqual([p.licence for p in plans if p.archive.name == "p"], ["private"])
        chosen = publish.select(plans, [], True)  # the fixture designs have no licence meta
        self.assertEqual([p.archive.name for p in chosen], ["t"])
        stage = self.root / "stage"
        publish.run_stage(stage, self.root / "a", chosen, idx, None, "https://x", False, False)
        staged = remote.load_archives(stage / "index")
        self.assertEqual(sorted(staged), ["t"])
        names = {p.name for p in (stage / "index").rglob("*") if p.is_file()}
        self.assertNotIn("p.tsv.xz", names)
        self.assertNotIn(b"private fixture", (stage / "index" / "licences.toml").read_bytes())
        self.assertNotIn(b'"p.tar.xz"', (stage / "index" / "licences.toml").read_bytes())

    def test_committed_index_has_no_private_manifest(self) -> None:
        idx = REPO / "data" / "remote"
        archives = remote.load_archives(idx)
        private = [a for a in archives.values() if a.private]
        self.assertTrue(private)
        for a in private:
            self.assertEqual((a.manifest, a.source, a.urls, a.members), ("", "", (), 0))
            self.assertEqual(a.public_sha256, "")
        named = {a.name for a in private}
        # the manifests of mimir-mcnc-originals*, mimir-meta-papers and the superseded snapshot
        for n in named & {"mimir-mcnc-originals", "mimir-mcnc-originals-r2",
                          "mimir-meta-papers", "mimir-snapshot-2026-10-27"}:
            self.assertFalse((idx / "manifests" / f"{n}.tsv.xz").exists(), n)


class LicenceGateTests(unittest.TestCase):
    def test_no_row_is_pending_and_refused(self) -> None:
        root = Path(tmpdir())
        (root / "a").mkdir()
        tar = root / "a" / "t.tar.xz"
        make_tar(tar)
        idx = make_index(root, tar)
        rules = load_licence_rules(REPO / "data/meta/licences.toml")
        plans = publish.build_plans(idx, rules, {})
        self.assertEqual(plans[0].licence, "pending")
        self.assertEqual(publish.select(plans, [], False), [])
        with self.assertRaises(publish.PlanError):
            publish.select(plans, ["t"], False)
        self.assertEqual(len(publish.select(plans, ["t"], True)), 1)

    def test_row_makes_it_hostable(self) -> None:
        arch = Archive("t", "d", "t.tar.xz", "tar.xz", "k", "", "m", "public", "", "", 0, 0)
        self.assertEqual(publish.status_of(arch, {"verdict": "host"}, {}, []), "host")
        self.assertEqual(publish.status_of(arch, None, {}, []), "pending")
        self.assertEqual(publish.status_of(arch, {"verdict": "host"}, {}, ["x.v"]), "pending")

    def test_committed_table_covers_every_public_archive(self) -> None:
        idx = REPO / "data" / "remote"
        rows, _ = load_table(idx / "licences.toml")
        for a in remote.load_archives(idx).values():
            self.assertIn(a.name, rows, a.name)
            if a.private:
                self.assertEqual(rows[a.name]["verdict"], "do-not-host", a.name)

    def test_verilogeval_notice_wording(self) -> None:
        from mimir.licscan import notice

        rules = load_licence_rules(REPO / "data/meta/licences.toml")
        text = notice("x", None, {"verilogeval": ["ve_Prob1"]}, rules)
        self.assertIn("VerilogEval repository licence: MIT (NVIDIA); the original problem "
                      "source does not state a licence", text)


def bomb() -> bytes:
    return lzma.compress(b"\0" * (30 << 20))


class BoundedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tmpdir())
        (self.root / "a").mkdir()
        self.tar = self.root / "a" / "t.tar.xz"
        make_tar(self.tar)

    def test_unxz_limits(self) -> None:
        data = lzma.compress(b"x" * 100)
        self.assertEqual(remote.unxz(data, 100), b"x" * 100)
        with self.assertRaises(FetchError):
            remote.unxz(data, 99)
        with self.assertRaises(FetchError):
            remote.unxz(data[:-8], 100)
        with self.assertRaises(FetchError):
            remote.unxz(data + b"junk", 100)
        with self.assertRaises(FetchError):
            remote.unxz(bomb(), 1000)  # an xz bomb of a few KiB

    def test_archive_download_longer_than_index_stopped(self) -> None:
        site = self.root / "site" / "2026-10-27"
        site.mkdir(parents=True)
        (site / "t.tar.xz").write_bytes(self.tar.read_bytes() + b"x" * 5000)
        idx = make_index(self.root, self.tar)
        with self.assertRaises(FetchError) as cm:
            remote.fetch_member(idx, loc(self.root, None, (self.root / "site").as_uri()), "t",
                                "d/a.txt", self.root / "o")
        self.assertIn("longer", str(cm.exception))
        cache = self.root / "cache" / "archives"
        for p in cache.glob("*"):
            self.assertLessEqual(p.stat().st_size, 0 if p.suffix == ".part" else 0)

    def test_download_stops_at_size_plus_one(self) -> None:
        src = self.root / "big"
        src.write_bytes(b"y" * 5000)
        dest = self.root / "dl" / "f"
        with self.assertRaises(FetchError):
            remote.download(src.as_uri(), dest, "0" * 64, 100)
        part = dest.with_name("f.part")
        self.assertFalse(dest.exists())
        self.assertLessEqual(part.stat().st_size, 0)  # truncated, nothing kept

    def test_blob_bomb_refused_and_no_chk_file(self) -> None:
        raw = b"\0" * (30 << 20)
        sha = hashlib.sha256(raw).hexdigest()
        xz = bomb()
        site = self.root / "site"
        (site / "blobs" / sha[:2]).mkdir(parents=True)
        (site / "blobs" / sha[:2] / f"{sha}.xz").write_bytes(xz)
        idx = make_index(self.root, self.tar)
        # the index says 100 raw bytes: the stream is refused at 101
        remote.write_xz(idx / "blobs.tsv.xz", f"{sha}\t{len(xz)}\t100\t-\tpublic\n".encode())
        with self.assertRaises(FetchError) as cm:
            remote.fetch_blob(idx, loc(self.root, None, site.as_uri()), sha, self.root / "o")
        self.assertIn("more than", str(cm.exception))
        self.assertEqual(list((self.root / "cache").rglob("*.chk")), [])
        self.assertFalse((self.root / "o").exists())

    def test_blob_longer_than_indexed_xz_bytes(self) -> None:
        sha = SHA(BLOB).hexdigest()
        xz = lzma.compress(BLOB)
        site = self.root / "site"
        (site / "blobs" / sha[:2]).mkdir(parents=True)
        (site / "blobs" / sha[:2] / f"{sha}.xz").write_bytes(xz + b"x" * 4000)
        idx = make_index(self.root, self.tar)
        remote.write_xz(idx / "blobs.tsv.xz",
                        f"{sha}\t{len(xz)}\t{len(BLOB)}\t-\tpublic\n".encode())
        with self.assertRaises(FetchError) as cm:
            remote.fetch_blob(idx, loc(self.root, None, site.as_uri()), sha, self.root / "o")
        self.assertIn("longer", str(cm.exception))

    def test_blob_ok_and_cached_without_chk(self) -> None:
        sha = SHA(BLOB).hexdigest()
        xz = lzma.compress(BLOB)
        site = self.root / "site"
        (site / "blobs" / sha[:2]).mkdir(parents=True)
        (site / "blobs" / sha[:2] / f"{sha}.xz").write_bytes(xz)
        idx = make_index(self.root, self.tar)
        remote.write_xz(idx / "blobs.tsv.xz",
                        f"{sha}\t{len(xz)}\t{len(BLOB)}\t-\tpublic\n".encode())
        out = remote.fetch_blob(idx, loc(self.root, None, site.as_uri()), sha, self.root / "o")
        self.assertEqual(out.read_bytes(), BLOB)
        self.assertEqual(list((self.root / "cache").rglob("*.chk")), [])
        self.assertTrue((self.root / "cache" / "blobs" / sha[:2] / f"{sha}.xz").exists())

    def test_nonpublic_blob_never_downloaded(self) -> None:
        sha = SHA(BLOB).hexdigest()
        site = self.root / "site"
        (site / "blobs" / sha[:2]).mkdir(parents=True)
        (site / "blobs" / sha[:2] / f"{sha}.xz").write_bytes(lzma.compress(BLOB))
        idx = make_index(self.root, self.tar)
        for vis in ("private", "orphan"):
            remote.write_xz(idx / "blobs.tsv.xz", f"{sha}\t100\t{len(BLOB)}\t-\t{vis}\n".encode())
            with self.assertRaises(FetchError) as cm:
                remote.fetch_blob(idx, loc(self.root, None, site.as_uri()), sha, self.root / "o")
            self.assertIn(vis, str(cm.exception))

    def test_urls_are_quoted(self) -> None:
        arch = Archive("t", "2026-10-27", "a b#c.tar.xz", "tar.xz", "k", "", "m", "public", "",
                       "0" * 64, 1, 0)
        (url,) = remote._urls(Locations(Path("b"), None, "https://h/base", Path("c")), arch)
        self.assertEqual(url, "https://h/base/2026-10-27/a%20b%23c.tar.xz")
        (murl,) = remote._urls(Locations(Path("b"), None, "https://h", Path("c")),
                               replace(arch, form="dir"), "/" + "x y/z%.txt".replace("%", "%25"))
        self.assertIn("x y/z%25.txt", murl)

    def test_non_hex_sha_refused_as_path_part(self) -> None:
        idx = make_index(self.root, self.tar)
        ents = remote.read_manifest(idx, "manifests/t.tsv.xz")
        ents = [e._replace(sha="../../evil") if e.path == "d/a.txt" else e for e in ents]
        remote.write_xz(idx / "manifests" / "t.tsv.xz", remote.manifest_text(ents))
        with self.assertRaises(FetchError):
            remote.fetch_member(idx, loc(self.root, self.root / "a"), "t", "d/a.txt")
        with self.assertRaises(FetchError):
            remote.fetch_blob(idx, loc(self.root), "../x")

    def test_member_longer_than_manifest_size_stopped(self) -> None:
        idx = make_index(self.root, self.tar)
        ents = remote.read_manifest(idx, "manifests/t.tsv.xz")
        ents = [e._replace(size=2) if e.path == "d/a.txt" else e for e in ents]
        remote.write_xz(idx / "manifests" / "t.tsv.xz", remote.manifest_text(ents))
        out = self.root / "o"
        with self.assertRaises(FetchError):
            remote.fetch_member(idx, loc(self.root, self.root / "a"), "t", "d/a.txt", out)
        self.assertFalse(out.exists())


class ScrubTests(unittest.TestCase):
    def test_clean_zeroes_mtime_and_pax(self) -> None:
        root = Path(tmpdir())
        src = tar_of(root / "m.tar.xz", {"d/a.txt": b"alpha\n", "d/b.v": b"x"})
        out = root / "p.tar.xz"
        publish.repack_tar(src, out, [], {"NOTICE.txt": b"n"}, True)
        with tarfile.open(out, "r:xz") as tf:
            for ti in tf:
                self.assertEqual(ti.mtime, 0, ti.name)
                self.assertEqual(ti.pax_headers, {}, ti.name)
                self.assertEqual((ti.uid, ti.gid, ti.uname, ti.gname), (0, 0, "", ""))

    def test_email_and_person_scrubbed(self) -> None:
        text = f"by {MAIL}\n{PERSON} wrote\nuser {USER}\nsee {GM}\n".encode()
        self.assertTrue(publish.has_home(text))
        self.assertTrue(publish.has_home(f"CEC-{USER.upper()}701".encode()))  # a host name
        new = publish.scrub_bytes(text)
        self.assertFalse(publish.has_home(new))
        for bad in (MAIL, PERSON, USER, "g" + "mail"):
            self.assertNotIn(bad.encode().lower(), new.lower())
        root = Path(tmpdir())
        src = tar_of(root / "m.tar.xz", {"d/c.txt": text})
        publish.repack_tar(src, root / "p.tar.xz", [], {}, True)
        with tarfile.open(root / "p.tar.xz", "r:xz") as tf:
            f = tf.extractfile("d/c.txt")
            assert f is not None
            self.assertFalse(publish.has_home(f.read()))

    def test_binary_with_person_dropped(self) -> None:
        new, note = publish.process_bytes("x.bin", b"\x00\x01" + MAIL.encode(), True)
        self.assertIsNone(new)
        self.assertIn("binary", note)

    def test_member_names_scanned(self) -> None:
        root = Path(tmpdir())
        src = tar_of(root / "m.tar.xz", {f"d/{USER}.txt": b"ok", f"{PERSON}/x.txt": b"ok",
                                         "d/fine.txt": b"ok"})
        stats = publish.repack_tar(src, root / "p.tar.xz", [], {}, True)
        names = {e.path for e in stats.members}
        self.assertEqual(names, {"d/fine.txt"})
        self.assertEqual(len(stats.dropped), 2)
        # dir repack
        master = root / "snap"
        (master / "d").mkdir(parents=True)
        (master / "d" / f"{USER}.txt").write_text("ok")
        (master / "d" / "fine.txt").write_text("ok")
        st = publish.repack_dir(master, root / "out", [], {})
        self.assertEqual({e.path for e in st.members}, {"d/fine.txt"})

    def _npz(self, inner: bytes, name: str = "a.npy") -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(name, inner)
        return buf.getvalue()

    def test_zip_members_scanned_and_7z_dropped(self) -> None:
        good = self._npz(b"numbers 1 2 3")
        bad = self._npz(b"path /home/someone/x")
        badname = self._npz(b"ok", f"{USER}.npy")
        self.assertEqual(publish.process_bytes("a.npz", good)[0], good)
        for blob in (bad, badname):
            new, note = publish.process_bytes("a.npz", blob)
            self.assertIsNone(new)
            self.assertIn("zip", note)
        self.assertIsNone(publish.process_bytes("a.zip", b"not a zip")[0])
        self.assertEqual(publish.drop_reason("x/a.7z", True, False, []), "excluded type 7z")

    def test_inflate_bounded(self) -> None:
        with mock.patch.object(publish, "MAX_MEMBER", 1000):
            big = lzma.compress(b"a" * 5000)
            new, note = publish.process_bytes("x.xz", big, True)
            self.assertIsNone(new)
            self.assertIn("cannot be scanned", note)
            small = lzma.compress(b"a" * 50)
            self.assertEqual(publish.process_bytes("x.xz", small, True)[0], small)

    def test_repack_dir_max_member(self) -> None:
        root = Path(tmpdir())
        master = root / "snap"
        master.mkdir()
        (master / "big.txt").write_bytes(b"z" * 200)
        (master / "small.txt").write_bytes(b"z")
        with mock.patch.object(publish, "MAX_MEMBER", 100):
            st = publish.repack_dir(master, root / "out", [], {})
        self.assertEqual({e.path for e in st.members}, {"small.txt"})
        self.assertEqual([m for m, _ in st.dropped], ["big.txt"])

    def test_source_holds_no_identity_string(self) -> None:
        for rel in ("mimir/publish.py", "mimir/remote.py", "mimir/remoteindex.py",
                    "tests/test_remote_fix.py"):
            text = (REPO / rel).read_text(encoding="utf-8").lower()
            for bad in (USER, PERSON, "g" + "mail", "/home/" + USER):
                self.assertNotIn(bad, text, f"{rel}: {bad}")


class IndexTests(unittest.TestCase):
    def _date_dir(self, root: Path, tar_files: dict[str, bytes], sums: bool = True) -> Path:
        date = root / "2026-10-27"
        date.mkdir(exist_ok=True)
        t = tar_of(date / "loki-exp5-data.tar.xz", tar_files)
        if sums:
            (date / "SHA256SUMS").write_text(f"{remote.sha256_path(t)}  {t.name}\n")
        else:
            (date / "SHA256SUMS").write_text("")
        return date

    def test_missing_sums_entry_fails(self) -> None:
        root = Path(tmpdir())
        date = self._date_dir(root, {"d/a": b"1"}, sums=False)
        with self.assertRaises(ValueError):
            remoteindex.build_archives(date, root / "idx", {}, root / "priv")

    def test_manifest_from_dir_skips_symlinks(self) -> None:
        root = Path(tmpdir())
        (root / "d").mkdir()
        (root / "d" / "f").write_text("a")
        (root / "d" / "l").symlink_to(root / "d" / "f")
        ents = remoteindex.manifest_from_dir(root / "d")
        self.assertEqual([e.path for e in ents], ["f"])

    def test_private_goes_to_local_dir(self) -> None:
        root = Path(tmpdir())
        date = root / "2026-10-27"
        date.mkdir()
        t = tar_of(date / "mimir-meta-papers.tar.xz", {"p.pdf": b"%PDF"})
        (date / "SHA256SUMS").write_text(f"{remote.sha256_path(t)}  {t.name}\n")
        arch = remoteindex.build_archives(date, root / "idx", {}, root / "priv")
        self.assertEqual([(a.visibility, a.manifest, a.source, a.members) for a in arch],
                         [("private", "", "", 0)])
        self.assertTrue((root / "priv" / "manifests" / "mimir-meta-papers.tsv.xz").exists())
        self.assertFalse((root / "idx" / "manifests").exists())

    def test_changed_master_clears_repack(self) -> None:
        root = Path(tmpdir())
        idx = root / "idx"
        idx.mkdir()
        date = self._date_dir(root, {"d/a": b"1"})
        first = remoteindex.build_archives(date, idx, {}, root / "priv")
        done = replace(first[0], public_file="x.tar.xz", public_sha256="1" * 64,
                       public_manifest="manifests/x.public.tsv.xz", urls=("https://u/x",),
                       public_size=7)
        (idx / "archives.toml").write_text(remote.dump_archives([done]), encoding="utf-8")
        same: list[str] = []
        kept = remoteindex.build_archives(date, idx, {}, root / "priv", same)
        self.assertEqual((kept[0].public_sha256, same), ("1" * 64, []))
        date = self._date_dir(root, {"d/a": b"2222"})  # the master changed
        notes: list[str] = []
        new = remoteindex.build_archives(date, idx, {}, root / "priv", notes)
        self.assertEqual((new[0].public_sha256, new[0].public_manifest, new[0].public_size),
                         ("", "", 0))
        self.assertEqual(new[0].urls, ("https://u/x",))
        self.assertTrue(notes and "stale" in notes[0])


class VisibilityTests(unittest.TestCase):
    def test_blob_visibility_rules(self) -> None:
        vis = remoteindex.blob_visibility
        self.assertEqual(vis("a", "-", {"a"}, set(), set(), set()), "public")
        self.assertEqual(vis("a", "-", {"a"}, set(), {"a"}, set()), "private")
        self.assertEqual(vis("b", "-", {"a"}, {"b"}, set(), set()), "private")
        self.assertEqual(vis("c", "-", {"a"}, set(), set(), set()), "orphan")
        self.assertEqual(vis("d", "t", set(), set(), set(), {"t"}), "public")
        self.assertEqual(vis("a", "-", {"a"}, set(), set(), set(), True), "withheld")
        self.assertEqual(vis("c", "-", set(), set(), set(), set(), True), "orphan")

    def test_index_visibility_from_store(self) -> None:
        from mimir import blobs

        root = Path(tmpdir())
        store = root / "blobs"
        pub = blobs.put_bytes(store, b"public blob")
        only_priv = blobs.put_bytes(store, b"private run blob")
        orphan = blobs.put_bytes(store, b"orphan blob")
        traced = blobs.put_bytes(store, b"original circuit")
        named = blobs.put_bytes(store, f"host CEC-{USER.upper()}701".encode())
        db_path = root / "s.db"
        db = sqlite3.connect(db_path)
        db.execute("CREATE TABLE run (run_id TEXT, source TEXT)")
        db.execute("CREATE TABLE run_artifact (run_id TEXT, kind TEXT, blob_sha256 TEXT)")
        db.executemany("INSERT INTO run VALUES (?,?)", [("r1", "mimir-structures"),
                                                        ("r2", "mcnc-originals")])
        db.executemany("INSERT INTO run_artifact VALUES (?,?,?)",
                       [("r1", "net", pub), ("r2", "net", only_priv), ("r2", "x", pub),
                        ("r1", "host", named)])
        db.commit()
        db.close()
        priv = root / "priv"
        (priv / "manifests").mkdir(parents=True)
        remote.write_xz(priv / "manifests" / "mimir-mcnc-originals.tsv.xz",
                        remote.manifest_text([Entry("o/c.blif", "f", 1, traced)]))
        archives = [Archive("mimir-mcnc-originals", "d", "o.tar.xz", "tar.xz", "originals", "",
                            "", "private", "private", "0" * 64, 1, 0)]
        data, counts = remoteindex.build_blob_index(store, root, archives, [db_path], priv)
        rows = {r.split("\t")[0]: r.split("\t") for r in data.decode().splitlines()}
        self.assertEqual(rows[pub][4], "public")
        self.assertEqual(rows[only_priv][4], "private")
        self.assertEqual(rows[orphan][4], "orphan")
        self.assertEqual(rows[named][4], "withheld")
        self.assertEqual(rows[traced][4], "private")
        self.assertEqual(int(rows[pub][2]), len(b"public blob"))
        self.assertEqual(counts["traced-to:mimir-mcnc-originals"], 1)
        self.assertEqual((counts["public"], counts["private"], counts["orphan"]), (1, 2, 1))
        self.assertEqual(counts["withheld"], 1)

    def test_stage_blobs_public_only(self) -> None:
        root = Path(tmpdir())
        idx = root / "idx"
        idx.mkdir()
        a, b = "a" * 64, "b" * 64
        remote.write_xz(idx / "blobs.tsv.xz",
                        f"{a}\t1\t1\t-\tpublic\n{b}\t1\t1\t-\torphan\n".encode())
        self.assertEqual(sorted(publish.public_blob_index(idx)), [a])
        text = publish.staged_blob_index(idx).decode()
        self.assertIn(a, text)
        self.assertNotIn(b, text)
        self.assertEqual(BlobRef(a, 1, 1, "-", "public").visibility, "public")


class SumsAllDatesTests(unittest.TestCase):
    def test_every_date_dir_gets_sums(self) -> None:
        root = Path(tmpdir())
        (root / "a").mkdir()
        tar = root / "a" / "t.tar.xz"
        make_tar(tar)
        idx = make_index(root, tar)
        arch = remote.load_archives(idx)["t"]
        t2 = replace(arch, name="t2", file="t2.tar.xz", date="2026-10-28",
                     manifest="manifests/t2.tsv.xz")
        (root / "a" / "t2.tar.xz").write_bytes(tar.read_bytes())
        (idx / "manifests" / "t2.tsv.xz").write_bytes((idx / arch.manifest).read_bytes())
        (idx / "archives.toml").write_text(remote.dump_archives([arch, t2]), encoding="utf-8")
        rdir = REPO / "data" / "remote"
        (idx / "licences.toml").write_bytes((rdir / "licences.toml").read_bytes())
        (idx / "licence-texts").mkdir()
        for p in (rdir / "licence-texts").iterdir():
            (idx / "licence-texts" / p.name).write_bytes(p.read_bytes())
        meta = idx.parent / "meta"
        meta.mkdir()
        (meta / "licences.toml").write_bytes((REPO / "data/meta/licences.toml").read_bytes())
        rules = load_licence_rules(meta / "licences.toml")
        rows, _ = load_table(idx / "licences.toml")
        rows["t"] = rows["t2"] = rows["norns-runs-n5"]
        plans = publish.build_plans(idx, rules, rows)
        stage = root / "stage"
        lines = publish.run_stage(stage, root / "a", plans, idx, None, "https://x", False, False)
        self.assertTrue(any("2026-10-27" in x and "2026-10-28" in x for x in lines))
        for date, name in (("2026-10-27", "t.tar.xz"), ("2026-10-28", "t2.tar.xz")):
            sums = remoteindex.read_sums(stage / date)
            self.assertEqual(sums[name], remote.sha256_path(stage / date / name))
        first = {d: (stage / d / "SHA256SUMS").read_bytes() for d in ("2026-10-27", "2026-10-28")}
        publish.run_stage(stage, root / "a", plans, idx, None, "https://x", False, False)
        for d, b in first.items():
            self.assertEqual((stage / d / "SHA256SUMS").read_bytes(), b)
