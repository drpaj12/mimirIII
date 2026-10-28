"""The record schema (version 1): one tidy row per measured value."""

from __future__ import annotations

from dataclasses import astuple, dataclass, fields

SCHEMA_VERSION = 6  # store schema; the `records` table is unchanged since version 1
CONF = ("primary", "secondary", "inferred", "missing")
PARAM_CONF = ("given", "default", "default-unrecorded", "unknown")
UNKNOWN_CONF = ("unknown", "default-unrecorded")  # counted as unknown by the run status
TEXT_KINDS = ("reconstructed", "recorded-normalised")
LEVELS = ("hdl", "elab", "gate", "lut", "ble", "clb", "placed", "routed")
FAMILIES = ("", "analytic", "annealing")
STRUCT_KINDS = ("adder", "multiplier", "shifter", "equality", "relational", "mux", "register_word",
                "counter", "fsm", "memory", "logic", "unknown")
STRUCT_GRANULARITY = ("block", "operator", "")  # '' for a detector structure
MAP_LEVELS = ("gate", "lut", "ble", "clb", "placed")


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
    f"""CREATE TABLE IF NOT EXISTS flow_config (
        config_hash TEXT PRIMARY KEY, name TEXT NOT NULL, config_text_reconstructed TEXT NOT NULL,
        text_kind TEXT NOT NULL {_ck("text_kind", TEXT_KINDS)},
        status TEXT NOT NULL CHECK (status IN ('full', 'partial')), origin TEXT NOT NULL)""",
    f"""CREATE TABLE IF NOT EXISTS flow_param (
        config_hash TEXT NOT NULL, step TEXT NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL,
        conf TEXT NOT NULL {_ck("conf", PARAM_CONF)}, source TEXT NOT NULL,
        PRIMARY KEY (config_hash, step, key))""",
    """CREATE TABLE IF NOT EXISTS run (
        run_id TEXT PRIMARY KEY, slug TEXT NOT NULL, config_hash TEXT NOT NULL,
        source TEXT NOT NULL, design TEXT NOT NULL, arch TEXT NOT NULL, seed INTEGER NOT NULL,
        arm TEXT NOT NULL, family TEXT NOT NULL, tool_commits TEXT NOT NULL, command_line TEXT,
        time_s REAL, peak_rss_mib REAL, host TEXT, origin TEXT NOT NULL,
        tool_commit TEXT NOT NULL DEFAULT '', input_sha256 TEXT NOT NULL DEFAULT '',
        UNIQUE (source, design, arch, seed, arm, config_hash, tool_commit, input_sha256))""",
    "CREATE INDEX IF NOT EXISTS run_key ON run(source, design, arch, seed, arm)",
    """CREATE TABLE IF NOT EXISTS run_artifact (
        run_id TEXT NOT NULL, kind TEXT NOT NULL, blob_sha256 TEXT NOT NULL,
        PRIMARY KEY (run_id, kind))""",
    """CREATE TABLE IF NOT EXISTS partition (
        partition_id TEXT PRIMARY KEY, algorithm TEXT NOT NULL, algorithm_version TEXT NOT NULL,
        params TEXT NOT NULL, seed INTEGER NOT NULL, slug TEXT NOT NULL, input_hash TEXT NOT NULL,
        n_objects INTEGER NOT NULL, n_clusters INTEGER NOT NULL, assignment_blob TEXT NOT NULL,
        origin TEXT NOT NULL, version_kind TEXT NOT NULL DEFAULT 'recorded',
        dirty INTEGER NOT NULL DEFAULT 0, seed_conf TEXT NOT NULL DEFAULT 'confirmed')""",
    """CREATE TABLE IF NOT EXISTS analysis_result (
        analysis_id TEXT PRIMARY KEY, algorithm TEXT NOT NULL, params TEXT NOT NULL,
        feature_set_hash TEXT NOT NULL, input_selection TEXT NOT NULL, seed INTEGER NOT NULL,
        script_hash TEXT NOT NULL, script_version TEXT NOT NULL, labels_blob TEXT NOT NULL,
        origin TEXT NOT NULL)""",
    """CREATE VIEW IF NOT EXISTS record_run AS
        SELECT r.rowid AS record_rowid, u.run_id AS run_id, u.slug AS slug,
               u.config_hash AS config_hash
        FROM records r JOIN run u ON u.source = r.source AND u.design = r.design
             AND u.arch = r.arch AND u.seed = r.seed AND u.arm = r.arm
             AND u.tool_commit = r.tool_commit AND u.input_sha256 = r.input_sha256""",
)


