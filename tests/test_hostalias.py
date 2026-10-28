from __future__ import annotations

import json
import lzma
import os
import shutil
import sqlite3
import unittest
from pathlib import Path
from unittest import mock

from mimir import blobs, hostalias, hostscrub, privacy
from mimir.hostcli import _cmd_host_alias, _cmd_privacy_check
from mimir.remote import load_blob_index, write_xz
from mimir.scrub import Scrubber
from mimir.store import Store
from mimir.structdb import DesignInfo, import_flow_dir
from tests.depsfix import deps
from tests.helpers import tmpdir
from tests.test_structdb import FLOW, ROOT, fake_vtr

# Planted names are built from parts, so this file holds no real name.
REAL = "ab" + "cd-" + "wxyz" + "701"
USER = "qq" + "user" + "x"


def tmap() -> Path:
    return Path(tmpdir()) / "hosts.toml"


class AliasTests(unittest.TestCase):
    def test_alias_is_stable_and_appended(self) -> None:
        m = tmap()
        self.assertEqual(hostalias.alias_of(REAL, m), "host-1")
        self.assertEqual(hostalias.alias_of(REAL.upper(), m), "host-1")
        self.assertEqual(hostalias.alias_of("other", m), "host-2")
        self.assertEqual(hostalias.alias_of(REAL, m), "host-1")
        self.assertEqual(hostalias.alias_of("host-7", m), "host-7")
        self.assertEqual(hostalias.load_map(m), {REAL.lower(): "host-1", "other": "host-2"})

    def test_scrub_text_any_case_and_no_map(self) -> None:
        m = tmap()
        self.assertEqual(hostalias.scrub_text(f"on {REAL}", m), f"on {REAL}")
        hostalias.alias_of(REAL, m)
        self.assertEqual(hostalias.scrub_text(f"on {REAL.upper()} and {REAL}", m),
                         "on host-1 and host-1")
        self.assertEqual(hostalias.scrub_bytes(REAL.encode(), m), b"host-1")

    def test_facts_have_sources(self) -> None:
        facts = hostalias.host_facts()
        self.assertIn("kernel", facts)
        self.assertTrue(all(v["source"] and v["value"] for v in facts.values()))

    def test_scrubber_replaces_a_mapped_host(self) -> None:
        m = tmap()
        hostalias.alias_of(REAL, m)
        with mock.patch.dict(os.environ, {"MIMIR_HOST_MAP": str(m)}):
            self.assertEqual(Scrubber({}).text(f"host {REAL}"), "host host-1")


class RecordTimeTests(unittest.TestCase):
    def test_import_records_the_alias_and_the_facts(self) -> None:
        tmp = Path(tmpdir())
        cwd = os.getcwd()
        os.chdir(ROOT)
        try:
            flow = tmp / "flow"
            shutil.copytree(FLOW, flow)
            vtr = tmp / "vtr"
            head = fake_vtr(vtr)
            run_json = flow / "mimir-run.json"
            info = json.loads(run_json.read_text(encoding="utf-8"))
            info.update({"vtr_commit": head, "host": REAL,
                         "host_facts": {"cpu_cores": {"value": "8", "source": "os.cpu_count()"}}})
            run_json.write_text(json.dumps(info), encoding="utf-8")
            d = DesignInfo("micro/bm_dag3_lpm", "bm_dag3_lpm", "odin3-micro",
                           (Path("tests/fixtures/flow/design/bm_dag3_lpm.v"),))
            m = tmap()
            with mock.patch.dict(os.environ, {"MIMIR_HOST_MAP": str(m)}):
                s = Store(tmp / "s.db")
                import_flow_dir(s, tmp / "blobs", flow, d, deps(), Scrubber({}), "t", vtr)
            host = s.db.execute("SELECT host FROM run").fetchone()[0]
            self.assertTrue(host.startswith("host-1 "), host)
            self.assertNotIn(REAL, host)
            row = s.db.execute("SELECT key, value, conf, source FROM flow_param "
                               "WHERE step='host'").fetchall()
            self.assertEqual(row, [("host-1.cpu_cores", "8", "given", "os.cpu_count()")])
        finally:
            os.chdir(cwd)


def make_store(tmp: Path, host: str, blob_sha: str) -> Path:
    path = tmp / "s.db"
    s = Store(path)
    s.db.execute("INSERT INTO run (run_id, slug, config_hash, source, design, arch, seed, arm, "
                 "family, tool_commits, origin, host) VALUES "
                 "('r1','s','c','src','d','a',1,'','','','o',?)", (f"{host} 6.1 2026",))
    s.db.execute("INSERT INTO run_artifact VALUES ('r1', 'log', ?)", (blob_sha,))
    s.db.commit()
    s.close()
    return path


