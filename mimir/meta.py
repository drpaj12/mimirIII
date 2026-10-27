"""Design registry and design meta: the `design`, `design_source`, `design_meta`, `design_lineage`
tables (spec docs/specs/2026-10-27-mimir-schema-v2.md, sections 3.1 to 3.3, 6)."""

from __future__ import annotations

import fnmatch
import hashlib
import tomllib
from dataclasses import dataclass
from pathlib import Path

from mimir.importers.common import sha256_file
from mimir.store import Store

MCNC_SOURCES = ("mcnc", "mcnc-k2", "mcnc-k4")
NORNS_VERILOG = "vtr_flow/benchmarks/verilog"
MCNC_BLIF = "vtr_flow/benchmarks/blif"
# fields every design should carry; a design without a sourced value gets a `missing` row
LABEL_FIELDS = ("function_class", "intent", "author", "institution", "year", "original_format")
# toml field -> (design_meta field); each has <field>_src and <field>_conf in mcnc.toml
TOML_FIELDS = ("suite", "original_file", "original_format", "intent", "function_class", "author",
               "institution", "year", "original_header", "stated_counts", "lgsynth93")
# a design's own header comment is kept verbatim, at most this many lines (never a whole file)
HEADER_MAX_LINES = 5
LICENCE_FIELDS = ("licence", "licence_source", "licence_notice")


@dataclass(frozen=True)
class DesignRef:
    """A design as found in the records: where its defining file is, if any."""

    slug: str
    suite: str
    name: str
    design_hash: str
    hash_kind: str
    origin: str


def slug_of(source: str, name: str) -> tuple[str, str]:
    """(suite, slug) of a record's (source, design)."""
    if source in MCNC_SOURCES:
        return "mcnc20", f"mcnc20/{name}"
    if source.startswith("loki:"):
        ds = source[len("loki:"):]
        return source, f"loki/{ds}/{name}"
    return "norns", f"norns/{name}"


def _slug_hash(slug: str) -> str:
    return hashlib.sha256(slug.encode()).hexdigest()


def _file_ref(slug: str, suite: str, name: str, path: Path | None, kind: str, origin: str
              ) -> DesignRef:
    if path is not None and path.is_file():
        return DesignRef(slug, suite, name, sha256_file(path), kind, origin)
    return DesignRef(slug, suite, name, _slug_hash(slug), "slug", "")


@dataclass(frozen=True)
class Roots:
    """Read-only source roots; any may be None (the hash is then of the slug, kind `slug`)."""

    vtr: Path | None = None
    norns: Path | None = None
    loki: Path | None = None


def design_ref(source: str, name: str, roots: Roots) -> DesignRef:
    suite, slug = slug_of(source, name)
    if suite == "mcnc20" and roots.vtr:
        rel = f"{MCNC_BLIF}/{name}.blif"
        return _file_ref(slug, suite, name, roots.vtr / rel, "blif", f"vtr:{rel}")
    if suite == "norns":
        return _norns_ref(slug, name, roots)
    if source.startswith("loki:") and roots.loki:
        rel = f"{source[len('loki:'):]}/{name}/design.json"
        return _file_ref(slug, suite, name, roots.loki / rel, "design.json", f"loki:{rel}")
    return _file_ref(slug, suite, name, None, "slug", "")


def _norns_ref(slug: str, name: str, roots: Roots) -> DesignRef:
    if roots.vtr:
        rel = f"{NORNS_VERILOG}/{name}.v"
        if (roots.vtr / rel).is_file():
            return _file_ref(slug, "norns", name, roots.vtr / rel, "hdl", f"vtr:{rel}")
    if roots.norns:
        rel = f"runs/{name}/netlist/{name}.blif"
        if (roots.norns / rel).is_file():
            return _file_ref(slug, "norns", name, roots.norns / rel, "blif", f"norns:{rel}")
    return _file_ref(slug, "norns", name, None, "slug", "")


def _put_design(store: Store, ref: DesignRef) -> None:
    store.db.execute(
        "INSERT OR REPLACE INTO design VALUES (?, ?, ?, ?, ?, ?)",
        (ref.slug, ref.design_hash, ref.hash_kind, ref.suite, ref.name, ref.origin),
    )


