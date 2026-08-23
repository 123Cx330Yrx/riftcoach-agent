from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from app.product.recent_review import RecentReviewProductRequest
from app.tasks.fingerprint import (
    canonical_task_request_bytes,
    compute_task_request_fingerprint,
)
from app.tasks.models import (
    CreateReviewTaskCommand,
    PendingReviewTask,
    ReviewTask,
    TaskCapacityPolicy,
    TaskCreateDisposition,
    TaskRepositoryCreateDisposition,
    TaskRepositoryCreateResult,
    TaskStatus,
)
from app.tasks.ports import TaskRepository, TaskRepositoryError
from app.tasks.service import ReviewTaskService, TaskServiceError
from app.tasks.reliable_runtime import (
    TaskCancelDisposition,
    TaskCancelResult,
    TaskEventPage,
    TaskLifecycleEvent,
    TaskLifecycleEventKind,
)


NOW = datetime(2026, 8, 18, 2, 0, 0, tzinfo=timezone.utc)
TASK_IDS = (
    UUID("10000000-0000-4000-8000-000000000001"),
    UUID("10000000-0000-4000-8000-000000000002"),
    UUID("10000000-0000-4000-8000-000000000003"),
    UUID("10000000-0000-4000-8000-000000000004"),
)


def command(
    *,
    owner_id: str = "owner-1",
    key: str = "request-1",
    focus: str = "overall",
) -> CreateReviewTaskCommand:
    return CreateReviewTaskCommand(
        owner_id=owner_id,
        idempotency_key=key,
        request=RecentReviewProductRequest(
            routing_region="asia",
            riot_id="DemoPlayer#TEST",
            focus=focus,
        ),
    )


def task_from_pending(pending: PendingReviewTask) -> ReviewTask:
    return ReviewTask(
        task_id=pending.task_id,
        run_id=pending.run_id,
        task_kind=pending.task_kind,
        schema_version=pending.schema_version,
        owner_id=pending.owner_id,
        idempotency_key=pending.idempotency_key,
        request_fingerprint=pending.request_fingerprint,
        request_payload=pending.request_payload,
        status=TaskStatus.QUEUED,
        worker_id=None,
        created_at=pending.created_at,
        updated_at=pending.created_at,
        claimed_at=None,
        finished_at=None,
        terminal_reason=None,
        publication_status=None,
        report_available=False,
        trace_reference=None,
        receipt_reference=None,
        artifact_reference=None,
    )


class FakeTaskRepository(TaskRepository):
    def __init__(self) -> None:
        self.tasks: list[ReviewTask] = []
        self.failure: Exception | None = None
        self.cancel_calls = []
        self.event_calls = []

    def create_or_replay(
        self,
        pending: PendingReviewTask,
        *,
        capacity: TaskCapacityPolicy,
    ) -> TaskRepositoryCreateResult:
        if self.failure is not None:
            raise self.failure
        existing = next(
            (
                task
                for task in self.tasks
                if task.owner_id == pending.owner_id
                and task.idempotency_key == pending.idempotency_key
            ),
            None,
        )
        if existing is not None:
            if existing.request_fingerprint == pending.request_fingerprint:
                return TaskRepositoryCreateResult(
                    disposition=TaskRepositoryCreateDisposition.REPLAYED,
                    task=existing,
                )
            return TaskRepositoryCreateResult(
                disposition=TaskRepositoryCreateDisposition.IDEMPOTENCY_CONFLICT,
            )

        active = {TaskStatus.QUEUED, TaskStatus.RUNNING}
        owner_active = sum(
            task.owner_id == pending.owner_id and task.status in active
            for task in self.tasks
        )
        global_active = sum(task.status in active for task in self.tasks)
        if owner_active >= capacity.owner_active_limit:
            return TaskRepositoryCreateResult(
                disposition=TaskRepositoryCreateDisposition.OWNER_CAPACITY_EXCEEDED,
            )
        if global_active >= capacity.global_active_limit:
            return TaskRepositoryCreateResult(
                disposition=TaskRepositoryCreateDisposition.GLOBAL_CAPACITY_EXCEEDED,
            )

        created = task_from_pending(pending)
        self.tasks.append(created)
        return TaskRepositoryCreateResult(
            disposition=TaskRepositoryCreateDisposition.CREATED,
            task=created,
        )

    def get_by_task_id(self, *, owner_id: str, task_id: UUID) -> ReviewTask | None:
        if self.failure is not None:
            raise self.failure
        return next(
            (
                task
                for task in self.tasks
                if task.owner_id == owner_id and task.task_id == task_id
            ),
            None,
        )

    def get_by_run_id(self, *, owner_id: str, run_id: str) -> ReviewTask | None:
        if self.failure is not None:
            raise self.failure
        return next(
            (
                task
                for task in self.tasks
                if task.owner_id == owner_id and task.run_id == run_id
            ),
            None,
        )

    def request_cancel(
        self,
        *,
        owner_id,
        task_id,
        request_id,
        reason,
        now,
    ):
        self.cancel_calls.append(
            (owner_id, task_id, request_id, reason, now)
        )
        task = self.get_by_task_id(owner_id=owner_id, task_id=task_id)
        if task is None:
            return None
        return TaskCancelResult(
            task_id=task_id,
            disposition=TaskCancelDisposition.CANCELLED,
            status=TaskStatus.CANCELLED,
        )

    def read_events(self, *, owner_id, task_id, after_cursor, limit):
        self.event_calls.append((owner_id, task_id, after_cursor, limit))
        task = self.get_by_task_id(owner_id=owner_id, task_id=task_id)
        if task is None:
            return None
        item = TaskLifecycleEvent.create(
            event_cursor=1,
            task_sequence=1,
            task_id=task.task_id,
            run_id=task.run_id,
            owner_id=task.owner_id,
            event_kind=TaskLifecycleEventKind.CREATED,
            status_after=TaskStatus.QUEUED,
            lease_generation=0,
            operation_identity="created",
            occurred_at=task.created_at,
        )
        return TaskEventPage(
            after_cursor=after_cursor,
            next_cursor=1,
            limit=limit,
            has_more=False,
            events=(item,),
        )


