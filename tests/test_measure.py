from __future__ import annotations

import unittest
from pathlib import Path

from mimir.cli import main
from mimir.measure import measure_job
from mimir.sets import Job
from mimir.store import Store
from tests.helpers import skip_without, tmpdir

BLIF = """\
.model t
.inputs a b
.outputs y
.names a b n1
11 1
.names a n1 n2
10 1
.names n1 n2 y
11 1
.end
"""


def job() -> Job:
    d = Path(tmpdir())
    (d / "t.blif").write_text(BLIF, encoding="utf-8")
    return Job(d / "t.blif", "t", "unit", "lut", "unit:t.blif")


class MeasureTests(unittest.TestCase):
    def test_structural_rows(self) -> None:
        out = measure_job(job(), rent=False)
        got = {(r.metric, r.bin): r for r in out.records}
        self.assertEqual(got[("struct.depth", "")].value, 3.0)
        self.assertEqual(got[("struct.n_comb", "")].value, 3.0)
        self.assertEqual(got[("struct.n_comb", "")].level, "lut")
        self.assertEqual(len(got[("struct.n_comb", "")].input_sha256), 64)
        self.assertEqual(got[("struct.n_comb", "")].measurer, "struct")

    @skip_without("pymetis")
    def test_small_netlist_notes_rent_skip(self) -> None:
        out = measure_job(job())
        self.assertEqual({r.metric for r in out.records if r.measurer == "rent"}, {"rent.nodes"})
        self.assertIn("fit skipped", out.rent_note)

    def test_bad_blif_is_an_error_not_a_crash(self) -> None:
        d = Path(tmpdir())
        (d / "bad.blif").write_text(".model t\n.subckt zzz a=b\n.end\n", encoding="utf-8")
        out = measure_job(Job(d / "bad.blif", "bad", "unit", "lut", "unit:bad"), rent=False)
        self.assertIn("undefined model", out.error)
        self.assertFalse(out.records)

    def test_cli_init_registry_export(self) -> None:
        d = Path(tmpdir())
        self.assertEqual(main(["init", str(d / "x.db")]), 0)
        self.assertEqual(main(["registry"]), 0)
        s = Store(d / "x.db")
        s.add(measure_job(job(), rent=False).records)
        self.assertEqual(main(["export", str(d / "x.db"), "--csv", str(d / "x.csv")]), 0)
        self.assertEqual(main(["coverage", str(d / "x.db")]), 0)
        self.assertGreater(len((d / "x.csv").read_text().splitlines()), 10)


if __name__ == "__main__":
    unittest.main()
