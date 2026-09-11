from datetime import datetime

import pytest

from app.memory.gate import evaluate_candidate_gate
from app.memory.models import CandidateKind, MemoryOperation, ProvenanceKind, RelationshipRole, TargetScope
from app.memory.typed_models import ObservationNotePayload, TypedMemoryContractError, parse_typed_memory_write


def _gate(**overrides):
    values = dict(
        target_scope=TargetScope.OWNER_PLAYER,
        candidate_kind=CandidateKind.REVIEW_MEMORY,
        memory_key="observation_note",
        operation=MemoryOperation.APPEND,
        provenance_kind=ProvenanceKind.USER_STRUCTURED_INPUT,
        relationship_role=RelationshipRole.OBSERVED,
        proposal_confidence=None,
    )
    values.update(overrides)
    return evaluate_candidate_gate(**values)


def test_user_observation_requires_confirmation_and_v2_policy():
    decision = _gate()
    assert decision.allowed is True
    assert decision.requires_confirmation is True
    assert decision.auto_accept_eligible is False
    assert decision.policy_version == "memory-gate-v2-user-observation"


@pytest.mark.parametrize("changes", [
    {"candidate_kind": CandidateKind.REVIEW_MEMORY, "memory_key": "public_trend"},
    {"candidate_kind": CandidateKind.TRAINING_PLAN},
    {"memory_key": "review_summary"},
    {"operation": MemoryOperation.SET},
    {"relationship_role": RelationshipRole.SELF},
])
def test_user_observation_allowlist_does_not_widen(changes):
    assert _gate(**changes).allowed is False


def test_old_text_payload_remains_compatible():
    value = parse_typed_memory_write(
        target_scope=TargetScope.OWNER_PLAYER,
        candidate_kind=CandidateKind.REVIEW_MEMORY,
        memory_key="observation_note",
        operation=MemoryOperation.APPEND,
        relationship_role=RelationshipRole.OBSERVED,
        proposal_payload={"value": {"text": "观摩记录"}},
    )
    assert value.normalized_payload == {"text": "观摩记录"}


def test_archive_reference_is_normalized_and_bounded():
    payload = ObservationNotePayload.model_validate({
        "text": "观摩记录",
        "archive_reference": {
            "kind": "user_attached_archive",
            "source_run_id": "golden_20260910_compact_1cd694d",
            "bundle_digest": "a" * 64,
            "report_sha256": "b" * 64,
            "observed_at": "2026-09-10T12:15:25+00:00",
        },
    })
    assert payload.archive_reference is not None
    assert payload.archive_reference.observed_at.endswith("+00:00")


@pytest.mark.parametrize("reference", [
    {"kind": "user_attached_archive", "source_run_id": "x", "bundle_digest": "A" * 64, "report_sha256": "b" * 64, "observed_at": "2026-09-10T12:00:00+00:00"},
    {"kind": "user_attached_archive", "source_run_id": "../escape", "bundle_digest": "a" * 64, "report_sha256": "b" * 64, "observed_at": "2026-09-10T12:00:00+00:00"},
    {"kind": "user_attached_archive", "source_run_id": "x", "bundle_digest": "a" * 64, "report_sha256": "b" * 64, "observed_at": "2026-09-10T12:00:00"},
    {"kind": "user_attached_archive", "source_run_id": "x", "bundle_digest": "a" * 64, "report_sha256": "b" * 64, "observed_at": "2026-09-10T12:00:00+00:00", "extra": 1},
])
def test_invalid_archive_reference_is_rejected(reference):
    with pytest.raises(ValueError):
        ObservationNotePayload.model_validate({"text": "观摩记录", "archive_reference": reference})
