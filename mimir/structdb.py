"""Import one flow output directory into the store: design, flow_config, run, run_artifact, the
structures (from the HDL) and their mapping rows. Spec: docs/specs/2026-10-27-mimir-structures.md.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mimir.blif import parse_models
from mimir.blobs import put_bytes
from mimir.flowcfg import put_config, run_id_of
from mimir.flowspec import Spec, add_found, option_default
from mimir.schema import Record
from mimir.scrub import Scrubber, check_clean
from mimir.store import Store
from mimir.structmap import Analysis, Deps, MapRow, Struct, analyse, atoms_from_blif

SOURCE = "mimir-structures"
MEASURER = "structures"
ODIN_SCRIPT = re.compile(r"^\$ (\S+/odin3) (.*)$")
_ABC = re.compile(r"# abc: script=(\S+) sha256=(\w+) abc=(\w+) K=(\d+)")
_SHA40 = re.compile(r"[0-9a-f]{40}")
_OPT = re.compile(r"^(\w[\w.]*)\s*:\s*(.*)$")
_CHAN = re.compile(r"(--route_chan_width\s+)\d+")
VPR_OPTIONS_HEAD = "VPR was run with the following options:"
VPR_CMD_HEAD = "VPR was run with the following command-line:"
SEED_SOURCE = "vpr/src/base/read_options.cpp"


@dataclass(frozen=True)
class DesignInfo:
    """The design a flow dir belongs to: slug, short name, suite, defining files."""

    slug: str
    name: str
    suite: str
    files: tuple[Path, ...]


def commit_or_unknown(value: object) -> str:
    """A commit as stored: the 40-hex SHA, else `unknown` (an odd text is never `given`)."""
    text = str(value)
    return text if _SHA40.fullmatch(text) else "unknown"


def read_vpr_log(path: Path) -> tuple[str, int, dict[str, tuple[str, int]]]:
    """(command line, its line number, {option: (value, line number)}) of a VPR stdout log: the
    line after "VPR was run with the following command-line:" and the "key : value" lines after
    "VPR was run with the following options:" up to the next blank-then-text line that is not an
    option. Raises ValueError when either block is missing."""
    lines = path.read_text(encoding="utf-8", errors="replace").split("\n")
    try:
        ci = lines.index(VPR_CMD_HEAD)
        oi = lines.index(VPR_OPTIONS_HEAD)
    except ValueError as exc:
        raise ValueError(f"{path}: no VPR command-line or options block") from exc
    opts: dict[str, tuple[str, int]] = {}
    for n in range(oi + 1, len(lines)):
        m = _OPT.match(lines[n])
        if m:
            opts[m.group(1)] = (m.group(2).strip(), n + 1)
        elif lines[n].strip() and not lines[n].startswith(" "):
            break
    if not opts:
        raise ValueError(f"{path}: empty VPR options block")
    return lines[ci + 1].strip(), ci + 2, opts


def _first_line(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").split("\n", 1)[0]


def build_spec(flow_dir: Path, info: dict[str, Any], scrub: Scrubber, name: str,
               vtr_root: Path | None = None) -> Spec:
    """The flow configuration of one run, every parameter from a recorded line of the run itself
    (command, logs, BLIF header, VPR's own options block). Paths and the design name become
    placeholders so that the runs of one setup share one config. The VPR seed is recorded by VPR
    (`placer_opts.seed`) and cross-checked with VTR's default read from `vtr_root` at the run's
    VTR commit (read only); without that checkout the default is `default-unrecorded` and the
    config is `partial`."""
    top = str(info["top"])
    run_dir = str(info.get("run_dir", "vpr/run"))

    files = sorted((scrub.text(str(f)) for f in info["design_files"]), key=len, reverse=True)

    def norm(text: str) -> str:
        t = scrub.text(text)
        for f in files:
            t = t.replace(f, "<design_file>")
        t = re.sub(rf"(?<![\w-]){re.escape(top)}(?!\w)", "<design>", t)
        return t.replace(scrub.text(str(flow_dir)), "<out>")

    odin_line = _first_line(next(flow_dir.glob("odin3/odin3.log")))
    m = ODIN_SCRIPT.match(odin_line)
    script = norm(m.group(2)) if m else norm(odin_line)
    blif = next(flow_dir.glob("odin3/*.blif"))
    abc = _ABC.search(blif.read_text(encoding="utf-8"))
    vpr_log = (flow_dir / "vpr" / "vpr.log").read_text(encoding="utf-8").split("\n")
    vcmd = next(norm(ln) for ln in vpr_log if ln.startswith("$ "))
    flow_cmd = norm(" ".join(info["commands"][0]))
    post_argv = list(info["commands"][1])
    if "--run-dir" in post_argv:  # where the retry left its files is not a configuration choice
        i = post_argv.index("--run-dir")
        del post_argv[i:i + 2]
    post = norm(" ".join(post_argv))
    spec = Spec(name=name, text=f"{flow_cmd}\nodin3 {script}\n{vcmd}\n{post}",
                origin="mimir-run.json commands; odin3/odin3.log:1; vpr/vpr.log vpr command",
                text_kind="recorded-normalised")
    src_odin, src_cmd = "odin3/odin3.log:1", "mimir-run.json commands[0]"
    commit = commit_or_unknown(info["odin3_commit"])
    built = commit != "unknown" and bool(info.get("odin3_built_from_tree"))
    spec.add("odin", "odin3_commit", commit if commit != "unknown" else "", "given" if built
             else "unknown", "mimir-run.json odin3_commit (HEAD of the tree; tree clean, build "
             "dir configured from it, binary newer than the commit)" if built else
             "inferred: HEAD of the tree, but the tree is dirty, the build dir is not its own, "
             "or the binary is older than the commit (mimir-run.json odin3_build_check)")
    spec.add("odin", "binary_sha256", str(info.get("odin3_binary_sha256", "")), "given",
             "mimir-run.json odin3_binary_sha256")
    spec.add("odin", "binary_version", str(info.get("odin3_binary_version", "")).replace(
        "\n", " | "), "given", "mimir-run.json odin3_binary_version (odin3 --version)")
    spec.add("odin", "script", script, "given", src_odin)
    spec.add("odin", "flow_options", norm(" ".join(info["commands"][0][1:])), "given", src_cmd)
    if abc:
        spec.add("abc", "abc_script", abc.group(1), "given", "odin3/*.blif header line 2")
        spec.add("abc", "abc_script_sha256", abc.group(2), "given", "odin3/*.blif header line 2")
        spec.add("abc", "abc_commit", abc.group(3), "given", "odin3/*.blif header line 2")
        spec.add("abc", "lut_k", abc.group(4), "given", "odin3/*.blif header line 2")
    arch = norm(Path(next((a for a in vcmd.split() if a.endswith(".xml")), "")).name)
    spec.add("arch", "arch_file", arch, "given", "vpr/vpr.log:1 (run_vtr_flow arguments)")
    vtr = commit_or_unknown(info["vtr_commit"])
    spec.add("pack", "vtr_commit", vtr if vtr != "unknown" else "", "given" if vtr != "unknown"
             else "unknown", "mimir-run.json vtr_commit" if vtr != "unknown" else
             "mimir-run.json vtr_commit is not a SHA")
    cmd, cmd_line, opts = read_vpr_log(flow_dir / run_dir / "vpr_stdout.log")
    log = f"{run_dir}/vpr_stdout.log"
    for step in ("pack", "place", "route"):
        spec.add(step, "vpr_driver_command", vcmd, "given", "vpr/vpr.log:1")
    spec.add("route", "vpr_command_line", _CHAN.sub(r"\g<1><W>", norm(cmd)), "given",
             f"{log}:{cmd_line}")
    for key, (value, line) in sorted(opts.items()):
        spec.add("vpr", key, value or "(empty)", "given", f"{log}:{line}")
    found = (option_default(vtr_root, vtr, SEED_SOURCE, "--seed")
             if vtr_root is not None and vtr != "unknown" else None)
    add_found(spec, "place", "seed_default", found, vtr_root, vtr, "vtr",
              "VTR checkout or its recorded commit not available")
    if "placer_opts.seed" not in opts:
        spec.add("place", "seed", "", "default-unrecorded",
                 f"{log} has no placer_opts.seed: the placement of this run is VPR's analytical "
                 "placer (a route retry); its annealer seed is not recorded")
    spec.add("route", "post_step", norm(" ".join(post_argv[1:])), "given",
             "mimir-run.json commands[1]")
    return spec


def _log_blob(flow_dir: Path, scrub: Scrubber, run_dir: str) -> bytes:
    parts = []
    for pat in ("odin3/odin3.log", "odin3/*.names.log", "vpr/vpr.log", f"{run_dir}/vpr_stdout.log",
                "summary.json", "mimir-run.json", "timing/timing.log"):
        for f in sorted(flow_dir.glob(pat)):
            parts.append(f"=== {f.relative_to(flow_dir)}\n"
                         + scrub.text(f.read_text(encoding="utf-8", errors="replace")))
    return "\n".join(parts).encode()


def _put_clean(blobs: Path, kind: str, text: str) -> str:
    """Store `text` (already scrubbed) as a blob after checking that no home path is left."""
    if not check_clean(text):
        raise ValueError(f"{kind} blob still holds a home path")
    return put_bytes(blobs, text.encode())


def store_artifacts(store: Store, blobs: Path, run_id: str, flow_dir: Path,
                    scrub: Scrubber, run_dir: str = "vpr/run",
                    design_files: Iterable[Path] = ()) -> dict[str, str]:
    """Scrub and compress the run's artifacts into the blob store; fill `run_artifact`. Every
    blob is checked for a home path before it is written."""
    run = flow_dir / run_dir
    files = {"blif": next(flow_dir.glob("odin3/*.blif")),
             "map": next(flow_dir.glob("odin3/*.blif.names"))}
    for kind, pat in (("net", "*.net"), ("place", "*.place"), ("route", "*.route")):
        hit = sorted(p for p in run.glob(pat) if ".post_routing" not in p.name
                     and "pre-vpr" not in p.name)
        if hit:
            files[kind] = hit[0]
    attribution = flow_dir / "timing" / "attribution.json"
    if attribution.is_file():
        files["timing"] = attribution
    got = {}
    for kind, path in sorted(files.items()):
        got[kind] = _put_clean(blobs, kind, scrub.text(
            path.read_text(encoding="utf-8", errors="replace")))
    got["log"] = _put_clean(blobs, "log", _log_blob(flow_dir, scrub, run_dir).decode())
    hdl = "\n".join(f"=== {scrub.path(str(f))}\n" + f.read_text(encoding="utf-8", errors="replace")
                    for f in design_files)
    if hdl:
        got["hdl"] = _put_clean(blobs, "hdl", scrub.text(hdl))
    store.db.execute("DELETE FROM run_artifact WHERE run_id = ?", (run_id,))
    store.db.executemany("INSERT INTO run_artifact VALUES (?, ?, ?)",
                         [(run_id, k, v) for k, v in sorted(got.items())])
    return got


def files_sha256(files: Iterable[Path]) -> str:
    h = hashlib.sha256()
    for f in files:
        h.update(f.read_bytes())
    return h.hexdigest()


def put_design(store: Store, d: DesignInfo, scrub: Scrubber) -> str:
    digest = files_sha256(d.files)
    origin = scrub.path(str(d.files[0]))
    store.db.execute("INSERT OR REPLACE INTO design VALUES (?, ?, ?, ?, ?, ?)",
                     (d.slug, digest, "hdl", d.suite, d.name, origin))
    return digest


def vpr_facts(flow_dir: Path, info: dict[str, Any]) -> tuple[str, int]:
    """(architecture file name, placement seed) of a run, from VPR's own recorded lines: the arch
    from the driver command in `vpr/vpr.log`, the seed from `placer_opts.seed` of the options block
    of the run directory. The seed is -1 when the run directory has none (the analytical placer of
    a route retry; the flow config then holds `place.seed` as `default-unrecorded`). Raises
    ValueError when the architecture is not recorded."""
    log = (flow_dir / "vpr" / "vpr.log").read_text(encoding="utf-8").split("\n")
    cmd = next((ln for ln in log if ln.startswith("$ ")), "")
    arch = next((Path(a).name for a in cmd.split() if a.endswith(".xml")), "")
    _, _, opts = read_vpr_log(flow_dir / str(info.get("run_dir", "vpr/run")) / "vpr_stdout.log")
    if not arch:
        raise ValueError(f"{flow_dir}: the architecture is not recorded")
    return arch, int(opts["placer_opts.seed"][0]) if "placer_opts.seed" in opts else -1


def put_run(store: Store, d: DesignInfo, info: dict[str, Any], config: str, input_sha: str,
            scrub: Scrubber, flow_dir: Path) -> str:
    arch, seed = vpr_facts(flow_dir, info)
    commit = commit_or_unknown(info["odin3_commit"])
    rid = run_id_of(SOURCE, d.name, arch, seed, "", config, commit, input_sha)
    cmd = " && ".join(scrub.text(" ".join(c)) for c in info["commands"])
    store.db.execute(
        "INSERT OR REPLACE INTO run (run_id, slug, config_hash, source, design, arch, seed, arm, "
        "family, tool_commits, command_line, time_s, peak_rss_mib, host, origin, tool_commit, "
        "input_sha256) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (rid, d.slug, config, SOURCE, d.name, arch, seed, "", "",
         f"odin3={commit};vtr={commit_or_unknown(info['vtr_commit'])}", cmd, info["time_s"],
         info["peak_rss_mib"], f"{info['host']} {info['kernel']} {info['started_utc']}",
         scrub.text(str(flow_dir)), commit, input_sha))
    return rid


def _row_values(d: str, rid: str, cfg: str, r: MapRow) -> tuple[Any, ...]:
    box = r.bbox or (None, None, None, None)
    return (d, r.sid, rid, r.level, cfg, r.n_objects, r.n_pure, r.n_shared, r.n_gates, r.n_luts,
            r.n_carry, r.n_ffs, r.n_bles, r.n_clbs, r.n_sites, r.joined_with, r.lost_at_pass,
            *box, r.spread, r.crit_share)


def clear_structures(store: Store, slug: str, detector: bool) -> None:
    """Delete the structure, member and mapping rows of a design of one label source (`hdl`, or
    `detector:%`), so a re-import leaves no row of an earlier run behind."""
    like = "detector:%" if detector else "hdl"
    op = "LIKE" if detector else "="
    ids = f"SELECT structure_id FROM structure WHERE design = ? AND label_source {op} ?"
    for table in ("structure_member", "structure_mapping"):
        store.db.execute(f"DELETE FROM {table} WHERE design = ? AND structure_id IN ({ids})",
                         (slug, slug, like))
    store.db.execute(f"DELETE FROM structure WHERE design = ? AND label_source {op} ?",
                     (slug, like))


def put_structures(store: Store, slug: str, rid: str, cfg: str, structs: Iterable[Struct],
                   rows: Iterable[MapRow], members: Mapping[str, Iterable[str]]) -> None:
    """Write structure, structure_member and structure_mapping rows of one run (replacing the
    rows of the same keys; `members` are keyed by the run)."""
    store.db.executemany(
        "INSERT OR REPLACE INTO structure VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [(slug, s.sid, s.kind, s.span, s.chain, s.source, s.conf, rid, cfg,
          s.granularity if s.source == "hdl" else "", s.parent) for s in structs])
    store.db.executemany("INSERT OR REPLACE INTO structure_member VALUES (?,?,?,?)",
                         [(slug, sid, rid, a) for sid, atoms in sorted(members.items())
                          for a in sorted(atoms)])
    store.db.executemany(
        "INSERT OR REPLACE INTO structure_mapping VALUES (" + ",".join("?" * 23) + ")",
        [_row_values(slug, rid, cfg, r) for r in rows])


def l15_records(d: DesignInfo, rid_arch: str, seed: int, commit: str, sha: str, rid: str,
                a: Analysis) -> list[Record]:
    blocks = [s for s in a.structs if s.granularity == "block"]
    pure = len({r.sid for r in a.rows if r.level == "lut" and r.n_pure > 0
                and not r.sid.endswith(":op")})
    vals = {"structure.blocks_reached": len(blocks), "structure.blocks_separable": pure,
            "structure.operators_reached": len(a.structs) - len(blocks),
            "structure.blocks_unknown": a.unknown_structs,
            "structure.gate_only_structures": a.gate_only,
            "structure.l15_units_reached": a.l15_units,
            "structure.l15_units_separable": a.l15_separable,
            "structure.atoms_unattributed": a.unattributed}
    return [Record(d.name, SOURCE, sha, commit, "", "lut", rid_arch, seed, "", "", k, "", float(v),
                   "count", MEASURER, "1", rid) for k, v in sorted(vals.items())]


def crit_shares(flow_dir: Path, members: Mapping[str, set[str]]) -> dict[str, float]:
    """Share of the critical path's data delay carried by each structure's atoms: the sum of the
    `delay_ns` of the nodes of path 1 of `timing/attribution.json` whose atom is a member, over
    `timing.critical_data_delay_ns`. Shares of structures that share atoms overlap. Empty when the
    run has no attribution."""
    f = flow_dir / "timing" / "attribution.json"
    if not f.is_file():
        return {}
    data = json.loads(f.read_text(encoding="utf-8"))
    total = data["timing"].get("critical_data_delay_ns")
    paths = data.get("paths") or []
    if not total or not paths:
        return {}
    delay: dict[str, float] = {}
    for node in paths[0]["nodes"]:
        delay[node["atom"]] = delay.get(node["atom"], 0.0) + float(node["delay_ns"])
    return {sid: round(sum(delay.get(a, 0.0) for a in atoms) / total, 6)
            for sid, atoms in members.items()}


def source_texts(info: dict[str, Any], files: Iterable[str]) -> dict[str, str]:
    """The text of each source file the map lists, read from disk after its sha256 is checked
    against the one recorded when the run ended (`source_sha256` in mimir-run.json). A file that
    changed is refused (ValueError); a file with no recorded sha has no text."""
    recorded: dict[str, str] = info.get("source_sha256", {})
    out: dict[str, str] = {}
    for f in files:
        if f not in recorded:
            continue
        data = Path(f).read_bytes()
        if hashlib.sha256(data).hexdigest() != recorded[f]:
            raise ValueError(f"{f}: changed since the run (sha256 differs from mimir-run.json)")
        out[f] = data.decode("utf-8", errors="replace")
    return out


def check_hdl_files(info: dict[str, Any], d: DesignInfo) -> None:
    """Refuse an import when the design files on disk are not the ones the run read."""
    recorded = info.get("design_sha256")
    if not recorded or files_sha256(d.files) != recorded:
        raise ValueError(f"{d.slug}: the design files differ from the ones the run read "
                         f"(sha256 recorded in mimir-run.json: {recorded or 'none'})")


def import_flow_dir(store: Store, blobs: Path, flow_dir: Path, d: DesignInfo, deps: Deps,
                    scrub: Scrubber, config_name: str, vtr_root: Path | None = None) -> str:
    """Import one flow dir (a run that passed): returns the run id. Raises ValueError when the
    run did not finish or the design files changed. The flow config is stored as it is: `full` or
    `partial` (a parameter with no cited value), never relabelled. The design's old
    HDL and detector rows are replaced (the detector rows name the flow run, so a new flow run
    makes them stale)."""
    info = json.loads((flow_dir / "mimir-run.json").read_text(encoding="utf-8"))
    if not info["ok"]:
        raise ValueError(f"{flow_dir}: the run did not finish")
    check_hdl_files(info, d)
    spec = build_spec(flow_dir, info, scrub, config_name, vtr_root)
    try:
        cfg = put_config(store, spec)
        sha = put_design(store, d, scrub)
        rid = put_run(store, d, info, cfg, sha, scrub, flow_dir)
        store_artifacts(store, blobs, rid, flow_dir, scrub, info.get("run_dir", "vpr/run"),
                        d.files)
        nm = deps.nmv2.read_name_map(next(flow_dir.glob("odin3/*.blif.names")))
        models = parse_models(next(flow_dir.glob("odin3/*.blif")).read_text(encoding="utf-8"))
        atoms = atoms_from_blif(models, lambda n: nm.atom(n) is not None)
        texts = source_texts(info, nm.files)
        a = analyse(nm, deps, atoms, texts, scrub.path)
        members: dict[str, set[str]] = {}
        for atom, sids in a.atom_structs.items():
            for sid in sids:
                members.setdefault(sid, set()).add(atom)
        for sid, share in crit_shares(flow_dir, members).items():
            for row in a.rows:
                if row.sid == sid and row.level == "lut":
                    row.crit_share = share
        clear_structures(store, d.slug, detector=False)
        clear_structures(store, d.slug, detector=True)
        put_structures(store, d.slug, rid, cfg, a.structs, a.rows, members)
        arch, seed = vpr_facts(flow_dir, info)
        store.add(l15_records(d, arch, seed, commit_or_unknown(info["odin3_commit"]), sha, rid, a))
        store.db.commit()
    except BaseException:
        store.db.rollback()
        raise
    return rid
