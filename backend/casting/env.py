"""Minimal `.env` loading.

Deliberately not `python-dotenv`. The pipeline has no third-party dependencies
and reading twenty lines of `KEY=value` does not justify the first one — the
requirements files stay honest about covering only the HTTP surface.

Two rules that matter more than they look:

* A variable already present in the real environment always wins. A `.env`
  committed by accident, or left stale in a checkout, must never silently
  override what an operator exported or what a deployment injected.
* Nothing here is logged or echoed. The file holds an API key.
"""

from __future__ import annotations

import os
from pathlib import Path

FILENAME = ".env"

#: How far up to look for the file, starting from this package. Covers running
#: from the repo root, from backend/, or from anywhere via an editable install.
SEARCH_DEPTH = 4

_loaded = False


def find_env_file(start: Path | None = None) -> Path | None:
    here = (start or Path(__file__).resolve()).parent
    for directory in [here, *here.parents][:SEARCH_DEPTH]:
        candidate = directory / FILENAME
        if candidate.is_file():
            return candidate
    return None


def parse(text: str) -> dict[str, str]:
    """`KEY=value` per line. Comments, blanks and `export ` prefixes tolerated."""
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.removeprefix("export ").partition("=")
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def load(path: Path | None = None, *, force: bool = False) -> dict[str, str]:
    """Read `.env` into `os.environ` without clobbering what is already set.

    Returns the keys it actually applied, so a caller can tell the difference
    between "no file" and "file, but every value was already in the environment".
    """
    global _loaded
    if _loaded and not force:
        return {}

    env_file = path or find_env_file()
    _loaded = True
    # An explicitly passed path may not exist either, and a missing file is a
    # normal state — a fresh checkout has no .env at all.
    if env_file is None or not env_file.is_file():
        return {}

    applied = {}
    for key, value in parse(env_file.read_text()).items():
        if os.environ.get(key):          # real environment wins
            continue
        os.environ[key] = value
        applied[key] = value
    return applied
