from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.conversations.models import (
    AppendUserMessageCommand,
    Conversation,
    ConversationMessage,
    ConversationMessageRole,
    ConversationRepositoryAppendDisposition,
    ConversationRepositoryAppendResult,
    ConversationRepositoryCreateDisposition,
    ConversationRepositoryCreateResult,
    ConversationRepositoryListDisposition,
    ConversationRepositoryListResult,
    ConversationRepositoryMutationDisposition,
    ConversationRepositoryMutationResult,
    ConversationStatus,
    CreateConversationCommand,
    PendingConversation,
    PendingUserMessage,
    RelationshipRole,
    compute_message_content_sha256,
)
from app.conversations.ports import ConversationRepository, ConversationServicePort
from app.conversations.service import ConversationService, ConversationServiceError


NOW = datetime(2026, 8, 20, 10, 0, 0, tzinfo=timezone.utc)
CONVERSATION_IDS = (
    UUID("50000000-0000-4000-8000-000000000001"),
    UUID("50000000-0000-4000-8000-000000000002"),
    UUID("50000000-0000-4000-8000-000000000003"),
)
MESSAGE_IDS = (
    UUID("50000000-0000-4000-8000-000000000010"),
    UUID("50000000-0000-4000-8000-000000000011"),
)
RELATIONSHIP_ID = UUID("50000000-0000-4000-8000-000000000020")
SUBJECT_ID = UUID("50000000-0000-4000-8000-000000000021")


def materialize_conversation(pending: PendingConversation) -> Conversation:
    return Conversation(
        conversation_id=pending.conversation_id,
        schema_version=pending.schema_version,
        owner_id=pending.owner_id,
        relationship_id=pending.relationship_id,
        player_subject_id=SUBJECT_ID,
        relationship_role=RelationshipRole.SELF,
        idempotency_key=pending.idempotency_key,
        request_fingerprint=pending.request_fingerprint,
        status=ConversationStatus.ACTIVE,
        next_message_sequence=1,
        created_at=pending.created_at,
        updated_at=pending.created_at,
        last_message_at=None,
        hidden_at=None,
    )


