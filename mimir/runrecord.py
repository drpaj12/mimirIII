"""Import the run records Norns runners write (`mimir-run.json`, record_version 1).

A record is checked against docs/specs/2026-10-28-mimir-run-record.md; a record that fails is
refused with every reason. A valid one becomes a `flow_config` (parameters with the conf as
recorded, nothing reconstructed), `flow_param` rows and a `run` row.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mimir.flowcfg import ConfigConflict, _put_run, put_config, run_id_of
from mimir.flowspec import Spec
from mimir.schema import FAMILIES, PARAM_CONF
from mimir.store import Store

RECORD_VERSION = 1
KINDS = ("norns-run",)
FILE_NAME = "mimir-run.json"
_HOST = re.compile(r"host-\d+")
_UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
# an absolute path in a value: a slash that starts the string or follows a blank, `=`, `:`, a
# quote or a bracket and is followed by a path character (spec section 6); /dev/null is allowed
_ABS = re.compile(r"(?:^|[\s=,;:'\"(\[])/(?!dev/null(?![\w.-]))[\w.~-]")
_SHA40 = re.compile(r"[0-9a-f]{40}")
_SHA64 = re.compile(r"[0-9a-f]{64}")
_CITE = re.compile(r":\d+(-\d+)?$")
_SEED = re.compile(r"(--seed\s+)\S+")
_REQUIRED: dict[str, type | tuple[type, ...]] = {
    "source": str, "design": str, "arch": str, "seed": int, "arm": str, "family": str,
    "host": str, "kernel": str, "started_utc": str, "steps": list, "tools": dict,
    "params": dict, "inputs": dict, "artifacts": dict, "ok": bool,
    "time_s": (int, float, type(None)), "peak_rss_mib": (int, float, type(None)),
    "time_conf": str}
_STEP: dict[str, type | tuple[type, ...]] = {
    "name": str, "argv": list, "exit_code": int, "time_s": (int, float, type(None)),
    "peak_rss_mib": (int, float, type(None)), "time_conf": str, "locked": bool, "shared": bool}
_TIME_CONF = ("given", "unknown")


@dataclass
class ImportReport:
    """Records imported, refused (file, reasons), and each imported run's status."""

    imported: list[tuple[str, str, str]] = field(default_factory=list)  # (arm, design, status)
    refused: list[tuple[str, list[str]]] = field(default_factory=list)


def _type_errors(obj: dict[str, Any], spec: dict[str, Any], where: str) -> list[str]:
    errs = []
    for key, typ in spec.items():
        val = obj.get(key)
        if key not in obj:
            errs.append(f"{where}: missing '{key}'")
        elif not isinstance(val, typ) or (typ is int and isinstance(val, bool)):
            errs.append(f"{where}: '{key}' has the wrong type")
    return errs


def _strings(obj: object, where: str = "record") -> list[tuple[str, str]]:
    """(location, string) of every string in `obj`; the location is a key path, never a value."""
    if isinstance(obj, str):
        return [(where, obj)]
    if isinstance(obj, dict):
        return [x for k, v in obj.items() for x in _strings(v, f"{where}.{k}")]
    if isinstance(obj, list):
        return [x for i, v in enumerate(obj) for x in _strings(v, f"{where}[{i}]")]
    return []


def _param_errors(params: dict[str, Any]) -> list[str]:
    errs = []
    for key, p in sorted(params.items()):
        if not isinstance(p, dict) or not all(isinstance(p.get(f), str) for f in
                                              ("value", "conf", "source")):
            errs.append(f"param {key}: needs string value, conf and source")
        elif p["conf"] not in PARAM_CONF:
            errs.append(f"param {key}: conf {p['conf']!r} not in {PARAM_CONF}")
        elif not p["source"]:
            errs.append(f"param {key}: empty source")
        elif p["conf"] == "given" and not p["value"]:
            errs.append(f"param {key}: given with an empty value")
        elif p["conf"] == "default" and not _CITE.search(p["source"]):
            errs.append(f"param {key}: default without a file:line citation")
    return errs


def _time_errors(obj: dict[str, Any], where: str) -> list[str]:
    """`time_conf` is given for a number and unknown for a null: a missing time is never a 0."""
    conf = obj.get("time_conf")
    if conf not in _TIME_CONF:
        return [f"{where}: time_conf must be one of {_TIME_CONF}"]
    if (obj.get("time_s") is None) != (conf == "unknown"):
        return [f"{where}: time_s is null exactly when time_conf is unknown"]
    return []


