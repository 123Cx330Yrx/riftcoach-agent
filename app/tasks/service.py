from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Literal, TypeAlias
from uuid import UUID, uuid4

from pydantic import TypeAdapter, ValidationError

from app.harness.run_ids import normalize_run_id
from app.tasks.fingerprint import compute_task_request_fingerprint
from app.tasks.models import (
    CreateConversationReviewTaskCommand,
    CreateReviewTaskCommand,
    OwnerId,
    PendingReviewTask,
    PendingConversationReviewTask,
    ReviewTask,
    ReviewTaskView,
    TaskCapacityPolicy,
    TaskCreateDisposition,
    TaskCreateResult,
    TaskRepositoryCreateDisposition,
)
from app.tasks.ports import TaskRepository
from app.tasks.reliable_runtime import (
    OperationIdentity,
    TaskCancelResult,
    TaskEventPage,
)


TaskServiceErrorCode: TypeAlias = Literal[
    "idempotency_conflict",
    "owner_capacity_exceeded",
    "global_capacity_exceeded",
    "task_not_found",
    "task_persistence_failed",
    "task_identity_invalid",
    "conversation_not_found",
]
_TASK_SERVICE_ERROR_CODES = frozenset(
    {
        "idempotency_conflict",
        "owner_capacity_exceeded",
        "global_capacity_exceeded",
        "task_not_found",
        "task_persistence_failed",
        "task_identity_invalid",
        "conversation_not_found",
    }
)
TaskIdFactory = Callable[[], UUID]
RunIdFactory = Callable[[], str]
Clock = Callable[[], datetime]
_OWNER_ID_ADAPTER = TypeAdapter(OwnerId)
_OPERATION_ID_ADAPTER = TypeAdapter(OperationIdentity)


class TaskServiceError(RuntimeError):
    def __init__(self, code: TaskServiceErrorCode) -> None:
        if code not in _TASK_SERVICE_ERROR_CODES:
            raise ValueError("unsupported task service error code")
        self.code = code
        super().__init__(code)

    def to_public_dict(self) -> dict[str, str]:
        return {"code": self.code}


