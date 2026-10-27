"""Flow configurations of the Norns rounds, from an explicit table of the arms each round defines.

Every arm a round's scripts define is listed in ARM_TABLES with its source line (script:line, in
the Norns experiment checkout `scripts/`). An arm that is not in its round's table raises
`UnknownArm`; the importer counts it as skipped and never invents values for it. Parameters the
arm token encodes (`-b<beta>`, a scale, a seed family) are parsed from the token.
A `given` parameter always carries a cited line; a tool default is read by `flowspec`.
"""

from __future__ import annotations

import re

from mimir.flowspec import (
    Spec,
    SrcRoots,
    abc_default_script,
    add_found,
    option_default,
)

VTR_COMMIT = "3c9a4d23b2"
ODIN_V111 = "a1cf6ffd"  # Odin III v1.1.1, the version rounds 5 and 6 used (round6.md:19)
ARCH = "k6_frac_N10_frac_chain_mem32K_40nm"
ARCH_REL = f"vtr_flow/arch/timing/{ARCH}.xml"
# nornsIII HEAD when the defaults were read; the commit of the binary that ran is unrecorded
NORNS_SRC_REV = "e6891fe048"
READ_OPTIONS = "vpr/src/base/read_options.cpp"
NORNS_READ_OPTIONS = "packer/vpr/src/base/read_options.cpp"

STD = "--write_initial_place_file <run>/initial.place --write_flat_place <run>/final.flat_place"
AFF = " --norns_affinity <file> --norns_affinity_weight"
SCALE = r"[0-9]+(?:\.[0-9]+)?"
ODIN_TEXT = (
    "odin3 -p \"read_arch <arch>; read_verilog --nolatches --vtr-compat <design>.v; proc; fsm; "
    "opt; flatten; opt -full; wreduce; hardmap; lower; abc --lut 6; stats; "
    "write_blif --vtr --lut-k 6 --name-style provenance <design>.blif\""
)
ODIN_SRC = "scripts/nornlib.py:389-395 odin_script"
BLIF_SRC = "scripts/matrix.py:63-64 blif_of"
PLAN7 = "docs/plan/round7.md:33-36"


class UnknownArm(ValueError):
    """The arm is not one the round's scripts define."""


# ------------------------------------------------------------------ the tables (arm -> source line)

SEED_FAMILIES = ("urd", "louvain", "spectral", "affinity", "kmeans_k", "kmeans_2k", "kmeans_4k")
NEW_FAMILIES = ("words", "slices", "hier", "words_partial")  # scripts/round2.py:32
ROUND2_SOFT = {"words": ("full", "inter"), "slices": ("full",), "hier": ("full",),
               "words_partial": ("full",), "random": ("full",), "urd_shuf": ("full",)}
R3_SOURCES = ("module", "word", "wordio")  # scripts/affinity.py:19
R3_BETAS = ("0.05", "0.1", "0.2", "0.5", "1", "2", "4")  # scripts/round3.py:30 (pilot grid)
R4_PACKS = {"stock": None, "norns": ("word", "4")}  # scripts/round4.py:356 (SOURCE :38, BETA :37)
R4_STARTS = ("analytic", "wordseed", "stagebit")  # scripts/round4.py:357
R7_HIND = tuple(f"h{k}" for k in range(1, 6))  # scripts/r7.py:206-208, r7lib.py:22 MAX_ROUNDS = 5

