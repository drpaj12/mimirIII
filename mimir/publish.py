"""`mimir remote publish-plan`: what to upload, the public repack, and the staged tree.

Nothing is uploaded and nothing is deleted. The F: archives stay the private masters; a public
archive is a repack made from the master. Spec: docs/specs/2026-10-27-mimir-remote-data.md."""

from __future__ import annotations

import gzip
import hashlib
import io
import lzma
import re
import shutil
import subprocess
import tarfile
from dataclasses import dataclass, field, replace
from pathlib import Path

from mimir import blobs
from mimir.licscan import (
    drop_glob,
    load_table,
    notice,
    rule_hits,
    texts_for,
    unmatched_design_files,
)
from mimir.meta import Rule, load_licence_rules
from mimir.remote import (
    Archive,
    Entry,
    dump_archives,
    index_dir,
    load_archives,
    load_blob_index,
    manifest_text,
    read_manifest,
    sha256_path,
    write_xz,
)

HOME_RE = re.compile(rb"/home/[A-Za-z0-9_.-]+(/odin3-ws)?")
USER_RE = re.compile(rb"\bjamiespa\b")
DROP_DIRS = (".venv", "__pycache__")
DROP_SUFFIXES = (".pkl", ".db", ".lock", ".sh", ".pdf")
MIN_FREE_GB = 30
MAX_MEMBER = 1 << 30


class PlanError(Exception):
    """A request the plan refuses (private archive, pending licence, no space)."""


@dataclass
class RepackStats:
    dropped: list[tuple[str, str]] = field(default_factory=list)  # (member, reason)
    scrubbed: list[str] = field(default_factory=list)
    members: list[Entry] = field(default_factory=list)


def has_home(data: bytes) -> bool:
    return bool(HOME_RE.search(data) or USER_RE.search(data))


def scrub_bytes(data: bytes) -> bytes:
    """Text with `/home/<user>/odin3-ws` as `$WS`, other `/home/<user>` as `$HOME`, and the user
    name as `user`."""
    data = HOME_RE.sub(lambda m: b"$WS" if m.group(1) else b"$HOME", data)
    return USER_RE.sub(b"user", data)


def _is_text(data: bytes) -> bool:
    if b"\x00" in data[:8192]:
        return False
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def process_bytes(name: str, data: bytes, scrub: bool = True) -> tuple[bytes | None, str]:
    """(new content or None to drop, note). A `.gz` or `.xz` member is looked into: it is
    decompressed, scrubbed and compressed again. With scrub=False (blobs, named by their
    hash) a hit drops the member."""
    inner, kind = data, ""
    try:
        if name.endswith(".gz"):
            inner, kind = gzip.decompress(data), "gz"
        elif name.endswith(".xz"):
            inner, kind = lzma.decompress(data), "xz"
    except (OSError, EOFError, lzma.LZMAError):
        inner, kind = data, ""
    if not has_home(inner):
        return data, ""
    if not scrub or not _is_text(inner):
        return None, "binary with a home path" if scrub else "hash-named, has a home path"
    new = scrub_bytes(inner)
    if kind == "gz":
        new = gzip.compress(new, 6, mtime=0)
    elif kind == "xz":
        new = lzma.compress(new, format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64, preset=6)
    return new, "scrubbed"


def drop_globs(row: dict[str, object] | None) -> list[str]:
    drop = row.get("drop", []) if row else []
    return [str(g) for g in drop] if isinstance(drop, list) else []


def drop_reason(path: str, kind_is_reg: bool, is_dir: bool, extra: list[str]) -> str:
    parts = path.split("/")
    if not (kind_is_reg or is_dir):
        return "link or special file"
    if any(p in DROP_DIRS for p in parts):
        return "venv or pycache"
    if not is_dir and path.endswith(DROP_SUFFIXES):
        return "excluded type " + path.rsplit(".", 1)[-1]
    if drop_glob(path, extra):
        return "licence table drop"
    return ""


def _tarinfo(name: str, data: bytes, mtime: int = 0) -> tarfile.TarInfo:
    ti = tarfile.TarInfo(name)
    ti.size, ti.mtime, ti.mode = len(data), mtime, 0o644
    return ti


def _clean(ti: tarfile.TarInfo) -> tarfile.TarInfo:
    ti.uid = ti.gid = 0
    ti.uname = ti.gname = ""
    return ti


