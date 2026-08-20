from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import datetime, timezone
from uuid import UUID

import sqlalchemy as sa
from pydantic import TypeAdapter, ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.conversations.models import (
    Conversation,
    ConversationMessage,
    ConversationMessageRole,
    ConversationRepositoryAppendDisposition,
    ConversationRepositoryAppendResult,
    ConversationRepositoryCreateDisposition,
    ConversationRepositoryCreateResult,
    ConversationRepositoryListDisposition,
    ConversationRepositoryListResult,
    ConversationRepositoryMutationDisposition,
    ConversationRepositoryMutationResult,
    ConversationStatus,
    OwnerId,
    PendingConversation,
    PendingUserMessage,
    RelationshipRole,
)
from app.conversations.ports import ConversationRepositoryError
from app.persistence.conversation_records import (
    ConversationMessageRecord,
    ConversationRecord,
)
from app.persistence.player_records import OwnerPlayerRelationshipRecord


SessionFactory = Callable[[], Session]
_OWNER_ID_ADAPTER = TypeAdapter(OwnerId)


class PostgresConversationRepository:
    """PostgreSQL control-plane storage for Conversations and Messages.

    Every method owns one short transaction.  No callback, network client,
    model provider, or file operation can run while a relationship or
    Conversation row lock is held.
    """

    def __init__(self, session_factory: SessionFactory) -> None:
        if not callable(session_factory):
            raise TypeError("session_factory must be callable")
        self._session_factory = session_factory

    def create_or_replay_conversation(
        self,
        pending: PendingConversation,
    ) -> ConversationRepositoryCreateResult:
        if not isinstance(pending, PendingConversation):
            raise TypeError("pending must be a PendingConversation")
        try:
            with self._session_factory() as session:
                with session.begin():
                    relationship = session.scalar(
                        sa.select(OwnerPlayerRelationshipRecord)
                        .where(
                            OwnerPlayerRelationshipRecord.owner_id
                            == pending.owner_id,
                            OwnerPlayerRelationshipRecord.relationship_id
                            == pending.relationship_id,
                        )
                        .with_for_update()
                    )
                    if relationship is None or relationship.status != "active":
                        return ConversationRepositoryCreateResult(
                            disposition=(
                                ConversationRepositoryCreateDisposition.
                                RELATIONSHIP_UNAVAILABLE
                            )
                        )

                    # The relationship row serializes normal retries for one
                    # subject.  This transaction advisory lock also closes the
                    # rare same-owner/key race across two different active
                    # relationships without serializing unrelated owners or
                    # idempotency keys behind one global lock.
                    session.execute(
                        sa.text(
                            "SELECT pg_advisory_xact_lock("
                            ":conversation_create_lock_id)"
                        ),
                        {
                            "conversation_create_lock_id": (
                                _conversation_create_lock_id(
                                    pending.owner_id,
                                    pending.idempotency_key,
                                )
                            )
                        },
                    )
                    existing = session.scalar(
                        sa.select(ConversationRecord).where(
                            ConversationRecord.owner_id == pending.owner_id,
                            ConversationRecord.idempotency_key
                            == pending.idempotency_key,
                        )
                    )
                    if existing is not None:
                        if existing.status == ConversationStatus.HIDDEN.value:
                            return ConversationRepositoryCreateResult(
                                disposition=(
                                    ConversationRepositoryCreateDisposition.
                                    RELATIONSHIP_UNAVAILABLE
                                )
                            )
                        if (
                            existing.request_fingerprint
                            == pending.request_fingerprint
                        ):
                            return ConversationRepositoryCreateResult(
                                disposition=(
                                    ConversationRepositoryCreateDisposition.REPLAYED
                                ),
                                conversation=_record_to_conversation(existing),
                            )
                        return ConversationRepositoryCreateResult(
                            disposition=(
                                ConversationRepositoryCreateDisposition.
                                IDEMPOTENCY_CONFLICT
                            )
                        )

                    record = ConversationRecord(
                        conversation_id=pending.conversation_id,
                        schema_version=pending.schema_version,
                        owner_id=pending.owner_id,
                        relationship_id=relationship.relationship_id,
                        player_subject_id=relationship.player_subject_id,
                        relationship_role=relationship.relationship_role,
                        idempotency_key=pending.idempotency_key,
                        request_fingerprint=pending.request_fingerprint,
                        status=ConversationStatus.ACTIVE.value,
                        next_message_sequence=1,
                        created_at=pending.created_at,
                        updated_at=pending.created_at,
                        last_message_at=None,
                        hidden_at=None,
                    )
                    session.add(record)
                    session.flush()
                    created = _record_to_conversation(record)
                return ConversationRepositoryCreateResult(
                    disposition=ConversationRepositoryCreateDisposition.CREATED,
                    conversation=created,
                )
        except ConversationRepositoryError:
            raise
        except IntegrityError:
            raise ConversationRepositoryError(
                "conversation_repository_integrity_failed"
            ) from None
        except SQLAlchemyError:
            raise ConversationRepositoryError(
                "conversation_repository_unavailable"
            ) from None
        except (TypeError, ValueError, ValidationError):
            raise ConversationRepositoryError(
                "conversation_repository_integrity_failed"
            ) from None

    def get_conversation(
        self,
        *,
        owner_id: str,
        conversation_id: UUID,
    ) -> Conversation | None:
        normalized_owner_id = _validate_owner_id(owner_id)
        _validate_uuid(conversation_id, name="conversation_id")
        try:
            with self._session_factory() as session:
                with session.begin():
                    record = _select_visible_conversation(
                        session,
                        owner_id=normalized_owner_id,
                        conversation_id=conversation_id,
                    )
                    conversation = (
                        None if record is None else _record_to_conversation(record)
                    )
                return conversation
        except ConversationRepositoryError:
            raise
        except SQLAlchemyError:
            raise ConversationRepositoryError(
                "conversation_repository_unavailable"
            ) from None
        except (TypeError, ValueError, ValidationError):
            raise ConversationRepositoryError(
                "conversation_repository_integrity_failed"
            ) from None

    def append_user_message(
        self,
        pending: PendingUserMessage,
    ) -> ConversationRepositoryAppendResult:
        if not isinstance(pending, PendingUserMessage):
            raise TypeError("pending must be a PendingUserMessage")
        try:
            with self._session_factory() as session:
                with session.begin():
                    record = _lock_visible_conversation(
                        session,
                        owner_id=pending.owner_id,
                        conversation_id=pending.conversation_id,
                    )
                    if record is None:
                        return ConversationRepositoryAppendResult(
                            disposition=(
                                ConversationRepositoryAppendDisposition.NOT_FOUND
                            )
                        )
                    if record.status == ConversationStatus.ARCHIVED.value:
                        return ConversationRepositoryAppendResult(
                            disposition=(
                                ConversationRepositoryAppendDisposition.ARCHIVED
                            )
                        )
                    if record.status != ConversationStatus.ACTIVE.value:
                        return ConversationRepositoryAppendResult(
                            disposition=(
                                ConversationRepositoryAppendDisposition.NOT_FOUND
                            )
                        )

                    message_time = _monotonic_time(
                        pending.created_at,
                        record.created_at,
                        record.updated_at,
                        record.last_message_at,
                    )
                    sequence_no = record.next_message_sequence
                    message_record = ConversationMessageRecord(
                        message_id=pending.message_id,
                        conversation_id=record.conversation_id,
                        owner_id=record.owner_id,
                        relationship_id=record.relationship_id,
                        player_subject_id=record.player_subject_id,
                        relationship_role=record.relationship_role,
                        sequence_no=sequence_no,
                        role=ConversationMessageRole.USER.value,
                        content=pending.content,
                        content_sha256=pending.content_sha256,
                        source_task_id=None,
                        source_run_id=None,
                        created_at=message_time,
                        hidden_at=None,
                    )
                    session.add(message_record)
                    record.next_message_sequence = sequence_no + 1
                    record.updated_at = message_time
                    record.last_message_at = message_time
                    session.flush()
                    message = _record_to_message(message_record)
                return ConversationRepositoryAppendResult(
                    disposition=ConversationRepositoryAppendDisposition.CREATED,
                    message=message,
                )
        except ConversationRepositoryError:
            raise
        except IntegrityError:
            raise ConversationRepositoryError(
                "conversation_repository_integrity_failed"
            ) from None
        except SQLAlchemyError:
            raise ConversationRepositoryError(
                "conversation_repository_unavailable"
            ) from None
        except (TypeError, ValueError, ValidationError):
            raise ConversationRepositoryError(
                "conversation_repository_integrity_failed"
            ) from None

    def list_messages(
        self,
        *,
        owner_id: str,
        conversation_id: UUID,
        after_sequence: int,
        limit: int,
    ) -> ConversationRepositoryListResult:
        normalized_owner_id = _validate_owner_id(owner_id)
        _validate_uuid(conversation_id, name="conversation_id")
        if type(after_sequence) is not int or after_sequence < 0:
            raise TypeError("after_sequence must be a non-negative integer")
        if type(limit) is not int or not 1 <= limit <= 100:
            raise TypeError("limit must be an integer between 1 and 100")
        try:
            with self._session_factory() as session:
                with session.begin():
                    conversation = _lock_visible_conversation(
                        session,
                        owner_id=normalized_owner_id,
                        conversation_id=conversation_id,
                    )
                    if conversation is None:
                        return ConversationRepositoryListResult(
                            disposition=(
                                ConversationRepositoryListDisposition.NOT_FOUND
                            )
                        )
                    records = session.scalars(
                        sa.select(ConversationMessageRecord)
                        .where(
                            ConversationMessageRecord.owner_id
                            == normalized_owner_id,
                            ConversationMessageRecord.conversation_id
                            == conversation_id,
                            ConversationMessageRecord.hidden_at.is_(None),
                            ConversationMessageRecord.sequence_no > after_sequence,
                        )
                        .order_by(ConversationMessageRecord.sequence_no.asc())
                        .limit(limit + 1)
                    ).all()
                    has_more = len(records) > limit
                    messages = tuple(
                        _record_to_message(record) for record in records[:limit]
                    )
                return ConversationRepositoryListResult(
                    disposition=ConversationRepositoryListDisposition.FOUND,
                    messages=messages,
                    has_more=has_more,
                )
        except ConversationRepositoryError:
            raise
        except SQLAlchemyError:
            raise ConversationRepositoryError(
                "conversation_repository_unavailable"
            ) from None
        except (TypeError, ValueError, ValidationError):
            raise ConversationRepositoryError(
                "conversation_repository_integrity_failed"
            ) from None

    def archive_conversation(
        self,
        *,
        owner_id: str,
        conversation_id: UUID,
        now: datetime,
    ) -> ConversationRepositoryMutationResult:
        return self._mutate_conversation(
            owner_id=owner_id,
            conversation_id=conversation_id,
            now=now,
            target=ConversationStatus.ARCHIVED,
        )

    def hide_conversation(
        self,
        *,
        owner_id: str,
        conversation_id: UUID,
        now: datetime,
    ) -> ConversationRepositoryMutationResult:
        return self._mutate_conversation(
            owner_id=owner_id,
            conversation_id=conversation_id,
            now=now,
            target=ConversationStatus.HIDDEN,
        )

    def _mutate_conversation(
        self,
        *,
        owner_id: str,
        conversation_id: UUID,
        now: datetime,
        target: ConversationStatus,
    ) -> ConversationRepositoryMutationResult:
        normalized_owner_id = _validate_owner_id(owner_id)
        _validate_uuid(conversation_id, name="conversation_id")
        normalized_now = _as_utc(now)
        if target not in {ConversationStatus.ARCHIVED, ConversationStatus.HIDDEN}:
            raise TypeError("unsupported conversation mutation target")
        try:
            with self._session_factory() as session:
                with session.begin():
                    record = _lock_visible_conversation(
                        session,
                        owner_id=normalized_owner_id,
                        conversation_id=conversation_id,
                    )
                    if record is None:
                        return ConversationRepositoryMutationResult(
                            disposition=(
                                ConversationRepositoryMutationDisposition.NOT_FOUND
                            )
                        )
                    if record.status == target.value:
                        return ConversationRepositoryMutationResult(
                            disposition=(
                                ConversationRepositoryMutationDisposition.REPLAYED
                            ),
                            conversation=_record_to_conversation(record),
                        )

                    mutation_time = _monotonic_time(
                        normalized_now,
                        record.created_at,
                        record.updated_at,
                        record.last_message_at,
                    )
                    record.status = target.value
                    record.updated_at = mutation_time
                    if target is ConversationStatus.HIDDEN:
                        record.hidden_at = mutation_time
                    session.flush()
                    mutated = _record_to_conversation(record)
                return ConversationRepositoryMutationResult(
                    disposition=ConversationRepositoryMutationDisposition.UPDATED,
                    conversation=mutated,
                )
        except ConversationRepositoryError:
            raise
        except IntegrityError:
            raise ConversationRepositoryError(
                "conversation_repository_integrity_failed"
            ) from None
        except SQLAlchemyError:
            raise ConversationRepositoryError(
                "conversation_repository_unavailable"
            ) from None
        except (TypeError, ValueError, ValidationError):
            raise ConversationRepositoryError(
                "conversation_repository_integrity_failed"
            ) from None


