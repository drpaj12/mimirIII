"""Default data paths resolve against the repo root, not the working directory."""

from __future__ import annotations

import os
import unittest
from pathlib import Path

from mimir.cli import build_parser
from tests.helpers import tmpdir


class DefaultPathTest(unittest.TestCase):
    def test_import_meta_and_bench_measure_defaults_from_another_directory(self) -> None:
        old = Path.cwd()
        os.chdir(tmpdir())
        try:
            p = build_parser()
            meta = p.parse_args(["import-meta", "x.db"])
            desc = p.parse_args(["bench", "measure", "desc"])
        finally:
            os.chdir(old)
        for path in (Path(meta.toml), Path(meta.licences), Path(desc.meta)):
            self.assertTrue(path.is_absolute(), path)
        os.chdir(tmpdir())
        try:
            for path in (Path(meta.toml), Path(meta.licences), Path(desc.meta)):
                self.assertTrue(path.is_file(), path)
        finally:
            os.chdir(old)


if __name__ == "__main__":
    unittest.main()
