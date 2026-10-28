"""Command line of lane 3: `python -m mimir.structcli import-flow|detect|report|export`.

Paths of the Odin III checkout, the Loki checkout and the Loki Python come from options or the
environment (`MIMIR_ODIN3_TREE`, `MIMIR_LOKI_SRC`, `MIMIR_LOKI_PYTHON`, `VTR_ROOT`), never from a
committed absolute path. Spec: docs/specs/2026-10-27-mimir-structures.md.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from mimir import blobs
from mimir.blif import parse_models
from mimir.blobs import put_bytes
from mimir.flowcfg import put_config, run_id_of
from mimir.flowspec import Spec
from mimir.scrub import Scrubber
from mimir.store import Store
from mimir.structdb import (
    SOURCE,
    DesignInfo,
    clear_structures,
    commit_or_unknown,
    import_flow_dir,
    put_structures,
    vpr_facts,
)
from mimir.structdet import (
    WALL_LIMIT_S,
    DetectRun,
    compare,
    confusion,
    loki_argv,
    read_structs,
    run_loki,
    scoring_set,
)
from mimir.structmap import Deps, atoms_from_blif, load_deps, set_rows

DETECT_SOURCE = "mimir-detect"
TABLES = {"structure": "1, 2", "structure_mapping": "1, 2, 3, 4",
          "structure_member": "1, 2, 3, 4"}


def _env(arg: str | None, var: str) -> Path:
    value = arg or os.environ.get(var)
    if not value:
        raise SystemExit(f"error: give the path or set ${var}")
    return Path(value)


def make_scrub(args: argparse.Namespace) -> Scrubber:
    tree = _env(args.odin3_tree, "MIMIR_ODIN3_TREE")
    return Scrubber({
        "$VTR_ROOT": Path(os.environ["VTR_ROOT"]) if os.environ.get("VTR_ROOT") else None,
        "$ODIN3_BUILD": tree,
        "$ODIN3": Path(os.environ["MIMIR_ODIN3"]) if os.environ.get("MIMIR_ODIN3") else None,
        "$LOKI": _env(args.loki_src, "MIMIR_LOKI_SRC"),
        "$WS": Path.home() / "odin3-ws", "$OUT": Path(args.flow_dir) if args.flow_dir else None,
    })


def _deps(args: argparse.Namespace) -> Deps:
    return load_deps(_env(args.odin3_tree, "MIMIR_ODIN3_TREE"), _env(args.loki_src,
                                                                    "MIMIR_LOKI_SRC"))


def _vtr_root() -> Path:
    value = os.environ.get("VTR_ROOT")
    if not value:
        raise SystemExit("error: set $VTR_ROOT (read only; the VTR commit comes from it)")
    return Path(value)


def _cmd_import(args: argparse.Namespace) -> int:
    store = Store(args.db)
    info = DesignInfo(args.slug, args.name, args.suite, tuple(Path(f) for f in args.file))
    blob_root = Path(args.blobs) if args.blobs else blobs.default_dir()
    rid = import_flow_dir(store, blob_root, Path(args.flow_dir), info, _deps(args),
                          make_scrub(args), args.config_name, _vtr_root())
    print(f"run {rid}")
    store.close()
    return 0


def _git(root: Path, *a: str) -> str:
    res = subprocess.run(["git", "-C", str(root), *a], capture_output=True, text=True,
                         check=False)
    return res.stdout.strip()


def detect_spec(argv: Sequence[str], loki_src: Path, tree: Path,
                wall_limit: float = WALL_LIMIT_S) -> Spec:
    """The detector configuration: the Loki command with paths replaced by placeholders."""
    opts = list(argv[4:])
    skip = {"--odin3-root", "--out"}
    norm = [("<" + o.lstrip("-") + ">" if o in skip else o) for o in opts]
    for i in range(1, len(opts)):
        if opts[i - 1] in skip:
            norm[i] = ""
    text = "loki re <netlist> " + " ".join(x for x in norm if x)
    spec = Spec(name="loki-detect/round5", text=text, origin="mimir.structdet.loki_argv",
                text_kind="recorded-normalised")
    pairs = {o: opts[i + 1] for i, o in enumerate(opts[:-1]) if o.startswith("--")
             and not opts[i + 1].startswith("--")}
    for key in ("--floor", "--detectors", "--seed", "--timeout",
                "--time-budget", "--max-rounds", "--calib"):
        spec.add("detect", key.lstrip("-"), pairs[key], "given", "command line of the run")
    spec.add("detect", "wall_limit_s", str(wall_limit), "given", "mimir.structdet.run_loki")
    for key, root, what in (("loki_commit", loki_src, "the Loki checkout"),
                            ("odin3_commit", tree, "the Odin III tree")):
        sha = commit_or_unknown(_git(root, "rev-parse", "HEAD"))
        spec.add("detect", key, sha if sha != "unknown" else "", "given" if sha != "unknown"
                 else "unknown", f"git rev-parse HEAD of {what}")
    return spec


def _final_equiv(out: Path) -> str:
    try:
        rep = json.loads((out / "report.json").read_text(encoding="utf-8"))
        return str(rep["final_equiv"]["status"])
    except (OSError, ValueError, KeyError):
        return "unknown"


def detect_status(run: DetectRun, out: Path) -> str:
    """`ok` (exit 0), `differs` (exit 1 with an overlay and `final_equiv` = differs: the netlist
    Loki rebuilt is not equivalent, the hypotheses are still valid), `timeout`, or `failed`."""
    if run.timed_out:
        return "timeout"
    if run.returncode == 0 and (out / "overlay.json").is_file():
        return "ok"
    if run.returncode == 1 and (out / "overlay.json").is_file() and _final_equiv(out) == "differs":
        return "differs"
    return "failed"


def detect_one(store: Store, deps: Deps, blob_root: Path, args: argparse.Namespace,
               scrub: Scrubber) -> str:
    """Run the detectors on one LUT netlist and store the structures. With --flow-dir the netlist
    is that run's BLIF and the mapping uses its map; without, the netlist is --blif (LUT level).
    One transaction: any failure after the run rolls the store back. A run that fails or times out
    is recorded as a run (status in `origin`) and stores no structure."""
    try:
        return _detect_one(store, deps, blob_root, args, scrub)
    except BaseException:
        store.db.rollback()
        raise


def _detect_one(store: Store, deps: Deps, blob_root: Path, args: argparse.Namespace,
                scrub: Scrubber) -> str:
    tree, loki_src = _env(args.odin3_tree, "MIMIR_ODIN3_TREE"), _env(args.loki_src,
                                                                    "MIMIR_LOKI_SRC")
    flow = Path(args.flow_dir) if args.flow_dir else None
    blif = next(flow.glob("odin3/*.blif")) if flow else Path(args.blif)
    nm = deps.nmv2.read_name_map(next(flow.glob("odin3/*.blif.names"))) if flow else None
    models = parse_models(blif.read_text(encoding="utf-8"))
    atoms = atoms_from_blif(models, (lambda n: nm.atom(n) is not None) if nm else (lambda n: True))
    out = Path(args.work) / args.name
    out.mkdir(parents=True, exist_ok=True)
    stage = out / "f1-k6"
    stage.mkdir(exist_ok=True)
    (stage / "netlist.blif").write_bytes(blif.read_bytes())
    limit = float(getattr(args, "wall_limit", WALL_LIMIT_S))
    argv = loki_argv(Path(args.loki_python), stage / "netlist.blif", out / "re", tree)
    run = run_loki(argv, out / "re", tree, loki_src, tree / "build" / "release", limit)
    status = detect_status(run, out / "re")
    sha = hashlib.sha256(blif.read_bytes()).hexdigest()
    spec = detect_spec(argv, loki_src, tree, limit)
    cfg = put_config(store, spec)
    commit = commit_or_unknown(_git(loki_src, "rev-parse", "HEAD"))
    arch = vpr_facts(flow, json.loads((flow / "mimir-run.json").read_text(encoding="utf-8")))[0] \
        if flow else ""
    rid = run_id_of(DETECT_SOURCE, args.name, arch, 1, "", cfg, commit, sha)
    where = "the run's BLIF" if flow else "the BLIF as distributed (no flow, no architecture)"
    note = getattr(args, "lock_note", "")
    origin = (f"status={status}; exit={run.returncode}; final_equiv={_final_equiv(out / 're')}; "
              f"loki re on {where}" + (f"; {note}" if note else ""))
    store.db.execute(
        "INSERT OR REPLACE INTO run (run_id, slug, config_hash, source, design, arch, seed, arm, "
        "family, tool_commits, command_line, time_s, peak_rss_mib, host, origin, tool_commit, "
        "input_sha256) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (rid, args.slug, cfg, DETECT_SOURCE, args.name, arch, 1, "", "",
         f"loki={commit};odin3={commit_or_unknown(_git(tree, 'rev-parse', 'HEAD'))}",
         scrub.text(" ".join(argv)), run.time_s, run.peak_rss_mib, os.uname().nodename, origin,
         commit, sha))
    log = scrub.text(f"exit {run.returncode}, status {status}, {run.time_s} s\n"
                     + (f"{note}\n" if note else "")
                     + f"final_equiv {_final_equiv(out / 're')}\n"
                     f"--- stderr tail\n{run.stderr_tail}")
    store.db.execute("DELETE FROM run_artifact WHERE run_id = ? AND kind = 'detect_log'", (rid,))
    store.db.execute("INSERT INTO run_artifact VALUES (?, 'detect_log', ?)",
                     (rid, put_bytes(blob_root, log.encode())))
    clear_structures(store, args.slug, detector=True)
    if status in ("ok", "differs"):
        structs, members = read_structs(out / "re" / "overlay.json", atoms, rid[:8])
        flow_rid = _flow_run(store, args.slug, getattr(args, "flow_run", "")) if flow else rid
        flow_cfg = str(store.db.execute("SELECT config_hash FROM run WHERE run_id=?",
                                        (flow_rid,)).fetchone()[0]) if flow else cfg
        put_structures(store, args.slug, rid, cfg, structs, [], members)
        put_structures(store, args.slug, flow_rid, flow_cfg, [], set_rows(members, atoms, nm), {})
    store.db.commit()
    return rid


def _flow_run(store: Store, slug: str, pick: str = "") -> str:
    """The flow run of a design: `pick` when given, else the one with the smallest run id
    (deterministic; a re-import with another config leaves an older run behind)."""
    row = store.db.execute(
        "SELECT run_id FROM run WHERE slug=? AND source=? AND (?='' OR run_id=?) "
        "ORDER BY run_id LIMIT 1", (slug, SOURCE, pick, pick)).fetchone()
    if row is None:
        raise ValueError(f"{slug}: no flow run in the store to attach the detector rows to")
    return str(row[0])


def _cmd_detect(args: argparse.Namespace) -> int:
    store = Store(args.db)
    blob_root = Path(args.blobs) if args.blobs else blobs.default_dir()
    print(f"detect run {detect_one(store, _deps(args), blob_root, args, make_scrub(args))}")
    store.close()
    return 0


def _cmd_detect_mcnc(args: argparse.Namespace) -> int:
    """Detector structures for the 20 MCNC circuits (no HDL: detector rows, lut level only). Each
    circuit is one `tools/heavy-run` call of `structcli detect`; a circuit with a finished run
    (ok or differs) is skipped, a failed or timed out one is run again."""
    from mimir.sets import mcnc_jobs

    store = Store(args.db)
    only = set(args.only.split(",")) if args.only else None
    for job in mcnc_jobs(_vtr_root()):
        slug = f"mcnc20/{job.design}"
        if only is not None and job.design not in only:
            continue
        if store.db.execute("SELECT 1 FROM run WHERE slug=? AND source=? AND (origin LIKE "
                            "'status=ok;%' OR origin LIKE 'status=differs;%')",
                            (slug, DETECT_SOURCE)).fetchone():
            print(f"{slug}: already detected", flush=True)
            continue
        sha = hashlib.sha256(job.path.read_bytes()).hexdigest()
        store.db.execute("INSERT OR REPLACE INTO design VALUES (?,?,?,?,?,?)",
                         (slug, sha, "blif", "mcnc20", job.design, job.origin))
        store.db.commit()
        wrap = args.heavy_run or ["nice", "-n", "10"]
        cmd = [*wrap, sys.executable, "-m", "mimir.structcli", "detect", args.db,
               "--slug", slug, "--name", job.design, "--blif", str(job.path),
               "--work", args.work, "--wall-limit", str(args.wall_limit),
               "--loki-python", args.loki_python]
        if not args.heavy_run:
            cmd += ["--lock-note", NO_LOCK_NOTE]
        for opt, val in (("--odin3-tree", args.odin3_tree), ("--loki-src", args.loki_src),
                         ("--blobs", args.blobs)):
            if val:
                cmd += [opt, val]
        code = subprocess.run(cmd, check=False).returncode
        print(f"{slug}: {'done' if code == 0 else f'exit {code}'}", flush=True)
    store.close()
    return 0


REPORT_SQL = {
    "structures by kind x granularity x source": (
        "SELECT kind, granularity, CASE WHEN label_source='hdl' THEN 'hdl' ELSE 'detector' END "
        "AS src, COUNT(*) FROM structure GROUP BY 1, 2, 3 ORDER BY 1, 2, 3"),
    "flow runs by flow_config status": (
        "SELECT c.status, COUNT(*) FROM run r JOIN flow_config c ON c.config_hash = r.config_hash "
        "WHERE r.source = 'mimir-structures' GROUP BY 1 ORDER BY 1"),
    "detector runs by status": (
        "SELECT substr(origin, 8, instr(origin, ';') - 8), COUNT(*) FROM run "
        "WHERE source = 'mimir-detect' GROUP BY 1 ORDER BY 1"),
    "structure_mapping rows with crit_share": (
        "SELECT COUNT(*), COUNT(crit_share) FROM structure_mapping"),
    "structures by kind x source": (
        "SELECT kind, CASE WHEN label_source='hdl' THEN 'hdl' ELSE 'detector' END AS src, "
        "COUNT(*) FROM structure GROUP BY 1, 2 ORDER BY 1, 2"),
    "designs with a structure of the kind, by source": (
        "SELECT kind, CASE WHEN label_source='hdl' THEN 'hdl' ELSE 'detector' END AS src, "
        "COUNT(DISTINCT design) FROM structure GROUP BY 1, 2 ORDER BY 1, 2"),
    "structures with a mapping at the level, by suite and source": (
        "SELECT substr(m.design, 1, instr(m.design, '/') - 1) AS suite, "
        "CASE WHEN s.label_source='hdl' THEN 'hdl' ELSE 'detector' END AS src, m.level, "
        "COUNT(*) FROM structure_mapping m JOIN structure s ON s.design = m.design "
        "AND s.structure_id = m.structure_id GROUP BY 1, 2, 3 ORDER BY 1, 2, "
        "CASE m.level WHEN 'gate' THEN 1 WHEN 'lut' THEN 2 WHEN 'ble' THEN 3 WHEN 'clb' THEN 4 "
        "ELSE 5 END"),
    "mappings by level": (
        "SELECT level, COUNT(*), SUM(n_pure > 0), SUM(lost_at_pass != ''), SUM(joined_with != '') "
        "FROM structure_mapping GROUP BY level ORDER BY CASE level WHEN 'gate' THEN 1 "
        "WHEN 'lut' THEN 2 WHEN 'ble' THEN 3 WHEN 'clb' THEN 4 ELSE 5 END"),
    "hdl structures by level: mapped, with no pure object (joined away)": (
        "SELECT m.level, COUNT(*), SUM(m.n_pure = 0) FROM structure_mapping m JOIN structure s "
        "ON s.design = m.design AND s.structure_id = m.structure_id WHERE s.label_source='hdl' "
        "GROUP BY 1 ORDER BY CASE m.level WHEN 'gate' THEN 1 WHEN 'lut' THEN 2 WHEN 'ble' THEN 3 "
        "WHEN 'clb' THEN 4 ELSE 5 END"),
    "hdl structures lost (no pure object) by level and pass": (
        "SELECT m.level, m.lost_at_pass, COUNT(*) FROM structure_mapping m JOIN structure s "
        "ON s.design = m.design AND s.structure_id = m.structure_id WHERE s.label_source='hdl' "
        "AND m.level IN ('gate', 'lut') AND m.lost_at_pass != '' GROUP BY 1, 2 ORDER BY 1, 2"),
    "lost at pass (hdl structures, lut level)": (
        "SELECT lost_at_pass, COUNT(*) FROM structure_mapping m JOIN structure s "
        "ON s.design=m.design AND s.structure_id=m.structure_id WHERE m.level='lut' "
        "AND s.label_source='hdl' GROUP BY 1 ORDER BY 1"),
}


def _members(store: Store, label: str) -> dict[str, dict[str, tuple[str, set[str], str, str]]]:
    """design -> structure id -> (kind, atoms, granularity, parent id) for the HDL structures
    (`hdl`) or the detector structures (anything else)."""
    out: dict[str, dict[str, tuple[str, set[str], str, str]]] = {}
    where = "label_source = 'hdl'" if label == "hdl" else "label_source LIKE 'detector:%'"
    for slug, sid, kind, gran, parent in store.db.execute(
            f"SELECT design, structure_id, kind, granularity, parent_id FROM structure "
            f"WHERE {where}"):
        out.setdefault(slug, {})[sid] = (kind, set(), gran, parent)
    for slug, sid, atom in store.db.execute("SELECT design, structure_id, atom "
                                            "FROM structure_member"):
        if slug in out and sid in out[slug]:
            out[slug][sid][1].add(atom)
    return out


def _paired(store: Store, prefix: str) -> list[tuple[dict[str, tuple[str, set[str], str]],
                                                  dict[str, tuple[str, set[str]]]]]:
    """For each design (slug starting with `prefix`) that has HDL and detector structures: the
    HDL scoring set and the detector structures as (kind, atoms)."""
    hdl, det = _members(store, "hdl"), _members(store, "det")
    out = []
    for slug in sorted(set(hdl) & set(det)):
        if slug.startswith(prefix):
            out.append((scoring_set(hdl[slug]), {k: (v[0], v[1]) for k, v in det[slug].items()}))
    return out


def detector_scores(store: Store, prefix: str = ""
                    ) -> list[tuple[str, int, int, int, int, int, int]]:
    """(kind, detected, correct, hdl, found, hdl operator-level, hdl block-level) summed over the
    designs whose slug starts with prefix, scored against operator-level HDL structures where
    they exist and block-level ones otherwise (`structdet.scoring_set`)."""
    tot: dict[str, list[int]] = {}
    for hdl, det in _paired(store, prefix):
        for s in compare(hdl, det):
            t = tot.setdefault(s.kind, [0] * 6)
            for i, v in enumerate((s.detected, s.correct, s.hdl, s.found, s.hdl_operator,
                                   s.hdl_block)):
                t[i] += v
    return [(k, v[0], v[1], v[2], v[3], v[4], v[5]) for k, v in sorted(tot.items())]


def confusion_matrix(store: Store, prefix: str = "") -> dict[tuple[str, str], int]:
    """(HDL kind, detector kind) -> pairs, summed over designs (`structdet.confusion`)."""
    tot: dict[tuple[str, str], int] = {}
    for hdl, det in _paired(store, prefix):
        for key, n in confusion(hdl, det).items():
            tot[key] = tot.get(key, 0) + n
    return tot


def _print_matrix(matrix: dict[tuple[str, str], int]) -> None:
    hkinds = sorted({h for h, _ in matrix})
    dkinds = sorted({d for _, d in matrix})
    print("hdl kind \\ detector kind\t" + "\t".join(dkinds))
    for h in hkinds:
        print(h + "\t" + "\t".join(str(matrix.get((h, d), 0)) for d in dkinds))


def _cmd_report(args: argparse.Namespace) -> int:
    store = Store(args.db, readonly=True)
    for title, sql in REPORT_SQL.items():
        print(f"## {title}")
        for row in store.db.execute(sql):
            print("\t".join("NULL" if x is None else str(x) for x in row))
    print("## confusion matrix: hdl kind x detector kind, pairs by atom overlap "
          "(none = no match)")
    _print_matrix(confusion_matrix(store, args.prefix))
    print("## detector precision and recall per kind (designs with both); recall against "
          "operator-level hdl structures where they exist, block-level otherwise")
    print("kind\tdetected\tcorrect\tprecision\thdl\thdl_operator\thdl_block\tfound\trecall")
    for k, d, c, h, f, ho, hb in detector_scores(store, args.prefix):
        p = f"{c / d:.3f}" if d else "-"
        r = f"{f / h:.3f}" if h else "-"
        print(f"{k}\t{d}\t{c}\t{p}\t{h}\t{ho}\t{hb}\t{f}\t{r}")
    if args.l15:
        from mimir.structl15 import compare as l15_compare

        print("## L15 cross-check (units, stmt level): design, mimir units, mimir separable, "
              "loki units, loki separable at the final snapshot (lower bound), (upper bound)")
        rows = l15_compare(store, Path(args.l15))
        for row in rows:
            print("\t".join(str(x) for x in row))
        print("total\t" + "\t".join(str(sum(int(w[i]) for w in rows)) for i in range(1, 6)))
    return 0


NO_LOCK_NOTE = ("no heavy lock held, run at nice 10: controller ruling 2026-10-27, an MCNC detect "
                "is one core and about 200 MB, and holding the lock for up to 30 min blocked "
                "other lanes' builds")
NULL_MARK = "\\N"


def export_tables(store: Store, out: Path) -> dict[str, int]:
    """One CSV per new table, rows in primary-key order, `\\n` line ends, floats by repr. A NULL is
    written as `\\N`, so it differs from an empty text."""
    out.mkdir(parents=True, exist_ok=True)
    counts = {}
    for table, order in TABLES.items():
        cur = store.db.execute(f"SELECT * FROM {table} ORDER BY {order}")
        cols = [d[0] for d in cur.description]
        with open(out / f"{table}.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(cols)
            n = 0
            for row in cur:
                w.writerow([NULL_MARK if x is None else repr(x) if isinstance(x, float) else x
                            for x in row])
                n += 1
        counts[table] = n
    return counts


def _cmd_export(args: argparse.Namespace) -> int:
    store = Store(args.db, readonly=True)
    for table, n in export_tables(store, Path(args.out)).items():
        print(f"{table}: {n} rows")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="mimir.structcli")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(s: argparse.ArgumentParser) -> None:
        s.add_argument("db")
        s.add_argument("--odin3-tree", help="Odin III checkout with tools/flow (MIMIR_ODIN3_TREE)")
        s.add_argument("--loki-src", help="Loki checkout (MIMIR_LOKI_SRC)")
        s.add_argument("--blobs")
        s.add_argument("--flow-dir")

    s = sub.add_parser("import-flow", help="import one odin3-flow output dir")
    common(s)
    s.add_argument("--slug", required=True)
    s.add_argument("--name", required=True)
    s.add_argument("--suite", required=True)
    s.add_argument("--file", action="append", required=True)
    s.add_argument("--config-name", default="structures/odin3-flow-prov")
    s.set_defaults(fn=_cmd_import)
    s = sub.add_parser("detect", help="run Loki detectors on a run's BLIF (or --blif)")
    common(s)
    s.add_argument("--slug", required=True)
    s.add_argument("--name", required=True)
    s.add_argument("--blif")
    s.add_argument("--work", required=True)
    s.add_argument("--loki-python", default=os.environ.get("MIMIR_LOKI_PYTHON", "python3"))
    s.add_argument("--wall-limit", type=float, default=WALL_LIMIT_S, help="hard stop in seconds")
    s.add_argument("--flow-run", default="", help="run id of the flow run to attach to")
    s.add_argument("--lock-note", default="", help="text for the run record (no lock held, why)")
    s.set_defaults(fn=_cmd_detect)
    s = sub.add_parser("detect-mcnc", help="run the detectors on the 20 MCNC circuits")
    common(s)
    s.add_argument("--work", required=True)
    s.add_argument("--loki-python", default=os.environ.get("MIMIR_LOKI_PYTHON", "python3"))
    s.add_argument("--wall-limit", type=float, default=WALL_LIMIT_S, help="hard stop in seconds")
    s.add_argument("--heavy-run", nargs="*", default=[],
                   help="the heavy-run command (needs ODIN3_HEAVY_OK=1 from the caller); "
                   "without it each detect runs at nice 10 and the run record says "
                   "no lock was held")
    s.add_argument("--only", default="", help="comma separated circuit names")
    s.set_defaults(fn=_cmd_detect_mcnc)
    s = sub.add_parser("report", help="coverage tables and detector precision and recall")
    s.add_argument("db")
    s.add_argument("--prefix", default="")
    s.add_argument("--l15", help="directory with the Loki round-6 `<design>.stmt.json` files")
    s.set_defaults(fn=_cmd_report)
    s = sub.add_parser("export", help="CSV of the new tables")
    s.add_argument("db")
    s.add_argument("out")
    s.set_defaults(fn=_cmd_export)
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.fn(args))


if __name__ == "__main__":
    sys.exit(main())
