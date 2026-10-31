from __future__ import annotations

import contextlib
import io
import os
import stat
import unittest
from pathlib import Path
from unittest import mock

from mimir import bench, benchreg, blobs, remote
from mimir.cli import main
from mimir.sets import SETS
from tests.helpers import tmpdir

ROOT = Path(__file__).resolve().parent.parent
BLIF = ".model top\n.inputs a\n.outputs y\n.names a y\n1 1\n.end\n"

SUITES = """\
[[suite]]
id = "s1"
title = "t"
format = "verilog"
upstream = "https://example.org/s1"
commit = "abc"
external = "s1repo"
subdir = "src"
glob = "*.v"
slug_prefix = "x/"
licence = "MIT"
licence_source = "LICENSE:1"
hosting = "{hosting}"
obtained = "clone"
default_flow = "f2"
"""

FLOWS = """\
[[flow]]
id = "f1"
tool = "odin3"
tool_version = "1"
tool_commit = "c1"
binary_sha256 = "b"
input = "verilog"
arch = "a"
lut_k = 6
script = "s"
source = "test"
layout = "out/{d}/{d}.blif"
record = "out/{d}/meta.json"
build = "{odin3} {src} {out}/{design}.blif"

[[flow]]
id = "f2"
tool = "odin3"
tool_version = "2"
tool_commit = "c2"
binary_sha256 = "b"
input = "verilog"
arch = "a"
lut_k = 6
script = "s"
source = "test"
"""


def make_world(hosting: str = "public") -> tuple[Path, Path, Path]:
    """(index dir, external root, blob store) of a tiny registry with sources alpha and beta."""
    base = Path(tmpdir())
    idx, ext, store = base / "idx", base / "external", base / "blobs"
    (idx).mkdir()
    src = ext / "s1repo" / "src"
    src.mkdir(parents=True)
    (src / "alpha.v").write_text("module alpha(input a);\nendmodule\n", encoding="utf-8")
    (src / "beta.v").write_text("module b1;\nendmodule\nmodule b2;\nendmodule\n", encoding="utf-8")
    (idx / "suites.toml").write_text(SUITES.format(hosting=hosting), encoding="utf-8")
    (idx / "flows.toml").write_text(FLOWS, encoding="utf-8")
    return idx, ext, store


def register(idx: Path, ext: Path) -> None:
    with mock.patch.dict(os.environ, {"MIMIR_EXTERNAL": str(ext)}):
        benchreg.register_suite(idx, "s1", [])


class Registry(unittest.TestCase):
    def test_committed_index_is_consistent(self) -> None:
        self.assertEqual(bench.check(), [])
        suites = bench.load_suites()
        want = ["brisc-v", "itc99", "mcnc20", "verilogeval", "vtr-blif-k2", "vtr-blif-k4",
                "vtr-verilog"]
        self.assertEqual(sorted(suites), want)
        for s in suites.values():
            self.assertTrue(s.licence and s.licence_source and s.commit and s.upstream, s.id)

    def test_committed_designs_have_licence_rules(self) -> None:
        for d in bench.load_designs():
            if d.suite in ("vtr-verilog", "mcnc20"):
                self.assertNotEqual(d.licence_rule, "-", d.design)

    def test_unchecked_suites_hold_no_netlists(self) -> None:
        unchecked = {s.id for s in bench.load_suites().values() if s.hosting == "unchecked"}
        self.assertEqual(unchecked, {"vtr-blif-k2", "vtr-blif-k4"})
        self.assertFalse([n for n in bench.load_netlists() if n.suite in unchecked])

    def test_norns_base_is_35_designs(self) -> None:
        nets = [n for n in bench.load_netlists() if n.flow.startswith("odin3-1.2.0-k6-")]
        self.assertEqual(len(nets), 35)
        self.assertEqual(len({n.design for n in nets}), 35)

    def test_no_home_path_in_index_or_cache_of_names(self) -> None:
        for name in ("suites.toml", "flows.toml", "designs.tsv", "netlists.tsv"):
            self.assertNotIn("/home/", (bench.index_dir() / name).read_text(encoding="utf-8"))

    def test_source_hashes_match_checkout_when_present(self) -> None:
        suites = bench.load_suites()
        checked = 0
        for d in bench.load_designs():
            if d.format == "verilog-project" or d.suite != "vtr-verilog":
                continue
            path = bench.source_path(suites[d.suite], d)
            if path.is_file():
                self.assertEqual(remote.sha256_path(path), d.sha256, d.design)
                checked += 1
        if checked == 0:
            self.skipTest("no VTR checkout")


