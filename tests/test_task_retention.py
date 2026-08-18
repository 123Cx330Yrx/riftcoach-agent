from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.tasks.retention import RetentionKind, RetentionPolicy, RetentionService
from scripts.purge_expired_task_data import purge_expired_task_data


NOW = datetime(2026, 8, 18, 12, 0, 0, tzinfo=timezone.utc)


def test_default_retention_policy_has_the_frozen_7_90_30_day_contract() -> None:
    policy = RetentionPolicy()

    assert policy.ttl_for(RetentionKind.RIOT_CACHE) == timedelta(days=7)
    assert policy.ttl_for(RetentionKind.TERMINAL_RUN) == timedelta(days=90)
    assert policy.ttl_for(RetentionKind.OPERATIONS_LOG) == timedelta(days=30)


@pytest.mark.parametrize(
    ("kind", "age", "expired"),
    (
        (RetentionKind.RIOT_CACHE, timedelta(days=6, hours=23), False),
        (RetentionKind.RIOT_CACHE, timedelta(days=7), True),
        (RetentionKind.TERMINAL_RUN, timedelta(days=89, hours=23), False),
        (RetentionKind.TERMINAL_RUN, timedelta(days=90), True),
        (RetentionKind.OPERATIONS_LOG, timedelta(days=30), True),
    ),
)
def test_retention_uses_injected_clock_and_expiry_boundary(
    kind: RetentionKind,
    age: timedelta,
    expired: bool,
) -> None:
    service = RetentionService(policy=RetentionPolicy(), clock=lambda: NOW)
    created_at = NOW - age

    assert service.is_expired(kind=kind, created_at=created_at) is expired


def test_retention_does_not_depend_on_wall_clock_argument() -> None:
    service = RetentionService(policy=RetentionPolicy(), clock=lambda: NOW)

    assert service.expiry_for(
        kind=RetentionKind.RIOT_CACHE,
        created_at=NOW,
    ) == NOW + timedelta(days=7)
    assert service.is_expired(
        kind=RetentionKind.RIOT_CACHE,
        created_at=NOW,
        now=NOW + timedelta(days=6, seconds=1),
    ) is False


@pytest.mark.parametrize(
    "kwargs",
    (
        {"riot_cache_days": 0},
        {"terminal_run_days": -1},
        {"operations_log_days": 1.5},
    ),
)
def test_retention_policy_rejects_invalid_ttls(kwargs: dict[str, object]) -> None:
    with pytest.raises((TypeError, ValueError)):
        RetentionPolicy(**kwargs)  # type: ignore[arg-type]


def test_purge_filesystem_roots_uses_the_same_injected_clock(tmp_path) -> None:
    cache = tmp_path / "cache"
    logs = tmp_path / "logs"
    cache.mkdir()
    logs.mkdir()
    old_cache = cache / "old.json"
    fresh_cache = cache / "fresh.json"
    old_log = logs / "old.log"
    old_cache.write_text("cache", encoding="utf-8")
    fresh_cache.write_text("cache", encoding="utf-8")
    old_log.write_text("log", encoding="utf-8")
    old_timestamp = (NOW - timedelta(days=8)).timestamp()
    fresh_timestamp = (NOW - timedelta(days=1)).timestamp()
    import os

    os.utime(old_cache, (old_timestamp, old_timestamp))
    os.utime(fresh_cache, (fresh_timestamp, fresh_timestamp))
    old_log_timestamp = (NOW - timedelta(days=31)).timestamp()
    os.utime(old_log, (old_log_timestamp, old_log_timestamp))

    report = purge_expired_task_data(
        runs_root=tmp_path / "runs",
        cache_root=cache,
        logs_root=logs,
        now=NOW,
    )

    assert report.filesystem_entries_removed == 2
    assert not old_cache.exists()
    assert fresh_cache.exists()
    assert not old_log.exists()