class FakeConversationRepository(ConversationRepository):
    def __init__(self) -> None:
        self.conversations: list[Conversation] = []
        self.messages: list[ConversationMessage] = []
        self.create_override: ConversationRepositoryCreateDisposition | None = None
        self.failure: Exception | None = None

    def _raise_if_failed(self) -> None:
        if self.failure is not None:
            raise self.failure

    def create_or_replay_conversation(
        self,
        pending: PendingConversation,
    ) -> ConversationRepositoryCreateResult:
        self._raise_if_failed()
        if self.create_override is not None:
            return ConversationRepositoryCreateResult(disposition=self.create_override)
        existing = next(
            (
                item
                for item in self.conversations
                if item.owner_id == pending.owner_id
                and item.idempotency_key == pending.idempotency_key
            ),
            None,
        )
        if existing is not None:
            if existing.request_fingerprint == pending.request_fingerprint:
                return ConversationRepositoryCreateResult(
                    disposition=ConversationRepositoryCreateDisposition.REPLAYED,
                    conversation=existing,
                )
            return ConversationRepositoryCreateResult(
                disposition=ConversationRepositoryCreateDisposition.IDEMPOTENCY_CONFLICT
            )
        created = materialize_conversation(pending)
        self.conversations.append(created)
        return ConversationRepositoryCreateResult(
            disposition=ConversationRepositoryCreateDisposition.CREATED,
            conversation=created,
        )

    def get_conversation(
        self,
        *,
        owner_id: str,
        conversation_id: UUID,
    ) -> Conversation | None:
        self._raise_if_failed()
        return next(
            (
                item
                for item in self.conversations
                if item.owner_id == owner_id
                and item.conversation_id == conversation_id
                and item.status is not ConversationStatus.HIDDEN
            ),
            None,
        )

    def append_user_message(
        self,
        pending: PendingUserMessage,
    ) -> ConversationRepositoryAppendResult:
        self._raise_if_failed()
        stored_conversation = self.get_conversation(
            owner_id=pending.owner_id,
            conversation_id=pending.conversation_id,
        )
        if stored_conversation is None:
            return ConversationRepositoryAppendResult(
                disposition=ConversationRepositoryAppendDisposition.NOT_FOUND
            )
        if stored_conversation.status is ConversationStatus.ARCHIVED:
            return ConversationRepositoryAppendResult(
                disposition=ConversationRepositoryAppendDisposition.ARCHIVED
            )
        stored = ConversationMessage(
            message_id=pending.message_id,
            conversation_id=stored_conversation.conversation_id,
            owner_id=stored_conversation.owner_id,
            relationship_id=stored_conversation.relationship_id,
            player_subject_id=stored_conversation.player_subject_id,
            relationship_role=stored_conversation.relationship_role,
            sequence_no=stored_conversation.next_message_sequence,
            role=pending.role,
            content=pending.content,
            content_sha256=pending.content_sha256,
            source_task_id=None,
            source_run_id=None,
            created_at=pending.created_at,
            hidden_at=None,
        )
        self.messages.append(stored)
        updated = stored_conversation.model_copy(
            update={
                "next_message_sequence": stored.sequence_no + 1,
                "updated_at": pending.created_at,
                "last_message_at": pending.created_at,
            }
        )
        self.conversations[
            self.conversations.index(stored_conversation)
        ] = Conversation.model_validate(updated)
        return ConversationRepositoryAppendResult(
            disposition=ConversationRepositoryAppendDisposition.CREATED,
            message=stored,
        )

    def list_messages(
        self,
        *,
        owner_id: str,
        conversation_id: UUID,
        after_sequence: int,
        limit: int,
    ) -> ConversationRepositoryListResult:
        self._raise_if_failed()
        if self.get_conversation(owner_id=owner_id, conversation_id=conversation_id) is None:
            return ConversationRepositoryListResult(
                disposition=ConversationRepositoryListDisposition.NOT_FOUND,
                messages=(),
                has_more=False,
            )
        candidates = [
            item
            for item in self.messages
            if item.owner_id == owner_id
            and item.conversation_id == conversation_id
            and item.sequence_no > after_sequence
            and item.hidden_at is None
        ]
        candidates.sort(key=lambda item: item.sequence_no)
        return ConversationRepositoryListResult(
            disposition=ConversationRepositoryListDisposition.FOUND,
            messages=tuple(candidates[:limit]),
            has_more=len(candidates) > limit,
        )

    def archive_conversation(
        self,
        *,
        owner_id: str,
        conversation_id: UUID,
        now: datetime,
    ) -> ConversationRepositoryMutationResult:
        return self._mutate(owner_id, conversation_id, now, ConversationStatus.ARCHIVED)

    def hide_conversation(
        self,
        *,
        owner_id: str,
        conversation_id: UUID,
        now: datetime,
    ) -> ConversationRepositoryMutationResult:
        return self._mutate(owner_id, conversation_id, now, ConversationStatus.HIDDEN)

    def _mutate(
        self,
        owner_id: str,
        conversation_id: UUID,
        now: datetime,
        target: ConversationStatus,
    ) -> ConversationRepositoryMutationResult:
        self._raise_if_failed()
        stored = self.get_conversation(owner_id=owner_id, conversation_id=conversation_id)
        if stored is None:
            return ConversationRepositoryMutationResult(
                disposition=ConversationRepositoryMutationDisposition.NOT_FOUND
            )
        if stored.status is target:
            return ConversationRepositoryMutationResult(
                disposition=ConversationRepositoryMutationDisposition.REPLAYED,
                conversation=stored,
            )
        updated = Conversation.model_validate(
            stored.model_copy(
                update={
                    "status": target,
                    "updated_at": now,
                    "hidden_at": now if target is ConversationStatus.HIDDEN else None,
                }
            )
        )
        self.conversations[self.conversations.index(stored)] = updated
        return ConversationRepositoryMutationResult(
            disposition=ConversationRepositoryMutationDisposition.UPDATED,
            conversation=updated,
        )


def service(repository: FakeConversationRepository) -> ConversationService:
    conversation_ids = iter(CONVERSATION_IDS)
    message_ids = iter(MESSAGE_IDS)
    return ConversationService(
        repository=repository,
        conversation_id_factory=lambda: next(conversation_ids),
        message_id_factory=lambda: next(message_ids),
        clock=lambda: NOW,
    )


def command(*, owner_id: str = "owner-1", key: str = "conversation-1") -> CreateConversationCommand:
    return CreateConversationCommand(
        owner_id=owner_id,
        idempotency_key=key,
        relationship_id=RELATIONSHIP_ID,
    )


def test_service_satisfies_port_and_create_replays_without_duplicate() -> None:
    repository = FakeConversationRepository()
    conversation_service: ConversationServicePort = service(repository)
    created = conversation_service.create(command())
    replayed = conversation_service.create(command())
    assert created.disposition.value == "created"
    assert replayed.disposition.value == "replayed"
    assert replayed.conversation.conversation_id == created.conversation.conversation_id
    assert len(repository.conversations) == 1