class RefParsing(unittest.TestCase):
    def test_parse(self) -> None:
        self.assertEqual(bench.parse_ref("a:b.1@f-1"), ("a", "b.1", "f-1"))
        self.assertEqual(bench.parse_ref("a:b"), ("a", "b", None))
        for bad in ("a", "a:", ":b", "a:b@", "a b:c", "a:b@c@d"):
            with self.assertRaises(bench.BenchError, msg=bad):
                bench.parse_ref(bad)


class Register(unittest.TestCase):
    def test_register_designs_top_and_rules(self) -> None:
        idx, ext, _ = make_world()
        register(idx, ext)
        rows = {d.design: d for d in bench.load_designs(idx)}
        self.assertEqual(sorted(rows), ["alpha", "beta"])
        self.assertEqual(rows["alpha"].top, "alpha")
        self.assertEqual(rows["beta"].top, "-")
        self.assertEqual(rows["alpha"].slug, "x/alpha")
        self.assertEqual(rows["alpha"].lines, 2)
        before = (idx / "designs.tsv").read_bytes()
        register(idx, ext)
        self.assertEqual((idx / "designs.tsv").read_bytes(), before)

    def test_unknown_suite_and_missing_checkout(self) -> None:
        idx, ext, _ = make_world()
        with self.assertRaises(bench.BenchError):
            benchreg.register_suite(idx, "nope", [])
        with mock.patch.dict(os.environ, {"MIMIR_EXTERNAL": str(ext / "elsewhere")}), \
                self.assertRaises(bench.BenchError):
            benchreg.register_suite(idx, "s1", [])


def populate(idx: Path, ext: Path, store: Path, hosting: str = "public") -> Path:
    """Register and import a netlist for alpha under flow f1; returns the import tree."""
    register(idx, ext)
    tree = idx.parent / "tree"
    (tree / "out" / "alpha").mkdir(parents=True)
    (tree / "out" / "alpha" / "alpha.blif").write_text(BLIF, encoding="utf-8")
    (tree / "out" / "alpha" / "alpha.blif.names").write_text(
        "O\ttop\tnet\th1\tn@/home/someone/odin3-ws/x.v:1\n", encoding="utf-8")
    (tree / "out" / "alpha" / "meta.json").write_text('{"argv": ["<odin3>", "--top", "alpha"]}',
                                                      encoding="utf-8")
    (tree / "out" / "gamma").mkdir()
    (tree / "out" / "gamma" / "gamma.blif").write_text(BLIF, encoding="utf-8")
    return tree


