"""Cross-check of the stored L15 counts against the Loki round-6 audit files (read only).

Loki's audit (`loki audit report`, one `<design>.stmt.json` per design) lists the units (stmt-level
anchors) and a status per unit after the last snapshot: `kept`, `late`, `lost`, `born-joined`.
Mimir's `structure.l15_units_*` records count the same units on a single final map. The flows differ
(Loki's f2 script has no `hardmap` and no `--vtr-compat`), so the two are compared, not equated.
"""

from __future__ import annotations

import json
from pathlib import Path

from mimir.store import Store

NOT_SEPARABLE = ("lost", "born-joined")


def loki_counts(path: Path) -> tuple[int, int]:
    """(units, units separable after the last snapshot) of one `<design>.stmt.json`."""
    units = json.loads(path.read_text(encoding="utf-8"))["units"]
    return len(units), sum(1 for u in units if u["status"] not in NOT_SEPARABLE)


def compare(store: Store, audit_dir: Path, prefix: str = "micro_"
            ) -> list[tuple[str, int, int, int, int]]:
    """(design, mimir units, mimir separable, loki units, loki separable) for each stored design
    that has a Loki audit file `audit_dir/<prefix><design>.stmt.json`."""
    rows = store.db.execute(
        "SELECT design, metric, value FROM records WHERE source = 'mimir-structures' "
        "AND metric IN ('structure.l15_units_reached', 'structure.l15_units_separable') "
        "ORDER BY design, metric").fetchall()
    mine: dict[str, dict[str, int]] = {}
    for design, metric, value in rows:
        mine.setdefault(design, {})[metric] = int(value)
    out = []
    for design in sorted(mine):
        f = audit_dir / f"{prefix}{design}.stmt.json"
        if not f.is_file():
            continue
        lu, ls = loki_counts(f)
        m = mine[design]
        out.append((design, m["structure.l15_units_reached"], m["structure.l15_units_separable"],
                    lu, ls))
    return out
