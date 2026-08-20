from __future__ import annotations

import hashlib
import json
import re
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

from app.players.models import RelationshipRole


_OWNER_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:@|+-]{0,127}$"
_IDEMPOTENCY_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"
_FINGERPRINT_PATTERN = r"^[0-9a-f]{64}$"
_SOURCE_RUN_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"
_LOWER_HEX_64 = re.compile(_FINGERPRINT_PATTERN)

MAX_MESSAGE_CONTENT_CHARACTERS = 16_384
DEFAULT_MESSAGE_PAGE_LIMIT = 50
MAX_MESSAGE_PAGE_LIMIT = 100

ConversationSchemaVersion = Literal["1.0"]
OwnerId = Annotated[
    str,
    StringConstraints(min_length=1, max_length=128, pattern=_OWNER_PATTERN),
]
IdempotencyKey = Annotated[
    str,
    StringConstraints(min_length=1, max_length=128, pattern=_IDEMPOTENCY_PATTERN),
]
Fingerprint = Annotated[
    str,
    StringConstraints(min_length=64, max_length=64, pattern=_FINGERPRINT_PATTERN),
]
SourceRunId = Annotated[
    str,
    StringConstraints(min_length=1, max_length=128, pattern=_SOURCE_RUN_PATTERN),
]


class ConversationDomainModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )


class ConversationStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    HIDDEN = "hidden"


class ConversationMessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class CreateConversationCommand(ConversationDomainModel):
    owner_id: OwnerId
    idempotency_key: IdempotencyKey
    relationship_id: UUID


class AppendUserMessageCommand(ConversationDomainModel):
    owner_id: OwnerId
    conversation_id: UUID
    content: str

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        return validate_message_content(value)


class ListConversationMessagesQuery(ConversationDomainModel):
    owner_id: OwnerId
    conversation_id: UUID
    limit: int = Field(default=DEFAULT_MESSAGE_PAGE_LIMIT, ge=1, le=MAX_MESSAGE_PAGE_LIMIT)
    after_sequence: int = Field(default=0, ge=0)


class PendingConversation(ConversationDomainModel):
    conversation_id: UUID
    schema_version: ConversationSchemaVersion = "1.0"
    owner_id: OwnerId
    idempotency_key: IdempotencyKey
    relationship_id: UUID
    request_fingerprint: Fingerprint
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        return _as_utc(value)


