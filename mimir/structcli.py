"""Command line of lane 3: `python -m mimir.structcli import-flow|detect|report|export`.

Paths of the Odin III checkout, the Loki checkout and the Loki Python come from options or the
environment (`MIMIR_ODIN3_TREE`, `MIMIR_LOKI_SRC`, `MIMIR_LOKI_PYTHON`, `VTR_ROOT`), never from a
committed absolute path. Spec: docs/specs/2026-10-27-mimir-structures.md.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from mimir import blobs
from mimir.blif import parse_models
from mimir.flowcfg import put_config, run_id_of
from mimir.flowspec import Spec
from mimir.scrub import Scrubber
from mimir.store import Store
from mimir.structdb import SOURCE, DesignInfo, import_flow_dir, put_structures
from mimir.structdet import WALL_LIMIT_S, compare, loki_argv, read_structs, run_loki
from mimir.structmap import Deps, atoms_from_blif, load_deps, set_rows

DETECT_SOURCE = "mimir-detect"
TABLES = {"structure": "1, 2", "structure_mapping": "1, 2, 3, 4", "structure_member": "1, 2, 3"}


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


def _cmd_import(args: argparse.Namespace) -> int:
    store = Store(args.db)
    info = DesignInfo(args.slug, args.name, args.suite, tuple(Path(f) for f in args.file))
    blob_root = Path(args.blobs) if args.blobs else blobs.default_dir()
    rid = import_flow_dir(store, blob_root, Path(args.flow_dir), info, _deps(args),
                          make_scrub(args), args.config_name)
    print(f"run {rid}")
    store.close()
    return 0


def _git(root: Path, *a: str) -> str:
    res = subprocess.run(["git", "-C", str(root), *a], capture_output=True, text=True,
                         check=False)
    return res.stdout.strip()


def detect_spec(argv: Sequence[str], loki_src: Path, tree: Path) -> Spec:
    """The detector configuration: the Loki command with paths replaced by placeholders."""
    opts = list(argv[3:])
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
    for key in ("--floor", "--detectors", "--seed", "--timeout", "--time-budget", "--max-rounds",
                "--calib"):
        spec.add("detect", key.lstrip("-"), pairs[key], "given", "command line of the run")
    spec.add("detect", "wall_limit_s", str(WALL_LIMIT_S), "given", "mimir.structdet.WALL_LIMIT_S")
    spec.add("detect", "loki_commit", _git(loki_src, "rev-parse", "HEAD"), "given",
             "git rev-parse HEAD of the Loki checkout")
    spec.add("detect", "odin3_commit", _git(tree, "rev-parse", "HEAD"), "given",
             "git rev-parse HEAD of the Odin III tree")
    return spec


def detect_one(store: Store, deps: Deps, blob_root: Path, args: argparse.Namespace,
               scrub: Scrubber) -> str:
    """Run the detectors on one LUT netlist and store the structures. With --flow-dir the netlist
    is that run's BLIF and the mapping uses its map; without, the netlist is --blif (LUT level)."""
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
    argv = loki_argv(Path(args.loki_python), stage / "netlist.blif", out / "re", tree)
    run = run_loki(argv, out / "re", tree, loki_src, tree / "build" / "release")
    if run.returncode not in (0, 1):
        raise ValueError(f"loki re exit {run.returncode} on {args.name} after {run.time_s} s")
    sha = hashlib.sha256(blif.read_bytes()).hexdigest()
    spec = detect_spec(argv, loki_src, tree)
    cfg = put_config(store, spec)
    commit = _git(loki_src, "rev-parse", "HEAD")
    arch = "k6_frac_N10_frac_chain_mem32K_40nm.xml"
    rid = run_id_of(DETECT_SOURCE, args.name, arch, 1, "", cfg, commit, sha)
    cmd = scrub.text(" ".join(argv))
    store.db.execute(
        "INSERT OR REPLACE INTO run (run_id, slug, config_hash, source, design, arch, seed, arm, "
        "family, tool_commits, command_line, time_s, peak_rss_mib, host, origin, tool_commit, "
        "input_sha256) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (rid, args.slug, cfg, DETECT_SOURCE, args.name, arch, 1, "", "",
         f"loki={commit};odin3={_git(tree, 'rev-parse', 'HEAD')}", cmd, run.time_s,
         run.peak_rss_mib, os.uname().nodename, "loki re on the run's BLIF", commit, sha))
    structs, members = read_structs(out / "re" / "overlay.json", atoms, rid[:8])
    rows = set_rows(members, atoms, nm)
    flow_rid = _flow_run(store, args.slug) or rid
    flow_cfg = str(store.db.execute("SELECT config_hash FROM run WHERE run_id=?",
                                    (flow_rid,)).fetchone()[0])
    store.db.execute("DELETE FROM structure WHERE design=? AND label_source LIKE 'detector:%'",
                     (args.slug,))
    store.db.execute("DELETE FROM structure_member WHERE design=? AND structure_id LIKE 'det:%'",
                     (args.slug,))
    store.db.execute("DELETE FROM structure_mapping WHERE design=? AND structure_id LIKE 'det:%'",
                     (args.slug,))
    put_structures(store, args.slug, rid, cfg, structs, [], members)
    put_structures(store, args.slug, flow_rid, flow_cfg, [], rows, {})
    store.db.commit()
    return rid


def _flow_run(store: Store, slug: str) -> str:
    row = store.db.execute("SELECT run_id FROM run WHERE slug=? AND source=?",
                           (slug, SOURCE)).fetchone()
    return str(row[0]) if row else ""


def _cmd_detect(args: argparse.Namespace) -> int:
    store = Store(args.db)
    blob_root = Path(args.blobs) if args.blobs else blobs.default_dir()
    print(f"detect run {detect_one(store, _deps(args), blob_root, args, make_scrub(args))}")
    store.close()
    return 0