def _select_visible_conversation(
    session: Session,
    *,
    owner_id: str,
    conversation_id: UUID,
) -> ConversationRecord | None:
    return session.scalar(
        sa.select(ConversationRecord)
        .join(
            OwnerPlayerRelationshipRecord,
            sa.and_(
                OwnerPlayerRelationshipRecord.owner_id
                == ConversationRecord.owner_id,
                OwnerPlayerRelationshipRecord.relationship_id
                == ConversationRecord.relationship_id,
                OwnerPlayerRelationshipRecord.player_subject_id
                == ConversationRecord.player_subject_id,
                OwnerPlayerRelationshipRecord.relationship_role
                == ConversationRecord.relationship_role,
            ),
        )
        .where(
            ConversationRecord.owner_id == owner_id,
            ConversationRecord.conversation_id == conversation_id,
            ConversationRecord.status != ConversationStatus.HIDDEN.value,
            OwnerPlayerRelationshipRecord.status == "active",
        )
    )


def _lock_visible_conversation(
    session: Session,
    *,
    owner_id: str,
    conversation_id: UUID,
) -> ConversationRecord | None:
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
            OwnerPlayerRelationshipRecord.relationship_id
            == identity.relationship_id,
            OwnerPlayerRelationshipRecord.player_subject_id
            == identity.player_subject_id,
            OwnerPlayerRelationshipRecord.relationship_role
            == identity.relationship_role,
        )
        .with_for_update()
    )
    if relationship is None or relationship.status != "active":
        return None

    return session.scalar(
        sa.select(ConversationRecord)
        .where(
            ConversationRecord.owner_id == owner_id,
            ConversationRecord.conversation_id == conversation_id,
            ConversationRecord.relationship_id == relationship.relationship_id,
            ConversationRecord.player_subject_id
            == relationship.player_subject_id,
            ConversationRecord.relationship_role
            == relationship.relationship_role,
            ConversationRecord.status != ConversationStatus.HIDDEN.value,
        )
        .with_for_update()
    )


