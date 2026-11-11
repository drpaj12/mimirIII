"""AI digit recognition results in the store (schema 8): read a suite's `results/*.jsonl`, join
them with `implementations.toml`, write `aidigit_result` and `aidigit_null`.
Spec: docs/specs/2026-11-10-ai-digit-results.md.

One row per (suite, design, target). A value the source row does not hold is NULL and has a reason
in `aidigit_null`; no value is ever filled in from anywhere but the source row, the design's
entry in `implementations.toml` and the suite's `pins.toml`."""

from __future__ import annotations

import json
import re
import sqlite3
import tomllib
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mimir.schema import AIDIGIT_COLUMNS
from mimir.store import Store

COLS = tuple(n for n, _ in AIDIGIT_COLUMNS)
RTL_TARGET = "rtl"
Json = dict[str, Any]
Row = dict[str, Any]

# columns a target fills from its own leg; a NULL among them needs a reason
VTR_FIELDS = ("grid_w", "grid_h", "grid_tiles", "clb_tiles", "clb_util_pct", "area_lut",
              "area_ff", "area_adder", "area_clb", "area_mult36", "area_ram_blocks",
              "area_grid", "area_min_chan_width", "area_wirelength", "speed_fmax_mhz",
              "speed_crit_path_ns", "speed_latency_us", "speed_ii_cycles", "speed_images_per_s",
              "power_total_mw", "power_dynamic_mw", "power_static_mw", "power_method",
              "power_channel_width", "energy_uj_per_img", "arch_file", "acc_netlist_n",
              "acc_netlist_class_match")
LPM_FIELDS = ("lpm_mult", "lpm_add_sub", "lpm_compare", "lpm_altsyncram", "lpm_scfifo",
              "netlist_bytes", "area_alm", "area_dsp_blocks", "area_m10k_blocks",
              "speed_fmax_mhz", "speed_latency_us", "power_total_mw", "energy_uj_per_img")
COMMON_FIELDS = ("acc_n", "acc_top1", "acc_class_match", "acc_score_match", "speed_cycles_per_img",
                 "speed_init_cycles", "odin3_build", "odin3_commit", "rtl_sha256", "run_date")
# the fixed-device leg (tools/fixed_device.py) routes at a given W and runs no netlist simulation
FIXED_TARGET = "vtr-k6-fixed"
FIXED_FIELDS = tuple(f for f in VTR_FIELDS if f not in (
    "area_min_chan_width", "acc_netlist_n", "acc_netlist_class_match"))
TARGET_FIELDS = {"vtr-k6": VTR_FIELDS, FIXED_TARGET: FIXED_FIELDS, "cyclonev-lpm": LPM_FIELDS,
                 RTL_TARGET: ()}
# source null_reason keys that explain a column, by column prefix (first key present wins)
REASON_KEYS = (
    ("area_alm", ("area.alm", "area")), ("area_dsp_blocks", ("area.dsp_blocks", "area")),
    ("area_m10k_blocks", ("area.m10k_blocks", "area")), ("acc_netlist",
     ("accuracy.netlist_odin_sim", "accuracy.netlist", "area")),
    ("area_min_chan_width", ("area.min_chan_width", "area")),
    ("grid_", ("area",)), ("clb_", ("area",)), ("area_", ("area",)), ("lpm_", ("area",)),
    ("netlist_bytes", ("area",)),
    ("arch_file", ("area",)), ("speed_", ("speed",)), ("power_", ("power",)),
    ("energy_", ("power",)),
)


@dataclass
class Imported:
    rows: list[Row] = field(default_factory=list)
    # (design, target, field, reason)
    nulls: list[tuple[str, str, str, str]] = field(default_factory=list)

    def per_impl(self) -> Counter[str]:
        return Counter(r["impl_id"] for r in self.rows)


