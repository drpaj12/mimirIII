"""Command line: `mimir init|import|measure-set|merge|export|coverage|check|registry|citations`."""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sqlite3
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from mimir.citations import load_citations, render_markdown
from mimir.flowcfg import (
    ARCH_REL,
    SrcRoots,
    config_coverage,
    import_runs,
    param_conf_counts,
    unknown_params,
)
from mimir.importers.common import Report
from mimir.measure import RENT_MAX_NODES, measure_job
from mimir.meta import (
    Roots,
    import_licences,
    import_mcnc_meta,
    meta_coverage,
    register_designs,
)
from mimir.registry import load_registry
from mimir.sets import SETS
from mimir.store import Store


def _root(arg: str | None, var: str) -> Path:
    value = arg or os.environ.get(var)
    if not value:
        raise SystemExit(f"error: give the path or set ${var}")
    return Path(value)


def _cmd_init(args: argparse.Namespace) -> int:
    Store(args.db).close()
    return 0


def _cmd_import(args: argparse.Namespace) -> int:
    from mimir.importers.atlas import import_atlas
    from mimir.importers.loki import import_loki
    from mimir.importers.norns import import_norns

    store = Store(args.db)
    report = Report()
    if args.what in ("norns", "all"):
        root = _root(args.norns, "MIMIR_NORNS")
        for importer in (import_norns, import_atlas):
            recs, rep = importer(root)
            store.replace_origins(recs)
            report.merge(rep)
    if args.what in ("loki", "all"):
        recs, rep = import_loki(_root(args.loki, "MIMIR_LOKI"))
        store.replace_origins(recs)
        report.merge(rep)
    print("\n".join(report.lines()))
    print(f"records in store: {store.count()}")
    if args.what == "norns" and args.runs:
        return _import_kept(store, args)
    return 0


def _import_kept(store: Store, args: argparse.Namespace) -> int:
    """`import norns --runs DIR`: run records, then their kept timing evidence."""
    import os

    from mimir import blobs
    from mimir.importers.nornskept import import_kept
    from mimir.runrecord import import_runrecords

    runs = Path(args.runs)
    rep = import_runrecords(store, runs)
    tree = args.odin3_tree or os.environ.get("MIMIR_ODIN3_TREE")
    keep = args.keep_store or os.environ.get("NORNS_KEEP_STORE")
    got = import_kept(store, runs, Path(args.blobs) if args.blobs else blobs.default_dir(),
                      Path(keep) if keep else None, Path(tree) if tree else None)
    for rel, status in got.rows:
        if status != "skipped: no kept timing":
            print(f"{rel}\t{status}")
    print(f"run records {len(rep.imported)}, refused {len(rep.refused)}; kept timing: "
          + ", ".join(f"{k} {n}" for k, n in sorted(got.count().items())))
    return 1 if rep.refused or got.count().get("error") else 0


def _cmd_import_e10(args: argparse.Namespace) -> int:
    from mimir.importers.e10 import import_e10

    store = Store(args.db)
    report = Report()
    netlists = Path(args.netlists) if args.netlists else None
    recs = list(import_e10(store, Path(args.data), args.label, netlists, report))
    store.replace_origins(recs)
    print("\n".join(report.lines()))
    print(f"records in store: {store.count()}")
    return 0


def _cmd_measure_set(args: argparse.Namespace) -> int:
    build, var = SETS[args.set]
    store = Store(args.db)
    seeds = [int(s) for s in args.seeds.split(",")]
    errors: Counter[str] = Counter()
    notes: Counter[str] = Counter()
    gnotes: Counter[str] = Counter()
    done = 0
    from mimir import blobs

    default = blobs.default_dir() if var == "MIMIR_BLOBS" else None
    root = Path(args.root or os.environ.get(var) or default or _root(None, var))
    for job in build(root):
        out = measure_job(job, seeds=seeds, rent=not args.no_rent,
                          rent_max_nodes=args.rent_max_nodes, graphlet=args.graphlet)
        if out.error:
            errors[out.error[:90]] += 1
            continue
        store.replace_measured(out.records)
        done += 1
        if out.rent_note:
            notes[out.rent_note] += 1
        if out.graphlet_note:
            gnotes[out.graphlet_note[:120]] += 1
    print(f"set {args.set}: measured {done} netlists")
    for msg, n in sorted(errors.items()):
        print(f"  skipped {n}: {msg}")
    for msg, n in sorted(notes.items()):
        print(f"  rent note {n}: {msg}")
    for msg, n in sorted(gnotes.items()):
        print(f"  graphlet skipped {n}: {msg}")
    return 0


