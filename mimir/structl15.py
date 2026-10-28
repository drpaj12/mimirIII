"""Cross-check of the stored L15 counts against the Loki round-6 audit files (read only).

Loki's audit (`loki audit report`, one `<design>.stmt.json` per design) lists the units (stmt-level
anchors) and a status per unit over eight snapshots: `kept`, `late`, `lost`, `born-joined`.
Mimir's `structure.l15_units_*` records count the same units on the single final map of the flow.
They differ in two real ways, so the two are compared, not equated:

- the snapshot set: the audit snapshots after `proc; fsm; opt; flatten; opt -full; wreduce; lower;
  abc --lut 6` (loki/audit/snap.py:12-15, no `hardmap`); the flow here is the full `odin3-flow`
  script, and the units are those of the final BLIF's atoms (LUTs, flip-flops, carry cells, hard
  blocks), not of the objects of snapshot 8;
- the unit definition at the end: the audit's objects are the logic objects of the snapshot JSON
  (loki/audit/units.py `view_map`), Mimir's are the BLIF atoms.

(Loki gives `--vtr-compat` to the `.v` files of both, loki/odin.py:64-70; the read flags are not a
difference for these designs.)

Loki's `lost` also covers a unit that is pure again at a later snapshot (`loss.transient`,
loki/audit/loss.py:118-146, `later`), so `lost` is not "not separable at the end". The audit file
has no final-snapshot separable field, so `loki_counts` gives bounds: the lower bound counts
`kept` and `late` units; the upper bound adds the `lost` units flagged `transient` (pure again
after the loss, not necessarily at the last snapshot).
"""

from __future__ import annotations

import json
from pathlib import Path

from mimir.store import Store

SEPARABLE = ("kept", "late")


def loki_counts(path: Path) -> tuple[int, int, int]:
    """(units, separable at the final snapshot: lower bound, upper bound) of one
    `<design>.stmt.json`."""
    units = json.loads(path.read_text(encoding="utf-8"))["units"]
    low = sum(1 for u in units if u["status"] in SEPARABLE)
    transient = sum(1 for u in units if u["status"] == "lost"
                    and u.get("loss", {}).get("transient"))
    return len(units), low, low + transient


def compare(store: Store, audit_dir: Path, prefix: str = "micro_"
            ) -> list[tuple[str, int, int, int, int, int]]:
    """(design, mimir units, mimir separable, loki units, loki separable lower, upper) for each
    stored design that has a Loki audit file `audit_dir/<prefix><design>.stmt.json`."""
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
        lu, lo, hi = loki_counts(f)
        m = mine[design]
        out.append((design, m["structure.l15_units_reached"], m["structure.l15_units_separable"],
                    lu, lo, hi))
    return out