def _record_to_conversation(record: ConversationRecord) -> Conversation:
    return Conversation(
        conversation_id=record.conversation_id,
        schema_version=record.schema_version,
        owner_id=record.owner_id,
        relationship_id=record.relationship_id,
        player_subject_id=record.player_subject_id,
        relationship_role=RelationshipRole(record.relationship_role),
        idempotency_key=record.idempotency_key,
        request_fingerprint=record.request_fingerprint,
        status=ConversationStatus(record.status),
        next_message_sequence=record.next_message_sequence,
        created_at=record.created_at,
        updated_at=record.updated_at,
        last_message_at=record.last_message_at,
        hidden_at=record.hidden_at,
    )


def _record_to_message(record: ConversationMessageRecord) -> ConversationMessage:
    return ConversationMessage(
        message_id=record.message_id,
        conversation_id=record.conversation_id,
        owner_id=record.owner_id,
        relationship_id=record.relationship_id,
        player_subject_id=record.player_subject_id,
        relationship_role=RelationshipRole(record.relationship_role),
        sequence_no=record.sequence_no,
        role=ConversationMessageRole(record.role),
        content=record.content,
        content_sha256=record.content_sha256,
        source_task_id=record.source_task_id,
        source_run_id=record.source_run_id,
        created_at=record.created_at,
        hidden_at=record.hidden_at,
    )


def _validate_owner_id(value: str) -> str:
    try:
        return _OWNER_ID_ADAPTER.validate_python(value, strict=True)
    except (TypeError, ValueError, ValidationError):
        raise TypeError("owner_id must be a bounded safe identifier") from None


def _conversation_create_lock_id(owner_id: str, idempotency_key: str) -> int:
    """Return one stable signed-bigint advisory lock key for a request scope."""

    payload = f"{owner_id}\x1f{idempotency_key}".encode("utf-8")
    unsigned = int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")
    return unsigned if unsigned < 2**63 else unsigned - 2**64


def _validate_uuid(value: UUID, *, name: str) -> UUID:
    if not isinstance(value, UUID):
        raise TypeError(f"{name} must be a UUID")
    return value


def _as_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError("now must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    return value.astimezone(timezone.utc)


def _monotonic_time(
    candidate: datetime,
    created_at: datetime,
    updated_at: datetime,
    last_message_at: datetime | None,
) -> datetime:
    values = [
        _as_utc(candidate),
        _as_utc(created_at),
        _as_utc(updated_at),
    ]
    if last_message_at is not None:
        values.append(_as_utc(last_message_at))
    return max(values)


__all__ = ["PostgresConversationRepository"]
