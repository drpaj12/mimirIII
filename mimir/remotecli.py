"""Command line of the remote-data lane: `mimir fetch` and `mimir remote ...`."""

from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path

from mimir import blobs, publish, remote
from mimir.licscan import load_table
from mimir.meta import load_licence_rules


def _idx(args: argparse.Namespace) -> Path:
    return Path(args.index) if args.index else remote.index_dir()


def _cmd_fetch(args: argparse.Namespace) -> int:
    idx = _idx(args)
    loc = remote.Locations.from_env(args.online)
    if args.url:
        loc = remote.Locations(loc.blobs, loc.archive_dir, args.url, loc.cache)
    out = Path(args.out) if args.out else None
    try:
        if args.run:
            if not args.db:
                raise remote.FetchError("--run needs --db")
            db = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
            for kind, path in remote.fetch_run(idx, loc, db, args.run, out):
                print(f"{kind}\t{path}")
        elif args.sha:
            print(remote.fetch_sha(idx, loc, args.sha, out))
        elif args.target and ":" in args.target:
            name, member = args.target.split(":", 1)
            print(remote.fetch_member(idx, loc, name, member, out))
        else:
            raise remote.FetchError("give ARCHIVE:MEMBER, --sha SHA or --run RUN_ID")
    except remote.FetchError as exc:
        print(f"error: {exc}")
        return 1
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    db = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    rows = remote.remote_check(db, remote.load_blob_index(_idx(args)))
    print("table\tcolumn\trefs\tresolved\tmissing")
    for r in rows:
        print(f"{r.table}\t{r.column}\t{r.refs}\t{r.resolved}\t{len(r.missing)}")
    for r in rows:
        for sha in r.missing[:args.max_list]:
            print(f"missing\t{r.table}.{r.column}\t{sha}")
    return 1 if any(r.missing for r in rows) else 0


def _cmd_index(args: argparse.Namespace) -> int:
    from mimir.remoteindex import run_index

    idx = _idx(args)
    store = Path(args.blobs) if args.blobs else blobs.default_dir()
    archives = run_index(Path(args.archive_dir), idx, store, idx / "licences.toml")
    print(f"archives: {len(archives)}")
    return 0


def _cmd_plan(args: argparse.Namespace) -> int:
    idx = _idx(args)
    rules = load_licence_rules(idx.parent / "meta" / "licences.toml")
    rows, _ = load_table(idx / "licences.toml")
    plans = publish.build_plans(idx, rules, rows)
    only = [n for n in args.only.split(",") if n] if args.only else []
    try:
        chosen = publish.select(plans, only, args.allow_pending)
        print(publish.format_plan(chosen))
        for p in plans if not only else []:
            if p not in chosen:
                print(f"skipped\t{p.archive.name}\t{p.licence}")
        for p in chosen:
            for rid, names in p.hits.items():
                print(f"licence\t{p.archive.name}\t{rid}\t{len(names)} designs")
            for path in p.unlicensed[:5]:
                print(f"no-licence-meta\t{p.archive.name}\t{path}")
        if args.stage:
            stage = Path(args.stage)
            publish.check_space(stage)
            master = Path(args.archive_dir or os.environ.get("MIMIR_ARCHIVE", ""))
            store = Path(args.blobs) if args.blobs else blobs.default_dir()
            for line in publish.run_stage(stage, master, chosen, idx, store, remote.DEFAULT_BASE,
                                          args.with_blobs, args.record):
                print(line)
        if args.record:
            publish.record_licences(idx, plans)
    except publish.PlanError as exc:
        print(f"error: {exc}")
        return 2
    return 0


def add_parsers(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    s = sub.add_parser("fetch", help="fetch one archive member, blob or run artifacts")
    s.add_argument("target", nargs="?", help="ARCHIVE:MEMBER")
    s.add_argument("--sha", help="a blob or manifest file by sha256")
    s.add_argument("--run", help="every artifact of a run (needs --db)")
    s.add_argument("--db")
    s.add_argument("--out", help="output file (a dir for --run)")
    s.add_argument("--url", help="base URL (overrides MIMIR_DATA_URL and the index)")
    s.add_argument("--online", action="store_true", help="use the default Hostinger base URL")
    s.add_argument("--index", help="index dir (default: the repo's data/remote)")
    s.set_defaults(fn=_cmd_fetch)
    r = sub.add_parser("remote", help="index, check and publish-plan for the remote data")
    rs = r.add_subparsers(dest="rcmd", required=True)
    c = rs.add_parser("check", help="every blob reference of a store resolves to the index")
    c.add_argument("db")
    c.add_argument("--index")
    c.add_argument("--max-list", type=int, default=50)
    c.set_defaults(fn=_cmd_check)
    i = rs.add_parser("index", help="rebuild data/remote from an archive dir (read only)")
    i.add_argument("archive_dir")
    i.add_argument("--index")
    i.add_argument("--blobs")
    i.set_defaults(fn=_cmd_index)
    p = rs.add_parser("publish-plan", help="what to upload; --stage writes the tree locally")
    p.add_argument("--index")
    p.add_argument("--only", help="comma separated archive names")
    p.add_argument("--stage", help="directory to write the upload tree to")
    p.add_argument("--archive-dir", help="dir with the master archives (default $MIMIR_ARCHIVE)")
    p.add_argument("--blobs")
    p.add_argument("--with-blobs", action="store_true")
    p.add_argument("--allow-pending", action="store_true")
    p.add_argument("--record", action="store_true", help="write the repack fields into the index")
    p.set_defaults(fn=_cmd_plan)
