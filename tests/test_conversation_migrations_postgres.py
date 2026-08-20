from __future__ import annotations

import io
import os
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.persistence.conversation_records import (
    ConversationMessageRecord,
    ConversationRecord,
)
from app.persistence.database import Base


ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_ENV = "RIFTCOACH_TEST_DATABASE_URL"


def _alembic_config() -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    return config


def test_conversation_revision_fits_alembic_version_column() -> None:
    head = ScriptDirectory.from_config(_alembic_config()).get_current_head()

    assert head is not None
    assert len(head) <= 32


def test_conversation_metadata_defines_expected_schema() -> None:
    assert ConversationRecord.__table__.metadata is Base.metadata
    assert ConversationMessageRecord.__table__.metadata is Base.metadata
    assert {"conversations", "conversation_messages"} <= set(Base.metadata.tables)

    conversation_constraints = {
        constraint.name for constraint in ConversationRecord.__table__.constraints
    }
    message_constraints = {
        constraint.name
        for constraint in ConversationMessageRecord.__table__.constraints
    }
    conversation_indexes = {
        index.name for index in ConversationRecord.__table__.indexes
    }
    message_indexes = {
        index.name for index in ConversationMessageRecord.__table__.indexes
    }

    assert {
        "pk_conversations",
        "uq_conversations_owner_id_idempotency_key",
        "uq_conversations_identity",
        "fk_conversations_relationship_identity",
        "ck_conversations_schema_version_allowed",
        "ck_conversations_owner_id_bounded",
        "ck_conversations_idempotency_key_bounded",
        "ck_conversations_request_fingerprint_format",
        "ck_conversations_relationship_role_allowed",
        "ck_conversations_status_allowed",
        "ck_conversations_next_message_sequence_positive",
        "ck_conversations_hidden_status_shape",
        "ck_conversations_timestamp_order",
    } <= conversation_constraints
    assert {
        "pk_conversation_messages",
        "uq_conversation_messages_conversation_sequence",
        "fk_conversation_messages_conversation_identity",
        "ck_conversation_messages_relationship_role_allowed",
        "ck_conversation_messages_sequence_no_positive",
        "ck_conversation_messages_role_allowed",
        "ck_conversation_messages_content_bounded",
        "ck_conversation_messages_content_control_characters_allowed",
        "ck_conversation_messages_content_sha256_format",
        "ck_conversation_messages_user_source_empty",
        "ck_conversation_messages_source_run_id_bounded",
        "ck_conversation_messages_assistant_source_required",
        "ck_conversation_messages_timestamp_order",
    } <= message_constraints
    assert {
        "ix_conversations_relationship_id",
        "ix_conversations_player_subject_id",
        "ix_conversations_owner_history",
    } <= conversation_indexes
    assert {
        "ix_conversation_messages_relationship_id",
        "ix_conversation_messages_player_subject_id",
        "ix_conversation_messages_source_task_id",
        "ix_conversation_messages_source_run_id",
    } <= message_indexes

    for column_name in (
        "created_at",
        "updated_at",
        "last_message_at",
        "hidden_at",
    ):
        assert ConversationRecord.__table__.c[column_name].type.timezone is True
    for column_name in ("created_at", "hidden_at"):
        assert (
            ConversationMessageRecord.__table__.c[column_name].type.timezone
            is True
        )


def test_conversation_offline_migration_has_stable_names_and_triggers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://riftcoach:offline@localhost:5432/riftcoach",
    )
    output = io.StringIO()
    config = Config(str(ROOT / "alembic.ini"), output_buffer=output)
    config.set_main_option("script_location", str(ROOT / "migrations"))

    command.upgrade(config, "head", sql=True)
    sql = output.getvalue()

    assert "CONSTRAINT ck_conversations_hidden_status_shape" in sql
    assert "CONSTRAINT ck_conversation_messages_content_bounded" in sql
    assert (
        "CONSTRAINT ck_conversation_messages_content_control_characters_allowed"
        in sql
    )
    assert "CREATE FUNCTION riftcoach_guard_conversation_update" in sql
    assert "CREATE FUNCTION riftcoach_guard_conversation_message_update" in sql
    assert "CREATE TRIGGER trg_conversations_guard_update" in sql
    assert "CREATE TRIGGER trg_conversation_messages_guard_update" in sql
    assert "ck_conversations_ck_conversations" not in sql
    assert "ck_conversation_messages_ck_conversation_messages" not in sql


