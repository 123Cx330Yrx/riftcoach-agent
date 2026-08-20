from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import timedelta
from enum import StrEnum
from uuid import NAMESPACE_URL, uuid5

import sqlalchemy as sa
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.conversations.models import ConversationStatus
from app.conversations.turns import (
    TerminalAssistantTurn,
    TerminalTurnWriteDisposition,
    TerminalTurnWriteResult,
)
from app.memory.gate import evaluate_candidate_gate
from app.memory.models import (
    CandidateCreateDisposition,
    MemoryConversationIdentity,
    PendingMemoryCandidate,
)
from app.persistence.conversation_records import ConversationMessageRecord, ConversationRecord
from app.persistence.memory_repository import PostgresMemoryCandidateRepository
from app.persistence.task_record import ReviewTaskRecord
from app.runtime.models import RuntimeArtifactReference


SessionFactory = Callable[[], Session]


class TerminalTurnWriterDisposition(StrEnum):
    SOURCE_INVALID = "source_invalid"
    CONVERSATION_UNAVAILABLE = "conversation_unavailable"


class TerminalTurnWriterError(RuntimeError):
    """Body-free persistence/integrity failure."""


class PostgresTerminalTurnWriter:
    def __init__(self, session_factory: SessionFactory) -> None:
        if not callable(session_factory):
            raise TypeError("session_factory must be callable")
        self._session_factory = session_factory
        self._candidate_repository = PostgresMemoryCandidateRepository(
            session_factory
        )

    def write(
        self,
        turn: TerminalAssistantTurn,
    ) -> TerminalTurnWriteResult | TerminalTurnWriterDisposition:
        if not isinstance(turn, TerminalAssistantTurn):
            raise TypeError("turn must be a TerminalAssistantTurn")
        gates = tuple(
            evaluate_candidate_gate(
                target_scope=proposal.target_scope,
                candidate_kind=proposal.candidate_kind,
                memory_key=proposal.memory_key,
                operation=proposal.operation,
                provenance_kind=proposal.provenance_kind,
                relationship_role=turn.binding.relationship_role,
                proposal_confidence=proposal.proposal_confidence,
            )
            for proposal in turn.candidate_proposals
        )
        if any(not gate.allowed for gate in gates):
            return TerminalTurnWriterDisposition.SOURCE_INVALID

        try:
            with self._session_factory() as session:
                with session.begin():
                    task = session.scalar(
                        sa.select(ReviewTaskRecord)
                        .where(
                            ReviewTaskRecord.task_id == turn.source_task_id,
                            ReviewTaskRecord.run_id == turn.binding.run_id,
                        )
                        .with_for_update()
                    )
                    if not _task_matches_turn(task, turn):
                        return TerminalTurnWriterDisposition.SOURCE_INVALID
                    conversation = session.scalar(
                        sa.select(ConversationRecord)
                        .where(
                            ConversationRecord.owner_id
                            == turn.binding.owner_id,
                            ConversationRecord.conversation_id
                            == turn.binding.conversation_id,
                            ConversationRecord.relationship_id
                            == turn.binding.relationship_id,
                            ConversationRecord.player_subject_id
                            == turn.binding.player_subject_id,
                            ConversationRecord.relationship_role
                            == turn.binding.relationship_role.value,
                        )
                        .with_for_update()
                    )
                    if (
                        conversation is None
                        or conversation.status != ConversationStatus.ACTIVE.value
                    ):
                        return (
                            TerminalTurnWriterDisposition.CONVERSATION_UNAVAILABLE
                        )
                    existing = session.scalar(
                        sa.select(ConversationMessageRecord).where(
                            ConversationMessageRecord.conversation_id
                            == turn.binding.conversation_id,
                            ConversationMessageRecord.source_run_id
                            == turn.binding.run_id,
                            ConversationMessageRecord.role == "assistant",
                        )
                    )
                    if existing is not None:
                        if (
                            existing.source_task_id != turn.source_task_id
                            or existing.content_sha256
                            != turn.assistant_content_sha256
                        ):
                            return TerminalTurnWriterDisposition.SOURCE_INVALID
                        disposition = TerminalTurnWriteDisposition.REPLAYED
                        message_id = existing.message_id
                        sequence_no = existing.sequence_no
                    else:
                        message_time = max(
                            value
                            for value in (
                                turn.created_at,
                                conversation.created_at,
                                conversation.updated_at,
                                conversation.last_message_at,
                            )
                            if value is not None
                        )
                        sequence_no = conversation.next_message_sequence
                        message_id = uuid5(
                            NAMESPACE_URL,
                            "riftcoach:terminal-turn:"
                            f"{turn.source_task_id}:{turn.binding.run_id}",
                        )
                        session.add(
                            ConversationMessageRecord(
                                message_id=message_id,
                                conversation_id=conversation.conversation_id,
                                owner_id=conversation.owner_id,
                                relationship_id=conversation.relationship_id,
                                player_subject_id=conversation.player_subject_id,
                                relationship_role=conversation.relationship_role,
                                sequence_no=sequence_no,
                                role="assistant",
                                content=turn.assistant_content,
                                content_sha256=turn.assistant_content_sha256,
                                source_task_id=turn.source_task_id,
                                source_run_id=turn.binding.run_id,
                                created_at=message_time,
                                hidden_at=None,
                            )
                        )
                        conversation.next_message_sequence = sequence_no + 1
                        conversation.updated_at = message_time
                        conversation.last_message_at = message_time
                        session.flush()
                        disposition = TerminalTurnWriteDisposition.CREATED
        except IntegrityError:
            raise TerminalTurnWriterError(
                "terminal_turn_integrity_failed"
            ) from None
        except SQLAlchemyError:
            raise TerminalTurnWriterError(
                "terminal_turn_repository_unavailable"
            ) from None
        except (TypeError, ValueError, ValidationError):
            raise TerminalTurnWriterError(
                "terminal_turn_integrity_failed"
            ) from None

        candidate_ids = []
        identity = MemoryConversationIdentity(
            owner_id=turn.binding.owner_id,
            conversation_id=turn.binding.conversation_id,
            relationship_id=turn.binding.relationship_id,
            player_subject_id=turn.binding.player_subject_id,
            relationship_role=turn.binding.relationship_role,
        )
        for index, (proposal, gate) in enumerate(
            zip(turn.candidate_proposals, gates, strict=True),
            start=1,
        ):
            candidate_id = uuid5(
                NAMESPACE_URL,
                "riftcoach:terminal-candidate:"
                f"{turn.source_task_id}:{turn.binding.run_id}:{index}",
            )
            key_digest = hashlib.sha256(
                f"{turn.binding.run_id}:{index}".encode("utf-8")
            ).hexdigest()[:32]
            pending = PendingMemoryCandidate(
                candidate_id=candidate_id,
                owner_id=turn.binding.owner_id,
                conversation_id=turn.binding.conversation_id,
                idempotency_key=f"terminal-{key_digest}-{index}",
                source_message_id=message_id,
                source_task_id=turn.source_task_id,
                source_run_id=turn.binding.run_id,
                source_artifact_sha256=turn.artifact_reference.sha256,
                target_scope=proposal.target_scope,
                candidate_kind=proposal.candidate_kind,
                memory_key=proposal.memory_key,
                operation=proposal.operation,
                proposal_payload=proposal.proposal_payload,
                provenance_kind=proposal.provenance_kind,
                producer_id=proposal.producer_id,
                producer_version=proposal.producer_version,
                proposal_confidence=proposal.proposal_confidence,
                created_at=turn.created_at,
                expires_at=turn.created_at + timedelta(days=30),
            )
            result = self._candidate_repository.create_or_replay_candidate(
                pending,
                identity=identity,
                requires_confirmation=gate.requires_confirmation,
                gate_policy_version=gate.policy_version,
            )
            if result.disposition not in {
                CandidateCreateDisposition.CREATED,
                CandidateCreateDisposition.REPLAYED,
            } or result.candidate is None:
                raise TerminalTurnWriterError(
                    "terminal_candidate_persistence_failed"
                )
            candidate_ids.append(result.candidate.candidate_id)

        return TerminalTurnWriteResult(
            disposition=disposition,
            message_id=message_id,
            sequence_no=sequence_no,
            candidate_ids=tuple(candidate_ids),
        )


def _task_matches_turn(
    task: ReviewTaskRecord | None,
    turn: TerminalAssistantTurn,
) -> bool:
    if task is None:
        return False
    if (
        task.schema_version != "2.0"
        or task.status != "succeeded"
        or task.owner_id != turn.binding.owner_id
        or task.conversation_id != turn.binding.conversation_id
        or task.relationship_id != turn.binding.relationship_id
        or task.player_subject_id != turn.binding.player_subject_id
        or task.relationship_role != turn.binding.relationship_role.value
        or task.publication_status != turn.publication_status.value
        or not task.report_available
        or task.artifact_reference is None
    ):
        return False
    try:
        stored_artifact = RuntimeArtifactReference.model_validate(
            task.artifact_reference
        )
    except (TypeError, ValueError, ValidationError):
        return False
    return stored_artifact == turn.artifact_reference


__all__ = [
    "PostgresTerminalTurnWriter",
    "TerminalTurnWriterDisposition",
    "TerminalTurnWriterError",
]
