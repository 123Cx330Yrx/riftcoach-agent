from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)


_OWNER_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:@|+-]{0,127}$"
_IDEMPOTENCY_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"
_WORKER_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"
_PUUID_PATTERN = r"^[A-Za-z0-9_-]{1,128}$"
_FINGERPRINT_PATTERN = r"^[0-9a-f]{64}$"
_SAFE_COMPONENT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")

_MAX_GAME_NAME_LENGTH = 64
_MAX_TAG_LINE_LENGTH = 32
_MAX_RIOT_ID_LENGTH = _MAX_GAME_NAME_LENGTH + 1 + _MAX_TAG_LINE_LENGTH
_RETRYABLE_FAILURE_CODES = frozenset(
    {"riot_rate_limited", "upstream_timeout", "upstream_unavailable"}
)
_NON_RETRYABLE_FAILURE_CODES = frozenset(
    {
        "player_not_found",
        "riot_authentication_failed",
        "account_response_invalid",
        "relationship_role_conflict",
    }
)
_FAILURE_CODES = _RETRYABLE_FAILURE_CODES | _NON_RETRYABLE_FAILURE_CODES
_ROLE_VERIFICATION_PAIRS = frozenset(
    {
        ("self", "unverified_claim"),
        ("self", "rso_verified"),
        ("observed", "not_applicable"),
    }
)

OwnerId = Annotated[
    str,
    StringConstraints(min_length=1, max_length=128, pattern=_OWNER_PATTERN),
]
IdempotencyKey = Annotated[
    str,
    StringConstraints(min_length=1, max_length=128, pattern=_IDEMPOTENCY_PATTERN),
]
WorkerId = Annotated[
    str,
    StringConstraints(min_length=1, max_length=128, pattern=_WORKER_PATTERN),
]
Fingerprint = Annotated[
    str,
    StringConstraints(min_length=64, max_length=64, pattern=_FINGERPRINT_PATTERN),
]
TaskKind = Literal["player_link"]
TaskSchemaVersion = Literal["1.0"]
Puuid = Annotated[
    str,
    StringConstraints(min_length=1, max_length=128, pattern=_PUUID_PATTERN),
]


class PlayerDomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class RoutingRegion(StrEnum):
    AMERICAS = "americas"
    ASIA = "asia"
    EUROPE = "europe"
    SEA = "sea"


class RelationshipRole(StrEnum):
    SELF = "self"
    OBSERVED = "observed"


class VerificationStatus(StrEnum):
    UNVERIFIED_CLAIM = "unverified_claim"
    NOT_APPLICABLE = "not_applicable"
    RSO_VERIFIED = "rso_verified"


class PlayerLinkStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class PlayerLinkFailure(PlayerDomainModel):
    code: str = Field(min_length=1, max_length=64)
    retryable: bool

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        if value not in _FAILURE_CODES:
            raise ValueError("failure code is not allowlisted")
        return value

    @model_validator(mode="after")
    def validate_retryable_projection(self) -> Self:
        expected_retryable = self.code in _RETRYABLE_FAILURE_CODES
        if self.retryable is not expected_retryable:
            raise ValueError("retryable must match the allowlisted failure code")
        return self


class OwnerPlayerRelationshipRef(PlayerDomainModel):
    relationship_id: UUID
    player_subject_id: UUID
    relationship_role: RelationshipRole
    verification_status: VerificationStatus

    @model_validator(mode="after")
    def validate_role_verification_pair(self) -> Self:
        _validate_role_verification_pair(
            self.relationship_role,
            self.verification_status,
        )
        return self


class CreatePlayerLinkCommand(PlayerDomainModel):
    owner_id: OwnerId
    idempotency_key: IdempotencyKey
    riot_id: str = Field(min_length=3, max_length=_MAX_RIOT_ID_LENGTH)
    routing_region: RoutingRegion
    relationship_role: RelationshipRole

    @field_validator("riot_id")
    @classmethod
    def normalize_riot_id(cls, value: str) -> str:
        normalized = unicodedata.normalize("NFC", value.strip())
        if any(
            unicodedata.category(character).startswith("C")
            for character in normalized
        ):
            raise ValueError("riot_id must not contain control characters")
        game_name, separator, tag_line = normalized.rpartition("#")
        game_name = game_name.strip()
        tag_line = tag_line.strip()
        if not separator or not game_name or not tag_line:
            raise ValueError("riot_id must contain non-blank game name and tag line")
        if len(game_name) > _MAX_GAME_NAME_LENGTH:
            raise ValueError("riot_id game name exceeds the local bound")
        if len(tag_line) > _MAX_TAG_LINE_LENGTH:
            raise ValueError("riot_id tag line exceeds the local bound")
        return f"{game_name}#{tag_line}"

    @property
    def game_name(self) -> str:
        return self.riot_id.rpartition("#")[0]

    @property
    def tag_line(self) -> str:
        return self.riot_id.rpartition("#")[2]

    @property
    def derived_verification_status(self) -> VerificationStatus:
        if self.relationship_role is RelationshipRole.SELF:
            return VerificationStatus.UNVERIFIED_CLAIM
        return VerificationStatus.NOT_APPLICABLE