def test_create_maps_atomic_repository_conflict_and_unavailable_relationship() -> None:
    repository = FakeConversationRepository()
    conversation_service = service(repository)
    conversation_service.create(command())
    with pytest.raises(ConversationServiceError) as conflict:
        conversation_service.create(
            command(key="conversation-1").model_copy(
                update={
                    "relationship_id": UUID(
                        "50000000-0000-4000-8000-000000000099"
                    )
                }
            )
        )
    assert conflict.value.code == "conversation_idempotency_conflict"
    assert conflict.value.to_public_dict() == {"code": "conversation_idempotency_conflict"}

    repository.create_override = ConversationRepositoryCreateDisposition.RELATIONSHIP_UNAVAILABLE
    with pytest.raises(ConversationServiceError) as unavailable:
        conversation_service.create(command(key="conversation-2"))
    assert unavailable.value.code == "conversation_not_found"


@pytest.mark.parametrize(
    "invalid_projection",
    (
        {"conversation_id": CONVERSATION_IDS[1]},
        {"status": ConversationStatus.ARCHIVED},
    ),
)
def test_created_conversation_must_match_server_identity_and_initial_state(
    invalid_projection: dict[str, object],
) -> None:
    repository = FakeConversationRepository()
    conversation_service = service(repository)

    def return_invalid_created(
        pending: PendingConversation,
    ) -> ConversationRepositoryCreateResult:
        conversation = materialize_conversation(pending).model_copy(
            update=invalid_projection
        )
        return ConversationRepositoryCreateResult(
            disposition=ConversationRepositoryCreateDisposition.CREATED,
            conversation=conversation,
        )

    repository.create_or_replay_conversation = return_invalid_created  # type: ignore[method-assign]

    with pytest.raises(ConversationServiceError) as failed:
        conversation_service.create(command())

    assert failed.value.code == "service_unavailable"


def test_get_is_owner_scoped_and_repository_error_is_body_free() -> None:
    repository = FakeConversationRepository()
    conversation_service = service(repository)
    created = conversation_service.create(command())
    assert conversation_service.get_conversation(
        owner_id="owner-1",
        conversation_id=created.conversation.conversation_id,
    ) == created.conversation
    with pytest.raises(ConversationServiceError) as wrong_owner:
        conversation_service.get_conversation(
            owner_id="owner-2",
            conversation_id=created.conversation.conversation_id,
        )
    assert wrong_owner.value.code == "conversation_not_found"

    repository.failure = RuntimeError("sql contained secret and message body")
    with pytest.raises(ConversationServiceError) as failed:
        conversation_service.get_conversation(
            owner_id="owner-1",
            conversation_id=created.conversation.conversation_id,
        )
    assert failed.value.to_public_dict() == {"code": "service_unavailable"}
    assert "secret" not in repr(failed.value)


def test_service_rejects_repository_cross_scope_projection_without_leaking_it() -> None:
    repository = FakeConversationRepository()
    conversation_service = service(repository)
    created = conversation_service.create(command())
    wrong_scope = repository.conversations[0].model_copy(update={"owner_id": "owner-2"})
    repository.get_conversation = lambda **_: wrong_scope  # type: ignore[method-assign]

    with pytest.raises(ConversationServiceError) as failed:
        conversation_service.get_conversation(
            owner_id="owner-1",
            conversation_id=created.conversation.conversation_id,
        )

    assert failed.value.code == "service_unavailable"
    assert "owner-2" not in repr(failed.value)


def test_append_user_message_preserves_content_and_derives_digest() -> None:
    repository = FakeConversationRepository()
    conversation_service = service(repository)
    created = conversation_service.create(command())
    content = "  exact\tcontent\r\n"
    result = conversation_service.append_user_message(
        AppendUserMessageCommand(
            owner_id="owner-1",
            conversation_id=created.conversation.conversation_id,
            content=content,
        )
    )
    assert result.role is ConversationMessageRole.USER
    assert result.content == content
    assert result.sequence_no == 1
    assert result.content_sha256 == compute_message_content_sha256(content)
    assert not hasattr(conversation_service, "append_assistant_message")


def test_append_rejects_archived_and_hides_not_found_scope() -> None:
    repository = FakeConversationRepository()
    conversation_service = service(repository)
    created = conversation_service.create(command())
    conversation_service.archive_conversation(
        owner_id="owner-1",
        conversation_id=created.conversation.conversation_id,
    )
    with pytest.raises(ConversationServiceError) as archived:
        conversation_service.append_user_message(
            AppendUserMessageCommand(
                owner_id="owner-1",
                conversation_id=created.conversation.conversation_id,
                content="hello",
            )
        )
    assert archived.value.code == "conversation_archived"

    with pytest.raises(ConversationServiceError) as missing:
        conversation_service.append_user_message(
            AppendUserMessageCommand(
                owner_id="owner-2",
                conversation_id=created.conversation.conversation_id,
                content="hello",
            )
        )
    assert missing.value.code == "conversation_not_found"


