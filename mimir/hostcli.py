"""Commands `mimir host-alias` and `mimir privacy-check`
(docs/specs/2026-10-28-mimir-host-alias.md)."""

from __future__ import annotations

import argparse
from pathlib import Path

from mimir import hostalias, hostscrub, privacy


def _dbs(args: argparse.Namespace) -> list[Path]:
    if args.db:
        return [Path(d) for d in args.db]
    return sorted(Path(args.dir).glob("*.db")) if args.dir else []


def _cmd_host_alias(args: argparse.Namespace) -> int:
    map_file = Path(args.map) if args.map else None
    hostalias.this_host(map_file)  # this machine always has an alias before any scrub
    dbs = _dbs(args)
    for db in dbs:
        done, left = hostscrub.rewrite_hosts(db, map_file)
        print(f"{db.name}\thost rows rewritten: {done}\tunaliased after: {left}")
    if args.blobs:
        root = Path(args.blobs)
        strings = privacy.private_strings(map_file)
        total: dict[str, str] = {}
        for db in dbs:
            got = hostscrub.reblob(db, root, strings, map_file)
            total.update(got)
            print(f"{db.name}\tblobs re-blobbed: {len(got)}")
        print(f"blobs re-blobbed (distinct): {len(total)}")
        for old, new in sorted(total.items()):
            print(f"blob\t{old}\t{new}")
        if args.index:
            n = hostscrub.update_blob_index(Path(args.index), total, root, args.archive)
            print(f"blob index rows changed: {n}")
    return 0


def _cmd_privacy_check(args: argparse.Namespace) -> int:
    strings = privacy.private_strings(Path(args.map) if args.map else None)
    hits: list[str] = []
    for db in args.db:
        hits += privacy.scan_db(Path(db), strings)
    for path in args.path:
        p = Path(path)
        hits += privacy.scan_tree(p, strings) if p.is_dir() else privacy.scan_file(p, strings)
    if args.blobs:
        n, found = privacy.scan_blobs(Path(args.blobs), strings,
                                      Path(args.index) if args.index else None)
        print(f"blobs scanned: {n}")
        hits += found
    print(f"private strings checked: {len(strings)}")
    for h in hits[:args.max_list]:
        print(f"hit\t{h}")
    print(f"hits: {len(hits)}")
    return 1 if hits else 0


def add_parsers(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    s = sub.add_parser("host-alias", help="rewrite run.host to host aliases; --blobs re-blobs "
                       "the blobs that hold a private string")
    s.add_argument("db", nargs="*", help="stores (default: every *.db of --dir)")
    s.add_argument("--dir", help="a directory of stores")
    s.add_argument("--map", help="host map (default $MIMIR_HOST_MAP or the workspace private dir)")
    s.add_argument("--blobs", help="blob directory to scrub")
    s.add_argument("--index", help="remote index dir: old blobs become withheld, new are added")
    s.add_argument("--archive", default="-", help="archive name of the new blobs in the index")
    s.set_defaults(fn=_cmd_host_alias)
    c = sub.add_parser("privacy-check", help="scan stores, CSV, blobs and snapshots for the "
                       "private strings of the local map and $MIMIR_PRIVATE_STRINGS")
    c.add_argument("--db", action="append", default=[], help="a store (repeatable)")
    c.add_argument("--path", action="append", default=[],
                   help="a file, directory (CSV export, snapshot) or .tar.xz (repeatable)")
    c.add_argument("--blobs", help="blob directory")
    c.add_argument("--index", help="remote index dir: scan only the blobs marked public")
    c.add_argument("--map")
    c.add_argument("--max-list", type=int, default=50)
    c.set_defaults(fn=_cmd_privacy_check)

