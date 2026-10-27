from __future__ import annotations

import gzip
import json
import unittest
from dataclasses import replace
from pathlib import Path

from mimir import blobs
from mimir.meta import Roots, register_designs
from mimir.partition import (
    PartitionSpec,
    add_partition,
    assignment_text,
    import_norns_hindsight,
    normalise_name,
    partition_id,
    size_metrics,
)
from mimir.store import Store
from tests.helpers import tmpdir
from tests.test_store import rec

ASSIGN = {"a": 0, "b": 0, "c": 1, "d": 2, "e": 2, "f": 2}


def spec() -> PartitionSpec:
    return PartitionSpec(slug="t/x", design="x", algorithm="toy", algorithm_version="1",
                         params={"k": 3}, seed=7, input_hash="ab", assignment=ASSIGN, origin="o")


class PartitionTests(unittest.TestCase):
    def test_sizes(self) -> None:
        got = dict(size_metrics(ASSIGN))
        self.assertEqual(got["partition.n_objects"], 6.0)
        self.assertEqual(got["partition.n_clusters"], 3.0)
        self.assertEqual(got["partition.cluster_size_max"], 3.0)
        self.assertEqual(got["partition.cluster_size_mean"], 2.0)

    def test_add_is_idempotent_and_blob_roundtrips(self) -> None:
        d = Path(tmpdir())
        s = Store(d / "x.db")
        p1 = add_partition(s, d / "blobs", spec(), [("partition.cost_after", 1.5, "")])
        p2 = add_partition(s, d / "blobs", spec(), [("partition.cost_after", 1.5, "")])
        self.assertEqual(p1, p2)
        row = s.db.execute("SELECT n_objects, n_clusters, assignment_blob FROM partition"
                           ).fetchone()
        self.assertEqual(row[:2], (6, 3))
        self.assertEqual(blobs.get_bytes(d / "blobs", row[2]), assignment_text(ASSIGN))
        n = s.db.execute("SELECT COUNT(*) FROM records WHERE source = ?",
                         (f"partition:{p1}",)).fetchone()[0]
        self.assertEqual(n, 5)

    def test_hindsight_import(self) -> None:
        d = Path(tmpdir())
        base = d / "norns" / "runs/r7/dd"
        (base / "stock.s5").mkdir(parents=True)
        (base / "stock.s5" / "dd.net.gz").write_bytes(gzip.compress(b"net"))
        (base / "h1.affinity.tsv").write_text("p/q@f.v:1\t3\nr\t4\nz\t3\n")
        (base / "h1.recluster.json").write_text(json.dumps(
            {"source_arm": "stock", "source_seed": 5, "cost_before": 5.0, "cost_after": 4.0,
             "atoms_moved": 1}))
        (base / "rounds.json").write_text(json.dumps({"medians": {"h1": 3.0, "stock": 2.0}}))
        s = Store(d / "x.db")
        s.add([replace(rec("dd", "m", 1.0), source="norns-r7")])
        register_designs(s, Roots())
        pid = import_norns_hindsight(s, d / "blobs", d / "norns", "dd")
        row = s.db.execute("SELECT slug, n_objects, n_clusters FROM partition WHERE partition_id=?",
                           (pid,)).fetchone()
        self.assertEqual(row, ("norns/dd", 3, 2))
        med = s.db.execute("SELECT bin, value FROM records WHERE source = ? AND metric = "
                           "'partition.downstream_median_objective' ORDER BY bin",
                           (f"partition:{pid}",)).fetchall()
        self.assertEqual(med, [("h1", 3.0), ("stock", 2.0)])

    def test_names_are_machine_independent(self) -> None:
        a = normalise_name("memset/$n176@/home/u/vtr/vtr_flow/benchmarks/verilog/c.v:147")
        b = normalise_name("memset/$n176@/mnt/other/vtr/vtr_flow/benchmarks/verilog/c.v:147")
        self.assertEqual(a, b)
        self.assertEqual(a, "memset/$n176@vtr_flow/benchmarks/verilog/c.v:147")
        self.assertEqual(normalise_name("p@/x/y/z.v:3"), "p@z.v:3")
        self.assertEqual(normalise_name("plain"), "plain")
        with self.assertRaises(ValueError):
            normalise_name("a/home/b")

    def test_blob_and_id_do_not_depend_on_the_path_prefix(self) -> None:
        d = Path(tmpdir())
        s = Store(d / "x.db")
        home = {"m@/home/a/vtr_flow/b.v:1": 0, "n": 1}
        other = {"m@/srv/q/vtr_flow/b.v:1": 0, "n": 1}
        p1 = add_partition(s, d / "b1", replace(spec(), assignment=home), [])
        p2 = add_partition(s, d / "b2", replace(spec(), assignment=other), [])
        self.assertEqual(p1, p2)
        for sha in blobs.all_hashes(d / "b1"):
            self.assertNotIn(b"/home/", blobs.get_bytes(d / "b1", sha))

    def test_id_includes_slug_and_version(self) -> None:
        base = spec()
        ids = {partition_id(base, "b"), partition_id(replace(base, slug="t/y"), "b"),
               partition_id(replace(base, algorithm_version="2"), "b")}
        self.assertEqual(len(ids), 3)

    def test_failed_import_leaves_nothing(self) -> None:
        d = Path(tmpdir())
        s = Store(d / "x.db")
        with self.assertRaises(ValueError):
            add_partition(s, d / "blobs", spec(), [("partition.cost_after", float("nan"), "")])
        self.assertEqual(s.db.execute("SELECT COUNT(*) FROM partition").fetchone()[0], 0)
        self.assertEqual(s.db.execute("SELECT COUNT(*) FROM records").fetchone()[0], 0)

    def test_provenance_labels_of_the_worked_example(self) -> None:
        d = Path(tmpdir())
        base = d / "norns" / "runs/r7/dd"
        base.mkdir(parents=True)
        (base / "h1.affinity.tsv").write_text("q\t1\n")
        (base / "h1.recluster.json").write_text(json.dumps(
            {"source_arm": "stock", "source_seed": 5, "cost_before": 5.0, "cost_after": 4.0,
             "atoms_moved": 1}))
        (base / "rounds.json").write_text(json.dumps({"medians": {"h1": 3.0}}))
        s = Store(d / "x.db")
        pid = import_norns_hindsight(s, d / "blobs", d / "norns", "dd")
        row = s.db.execute("SELECT input_hash, version_kind, seed_conf, algorithm_version "
                           "FROM partition WHERE partition_id=?", (pid,)).fetchone()
        self.assertEqual(row[0], "missing:dd.net.gz")  # no input file: a sentinel, not ''
        self.assertEqual(row[1], "importer-checkout")
        self.assertEqual(row[2], "default-unconfirmed")  # no scripts to confirm the seed from
        self.assertTrue(row[3].startswith("norns-exp scripts at"))


if __name__ == "__main__":
    unittest.main()