class Conversation(ConversationDomainModel):
    conversation_id: UUID
    schema_version: ConversationSchemaVersion
    owner_id: OwnerId
    relationship_id: UUID
    player_subject_id: UUID
    relationship_role: RelationshipRole
    idempotency_key: IdempotencyKey
    request_fingerprint: Fingerprint
    status: ConversationStatus
    next_message_sequence: int = Field(ge=1)
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime | None
    hidden_at: datetime | None

    @field_validator("created_at", "updated_at", "last_message_at", "hidden_at")
    @classmethod
    def normalize_datetimes(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _as_utc(value)

    @model_validator(mode="after")
    def validate_lifecycle(self) -> Self:
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not precede created_at")
        if self.last_message_at is not None:
            if self.last_message_at < self.created_at:
                raise ValueError("last_message_at must not precede created_at")
            if self.updated_at < self.last_message_at:
                raise ValueError("updated_at must not precede last_message_at")
        if (self.next_message_sequence == 1) != (self.last_message_at is None):
            raise ValueError(
                "next_message_sequence and last_message_at must describe the same history"
            )
        if self.status is ConversationStatus.HIDDEN:
            if self.hidden_at is None:
                raise ValueError("hidden conversation requires hidden_at")
            if self.hidden_at < self.created_at or self.updated_at < self.hidden_at:
                raise ValueError("hidden_at must fit the conversation timeline")
        elif self.hidden_at is not None:
            raise ValueError("visible conversation cannot include hidden_at")
        return self


class ConversationView(ConversationDomainModel):
    schema_version: ConversationSchemaVersion
    conversation_id: UUID
    relationship_id: UUID
    relationship_role: RelationshipRole
    status: ConversationStatus
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime | None

    @field_validator("created_at", "updated_at", "last_message_at")
    @classmethod
    def normalize_datetimes(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _as_utc(value)

    @classmethod
    def from_conversation(cls, conversation: Conversation) -> ConversationView:
        if not isinstance(conversation, Conversation):
            raise TypeError("conversation must be a Conversation")
        return cls(
            schema_version=conversation.schema_version,
            conversation_id=conversation.conversation_id,
            relationship_id=conversation.relationship_id,
            relationship_role=conversation.relationship_role,
            status=conversation.status,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            last_message_at=conversation.last_message_at,
        )


class PendingUserMessage(ConversationDomainModel):
    message_id: UUID
    owner_id: OwnerId
    conversation_id: UUID
    role: Literal[ConversationMessageRole.USER] = ConversationMessageRole.USER
    content: str
    content_sha256: Fingerprint
    created_at: datetime

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        return validate_message_content(value)

    @field_validator("created_at")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        return _as_utc(value)

    @model_validator(mode="after")
    def validate_digest(self) -> Self:
        _require_matching_content_digest(self.content, self.content_sha256)
        return self


class ConversationMessage(ConversationDomainModel):
    message_id: UUID
    conversation_id: UUID
    owner_id: OwnerId
    relationship_id: UUID
    player_subject_id: UUID
    relationship_role: RelationshipRole
    sequence_no: int = Field(ge=1)
    role: ConversationMessageRole
    content: str
    content_sha256: Fingerprint
    source_task_id: UUID | None
    source_run_id: SourceRunId | None
    created_at: datetime
    hidden_at: datetime | None

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        return validate_message_content(value)

    @field_validator("created_at", "hidden_at")
    @classmethod
    def normalize_datetimes(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _as_utc(value)

    @model_validator(mode="after")
    def validate_integrity_and_source(self) -> Self:
        _require_matching_content_digest(self.content, self.content_sha256)
        if self.hidden_at is not None and self.hidden_at < self.created_at:
            raise ValueError("hidden_at must not precede created_at")
        if self.role is ConversationMessageRole.USER and (
            self.source_task_id is not None or self.source_run_id is not None
        ):
            raise ValueError("user message cannot contain internal source references")
        if (
            self.role is ConversationMessageRole.ASSISTANT
            and self.source_run_id is None
        ):
            raise ValueError("assistant message requires source_run_id")
        return self


class ConversationMessageView(ConversationDomainModel):
    schema_version: ConversationSchemaVersion = "1.0"
    message_id: UUID
    conversation_id: UUID
    sequence_no: int = Field(ge=1)
    role: ConversationMessageRole
    content: str
    content_sha256: Fingerprint
    created_at: datetime

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        return validate_message_content(value)

    @field_validator("created_at")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        return _as_utc(value)

    @model_validator(mode="after")
    def validate_digest(self) -> Self:
        _require_matching_content_digest(self.content, self.content_sha256)
        return self

    @classmethod
    def from_message(cls, message: ConversationMessage) -> ConversationMessageView:
        if not isinstance(message, ConversationMessage):
            raise TypeError("message must be a ConversationMessage")
        if message.hidden_at is not None:
            raise ValueError("hidden message cannot be projected")
        return cls(
            message_id=message.message_id,
            conversation_id=message.conversation_id,
            sequence_no=message.sequence_no,
            role=message.role,
            content=message.content,
            content_sha256=message.content_sha256,
            created_at=message.created_at,
        )


class ConversationCreateDisposition(StrEnum):
    CREATED = "created"
    REPLAYED = "replayed"


class ConversationCreateResult(ConversationDomainModel):
    disposition: ConversationCreateDisposition
    conversation: ConversationView


class ConversationRepositoryCreateDisposition(StrEnum):
    CREATED = "created"
    REPLAYED = "replayed"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"
    RELATIONSHIP_UNAVAILABLE = "relationship_unavailable"


class ConversationRepositoryCreateResult(ConversationDomainModel):
    disposition: ConversationRepositoryCreateDisposition
    conversation: Conversation | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> Self:
        includes_conversation = self.disposition in {
            ConversationRepositoryCreateDisposition.CREATED,
            ConversationRepositoryCreateDisposition.REPLAYED,
        }
        if includes_conversation != (self.conversation is not None):
            raise ValueError("repository create result has an invalid projection")
        return self


class ConversationRepositoryAppendDisposition(StrEnum):
    CREATED = "created"
    NOT_FOUND = "not_found"
    ARCHIVED = "archived"


class ConversationRepositoryAppendResult(ConversationDomainModel):
    disposition: ConversationRepositoryAppendDisposition
    message: ConversationMessage | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> Self:
        includes_message = (
            self.disposition is ConversationRepositoryAppendDisposition.CREATED
        )
        if includes_message != (self.message is not None):
            raise ValueError("repository append result has an invalid projection")
        return self


class ConversationRepositoryListDisposition(StrEnum):
    FOUND = "found"
    NOT_FOUND = "not_found"


class ConversationRepositoryListResult(ConversationDomainModel):
    disposition: ConversationRepositoryListDisposition
    messages: tuple[ConversationMessage, ...] = ()
    has_more: bool = False

    @model_validator(mode="after")
    def validate_shape(self) -> Self:
        if self.disposition is ConversationRepositoryListDisposition.NOT_FOUND:
            if self.messages or self.has_more:
                raise ValueError("not-found list cannot include message state")
            return self
        sequence_numbers = [message.sequence_no for message in self.messages]
        if sequence_numbers != sorted(sequence_numbers) or len(sequence_numbers) != len(
            set(sequence_numbers)
        ):
            raise ValueError("repository messages must be strictly sequence ordered")
        return self


class ConversationMessagePage(ConversationDomainModel):
    items: tuple[ConversationMessageView, ...]
    limit: int = Field(ge=1, le=MAX_MESSAGE_PAGE_LIMIT)
    after_sequence: int = Field(ge=0)
    has_more: bool
    next_after_sequence: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_shape(self) -> Self:
        if len(self.items) > self.limit:
            raise ValueError("message page exceeds its requested limit")
        sequence_numbers = [item.sequence_no for item in self.items]
        if any(number <= self.after_sequence for number in sequence_numbers):
            raise ValueError("message page contains an item before its cursor")
        if sequence_numbers != sorted(sequence_numbers) or len(sequence_numbers) != len(
            set(sequence_numbers)
        ):
            raise ValueError("message page must be strictly sequence ordered")
        expected_cursor = sequence_numbers[-1] if self.has_more and sequence_numbers else None
        if self.next_after_sequence != expected_cursor:
            raise ValueError("next_after_sequence does not match page state")
        if self.has_more and len(self.items) != self.limit:
            raise ValueError("partial page cannot claim more results")
        return self


class ConversationRepositoryMutationDisposition(StrEnum):
    UPDATED = "updated"
    REPLAYED = "replayed"
    NOT_FOUND = "not_found"


class ConversationRepositoryMutationResult(ConversationDomainModel):
    disposition: ConversationRepositoryMutationDisposition
    conversation: Conversation | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> Self:
        includes_conversation = self.disposition in {
            ConversationRepositoryMutationDisposition.UPDATED,
            ConversationRepositoryMutationDisposition.REPLAYED,
        }
        if includes_conversation != (self.conversation is not None):
            raise ValueError("repository mutation result has an invalid projection")
        return self


def canonical_conversation_request_bytes(
    *,
    schema_version: str,
    relationship_id: UUID,
) -> bytes:
    if schema_version != "1.0":
        raise ValueError("unsupported conversation schema_version")
    if not isinstance(relationship_id, UUID):
        raise ValueError("relationship_id must be a UUID")
    payload = {
        "relationship_id": str(relationship_id),
        "schema_version": schema_version,
    }
    return json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def compute_conversation_request_fingerprint(
    *,
    schema_version: str,
    relationship_id: UUID,
) -> str:
    return hashlib.sha256(
        canonical_conversation_request_bytes(
            schema_version=schema_version,
            relationship_id=relationship_id,
        )
    ).hexdigest()


def validate_message_content(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("message content must be a string")
    if not value.strip():
        raise ValueError("message content must not be blank")
    if len(value) > MAX_MESSAGE_CONTENT_CHARACTERS:
        raise ValueError("message content exceeds the local character bound")
    for character in value:
        codepoint = ord(character)
        is_c0 = 0x00 <= codepoint <= 0x1F
        is_c1 = 0x7F <= codepoint <= 0x9F
        if (is_c0 or is_c1) and codepoint not in {0x09, 0x0A, 0x0D}:
            raise ValueError("message content contains a forbidden control character")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError:
        raise ValueError("message content is not valid UTF-8 text") from None
    return value


def compute_message_content_sha256(content: str) -> str:
    validated = validate_message_content(content)
    return hashlib.sha256(validated.encode("utf-8")).hexdigest()


def _require_matching_content_digest(content: str, digest: str) -> None:
    if not _LOWER_HEX_64.fullmatch(digest):
        raise ValueError("content_sha256 must be lowercase hexadecimal")
    if digest != compute_message_content_sha256(content):
        raise ValueError("content_sha256 must match the exact UTF-8 content")


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("conversation timestamps must be timezone-aware")
    return value.astimezone(timezone.utc)


__all__ = [
    "AppendUserMessageCommand",
    "Conversation",
    "ConversationCreateDisposition",
    "ConversationCreateResult",
    "ConversationMessage",
    "ConversationMessagePage",
    "ConversationMessageRole",
    "ConversationMessageView",
    "ConversationRepositoryAppendDisposition",
    "ConversationRepositoryAppendResult",
    "ConversationRepositoryCreateDisposition",
    "ConversationRepositoryCreateResult",
    "ConversationRepositoryListDisposition",
    "ConversationRepositoryListResult",
    "ConversationRepositoryMutationDisposition",
    "ConversationRepositoryMutationResult",
    "ConversationSchemaVersion",
    "ConversationStatus",
    "ConversationView",
    "CreateConversationCommand",
    "DEFAULT_MESSAGE_PAGE_LIMIT",
    "Fingerprint",
    "IdempotencyKey",
    "ListConversationMessagesQuery",
    "MAX_MESSAGE_CONTENT_CHARACTERS",
    "MAX_MESSAGE_PAGE_LIMIT",
    "OwnerId",
    "PendingConversation",
    "PendingUserMessage",
    "RelationshipRole",
    "SourceRunId",
    "canonical_conversation_request_bytes",
    "compute_conversation_request_fingerprint",
    "compute_message_content_sha256",
    "validate_message_content",
]
