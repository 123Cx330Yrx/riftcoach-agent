"""Length-limited JSONL framing for the Pi runtime experiment."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

from .models import MAX_FRAME_BYTES, PROTOCOL_VERSION


_FRAME_TYPES = frozenset(
    {
        "run.start",
        "tool.request",
        "tool.response",
        "event",
        "run.result",
        "protocol.error",
    }
)
_SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class PiProtocolError(ValueError):
    """Fail-closed framing error with a public-safe code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def encode_frame(frame: Mapping[str, Any]) -> bytes:
    if not isinstance(frame, Mapping):
        raise PiProtocolError("invalid_frame")
    try:
        payload = json.dumps(
            dict(frame),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8") + b"\n"
    except (TypeError, ValueError):
        raise PiProtocolError("invalid_frame") from None
    if len(payload) > MAX_FRAME_BYTES:
        raise PiProtocolError("frame_too_large")
    decode_frame(payload)
    return payload


def decode_frame(payload: bytes) -> dict[str, Any]:
    if not isinstance(payload, bytes):
        raise PiProtocolError("invalid_frame")
    if len(payload) > MAX_FRAME_BYTES:
        raise PiProtocolError("frame_too_large")
    if not payload.endswith(b"\n") or payload.count(b"\n") != 1:
        raise PiProtocolError("invalid_frame")
    try:
        value = json.loads(payload[:-1].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise PiProtocolError("invalid_json") from None
    if not isinstance(value, dict):
        raise PiProtocolError("invalid_frame")
    if value.get("protocol_version") != PROTOCOL_VERSION:
        raise PiProtocolError("protocol_version_mismatch")
    if value.get("type") not in _FRAME_TYPES:
        raise PiProtocolError("unsupported_frame_type")
    run_id = value.get("run_id")
    if not isinstance(run_id, str) or not _SAFE_ID_PATTERN.fullmatch(run_id):
        raise PiProtocolError("invalid_run_id")
    return value
