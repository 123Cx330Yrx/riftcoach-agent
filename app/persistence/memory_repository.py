from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from decimal import Decimal
from types import MappingProxyType
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from pydantic import TypeAdapter, ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.conversations.models import ConversationStatus
from app.memory.gate import evaluate_candidate_gate
from app.memory.models import (
    CandidateCreateDisposition,
    CandidateCreateResult,
    CandidateKind,
    CandidateMutationDisposition,
    CandidateMutationResult,
    CandidateStatus,
    DecisionActorKind,
    MaterializedMemoryReference,
    MemoryCandidate,
    MemoryConversationIdentity,
    MemoryOperation,
    OwnerId,
    PendingMemoryCandidate,
    ProvenanceKind,
    RelationshipRole,
    TargetScope,
    compute_candidate_fingerprint,
    compute_payload_sha256,
)
from app.memory.ports import (
    MaterializationSession,
    MaterializerRegistry,
    MemoryCandidateRepositoryError,
)
from app.persistence.conversation_records import ConversationMessageRecord, ConversationRecord
from app.persistence.memory_records import MemoryCandidateRecord
from app.persistence.player_records import OwnerPlayerRelationshipRecord
from app.persistence.task_record import ReviewTaskRecord


SessionFactory = Callable[[], Session]
_OWNER_ADAPTER = TypeAdapter(OwnerId)


