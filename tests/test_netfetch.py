from __future__ import annotations

import contextlib
import hashlib
import http.server
import io
import lzma
import tarfile
import threading
import unittest
from collections.abc import Iterator
from pathlib import Path
from unittest import mock

from mimir import benchbulk, benchpub, netfetch, remote
from tests.helpers import tmpdir
from tests.test_benchpub import META, world


class FakeHost(http.server.BaseHTTPRequestHandler):
    script: list[tuple[int, dict[str, str]]] = []
    body = b"hello"
    hits = 0

    def do_GET(self) -> None:
        cls = type(self)
        cls.hits += 1
        code, headers = cls.script.pop(0) if cls.script else (200, {})
        self.send_response(code)
        for k, v in headers.items():
            self.send_header(k, v)
        data = cls.body if code == 200 else b""
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args: object) -> None:
        pass


@contextlib.contextmanager
def host(script: list[tuple[int, dict[str, str]]], body: bytes = b"hello"
         ) -> Iterator[tuple[str, type[FakeHost]]]:
    handler = type("H", (FakeHost,), {"script": list(script), "body": body, "hits": 0})
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}/x", handler
    finally:
        srv.shutdown()
        srv.server_close()
        thread.join()


class Backoff(unittest.TestCase):
    def setUp(self) -> None:
        self.sleeps: list[float] = []
        self.clock = [0.0]

        def sleep(s: float) -> None:
            self.sleeps.append(s)
            self.clock[0] += s

        for name, val in (("_sleep", sleep), ("_now", lambda: self.clock[0]),
                          ("_rand", lambda: 1.0)):
            p = mock.patch.object(netfetch, name, val)
            p.start()
            self.addCleanup(p.stop)
        netfetch._last_start = float("-inf")
        netfetch._override = None
        self.addCleanup(setattr, netfetch, "_override", None)
        env = mock.patch.dict("os.environ", {"MIMIR_FETCH_MIN_SPACING": "0"})
        env.start()
        self.addCleanup(env.stop)

    def get(self, url: str) -> bytes:
        with contextlib.redirect_stderr(io.StringIO()) as err, netfetch.open_url(url) as r:
            data: bytes = r.read()
        self.err = err.getvalue()
        return data

    def test_retry_after_honoured(self) -> None:
        script = [(429, {"Retry-After": "7"}), (503, {"Retry-After": "2"}), (200, {})]
        with host(script) as (url, _):
            self.assertEqual(self.get(url), b"hello")
        self.assertEqual(self.sleeps, [7.0, 2.0])
        self.assertIn("HTTP 429", self.err)
        self.assertIn("retry 1 of 6", self.err)

    def test_exponential_without_header_and_cap(self) -> None:
        env = {"MIMIR_FETCH_BACKOFF_CAP": "12"}
        none: dict[str, str] = {}
        script = [(429, none)] * 4 + [(200, none)]
        with mock.patch.dict("os.environ", env), host(script) as (url, _):
            self.get(url)
        self.assertEqual(self.sleeps, [5.0, 10.0, 12.0, 12.0])

    def test_jitter_range(self) -> None:
        pol = netfetch.Policy()
        with mock.patch.object(netfetch, "_rand", lambda: 0.0):
            self.assertEqual(netfetch.wait_for(1, None, pol), 5.0)
        self.assertEqual(netfetch.wait_for(1, None, pol), 10.0)

    def test_retry_after_capped(self) -> None:
        self.assertEqual(netfetch.wait_for(0, "9999", netfetch.Policy()), 300.0)
        self.assertIsNone(netfetch.retry_after("soon"))
        date = netfetch.retry_after("Thu, 01 Jan 1970 00:01:40 GMT", 0.0)
        self.assertEqual(date, 100.0)

    def test_gives_up_after_retries(self) -> None:
        env = {"MIMIR_FETCH_RETRIES": "2"}
        with (mock.patch.dict("os.environ", env), host([(429, {"Retry-After": "1"})] * 5) as
              (url, srv), self.assertRaises(OSError)):
            self.get(url)
        self.assertEqual(self.sleeps, [1.0, 1.0])
        self.assertEqual(srv.hits, 3)

    def test_other_errors_not_retried(self) -> None:
        with host([(404, {})]) as (url, _), self.assertRaises(OSError):
            self.get(url)
        self.assertEqual(self.sleeps, [])

    def test_min_spacing(self) -> None:
        netfetch.set_policy(min_spacing=2.0)
        with host([]) as (url, _):
            self.get(url)
            self.get(url)
        self.assertEqual(self.sleeps, [2.0])

    def test_download_retries_through_fetch_error_path(self) -> None:
        dest = Path(tmpdir()) / "d"
        sha = hashlib.sha256(b"hello").hexdigest()
        script = [(429, {"Retry-After": "1"}), (200, {})]
        with host(script) as (url, _), contextlib.redirect_stderr(io.StringIO()):
            remote.download(url, dest, sha, 5)
        self.assertEqual(dest.read_bytes(), b"hello")
        with (host([(429, {"Retry-After": "1"})] * 9) as (url, _),
              contextlib.redirect_stderr(io.StringIO()), self.assertRaises(remote.FetchError)):
            remote.download(url, dest, sha, 5)

    def test_bad_env_is_an_error(self) -> None:
        env = {"MIMIR_FETCH_RETRIES": "many"}
        with mock.patch.dict("os.environ", env), self.assertRaises(ValueError):
            netfetch.policy()


