from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Literal, TypeAlias
from uuid import UUID, uuid4

from pydantic import TypeAdapter, ValidationError

from app.conversations.models import (
    AppendUserMessageCommand,
    ConversationCreateDisposition,
    ConversationCreateResult,
    ConversationMessagePage,
    ConversationMessageView,
    ConversationRepositoryAppendDisposition,
    ConversationRepositoryAppendResult,
    ConversationRepositoryCreateDisposition,
    ConversationRepositoryCreateResult,
    ConversationRepositoryListDisposition,
    ConversationRepositoryListResult,
    ConversationRepositoryMutationDisposition,
    ConversationRepositoryMutationResult,
    ConversationStatus,
    ConversationView,
    CreateConversationCommand,
    ListConversationMessagesQuery,
    OwnerId,
    PendingConversation,
    PendingUserMessage,
    compute_conversation_request_fingerprint,
    compute_message_content_sha256,
)
from app.conversations.ports import ConversationRepository


ConversationServiceErrorCode: TypeAlias = Literal[
    "request_invalid",
    "conversation_not_found",
    "conversation_idempotency_conflict",
    "conversation_archived",
    "service_unavailable",
]
_CONVERSATION_SERVICE_ERROR_CODES = frozenset(
    {
        "request_invalid",
        "conversation_not_found",
        "conversation_idempotency_conflict",
        "conversation_archived",
        "service_unavailable",
    }
)

ConversationIdFactory = Callable[[], UUID]
MessageIdFactory = Callable[[], UUID]
Clock = Callable[[], datetime]
_OWNER_ID_ADAPTER = TypeAdapter(OwnerId)


class ConversationServiceError(RuntimeError):
    def __init__(self, code: ConversationServiceErrorCode) -> None:
        if code not in _CONVERSATION_SERVICE_ERROR_CODES:
            raise ValueError("unsupported conversation service error code")
        self.code = code
        super().__init__(code)

    def to_public_dict(self) -> dict[str, str]:
        return {"code": self.code}