class PostgresMemoryCandidateRepository:
    """Short-transaction PostgreSQL control plane for Memory Candidates."""

    def __init__(self, session_factory: SessionFactory) -> None:
        if not callable(session_factory):
            raise TypeError("session_factory must be callable")
        self._session_factory = session_factory

    def get_conversation_identity(
        self,
        *,
        owner_id: str,
        conversation_id: UUID,
    ) -> MemoryConversationIdentity | None:
        owner = _validate_owner(owner_id)
        _validate_uuid(conversation_id, name="conversation_id")
        try:
            with self._session_factory() as session:
                with session.begin():
                    row = session.execute(
                        sa.select(
                            ConversationRecord.owner_id,
                            ConversationRecord.conversation_id,
                            ConversationRecord.relationship_id,
                            ConversationRecord.player_subject_id,
                            ConversationRecord.relationship_role,
                        )
                        .join(
                            OwnerPlayerRelationshipRecord,
                            sa.and_(
                                OwnerPlayerRelationshipRecord.owner_id == ConversationRecord.owner_id,
                                OwnerPlayerRelationshipRecord.relationship_id == ConversationRecord.relationship_id,
                                OwnerPlayerRelationshipRecord.player_subject_id == ConversationRecord.player_subject_id,
                                OwnerPlayerRelationshipRecord.relationship_role == ConversationRecord.relationship_role,
                            ),
                        )
                        .where(
                            ConversationRecord.owner_id == owner,
                            ConversationRecord.conversation_id == conversation_id,
                            ConversationRecord.status == ConversationStatus.ACTIVE.value,
                            OwnerPlayerRelationshipRecord.status == "active",
                        )
                    ).one_or_none()
                if row is None:
                    return None
                return MemoryConversationIdentity(
                    owner_id=row.owner_id,
                    conversation_id=row.conversation_id,
                    relationship_id=row.relationship_id,
                    player_subject_id=row.player_subject_id,
                    relationship_role=RelationshipRole(row.relationship_role),
                )
        except SQLAlchemyError:
            raise MemoryCandidateRepositoryError("memory_candidate_repository_unavailable") from None
        except (TypeError, ValueError, ValidationError):
            raise MemoryCandidateRepositoryError("memory_candidate_repository_integrity_failed") from None

    def create_or_replay_candidate(
        self,
        pending: PendingMemoryCandidate,
        *,
        identity: MemoryConversationIdentity,
        requires_confirmation: bool,
        gate_policy_version: str,
    ) -> CandidateCreateResult:
        if not isinstance(pending, PendingMemoryCandidate):
            raise TypeError("pending must be a PendingMemoryCandidate")
        if not isinstance(identity, MemoryConversationIdentity):
            raise TypeError("identity must be a MemoryConversationIdentity")
        fingerprint = compute_candidate_fingerprint(pending)
        payload_sha = compute_payload_sha256(pending.proposal_payload)
        try:
            with self._session_factory() as session:
                with session.begin():
                    locked = _lock_conversation_identity(
                        session,
                        owner_id=pending.owner_id,
                        conversation_id=pending.conversation_id,
                        require_active=True,
                    )
                    if locked is None or locked != identity:
                        return CandidateCreateResult(
                            disposition=CandidateCreateDisposition.IDENTITY_UNAVAILABLE
                        )

                    gate = evaluate_candidate_gate(
                        target_scope=pending.target_scope,
                        candidate_kind=pending.candidate_kind,
                        memory_key=pending.memory_key,
                        operation=pending.operation,
                        provenance_kind=pending.provenance_kind,
                        relationship_role=locked.relationship_role,
                        proposal_confidence=pending.proposal_confidence,
                    )
                    if (
                        not gate.allowed
                        or gate.requires_confirmation is not requires_confirmation
                        or gate.policy_version != gate_policy_version
                    ):
                        return CandidateCreateResult(
                            disposition=CandidateCreateDisposition.SOURCE_INVALID
                        )

                    session.execute(
                        sa.text("SELECT pg_advisory_xact_lock(:lock_id)"),
                        {"lock_id": _candidate_create_lock_id(pending.owner_id, pending.idempotency_key)},
                    )
                    existing = session.scalar(
                        sa.select(MemoryCandidateRecord).where(
                            MemoryCandidateRecord.owner_id == pending.owner_id,
                            MemoryCandidateRecord.idempotency_key == pending.idempotency_key,
                        )
                    )
                    if existing is not None:
                        if existing.request_fingerprint != fingerprint:
                            return CandidateCreateResult(
                                disposition=CandidateCreateDisposition.IDEMPOTENCY_CONFLICT
                            )
                        return CandidateCreateResult(
                            disposition=CandidateCreateDisposition.REPLAYED,
                            candidate=_record_to_candidate(existing),
                        )

                    if not _source_is_valid(session, pending=pending, identity=locked):
                        return CandidateCreateResult(
                            disposition=CandidateCreateDisposition.SOURCE_INVALID
                        )

                    record = MemoryCandidateRecord(
                        candidate_id=pending.candidate_id,
                        schema_version="1.0",
                        owner_id=locked.owner_id,
                        conversation_id=locked.conversation_id,
                        relationship_id=locked.relationship_id,
                        player_subject_id=locked.player_subject_id,
                        relationship_role=locked.relationship_role.value,
                        idempotency_key=pending.idempotency_key,
                        request_fingerprint=fingerprint,
                        source_message_id=pending.source_message_id,
                        source_task_id=pending.source_task_id,
                        source_run_id=pending.source_run_id,
                        source_artifact_sha256=pending.source_artifact_sha256,
                        target_scope=pending.target_scope.value,
                        candidate_kind=pending.candidate_kind.value,
                        memory_key=pending.memory_key,
                        operation=pending.operation.value,
                        proposal_payload=pending.proposal_payload,
                        proposal_payload_sha256=payload_sha,
                        provenance_kind=pending.provenance_kind.value,
                        producer_id=pending.producer_id,
                        producer_version=pending.producer_version,
                        proposal_confidence=(
                            None
                            if pending.proposal_confidence is None
                            else Decimal(str(pending.proposal_confidence))
                        ),
                        gate_policy_version=gate_policy_version,
                        requires_confirmation=requires_confirmation,
                        status=CandidateStatus.PENDING.value,
                        decision_actor_kind=None,
                        decision_actor_id=None,
                        decision_reason_code=None,
                        decided_at=None,
                        materialized_target_kind=None,
                        materialized_target_id=None,
                        materializer_version=None,
                        created_at=pending.created_at,
                        updated_at=pending.created_at,
                        expires_at=pending.expires_at,
                    )
                    session.add(record)
                    session.flush()
                    created = _record_to_candidate(record)
                return CandidateCreateResult(
                    disposition=CandidateCreateDisposition.CREATED,
                    candidate=created,
                )
        except IntegrityError:
            raise MemoryCandidateRepositoryError("memory_candidate_repository_integrity_failed") from None
        except SQLAlchemyError:
            raise MemoryCandidateRepositoryError("memory_candidate_repository_unavailable") from None
        except MemoryCandidateRepositoryError:
            raise
        except (TypeError, ValueError, ValidationError):
            raise MemoryCandidateRepositoryError("memory_candidate_repository_integrity_failed") from None

    def get_candidate(self, *, owner_id: str, candidate_id: UUID) -> MemoryCandidate | None:
        owner = _validate_owner(owner_id)
        _validate_uuid(candidate_id, name="candidate_id")
        try:
            with self._session_factory() as session:
                with session.begin():
                    record = _select_visible_candidate(session, owner_id=owner, candidate_id=candidate_id)
                    result = None if record is None else _record_to_candidate(record)
                return result
        except SQLAlchemyError:
            raise MemoryCandidateRepositoryError("memory_candidate_repository_unavailable") from None
        except (TypeError, ValueError, ValidationError):
            raise MemoryCandidateRepositoryError("memory_candidate_repository_integrity_failed") from None

    def reject_candidate(
        self,
        *,
        owner_id: str,
        candidate_id: UUID,
        actor_id: str,
        reason_code: str,
        now: datetime,
    ) -> CandidateMutationResult:
        owner = _validate_owner(owner_id)
        if _validate_owner(actor_id) != owner:
            raise TypeError("user decision actor must match owner")
        _validate_uuid(candidate_id, name="candidate_id")
        decision_time = _as_utc(now)
        return self._terminal_without_materializer(
            owner_id=owner,
            candidate_id=candidate_id,
            target=CandidateStatus.REJECTED,
            actor_kind=DecisionActorKind.USER,
            actor_id=actor_id,
            reason_code=reason_code,
            now=decision_time,
            require_due=False,
        )

    def expire_candidate(
        self,
        *,
        owner_id: str,
        candidate_id: UUID,
        now: datetime,
    ) -> CandidateMutationResult:
        owner = _validate_owner(owner_id)
        _validate_uuid(candidate_id, name="candidate_id")
        return self._terminal_without_materializer(
            owner_id=owner,
            candidate_id=candidate_id,
            target=CandidateStatus.EXPIRED,
            actor_kind=DecisionActorKind.SYSTEM,
            actor_id="memory-expiry-v1",
            reason_code="expired_by_policy",
            now=_as_utc(now),
            require_due=True,
        )

    def accept_candidate(
        self,
        *,
        owner_id: str,
        candidate_id: UUID,
        actor_id: str,
        actor_kind: DecisionActorKind,
        now: datetime,
        materializers: MaterializerRegistry,
    ) -> CandidateMutationResult:
        owner = _validate_owner(owner_id)
        _validate_uuid(candidate_id, name="candidate_id")
        if not isinstance(actor_kind, DecisionActorKind):
            raise TypeError("actor_kind must be a DecisionActorKind")
        if actor_kind is DecisionActorKind.USER and _validate_owner(actor_id) != owner:
            raise TypeError("user decision actor must match owner")
        _validate_owner(actor_id)
        decision_time = _as_utc(now)
        registry = MappingProxyType(dict(materializers))
        try:
            with self._session_factory() as session:
                with session.begin():
                    record = _lock_visible_candidate(
                        session,
                        owner_id=owner,
                        candidate_id=candidate_id,
                        require_active_conversation=True,
                    )
                    if record is None:
                        return CandidateMutationResult(
                            disposition=CandidateMutationDisposition.NOT_FOUND
                        )
                    current = _record_to_candidate(record)
                    if current.status is CandidateStatus.ACCEPTED:
                        return CandidateMutationResult(
                            disposition=CandidateMutationDisposition.REPLAYED,
                            candidate=current,
                        )
                    if current.status in {CandidateStatus.REJECTED, CandidateStatus.EXPIRED}:
                        return CandidateMutationResult(
                            disposition=CandidateMutationDisposition.TERMINAL_CONFLICT
                        )
                    if decision_time >= current.expires_at:
                        _set_terminal(
                            record,
                            status=CandidateStatus.EXPIRED,
                            actor_kind=DecisionActorKind.SYSTEM,
                            actor_id="memory-expiry-v1",
                            reason_code="expired_by_policy",
                            now=decision_time,
                        )
                        session.flush()
                        expired = _record_to_candidate(record)
                        return CandidateMutationResult(
                            disposition=CandidateMutationDisposition.EXPIRED,
                            candidate=expired,
                        )
                    if actor_kind is DecisionActorKind.SYSTEM and current.requires_confirmation:
                        return CandidateMutationResult(
                            disposition=CandidateMutationDisposition.TERMINAL_CONFLICT
                        )
                    materializer = registry.get(current.candidate_kind)
                    if materializer is None:
                        return CandidateMutationResult(
                            disposition=CandidateMutationDisposition.TARGET_UNAVAILABLE
                        )
                    if materializer.candidate_kind is not current.candidate_kind:
                        raise MemoryCandidateRepositoryError(
                            "memory_candidate_materializer_contract_failed"
                        )
                    reference = materializer.materialize(
                        _MaterializationSession(session),
                        current,
                    )
                    if not isinstance(reference, MaterializedMemoryReference):
                        raise MemoryCandidateRepositoryError(
                            "memory_candidate_materializer_contract_failed"
                        )
                    if (
                        reference.target_kind != current.candidate_kind.value
                        or reference.materializer_version != materializer.version
                    ):
                        raise MemoryCandidateRepositoryError(
                            "memory_candidate_materializer_contract_failed"
                        )
                    session.flush()
                    _set_terminal(
                        record,
                        status=CandidateStatus.ACCEPTED,
                        actor_kind=actor_kind,
                        actor_id=actor_id,
                        reason_code=(
                            "user_confirmed"
                            if actor_kind is DecisionActorKind.USER
                            else "system_allowlisted"
                        ),
                        now=decision_time,
                        reference=reference,
                    )
                    session.flush()
                    accepted = _record_to_candidate(record)
                return CandidateMutationResult(
                    disposition=CandidateMutationDisposition.ACCEPTED,
                    candidate=accepted,
                )
        except MemoryCandidateRepositoryError:
            raise
        except IntegrityError:
            raise MemoryCandidateRepositoryError("memory_candidate_repository_integrity_failed") from None
        except SQLAlchemyError:
            raise MemoryCandidateRepositoryError("memory_candidate_repository_unavailable") from None
        except (TypeError, ValueError, ValidationError):
            raise MemoryCandidateRepositoryError("memory_candidate_repository_integrity_failed") from None
        except Exception:
            raise MemoryCandidateRepositoryError("memory_candidate_materializer_failed") from None

    def _terminal_without_materializer(
        self,
        *,
        owner_id: str,
        candidate_id: UUID,
        target: CandidateStatus,
        actor_kind: DecisionActorKind,
        actor_id: str,
        reason_code: str,
        now: datetime,
        require_due: bool,
    ) -> CandidateMutationResult:
        disposition = (
            CandidateMutationDisposition.REJECTED
            if target is CandidateStatus.REJECTED
            else CandidateMutationDisposition.EXPIRED
        )
        try:
            with self._session_factory() as session:
                with session.begin():
                    record = _lock_visible_candidate(
                        session,
                        owner_id=owner_id,
                        candidate_id=candidate_id,
                        require_active_conversation=False,
                    )
                    if record is None:
                        return CandidateMutationResult(
                            disposition=CandidateMutationDisposition.NOT_FOUND
                        )
                    current = _record_to_candidate(record)
                    if current.status is target:
                        return CandidateMutationResult(
                            disposition=CandidateMutationDisposition.REPLAYED,
                            candidate=current,
                        )
                    if current.status is not CandidateStatus.PENDING:
                        return CandidateMutationResult(
                            disposition=CandidateMutationDisposition.TERMINAL_CONFLICT
                        )
                    if require_due and now < current.expires_at:
                        return CandidateMutationResult(
                            disposition=CandidateMutationDisposition.TERMINAL_CONFLICT
                        )
                    _set_terminal(
                        record,
                        status=target,
                        actor_kind=actor_kind,
                        actor_id=actor_id,
                        reason_code=reason_code,
                        now=now,
                    )
                    session.flush()
                    terminal = _record_to_candidate(record)
                return CandidateMutationResult(
                    disposition=disposition,
                    candidate=terminal,
                )
        except IntegrityError:
            raise MemoryCandidateRepositoryError("memory_candidate_repository_integrity_failed") from None
        except SQLAlchemyError:
            raise MemoryCandidateRepositoryError("memory_candidate_repository_unavailable") from None
        except (TypeError, ValueError, ValidationError):
            raise MemoryCandidateRepositoryError("memory_candidate_repository_integrity_failed") from None


