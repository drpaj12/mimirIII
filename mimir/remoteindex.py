"""`mimir remote index`: build data/remote/ (archives.toml, manifests, blobs.tsv.xz) from an
archive directory (read only) and the blob store. Spec: docs/specs/2026-10-27-mimir-remote-data.md.
"""

from __future__ import annotations

import hashlib
import lzma
import re
import sqlite3
import tarfile
import tomllib
from collections import Counter
from dataclasses import replace
from pathlib import Path

from mimir import blobs
from mimir.remote import (
    Archive,
    Entry,
    blob_columns,
    dump_archives,
    load_archives,
    manifest_text,
    parse_manifest_rows,
    read_tsv_xz,
    sha256_path,
    write_xz,
)

DATE_SOURCES = {
    "loki-exp2-data": "~/odin3-ws/work/loki-exp2-data",
    "loki-exp3-data": "~/odin3-ws/work/loki-exp3-data",
    "loki-exp4-data": "~/odin3-ws/work/loki-exp4-data",
    "loki-exp5-data": "~/odin3-ws/work/loki-exp5-data",
    "loki-exp6-data": "~/odin3-ws/work/loki-exp6-data",
    "loki-veval-exp": "~/odin3-ws/work/loki-veval-exp",
    "mimir-meta-papers": "~/odin3-ws/work/mimir-papers (earlier archive)",
    "mimir-mcnc-originals": "mcnc-originals store of the Mimir originals lane",
    "mimir-mcnc-originals-r2": "mcnc-originals store of the Mimir originals lane (fix round 1)",
    "odin3-writer-run": "~/odin3-ws/work/writer-run",
    "odin3-vtr-gfx": "~/odin3-ws/work/vtr-gfx",
    "odin3-spike-abc": "~/odin3-ws/work/spike-abc",
    "norns-placers-fix1-runs": "~/odin3-ws/work/norns-exp/runs-fix1",
}
# Private: never staged, never given a URL, no manifest or member in the committed index.
# The three odin3-* archives are Odin development intermediates, not dataset (controller
# decision 2026-10-27).
PRIVATE = {"mimir-meta-papers", "mimir-mcnc-originals", "mimir-mcnc-originals-r2",
           "mimir-snapshot-2026-10-27", "odin3-spike-abc", "odin3-writer-run", "odin3-vtr-gfx"}
# Run sources (run.source) whose runs belong to a private archive.
PRIVATE_RUN_SOURCES = {"mcnc-originals", "mimir-meta-papers", "mimir-snapshot-2026-10-27"}
_HOME = re.compile(r"/home/[^/\s]+(/odin3-ws)?")


def scrub_target(text: str) -> str:
    """A link target with the home dir written `$HOME` (`$WS` for the workspace)."""
    return _HOME.sub(lambda m: "$WS" if m.group(1) else "$HOME", text)


def kind_of(name: str) -> str:
    table = (("loki-", "loki-data"), ("norns-", "norns-runs"), ("odin3-", "odin3-work"),
             ("mimir-snapshot-", "snapshot"), ("mimir-mcnc-", "originals"),
             ("mimir-meta-", "papers"))
    for prefix, kind in table:
        if name.startswith(prefix):
            return "blobs" if name.endswith("-blobs") else kind
    raise ValueError(f"no kind for {name}")


def source_of(name: str) -> str:
    if name in DATE_SOURCES:
        return DATE_SOURCES[name]
    if name.startswith("norns-runs-"):
        return "~/odin3-ws/work/norns-exp/runs"
    if name.startswith("norns-placers-d4-temp-"):
        return "/tmp/claude-1000/npl-" + name.rsplit("-", 1)[1]
    if name.startswith("norns-placers-d4-"):
        return "/tmp/claude-1000/npl-TX55/" + name[len("norns-placers-d4-"):]
    if name.startswith("mimir-snapshot-"):
        return "mimir snapshot dir of the Mimir lane 2"
    return ""


def read_f_manifest(path: Path) -> list[Entry]:
    rows = [line.split("\t") for line in path.read_text(encoding="utf-8").split("\n") if line]
    out = []
    for e in parse_manifest_rows(rows):
        out.append(e._replace(sha=scrub_target(e.sha)) if e.type == "l" else e)
    return out


def manifest_from_tar(path: Path) -> list[Entry]:
    out = []
    with tarfile.open(path, "r|xz") as tf:
        for ti in tf:
            name = "/".join(p for p in ti.name.split("/") if p not in ("", "."))
            if ti.isdir():
                out.append(Entry(name, "d", 0, "-"))
            elif ti.isreg():
                src = tf.extractfile(ti)
                assert src is not None
                h = hashlib.sha256()
                while chunk := src.read(1 << 20):
                    h.update(chunk)
                out.append(Entry(name, "f", ti.size, h.hexdigest()))
            else:
                out.append(Entry(name, "l", 0, scrub_target(ti.linkname or "-")))
    return out


