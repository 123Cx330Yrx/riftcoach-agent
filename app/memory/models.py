from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated, Any, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

from app.players.models import RelationshipRole


MAX_CANDIDATE_PAYLOAD_BYTES = 8 * 1024
_OWNER_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:@|+-]{0,127}$"
_KEY_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"
_DIGEST_PATTERN = r"^[0-9a-f]{64}$"
_VERSION_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$"
_IDEMPOTENCY_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"
_SAFE_ID = re.compile(_OWNER_PATTERN)
_DIGEST = re.compile(_DIGEST_PATTERN)

OwnerId = Annotated[str, StringConstraints(min_length=1, max_length=128, pattern=_OWNER_PATTERN)]
SafeKey = Annotated[str, StringConstraints(min_length=1, max_length=128, pattern=_KEY_PATTERN)]
SafeVersion = Annotated[str, StringConstraints(min_length=1, max_length=64, pattern=_VERSION_PATTERN)]
IdempotencyKey = Annotated[str, StringConstraints(min_length=1, max_length=128, pattern=_IDEMPOTENCY_PATTERN)]


class CandidateDomainModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )


class TargetScope(StrEnum):
    OWNER_GLOBAL = "owner_global"
    OWNER_PLAYER = "owner_player"


class CandidateKind(StrEnum):
    OWNER_PREFERENCE = "owner_preference"
    PLAYER_PROFILE = "player_profile"
    REVIEW_MEMORY = "review_memory"
    TRAINING_PLAN = "training_plan"
    TRAINING_PROGRESS = "training_progress"


class MemoryOperation(StrEnum):
    SET = "set"
    APPEND = "append"


class ProvenanceKind(StrEnum):
    USER_STRUCTURED_INPUT = "user_structured_input"
    USER_MESSAGE_EXTRACTION = "user_message_extraction"
    MODEL_INFERENCE = "model_inference"
    DETERMINISTIC_RUN_FACT = "deterministic_run_fact"
    PUBLISHED_REVIEW_OBSERVATION = "published_review_observation"


class CandidateStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class DecisionActorKind(StrEnum):
    USER = "user"
    SYSTEM = "system"


class MemoryCandidateError(ValueError):
    """Raised when a candidate violates a pure domain contract."""


class CreateMemoryCandidateCommand(CandidateDomainModel):
    owner_id: OwnerId
    conversation_id: UUID
    idempotency_key: IdempotencyKey
    source_message_id: UUID | None = None
    source_task_id: UUID | None = None
    source_run_id: SafeKey | None = None
    source_artifact_sha256: str | None = None
    target_scope: TargetScope
    candidate_kind: CandidateKind
    memory_key: SafeKey
    operation: MemoryOperation
    proposal_payload: dict[str, Any]
    provenance_kind: ProvenanceKind
    producer_id: SafeKey
    producer_version: SafeVersion
    proposal_confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    @field_validator("proposal_payload")
    @classmethod
    def validate_payload(cls, value: dict[str, Any]) -> dict[str, Any]:
        canonical_payload_bytes(value)
        return value

    @field_validator("proposal_confidence")
    @classmethod
    def reject_bool_confidence(cls, value: float | None) -> float | None:
        if isinstance(value, bool):
            raise ValueError("proposal_confidence must be a number")
        return value

    @field_validator("source_artifact_sha256")
    @classmethod
    def validate_artifact_digest(cls, value: str | None) -> str | None:
        if value is not None and not _DIGEST.fullmatch(value):
            raise ValueError("source_artifact_sha256 must be lowercase hexadecimal")
        return value

    @model_validator(mode="after")
    def validate_source(self) -> Self:
        if (self.source_run_id is None) != (self.source_task_id is None):
            raise ValueError("source_task_id and source_run_id must appear together")
        if self.source_artifact_sha256 is not None and (
            self.source_task_id is None and self.source_run_id is None
        ):
            raise ValueError("source artifact requires a task or run source")
        return self


