"""Host aliasing of an existing store: `run.host` rewritten to the alias, and every blob that
holds a private string re-blobbed scrubbed (the old blob stays on disk, marked `withheld` in
the blob index). The change is recorded in `blob_scrub`, which extends the artifact row."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from mimir import blobs, hostalias, privacy, publish
from mimir.remote import load_blob_index, write_xz
from mimir.snapshot import BLOB_REFS

# Free-text columns that can hold a host name, a user name or an e-mail: every one is rewritten.
# `test_every_text_column_is_listed` fails when a column is in neither list, so a new column has
# to be classified. Identifier, hash, closed-set and blob columns cannot hold a host name.
TEXT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("analysis_result", "params"), ("analysis_result", "input_selection"),
    ("analysis_result", "origin"), ("design", "origin"), ("design_lineage", "tool"),
    ("design_lineage", "script"), ("design_lineage", "source"), ("design_meta", "value"),
    ("design_meta", "source"), ("flow_config", "name"),
    ("flow_config", "config_text_reconstructed"), ("flow_config", "origin"),
    ("flow_param", "value"), ("flow_param", "source"), ("meta", "value"),
    ("partition", "params"), ("partition", "origin"), ("records", "origin"),
    ("run", "command_line"), ("run", "origin"), ("run", "tool_commits"),
    ("structure", "hdl_span"), ("structure", "construct_chain"),
    ("structure_mapping", "joined_with"), ("structure_mapping", "lost_at_pass"),
    ("timing_object", "object_key"), ("timing_path", "startpoint"), ("timing_path", "endpoint"),
    ("timing_path_node", "atom"), ("timing_path_node", "pins"), ("timing_path_node", "span"),
    ("timing_path_node", "loc"), ("timing_path_node", "module"), ("timing_path_node", "word"),
)
EXEMPT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("analysis_result", "analysis_id"), ("analysis_result", "algorithm"),
    ("analysis_result", "feature_set_hash"), ("analysis_result", "script_hash"),
    ("analysis_result", "script_version"), ("analysis_result", "labels_blob"),
    ("blob_scrub", "ref_table"), ("blob_scrub", "ref_column"), ("blob_scrub", "ref_key"),
    ("blob_scrub", "scrubbed_from"), ("blob_scrub", "blob_sha256"),
    ("design", "slug"), ("design", "design_hash"), ("design", "hash_kind"), ("design", "suite"),
    ("design", "name"), ("design_lineage", "slug"), ("design_lineage", "parent_hash"),
    ("design_lineage", "conf"), ("design_meta", "slug"), ("design_meta", "field"),
    ("design_meta", "conf"), ("design_source", "source"), ("design_source", "name"),
    ("design_source", "slug"), ("flow_config", "config_hash"), ("flow_config", "text_kind"),
    ("flow_config", "status"), ("flow_param", "config_hash"), ("flow_param", "step"),
    ("flow_param", "key"), ("flow_param", "conf"), ("meta", "key"),
    ("partition", "partition_id"), ("partition", "algorithm"),
    ("partition", "algorithm_version"), ("partition", "slug"), ("partition", "input_hash"),
    ("partition", "assignment_blob"), ("partition", "version_kind"), ("partition", "seed_conf"),
    ("records", "design"), ("records", "source"), ("records", "input_sha256"),
    ("records", "tool_commit"), ("records", "script_hash"), ("records", "level"),
    ("records", "arch"), ("records", "arm"), ("records", "family"), ("records", "metric"),
    ("records", "bin"), ("records", "unit"), ("records", "measurer"),
    ("records", "measurer_version"), ("run", "run_id"), ("run", "slug"), ("run", "config_hash"),
    ("run", "source"), ("run", "design"), ("run", "arch"), ("run", "arm"), ("run", "family"),
    ("run", "host"), ("run", "tool_commit"), ("run", "input_sha256"),
    ("run_artifact", "run_id"), ("run_artifact", "kind"), ("run_artifact", "blob_sha256"),
    ("structure", "design"), ("structure", "structure_id"), ("structure", "kind"),
    ("structure", "label_source"), ("structure", "run_id"), ("structure", "config_hash"),
    ("structure", "granularity"), ("structure", "parent_id"), ("structure_mapping", "design"),
    ("structure_mapping", "structure_id"), ("structure_mapping", "run_id"),
    ("structure_mapping", "level"), ("structure_mapping", "config_hash"),
    ("structure_member", "design"), ("structure_member", "structure_id"),
    ("structure_member", "run_id"), ("structure_member", "atom"),
    ("timing_run", "run_id"), ("timing_run", "dmax_source"), ("timing_run", "source_kind"),
    ("timing_run", "source_sha256"), ("timing_path_hist", "run_id"),
    ("timing_object", "run_id"), ("timing_object", "kind"), ("timing_object", "via"),
    ("timing_path", "run_id"), ("timing_path_node", "run_id"),
    ("timing_path_node", "block_type"), ("timing_path_node", "word_via"),
    ("timing_path_node", "category"),
)  # run.host has its own rule (`alias_host_value`)
# The blob columns and how a blob_scrub row names the artifact row that holds the column.
BLOB_KEYS = {"run_artifact": "run_id || ':' || kind", "partition": "partition_id",
             "analysis_result": "analysis_id"}


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


def _redact_rx(strings: list[str]) -> re.Pattern[bytes]:
    parts = [(rb"(?<![A-Za-z0-9])" + re.escape(x.encode()) + rb"(?![A-Za-z0-9])"
              if len(x) < privacy.MIN_LEN else re.escape(x.encode())) for x in strings]
    return re.compile(b"|".join(parts), re.IGNORECASE)


def scrub_blob_bytes(raw: bytes, strings: list[str], map_file: Path | None = None) -> bytes:
    """Real host name to alias, then home paths, user name and e-mail as `publish.scrub_bytes`
    does, then any other private string to `redacted`."""
    out = publish.scrub_bytes(hostalias.scrub_bytes(raw, map_file))
    if strings and privacy.hits_in(out, strings):
        out = _redact_rx(strings).sub(b"redacted", out)
    return out


def _dirty(raw: bytes, strings: list[str]) -> bool:
    return bool(privacy.hits_in(raw, strings)) or publish.has_home(raw)


def rewrite_columns(db_path: Path, strings: list[str], map_file: Path | None = None
                    ) -> dict[str, int]:
    """Rewrite every cell of `TEXT_COLUMNS` that holds a host name of the map, a private string,
    a home path, the user name or an e-mail, in one transaction. Returns `table.column` -> cells
    changed (only columns that changed). A second call changes nothing."""
    table_scrub = hostalias.text_scrubber(map_file)
    rx = _redact_rx(strings) if strings else None

    def clean(text: str) -> str:
        out = publish.scrub_bytes(table_scrub(text).encode("utf-8")).decode("utf-8")
        if rx is not None and privacy.hits_in(out.encode("utf-8"), strings):
            out = rx.sub(b"redacted", out.encode("utf-8")).decode("utf-8")
        return out

    db = sqlite3.connect(db_path)
    changed: dict[str, int] = {}
    try:
        db.execute("BEGIN")
        have = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table, col in TEXT_COLUMNS:
            if table not in have or col not in {r[1] for r in db.execute(
                    f'PRAGMA table_info("{table}")')}:
                continue
            todo = []
            for rowid, value in db.execute(
                    f'SELECT rowid, "{col}" FROM "{table}" WHERE typeof("{col}") = \'text\''):
                new = clean(value)
                if new != value:
                    todo.append((new, rowid))
            db.executemany(f'UPDATE "{table}" SET "{col}" = ? WHERE rowid = ?', todo)
            if todo:
                changed[f"{table}.{col}"] = len(todo)
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()
    return changed


def vacuum(db_path: Path) -> None:
    """Rebuild the file so that no free page keeps the old text of a rewritten row."""
    db = sqlite3.connect(db_path)
    try:
        db.execute("VACUUM")
    finally:
        db.close()


def _blob_cols(db: sqlite3.Connection) -> list[tuple[str, str]]:
    have = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    return [(t, c) for t, c in BLOB_REFS if t in have]


def _shas(db: sqlite3.Connection) -> list[str]:
    return sorted({str(v) for t, c in _blob_cols(db) for (v,) in db.execute(
        f'SELECT DISTINCT "{c}" FROM "{t}" WHERE "{c}" IS NOT NULL AND "{c}" != \'\'')})


def reblob(db_path: Path, root: Path, strings: list[str], map_file: Path | None = None
           ) -> dict[str, str]:
    """Re-blob every referenced blob (the `BLOB_REFS` columns) that holds a private string or a
    home path: a scrubbed copy is stored as a new blob, every blob column pointing at the old sha
    is repointed, and `blob_scrub` (schema version 4) records the old sha. Returns old sha -> new
    sha. The old blobs are not touched. A referenced blob missing from disk is skipped here
    (`missing_blobs` counts it). ValueError when a scrubbed copy is still not clean."""
    db = sqlite3.connect(db_path)
    done: dict[str, str] = {}
    try:
        for sha in _shas(db):
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
        for old, new in done.items():
            for table, col in _blob_cols(db):
                _repoint(db, table, col, old, new)
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()
    return done


def _repoint(db: sqlite3.Connection, table: str, col: str, old: str, new: str) -> None:
    key = BLOB_KEYS[table]
    db.execute(f'INSERT OR IGNORE INTO blob_scrub SELECT ?, ?, {key}, ?, ? FROM "{table}" '
               f'WHERE "{col}" = ?', (table, col, old, new, old))
    db.execute(f'UPDATE "{table}" SET "{col}" = ? WHERE "{col}" = ?', (new, old))


def referenced_blobs(db_path: Path) -> set[str]:
    """Every sha a blob column of the store holds."""
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        return set(_shas(db))
    finally:
        db.close()


def missing_blobs(db_path: Path, root: Path) -> list[str]:
    """Referenced shas whose blob file is not in the blob directory."""
    return [s for s in sorted(referenced_blobs(db_path))
            if not blobs.blob_path(root, s).exists()]


def update_blob_index(idx: Path, mapping: dict[str, str], root: Path, archive: str,
                      extra: set[str] | None = None, strings: list[str] | None = None) -> int:
    """blobs.tsv.xz: each old sha becomes `withheld`; each new sha, and each sha of `extra` that
    the store has and the index lacks, is added as `public` in `archive` (a row that exists is
    kept). A new sha or an `extra` sha whose bytes hold a private string, a home path, the user
    name or an e-mail (`strings` plus `publish.has_home`) is added as `withheld`, never public.
    Returns the number of rows changed or added."""
    rows = {sha: (r.xz_bytes, r.raw_bytes, r.archive, r.visibility)
            for sha, r in load_blob_index(idx).items()}
    changed = 0
    for old, new in sorted(mapping.items()):
        if old in rows and rows[old][3] != "withheld":
            rows[old] = (*rows[old][:3], "withheld")
            changed += 1
        if new not in rows:
            rows[new] = _new_row(root, new, archive, strings or [])
            changed += 1
    for sha in sorted((extra or set()) - set(rows)):
        if blobs.blob_path(root, sha).exists():
            rows[sha] = _new_row(root, sha, archive, strings or [])
            changed += 1
    text = "".join(f"{s}\t{a}\t{b}\t{c}\t{d}\n" for s, (a, b, c, d) in sorted(rows.items()))
    write_xz(idx / "blobs.tsv.xz", text.encode())
    return changed


def _new_row(root: Path, sha: str, archive: str, strings: list[str]
             ) -> tuple[int, int, str, str]:
    raw = blobs.get_bytes(root, sha)
    hit = bool(privacy.scan_member(f"blob {sha}", "", raw, strings))
    return (blobs.blob_path(root, sha).stat().st_size, len(raw), archive,
            "withheld" if hit else "public")
