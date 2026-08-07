"""Deterministic byte encoding and hashing for Harness artifacts."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any


def encode_json_artifact(payload: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        + b"\n"
    )


def encode_text_artifact(content: str) -> bytes:
    return content.encode("utf-8")


def sha256_hex(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
