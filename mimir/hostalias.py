"""Host aliases: the real machine name never reaches the store, a blob or a snapshot.

`platform.node()` can hold the user name, so every `host` value records a stable alias such as
`host-1`. The real name lives only in a local private map (never committed):
`$MIMIR_HOST_MAP`, else `work/mimir-data/remote-private/hosts.toml` of the workspace.

Map file format (docs/specs/2026-10-28-mimir-host-alias.md): a TOML table `[hosts]`, one line per
host, `"<lower-cased real name>" = "host-<n>"`. The file is append-only; a lock file
`<map>.lock` beside it carries an exclusive `flock` around every read-number-append, so
two processes (this code, or any other writer such as the Norns run-record writer) never give one
name two aliases. Both files are mode 600. The map is created only by `init_map`
(`mimir host-alias --init`); a missing map is an error, never an empty map.
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import platform
import re
from collections.abc import Callable, Iterator
from pathlib import Path

ALIAS_RE = re.compile(r"host-\d+")
HEADER = "# Private map of real host names to aliases. Never commit this file.\n[hosts]\n"
_cache: dict[tuple[str, ...], re.Pattern[str]] = {}


class HostMapError(Exception):
    """The host map is missing or cannot be used safely: the caller must stop, not continue."""


def map_path() -> Path:
    env = os.environ.get("MIMIR_HOST_MAP")
    if env:
        return Path(env)
    return Path.home() / "odin3-ws" / "work" / "mimir-data" / "remote-private" / "hosts.toml"


def lock_path(path: Path) -> Path:
    return path.with_name(path.name + ".lock")


@contextlib.contextmanager
def _locked(path: Path, exclusive: bool) -> Iterator[None]:
    """Hold a flock on the map's lock file (created, mode 600, when it does not exist and the
    lock is exclusive). A shared lock on a map with no lock file yet is not needed."""
    lock = lock_path(path)
    if not exclusive and not lock.exists():
        yield
        return
    fd = os.open(lock, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        os.fchmod(fd, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        yield
    finally:
        os.close(fd)  # closing the descriptor releases the lock


def _read_table(path: Path) -> dict[str, str]:
    import tomllib

    table = tomllib.loads(path.read_text(encoding="utf-8")).get("hosts", {})
    return {str(k).lower(): str(v) for k, v in table.items()}


def load_map(path: Path | None = None) -> dict[str, str]:
    """Lower-cased real name -> alias. HostMapError when the map does not exist: an absent map
    is never read as an empty one."""
    path = path or map_path()
    if not path.is_file():
        raise HostMapError(f"host map {path.name} does not exist (create it with "
                           "`mimir host-alias --init`, or restore it; never start over)")
    with _locked(path, exclusive=False):
        return _read_table(path)


def stored_aliases(dbs: list[Path]) -> list[str]:
    """The distinct `host-<n>` first tokens that the given stores hold in `run.host`."""
    import sqlite3

    found: set[str] = set()
    for db_path in dbs:
        db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            has_run = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='run'").fetchone()
            if has_run is None:
                continue
            for (host,) in db.execute("SELECT DISTINCT host FROM run WHERE host IS NOT NULL"):
                token = str(host).split(None, 1)[0] if str(host).strip() else ""
                if ALIAS_RE.fullmatch(token):
                    found.add(token)
        finally:
            db.close()
    return sorted(found, key=lambda a: int(a.split("-")[1]))


def init_map(path: Path | None = None, stores: list[Path] | None = None) -> bool:
    """Create the map (header only) when it does not exist; True when it was created. Refuses
    (HostMapError) when any of `stores` already holds a `host-<n>`: the numbering would restart
    and give a second machine an alias already used for another. An existing map is left as is."""
    path = path or map_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _locked(path, exclusive=True):
        if path.is_file():
            return False
        used = stored_aliases(stores or [])
        if used:
            raise HostMapError(f"refusing to create a new host map: the stores already hold "
                               f"{', '.join(used[:5])}; restore the map they were aliased with")
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(HEADER)
            fh.flush()
            os.fsync(fh.fileno())
    return True


def alias_of(name: str, path: Path | None = None) -> str:
    """The alias of a host name. An alias maps to itself; an unknown name gets the next
    `host-<n>` and is appended to the map, so the alias is stable per real name. The read,
    the numbering and the append happen under one exclusive lock, with the map re-read inside it.
    HostMapError when the map does not exist."""
    name = name.strip()
    if not name:
        raise ValueError("empty host name")
    if ALIAS_RE.fullmatch(name):
        return name
    path = path or map_path()
    key = name.lower()
    table = load_map(path)  # raises when the map does not exist
    if key in table:
        return table[key]
    with _locked(path, exclusive=True):
        table = _read_table(path)
        if key in table:
            return table[key]
        used = [int(a.split("-")[1]) for a in table.values() if ALIAS_RE.fullmatch(a)]
        alias = f"host-{max(used, default=0) + 1}"
        line = f"{json.dumps(key)} = {json.dumps(alias)}\n"
        fd = os.open(path, os.O_WRONLY | os.O_APPEND)
        try:
            os.fchmod(fd, 0o600)
            os.write(fd, line.encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)
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
    """Real host names of the map (any case) replaced by their aliases. HostMapError when the
    map does not exist: text is never passed through unchecked."""
    table = load_map(path)
    if not table or not text:
        return text
    return _pattern(sorted(table, key=lambda n: (-len(n), n))).sub(
        lambda m: table[m.group(0).lower()], text)


def text_scrubber(path: Path | None = None) -> Callable[[str], str]:
    """`scrub_text` with the map read once (for a loop over many cells)."""
    table = load_map(path)
    if not table:
        return lambda text: text
    rx = _pattern(sorted(table, key=lambda n: (-len(n), n)))
    return lambda text: rx.sub(lambda m: table[m.group(0).lower()], text) if text else text


def scrub_bytes(data: bytes, path: Path | None = None) -> bytes:
    """As `scrub_text` for bytes."""
    table = load_map(path)
    if not table or not data:
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
