from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.conversations.models import (
    AppendUserMessageCommand,
    Conversation,
    ConversationMessage,
    ConversationMessagePage,
    ConversationMessageRole,
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
    PendingConversation,
    PendingUserMessage,
    RelationshipRole,
    canonical_conversation_request_bytes,
    compute_conversation_request_fingerprint,
    compute_message_content_sha256,
)


NOW = datetime(2026, 8, 20, 9, 0, 0, tzinfo=timezone.utc)
CONVERSATION_ID = UUID("40000000-0000-4000-8000-000000000001")
RELATIONSHIP_ID = UUID("40000000-0000-4000-8000-000000000002")
SUBJECT_ID = UUID("40000000-0000-4000-8000-000000000003")
MESSAGE_ID = UUID("40000000-0000-4000-8000-000000000004")


def conversation(**changes: object) -> Conversation:
    values: dict[str, object] = {
        "conversation_id": CONVERSATION_ID,
        "schema_version": "1.0",
        "owner_id": "owner-1",
        "relationship_id": RELATIONSHIP_ID,
        "player_subject_id": SUBJECT_ID,
        "relationship_role": RelationshipRole.SELF,
        "idempotency_key": "conversation-1",
        "request_fingerprint": "a" * 64,
        "status": ConversationStatus.ACTIVE,
        "next_message_sequence": 1,
        "created_at": NOW,
        "updated_at": NOW,
        "last_message_at": None,
        "hidden_at": None,
    }
    values.update(changes)
    return Conversation(**values)  # type: ignore[arg-type]


def message(**changes: object) -> ConversationMessage:
    content = changes.pop("content", "  keep this exactly \n")
    values: dict[str, object] = {
        "message_id": MESSAGE_ID,
        "conversation_id": CONVERSATION_ID,
        "owner_id": "owner-1",
        "relationship_id": RELATIONSHIP_ID,
        "player_subject_id": SUBJECT_ID,
        "relationship_role": RelationshipRole.SELF,
        "sequence_no": 1,
        "role": ConversationMessageRole.USER,
        "content": content,
        "content_sha256": compute_message_content_sha256(content),
        "source_task_id": None,
        "source_run_id": None,
        "created_at": NOW,
        "hidden_at": None,
    }
    values.update(changes)
    return ConversationMessage(**values)  # type: ignore[arg-type]


def test_command_is_strict_and_only_accepts_server_scoped_identity() -> None:
    command = CreateConversationCommand(
        owner_id="owner-1",
        idempotency_key="conversation-1",
        relationship_id=RELATIONSHIP_ID,
    )
    assert command.relationship_id == RELATIONSHIP_ID
    assert set(CreateConversationCommand.model_fields) == {
        "owner_id",
        "idempotency_key",
        "relationship_id",
    }

    with pytest.raises(ValidationError):
        CreateConversationCommand(
            owner_id="owner-1",
            idempotency_key="conversation-1",
            relationship_id=str(RELATIONSHIP_ID),
        )
    with pytest.raises(ValidationError):
        CreateConversationCommand(
            owner_id="owner-1",
            idempotency_key="conversation-1",
            relationship_id=RELATIONSHIP_ID,
            player_subject_id=SUBJECT_ID,
        )


def test_fingerprint_is_canonical_and_sensitive_to_relationship() -> None:
    expected = (
        b'{"relationship_id":"40000000-0000-4000-8000-000000000002",'
        b'"schema_version":"1.0"}'
    )
    assert canonical_conversation_request_bytes(
        schema_version="1.0",
        relationship_id=RELATIONSHIP_ID,
    ) == expected
    baseline = compute_conversation_request_fingerprint(
        schema_version="1.0",
        relationship_id=RELATIONSHIP_ID,
    )
    assert len(baseline) == 64
    assert baseline != compute_conversation_request_fingerprint(
        schema_version="1.0",
        relationship_id=UUID("40000000-0000-4000-8000-000000000099"),
    )


