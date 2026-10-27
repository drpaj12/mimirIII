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
from mimir.flowspec import Spec
from mimir.schema import Record
from mimir.scrub import Scrubber, check_clean
from mimir.store import Store
from mimir.structmap import Analysis, Deps, MapRow, Struct, analyse, atoms_from_blif

SOURCE = "mimir-structures"
MEASURER = "structures"
ODIN_SCRIPT = re.compile(r"^\$ (\S+/odin3) (.*)$")
_ABC = re.compile(r"# abc: script=(\S+) sha256=(\w+) abc=(\w+) K=(\d+)")


@dataclass(frozen=True)
class DesignInfo:
    """The design a flow dir belongs to: slug, short name, suite, defining files."""

    slug: str
    name: str
    suite: str
    files: tuple[Path, ...]


def _first_line(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").split("\n", 1)[0]


def build_spec(flow_dir: Path, info: dict[str, Any], scrub: Scrubber, name: str) -> Spec:
    """The flow configuration of one run, every parameter from a recorded line of the run itself
    (command, logs, BLIF header). Paths and the design name become placeholders so that the runs
    of one setup share one config."""
    top = str(info["top"])

    def norm(text: str) -> str:
        t = scrub.text(text).replace(top, "<design>")
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
    spec.add("odin", "odin3_commit", str(info["odin3_commit"]), "given",
             "mimir-run.json odin3_commit")
    spec.add("odin", "script", script, "given", src_odin)
    spec.add("odin", "flow_options", norm(" ".join(info["commands"][0][1:])), "given", src_cmd)
    if abc:
        spec.add("abc", "abc_script", abc.group(1), "given", "odin3/*.blif header line 2")
        spec.add("abc", "abc_script_sha256", abc.group(2), "given", "odin3/*.blif header line 2")
        spec.add("abc", "abc_commit", abc.group(3), "given", "odin3/*.blif header line 2")
        spec.add("abc", "lut_k", abc.group(4), "given", "odin3/*.blif header line 2")
    arch = norm(Path(next((a for a in vcmd.split() if a.endswith(".xml")), "")).name)
    spec.add("arch", "arch_file", arch, "given", "vpr/vpr.log:1 (run_vtr_flow arguments)")
    spec.add("pack", "vtr_commit", str(info["vtr_commit"]), "given", "mimir-run.json vtr_commit")
    for step in ("pack", "place", "route"):
        spec.add(step, "vpr_driver_command", vcmd, "given", "vpr/vpr.log:1")
    spec.add("route", "post_step", norm(" ".join(post_argv[1:])), "given",
             "mimir-run.json commands[1]")
    return spec


def _log_blob(flow_dir: Path, scrub: Scrubber) -> bytes:
    parts = []
    for pat in ("odin3/odin3.log", "odin3/*.names.log", "vpr/vpr.log", "summary.json",
                "mimir-run.json"):
        for f in sorted(flow_dir.glob(pat)):
            parts.append(f"=== {f.relative_to(flow_dir)}\n"
                         + scrub.text(f.read_text(encoding="utf-8", errors="replace")))
    return "\n".join(parts).encode()


def store_artifacts(store: Store, blobs: Path, run_id: str, flow_dir: Path,
                    scrub: Scrubber, run_dir: str = "vpr/run") -> dict[str, str]:
    """Scrub and compress the run's artifacts into the blob store; fill `run_artifact`."""
    run = flow_dir / run_dir
    files = {"blif": next(flow_dir.glob("odin3/*.blif")),
             "map": next(flow_dir.glob("odin3/*.blif.names"))}
    for kind, pat in (("net", "*.net"), ("place", "*.place"), ("route", "*.route")):
        hit = sorted(p for p in run.glob(pat) if ".post_routing" not in p.name
                     and "pre-vpr" not in p.name)
        if hit:
            files[kind] = hit[0]
    got = {}
    for kind, path in sorted(files.items()):
        text = scrub.text(path.read_text(encoding="utf-8", errors="replace"))
        got[kind] = put_bytes(blobs, text.encode())
    log = _log_blob(flow_dir, scrub)
    if not check_clean(log.decode()):
        raise ValueError("log blob still holds a home path")
    got["log"] = put_bytes(blobs, log)
    store.db.execute("DELETE FROM run_artifact WHERE run_id = ?", (run_id,))
    store.db.executemany("INSERT INTO run_artifact VALUES (?, ?, ?)",
                         [(run_id, k, v) for k, v in sorted(got.items())])
    return got


def put_design(store: Store, d: DesignInfo, scrub: Scrubber) -> str:
    h = hashlib.sha256()
    for f in d.files:
        h.update(f.read_bytes())
    origin = scrub.path(str(d.files[0]))
    store.db.execute("INSERT OR REPLACE INTO design VALUES (?, ?, ?, ?, ?, ?)",
                     (d.slug, h.hexdigest(), "hdl", d.suite, d.name, origin))
    return h.hexdigest()


def put_run(store: Store, d: DesignInfo, info: dict[str, Any], config: str, input_sha: str,
            scrub: Scrubber, flow_dir: Path) -> str:
    arch = Path(next((a for a in info["commands"][0] if a.endswith(".xml")), "")).name \
        or "k6_frac_N10_frac_chain_mem32K_40nm.xml"
    commit = str(info["odin3_commit"])
    rid = run_id_of(SOURCE, d.name, arch, -1, "", config, commit, input_sha)
    cmd = " && ".join(scrub.text(" ".join(c)) for c in info["commands"])
    store.db.execute(
        "INSERT OR REPLACE INTO run (run_id, slug, config_hash, source, design, arch, seed, arm, "
        "family, tool_commits, command_line, time_s, peak_rss_mib, host, origin, tool_commit, "
        "input_sha256) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (rid, d.slug, config, SOURCE, d.name, arch, -1, "", "",
         f"odin3={commit};vtr={info['vtr_commit']}", cmd, info["time_s"], info["peak_rss_mib"],
         f"{info['host']} {info['kernel']} {info['started_utc']}",
         scrub.text(str(flow_dir)), commit, input_sha))
    return rid


