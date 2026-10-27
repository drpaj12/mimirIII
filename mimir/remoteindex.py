"""`mimir remote index`: build data/remote/ (archives.toml, manifests, blobs.tsv.xz) from an
archive directory (read only) and the blob store. Spec: docs/specs/2026-10-27-mimir-remote-data.md.
"""

from __future__ import annotations

import hashlib
import re
import tarfile
import tomllib
from pathlib import Path

from mimir import blobs
from mimir.remote import (
    Archive,
    Entry,
    dump_archives,
    load_archives,
    manifest_text,
    parse_manifest_rows,
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
PRIVATE = {"mimir-meta-papers", "mimir-mcnc-originals", "mimir-mcnc-originals-r2",
           "mimir-snapshot-2026-10-27"}
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
        if p.is_file():
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
    return table.get(name, "derived")


def load_verdicts(path: Path | None) -> dict[str, str]:
    """archive name -> verdict from licences.toml (keys `archive`, with or without `.tar.xz`)."""
    if path is None or not path.exists():
        return {}
    out = {}
    for row in tomllib.loads(path.read_text(encoding="utf-8")).get("archive", []):
        out[str(row["archive"]).removesuffix(".tar.xz")] = str(row["verdict"])
    return out


def build_archives(date_dir: Path, idx: Path, verdicts: dict[str, str]) -> list[Archive]:
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
        write_xz(idx / "manifests" / f"{name}.tsv.xz", manifest_text(entries))
        sha = sums.get(item.name, "") if form == "tar.xz" else ""
        size = item.stat().st_size if form == "tar.xz" else 0
        private = name in PRIVATE or verdicts.get(name, "") == "do-not-host"
        arch = Archive(name, date_dir.name, item.name, form, kind_of(name), source_of(name),
                       f"manifests/{name}.tsv.xz", "private" if private else "public",
                       _licence_status(name, verdicts), sha, size,
                       sum(1 for e in entries if e.type == "f"))
        prev = old.get(name)
        if prev is not None:
            arch = _keep_public(arch, prev)
        out.append(arch)
    return out


def _keep_public(arch: Archive, prev: Archive) -> Archive:
    from dataclasses import replace

    return replace(arch, urls=prev.urls, public_file=prev.public_file,
                   public_sha256=prev.public_sha256, public_size=prev.public_size,
                   public_manifest=prev.public_manifest, public_members=prev.public_members,
                   public_dropped=prev.public_dropped, public_scrubbed=prev.public_scrubbed)


def _manifest(date_dir: Path, item: Path, name: str, form: str) -> list[Entry]:
    if form == "dir":
        return manifest_from_dir(item)
    f = date_dir / f"MANIFEST-{name}.tsv"
    return read_f_manifest(f) if f.exists() else manifest_from_tar(item)


def build_blob_index(store: Path, date_dir: Path, archives: list[Archive]) -> bytes:
    """sha256, xz bytes, archive: the store's blobs, plus members of the blob tarballs."""
    rows: dict[str, tuple[int, str]] = {}
    for sha in blobs.all_hashes(store):
        rows[sha] = (blobs.blob_path(store, sha).stat().st_size, "-")
    for arch in archives:
        if arch.kind != "blobs":
            continue
        with tarfile.open(date_dir / arch.file, "r|xz") as tf:
            for ti in tf:
                stem = Path(ti.name).name
                if ti.isreg() and stem.endswith(".xz") and re.fullmatch(r"[0-9a-f]{64}", stem[:-3]):
                    rows[stem[:-3]] = (ti.size, arch.name)
    text = "".join(f"{s}\t{n}\t{a}\n" for s, (n, a) in sorted(rows.items()))
    return text.encode()


def run_index(date_dir: Path, idx: Path, store: Path, verdicts_path: Path | None) -> list[Archive]:
    archives = build_archives(date_dir, idx, load_verdicts(verdicts_path))
    (idx / "archives.toml").write_text(dump_archives(archives), encoding="utf-8")
    write_xz(idx / "blobs.tsv.xz", build_blob_index(store, date_dir, archives))
    return archives
