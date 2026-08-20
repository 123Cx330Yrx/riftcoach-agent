from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

from app.harness.run_ids import normalize_run_id
from app.players.models import RelationshipRole


_OWNER_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:@|+-]{0,127}$"
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_SAFE_CODE_PATTERN = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
_SAFE_ORDER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$")
_MAX_RECORD_CONTENT_CHARACTERS = 16_384

OwnerId = Annotated[
    str,
    StringConstraints(min_length=1, max_length=128, pattern=_OWNER_PATTERN),
]


class MemoryContextModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )


class MemoryContextRecordKind(StrEnum):
    MESSAGE = "message"
    OWNER_PREFERENCE = "owner_preference"
    PLAYER_PROFILE = "player_profile"
    REVIEW_MEMORY = "review_memory"
    TRAINING_PLAN = "training_plan"
    TRAINING_PROGRESS = "training_progress"

    @property
    def self_only(self) -> bool:
        return self in {
            MemoryContextRecordKind.PLAYER_PROFILE,
            MemoryContextRecordKind.TRAINING_PLAN,
            MemoryContextRecordKind.TRAINING_PROGRESS,
        }


class MemoryContextBinding(MemoryContextModel):
    run_id: str
    owner_id: OwnerId
    conversation_id: UUID
    relationship_id: UUID
    player_subject_id: UUID
    relationship_role: RelationshipRole

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        return normalize_run_id(value)


class MemoryContextRecord(MemoryContextModel):
    kind: MemoryContextRecordKind
    record_id: UUID
    version: int = Field(ge=1, le=2_147_483_647)
    content_sha256: str
    content: str
    priority: int = Field(ge=0, le=10_000)
    stable_order: str
    relationship_role: RelationshipRole | None

    @field_validator("content_sha256")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if not _DIGEST_PATTERN.fullmatch(value):
            raise ValueError("content_sha256 must be lowercase hexadecimal")
        return value

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("content must not be blank")
        if len(value) > _MAX_RECORD_CONTENT_CHARACTERS:
            raise ValueError("content exceeds the context record bound")
        value.encode("utf-8", errors="strict")
        return value

    @field_validator("stable_order")
    @classmethod
    def validate_stable_order(cls, value: str) -> str:
        if not _SAFE_ORDER_PATTERN.fullmatch(value):
            raise ValueError("stable_order must be a bounded safe key")
        return value

    @model_validator(mode="after")
    def validate_role_shape(self) -> Self:
        if self.kind is MemoryContextRecordKind.OWNER_PREFERENCE:
            if self.relationship_role is not None:
                raise ValueError("owner preference must not carry a relationship role")
        elif self.relationship_role is None:
            raise ValueError("owner-player context record requires relationship_role")
        if self.kind.self_only and self.relationship_role is not RelationshipRole.SELF:
            raise ValueError("self-only context record requires a self relationship")
        return self


class MemoryContextSnapshot(MemoryContextModel):
    binding: MemoryContextBinding
    records: tuple[MemoryContextRecord, ...]

    @model_validator(mode="after")
    def validate_scope_and_order(self) -> Self:
        identities = tuple((row.kind, row.record_id) for row in self.records)
        if len(set(identities)) != len(identities):
            raise ValueError("snapshot contains duplicate context records")
        order = tuple((-row.priority, row.stable_order) for row in self.records)
        if order != tuple(sorted(order)):
            raise ValueError("snapshot records must use stable priority order")
        if self.binding.relationship_role is RelationshipRole.OBSERVED:
            for row in self.records:
                if row.kind.self_only:
                    raise ValueError("observed snapshot cannot contain self-only records")
                if (
                    row.kind is not MemoryContextRecordKind.OWNER_PREFERENCE
                    and row.relationship_role is not RelationshipRole.OBSERVED
                ):
                    raise ValueError("observed snapshot contains a mismatched role")
        else:
            for row in self.records:
                if (
                    row.kind is not MemoryContextRecordKind.OWNER_PREFERENCE
                    and row.relationship_role is not RelationshipRole.SELF
                ):
                    raise ValueError("self snapshot contains a mismatched role")
        return self


class MemoryContextManifestDisposition(StrEnum):
    SELECTED = "selected"
    OMITTED = "omitted"


class MemoryContextManifestRef(MemoryContextModel):
    kind: MemoryContextRecordKind
    record_id: UUID
    version: int = Field(ge=1, le=2_147_483_647)
    content_sha256: str
    disposition: MemoryContextManifestDisposition
    omission_reason: Literal["context_budget"] | None

    @field_validator("content_sha256")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if not _DIGEST_PATTERN.fullmatch(value):
            raise ValueError("content_sha256 must be lowercase hexadecimal")
        return value

    @model_validator(mode="after")
    def validate_disposition(self) -> Self:
        if (
            self.disposition is MemoryContextManifestDisposition.SELECTED
        ) != (self.omission_reason is None):
            raise ValueError("manifest disposition and omission_reason disagree")
        return self


class MemoryContextManifest(MemoryContextModel):
    schema_version: Literal["1.0"] = "1.0"
    binding: MemoryContextBinding
    selector_policy_version: str
    effective_context_ceiling: int = Field(gt=0, le=200_000)
    estimated_context_units: int = Field(ge=0, le=200_000)
    candidate_count: int = Field(ge=0, le=69)
    selected_count: int = Field(ge=0, le=69)
    omitted_count: int = Field(ge=0, le=69)
    records: tuple[MemoryContextManifestRef, ...]
    created_at: datetime

    @field_validator("selector_policy_version")
    @classmethod
    def validate_policy_version(cls, value: str) -> str:
        if not _SAFE_CODE_PATTERN.fullmatch(value):
            raise ValueError("selector_policy_version must be a safe code")
        return value

    @field_validator("created_at")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_counts_and_refs(self) -> Self:
        if self.estimated_context_units > self.effective_context_ceiling:
            raise ValueError("estimated context exceeds effective ceiling")
        if self.candidate_count != len(self.records):
            raise ValueError("manifest counts do not match records")
        if self.selected_count + self.omitted_count != self.candidate_count:
            raise ValueError("manifest counts do not partition candidates")
        selected = sum(
            row.disposition is MemoryContextManifestDisposition.SELECTED
            for row in self.records
        )
        if selected != self.selected_count:
            raise ValueError("manifest counts do not match dispositions")
        identities = tuple((row.kind, row.record_id) for row in self.records)
        if len(set(identities)) != len(identities):
            raise ValueError("manifest contains duplicate record refs")
        return self


def canonical_memory_context_manifest_bytes(
    manifest: MemoryContextManifest,
) -> bytes:
    if not isinstance(manifest, MemoryContextManifest):
        raise TypeError("manifest must be a MemoryContextManifest")
    return json.dumps(
        manifest.model_dump(mode="json"),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def compute_memory_context_manifest_sha256(
    manifest: MemoryContextManifest,
) -> str:
    return hashlib.sha256(
        canonical_memory_context_manifest_bytes(manifest)
    ).hexdigest()


__all__ = [
    "MemoryContextBinding",
    "MemoryContextManifest",
    "MemoryContextManifestDisposition",
    "MemoryContextManifestRef",
    "MemoryContextRecord",
    "MemoryContextRecordKind",
    "MemoryContextSnapshot",
    "canonical_memory_context_manifest_bytes",
    "compute_memory_context_manifest_sha256",
]