def _row_values(d: str, rid: str, cfg: str, r: MapRow) -> tuple[Any, ...]:
    box = r.bbox or (None, None, None, None)
    return (d, r.sid, rid, r.level, cfg, r.n_objects, r.n_pure, r.n_shared, r.n_gates, r.n_luts,
            r.n_carry, r.n_ffs, r.n_bles, r.n_clbs, r.joined_with, r.lost_at_pass, *box, r.spread,
            r.crit_share)


def put_structures(store: Store, slug: str, rid: str, cfg: str, structs: Iterable[Struct],
                   rows: Iterable[MapRow], members: Mapping[str, Iterable[str]]) -> None:
    """Write structure, structure_member and structure_mapping rows of one run (replacing the
    rows of the same keys)."""
    store.db.executemany(
        "INSERT OR REPLACE INTO structure VALUES (?,?,?,?,?,?,?,?,?)",
        [(slug, s.sid, s.kind, s.span, s.chain, s.source, s.conf, rid, cfg) for s in structs])
    store.db.executemany("INSERT OR REPLACE INTO structure_member VALUES (?,?,?)",
                         [(slug, sid, a) for sid, atoms in sorted(members.items())
                          for a in sorted(atoms)])
    store.db.executemany(
        "INSERT OR REPLACE INTO structure_mapping VALUES (" + ",".join("?" * 22) + ")",
        [_row_values(slug, rid, cfg, r) for r in rows])


def l15_records(d: DesignInfo, rid_arch: str, commit: str, sha: str, rid: str,
                a: Analysis) -> list[Record]:
    blocks = len(a.structs)
    pure = len({r.sid for r in a.rows if r.level == "lut" and r.n_pure > 0})
    vals = {"structure.blocks_reached": blocks, "structure.blocks_separable": pure,
            "structure.l15_units_reached": a.l15_units,
            "structure.l15_units_separable": a.l15_separable,
            "structure.atoms_unattributed": a.unattributed}
    return [Record(d.name, SOURCE, sha, commit, "", "lut", rid_arch, -1, "", "", k, "", float(v),
                   "count", MEASURER, "1", rid) for k, v in sorted(vals.items())]


def import_flow_dir(store: Store, blobs: Path, flow_dir: Path, d: DesignInfo, deps: Deps,
                    scrub: Scrubber, config_name: str) -> str:
    """Import one flow dir (a run that passed): returns the run id. Raises ValueError when the
    run did not finish, or its config is not `full`."""
    info = json.loads((flow_dir / "mimir-run.json").read_text(encoding="utf-8"))
    if not info["ok"]:
        raise ValueError(f"{flow_dir}: the run did not finish")
    spec = build_spec(flow_dir, info, scrub, config_name)
    if spec.status() != "full":
        raise ValueError(f"{flow_dir}: flow config is {spec.status()}")
    try:
        cfg = put_config(store, spec)
        sha = put_design(store, d, scrub)
        rid = put_run(store, d, info, cfg, sha, scrub, flow_dir)
        store_artifacts(store, blobs, rid, flow_dir, scrub, info.get("run_dir", "vpr/run"))
        map_path = next(flow_dir.glob("odin3/*.blif.names"))
        nm = deps.nmv2.read_name_map(map_path)
        models = parse_models(next(flow_dir.glob("odin3/*.blif")).read_text(encoding="utf-8"))
        atoms = atoms_from_blif(models, lambda n: nm.atom(n) is not None)
        texts = {f: Path(f).read_text(encoding="utf-8", errors="replace") for f in nm.files
                 if Path(f).is_file()}
        a = analyse(nm, deps, atoms, texts, scrub.path)
        members: dict[str, set[str]] = {}
        for atom, sids in a.atom_structs.items():
            for sid in sids:
                members.setdefault(sid, set()).add(atom)
        put_structures(store, d.slug, rid, cfg, a.structs, a.rows, members)
        arch = store.db.execute("SELECT arch FROM run WHERE run_id=?", (rid,)).fetchone()[0]
        store.add(l15_records(d, arch, str(info["odin3_commit"]), sha, rid, a))
        store.db.commit()
    except BaseException:
        store.db.rollback()
        raise
    return rid