class _MaterializationSession(MaterializationSession):
    __slots__ = ("__session",)

    def __init__(self, session: Session) -> None:
        self.__session = session

    def add(self, instance: object) -> None:
        self.__session.add(instance)

    def flush(self) -> None:
        self.__session.flush()

    def execute(self, statement: object, params: object | None = None) -> Any:
        if params is None:
            return self.__session.execute(statement)
        return self.__session.execute(statement, params)

    def scalar(self, statement: object) -> Any:
        return self.__session.scalar(statement)


def _source_is_valid(
    session: Session,
    *,
    pending: PendingMemoryCandidate,
    identity: MemoryConversationIdentity,
) -> bool:
    if pending.source_message_id is not None:
        message = session.scalar(
            sa.select(ConversationMessageRecord).where(
                ConversationMessageRecord.message_id == pending.source_message_id,
                ConversationMessageRecord.owner_id == identity.owner_id,
                ConversationMessageRecord.conversation_id == identity.conversation_id,
                ConversationMessageRecord.hidden_at.is_(None),
            )
        )
        if message is None:
            return False
    if pending.source_task_id is not None:
        task = session.scalar(
            sa.select(ReviewTaskRecord).where(
                ReviewTaskRecord.task_id == pending.source_task_id,
                ReviewTaskRecord.run_id == pending.source_run_id,
                ReviewTaskRecord.owner_id == identity.owner_id,
                ReviewTaskRecord.conversation_id == identity.conversation_id,
                ReviewTaskRecord.relationship_id == identity.relationship_id,
                ReviewTaskRecord.player_subject_id == identity.player_subject_id,
                ReviewTaskRecord.relationship_role == identity.relationship_role.value,
            )
        )
        if task is None:
            return False
    return True


