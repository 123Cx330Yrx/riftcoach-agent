from datetime import timedelta

from app.conversations.models import PendingUserMessage, compute_message_content_sha256
from app.lifecycle.models import (
    OwnerDataDeleteCommand,
    OwnerDataDeleteScope,
    OwnerDataDeletionStatus,
)
from app.persistence.conversation_records import ConversationMessageRecord, ConversationRecord
from app.persistence.conversation_repository import PostgresConversationRepository
from app.persistence.owner_data_lifecycle_repository import (
    PostgresOwnerDataLifecycleRepository,
)
from app.persistence.task_record import ReviewTaskRecord
from tests.memory_candidate_postgres_support import BASE, migrated_memory_repository, seed_conversation
from uuid import UUID


def _command(scope, *, conversation_id=None, relationship_id=None, key="delete-1"):
    return OwnerDataDeleteCommand(
        owner_id="memory-owner",
        idempotency_key=key,
        scope=scope,
        conversation_id=conversation_id,
        relationship_id=relationship_id,
        requested_at=BASE + timedelta(days=2),
    )


def test_export_is_owner_scoped_and_excludes_hidden_rows() -> None:
    with migrated_memory_repository() as (_candidate, factory, _engine):
        _subject, _relationship, conversation = seed_conversation(factory, number=601)
        PostgresConversationRepository(factory).append_user_message(
            PendingUserMessage(
                message_id=UUID("96000000-0000-4000-8000-000000000601"),
                owner_id="memory-owner",
                conversation_id=conversation,
                content="export me",
                content_sha256=compute_message_content_sha256("export me"),
                created_at=BASE + timedelta(minutes=1),
            )
        )
        repository = PostgresOwnerDataLifecycleRepository(factory)
        exported = repository.export_owner_data(
            owner_id="memory-owner",
            generated_at=BASE + timedelta(days=2),
            limit_per_section=500,
        )
        messages = next(section for section in exported.sections if section.name == "messages")
        assert len(messages.records) == 1
        assert messages.records[0].data["content"] == "export me"
        assert "puuid" not in exported.model_dump_json().lower()

        marker = repository.hide_owner_data(
            _command(OwnerDataDeleteScope.CONVERSATION_ONLY, conversation_id=conversation)
        )
        assert marker.status is OwnerDataDeletionStatus.CLEANUP_PENDING
        hidden_export = repository.export_owner_data(
            owner_id="memory-owner",
            generated_at=BASE + timedelta(days=2),
            limit_per_section=500,
        )
        assert not next(
            section for section in hidden_export.sections if section.name == "messages"
        ).records

        with factory() as session:
            row = session.get(ConversationRecord, conversation)
            message = session.get(ConversationMessageRecord, messages.records[0].record_id)
            assert row is not None and row.status == "hidden"
            assert message is not None and message.hidden_at is not None


def test_delete_idempotency_and_scope_conflict_are_owner_scoped() -> None:
    with migrated_memory_repository() as (_candidate, factory, _engine):
        _subject, _relationship, conversation = seed_conversation(factory, number=602)
        repository = PostgresOwnerDataLifecycleRepository(factory)
        command = _command(
            OwnerDataDeleteScope.CONVERSATION_ONLY,
            conversation_id=conversation,
            key="delete-replay",
        )
        first = repository.hide_owner_data(command)
        replay = repository.hide_owner_data(command)
        assert replay.marker_id == first.marker_id

        conflict = _command(
            OwnerDataDeleteScope.CONVERSATION_AND_DERIVED_MEMORY,
            conversation_id=conversation,
            key="delete-replay",
        )
        try:
            repository.hide_owner_data(conflict)
        except Exception as error:
            assert getattr(error, "code", None) == "idempotency_conflict"
        else:
            raise AssertionError("scope conflict must be rejected")


def test_relationship_private_data_hides_relationship_and_conversation() -> None:
    with migrated_memory_repository() as (_candidate, factory, _engine):
        _subject, relationship, conversation = seed_conversation(factory, number=603)
        repository = PostgresOwnerDataLifecycleRepository(factory)
        marker = repository.hide_owner_data(
            _command(
                OwnerDataDeleteScope.RELATIONSHIP_PRIVATE_DATA,
                relationship_id=relationship,
                key="delete-relationship",
            )
        )
        assert marker.affected.relationships == 1
        with factory() as session:
            row = session.get(ConversationRecord, conversation)
            assert row is not None and row.status == "hidden"


def test_locate_returns_only_marker_targeted_run_namespaces() -> None:
    with migrated_memory_repository() as (_candidate, factory, _engine):
        subject, relationship, conversation = seed_conversation(factory, number=604)
        task_id = UUID("96000000-0000-4000-8000-000000000604")
        with factory() as session:
            session.add(
                ReviewTaskRecord(
                    task_id=task_id,
                    run_id="owner-run-604",
                    task_kind="recent_form_review",
                    schema_version="2.0",
                    owner_id="memory-owner",
                    idempotency_key="run-604",
                    request_fingerprint="a" * 64,
                    request_payload={},
                    conversation_id=conversation,
                    relationship_id=relationship,
                    player_subject_id=subject,
                    relationship_role="self",
                    status="failed",
                    worker_id="worker-604",
                    created_at=BASE,
                    updated_at=BASE + timedelta(minutes=1),
                    claimed_at=BASE + timedelta(minutes=1),
                    finished_at=BASE + timedelta(minutes=2),
                    lease_generation=0,
                    checkpoint_sequence=0,
                    terminal_reason="worker_execution_failed",
                    report_available=False,
                )
            )
            session.commit()

        repository = PostgresOwnerDataLifecycleRepository(factory)
        marker = repository.hide_owner_data(
            _command(
                OwnerDataDeleteScope.CONVERSATION_ONLY,
                conversation_id=conversation,
                key="delete-run-604",
            )
        )

        references = repository.locate(marker)

        assert tuple(reference.run_id for reference in references) == ("owner-run-604",)
        assert references[0].owner_id == "memory-owner"
        assert references[0].conversation_id == conversation
        assert references[0].relationship_id == relationship