def _roots(args: argparse.Namespace) -> Roots:
    def opt(arg: str | None, var: str) -> Path | None:
        value = arg or os.environ.get(var)
        return Path(value) if value else None

    return Roots(opt(args.vtr, "VTR_ROOT"), opt(args.norns, "MIMIR_NORNS"),
                 opt(args.loki, "MIMIR_LOKI"))


def _cmd_meta(args: argparse.Namespace) -> int:
    store = Store(args.db)
    roots = _roots(args)
    n = import_mcnc_meta(store, Path(args.toml), roots)
    m = register_designs(store, roots)
    try:
        k = import_licences(store, Path(args.licences))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"mcnc meta circuits: {n}; designs registered: {m}; licences matched: {k}; "
          "unmatched: 0")
    return 0


def _cmd_meta_coverage(args: argparse.Namespace) -> int:
    store = Store(args.db, readonly=True)
    print("field\tconf\tdesigns")
    for field, conf, n in meta_coverage(store, args.prefix):
        print(f"{field}\t{conf}\t{n}")
    return 0


def _src_roots(args: argparse.Namespace, vtr: Path | None) -> SrcRoots:
    def opt(arg: str | None, var: str) -> Path | None:
        value = arg or os.environ.get(var)
        return Path(value) if value else None

    return SrcRoots(opt(args.odin3, "MIMIR_ODIN3"), vtr, opt(args.norns_src, "MIMIR_NORNS_SRC"))


def _cmd_runs(args: argparse.Namespace) -> int:
    from mimir.importers.common import sha256_file

    store = Store(args.db)
    roots = _roots(args)
    arch = roots.vtr / ARCH_REL if roots.vtr else None
    sha = sha256_file(arch) if arch and arch.is_file() else None
    res = import_runs(store, sha, roots.loki, _src_roots(args, roots.vtr))
    for source, n in sorted(res.counts.items()):
        print(f"{source}: {n} runs")
    for reason, n in sorted(res.skipped.items()):
        print(f"skipped {n} runs: {reason}")
    if res.ambiguous_time:
        print(f"ambiguous time or RSS (a run stored twice, left NULL): {res.ambiguous_time}")
    return 1 if res.skipped else 0


def _cmd_import_runrecords(args: argparse.Namespace) -> int:
    from mimir.runrecord import conf_counts, coverage, import_runrecords, non_given

    store = Store(args.db)
    try:
        rep = import_runrecords(store, Path(args.dir))
    except NotADirectoryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for rel, errs in rep.refused:
        print(f"refused {rel}")
        for err in errs:
            print(f"  {err}")
    print(f"imported {len(rep.imported)} records, refused {len(rep.refused)}")
    print("arm\tstatus\truns")
    for row in coverage(store, args.source):
        print("\t".join(str(x) for x in row))
    print("conf\tparameters")
    for conf, n in sorted(conf_counts(store, args.source).items()):
        print(f"{conf}\t{n}")
    print("non-given parameter\tarm\tconf\tsource")
    for arm, key, conf, src in non_given(store, args.source):
        print(f"{key}\t{arm}\t{conf}\t{src}")
    return 1 if rep.refused else 0


