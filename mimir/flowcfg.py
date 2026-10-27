"""Flow configurations and runs: the `flow_config`, `flow_param`, `run` tables.

The configurations of the imported data are rebuilt from what the runner scripts and plans state
(read only, every `given` parameter cited as script:line). Norns arms come from the explicit
tables of `armtables`: an arm not in its round's table is skipped with the reason, never defaulted.
A parameter no source states is `unknown`; a tool default is `default` (value and source version
cited) or `default-unrecorded`; a config with an unknown or unrecorded parameter is `partial`.
Spec: docs/specs/2026-10-27-mimir-schema-v2.md, sections 3.4, 3.5, 6.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from mimir.armtables import ARCH_REL, UnknownArm, norns_spec
from mimir.flowspec import (
    Spec,
    SrcRoots,
    abc_default_script,
    abc_lut_default,
    add_found,
)
from mimir.importers.loki import find_datasets
from mimir.schema import UNKNOWN_CONF
from mimir.store import Store

__all__ = ["ARCH_REL", "ImportResult", "Spec", "SrcRoots", "UnknownArm", "config_coverage",
           "import_runs", "loki_spec", "norns_spec", "run_id_of", "unknown_params"]

LOKI_SRC = "meta.json script of the floor"
_DESIGN_FILE = re.compile(r"(read_verilog[^;]*?)\s+\S+\.(sv|v)\b")


def loki_spec(floor: str, script: list[str], meta: dict[str, object],
              roots: SrcRoots | None = None) -> Spec:
    """The flow configuration of one Loki floor, from the script its meta.json recorded."""
    roots = roots or SrcRoots()
    lines = [_DESIGN_FILE.sub(r"\1 <design>.\2", ln) for ln in script]
    spec = Spec(name=f"loki/{floor}", text="\n".join(lines), text_kind="recorded-normalised",
                origin="meta.json of the floor (script list, design file name replaced)")
    arch = re.search(r"read_(?:arch|techlib) (\S+?);", lines[0] + ";") if lines else None
    named = arch is not None and not arch.group(1).startswith("<")
    spec.add("arch", "arch", arch.group(1) if arch and named else "",
             "given" if named else "unknown", LOKI_SRC)
    spec.add("odin", "passes", ";".join(ln.split(";")[-1].strip() for ln in lines), "given",
             LOKI_SRC)
    abc = [ln for ln in lines if ln.startswith("abc")]
    spec.add("abc", "abc_cmd", abc[0] if abc else "none", "given", LOKI_SRC)
    version = str(meta.get("odin3_version", ""))
    rev = f"v{version}" if version else ""
    lut = re.search(r"--lut (\d+)", abc[0]) if abc else None
    if lut:
        spec.add("abc", "lut_k", lut.group(1), "given", LOKI_SRC)
    elif abc:
        add_found(spec, "abc", "lut_k", abc_lut_default(roots.odin3, rev) if rev else None,
                  roots.odin3, rev, f"odin3 tag {rev} (the version meta.json states)",
                  "odin3 checkout or version not available")
    gates = re.search(r"--gates (\S+)", abc[0]) if abc else None
    if gates:
        spec.add("abc", "gates", gates.group(1), "given", LOKI_SRC)
    elif abc:
        spec.add("abc", "gates", "none", "given", LOKI_SRC + " (no --gates in the abc command)")
    if abc:
        found = abc_default_script(roots.odin3, rev, gates=bool(gates)) if rev else None
        add_found(spec, "abc", "abc_script", found, roots.odin3, rev,
                  f"odin3 tag {rev} (the version meta.json states)",
                  "odin3 checkout or version not available")
    spec.add("odin", "odin3_version", version, "given" if version else "unknown",
             "meta.json odin3_version")
    spec.add("odin", "abi_version", str(meta.get("abi_version", "")),
             "given" if meta.get("abi_version") is not None else "unknown", "meta.json abi_version")
    spec.add("odin", "odin3_commit", "", "unknown", "meta.json holds versions, not commits")
    return spec


def loki_runs(loki_root: Path, roots: SrcRoots) -> list[tuple[str, str, str, Spec]]:
    """(source, design, floor, spec) for every floor meta.json under the Loki sources."""
    out: list[tuple[str, str, str, Spec]] = []
    for sub in sorted(loki_root.glob("loki-*")):
        for ds in find_datasets(sub) if sub.is_dir() else []:
            source = "loki:" + ds.relative_to(loki_root).as_posix()
            for path in sorted(ds.glob("*/*/meta.json")):
                meta = json.loads(path.read_text(encoding="utf-8"))
                script = meta.get("script")
                if not isinstance(script, list):
                    continue
                floor = str(meta.get("floor", path.parent.name))
                out.append((source, path.parent.parent.name, floor,
                            loki_spec(floor, script, meta, roots)))
    return out


# ---------------------------------------------------------------- tables

def put_config(store: Store, spec: Spec) -> str:
    h = spec.config_hash()
    store.db.execute("INSERT OR REPLACE INTO flow_config VALUES (?, ?, ?, ?, ?, ?)",
                     (h, spec.name, spec.text, spec.text_kind, spec.status(), spec.origin))
    store.db.execute("DELETE FROM flow_param WHERE config_hash = ?", (h,))
    store.db.executemany("INSERT OR REPLACE INTO flow_param VALUES (?, ?, ?, ?, ?, ?)",
                         [(h, *p) for p in spec.params])
    return h


def _esc(part: str) -> str:
    return part.replace("\\", "\\\\").replace("|", "\\|")


def run_id_of(source: str, design: str, arch: str, seed: int, arm: str, config_hash: str = "",
              tool_commit: str = "", input_sha256: str = "") -> str:
    """The run key, `|` and `\\` escaped so that no two different keys give the same text."""
    key = "|".join(_esc(p) for p in (source, design, arch, str(seed), arm, config_hash,
                                     tool_commit, input_sha256))
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _slug(store: Store, source: str, design: str) -> str:
    row = store.db.execute("SELECT slug FROM design_source WHERE source=? AND name=?",
                           (source, design)).fetchone()
    return str(row[0]) if row else ""


@dataclass
class ImportResult:
    """Runs imported per source, runs skipped per reason, runs whose time is ambiguous."""

    counts: dict[str, int] = field(default_factory=dict)
    skipped: Counter[str] = field(default_factory=Counter)
    ambiguous_time: int = 0


_DERIVED = ("slug", "config_hash", "source", "design", "arch", "seed", "arm", "family",
            "tool_commits", "origin", "tool_commit", "input_sha256")


def _put_run(store: Store, key: tuple[str, str, str, int, str], family: str, config: str,
             tool_commit: str, input_sha: str, origin: str) -> None:
    """Insert a run, or refresh only its derived columns (command_line, host, time and the
    artifacts a runner filled in are kept)."""
    source, design, arch, seed, arm = key
    rid = run_id_of(source, design, arch, seed, arm, config, tool_commit, input_sha)
    commits = f"vtr={tool_commit}" if tool_commit else ""
    values = {"run_id": rid, "slug": _slug(store, source, design), "config_hash": config,
              "source": source, "design": design, "arch": arch, "seed": seed, "arm": arm,
              "family": family, "tool_commits": commits, "origin": origin,
              "tool_commit": tool_commit, "input_sha256": input_sha}
    cols = ", ".join(values)
    marks = ", ".join(f":{c}" for c in values)
    sets = ", ".join(f"{c} = excluded.{c}" for c in _DERIVED)
    store.db.execute(f"INSERT INTO run ({cols}) VALUES ({marks}) "
                     f"ON CONFLICT(run_id) DO UPDATE SET {sets}", values)


def _fill_time_rss(store: Store) -> int:
    """time_s and peak_rss_mib from the routed-level, bin-less VPR rows. A run with more than one
    such row (the same run stored twice) is left NULL and counted: the value is ambiguous."""
    ambiguous = 0
    for col, metric in (("time_s", "vpr.flow_time"), ("peak_rss_mib", "vpr.max_rss")):
        rows = store.db.execute(
            "SELECT u.run_id, COUNT(r.value), MIN(r.value) FROM run u LEFT JOIN records r "
            "ON r.source = u.source AND r.design = u.design AND r.arch = u.arch "
            "AND r.seed = u.seed AND r.arm = u.arm AND r.tool_commit = u.tool_commit "
            "AND r.input_sha256 = u.input_sha256 AND r.metric = ? AND r.level = 'routed' "
            "AND r.bin = '' GROUP BY u.run_id", (metric,)).fetchall()
        updates = [(value if n == 1 else None, rid) for rid, n, value in rows]
        ambiguous += sum(1 for _, n, _ in rows if n > 1)
        store.db.executemany(f"UPDATE run SET {col} = ? WHERE run_id = ?", updates)
    return ambiguous


def _prune_configs(store: Store) -> None:
    store.db.execute("DELETE FROM flow_param WHERE config_hash NOT IN "
                     "(SELECT config_hash FROM run)")
    store.db.execute("DELETE FROM flow_config WHERE config_hash NOT IN "
                     "(SELECT config_hash FROM run)")


def import_runs(store: Store, arch_sha: str | None, loki_root: Path | None,
                roots: SrcRoots | None = None) -> ImportResult:
    """Create flow_config and run rows for the imported Norns and Loki data, in one transaction.
    Runs of an arm outside its round's table are skipped and counted with the reason. Needs the
    designs registered first (the run's slug comes from design_source)."""
    roots = roots or SrcRoots()
    res = ImportResult()
    cache: dict[tuple[str, str, bool], tuple[str, str]] = {}  # -> (config hash, skip reason)
    try:
        groups = store.db.execute(
            "SELECT source, design, arch, seed, arm, family, tool_commit, input_sha256, "
            "MIN(origin) FROM records WHERE (source LIKE 'norns-r%' OR source = 'wyrd-atlas-r7') "
            "AND source != 'norns-r7-corpus' "
            "GROUP BY source, design, arch, seed, arm, family, tool_commit, input_sha256 "
            "ORDER BY 1, 2, 3, 4, 5, 6, 7, 8").fetchall()
        for source, design, arch, seed, arm, family, commit, sha, origin in groups:
            n5 = design.startswith("n5_")
            ck = (source, arm, n5)
            if ck not in cache:
                cache[ck] = _config_for(store, source, arm, n5, arch_sha, roots)
            h, reason = cache[ck]
            if reason:
                res.skipped[reason] += 1
                continue
            _put_run(store, (source, design, arch, seed, arm), family, h, commit, sha, origin)
            res.counts[source] = res.counts.get(source, 0) + 1
        if loki_root is not None:
            _import_loki_runs(store, loki_root, roots, res)
        res.ambiguous_time = _fill_time_rss(store)
        _prune_configs(store)
        store.db.commit()
    except BaseException:
        store.db.rollback()
        raise
    return res


def _config_for(store: Store, source: str, arm: str, n5: bool, arch_sha: str | None,
                roots: SrcRoots) -> tuple[str, str]:
    try:
        return put_config(store, norns_spec(source, arm, n5, arch_sha, roots)), ""
    except UnknownArm as exc:
        return "", str(exc)


def _import_loki_runs(store: Store, loki_root: Path, roots: SrcRoots, res: ImportResult) -> None:
    cache: dict[str, str] = {}
    for source, design, floor, spec in loki_runs(loki_root, roots):
        h = spec.config_hash()
        if h not in cache:
            cache[h] = put_config(store, spec)
        _put_run(store, (source, design, floor, -1, ""), "", h, "", "",
                 f"{source}/{design}/{floor}")
        res.counts[source] = res.counts.get(source, 0) + 1


def config_coverage(store: Store) -> list[tuple[str, str, int, int]]:
    """(source, status, configs used, runs) over the runs, one row per source and status."""
    rows = store.db.execute(
        "SELECT u.source, c.status, COUNT(DISTINCT c.config_hash), COUNT(*) FROM run u "
        "JOIN flow_config c ON c.config_hash = u.config_hash GROUP BY 1, 2 ORDER BY 1, 2"
    ).fetchall()
    return [(a, b, int(c), int(d)) for a, b, c, d in rows]


def param_conf_counts(store: Store) -> list[tuple[str, int, int]]:
    """(conf, parameter rows, parameter rows used by a run's config)."""
    rows = store.db.execute(
        "SELECT p.conf, COUNT(*), SUM(p.config_hash IN (SELECT config_hash FROM run)) "
        "FROM flow_param p GROUP BY p.conf ORDER BY p.conf").fetchall()
    return [(a, int(b), int(c)) for a, b, c in rows]


def unknown_params(store: Store) -> list[tuple[str, str, int]]:
    """(step.key, source group, configs) for every parameter that is unknown or unrecorded."""
    marks = ", ".join(repr(c) for c in UNKNOWN_CONF)
    rows = store.db.execute(
        "SELECT p.step || '.' || p.key, substr(c.name, 1, instr(c.name || '/', '/') - 1), "
        f"COUNT(DISTINCT c.config_hash) FROM flow_param p JOIN flow_config c "
        f"ON c.config_hash = p.config_hash WHERE p.conf IN ({marks}) GROUP BY 1, 2 ORDER BY 1, 2"
    ).fetchall()
    return [(a, b, int(c)) for a, b, c in rows]
