"""Fetch the pinned MNIST test files (pins.toml) into a directory, sha256 verified.

usage: fetch_data.py <out_dir> [--local DIR]

For each `[[data]]` entry: use `<out_dir>/<file>` if it already hashes right; else take `<file>` or
`<file>.gz` from --local (if given) or download the `.gz` from the first working URL; the
decompressed bytes must match `sha256`. A mismatch is an error and nothing is written. MNIST is
never stored in the repository. Licence: see docs/DATA.md.
"""
import gzip
import hashlib
import sys
import tomllib
import urllib.request
from pathlib import Path

PINS = Path(__file__).resolve().parent.parent / "pins.toml"
LIMIT = 64 * 1024 * 1024


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_pins() -> dict:
    with open(PINS, "rb") as f:
        return tomllib.load(f)


def _from_local(local: Path, name: str) -> bytes | None:
    plain, gz = local / name, local / (name + ".gz")
    if plain.is_file():
        return plain.read_bytes()
    if gz.is_file():
        return gzip.decompress(gz.read_bytes())
    return None


def _download(urls: list[str], gz_sha: str) -> bytes:
    errors = []
    for url in urls:
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                blob = r.read(LIMIT + 1)
        except OSError as exc:
            errors.append(f"{url}: {exc}")
            continue
        if len(blob) > LIMIT or sha256(blob) != gz_sha:
            errors.append(f"{url}: size or sha256 of the download does not match the pin")
            continue
        return gzip.decompress(blob)
    raise SystemExit("download failed:\n  " + "\n  ".join(errors))


def fetch(out: Path, local: Path | None = None) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    done = []
    for d in load_pins()["data"]:
        dest = out / d["file"]
        if dest.is_file() and sha256(dest.read_bytes()) == d["sha256"]:
            done.append(dest)
            continue
        data = _from_local(local, d["file"]) if local else None
        if data is None:
            data = _download(d["urls"], d["gz_sha256"])
        if len(data) != d["bytes"] or sha256(data) != d["sha256"]:
            raise SystemExit(f"{d['file']}: sha256 mismatch against pins.toml; nothing written")
        dest.write_bytes(data)
        done.append(dest)
    return done


def main(argv: list[str]) -> int:
    if not argv or argv[0].startswith("-"):
        print(__doc__)
        return 2
    local = Path(argv[argv.index("--local") + 1]) if "--local" in argv else None
    for p in fetch(Path(argv[0]), local):
        print("ok", p)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
