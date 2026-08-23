"""Public, PUUID-free HTTP models for asynchronous player linking."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.players.models import (
    PlayerLinkCreateDisposition,
    PlayerLinkFailure,
    PlayerLinkStatus,
    PlayerLinkTaskView,
    PlayerProfilePage,
    PlayerProfileView,
    RelationshipRole,
    VerificationStatus,
)


class PlayerApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class CreatePlayerLinkRequest(PlayerApiModel):
    riot_id: str = Field(min_length=3, max_length=97)
    routing_region: Literal["americas", "asia", "europe", "sea"]
    relationship_role: Literal["self", "observed"]


class CreatePlayerLinkResponse(PlayerApiModel):
    schema_version: Literal["1.0"] = "1.0"
    disposition: PlayerLinkCreateDisposition
    link_task_id: UUID
    status: PlayerLinkStatus
    link: str


class PlayerLinkFailureResponse(PlayerApiModel):
    code: str = Field(min_length=1, max_length=64)
    retryable: bool

    @classmethod
    def from_failure(
        cls,
        failure: PlayerLinkFailure,
    ) -> PlayerLinkFailureResponse:
        if not isinstance(failure, PlayerLinkFailure):
            raise TypeError("failure must be a PlayerLinkFailure")
        return cls(code=failure.code, retryable=failure.retryable)


class PlayerLinkResponse(PlayerApiModel):
    schema_version: Literal["1.0"] = "1.0"
    link_task_id: UUID
    status: PlayerLinkStatus
    created_at: datetime
    updated_at: datetime
    claimed_at: datetime | None
    finished_at: datetime | None
    relationship_role: RelationshipRole
    verification_status: VerificationStatus
    player_subject_id: UUID | None
    relationship_id: UUID | None
    confirmed_riot_id: str | None
    failure: PlayerLinkFailureResponse | None

    @model_validator(mode="after")
    def validate_terminal_projection(self) -> Self:
        if self.status is PlayerLinkStatus.SUCCEEDED:
            if (
                self.player_subject_id is None
                or self.relationship_id is None
                or self.confirmed_riot_id is None
                or self.failure is not None
            ):
                raise ValueError("succeeded response requires resolved identity")
        elif self.status is PlayerLinkStatus.FAILED:
            if (
                self.failure is None
                or self.player_subject_id is not None
                or self.relationship_id is not None
                or self.confirmed_riot_id is not None
            ):
                raise ValueError("failed response requires only safe failure data")
        elif any(
            value is not None
            for value in (
                self.player_subject_id,
                self.relationship_id,
                self.confirmed_riot_id,
                self.failure,
            )
        ):
            raise ValueError("active response cannot contain terminal data")
        return self

    @classmethod
    def from_view(cls, view: PlayerLinkTaskView) -> PlayerLinkResponse:
        if not isinstance(view, PlayerLinkTaskView):
            raise TypeError("view must be a PlayerLinkTaskView")
        relationship_id = (
            view.relationship.relationship_id
            if view.relationship is not None
            else None
        )
        return cls(
            schema_version=view.schema_version,
            link_task_id=view.link_task_id,
            status=view.status,
            created_at=view.created_at,
            updated_at=view.updated_at,
            claimed_at=view.claimed_at,
            finished_at=view.finished_at,
            relationship_role=view.relationship_role,
            verification_status=view.verification_status,
            player_subject_id=view.player_subject_id,
            relationship_id=relationship_id,
            confirmed_riot_id=view.confirmed_riot_id,
            failure=(
                PlayerLinkFailureResponse.from_failure(view.failure)
                if view.failure is not None
                else None
            ),
        )


class PlayerProfileResponse(PlayerApiModel):
    schema_version: Literal["1.0"] = "1.0"
    player_profile_id: UUID
    riot_id: str = Field(min_length=3, max_length=97)
    routing_region: Literal["americas", "asia", "europe", "sea"]
    relationship_role: Literal["self", "observed"]
    verification_status: Literal[
        "unverified_claim",
        "not_applicable",
        "rso_verified",
    ]
    last_resolved_at: datetime

    @classmethod
    def from_view(cls, view: PlayerProfileView) -> PlayerProfileResponse:
        if not isinstance(view, PlayerProfileView):
            raise TypeError("view must be a PlayerProfileView")
        return cls(**view.model_dump(mode="python"))


class PlayerProfilePageResponse(PlayerApiModel):
    schema_version: Literal["1.0"] = "1.0"
    profiles: tuple[PlayerProfileResponse, ...]
    limit: int = Field(ge=1, le=100)

    @classmethod
    def from_page(cls, page: PlayerProfilePage) -> PlayerProfilePageResponse:
        if not isinstance(page, PlayerProfilePage):
            raise TypeError("page must be a PlayerProfilePage")
        return cls(
            profiles=tuple(
                PlayerProfileResponse.from_view(profile) for profile in page.items
            ),
            limit=page.limit,
        )


__all__ = [
    "CreatePlayerLinkRequest",
    "CreatePlayerLinkResponse",
    "PlayerLinkFailureResponse",
    "PlayerLinkResponse",
    "PlayerProfilePageResponse",
    "PlayerProfileResponse",
]
