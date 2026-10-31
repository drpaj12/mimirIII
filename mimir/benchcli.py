"""Command line of the benchmark registry: `mimir bench list|show|fetch|build|...`."""

from __future__ import annotations

import argparse
import os
from collections import Counter
from pathlib import Path

from mimir import bench, benchreg, blobs
from mimir.meta import load_licence_rules


def _idx(args: argparse.Namespace) -> Path:
    return Path(args.index) if args.index else bench.index_dir()


def _store(args: argparse.Namespace) -> Path:
    return Path(args.blobs) if args.blobs else blobs.default_dir()


def _cmd_list(args: argparse.Namespace) -> int:
    idx = _idx(args)
    suites = bench.load_suites(idx)
    designs = bench.load_designs(idx)
    nets = bench.load_netlists(idx)
    if not args.suite:
        print("suite\thosting\tdesigns\tnetlists\tcommit\tlicence")
        for s in suites.values():
            n_d = sum(d.suite == s.id for d in designs)
            n_n = sum(n.suite == s.id for n in nets)
            print(f"{s.id}\t{s.hosting}\t{n_d}\t{n_n}\t{s.commit[:10]}\t{s.licence[:60]}")
        return 0
    if args.suite not in suites:
        print(f"error: unknown suite {args.suite!r}")
        return 2
    have = {(n.design, n.flow) for n in nets if n.suite == args.suite}
    if args.netlists:
        for design, flow in sorted(have):
            print(f"{args.suite}:{design}@{flow}")
        return 0
    for d in designs:
        if d.suite == args.suite:
            flows = ",".join(sorted(f for dd, f in have if dd == d.design)) or "-"
            print(f"{d.design}\t{d.bytes}\t{d.lines}\t{d.licence_rule}\t{flows}")
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    idx = _idx(args)
    try:
        res = bench.resolve(args.ref, idx)
    except bench.BenchError as exc:
        print(f"error: {exc}")
        return 2
    s, d = res.suite, res.design
    print(f"design\t{s.id}:{d.design}\nformat\t{d.format}\ntop\t{d.top}\nslug\t{d.slug}")
    print(f"source\t{s.external}/{s.subdir}/{d.path}\nsource_sha256\t{d.sha256}")
    print(f"size\t{d.bytes} bytes, {d.lines} lines\nupstream\t{s.upstream}\ncommit\t{s.commit}")
    print(f"licence\t{s.licence}\nlicence_source\t{s.licence_source}\nlicence_rule\t{d.licence_rule}")
    print(f"hosting\t{s.hosting}\nobtained\t{s.obtained}")
    flows = bench.load_flows(idx)
    for n in bench.load_netlists(idx):
        if (n.suite, n.design) == (s.id, d.design):
            f = flows[n.flow]
            print(f"netlist\t{n.flow}\t{n.sha256}\t{n.raw_bytes} bytes\tmap={n.map_sha256}"
                  f"\trecord={n.flowrec_sha256}")
            print(f"flow\t{f.id}\t{f.tool} {f.tool_version} {f.tool_commit}\tarch={f.arch}"
                  f"\tK={f.lut_k}")
    return 0


def _cmd_fetch(args: argparse.Namespace) -> int:
    try:
        out = Path(args.out) if args.out else None
        print(bench.materialise(args.ref, out, args.kind, _idx(args)))
    except bench.BenchError as exc:
        print(f"error: {exc}")
        return 1
    return 0


def _refresh_blob_index(idx: Path, store: Path) -> int:
    return bench.write_blob_index(idx, store, bench.load_suites(idx), bench.load_netlists(idx))


def _cmd_build(args: argparse.Namespace) -> int:
    idx, store = _idx(args), _store(args)
    odin3 = Path(args.odin3 or os.environ.get("MIMIR_ODIN3", ""))
    arch = Path(args.arch_dir) if args.arch_dir else None
    try:
        row = benchreg.build_netlist(idx, store, args.ref, args.flow, odin3, arch)
        _refresh_blob_index(idx, store)
    except (bench.BenchError, OSError) as exc:
        print(f"error: {exc}")
        return 1
    print(f"{args.ref}@{row.flow}\t{row.sha256}")
    return 0