def _cmd_import_timing(args: argparse.Namespace) -> int:
    from mimir import blobs, timing
    from mimir.scrub import Scrubber

    store = Store(args.db)
    scrub = Scrubber({})
    if args.paths_from_blobs:
        root = Path(args.blobs) if args.blobs else blobs.default_dir()
        rows = timing.backfill_paths(
            store, root, scrub, attr_dir=Path(args.attr_dir) if args.attr_dir else None,
            full_dir=Path(args.full_dir) if args.full_dir else None,
            full_requested=args.full_requested or 500000)
        for run_id, status in rows:
            print(f"{run_id}\t{status}")
        bad = sum(1 for _, st in rows if st != "ok")
        print(f"runs {len(rows)}, filled {len(rows) - bad}, not filled {bad}")
        return 1 if any(st.startswith("error") for _, st in rows) else 0
    if args.from_blobs:
        root = Path(args.blobs) if args.blobs else blobs.default_dir()
        rows = timing.import_from_blobs(
            store, root, scrub, attr_dir=Path(args.attr_dir) if args.attr_dir else None,
            full_dir=Path(args.full_dir) if args.full_dir else None,
            full_requested=args.full_requested or 500000)
    else:
        data = Path(args.file).read_bytes()
        if args.report:
            inp = timing.parse_report(data.decode("utf-8", "replace"), timing.sha_of(data),
                                      args.requested)
        else:
            inp = timing.load_attribution_bytes(data)
        if args.full_report:
            fdata = Path(args.full_report).read_bytes()
            full = timing.exhaustive_extent(timing.parse_report(
                fdata.decode("utf-8", "replace"), timing.sha_of(fdata), args.full_requested))
            inp = dataclasses.replace(inp, full=full)
        try:
            res, _ = timing.import_run(store, args.run_id, inp, scrub, args.analysis_n)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        rows = [(args.run_id, timing.status_of(res))]
    for run_id, status in rows:
        print(f"{run_id}\t{status}")
    print(f"runs {len(rows)}, truncated {sum(1 for _, s in rows if s == 'truncated')}, "
          f"errors {sum(1 for _, s in rows if s.startswith('error'))}")
    return 1 if any(s.startswith("error") for _, s in rows) else 0


def _cmd_hdl_graph(args: argparse.Namespace) -> int:
    import os

    from mimir import blobs, hdlgraph
    from mimir.scrub import Scrubber

    tree = args.odin3_tree or os.environ.get("MIMIR_ODIN3_TREE")
    if not tree:
        print("error: give --odin3-tree or set MIMIR_ODIN3_TREE (an Odin III checkout)",
              file=sys.stderr)
        return 2
    store = Store(args.db)
    root = Path(args.blobs) if args.blobs else blobs.default_dir()
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        rows = hdlgraph.backfill(store, root, Scrubber({}), Path(tree), Path(tmp),
                                 set(args.run) if args.run else None)
    for run_id, status in rows:
        print(f"{run_id}\t{status}")
    bad = sum(1 for _, s in rows if not s.startswith("ok"))
    print(f"runs {len(rows)}, built {len(rows) - bad}, errors {bad}")
    return 1 if bad else 0


def _cmd_timing_coverage(args: argparse.Namespace) -> int:
    from mimir import timing

    store = Store(args.db, readonly=True)
    try:
        rows = timing.coverage(store)
    except LookupError as exc:
        print(str(exc))
        return 0
    print("dmax_source\truns\ttruncated\ttruncation unknown\tlower-bound runs")
    for row in rows:
        print("\t".join(str(x) for x in row))
    return 0


def _cmd_migrate(args: argparse.Namespace) -> int:
    if not Path(args.db).is_file():
        print(f"error: no such store {args.db}", file=sys.stderr)
        return 2
    db = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    row = db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    db.close()
    old = None if row is None else str(row[0])
    Store(args.db).close()
    print(f"{args.db}: schema version {old} -> 7")
    return 0


def _cmd_run_coverage(args: argparse.Namespace) -> int:
    store = Store(args.db, readonly=True)
    print("source\tstatus\tconfigs\truns")
    for row in config_coverage(store):
        print("\t".join(str(x) for x in row))
    print("parameter conf\trows\trows used by a run")
    for conf in param_conf_counts(store):
        print("\t".join(str(x) for x in conf))
    print("unknown or unrecorded parameter\tgroup\tconfigs")
    for unk in unknown_params(store):
        print("\t".join(str(x) for x in unk))
    collisions = store.db.execute(
        "SELECT COUNT(*) FROM (SELECT 1 FROM run GROUP BY source, design, arch, seed, arm, "
        "config_hash, tool_commit, input_sha256 HAVING COUNT(*) > 1)").fetchone()[0]
    print(f"run-key collisions\t{collisions}")
    return 0


