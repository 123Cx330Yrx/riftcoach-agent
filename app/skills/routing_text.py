"""Shared text normalization for deterministic Skill routing."""

from __future__ import annotations

import unicodedata


def normalize_routing_text(value: str) -> str:
    """Return a case-folded alphanumeric form for literal signal matching."""

    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(character for character in normalized if character.isalnum())
