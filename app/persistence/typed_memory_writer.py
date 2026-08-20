from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import datetime, timezone
from uuid import UUID, uuid4

import sqlalchemy as sa

from app.memory.models import MemoryCandidate, RelationshipRole, compute_payload_sha256
from app.memory.ports import MaterializationSession
from app.memory.typed_models import MemoryTargetKind, ParsedTypedMemoryWrite
from app.memory.typed_materializers import TypedMemoryTargetWriter
from app.persistence.typed_memory_records import (
    MemoryPreferenceRecord,
    PlayerProfileRecord,
    ReviewMemoryRecord,
)


RecordIdFactory = Callable[[], UUID]
Clock = Callable[[], datetime]


class MemoryTargetVersionConflict(RuntimeError):
    """The Candidate expected a target version that is no longer active."""


class PostgresTypedMemoryTargetWriter(TypedMemoryTargetWriter):
    """Versioned typed target writer that never owns commit or rollback."""

    def __init__(
        self,
        *,
        record_id_factory: RecordIdFactory = uuid4,
        clock: Clock | None = None,
    ) -> None:
        if not callable(record_id_factory):
            raise TypeError("record_id_factory must be callable")
        if clock is not None and not callable(clock):
            raise TypeError("clock must be callable")
        self._record_id_factory = record_id_factory
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def write(
        self,
        session: MaterializationSession,
        *,
        candidate: MemoryCandidate,
        parsed: ParsedTypedMemoryWrite,
    ) -> UUID:
        if not isinstance(candidate, MemoryCandidate):
            raise TypeError("candidate must be a MemoryCandidate")
        if not isinstance(parsed, ParsedTypedMemoryWrite):
            raise TypeError("parsed must be a ParsedTypedMemoryWrite")
        if parsed.target_kind.value != candidate.candidate_kind.value:
            raise TypeError("parsed target kind must match Candidate kind")

        lock_key = _scope_lock_key(candidate=candidate, parsed=parsed)
        session.scalar(sa.select(sa.func.pg_advisory_xact_lock(lock_key)))

        record_type = _record_type(parsed.target_kind)
        existing = session.scalar(
            sa.select(record_type).where(
                record_type.source_candidate_id == candidate.candidate_id
            )
        )
        if existing is not None:
            return existing.record_id

        current = session.scalar(_active_statement(candidate=candidate, parsed=parsed))
        _validate_expected_version(current=current, parsed=parsed)

        now = _as_utc(self._clock())
        next_version = 1
        supersedes_record_id = None
        if current is not None:
            next_version = current.version + 1
            supersedes_record_id = current.record_id
            current.status = "superseded"
            current.updated_at = now
            session.flush()

        record_id = self._record_id_factory()
        if not isinstance(record_id, UUID):
            raise TypeError("record_id_factory must return UUID")
        record = record_type(
            record_id=record_id,
            schema_version="1.0",
            owner_id=candidate.owner_id,
            source_conversation_id=candidate.conversation_id,
            relationship_id=candidate.relationship_id,
            player_subject_id=candidate.player_subject_id,
            relationship_role=candidate.relationship_role.value,
            memory_key=candidate.memory_key,
            version=next_version,
            status="active",
            payload=parsed.normalized_payload,
            payload_sha256=compute_payload_sha256(parsed.normalized_payload),
            source_candidate_id=candidate.candidate_id,
            supersedes_record_id=supersedes_record_id,
            created_at=now,
            updated_at=now,
        )
        session.add(record)
        session.flush()
        return record_id


def _active_statement(*, candidate: MemoryCandidate, parsed: ParsedTypedMemoryWrite):
    record_type = _record_type(parsed.target_kind)
    filters = [
        record_type.owner_id == candidate.owner_id,
        record_type.memory_key == candidate.memory_key,
        record_type.status == "active",
    ]
    if parsed.target_kind is not MemoryTargetKind.OWNER_PREFERENCE:
        filters.extend(
            [
                record_type.relationship_id == candidate.relationship_id,
                record_type.player_subject_id == candidate.player_subject_id,
            ]
        )
    if parsed.target_kind is MemoryTargetKind.REVIEW_MEMORY:
        filters.append(record_type.relationship_role == candidate.relationship_role.value)
    return sa.select(record_type).where(*filters).with_for_update()


def _validate_expected_version(*, current: object | None, parsed: ParsedTypedMemoryWrite) -> None:
    current_version = None if current is None else current.version
    if current_version is None:
        if parsed.expected_version is not None:
            raise MemoryTargetVersionConflict("memory_version_conflict")
        return
    if parsed.expected_version != current_version:
        raise MemoryTargetVersionConflict("memory_version_conflict")


def _record_type(target_kind: MemoryTargetKind):
    if target_kind is MemoryTargetKind.OWNER_PREFERENCE:
        return MemoryPreferenceRecord
    if target_kind is MemoryTargetKind.PLAYER_PROFILE:
        return PlayerProfileRecord
    if target_kind is MemoryTargetKind.REVIEW_MEMORY:
        return ReviewMemoryRecord
    raise TypeError("unsupported typed memory target")


def _scope_lock_key(*, candidate: MemoryCandidate, parsed: ParsedTypedMemoryWrite) -> int:
    components = [parsed.target_kind.value, candidate.owner_id]
    if parsed.target_kind is not MemoryTargetKind.OWNER_PREFERENCE:
        components.extend(
            [str(candidate.relationship_id), str(candidate.player_subject_id)]
        )
    if parsed.target_kind is MemoryTargetKind.REVIEW_MEMORY:
        components.append(candidate.relationship_role.value)
    components.append(candidate.memory_key)
    digest = hashlib.sha256("\x1f".join(components).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=True)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("typed memory timestamps must be timezone-aware")
    return value.astimezone(timezone.utc)


__all__ = ["MemoryTargetVersionConflict", "PostgresTypedMemoryTargetWriter"]
