"""Command line: `mimir init|import|measure-set|merge|export|coverage|check|registry|citations`."""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from mimir.citations import load_citations, render_markdown
from mimir.importers.common import Report
from mimir.measure import RENT_MAX_NODES, measure_job
from mimir.meta import Roots, import_mcnc_meta, meta_coverage, register_designs
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
    print(f"mcnc meta circuits: {n}; designs registered: {m}")
    return 0


def _cmd_meta_coverage(args: argparse.Namespace) -> int:
    store = Store(args.db)
    print("field\tconf\tdesigns")
    for field, conf, n in meta_coverage(store, args.prefix):
        print(f"{field}\t{conf}\t{n}")
    return 0


def _cmd_merge(args: argparse.Namespace) -> int:
    store = Store(args.db)
    for other in args.other:
        print(f"{other}: {store.merge(other)} rows")
    print(f"records in store: {store.count()}")
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    store = Store(args.db)
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
    store = Store(args.db)
    print("source\tlevel\tdesigns\twith_struct\twith_rent")
    for row in store.db.execute(COVERAGE_SQL):
        print("\t".join(str(x) for x in row))
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    store = Store(args.db)
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
    s.add_argument("--vtr", help="VTR checkout (default $VTR_ROOT)")
    s.add_argument("--norns", help="Norns checkout (default $MIMIR_NORNS)")
    s.add_argument("--loki", help="Loki sources dir (default $MIMIR_LOKI)")
    s.set_defaults(fn=_cmd_meta)
    s = sub.add_parser("meta-coverage", help="design_meta rows per field and confidence")
    s.add_argument("db")
    s.add_argument("--prefix", default="", help="slug prefix, for example mcnc20/")
    s.set_defaults(fn=_cmd_meta_coverage)
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
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.fn(args))


if __name__ == "__main__":
    sys.exit(main())