class RewriteTests(unittest.TestCase):
    def test_rewrite_is_idempotent_with_counts(self) -> None:
        tmp, m = Path(tmpdir()), tmap()
        db = make_store(tmp, REAL, "0" * 64)
        self.assertEqual(hostscrub.rewrite_hosts(db, m), (1, 0))
        self.assertEqual(hostscrub.rewrite_hosts(db, m), (0, 0))
        c = sqlite3.connect(db)
        self.assertEqual(c.execute("SELECT host FROM run").fetchone()[0], "host-1 6.1 2026")
        c.close()

    def test_reblob_repoints_and_keeps_the_old_blob(self) -> None:
        tmp, m = Path(tmpdir()), tmap()
        root = tmp / "blobs"
        old = blobs.put_bytes(root, f"ran on {REAL.upper()} as {USER}\n".encode())
        db = make_store(tmp, REAL, old)
        strings = [REAL.lower(), USER]
        hostalias.alias_of(REAL, m)
        got = hostscrub.reblob(db, root, strings, m)
        self.assertEqual(list(got), [old])
        new = got[old]
        self.assertNotEqual(new, old)
        self.assertEqual(blobs.get_bytes(root, new), b"ran on host-1 as redacted\n")
        self.assertEqual(blobs.get_bytes(root, old), f"ran on {REAL.upper()} as {USER}\n".encode())
        c = sqlite3.connect(db)
        self.assertEqual(c.execute("SELECT blob_sha256 FROM run_artifact").fetchone()[0], new)
        self.assertEqual(c.execute("SELECT ref_table, ref_key, scrubbed_from, blob_sha256 "
                                   "FROM blob_scrub").fetchall(),
                         [("run_artifact", "r1:log", old, new)])
        c.close()
        self.assertEqual(hostscrub.reblob(db, root, strings, m), {})  # idempotent

    def test_index_marks_old_withheld_and_adds_new(self) -> None:
        tmp = Path(tmpdir())
        root = tmp / "blobs"
        old = blobs.put_bytes(root, b"old " + REAL.encode())
        new = blobs.put_bytes(root, b"new host-1")
        idx = tmp / "idx"
        idx.mkdir()
        write_xz(idx / "blobs.tsv.xz", f"{old}\t10\t20\t-\tpublic\n".encode())
        self.assertEqual(hostscrub.update_blob_index(idx, {old: new}, root, "arc.tar.xz"), 2)
        ref = load_blob_index(idx)
        self.assertEqual(ref[old].visibility, "withheld")
        self.assertEqual((ref[new].visibility, ref[new].archive), ("public", "arc.tar.xz"))
        late = blobs.put_bytes(root, b"late clean blob")
        self.assertEqual(hostscrub.update_blob_index(idx, {}, root, "arc.tar.xz", {late, "0" * 64}),
                         1)
        self.assertEqual(load_blob_index(idx)[late].visibility, "public")


class PrivacyTests(unittest.TestCase):
    def test_finds_a_planted_string_everywhere(self) -> None:
        tmp = Path(tmpdir())
        strings = [REAL.lower()]
        root = tmp / "blobs"
        sha = blobs.put_bytes(root, f"x {REAL.upper()}".encode())
        db = make_store(tmp, REAL, sha)
        self.assertEqual(len(privacy.scan_db(db, strings)), 1)
        self.assertIn("run.host", privacy.scan_db(db, strings)[0])
        n, hits = privacy.scan_blobs(root, strings)
        self.assertEqual((n, len(hits)), (1, 1))
        (tmp / "out").mkdir()
        (tmp / "out" / "a.csv").write_text(f"h\n{REAL}\n", encoding="utf-8")
        (tmp / "out" / "b.sql.xz").write_bytes(lzma.compress(REAL.encode()))
        self.assertEqual(len(privacy.scan_tree(tmp / "out", strings)), 2)

    def test_clean_store_has_no_hit(self) -> None:
        tmp = Path(tmpdir())
        db = make_store(tmp, "host-1", "0" * 64)
        self.assertEqual(privacy.scan_db(db, [REAL.lower()]), [])

    def test_cli_exit_codes_and_no_name_in_the_output(self) -> None:
        import argparse
        import contextlib
        import io

        tmp = Path(tmpdir())
        db = make_store(tmp, REAL, "0" * 64)
        ns = argparse.Namespace(db=[str(db)], path=[], blobs=None, index=None, map=None,
                                max_list=5)
        with mock.patch.dict(os.environ, {"MIMIR_PRIVATE_STRINGS": f"{REAL}\n{USER}"}):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = _cmd_privacy_check(ns)
        self.assertEqual(code, 1)
        self.assertNotIn(REAL.lower(), buf.getvalue().lower())

    def test_host_alias_cli_end_to_end(self) -> None:
        import argparse
        import contextlib
        import io

        tmp, m = Path(tmpdir()), tmap()
        root = tmp / "blobs"
        sha = blobs.put_bytes(root, f"x {REAL}".encode())
        db = make_store(tmp, REAL, sha)
        hostalias.alias_of(REAL, m)
        ns = argparse.Namespace(db=[str(db)], dir=None, map=str(m), blobs=str(root), index=None,
                                archive="-")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(_cmd_host_alias(ns), 0)
        self.assertEqual(privacy.scan_db(db, [REAL.lower()]), [])
        self.assertEqual(privacy.scan_blobs(root, [REAL.lower()])[1],
                         [f"blob {sha}#0"])  # the old blob stays on disk


if __name__ == "__main__":
    unittest.main()
