"""Import of the Norns III data (read only): rounds 1-7 per-run metrics and the round 7 corpus."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

from mimir.importers.common import Ctx, Report
from mimir.schema import Record

MEASURER = "import-norns"
VERSION = "1"
ARCH = "k6_frac_N10_frac_chain_mem32K_40nm"
VTR_COMMIT = "3c9a4d23b2"  # documented in the round 3-7 plans; rounds 1-2 do not state it

# field -> (metric, level)
FIELDS: dict[str, tuple[str, str]] = {
    "wirelength": ("vpr.wirelength", "routed"),
    "chan_width": ("vpr.chan_width", "routed"),
    "cpd_ns": ("vpr.cpd", "routed"),
    "worst_slack_ns": ("vpr.worst_slack", "routed"),
    "route_s": ("vpr.route_time", "routed"),
    "flow_s": ("vpr.flow_time", "routed"),
    "max_rss_mib": ("vpr.max_rss", "routed"),
    "paths_in_report": ("vpr.paths_in_report", "routed"),
    "rc": ("vpr.rc", "routed"),
    "pack_s": ("vpr.pack_time", "clb"),
    "logic_clbs": ("vpr.logic_clbs", "clb"),
    "clbs": ("vpr.blocks", "clb"),
    "place_s": ("vpr.place_time", "placed"),
    "bb_final": ("vpr.bb_cost_final", "placed"),
    "bb_initial": ("vpr.bb_cost_initial", "placed"),
    "n_temperatures": ("vpr.n_temperatures", "placed"),
    "init_t": ("vpr.init_t", "placed"),
    "device_utilization": ("vpr.device_utilization", "placed"),
    "attr_cpd_ns": ("norns.attr_cpd", "routed"),
    "paths_skipped": ("norns.paths_skipped", "routed"),
    "critical_matched_delay_share": ("norns.critical_matched_delay_share", "routed"),
    "purity": ("norns.purity", "clb"),
    "null_purity": ("norns.null_purity", "clb"),
    "null_purity_max": ("norns.null_purity_max", "clb"),
    "reproduction": ("norns.reproduction", "clb"),
    "cut": ("norns.cut", "clb"),
    "exact_blocks": ("norns.exact_blocks", "clb"),
    "labelled_in_logic": ("norns.labelled_in_logic", "clb"),
    "matched_share": ("norns.matched_share", "placed"),
    "matched_share_excl_port": ("norns.matched_share_excl_port", "placed"),
    "retention": ("norns.retention", "placed"),
    "displacement": ("norns.displacement", "placed"),
    "scale": ("norns.scale", "placed"),
    "beta": ("norns.beta", "placed"),
    "objective": ("norns.objective", "routed"),
    "n_blocks": ("norns.n_blocks", "clb"),
}
# Fields that carry identity or text, not a measurement (not counted as skipped). Where each
# one ends up:
#   design       -> Record.design
#   arm          -> Record.arm (rounds 1-7); round 3 appends "/<start>"
#   pack         -> Record.arm in round 4 (`stock` or `norns`), with "/<start>" appended
#   start        -> Record.arm suffix (`analytic`, `seed`, `wordseed`, `stagebit`), and family
#   tag          -> Record.arm suffix "arm/tag" in rounds 1-2 and the round-3 pilot. In rounds 3
#                   and 4 it is "<arm>.<start>.s<seed>", rebuilt from arm, start and seed: dropped
#   vseed, seed  -> Record.seed (vseed when both exist)
#   net_sha256   -> Record.input_sha256
#   source       -> not stored: the round-3 and pilot affinity source (module, word, wordio,
#                   stock) is the prefix of `arm`, so it is already in Record.arm
IDENTITY = {"design", "arm", "tag", "vseed", "seed", "net_sha256", "source", "start", "pack"}

# (glob under the Norns root, source label, tool commit)
RUN_FILES = (
    ("data/*/runs.jsonl", None, ""),
    ("data/*/r3runs.jsonl", "norns-r3", VTR_COMMIT),
    ("data/*/r3pilot.jsonl", "norns-r3-pilot", VTR_COMMIT),
    ("data/*/r4runs.jsonl", "norns-r4", VTR_COMMIT),
    ("runs/r7/runs.jsonl", "norns-r7", VTR_COMMIT),
    ("runs/r7f/runs.jsonl", "norns-r7", VTR_COMMIT),
)

# Family rule table, decided per round and per row from the flow each round recorded (the sources
# are read-only and named in docs/specs section 4). The closed set is analytic, annealing, empty.
#   analytic   = VPR's default flow in the pinned build: analytical placement (lp-b2b, APPack), then
#                VPR's annealing refinement at the default schedule, from the flow's own start
#                (norns round3.md "Flow", round7.md lines 33-36; vtr-interfaces.md line 13).
#   annealing  = VPR's anneal from a supplied start (--read_initial_place_file continues placement
#                from the file: vtr-interfaces.md line 11) or from a random start (round7.md lines
#                271-275, "Analytical Placer: DISABLED"), or with a changed initial temperature.
#   empty      = the flow is not stated for the row (round 1-2 `hard` region-constraint runs).
SEEDED_START = {"seed", "wordseed", "stagebit"}
R12_ANNEALING = {"soft", "cold", "cold-r2", "cold-off", "hot", "hot-r2"}


def family_of(source: str, path: Path, row: dict[str, object]) -> str:
    """The placer family of one run row (see the rule table above)."""
    start, arm = row.get("start"), str(row.get("arm") or "")
    if source == "norns-r1r2":
        if arm == "baseline":
            return "analytic"
        if arm in R12_ANNEALING:
            return "annealing"
        if arm in ("unseeded", "unseeded-off"):
            return "analytic" if row.get("scale") == 1.0 else "annealing"
        return ""
    if source in ("norns-r3", "norns-r4"):
        if start == "analytic":
            return "analytic"
        return "annealing" if start in SEEDED_START else ""
    if source == "norns-r7" and "runs/r7f/" in path.as_posix():
        return "annealing"
    return "analytic"  # round-3 pilot (--analytical_place), rounds 5 and 6, round-7 default flow


ROUND_OF_DIR = {"r5": "norns-r5", "r6": "norns-r6"}


def _source(path: Path, label: str | None) -> str:
    if label:
        return label
    return ROUND_OF_DIR.get(path.parent.name, "norns-r1r2")


def _commit(source: str, commit: str) -> str:
    return VTR_COMMIT if source in ("norns-r5", "norns-r6") else commit


def _rows(path: Path) -> Iterator[tuple[int, dict[str, object]]]:
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            if line.strip():
                yield n, json.loads(line)


def _num(v: object) -> float | None:
    """The value as a float when it is a number (not a bool), else None."""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    return None


def _scalars(row: dict[str, object]) -> Iterator[tuple[str, str, float]]:
    """(metric, level, value) for each mapped numeric field, in key order."""
    for key in sorted(row):
        v = row[key]
        if key == "grid" and isinstance(v, list) and len(v) == 2:
            yield "vpr.grid_w", "placed", float(v[0])
            yield "vpr.grid_h", "placed", float(v[1])
        elif key in FIELDS and (x := _num(v)) is not None:
            yield FIELDS[key][0], FIELDS[key][1], x


def _arm(row: dict[str, object]) -> str:
    """The experiment arm. Rounds 3 and 4: "<arm or pack>/<start>"; else "<arm>/<tag>" if both."""
    arm, tag = str(row.get("arm") or ""), str(row.get("tag") or "")
    start = str(row.get("start") or "")
    if start:
        return f"{arm or str(row.get('pack') or '')}/{start}"
    return f"{arm}/{tag}" if arm and tag and tag != arm else arm or tag


def _count_skips(row: dict[str, object], source: str, report: Report) -> None:
    for key, v in sorted(row.items()):
        if key in IDENTITY or key == "grid":
            continue
        if key in FIELDS:
            if _num(v) is None:
                report.skip(source, f"mapped field without a number: {key}")
        elif isinstance(v, (dict, list)):
            report.skip(source, f"nested value not imported: {key}")
        else:
            report.skip(source, f"field not in the field map: {key}")


def import_run_file(
    root: Path, path: Path, label: str | None, commit: str, report: Report
) -> Iterator[Record]:
    source = _source(path, label)
    commit = _commit(source, commit)
    rel = path.relative_to(root).as_posix()
    for n, row in _rows(path):
        report.seen[source] += 1
        made = 0
        seed = row.get("vseed", row.get("seed", -1))
        ctx = Ctx(
            design=str(row["design"]), source=source, origin=f"{rel}:{n}", measurer=MEASURER,
            measurer_version=VERSION, input_sha256=str(row.get("net_sha256") or ""),
            tool_commit=commit, arch=ARCH, seed=seed if isinstance(seed, int) else -1,
            arm=_arm(row), family=family_of(source, path, row),
        )
        for metric, level, value in _scalars(row):
            made += 1
            yield ctx.rec(metric, level, value)
        report.used[source] += bool(made)
        report.records[source] += made
        _count_skips(row, source, report)


CORPUS_SCALARS = (
    "atoms", "carry_pairs", "coverage_pcrit_mean", "pairs", "pairs_connected_random",
    "pairs_connected_sample", "pairs_cooccur", "pairs_uniform", "runs",
)
CORPUS_DICTS = ("class_share_pairs", "relation_share")


def _corpus_items(d: dict[str, object]) -> Iterator[tuple[str, str, float]]:
    for key in CORPUS_SCALARS:
        if (x := _num(d.get(key))) is not None:
            yield f"norns.corpus.{key}", "", x
    for key in CORPUS_DICTS:
        sub = d.get(key)
        if isinstance(sub, dict):
            for name in sorted(sub):
                if (x := _num(sub[name])) is not None:
                    yield f"norns.corpus.{key}", str(name), x


def import_corpus(root: Path, report: Report) -> Iterator[Record]:
    """Round 7 corpus summaries: one JSON per design (scalars and two one-level dicts)."""
    source = "norns-r7-corpus"
    for path in sorted((root / "data/r7/corpus").glob("*.json")):
        report.seen[source] += 1
        d = json.loads(path.read_text(encoding="utf-8"))
        rel = path.relative_to(root).as_posix()
        made = 0
        ctx = Ctx(design=d["design"], source=source, origin=rel, measurer=MEASURER,
                  measurer_version=VERSION, tool_commit=VTR_COMMIT, arch=ARCH)
        for metric, bin_, value in _corpus_items(d):
            made += 1
            yield ctx.rec(metric, "placed", value, bin_)
        report.used[source] += bool(made)
        report.records[source] += made
        known = {"design", "arms", *CORPUS_SCALARS, *CORPUS_DICTS}
        for key in sorted(set(d) - known):
            report.skip(source, f"field not in the field map: {key}")
        report.skip(source, "arms list (names only, no values)")


def note_unimported(root: Path, report: Report) -> None:
    """Count the derived summary files the importer leaves out, with the reason."""
    why = "derived summary (nested aggregates); recomputable from the per-run rows"
    groups = {
        "norns-summaries": ["data/analysis/*.json", "data/r7/*.json", "data/r5/designs.json",
                            "data/r6/designs.json", "data/benchmark-sizes.json"],
        "norns-design-files": ["data/*/n8.json", "data/*/n11.json", "data/*/words.json",
                               "data/*/netlist.json", "data/*/r4*.json", "data/*/iowords.json"],
    }
    for source, patterns in groups.items():
        files = {p for pat in patterns for p in root.glob(pat)}
        report.seen[source] += 0
        report.skip(source, f"{len(files)} files: {why}", len(files))


def import_norns(root: Path) -> tuple[list[Record], Report]:
    """All Norns records under `root` (the Norns checkout, read only)."""
    report = Report()
    out: list[Record] = []
    for pattern, label, commit in RUN_FILES:
        for path in sorted(root.glob(pattern)):
            out.extend(import_run_file(root, path, label, commit, report))
    out.extend(import_corpus(root, report))
    note_unimported(root, report)
    return out, report
