"""`mimir import-aidigit` and `mimir aidigit-table`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mimir import aidigit, aidigittable
from mimir.store import Store

DEFAULT_SUITE = Path(__file__).resolve().parents[1] / "suites" / "ai-digit-recognition"


def _cmd_import(args: argparse.Namespace) -> int:
    suite = Path(args.suite)
    try:
        data = aidigit.load(suite)
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    store = Store(args.db)
    try:
        rows, nulls = aidigit.write(store, data)
    finally:
        store.close()
    per = data.per_impl()
    print(f"aidigit: {rows} rows, {nulls} null reasons")
    for impl in sorted(per):
        print(f"  {impl}\t{per[impl]}")
    return 0


def _cmd_table(args: argparse.Namespace) -> int:
    store = Store(args.db, readonly=True)
    try:
        if not aidigit.has_tables(store.db):
            print("error: store has no aidigit tables; run `mimir migrate` then "
                  "`mimir import-aidigit`", file=sys.stderr)
            return 2
        rows = aidigit.read_rows(store.db)
        nulls = aidigit.read_nulls(store.db)
    finally:
        store.close()
    if not rows:
        print("error: no AI digit rows in the store; run `mimir import-aidigit`", file=sys.stderr)
        return 2
    for path in aidigittable.write_all(rows, nulls, Path(args.out_dir)):
        print(path)
    return 0


def add_parsers(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p = sub.add_parser("import-aidigit", help="AI digit recognition results into the store")
    p.add_argument("--db", required=True)
    p.add_argument("--suite", default=str(DEFAULT_SUITE),
                   help="suite directory with results/*.jsonl and implementations.toml")
    p.set_defaults(fn=_cmd_import)
    p = sub.add_parser("aidigit-table", help="academic table (md, csv, tex) and Pareto plots")
    p.add_argument("--db", required=True)
    p.add_argument("--out-dir", required=True)
    p.set_defaults(fn=_cmd_table)
