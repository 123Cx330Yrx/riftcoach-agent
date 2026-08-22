from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.tasks.models import TaskStatus
from app.tasks.reliable_runtime import (
    TaskCancelDisposition,
    TaskCancelResult,
    TaskCheckpointPhase,
    TaskCheckpointReference,
    TaskLease,
    TaskLeasePolicy,
    TaskEventPage,
    TaskLifecycleEvent,
    TaskLifecycleEventKind,
    project_task_lifecycle,
)


NOW = datetime(2026, 8, 22, 13, 30, tzinfo=timezone.utc)
TASK_ID = UUID("81000000-0000-4000-8000-000000000001")
RUN_ID = "review_reliable_contract_1"
OWNER_ID = "owner-reliable-contract"
TOKEN = "a" * 64


def event(
    *,
    cursor: int,
    sequence: int,
    kind: TaskLifecycleEventKind,
    status: TaskStatus,
    generation: int,
    operation: str,
    worker_id: str | None = None,
    reason: str | None = None,
    checkpoint: TaskCheckpointReference | None = None,
) -> TaskLifecycleEvent:
    return TaskLifecycleEvent.create(
        event_cursor=cursor,
        task_sequence=sequence,
        task_id=TASK_ID,
        run_id=RUN_ID,
        owner_id=OWNER_ID,
        event_kind=kind,
        status_after=status,
        lease_generation=generation,
        worker_id=worker_id,
        operation_identity=operation,
        reason=reason,
        checkpoint_reference=checkpoint,
        occurred_at=NOW + timedelta(seconds=sequence),
    )


def test_lease_policy_requires_heartbeat_well_inside_lease() -> None:
    policy = TaskLeasePolicy()

    assert policy.lease_seconds == 120
    assert policy.heartbeat_seconds == 30
    assert policy.recovery_batch_size == 25
    assert policy.max_recoveries == 3

    with pytest.raises(ValidationError, match="heartbeat_seconds"):
        TaskLeasePolicy(lease_seconds=30, heartbeat_seconds=15)


def test_lease_token_is_private_and_expiry_is_strict() -> None:
    lease = TaskLease(
        worker_id="worker-reliable-1",
        generation=1,
        token=TOKEN,
        acquired_at=NOW,
        heartbeat_at=NOW,
        expires_at=NOW + timedelta(seconds=120),
    )

    assert "token" not in repr(lease)
    assert "token" not in lease.model_dump(mode="json")
    assert lease.private_token == TOKEN

    with pytest.raises(ValidationError, match="expires_at"):
        TaskLease(
            worker_id="worker-reliable-1",
            generation=1,
            token=TOKEN,
            acquired_at=NOW,
            heartbeat_at=NOW,
            expires_at=NOW,
        )


def test_checkpoint_only_claimed_safe_can_be_replayed() -> None:
    safe = TaskCheckpointReference(
        checkpoint_id="claimed-1",
        run_id=RUN_ID,
        checkpoint_sequence=1,
        lease_generation=1,
        phase=TaskCheckpointPhase.CLAIMED_SAFE,
        safe_to_replay=True,
        created_at=NOW,
    )
    started = safe.model_copy(
        update={
            "checkpoint_id": "started-2",
            "checkpoint_sequence": 2,
            "phase": TaskCheckpointPhase.EXECUTION_STARTED,
            "safe_to_replay": False,
        }
    )

    assert safe.safe_to_replay is True
    assert started.safe_to_replay is False
    with pytest.raises(ValidationError, match="claimed_safe"):
        TaskCheckpointReference(
            checkpoint_id="unsafe-claimed",
            run_id=RUN_ID,
            checkpoint_sequence=1,
            lease_generation=1,
            phase=TaskCheckpointPhase.CLAIMED_SAFE,
            safe_to_replay=False,
            created_at=NOW,
        )


def test_cancel_result_has_a_stable_body_free_shape() -> None:
    result = TaskCancelResult(
        task_id=TASK_ID,
        disposition=TaskCancelDisposition.REQUESTED,
        status=TaskStatus.RUNNING,
    )

    assert result.model_dump(mode="json") == {
        "schema_version": "1.0",
        "task_id": str(TASK_ID),
        "disposition": "requested",
        "status": "running",
    }
    with pytest.raises(ValidationError):
        TaskCancelResult.model_validate(
            {
                **result.model_dump(mode="python"),
                "request_payload": {"prompt": "must-not-appear"},
            }
        )


