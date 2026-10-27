"""Run one design through `odin3-flow --prov --vpr --keep-results` and `odin3-prov-post`, and
write `mimir-run.json` with the full how-obtained data (commands, commits, host, time, peak RSS).

It is the command a `tools/heavy-run` call wraps, so the flow and VPR run inside the heavy slice.
Peak RSS is `ru_maxrss` of the largest child (the flow's biggest process, VPR in practice).
Spec: docs/specs/2026-10-27-mimir-structures.md, section 4.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import subprocess
import sys
import time
from collections.abc import Sequence
from pathlib import Path


def git_head(root: Path) -> str:
    res = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True,
                         text=True, check=False)
    return res.stdout.strip()


def _run(argv: list[str]) -> tuple[int, float]:
    start = time.monotonic()
    code = subprocess.run(argv, check=False).returncode
    return code, time.monotonic() - start


def build_commands(tree: Path, odin3: Path, designs: Sequence[Path], top: str, arch: str | None,
                   out: Path) -> list[list[str]]:
    flow = [str(tree / "tools/flow/odin3-flow"), *map(str, designs), "--top", top, "--vpr",
            "--prov", "--keep-results", "--odin3", str(odin3), "--out", str(out)]
    if arch:
        flow += ["--arch", arch]
    return [flow, [str(tree / "tools/flow/odin3-prov-post"), str(out), "--top", top]]


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="mimir.structrun")
    ap.add_argument("--tree", required=True, type=Path, help="odin3 checkout (tools/flow)")
    ap.add_argument("--odin3", required=True, type=Path, help="the odin3 binary")
    ap.add_argument("--top", required=True)
    ap.add_argument("--arch", default="")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("designs", nargs="+", type=Path)
    ns = ap.parse_args(argv)
    cmds = build_commands(ns.tree, ns.odin3, ns.designs, ns.top, ns.arch or None, ns.out)
    codes, times = [], []
    for cmd in cmds:
        code, secs = _run(cmd)
        codes.append(code)
        times.append(round(secs, 3))
        if code != 0:
            break
    rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024.0
    info = {
        "commands": cmds[:len(codes)], "exit_codes": codes, "step_time_s": times,
        "time_s": round(sum(times), 3), "peak_rss_mib": round(rss, 1),
        "host": platform.node(), "kernel": platform.release(),
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "odin3_commit": git_head(ns.tree), "vtr_commit": git_head(Path(os.environ.get(
            "VTR_ROOT", "."))), "design_files": [str(d) for d in ns.designs], "top": ns.top,
        "arch": ns.arch, "ok": all(c == 0 for c in codes) and len(codes) == len(cmds),
    }
    ns.out.mkdir(parents=True, exist_ok=True)
    (ns.out / "mimir-run.json").write_text(json.dumps(info, indent=1, sort_keys=True) + "\n",
                                           encoding="utf-8")
    return 0 if info["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
