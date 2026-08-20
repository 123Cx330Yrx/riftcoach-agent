from __future__ import annotations

from datetime import timedelta

import sqlalchemy as sa

from app.conversations.turns import (
    TerminalAssistantTurn,
    TerminalCandidateProposal,
    TerminalTurnWriteDisposition,
)
from app.memory.context_models import MemoryContextBinding
from app.memory.models import (
    CandidateKind,
    MemoryOperation,
    ProvenanceKind,
    RelationshipRole,
    TargetScope,
)
from app.persistence.conversation_records import ConversationMessageRecord
from app.persistence.memory_records import MemoryCandidateRecord
from app.persistence.terminal_turn_writer import (
    PostgresTerminalTurnWriter,
    TerminalTurnWriterDisposition,
)
from app.runtime.models import RuntimeArtifactReference
from app.runtime.signals import RuntimePublicationStatus
from tests.memory_candidate_postgres_support import (
    BASE,
    migrated_memory_repository,
    seed_conversation,
)
from tests.test_training_repository_postgres import ARTIFACT_SHA, _seed_terminal_review


def _turn(*, task_id, run_id, subject, relationship, conversation, artifact_sha=ARTIFACT_SHA, proposals=()):
    return TerminalAssistantTurn(
        source_task_id=task_id,
        binding=MemoryContextBinding(
            run_id=run_id,
            owner_id="memory-owner",
            conversation_id=conversation,
            relationship_id=relationship,
            player_subject_id=subject,
            relationship_role=RelationshipRole.SELF,
        ),
        publication_status=RuntimePublicationStatus.PUBLISHED,
        artifact_reference=RuntimeArtifactReference(
            kind="final_report",
            schema_version="1.0",
            relative_path="output/final_report.md",
            sha256=artifact_sha,
            producer="review-harness",
        ),
        assistant_content="# trusted terminal report",
        candidate_proposals=proposals,
        created_at=BASE + timedelta(minutes=3),
    )


def test_terminal_writer_appends_once_after_task_and_artifact_verification() -> None:
    with migrated_memory_repository() as (_candidate_repository, factory, _engine):
        subject, relationship, conversation = seed_conversation(factory, number=401)
        task_id, run_id = _seed_terminal_review(
            factory,
            number=401,
            conversation_id=conversation,
            relationship_id=relationship,
            subject_id=subject,
        )
        writer = PostgresTerminalTurnWriter(factory)
        turn = _turn(
            task_id=task_id,
            run_id=run_id,
            subject=subject,
            relationship=relationship,
            conversation=conversation,
        )

        created = writer.write(turn)
        replayed = writer.write(turn)

        assert created.disposition is TerminalTurnWriteDisposition.CREATED
        assert replayed.disposition is TerminalTurnWriteDisposition.REPLAYED
        assert created.message_id == replayed.message_id
        with factory() as session:
            rows = session.scalars(sa.select(ConversationMessageRecord)).all()
        assert len(rows) == 1
        assert rows[0].role == "assistant"
        assert rows[0].source_task_id == task_id
        assert rows[0].source_run_id == run_id


def test_terminal_writer_rejects_artifact_drift_without_message() -> None:
    with migrated_memory_repository() as (_candidate_repository, factory, _engine):
        subject, relationship, conversation = seed_conversation(factory, number=411)
        task_id, run_id = _seed_terminal_review(
            factory,
            number=411,
            conversation_id=conversation,
            relationship_id=relationship,
            subject_id=subject,
        )

        result = PostgresTerminalTurnWriter(factory).write(
            _turn(
                task_id=task_id,
                run_id=run_id,
                subject=subject,
                relationship=relationship,
                conversation=conversation,
                artifact_sha="b" * 64,
            )
        )

        assert result is TerminalTurnWriterDisposition.SOURCE_INVALID
        with factory() as session:
            assert session.scalar(sa.select(sa.func.count()).select_from(ConversationMessageRecord)) == 0


def test_terminal_writer_creates_explicit_typed_candidate_as_pending() -> None:
    with migrated_memory_repository() as (_candidate_repository, factory, _engine):
        subject, relationship, conversation = seed_conversation(factory, number=421)
        task_id, run_id = _seed_terminal_review(
            factory,
            number=421,
            conversation_id=conversation,
            relationship_id=relationship,
            subject_id=subject,
        )
        proposal = TerminalCandidateProposal(
            target_scope=TargetScope.OWNER_PLAYER,
            candidate_kind=CandidateKind.REVIEW_MEMORY,
            memory_key="review_summary",
            operation=MemoryOperation.APPEND,
            proposal_payload={"value": "typed terminal conclusion"},
            provenance_kind=ProvenanceKind.MODEL_INFERENCE,
            producer_id="recent-form-review",
            producer_version="0.2.0",
            proposal_confidence=0.8,
        )

        result = PostgresTerminalTurnWriter(factory).write(
            _turn(
                task_id=task_id,
                run_id=run_id,
                subject=subject,
                relationship=relationship,
                conversation=conversation,
                proposals=(proposal,),
            )
        )

        assert result.disposition is TerminalTurnWriteDisposition.CREATED
        assert len(result.candidate_ids) == 1
        with factory() as session:
            candidate = session.scalar(sa.select(MemoryCandidateRecord))
        assert candidate is not None
        assert candidate.status == "pending"
        assert candidate.source_message_id == result.message_id
        assert candidate.source_task_id == task_id
        assert candidate.source_run_id == run_id