ARM_TABLES: dict[str, list[tuple[str, str]]] = {
    "norns-r1r2": [
        ("baseline", "scripts/matrix.py:169-174"),
        ("soft/soft-<seed>-<full|inter>, seed in " + ",".join(SEED_FAMILIES),
         "scripts/matrix.py:177-186, 358; nornlib.py:32"),
        ("soft/soft-<words|slices|hier|words_partial|random|urd_shuf>-<full[|inter for words]>",
         "scripts/round2.py:38-45"),
        ("soft/soft-<words|slices|hier|words_partial>_shuf-full", "scripts/round2.py:32, 47-48"),
        ("hard/hard-<seed>, seed in the 7 families or words_partial",
         "scripts/matrix.py:189-198, 363; round2.py:51-52"),
        ("unseeded/unseeded-<scale>", "scripts/matrix.py:221-226"),
        ("cold/cold-<scale>", "scripts/matrix.py:229-237"),
        ("hot/hot-<seed>-<scale>, seed in the 7 families", "scripts/matrix.py:337-352"),
        ("unseeded-off/unseededoff-<scale>", "scripts/matrix.py:279-285"),
        ("cold-off/coldoff-<scale>", "scripts/matrix.py:288-297"),
        ("cold-r2/cold-r2-<words|slices|hier|words_partial>-<scale>", "scripts/round2.py:62-78"),
        ("hot-r2/hot-r2-<words|slices|hier|words_partial>-<scale>", "scripts/round2.py:86-94"),
    ],
    "norns-r3": [
        ("stock/<analytic|seed>", "scripts/round3.py:230-236, 266-290"),
        ("<module|word|wordio>-b<beta>/<analytic|seed>, beta parsed from the token",
         "scripts/round3.py:233-236, 277"),
    ],
    "norns-r3-pilot": [
        ("pilot-stock", "scripts/round3.py:184"),
        ("pilot/pilot-<module|word|wordio>-b<beta>, beta in " + ",".join(R3_BETAS),
         "scripts/round3.py:30, 185-191"),
    ],
    "norns-r4": [
        ("<stock|norns>/<analytic|wordseed|stagebit>", "scripts/round4.py:356-357, 426-470"),
    ],
    "norns-r5": [
        ("stock", "scripts/r5.py:31, 89-90"),
        ("norns (HDL designs only)", "scripts/r5.py:31, 94-96, 101-102"),
        ("known", "scripts/r5.py:31, 97-98; r5lib.py:23"),
    ],
    "norns-r6": [
        ("stock", "scripts/r6.py:34, 145-146"),
        ("norns", "scripts/r6.py:34, 38, 147-150"),
        ("known", "scripts/r6.py:34, 151-152; r5lib.py:23"),
    ],
    "norns-r7": [
        ("stock", "scripts/r7.py:79-82, 192"),
        ("known (calibration designs)", "scripts/r7.py:199-203"),
        ("h1..h5", "scripts/r7.py:206-208; r7lib.py:22"),
        ("net0", "scripts/r7net.py:599, 615"),
        ("net_h1..net_h5", "scripts/r7net.py:635-637"),
        ("net_known", "scripts/r7net.py:625-632"),
    ],
}
ROUND_FILES = {
    "norns-r1r2": "scripts/matrix.py:98-107; scripts/round2.py:62-94",
    "norns-r3": "scripts/round3.py:90-104, 264-290",
    "norns-r3-pilot": "scripts/round3.py:90-104, 184-191",
    "norns-r4": "scripts/round4.py:440-470",
    "norns-r5": "scripts/r5.py:89-125",
    "norns-r6": "scripts/r6.py:145-175",
    "norns-r7": "scripts/r7.py:70-95; scripts/r7net.py:511-530",
}
NPATHS = {"norns-r4": ("1000", "scripts/round4.py:359"), "norns-r5": ("100", "scripts/r5.py:34"),
          "norns-r6": ("100", "scripts/r6.py:37"), "norns-r7": ("200", "scripts/r7lib.py:24")}
# what each round's notes say about the Odin III build that wrote its BLIFs
ODIN_NOTES = {
    "norns-r1r2": "BLIFs of rounds 1-2; no source names the Odin III build",
    "norns-r3": "read via matrix.blif_of (scripts/round3.py); the Odin III build is not recorded",
    "norns-r3-pilot": "read via matrix.blif_of (scripts/round3.py); Odin III build not recorded",
    "norns-r4": "read via matrix.blif_of (scripts/round4.py); the Odin III build is not recorded",
    "norns-r5": "synthesised in round 5 with Odin III v1.1.1 (docs/plan/round5.md:44-46)",
    "norns-r6": "synthesised in round 6 with Odin III v1.1.1 (docs/plan/round6.md:15-19)",
    "norns-r7": "BLIFs of rounds 1-5 reused, not re-synthesised (docs/plan/round7.md:11)",
}
ODIN_REV = {"norns-r5": ODIN_V111, "norns-r6": ODIN_V111}
ODIN_REV_SRC = {"norns-r5": "docs/plan/round6.md:18-19 (v1.1.1, a1cf6ffd; used by round 5)",
                "norns-r6": "docs/plan/round6.md:18-19 (v1.1.1, a1cf6ffd)"}