def _cmd_register(args: argparse.Namespace) -> int:
    idx = _idx(args)
    rules = load_licence_rules(Path(__file__).resolve().parents[1] / "data/meta/licences.toml")
    try:
        for suite in args.suite:
            print(f"{suite}: {benchreg.register_suite(idx, suite, rules)} designs")
    except bench.BenchError as exc:
        print(f"error: {exc}")
        return 1
    return 0


def _cmd_import(args: argparse.Namespace) -> int:
    idx, store = _idx(args), _store(args)
    ws = Path(args.workspace) if args.workspace else bench.external_root().parent
    try:
        n, skipped = benchreg.import_netlists(idx, store, args.suite, args.flow,
                                              Path(args.dir), ws)
        total = _refresh_blob_index(idx, store)
    except (bench.BenchError, OSError) as exc:
        print(f"error: {exc}")
        return 1
    print(f"{args.suite}@{args.flow}: imported {n} netlists; blobs in index {total}")
    if skipped:
        print(f"  not registered in this suite: {len(skipped)} ({', '.join(skipped[:6])}...)")
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    store = _store(args) if args.local else None
    probs = bench.check(_idx(args), store, args.verify)
    for p in probs:
        print(p)
    idx = _idx(args)
    nets = bench.load_netlists(idx)
    print(f"suites {len(bench.load_suites(idx))}, designs {len(bench.load_designs(idx))}"
          f", netlists {len(nets)}, problems {len(probs)}")
    by = Counter(n.flow for n in nets)
    for flow, n in sorted(by.items()):
        print(f"  {flow}\t{n}")
    return 1 if probs else 0


def add_parsers(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    b = sub.add_parser("bench", help="the benchmark registry: suites, designs, netlists")
    bs = b.add_subparsers(dest="bcmd", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--index", help="registry dir (default: the repo's data/benchmarks)")
        p.add_argument("--blobs", help="blob store (default $MIMIR_BLOBS)")

    p = bs.add_parser("list", help="suites, or the designs (or netlist references) of a suite")
    common(p)
    p.add_argument("--suite")
    p.add_argument("--netlists", action="store_true", help="with --suite: suite:design@flow lines")
    p.set_defaults(fn=_cmd_list)
    p = bs.add_parser("show", help="one design: source, licence, netlists, flows")
    common(p)
    p.add_argument("ref", help="suite:design[@flow]")
    p.set_defaults(fn=_cmd_show)
    p = bs.add_parser("fetch", help="write a netlist (or map, flow record, source path)")
    common(p)
    p.add_argument("ref")
    p.add_argument("--kind", default="netlist", choices=("netlist", "map", "flow", "source"))
    p.add_argument("--out")
    p.set_defaults(fn=_cmd_fetch)
    p = bs.add_parser("build", help="compile a registered source with a flow; record it")
    common(p)
    p.add_argument("ref")
    p.add_argument("--flow", required=True)
    p.add_argument("--odin3", help="Odin III binary (default $MIMIR_ODIN3)")
    p.add_argument("--arch-dir", help="dir holding the architecture xml of the flow")
    p.set_defaults(fn=_cmd_build)
    p = bs.add_parser("register", help="rebuild the designs of suites from their checkouts")
    common(p)
    p.add_argument("suite", nargs="+")
    p.set_defaults(fn=_cmd_register)
    p = bs.add_parser("import", help="import the netlists of a flow layout under DIR")
    common(p)
    p.add_argument("dir")
    p.add_argument("--suite", required=True)
    p.add_argument("--flow", required=True)
    p.add_argument("--workspace", help="root replaced by $WS in stored text")
    p.set_defaults(fn=_cmd_import)
    p = bs.add_parser("check", help="the index is consistent; with --local the blobs are present")
    common(p)
    p.add_argument("--local", action="store_true")
    p.add_argument("--verify", action="store_true", help="with --local: hash every blob")
    p.set_defaults(fn=_cmd_check)
