"""Writers of the benchmark registry: register a suite's designs, import netlists, build one."""

from __future__ import annotations

import hashlib
import json
import re
import shlex
import subprocess
import tempfile
from dataclasses import replace
from pathlib import Path

from mimir import blobs
from mimir.bench import (
    NONE,
    BenchError,
    Design,
    Flow,
    Netlist,
    Suite,
    external_root,
    load_designs,
    load_flows,
    load_netlists,
    load_suites,
    save_designs,
    save_netlists,
    source_path,
)
from mimir.meta import Rule, rules_matching
from mimir.scrub import Scrubber, check_clean

_MODULE = re.compile(rb"^\s*module\s+([A-Za-z_][A-Za-z0-9_$]*)", re.MULTILINE)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _lines(data: bytes) -> int:
    return data.count(b"\n") + (0 if data.endswith(b"\n") or not data else 1)


def _files(suite: Suite, base: Path) -> list[Path]:
    if suite.list:
        names = [n.strip() for n in (base / suite.list).read_text().splitlines() if n.strip()]
        return [base / n for n in names if (base / n).is_file()]
    return sorted(p for p in base.glob(suite.glob) if p.is_file())


def _top(data: bytes, default: str) -> str:
    mods = sorted(set(_MODULE.findall(data)))
    return mods[0].decode() if len(mods) == 1 else (default or NONE)


def _design(suite: Suite, base: Path, path: Path, rules: list[Rule]) -> Design:
    data = path.read_bytes()
    name = path.stem
    if suite.strip_suffix and name.endswith(suite.strip_suffix):
        name = name[: -len(suite.strip_suffix)]
    slug = f"{suite.slug_prefix}{name}" if suite.slug_prefix else NONE
    hit = rules_matching(slug, rules) if suite.slug_prefix else []
    top = _top(data, suite.top) if suite.format == "verilog" else NONE
    return Design(suite.id, name, slug, path.relative_to(base).as_posix(), suite.format, top,
                  len(data), _lines(data), _sha(data), str(hit[0]["id"]) if hit else NONE)


def _project(suite: Suite, base: Path) -> Design:
    files = sorted(base.glob(suite.glob))
    listing = "".join(f"{p.name} {_sha(p.read_bytes())}\n" for p in files)
    data = [p.read_bytes() for p in files]
    return Design(suite.id, base.name if base.name != "." else suite.id, NONE, ".",
                  "verilog-project", suite.top or NONE, sum(len(d) for d in data),
                  sum(_lines(d) for d in data), _sha(listing.encode()), NONE)


def register_suite(idx: Path, suite_id: str, rules: list[Rule]) -> int:
    """Rebuild the `designs.tsv` rows of one suite from its checkout; rows of other suites and a
    known `top` stay."""
    suite = load_suites(idx).get(suite_id)
    if suite is None:
        raise BenchError(f"unknown suite {suite_id!r}")
    base = external_root() / suite.external / suite.subdir
    if not base.is_dir():
        raise BenchError(f"{suite_id}: checkout not found: {suite.external}/{suite.subdir}")
    if suite.format == "verilog-project":
        new = [_project(suite, base)]
    else:
        new = [_design(suite, base, p, rules) for p in _files(suite, base)]
    names = [d.design for d in new]
    if len(set(names)) != len(names):
        raise BenchError(f"{suite_id}: duplicate design names")
    old = load_designs(idx)
    known = {(d.suite, d.design): d.top for d in old}
    new = [replace(d, top=known[(d.suite, d.design)])
           if d.top == NONE and known.get((d.suite, d.design), NONE) != NONE else d for d in new]
    save_designs(idx, [d for d in old if d.suite != suite_id] + new)
    return len(new)


# ---- netlists ----------------------------------------------------------------------------------

def _layout_regex(layout: str) -> tuple[str, re.Pattern[str]]:
    """Glob and regex of a layout template whose `{d}` is the design name (a repeat of `{d}` must
    repeat the same name)."""
    parts = layout.split("{d}")
    rx = re.escape(parts[0]) + "(?P<d>[^/]+)" + "(?P=d)".join(re.escape(p) for p in parts[1:])
    return "*".join(parts), re.compile(rx)


def _upsert(rows: list[Netlist], new: Netlist) -> list[Netlist]:
    out = []
    for r in rows:
        if (r.suite, r.design, r.flow) == (new.suite, new.design, new.flow):
            if r.sha256 != new.sha256:
                raise BenchError(f"{r.suite}:{r.design}@{r.flow}: a different netlist "
                                 f"({r.sha256[:12]}) is registered; not overwritten")
            continue
        out.append(r)
    return [*out, new]


def _scrubber(ws: Path) -> Scrubber:
    vtr = external_root() / "vtr-verilog-to-routing"
    return Scrubber({"$VTR_ROOT": vtr, "$WS": ws})


def _store_text(store: Path, path: Path, scrub: Scrubber) -> str:
    if not path.is_file():
        return NONE
    return blobs.put_bytes(store, scrub.text(path.read_text(encoding="utf-8")).encode("utf-8"))