def repack_tar(master: Path, out: Path, extra_drop: list[str], extras: dict[str, bytes],
               scrub: bool, threads: int = 2) -> RepackStats:
    """Stream the master through the filters into `out` (xz -T<threads> -6; temp name, then
    rename). `extras` are added members (NOTICE, licence texts)."""
    stats = RepackStats()
    part = out.with_name(out.name + ".part")
    with part.open("wb") as sink:
        proc = subprocess.Popen(["xz", f"-T{threads}", "-6", "-c"], stdin=subprocess.PIPE,
                                stdout=sink)
        assert proc.stdin is not None
        with tarfile.open(master, "r|xz") as src, \
                tarfile.open(fileobj=proc.stdin, mode="w|", format=tarfile.PAX_FORMAT) as dst:
            for ti in src:
                _repack_member(src, dst, ti, extra_drop, scrub, stats)
            for name, data in sorted(extras.items()):
                dst.addfile(_clean(_tarinfo(name, data)), io.BytesIO(data))
                stats.members.append(Entry(name, "f", len(data), hashlib.sha256(data).hexdigest()))
        proc.stdin.close()
        if proc.wait() != 0:
            raise PlanError(f"xz failed for {out.name}")
    part.replace(out)
    return stats


def _repack_member(src: tarfile.TarFile, dst: tarfile.TarFile, ti: tarfile.TarInfo,
                   extra_drop: list[str], scrub: bool, stats: RepackStats) -> None:
    name = "/".join(p for p in ti.name.split("/") if p not in ("", "."))
    why = drop_reason(name, ti.isreg(), ti.isdir(), extra_drop)
    if why:
        stats.dropped.append((name, why))
        return
    if ti.isdir():
        dst.addfile(_clean(ti))
        stats.members.append(Entry(name, "d", 0, "-"))
        return
    fobj = src.extractfile(ti)
    assert fobj is not None
    if ti.size > MAX_MEMBER:
        stats.dropped.append((name, "larger than 1 GiB, not scanned"))
        return
    data = fobj.read()
    new, note = process_bytes(name, data, scrub)
    if new is None:
        stats.dropped.append((name, note))
        return
    if note == "scrubbed":
        stats.scrubbed.append(name)
    ti.size = len(new)
    dst.addfile(_clean(ti), io.BytesIO(new))
    stats.members.append(Entry(name, "f", len(new), hashlib.sha256(new).hexdigest()))


def repack_dir(master: Path, out: Path, extra_drop: list[str], extras: dict[str, bytes]
               ) -> RepackStats:
    """The same filters for a snapshot dir: files are written under `out` (a dir)."""
    stats = RepackStats()
    for p in sorted(master.rglob("*")):
        rel = p.relative_to(master).as_posix()
        if p.is_dir() and not p.is_symlink():
            continue
        why = drop_reason(rel, p.is_file() and not p.is_symlink(), False, extra_drop)
        if why:
            stats.dropped.append((rel, why))
            continue
        new, note = process_bytes(rel, p.read_bytes(), True)
        if new is None:
            stats.dropped.append((rel, note))
            continue
        if note == "scrubbed":
            stats.scrubbed.append(rel)
        _put(out / rel, new)
        stats.members.append(Entry(rel, "f", len(new), hashlib.sha256(new).hexdigest()))
    for name, data in sorted(extras.items()):
        _put(out / name, data)
        stats.members.append(Entry(name, "f", len(data), hashlib.sha256(data).hexdigest()))
    return stats


