from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.tasks.models import (
    CreateReviewTaskCommand,
    ReviewTask,
    ReviewTaskView,
    TaskCapacityPolicy,
    TaskCreateDisposition,
    TaskCreateResult,
    TaskPublicationStatus,
    TaskStatus,
    TaskTerminal,
)
from app.product.recent_review import RecentReviewProductRequest
from app.product.run_receipts import RunReceiptReference
from app.runtime.models import RuntimeArtifactReference, RuntimeTraceReference
from app.tasks.reliable_runtime import TaskLease


TASK_ID = UUID("11111111-1111-4111-8111-111111111111")
NOW = datetime(2026, 8, 18, 1, 2, 3, tzinfo=timezone.utc)


def queued_task(**changes: object) -> ReviewTask:
    values: dict[str, object] = {
        "task_id": TASK_ID,
        "run_id": "review_task_models",
        "task_kind": "recent_review",
        "schema_version": "1.0",
        "owner_id": "owner-1",
        "idempotency_key": "request-1",
        "request_fingerprint": "a" * 64,
        "request_payload": {
            "riot_id": "DemoPlayer#TEST",
            "count": 10,
            "queue": 420,
            "focus": "overall",
        },
        "status": TaskStatus.QUEUED,
        "worker_id": None,
        "created_at": NOW,
        "updated_at": NOW,
        "claimed_at": None,
        "finished_at": None,
        "terminal_reason": None,
        "publication_status": None,
        "report_available": False,
        "trace_reference": None,
        "receipt_reference": None,
        "artifact_reference": None,
    }
    values.update(changes)
    return ReviewTask(**values)  # type: ignore[arg-type]


def terminal_evidence(run_id: str = "review_task_models") -> dict[str, object]:
    return {
        "trace_reference": RuntimeTraceReference(
            run_id=run_id,
            sha256="a" * 64,
        ),
        "receipt_reference": RunReceiptReference(
            run_id=run_id,
            sha256="b" * 64,
        ),
        "artifact_reference": RuntimeArtifactReference(
            kind="final_report",
            schema_version="1.0",
            relative_path="output/final_report.md",
            sha256="c" * 64,
            producer="review_harness.publisher",
        ),
    }


def test_task_status_contract_includes_reliable_recovery_and_cancel_states() -> None:
    assert tuple(status.value for status in TaskStatus) == (
        "queued",
        "running",
        "recovery_required",
        "succeeded",
        "failed",
        "cancelled",
    )


def test_create_command_is_strict_frozen_and_normalizes_only_product_request() -> None:
    command = CreateReviewTaskCommand(
        owner_id="owner-1",
        idempotency_key="request-1",
        request=RecentReviewProductRequest(riot_id="  DemoPlayer#TEST  "),
    )

    assert command.owner_id == "owner-1"
    assert command.idempotency_key == "request-1"
    assert command.request.riot_id == "DemoPlayer#TEST"
    with pytest.raises(ValidationError, match="frozen"):
        command.owner_id = "owner-2"


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("owner_id", " owner-1"),
        ("owner_id", "owner/1"),
        ("owner_id", "o" * 129),
        ("idempotency_key", "request 1"),
        ("idempotency_key", "r" * 129),
        ("idempotency_key", 123),
    ),
)
def test_create_command_rejects_unsafe_or_coerced_identity_fields(
    field: str,
    value: object,
) -> None:
    payload: dict[str, object] = {
        "owner_id": "owner-1",
        "idempotency_key": "request-1",
        "request": RecentReviewProductRequest(riot_id="DemoPlayer#TEST"),
    }
    payload[field] = value

    with pytest.raises(ValidationError):
        CreateReviewTaskCommand(**payload)  # type: ignore[arg-type]


def test_task_normalizes_aware_datetimes_to_utc_and_projects_body_free_view() -> None:
    offset_time = NOW.astimezone(timezone(timedelta(hours=8)))
    task = queued_task(created_at=offset_time, updated_at=offset_time)

    assert task.created_at == NOW
    assert task.updated_at == NOW
    view = ReviewTaskView.from_task(task)
    payload = view.model_dump(mode="json")

    assert payload == {
        "schema_version": "1.0",
        "task_id": str(TASK_ID),
        "run_id": "review_task_models",
        "status": "queued",
        "created_at": "2026-08-18T01:02:03Z",
        "updated_at": "2026-08-18T01:02:03Z",
        "claimed_at": None,
        "finished_at": None,
        "terminal_reason": None,
        "publication_status": None,
        "report_available": False,
    }
    assert "owner_id" not in payload
    assert "idempotency_key" not in payload
    assert "request_payload" not in payload
    assert "worker_id" not in payload
    assert "trace_reference" not in payload


def test_task_rejects_naive_or_reverse_ordered_timestamps() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        queued_task(created_at=NOW.replace(tzinfo=None))
    with pytest.raises(ValidationError, match="updated_at"):
        queued_task(updated_at=NOW - timedelta(seconds=1))