def test_list_is_bounded_ordered_and_uses_repository_has_more() -> None:
    repository = FakeConversationRepository()
    conversation_service = service(repository)
    created = conversation_service.create(command())
    for content in ("one", "two"):
        conversation_service.append_user_message(
            AppendUserMessageCommand(
                owner_id="owner-1",
                conversation_id=created.conversation.conversation_id,
                content=content,
            )
        )
    first_page = conversation_service.list_messages(
        owner_id="owner-1",
        conversation_id=created.conversation.conversation_id,
        limit=1,
        after_sequence=0,
    )
    assert [item.content for item in first_page.items] == ["one"]
    assert first_page.has_more is True
    assert first_page.next_after_sequence == 1
    second_page = conversation_service.list_messages(
        owner_id="owner-1",
        conversation_id=created.conversation.conversation_id,
        limit=1,
        after_sequence=1,
    )
    assert [item.content for item in second_page.items] == ["two"]

    with pytest.raises(ConversationServiceError) as invalid:
        conversation_service.list_messages(
            owner_id="owner-1",
            conversation_id=created.conversation.conversation_id,
            limit=101,
            after_sequence=0,
        )
    assert invalid.value.code == "request_invalid"


def test_archive_and_hide_are_one_way_and_hidden_becomes_not_found() -> None:
    repository = FakeConversationRepository()
    conversation_service = service(repository)
    created = conversation_service.create(command())
    archived = conversation_service.archive_conversation(
        owner_id="owner-1",
        conversation_id=created.conversation.conversation_id,
    )
    assert archived.status is ConversationStatus.ARCHIVED
    replayed = conversation_service.archive_conversation(
        owner_id="owner-1",
        conversation_id=created.conversation.conversation_id,
    )
    assert replayed.status is ConversationStatus.ARCHIVED
    hidden = conversation_service.hide_conversation(
        owner_id="owner-1",
        conversation_id=created.conversation.conversation_id,
    )
    assert hidden.status is ConversationStatus.HIDDEN
    with pytest.raises(ConversationServiceError) as missing:
        conversation_service.get_conversation(
            owner_id="owner-1",
            conversation_id=created.conversation.conversation_id,
        )
    assert missing.value.code == "conversation_not_found"


def test_service_error_codes_are_allowlisted_and_constructor_checks_port() -> None:
    assert ConversationServiceError("request_invalid").to_public_dict() == {
        "code": "request_invalid"
    }
    with pytest.raises(ValueError):
        ConversationServiceError("raw_sql_error")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="create_or_replay_conversation"):
        ConversationService(repository=object())  # type: ignore[arg-type]


@pytest.mark.parametrize("operation", ("create", "append"))
@pytest.mark.parametrize("broken_dependency", ("id_factory", "clock"))
def test_valid_command_maps_internal_factory_failure_to_service_unavailable(
    operation: str,
    broken_dependency: str,
) -> None:
    repository = FakeConversationRepository()
    kwargs: dict[str, object] = {"repository": repository}
    if broken_dependency == "clock":
        kwargs["clock"] = lambda: "not-a-datetime"
    elif operation == "create":
        kwargs["conversation_id_factory"] = lambda: "not-a-uuid"
    else:
        kwargs["message_id_factory"] = lambda: "not-a-uuid"
    conversation_service = ConversationService(**kwargs)  # type: ignore[arg-type]

    with pytest.raises(ConversationServiceError) as failure:
        if operation == "create":
            conversation_service.create(command())
        else:
            conversation_service.append_user_message(
                AppendUserMessageCommand(
                    owner_id="owner-1",
                    conversation_id=CONVERSATION_IDS[0],
                    content="valid user message",
                )
            )

    assert failure.value.code == "service_unavailable"


def test_service_rejects_wrong_command_type_before_repository() -> None:
    repository = FakeConversationRepository()
    conversation_service = service(repository)
    with pytest.raises(TypeError):
        conversation_service.create(object())  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        conversation_service.append_user_message(object())  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        AppendUserMessageCommand(
            owner_id="owner-1",
            conversation_id=CONVERSATION_IDS[0],
            content="hello",
            source_run_id="forged",
        )