def _select_visible_candidate(
    session: Session,
    *,
    owner_id: str,
    candidate_id: UUID,
) -> MemoryCandidateRecord | None:
    return session.scalar(
        sa.select(MemoryCandidateRecord)
        .join(
            ConversationRecord,
            sa.and_(
                ConversationRecord.conversation_id == MemoryCandidateRecord.conversation_id,
                ConversationRecord.owner_id == MemoryCandidateRecord.owner_id,
                ConversationRecord.relationship_id == MemoryCandidateRecord.relationship_id,
                ConversationRecord.player_subject_id == MemoryCandidateRecord.player_subject_id,
                ConversationRecord.relationship_role == MemoryCandidateRecord.relationship_role,
            ),
        )
        .join(
            OwnerPlayerRelationshipRecord,
            sa.and_(
                OwnerPlayerRelationshipRecord.owner_id == MemoryCandidateRecord.owner_id,
                OwnerPlayerRelationshipRecord.relationship_id == MemoryCandidateRecord.relationship_id,
                OwnerPlayerRelationshipRecord.player_subject_id == MemoryCandidateRecord.player_subject_id,
                OwnerPlayerRelationshipRecord.relationship_role == MemoryCandidateRecord.relationship_role,
            ),
        )
        .where(
            MemoryCandidateRecord.owner_id == owner_id,
            MemoryCandidateRecord.candidate_id == candidate_id,
            ConversationRecord.status != ConversationStatus.HIDDEN.value,
            OwnerPlayerRelationshipRecord.status == "active",
        )
    )


