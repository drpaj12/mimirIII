"""Run one design through `odin3-flow --prov --vpr --keep-results` and `odin3-prov-post`, and
write `mimir-run.json` with the full how-obtained data (commands, commits, host, time, peak RSS).

It is the command a `tools/heavy-run` call wraps, so the flow and VPR run inside the heavy slice.
The Norns VPR lock is held around the `odin3-flow` step only (it holds Odin III for a few seconds
and then VPR; VPR cannot be locked alone from outside the flow), not around `odin3-prov-post`.
Peak RSS is `ru_maxrss` of the largest child (the flow's biggest process, VPR in practice).
`VTR_ROOT` is required: the VTR commit is the commit of that checkout, never of the cwd.
Spec: docs/specs/2026-10-27-mimir-structures.md, section 4.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
import platform
import re
import resource
import subprocess
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from urllib.parse import unquote

NORNS_LOCK = os.environ.get("MIMIR_NORNS_LOCK", "/tmp/claude-1000/norns-vpr.lock")
_SHA40 = re.compile(r"[0-9a-f]{40}")


def git_head(root: Path) -> str:
    """HEAD of the checkout at `root`; '' when it is not a git checkout."""
    res = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True,
                         text=True, check=False)
    head = res.stdout.strip()
    return head if _SHA40.fullmatch(head) else ""


def git_out(root: Path, *args: str) -> str:
    res = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                         check=False)
    return res.stdout.strip() if res.returncode == 0 else ""


def build_check(tree: Path, odin3: Path) -> dict[str, object]:
    """Facts that say whether the binary was built from the tree's HEAD: the tree has no change
    (`git status --porcelain` empty), the build dir's CMake source dir is the tree, and the binary
    is newer than the HEAD commit. All three must hold for the commit to be `given`; the sha256
    and the `--version` text of the binary are recorded beside it."""
    clean = git_out(tree, "status", "--porcelain") == "" and bool(git_head(tree))
    cache = odin3.parent / "CMakeCache.txt"
    home = ""
    if cache.is_file():
        for line in cache.read_text(encoding="utf-8", errors="replace").split("\n"):
            if line.startswith("CMAKE_HOME_DIRECTORY:"):
                home = line.split("=", 1)[1]
    commit_time = git_out(tree, "log", "-1", "--format=%ct")
    newer = odin3.is_file() and commit_time.isdigit() and odin3.stat().st_mtime > int(commit_time)
    same_home = bool(home) and Path(home).resolve() == tree.resolve()
    version = subprocess.run([str(odin3), "--version"], capture_output=True, text=True,
                             check=False).stdout.strip()
    return {"odin3_tree_clean": clean, "odin3_cmake_home_is_tree": same_home,
            "odin3_binary_newer_than_commit": bool(newer),
            "odin3_built_from_tree": bool(clean and same_home and newer),
            "odin3_binary_sha256": hashlib.sha256(odin3.read_bytes()).hexdigest(),
            "odin3_binary_version": version}


def _run(argv: list[str], lock: str = "") -> tuple[int, float]:
    """Run `argv`; with `lock`, hold an exclusive flock on that file for the run."""
    with contextlib.ExitStack() as stack:
        if lock:
            handle = stack.enter_context(open(lock, "a", encoding="utf-8"))
            fcntl.flock(handle, fcntl.LOCK_EX)
        start = time.monotonic()
        code = subprocess.run(argv, check=False).returncode
        return code, time.monotonic() - start


def build_commands(tree: Path, odin3: Path, designs: Sequence[Path], top: str, arch: str | None,
                   out: Path, timing_attr: bool = True) -> list[list[str]]:
    flow = [str(tree / "tools/flow/odin3-flow"), *map(str, designs), "--top", top, "--vpr",
            "--prov", "--keep-results", "--odin3", str(odin3), "--out", str(out)]
    if timing_attr:
        flow.append("--timing-attr")
    if arch:
        flow += ["--arch", arch]
    return [flow, [str(tree / "tools/flow/odin3-prov-post"), str(out), "--top", top]]


def map_sources(out: Path) -> dict[str, str]:
    """{path: sha256} of every source file the v2 name map lists (its `F` lines), as read at the
    end of the run. A listed file that cannot be read is left out."""
    found: dict[str, str] = {}
    for names in sorted(out.glob("odin3/*.blif.names")):
        for line in names.read_text(encoding="utf-8", errors="replace").split("\n"):
            parts = line.split("\t")
            if len(parts) >= 3 and parts[0] == "F":
                path = Path(unquote(parts[2]))
                if path.is_file():
                    found[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    return dict(sorted(found.items()))


def run_dir_of(out: Path) -> str:
    """The VPR run directory (relative to `out`) whose .net and .place prov-post reads: `vpr/run`,
    or `vpr/retry-<W>/run` when the flow retried the route at a fixed width."""
    try:
        summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "vpr/run"
    retry = summary.get("route_retry")
    return f"vpr/retry-{retry['used_width']}/run" if retry else "vpr/run"


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="mimir.structrun")
    ap.add_argument("--tree", required=True, type=Path, help="odin3 checkout (tools/flow)")
    ap.add_argument("--odin3", required=True, type=Path, help="the odin3 binary")
    ap.add_argument("--top", required=True)
    ap.add_argument("--arch", default="")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--no-timing-attr", action="store_true",
                    help="leave out --timing-attr (crit_share stays NULL)")
    ap.add_argument("designs", nargs="+", type=Path)
    ns = ap.parse_args(argv)
    vtr_root = os.environ.get("VTR_ROOT", "")
    odin_commit = git_head(ns.tree)
    vtr_commit = git_head(Path(vtr_root)) if vtr_root else ""
    if not vtr_commit or not odin_commit:
        print("mimir.structrun: VTR_ROOT must be set to a git checkout and --tree must be one "
              f"(odin3 commit '{odin_commit}', vtr commit '{vtr_commit}')", file=sys.stderr)
        return 2
    cmds = build_commands(ns.tree, ns.odin3, ns.designs, ns.top, ns.arch or None, ns.out,
                          not ns.no_timing_attr)
    codes, times = [], []
    run_dir = "vpr/run"
    for i, cmd in enumerate(cmds):
        if i == 1:
            run_dir = run_dir_of(ns.out)
            cmd += ["--run-dir", str(ns.out / run_dir)]
        code, secs = _run(cmd, NORNS_LOCK if i == 0 else "")
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
        "odin3_commit": odin_commit, "vtr_commit": vtr_commit,
        **build_check(ns.tree, ns.odin3),
        "design_files": [str(d) for d in ns.designs], "top": ns.top,
        "design_sha256": hashlib.sha256(b"".join(d.read_bytes() for d in ns.designs)).hexdigest(),
        "timing_attr": not ns.no_timing_attr, "source_sha256": map_sources(ns.out),
        "arch": ns.arch, "run_dir": run_dir,
        "ok": all(c == 0 for c in codes) and len(codes) == len(cmds),
    }
    ns.out.mkdir(parents=True, exist_ok=True)
    (ns.out / "mimir-run.json").write_text(json.dumps(info, indent=1, sort_keys=True) + "\n",
                                           encoding="utf-8")
    return 0 if info["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