def test_event_identity_is_deterministic_and_excludes_cursor() -> None:
    first = event(
        cursor=1,
        sequence=1,
        kind=TaskLifecycleEventKind.CREATED,
        status=TaskStatus.QUEUED,
        generation=0,
        operation="created",
    )
    replayed_page = first.model_copy(update={"event_cursor": 99})

    assert first.event_identity == replayed_page.event_identity
    assert first.has_valid_identity()
    assert replayed_page.has_valid_identity()


def test_event_rejects_tampered_identity_and_arbitrary_body() -> None:
    created = event(
        cursor=1,
        sequence=1,
        kind=TaskLifecycleEventKind.CREATED,
        status=TaskStatus.QUEUED,
        generation=0,
        operation="created",
    )

    assert not created.model_copy(update={"reason": "tampered"}).has_valid_identity()
    assert not created.model_copy(
        update={"occurred_at": created.occurred_at + timedelta(seconds=1)}
    ).has_valid_identity()
    with pytest.raises(ValidationError):
        TaskLifecycleEvent.model_validate(
            {
                **created.model_dump(mode="python"),
                "payload": {"report": "must-not-appear"},
            }
        )


def test_projector_replays_claim_heartbeat_checkpoint_and_success() -> None:
    checkpoint = TaskCheckpointReference(
        checkpoint_id="started-1",
        run_id=RUN_ID,
        checkpoint_sequence=2,
        lease_generation=1,
        phase=TaskCheckpointPhase.EXECUTION_STARTED,
        safe_to_replay=False,
        created_at=NOW + timedelta(seconds=3),
    )
    events = (
        event(
            cursor=10,
            sequence=1,
            kind=TaskLifecycleEventKind.CREATED,
            status=TaskStatus.QUEUED,
            generation=0,
            operation="created",
        ),
        event(
            cursor=12,
            sequence=2,
            kind=TaskLifecycleEventKind.CLAIMED,
            status=TaskStatus.RUNNING,
            generation=1,
            operation="claim-1",
            worker_id="worker-reliable-1",
        ),
        event(
            cursor=15,
            sequence=3,
            kind=TaskLifecycleEventKind.EXECUTION_STARTED,
            status=TaskStatus.RUNNING,
            generation=1,
            operation="checkpoint-started-1",
            worker_id="worker-reliable-1",
            checkpoint=checkpoint,
        ),
        event(
            cursor=18,
            sequence=4,
            kind=TaskLifecycleEventKind.HEARTBEAT,
            status=TaskStatus.RUNNING,
            generation=1,
            operation="heartbeat-1",
            worker_id="worker-reliable-1",
        ),
        event(
            cursor=20,
            sequence=5,
            kind=TaskLifecycleEventKind.SUCCEEDED,
            status=TaskStatus.SUCCEEDED,
            generation=1,
            operation="succeeded-1",
            worker_id="worker-reliable-1",
            reason="quality_gate_passed",
        ),
    )

    projection = project_task_lifecycle(events)

    assert projection.task_id == TASK_ID
    assert projection.status is TaskStatus.SUCCEEDED
    assert projection.lease_generation == 1
    assert projection.last_cursor == 20
    assert projection.last_sequence == 5
    assert projection.checkpoint_reference == checkpoint
    assert projection.terminal_seen is True


def test_projector_tracks_cancel_request_before_cancel_terminal() -> None:
    projection = project_task_lifecycle(
        (
            event(
                cursor=1,
                sequence=1,
                kind=TaskLifecycleEventKind.CREATED,
                status=TaskStatus.QUEUED,
                generation=0,
                operation="created",
            ),
            event(
                cursor=2,
                sequence=2,
                kind=TaskLifecycleEventKind.CLAIMED,
                status=TaskStatus.RUNNING,
                generation=1,
                operation="claim-1",
                worker_id="worker-reliable-1",
            ),
            event(
                cursor=3,
                sequence=3,
                kind=TaskLifecycleEventKind.CANCEL_REQUESTED,
                status=TaskStatus.RUNNING,
                generation=1,
                operation="cancel-request-1",
                worker_id="worker-reliable-1",
                reason="user_requested",
            ),
            event(
                cursor=4,
                sequence=4,
                kind=TaskLifecycleEventKind.CANCELLED,
                status=TaskStatus.CANCELLED,
                generation=1,
                operation="cancelled-1",
                worker_id="worker-reliable-1",
                reason="user_requested",
            ),
        )
    )

    assert projection.cancel_requested is True
    assert projection.status is TaskStatus.CANCELLED
    assert projection.terminal_seen is True


