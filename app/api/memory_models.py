"""Body-safe HTTP models for the Memory Candidate control plane."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Self, TypeAlias
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.memory.models import MemoryCandidateView, canonical_payload_bytes


MemoryCandidateApiErrorCode: TypeAlias = Literal[
    "request_invalid",
    "conversation_not_found",
    "candidate_not_found",
    "candidate_idempotency_conflict",
    "candidate_gate_rejected",
    "candidate_terminal_conflict",
    "candidate_expired",
    "memory_target_unavailable",
    "service_unavailable",
]


class MemoryCandidateApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class CreateMemoryCandidateRequest(MemoryCandidateApiModel):
    target_scope: Literal["owner_global", "owner_player"]
    candidate_kind: Literal[
        "owner_preference",
        "player_profile",
        "review_memory",
        "training_plan",
        "training_progress",
    ]
    memory_key: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$",
    )
    operation: Literal["set", "append"]
    proposal_payload: dict[str, Any]

    @field_validator("proposal_payload")
    @classmethod
    def validate_payload(cls, value: dict[str, Any]) -> dict[str, Any]:
        canonical_payload_bytes(value)
        return value


class MemoryCandidateResponse(MemoryCandidateApiModel):
    schema_version: Literal["1.0"] = "1.0"
    candidate_id: UUID
    conversation_id: UUID
    target_scope: Literal["owner_global", "owner_player"]
    candidate_kind: Literal[
        "owner_preference",
        "player_profile",
        "review_memory",
        "training_plan",
        "training_progress",
    ]
    memory_key: str
    operation: Literal["set", "append"]
    requires_confirmation: bool
    status: Literal["pending", "accepted", "rejected", "expired"]
    gate_policy_version: str
    created_at: datetime
    expires_at: datetime
    decided_at: datetime | None
    decision_reason_code: str | None

    @classmethod
    def from_view(cls, view: MemoryCandidateView) -> Self:
        if not isinstance(view, MemoryCandidateView):
            raise TypeError("view must be a MemoryCandidateView")
        return cls(
            candidate_id=view.candidate_id,
            conversation_id=view.conversation_id,
            target_scope=view.target_scope,
            candidate_kind=view.candidate_kind,
            memory_key=view.memory_key,
            operation=view.operation,
            requires_confirmation=view.requires_confirmation,
            status=view.status,
            gate_policy_version=view.gate_policy_version,
            created_at=view.created_at,
            expires_at=view.expires_at,
            decided_at=view.decided_at,
            decision_reason_code=view.decision_reason_code,
        )


class MemoryCandidateErrorResponse(MemoryCandidateApiModel):
    code: MemoryCandidateApiErrorCode
    reason: str | None = None


__all__ = [
    "CreateMemoryCandidateRequest",
    "MemoryCandidateApiErrorCode",
    "MemoryCandidateErrorResponse",
    "MemoryCandidateResponse",
]