def service(
    repository: FakeTaskRepository,
    *,
    capacity: TaskCapacityPolicy | None = None,
) -> ReviewTaskService:
    ids = iter(TASK_IDS)
    run_ids = iter(f"review_service_{number}" for number in range(1, 10))
    return ReviewTaskService(
        repository=repository,
        capacity=capacity or TaskCapacityPolicy(),
        task_id_factory=lambda: next(ids),
        run_id_factory=lambda: next(run_ids),
        clock=lambda: NOW,
    )


def test_canonical_fingerprint_is_order_stable_and_semantically_sensitive() -> None:
    first = {"focus": "overall", "count": 10, "queue": 420}
    reordered = {"queue": 420, "count": 10, "focus": "overall"}

    assert canonical_task_request_bytes(
        task_kind="recent_review",
        schema_version="1.0",
        request_payload=first,
    ) == canonical_task_request_bytes(
        task_kind="recent_review",
        schema_version="1.0",
        request_payload=reordered,
    )
    baseline = compute_task_request_fingerprint(
        task_kind="recent_review",
        schema_version="1.0",
        request_payload=first,
    )
    assert len(baseline) == 64
    assert baseline != compute_task_request_fingerprint(
        task_kind="recent_review",
        schema_version="1.0",
        request_payload={**first, "focus": "vision"},
    )
    assert baseline != compute_task_request_fingerprint(
        task_kind="single_match_review",
        schema_version="1.0",
        request_payload=first,
    )
    assert baseline != compute_task_request_fingerprint(
        task_kind="recent_review",
        schema_version="2.0",
        request_payload=first,
    )


@pytest.mark.parametrize(
    "payload",
    (
        {"value": float("nan")},
        {1: "non-string-key"},
        {"value": object()},
    ),
)
def test_canonical_fingerprint_rejects_non_json_or_ambiguous_values(
    payload: dict[object, object],
) -> None:
    with pytest.raises(ValueError, match="canonical JSON"):
        canonical_task_request_bytes(
            task_kind="recent_review",
            schema_version="1.0",
            request_payload=payload,  # type: ignore[arg-type]
        )


def test_service_creates_one_queued_task_and_returns_only_safe_view() -> None:
    repository = FakeTaskRepository()
    result = service(repository).create(command())

    assert result.disposition is TaskCreateDisposition.CREATED
    assert result.task.task_id == TASK_IDS[0]
    assert result.task.run_id == "review_service_1"
    assert result.task.status is TaskStatus.QUEUED
    assert len(repository.tasks) == 1
    stored = repository.tasks[0]
    assert stored.request_payload == {
        "riot_id": "DemoPlayer#TEST",
        "routing_region": "asia",
        "count": 10,
        "queue": 420,
        "focus": "overall",
    }
    assert len(stored.request_fingerprint) == 64
    public = result.model_dump(mode="json")
    assert "request_payload" not in public["task"]
    assert "owner_id" not in public["task"]


def test_same_owner_key_and_fingerprint_replays_original_identity() -> None:
    repository = FakeTaskRepository()
    task_service = service(repository)

    created = task_service.create(command())
    replayed = task_service.create(command())

    assert replayed.disposition is TaskCreateDisposition.REPLAYED
    assert replayed.task.task_id == created.task.task_id
    assert replayed.task.run_id == created.task.run_id
    assert len(repository.tasks) == 1