@pytest.mark.parametrize(
    "mutate",
    (
        lambda items: (items[0], items[2]),
        lambda items: (items[1], items[0], items[2]),
        lambda items: (
            items[0],
            items[1].model_copy(update={"event_identity": "f" * 64}),
            items[2],
        ),
    ),
)
def test_projector_rejects_sequence_cursor_and_identity_drift(mutate) -> None:
    items = (
        event(
            cursor=1,
            sequence=1,
            kind=TaskLifecycleEventKind.CREATED,
            status=TaskStatus.QUEUED,
            generation=0,
            operation="created",
        ),
        event(
            cursor=2,
            sequence=2,
            kind=TaskLifecycleEventKind.CLAIMED,
            status=TaskStatus.RUNNING,
            generation=1,
            operation="claim-1",
            worker_id="worker-reliable-1",
        ),
        event(
            cursor=3,
            sequence=3,
            kind=TaskLifecycleEventKind.FAILED,
            status=TaskStatus.FAILED,
            generation=1,
            operation="failed-1",
            worker_id="worker-reliable-1",
            reason="worker_execution_failed",
        ),
    )

    with pytest.raises(ValueError):
        project_task_lifecycle(mutate(items))


def test_projector_rejects_duplicate_or_late_terminal() -> None:
    created = event(
        cursor=1,
        sequence=1,
        kind=TaskLifecycleEventKind.CREATED,
        status=TaskStatus.QUEUED,
        generation=0,
        operation="created",
    )
    cancelled = event(
        cursor=2,
        sequence=2,
        kind=TaskLifecycleEventKind.CANCELLED,
        status=TaskStatus.CANCELLED,
        generation=0,
        operation="cancelled-before-claim",
        reason="user_requested",
    )
    late = event(
        cursor=3,
        sequence=3,
        kind=TaskLifecycleEventKind.SUCCEEDED,
        status=TaskStatus.SUCCEEDED,
        generation=1,
        operation="late-success",
        worker_id="worker-reliable-1",
        reason="quality_gate_passed",
    )

    with pytest.raises(ValueError, match="terminal"):
        project_task_lifecycle((created, cancelled, late))


def test_checkpoint_timestamp_is_part_of_event_identity() -> None:
    checkpoint = TaskCheckpointReference(
        checkpoint_id="started-identity-1",
        run_id=RUN_ID,
        checkpoint_sequence=2,
        lease_generation=1,
        phase=TaskCheckpointPhase.EXECUTION_STARTED,
        safe_to_replay=False,
        created_at=NOW,
    )
    started = event(
        cursor=2,
        sequence=2,
        kind=TaskLifecycleEventKind.EXECUTION_STARTED,
        status=TaskStatus.RUNNING,
        generation=1,
        operation="started-identity-1",
        worker_id="worker-reliable-1",
        checkpoint=checkpoint,
    )

    changed = started.model_copy(
        update={
            "checkpoint_reference": checkpoint.model_copy(
                update={"created_at": NOW + timedelta(seconds=1)}
            )
        }
    )

    assert started.has_valid_identity()
    assert not changed.has_valid_identity()


def test_event_page_rejects_cursor_order_and_cross_task_drift() -> None:
    first = event(
        cursor=7,
        sequence=1,
        kind=TaskLifecycleEventKind.CREATED,
        status=TaskStatus.QUEUED,
        generation=0,
        operation="created",
    )
    claimed = event(
        cursor=9,
        sequence=2,
        kind=TaskLifecycleEventKind.CLAIMED,
        status=TaskStatus.RUNNING,
        generation=1,
        operation="claim-1",
        worker_id="worker-reliable-1",
    )

    with pytest.raises(ValidationError):
        TaskEventPage(
            after_cursor=0,
            next_cursor=7,
            limit=2,
            has_more=False,
            events=(claimed, first),
        )
    with pytest.raises(ValidationError):
        TaskEventPage(
            after_cursor=0,
            next_cursor=9,
            limit=2,
            has_more=False,
            events=(
                first,
                claimed.model_copy(
                    update={
                        "task_id": UUID(
                            "81000000-0000-4000-8000-000000000002"
                        )
                    }
                ),
            ),
        )


@pytest.mark.parametrize(
    ("kind", "status"),
    (
        (TaskLifecycleEventKind.CANCEL_REQUESTED, TaskStatus.RUNNING),
        (TaskLifecycleEventKind.RECOVERY_REQUEUED, TaskStatus.QUEUED),
        (TaskLifecycleEventKind.RECOVERY_REQUIRED, TaskStatus.RECOVERY_REQUIRED),
    ),
)
def test_owned_control_events_require_generation_and_worker(kind, status) -> None:
    with pytest.raises(ValidationError, match="owned"):
        event(
            cursor=2,
            sequence=2,
            kind=kind,
            status=status,
            generation=0,
            operation=f"invalid-{kind.value}",
        )