class Import(unittest.TestCase):
    def test_import_stores_blobs_scrubs_and_skips(self) -> None:
        idx, ext, store = make_world()
        tree = populate(idx, ext, store)
        with mock.patch.dict(os.environ, {"MIMIR_EXTERNAL": str(ext)}):
            n, skipped = benchreg.import_netlists(idx, store, "s1", "f1", tree, ext.parent)
        self.assertEqual((n, skipped), (1, ["gamma"]))
        (row,) = bench.load_netlists(idx)
        self.assertEqual(blobs.get_bytes(store, row.sha256).decode(), BLIF)
        names = blobs.get_bytes(store, row.map_sha256).decode()
        self.assertNotIn("/home/", names)
        self.assertIn("$HOME", names)
        self.assertEqual(len(row.flowrec_sha256), 64)
        self.assertEqual(bench.write_blob_index(idx, store, bench.load_suites(idx), [row]), 3)
        self.assertEqual(bench.check(idx, store, True), [])
        again = {d.design: d.top for d in bench.load_designs(idx)}
        self.assertEqual(again["alpha"], "alpha")

    def test_dirty_netlist_is_tokenised(self) -> None:
        idx, ext, store = make_world()
        tree = populate(idx, ext, store)
        dirty = BLIF.replace("a y", "a y@/home/someone/odin3-ws/z.v:3")
        (tree / "out" / "alpha" / "alpha.blif").write_text(dirty, encoding="utf-8")
        with mock.patch.dict(os.environ, {"MIMIR_EXTERNAL": str(ext)}):
            benchreg.import_netlists(idx, store, "s1", "f1", tree, ext.parent)
        (row,) = bench.load_netlists(idx)
        self.assertNotIn("/home/", blobs.get_bytes(store, row.sha256).decode())
        self.assertIn("tokenised", row.origin)

    def test_unchecked_and_local_only(self) -> None:
        idx, ext, store = make_world("unchecked")
        tree = populate(idx, ext, store)
        with self.assertRaises(bench.BenchError):
            benchreg.import_netlists(idx, store, "s1", "f1", tree, ext.parent)

    def test_different_netlist_is_not_overwritten(self) -> None:
        idx, ext, store = make_world()
        tree = populate(idx, ext, store)
        with mock.patch.dict(os.environ, {"MIMIR_EXTERNAL": str(ext)}):
            benchreg.import_netlists(idx, store, "s1", "f1", tree, ext.parent)
            (tree / "out" / "alpha" / "alpha.blif").write_text(BLIF + "# x\n", encoding="utf-8")
            with self.assertRaises(bench.BenchError):
                benchreg.import_netlists(idx, store, "s1", "f1", tree, ext.parent)

    def test_local_only_blobs_are_private_and_never_downloaded(self) -> None:
        idx, ext, store = make_world("local-only")
        register(idx, ext)
        sha = blobs.put_bytes(store, BLIF.encode())
        row = bench.Netlist("s1", "alpha", "f1", sha, len(BLIF), "-", "-", "test")
        bench.save_netlists(idx, [row])
        bench.write_blob_index(idx, store, bench.load_suites(idx), [row])
        self.assertEqual(remote.load_blob_index(idx)[sha].visibility, "private")
        empty = Path(tmpdir())
        loc = remote.Locations(empty / "none", None, "file:///nowhere", empty / "cache")
        with self.assertRaises(bench.BenchError) as cm:
            bench.materialise("s1:alpha@f1", empty / "o.blif", idx=idx, loc=loc)
        self.assertIn("never downloaded", str(cm.exception))