def _cmd_blob(args: argparse.Namespace) -> int:
    from mimir import blobs

    root = Path(args.blobs) if args.blobs else blobs.default_dir()
    if args.action == "put":
        print(blobs.put_file(root, Path(args.arg)))
    elif args.action == "get":
        Path(args.out).write_bytes(blobs.get_bytes(root, args.arg))
    else:
        problems = blobs.verify(root, [args.arg] if args.arg else None)
        print("\n".join(problems) or f"ok: {len(blobs.all_hashes(root))} blobs")
        return 1 if problems else 0
    return 0


def _cmd_snapshot(args: argparse.Namespace) -> int:
    import tempfile

    from mimir import snapshot

    out = Path(args.dir)
    manifest = snapshot.write_snapshot(Path(args.db), out, parquet=args.parquet)
    print(json.dumps({k: manifest[k] for k in ("dump_bytes", "dump_sha256", "canonical_sha256",
                                                "source_db_bytes")}, sort_keys=True))
    if args.verify:
        tmp = Path(tempfile.mkdtemp(prefix="mim-verify-", dir=args.tmp)) / "restored.db"
        blob_root = Path(args.blobs) if args.blobs else None
        problems = snapshot.verify_snapshot(Path(args.db), out, tmp, blob_root)
        print("\n".join(problems) or "verify: restored store is identical")
        return 1 if problems else 0
    return 0


def _cmd_partition_example(args: argparse.Namespace) -> int:
    from mimir import blobs
    from mimir.partition import import_norns_hindsight

    store = Store(args.db)
    root = Path(args.blobs) if args.blobs else blobs.default_dir()
    pid = import_norns_hindsight(store, root, _root(args.norns, "MIMIR_NORNS"), args.design,
                                 args.arm)
    print(f"partition {pid}")
    return 0


def _cmd_merge_runs(args: argparse.Namespace) -> int:
    from mimir import runmerge

    print(runmerge.BACKUP_ADVICE)
    bf = Path(args.blobs_from) if args.blobs_from else None
    bt = Path(args.blobs_to) if args.blobs_to else None
    bad = 0
    try:
        for other in args.other:
            r = runmerge.merge_runs(args.db, other, bf, bt)
            print(f"{other}: runs copied {r.runs}, records {r.records}, flow_config {r.configs}, "
                  f"blobs copied {r.blobs_copied} (already there {r.blobs_present})")
            for table, n in r.rows.items():
                print(f"  {table}: {n}")
            for line in (*r.conflicts, *r.blobs_missing):
                print(f"  problem: {line}")
            bad += len(r.conflicts) + len(r.blobs_missing)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    check = runmerge.integrity(args.db)
    print(f"integrity_check: {check}")
    return 0 if check == "ok" and not bad else 1


def _cmd_merge(args: argparse.Namespace) -> int:
    if args.runs:
        return _cmd_merge_runs(args)
    if args.blobs_from or args.blobs_to:
        print("error: --blobs-from/--blobs-to need --runs", file=sys.stderr)
        return 2
    store = Store(args.db)
    for other in args.other:
        print(f"{other}: {store.merge(other)} rows")
    print(f"records in store: {store.count()}")
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    store = Store(args.db, readonly=True)
    if args.csv:
        print(f"csv: {store.export_csv(args.csv)} rows")
    if args.parquet:
        print(f"parquet: {store.export_parquet(args.parquet)} rows")
    return 0