def _cmd_detect_mcnc(args: argparse.Namespace) -> int:
    """Detector structures for the 20 MCNC circuits (no HDL: detector rows, lut level only)."""
    from mimir.sets import mcnc_jobs

    store, deps, scrub = Store(args.db), _deps(args), make_scrub(args)
    blob_root = Path(args.blobs) if args.blobs else blobs.default_dir()
    for job in mcnc_jobs(_env(None, "VTR_ROOT")):
        slug = f"mcnc20/{job.design}"
        if store.db.execute("SELECT 1 FROM run WHERE slug=? AND source=?",
                            (slug, DETECT_SOURCE)).fetchone():
            print(f"{slug}: already detected", flush=True)
            continue
        sha = hashlib.sha256(job.path.read_bytes()).hexdigest()
        store.db.execute("INSERT OR REPLACE INTO design VALUES (?,?,?,?,?,?)",
                         (slug, sha, "blif", "mcnc20", job.design, job.origin))
        store.db.commit()
        one = argparse.Namespace(**{**vars(args), "slug": slug, "name": job.design,
                                    "blif": str(job.path), "flow_dir": None})
        try:
            print(f"{slug}: detect run {detect_one(store, deps, blob_root, one, scrub)}",
                  flush=True)
        except (ValueError, OSError, KeyError) as exc:
            print(f"{slug}: failed: {exc}", flush=True)
    store.close()
    return 0


REPORT_SQL = {
    "structures by kind x source": (
        "SELECT kind, CASE WHEN label_source='hdl' THEN 'hdl' ELSE 'detector' END AS src, "
        "COUNT(*) FROM structure GROUP BY 1, 2 ORDER BY 1, 2"),
    "mappings by level": (
        "SELECT level, COUNT(*), SUM(n_pure > 0), SUM(lost_at_pass != ''), SUM(joined_with != '') "
        "FROM structure_mapping GROUP BY level ORDER BY CASE level WHEN 'gate' THEN 1 "
        "WHEN 'lut' THEN 2 WHEN 'ble' THEN 3 WHEN 'clb' THEN 4 ELSE 5 END"),
    "lost at pass (hdl structures, lut level)": (
        "SELECT lost_at_pass, COUNT(*) FROM structure_mapping m JOIN structure s "
        "ON s.design=m.design AND s.structure_id=m.structure_id WHERE m.level='lut' "
        "AND s.label_source='hdl' GROUP BY 1 ORDER BY 1"),
}


def _members(store: Store, label: str) -> dict[str, dict[str, tuple[str, set[str]]]]:
    out: dict[str, dict[str, tuple[str, set[str]]]] = {}
    where = "label_source = 'hdl'" if label == "hdl" else "label_source LIKE 'detector:%'"
    for slug, sid, kind in store.db.execute(
            f"SELECT design, structure_id, kind FROM structure WHERE {where}"):
        out.setdefault(slug, {})[sid] = (kind, set())
    for slug, sid, atom in store.db.execute("SELECT design, structure_id, atom "
                                            "FROM structure_member"):
        if slug in out and sid in out[slug]:
            out[slug][sid][1].add(atom)
    return out


def detector_scores(store: Store, prefix: str = "") -> list[tuple[str, int, int, int, int]]:
    """(kind, detected, correct, hdl, found) summed over designs whose slug starts with prefix."""
    hdl, det = _members(store, "hdl"), _members(store, "det")
    tot: dict[str, list[int]] = {}
    for slug in sorted(set(hdl) & set(det)):
        if not slug.startswith(prefix):
            continue
        for s in compare(hdl[slug], det[slug]):
            t = tot.setdefault(s.kind, [0, 0, 0, 0])
            t[0] += s.detected
            t[1] += s.correct
            t[2] += s.hdl
            t[3] += s.found
    return [(k, v[0], v[1], v[2], v[3]) for k, v in sorted(tot.items())]


def _cmd_report(args: argparse.Namespace) -> int:
    store = Store(args.db, readonly=True)
    for title, sql in REPORT_SQL.items():
        print(f"## {title}")
        for row in store.db.execute(sql):
            print("\t".join(str(x) for x in row))
    print("## detector precision and recall per kind (designs with both)")
    print("kind\tdetected\tcorrect\tprecision\thdl\tfound\trecall")
    for k, d, c, h, f in detector_scores(store, args.prefix):
        p = f"{c / d:.3f}" if d else "-"
        r = f"{f / h:.3f}" if h else "-"
        print(f"{k}\t{d}\t{c}\t{p}\t{h}\t{f}\t{r}")
    if args.l15:
        from mimir.structl15 import compare as l15_compare

        print("## L15 cross-check (units, stmt level): design, mimir units, mimir separable, "
              "loki units, loki separable")
        rows = l15_compare(store, Path(args.l15))
        for row in rows:
            print("\t".join(str(x) for x in row))
        tot = (sum(w[1] for w in rows), sum(w[2] for w in rows), sum(w[3] for w in rows),
               sum(w[4] for w in rows))
        print("total\t" + "\t".join(str(x) for x in tot))
    return 0


def export_tables(store: Store, out: Path) -> dict[str, int]:
    """One CSV per new table, rows in primary-key order, `\\n` line ends, floats by repr."""
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
                w.writerow(["" if x is None else repr(x) if isinstance(x, float) else x
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
    s.set_defaults(fn=_cmd_detect)
    s = sub.add_parser("detect-mcnc", help="run the detectors on the 20 MCNC circuits")
    common(s)
    s.add_argument("--work", required=True)
    s.add_argument("--loki-python", default=os.environ.get("MIMIR_LOKI_PYTHON", "python3"))
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