class Resolve(unittest.TestCase):
    def setUp(self) -> None:
        self.idx, self.ext, self.store = make_world()
        register(self.idx, self.ext)
        sha = blobs.put_bytes(self.store, BLIF.encode())
        sha2 = blobs.put_bytes(self.store, (BLIF + "# 2\n").encode())
        bench.save_netlists(self.idx, [
            bench.Netlist("s1", "alpha", "f1", sha, 10, "-", "-", "t"),
            bench.Netlist("s1", "alpha", "f2", sha2, 10, "-", "-", "t"),
            bench.Netlist("s1", "beta", "f1", sha, 10, "-", "-", "t")])
        suites = bench.load_suites(self.idx)
        bench.write_blob_index(self.idx, self.store, suites, bench.load_netlists(self.idx))

    def test_rules(self) -> None:
        r = bench.resolve("s1:alpha@f1", self.idx)
        assert r.netlist is not None
        self.assertEqual(r.netlist.flow, "f1")
        d = bench.resolve("s1:alpha", self.idx)
        assert d.netlist is not None
        self.assertEqual(d.netlist.flow, "f2")  # the suite default
        b = bench.resolve("s1:beta", self.idx)
        assert b.netlist is not None
        self.assertEqual(b.netlist.flow, "f1")  # the only one
        for bad in ("zz:alpha", "s1:nope", "s1:alpha@f9"):
            with self.assertRaises(bench.BenchError, msg=bad):
                bench.resolve(bad, self.idx)

    def test_ambiguous_without_default(self) -> None:
        text = (self.idx / "suites.toml").read_text().replace('default_flow = "f2"\n', "")
        (self.idx / "suites.toml").write_text(text)
        with self.assertRaises(bench.BenchError) as cm:
            bench.resolve("s1:alpha", self.idx)
        self.assertIn("ambiguous", str(cm.exception))

    def test_materialise_verifies_and_reads_source(self) -> None:
        out = Path(tmpdir()) / "o.blif"
        loc = remote.Locations(self.store, None, None, Path(tmpdir()))
        path = bench.materialise("s1:alpha@f1", out, idx=self.idx, loc=loc)
        self.assertEqual(path.read_text(), BLIF)
        with self.assertRaises(bench.BenchError):
            bench.materialise("s1:alpha@f1", out, "map", self.idx, loc)
        with mock.patch.dict(os.environ, {"MIMIR_EXTERNAL": str(self.ext)}):
            src = bench.materialise("s1:alpha", None, "source", self.idx)
            self.assertEqual(src.name, "alpha.v")
            src.write_text("module changed;\nendmodule\n", encoding="utf-8")
            with self.assertRaises(bench.BenchError):
                bench.materialise("s1:alpha", None, "source", self.idx)

    def test_corrupt_blob_is_refused(self) -> None:
        sha = bench.resolve("s1:alpha@f1", self.idx).netlist
        assert sha is not None
        path = blobs.blob_path(self.store, sha.sha256)
        import lzma
        path.write_bytes(lzma.compress(b"something else"))
        loc = remote.Locations(self.store, None, None, Path(tmpdir()))
        with self.assertRaises(bench.BenchError):
            bench.materialise("s1:alpha@f1", Path(tmpdir()) / "o", idx=self.idx, loc=loc)

    def test_fetch_by_url_checks_hash(self) -> None:
        sha = bench.resolve("s1:alpha@f1", self.idx).netlist
        assert sha is not None
        web = Path(tmpdir())
        dest = web / "blobs" / sha.sha256[:2]
        dest.mkdir(parents=True)
        src = blobs.blob_path(self.store, sha.sha256)
        (dest / src.name).write_bytes(src.read_bytes())
        empty = Path(tmpdir())
        loc = remote.Locations(empty / "none", None, f"file://{web}", empty / "cache")
        out = bench.materialise("s1:alpha@f1", empty / "o.blif", idx=self.idx, loc=loc)
        self.assertEqual(out.read_text(), BLIF)
        import lzma
        (dest / src.name).write_bytes(lzma.compress(b"tampered"))
        loc2 = remote.Locations(empty / "none", None, f"file://{web}", empty / "cache2")
        with self.assertRaises(bench.BenchError):
            bench.materialise("s1:alpha@f1", empty / "o2.blif", idx=self.idx, loc=loc2)

    def test_check_finds_problems(self) -> None:
        rows = bench.load_netlists(self.idx)
        bench.save_netlists(self.idx, [*rows, bench.Netlist("s1", "ghost", "f9", "0" * 64, 1,
                                                            "-", "-", "t")])
        probs = bench.check(self.idx)
        self.assertTrue(any("design not registered" in p for p in probs))
        self.assertTrue(any("unknown flow" in p for p in probs))
        self.assertTrue(any("not in blobs.tsv.xz" in p for p in probs))


