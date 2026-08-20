from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.conversations.models import (
    AppendUserMessageCommand,
    Conversation,
    ConversationCreateResult,
    ConversationMessagePage,
    ConversationMessageView,
    ConversationRepositoryAppendResult,
    ConversationRepositoryCreateResult,
    ConversationRepositoryListResult,
    ConversationRepositoryMutationResult,
    ConversationView,
    CreateConversationCommand,
    PendingConversation,
    PendingUserMessage,
)


class ConversationRepositoryError(RuntimeError):
    """Repository failure that must be mapped before a public boundary."""


class ConversationRepository(Protocol):
    def create_or_replay_conversation(
        self,
        pending: PendingConversation,
    ) -> ConversationRepositoryCreateResult: ...

    def get_conversation(
        self,
        *,
        owner_id: str,
        conversation_id: UUID,
    ) -> Conversation | None: ...

    def append_user_message(
        self,
        pending: PendingUserMessage,
    ) -> ConversationRepositoryAppendResult: ...

    def list_messages(
        self,
        *,
        owner_id: str,
        conversation_id: UUID,
        after_sequence: int,
        limit: int,
    ) -> ConversationRepositoryListResult: ...

    def archive_conversation(
        self,
        *,
        owner_id: str,
        conversation_id: UUID,
        now: datetime,
    ) -> ConversationRepositoryMutationResult: ...

    def hide_conversation(
        self,
        *,
        owner_id: str,
        conversation_id: UUID,
        now: datetime,
    ) -> ConversationRepositoryMutationResult: ...


class ConversationServicePort(Protocol):
    def create(self, command: CreateConversationCommand) -> ConversationCreateResult: ...

    def get_conversation(
        self,
        *,
        owner_id: str,
        conversation_id: UUID,
    ) -> ConversationView: ...

    def append_user_message(
        self,
        command: AppendUserMessageCommand,
    ) -> ConversationMessageView: ...

    def list_messages(
        self,
        *,
        owner_id: str,
        conversation_id: UUID,
        limit: int = 50,
        after_sequence: int = 0,
    ) -> ConversationMessagePage: ...

    def archive_conversation(
        self,
        *,
        owner_id: str,
        conversation_id: UUID,
    ) -> ConversationView: ...

    def hide_conversation(
        self,
        *,
        owner_id: str,
        conversation_id: UUID,
    ) -> ConversationView: ...


__all__ = [
    "ConversationRepository",
    "ConversationRepositoryError",
    "ConversationServicePort",
]