def clb_tiles(layout: Json, width: int, height: int) -> int:
    """clb tiles of VPR's auto-sized grid `width` x `height` (IO ring included). The IO ring takes
    the outer tile on each side; every column of a hard block (`layout.columns`, from the arch's
    auto_layout `<col>` lines: first x `startx`, every `repeatx`) that fits inside the ring takes
    the whole interior height (a block that does not fit leaves EMPTY tiles, not clbs); the rest of
    the interior is clb. Checked against the clb count VPR prints for 18 grids (see the spec
    2026-11-10-ai-digit-grid.md)."""
    ring = int(layout["io_ring"])
    inner_w, inner_h = width - 2 * ring, height - 2 * ring
    taken = sum(len(range(int(c["startx"]), width - ring, int(c["repeatx"])))
                for c in layout["columns"])
    return inner_h * (inner_w - taken)


def load_layouts(suite: Path) -> Json:
    """The `[arch_layout]` tables of a suite's implementations.toml, by arch file name."""
    cfg = tomllib.loads((suite / "implementations.toml").read_text(encoding="utf-8"))
    return dict(cfg.get("arch_layout", {}))


def _grid_cols(area: Json, layouts: Json, arch: str | None) -> Row:
    """Device-size columns of a VPR leg: grid W x H, tiles, clb tiles, clb use in percent."""
    grid = area.get("grid")
    if not grid:
        return {}
    w, h = int(grid[0]), int(grid[1])
    out: Row = {"grid_w": w, "grid_h": h, "grid_tiles": w * h}
    layout = layouts.get(arch or "")
    if layout is not None:
        tiles = clb_tiles(layout, w, h)
        out["clb_tiles"] = tiles
        if area.get("clbs") is not None:
            out["clb_util_pct"] = area["clbs"] / tiles * 100
    return out


def has_tables(db: sqlite3.Connection) -> bool:
    """True when the store has the schema 8 tables (a store of version 4 to 7 does not)."""
    return db.execute("SELECT 1 FROM sqlite_master WHERE name = 'aidigit_result'").fetchone() \
        is not None


def _read_jsonl(path: Path) -> list[tuple[int, Json]]:
    out = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            out.append((n, json.loads(line)))
    return out


def _num(d: Json | None, key: str) -> Any:
    return None if not d else d.get(key)


def _accuracy_pool(rows: list[tuple[str, int, Json]]) -> dict[str, Json]:
    """Best RTL accuracy per design: the full tier (10,000 images) from rtl.jsonl or from a leg's
    `rtl_verilator_full`, else the quick tier (100). Accuracy is a property of the RTL, not of the
    target, so every target row of a design carries the same accuracy."""
    best: dict[str, tuple[int, Json, str]] = {}

    def offer(design: str, res: Json | None, tier: str, rank: int) -> None:
        if res and design not in best or res and rank > best[design][0]:
            best[design] = (rank, res, tier)

    for _, _, row in rows:
        d = row["design"]
        if "result" in row:
            if row.get("error") is None:
                offer(d, row["result"], row["tier"], 2 if row["tier"] == "full" else 1)
            continue
        acc = row.get("accuracy") or {}
        offer(d, acc.get("rtl_verilator_full"), "full", 2)
        offer(d, acc.get("rtl_verilator"), "quick", 1)
    return {d: {**res, "_tier": tier} for d, (_, res, tier) in best.items()}


def _accuracy_cols(res: Json | None) -> Row:
    if not res:
        return {}
    return {"acc_tier": res["_tier"], "acc_sim": "verilator", "acc_n": res.get("n"),
            "acc_label_correct": res.get("label_correct"), "acc_top1": res.get("top1"),
            "acc_class_match": res.get("class_match"), "acc_score_match": res.get("score_match"),
            "speed_init_cycles": res.get("init_cycles"),
            "speed_cycles_per_img": res.get("cycles_per_img")}