def import_netlists(idx: Path, store: Path, suite_id: str, flow_id: str, root: Path,
                    ws: Path) -> tuple[int, list[str]]:
    """Import `flow.layout` netlists under `root` for the designs of the suite. Returns the count
    and the names found in the tree that the suite does not register."""
    suite = load_suites(idx).get(suite_id)
    flow = load_flows(idx).get(flow_id)
    if suite is None or flow is None or not flow.layout:
        raise BenchError(f"unknown suite {suite_id!r}, or flow {flow_id!r} without a layout")
    if suite.hosting != "public":
        raise BenchError(f"{suite_id}: hosting is {suite.hosting}; no netlist blobs imported")
    designs = {d.design: d for d in load_designs(idx) if d.suite == suite_id}
    glob, rx = _layout_regex(flow.layout)
    scrub, rows, skipped, n = _scrubber(ws), load_netlists(idx), [], 0
    for path in sorted(root.glob(glob)):
        m = rx.fullmatch(path.relative_to(root).as_posix())
        if not m:
            continue
        name = m.group("d")
        if name not in designs:
            skipped.append(name)
            continue
        rows = _upsert(rows, _import_one(store, suite, flow, designs[name], path, scrub, root))
        n += 1
    save_netlists(idx, rows)
    _set_tops(idx, suite_id, flow, root)
    return n, skipped


def _import_one(store: Path, suite: Suite, flow: Flow, design: Design, path: Path,
                scrub: Scrubber, root: Path) -> Netlist:
    data = path.read_bytes()
    note = ""
    if not check_clean(data.decode("utf-8", "replace")):
        text = scrub.text(data.decode("utf-8"))
        if not check_clean(text):
            raise BenchError(f"{path.name}: a /home path stays after scrubbing")
        data, note = text.encode("utf-8"), " (home paths tokenised $WS/$VTR_ROOT in net names)"
    rec = root / flow.record.replace("{d}", design.design) if flow.record else None
    return Netlist(suite.id, design.design, flow.id, blobs.put_bytes(store, data), len(data),
                   _store_text(store, Path(str(path) + ".names"), scrub),
                   _store_text(store, rec, scrub) if rec else NONE,
                   scrub.text(str(path)) + note)


def _set_tops(idx: Path, suite_id: str, flow: Flow, root: Path) -> None:
    if not flow.record:
        return
    designs = load_designs(idx)
    out = []
    for d in designs:
        rec = root / flow.record.replace("{d}", d.design)
        if d.suite == suite_id and d.top == NONE and rec.is_file():
            argv = json.loads(rec.read_text(encoding="utf-8")).get("argv", [])
            if "--top" in argv:
                d = replace(d, top=str(argv[argv.index("--top") + 1]))
        out.append(d)
    save_designs(idx, out)


# ---- build -------------------------------------------------------------------------------------

def build_netlist(idx: Path, store: Path, ref: str, flow_id: str, odin3: Path,
                  arch_dir: Path | None = None) -> Netlist:
    """Compile a registered source with a flow's `build` command; store the netlist, the name map
    and a flow record (flow id, binary sha256, argv) as blobs; upsert the netlists row."""
    from mimir.bench import resolve

    res = resolve(ref, idx)
    flow = load_flows(idx).get(flow_id)
    if flow is None or not flow.build:
        raise BenchError(f"flow {flow_id!r}: unknown or has no build command")
    if res.suite.hosting != "public":
        raise BenchError(f"{ref}: hosting is {res.suite.hosting}; build would store a blob")
    src = source_path(res.suite, res.design)
    if not src.is_file() or _sha(src.read_bytes()) != res.design.sha256:
        raise BenchError(f"{ref}: checkout source missing or changed: {src.name}")
    with tempfile.TemporaryDirectory(prefix="mimir-build-") as tmp:
        out = Path(tmp)
        top = f"--top {res.design.top}" if res.design.top != NONE else ""
        arch = str((arch_dir or Path()) / f"{flow.arch}.xml")
        cmd = flow.build.format(odin3=str(odin3), src=str(src), out=str(out), arch=arch,
                                design=res.design.design, top_args=top)
        argv = shlex.split(cmd)
        proc = subprocess.run(argv, capture_output=True, text=True, check=False)
        blif = out / f"{res.design.design}.blif"
        if proc.returncode != 0 or not blif.is_file():
            raise BenchError(f"{ref}: build failed (rc={proc.returncode}): {proc.stderr[-300:]}")
        rec = json.dumps({"flow": flow.id, "binary_sha256": _sha(odin3.read_bytes()),
                          "argv": [Path(a).name if Path(a).is_absolute() else a for a in argv]},
                         sort_keys=True, indent=1) + "\n"
        data = blif.read_bytes()
        names = out / f"{blif.name}.names"
        new = Netlist(res.suite.id, res.design.design, flow.id, blobs.put_bytes(store, data),
                      len(data),
                      blobs.put_bytes(store, names.read_bytes()) if names.is_file() else NONE,
                      blobs.put_bytes(store, rec.encode()), "mimir bench build")
    save_netlists(idx, _upsert(load_netlists(idx), new))
    return new
