"""The record schema (version 1): one tidy row per measured value."""

from __future__ import annotations

from dataclasses import astuple, dataclass, fields

SCHEMA_VERSION = 1
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