def _put_meta(store: Store, slug: str, field: str, value: str, source: str, conf: str) -> None:
    store.db.execute("INSERT OR REPLACE INTO design_meta VALUES (?, ?, ?, ?, ?)",
                     (slug, field, value, source, conf))


REGISTER = "mimir-register"
CONF_ORDER = {"primary": 0, "secondary": 1, "inferred": 2, "missing": 3}


def register_designs(store: Store, roots: Roots) -> int:
    """Register every (source, design) pair of the records; return the number of designs.

    A design gets rows for what its source states: `records_source` and `repo_path` (where its
    defining file was found), both `inferred`, and `missing` rows for suite, original_file and
    the label fields. Re-registering refreshes the rows this function wrote while their conf is
    `inferred` or `missing` (a later run with more sources fills them); `primary` and `secondary`
    rows, and rows from another source (the MCNC research file), are never touched."""
    pairs = store.db.execute(
        "SELECT DISTINCT source, design FROM records WHERE source NOT LIKE 'partition:%' "
        "AND source NOT LIKE 'analysis:%' ORDER BY 1, 2"
    ).fetchall()
    seen: set[str] = set()
    try:
        for source, name in pairs:
            ref = design_ref(source, name, roots)
            store.db.execute("INSERT OR REPLACE INTO design_source VALUES (?, ?, ?)",
                             (source, name, ref.slug))
            if ref.slug in seen:
                continue
            seen.add(ref.slug)
            _put_design(store, ref)
            _registered_meta(store, ref, source)
        store.db.commit()
    except BaseException:
        store.db.rollback()
        raise
    return len(seen)


def _registered_meta(store: Store, ref: DesignRef, source: str) -> None:
    how = f"{REGISTER}: records.source {source}"
    none = f"{REGISTER}: no source states it"
    rows = [("records_source", source, how, "inferred")]
    rows.append(("repo_path", ref.origin, how, "inferred") if ref.origin
                else ("repo_path", "", none, "missing"))
    rows.append(("suite", "", none, "missing"))
    rows.append(("original_file", "", none, "missing"))
    rows += [(f, "", none, "missing") for f in LABEL_FIELDS if f != "original_file"]
    for field, value, src, conf in rows:
        store.db.execute(
            "INSERT INTO design_meta VALUES (?, ?, ?, ?, ?) ON CONFLICT(slug, field) DO UPDATE "
            "SET value = excluded.value, source = excluded.source, conf = excluded.conf "
            "WHERE design_meta.conf IN ('inferred', 'missing') AND design_meta.source LIKE ?",
            (ref.slug, field, value, src, conf, REGISTER + "%"))


def derive_lineage(steps: list[dict[str, object]]) -> tuple[str, int]:
    """(lineage_conf, gaps) from the steps: gaps = steps with conf missing; the conf is the
    weakest conf of the other steps, and `primary` only when there is no gap."""
    confs = [str(st["conf"]) for st in steps]
    gaps = sum(1 for c in confs if c == "missing")
    present = [c for c in confs if c != "missing"]
    if not present:
        return "missing", gaps
    worst = max(present, key=lambda c: CONF_ORDER[c])
    return ("secondary" if gaps and worst == "primary" else worst), gaps


def import_mcnc_meta(store: Store, toml_path: Path, roots: Roots) -> int:
    """Write design, design_meta and design_lineage for the circuits of mcnc.toml that are in
    circuits.txt (the 20 MCNC circuits). Returns the number of circuits. A field with conf
    `missing` has the value '' and its note, if any, goes to the source column."""
    data = tomllib.loads(toml_path.read_text(encoding="utf-8"))["circuit"]
    n = 0
    try:
        for name in sorted(data):
            item = data[name]
            if item.get("in_circuits_txt") is False:
                continue
            ref = design_ref("mcnc", name, roots)
            _put_design(store, ref)
            _toml_meta(store, ref.slug, item)
            _lineage(store, ref.slug, item.get("lineage", []))
            n += 1
        store.db.commit()
    except BaseException:
        store.db.rollback()
        raise
    return n


