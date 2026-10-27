"""Shared pieces of the importers: the report and the record builder."""

from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from mimir.registry import load_registry
from mimir.schema import Record


@dataclass
class Report:
    """Per source: rows read, rows that gave at least one record, records, and skips by reason."""

    seen: Counter[str] = field(default_factory=Counter)
    used: Counter[str] = field(default_factory=Counter)
    records: Counter[str] = field(default_factory=Counter)
    skipped: dict[str, Counter[str]] = field(default_factory=dict)

    def skip(self, source: str, reason: str, n: int = 1) -> None:
        self.skipped.setdefault(source, Counter())[reason] += n

    def merge(self, other: Report) -> None:
        self.seen.update(other.seen)
        self.used.update(other.used)
        self.records.update(other.records)
        for source, reasons in other.skipped.items():
            self.skipped.setdefault(source, Counter()).update(reasons)

    def lines(self) -> list[str]:
        out = []
        for source in sorted(set(self.seen) | set(self.skipped)):
            out.append(
                f"{source}: read {self.seen[source]}, used {self.used[source]}, "
                f"records {self.records[source]}"
            )
            for reason, n in sorted(self.skipped.get(source, Counter()).items()):
                out.append(f"  skipped {n}: {reason}")
        return out


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True)
class Ctx:
    """The fields shared by the records of one design (or one run) from one source."""

    design: str
    source: str
    origin: str
    measurer: str
    measurer_version: str
    input_sha256: str = ""
    tool_commit: str = ""
    script_hash: str = ""
    arch: str = ""
    seed: int = -1
    arm: str = ""
    family: str = ""

    def rec(self, metric: str, level: str, value: float, bin: str = "") -> Record:
        """A record whose unit comes from the registry (KeyError if the metric is unregistered)."""
        return Record(
            design=self.design, source=self.source, input_sha256=self.input_sha256,
            tool_commit=self.tool_commit, script_hash=self.script_hash, level=level,
            arch=self.arch, seed=self.seed, arm=self.arm, family=self.family, metric=metric,
            bin=bin, value=float(value), unit=load_registry()[metric].unit,
            measurer=self.measurer, measurer_version=self.measurer_version, origin=self.origin,
        )
