from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from app.players.models import RelationshipRole, RoutingRegion
from app.product.recent_review import ConversationRecentReviewRequest
from app.tasks.fingerprint import compute_conversation_review_task_fingerprint
from app.tasks.models import (
    ConversationReviewExecutionTarget,
    ConversationReviewTaskBinding,
    CreateConversationReviewTaskCommand,
    PendingConversationReviewTask,
    ReviewTask,
    TaskCapacityPolicy,
    TaskCreateDisposition,
    TaskRepositoryCreateDisposition,
    TaskRepositoryCreateResult,
    TaskStatus,
)
from app.tasks.service import ReviewTaskService, TaskServiceError


NOW = datetime(2026, 8, 20, 7, 0, 0, tzinfo=timezone.utc)
TASK_ID = UUID("82000000-0000-4000-8000-000000000001")
CONVERSATION_ID = UUID("82000000-0000-4000-8000-000000000002")
RELATIONSHIP_ID = UUID("82000000-0000-4000-8000-000000000003")
SUBJECT_ID = UUID("82000000-0000-4000-8000-000000000004")


class FakeConversationTaskRepository:
    def __init__(self) -> None:
        self.pending: list[PendingConversationReviewTask] = []
        self.disposition = TaskRepositoryCreateDisposition.CREATED
        self.failure: Exception | None = None

    def create_or_replay(self, *_args, **_kwargs):
        raise AssertionError("v2 service must not use the legacy create method")

    def get_by_task_id(self, **_kwargs):
        return None

    def get_by_run_id(self, **_kwargs):
        return None

    def create_conversation_bound_or_replay(
        self,
        pending: PendingConversationReviewTask,
        *,
        capacity: TaskCapacityPolicy,
    ) -> TaskRepositoryCreateResult:
        del capacity
        self.pending.append(pending)
        if self.failure is not None:
            raise self.failure
        if self.disposition not in {
            TaskRepositoryCreateDisposition.CREATED,
            TaskRepositoryCreateDisposition.REPLAYED,
        }:
            return TaskRepositoryCreateResult(disposition=self.disposition)
        binding = ConversationReviewTaskBinding(
            conversation_id=pending.conversation_id,
            relationship_id=RELATIONSHIP_ID,
            player_subject_id=SUBJECT_ID,
            relationship_role=RelationshipRole.SELF,
        )
        task = ReviewTask(
            task_id=pending.task_id,
            run_id=pending.run_id,
            task_kind=pending.task_kind,
            schema_version="2.0",
            owner_id=pending.owner_id,
            idempotency_key=pending.idempotency_key,
            request_fingerprint=compute_conversation_review_task_fingerprint(
                owner_id=pending.owner_id,
                binding=binding,
                request_payload=pending.request_payload,
            ),
            request_payload=pending.request_payload,
            conversation_binding=binding,
            execution_target=ConversationReviewExecutionTarget(
                puuid="trusted_puuid",
                routing_region=RoutingRegion.ASIA,
                game_name="Demo Player",
                tag_line="KR1",
            ),
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
        return TaskRepositoryCreateResult(
            disposition=self.disposition,
            task=task,
        )


def command() -> CreateConversationReviewTaskCommand:
    return CreateConversationReviewTaskCommand(
        owner_id="owner-1",
        idempotency_key="conversation-review-1",
        conversation_id=CONVERSATION_ID,
        request=ConversationRecentReviewRequest(focus="vision"),
    )


def service(repository: FakeConversationTaskRepository) -> ReviewTaskService:
    return ReviewTaskService(
        repository=repository,  # type: ignore[arg-type]
        task_id_factory=lambda: TASK_ID,
        run_id_factory=lambda: "review_conversation_service_1",
        clock=lambda: NOW,
    )


def test_service_passes_only_unbound_intent_to_atomic_repository() -> None:
    repository = FakeConversationTaskRepository()

    result = service(repository).create_conversation_review(command())

    assert result.disposition is TaskCreateDisposition.CREATED
    assert result.task.schema_version == "2.0"
    assert result.task.task_id == TASK_ID
    assert len(repository.pending) == 1
    pending = repository.pending[0]
    assert pending.conversation_id == CONVERSATION_ID
    assert pending.request_payload == {
        "count": 10,
        "queue": 420,
        "focus": "vision",
    }
    payload = pending.model_dump(mode="json")
    assert "relationship_id" not in payload
    assert "player_subject_id" not in payload
    assert "puuid" not in payload


def test_service_preserves_repository_replay_identity() -> None:
    repository = FakeConversationTaskRepository()
    repository.disposition = TaskRepositoryCreateDisposition.REPLAYED

    result = service(repository).create_conversation_review(command())

    assert result.disposition is TaskCreateDisposition.REPLAYED
    assert result.task.task_id == TASK_ID


@pytest.mark.parametrize(
    ("disposition", "expected_code"),
    (
        (
            TaskRepositoryCreateDisposition.CONVERSATION_UNAVAILABLE,
            "conversation_not_found",
        ),
        (
            TaskRepositoryCreateDisposition.IDEMPOTENCY_CONFLICT,
            "idempotency_conflict",
        ),
        (
            TaskRepositoryCreateDisposition.OWNER_CAPACITY_EXCEEDED,
            "owner_capacity_exceeded",
        ),
        (
            TaskRepositoryCreateDisposition.GLOBAL_CAPACITY_EXCEEDED,
            "global_capacity_exceeded",
        ),
    ),
)
def test_service_maps_atomic_repository_dispositions_to_safe_codes(
    disposition: TaskRepositoryCreateDisposition,
    expected_code: str,
) -> None:
    repository = FakeConversationTaskRepository()
    repository.disposition = disposition

    with pytest.raises(TaskServiceError) as caught:
        service(repository).create_conversation_review(command())

    assert caught.value.code == expected_code
    assert "trusted_puuid" not in repr(caught.value)


def test_missing_atomic_repository_method_fails_closed() -> None:
    class LegacyOnlyRepository(FakeConversationTaskRepository):
        create_conversation_bound_or_replay = None  # type: ignore[assignment]

    with pytest.raises(TaskServiceError) as caught:
        service(LegacyOnlyRepository()).create_conversation_review(command())

    assert caught.value.code == "task_persistence_failed"
