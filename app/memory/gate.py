from __future__ import annotations

from dataclasses import dataclass

from app.memory.models import (
    CandidateKind,
    MemoryOperation,
    ProvenanceKind,
    RelationshipRole,
    TargetScope,
)


@dataclass(frozen=True, slots=True)
class GateDecision:
    allowed: bool
    requires_confirmation: bool
    auto_accept_eligible: bool
    reason_code: str
    policy_version: str = "memory-gate-v1"


def evaluate_candidate_gate(
    *,
    target_scope: TargetScope,
    candidate_kind: CandidateKind,
    memory_key: str,
    operation: MemoryOperation,
    provenance_kind: ProvenanceKind,
    relationship_role: RelationshipRole,
    proposal_confidence: float | None,
) -> GateDecision:
    del proposal_confidence  # Confidence is presentation metadata, never authority.

    if candidate_kind is CandidateKind.OWNER_PREFERENCE:
        if target_scope is not TargetScope.OWNER_GLOBAL:
            return _denied("scope_kind_mismatch")
    elif target_scope is not TargetScope.OWNER_PLAYER:
        return _denied("scope_kind_mismatch")

    if relationship_role is RelationshipRole.OBSERVED:
        if not (
            candidate_kind is CandidateKind.REVIEW_MEMORY
            and operation is MemoryOperation.APPEND
            and memory_key in {"observation_note", "public_trend"}
        ):
            return _denied("observed_kind_forbidden")

    if provenance_kind is ProvenanceKind.MODEL_INFERENCE:
        return _allowed("model_requires_confirmation", requires_confirmation=True)
    if provenance_kind is ProvenanceKind.USER_MESSAGE_EXTRACTION:
        return _allowed("extraction_requires_confirmation", requires_confirmation=True)
    if candidate_kind is CandidateKind.TRAINING_PLAN and provenance_kind is not ProvenanceKind.USER_STRUCTURED_INPUT:
        return _denied("training_plan_source_forbidden")
    if provenance_kind is ProvenanceKind.USER_STRUCTURED_INPUT:
        if candidate_kind is CandidateKind.PLAYER_PROFILE and relationship_role is not RelationshipRole.SELF:
            return _denied("self_profile_requires_self_relationship")
        if candidate_kind in {CandidateKind.OWNER_PREFERENCE, CandidateKind.PLAYER_PROFILE}:
            return _allowed("structured_input_allowlisted", auto_accept_eligible=True)
        if candidate_kind is CandidateKind.TRAINING_PLAN:
            return _allowed("training_plan_requires_confirmation", requires_confirmation=True)
        return _denied("structured_source_kind_forbidden")
    if provenance_kind is ProvenanceKind.DETERMINISTIC_RUN_FACT:
        if candidate_kind not in {CandidateKind.REVIEW_MEMORY, CandidateKind.TRAINING_PROGRESS}:
            return _denied("deterministic_source_kind_forbidden")
        return _allowed("deterministic_fact_allowlisted")
    if provenance_kind is ProvenanceKind.PUBLISHED_REVIEW_OBSERVATION:
        if candidate_kind is not CandidateKind.REVIEW_MEMORY:
            return _denied("published_observation_kind_forbidden")
        return _allowed("published_observation_allowlisted")
    return _denied("provenance_kind_forbidden")


def _allowed(
    reason_code: str,
    *,
    requires_confirmation: bool = False,
    auto_accept_eligible: bool = False,
) -> GateDecision:
    return GateDecision(
        allowed=True,
        requires_confirmation=requires_confirmation,
        auto_accept_eligible=auto_accept_eligible,
        reason_code=reason_code,
    )


def _denied(reason_code: str) -> GateDecision:
    return GateDecision(
        allowed=False,
        requires_confirmation=False,
        auto_accept_eligible=False,
        reason_code=reason_code,
    )


__all__ = ["GateDecision", "evaluate_candidate_gate"]
