"""Host aliases: the real machine name never reaches the store, a blob or a snapshot.

`platform.node()` can hold the user name, so every `host` value records a stable alias such as
`host-1`. The real name lives only in a local private map (never committed):
`$MIMIR_HOST_MAP`, else `work/mimir-data/remote-private/hosts.toml` of the workspace.
"""

from __future__ import annotations

import os
import platform
import re
from pathlib import Path

ALIAS_RE = re.compile(r"host-\d+")
HEADER = "# Private map of real host names to aliases. Never commit this file.\n[hosts]\n"
_cache: dict[tuple[str, ...], re.Pattern[str]] = {}


def map_path() -> Path:
    env = os.environ.get("MIMIR_HOST_MAP")
    if env:
        return Path(env)
    return Path.home() / "odin3-ws" / "work" / "mimir-data" / "remote-private" / "hosts.toml"


def load_map(path: Path | None = None) -> dict[str, str]:
    """Lower-cased real name -> alias; empty when the map does not exist yet."""
    import tomllib

    path = path or map_path()
    if not path.is_file():
        return {}
    table = tomllib.loads(path.read_text(encoding="utf-8")).get("hosts", {})
    return {str(k).lower(): str(v) for k, v in table.items()}


def alias_of(name: str, path: Path | None = None) -> str:
    """The alias of a host name. An alias maps to itself; an unknown name gets the next
    `host-<n>` and is appended to the map, so the alias is stable per real name."""
    name = name.strip()
    if ALIAS_RE.fullmatch(name):
        return name
    path = path or map_path()
    table = load_map(path)
    key = name.lower()
    if key in table:
        return table[key]
    used = [int(a.split("-")[1]) for a in table.values() if ALIAS_RE.fullmatch(a)]
    alias = f"host-{max(used, default=0) + 1}"
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.is_file()
    with path.open("a", encoding="utf-8") as fh:
        if new:
            fh.write(HEADER)
        fh.write(f'"{key}" = "{alias}"\n')
    return alias


def real_names(path: Path | None = None) -> list[str]:
    """Every real host name of the map (lower case), longest first."""
    return sorted(load_map(path), key=lambda n: (-len(n), n))


def _pattern(names: list[str]) -> re.Pattern[str]:
    key = tuple(names)
    if key not in _cache:
        _cache[key] = re.compile("|".join(re.escape(n) for n in names), re.IGNORECASE)
    return _cache[key]


def scrub_text(text: str, path: Path | None = None) -> str:
    """Real host names of the map (any case) replaced by their aliases. No map: unchanged."""
    table = load_map(path)
    if not table:
        return text
    return _pattern(sorted(table, key=lambda n: (-len(n), n))).sub(
        lambda m: table[m.group(0).lower()], text)


def scrub_bytes(data: bytes, path: Path | None = None) -> bytes:
    table = load_map(path)
    if not table:
        return data
    names = sorted(table, key=lambda n: (-len(n), n))
    rx = re.compile(b"|".join(re.escape(n.encode()) for n in names), re.IGNORECASE)
    return rx.sub(lambda m: table[m.group(0).decode().lower()].encode(), data)


def this_host(path: Path | None = None) -> str:
    """The alias of the machine the code runs on."""
    return alias_of(platform.node(), path)


def _cpu_model() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").split("\n"):
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return ""


def _ram_mib() -> str:
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").split("\n"):
            if line.startswith("MemTotal:"):
                return str(int(line.split()[1]) // 1024)
    except (OSError, ValueError, IndexError):
        pass
    return ""


def host_facts() -> dict[str, dict[str, str]]:
    """Hardware facts that identify no person, each with the source it was read from."""
    facts = {
        "cpu_model": (_cpu_model(), "/proc/cpuinfo, first 'model name'"),
        "cpu_cores": (str(os.cpu_count() or ""), "os.cpu_count()"),
        "ram_mib": (_ram_mib(), "/proc/meminfo, MemTotal in MiB"),
        "kernel": (platform.release(), "platform.release()"),
    }
    return {k: {"value": v, "source": s} for k, (v, s) in facts.items() if v}