class PendingPlayerLinkTask(PlayerDomainModel):
    link_task_id: UUID
    task_kind: TaskKind = "player_link"
    schema_version: TaskSchemaVersion = "1.0"
    owner_id: OwnerId
    idempotency_key: IdempotencyKey
    request_fingerprint: Fingerprint
    routing_region: RoutingRegion
    relationship_role: RelationshipRole
    verification_status: VerificationStatus
    game_name: str = Field(min_length=1, max_length=_MAX_GAME_NAME_LENGTH)
    tag_line: str = Field(min_length=1, max_length=_MAX_TAG_LINE_LENGTH)
    alias_hash: Fingerprint
    created_at: datetime

    @field_validator("game_name", "tag_line")
    @classmethod
    def validate_private_riot_component(cls, value: str) -> str:
        normalized = unicodedata.normalize("NFC", value.strip())
        if not normalized:
            raise ValueError("riot_id component must not be blank")
        if any(
            unicodedata.category(character).startswith("C")
            for character in normalized
        ):
            raise ValueError("riot_id component must not contain control characters")
        return normalized

    @field_validator("created_at")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        return _as_utc(value)

    @model_validator(mode="after")
    def validate_relationship_projection(self) -> Self:
        _validate_role_verification_pair(
            self.relationship_role,
            self.verification_status,
        )
        return self