class Build(unittest.TestCase):
    def setUp(self) -> None:
        stack = contextlib.ExitStack()
        stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        self.addCleanup(stack.close)

    def test_build_with_fake_odin(self) -> None:
        idx, ext, store = make_world()
        register(idx, ext)
        fake = idx.parent / "fake-odin"
        fake.write_text(f"#!/bin/sh\nprintf '{BLIF}' > \"$2\"\n",
                        encoding="utf-8")
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
        argv = ["bench", "build", "s1:alpha", "--flow", "f1", "--odin3", str(fake),
                "--index", str(idx), "--blobs", str(store)]
        with mock.patch.dict(os.environ, {"MIMIR_EXTERNAL": str(ext)}):
            self.assertEqual(main(argv), 0)
            (row,) = bench.load_netlists(idx)
            self.assertEqual(blobs.get_bytes(store, row.sha256).decode(), BLIF)
            self.assertEqual(main(argv), 0)  # same output: idempotent
            self.assertEqual(len(bench.load_netlists(idx)), 1)
            no_build = [a if a != "f1" else "f2" for a in argv]
            self.assertEqual(main(no_build), 1)  # f2 has no build command
        self.assertEqual(bench.check(idx, store, True), [])
        self.assertIn("alpha.v", blobs.get_bytes(store, row.flowrec_sha256).decode())

    def test_failed_build_stores_nothing(self) -> None:
        idx, ext, store = make_world()
        register(idx, ext)
        fake = idx.parent / "bad-odin"
        fake.write_text("#!/bin/sh\nexit 3\n", encoding="utf-8")
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
        with mock.patch.dict(os.environ, {"MIMIR_EXTERNAL": str(ext)}), \
                self.assertRaises(bench.BenchError):
            benchreg.build_netlist(idx, store, "s1:alpha", "f1", fake)
        self.assertEqual(bench.load_netlists(idx), [])


class Cli(unittest.TestCase):
    def setUp(self) -> None:
        stack = contextlib.ExitStack()
        stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        self.addCleanup(stack.close)

    def test_list_show_fetch_check(self) -> None:
        self.assertEqual(main(["bench", "list"]), 0)
        self.assertEqual(main(["bench", "list", "--suite", "mcnc20"]), 0)
        self.assertEqual(main(["bench", "list", "--suite", "mcnc20", "--netlists"]), 0)
        self.assertEqual(main(["bench", "list", "--suite", "nope"]), 2)
        self.assertEqual(main(["bench", "show", "vtr-verilog:sha@odin3-1.2.0-k6-verilog"]), 0)
        self.assertEqual(main(["bench", "show", "vtr-verilog:nope"]), 2)
        self.assertEqual(main(["bench", "check"]), 0)

    def test_fetch_from_local_store_when_present(self) -> None:
        store = blobs.default_dir()
        ref = "mcnc20:alu4@odin3-1.2.0-k6-blif"
        sha = bench.resolve(ref).netlist
        assert sha is not None
        if not blobs.blob_path(store, sha.sha256).is_file():
            self.skipTest("blob store not on this machine")
        out = Path(tmpdir()) / "alu4.blif"
        self.assertEqual(main(["bench", "fetch", ref, "--out", str(out)]), 0)
        self.assertTrue(out.read_text().startswith("# Odin III"))


class NornsSet(unittest.TestCase):
    def test_norns_set_reads_the_registry(self) -> None:
        build, var = SETS["norns"]
        self.assertEqual(var, "MIMIR_BLOBS")
        self.assertIn("norns-runs", SETS)
        store = blobs.default_dir()
        probe = bench.load_netlists()[0]
        if not blobs.blob_path(store, probe.sha256).is_file():
            self.skipTest("blob store not on this machine")
        with mock.patch.dict(os.environ, {"MIMIR_CACHE": tmpdir()}):
            jobs = build(store)
        self.assertEqual(len(jobs), 35)
        self.assertTrue(all(j.path.is_file() and j.source == "norns-netlist" for j in jobs))
        self.assertTrue(all(j.origin.startswith("bench:") for j in jobs))
        sizes = [j.path.stat().st_size for j in jobs]
        self.assertEqual(sizes, sorted(sizes))


if __name__ == "__main__":
    unittest.main()
