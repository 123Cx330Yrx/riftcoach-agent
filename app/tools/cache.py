"""Small bounded in-memory TTL cache for deterministic tool results."""

from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable, Mapping


def make_cache_key(
    tool_name: str,
    tool_version: str,
    params: Mapping[str, Any],
) -> str:
    """Build a stable, opaque key without exposing raw business parameters."""

    canonical = json.dumps(
        {
            "tool_name": tool_name,
            "tool_version": tool_version,
            "params": params,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"{tool_name}:{tool_version}:{digest}"


@dataclass
class _CacheEntry:
    value: Mapping[str, Any]
    expires_at: float


class TTLCache:
    """Process-local LRU cache whose entries expire after a bounded TTL."""

    def __init__(
        self,
        *,
        max_entries: int = 256,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be at least 1")
        self._max_entries = max_entries
        self._clock = clock
        self._entries: OrderedDict[str, _CacheEntry] = OrderedDict()

    def get(self, key: str) -> Mapping[str, Any] | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.expires_at <= self._clock():
            del self._entries[key]
            return None
        self._entries.move_to_end(key)
        return deepcopy(entry.value)

    def set(
        self,
        key: str,
        value: Mapping[str, Any],
        *,
        ttl_s: float,
    ) -> None:
        if ttl_s < 0:
            raise ValueError("ttl_s cannot be negative")
        if ttl_s == 0:
            return

        self._purge_expired()
        self._entries[key] = _CacheEntry(
            value=deepcopy(value),
            expires_at=self._clock() + ttl_s,
        )
        self._entries.move_to_end(key)

        while len(self._entries) > self._max_entries:
            self._entries.popitem(last=False)

    def clear(self) -> None:
        self._entries.clear()

    def _purge_expired(self) -> None:
        now = self._clock()
        expired = [
            key
            for key, entry in self._entries.items()
            if entry.expires_at <= now
        ]
        for key in expired:
            del self._entries[key]

    def __len__(self) -> int:
        self._purge_expired()
        return len(self._entries)

