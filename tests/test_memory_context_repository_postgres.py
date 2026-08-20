from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from app.conversations.models import PendingUserMessage, compute_message_content_sha256
from app.memory.composition import build_typed_memory_materializers
from app.memory.context_models import MemoryContextBinding, MemoryContextRecordKind
from app.memory.models import (
    CandidateKind,
    DecisionActorKind,
    MemoryOperation,
    ProvenanceKind,
    RelationshipRole,
    TargetScope,
)
from app.persistence.conversation_repository import PostgresConversationRepository
from app.persistence.memory_context_repository import PostgresMemoryContextRepository
from tests.memory_candidate_postgres_support import (
    BASE,
    migrated_memory_repository,
    pending_candidate,
    seed_conversation,
)
from tests.test_training_repository_postgres import _accept, _activate_payload, _identity_and_candidate


def _materialize(
    repository,
    *,
    number: int,
    conversation_id: UUID,
    kind: CandidateKind,
    key: str,
    payload: dict[str, object],
    scope: TargetScope,
    operation: MemoryOperation = MemoryOperation.SET,
    provenance: ProvenanceKind = ProvenanceKind.USER_STRUCTURED_INPUT,
):
    identity = repository.get_conversation_identity(
        owner_id="memory-owner",
        conversation_id=conversation_id,
    )
    assert identity is not None
    created = repository.create_or_replay_candidate(
        pending_candidate(
            number,
            conversation_id=conversation_id,
            target_scope=scope,
            candidate_kind=kind,
            memory_key=key,
            payload=payload,
            operation=operation,
            provenance_kind=provenance,
        ),
        identity=identity,
        requires_confirmation=provenance in {
            ProvenanceKind.MODEL_INFERENCE,
            ProvenanceKind.USER_MESSAGE_EXTRACTION,
        },
        gate_policy_version="memory-gate-v1",
    )
    assert created.candidate is not None
    result = repository.accept_candidate(
        owner_id="memory-owner",
        candidate_id=created.candidate.candidate_id,
        actor_id="memory-owner",
        actor_kind=DecisionActorKind.USER,
        now=BASE + timedelta(days=2),
        materializers=build_typed_memory_materializers(),
    )
    assert result.candidate is not None


def _binding(
    *,
    conversation_id: UUID,
    relationship_id: UUID,
    subject_id: UUID,
    role: RelationshipRole,
) -> MemoryContextBinding:
    return MemoryContextBinding(
        run_id="memory-context-postgres",
        owner_id="memory-owner",
        conversation_id=conversation_id,
        relationship_id=relationship_id,
        player_subject_id=subject_id,
        relationship_role=role,
    )


def test_self_context_selects_bounded_active_records_in_stable_order() -> None:
    with migrated_memory_repository() as (candidate_repository, factory, _engine):
        subject, relationship, conversation = seed_conversation(factory, number=301)
        conversation_repository = PostgresConversationRepository(factory)
        for number in range(1, 15):
            content = f"message {number}"
            result = conversation_repository.append_user_message(
                PendingUserMessage(
                    message_id=UUID(f"91000000-0000-4000-8000-{number:012d}"),
                    owner_id="memory-owner",
                    conversation_id=conversation,
                    content=content,
                    content_sha256=compute_message_content_sha256(content),
                    created_at=BASE + timedelta(minutes=number),
                )
            )
            assert result.message is not None

        _materialize(
            candidate_repository,
            number=302,
            conversation_id=conversation,
            kind=CandidateKind.OWNER_PREFERENCE,
            key="report_language",
            payload={"value": "zh-CN"},
            scope=TargetScope.OWNER_GLOBAL,
        )
        _materialize(
            candidate_repository,
            number=303,
            conversation_id=conversation,
            kind=CandidateKind.PLAYER_PROFILE,
            key="main_role",
            payload={"value": "MID"},
            scope=TargetScope.OWNER_PLAYER,
        )
        _materialize(
            candidate_repository,
            number=304,
            conversation_id=conversation,
            kind=CandidateKind.REVIEW_MEMORY,
            key="review_summary",
            payload={"value": {"text": "bounded summary"}},
            scope=TargetScope.OWNER_PLAYER,
            operation=MemoryOperation.APPEND,
            provenance=ProvenanceKind.MODEL_INFERENCE,
        )
        plan = _identity_and_candidate(
            candidate_repository,
            factory,
            number=305,
            payload=_activate_payload(),
            kind=CandidateKind.TRAINING_PLAN,
            conversation_id=conversation,
        )
        assert _accept(candidate_repository, plan.candidate_id).candidate is not None

        snapshot = PostgresMemoryContextRepository(factory).load(
            _binding(
                conversation_id=conversation,
                relationship_id=relationship,
                subject_id=subject,
                role=RelationshipRole.SELF,
            )
        )

        kinds = [row.kind for row in snapshot.records]
        assert MemoryContextRecordKind.OWNER_PREFERENCE in kinds
        assert MemoryContextRecordKind.PLAYER_PROFILE in kinds
        assert MemoryContextRecordKind.REVIEW_MEMORY in kinds
        assert MemoryContextRecordKind.TRAINING_PLAN in kinds
        messages = [row for row in snapshot.records if row.kind is MemoryContextRecordKind.MESSAGE]
        assert len(messages) == 12
        assert [row.version for row in messages] == list(range(3, 15))
        assert tuple((-row.priority, row.stable_order) for row in snapshot.records) == tuple(
            sorted((-row.priority, row.stable_order) for row in snapshot.records)
        )


def test_observed_context_excludes_self_only_records_but_keeps_global_preference() -> None:
    with migrated_memory_repository() as (candidate_repository, factory, _engine):
        _self_subject, _self_relationship, self_conversation = seed_conversation(
            factory, number=311
        )
        _materialize(
            candidate_repository,
            number=312,
            conversation_id=self_conversation,
            kind=CandidateKind.OWNER_PREFERENCE,
            key="report_language",
            payload={"value": "en-US"},
            scope=TargetScope.OWNER_GLOBAL,
        )
        subject, relationship, conversation = seed_conversation(
            factory,
            number=313,
            role=RelationshipRole.OBSERVED,
        )
        _materialize(
            candidate_repository,
            number=314,
            conversation_id=conversation,
            kind=CandidateKind.REVIEW_MEMORY,
            key="public_trend",
            payload={"value": {"metric": "wins", "direction": "up", "value": 3}},
            scope=TargetScope.OWNER_PLAYER,
            operation=MemoryOperation.APPEND,
            provenance=ProvenanceKind.DETERMINISTIC_RUN_FACT,
        )

        snapshot = PostgresMemoryContextRepository(factory).load(
            _binding(
                conversation_id=conversation,
                relationship_id=relationship,
                subject_id=subject,
                role=RelationshipRole.OBSERVED,
            )
        )

        assert {row.kind for row in snapshot.records} == {
            MemoryContextRecordKind.OWNER_PREFERENCE,
            MemoryContextRecordKind.REVIEW_MEMORY,
        }
        review = next(
            row for row in snapshot.records if row.kind is MemoryContextRecordKind.REVIEW_MEMORY
        )
        assert review.relationship_role is RelationshipRole.OBSERVED
