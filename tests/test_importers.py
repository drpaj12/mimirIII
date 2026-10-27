from __future__ import annotations

import gzip
import json
import unittest
from pathlib import Path

from mimir.importers.atlas import import_atlas
from mimir.importers.loki import find_datasets, import_loki
from mimir.importers.norns import import_norns
from mimir.store import Store
from tests.helpers import tmpdir


def put(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def norns_tree() -> Path:
    root = Path(tmpdir())
    rows = [
        {"design": "d1", "arm": "stock", "vseed": 1, "wirelength": 10.0, "cpd_ns": 1.5,
         "grid": [5, 5], "purity": {"x": 1}, "scale": None, "mystery": 3, "net_sha256": "ab"},
        {"design": "d1", "arm": "h1", "vseed": 2, "wirelength": 12.0, "rc": 1, "error": "boom"},
    ]
    put(root / "data/d1/runs.jsonl", "\n".join(json.dumps(r) for r in rows) + "\n")
    put(root / "data/r5/runs.jsonl", json.dumps({"design": "s", "arm": "norns", "seed": 3,
                                                 "chan_width": 20.0}) + "\n")
    put(root / "runs/r7f/runs.jsonl", json.dumps({"design": "s", "arm": "net0", "seed": 1,
                                                  "cpd_ns": 2.0}) + "\n")
    corpus = {"design": "d1", "atoms": 5, "relation_share": {"same_word": 0.5}, "arms": ["stock"]}
    put(root / "data/r7/corpus/d1.json", json.dumps(corpus))
    atlas = {"design": "d1", "arm": "stock", "seed": 1, "cpd_ns": 2.5, "wirelength": 9.0,
             "chan_width": 30.0, "clbs": [{}, {}], "atoms": [{}, {}, {}]}
    gz = root / "data/r7/atlas/d1.stock.s1.json.gz"
    gz.parent.mkdir(parents=True)
    gz.write_bytes(gzip.compress(json.dumps(atlas).encode()))
    return root


class NornsTests(unittest.TestCase):
    def test_counts_families_and_skips(self) -> None:
        recs, rep = import_norns(norns_tree())
        by = {(r.source, r.metric, r.arm): r for r in recs}
        self.assertEqual(rep.seen["norns-r1r2"], 2)
        self.assertEqual(by[("norns-r1r2", "vpr.wirelength", "stock")].value, 10.0)
        self.assertEqual(by[("norns-r1r2", "vpr.wirelength", "stock")].input_sha256, "ab")
        self.assertEqual(by[("norns-r1r2", "vpr.grid_w", "stock")].value, 5.0)
        self.assertEqual(by[("norns-r5", "vpr.chan_width", "norns")].tool_commit, "3c9a4d23b2")
        self.assertEqual(by[("norns-r5", "vpr.chan_width", "norns")].seed, 3)
        self.assertEqual(by[("norns-r7", "vpr.cpd", "net0")].family, "annealing")
        share = by[("norns-r7-corpus", "norns.corpus.relation_share", "")]
        self.assertEqual(share.bin, "same_word")
        skipped = rep.skipped["norns-r1r2"]
        self.assertEqual(skipped["field not in the field map: mystery"], 1)
        self.assertEqual(skipped["mapped field without a number: scale"], 1)

    def test_atlas(self) -> None:
        recs, rep = import_atlas(norns_tree())
        self.assertEqual({r.metric for r in recs},
                         {"vpr.cpd", "vpr.wirelength", "vpr.chan_width", "atlas.n_clbs",
                          "atlas.n_atoms"})
        self.assertEqual(rep.records["wyrd-atlas-r7"], 5)

    def test_idempotent(self) -> None:
        root = norns_tree()
        store = Store(Path(tmpdir()) / "n.db")
        store.add(import_norns(root)[0])
        n = store.count()
        store.add(import_norns(root)[0])
        self.assertEqual(store.count(), n)


def loki_tree() -> Path:
    root = Path(tmpdir())
    ds = root / "loki-x" / "corpus"
    for design in ("a", "b"):
        put(ds / design / "design.json", "{}")
        for floor, counts in (("f2", {"lut": 4, "nodes": 9}), ("f3", {"gate": 7, "nodes": 12})):
            meta = {"floor": floor, "counts": counts, "loops_cut": 0, "odin3_version": "1.1.0",
                    "script": ["a", "b"]}
            put(ds / design / floor / "meta.json", json.dumps(meta))
            put(ds / design / floor / "netlist.blif", ".model t\n.end\n")
    manifest = {"designs": [{"design": "a", "split": "train"}, {"design": "b", "split": "test"}]}
    put(ds / "manifest.json", json.dumps(manifest))
    put(root / "loki-y" / "log.txt", "x")
    return root


class LokiTests(unittest.TestCase):
    def test_import(self) -> None:
        root = loki_tree()
        self.assertEqual(find_datasets(root / "loki-x"), [root / "loki-x" / "corpus"])
        recs, rep = import_loki(root)
        src = "loki:loki-x/corpus"
        self.assertEqual(rep.seen[src], 4)
        got = {(r.design, r.arch, r.metric): r for r in recs}
        self.assertEqual(got[("a", "f3", "loki.gates")].level, "gate")
        self.assertEqual(got[("a", "f2", "loki.luts")].level, "lut")
        self.assertEqual(got[("b", "f2", "loki.in_train")].value, 0.0)
        self.assertEqual(got[("a", "f2", "loki.in_train")].value, 1.0)
        self.assertEqual(len(got[("a", "f2", "loki.luts")].input_sha256), 64)
        self.assertIn("loki-round-results", rep.skipped)


if __name__ == "__main__":
    unittest.main()
