from __future__ import annotations

import os
import time

import pytest

from app.tasks.models import TaskCapacityPolicy
from app.tasks.observability import percentile
from tests.test_task_lifecycle_postgres import migrated_repository, pending


def test_performance_targets_are_named_as_baselines_not_slas() -> None:
    result = percentile([100, 120, 140, 160], 0.95)

    assert result.sample_count == 4
    assert result.value_ms >= 100
    assert result.target_name == "p95"


def test_warm_database_create_query_p95_has_samples_and_environment_boundary() -> None:
    with migrated_repository() as repository:
        samples: list[float] = []
        policy = TaskCapacityPolicy(owner_active_limit=20, global_active_limit=50)
        warmup = repository.create_or_replay(
            pending(99),
            capacity=policy,
        ).task
        assert warmup is not None
        assert repository.get_by_task_id(
            owner_id=warmup.owner_id,
            task_id=warmup.task_id,
        ) is not None
        for number in range(1, 9):
            started = time.perf_counter()
            task = repository.create_or_replay(
                pending(100 + number),
                capacity=policy,
            ).task
            assert task is not None
            queried = repository.get_by_task_id(
                owner_id=task.owner_id,
                task_id=task.task_id,
            )
            assert queried is not None
            samples.append((time.perf_counter() - started) * 1000)

        result = percentile(samples, 0.95)
        environment = _benchmark_environment()

        print(
            "task_performance_baseline "
            f"environment={environment} metric=create_query_p95 "
            f"samples={result.sample_count} p95_ms={result.value_ms:.3f} "
            "target_ms=300"
        )

        assert result.sample_count == 8
        assert result.value_ms < 300, (
            "warm-DB control-plane p95 target exceeded; this measures SQL "
            "create/query only, not Provider or Agent latency"
        )


def test_postgres_claim_delay_p95_has_samples_and_two_second_target() -> None:
    with migrated_repository() as repository:
        policy = TaskCapacityPolicy(owner_active_limit=20, global_active_limit=50)
        for number in range(1, 9):
            assert repository.create_or_replay(
                pending(200 + number),
                capacity=policy,
            ).task is not None

        samples: list[float] = []
        queued_at = time.perf_counter()
        for _ in range(8):
            claimed = repository.claim_next(
                worker_id="benchmark-worker",
                now=pending(1).created_at,
            )
            assert claimed is not None
            samples.append((time.perf_counter() - queued_at) * 1000)

        result = percentile(samples, 0.95)
        environment = _benchmark_environment()

        print(
            "task_performance_baseline "
            f"environment={environment} metric=queued_to_claim_p95 "
            f"samples={result.sample_count} p95_ms={result.value_ms:.3f} "
            "target_ms=2000"
        )

        assert result.sample_count == 8
        assert result.value_ms < 2_000, (
            "claim p95 target exceeded; report the sample count and CI "
            "environment before changing the target"
        )


def _benchmark_environment() -> str:
    return (
        "github-actions-postgresql-17-python-3.11"
        if os.getenv("GITHUB_ACTIONS") == "true"
        else "local-postgresql-python-3.11"
    )