def _lock_visible_candidate(
    session: Session,
    *,
    owner_id: str,
    candidate_id: UUID,
    require_active_conversation: bool,
) -> MemoryCandidateRecord | None:
    identity = session.execute(
        sa.select(
            MemoryCandidateRecord.conversation_id,
            MemoryCandidateRecord.relationship_id,
            MemoryCandidateRecord.player_subject_id,
            MemoryCandidateRecord.relationship_role,
        ).where(
            MemoryCandidateRecord.owner_id == owner_id,
            MemoryCandidateRecord.candidate_id == candidate_id,
        )
    ).one_or_none()
    if identity is None:
        return None
    locked = _lock_conversation_identity(
        session,
        owner_id=owner_id,
        conversation_id=identity.conversation_id,
        require_active=require_active_conversation,
    )
    if locked is None or (
        locked.relationship_id != identity.relationship_id
        or locked.player_subject_id != identity.player_subject_id
        or locked.relationship_role.value != identity.relationship_role
    ):
        return None
    return session.scalar(
        sa.select(MemoryCandidateRecord)
        .where(
            MemoryCandidateRecord.owner_id == owner_id,
            MemoryCandidateRecord.candidate_id == candidate_id,
            MemoryCandidateRecord.conversation_id == locked.conversation_id,
            MemoryCandidateRecord.relationship_id == locked.relationship_id,
            MemoryCandidateRecord.player_subject_id == locked.player_subject_id,
            MemoryCandidateRecord.relationship_role == locked.relationship_role.value,
        )
        .with_for_update()
    )


