from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID

import pytest

from app.memory.models import (
    CandidateKind,
    CandidateStatus,
    MemoryCandidate,
    MemoryOperation,
    ProvenanceKind,
    RelationshipRole,
    TargetScope,
)
from app.memory.typed_models import parse_typed_memory_write
from app.persistence.typed_memory_writer import (
    MemoryTargetVersionConflict,
    PostgresTypedMemoryTargetWriter,
)


NOW = datetime(2026, 8, 20, 17, 0, tzinfo=timezone.utc)
NEW_ID = UUID("92000000-0000-4000-8000-000000000001")


class FakeMaterializationSession:
    def __init__(self, scalar_results: list[object | None]) -> None:
        self.scalar_results = list(scalar_results)
        self.scalar_calls: list[object] = []
        self.added: list[object] = []
        self.flush_count = 0

    def scalar(self, statement: object):
        self.scalar_calls.append(statement)
        return self.scalar_results.pop(0)

    def add(self, instance: object) -> None:
        self.added.append(instance)

    def flush(self) -> None:
        self.flush_count += 1

    def execute(self, statement: object, params: object | None = None):
        raise AssertionError("writer uses scalar for lock/select operations")


def candidate(*, payload: dict[str, object] | None = None, number: int = 1) -> MemoryCandidate:
    return MemoryCandidate(
        candidate_id=UUID(f"92000000-0000-4000-8001-{number:012d}"),
        owner_id="writer-owner",
        conversation_id=UUID("92000000-0000-4000-8002-000000000001"),
        relationship_id=UUID("92000000-0000-4000-8003-000000000001"),
        player_subject_id=UUID("92000000-0000-4000-8004-000000000001"),
        relationship_role=RelationshipRole.SELF,
        idempotency_key=f"writer-{number}",
        request_fingerprint=f"{number:064x}",
        source_message_id=None,
        source_task_id=None,
        source_run_id=None,
        source_artifact_sha256=None,
        target_scope=TargetScope.OWNER_GLOBAL,
        candidate_kind=CandidateKind.OWNER_PREFERENCE,
        memory_key="report_language",
        operation=MemoryOperation.SET,
        proposal_payload=payload or {"value": "zh-CN"},
        proposal_payload_sha256="2" * 64,
        provenance_kind=ProvenanceKind.USER_STRUCTURED_INPUT,
        producer_id="writer-test",
        producer_version="1.0.0",
        proposal_confidence=None,
        gate_policy_version="memory-gate-v1",
        requires_confirmation=False,
        status=CandidateStatus.PENDING,
        created_at=NOW,
        updated_at=NOW,
        expires_at=NOW + timedelta(days=30),
    )


def parsed(item: MemoryCandidate):
    return parse_typed_memory_write(
        target_scope=item.target_scope,
        candidate_kind=item.candidate_kind,
        memory_key=item.memory_key,
        operation=item.operation,
        relationship_role=item.relationship_role,
        proposal_payload=item.proposal_payload,
    )


def writer() -> PostgresTypedMemoryTargetWriter:
    return PostgresTypedMemoryTargetWriter(
        record_id_factory=lambda: NEW_ID,
        clock=lambda: NOW,
    )


def test_first_write_creates_version_one_without_supersedes() -> None:
    item = candidate()
    session = FakeMaterializationSession([None, None, None])
    target_id = writer().write(session, candidate=item, parsed=parsed(item))
    assert target_id == NEW_ID
    assert len(session.scalar_calls) == 3
    assert session.flush_count == 1
    record = session.added[0]
    assert record.version == 1
    assert record.status == "active"
    assert record.supersedes_record_id is None
    assert record.source_candidate_id == item.candidate_id
    assert record.payload == {"value": "zh-CN"}


def test_update_supersedes_current_and_creates_next_version() -> None:
    current_id = UUID("92000000-0000-4000-8005-000000000001")
    current = SimpleNamespace(
        record_id=current_id,
        version=1,
        status="active",
        updated_at=NOW - timedelta(days=1),
    )
    item = candidate(payload={"value": "en-US", "expected_version": 1}, number=2)
    session = FakeMaterializationSession([None, None, current])
    writer().write(session, candidate=item, parsed=parsed(item))
    assert current.status == "superseded"
    assert current.updated_at == NOW
    assert session.flush_count == 2
    record = session.added[0]
    assert record.version == 2
    assert record.supersedes_record_id == current_id
    assert record.payload == {"value": "en-US"}


@pytest.mark.parametrize(
    ("current", "expected"),
    [
        (None, 1),
        (SimpleNamespace(version=1), None),
        (SimpleNamespace(version=2), 1),
    ],
)
def test_stale_or_missing_expected_version_fails_before_mutation(current, expected) -> None:
    item = candidate(payload={"value": "en-US", "expected_version": expected}, number=3)
    session = FakeMaterializationSession([None, None, current])
    with pytest.raises(MemoryTargetVersionConflict, match="memory_version_conflict"):
        writer().write(session, candidate=item, parsed=parsed(item))
    assert session.added == []
    assert session.flush_count == 0


def test_same_source_candidate_replays_existing_target() -> None:
    existing = SimpleNamespace(record_id=NEW_ID)
    item = candidate()
    session = FakeMaterializationSession([None, existing])
    assert writer().write(session, candidate=item, parsed=parsed(item)) == NEW_ID
    assert session.added == []
    assert session.flush_count == 0


def test_writer_rejects_naive_clock_and_non_uuid_factory() -> None:
    item = candidate()
    with pytest.raises(ValueError, match="timezone-aware"):
        PostgresTypedMemoryTargetWriter(
            record_id_factory=lambda: NEW_ID,
            clock=lambda: datetime(2026, 8, 20, 17, 0),
        ).write(
            FakeMaterializationSession([None, None, None]),
            candidate=item,
            parsed=parsed(item),
        )
    with pytest.raises(TypeError, match="record_id_factory must return UUID"):
        PostgresTypedMemoryTargetWriter(
            record_id_factory=lambda: "bad-id",
            clock=lambda: NOW,
        ).write(
            FakeMaterializationSession([None, None, None]),
            candidate=item,
            parsed=parsed(item),
        )