class ConversationService:
    def __init__(
        self,
        *,
        repository: ConversationRepository,
        conversation_id_factory: ConversationIdFactory = uuid4,
        message_id_factory: MessageIdFactory = uuid4,
        clock: Clock | None = None,
    ) -> None:
        for method_name in (
            "create_or_replay_conversation",
            "get_conversation",
            "append_user_message",
            "list_messages",
            "archive_conversation",
            "hide_conversation",
        ):
            if not callable(getattr(repository, method_name, None)):
                raise TypeError(f"repository must expose {method_name}()")
        if not callable(conversation_id_factory):
            raise TypeError("conversation_id_factory must be callable")
        if not callable(message_id_factory):
            raise TypeError("message_id_factory must be callable")
        if clock is not None and not callable(clock):
            raise TypeError("clock must be callable")
        self._repository = repository
        self._conversation_id_factory = conversation_id_factory
        self._message_id_factory = message_id_factory
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def create(self, command: CreateConversationCommand) -> ConversationCreateResult:
        if not isinstance(command, CreateConversationCommand):
            raise TypeError("command must be a CreateConversationCommand")
        try:
            pending = PendingConversation(
                conversation_id=self._conversation_id_factory(),
                owner_id=command.owner_id,
                idempotency_key=command.idempotency_key,
                relationship_id=command.relationship_id,
                request_fingerprint=compute_conversation_request_fingerprint(
                    schema_version="1.0",
                    relationship_id=command.relationship_id,
                ),
                created_at=self._clock(),
            )
        except (StopIteration, TypeError, ValueError, ValidationError):
            raise ConversationServiceError("service_unavailable") from None

        try:
            result = self._repository.create_or_replay_conversation(pending)
        except Exception:
            raise ConversationServiceError("service_unavailable") from None
        if not isinstance(result, ConversationRepositoryCreateResult):
            raise ConversationServiceError("service_unavailable")

        if result.disposition is ConversationRepositoryCreateDisposition.CREATED:
            disposition = ConversationCreateDisposition.CREATED
        elif result.disposition is ConversationRepositoryCreateDisposition.REPLAYED:
            disposition = ConversationCreateDisposition.REPLAYED
        elif (
            result.disposition
            is ConversationRepositoryCreateDisposition.IDEMPOTENCY_CONFLICT
        ):
            raise ConversationServiceError("conversation_idempotency_conflict")
        elif (
            result.disposition
            is ConversationRepositoryCreateDisposition.RELATIONSHIP_UNAVAILABLE
        ):
            raise ConversationServiceError("conversation_not_found")
        else:
            raise ConversationServiceError("service_unavailable")

        if result.conversation is None:
            raise ConversationServiceError("service_unavailable")
        if (
            result.conversation.owner_id != pending.owner_id
            or result.conversation.relationship_id != pending.relationship_id
            or result.conversation.idempotency_key != pending.idempotency_key
            or result.conversation.request_fingerprint != pending.request_fingerprint
            or result.conversation.status.value == "hidden"
            or (
                result.disposition
                is ConversationRepositoryCreateDisposition.CREATED
                and (
                    result.conversation.conversation_id
                    != pending.conversation_id
                    or result.conversation.status is not ConversationStatus.ACTIVE
                )
            )
        ):
            raise ConversationServiceError("service_unavailable")
        return ConversationCreateResult(
            disposition=disposition,
            conversation=ConversationView.from_conversation(result.conversation),
        )

    def get_conversation(
        self,
        *,
        owner_id: str,
        conversation_id: UUID,
    ) -> ConversationView:
        _validate_owner_and_conversation(owner_id, conversation_id)
        try:
            conversation = self._repository.get_conversation(
                owner_id=owner_id,
                conversation_id=conversation_id,
            )
        except Exception:
            raise ConversationServiceError("service_unavailable") from None
        if conversation is None:
            raise ConversationServiceError("conversation_not_found")
        if (
            conversation.owner_id != owner_id
            or conversation.conversation_id != conversation_id
            or conversation.status.value == "hidden"
        ):
            raise ConversationServiceError("service_unavailable")
        try:
            return ConversationView.from_conversation(conversation)
        except (TypeError, ValueError, ValidationError):
            raise ConversationServiceError("service_unavailable") from None

    def append_user_message(
        self,
        command: AppendUserMessageCommand,
    ) -> ConversationMessageView:
        if not isinstance(command, AppendUserMessageCommand):
            raise TypeError("command must be an AppendUserMessageCommand")
        try:
            pending = PendingUserMessage(
                message_id=self._message_id_factory(),
                owner_id=command.owner_id,
                conversation_id=command.conversation_id,
                content=command.content,
                content_sha256=compute_message_content_sha256(command.content),
                created_at=self._clock(),
            )
        except (StopIteration, TypeError, ValueError, ValidationError):
            raise ConversationServiceError("service_unavailable") from None
        try:
            result = self._repository.append_user_message(pending)
        except Exception:
            raise ConversationServiceError("service_unavailable") from None
        if not isinstance(result, ConversationRepositoryAppendResult):
            raise ConversationServiceError("service_unavailable")
        if result.disposition is ConversationRepositoryAppendDisposition.NOT_FOUND:
            raise ConversationServiceError("conversation_not_found")
        if result.disposition is ConversationRepositoryAppendDisposition.ARCHIVED:
            raise ConversationServiceError("conversation_archived")
        if (
            result.disposition is not ConversationRepositoryAppendDisposition.CREATED
            or result.message is None
        ):
            raise ConversationServiceError("service_unavailable")
        if (
            result.message.message_id != pending.message_id
            or result.message.owner_id != pending.owner_id
            or result.message.conversation_id != pending.conversation_id
            or result.message.role is not pending.role
            or result.message.content != pending.content
            or result.message.content_sha256 != pending.content_sha256
        ):
            raise ConversationServiceError("service_unavailable")
        try:
            return ConversationMessageView.from_message(result.message)
        except (TypeError, ValueError, ValidationError):
            raise ConversationServiceError("service_unavailable") from None

    def list_messages(
        self,
        *,
        owner_id: str,
        conversation_id: UUID,
        limit: int = 50,
        after_sequence: int = 0,
    ) -> ConversationMessagePage:
        _validate_owner_and_conversation(owner_id, conversation_id)
        try:
            query = ListConversationMessagesQuery(
                owner_id=owner_id,
                conversation_id=conversation_id,
                limit=limit,
                after_sequence=after_sequence,
            )
        except (TypeError, ValueError, ValidationError):
            raise ConversationServiceError("request_invalid") from None
        try:
            result = self._repository.list_messages(
                owner_id=query.owner_id,
                conversation_id=query.conversation_id,
                after_sequence=query.after_sequence,
                limit=query.limit,
            )
        except Exception:
            raise ConversationServiceError("service_unavailable") from None
        if not isinstance(result, ConversationRepositoryListResult):
            raise ConversationServiceError("service_unavailable")
        if result.disposition is ConversationRepositoryListDisposition.NOT_FOUND:
            raise ConversationServiceError("conversation_not_found")
        if result.disposition is not ConversationRepositoryListDisposition.FOUND:
            raise ConversationServiceError("service_unavailable")
        try:
            if len(result.messages) > query.limit or any(
                message.owner_id != query.owner_id
                or message.conversation_id != query.conversation_id
                or message.sequence_no <= query.after_sequence
                for message in result.messages
            ):
                raise ValueError("repository returned an out-of-scope message page")
            items = tuple(
                ConversationMessageView.from_message(message)
                for message in result.messages
            )
            next_cursor = items[-1].sequence_no if result.has_more and items else None
            return ConversationMessagePage(
                items=items,
                limit=query.limit,
                after_sequence=query.after_sequence,
                has_more=result.has_more,
                next_after_sequence=next_cursor,
            )
        except (TypeError, ValueError, ValidationError):
            raise ConversationServiceError("service_unavailable") from None

    def archive_conversation(
        self,
        *,
        owner_id: str,
        conversation_id: UUID,
    ) -> ConversationView:
        return self._mutate_conversation(
            operation="archive",
            owner_id=owner_id,
            conversation_id=conversation_id,
        )

    def hide_conversation(
        self,
        *,
        owner_id: str,
        conversation_id: UUID,
    ) -> ConversationView:
        return self._mutate_conversation(
            operation="hide",
            owner_id=owner_id,
            conversation_id=conversation_id,
        )

    def _mutate_conversation(
        self,
        *,
        operation: Literal["archive", "hide"],
        owner_id: str,
        conversation_id: UUID,
    ) -> ConversationView:
        _validate_owner_and_conversation(owner_id, conversation_id)
        try:
            now = self._clock()
            if operation == "archive":
                result = self._repository.archive_conversation(
                    owner_id=owner_id,
                    conversation_id=conversation_id,
                    now=now,
                )
            else:
                result = self._repository.hide_conversation(
                    owner_id=owner_id,
                    conversation_id=conversation_id,
                    now=now,
                )
        except Exception:
            raise ConversationServiceError("service_unavailable") from None
        if not isinstance(result, ConversationRepositoryMutationResult):
            raise ConversationServiceError("service_unavailable")
        if result.disposition is ConversationRepositoryMutationDisposition.NOT_FOUND:
            raise ConversationServiceError("conversation_not_found")
        if result.conversation is None:
            raise ConversationServiceError("service_unavailable")
        expected_status = "archived" if operation == "archive" else "hidden"
        if (
            result.conversation.owner_id != owner_id
            or result.conversation.conversation_id != conversation_id
            or result.conversation.status.value != expected_status
        ):
            raise ConversationServiceError("service_unavailable")
        try:
            return ConversationView.from_conversation(result.conversation)
        except (TypeError, ValueError, ValidationError):
            raise ConversationServiceError("service_unavailable") from None


def _validate_owner_and_conversation(owner_id: str, conversation_id: UUID) -> None:
    try:
        _OWNER_ID_ADAPTER.validate_python(owner_id, strict=True)
    except (TypeError, ValueError, ValidationError):
        raise ConversationServiceError("conversation_not_found") from None
    if not isinstance(conversation_id, UUID):
        raise ConversationServiceError("conversation_not_found")


__all__ = [
    "ConversationService",
    "ConversationServiceError",
    "ConversationServiceErrorCode",
]