def _lock_conversation_identity(
    session: Session,
    *,
    owner_id: str,
    conversation_id: UUID,
    require_active: bool,
) -> MemoryConversationIdentity | None:
    identity = session.execute(
        sa.select(
            ConversationRecord.relationship_id,
            ConversationRecord.player_subject_id,
            ConversationRecord.relationship_role,
        ).where(
            ConversationRecord.owner_id == owner_id,
            ConversationRecord.conversation_id == conversation_id,
            ConversationRecord.status != ConversationStatus.HIDDEN.value,
        )
    ).one_or_none()
    if identity is None:
        return None
    relationship = session.scalar(
        sa.select(OwnerPlayerRelationshipRecord)
        .where(
            OwnerPlayerRelationshipRecord.owner_id == owner_id,
            OwnerPlayerRelationshipRecord.relationship_id == identity.relationship_id,
            OwnerPlayerRelationshipRecord.player_subject_id == identity.player_subject_id,
            OwnerPlayerRelationshipRecord.relationship_role == identity.relationship_role,
        )
        .with_for_update()
    )
    if relationship is None or relationship.status != "active":
        return None
    statuses = [ConversationStatus.ACTIVE.value] if require_active else [
        ConversationStatus.ACTIVE.value,
        ConversationStatus.ARCHIVED.value,
    ]
    conversation = session.scalar(
        sa.select(ConversationRecord)
        .where(
            ConversationRecord.owner_id == owner_id,
            ConversationRecord.conversation_id == conversation_id,
            ConversationRecord.relationship_id == relationship.relationship_id,
            ConversationRecord.player_subject_id == relationship.player_subject_id,
            ConversationRecord.relationship_role == relationship.relationship_role,
            ConversationRecord.status.in_(statuses),
        )
        .with_for_update()
    )
    if conversation is None:
        return None
    return MemoryConversationIdentity(
        owner_id=conversation.owner_id,
        conversation_id=conversation.conversation_id,
        relationship_id=conversation.relationship_id,
        player_subject_id=conversation.player_subject_id,
        relationship_role=RelationshipRole(conversation.relationship_role),
    )


