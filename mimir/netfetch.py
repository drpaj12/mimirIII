"""Polite HTTP GET for `mimir fetch`: minimum spacing between requests and retry with backoff.

The static host rate-limits (HTTP 429 after a few dozen quick GETs and it stays throttled for a
long time). On 429 or 503 the wait is the Retry-After header when there is one (at most the cap),
else exponential backoff with jitter. Standard library only. Spec: docs/data-access.md."""

from __future__ import annotations

import email.utils
import os
import random
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, replace
from typing import Any

RETRY_CODES = (429, 503)
_ENV = {
    "min_spacing": ("MIMIR_FETCH_MIN_SPACING", float),
    "retries": ("MIMIR_FETCH_RETRIES", int),
    "backoff_start": ("MIMIR_FETCH_BACKOFF_START", float),
    "backoff_cap": ("MIMIR_FETCH_BACKOFF_CAP", float),
}


@dataclass(frozen=True)
class Policy:
    min_spacing: float = 2.0  # seconds between the starts of two http(s) requests
    retries: int = 6  # retries after the first attempt, per request
    backoff_start: float = 5.0  # first backoff wait, seconds; doubles each retry
    backoff_cap: float = 300.0  # no single wait is longer than this

    def __post_init__(self) -> None:
        if min(self.min_spacing, self.retries, self.backoff_start, self.backoff_cap) < 0:
            raise ValueError("fetch policy values must not be negative")

    @classmethod
    def from_env(cls) -> Policy:
        vals: dict[str, Any] = {}
        for key, (name, conv) in _ENV.items():
            raw = os.environ.get(name)
            if raw:
                try:
                    vals[key] = conv(raw)
                except ValueError as exc:
                    raise ValueError(f"{name}={raw!r} is not a number") from exc
        return cls(**vals)


_override: Policy | None = None
_last_start = float("-inf")
_sleep = time.sleep
_now = time.monotonic
_rand = random.random


def set_policy(retries: int | None = None, min_spacing: float | None = None) -> None:
    """Command-line overrides of the environment policy (None keeps the env value)."""
    global _override
    pol = Policy.from_env()
    if retries is not None:
        pol = replace(pol, retries=retries)
    if min_spacing is not None:
        pol = replace(pol, min_spacing=min_spacing)
    _override = Policy(pol.min_spacing, pol.retries, pol.backoff_start, pol.backoff_cap)


def policy() -> Policy:
    return _override if _override is not None else Policy.from_env()


def retry_after(value: str | None, now_wall: float | None = None) -> float | None:
    """Seconds from a Retry-After header (delta seconds or an HTTP date); None if absent/bad."""
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        when = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    wall = time.time() if now_wall is None else now_wall
    return float(max(0.0, when.timestamp() - wall))


def wait_for(attempt: int, header: str | None, pol: Policy) -> float:
    """Seconds to wait before retry number `attempt` (0 based)."""
    given = retry_after(header)
    if given is not None:
        return min(given, pol.backoff_cap)
    base = min(pol.backoff_cap, pol.backoff_start * (2 ** attempt))
    return float(base * (0.5 + 0.5 * _rand()))


def _space(pol: Policy) -> None:
    global _last_start
    gap = _last_start + pol.min_spacing - _now()
    if gap > 0:
        _sleep(gap)
    _last_start = _now()


def open_url(url: str, timeout: float = 60) -> Any:
    """urlopen with spacing and retry; the caller uses it as a context manager. A `file:` URL is
    not throttled. Raises the last HTTPError when the retries run out."""
    pol = policy()
    throttled = url.split(":", 1)[0].lower() in ("http", "https")
    attempt = 0
    while True:
        if throttled:
            _space(pol)
        try:
            return urllib.request.urlopen(url, timeout=timeout)
        except urllib.error.HTTPError as exc:
            if exc.code not in RETRY_CODES or attempt >= pol.retries:
                raise
            secs = wait_for(attempt, exc.headers.get("Retry-After") if exc.headers else None, pol)
            exc.close()
            print(f"mimir: HTTP {exc.code} from the host (rate limit); waiting {secs:.1f} s, "
                  f"retry {attempt + 1} of {pol.retries}", file=sys.stderr, flush=True)
            _sleep(secs)
            attempt += 1
