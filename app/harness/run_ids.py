"""Portable run namespace identifiers shared by Harness entry points."""

from __future__ import annotations

import re


_RUN_ID_PATTERN = re.compile(
    r"^[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9_-])?$"
)
_WINDOWS_RESERVED_STEMS = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


def normalize_run_id(run_id: str) -> str:
    """Return one portable directory component or fail closed."""

    if not isinstance(run_id, str):
        raise ValueError("run_id must be a string")
    normalized = run_id.strip()
    if not _RUN_ID_PATTERN.fullmatch(normalized):
        raise ValueError(
            "run_id must be 1-128 ASCII letters, digits, dots, underscores, "
            "or hyphens; it must start with a letter or digit and must not "
            "end with a dot"
        )
    stem = normalized.split(".", maxsplit=1)[0].upper()
    if stem in _WINDOWS_RESERVED_STEMS:
        raise ValueError("run_id must not use a Windows reserved device name")
    return normalized
