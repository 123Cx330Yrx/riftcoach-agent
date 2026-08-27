"""Project a Dragon video HTTP error into a bounded, body-free diagnostic."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from typing import Any


_OUTER_FIELDS = frozenset({"code", "message", "data"})
_NESTED_FIELDS = frozenset({"error"})
_ERROR_FIELDS = frozenset({"code", "message", "param", "type"})
_IDENTIFIER = re.compile(r"^[A-Za-z0-9_.\[\]-]{1,128}$")
_REQUEST_ID = re.compile(
    r"(?i)(request\s*id\s*:\s*)[A-Za-z0-9_.:-]{6,256}"
)
_SENSITIVE_MESSAGE = re.compile(
    r"(?i)(https?://|bearer\s+|\bsk-[A-Za-z0-9_-]+|"
    r"access[_-]?key|security[_-]?token|signature=|authorization)"
)
_MAX_BODY_BYTES = 64 * 1024
_MAX_MESSAGE_CHARS = 800


def _base_diagnostic(raw: bytes, http_status: int) -> dict[str, Any]:
    return {
        "http_status": http_status,
        "raw_body_length": len(raw),
        "raw_body_sha256": hashlib.sha256(raw).hexdigest(),
    }


def _parse_object(value: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _safe_identifier(value: Any) -> str | None:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        return None
    return value


def _safe_message(value: Any) -> str | None:
    if not isinstance(value, str) or not value or len(value) > _MAX_MESSAGE_CHARS:
        return None
    message = _REQUEST_ID.sub(r"\1[redacted]", value)
    if _SENSITIVE_MESSAGE.search(message):
        return None
    if any(ord(character) < 32 and character not in "\t" for character in message):
        return None
    return message


def sanitize_dragon_video_error(body: str, *, http_status: int) -> dict[str, Any]:
    """Return allowlisted fields or only a digest when the shape is not trusted."""

    raw = body.encode("utf-8")
    diagnostic = _base_diagnostic(raw, http_status)
    if not raw or len(raw) > _MAX_BODY_BYTES:
        return diagnostic

    outer = _parse_object(body)
    if outer is None or not set(outer).issubset(_OUTER_FIELDS):
        return diagnostic
    outer_code = _safe_identifier(outer.get("code"))
    nested = _parse_object(outer.get("message"))
    if outer_code is None or nested is None or set(nested) != _NESTED_FIELDS:
        return diagnostic
    error = nested.get("error")
    if not isinstance(error, dict) or set(error) != _ERROR_FIELDS:
        return diagnostic

    remote_code = _safe_identifier(error.get("code"))
    remote_param = _safe_identifier(error.get("param"))
    remote_type = _safe_identifier(error.get("type"))
    remote_message = _safe_message(error.get("message"))
    if None in (remote_code, remote_param, remote_type, remote_message):
        return diagnostic

    return {
        "http_status": http_status,
        "outer_code": outer_code,
        "remote_error_code": remote_code,
        "remote_error_param": remote_param,
        "remote_error_type": remote_type,
        "remote_message": remote_message,
        "raw_body_length": diagnostic["raw_body_length"],
        "raw_body_sha256": diagnostic["raw_body_sha256"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--http-status", type=int, required=True)
    args = parser.parse_args(argv)
    body = sys.stdin.read(_MAX_BODY_BYTES + 1)
    diagnostic = sanitize_dragon_video_error(body, http_status=args.http_status)
    json.dump(diagnostic, sys.stdout, ensure_ascii=True, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
