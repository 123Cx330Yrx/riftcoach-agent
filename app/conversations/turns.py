from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import StrEnum
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.conversations.models import compute_message_content_sha256, validate_message_content
from app.memory.context_models import MemoryContextBinding
from app.memory.models import (
    CandidateKind,
    MemoryOperation,
    ProvenanceKind,
    SafeKey,
    SafeVersion,
    TargetScope,
    canonical_payload_bytes,
)
from app.runtime.models import RuntimeArtifactReference
from app.runtime.signals import RuntimePublicationStatus


_DIGEST = re.compile(r"^[0-9a-f]{64}$")


class TerminalTurnModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )


class TerminalCandidateProposal(TerminalTurnModel):
    target_scope: TargetScope
    candidate_kind: CandidateKind
    memory_key: SafeKey
    operation: MemoryOperation
    proposal_payload: dict[str, object]
    provenance_kind: ProvenanceKind
    producer_id: SafeKey
    producer_version: SafeVersion
    proposal_confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    @field_validator("proposal_payload")
    @classmethod
    def validate_payload(cls, value: dict[str, object]) -> dict[str, object]:
        canonical_payload_bytes(value)
        return value

    @field_validator("proposal_confidence")
    @classmethod
    def reject_boolean_confidence(cls, value: float | None) -> float | None:
        if isinstance(value, bool):
            raise ValueError("proposal_confidence must be numeric")
        return value

    @model_validator(mode="after")
    def validate_terminal_provenance(self) -> Self:
        if self.provenance_kind not in {
            ProvenanceKind.MODEL_INFERENCE,
            ProvenanceKind.PUBLISHED_REVIEW_OBSERVATION,
        }:
            raise ValueError(
                "terminal proposal provenance must be model or published review"
            )
        return self


class TerminalAssistantTurn(TerminalTurnModel):
    source_task_id: UUID
    binding: MemoryContextBinding
    publication_status: RuntimePublicationStatus
    artifact_reference: RuntimeArtifactReference
    assistant_content: str
    assistant_content_sha256: str | None = None
    candidate_proposals: tuple[TerminalCandidateProposal, ...] = Field(
        default=(),
        max_length=8,
    )
    created_at: datetime

    @field_validator("assistant_content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        return validate_message_content(value)

    @field_validator("assistant_content_sha256")
    @classmethod
    def validate_digest(cls, value: str | None) -> str | None:
        if value is not None and not _DIGEST.fullmatch(value):
            raise ValueError("assistant_content_sha256 must be lowercase hexadecimal")
        return value

    @field_validator("created_at")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_terminal(self) -> Self:
        if self.publication_status not in {
            RuntimePublicationStatus.PUBLISHED,
            RuntimePublicationStatus.DEGRADED,
        }:
            raise ValueError("terminal Assistant requires a published report")
        if self.artifact_reference.kind != "final_report":
            raise ValueError("terminal Assistant requires final_report Artifact")
        digest = compute_message_content_sha256(self.assistant_content)
        if self.assistant_content_sha256 is not None and (
            self.assistant_content_sha256 != digest
        ):
            raise ValueError("assistant content digest mismatch")
        object.__setattr__(self, "assistant_content_sha256", digest)
        return self


class TerminalTurnWriteDisposition(StrEnum):
    CREATED = "created"
    REPLAYED = "replayed"


class TerminalTurnWriteResult(TerminalTurnModel):
    disposition: TerminalTurnWriteDisposition
    message_id: UUID
    sequence_no: int = Field(ge=1)
    candidate_ids: tuple[UUID, ...] = Field(default=(), max_length=8)


__all__ = [
    "TerminalAssistantTurn",
    "TerminalCandidateProposal",
    "TerminalTurnWriteDisposition",
    "TerminalTurnWriteResult",
]