def _leg_cols(row: Json, layouts: Json) -> Row:
    area, speed, power = row.get("area") or {}, row.get("speed") or {}, row.get("power") or {}
    lpm = row.get("lpm_cells")

    def cells(kind: str) -> int | None:
        """Instances of a cell type; a type absent from a present count table has none."""
        return None if lpm is None else int(lpm.get(kind, 0))

    grid = area.get("grid")
    method = power.get("method")
    width = re.search(r"\bW=(\d+)", method) if method else None
    net = (row.get("accuracy") or {}).get("netlist_odin_sim")
    note = str(speed.get("note", ""))
    out: Row = {
        "area_lut": area.get("luts"), "area_ff": area.get("ffs"), "area_adder": area.get("adders"),
        "area_clb": area.get("clbs"), "area_mult36": area.get("dsp_mult36"),
        "area_ram_blocks": area.get("ram_blocks"),
        "area_grid": f"{grid[0]}x{grid[1]}" if grid else None,
        "area_min_chan_width": area.get("min_chan_width"),
        "area_wirelength": area.get("wirelength"),
        "lpm_mult": cells("lpm_mult"), "lpm_add_sub": cells("lpm_add_sub"),
        "lpm_compare": cells("lpm_compare"), "lpm_altsyncram": cells("altsyncram"),
        "lpm_scfifo": cells("scfifo"), "netlist_bytes": row.get("netlist_bytes"),
        "area_alm": area.get("alm"), "area_dsp_blocks": area.get("dsp_blocks"),
        "area_m10k_blocks": area.get("m10k_blocks"),
        "speed_fmax_mhz": speed.get("fmax_mhz"), "speed_crit_path_ns": speed.get("crit_path_ns"),
        "speed_cycles_per_img": speed.get("cycles_per_img"),
        "speed_latency_us": speed.get("latency_us"),
        "speed_ii_cycles": speed.get("ii_cycles") or (speed.get("cycles_per_img")
                                                       if "initiation interval = cycles_per_img"
                                                       in note else None),
        "speed_images_per_s": speed.get("images_per_s"),
        "power_total_mw": power.get("total_mw"), "power_dynamic_mw": power.get("dynamic_mw"),
        "power_static_mw": power.get("static_mw"), "power_method": method,
        "power_channel_width": int(width.group(1)) if width else None,
        "energy_uj_per_img": power.get("energy_uj_per_img"),
        "acc_netlist_n": _num(net, "n"), "acc_netlist_class_match": _num(net, "class_match"),
        "arch_file": (row.get("tools") or {}).get("arch"),
        **_grid_cols(area, layouts, (row.get("tools") or {}).get("arch")),
    }
    return {k: v for k, v in out.items() if v is not None}


def _reason(col: str, source: Json, target: str) -> str:
    for prefix, keys in REASON_KEYS:
        if col.startswith(prefix):
            for key in keys:
                if key in source:
                    return str(source[key])
            break
    return f"not in the source row ({target} leg)"


def _design_cols(entry: Json, pins: dict[str, Json], tools: Json) -> Row:
    src = pins.get(entry["design_source"], {})
    out: Row = {
        "impl_id": entry["impl_id"], "arch_name": entry["arch_name"], "setting": entry["setting"],
        "model_kind": entry["model_kind"], "acc_ref": entry["acc_ref"],
        "design_source": entry["design_source"], "design_source_commit": src.get("commit"),
        "rtl_sha256": entry.get("rtl_sha256"), "odin3_build": tools.get("odin3_build"),
        "odin3_commit": tools.get("odin3_commit"),
    }
    return {k: v for k, v in out.items() if v is not None}


def _provenance_nulls(entry: Json, tools: Json, row: Row, target: str) -> dict[str, str]:
    out: dict[str, str] = {}
    if row.get("rtl_sha256") is None:
        out["rtl_sha256"] = str(entry.get("rtl_sha256_reason", "no hash recorded"))
    if row.get("run_date") is None:
        out["run_date"] = str(tools.get("run_date_reason", "not recorded"))
    if target in ("vtr-k6", FIXED_TARGET):
        out["vtr_commit"] = str(tools.get("vtr_commit_reason", "not recorded"))
    return out


Ctx = tuple[Json, dict[str, Json], Json, dict[str, Json], Json]
Leg = tuple[str, int, Json]


def _build_row(design: str, target: str, leg: Leg | None,
               ctx: Ctx) -> tuple[Row, dict[str, str]]:
    entries, pins, tools, acc, layouts = ctx
    entry = entries[design]
    row: Row = {c: None for c in COLS}
    row.update(_design_cols(entry, pins, tools))
    row.update(_accuracy_cols(acc.get(design)))
    source: Json = {}
    if leg is not None:
        fname, line, src = leg
        row.update(_leg_cols(src, layouts))
        row["result_tier"], row["origin"] = src.get("tier", ""), f"results/{fname}:{line}"
        source = src.get("null_reason") or {}
    row["suite"], row["design"], row["target"] = "ai-digit-recognition", design, target
    if leg is None:
        row["result_tier"], row["origin"] = acc[design]["_tier"], "results/rtl.jsonl"
    nulls = _provenance_nulls(entry, tools, row, target)
    for col in COMMON_FIELDS + TARGET_FIELDS[target]:
        if row.get(col) is None and col not in nulls:
            nulls[col] = _reason(col, source, target)
    return row, nulls


