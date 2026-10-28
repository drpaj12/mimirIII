"""A flow configuration (`Spec`) and the readers of tool defaults.

A parameter has a confidence: `given` (a source states the value, cited as file:line), `default`
(the tool's own default, read from a named version of the tool source and cited with file:line),
`default-unrecorded` (the value was left to a default, but the tool version is not recorded or its
source is not available) or `unknown`. Both of the last two count as unknown for the status.
Spec: docs/specs/2026-10-27-mimir-schema-v2.md, sections 3.4, 3.5, 6.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from mimir.schema import UNKNOWN_CONF

Param = tuple[str, str, str, str, str]  # (step, key, value, conf, source)
# parameters whose value depends on which checkout was at hand; kept as a parameter, left out of
# the hash (an import with and without $VTR_ROOT gives the same config_hash)
HASH_EXCLUDE = ("arch.arch_file_sha256", "vpr.placer_opts.place_chan_width",
                "vpr.router_opts.fixed_channel_width",  # these two: the width a run settled on
                "run.seed",  # the seed of a run record: the seeds of one setup share a config
                "vpr.placer_opts.seed")  # VPR echoes the seed it ran with (show_setup.cpp:626)


@dataclass(frozen=True)
class SrcRoots:
    """Read-only tool source checkouts the defaults are read from; any may be None."""

    odin3: Path | None = None
    vtr: Path | None = None
    norns_src: Path | None = None


@dataclass
class Spec:
    """One flow configuration: name, reconstructed command text, parameter rows, origin lines."""

    name: str
    text: str
    origin: str
    text_kind: str = "reconstructed"
    params: list[Param] = field(default_factory=list)

    def add(self, step: str, key: str, value: str, conf: str, src: str) -> None:
        self.params.append((step, key, value, conf, src))

    def status(self) -> str:
        """`full` only when every parameter is known, carries a cited source, and a `given` one
        carries a value (an empty value is not a recorded one: store a marker such as `(empty)`)."""
        bad = any(p[3] in UNKNOWN_CONF or not p[4] or (p[3] == "given" and not p[2])
                  for p in self.params)
        return "partial" if bad else "full"

    def config_hash(self) -> str:
        """Hash of the text and the parameters. A `given` parameter counts with its value; any
        other counts with its key and confidence class only, so a default read from a checkout
        that is present on one machine and absent on another does not change the identity."""
        rows = []
        for step, key, value, conf, _ in sorted(self.params):
            if f"{step}.{key}" in HASH_EXCLUDE:
                continue
            rows.append([step, key, value, "given"] if conf == "given"
                        else [step, key, "", "derived" if conf == "default" else conf])
        blob = json.dumps([self.text, rows], sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()


def _git_lines(root: Path | None, rev: str, path: str) -> list[str] | None:
    if root is None:
        return None
    try:
        res = subprocess.run(["git", "-C", str(root), "show", f"{rev}:{path}"],
                             capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return res.stdout.split("\n")[:-1] if res.stdout.endswith("\n") else res.stdout.split("\n")


def _short(root: Path | None, rev: str) -> str:
    if root is None:
        return rev
    try:
        res = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--short=8", f"{rev}^{{commit}}"],
            capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return rev
    return res.stdout.strip()


def option_default(root: Path | None, rev: str, path: str, option: str
                   ) -> tuple[str, str] | None:
    """(value, 'path:first-last') of the `.default_value("x")` that follows the argparse entry of
    `option` in a C++ source at `rev`; None when the file, entry or default is not found."""
    lines = _git_lines(root, rev, path)
    if lines is None:
        return None
    for i, ln in enumerate(lines):
        if f'"{option}")' in ln:
            for j in range(i, min(i + 20, len(lines))):
                m = re.search(r'\.default_value\("([^"]*)"\)', lines[j])
                if m:
                    return m.group(1), f"{path}:{i + 1}-{j + 1}"
            return None
    return None


def abc_default_script(root: Path | None, rev: str, gates: bool = False
                       ) -> tuple[str, str] | None:
    """(script text, source) of the abc pass default script of Odin III at `rev` (the --gates
    script when `gates`)."""
    path, marker = ("lib/abc/gates.abc", "map -a") if gates else ("lib/abc/vtr.abc", "if -K {K}")
    lines = _git_lines(root, rev, path)
    if lines is None or not any(marker in ln for ln in lines):
        return None
    text = "\n".join(lines)
    sha = hashlib.sha256((text + "\n").encode()).hexdigest()[:16]
    return text, f"{path}:1-{len(lines)} sha256 {sha}"


def abc_lut_default(root: Path | None, rev: str) -> tuple[str, str] | None:
    """('0', source): `odin3_abc_parse_args` zero-initialises the options, so with no `--lut`
    lut_k is 0 (no LUT width). None when that line is not found at `rev`."""
    lines = _git_lines(root, rev, "src/passes/abc/args.c")
    if lines is None:
        return None
    for i, ln in enumerate(lines):
        if "*out = (odin3_abc_opts){0};" in ln:
            return "0", f"src/passes/abc/args.c:{i + 1}"
    return None


def add_found(spec: Spec, step: str, key: str, found: tuple[str, str] | None, root: Path | None,
              rev: str, label: str, why: str) -> None:
    """A `default` parameter when `found`, else `default-unrecorded` with the reason."""
    if found is None:
        spec.add(step, key, "", "default-unrecorded", why)
    else:
        value, where = found
        spec.add(step, key, value, "default", f"{label} {_short(root, rev)} {where}")
