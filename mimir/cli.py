"""Command line: `mimir init|import|measure-set|merge|export|coverage|check|registry|citations`."""

from __future__ import annotations

import argparse
import json
import os
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
    return 0


def _cmd_measure_set(args: argparse.Namespace) -> int:
    build, var = SETS[args.set]
    store = Store(args.db)
    seeds = [int(s) for s in args.seeds.split(",")]
    errors: Counter[str] = Counter()
    notes: Counter[str] = Counter()
    done = 0
    for job in build(_root(args.root, var)):
        out = measure_job(job, seeds=seeds, rent=not args.no_rent,
                          rent_max_nodes=args.rent_max_nodes)
        if out.error:
            errors[out.error[:90]] += 1
            continue
        store.replace_measured(out.records)
        done += 1
        if out.rent_note:
            notes[out.rent_note] += 1
    print(f"set {args.set}: measured {done} netlists")
    for msg, n in sorted(errors.items()):
        print(f"  skipped {n}: {msg}")
    for msg, n in sorted(notes.items()):
        print(f"  rent note {n}: {msg}")
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


def _cmd_merge(args: argparse.Namespace) -> int:
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
       COUNT(DISTINCT CASE WHEN metric = 'rent.p' THEN design || '|' || arch END) AS with_rent
FROM records
WHERE measurer IN ('struct', 'rent')
GROUP BY source, level ORDER BY source, level
"""


def _cmd_coverage(args: argparse.Namespace) -> int:
    store = Store(args.db, readonly=True)
    print("source\tlevel\tdesigns\twith_struct\twith_rent")
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
    s.set_defaults(fn=_cmd_import)
    s = sub.add_parser("measure-set", help="measure a netlist set: mcnc, norns or loki")
    s.add_argument("db")
    s.add_argument("set", choices=sorted(SETS))
    s.add_argument("--root", help="set root (default $VTR_ROOT, $MIMIR_NORNS or $MIMIR_LOKI)")
    s.add_argument("--no-rent", action="store_true")
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
    s = sub.add_parser("merge", help="copy the rows of other databases into this one")
    s.add_argument("db")
    s.add_argument("other", nargs="+")
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
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.fn(args))


if __name__ == "__main__":
    sys.exit(main())