def _load_legs(suite: Path, files: list[str]) -> list[tuple[str, int, Json]]:
    legs: list[tuple[str, int, Json]] = []
    for name in files:
        path = suite / "results" / name
        if path.is_file():
            legs.extend((name, n, row) for n, row in _read_jsonl(path))
    return legs


def load(suite: Path) -> Imported:
    """The rows and null reasons of a suite directory. Raises ValueError for a design without an
    entry in implementations.toml and for two rows of one (design, target)."""
    cfg = tomllib.loads((suite / "implementations.toml").read_text(encoding="utf-8"))
    pins = {s["id"]: s for s in tomllib.loads(
        (suite / "pins.toml").read_text(encoding="utf-8")).get("source", [])}
    entries = {d["id"]: d for d in cfg["design"]}
    legs = _load_legs(suite, list(cfg["results"]["files"]))
    unknown = sorted({r["design"] for _, _, r in legs} - set(entries))
    if unknown:
        raise ValueError(f"designs without an entry in implementations.toml: {', '.join(unknown)}")
    acc = _accuracy_pool([(f, n, r) for f, n, r in legs])
    ctx = (entries, pins, cfg.get("tools", {}), acc, cfg.get("arch_layout", {}))
    by_key: dict[tuple[str, str], tuple[str, int, Json]] = {}
    for item in legs:
        if "target" not in item[2]:
            continue
        key = (item[2]["design"], item[2]["target"])
        if key in by_key:
            raise ValueError(f"two result rows for {key}: {by_key[key][0]} and {item[0]}")
        by_key[key] = item
    keys: dict[tuple[str, str], Leg | None] = dict(by_key)
    for design in acc:
        if not any(d == design for d, _ in by_key):
            keys[(design, RTL_TARGET)] = None
    out = Imported()
    for (design, target), found in sorted(keys.items()):
        row, nulls = _build_row(design, target, found, ctx)
        out.rows.append(row)
        out.nulls.extend((design, target, c, why) for c, why in sorted(nulls.items()))
    return out


def write(store: Store, data: Imported, suite_id: str = "ai-digit-recognition") -> tuple[int, int]:
    """Replace the suite's rows by `data` in one transaction; returns (rows, null reasons)."""
    marks = ", ".join("?" for _ in COLS)
    db = store.db
    try:
        db.execute("DELETE FROM aidigit_result WHERE suite = ?", (suite_id,))
        db.execute("DELETE FROM aidigit_null WHERE suite = ?", (suite_id,))
        db.executemany(f"INSERT INTO aidigit_result ({', '.join(COLS)}) VALUES ({marks})",
                       [tuple(r[c] for c in COLS) for r in data.rows])
        db.executemany("INSERT INTO aidigit_null VALUES (?, ?, ?, ?, ?)",
                       [(suite_id, d, t, f, why) for d, t, f, why in data.nulls])
        db.commit()
    except BaseException:
        db.rollback()
        raise
    return len(data.rows), len(data.nulls)


def read_rows(db: sqlite3.Connection, suite_id: str = "ai-digit-recognition") -> list[Row]:
    """The stored rows, sorted by implementation, setting order and target."""
    db.row_factory = sqlite3.Row
    try:
        got = db.execute("SELECT * FROM aidigit_result WHERE suite = ? ORDER BY impl_id, design, "
                         "target", (suite_id,)).fetchall()
    finally:
        db.row_factory = None
    return [dict(r) for r in got]


def read_nulls(db: sqlite3.Connection, suite_id: str = "ai-digit-recognition"
               ) -> dict[tuple[str, str, str], str]:
    return {(d, t, f): why for d, t, f, why in db.execute(
        "SELECT design, target, field, reason FROM aidigit_null WHERE suite = ?", (suite_id,))}
