from __future__ import annotations

from datetime import datetime, timedelta, timezone
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
from app.memory.typed_materializers import (
    OwnerPreferenceMaterializer,
    PlayerProfileMaterializer,
    ReviewMemoryMaterializer,
    TypedMemoryMaterializerError,
)


NOW = datetime(2026, 8, 20, 16, 0, tzinfo=timezone.utc)
TARGET_ID = UUID("91000000-0000-4000-8000-000000000001")


class FakeSession:
    def __init__(self) -> None:
        self.marker = object()

    def add(self, instance: object) -> None:
        raise AssertionError("pure writer should decide whether add() is needed")

    def flush(self) -> None:
        raise AssertionError("pure writer should decide whether flush() is needed")

    def execute(self, statement: object, params: object | None = None):
        raise AssertionError("pure writer should decide whether execute() is needed")

    def scalar(self, statement: object):
        raise AssertionError("pure writer should decide whether scalar() is needed")


class RecordingWriter:
    def __init__(self, result: object = TARGET_ID) -> None:
        self.result = result
        self.calls: list[tuple[object, MemoryCandidate, object]] = []

    def write(self, session, *, candidate, parsed):
        self.calls.append((session, candidate, parsed))
        return self.result


def candidate(
    *,
    kind: CandidateKind = CandidateKind.OWNER_PREFERENCE,
    scope: TargetScope = TargetScope.OWNER_GLOBAL,
    key: str = "report_language",
    operation: MemoryOperation = MemoryOperation.SET,
    role: RelationshipRole = RelationshipRole.SELF,
    payload: dict[str, object] | None = None,
) -> MemoryCandidate:
    return MemoryCandidate(
        candidate_id=UUID("90000000-0000-4000-8000-000000000001"),
        owner_id="typed-owner",
        conversation_id=UUID("90000000-0000-4000-8000-000000000002"),
        relationship_id=UUID("90000000-0000-4000-8000-000000000003"),
        player_subject_id=UUID("90000000-0000-4000-8000-000000000004"),
        relationship_role=role,
        idempotency_key="typed-candidate-1",
        request_fingerprint="1" * 64,
        source_message_id=None,
        source_task_id=None,
        source_run_id=None,
        source_artifact_sha256=None,
        target_scope=scope,
        candidate_kind=kind,
        memory_key=key,
        operation=operation,
        proposal_payload=payload or {"value": "zh-CN"},
        proposal_payload_sha256="2" * 64,
        provenance_kind=ProvenanceKind.USER_STRUCTURED_INPUT,
        producer_id="typed-test",
        producer_version="1.0.0",
        proposal_confidence=None,
        gate_policy_version="memory-gate-v1",
        requires_confirmation=False,
        status=CandidateStatus.PENDING,
        created_at=NOW,
        updated_at=NOW,
        expires_at=NOW + timedelta(days=30),
    )


@pytest.mark.parametrize(
    ("materializer_type", "item", "target_kind", "normalized"),
    [
        (
            OwnerPreferenceMaterializer,
            candidate(),
            "owner_preference",
            {"value": "zh-CN"},
        ),
        (
            PlayerProfileMaterializer,
            candidate(
                kind=CandidateKind.PLAYER_PROFILE,
                scope=TargetScope.OWNER_PLAYER,
                key="main_role",
                payload={"value": "TOP"},
            ),
            "player_profile",
            {"value": "TOP"},
        ),
        (
            ReviewMemoryMaterializer,
            candidate(
                kind=CandidateKind.REVIEW_MEMORY,
                scope=TargetScope.OWNER_PLAYER,
                key="public_trend",
                operation=MemoryOperation.APPEND,
                role=RelationshipRole.OBSERVED,
                payload={
                    "value": {
                        "metric": "deaths_before_15",
                        "direction": "down",
                        "value": 1.0,
                    }
                },
            ),
            "review_memory",
            {"metric": "deaths_before_15", "direction": "down", "value": 1.0},
        ),
    ],
)
def test_materializer_parses_candidate_and_returns_bounded_reference(
    materializer_type,
    item,
    target_kind,
    normalized,
) -> None:
    session = FakeSession()
    writer = RecordingWriter()
    materializer = materializer_type(writer)

    reference = materializer.materialize(session, item)

    assert reference.target_kind == target_kind
    assert reference.target_id == TARGET_ID
    assert reference.materializer_version == materializer.version
    assert len(writer.calls) == 1
    passed_session, passed_candidate, parsed = writer.calls[0]
    assert passed_session is session
    assert passed_candidate is item
    assert parsed.normalized_payload == normalized


def test_materializer_rejects_wrong_candidate_kind_without_calling_writer() -> None:
    writer = RecordingWriter()
    materializer = OwnerPreferenceMaterializer(writer)
    with pytest.raises(TypedMemoryMaterializerError, match="typed_materializer_kind_mismatch"):
        materializer.materialize(
            FakeSession(),
            candidate(
                kind=CandidateKind.PLAYER_PROFILE,
                scope=TargetScope.OWNER_PLAYER,
                key="main_role",
                payload={"value": "TOP"},
            ),
        )
    assert writer.calls == []


def test_materializer_rejects_invalid_target_id() -> None:
    materializer = OwnerPreferenceMaterializer(RecordingWriter(result="not-a-uuid"))
    with pytest.raises(TypedMemoryMaterializerError, match="typed_materializer_target_id_invalid"):
        materializer.materialize(FakeSession(), candidate())


def test_materializer_has_no_commit_or_rollback_dependency() -> None:
    session = FakeSession()
    assert not hasattr(session, "commit")
    assert not hasattr(session, "rollback")
    reference = OwnerPreferenceMaterializer(RecordingWriter()).materialize(
        session,
        candidate(),
    )
    assert reference.target_id == TARGET_ID


def test_writer_failure_propagates_for_outer_transaction_rollback() -> None:
    class FailingWriter:
        def write(self, session, *, candidate, parsed):
            del session, candidate, parsed
            raise RuntimeError("writer failed")

    with pytest.raises(RuntimeError, match="writer failed"):
        OwnerPreferenceMaterializer(FailingWriter()).materialize(
            FakeSession(),
            candidate(),
        )


def test_constructor_requires_a_writer_port() -> None:
    with pytest.raises(TypeError, match="writer must expose write"):
        OwnerPreferenceMaterializer(object())
