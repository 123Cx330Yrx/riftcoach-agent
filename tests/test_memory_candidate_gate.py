from __future__ import annotations

from app.memory.gate import evaluate_candidate_gate
from app.memory.models import (
    CandidateKind,
    MemoryOperation,
    ProvenanceKind,
    RelationshipRole,
    TargetScope,
)


def test_model_inference_never_gets_write_permission_even_at_confidence_one() -> None:
    decision = evaluate_candidate_gate(
        target_scope=TargetScope.OWNER_PLAYER,
        candidate_kind=CandidateKind.PLAYER_PROFILE,
        memory_key="main_role",
        operation=MemoryOperation.SET,
        provenance_kind=ProvenanceKind.MODEL_INFERENCE,
        relationship_role=RelationshipRole.SELF,
        proposal_confidence=1.0,
    )
    assert decision.allowed is True
    assert decision.requires_confirmation is True
    assert decision.auto_accept_eligible is False
    assert decision.reason_code == "model_requires_confirmation"


def test_observed_relationship_is_limited_to_public_review_observation() -> None:
    allowed = evaluate_candidate_gate(
        target_scope=TargetScope.OWNER_PLAYER,
        candidate_kind=CandidateKind.REVIEW_MEMORY,
        memory_key="public_trend",
        operation=MemoryOperation.APPEND,
        provenance_kind=ProvenanceKind.PUBLISHED_REVIEW_OBSERVATION,
        relationship_role=RelationshipRole.OBSERVED,
        proposal_confidence=None,
    )
    assert allowed.allowed is True
    assert allowed.requires_confirmation is False

    denied = evaluate_candidate_gate(
        target_scope=TargetScope.OWNER_PLAYER,
        candidate_kind=CandidateKind.PLAYER_PROFILE,
        memory_key="training_goal",
        operation=MemoryOperation.SET,
        provenance_kind=ProvenanceKind.MODEL_INFERENCE,
        relationship_role=RelationshipRole.OBSERVED,
        proposal_confidence=0.99,
    )
    assert denied.allowed is False
    assert denied.reason_code == "observed_kind_forbidden"


def test_structured_self_profile_is_only_system_eligible_for_self_relationship() -> None:
    decision = evaluate_candidate_gate(
        target_scope=TargetScope.OWNER_PLAYER,
        candidate_kind=CandidateKind.PLAYER_PROFILE,
        memory_key="main_role",
        operation=MemoryOperation.SET,
        provenance_kind=ProvenanceKind.USER_STRUCTURED_INPUT,
        relationship_role=RelationshipRole.SELF,
        proposal_confidence=None,
    )
    assert decision.auto_accept_eligible is True
    assert decision.requires_confirmation is False

    observed = evaluate_candidate_gate(
        target_scope=TargetScope.OWNER_PLAYER,
        candidate_kind=CandidateKind.PLAYER_PROFILE,
        memory_key="main_role",
        operation=MemoryOperation.SET,
        provenance_kind=ProvenanceKind.USER_STRUCTURED_INPUT,
        relationship_role=RelationshipRole.OBSERVED,
        proposal_confidence=None,
    )
    assert observed.allowed is False


def test_scope_kind_mismatch_is_rejected_before_candidate_creation() -> None:
    decision = evaluate_candidate_gate(
        target_scope=TargetScope.OWNER_GLOBAL,
        candidate_kind=CandidateKind.PLAYER_PROFILE,
        memory_key="main_role",
        operation=MemoryOperation.SET,
        provenance_kind=ProvenanceKind.USER_STRUCTURED_INPUT,
        relationship_role=RelationshipRole.SELF,
        proposal_confidence=None,
    )
    assert decision.allowed is False
    assert decision.reason_code == "scope_kind_mismatch"


def test_training_plan_always_requires_user_confirmation() -> None:
    decision = evaluate_candidate_gate(
        target_scope=TargetScope.OWNER_PLAYER,
        candidate_kind=CandidateKind.TRAINING_PLAN,
        memory_key="current_plan",
        operation=MemoryOperation.SET,
        provenance_kind=ProvenanceKind.DETERMINISTIC_RUN_FACT,
        relationship_role=RelationshipRole.SELF,
        proposal_confidence=None,
    )
    assert decision.allowed is False
    assert decision.reason_code == "training_plan_source_forbidden"