COVERAGE_SQL = """
SELECT source, level,
       COUNT(DISTINCT design || '|' || arch) AS designs,
       COUNT(DISTINCT CASE WHEN metric = 'struct.depth' THEN design || '|' || arch END)
           AS with_struct,
       COUNT(DISTINCT CASE WHEN metric = 'rent.p' THEN design || '|' || arch END) AS with_rent,
       COUNT(DISTINCT CASE WHEN metric = 'graphlet_nodes' THEN design || '|' || arch END)
           AS with_graphlet
FROM records
WHERE measurer IN ('struct', 'rent', 'graphlet')
GROUP BY source, level ORDER BY source, level
"""


def _cmd_coverage(args: argparse.Namespace) -> int:
    store = Store(args.db, readonly=True)
    print("source\tlevel\tdesigns\twith_struct\twith_rent\twith_graphlet")
    for row in store.db.execute(COVERAGE_SQL):
        print("\t".join(str(x) for x in row))
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    store = Store(args.db, readonly=True)
    mixed = store.mixed_versions()
    for measurer, versions in mixed:
        print(f"mixed versions: measurer {measurer} has {', '.join(versions)}; re-measure the set")
    print(f"records in store: {store.count()}")
    return 1 if mixed else 0


def _cmd_registry(_: argparse.Namespace) -> int:
    for key, m in sorted(load_registry().items()):
        print(f"{key}\t{m.kind}\t{m.unit}\t{','.join(m.levels)}\t{m.definition_source}")
    return 0


