from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest import mock

from mimir import structrun
from tests.helpers import tmpdir
from tests.test_structdb import fake_vtr


class CommitTests(unittest.TestCase):
    def test_git_head_of_a_non_repo_is_empty(self) -> None:
        self.assertEqual(structrun.git_head(Path(tmpdir())), "")

    def test_git_head_of_a_repo(self) -> None:
        root = Path(tmpdir()) / "r"
        head = fake_vtr(root)
        self.assertEqual(structrun.git_head(root), head)

    def test_main_refuses_without_vtr_root(self) -> None:
        tree = Path(tmpdir()) / "t"
        fake_vtr(tree)
        env = {k: v for k, v in os.environ.items() if k != "VTR_ROOT"}
        with mock.patch.dict(os.environ, env, clear=True):
            code = structrun.main(["--tree", str(tree), "--odin3", "x", "--top", "t", "--out",
                                   str(Path(tmpdir()) / "o"), "d.v"])
        self.assertEqual(code, 2)

    def test_main_does_not_take_the_commit_from_the_cwd(self) -> None:
        tree = Path(tmpdir()) / "t"
        fake_vtr(tree)
        notrepo = Path(tmpdir())
        with mock.patch.dict(os.environ, {"VTR_ROOT": str(notrepo)}):
            code = structrun.main(["--tree", str(tree), "--odin3", "x", "--top", "t", "--out",
                                   str(notrepo / "o"), "d.v"])
        self.assertEqual(code, 2)


class FlowFactsTests(unittest.TestCase):
    def test_commands_carry_timing_attr_unless_switched_off(self) -> None:
        args = (Path("t"), Path("o"), [Path("a.v")], "top", None, Path("out"))
        self.assertIn("--timing-attr", structrun.build_commands(*args)[0])
        self.assertNotIn("--timing-attr", structrun.build_commands(*args, False)[0])

    def test_timing_failure_is_read_only_when_vpr_ran(self) -> None:
        out = Path(tmpdir())
        self.assertEqual(structrun.timing_failure(out), "")
        (out / "timing").mkdir()
        (out / "vpr").mkdir()
        (out / "timing" / "timing.log").write_text(f"{out}/x: no '#Path' sections\n",
                                                   encoding="utf-8")
        self.assertEqual(structrun.timing_failure(out), "")  # no vpr.log yet
        (out / "vpr" / "vpr.log").write_text("ok", encoding="utf-8")
        self.assertEqual(structrun.timing_failure(out), "<out>/x: no '#Path' sections")
        (out / "timing" / "timing.log").write_text("ok\n", encoding="utf-8")
        self.assertEqual(structrun.timing_failure(out), "")

    def test_map_sources_hashes_the_listed_files(self) -> None:
        out = Path(tmpdir())
        src = out / "d.v"
        src.write_text("module m; endmodule\n", encoding="utf-8")
        (out / "odin3").mkdir()
        (out / "odin3" / "m.blif.names").write_text(f"# header\nF\tf1\t{src}\nF\tf2\t/nope.v\n",
                                                   encoding="utf-8")
        got = structrun.map_sources(out)
        self.assertEqual(list(got), [str(src)])
        self.assertEqual(len(got[str(src)]), 64)
