from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from typing import Any


_TASK_KIND_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_SCHEMA_VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+$")


def canonical_task_request_bytes(
    *,
    task_kind: str,
    schema_version: str,
    request_payload: Mapping[str, Any],
) -> bytes:
    if not isinstance(task_kind, str) or not _TASK_KIND_PATTERN.fullmatch(task_kind):
        raise ValueError("task_kind must be a safe canonical identifier")
    if (
        not isinstance(schema_version, str)
        or not _SCHEMA_VERSION_PATTERN.fullmatch(schema_version)
    ):
        raise ValueError("schema_version must be a canonical major.minor value")
    if not isinstance(request_payload, Mapping):
        raise ValueError("request payload must be canonical JSON")

    normalized_request = _copy_json_object(request_payload)
    envelope = {
        "request": normalized_request,
        "schema_version": schema_version,
        "task_kind": task_kind,
    }
    try:
        serialized = json.dumps(
            envelope,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("request payload must be canonical JSON") from exc
    return serialized.encode("utf-8")


def compute_task_request_fingerprint(
    *,
    task_kind: str,
    schema_version: str,
    request_payload: Mapping[str, Any],
) -> str:
    return hashlib.sha256(
        canonical_task_request_bytes(
            task_kind=task_kind,
            schema_version=schema_version,
            request_payload=request_payload,
        )
    ).hexdigest()


def _copy_json_object(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = _copy_json_value(value)
    if not isinstance(copied, dict):
        raise ValueError("request payload must be canonical JSON")
    return copied


def _copy_json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("request payload must be canonical JSON")
        return value
    if isinstance(value, list):
        return [_copy_json_value(item) for item in value]
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("request payload must be canonical JSON")
        return {
            key: _copy_json_value(item)
            for key, item in value.items()
        }
    raise ValueError("request payload must be canonical JSON")


__all__ = [
    "canonical_task_request_bytes",
    "compute_task_request_fingerprint",
]
