"""The metric registry: the file `mimir/data/metrics.toml`."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources


@dataclass(frozen=True)
class Metric:
    key: str
    description: str
    unit: str
    levels: tuple[str, ...]
    kind: str  # "measured" (computed by Mimir) or "imported" (copied from a source)
    measurer: str
    definition_source: str  # "mimir", "source" (the producing tool) or a citation id
    citations: tuple[str, ...]
    validation: str


def _str_list(item: dict[str, object], key: str) -> tuple[str, ...]:
    val = item.get(key, [])
    if not isinstance(val, list) or not all(isinstance(x, str) for x in val):
        raise ValueError(f"metric {item.get('key')!r}: {key} must be a list of strings")
    return tuple(val)


def _text(item: dict[str, object], key: str) -> str:
    val = item.get(key)
    if not isinstance(val, str) or not val:
        raise ValueError(f"metric {item.get('key')!r}: missing {key!r}")
    return val


def _metric(item: dict[str, object]) -> Metric:
    kind = _text(item, "kind")
    if kind not in ("measured", "imported"):
        raise ValueError(f"metric {item['key']!r}: bad kind {kind!r}")
    return Metric(
        key=_text(item, "key"),
        description=_text(item, "description"),
        unit=_text(item, "unit"),
        levels=_str_list(item, "levels"),
        kind=kind,
        measurer=_text(item, "measurer"),
        definition_source=_text(item, "definition_source"),
        citations=_str_list(item, "citations"),
        validation=_text(item, "validation"),
    )


@lru_cache(maxsize=1)
def load_registry() -> dict[str, Metric]:
    """The registry, keyed by metric key. Raises ValueError on a duplicate or malformed entry."""
    text = resources.files("mimir").joinpath("data/metrics.toml").read_text(encoding="utf-8")
    items = tomllib.loads(text).get("metric", [])
    out: dict[str, Metric] = {}
    for item in items:
        metric = _metric(item)
        if metric.key in out:
            raise ValueError(f"duplicate metric {metric.key!r}")
        out[metric.key] = metric
    return out


def unit_of(key: str) -> str:
    """The registered unit of a metric; KeyError when the metric is not in the registry."""
    return load_registry()[key].unit
