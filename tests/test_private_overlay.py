"""A local-only archives.toml in the private index dir is merged at load and never written back."""

from __future__ import annotations

import hashlib
import lzma
import unittest
from pathlib import Path

from mimir import remote
from mimir.remote import Entry, FetchError, Locations, manifest_text, write_xz
from tests.helpers import tmpdir

DATA = b"module m; endmodule\n"
SHA = hashlib.sha256(DATA).hexdigest()
ROW = (
    '[[archive]]\nname = "local-set"\ndate = "2026-01-01"\nfile = "set-dir"\nform = "dir"\n'
    'kind = "local"\nsource = ""\nmanifest = ""\nvisibility = "private"\nlicence = "private"\n'
    'sha256 = ""\nsize = 0\nmembers = 1\n'
)


def committed_index(root: Path) -> Path:
    idx = root / "idx"
    idx.mkdir()
    (idx / "archives.toml").write_text("", encoding="utf-8")
    write_xz(idx / "blobs.tsv.xz", b"")
    return idx


def private_index(root: Path) -> Path:
    priv = root / "priv"
    (priv / "manifests").mkdir(parents=True)
    (priv / "archives.toml").write_text(ROW, encoding="utf-8")
    entries = [Entry("a/m.v", "f", len(DATA), SHA)]
    data = lzma.compress(manifest_text(entries))
    (priv / "manifests" / "local-set.tsv.xz").write_bytes(data)
    return priv


class OverlayTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tmpdir())
        self.idx = committed_index(self.root)
        self.priv = private_index(self.root)
        (self.root / "store" / "set-dir" / "a").mkdir(parents=True)
        (self.root / "store" / "set-dir" / "a" / "m.v").write_bytes(DATA)

    def loc(self) -> Locations:
        return Locations(self.root / "blobs", self.root / "store", None, self.root / "cache",
                         self.priv)

    def test_merged_lists_overlay_and_plain_load_does_not(self) -> None:
        merged = remote.load_archives_merged(self.idx, self.priv)
        self.assertIn("local-set", merged)
        self.assertTrue(merged["local-set"].private)
        self.assertNotIn("local-set", remote.load_archives(self.idx))

    def test_absent_overlay_is_plain(self) -> None:
        empty = self.root / "empty"
        empty.mkdir()
        self.assertEqual(remote.load_archives_merged(self.idx, empty), {})

    def test_fetch_member_from_local_path(self) -> None:
        out = self.root / "out.v"
        remote.fetch_member(self.idx, self.loc(), "local-set", "a/m.v", out)
        self.assertEqual(out.read_bytes(), DATA)

    def test_fetch_by_sha(self) -> None:
        out = self.root / "out2.v"
        remote.fetch_sha(self.idx, self.loc(), SHA, out)
        self.assertEqual(out.read_bytes(), DATA)

    def test_committed_name_clash_refused(self) -> None:
        (self.idx / "archives.toml").write_text(ROW, encoding="utf-8")
        with self.assertRaises(ValueError):
            remote.load_archives_merged(self.idx, self.priv)

    def test_overlay_is_forced_private_and_has_no_url(self) -> None:
        text = ROW.replace('"private"\nlicence', '"public"\nlicence', 1)
        text += 'urls = ["https://example.invalid/x"]\n'
        (self.priv / "archives.toml").write_text(text, encoding="utf-8")
        arch = remote.load_archives_merged(self.idx, self.priv)["local-set"]
        self.assertTrue(arch.private)
        self.assertEqual(arch.urls, ())

    def test_missing_member_fails(self) -> None:
        with self.assertRaises(FetchError):
            remote.fetch_member(self.idx, self.loc(), "local-set", "a/none.v", self.root / "o")


if __name__ == "__main__":
    unittest.main()
