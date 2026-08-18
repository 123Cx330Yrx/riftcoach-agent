from __future__ import annotations

import logging

import pytest

from app.tasks.observability import (
    SAFE_METADATA_FIELDS,
    TaskObservability,
    percentile,
)
from app.tasks.models import TaskStatus


def test_structured_observability_keeps_only_allowlisted_metadata(
    caplog: pytest.LogCaptureFixture,
) -> None:
    observer = TaskObservability(logger_name="riftcoach.test.observability")

    with caplog.at_level(logging.INFO, logger="riftcoach.test.observability"):
        observer.emit(
            "task.completed",
            {
                "task_id": "task-1",
                "status": "succeeded",
                "latency_ms": 12,
                "riot_id": "MIDKING#asd",
                "prompt": "secret prompt body",
                "report": "private report",
                "api_key": "sk-live-secret",
                "exception": "postgres://user:password@db/private",
            },
        )

    assert observer.events[-1].metadata == {
        "task_id": "task-1",
        "status": "succeeded",
        "latency_ms": 12,
    }
    text = caplog.text
    assert "MIDKING" not in text
    assert "secret prompt body" not in text
    assert "private report" not in text
    assert "sk-live-secret" not in text
    assert "postgres://" not in text
    assert set(observer.events[-1].metadata).issubset(SAFE_METADATA_FIELDS)


def test_observability_counters_and_latency_snapshot_are_safe() -> None:
    observer = TaskObservability(logger_name="riftcoach.test.metrics")

    observer.increment("task.created")
    observer.increment("task.created", amount=2)
    observer.observe_latency("task.create", 10)
    observer.observe_latency("task.create", 30)

    snapshot = observer.snapshot()
    assert snapshot.counters["task.created"] == 3
    assert snapshot.latencies_ms["task.create"] == (10.0, 30.0)
    assert snapshot.public_metadata() == {
        "counter_names": ("task.created",),
        "latency_names": ("task.create",),
    }


@pytest.mark.parametrize(
    ("values", "expected"),
    (([10], 10.0), ([1, 2, 3, 4], 3.0), ([1, 2, 3, 4, 5], 4.0)),
)
def test_percentile_is_deterministic_and_reports_sample_count(
    values: list[float],
    expected: float,
) -> None:
    result = percentile(values, 0.75)

    assert result.value_ms == expected
    assert result.sample_count == len(values)


def test_percentile_rejects_empty_or_invalid_inputs() -> None:
    with pytest.raises(ValueError):
        percentile([], 0.95)
    with pytest.raises(ValueError):
        percentile([1, 2], 1.1)


def test_worker_observability_records_only_safe_terminal_metadata() -> None:
    from datetime import datetime, timezone
    from uuid import UUID

    from app.tasks.models import ReviewTask, TaskTerminal
    from app.workers.review_worker import ReviewWorker

    class Repository:
        def claim_next(self, *, worker_id, now):
            return ReviewTask(
                task_id=UUID("50000000-0000-4000-8000-000000000001"),
                run_id="review_observed_worker",
                task_kind="recent_review",
                schema_version="1.0",
                owner_id="owner-1",
                idempotency_key="key-1",
                request_fingerprint="1" * 64,
                request_payload={"riot_id": "private"},
                status=TaskStatus.RUNNING,
                worker_id=worker_id,
                created_at=now,
                updated_at=now,
                claimed_at=now,
                finished_at=None,
                terminal_reason=None,
                publication_status=None,
                report_available=False,
                trace_reference=None,
                receipt_reference=None,
                artifact_reference=None,
            )

        def succeed(self, *, task_id, worker_id, terminal):
            return True

        def fail(self, *, task_id, worker_id, reason):
            return True

    class Executor:
        def execute(self, task):
            from app.harness.models import ArtifactKind
            from app.runtime.models import RuntimeArtifactReference, RuntimeTraceReference
            from app.product.run_receipts import RunReceiptReference
            from app.tasks.models import TaskPublicationStatus

            return TaskTerminal(
                run_id=task.run_id,
                terminal_reason="quality_gate_passed",
                publication_status=TaskPublicationStatus.PUBLISHED,
                report_available=True,
                trace_reference=RuntimeTraceReference(
                    run_id=task.run_id,
                    trace_schema_version="1.1",
                    sha256="2" * 64,
                ),
                receipt_reference=RunReceiptReference(
                    run_id=task.run_id,
                    sha256="3" * 64,
                    ),
                    artifact_reference=RuntimeArtifactReference(
                        kind=ArtifactKind.FINAL_REPORT,
                    relative_path="report.md",
                    schema_version="1.0",
                    sha256="4" * 64,
                    producer="test",
                ),
            )

    observer = TaskObservability(logger_name="riftcoach.test.worker")
    worker = ReviewWorker(
        repository=Repository(),
        executor=Executor(),
        worker_id="worker-1",
        clock=lambda: datetime(2026, 8, 18, tzinfo=timezone.utc),
        observability=observer,
    )

    result = worker.run_once()

    assert result.status.value == "succeeded"
    assert any(event.name == "worker.terminal_committed" for event in observer.events)
    assert all("private" not in repr(event.metadata) for event in observer.events)
