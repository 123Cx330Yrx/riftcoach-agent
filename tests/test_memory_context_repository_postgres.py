from __future__ import annotations

import json
from datetime import timedelta
from uuid import UUID

import sqlalchemy as sa
import pytest

from app.conversations.models import PendingUserMessage, compute_message_content_sha256
from app.memory.composition import build_typed_memory_materializers
from app.memory.context_models import MemoryContextBinding, MemoryContextRecordKind
from app.memory.models import (
    CandidateKind,
    CandidateMutationDisposition,
    DecisionActorKind,
    MemoryOperation,
    ProvenanceKind,
    RelationshipRole,
    TargetScope,
)
from app.persistence.conversation_repository import PostgresConversationRepository
from app.persistence.memory_context_repository import PostgresMemoryContextRepository
from app.memory.training_materializers import TrainingProgressMaterializer
from app.persistence.training_query_repository import PostgresTrainingQueryRepository
from app.persistence.training_writer import PostgresTrainingTargetWriter
from tests.memory_candidate_postgres_support import (
    BASE,
    migrated_memory_repository,
    pending_candidate,
    seed_conversation,
)
from tests.test_training_repository_postgres import (
    ARTIFACT_SHA, _accept, _activate_payload, _identity_and_candidate, _seed_terminal_review,
)


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
            payload={"value": "MIDDLE"},
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


def _progress(repository, factory, *, number, plan_id, conversation, relationship,
              subject, progress_id, value):
    task_id, run_id = _seed_terminal_review(factory, number=number,
        conversation_id=conversation, relationship_id=relationship, subject_id=subject)
    candidate = _identity_and_candidate(repository, factory, number=number,
        conversation_id=conversation, kind=CandidateKind.TRAINING_PROGRESS,
        payload={"value": {"plan_id": str(plan_id), "metric_key": "deaths_before_15",
            "metric_value": value, "observed_at": BASE.isoformat()}},
        source_task_id=task_id, source_run_id=run_id, source_artifact_sha256=ARTIFACT_SHA)
    writer = PostgresTrainingTargetWriter(progress_id_factory=lambda: progress_id,
        clock=lambda: BASE + timedelta(days=1))
    result = repository.accept_candidate(owner_id="memory-owner",
        candidate_id=candidate.candidate_id, actor_id="memory-owner",
        actor_kind=DecisionActorKind.USER, now=BASE + timedelta(days=1),
        materializers={CandidateKind.TRAINING_PROGRESS: TrainingProgressMaterializer(writer)})
    assert result.disposition is CandidateMutationDisposition.ACCEPTED


def test_latest_training_progress_tie_matches_query_and_coach_context():
    with migrated_memory_repository() as (repository, factory, _engine):
        subject, relationship, conversation = seed_conversation(factory, number=321)
        candidate = _identity_and_candidate(repository, factory, number=322,
            payload=_activate_payload(), kind=CandidateKind.TRAINING_PLAN,
            conversation_id=conversation)
        plan_id = _accept(repository, candidate.candidate_id).candidate.materialized_target_id
        higher = UUID("94000000-0000-4000-8000-000000000002")
        lower = UUID("94000000-0000-4000-8000-000000000001")
        # Insert the higher UUID first: neither insertion order nor timestamps
        # distinguish these two events. Both consumers must use the same tie-break.
        for number, progress_id, value in ((323, higher, 1.0), (324, lower, 2.0)):
            _progress(repository, factory, number=number, plan_id=plan_id,
                conversation=conversation, relationship=relationship, subject=subject,
                progress_id=progress_id, value=value)
        page = PostgresTrainingQueryRepository(factory).list_progress(owner_id="memory-owner",
            relationship_id=relationship, metric_key="deaths_before_15",
            include_history=False, limit=50)
        assert page.events[0].observed_at == page.events[1].observed_at
        assert page.events[0].created_at == page.events[1].created_at
        assert page.events[0].progress_id == higher
        snapshot = PostgresMemoryContextRepository(factory).load(_binding(
            conversation_id=conversation, relationship_id=relationship,
            subject_id=subject, role=RelationshipRole.SELF))
        progress, = (r for r in snapshot.records if r.kind is MemoryContextRecordKind.TRAINING_PROGRESS)
        assert progress.record_id == page.events[0].progress_id
        assert json.loads(progress.content)["metric_value"] == page.events[0].metric_value


@pytest.mark.parametrize("has_plan", [True, False])
def test_context_uses_one_plan_when_another_transaction_replaces_it(has_plan):
    with migrated_memory_repository() as (repository, factory, engine):
        subject, relationship, conversation = seed_conversation(factory, number=331)
        first_id = None
        if has_plan:
            first = _identity_and_candidate(repository, factory, number=332,
                payload=_activate_payload(), kind=CandidateKind.TRAINING_PLAN,
                conversation_id=conversation)
            first_id = _accept(repository, first.candidate_id).candidate.materialized_target_id
            _progress(repository, factory, number=333, plan_id=first_id,
                conversation=conversation, relationship=relationship, subject=subject,
                progress_id=UUID("94000000-0000-4000-8000-000000000003"), value=2.0)
        switched = False
        second_id = None

        def replace_after_plan_read(conn, cursor, statement, params, context, executemany):
            nonlocal switched, second_id
            if switched or "FROM training_plans" not in statement:
                return
            switched = True
            # The reader's SELECT has executed, but the next SELECT under READ
            # COMMITTED will see this separate committed Candidate transaction.
            second = _identity_and_candidate(repository, factory, number=334,
                payload=_activate_payload(expected_version=1 if has_plan else None),
                kind=CandidateKind.TRAINING_PLAN,
                conversation_id=conversation)
            second_id = _accept(repository, second.candidate_id).candidate.materialized_target_id
            _progress(repository, factory, number=335, plan_id=second_id,
                conversation=conversation, relationship=relationship, subject=subject,
                progress_id=UUID("94000000-0000-4000-8000-000000000004"), value=1.0)

        sa.event.listen(engine, "after_cursor_execute", replace_after_plan_read)
        try:
            snapshot = PostgresMemoryContextRepository(factory).load(_binding(
                conversation_id=conversation, relationship_id=relationship,
                subject_id=subject, role=RelationshipRole.SELF))
        finally:
            sa.event.remove(engine, "after_cursor_execute", replace_after_plan_read)
        assert switched and second_id != first_id
        plans = [r for r in snapshot.records if r.kind is MemoryContextRecordKind.TRAINING_PLAN]
        progresses = [r for r in snapshot.records if r.kind is MemoryContextRecordKind.TRAINING_PROGRESS]
        if has_plan:
            plan, = plans
            progress, = progresses
            assert plan.record_id == first_id
            assert UUID(json.loads(progress.content)["plan_id"]) == plan.record_id
            assert json.loads(progress.content)["metric_value"] == 2.0
        else:
            assert plans == progresses == []
        page = PostgresTrainingQueryRepository(factory).list_plans(owner_id="memory-owner",
            relationship_id=relationship, include_history=False, limit=50)
        assert page[0].plan_id == second_id  # The replacement really committed.