def _toml_meta(store: Store, slug: str, item: dict[str, object]) -> None:
    for field in TOML_FIELDS:
        if field not in item:
            continue
        conf = str(item[f"{field}_conf"])
        src = str(item.get(f"{field}_src", ""))
        note = str(item.get(f"{field}_note", ""))
        value = "" if conf == "missing" else str(item[field])
        if field == "original_header" and len(value.splitlines()) > HEADER_MAX_LINES:
            raise ValueError(f"{slug}: original_header has more than {HEADER_MAX_LINES} lines")
        if conf == "missing" and note:
            src = f"{src}; note: {note}" if src else f"note: {note}"
        _put_meta(store, slug, field, value, src, conf)
    for field in ("vtr_file", "vtr_rev"):
        _put_meta(store, slug, field, str(item[field]), "VTR repository at vtr_rev", "primary")
    steps = item.get("lineage", [])
    if isinstance(steps, list) and steps:
        conf, gaps = derive_lineage(steps)
        _put_meta(store, slug, "lineage_gaps", str(gaps),
                  "count of lineage steps with conf missing", conf)


def _lineage(store: Store, slug: str, steps: list[dict[str, object]]) -> None:
    store.db.execute("DELETE FROM design_lineage WHERE slug = ?", (slug,))
    for st in steps:
        store.db.execute(
            "INSERT INTO design_lineage VALUES (?, ?, ?, ?, ?, ?, ?)",
            (slug, int(str(st["step"])), str(st["tool"]), str(st.get("script", "")), "",
             str(st.get("src", "")), str(st["conf"])),
        )


def meta_coverage(store: Store, suite_prefix: str = "") -> list[tuple[str, str, int]]:
    """(field, conf, designs) counts over designs whose slug starts with `suite_prefix`."""
    rows = store.db.execute(
        "SELECT field, conf, COUNT(*) FROM design_meta WHERE slug LIKE ? GROUP BY field, conf "
        "ORDER BY field, conf", (suite_prefix + "%",)
    ).fetchall()
    return [(f, c, int(n)) for f, c, n in rows]


Rule = dict[str, str | list[str]]


def load_licence_rules(toml_path: Path) -> list[Rule]:
    """The ordered rules of a licences toml (`[[rule]]` tables); each needs `match` (slug globs),
    `licence`, `licence_source`, `licence_notice` and `conf`. A bad rule raises ValueError."""
    rules = tomllib.loads(toml_path.read_text(encoding="utf-8")).get("rule", [])
    for rule in rules:
        absent = [k for k in ("id", "match", "licence", "licence_source", "licence_notice", "conf")
                  if k not in rule]
        if absent:
            raise ValueError(f"licence rule {rule.get('id', '?')}: missing {absent}")
        if rule["conf"] not in CONF_ORDER or rule["conf"] == "missing":
            raise ValueError(f"licence rule {rule['id']}: bad conf {rule['conf']}")
        if not rule["licence"] or not rule["licence_source"]:
            raise ValueError(f"licence rule {rule['id']}: licence and licence_source are required")
    return list(rules)


def rule_for(slug: str, rules: list[Rule]) -> Rule | None:
    """The first rule whose glob matches the slug (specific rules come first in the file)."""
    for rule in rules:
        if any(fnmatch.fnmatchcase(slug, str(g)) for g in rule["match"]):
            return rule
    return None


def import_licences(store: Store, toml_path: Path) -> int:
    """Write the `licence`, `licence_source` and `licence_notice` rows of every registered design,
    from the first matching rule. The licence is recorded as the benchmark states it, never
    changed or inferred; `none-stated` means the benchmark's own files and documents were read
    and carry none. A design no rule matches gets a `missing` licence row. Returns the number of
    designs a rule matched."""
    rules = load_licence_rules(toml_path)
    slugs = [s for (s,) in store.db.execute("SELECT slug FROM design ORDER BY slug").fetchall()]
    hit = 0
    try:
        for slug in slugs:
            rule = rule_for(slug, rules)
            if rule is None:
                _put_meta(store, slug, "licence", "", "no licence rule matches this design",
                          "missing")
                continue
            hit += 1
            conf, src = str(rule["conf"]), str(rule["licence_source"])
            _put_meta(store, slug, "licence", str(rule["licence"]), src, conf)
            _put_meta(store, slug, "licence_source", src, f"licence rule {rule['id']}", conf)
            _put_meta(store, slug, "licence_notice", str(rule["licence_notice"]), src, conf)
        store.db.commit()
    except BaseException:
        store.db.rollback()
        raise
    return hit