def arm_table(source: str) -> list[tuple[str, str]]:
    return ARM_TABLES["norns-r7" if source == "wyrd-atlas-r7" else source]


def _bad(source: str, arm: str, why: str = "not in the arm table") -> UnknownArm:
    return UnknownArm(f"{source}: arm {arm!r} {why}")


# ------------------------------------------------------------------ shared parameters

def _odin_params(spec: Spec, base: str, n5: bool, roots: SrcRoots) -> None:
    if n5:
        spec.add("odin", "synthesis", "none: netlist-level construction, no Verilog", "given",
                 "docs/plan/round7.md Stage 1 (calibration set); scripts/r5lib.py:54-61")
        return
    spec.add("odin", "script_source", ODIN_SRC, "given", "scripts/nornlib.py:389-395")
    spec.add("odin", "blif_set", f"runs/<design>/netlist/<design>.blif; {ODIN_NOTES[base]}",
             "given", BLIF_SRC)
    spec.add("odin", "lut_k", "6", "given", ODIN_SRC)
    spec.add("odin", "name_style", "provenance", "given", ODIN_SRC)
    rev = ODIN_REV.get(base)
    if rev:
        spec.add("odin", "odin3_commit", rev, "given", ODIN_REV_SRC[base])
        found = abc_default_script(roots.odin3, rev)
        add_found(spec, "odin", "abc_script", found, roots.odin3, rev, "odin3",
                  "odin3 checkout not available")
    else:
        spec.add("odin", "odin3_commit", "", "unknown", ODIN_NOTES[base])
        spec.add("odin", "abc_script", "", "default-unrecorded",
                 "abc ran with no --script; the Odin III build is not recorded, so the default "
                 "script cannot be tied to a version")


def _arch_params(spec: Spec, arch_sha: str | None) -> None:
    spec.add("arch", "arch", ARCH, "given", "scripts/nornlib.py:37 ARCH")
    if arch_sha:
        spec.add("arch", "arch_file_sha256", arch_sha, "given",
                 f"sha256 of {ARCH_REL} in the VTR checkout at {VTR_COMMIT}")
    else:
        spec.add("arch", "arch_file_sha256", "", "unknown", "VTR checkout not available")


def _vpr_commit(spec: Spec, base: str) -> None:
    if base == "norns-r1r2":
        spec.add("pack", "vpr_commit", "", "unknown", "rounds 1-2 do not state the VTR commit")
    else:
        spec.add("pack", "vpr_commit", VTR_COMMIT, "given", "packer/VTR_COMMIT; round plans")


def _place_params(spec: Spec, base: str, norns_binary: bool, roots: SrcRoots) -> None:
    src = ROUND_FILES[base]
    if base == "norns-r3-pilot":
        spec.add("place", "flow", "pack and analytical placement only (--analytical_place)",
                 "given", "scripts/round3.py:101-102")
        spec.add("route", "route", "none", "given", "scripts/round3.py:101-102")
    else:
        conf = "unknown" if base == "norns-r1r2" else "given"
        note = ("; the VTR commit of rounds 1-2 is not recorded, so this is the flow of "
                f"{VTR_COMMIT}" if conf == "unknown" else "")
        value = ("" if conf == "unknown" else
                 "default flow: analytical placement (lp-b2b, APPack), then VPR annealing")
        spec.add("place", "flow", value, conf, PLAN7 + note)
        spec.add("route", "route", "" if conf == "unknown" else
                 "VPR default, minimum channel width search", conf, PLAN7 + note)
    if base in NPATHS:
        spec.add("place", "timing_report_npaths", NPATHS[base][0], "given", NPATHS[base][1])
    if base == "norns-r7":
        spec.add("route", "route_file", "/dev/null", "given", "scripts/r7.py:79")
    _unrelated_default(spec, norns_binary, roots, src)


def _unrelated_default(spec: Spec, norns_binary: bool, roots: SrcRoots, src: str) -> None:
    if norns_binary:
        found = option_default(roots.norns_src, NORNS_SRC_REV, NORNS_READ_OPTIONS,
                               "--allow_unrelated_clustering")
        add_found(spec, "pack", "allow_unrelated_clustering", found, roots.norns_src,
                  NORNS_SRC_REV, "nornsIII (binary commit not recorded)",
                  "nornsIII checkout not available")
    else:
        found = option_default(roots.vtr, VTR_COMMIT, READ_OPTIONS, "--allow_unrelated_clustering")
        add_found(spec, "pack", "allow_unrelated_clustering", found, roots.vtr, VTR_COMMIT, "VTR",
                  "VTR checkout not available")