def test_conversation_status_shape_and_public_view_are_strict() -> None:
    assert tuple(status.value for status in ConversationStatus) == (
        "active",
        "archived",
        "hidden",
    )
    archived = conversation(status=ConversationStatus.ARCHIVED)
    hidden = conversation(
        status=ConversationStatus.HIDDEN,
        hidden_at=NOW + timedelta(seconds=1),
        updated_at=NOW + timedelta(seconds=1),
    )
    assert archived.hidden_at is None
    assert hidden.hidden_at is not None

    with pytest.raises(ValidationError):
        conversation(status=ConversationStatus.HIDDEN)
    with pytest.raises(ValidationError):
        conversation(hidden_at=NOW)
    with pytest.raises(ValidationError):
        conversation(next_message_sequence=0)
    with pytest.raises(ValidationError, match="same history"):
        conversation(next_message_sequence=2, last_message_at=None)
    with pytest.raises(ValidationError, match="same history"):
        conversation(last_message_at=NOW)

    payload = ConversationView.from_conversation(archived).model_dump(mode="json")
    assert payload["status"] == "archived"
    assert payload["relationship_id"] == str(RELATIONSHIP_ID)
    for private_field in (
        "owner_id",
        "player_subject_id",
        "idempotency_key",
        "request_fingerprint",
        "next_message_sequence",
        "hidden_at",
    ):
        assert private_field not in payload


def test_message_content_is_preserved_exactly_and_sha_is_server_derived() -> None:
    content = "  Caf\u00e9\t\U0001f680\r\n  "
    command = AppendUserMessageCommand(
        owner_id="owner-1",
        conversation_id=CONVERSATION_ID,
        content=content,
    )
    assert command.content == content
    assert "role" not in AppendUserMessageCommand.model_fields
    assert "content_sha256" not in AppendUserMessageCommand.model_fields
    assert compute_message_content_sha256(content) == (
        "bf56c6ba1e4518cbd573d3a54ddd90c655a3dc789ee76388f467b6a2faaeab3d"
    )

    pending = PendingUserMessage(
        message_id=MESSAGE_ID,
        owner_id="owner-1",
        conversation_id=CONVERSATION_ID,
        content=content,
        content_sha256=compute_message_content_sha256(content),
        created_at=NOW,
    )
    assert pending.role is ConversationMessageRole.USER
    assert pending.content == content


@pytest.mark.parametrize("content", ["", "   \t\r\n", "x\x00y", "x\x7fy", "x\x85y", "\ud800"])
def test_message_rejects_blank_control_and_invalid_utf8_surrogate(content: str) -> None:
    with pytest.raises((ValidationError, ValueError)):
        AppendUserMessageCommand(
            owner_id="owner-1",
            conversation_id=CONVERSATION_ID,
            content=content,
        )


def test_message_unicode_character_bound_is_16384_without_normalizing() -> None:
    accepted = "\U0001f680" * 16_384
    assert AppendUserMessageCommand(
        owner_id="owner-1",
        conversation_id=CONVERSATION_ID,
        content=accepted,
    ).content == accepted
    with pytest.raises(ValidationError):
        AppendUserMessageCommand(
            owner_id="owner-1",
            conversation_id=CONVERSATION_ID,
            content=accepted + "x",
        )


def test_message_model_validates_digest_binding_and_public_projection() -> None:
    stored = message()
    projected = ConversationMessageView.from_message(stored)
    payload = projected.model_dump(mode="json")
    assert payload["content"] == "  keep this exactly \n"
    assert payload["role"] == "user"
    assert payload["sequence_no"] == 1
    for private_field in (
        "owner_id",
        "relationship_id",
        "player_subject_id",
        "relationship_role",
        "source_task_id",
        "source_run_id",
        "hidden_at",
    ):
        assert private_field not in payload

    with pytest.raises(ValidationError):
        message(content_sha256="b" * 64)
    with pytest.raises(ValueError, match="hidden"):
        ConversationMessageView.from_message(message(hidden_at=NOW))


