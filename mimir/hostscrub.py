"""Host aliasing of an existing store: `run.host` rewritten to the alias, and every blob that
holds a private string re-blobbed scrubbed (the old blob stays on disk, marked `withheld` in
the blob index). The change is recorded in `blob_scrub`, which extends the artifact row."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from mimir import blobs, hostalias, privacy, publish
from mimir.remote import blob_columns, load_blob_index, write_xz

SCRUB_DDL = """CREATE TABLE IF NOT EXISTS blob_scrub (
    ref_table TEXT NOT NULL, ref_column TEXT NOT NULL, ref_key TEXT NOT NULL,
    scrubbed_from TEXT NOT NULL, blob_sha256 TEXT NOT NULL,
    PRIMARY KEY (ref_table, ref_column, ref_key))"""


def alias_host_value(host: str, map_file: Path | None = None) -> str:
    """`host` is `<name> <kernel> <time>` (or just a name): the first token becomes its alias,
    and any other real name of the map is replaced. An aliased value is returned unchanged."""
    parts = host.split(None, 1)
    if not parts:
        return host
    if not hostalias.ALIAS_RE.fullmatch(parts[0]):
        parts[0] = hostalias.alias_of(parts[0], map_file)
    return hostalias.scrub_text(" ".join(parts), map_file)


def _unaliased(db: sqlite3.Connection, map_file: Path | None) -> list[tuple[str, str, str]]:
    rows = db.execute("SELECT run_id, host FROM run WHERE host IS NOT NULL AND host != ''")
    return [(r[0], r[1], alias_host_value(r[1], map_file)) for r in rows.fetchall()
            if alias_host_value(r[1], map_file) != r[1]]


def rewrite_hosts(db_path: Path, map_file: Path | None = None) -> tuple[int, int]:
    """Rewrite every `run.host` to the alias in one transaction; return (rows rewritten,
    rows still unaliased after). A second call rewrites nothing."""
    db = sqlite3.connect(db_path)
    try:
        db.execute("BEGIN")
        todo = _unaliased(db, map_file)
        db.executemany("UPDATE run SET host = ? WHERE run_id = ?", [(n, r) for r, _, n in todo])
        left = len(_unaliased(db, map_file))
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()
    return len(todo), left


def scrub_blob_bytes(raw: bytes, strings: list[str], map_file: Path | None = None) -> bytes:
    """Real host name to alias, then home paths, user name and e-mail as `publish.scrub_bytes`
    does, then any other private string to `redacted`."""
    out = publish.scrub_bytes(hostalias.scrub_bytes(raw, map_file))
    if privacy.hits_in(out, strings):
        rx = re.compile(b"|".join(re.escape(s.encode()) for s in strings), re.IGNORECASE)
        out = rx.sub(b"redacted", out)
    return out


def _dirty(raw: bytes, strings: list[str]) -> bool:
    return bool(privacy.hits_in(raw, strings)) or publish.has_home(raw)


def reblob(db_path: Path, root: Path, strings: list[str], map_file: Path | None = None
           ) -> dict[str, str]:
    """Re-blob every referenced blob that holds a private string or a home path: a scrubbed
    copy is stored as a new blob, every blob column pointing at the old sha is repointed, and
    `blob_scrub` records the old sha. Returns old sha -> new sha. The old blobs are not touched.
    ValueError when a scrubbed copy is still not clean."""
    db = sqlite3.connect(db_path)
    done: dict[str, str] = {}
    try:
        cols = blob_columns(db)
        shas = sorted({str(v) for t, c in cols for (v,) in db.execute(
            f'SELECT DISTINCT "{c}" FROM "{t}" WHERE "{c}" IS NOT NULL AND "{c}" != \'\'')})
        for sha in shas:
            if not blobs.blob_path(root, sha).exists():
                continue
            raw = blobs.get_bytes(root, sha)
            if not _dirty(raw, strings):
                continue
            clean = scrub_blob_bytes(raw, strings, map_file)
            if _dirty(clean, strings):
                raise ValueError(f"blob {sha}: still not clean after the scrub")
            done[sha] = blobs.put_bytes(root, clean)
        db.execute("BEGIN")
        db.execute(SCRUB_DDL)
        for old, new in done.items():
            for table, col in cols:
                _repoint(db, table, col, old, new)
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()
    return done


def _repoint(db: sqlite3.Connection, table: str, col: str, old: str, new: str) -> None:
    key = "run_id || ':' || kind" if table == "run_artifact" else "CAST(rowid AS TEXT)"
    db.execute(f'INSERT OR IGNORE INTO blob_scrub SELECT ?, ?, {key}, ?, ? FROM "{table}" '
               f'WHERE "{col}" = ?', (table, col, old, new, old))
    db.execute(f'UPDATE "{table}" SET "{col}" = ? WHERE "{col}" = ?', (new, old))


def update_blob_index(idx: Path, mapping: dict[str, str], root: Path, archive: str) -> int:
    """blobs.tsv.xz: each old sha becomes `withheld`; each new sha is added as `public` in
    `archive` (a row that exists is kept). Returns the number of rows changed or added."""
    rows = {sha: (r.xz_bytes, r.raw_bytes, r.archive, r.visibility)
            for sha, r in load_blob_index(idx).items()}
    changed = 0
    for old, new in sorted(mapping.items()):
        if old in rows and rows[old][3] != "withheld":
            rows[old] = (*rows[old][:3], "withheld")
            changed += 1
        if new not in rows:
            raw = blobs.get_bytes(root, new)
            nx = blobs.blob_path(root, new).stat().st_size
            rows[new] = (nx, len(raw), archive, "public")
            changed += 1
    text = "".join(f"{s}\t{a}\t{b}\t{c}\t{d}\n" for s, (a, b, c, d) in sorted(rows.items()))
    write_xz(idx / "blobs.tsv.xz", text.encode())
    return changed