class PendingMemoryCandidate(CandidateDomainModel):
    candidate_id: UUID
    owner_id: OwnerId
    conversation_id: UUID
    idempotency_key: IdempotencyKey
    source_message_id: UUID | None = None
    source_task_id: UUID | None = None
    source_run_id: SafeKey | None = None
    source_artifact_sha256: str | None = None
    target_scope: TargetScope
    candidate_kind: CandidateKind
    memory_key: SafeKey
    operation: MemoryOperation
    proposal_payload: dict[str, Any]
    provenance_kind: ProvenanceKind
    producer_id: SafeKey
    producer_version: SafeVersion
    proposal_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    created_at: datetime
    expires_at: datetime

    @field_validator("proposal_payload")
    @classmethod
    def validate_payload(cls, value: dict[str, Any]) -> dict[str, Any]:
        canonical_payload_bytes(value)
        return value

    @field_validator("proposal_confidence")
    @classmethod
    def reject_bool_confidence(cls, value: float | None) -> float | None:
        if isinstance(value, bool):
            raise ValueError("proposal_confidence must be a number")
        return value

    @field_validator("source_artifact_sha256")
    @classmethod
    def validate_artifact_digest(cls, value: str | None) -> str | None:
        if value is not None and not _DIGEST.fullmatch(value):
            raise ValueError("source_artifact_sha256 must be lowercase hexadecimal")
        return value

    @field_validator("created_at", "expires_at")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        return _as_utc(value)

    @model_validator(mode="after")
    def validate_source_and_lifetime(self) -> Self:
        if (self.source_run_id is None) != (self.source_task_id is None):
            raise ValueError("source_task_id and source_run_id must appear together")
        if self.source_artifact_sha256 is not None and (
            self.source_task_id is None and self.source_run_id is None
        ):
            raise ValueError("source artifact requires a task or run source")
        if self.expires_at <= self.created_at:
            raise ValueError("candidate expires_at must follow created_at")
        return self


class MaterializedMemoryReference(CandidateDomainModel):
    target_kind: SafeKey
    target_id: UUID
    materializer_version: SafeVersion


