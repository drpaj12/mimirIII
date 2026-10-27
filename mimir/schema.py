"""The record schema (version 1): one tidy row per measured value."""

from __future__ import annotations

from dataclasses import astuple, dataclass, fields

SCHEMA_VERSION = 2  # store schema; the `records` table is unchanged since version 1
CONF = ("primary", "secondary", "inferred", "missing")
PARAM_CONF = ("given", "default", "unknown")
LEVELS = ("hdl", "elab", "gate", "lut", "ble", "clb", "placed", "routed")
FAMILIES = ("", "analytic", "annealing")


@dataclass(frozen=True)
class Record:
    """One measured value. Identity is every column except value, unit and measurer_version."""

    design: str
    source: str
    input_sha256: str
    tool_commit: str
    script_hash: str
    level: str
    arch: str
    seed: int
    arm: str
    family: str
    metric: str
    bin: str
    value: float
    unit: str
    measurer: str
    measurer_version: str
    origin: str

    def as_tuple(self) -> tuple[str | int | float, ...]:
        return astuple(self)


COLUMNS: tuple[str, ...] = tuple(f.name for f in fields(Record))
NON_KEY = ("value", "unit", "measurer_version")
KEY_COLUMNS: tuple[str, ...] = tuple(c for c in COLUMNS if c not in NON_KEY)


def check_record(rec: Record) -> None:
    """Raise ValueError when a record breaks the schema's closed sets."""
    if rec.level not in LEVELS:
        raise ValueError(f"level {rec.level!r} not in {LEVELS}")
    if rec.family not in FAMILIES:
        raise ValueError(f"family {rec.family!r} not in {FAMILIES}")
    if rec.value != rec.value:
        raise ValueError(f"metric {rec.metric!r}: NaN value")


def _ck(col: str, values: tuple[str, ...]) -> str:
    return f"CHECK ({col} IN ({', '.join(repr(v) for v in values)}))"


# Tables added in schema version 2 (docs/specs/2026-10-27-mimir-schema-v2.md, section 3).
V2_DDL: tuple[str, ...] = (
    """CREATE TABLE IF NOT EXISTS design (
        slug TEXT PRIMARY KEY, design_hash TEXT NOT NULL, hash_kind TEXT NOT NULL,
        suite TEXT NOT NULL, name TEXT NOT NULL, origin TEXT NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS design_hash_idx ON design(design_hash)",
    """CREATE TABLE IF NOT EXISTS design_source (
        source TEXT NOT NULL, name TEXT NOT NULL, slug TEXT NOT NULL,
        PRIMARY KEY (source, name))""",
    f"""CREATE TABLE IF NOT EXISTS design_meta (
        slug TEXT NOT NULL, field TEXT NOT NULL, value TEXT NOT NULL, source TEXT NOT NULL,
        conf TEXT NOT NULL {_ck("conf", CONF)}, PRIMARY KEY (slug, field))""",
    f"""CREATE TABLE IF NOT EXISTS design_lineage (
        slug TEXT NOT NULL, step_no INTEGER NOT NULL, tool TEXT NOT NULL, script TEXT NOT NULL,
        parent_hash TEXT NOT NULL, source TEXT NOT NULL,
        conf TEXT NOT NULL {_ck("conf", CONF)}, PRIMARY KEY (slug, step_no))""",
    """CREATE TABLE IF NOT EXISTS flow_config (
        config_hash TEXT PRIMARY KEY, name TEXT NOT NULL, config_text TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('full', 'partial')), origin TEXT NOT NULL)""",
    f"""CREATE TABLE IF NOT EXISTS flow_param (
        config_hash TEXT NOT NULL, step TEXT NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL,
        conf TEXT NOT NULL {_ck("conf", PARAM_CONF)}, source TEXT NOT NULL,
        PRIMARY KEY (config_hash, step, key))""",
    """CREATE TABLE IF NOT EXISTS run (
        run_id TEXT PRIMARY KEY, slug TEXT NOT NULL, config_hash TEXT NOT NULL,
        source TEXT NOT NULL, design TEXT NOT NULL, arch TEXT NOT NULL, seed INTEGER NOT NULL,
        arm TEXT NOT NULL, family TEXT NOT NULL, tool_commits TEXT NOT NULL, command_line TEXT,
        time_s REAL, peak_rss_mib REAL, host TEXT, origin TEXT NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS run_key ON run(source, design, arch, seed, arm)",
    """CREATE TABLE IF NOT EXISTS run_artifact (
        run_id TEXT NOT NULL, kind TEXT NOT NULL, blob_sha256 TEXT NOT NULL,
        PRIMARY KEY (run_id, kind))""",
    """CREATE TABLE IF NOT EXISTS partition (
        partition_id TEXT PRIMARY KEY, algorithm TEXT NOT NULL, algorithm_version TEXT NOT NULL,
        params TEXT NOT NULL, seed INTEGER NOT NULL, slug TEXT NOT NULL, input_hash TEXT NOT NULL,
        n_objects INTEGER NOT NULL, n_clusters INTEGER NOT NULL, assignment_blob TEXT NOT NULL,
        origin TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS analysis_result (
        analysis_id TEXT PRIMARY KEY, algorithm TEXT NOT NULL, params TEXT NOT NULL,
        feature_set_hash TEXT NOT NULL, input_selection TEXT NOT NULL, seed INTEGER NOT NULL,
        script_hash TEXT NOT NULL, script_version TEXT NOT NULL, labels_blob TEXT NOT NULL,
        origin TEXT NOT NULL)""",
    """CREATE VIEW IF NOT EXISTS record_run AS
        SELECT r.rowid AS record_rowid, u.run_id AS run_id, u.slug AS slug,
               u.config_hash AS config_hash
        FROM records r JOIN run u ON u.source = r.source AND u.design = r.design
             AND u.arch = r.arch AND u.seed = r.seed AND u.arm = r.arm""",
)
