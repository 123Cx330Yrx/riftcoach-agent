from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.players.models import RelationshipRole, RoutingRegion
from app.product.recent_review import ConversationRecentReviewRequest
from app.tasks.fingerprint import compute_conversation_review_task_fingerprint
from app.tasks.models import (
    ConversationReviewExecutionTarget,
    ConversationReviewTaskBinding,
    CreateConversationReviewTaskCommand,
    ReviewTask,
    ReviewTaskView,
    TaskStatus,
)


NOW = datetime(2026, 8, 20, 6, 0, 0, tzinfo=timezone.utc)
TASK_ID = UUID("81000000-0000-4000-8000-000000000001")
CONVERSATION_ID = UUID("81000000-0000-4000-8000-000000000002")
RELATIONSHIP_ID = UUID("81000000-0000-4000-8000-000000000003")
SUBJECT_ID = UUID("81000000-0000-4000-8000-000000000004")


def binding(**changes: object) -> ConversationReviewTaskBinding:
    values: dict[str, object] = {
        "conversation_id": CONVERSATION_ID,
        "relationship_id": RELATIONSHIP_ID,
        "player_subject_id": SUBJECT_ID,
        "relationship_role": RelationshipRole.SELF,
    }
    values.update(changes)
    return ConversationReviewTaskBinding(**values)  # type: ignore[arg-type]


def target(**changes: object) -> ConversationReviewExecutionTarget:
    values: dict[str, object] = {
        "puuid": "trusted_puuid_123",
        "routing_region": RoutingRegion.ASIA,
        "game_name": "Current Name",
        "tag_line": "KR1",
    }
    values.update(changes)
    return ConversationReviewExecutionTarget(**values)  # type: ignore[arg-type]


def v2_task(**changes: object) -> ReviewTask:
    request = ConversationRecentReviewRequest(focus="survival")
    trusted_binding = binding()
    values: dict[str, object] = {
        "task_id": TASK_ID,
        "run_id": "review_conversation_task_1",
        "task_kind": "recent_review",
        "schema_version": "2.0",
        "owner_id": "owner-1",
        "idempotency_key": "conversation-review-1",
        "request_fingerprint": compute_conversation_review_task_fingerprint(
            owner_id="owner-1",
            binding=trusted_binding,
            request_payload=request.model_dump(mode="json"),
        ),
        "request_payload": request.model_dump(mode="json"),
        "conversation_binding": trusted_binding,
        "execution_target": target(),
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


def test_conversation_review_request_contains_only_product_parameters() -> None:
    request = ConversationRecentReviewRequest(
        count=5,
        queue=420,
        focus="laning",
    )

    assert request.model_dump(mode="json") == {
        "count": 5,
        "queue": 420,
        "focus": "laning",
    }
    for privileged in (
        "riot_id",
        "owner_id",
        "conversation_id",
        "relationship_id",
        "player_subject_id",
        "relationship_role",
        "puuid",
    ):
        with pytest.raises(ValidationError):
            ConversationRecentReviewRequest.model_validate(
                {**request.model_dump(mode="json"), privileged: "attacker"}
            )


def test_create_command_accepts_path_conversation_but_no_derived_identity() -> None:
    command = CreateConversationReviewTaskCommand(
        owner_id="owner-1",
        idempotency_key="conversation-review-1",
        conversation_id=CONVERSATION_ID,
        request=ConversationRecentReviewRequest(),
    )

    assert command.conversation_id == CONVERSATION_ID
    for privileged in (
        "relationship_id",
        "player_subject_id",
        "relationship_role",
        "puuid",
    ):
        with pytest.raises(ValidationError):
            CreateConversationReviewTaskCommand.model_validate(
                {**command.model_dump(mode="python"), privileged: "attacker"}
            )


def test_v2_task_requires_complete_binding_and_private_execution_target() -> None:
    task = v2_task()

    assert task.conversation_binding == binding()
    assert task.execution_target == target()
    public = ReviewTaskView.from_task(task).model_dump(mode="json")
    assert "puuid" not in public
    assert "player_subject_id" not in public
    assert "relationship_id" not in public
    assert "execution_target" not in public

    with pytest.raises(ValidationError, match="schema 2.0"):
        v2_task(conversation_binding=None)
    with pytest.raises(ValidationError, match="schema 2.0"):
        v2_task(execution_target=None)


def test_legacy_v1_task_rejects_conversation_identity() -> None:
    with pytest.raises(ValidationError, match="schema 1.0"):
        v2_task(
            schema_version="1.0",
            conversation_binding=binding(),
            execution_target=target(),
        )


def test_v2_fingerprint_is_order_stable_and_covers_the_frozen_tuple() -> None:
    request = {"focus": "overall", "count": 10, "queue": 420}
    reordered = {"queue": 420, "count": 10, "focus": "overall"}
    baseline = compute_conversation_review_task_fingerprint(
        owner_id="owner-1",
        binding=binding(),
        request_payload=request,
    )

    assert baseline == compute_conversation_review_task_fingerprint(
        owner_id="owner-1",
        binding=binding(),
        request_payload=reordered,
    )
    variants = (
        {"owner_id": "owner-2"},
        {"binding": binding(conversation_id=UUID(int=100))},
        {"binding": binding(relationship_id=UUID(int=101))},
        {"binding": binding(player_subject_id=UUID(int=102))},
        {"binding": binding(relationship_role=RelationshipRole.OBSERVED)},
        {"request_payload": {**request, "focus": "vision"}},
    )
    for changed in variants:
        arguments = {
            "owner_id": "owner-1",
            "binding": binding(),
            "request_payload": request,
        }
        arguments.update(changed)
        assert baseline != compute_conversation_review_task_fingerprint(
            **arguments  # type: ignore[arg-type]
        )