def _put(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    part.write_bytes(data)
    part.replace(path)


# ---- the plan ------------------------------------------------------------------------------

@dataclass(frozen=True)
class Plan:
    archive: Archive
    licence: str  # host, host-with-notices, split, do-not-host, private or pending
    hits: dict[str, list[str]]
    unlicensed: list[str]
    links: int
    homes: int
    pdfs: int
    would_drop: int

    @property
    def hostable(self) -> bool:
        return self.licence not in ("do-not-host", "private", "pending")


def status_of(arch: Archive, row: dict[str, object] | None, hits: dict[str, list[str]],
              unlicensed: list[str]) -> str:
    verdict = str(row["verdict"]) if row else ""
    if arch.private or verdict == "do-not-host":
        return "private"
    if unlicensed:
        return "pending"
    return verdict or ("host-with-notices" if hits else "host")


def make_plan(idx: Path, arch: Archive, rules: list[Rule], rows: dict[str, dict[str, object]]
              ) -> Plan:
    entries = read_manifest(idx, arch.manifest)
    row = rows.get(arch.name)
    extra = drop_globs(row)
    hits = rule_hits(entries, rules)
    unl = [] if arch.private else unmatched_design_files(entries, rules)
    links = sum(1 for e in entries if e.type == "l")
    homes = sum(1 for e in entries if "/home" in e.path or "$HOME" in e.sha or "$WS" in e.sha)
    pdfs = sum(1 for e in entries if e.path.lower().endswith(".pdf"))
    drop = sum(1 for e in entries if drop_reason(e.path, e.type == "f", e.type == "d", extra))
    return Plan(arch, status_of(arch, row, hits, unl), hits, unl, links, homes, pdfs, drop)


def build_plans(idx: Path, rules: list[Rule], rows: dict[str, dict[str, object]]
                ) -> list[Plan]:
    return [make_plan(idx, a, rules, rows) for _, a in sorted(load_archives(idx).items())]


def select(plans: list[Plan], only: list[str], allow_pending: bool) -> list[Plan]:
    """The plans to publish. A named private or pending archive is refused, not skipped."""
    names = {p.archive.name: p for p in plans}
    chosen = []
    for name in only:
        if name not in names:
            raise PlanError(f"unknown archive {name!r}")
        p = names[name]
        if p.licence in ("private", "do-not-host"):
            raise PlanError(f"{name} is private: it is never published")
        if p.licence == "pending" and not allow_pending:
            raise PlanError(f"{name}: licence pending ({len(p.unlicensed)} design files without "
                            "licence meta); give --allow-pending to publish anyway")
        chosen.append(p)
    if only:
        return chosen
    return [p for p in plans if p.hostable or (p.licence == "pending" and allow_pending)]


def check_space(path: Path) -> None:
    mnt = Path("/mnt/c")
    probe = mnt if mnt.exists() else path
    free = shutil.disk_usage(probe).free / 2**30
    if free < MIN_FREE_GB:
        raise PlanError(f"only {free:.0f} GB free on {probe}; need over {MIN_FREE_GB} GB")


def format_plan(plans: list[Plan]) -> str:
    cols = "archive licence file master_bytes links home_paths pdfs would_drop design_hits"
    lines = [cols.replace(" ", "\t")]
    for p in plans:
        a = p.archive
        n = sum(len(v) for v in p.hits.values())
        lines.append(f"{a.name}\t{p.licence}\t{a.file}\t{a.size}\t{p.links}\t{p.homes}\t{p.pdfs}"
                     f"\t{p.would_drop}\t{n}")
    return "\n".join(lines)


# ---- staging -------------------------------------------------------------------------------

def _extras(plan: Plan, rows: dict[str, dict[str, object]], rules: list[Rule],
            rule_texts: dict[str, list[str]], idx: Path, prefix: str) -> dict[str, bytes]:
    out = {f"{prefix}NOTICE-{plan.archive.name}.txt":
           notice(plan.archive.name, rows.get(plan.archive.name), plan.hits, rules).encode()}
    for name in texts_for(plan.hits, rule_texts):
        out[f"{prefix}LICENSES/{name}"] = (idx / "licence-texts" / name).read_bytes()
    if not plan.hits:
        out[f"{prefix}LICENSES/LICENSE-MIMIR-MIT"] = (idx / "licence-texts"
                                                      / "LICENSE-MIMIR-MIT").read_bytes()
    return out


def stage_archive(plan: Plan, master_dir: Path, stage: Path, idx: Path, rules: list[Rule],
                  rows: dict[str, dict[str, object]], rule_texts: dict[str, list[str]]
                  ) -> tuple[Archive, RepackStats]:
    a = plan.archive
    row = rows.get(a.name)
    extra = drop_globs(row)
    src = master_dir / a.file
    if not src.exists():
        src = master_dir / a.date / a.file
    dest_dir = stage / a.date
    dest_dir.mkdir(parents=True, exist_ok=True)
    if a.form == "dir":
        stats = repack_dir(src, dest_dir / a.file, extra, _extras(plan, rows, rules, rule_texts,
                                                                  idx, ""))
        public = replace(a, public_file=a.file, public_sha256="", public_size=0)
    else:
        pub_name = f"{a.name}.tar.xz"
        # NOTICE files sit at the tar root, beside the archive's own top dir.
        stats = repack_tar(src, dest_dir / pub_name, extra,
                           _extras(plan, rows, rules, rule_texts, idx, ""), a.kind != "blobs")
        out = dest_dir / pub_name
        public = replace(a, public_file=pub_name, public_sha256=sha256_path(out),
                         public_size=out.stat().st_size)
    manifest = f"manifests/{a.name}.public.tsv.xz"
    public = replace(public, public_manifest=manifest, public_members=len(
        [m for m in stats.members if m.type == "f"]), public_dropped=len(stats.dropped),
        public_scrubbed=len(stats.scrubbed))
    text = manifest_text(stats.members)
    write_xz(stage / "index" / manifest, text)
    return public, stats


def stage_blobs(store: Path, stage: Path, shas: list[str]) -> tuple[int, list[str]]:
    """Copy the blobs (as stored: `<ab>/<sha>.xz`) that carry no home path; returns the count
    and the listed ones left out."""
    n, skipped = 0, []
    for sha in shas:
        path = blobs.blob_path(store, sha)
        data = path.read_bytes()
        new, _ = process_bytes(path.name, data, scrub=False)
        if new is None:
            skipped.append(sha)
            continue
        _put(stage / "blobs" / sha[:2] / f"{sha}.xz", data)
        n += 1
    return n, skipped


def write_sums(stage: Path, date: str) -> int:
    base = stage / date
    lines = []
    for p in sorted(base.rglob("*")):
        if p.is_file() and p.name != "SHA256SUMS":
            lines.append(f"{sha256_path(p)}  {p.relative_to(base).as_posix()}")
    _put(base / "SHA256SUMS", ("\n".join(lines) + "\n").encode())
    return len(lines)


def readme_text(plans: list[Plan], base: str) -> str:
    head = f"""Mimir III data (Yggdrasil III). Static files for {base}

Layout:
  <date>/<archive>.tar.xz    public repacks of the archives (links, venvs, caches, *.pkl, *.db,
                             *.lock, *.sh and PDFs removed; home paths replaced by $WS / $HOME)
  <date>/<snapshot>/...      snapshot files
  <date>/SHA256SUMS          check with:  cd <date> && sha256sum -c SHA256SUMS
  <date>/NOTICE-<archive>.txt  the licence notice of each archive (also inside the archive)
  blobs/<ab>/<sha256>.xz     content-addressed blobs; name = sha256 of the decompressed bytes
  index/                     archives.toml, blobs.tsv.xz, manifests/ and licences.toml of the
                             mimirIII repo (data/remote/); `mimir fetch` reads that index

Licences: each benchmark keeps the licence it states (or none-stated); nothing is relicensed.
Mimir's own files are MIT. Each archive carries a NOTICE (per design: licence, source, notice
text) and the licence texts it names under LICENSES/. This is not legal advice.

Archives and their verdicts:
"""
    rows = "\n".join(f"  {p.archive.name}: {p.licence}" for p in plans)
    return head + rows + "\n"


def run_stage(stage: Path, master_dir: Path, plans: list[Plan], idx: Path, store: Path | None,
              base: str, with_blobs: bool, record: bool) -> list[str]:
    """Write the staged tree; returns report lines. With `record`, the repack fields go into
    the index's archives.toml and the public manifests into the index dir."""
    rules = load_licence_rules(idx.parent / "meta" / "licences.toml")
    rows, rule_texts = load_table(idx / "licences.toml")
    report, updated = [], {}
    for plan in plans:
        pub, stats = stage_archive(plan, master_dir, stage, idx, rules, rows, rule_texts)
        updated[plan.archive.name] = pub
        report.append(f"{plan.archive.name}: dropped {len(stats.dropped)}, scrubbed "
                      f"{len(stats.scrubbed)}, members {pub.public_members}, bytes "
                      f"{pub.public_size}")
        report += [f"  dropped {m} ({r})" for m, r in stats.dropped[:20]]
        report += [f"  scrubbed {m}" for m in stats.scrubbed[:20]]
        _put(stage / plan.archive.date / f"NOTICE-{plan.archive.name}.txt",
             notice(plan.archive.name, rows.get(plan.archive.name), plan.hits, rules).encode())
    if with_blobs and store is not None:
        n, skipped = stage_blobs(store, stage, sorted(load_blob_index(idx)))
        report.append(f"blobs staged: {n}; left out (home path): {len(skipped)}")
    allarch = {**load_archives(idx), **updated}
    index_out = stage / "index"
    _put(index_out / "archives.toml", dump_archives(allarch.values()).encode())
    for name in ("blobs.tsv.xz", "licences.toml"):
        _put(index_out / name, (idx / name).read_bytes())
    for a in allarch.values():
        _put(index_out / a.manifest, (idx / a.manifest).read_bytes())
    _put(stage / "README.txt", readme_text(plans, base).encode())
    report.append(f"SHA256SUMS lines: {write_sums(stage, plans[0].archive.date) if plans else 0}")
    if record:
        for pub in updated.values():
            _put(idx / pub.public_manifest, (stage / "index" / pub.public_manifest).read_bytes())
        (idx / "archives.toml").write_text(dump_archives(allarch.values()), encoding="utf-8")
    return report


def default_index() -> Path:
    return index_dir()