def test_running_and_terminal_state_invariants_are_explicit() -> None:
    claimed = NOW + timedelta(seconds=1)
    finished = NOW + timedelta(seconds=2)

    running = queued_task(
        status=TaskStatus.RUNNING,
        worker_id="worker-1",
        updated_at=claimed,
        claimed_at=claimed,
        lease_generation=1,
        lease=TaskLease(
            worker_id="worker-1",
            generation=1,
            token="d" * 64,
            acquired_at=claimed,
            heartbeat_at=claimed,
            expires_at=finished,
        ),
    )
    assert running.status is TaskStatus.RUNNING

    succeeded = queued_task(
        status=TaskStatus.SUCCEEDED,
        worker_id="worker-1",
        updated_at=finished,
        claimed_at=claimed,
        finished_at=finished,
        terminal_reason="review_completed",
        publication_status=TaskPublicationStatus.PUBLISHED,
        report_available=True,
        **terminal_evidence(),
    )
    assert succeeded.publication_status is TaskPublicationStatus.PUBLISHED

    failed = queued_task(
        status=TaskStatus.FAILED,
        worker_id="worker-1",
        updated_at=finished,
        claimed_at=claimed,
        finished_at=finished,
        terminal_reason="worker_interrupted",
    )
    assert failed.publication_status is None


@pytest.mark.parametrize(
    "changes",
    (
        {"worker_id": "worker-1"},
        {"status": TaskStatus.RUNNING},
        {
            "status": TaskStatus.SUCCEEDED,
            "worker_id": "worker-1",
            "claimed_at": NOW,
            "finished_at": NOW,
            "terminal_reason": "review_completed",
        },
        {
            "status": TaskStatus.FAILED,
            "worker_id": "worker-1",
            "claimed_at": NOW,
            "finished_at": NOW,
            "terminal_reason": "worker_interrupted",
            "publication_status": TaskPublicationStatus.DEGRADED,
        },
        {"publication_status": TaskPublicationStatus.PUBLISHED},
        {"report_available": True},
    ),
)
def test_task_rejects_invalid_lifecycle_or_publication_shapes(
    changes: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        queued_task(**changes)


def test_cancel_request_shape_matches_the_only_legal_lifecycle_states() -> None:
    cancel = {
        "cancel_request_id": "cancel-request-1",
        "cancel_requested_at": NOW,
        "cancel_reason": "user_requested",
    }

    with pytest.raises(ValidationError, match="cancel"):
        queued_task(**cancel)
    with pytest.raises(ValidationError, match="cancel"):
        queued_task(
            status=TaskStatus.CANCELLED,
            updated_at=NOW,
            finished_at=NOW,
            terminal_reason="user_requested",
        )

    cancelled = queued_task(
        status=TaskStatus.CANCELLED,
        updated_at=NOW,
        finished_at=NOW,
        terminal_reason="user_requested",
        **cancel,
    )
    assert cancelled.cancel_request_id == "cancel-request-1"


def test_capacity_policy_is_bounded_and_global_cannot_be_below_owner() -> None:
    assert TaskCapacityPolicy() == TaskCapacityPolicy(
        owner_active_limit=3,
        global_active_limit=50,
    )
    with pytest.raises(ValidationError):
        TaskCapacityPolicy(owner_active_limit=0)
    with pytest.raises(ValidationError, match="global_active_limit"):
        TaskCapacityPolicy(owner_active_limit=4, global_active_limit=3)


def test_success_terminal_requires_cross_store_evidence_for_the_same_run() -> None:
    terminal = TaskTerminal(
        run_id="review_task_models",
        terminal_reason="quality_gate_passed",
        publication_status=TaskPublicationStatus.PUBLISHED,
        report_available=True,
        **terminal_evidence(),
    )

    assert terminal.trace_reference.run_id == terminal.run_id
    assert terminal.receipt_reference.run_id == terminal.run_id
    assert terminal.artifact_reference is not None

    with pytest.raises(ValidationError, match="receipt_reference"):
        TaskTerminal(
            run_id="review_task_models",
            terminal_reason="quality_gate_passed",
            publication_status=TaskPublicationStatus.PUBLISHED,
            report_available=True,
            trace_reference=terminal.trace_reference,
            receipt_reference=None,
            artifact_reference=terminal.artifact_reference,
        )

    with pytest.raises(ValidationError, match="run_id"):
        TaskTerminal(
            run_id="review_task_models",
            terminal_reason="quality_gate_passed",
            publication_status=TaskPublicationStatus.PUBLISHED,
            report_available=True,
            trace_reference=terminal.trace_reference.model_copy(
                update={"run_id": "review_other"}
            ),
            receipt_reference=terminal.receipt_reference,
            artifact_reference=terminal.artifact_reference,
        )


def test_create_result_distinguishes_created_from_replayed_without_body() -> None:
    view = ReviewTaskView.from_task(queued_task())
    result = TaskCreateResult(
        disposition=TaskCreateDisposition.CREATED,
        task=view,
    )

    payload = result.model_dump(mode="json")
    assert payload["disposition"] == "created"
    assert payload["task"]["task_id"] == str(TASK_ID)
    assert "request_payload" not in payload["task"]