def _affinity(spec: Spec, kind: str, weight: str, count: str, src: str) -> None:
    spec.add("pack", "packer", "norns-vpr (affinity overlay)", "given", src)
    spec.add("pack", "norns_affinity_source", kind, "given", src)
    spec.add("pack", "norns_affinity_weight", weight, "given", src)
    if count:
        spec.add("pack", "norns_proposal_count", count, "given", src)


def _stock(spec: Spec, src: str) -> None:
    spec.add("pack", "packer", "vpr-stock", "given", src)


def _scale(token: str) -> str:
    m = re.search(rf"-({SCALE})$", token)
    if m is None:
        raise UnknownArm(f"no scale in the arm tag {token!r}")
    return m.group(1)


# ------------------------------------------------------------------ rounds 1-2

def _r12(spec: Spec, arm: str) -> str:
    src = ROUND_FILES["norns-r1r2"]
    cmd = ("vpr <arch> <design>.blif --seed 1 " + STD
           + " --write_legalized_flat_place <run>/legalized.flat_place")
    _stock(spec, "scripts/matrix.py:98-107")
    spec.add("place", "seed", "1", "given", "scripts/matrix.py:104")
    if arm == "baseline":
        spec.add("place", "start", "unseeded, VPR defaults", "given", "scripts/matrix.py:169-174")
        return cmd
    head, _, tag = arm.partition("/")
    kind, rest = _r12_kind(head, tag)
    if kind in ("soft", "hot", "cold", "cold-off", "cold-r2", "hot-r2"):
        cmd += " --read_initial_place_file <seed.place>"
        spec.add("place", "start", "read_initial_place_file", "given", src)
    if kind == "hard":
        cmd += " --read_vpr_constraints <seed-hard.xml>"
        spec.add("place", "start", "read_vpr_constraints", "given", "scripts/matrix.py:197")
    if kind in ("unseeded", "unseeded-off"):
        spec.add("place", "start", "unseeded", "given", "scripts/matrix.py:225, 283")
    if rest.get("scale"):
        cmd += " --anneal_auto_init_t_scale <scale>"
        spec.add("place", "anneal_auto_init_t_scale", rest["scale"], "given",
                 "scripts/matrix.py:225-236, 283-295; round2.py:93 (value parsed from the arm tag)")
    if kind.endswith("-off"):
        cmd += " --place_checkpointing off"
        spec.add("place", "place_checkpointing", "off", "given", "scripts/matrix.py:283-295")
    if rest.get("seed"):
        spec.add("place", "seed_family", rest["seed"], "given", "arm tag; " + rest["cite"])
    if rest.get("var"):
        spec.add("place", "seed_variant", rest["var"], "given", "arm tag; scripts/matrix.py:9")
    return cmd


def _r12_kind(head: str, tag: str) -> tuple[str, dict[str, str]]:
    sc = SCALE
    fam = "|".join(SEED_FAMILIES)
    new = "|".join(NEW_FAMILIES)
    shapes: list[tuple[str, str, str]] = [
        ("soft", rf"soft-({fam}|words|slices|hier|words_partial|random|urd_shuf)-(full|inter)",
         "scripts/matrix.py:177-186; round2.py:38-45"),
        ("soft", rf"soft-(({new})_shuf)-(full)", "scripts/round2.py:47-48"),
        ("hard", rf"hard-({fam}|words_partial)", "scripts/matrix.py:189-198; round2.py:51-52"),
        ("unseeded", rf"unseeded-({sc})", "scripts/matrix.py:221-226"),
        ("cold", rf"cold-({sc})", "scripts/matrix.py:229-237"),
        ("hot", rf"hot-({fam})-({sc})", "scripts/matrix.py:337-352"),
        ("unseeded-off", rf"unseededoff-({sc})", "scripts/matrix.py:279-285"),
        ("cold-off", rf"coldoff-({sc})", "scripts/matrix.py:288-297"),
        ("cold-r2", rf"cold-r2-({new})-({sc})", "scripts/round2.py:62-78"),
        ("hot-r2", rf"hot-r2-({new})-({sc})", "scripts/round2.py:86-94"),
    ]
    for kind, pattern, cite in shapes:
        m = re.fullmatch(pattern, tag) if kind == head else None
        if m is None:
            continue
        got = _r12_fields(kind, m, cite)
        return kind, got
    raise _bad("norns-r1r2", f"{head}/{tag}")