def _file_errors(table: str, files: dict[str, Any]) -> list[str]:
    errs = []
    for role, f in sorted(files.items()):
        path, sha = (f.get("path"), f.get("sha256")) if isinstance(f, dict) else (None, None)
        if not isinstance(path, str) or not path or path.startswith("/") or ".." in path.split("/"):
            errs.append(f"{table}.{role}: path must be relative")
        if not isinstance(sha, str) or not _SHA64.fullmatch(sha):
            errs.append(f"{table}.{role}: sha256 must be 64 hex")
    return errs


def _tool_errors(tools: dict[str, Any]) -> list[str]:
    errs = [] if tools else ["tools: empty"]
    for name, t in sorted(tools.items()):
        if not isinstance(t, dict):
            errs.append(f"tool {name}: not an object")
            continue
        commit = t.get("commit")
        if not isinstance(commit, str) or (commit and not _SHA40.fullmatch(commit)):
            errs.append(f"tool {name}: commit must be '' or 40 hex")
        sha = t.get("binary_sha256")
        if not isinstance(sha, str) or sha and not _SHA64.fullmatch(sha):
            errs.append(f"tool {name}: binary_sha256 must be '' or 64 hex")
    return errs


def check_record(rec: object) -> list[str]:
    """Every way `rec` fails the spec (section 6); empty when it is valid."""
    if not isinstance(rec, dict):
        return ["record is not a JSON object"]
    if rec.get("record_version") != RECORD_VERSION:
        return [f"record_version {rec.get('record_version')!r} is not {RECORD_VERSION}"]
    errs = _type_errors(rec, _REQUIRED, "record")
    if errs:
        return errs
    if rec.get("kind") not in KINDS:
        errs.append(f"kind {rec.get('kind')!r} not in {KINDS}")
    if rec["family"] not in FAMILIES:
        errs.append(f"family {rec['family']!r} not in {FAMILIES}")
    if not _HOST.fullmatch(rec["host"]):
        errs.append("host must be host-<n>")
    errs += _time_errors(rec, "record")
    if not _UTC.fullmatch(rec["started_utc"]):
        errs.append("started_utc must be YYYY-MM-DDTHH:MM:SSZ")
    if not rec["steps"]:
        errs.append("steps: empty")
    for i, st in enumerate(rec["steps"]):
        if not isinstance(st, dict):
            errs.append(f"steps[{i}]: not an object")
            continue
        errs += _type_errors(st, _STEP, f"steps[{i}]") + _time_errors(st, f"steps[{i}]")
        if isinstance(st.get("argv"), list) and not all(isinstance(a, str) for a in st["argv"]):
            errs.append(f"steps[{i}]: argv holds a non-string item")
    errs += _tool_errors(rec["tools"]) + _param_errors(rec["params"])
    errs += _file_errors("inputs", rec["inputs"]) + _file_errors("artifacts", rec["artifacts"])
    if "netlist" not in rec["inputs"]:
        errs.append("inputs: the 'netlist' role is required")
    for where, text in _strings(rec):
        if "/home/" in text or "/Users/" in text or _ABS.search(text):
            errs.append(f"{where}: holds an absolute path or home path (spec section 6)")
            break
    return errs


def normalise_text(rec: dict[str, Any]) -> str:
    """The step command lines, one per line, the seed value replaced by `<seed>`."""
    return "\n".join(_SEED.sub(r"\1<seed>", " ".join(st["argv"])) for st in rec["steps"])


def record_spec(rec: dict[str, Any]) -> Spec:
    spec = Spec(name=f"{rec['source']}/{rec['arm']}", text=normalise_text(rec),
                origin=f"{FILE_NAME} record_version {RECORD_VERSION}",
                text_kind="recorded-normalised")
    for key, p in sorted(rec["params"].items()):
        step, _, name = key.partition(".")
        spec.add(step, name or step, p["value"], p["conf"], p["source"])
    arch = rec["inputs"].get("arch")
    if arch:
        spec.add("arch", "arch_file_sha256", arch["sha256"], "given", f"{FILE_NAME} inputs.arch")
    return spec


def _tool_commit(rec: dict[str, Any]) -> str:
    """The commit of the placer's tool: nextpnr for an external-placer arm, else VPR, else the
    first tool by name. The other tools stay in `run.tool_commits`."""
    tools = rec["tools"]
    names = [n for n in ("nextpnr", "vpr") if n in tools]
    return str(tools[names[0] if names else sorted(tools)[0]]["commit"])


