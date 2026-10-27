"""Flow configurations and runs: the `flow_config`, `flow_param`, `run` tables.

The configurations of the imported data are rebuilt from what the runner scripts and plans state
(read only, cited in each config's `origin`). A parameter no source states is `unknown`; a
config with one is `partial`. Spec: docs/specs/2026-10-27-mimir-schema-v2.md, sections 3.4, 3.5, 6.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from mimir.importers.loki import find_datasets
from mimir.store import Store

VTR_COMMIT = "3c9a4d23b2"
ARCH = "k6_frac_N10_frac_chain_mem32K_40nm"
ARCH_REL = f"vtr_flow/arch/timing/{ARCH}.xml"
Param = tuple[str, str, str, str, str]  # (step, key, value, conf, source)

NORNS_R = "norns scripts/"  # origin prefix, relative to the Norns checkout
STD_PLACE_FLAGS = (
    "--write_initial_place_file <run>/initial.place --write_flat_place <run>/final.flat_place"
)
AFF = " --norns_affinity <file> --norns_affinity_weight"


@dataclass
class Spec:
    """One flow configuration: name, verbatim command text, parameter rows and where it is from."""

    name: str
    text: str
    origin: str
    params: list[Param] = field(default_factory=list)

    def add(self, step: str, key: str, value: str, conf: str, src: str) -> None:
        self.params.append((step, key, value, conf, src))

    def status(self) -> str:
        return "partial" if any(p[3] == "unknown" for p in self.params) else "full"

    def config_hash(self) -> str:
        blob = json.dumps([self.text, sorted(self.params)], sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()


# ---------------------------------------------------------------- Norns

ODIN_TEXT = (
    "odin3 -p \"read_arch <arch>; read_verilog --nolatches --vtr-compat <design>.v; proc; fsm; "
    "opt; flatten; opt -full; wreduce; hardmap; lower; abc --lut 6; stats; "
    "write_blif --vtr --lut-k 6 --name-style provenance <design>.blif\""
)
ODIN_SRC = "scripts/nornlib.py odin_script"
ROUND_FILES = {
    "norns-r1r2": "scripts/matrix.py:98-107, scripts/round2.py",
    "norns-r3": "scripts/round3.py:90-104, 264-290",
    "norns-r3-pilot": "scripts/round3.py:90-104, 184-190",
    "norns-r4": "scripts/round4.py:440-470",
    "norns-r5": "scripts/r5.py:92-125",
    "norns-r6": "scripts/r6.py:146-175",
    "norns-r7": "scripts/r7.py:70-95",
}
NPATHS = {"norns-r4": "1000", "norns-r5": "100", "norns-r6": "100", "norns-r7": "200"}


def _odin_params(spec: Spec, n5: bool) -> None:
    if n5:
        spec.add("odin", "synthesis", "none: netlist-level construction, no Verilog", "given",
                 "docs/plan/round7.md Stage 1 (calibration set)")
        return
    spec.add("odin", "synthesis", "odin3 script, see config text", "given", ODIN_SRC)
    spec.add("odin", "lut_k", "6", "given", ODIN_SRC)
    spec.add("odin", "name_style", "provenance", "given", ODIN_SRC)
    spec.add("odin", "abc_script", "Odin III abc pass default (abc_script option not given)",
             "default", ODIN_SRC)
    spec.add("odin", "odin3_commit", "", "unknown",
             "BLIFs of rounds 1-5 are reused; docs/plan/round6.md:19 names a1cf6ffd for the "
             "plugin only; the commit that wrote each BLIF is not recorded")


def _arch_params(spec: Spec, arch_sha: str | None) -> None:
    spec.add("arch", "arch", ARCH, "given", "scripts/nornlib.py ARCH")
    if arch_sha:
        spec.add("arch", "arch_file_sha256", arch_sha, "given",
                 f"sha256 of {ARCH_REL} in the VTR checkout at {VTR_COMMIT}")
    else:
        spec.add("arch", "arch_file_sha256", "", "unknown", "VTR checkout not available")


def _vpr_commit(spec: Spec, source: str) -> None:
    if source == "norns-r1r2":
        spec.add("pack", "vpr_commit", "", "unknown", "rounds 1-2 do not state the VTR commit")
    else:
        spec.add("pack", "vpr_commit", VTR_COMMIT, "given", "packer/VTR_COMMIT; round plans")


def _beta(arm_token: str) -> str | None:
    m = re.search(r"-b([0-9.]+)$", arm_token)
    return m.group(1) if m else None


def _scale(tag: str) -> str | None:
    m = re.search(r"-([0-9.]+)$", tag)
    return m.group(1) if m else None


def _place_default(spec: Spec, source: str) -> None:
    src = ROUND_FILES[source]
    if source == "norns-r3-pilot":
        spec.add("place", "flow", "pack and analytical placement only (--analytical_place)",
                 "given", src)
        spec.add("route", "route", "none", "given", src)
    else:
        spec.add("place", "flow", "default flow: analytical placement (lp-b2b, APPack), then "
                 "VPR annealing refinement", "given", "docs/plan/round7.md Common definitions")
        spec.add("route", "route", "VPR default, minimum channel width search", "given",
                 "docs/plan/round7.md Common definitions")
    if source in NPATHS:
        spec.add("place", "timing_report_npaths", NPATHS[source], "given", src)
    if source == "norns-r7":
        spec.add("route", "route_file", "/dev/null", "given", src)
    spec.add("pack", "allow_unrelated_clustering", "VPR default (flag not passed)", "default", src)


def _affinity(spec: Spec, kind: str, weight: str, count: str, src: str) -> None:
    spec.add("pack", "packer", "norns-vpr (affinity overlay)", "given", src)
    spec.add("pack", "norns_affinity_source", kind, "given", src)
    spec.add("pack", "norns_affinity_weight", weight, "given", src)
    if count:
        spec.add("pack", "norns_proposal_count", count, "given", src)


def _stock(spec: Spec, src: str) -> None:
    spec.add("pack", "packer", "vpr-stock", "given", src)


def _r12(spec: Spec, arm: str) -> str:
    head, _, tag = arm.partition("/")
    base = head.split("-")[0]
    cmd = ("vpr <arch> <design>.blif --seed 1 " + STD_PLACE_FLAGS
           + " --write_legalized_flat_place <run>/legalized.flat_place")
    _stock(spec, ROUND_FILES["norns-r1r2"])
    src = ROUND_FILES["norns-r1r2"]
    if base in ("cold", "hot", "soft"):
        cmd += " --read_initial_place_file <seed.place>"
        spec.add("place", "start", "read_initial_place_file", "given", src)
    if base == "hard":
        cmd += " --read_vpr_constraints <seed-hard.xml>"
        spec.add("place", "start", "read_vpr_constraints", "given", src)
    if base in ("cold", "hot", "unseeded"):
        sc = _scale(tag)
        cmd += " --anneal_auto_init_t_scale <scale>"
        if sc:
            spec.add("place", "anneal_auto_init_t_scale", sc, "given", src)
        else:
            spec.add("place", "anneal_auto_init_t_scale", "", "unknown", "scale not in the arm tag")
    if head.endswith("-off"):
        spec.add("place", "variant_off", "", "unknown", "the arm tag says -off; its meaning is "
                 "not stated in the scripts read")
    if head.endswith("-r2"):
        spec.add("place", "variant", "round 2 (words_partial family)", "given", "arm tag")
    return cmd


def _r3(spec: Spec, source: str, arm: str) -> str:
    src = ROUND_FILES[source]
    cmd = "vpr <arch> <design>.blif --seed <s> " + STD_PLACE_FLAGS
    pilot = source == "norns-r3-pilot"
    if pilot:
        cmd += " --analytical_place"
    name, _, start = arm.rpartition("/") if not pilot else (arm.split("/")[-1], "", "")
    stock = name in ("pilot-stock", "stock")
    m = re.match(r"(?:pilot-)?(.+)-b([0-9.]+)$", name)
    if stock or m is None:
        _stock(spec, src)
    else:
        _affinity(spec, m.group(1), m.group(2), "", src)
        cmd += " --norns_affinity <file> --norns_affinity_weight <beta>"
    if not pilot:
        seeded = start == "seed"
        start_kind = "read_initial_place_file" if seeded else "analytic"
        spec.add("place", "start", start_kind, "given", src)
        cmd += " --read_initial_place_file <seed.place>" if seeded else ""
    return cmd


def _r4(spec: Spec, arm: str) -> str:
    src = ROUND_FILES["norns-r4"]
    pack, _, start = arm.partition("/")
    cmd = ("vpr <arch> <design>.blif --seed <s> --timing_report_npaths 1000 " + STD_PLACE_FLAGS)
    if pack == "stock":
        _stock(spec, src)
    else:
        _affinity(spec, "word", "4", "queued", src)
        cmd += " --norns_affinity <file> --norns_affinity_weight 4 --norns_proposal_count queued"
    kind = "analytic" if start == "analytic" else f"read_initial_place_file ({start})"
    spec.add("place", "start", kind, "given", src)
    return cmd


def _r56(spec: Spec, source: str, arm: str) -> str:
    src = ROUND_FILES[source]
    cmd = (f"vpr <arch> <design>.blif --seed <s> --timing_report_npaths {NPATHS[source]} "
           + STD_PLACE_FLAGS)
    if arm == "stock":
        _stock(spec, src)
        return cmd
    weight = "100" if arm == "known" else ("4" if source == "norns-r6" or arm == "norns" else "")
    kind = "known" if arm == "known" else "word"
    _affinity(spec, kind, weight, "queued", src)
    return cmd + f"{AFF} {weight} --norns_proposal_count queued"


def _r7(spec: Spec, arm: str) -> str:
    src = ROUND_FILES["norns-r7"]
    cmd = ("vpr <arch> <design>.blif --seed <s> --timing_report_npaths 200 --route_file /dev/null "
           + STD_PLACE_FLAGS)
    if arm.startswith("net"):
        spec.add("pack", "packer", "none: clustering written by r7net, VPR run with --net_file",
                 "given", "scripts/r7net.py:524-526")
        spec.add("pack", "net_arm", arm, "given", "arm name")
        return "vpr <arch> <design>.blif --place --route --analysis --net_file <net> --seed <s> " \
               "--timing_report_npaths 200 --route_file /dev/null " + STD_PLACE_FLAGS
    if arm == "stock":
        _stock(spec, src)
        return cmd + " --norns_pack_census <run>/census.tsv"
    _affinity(spec, "known" if arm == "known" else "hindsight recluster", "100", "queued", src)
    return cmd + f"{AFF} 100 --norns_proposal_count queued"


def norns_spec(source: str, arm: str, n5: bool, arch_sha: str | None) -> Spec:
    """The flow configuration of a Norns run (source label as the importer wrote it)."""
    base = "norns-r7" if source == "wyrd-atlas-r7" else source
    spec = Spec(name=f"{base}/{arm}" + ("/n5" if n5 else ""), text="", origin=ROUND_FILES[base])
    _odin_params(spec, n5)
    _arch_params(spec, arch_sha)
    _vpr_commit(spec, base)
    if base == "norns-r1r2":
        cmd = _r12(spec, arm)
    elif base in ("norns-r3", "norns-r3-pilot"):
        cmd = _r3(spec, base, arm)
    elif base == "norns-r4":
        cmd = _r4(spec, arm)
    elif base == "norns-r7":
        cmd = _r7(spec, arm)
    else:
        cmd = _r56(spec, base, arm)
    _place_default(spec, base)
    spec.text = (cmd if n5 else ODIN_TEXT + "\n" + cmd)
    return spec


# ---------------------------------------------------------------- Loki

LOKI_SRC = "meta.json script of the floor"
_DESIGN_FILE = re.compile(r"(read_verilog[^;]*?)\s+\S+\.(sv|v)\b")


def loki_spec(floor: str, script: list[str], meta: dict[str, object]) -> Spec:
    """The flow configuration of one Loki floor, from the script its meta.json recorded."""
    lines = [_DESIGN_FILE.sub(r"\1 <design>.\2", ln) for ln in script]
    spec = Spec(name=f"loki/{floor}", text="\n".join(lines), origin="meta.json of the floor")
    arch = re.search(r"read_(?:arch|techlib) (\S+?);", lines[0] + ";") if lines else None
    named = arch is not None and not arch.group(1).startswith("<")
    spec.add("arch", "arch", arch.group(1) if arch and named else "",
             "given" if named else "unknown", LOKI_SRC)
    spec.add("odin", "passes", ";".join(ln.split(";")[-1].strip() for ln in lines), "given",
             LOKI_SRC)
    abc = [ln for ln in lines if ln.startswith("abc")]
    spec.add("abc", "abc_cmd", abc[0] if abc else "none", "given", LOKI_SRC)
    lut = re.search(r"--lut (\d+)", abc[0]) if abc else None
    spec.add("abc", "lut_k", lut.group(1) if lut else "", "given" if lut else "default", LOKI_SRC)
    spec.add("abc", "abc_script", "Odin III abc pass default (abc_script option not given)",
             "default", LOKI_SRC)
    spec.add("odin", "odin3_version", str(meta.get("odin3_version", "")),
             "given" if meta.get("odin3_version") else "unknown", "meta.json odin3_version")
    spec.add("odin", "abi_version", str(meta.get("abi_version", "")),
             "given" if meta.get("abi_version") is not None else "unknown", "meta.json abi_version")
    spec.add("odin", "odin3_commit", "", "unknown", "meta.json holds versions, not commits")
    return spec


def loki_runs(loki_root: Path) -> list[tuple[str, str, str, Spec]]:
    """(source, design, floor, spec) for every floor meta.json under the Loki sources."""
    out: list[tuple[str, str, str, Spec]] = []
    for sub in sorted(loki_root.glob("loki-*")):
        for ds in find_datasets(sub) if sub.is_dir() else []:
            source = "loki:" + ds.relative_to(loki_root).as_posix()
            for path in sorted(ds.glob("*/*/meta.json")):
                meta = json.loads(path.read_text(encoding="utf-8"))
                script = meta.get("script")
                if not isinstance(script, list):
                    continue
                floor = str(meta.get("floor", path.parent.name))
                out.append((source, path.parent.parent.name, floor, loki_spec(floor, script, meta)))
    return out


# ---------------------------------------------------------------- tables

def put_config(store: Store, spec: Spec) -> str:
    h = spec.config_hash()
    store.db.execute("INSERT OR REPLACE INTO flow_config VALUES (?, ?, ?, ?, ?)",
                     (h, spec.name, spec.text, spec.status(), spec.origin))
    store.db.execute("DELETE FROM flow_param WHERE config_hash = ?", (h,))
    store.db.executemany("INSERT OR REPLACE INTO flow_param VALUES (?, ?, ?, ?, ?, ?)",
                         [(h, *p) for p in spec.params])
    return h


def run_id_of(source: str, design: str, arch: str, seed: int, arm: str) -> str:
    key = "|".join((source, design, arch, str(seed), arm))
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _slug(store: Store, source: str, design: str) -> str:
    row = store.db.execute("SELECT slug FROM design_source WHERE source=? AND name=?",
                           (source, design)).fetchone()
    return str(row[0]) if row else ""


def _put_run(store: Store, key: tuple[str, str, str, int, str], family: str, config: str,
             commits: str, origin: str) -> None:
    source, design, arch, seed, arm = key
    rid = run_id_of(*key)
    store.db.execute(
        "INSERT OR REPLACE INTO run VALUES (?,?,?,?,?,?,?,?,?,?,NULL,NULL,NULL,NULL,?)",
        (rid, _slug(store, source, design), config, source, design, arch, seed, arm, family,
         commits, origin),
    )


def _fill_time_rss(store: Store) -> None:
    for col, metric in (("time_s", "vpr.flow_time"), ("peak_rss_mib", "vpr.max_rss")):
        store.db.execute(
            f"UPDATE run SET {col} = (SELECT MAX(r.value) FROM records r "
            "WHERE r.source = run.source "
            "AND r.design = run.design AND r.arch = run.arch AND r.seed = run.seed "
            "AND r.arm = run.arm AND r.metric = ?)", (metric,))


def import_runs(store: Store, arch_sha: str | None, loki_root: Path | None) -> dict[str, int]:
    """Create flow_config and run rows for the imported Norns and Loki data. Returns run counts
    per source. Needs the designs registered first (the run's slug comes from design_source)."""
    counts: dict[str, int] = {}
    cache: dict[tuple[str, str, bool], str] = {}
    try:
        groups = store.db.execute(
            "SELECT source, design, arch, seed, arm, MIN(family), MIN(tool_commit), MIN(origin) "
            "FROM records WHERE (source LIKE 'norns-r%' OR source = 'wyrd-atlas-r7') "
            "AND source != 'norns-r7-corpus' GROUP BY source, design, arch, seed, arm "
            "ORDER BY 1, 2, 3, 4, 5").fetchall()
        for source, design, arch, seed, arm, family, commit, origin in groups:
            n5 = design.startswith("n5_")
            ck = (source, arm, n5)
            if ck not in cache:
                cache[ck] = put_config(store, norns_spec(source, arm, n5, arch_sha))
            commits = f"vtr={commit}" if commit else ""
            _put_run(store, (source, design, arch, seed, arm), family, cache[ck], commits, origin)
            counts[source] = counts.get(source, 0) + 1
        if loki_root is not None:
            _import_loki_runs(store, loki_root, counts)
        _fill_time_rss(store)
        store.db.commit()
    except BaseException:
        store.db.rollback()
        raise
    return counts


def _import_loki_runs(store: Store, loki_root: Path, counts: dict[str, int]) -> None:
    cache: dict[str, str] = {}
    for source, design, floor, spec in loki_runs(loki_root):
        h = spec.config_hash()
        if h not in cache:
            cache[h] = put_config(store, spec)
        _put_run(store, (source, design, floor, -1, ""), "", h, "", f"{source}/{design}/{floor}")
        counts[source] = counts.get(source, 0) + 1


def config_coverage(store: Store) -> list[tuple[str, str, int, int]]:
    """(source, status, configs used, runs) over the runs, one row per source and status."""
    rows = store.db.execute(
        "SELECT u.source, c.status, COUNT(DISTINCT c.config_hash), COUNT(*) FROM run u "
        "JOIN flow_config c ON c.config_hash = u.config_hash GROUP BY 1, 2 ORDER BY 1, 2"
    ).fetchall()
    return [(a, b, int(c), int(d)) for a, b, c, d in rows]


def unknown_params(store: Store) -> list[tuple[str, str, int]]:
    """(step.key, source group, configs) for every parameter that is unknown."""
    rows = store.db.execute(
        "SELECT p.step || '.' || p.key, substr(c.name, 1, instr(c.name || '/', '/') - 1), "
        "COUNT(DISTINCT c.config_hash) FROM flow_param p JOIN flow_config c "
        "ON c.config_hash = p.config_hash WHERE p.conf = 'unknown' GROUP BY 1, 2 ORDER BY 1, 2"
    ).fetchall()
    return [(a, b, int(c)) for a, b, c in rows]