def _r12_fields(kind: str, m: re.Match[str], cite: str) -> dict[str, str]:
    g = m.groups()
    out = {"cite": cite}
    if kind == "soft":
        out.update(seed=g[0], var=g[-1])
    elif kind == "hard":
        out["seed"] = g[0]
    elif kind in ("hot", "cold-r2", "hot-r2"):
        out.update(seed=g[0], scale=g[-1])
    else:
        out["scale"] = g[-1]
    return out


# ------------------------------------------------------------------ rounds 3 and 4

def _r3(spec: Spec, source: str, arm: str) -> str:
    src = ROUND_FILES[source]
    pilot = source == "norns-r3-pilot"
    cmd = "vpr <arch> <design>.blif --seed " + ("1 " if pilot else "<s> ") + STD
    start = ""
    if pilot:
        cmd += " --analytical_place"
        spec.add("place", "seed", "1", "given", "scripts/round3.py:184, 189")
        pack = _pilot_name(arm)
    else:
        pack, start = _r3_split(arm)
    if pack is None:
        _stock(spec, src)
        return cmd + _r3_start(spec, start, pilot)
    _affinity(spec, pack[0], pack[1], "",
              src + "; beta parsed from the arm token, scripts/round3.py:233-236")
    return cmd + AFF + " <beta>" + _r3_start(spec, start, pilot)


def _r3_start(spec: Spec, start: str, pilot: bool) -> str:
    if pilot:
        return ""
    seeded = start == "seed"
    spec.add("place", "start", "read_initial_place_file" if seeded else "analytic", "given",
             "scripts/round3.py:277-290")
    return " --read_initial_place_file <seed.place>" if seeded else ""


def _pilot_name(arm: str) -> tuple[str, str] | None:
    if arm == "pilot-stock":
        return None
    srcs = "|".join(R3_SOURCES)
    betas = "|".join(re.escape(b) for b in R3_BETAS)
    m = re.fullmatch(rf"pilot/pilot-({srcs})-b({betas})", arm)
    if m is None:
        raise _bad("norns-r3-pilot", arm)
    return m.group(1), m.group(2)


def _r3_split(arm: str) -> tuple[tuple[str, str] | None, str]:
    cfg, _, start = arm.partition("/")
    if start not in ("analytic", "seed"):
        raise _bad("norns-r3", arm)
    if cfg == "stock":
        return None, start
    m = re.fullmatch(rf"({'|'.join(R3_SOURCES)})-b({SCALE})", cfg)
    if m is None:
        raise _bad("norns-r3", arm)
    return (m.group(1), m.group(2)), start


def _r4(spec: Spec, roots: SrcRoots, arm: str) -> str:
    src = ROUND_FILES["norns-r4"]
    pack, _, start = arm.partition("/")
    if pack not in R4_PACKS or start not in R4_STARTS:
        raise _bad("norns-r4", arm)
    cmd = "vpr <arch> <design>.blif --seed <s> --timing_report_npaths 1000 " + STD
    spec.add("place", "start", "analytic" if start == "analytic"
             else f"read_initial_place_file ({start})", "given", "scripts/round4.py:426-457")
    if start != "analytic":
        cmd += " --read_initial_place_file <seed.place>"
    norns = R4_PACKS[pack]
    if norns is None:
        _stock(spec, src)
        return cmd
    _affinity(spec, norns[0], norns[1], "", "scripts/round4.py:37-38, 356, 463-465")
    found = option_default(roots.norns_src, NORNS_SRC_REV, NORNS_READ_OPTIONS,
                           "--norns_proposal_count")
    add_found(spec, "pack", "norns_proposal_count", found, roots.norns_src, NORNS_SRC_REV,
              "nornsIII (binary commit not recorded); round4.py passes no --norns_proposal_count",
              "nornsIII checkout not available; round4.py passes no --norns_proposal_count")
    return cmd + AFF + " 4"