class Bulk(unittest.TestCase):
    def setUp(self) -> None:
        self.idx, self.store, self.stage, self.sha = world()
        self.report = benchpub.run_stage(self.idx, self.store, self.stage, META, "2026-11-02")
        self.rec = (self.stage / "index/bench" / benchbulk.RECORD)

    def test_stage_writes_archive_and_record(self) -> None:
        arch = self.stage / benchbulk.BULK_FILE
        self.assertTrue(arch.is_file())
        text = self.rec.read_text(encoding="utf-8")
        self.assertIn(remote.sha256_path(arch), text)
        self.assertTrue(any(ln.startswith("bulk archive:") for ln in self.report))
        self.assertTrue(any(ln.startswith("note: copy") for ln in self.report))
        sums = (self.stage / benchpub.SUMS).read_text(encoding="utf-8")
        self.assertIn(benchbulk.BULK_FILE, sums)

    def test_archive_is_deterministic(self) -> None:
        first = (self.stage / benchbulk.BULK_FILE).read_bytes()
        benchpub.run_stage(self.idx, self.store, self.stage, META, "2026-11-02")
        self.assertEqual((self.stage / benchbulk.BULK_FILE).read_bytes(), first)

    def test_fetch_all_over_http(self) -> None:
        (self.idx / benchbulk.RECORD).write_bytes(self.rec.read_bytes())
        data = (self.stage / benchbulk.BULK_FILE).read_bytes()
        cache = Path(tmpdir())
        with mock.patch.dict("os.environ", {"MIMIR_FETCH_MIN_SPACING": "0"}):
            netfetch._override = None
            with host([(429, {"Retry-After": "0"})], data) as (url, srv):
                base = url.rsplit("/", 1)[0]
                # the fake host serves every path; the archive path is <base>/bulk/...
                loc = remote.Locations(Path(tmpdir()), None, base, cache)
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(benchbulk.fetch_all(self.idx, loc), (1, 0))
                self.assertEqual(srv.hits, 2)
            self.assertEqual(benchbulk.fetch_all(self.idx, loc), (0, 1))  # cached archive
        out = remote.fetch_blob(self.idx, remote.Locations(Path(tmpdir()), None, None, cache),
                                self.sha, Path(tmpdir()) / "o")
        self.assertEqual(hashlib.sha256(out.read_bytes()).hexdigest(), self.sha)

    def test_unpack_refuses_bad_members(self) -> None:
        (self.idx / benchbulk.RECORD).write_bytes(self.rec.read_bytes())
        for name, body in (("../evil", b"x"), (f"blobs/{self.sha[:2]}/{self.sha}.xz", b"junk"),
                           ("blobs/aa/" + "a" * 64 + ".xz", lzma.compress(b"x"))):
            buf = io.BytesIO()
            with tarfile.open(fileobj=buf, mode="w") as tf:
                ti = tarfile.TarInfo(name)
                ti.size = len(body)
                tf.addfile(ti, io.BytesIO(body))
            arch = Path(tmpdir()) / "a.tar.xz"
            arch.write_bytes(lzma.compress(buf.getvalue()))
            with self.assertRaises(remote.FetchError, msg=name):
                benchbulk.unpack(arch, self.idx, Path(tmpdir()))

    def test_sha_mismatch_not_unpacked(self) -> None:
        (self.idx / benchbulk.RECORD).write_bytes(self.rec.read_bytes())
        cache = Path(tmpdir())
        with host([], b"not the archive") as (url, srv):
            loc = remote.Locations(Path(tmpdir()), None, url.rsplit("/", 1)[0], cache)
            with self.assertRaises(remote.FetchError):
                benchbulk.fetch_all(self.idx, loc)
        self.assertFalse((cache / "blobs").exists())
