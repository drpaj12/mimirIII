from __future__ import annotations

import contextlib
import hashlib
import io
import lzma
import os
import unittest
from pathlib import Path
from unittest import mock

from mimir import bench, benchpub, blobs, remote
from mimir.cli import main
from tests.helpers import tmpdir
from tests.test_bench import BLIF, make_world, register

ROOT = Path(__file__).resolve().parent.parent
META = ROOT / "data" / "meta" / "licences.toml"


def world(hosting: str = "public") -> tuple[Path, Path, Path, str]:
    """(index, store, stage, sha) with one registered netlist of design alpha."""
    idx, ext, store = make_world(hosting)
    register(idx, ext)
    sha = blobs.put_bytes(store, BLIF.encode())
    row = bench.Netlist("s1", "alpha", "f1", sha, len(BLIF), "-", "-", "test")
    bench.save_netlists(idx, [row])
    bench.write_blob_index(idx, store, bench.load_suites(idx), [row])
    return idx, store, Path(tmpdir()) / "stage", sha


class Stage(unittest.TestCase):
    def test_public_blob_is_staged_and_summed(self) -> None:
        idx, store, stage, sha = world()
        report = benchpub.run_stage(idx, store, stage, META, "2026-10-31")
        out = stage / "blobs" / sha[:2] / f"{sha}.xz"
        self.assertEqual(hashlib.sha256(lzma.decompress(out.read_bytes())).hexdigest(), sha)
        self.assertIn("blobs staged: 1", report[0])
        self.assertIn("suite\ts1\thostable\tblobs 1", report)
        for name in benchpub.INDEX_FILES:
            self.assertTrue((stage / "index" / "bench" / name).is_file(), name)
        sums = (stage / benchpub.SUMS).read_text(encoding="utf-8").splitlines()
        self.assertIn(f"{hashlib.sha256(out.read_bytes()).hexdigest()}  blobs/{sha[:2]}/{sha}.xz",
                      sums)
        self.assertFalse([ln for ln in sums if ln.endswith("SHA256SUMS")])

    def test_local_only_and_unchecked_are_never_staged(self) -> None:
        for hosting in ("local-only", "unchecked"):
            idx, ext, store = make_world(hosting)
            register(idx, ext)
            sha = blobs.put_bytes(store, BLIF.encode())
            row = bench.Netlist("s1", "alpha", "f1", sha, len(BLIF), "-", "-", "test")
            bench.save_netlists(idx, [row])
            bench.write_blob_index(idx, store, bench.load_suites(idx), [row])
            stage = Path(tmpdir()) / "stage"
            report = benchpub.run_stage(idx, store, stage, META, "2026-10-31")
            self.assertIn("blobs staged: 0", report[0])
            self.assertIn(f"suite\ts1\t{hosting}\tblobs 0", report)
            self.assertFalse((stage / "blobs").exists())

    def test_shared_blob_with_unhostable_suite_is_left_out(self) -> None:
        idx, store, stage, sha = world()
        text = (idx / "suites.toml").read_text(encoding="utf-8")
        other = text.replace('id = "s1"', 'id = "s2"').replace('hosting = "public"',
                                                              'hosting = "unchecked"')
        (idx / "suites.toml").write_text(text + "\n" + other, encoding="utf-8")
        nets = bench.load_netlists(idx)
        bench.save_netlists(idx, nets + [bench.Netlist("s2", "alpha", "f1", sha, len(BLIF),
                                                       "-", "-", "test")])
        self.assertEqual(benchpub.hostable_shas(idx), {})

    def test_wrong_size_or_content_is_an_error(self) -> None:
        idx, store, stage, sha = world()
        path = blobs.blob_path(store, sha)
        other = lzma.compress(b"different", format=lzma.FORMAT_XZ)
        path.write_bytes(other)
        with self.assertRaises(benchpub.BenchPubError):
            benchpub.run_stage(idx, store, stage, META, "2026-10-31")
        rows = {sha: remote.BlobRef(sha, len(other), 9, "-", "public")}
        with self.assertRaises(benchpub.BenchPubError):
            benchpub.check_blob(path, rows[sha])

    def test_missing_blob_is_an_error(self) -> None:
        idx, store, stage, sha = world()
        blobs.blob_path(store, sha).rename(blobs.blob_path(store, sha).with_suffix(".gone"))
        with self.assertRaises(benchpub.BenchPubError):
            benchpub.run_stage(idx, store, stage, META, "2026-10-31")

    def test_blob_with_home_path_is_withheld(self) -> None:
        idx, ext, store = make_world()
        register(idx, ext)
        dirty = (BLIF + "# /home/someone/x\n").encode()
        sha = blobs.put_bytes(store, dirty)
        row = bench.Netlist("s1", "alpha", "f1", sha, len(dirty), "-", "-", "test")
        bench.save_netlists(idx, [row])
        bench.write_blob_index(idx, store, bench.load_suites(idx), [row])
        stage = Path(tmpdir()) / "stage"
        report = benchpub.run_stage(idx, store, stage, META, "2026-10-31")
        self.assertIn("blobs staged: 0; xz bytes: 0; withheld (home path): 1", report[0])

    def test_notice_lists_every_suite_and_verdict(self) -> None:
        text = benchpub.notice_text(bench.index_dir(), [], "2026-10-31")
        for sid, ver in (("vtr-verilog", "hostable"), ("vtr-blif-k2", "unchecked"),
                         ("itc99", "hostable")):
            self.assertIn(f"  {sid}: {ver}", text)
        self.assertNotIn("/home/", text)


class Cli(unittest.TestCase):
    def test_cli_stage(self) -> None:
        idx, store, stage, sha = world()
        buf = io.StringIO()
        with mock.patch.dict(os.environ, {"MIMIR_BLOBS": str(store)}), \
                contextlib.redirect_stdout(buf):
            code = main(["bench", "publish-plan", "--index", str(idx), "--stage", str(stage),
                         "--date", "2026-10-31"])
        self.assertEqual(code, 0, buf.getvalue())
        self.assertIn("blobs staged: 1", buf.getvalue())

    def test_cli_error_exit(self) -> None:
        idx, store, stage, sha = world()
        blobs.blob_path(store, sha).rename(blobs.blob_path(store, sha).with_suffix(".gone"))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main(["bench", "publish-plan", "--index", str(idx), "--blobs", str(store),
                         "--stage", str(stage), "--date", "2026-10-31"])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
