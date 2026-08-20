from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.memory.models import (
    CandidateKind,
    CandidateStatus,
    MaterializedMemoryReference,
    MemoryCandidate,
    MemoryCandidateView,
    MemoryOperation,
    PendingMemoryCandidate,
    ProvenanceKind,
    RelationshipRole,
    TargetScope,
    DecisionActorKind,
    canonical_payload_bytes,
    compute_candidate_fingerprint,
    compute_payload_sha256,
)


NOW = datetime(2026, 8, 20, 10, 0, tzinfo=timezone.utc)
OWNER = "owner-memory-test"
CONVERSATION_ID = UUID("71000000-0000-4000-8000-000000000001")
CANDIDATE_ID = UUID("71000000-0000-4000-8000-000000000002")
RELATIONSHIP_ID = UUID("71000000-0000-4000-8000-000000000003")
SUBJECT_ID = UUID("71000000-0000-4000-8000-000000000004")
TARGET_ID = UUID("71000000-0000-4000-8000-000000000005")


def pending(**overrides: object) -> PendingMemoryCandidate:
    values: dict[str, object] = {
        "candidate_id": CANDIDATE_ID,
        "owner_id": OWNER,
        "conversation_id": CONVERSATION_ID,
        "idempotency_key": "memory-request-1",
        "target_scope": TargetScope.OWNER_GLOBAL,
        "candidate_kind": CandidateKind.OWNER_PREFERENCE,
        "memory_key": "report_language",
        "operation": MemoryOperation.SET,
        "proposal_payload": {"value": "zh-CN"},
        "provenance_kind": ProvenanceKind.USER_STRUCTURED_INPUT,
        "producer_id": "public-api",
        "producer_version": "1.0.0",
        "proposal_confidence": None,
        "source_message_id": None,
        "source_task_id": None,
        "source_run_id": None,
        "source_artifact_sha256": None,
        "created_at": NOW,
        "expires_at": datetime(2026, 9, 19, 10, 0, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return PendingMemoryCandidate(**values)


def candidate(**overrides: object) -> MemoryCandidate:
    values: dict[str, object] = {
        **pending().model_dump(),
        "relationship_id": RELATIONSHIP_ID,
        "player_subject_id": SUBJECT_ID,
        "relationship_role": RelationshipRole.SELF,
        "request_fingerprint": compute_candidate_fingerprint(pending()),
        "proposal_payload_sha256": compute_payload_sha256({"value": "zh-CN"}),
        "gate_policy_version": "memory-gate-v1",
        "requires_confirmation": False,
        "status": CandidateStatus.PENDING,
        "decision_actor_kind": None,
        "decision_actor_id": None,
        "decision_reason_code": None,
        "decided_at": None,
        "materialized_target_kind": None,
        "materialized_target_id": None,
        "materializer_version": None,
        "updated_at": NOW,
    }
    values.update(overrides)
    return MemoryCandidate(**values)


def test_payload_is_canonical_and_bounded() -> None:
    assert canonical_payload_bytes({"b": 2, "a": 1}) == b'{"a":1,"b":2}'
    assert compute_payload_sha256({"value": "zh-CN"}) == (
        "501996d9ff18153da19d4568903b783571b80e43c5ada9648e44d4e28f15b30d"
    )


def test_payload_rejects_non_object_or_unstable_values() -> None:
    with pytest.raises(ValueError, match="JSON object"):
        canonical_payload_bytes(["not", "an", "object"])
    with pytest.raises(ValueError, match="finite"):
        canonical_payload_bytes({"value": float("nan")})


def test_candidate_inherits_strict_identity_and_pending_shape() -> None:
    item = candidate()
    assert item.status is CandidateStatus.PENDING
    assert item.relationship_role is RelationshipRole.SELF
    assert item.materialized_target_id is None
    with pytest.raises(ValidationError, match="pending candidate cannot contain"):
        candidate(materialized_target_id=TARGET_ID)


def test_accepted_candidate_requires_materialization_reference_and_decision() -> None:
    with pytest.raises(ValidationError, match="accepted candidate requires"):
        candidate(status=CandidateStatus.ACCEPTED)
    item = candidate(
        status=CandidateStatus.ACCEPTED,
        decision_actor_kind=DecisionActorKind.USER,
        decision_actor_id=OWNER,
        decision_reason_code="user_confirmed",
        decided_at=NOW,
        materialized_target_kind="owner_preference",
        materialized_target_id=TARGET_ID,
        materializer_version="preference-v1",
    )
    assert item.status is CandidateStatus.ACCEPTED


def test_rejected_candidate_cannot_contain_materialization() -> None:
    with pytest.raises(ValidationError, match="rejected or expired candidate cannot contain"):
        candidate(
            status=CandidateStatus.REJECTED,
            decision_actor_kind=DecisionActorKind.USER,
            decision_actor_id=OWNER,
            decision_reason_code="user_rejected",
            decided_at=NOW,
            materialized_target_kind="owner_preference",
            materialized_target_id=TARGET_ID,
            materializer_version="preference-v1",
        )


def test_public_view_omits_payload_and_full_provenance() -> None:
    view = MemoryCandidateView.from_candidate(candidate())
    dumped = view.model_dump()
    assert "proposal_payload" not in dumped
    assert "producer_id" not in dumped
    assert "proposal_confidence" not in dumped
    assert "player_subject_id" not in dumped