class PlayerLinkTask(PlayerDomainModel):
    link_task_id: UUID
    task_kind: TaskKind
    schema_version: TaskSchemaVersion
    owner_id: OwnerId
    idempotency_key: IdempotencyKey
    request_fingerprint: Fingerprint
    routing_region: RoutingRegion
    relationship_role: RelationshipRole
    verification_status: VerificationStatus
    game_name: str = Field(min_length=1, max_length=_MAX_GAME_NAME_LENGTH)
    tag_line: str = Field(min_length=1, max_length=_MAX_TAG_LINE_LENGTH)
    alias_hash: Fingerprint
    status: PlayerLinkStatus
    created_at: datetime
    updated_at: datetime
    claimed_at: datetime | None
    finished_at: datetime | None
    worker_id: WorkerId | None
    subject_id: UUID | None
    relationship: OwnerPlayerRelationshipRef | None
    confirmed_game_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=_MAX_GAME_NAME_LENGTH,
    )
    confirmed_tag_line: str | None = Field(
        default=None,
        min_length=1,
        max_length=_MAX_TAG_LINE_LENGTH,
    )
    failure: PlayerLinkFailure | None

    @field_validator("worker_id")
    @classmethod
    def validate_worker_id(cls, value: str | None) -> str | None:
        if value is not None and not _SAFE_COMPONENT_PATTERN.fullmatch(value):
            raise ValueError("worker_id must be a bounded safe identifier")
        return value

    @field_validator(
        "created_at",
        "updated_at",
        "claimed_at",
        "finished_at",
    )
    @classmethod
    def normalize_datetimes(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _as_utc(value)

    @field_validator(
        "game_name",
        "tag_line",
        "confirmed_game_name",
        "confirmed_tag_line",
    )
    @classmethod
    def validate_riot_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = unicodedata.normalize("NFC", value.strip())
        if not normalized:
            raise ValueError("riot text must not be blank")
        if any(
            unicodedata.category(character).startswith("C")
            for character in normalized
        ):
            raise ValueError("riot text must not contain control characters")
        return normalized

    @model_validator(mode="after")
    def validate_lifecycle(self) -> Self:
        _validate_role_verification_pair(
            self.relationship_role,
            self.verification_status,
        )
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not precede created_at")
        if self.claimed_at is not None and self.claimed_at < self.created_at:
            raise ValueError("claimed_at must not precede created_at")
        if self.finished_at is not None:
            if self.claimed_at is None or self.finished_at < self.claimed_at:
                raise ValueError("finished_at must not precede claimed_at")

        if self.status is PlayerLinkStatus.QUEUED:
            self._require_empty_execution_state("queued")
        elif self.status is PlayerLinkStatus.RUNNING:
            if self.worker_id is None or self.claimed_at is None:
                raise ValueError("running link task requires worker_id and claimed_at")
            if any(
                value is not None
                for value in (
                    self.finished_at,
                    self.subject_id,
                    self.relationship,
                    self.confirmed_game_name,
                    self.confirmed_tag_line,
                    self.failure,
                )
            ):
                raise ValueError("running link task cannot contain terminal data")
        elif self.status is PlayerLinkStatus.SUCCEEDED:
            if (
                self.worker_id is None
                or self.claimed_at is None
                or self.finished_at is None
                or self.subject_id is None
                or self.relationship is None
                or self.confirmed_game_name is None
                or self.confirmed_tag_line is None
            ):
                raise ValueError("succeeded link task requires resolved identity")
            if self.failure is not None:
                raise ValueError("succeeded link task cannot include failure data")
            if self.relationship.player_subject_id != self.subject_id:
                raise ValueError(
                    "relationship player_subject_id must match succeeded subject_id"
                )
            if self.relationship.relationship_role is not self.relationship_role:
                raise ValueError(
                    "relationship role must match the link task role projection"
                )
            if (
                self.relationship.verification_status
                is not self.verification_status
            ):
                raise ValueError(
                    "relationship verification must match the link task projection"
                )
        else:
            if (
                self.worker_id is None
                or self.claimed_at is None
                or self.finished_at is None
                or self.failure is None
            ):
                raise ValueError("failed link task requires failure terminal identity")
            if any(
                value is not None
                for value in (
                    self.subject_id,
                    self.relationship,
                    self.confirmed_game_name,
                    self.confirmed_tag_line,
                )
            ):
                raise ValueError("failed link task cannot expose resolved identity")
        return self

    def _require_empty_execution_state(self, state: str) -> None:
        if any(
            value is not None
            for value in (
                self.worker_id,
                self.claimed_at,
                self.finished_at,
                self.subject_id,
                self.relationship,
                self.confirmed_game_name,
                self.confirmed_tag_line,
                self.failure,
            )
        ):
            raise ValueError(f"{state} link task cannot contain execution state")


class PlayerLinkTaskView(PlayerDomainModel):
    schema_version: TaskSchemaVersion
    link_task_id: UUID
    status: PlayerLinkStatus
    created_at: datetime
    updated_at: datetime
    claimed_at: datetime | None
    finished_at: datetime | None
    relationship_role: RelationshipRole
    verification_status: VerificationStatus
    player_subject_id: UUID | None
    relationship: OwnerPlayerRelationshipRef | None
    confirmed_riot_id: str | None
    failure: PlayerLinkFailure | None

    @classmethod
    def from_task(cls, task: PlayerLinkTask) -> PlayerLinkTaskView:
        if not isinstance(task, PlayerLinkTask):
            raise TypeError("task must be a PlayerLinkTask")
        confirmed_riot_id = None
        if task.confirmed_game_name is not None and task.confirmed_tag_line is not None:
            confirmed_riot_id = f"{task.confirmed_game_name}#{task.confirmed_tag_line}"
        return cls(
            schema_version=task.schema_version,
            link_task_id=task.link_task_id,
            status=task.status,
            created_at=task.created_at,
            updated_at=task.updated_at,
            claimed_at=task.claimed_at,
            finished_at=task.finished_at,
            relationship_role=task.relationship_role,
            verification_status=task.verification_status,
            player_subject_id=task.subject_id,
            relationship=task.relationship,
            confirmed_riot_id=confirmed_riot_id,
            failure=task.failure,
        )


class PlayerProfileView(PlayerDomainModel):
    """PUUID-free selectable projection of one resolved owner relationship."""

    schema_version: Literal["1.0"] = "1.0"
    player_profile_id: UUID
    riot_id: str = Field(min_length=3, max_length=_MAX_RIOT_ID_LENGTH)
    routing_region: RoutingRegion
    relationship_role: RelationshipRole
    verification_status: VerificationStatus
    last_resolved_at: datetime

    @field_validator("riot_id")
    @classmethod
    def validate_riot_id(cls, value: str) -> str:
        return CreatePlayerLinkCommand.normalize_riot_id(value)

    @field_validator("last_resolved_at")
    @classmethod
    def normalize_last_resolved_at(cls, value: datetime) -> datetime:
        return _as_utc(value)

    @model_validator(mode="after")
    def validate_relationship_projection(self) -> Self:
        _validate_role_verification_pair(
            self.relationship_role,
            self.verification_status,
        )
        return self


class PlayerProfilePage(PlayerDomainModel):
    items: tuple[PlayerProfileView, ...]
    limit: int = Field(ge=1, le=100)

    @model_validator(mode="after")
    def validate_bound(self) -> Self:
        if len(self.items) > self.limit:
            raise ValueError("profile page exceeds its requested limit")
        return self


class PlayerLinkCreateDisposition(StrEnum):
    CREATED = "created"
    REPLAYED = "replayed"


class PlayerLinkRepositoryCreateDisposition(StrEnum):
    CREATED = "created"
    REPLAYED = "replayed"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"
    OWNER_CAPACITY_EXCEEDED = "owner_capacity_exceeded"
    GLOBAL_CAPACITY_EXCEEDED = "global_capacity_exceeded"


class PlayerLinkCreateResult(PlayerDomainModel):
    disposition: PlayerLinkCreateDisposition
    task: PlayerLinkTaskView


class PlayerLinkRepositoryCreateResult(PlayerDomainModel):
    disposition: PlayerLinkRepositoryCreateDisposition
    task: PlayerLinkTask | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> Self:
        includes_task = self.disposition in {
            PlayerLinkRepositoryCreateDisposition.CREATED,
            PlayerLinkRepositoryCreateDisposition.REPLAYED,
        }
        if includes_task != (self.task is not None):
            raise ValueError("repository create result has an invalid task projection")
        return self


class PlayerLinkCapacityPolicy(PlayerDomainModel):
    owner_active_limit: int = Field(default=3, ge=1, le=10_000)
    global_active_limit: int = Field(default=50, ge=1, le=100_000)

    @model_validator(mode="after")
    def validate_capacity_order(self) -> Self:
        if self.global_active_limit < self.owner_active_limit:
            raise ValueError(
                "global_active_limit must be greater than or equal to owner_active_limit"
            )
        return self


class ResolvedRiotAccount(PlayerDomainModel):
    routing_region: RoutingRegion
    puuid: Puuid
    game_name: str = Field(min_length=1, max_length=_MAX_GAME_NAME_LENGTH)
    tag_line: str = Field(min_length=1, max_length=_MAX_TAG_LINE_LENGTH)

    @field_validator("game_name", "tag_line")
    @classmethod
    def validate_display_identity(cls, value: str) -> str:
        normalized = unicodedata.normalize("NFC", value.strip())
        if not normalized:
            raise ValueError("resolved Riot display identity must not be blank")
        if any(
            unicodedata.category(character).startswith("C")
            for character in normalized
        ):
            raise ValueError(
                "resolved Riot display identity must not contain control characters"
            )
        return normalized


def compute_alias_hash(*, game_name: str, tag_line: str) -> str:
    normalized_game_name = normalize_riot_component(
        game_name,
        component_name="game_name",
        max_length=_MAX_GAME_NAME_LENGTH,
    )
    normalized_tag_line = normalize_riot_component(
        tag_line,
        component_name="tag_line",
        max_length=_MAX_TAG_LINE_LENGTH,
    )
    return hashlib.sha256(
        f"{normalized_game_name}#{normalized_tag_line}".encode("utf-8")
    ).hexdigest()


def normalize_riot_component(
    value: str,
    *,
    component_name: str,
    max_length: int,
) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{component_name} must be a string")
    normalized = unicodedata.normalize("NFC", value.strip())
    if not normalized:
        raise ValueError(f"{component_name} must not be blank")
    if any(
        unicodedata.category(character).startswith("C")
        for character in normalized
    ):
        raise ValueError(f"{component_name} must not contain control characters")
    if len(normalized) > max_length:
        raise ValueError(f"{component_name} exceeds the local bound")
    return normalized


def _validate_role_verification_pair(
    relationship_role: RelationshipRole,
    verification_status: VerificationStatus,
) -> None:
    if (relationship_role.value, verification_status.value) not in (
        _ROLE_VERIFICATION_PAIRS
    ):
        raise ValueError("relationship_role and verification_status conflict")


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("player link timestamps must be timezone-aware")
    return value.astimezone(timezone.utc)


__all__ = [
    "CreatePlayerLinkCommand",
    "Fingerprint",
    "IdempotencyKey",
    "OwnerId",
    "OwnerPlayerRelationshipRef",
    "PendingPlayerLinkTask",
    "PlayerLinkCapacityPolicy",
    "PlayerLinkCreateDisposition",
    "PlayerLinkCreateResult",
    "PlayerLinkFailure",
    "PlayerLinkRepositoryCreateDisposition",
    "PlayerLinkRepositoryCreateResult",
    "PlayerLinkStatus",
    "PlayerLinkTask",
    "PlayerLinkTaskView",
    "PlayerProfilePage",
    "PlayerProfileView",
    "RelationshipRole",
    "ResolvedRiotAccount",
    "RoutingRegion",
    "TaskKind",
    "TaskSchemaVersion",
    "VerificationStatus",
    "WorkerId",
    "compute_alias_hash",
    "normalize_riot_component",
]
