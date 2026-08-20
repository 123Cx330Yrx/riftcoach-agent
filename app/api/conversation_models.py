"""Strict public HTTP models for Conversation/Message control-plane APIs.

These DTOs intentionally omit owner, player-subject, PUUID, idempotency
fingerprint and internal source references.  Those values are server facts,
not client-authoritative HTTP fields.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Self, TypeAlias
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.conversations.models import (
    ConversationCreateResult,
    ConversationMessagePage,
    ConversationMessageView,
    ConversationView,
)


ConversationApiErrorCode: TypeAlias = Literal[
    "request_invalid",
    "conversation_not_found",
    "conversation_idempotency_conflict",
    "conversation_archived",
    "service_unavailable",
]
ConversationDisposition: TypeAlias = Literal["created", "replayed"]
ConversationRelationshipRole: TypeAlias = Literal["self", "observed"]
ConversationLifecycleStatus: TypeAlias = Literal[
    "active",
    "archived",
    "hidden",
]
ConversationMessageRoleValue: TypeAlias = Literal["user", "assistant"]


class ConversationApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class CreateConversationRequest(ConversationApiModel):
    relationship_id: UUID

    @field_validator("relationship_id", mode="before")
    @classmethod
    def parse_json_uuid(cls, value: object) -> object:
        # FastAPI supplies JSON strings to model validation.  Keep the DTO
        # strict for every other field while explicitly accepting the UUID's
        # canonical wire representation.
        if isinstance(value, UUID):
            return value
        if isinstance(value, str):
            try:
                return UUID(value)
            except ValueError:
                pass
        raise ValueError("relationship_id must be a UUID")


class AppendUserMessageRequest(ConversationApiModel):
    content: str = Field(min_length=1, max_length=16_384)


class ConversationResponse(ConversationApiModel):
    schema_version: Literal["1.0"] = "1.0"
    conversation_id: UUID
    relationship_id: UUID
    relationship_role: ConversationRelationshipRole
    status: ConversationLifecycleStatus
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime | None

    @classmethod
    def from_view(cls, view: ConversationView) -> Self:
        if not isinstance(view, ConversationView):
            raise TypeError("view must be a ConversationView")
        return cls(
            schema_version=view.schema_version,
            conversation_id=view.conversation_id,
            relationship_id=view.relationship_id,
            relationship_role=view.relationship_role,
            status=view.status,
            created_at=view.created_at,
            updated_at=view.updated_at,
            last_message_at=view.last_message_at,
        )


class CreateConversationResponse(ConversationResponse):
    disposition: ConversationDisposition

    @classmethod
    def from_result(cls, result: ConversationCreateResult) -> Self:
        if not isinstance(result, ConversationCreateResult):
            raise TypeError("result must be a ConversationCreateResult")
        view = result.conversation
        return cls(
            schema_version=view.schema_version,
            disposition=result.disposition,
            conversation_id=view.conversation_id,
            relationship_id=view.relationship_id,
            relationship_role=view.relationship_role,
            status=view.status,
            created_at=view.created_at,
            updated_at=view.updated_at,
            last_message_at=view.last_message_at,
        )


class ConversationMessageResponse(ConversationApiModel):
    schema_version: Literal["1.0"] = "1.0"
    message_id: UUID
    conversation_id: UUID
    sequence_no: int = Field(ge=1)
    role: ConversationMessageRoleValue
    content: str = Field(min_length=1, max_length=16_384)
    content_sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )
    created_at: datetime

    @classmethod
    def from_view(cls, view: ConversationMessageView) -> Self:
        if not isinstance(view, ConversationMessageView):
            raise TypeError("view must be a ConversationMessageView")
        return cls(
            message_id=view.message_id,
            conversation_id=view.conversation_id,
            sequence_no=view.sequence_no,
            role=view.role,
            content=view.content,
            content_sha256=view.content_sha256,
            created_at=view.created_at,
        )


class ConversationMessagePageResponse(ConversationApiModel):
    schema_version: Literal["1.0"] = "1.0"
    conversation_id: UUID
    items: tuple[ConversationMessageResponse, ...]
    limit: int = Field(ge=1, le=100)
    after_sequence: int = Field(ge=0)
    has_more: bool
    next_after_sequence: int | None = Field(default=None, ge=1)

    @classmethod
    def from_page(
        cls,
        *,
        conversation_id: UUID,
        page: ConversationMessagePage,
    ) -> Self:
        if not isinstance(conversation_id, UUID):
            raise TypeError("conversation_id must be a UUID")
        if not isinstance(page, ConversationMessagePage):
            raise TypeError("page must be a ConversationMessagePage")
        return cls(
            conversation_id=conversation_id,
            items=tuple(
                ConversationMessageResponse.from_view(item)
                for item in page.items
            ),
            limit=page.limit,
            after_sequence=page.after_sequence,
            has_more=page.has_more,
            next_after_sequence=page.next_after_sequence,
        )


class ConversationErrorResponse(ConversationApiModel):
    code: ConversationApiErrorCode


__all__ = [
    "AppendUserMessageRequest",
    "ConversationApiErrorCode",
    "ConversationErrorResponse",
    "ConversationMessagePageResponse",
    "ConversationMessageResponse",
    "ConversationResponse",
    "CreateConversationRequest",
    "CreateConversationResponse",
]