def put_record(store: Store, rec: dict[str, Any], origin: str) -> str:
    """Store one valid record; returns the run's flow_config status."""
    spec = record_spec(rec)
    h = put_config(store, spec)  # ConfigConflict: caught by the caller, the record is refused
    commit = _tool_commit(rec)
    sha = rec["inputs"]["netlist"]["sha256"]
    key = (rec["source"], rec["design"], rec["arch"], rec["seed"], rec["arm"])
    _put_run(store, key, rec["family"], h, commit, sha, origin)
    rid = run_id_of(*key, h, commit, sha)
    commits = "; ".join(f"{n}={t['commit']}{'-dirty' if t.get('clean') is not True else ''}"
                        for n, t in sorted(rec["tools"].items()))
    store.db.execute(
        "UPDATE run SET tool_commits = ?, command_line = ?, time_s = ?, peak_rss_mib = ?, "
        "host = ? WHERE run_id = ?",
        (commits, " ; ".join(" ".join(st["argv"]) for st in rec["steps"]), rec["time_s"],
         rec["peak_rss_mib"], rec["host"], rid))
    return spec.status()


def import_runrecords(store: Store, root: Path) -> ImportReport:
    """Import every `mimir-run.json` under `root`; a record that fails the spec is refused."""
    if not root.is_dir():
        raise NotADirectoryError(f"{root.name}: not a directory")
    report = ImportReport()
    if not store.db.in_transaction:
        store.db.execute("BEGIN")  # so that RELEASE of a record's savepoint does not commit
    try:
        for path in sorted(root.rglob(FILE_NAME)):
            rel = path.relative_to(root).as_posix()
            try:
                rec = json.loads(path.read_text(encoding="utf-8"))
            except ValueError as exc:
                report.refused.append((rel, [f"not JSON: {exc}"]))
                continue
            errs = check_record(rec)
            if errs:
                report.refused.append((rel, errs))
                continue
            try:
                store.db.execute("SAVEPOINT rec")
                status = put_record(store, rec, f"{FILE_NAME}:{rel}")
                store.db.execute("RELEASE rec")
            except ConfigConflict as exc:
                store.db.execute("ROLLBACK TO rec")
                store.db.execute("RELEASE rec")
                report.refused.append((rel, [f"config: {exc}"]))
                continue
            report.imported.append((rec["arm"], rec["design"], status))
        store.db.commit()
    except BaseException:
        store.db.rollback()
        raise
    return report


def _where(source: str) -> tuple[str, tuple[str, ...]]:
    """The run filter for `source`: exactly that source, or every run when it is empty."""
    return ("u.source = ?", (source,)) if source else ("1 = 1", ())


def coverage(store: Store, source: str = "") -> list[tuple[str, str, int]]:
    """(arm, status, runs) of the imported runs of `source` (all runs when empty)."""
    cond, args = _where(source)
    rows = store.db.execute(
        "SELECT u.arm, c.status, COUNT(*) FROM run u JOIN flow_config c "
        f"ON c.config_hash = u.config_hash WHERE {cond} GROUP BY 1, 2 ORDER BY 1, 2",
        args).fetchall()
    return [(a, b, int(n)) for a, b, n in rows]


def non_given(store: Store, source: str = "") -> list[tuple[str, str, str, str]]:
    """(arm, step.key, conf, source) of every non-given parameter of the imported runs."""
    cond, args = _where(source)
    rows = store.db.execute(
        "SELECT DISTINCT u.arm, p.step || '.' || p.key, p.conf, p.source FROM run u "
        f"JOIN flow_param p ON p.config_hash = u.config_hash WHERE {cond} "
        "AND p.conf != 'given' ORDER BY 1, 2", args).fetchall()
    return [(a, b, c, d) for a, b, c, d in rows]


def conf_counts(store: Store, source: str = "") -> Counter[str]:
    cond, args = _where(source)
    rows = store.db.execute(
        "SELECT p.conf, COUNT(DISTINCT u.config_hash || char(31) || p.step || char(31) || p.key) "
        f"FROM run u JOIN flow_param p ON p.config_hash = u.config_hash WHERE {cond} GROUP BY 1",
        args).fetchall()
    return Counter({c: int(n) for c, n in rows})