def manifest_from_dir(path: Path) -> list[Entry]:
    out = []
    for p in sorted(path.rglob("*")):
        rel = p.relative_to(path).as_posix()
        if p.is_file() and not p.is_symlink():
            out.append(Entry(rel, "f", p.stat().st_size, sha256_path(p)))
    return out


def read_sums(date_dir: Path) -> dict[str, str]:
    sums = {}
    for line in (date_dir / "SHA256SUMS").read_text(encoding="utf-8").split("\n"):
        if line.strip():
            sha, rel = line.split(None, 1)
            sums[rel.strip().lstrip("*")] = sha
    return sums


def _licence_status(name: str, table: dict[str, str]) -> str:
    return table.get(name, "pending")


def load_verdicts(path: Path | None) -> dict[str, str]:
    """archive name -> verdict from licences.toml (keys `archive`, with or without `.tar.xz`)."""
    if path is None or not path.exists():
        return {}
    out = {}
    for row in tomllib.loads(path.read_text(encoding="utf-8")).get("archive", []):
        out[str(row["archive"]).removesuffix(".tar.xz")] = str(row["verdict"])
    return out


def build_archives(date_dir: Path, idx: Path, verdicts: dict[str, str],
                   priv: Path | None = None, notes: list[str] | None = None) -> list[Archive]:
    """The archives of a date dir. Public manifests are written under idx; a private archive's
    manifest goes to `priv/manifests` (local, never committed) and its row carries no manifest,
    source or member count."""
    old = load_archives(idx) if (idx / "archives.toml").exists() else {}
    sums = read_sums(date_dir)
    out = []
    for item in sorted(date_dir.iterdir()):
        if item.name.endswith(".tar.xz"):
            name, form = item.name.removesuffix(".tar.xz"), "tar.xz"
        elif item.is_dir() and item.name.startswith("mimir-snapshot-"):
            name, form = item.name, "dir"
        else:
            continue
        entries = _manifest(date_dir, item, name, form)
        private = name in PRIVATE or verdicts.get(name, "") == "do-not-host"
        if form == "tar.xz":
            if item.name not in sums:
                raise ValueError(f"no SHA256SUMS entry for {item.name} in {date_dir.name}")
            sha, size = sums[item.name], item.stat().st_size
        else:
            sha, size = "", 0
        if private:
            if priv is None:
                raise ValueError(f"{name} is private: give a private manifest dir")
            write_xz(priv / "manifests" / f"{name}.tsv.xz", manifest_text(entries))
            arch = Archive(name, date_dir.name, item.name, form, kind_of(name), "", "",
                           "private", "private", sha, size, 0)
        else:
            write_xz(idx / "manifests" / f"{name}.tsv.xz", manifest_text(entries))
            arch = Archive(name, date_dir.name, item.name, form, kind_of(name), source_of(name),
                           f"manifests/{name}.tsv.xz", "public",
                           _licence_status(name, verdicts), sha, size,
                           sum(1 for e in entries if e.type == "f"))
            prev = old.get(name)
            if prev is not None:
                arch = _keep_public(arch, prev, notes)
        out.append(arch)
    return out


def _keep_public(arch: Archive, prev: Archive, notes: list[str] | None = None) -> Archive:
    """Carry the repack record over from the old index. A master whose sha256 changed makes
    the repack stale: its public_* fields are cleared (urls are kept) and a note says so."""
    if prev.sha256 != arch.sha256 and (prev.public_sha256 or prev.public_manifest):
        if notes is not None:
            notes.append(f"{arch.name}: master sha256 changed; cleared public_sha256 and "
                         "public_manifest (the repack is stale, run publish-plan again)")
        return replace(arch, urls=prev.urls)
    return replace(arch, urls=prev.urls, public_file=prev.public_file,
                   public_sha256=prev.public_sha256, public_size=prev.public_size,
                   public_manifest=prev.public_manifest, public_members=prev.public_members,
                   public_dropped=prev.public_dropped, public_scrubbed=prev.public_scrubbed)


def _manifest(date_dir: Path, item: Path, name: str, form: str) -> list[Entry]:
    if form == "dir":
        return manifest_from_dir(item)
    f = date_dir / f"MANIFEST-{name}.tsv"
    return read_f_manifest(f) if f.exists() else manifest_from_tar(item)