# ------------------------------------------------------------------ rounds 5, 6, 7

def _r56(spec: Spec, source: str, arm: str, n5: bool) -> str:
    cites = {"norns-r5": ("scripts/r5.py:89-98", "scripts/r5.py:95", "scripts/r5.py:97-98"),
             "norns-r6": ("scripts/r6.py:145-152", "scripts/r6.py:38, 149",
                          "scripts/r6.py:151-152")}
    whole, norns_c, known_c = cites[source]
    cmd = (f"vpr <arch> <design>.blif --seed <s> --timing_report_npaths {NPATHS[source][0]} "
           + STD)
    if arm not in ("stock", "norns", "known"):
        raise _bad(source, arm)
    if arm == "norns" and n5 and source == "norns-r5":
        raise _bad(source, arm, "is not run on netlist-level designs (scripts/r5.py:101-102)")
    if arm == "stock":
        _stock(spec, whole)
        return cmd
    weight = "4" if arm == "norns" else "100"
    wcite = norns_c if arm == "norns" else known_c + "; BETA_KNOWN scripts/r5lib.py:23"
    _affinity(spec, "word" if arm == "norns" else "known", weight, "queued", wcite)
    return cmd + f"{AFF} {weight} --norns_proposal_count queued"


def _r7(spec: Spec, arm: str) -> str:
    if re.fullmatch(r"net0|net_known|net_h[1-5]", arm):
        spec.add("pack", "packer", "none: clustering written by r7net, VPR run with --net_file",
                 "given", "scripts/r7net.py:524-526")
        spec.add("pack", "net_arm", arm, "given", "scripts/r7net.py:599, 635-637")
        return ("vpr <arch> <design>.blif --place --route --analysis --net_file <net> --seed <s> "
                "--timing_report_npaths 200 --route_file /dev/null " + STD)
    cmd = ("vpr <arch> <design>.blif --seed <s> --timing_report_npaths 200 --route_file /dev/null "
           + STD)
    if arm == "stock":
        _stock(spec, "scripts/r7.py:79-82, 192")
        return cmd + " --norns_pack_census <run>/census.tsv"
    if arm == "known":
        kind, cite = "known", "scripts/r7.py:199-203, 84-85; r7lib.py:37"
    elif arm in R7_HIND:
        kind, cite = "hindsight recluster", "scripts/r7.py:206-208, 84-85; r7lib.py:22, 37"
    else:
        raise _bad("norns-r7", arm)
    _affinity(spec, kind, "100", "queued", cite)
    return cmd + f"{AFF} 100 --norns_proposal_count queued"


def norns_spec(source: str, arm: str, n5: bool, arch_sha: str | None,
               roots: SrcRoots | None = None) -> Spec:
    """The flow configuration of a Norns run (source label as the importer wrote it).
    Raises UnknownArm when the arm is not in the round's table."""
    roots = roots or SrcRoots()
    base = "norns-r7" if source == "wyrd-atlas-r7" else source
    if base not in ARM_TABLES:
        raise _bad(source, arm, "is from a round with no arm table")
    spec = Spec(name=f"{base}/{arm}" + ("/n5" if n5 else ""), text="", origin=ROUND_FILES[base])
    cmd = _arm_cmd(spec, base, arm, n5, roots)
    _odin_params(spec, base, n5, roots)
    _arch_params(spec, arch_sha)
    _vpr_commit(spec, base)
    _place_params(spec, base, norns_binary=base == "norns-r7" or not _is_stock(spec),
                  roots=roots)
    spec.text = cmd if n5 else ODIN_TEXT + "\n" + cmd
    return spec


def _is_stock(spec: Spec) -> bool:
    return any(p[1] == "packer" and p[2] == "vpr-stock" for p in spec.params)


def _arm_cmd(spec: Spec, base: str, arm: str, n5: bool, roots: SrcRoots) -> str:
    if base == "norns-r1r2":
        return _r12(spec, arm)
    if base in ("norns-r3", "norns-r3-pilot"):
        return _r3(spec, base, arm)
    if base == "norns-r4":
        return _r4(spec, roots, arm)
    if base == "norns-r7":
        return _r7(spec, arm)
    return _r56(spec, base, arm, n5)