def test_same_owner_key_with_different_request_is_safe_conflict() -> None:
    repository = FakeTaskRepository()
    task_service = service(repository)
    task_service.create(command())

    with pytest.raises(TaskServiceError) as exc_info:
        task_service.create(command(focus="vision"))

    assert exc_info.value.code == "idempotency_conflict"
    assert exc_info.value.to_public_dict() == {"code": "idempotency_conflict"}
    assert str(exc_info.value) == "idempotency_conflict"
    assert "DemoPlayer" not in repr(exc_info.value)
    assert len(repository.tasks) == 1


def test_owner_and_global_capacity_apply_only_to_new_nonterminal_tasks() -> None:
    owner_repository = FakeTaskRepository()
    owner_service = service(
        owner_repository,
        capacity=TaskCapacityPolicy(owner_active_limit=1, global_active_limit=3),
    )
    original = owner_service.create(command())

    assert owner_service.create(command()).disposition is TaskCreateDisposition.REPLAYED
    with pytest.raises(TaskServiceError) as owner_error:
        owner_service.create(command(key="request-2"))
    assert owner_error.value.code == "owner_capacity_exceeded"

    terminal = owner_repository.tasks[0].model_copy(
        update={
            "status": TaskStatus.FAILED,
            "worker_id": "worker-1",
            "updated_at": NOW + timedelta(seconds=2),
            "claimed_at": NOW + timedelta(seconds=1),
            "finished_at": NOW + timedelta(seconds=2),
            "terminal_reason": "worker_interrupted",
        }
    )
    owner_repository.tasks[0] = ReviewTask.model_validate(terminal)
    replacement = owner_service.create(command(key="request-2"))
    assert replacement.task.task_id != original.task.task_id

    global_repository = FakeTaskRepository()
    global_service = service(
        global_repository,
        capacity=TaskCapacityPolicy(owner_active_limit=2, global_active_limit=2),
    )
    global_service.create(command(owner_id="owner-1", key="one"))
    global_service.create(command(owner_id="owner-2", key="two"))
    with pytest.raises(TaskServiceError) as global_error:
        global_service.create(command(owner_id="owner-3", key="three"))
    assert global_error.value.code == "global_capacity_exceeded"


def test_owner_scoped_queries_hide_other_owners_and_missing_rows_equally() -> None:
    repository = FakeTaskRepository()
    task_service = service(repository)
    created = task_service.create(command())

    assert task_service.get_task(
        owner_id="owner-1",
        task_id=created.task.task_id,
    ) == created.task
    assert task_service.get_task_by_run_id(
        owner_id="owner-1",
        run_id=created.task.run_id,
    ) == created.task

    for call in (
        lambda: task_service.get_task(
            owner_id="owner-2",
            task_id=created.task.task_id,
        ),
        lambda: task_service.get_task(
            owner_id="owner-1",
            task_id=TASK_IDS[-1],
        ),
        lambda: task_service.get_task_by_run_id(
            owner_id="owner-2",
            run_id=created.task.run_id,
        ),
    ):
        with pytest.raises(TaskServiceError) as exc_info:
            call()
        assert exc_info.value.code == "task_not_found"


def test_repository_failures_are_mapped_without_database_details() -> None:
    repository = FakeTaskRepository()
    repository.failure = TaskRepositoryError("database-secret-detail")
    task_service = service(repository)

    with pytest.raises(TaskServiceError) as exc_info:
        task_service.create(command())

    assert exc_info.value.code == "task_persistence_failed"
    assert str(exc_info.value) == "task_persistence_failed"
    assert "database-secret-detail" not in repr(exc_info.value)


def test_cancel_and_event_queries_remain_owner_scoped_and_body_free() -> None:
    repository = FakeTaskRepository()
    task_service = service(repository)
    created = task_service.create(command())

    cancelled = task_service.request_cancel(
        owner_id="owner-1",
        task_id=created.task.task_id,
        request_id="cancel-request-1",
    )
    page = task_service.read_events(
        owner_id="owner-1",
        task_id=created.task.task_id,
        after_cursor=0,
        limit=50,
    )

    assert cancelled.disposition is TaskCancelDisposition.CANCELLED
    assert page.events[0].event_kind is TaskLifecycleEventKind.CREATED
    assert repository.cancel_calls[0][2:4] == (
        "cancel-request-1",
        "user_requested",
    )
    for operation in (
        lambda: task_service.request_cancel(
            owner_id="owner-2",
            task_id=created.task.task_id,
            request_id="cancel-request-2",
        ),
        lambda: task_service.read_events(
            owner_id="owner-2",
            task_id=created.task.task_id,
        ),
    ):
        with pytest.raises(TaskServiceError) as exc_info:
            operation()
        assert exc_info.value.code == "task_not_found"