def test_message_role_is_schema_bounded_but_public_command_cannot_set_it() -> None:
    assert tuple(role.value for role in ConversationMessageRole) == (
        "user",
        "assistant",
    )
    with pytest.raises(ValidationError):
        AppendUserMessageCommand(
            owner_id="owner-1",
            conversation_id=CONVERSATION_ID,
            content="hello",
            role="assistant",
        )

    with pytest.raises(ValidationError, match="source_run_id"):
        message(role=ConversationMessageRole.ASSISTANT)
    assistant = message(
        role=ConversationMessageRole.ASSISTANT,
        source_run_id="review_run_1",
    )
    assert assistant.source_task_id is None
    assert assistant.source_run_id == "review_run_1"


def test_list_query_and_page_are_bounded_and_stably_ordered() -> None:
    query = ListConversationMessagesQuery(
        owner_id="owner-1",
        conversation_id=CONVERSATION_ID,
    )
    assert query.limit == 50
    assert query.after_sequence == 0
    for bad_limit in (0, 101):
        with pytest.raises(ValidationError):
            ListConversationMessagesQuery(
                owner_id="owner-1",
                conversation_id=CONVERSATION_ID,
                limit=bad_limit,
            )

    first = ConversationMessageView.from_message(message())
    second = ConversationMessageView.from_message(
        message(
            message_id=UUID("40000000-0000-4000-8000-000000000005"),
            sequence_no=2,
        )
    )
    page = ConversationMessagePage(
        items=(first, second),
        limit=2,
        after_sequence=0,
        has_more=True,
        next_after_sequence=2,
    )
    assert [item.sequence_no for item in page.items] == [1, 2]
    with pytest.raises(ValidationError):
        ConversationMessagePage(
            items=(second, first),
            limit=2,
            after_sequence=0,
            has_more=False,
            next_after_sequence=None,
        )


def test_repository_result_shapes_cannot_smuggle_missing_or_extra_entities() -> None:
    full_conversation = conversation()
    full_message = message()
    assert ConversationRepositoryCreateResult(
        disposition=ConversationRepositoryCreateDisposition.CREATED,
        conversation=full_conversation,
    ).conversation is not None
    assert ConversationRepositoryAppendResult(
        disposition=ConversationRepositoryAppendDisposition.CREATED,
        message=full_message,
    ).message is not None
    assert ConversationRepositoryListResult(
        disposition=ConversationRepositoryListDisposition.FOUND,
        messages=(full_message,),
        has_more=False,
    ).messages == (full_message,)
    assert ConversationRepositoryMutationResult(
        disposition=ConversationRepositoryMutationDisposition.UPDATED,
        conversation=full_conversation,
    ).conversation is not None

    with pytest.raises(ValidationError):
        ConversationRepositoryCreateResult(
            disposition=ConversationRepositoryCreateDisposition.CREATED
        )
    with pytest.raises(ValidationError):
        ConversationRepositoryAppendResult(
            disposition=ConversationRepositoryAppendDisposition.ARCHIVED,
            message=full_message,
        )
    with pytest.raises(ValidationError):
        ConversationRepositoryListResult(
            disposition=ConversationRepositoryListDisposition.NOT_FOUND,
            messages=(full_message,),
            has_more=False,
        )
    with pytest.raises(ValidationError):
        ConversationRepositoryMutationResult(
            disposition=ConversationRepositoryMutationDisposition.NOT_FOUND,
            conversation=full_conversation,
        )


def test_pending_conversation_contains_only_identity_needed_for_atomic_create() -> None:
    pending = PendingConversation(
        conversation_id=CONVERSATION_ID,
        owner_id="owner-1",
        idempotency_key="conversation-1",
        relationship_id=RELATIONSHIP_ID,
        request_fingerprint="a" * 64,
        created_at=NOW,
    )
    assert "player_subject_id" not in PendingConversation.model_fields
    assert "relationship_role" not in PendingConversation.model_fields
    assert pending.created_at.tzinfo is not None