def _set_terminal(
    record: MemoryCandidateRecord,
    *,
    status: CandidateStatus,
    actor_kind: DecisionActorKind,
    actor_id: str,
    reason_code: str,
    now: datetime,
    reference: MaterializedMemoryReference | None = None,
) -> None:
    timestamp = max(_as_utc(now), _as_utc(record.created_at), _as_utc(record.updated_at))
    record.status = status.value
    record.decision_actor_kind = actor_kind.value
    record.decision_actor_id = actor_id
    record.decision_reason_code = reason_code
    record.decided_at = timestamp
    record.updated_at = timestamp
    if reference is not None:
        record.materialized_target_kind = reference.target_kind
        record.materialized_target_id = reference.target_id
        record.materializer_version = reference.materializer_version


def _record_to_candidate(record: MemoryCandidateRecord) -> MemoryCandidate:
    return MemoryCandidate(
        candidate_id=record.candidate_id,
        owner_id=record.owner_id,
        conversation_id=record.conversation_id,
        idempotency_key=record.idempotency_key,
        source_message_id=record.source_message_id,
        source_task_id=record.source_task_id,
        source_run_id=record.source_run_id,
        source_artifact_sha256=record.source_artifact_sha256,
        target_scope=TargetScope(record.target_scope),
        candidate_kind=CandidateKind(record.candidate_kind),
        memory_key=record.memory_key,
        operation=MemoryOperation(record.operation),
        proposal_payload=record.proposal_payload,
        provenance_kind=ProvenanceKind(record.provenance_kind),
        producer_id=record.producer_id,
        producer_version=record.producer_version,
        proposal_confidence=(
            None if record.proposal_confidence is None else float(record.proposal_confidence)
        ),
        created_at=record.created_at,
        expires_at=record.expires_at,
        relationship_id=record.relationship_id,
        player_subject_id=record.player_subject_id,
        relationship_role=RelationshipRole(record.relationship_role),
        request_fingerprint=record.request_fingerprint,
        proposal_payload_sha256=record.proposal_payload_sha256,
        gate_policy_version=record.gate_policy_version,
        requires_confirmation=record.requires_confirmation,
        status=CandidateStatus(record.status),
        decision_actor_kind=(
            None
            if record.decision_actor_kind is None
            else DecisionActorKind(record.decision_actor_kind)
        ),
        decision_actor_id=record.decision_actor_id,
        decision_reason_code=record.decision_reason_code,
        decided_at=record.decided_at,
        materialized_target_kind=record.materialized_target_kind,
        materialized_target_id=record.materialized_target_id,
        materializer_version=record.materializer_version,
        updated_at=record.updated_at,
    )


def _candidate_create_lock_id(owner_id: str, idempotency_key: str) -> int:
    payload = f"{owner_id}\x1f{idempotency_key}".encode("utf-8")
    unsigned = int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")
    return unsigned if unsigned < 2**63 else unsigned - 2**64


def _validate_owner(value: str) -> str:
    try:
        return _OWNER_ADAPTER.validate_python(value, strict=True)
    except (TypeError, ValueError, ValidationError):
        raise TypeError("owner identifier is invalid") from None


def _validate_uuid(value: UUID, *, name: str) -> UUID:
    if not isinstance(value, UUID):
        raise TypeError(f"{name} must be a UUID")
    return value


def _as_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("candidate timestamp must be timezone-aware")
    return value.astimezone(timezone.utc)


__all__ = ["PostgresMemoryCandidateRepository"]