def _cmd_citations(args: argparse.Namespace) -> int:
    text = render_markdown(load_citations(Path(args.toml)))
    Path(args.out).write_text(text, encoding="utf-8")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="mimir", description="Mimir III circuit knowledge base")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("init", help="create an empty database")
    s.add_argument("db")
    s.set_defaults(fn=_cmd_init)
    s = sub.add_parser("import", help="import existing Norns, atlas and Loki data (read only)")
    s.add_argument("db")
    s.add_argument("what", choices=("norns", "loki", "all"))
    s.add_argument("--norns", help="Norns checkout (default $MIMIR_NORNS)")
    s.add_argument("--loki", help="directory holding the loki-* data dirs (default $MIMIR_LOKI)")
    s.add_argument("--runs", help="norns: also import the run records under DIR and the timing "
                   "evidence they kept (timing, blif, map blobs; schema 5-7 tables)")
    s.add_argument("--blobs", help="with --runs: blob directory (default $MIMIR_BLOBS)")
    s.add_argument("--odin3-tree", help="with --runs: Odin III checkout for the HDL graph "
                   "(default $MIMIR_ODIN3_TREE)")
    s.add_argument("--keep-store", help="with --runs: Norns keep store (default "
                   "$NORNS_KEEP_STORE, else DIR/_keep-inputs)")
    s.set_defaults(fn=_cmd_import)
    s = sub.add_parser(
        "import-e10",
        help="E10 placer-sweep metrics from <data>/placers/*.json into records (joined to run)")
    s.add_argument("db")
    s.add_argument("data", help="the run root's data directory (holds placers/)")
    s.add_argument("--label", default="e10")
    s.add_argument(
        "--netlists",
        help="the run root's netlists directory (adds struct.n_comb, the Odin III netlist LUTs)")
    s.set_defaults(fn=_cmd_import_e10)
    s = sub.add_parser("measure-set", help="measure a netlist set: mcnc, mcnc-k2/k4, norns, "
                       "norns-runs or loki")
    s.add_argument("db")
    s.add_argument("set", choices=sorted(SETS))
    s.add_argument("--root", help="set root (default $VTR_ROOT, $MIMIR_BLOBS, $MIMIR_NORNS "
                   "or $MIMIR_LOKI)")
    s.add_argument("--no-rent", action="store_true")
    s.add_argument("--graphlet", action="store_true",
                   help="also run the Odin III graphlets pass (needs the odin3 package)")
    s.add_argument("--seeds", default="1,2,3")
    s.add_argument("--rent-max-nodes", type=int, default=RENT_MAX_NODES)
    s.set_defaults(fn=_cmd_measure_set)
    s = sub.add_parser("import-meta", help="MCNC design meta from the toml, then register designs")
    s.add_argument("db")
    s.add_argument("--toml", default="data/meta/mcnc.toml")
    s.add_argument("--licences", default="data/meta/licences.toml")
    s.add_argument("--vtr", help="VTR checkout (default $VTR_ROOT)")
    s.add_argument("--norns", help="Norns checkout (default $MIMIR_NORNS)")
    s.add_argument("--loki", help="Loki sources dir (default $MIMIR_LOKI)")
    s.set_defaults(fn=_cmd_meta)
    s = sub.add_parser("meta-coverage", help="design_meta rows per field and confidence")
    s.add_argument("db")
    s.add_argument("--prefix", default="", help="slug prefix, for example mcnc20/")
    s.set_defaults(fn=_cmd_meta_coverage)
    s = sub.add_parser("import-runs", help="flow_config and run rows from the stored records")
    s.add_argument("db")
    s.add_argument("--vtr", help="VTR checkout (default $VTR_ROOT)")
    s.add_argument("--norns", help="unused; kept for symmetry with import-meta")
    s.add_argument("--loki", help="Loki sources dir (default $MIMIR_LOKI)")
    s.add_argument("--odin3", help="Odin III checkout, for its defaults (default $MIMIR_ODIN3)")
    s.add_argument("--norns-src", dest="norns_src",
                   help="nornsIII checkout, for its defaults (default $MIMIR_NORNS_SRC)")
    s.set_defaults(fn=_cmd_runs)
    s = sub.add_parser("import-runrecords", help="runs and flow configs from run records")
    s.add_argument("db")
    s.add_argument("dir", help="directory searched for mimir-run.json files")
    s.add_argument("--source", default="", help="report only the runs of this source (exact)")
    s.set_defaults(fn=_cmd_import_runrecords)
    s = sub.add_parser("import-timing", help="near-critical timing data and per-path rows "
                       "(schema 6)")
    s.add_argument("db")
    s.add_argument("file", nargs="?", help="attribution.json, or a VPR report with --report")
    s.add_argument("--run-id", help="the run the file belongs to")
    s.add_argument("--report", action="store_true", help="FILE is report_timing.setup.rpt")
    s.add_argument("--requested", type=int, help="--timing_report_npaths of a report")
    s.add_argument("--analysis-n", type=int, help="npaths of a timing-only re-run")
    s.add_argument("--from-blobs", action="store_true", help="every stored `timing` artifact")
    s.add_argument("--paths-from-blobs", action="store_true",
                   help="fill timing_path and timing_path_node (schema 6) of every run that has "
                   "a timing_run row and no path rows, from its stored `timing` artifact (sha256 "
                   "checked); idempotent; writes only those two tables. Back the store up first")
    s.add_argument("--blobs", help="blob directory (default $MIMIR_BLOBS)")
    s.add_argument("--attr-dir", help="with --from-blobs: DIR/<run_id>.attribution.json replaces "
                   "that run's stored artifact (a re-run with a larger N)")
    s.add_argument("--full-dir", help="with --from-blobs: DIR/<run_id>.rpt.xz is an exhaustive "
                   "report of that run (see --full-requested)")
    s.add_argument("--full-report", help="an exhaustive report_timing.setup.rpt of the same "
                   "run: gives the exact max required time per clock domain pair")
    s.add_argument("--full-requested", type=int, help="--timing_report_npaths of --full-report "
                   "(the report must hold fewer paths)")
    s.set_defaults(fn=_cmd_import_timing)
    s = sub.add_parser("hdl-graph", help="line-level HDL graph of runs from their stored blif and "
                       "map blobs (schema 7); idempotent. Back the store up first")
    s.add_argument("db")
    s.add_argument("--odin3-tree", help="Odin III checkout (default $MIMIR_ODIN3_TREE)")
    s.add_argument("--blobs", help="blob directory (default $MIMIR_BLOBS)")
    s.add_argument("--run", action="append", help="only this run id (repeatable)")
    s.set_defaults(fn=_cmd_hdl_graph)
    s = sub.add_parser("timing-coverage", help="timing runs by max_req basis and truncation "
                       "(read only; reports 'no timing tables' on a version 4 store)")
    s.add_argument("db")
    s.set_defaults(fn=_cmd_timing_coverage)
    s = sub.add_parser("migrate", help="migrate a store to the current schema version in place "
                       "(additive; BACK UP the file first: copy it and compare sha256)")
    s.add_argument("db")
    s.set_defaults(fn=_cmd_migrate)
    s = sub.add_parser("run-coverage", help="runs with full against partial flow configs")
    s.add_argument("db")
    s.set_defaults(fn=_cmd_run_coverage)
    s = sub.add_parser("blob", help="content-addressed xz blob store: put, get, verify")
    s.add_argument("action", choices=("put", "get", "verify"))
    s.add_argument("arg", nargs="?", help="put: file; get: sha256; verify: sha256 (default all)")
    s.add_argument("out", nargs="?", help="get: output file")
    s.add_argument("--blobs", help="blob directory (default $MIMIR_BLOBS)")
    s.set_defaults(fn=_cmd_blob)
    s = sub.add_parser("snapshot", help="write the store as an xz SQL dump plus a manifest")
    s.add_argument("db")
    s.add_argument("dir")
    s.add_argument("--verify", action="store_true", help="restore and compare byte for byte")
    s.add_argument("--parquet", action="store_true", help="also one zstd Parquet file per table")
    s.add_argument("--tmp", default="/tmp/claude-1000", help="parent of the restore temp dir")
    s.add_argument("--blobs", help="blob directory the manifest's blobs are checked in "
                   "(default $MIMIR_BLOBS)")
    s.set_defaults(fn=_cmd_snapshot)
    s = sub.add_parser("partition-example", help="import a Norns round 7 hindsight clustering")
    s.add_argument("db")
    s.add_argument("--design", default="ch_intrinsics")
    s.add_argument("--arm", default="h1")
    s.add_argument("--norns", help="Norns checkout (default $MIMIR_NORNS)")
    s.add_argument("--blobs", help="blob directory (default $MIMIR_BLOBS)")
    s.set_defaults(fn=_cmd_partition_example)
    s = sub.add_parser("merge", help="copy the records of other databases into this one; "
                   "--runs copies whole runs (and structures, timing, HDL graph, blobs)")
    s.add_argument("db")
    s.add_argument("other", nargs="+")
    s.add_argument("--runs", action="store_true",
                   help="copy every run the target lacks (by run_id) with all its run-keyed rows "
                   "and records; flow_config/flow_param insert-or-ignore; idempotent; both "
                   "stores must be at the current schema; BACK UP the target first")
    s.add_argument("--blobs-from", help="with --runs: source blob dir of the run artifacts")
    s.add_argument("--blobs-to", help="with --runs: target blob dir (sha256 checked copy); "
                   "give both or neither")
    s.set_defaults(fn=_cmd_merge)
    s = sub.add_parser("export", help="write CSV and/or Parquet in identity order")
    s.add_argument("db")
    s.add_argument("--csv")
    s.add_argument("--parquet")
    s.set_defaults(fn=_cmd_export)
    s = sub.add_parser("coverage", help="designs x levels with the structural and Rent metrics")
    s.add_argument("db")
    s.set_defaults(fn=_cmd_coverage)
    s = sub.add_parser("check", help="report a store that mixes versions of one measurer")
    s.add_argument("db")
    s.set_defaults(fn=_cmd_check)
    s = sub.add_parser("registry", help="list the metric registry")
    s.set_defaults(fn=_cmd_registry)
    s = sub.add_parser("citations", help="render citations.toml to markdown")
    s.add_argument("--toml", default="citations.toml")
    s.add_argument("--out", default="docs/CITATIONS.md")
    s.set_defaults(fn=_cmd_citations)
    from mimir.remotecli import add_parsers

    add_parsers(sub)
    from mimir.benchcli import add_parsers as add_bench_parsers

    add_bench_parsers(sub)
    from mimir.hostcli import add_parsers as add_host_parsers

    add_host_parsers(sub)
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.fn(args))


if __name__ == "__main__":
    sys.exit(main())