@pytest.fixture()
def postgres_migration_database(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    url = os.getenv(TEST_DATABASE_ENV)
    if not url:
        pytest.skip(
            f"{TEST_DATABASE_ENV} is not configured; real PostgreSQL "
            "conversation migration evidence runs in CI"
        )
    if not url.startswith("postgresql+psycopg://"):
        pytest.fail(f"{TEST_DATABASE_ENV} must use postgresql+psycopg")

    monkeypatch.setenv("DATABASE_URL", url)
    config = _alembic_config()
    command.downgrade(config, "base")
    try:
        yield url
    finally:
        command.downgrade(config, "base")


def test_conversation_migration_creates_tables_constraints_and_triggers(
    postgres_migration_database: str,
) -> None:
    config = _alembic_config()
    command.upgrade(config, "head")
    engine = sa.create_engine(postgres_migration_database)
    try:
        inspector = sa.inspect(engine)
        assert {
            "owner_player_relationships",
            "conversations",
            "conversation_messages",
        } <= set(inspector.get_table_names())

        conversation_unique_names = {
            item["name"]
            for item in inspector.get_unique_constraints("conversations")
        }
        conversation_check_names = {
            item["name"]
            for item in inspector.get_check_constraints("conversations")
        }
        conversation_fk_names = {
            item["name"]
            for item in inspector.get_foreign_keys("conversations")
        }
        conversation_index_names = {
            item["name"] for item in inspector.get_indexes("conversations")
        }
        message_unique_names = {
            item["name"]
            for item in inspector.get_unique_constraints("conversation_messages")
        }
        message_check_names = {
            item["name"]
            for item in inspector.get_check_constraints("conversation_messages")
        }
        message_foreign_keys = inspector.get_foreign_keys(
            "conversation_messages"
        )
        message_index_names = {
            item["name"]
            for item in inspector.get_indexes("conversation_messages")
        }

        assert {
            "uq_conversations_owner_id_idempotency_key",
            "uq_conversations_identity",
        } <= conversation_unique_names
        assert {
            "ck_conversations_hidden_status_shape",
            "ck_conversations_next_message_sequence_positive",
        } <= conversation_check_names
        assert conversation_fk_names == {
            "fk_conversations_relationship_identity"
        }
        assert {
            "ix_conversations_relationship_id",
            "ix_conversations_player_subject_id",
            "ix_conversations_owner_history",
        } <= conversation_index_names

        assert message_unique_names == {
            "uq_conversation_messages_conversation_sequence"
        }
        assert {
            "ck_conversation_messages_content_bounded",
            "ck_conversation_messages_content_control_characters_allowed",
            "ck_conversation_messages_content_sha256_format",
            "ck_conversation_messages_user_source_empty",
            "ck_conversation_messages_assistant_source_required",
        } <= message_check_names
        assert {
            item["name"] for item in message_foreign_keys
        } == {"fk_conversation_messages_conversation_identity"}
        assert all(
            item["referred_table"] != "review_tasks"
            for item in message_foreign_keys
        )
        assert {
            "ix_conversation_messages_relationship_id",
            "ix_conversation_messages_player_subject_id",
            "ix_conversation_messages_source_task_id",
            "ix_conversation_messages_source_run_id",
        } <= message_index_names

        with engine.connect() as connection:
            trigger_names = {
                row.trigger_name
                for row in connection.execute(
                    sa.text(
                        "SELECT tgname AS trigger_name "
                        "FROM pg_trigger "
                        "WHERE NOT tgisinternal "
                        "AND tgrelid IN ("
                        "'conversations'::regclass, "
                        "'conversation_messages'::regclass"
                        ")"
                    )
                )
            }
        assert trigger_names == {
            "trg_conversations_guard_update",
            "trg_conversation_messages_guard_update",
        }
    finally:
        engine.dispose()


def _seed_relationship_and_conversation(
    connection: sa.Connection,
) -> dict[str, object]:
    values: dict[str, object] = {
        "player_subject_id": uuid.uuid4(),
        "relationship_id": uuid.uuid4(),
        "conversation_id": uuid.uuid4(),
        "owner_id": "owner-migration",
    }
    connection.execute(
        sa.text(
            "INSERT INTO player_subjects ("
            "player_subject_id, game, puuid, current_routing_region"
            ") VALUES ("
            ":player_subject_id, 'lol', :puuid, 'asia'"
            ")"
        ),
        {**values, "puuid": f"PUUID_{values['player_subject_id']}"},
    )
    connection.execute(
        sa.text(
            "INSERT INTO owner_player_relationships ("
            "relationship_id, owner_id, player_subject_id, "
            "relationship_role, verification_status"
            ") VALUES ("
            ":relationship_id, :owner_id, :player_subject_id, "
            "'self', 'unverified_claim'"
            ")"
        ),
        values,
    )
    connection.execute(
        sa.text(
            "INSERT INTO conversations ("
            "conversation_id, owner_id, relationship_id, player_subject_id, "
            "relationship_role, idempotency_key, request_fingerprint"
            ") VALUES ("
            ":conversation_id, :owner_id, :relationship_id, "
            ":player_subject_id, 'self', 'migration-key', :fingerprint"
            ")"
        ),
        {**values, "fingerprint": "a" * 64},
    )
    return values


def test_conversation_triggers_reject_rebind_and_lifecycle_reversal(
    postgres_migration_database: str,
) -> None:
    config = _alembic_config()
    command.upgrade(config, "head")
    engine = sa.create_engine(postgres_migration_database)
    try:
        with engine.begin() as connection:
            values = _seed_relationship_and_conversation(connection)

        with pytest.raises(sa.exc.IntegrityError):
            with engine.begin() as connection:
                connection.execute(
                    sa.text(
                        "UPDATE conversations SET owner_id = 'other-owner' "
                        "WHERE conversation_id = :conversation_id"
                    ),
                    values,
                )

        with engine.begin() as connection:
            connection.execute(
                sa.text(
                    "UPDATE conversations SET status = 'archived' "
                    "WHERE conversation_id = :conversation_id"
                ),
                values,
            )
        with pytest.raises(sa.exc.IntegrityError):
            with engine.begin() as connection:
                connection.execute(
                    sa.text(
                        "UPDATE conversations SET status = 'active' "
                        "WHERE conversation_id = :conversation_id"
                    ),
                    values,
                )

        with engine.begin() as connection:
            connection.execute(
                sa.text(
                    "UPDATE conversations SET status = 'hidden', "
                    "hidden_at = now(), updated_at = now() "
                    "WHERE conversation_id = :conversation_id"
                ),
                values,
            )
        with pytest.raises(sa.exc.IntegrityError):
            with engine.begin() as connection:
                connection.execute(
                    sa.text(
                        "UPDATE conversations SET status = 'archived', "
                        "hidden_at = NULL WHERE conversation_id = :conversation_id"
                    ),
                    values,
                )
    finally:
        engine.dispose()


def test_message_trigger_rejects_immutable_content_update(
    postgres_migration_database: str,
) -> None:
    config = _alembic_config()
    command.upgrade(config, "head")
    engine = sa.create_engine(postgres_migration_database)
    try:
        with engine.begin() as connection:
            values = _seed_relationship_and_conversation(connection)
            values["message_id"] = uuid.uuid4()
            connection.execute(
                sa.text(
                    "INSERT INTO conversation_messages ("
                    "message_id, conversation_id, owner_id, relationship_id, "
                    "player_subject_id, relationship_role, sequence_no, role, "
                    "content, content_sha256"
                    ") VALUES ("
                    ":message_id, :conversation_id, :owner_id, :relationship_id, "
                    ":player_subject_id, 'self', 1, 'user', 'hello', :digest"
                    ")"
                ),
                {
                    **values,
                    "digest": (
                        "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e"
                        "73043362938b9824"
                    ),
                },
            )

        with pytest.raises(sa.exc.IntegrityError):
            with engine.begin() as connection:
                connection.execute(
                    sa.text(
                        "UPDATE conversation_messages SET content = 'changed' "
                        "WHERE message_id = :message_id"
                    ),
                    values,
                )
    finally:
        engine.dispose()


def test_message_checks_reject_unproven_assistant_direct_insert(
    postgres_migration_database: str,
) -> None:
    config = _alembic_config()
    command.upgrade(config, "head")
    engine = sa.create_engine(postgres_migration_database)
    try:
        with engine.begin() as connection:
            values = _seed_relationship_and_conversation(connection)

        with pytest.raises(sa.exc.IntegrityError):
            with engine.begin() as connection:
                connection.execute(
                    sa.text(
                        "INSERT INTO conversation_messages ("
                        "message_id, conversation_id, owner_id, "
                        "relationship_id, player_subject_id, "
                        "relationship_role, sequence_no, role, content, "
                        "content_sha256"
                        ") VALUES ("
                        ":message_id, :conversation_id, :owner_id, "
                        ":relationship_id, :player_subject_id, 'self', "
                        "1, 'assistant', 'unproven', :digest"
                        ")"
                    ),
                    {
                        **values,
                        "message_id": uuid.uuid4(),
                        "digest": "a" * 64,
                    },
                )
    finally:
        engine.dispose()


def test_message_source_checks_allow_proven_assistant_and_reject_user_source(
    postgres_migration_database: str,
) -> None:
    config = _alembic_config()
    command.upgrade(config, "head")
    engine = sa.create_engine(postgres_migration_database)
    statement = sa.text(
        "INSERT INTO conversation_messages ("
        "message_id, conversation_id, owner_id, relationship_id, "
        "player_subject_id, relationship_role, sequence_no, role, content, "
        "content_sha256, source_task_id, source_run_id"
        ") VALUES ("
        ":message_id, :conversation_id, :owner_id, :relationship_id, "
        ":player_subject_id, 'self', :sequence_no, :role, :content, "
        ":digest, :source_task_id, :source_run_id"
        ")"
    )
    try:
        with engine.begin() as connection:
            values = _seed_relationship_and_conversation(connection)
            connection.execute(
                statement,
                {
                    **values,
                    "message_id": uuid.uuid4(),
                    "sequence_no": 1,
                    "role": "assistant",
                    "content": "proven terminal",
                    "digest": "d" * 64,
                    "source_task_id": None,
                    "source_run_id": "review_run_1",
                },
            )

        with pytest.raises(sa.exc.IntegrityError):
            with engine.begin() as connection:
                connection.execute(
                    statement,
                    {
                        **values,
                        "message_id": uuid.uuid4(),
                        "sequence_no": 2,
                        "role": "user",
                        "content": "forged source",
                        "digest": "e" * 64,
                        "source_task_id": uuid.uuid4(),
                        "source_run_id": "forged_run",
                    },
                )
    finally:
        engine.dispose()


def test_message_check_rejects_forbidden_controls_but_allows_text_whitespace(
    postgres_migration_database: str,
) -> None:
    config = _alembic_config()
    command.upgrade(config, "head")
    engine = sa.create_engine(postgres_migration_database)
    insert = sa.text(
        "INSERT INTO conversation_messages ("
        "message_id, conversation_id, owner_id, relationship_id, "
        "player_subject_id, relationship_role, sequence_no, role, "
        "content, content_sha256"
        ") VALUES ("
        ":message_id, :conversation_id, :owner_id, :relationship_id, "
        ":player_subject_id, 'self', :sequence_no, 'user', :content, :digest"
        ")"
    )
    try:
        with engine.begin() as connection:
            values = _seed_relationship_and_conversation(connection)
            connection.execute(
                insert,
                {
                    **values,
                    "message_id": uuid.uuid4(),
                    "sequence_no": 1,
                    "content": "tab\tline\ncarriage\rreturn",
                    "digest": "b" * 64,
                },
            )

        for forbidden in ("\x01", "\x0b", "\x7f", "\x85"):
            with pytest.raises(sa.exc.IntegrityError):
                with engine.begin() as connection:
                    connection.execute(
                        insert,
                        {
                            **values,
                            "message_id": uuid.uuid4(),
                            "sequence_no": 2,
                            "content": f"before{forbidden}after",
                            "digest": "c" * 64,
                        },
                    )
    finally:
        engine.dispose()


def test_conversation_migration_downgrades_to_player_identity_and_reupgrades(
    postgres_migration_database: str,
) -> None:
    config = _alembic_config()
    command.upgrade(config, "head")
    command.downgrade(config, "0002_player_identity_link")

    engine = sa.create_engine(postgres_migration_database)
    try:
        tables = set(sa.inspect(engine).get_table_names())
        assert "owner_player_relationships" in tables
        assert "conversations" not in tables
        assert "conversation_messages" not in tables
        with engine.connect() as connection:
            function_count = connection.scalar(
                sa.text(
                    "SELECT count(*) FROM pg_proc WHERE proname IN ("
                    "'riftcoach_guard_conversation_update', "
                    "'riftcoach_guard_conversation_message_update'"
                    ")"
                )
            )
        assert function_count == 0
    finally:
        engine.dispose()

    command.upgrade(config, "head")
    engine = sa.create_engine(postgres_migration_database)
    try:
        assert {"conversations", "conversation_messages"} <= set(
            sa.inspect(engine).get_table_names()
        )
    finally:
        engine.dispose()