# Tables added in schema version 3 (docs/specs/2026-10-27-mimir-structures.md, section 3).
V3_DDL: tuple[str, ...] = (
    f"""CREATE TABLE IF NOT EXISTS structure (
        design TEXT NOT NULL, structure_id TEXT NOT NULL,
        kind TEXT NOT NULL {_ck("kind", STRUCT_KINDS)},
        hdl_span TEXT NOT NULL, construct_chain TEXT NOT NULL, label_source TEXT NOT NULL,
        confidence REAL, run_id TEXT NOT NULL, config_hash TEXT NOT NULL,
        granularity TEXT NOT NULL {_ck("granularity", STRUCT_GRANULARITY)},
        parent_id TEXT NOT NULL, PRIMARY KEY (design, structure_id))""",
    f"""CREATE TABLE IF NOT EXISTS structure_mapping (
        design TEXT NOT NULL, structure_id TEXT NOT NULL, run_id TEXT NOT NULL,
        level TEXT NOT NULL {_ck("level", MAP_LEVELS)}, config_hash TEXT NOT NULL,
        n_objects INTEGER NOT NULL, n_pure INTEGER NOT NULL, n_shared INTEGER NOT NULL,
        n_gates INTEGER, n_luts INTEGER, n_carry INTEGER, n_ffs INTEGER, n_bles INTEGER,
        n_clbs INTEGER, n_sites INTEGER, joined_with TEXT NOT NULL, lost_at_pass TEXT NOT NULL,
        bbox_x0 INTEGER, bbox_y0 INTEGER, bbox_x1 INTEGER, bbox_y1 INTEGER, spread REAL,
        crit_share REAL, PRIMARY KEY (design, structure_id, run_id, level))""",
    """CREATE TABLE IF NOT EXISTS structure_member (
        design TEXT NOT NULL, structure_id TEXT NOT NULL, run_id TEXT NOT NULL,
        atom TEXT NOT NULL, PRIMARY KEY (design, structure_id, run_id, atom))""",
    "CREATE INDEX IF NOT EXISTS structure_run ON structure(run_id)",
)


# Table added in schema version 4 (docs/specs/2026-10-28-mimir-host-alias.md): the scrub record
# that extends an artifact row (`scrubbed_from` is the sha before the private strings were removed).
V4_DDL: tuple[str, ...] = (
    """CREATE TABLE IF NOT EXISTS blob_scrub (
        ref_table TEXT NOT NULL, ref_column TEXT NOT NULL, ref_key TEXT NOT NULL,
        scrubbed_from TEXT NOT NULL, blob_sha256 TEXT NOT NULL,
        PRIMARY KEY (ref_table, ref_column, ref_key))""",
)

V5_ALTER = "ALTER TABLE timing_run ADD COLUMN req_spread_ns REAL"


# Tables added in schema version 5 (docs/specs/2026-10-28-near-critical.md, section 3).
# `req_spread_ns` was added to timing_run while v5 was in review: a v5 store without it gets it
# by ALTER on its next write open (V5_ALTER).
V5_DDL: tuple[str, ...] = (
    """CREATE TABLE IF NOT EXISTS timing_run (
        run_id TEXT PRIMARY KEY, cpd_ns REAL, worst_slack_ns REAL, paths_requested INTEGER,
        paths_in_report INTEGER NOT NULL, paths_used INTEGER NOT NULL, max_req_ns REAL,
        dmax_source TEXT NOT NULL, pairs INTEGER NOT NULL, pairs_skipped INTEGER NOT NULL,
        last_crit REAL, trunc_090 INTEGER NOT NULL, trunc_095 INTEGER NOT NULL,
        trunc_099 INTEGER NOT NULL, n_endpoints_090 INTEGER NOT NULL,
        n_endpoints_095 INTEGER NOT NULL, n_endpoints_099 INTEGER NOT NULL,
        source_kind TEXT NOT NULL CHECK (source_kind IN ('attribution', 'report')),
        source_sha256 TEXT NOT NULL, analysis_n INTEGER, req_spread_ns REAL)""",
    """CREATE TABLE IF NOT EXISTS timing_path_hist (
        run_id TEXT NOT NULL, bin INTEGER NOT NULL, n INTEGER NOT NULL,
        PRIMARY KEY (run_id, bin))""",
    """CREATE TABLE IF NOT EXISTS timing_object (
        run_id TEXT NOT NULL, kind TEXT NOT NULL
        CHECK (kind IN ('module', 'span', 'word', 'structure')),
        object_key TEXT NOT NULL, bit INTEGER NOT NULL DEFAULT -1, via TEXT NOT NULL DEFAULT '',
        crit_max REAL NOT NULL, n_paths INTEGER NOT NULL, n_paths_090 INTEGER NOT NULL,
        n_paths_095 INTEGER NOT NULL, n_paths_099 INTEGER NOT NULL, delay_share_090 REAL,
        PRIMARY KEY (run_id, kind, object_key, bit))""",
)


# Tables added in schema version 6 (docs/specs/2026-10-28-timing-paths.md, section 2): the
# reported paths of a run and their nodes. `bit` is -1 where the attribution gives none.
V6_DDL: tuple[str, ...] = (
    """CREATE TABLE IF NOT EXISTS timing_path (
        run_id TEXT NOT NULL, path_index INTEGER NOT NULL, slack_ns REAL, arrival_ns REAL,
        required_ns REAL, crit REAL, startpoint TEXT NOT NULL, endpoint TEXT NOT NULL,
        n_nodes INTEGER NOT NULL, PRIMARY KEY (run_id, path_index))""",
    """CREATE TABLE IF NOT EXISTS timing_path_node (
        run_id TEXT NOT NULL, path_index INTEGER NOT NULL, step INTEGER NOT NULL,
        atom TEXT, block_type TEXT, pins TEXT, span TEXT, loc TEXT, module TEXT, word TEXT,
        bit INTEGER, word_via TEXT, category TEXT, cell_delay_ns REAL, net_delay_in_ns REAL,
        delay_ns REAL, PRIMARY KEY (run_id, path_index, step))""",
    "CREATE INDEX IF NOT EXISTS timing_path_node_span ON timing_path_node(run_id, span)",
    "CREATE INDEX IF NOT EXISTS timing_path_node_word ON timing_path_node(run_id, word, bit)",
)
