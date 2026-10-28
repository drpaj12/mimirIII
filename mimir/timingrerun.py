"""Timing-only re-analysis of a stored lane 3 run: the pure parts (architecture lookup, VPR option
parsing, argument building). The runner is `scripts/timing_rerun.py`. Spec:
docs/specs/2026-10-28-near-critical.md, section 4."""

from __future__ import annotations

import re
from collections.abc import Sequence

# Architecture file name (as stored in `run.arch`) to its path under $VTR_ROOT. A name that is not
# here aborts the re-run: the architecture is never guessed.
ARCHS = {
    "k6_frac_N10_frac_chain_mem32K_40nm.xml":
        "vtr_flow/arch/timing/k6_frac_N10_frac_chain_mem32K_40nm.xml",
}

# VPR options of the original command line that change the timing graph or the delays of an
# analysis of stored pack/place/route results; each takes one value. Verified against
# vpr/src/base/read_options.cpp at VTR commit 3c9a4d23b2.
CARRIED = ("--route_chan_width", "--timing_analysis", "--clock_modeling", "--constant_net_method",
           "--allow_dangling_combinational_nodes", "--absorb_buffer_luts", "--const_gen_inference",
           "--sweep_dangling_primary_ios", "--sweep_dangling_nets", "--sweep_dangling_blocks",
           "--sweep_constant_primary_outputs", "--device")
# Options the re-run sets itself, or that only steer a pack, place or route that is not re-run.
SET_BY_RERUN = ("--circuit_file", "--analysis", "--net_file", "--place_file", "--route_file",
                "--timing_report_npaths", "--route", "--pack", "--place")
_CMD = re.compile(r"VPR was run with the following command-line:\n(.*)\n")


def arch_path(name: str) -> str:
    """The architecture file under $VTR_ROOT for a stored `run.arch`; ValueError when unknown."""
    if name not in ARCHS:
        raise ValueError(f"unknown architecture {name!r}: add it to mimir.timingrerun.ARCHS")
    return ARCHS[name]


def stored_vpr_argv(log: str) -> list[str]:
    """The VPR command line the stored flow log printed, split into words."""
    m = _CMD.search(log)
    if m is None:
        raise ValueError("no 'VPR was run with the following command-line' in the stored log")
    return m.group(1).split()


def parse_options(argv: Sequence[str]) -> dict[str, str | None]:
    """`--name value` pairs of a VPR command line (after the architecture and circuit words); a
    flag with no value maps to None."""
    out: dict[str, str | None] = {}
    i = 0
    while i < len(argv):
        if argv[i].startswith("--"):
            has_value = i + 1 < len(argv) and not argv[i + 1].startswith("--")
            out[argv[i]] = argv[i + 1] if has_value else None
            i += 2 if has_value else 1
        else:
            i += 1
    return out


def carried_options(argv: Sequence[str]) -> tuple[list[str], list[str]]:
    """(options to pass on, names of the stored options left out), in command-line order."""
    opts = parse_options(argv)
    carry: list[str] = []
    left: list[str] = []
    for name, value in opts.items():
        if name in CARRIED:
            carry += [name] if value is None else [name, value]
        elif name not in SET_BY_RERUN:
            left.append(name)
    if "--route_chan_width" not in opts:
        raise ValueError("the stored command line has no --route_chan_width: cannot re-analyse")
    return carry, left


def vpr_argv(vpr: str, arch: str, top: str, carried: Sequence[str], npaths: int) -> list[str]:
    """The `vpr --analysis` argument list over the stored net, place and route files."""
    return [vpr, arch, top, "--circuit_file", f"{top}.pre-vpr.blif", "--analysis", *carried,
            "--timing_report_npaths", str(npaths), "--net_file", f"{top}.net",
            "--place_file", f"{top}.place", "--route_file", f"{top}.route"]
