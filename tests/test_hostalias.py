from __future__ import annotations

import argparse
import contextlib
import gzip
import io
import json
import lzma
import multiprocessing
import os
import shutil
import sqlite3
import stat
import tarfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from mimir import blobs, hostalias, hostscrub, privacy, publish
from mimir.hostcli import _cmd_host_alias, _cmd_privacy_check
from mimir.remote import load_blob_index, write_xz
from mimir.scrub import Scrubber
from mimir.store import Store
from mimir.structdb import DesignInfo, import_flow_dir
from tests.depsfix import deps
from tests.helpers import skip_without, tmpdir
from tests.test_structdb import FLOW, ROOT, fake_vtr

# Planted names are built from parts, so this file holds no real name.
REAL = "ab" + "cd-" + "wxyz" + "701"
USER = "qq" + "user" + "x"
LOGIN = publish._USER  # the login name, itself built from parts in publish.py
EMAIL = publish._PERSON.replace("\\", "") + "@" + "g" + "mail.com"


def tmap() -> Path:
    m = Path(tmpdir()) / "hosts.toml"
    hostalias.init_map(m)
    return m


def _alias_job(args: tuple[str, str]) -> str:
    return hostalias.alias_of(args[1], Path(args[0]))


class AliasTests(unittest.TestCase):
    def test_alias_is_stable_and_appended(self) -> None:
        m = tmap()
        self.assertEqual(hostalias.alias_of(REAL, m), "host-1")
        self.assertEqual(hostalias.alias_of(REAL.upper(), m), "host-1")
        self.assertEqual(hostalias.alias_of("other", m), "host-2")
        self.assertEqual(hostalias.alias_of(REAL, m), "host-1")
        self.assertEqual(hostalias.alias_of("host-7", m), "host-7")
        self.assertEqual(hostalias.load_map(m), {REAL.lower(): "host-1", "other": "host-2"})

    def test_two_processes_alias_the_same_new_name_at_once(self) -> None:
        m = tmap()
        ctx = multiprocessing.get_context("fork")
        jobs = [(str(m), REAL if i % 2 == 0 else f"other{i % 4}") for i in range(16)]
        with ctx.Pool(8) as pool:
            got = pool.map(_alias_job, jobs)
        table = hostalias.load_map(m)
        self.assertEqual(len(table), 3)  # REAL, other1, other3: one entry each
        self.assertEqual(len(set(table.values())), 3)  # three distinct aliases
        self.assertEqual({got[i] for i in range(0, 16, 2)}, {table[REAL.lower()]})
        self.assertEqual(m.read_text(encoding="utf-8").count(REAL.lower()), 1)

    def test_a_missing_map_is_an_error_and_is_never_created(self) -> None:
        m = Path(tmpdir()) / "none.toml"
        with self.assertRaises(hostalias.HostMapError):
            hostalias.alias_of(REAL, m)
        with self.assertRaises(hostalias.HostMapError):
            hostalias.scrub_text("x", m)
        with self.assertRaises(hostalias.HostMapError):
            hostalias.scrub_bytes(b"x", m)
        with self.assertRaises(hostalias.HostMapError):
            privacy.private_strings(m)
        with mock.patch.dict(os.environ, {"MIMIR_HOST_MAP": str(m)}), \
                self.assertRaises(hostalias.HostMapError):
            Scrubber({}).text("any text")
        self.assertFalse(m.exists())  # nothing was created on the way

    def test_init_refuses_to_restart_numbering_over_stored_aliases(self) -> None:
        tmp = Path(tmpdir())
        db = make_store(tmp, "host-3", "0" * 64)
        m = tmp / "new" / "hosts.toml"
        with self.assertRaises(hostalias.HostMapError):
            hostalias.init_map(m, [db])
        self.assertFalse(m.exists())
        clean = make_store(Path(tmpdir()), REAL, "0" * 64)  # real names only: no alias in use
        self.assertTrue(hostalias.init_map(m, [clean]))
        self.assertFalse(hostalias.init_map(m, [db]))  # an existing map is left as it is
        self.assertEqual(hostalias.alias_of(REAL, m), "host-1")

    def test_map_and_lock_files_are_mode_600(self) -> None:
        m = tmap()
        hostalias.alias_of(REAL, m)
        for p in (m, hostalias.lock_path(m)):
            self.assertEqual(stat.S_IMODE(p.stat().st_mode), 0o600, p.name)

    def test_the_key_is_escaped(self) -> None:
        m = tmap()
        odd = 'a"b\\c d'
        self.assertEqual(hostalias.alias_of(odd, m), "host-1")
        self.assertEqual(hostalias.load_map(m), {odd.lower(): "host-1"})
        self.assertEqual(hostalias.alias_of(odd, m), "host-1")

    def test_scrub_text_any_case(self) -> None:
        m = tmap()
        self.assertEqual(hostalias.scrub_text(f"on {REAL}", m), f"on {REAL}")  # no name known yet
        hostalias.alias_of(REAL, m)
        self.assertEqual(hostalias.scrub_text(f"on {REAL.upper()} and {REAL}", m),
                         "on host-1 and host-1")
        self.assertEqual(hostalias.scrub_bytes(REAL.encode(), m), b"host-1")

    def test_facts_have_sources(self) -> None:
        facts = hostalias.host_facts()
        self.assertIn("kernel", facts)
        self.assertTrue(all(v["source"] and v["value"] for v in facts.values()))

    def test_scrubber_replaces_a_mapped_host_and_a_bare_login(self) -> None:
        m = tmap()
        hostalias.alias_of(REAL, m)
        with mock.patch.dict(os.environ, {"MIMIR_HOST_MAP": str(m)}):
            self.assertEqual(Scrubber({}).text(f"host {REAL}"), "host host-1")
            out = Scrubber({}).text(f"by {LOGIN} <{EMAIL}> in /home/{LOGIN}/x")
        self.assertNotIn(LOGIN, out.lower())
        self.assertNotIn(EMAIL, out)
        self.assertIn("$HOME/x", out)


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
            info["commands"][0].append("--tag=" + REAL.upper())
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
            cmd = s.db.execute("SELECT command_line FROM run").fetchone()[0]
            self.assertIn("--tag=host-1", cmd)  # registered before build_spec scrubs anything
            self.assertNotIn(REAL.lower(), cmd.lower())
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

    def test_every_text_column_is_listed(self) -> None:
        s = Store(Path(tmpdir()) / "x.db")
        listed = set(hostscrub.TEXT_COLUMNS) | set(hostscrub.EXEMPT_COLUMNS)
        self.assertFalse(set(hostscrub.TEXT_COLUMNS) & set(hostscrub.EXEMPT_COLUMNS))
        text = set()
        for (t,) in s.db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
            for col in s.db.execute(f'PRAGMA table_info("{t}")').fetchall():
                if col[2] not in ("INTEGER", "REAL"):
                    text.add((t, col[1]))
        self.assertEqual(text - listed, set(), "classify these columns in hostscrub")
        self.assertEqual(listed - text, set(), "listed columns that do not exist")

    def test_rewrite_columns_scrubs_every_listed_column(self) -> None:
        tmp, m = Path(tmpdir()), tmap()
        hostalias.alias_of(REAL, m)
        db = make_store(tmp, "host-1", "0" * 64)
        c = sqlite3.connect(db)
        planted = f"on {REAL.upper()} by {USER} {LOGIN} {EMAIL}"
        for table, col in hostscrub.TEXT_COLUMNS:
            c.execute(f'UPDATE "{table}" SET "{col}" = ?', (planted,))  # rows that exist
        c.execute("INSERT INTO flow_param VALUES ('c', 'host', 'k', ?, 'given', ?)",
                  (planted, planted))
        c.execute("INSERT INTO design_meta VALUES ('s', 'f', ?, ?, 'primary')", (planted, planted))
        c.execute("INSERT INTO flow_config VALUES ('c', ?, ?, 'reconstructed', 'full', ?)",
                  (planted, planted, planted))
        c.commit()
        c.close()
        strings = [REAL.lower(), USER]
        got = hostscrub.rewrite_columns(db, strings, m)
        self.assertIn("run.command_line", got)
        self.assertIn("flow_param.value", got)
        self.assertIn("flow_config.config_text_reconstructed", got)
        hostscrub.vacuum(db)  # no free page keeps the old text
        self.assertEqual(privacy.scan_db(db, strings + [LOGIN]), [])
        c = sqlite3.connect(db)
        for table, col in hostscrub.TEXT_COLUMNS:
            for (v,) in c.execute(f'SELECT "{col}" FROM "{table}"'):
                low = str(v).lower()
                for bad in (REAL.lower(), USER, LOGIN, EMAIL):
                    self.assertNotIn(bad, low, f"{table}.{col}")
        self.assertEqual(c.execute("SELECT value FROM flow_param").fetchone()[0],
                         "on host-1 by redacted user user@example.invalid")
        c.close()
        self.assertEqual(hostscrub.rewrite_columns(db, strings, m), {})  # idempotent

    def test_vacuum_leaves_no_free_page_residue(self) -> None:
        tmp, m = Path(tmpdir()), tmap()
        hostalias.alias_of(REAL, m)
        db = make_store(tmp, "host-1", "0" * 64)
        c = sqlite3.connect(db)
        c.execute("PRAGMA secure_delete = OFF")  # some builds zero freed pages by default
        c.execute("INSERT INTO flow_param VALUES ('c', 'host', 'k', ?, 'given', 's')",
                  ("x" * 3000 + REAL,))
        c.commit()
        c.execute("DELETE FROM flow_param")  # the page is free, the text is still in the file
        c.commit()
        c.close()
        strings = [REAL.lower()]
        self.assertEqual(privacy.scan_db(db, strings), [f"{db.name}:raw#0"])
        hostscrub.vacuum(db)
        self.assertEqual(privacy.scan_db(db, strings), [])

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
        # the second run sees the blob_scrub table: its columns are not blob references
        c = sqlite3.connect(db)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM blob_scrub").fetchone()[0], 1)
        c.close()

    def test_partition_and_analysis_rows_are_keyed_by_their_id(self) -> None:
        tmp, m = Path(tmpdir()), tmap()
        root = tmp / "blobs"
        hostalias.alias_of(REAL, m)
        old = blobs.put_bytes(root, f"labels {REAL}\n".encode())
        db = make_store(tmp, "host-1", "0" * 64)
        c = sqlite3.connect(db)
        c.execute("INSERT INTO partition (partition_id, algorithm, algorithm_version, params, "
                  "seed, slug, input_hash, n_objects, n_clusters, assignment_blob, origin) "
                  "VALUES ('p1','a','1','{}',1,'s','h',1,1,?,'o')", (old,))
        c.execute("INSERT INTO analysis_result VALUES ('a1','a','{}','f','sel',1,'h','1',?,'o')",
                  (old,))
        c.commit()
        c.close()
        new = hostscrub.reblob(db, root, [REAL.lower()], m)[old]
        c = sqlite3.connect(db)
        rows = c.execute("SELECT ref_table, ref_column, ref_key, scrubbed_from, blob_sha256 "
                         "FROM blob_scrub ORDER BY ref_table").fetchall()
        c.close()
        self.assertEqual(rows, [("analysis_result", "labels_blob", "a1", old, new),
                                ("partition", "assignment_blob", "p1", old, new)])

    def test_missing_blobs_are_counted(self) -> None:
        tmp = Path(tmpdir())
        db = make_store(tmp, "host-1", "0" * 64)
        self.assertEqual(hostscrub.missing_blobs(db, tmp / "blobs"), ["0" * 64])

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

    def test_extra_blobs_are_scanned_before_they_are_indexed_public(self) -> None:
        tmp = Path(tmpdir())
        root = tmp / "blobs"
        dirty = blobs.put_bytes(root, b"seen on " + REAL.encode())
        home = blobs.put_bytes(root, f"in /home/{USER}/x".encode())
        clean = blobs.put_bytes(root, b"nothing here")
        idx = tmp / "idx"
        idx.mkdir()
        write_xz(idx / "blobs.tsv.xz", b"")
        n = hostscrub.update_blob_index(idx, {}, root, "arc", {dirty, home, clean}, [REAL.lower()])
        ref = load_blob_index(idx)
        self.assertEqual(n, 3)
        self.assertEqual((ref[dirty].visibility, ref[home].visibility, ref[clean].visibility),
                         ("withheld", "withheld", "public"))