def raw_size(xz_bytes: bytes) -> int:
    """Decompressed size of an xz blob, counted in chunks (never held whole)."""
    dec = lzma.LZMADecompressor(format=lzma.FORMAT_XZ)
    total, data = 0, xz_bytes
    while True:
        out = dec.decompress(data, max_length=1 << 20)
        total += len(out)
        if dec.eof:
            return total
        if not out and dec.needs_input:
            raise ValueError("truncated xz blob")
        data = b""


def db_blob_refs(dbs: list[Path]) -> tuple[set[str], set[str]]:
    """(shas used by a public row, shas used only by runs of a private source) of the stores,
    read only. A blob column is any column whose name holds `blob`."""
    used: set[str] = set()
    private: set[str] = set()
    for path in dbs:
        db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            for table, col in blob_columns(db):
                if table == "run_artifact":
                    sql = (f'SELECT a."{col}", r.source FROM run_artifact a '
                           "LEFT JOIN run r ON r.run_id = a.run_id")
                    for sha, src in db.execute(sql):
                        if sha:
                            (private if src in PRIVATE_RUN_SOURCES else used).add(str(sha))
                else:
                    sql = f'SELECT "{col}" FROM "{table}" WHERE "{col}" IS NOT NULL'
                    used.update(str(v) for (v,) in db.execute(sql) if v)
        finally:
            db.close()
    return used, private - used


def private_shas(priv: Path | None, archives: list[Archive]) -> dict[str, set[str]]:
    """archive name -> file shas of its local manifest, for each private archive."""
    out: dict[str, set[str]] = {}
    if priv is None:
        return out
    for arch in archives:
        path = priv / "manifests" / f"{arch.name}.tsv.xz"
        if arch.private and path.is_file():
            out[arch.name] = {e.sha for e in parse_manifest_rows(read_tsv_xz(path))
                              if e.type == "f"}
    return out


def blob_visibility(sha: str, archive: str, used: set[str], priv_used: set[str],
                    traced: set[str], public_tars: set[str]) -> str:
    """public, private or orphan. A blob that is a file of a private archive, or that only
    runs of a private source use, is private. A blob nothing uses is an orphan, unless a
    public blob tarball holds it."""
    if sha in traced:
        return "private"
    if sha in used:
        return "public"
    if sha in priv_used:
        return "private"
    return "public" if archive in public_tars else "orphan"


def build_blob_index(store: Path, date_dir: Path, archives: list[Archive],
                     dbs: list[Path] | None = None, priv: Path | None = None
                     ) -> tuple[bytes, Counter[str]]:
    """sha256, xz bytes, raw bytes, archive, visibility: the store's blobs, plus members of
    the blob tarballs. Also the count per visibility (and `traced-to:<archive>`)."""
    rows: dict[str, tuple[int, int, str]] = {}
    for sha in blobs.all_hashes(store):
        data = blobs.blob_path(store, sha).read_bytes()
        rows[sha] = (len(data), raw_size(data), "-")
    for arch in archives:
        if arch.kind != "blobs":
            continue
        with tarfile.open(date_dir / arch.file, "r|xz") as tf:
            for ti in tf:
                stem = Path(ti.name).name
                if ti.isreg() and stem.endswith(".xz") and re.fullmatch(r"[0-9a-f]{64}", stem[:-3]):
                    src = tf.extractfile(ti)
                    assert src is not None
                    data = src.read()
                    rows[stem[:-3]] = (ti.size, raw_size(data), arch.name)
    used, priv_used = db_blob_refs(dbs or [])
    by_arch = private_shas(priv, archives)
    traced = set().union(*by_arch.values()) if by_arch else set()
    public_tars = {a.name for a in archives if a.kind == "blobs" and not a.private}
    counts: Counter[str] = Counter()
    lines = []
    for sha, (nx, nr, arch_name) in sorted(rows.items()):
        vis = blob_visibility(sha, arch_name, used, priv_used, traced, public_tars)
        counts[vis] += 1
        for name, shas in by_arch.items():
            if sha in shas:
                counts[f"traced-to:{name}"] += 1
        lines.append(f"{sha}\t{nx}\t{nr}\t{arch_name}\t{vis}\n")
    return "".join(lines).encode(), counts


def run_index(date_dir: Path, idx: Path, store: Path, verdicts_path: Path | None,
              priv: Path | None = None, dbs: list[Path] | None = None,
              report: list[str] | None = None) -> list[Archive]:
    notes: list[str] = []
    archives = build_archives(date_dir, idx, load_verdicts(verdicts_path), priv, notes)
    (idx / "archives.toml").write_text(dump_archives(archives), encoding="utf-8")
    data, counts = build_blob_index(store, date_dir, archives, dbs, priv)
    write_xz(idx / "blobs.tsv.xz", data)
    if report is not None:
        report += notes
        report += [f"blobs {k}: {v}" for k, v in sorted(counts.items())]
    return archives
