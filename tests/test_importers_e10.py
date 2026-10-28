from __future__ import annotations

import json
import unittest
from pathlib import Path

from mimir.importers.common import Report
from mimir.importers.e10 import import_e10, lut_count
from mimir.store import Store
from tests.helpers import tmpdir


def _run_row(store: Store, run_id: str, source: str, arm: str, seed: int = 1) -> None:
    vals = {"run_id": run_id, "slug": "s", "config_hash": run_id, "source": source, "design": "d",
            "arch": "A", "seed": seed, "arm": arm, "family": "annealing", "input_sha256": "ab",
            "tool_commit": "c", "tool_commits": "", "command_line": "", "time_s": 1.0,
            "peak_rss_mib": 1.0, "host": "h", "origin": "o"}
    cols = ",".join(vals)
    marks = ",".join("?" * len(vals))
    store.db.execute(f"insert into run ({cols}) values ({marks})", tuple(vals.values()))


def _netlist(root: Path, netkey: str) -> Path:
    nl = root / "netlists" / netkey / "d" / "netlist"
    nl.mkdir(parents=True)
    (nl / "d.blif").write_text(".model d\n.names a\n1\n.names a b o\n11 1\n.names b c\n1 1\n")
    return nl / "d.blif"


class ImportE10(unittest.TestCase):
    def test_records_join_run_rows(self) -> None:
        root = Path(tmpdir())
        (root / "data/placers").mkdir(parents=True)
        res = [{"arm": "vpr_sa", "seed": 1, "rc": 0, "wl": 10.0, "cpd_ns": 1.5, "W": 40.0,
                "clbs": 3.0, "flow_s": 2.0, "routed_ok": True},
               {"arm": "ext_nextpnr_sa", "seed": 1, "starttemp": 100.0, "rc": 1}]
        (root / "data/placers/e10-base_d.json").write_text(json.dumps({"runs": res}))
        self.assertEqual(lut_count(_netlist(root, "base")), 2)
        store = Store(root / "t.db")
        for arm in ("vpr_sa", "ext_nextpnr_sa-t100"):
            _run_row(store, arm, "norns-placers-e10-base", arm)
        store.db.commit()
        rep = Report()
        recs = list(import_e10(store, root / "data", "e10", root / "netlists", rep))
        by = {(r.arm, r.metric): r for r in recs}
        self.assertEqual(by[("vpr_sa", "vpr.wirelength")].value, 10.0)
        self.assertEqual(by[("vpr_sa", "struct.n_comb")].value, 2.0)
        self.assertEqual(by[("ext_nextpnr_sa-t100", "vpr.rc")].value, 1.0)
        # the netlist exists, so its LUT count is written whatever the VPR exit code (E10 fix 5)
        self.assertEqual(by[("ext_nextpnr_sa-t100", "struct.n_comb")].value, 2.0)
        self.assertTrue(all(r.source == "norns-placers-e10-base" and r.arch == "A" and r.seed == 1
                            for r in recs))
        store.replace_origins(recs)
        self.assertEqual(store.count(), len(recs))

    def test_failed_run_keeps_netlist_luts(self) -> None:
        root = Path(tmpdir())
        (root / "data/placers").mkdir(parents=True)
        res = [{"arm": "vpr_sa", "seed": 1, "rc": 124}]
        (root / "data/placers/e10-k4_d.json").write_text(json.dumps({"runs": res}))
        _netlist(root, "k4")
        store = Store(root / "t.db")
        _run_row(store, "k4", "norns-placers-e10-k4", "vpr_sa")
        store.db.commit()
        recs = list(import_e10(store, root / "data", "e10", root / "netlists", Report()))
        by = {r.metric: r.value for r in recs}
        self.assertEqual(by["vpr.rc"], 124.0)
        self.assertEqual(by["struct.n_comb"], 2.0)
        self.assertNotIn("vpr.wirelength", by)