class ReviewTaskService:
    def __init__(
        self,
        *,
        repository: TaskRepository,
        capacity: TaskCapacityPolicy | None = None,
        task_id_factory: TaskIdFactory = uuid4,
        run_id_factory: RunIdFactory | None = None,
        clock: Clock | None = None,
    ) -> None:
        for method_name in ("create_or_replay", "get_by_task_id", "get_by_run_id"):
            if not callable(getattr(repository, method_name, None)):
                raise TypeError(f"repository must expose {method_name}()")
        if not callable(task_id_factory):
            raise TypeError("task_id_factory must be callable")
        if run_id_factory is not None and not callable(run_id_factory):
            raise TypeError("run_id_factory must be callable")
        if clock is not None and not callable(clock):
            raise TypeError("clock must be callable")

        self._repository = repository
        self._capacity = capacity or TaskCapacityPolicy()
        self._task_id_factory = task_id_factory
        self._run_id_factory = run_id_factory or _default_run_id
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def create(self, command: CreateReviewTaskCommand) -> TaskCreateResult:
        if not isinstance(command, CreateReviewTaskCommand):
            raise TypeError("command must be a CreateReviewTaskCommand")

        request_payload = command.request.model_dump(mode="json")
        fingerprint = compute_task_request_fingerprint(
            task_kind="recent_review",
            schema_version="1.0",
            request_payload=request_payload,
        )
        try:
            pending = PendingReviewTask(
                task_id=self._task_id_factory(),
                run_id=normalize_run_id(self._run_id_factory()),
                owner_id=command.owner_id,
                idempotency_key=command.idempotency_key,
                request_fingerprint=fingerprint,
                request_payload=request_payload,
                created_at=self._clock(),
            )
        except (StopIteration, TypeError, ValueError, ValidationError):
            raise TaskServiceError("task_identity_invalid") from None

        try:
            repository_result = self._repository.create_or_replay(
                pending,
                capacity=self._capacity,
            )
        except Exception:
            raise TaskServiceError("task_persistence_failed") from None

        if repository_result.disposition is TaskRepositoryCreateDisposition.CREATED:
            disposition = TaskCreateDisposition.CREATED
        elif repository_result.disposition is TaskRepositoryCreateDisposition.REPLAYED:
            disposition = TaskCreateDisposition.REPLAYED
        else:
            code_by_disposition: dict[
                TaskRepositoryCreateDisposition,
                TaskServiceErrorCode,
            ] = {
                TaskRepositoryCreateDisposition.IDEMPOTENCY_CONFLICT: (
                    "idempotency_conflict"
                ),
                TaskRepositoryCreateDisposition.OWNER_CAPACITY_EXCEEDED: (
                    "owner_capacity_exceeded"
                ),
                TaskRepositoryCreateDisposition.GLOBAL_CAPACITY_EXCEEDED: (
                    "global_capacity_exceeded"
                ),
            }
            code = code_by_disposition.get(repository_result.disposition)
            if code is None:
                raise TaskServiceError("task_persistence_failed")
            raise TaskServiceError(code)

        assert repository_result.task is not None
        return TaskCreateResult(
            disposition=disposition,
            task=ReviewTaskView.from_task(repository_result.task),
        )

    def create_conversation_review(
        self,
        command: CreateConversationReviewTaskCommand,
    ) -> TaskCreateResult:
        if not isinstance(command, CreateConversationReviewTaskCommand):
            raise TypeError(
                "command must be a CreateConversationReviewTaskCommand"
            )
        try:
            pending = PendingConversationReviewTask(
                task_id=self._task_id_factory(),
                run_id=normalize_run_id(self._run_id_factory()),
                owner_id=command.owner_id,
                idempotency_key=command.idempotency_key,
                conversation_id=command.conversation_id,
                request_payload=command.request.model_dump(mode="json"),
                created_at=self._clock(),
            )
        except (StopIteration, TypeError, ValueError, ValidationError):
            raise TaskServiceError("task_identity_invalid") from None

        create = getattr(
            self._repository,
            "create_conversation_bound_or_replay",
            None,
        )
        if not callable(create):
            raise TaskServiceError("task_persistence_failed")
        try:
            repository_result = create(pending, capacity=self._capacity)
        except Exception:
            raise TaskServiceError("task_persistence_failed") from None

        if repository_result.disposition is TaskRepositoryCreateDisposition.CREATED:
            disposition = TaskCreateDisposition.CREATED
        elif repository_result.disposition is TaskRepositoryCreateDisposition.REPLAYED:
            disposition = TaskCreateDisposition.REPLAYED
        else:
            code_by_disposition: dict[
                TaskRepositoryCreateDisposition,
                TaskServiceErrorCode,
            ] = {
                TaskRepositoryCreateDisposition.CONVERSATION_UNAVAILABLE: (
                    "conversation_not_found"
                ),
                TaskRepositoryCreateDisposition.IDEMPOTENCY_CONFLICT: (
                    "idempotency_conflict"
                ),
                TaskRepositoryCreateDisposition.OWNER_CAPACITY_EXCEEDED: (
                    "owner_capacity_exceeded"
                ),
                TaskRepositoryCreateDisposition.GLOBAL_CAPACITY_EXCEEDED: (
                    "global_capacity_exceeded"
                ),
            }
            code = code_by_disposition.get(repository_result.disposition)
            if code is None:
                raise TaskServiceError("task_persistence_failed")
            raise TaskServiceError(code)

        if repository_result.task is None:
            raise TaskServiceError("task_persistence_failed")
        return TaskCreateResult(
            disposition=disposition,
            task=ReviewTaskView.from_task(repository_result.task),
        )

    def get_task(self, *, owner_id: str, task_id: UUID) -> ReviewTaskView:
        _validate_owner_scope(owner_id)
        if not isinstance(task_id, UUID):
            raise TaskServiceError("task_not_found")
        try:
            task = self._repository.get_by_task_id(
                owner_id=owner_id,
                task_id=task_id,
            )
        except Exception:
            raise TaskServiceError("task_persistence_failed") from None
        return self._project_lookup(task)

    def get_task_by_run_id(self, *, owner_id: str, run_id: str) -> ReviewTaskView:
        _validate_owner_scope(owner_id)
        try:
            normalized_run_id = normalize_run_id(run_id)
        except (TypeError, ValueError):
            raise TaskServiceError("task_not_found") from None
        try:
            task = self._repository.get_by_run_id(
                owner_id=owner_id,
                run_id=normalized_run_id,
            )
        except Exception:
            raise TaskServiceError("task_persistence_failed") from None
        return self._project_lookup(task)

    def request_cancel(
        self,
        *,
        owner_id: str,
        task_id: UUID,
        request_id: str,
    ) -> TaskCancelResult:
        _validate_owner_scope(owner_id)
        if not isinstance(task_id, UUID):
            raise TaskServiceError("task_not_found")
        try:
            normalized_request_id = _OPERATION_ID_ADAPTER.validate_python(
                request_id,
                strict=True,
            )
        except (TypeError, ValueError, ValidationError):
            raise TaskServiceError("task_identity_invalid") from None
        request_cancel = getattr(self._repository, "request_cancel", None)
        if not callable(request_cancel):
            raise TaskServiceError("task_persistence_failed")
        try:
            result = request_cancel(
                owner_id=owner_id,
                task_id=task_id,
                request_id=normalized_request_id,
                reason="user_requested",
                now=self._clock(),
            )
        except Exception:
            raise TaskServiceError("task_persistence_failed") from None
        if result is None:
            raise TaskServiceError("task_not_found")
        if not isinstance(result, TaskCancelResult) or result.task_id != task_id:
            raise TaskServiceError("task_persistence_failed")
        return result

    def read_events(
        self,
        *,
        owner_id: str,
        task_id: UUID,
        after_cursor: int = 0,
        limit: int = 50,
    ) -> TaskEventPage:
        _validate_owner_scope(owner_id)
        if not isinstance(task_id, UUID):
            raise TaskServiceError("task_not_found")
        read_events = getattr(self._repository, "read_events", None)
        if not callable(read_events):
            raise TaskServiceError("task_persistence_failed")
        try:
            result = read_events(
                owner_id=owner_id,
                task_id=task_id,
                after_cursor=after_cursor,
                limit=limit,
            )
        except Exception:
            raise TaskServiceError("task_persistence_failed") from None
        if result is None:
            raise TaskServiceError("task_not_found")
        if not isinstance(result, TaskEventPage) or any(
            event.task_id != task_id for event in result.events
        ):
            raise TaskServiceError("task_persistence_failed")
        return result

    @staticmethod
    def _project_lookup(task: ReviewTask | None) -> ReviewTaskView:
        if task is None:
            raise TaskServiceError("task_not_found")
        return ReviewTaskView.from_task(task)


def _default_run_id() -> str:
    return f"review_{uuid4().hex}"


def _validate_owner_scope(owner_id: str) -> None:
    try:
        _OWNER_ID_ADAPTER.validate_python(owner_id, strict=True)
    except (TypeError, ValueError, ValidationError):
        raise TaskServiceError("task_not_found") from None


__all__ = ["ReviewTaskService", "TaskServiceError", "TaskServiceErrorCode"]