class PrivacyTests(unittest.TestCase):
    def test_finds_a_planted_string_everywhere(self) -> None:
        tmp = Path(tmpdir())
        strings = [REAL.lower()]
        root = tmp / "blobs"
        sha = blobs.put_bytes(root, f"x {REAL.upper()}".encode())
        db = make_store(tmp, REAL, sha)
        found = privacy.scan_db(db, strings)
        self.assertEqual(len(found), 2)  # the cell and the raw bytes of the file
        self.assertIn("run.host", found[0])
        n, hits = privacy.scan_blobs(root, strings)
        self.assertEqual((n, len(hits)), (1, 1))
        (tmp / "out").mkdir()
        (tmp / "out" / "a.csv").write_text(f"h\n{REAL}\n", encoding="utf-8")
        (tmp / "out" / "b.sql.xz").write_bytes(lzma.compress(REAL.encode()))
        got = privacy.scan_tree(tmp / "out", strings)
        self.assertTrue(any(h.startswith("a.csv") for h in got))
        self.assertTrue(any(h.startswith("b.sql.xz") for h in got))

    def test_clean_store_has_no_hit(self) -> None:
        tmp = Path(tmpdir())
        db = make_store(tmp, "host-1", "0" * 64)
        self.assertEqual(privacy.scan_db(db, [REAL.lower()]), [])

    def test_email_and_bare_login_are_hits_without_a_private_string(self) -> None:
        for text in (f"mail {EMAIL}", f"by {LOGIN}", f"at /home/{USER}/x"):
            self.assertEqual(len(privacy.scan_member("m", "", text.encode(), [])), 1, text)
        self.assertEqual(privacy.scan_member("m", "", b"host-1 and $HOME/x", []), [])

    def test_short_names_are_not_dropped(self) -> None:
        strings = privacy.private_strings(tmap())
        with mock.patch.dict(os.environ, {"MIMIR_PRIVATE_STRINGS": "ab"}):
            strings = privacy.private_strings(tmap())
        self.assertIn("ab", strings)
        i = strings.index("ab")
        self.assertEqual(privacy.hits_in(b"user ab here", strings).count(i), 1)
        self.assertNotIn(i, privacy.hits_in(b"cabinet table", strings))

    def test_looks_inside_gz_zip_npz_tar_and_nested(self) -> None:
        strings = [REAL.lower()]
        raw = f"x {REAL}".encode()
        zbuf = io.BytesIO()
        with zipfile.ZipFile(zbuf, "w") as zf:
            zf.writestr("a.txt", raw)
        tbuf = io.BytesIO()
        with tarfile.open(fileobj=tbuf, mode="w") as tf:
            ti = tarfile.TarInfo("m/inner.txt")
            ti.size = len(raw)
            tf.addfile(ti, io.BytesIO(raw))
        cases = {
            "a.gz": gzip.compress(raw), "a.xz": lzma.compress(raw),
            "a.zip": zbuf.getvalue(), "a.npz": zbuf.getvalue(), "a.tar": tbuf.getvalue(),
            "a.txt.gz.xz": lzma.compress(gzip.compress(raw)),
            "n.zip": _zip_of("b.txt.xz", lzma.compress(raw)),
        }
        for name, data in cases.items():
            hits = privacy.scan_member("p", name, data, strings)
            self.assertTrue(any(h.endswith("#0") for h in hits), (name, hits))

    def test_an_undecodable_member_is_a_hit(self) -> None:
        for name, data in (("a.xz", b"not xz at all"), ("a.gz", b"\x1f\x8bbroken"),
                           ("a.zip", b"PK\x03\x04junk"), ("a.npz", b"junk"),
                           ("a.xz", lzma.compress(b"clean text")[:-8])):
            hits = privacy.scan_member("p", name, data, [REAL.lower()])
            self.assertTrue(any("undecodable" in h for h in hits), (name, hits))

    def test_tar_xz_members_are_read_and_a_clean_one_is_clean(self) -> None:
        tmp = Path(tmpdir())
        for body, expected in ((f"x {REAL}".encode(), True), (b"clean", False)):
            path = tmp / f"t{expected}.tar.xz"
            with tarfile.open(path, "w:xz") as tf:
                ti = tarfile.TarInfo("blobs/ab/inner.xz")
                data = lzma.compress(body)
                ti.size = len(data)
                tf.addfile(ti, io.BytesIO(data))
            self.assertEqual(bool(privacy.scan_file(path, [REAL.lower()])), expected)

    @skip_without("pyarrow")
    def test_parquet_is_read(self) -> None:
        import pyarrow as pa
        import pyarrow.parquet as pq

        tmp = Path(tmpdir())
        pq.write_table(pa.table({"host": [f"on {REAL}"]}), str(tmp / "a.parquet"))
        pq.write_table(pa.table({"host": ["host-1"]}), str(tmp / "b.parquet"))
        self.assertTrue(any(".host#0" in h for h in
                            privacy.scan_file(tmp / "a.parquet", [REAL.lower()])))
        self.assertEqual(privacy.scan_file(tmp / "b.parquet", [REAL.lower()]), [])

    def test_parquet_without_pyarrow_is_not_scanned_never_clean(self) -> None:
        with mock.patch.dict("sys.modules", {"pyarrow": None, "pyarrow.parquet": None}):
            hits = privacy.scan_member("p", "a.parquet", b"PAR1", [REAL.lower()])
        self.assertTrue(any("not scanned" in h for h in hits), hits)

    def test_cli_exit_codes_and_no_name_in_the_output(self) -> None:
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

    def test_cli_without_a_map_is_an_error_not_a_zero(self) -> None:
        tmp = Path(tmpdir())
        db = make_store(tmp, "host-1", "0" * 64)
        ns = argparse.Namespace(db=[str(db)], path=[], blobs=None, index=None,
                                map=str(tmp / "none.toml"), max_list=5)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(_cmd_privacy_check(ns), 2)

    def test_host_alias_cli_end_to_end(self) -> None:
        tmp, m = Path(tmpdir()), tmap()
        root = tmp / "blobs"
        sha = blobs.put_bytes(root, f"x {REAL}".encode())
        db = make_store(tmp, REAL, sha)
        ns = argparse.Namespace(db=[str(db)], dir=None, map=str(m), blobs=str(root), index=None,
                                archive="-", init=False)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(_cmd_host_alias(ns), 0)
        self.assertEqual(privacy.scan_db(db, [REAL.lower()]), [])
        self.assertEqual(privacy.scan_blobs(root, [REAL.lower()])[1],
                         [f"blob {sha}#0"])  # the old blob stays on disk

    def test_host_alias_cli_needs_init_for_a_missing_map(self) -> None:
        tmp = Path(tmpdir())
        db = make_store(tmp, REAL, "0" * 64)
        m = tmp / "sub" / "hosts.toml"
        ns = argparse.Namespace(db=[str(db)], dir=None, map=str(m), blobs=None, index=None,
                                archive="-", init=False)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(_cmd_host_alias(ns), 2)
        self.assertFalse(m.exists())
        ns.init = True
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(_cmd_host_alias(ns), 0)
        self.assertTrue(m.exists())

    def test_host_alias_cli_indexes_extra_blobs_after_a_scan(self) -> None:
        tmp, m = Path(tmpdir()), tmap()
        root = tmp / "blobs"
        hostalias.alias_of(REAL, m)
        late = blobs.put_bytes(root, b"clean late blob")
        db = make_store(tmp, "host-1", late)
        idx = tmp / "idx"
        idx.mkdir()
        write_xz(idx / "blobs.tsv.xz", b"")
        ns = argparse.Namespace(db=[str(db)], dir=None, map=str(m), blobs=str(root),
                                index=str(idx), archive="arc", init=False)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(_cmd_host_alias(ns), 0)
        self.assertEqual(load_blob_index(idx)[late].visibility, "public")


def _zip_of(name: str, data: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(name, data)
    return buf.getvalue()


if __name__ == "__main__":
    unittest.main()