class MemoryCandidate(PendingMemoryCandidate):
    relationship_id: UUID
    player_subject_id: UUID
    relationship_role: RelationshipRole
    request_fingerprint: str
    proposal_payload_sha256: str
    gate_policy_version: SafeVersion
    requires_confirmation: bool
    status: CandidateStatus
    decision_actor_kind: DecisionActorKind | None = None
    decision_actor_id: OwnerId | None = None
    decision_reason_code: SafeKey | None = None
    decided_at: datetime | None = None
    materialized_target_kind: SafeKey | None = None
    materialized_target_id: UUID | None = None
    materializer_version: SafeVersion | None = None
    updated_at: datetime

    @field_validator("request_fingerprint", "proposal_payload_sha256")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if not _DIGEST.fullmatch(value):
            raise ValueError("candidate digest must be lowercase hexadecimal")
        return value

    @field_validator("created_at", "expires_at", "updated_at", "decided_at")
    @classmethod
    def normalize_all_times(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _as_utc(value)

    @model_validator(mode="after")
    def validate_state_shape(self) -> Self:
        if self.updated_at < self.created_at:
            raise ValueError("candidate updated_at must not precede created_at")
        decision_fields = (
            self.decision_actor_kind,
            self.decision_actor_id,
            self.decision_reason_code,
            self.decided_at,
        )
        reference_fields = (
            self.materialized_target_kind,
            self.materialized_target_id,
            self.materializer_version,
        )
        if self.status is CandidateStatus.PENDING:
            if any(value is not None for value in (*decision_fields, *reference_fields)):
                raise ValueError("pending candidate cannot contain decision or materialization")
        elif self.status is CandidateStatus.ACCEPTED:
            if any(value is None for value in decision_fields):
                raise ValueError("accepted candidate requires decision metadata")
            if any(value is None for value in reference_fields):
                raise ValueError("accepted candidate requires materialization reference")
        else:
            if any(value is None for value in decision_fields):
                raise ValueError("terminal candidate requires decision metadata")
            if any(value is not None for value in reference_fields):
                raise ValueError("rejected or expired candidate cannot contain materialization")
        return self


class MemoryCandidateView(CandidateDomainModel):
    """Body-safe owner projection; proposal and provenance body stay private."""

    candidate_id: UUID
    conversation_id: UUID
    target_scope: TargetScope
    candidate_kind: CandidateKind
    memory_key: SafeKey
    operation: MemoryOperation
    requires_confirmation: bool
    status: CandidateStatus
    gate_policy_version: SafeVersion
    created_at: datetime
    expires_at: datetime
    decided_at: datetime | None
    decision_reason_code: SafeKey | None

    @classmethod
    def from_candidate(cls, candidate: MemoryCandidate) -> Self:
        if not isinstance(candidate, MemoryCandidate):
            raise TypeError("candidate must be a MemoryCandidate")
        return cls(
            candidate_id=candidate.candidate_id,
            conversation_id=candidate.conversation_id,
            target_scope=candidate.target_scope,
            candidate_kind=candidate.candidate_kind,
            memory_key=candidate.memory_key,
            operation=candidate.operation,
            requires_confirmation=candidate.requires_confirmation,
            status=candidate.status,
            gate_policy_version=candidate.gate_policy_version,
            created_at=candidate.created_at,
            expires_at=candidate.expires_at,
            decided_at=candidate.decided_at,
            decision_reason_code=candidate.decision_reason_code,
        )


class MemoryConversationIdentity(CandidateDomainModel):
    owner_id: OwnerId
    conversation_id: UUID
    relationship_id: UUID
    player_subject_id: UUID
    relationship_role: RelationshipRole


class CandidateCreateDisposition(StrEnum):
    CREATED = "created"
    REPLAYED = "replayed"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"
    IDENTITY_UNAVAILABLE = "identity_unavailable"
    SOURCE_INVALID = "source_invalid"


class CandidateCreateResult(CandidateDomainModel):
    disposition: CandidateCreateDisposition
    candidate: MemoryCandidate | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> Self:
        includes_candidate = self.disposition in {
            CandidateCreateDisposition.CREATED,
            CandidateCreateDisposition.REPLAYED,
        }
        if includes_candidate != (self.candidate is not None):
            raise ValueError("candidate create result has invalid projection")
        return self


class CandidateMutationDisposition(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    REPLAYED = "replayed"
    NOT_FOUND = "not_found"
    TERMINAL_CONFLICT = "terminal_conflict"
    TARGET_UNAVAILABLE = "target_unavailable"


class CandidateMutationResult(CandidateDomainModel):
    disposition: CandidateMutationDisposition
    candidate: MemoryCandidate | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> Self:
        needs_candidate = self.disposition not in {
            CandidateMutationDisposition.NOT_FOUND,
            CandidateMutationDisposition.TERMINAL_CONFLICT,
            CandidateMutationDisposition.TARGET_UNAVAILABLE,
        }
        if needs_candidate != (self.candidate is not None):
            raise ValueError("candidate mutation result has invalid projection")
        return self


def canonical_payload_bytes(payload: object) -> bytes:
    if not isinstance(payload, dict):
        raise ValueError("proposal payload must be a JSON object")
    _validate_json_value(payload, depth=0)
    try:
        encoded = json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError):
        raise ValueError("proposal payload must contain finite JSON values") from None
    if len(encoded) > MAX_CANDIDATE_PAYLOAD_BYTES:
        raise ValueError("proposal payload exceeds the 8 KiB bound")
    return encoded


def compute_payload_sha256(payload: object) -> str:
    return hashlib.sha256(canonical_payload_bytes(payload)).hexdigest()


def compute_candidate_fingerprint(candidate: PendingMemoryCandidate) -> str:
    if not isinstance(candidate, PendingMemoryCandidate):
        raise TypeError("candidate must be a PendingMemoryCandidate")
    payload = {
        "conversation_id": str(candidate.conversation_id),
        "idempotency_key": candidate.idempotency_key,
        "source_artifact_sha256": candidate.source_artifact_sha256,
        "source_message_id": _uuid_text(candidate.source_message_id),
        "source_run_id": candidate.source_run_id,
        "source_task_id": _uuid_text(candidate.source_task_id),
        "target_scope": candidate.target_scope.value,
        "candidate_kind": candidate.candidate_kind.value,
        "memory_key": candidate.memory_key,
        "operation": candidate.operation.value,
        "proposal_payload": json.loads(canonical_payload_bytes(candidate.proposal_payload)),
        "provenance_kind": candidate.provenance_kind.value,
        "producer_id": candidate.producer_id,
        "producer_version": candidate.producer_version,
        "proposal_confidence": candidate.proposal_confidence,
    }
    return hashlib.sha256(canonical_payload_bytes(payload)).hexdigest()


def _validate_json_value(value: object, *, depth: int) -> None:
    if depth > 8:
        raise ValueError("proposal payload nesting exceeds the bound")
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("proposal payload object keys must be strings")
        for key, item in value.items():
            if len(key) > 256:
                raise ValueError("proposal payload key is too long")
            _validate_json_value(item, depth=depth + 1)
        return
    if isinstance(value, list):
        for item in value:
            _validate_json_value(item, depth=depth + 1)
        return
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("proposal payload must contain finite JSON values")
        return
    raise ValueError("proposal payload contains a non-JSON value")


def _uuid_text(value: UUID | None) -> str | None:
    return None if value is None else str(value)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("candidate timestamps must be timezone-aware")
    return value.astimezone(timezone.utc)


__all__ = [
    "CandidateKind",
    "CandidateCreateDisposition",
    "CandidateCreateResult",
    "CandidateMutationDisposition",
    "CandidateMutationResult",
    "CandidateStatus",
    "DecisionActorKind",
    "CreateMemoryCandidateCommand",
    "MAX_CANDIDATE_PAYLOAD_BYTES",
    "MaterializedMemoryReference",
    "MemoryConversationIdentity",
    "MemoryCandidate",
    "MemoryCandidateError",
    "MemoryCandidateView",
    "MemoryOperation",
    "PendingMemoryCandidate",
    "ProvenanceKind",
    "RelationshipRole",
    "TargetScope",
    "canonical_payload_bytes",
    "compute_candidate_fingerprint",
    "compute_payload_sha256",
]
