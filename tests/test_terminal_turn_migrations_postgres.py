import sqlalchemy as sa

from tests.memory_candidate_postgres_support import migrated_memory_repository


def test_0008_adds_unique_terminal_assistant_source_index() -> None:
    with migrated_memory_repository() as (_repository, _factory, engine):
        indexes = {
            row["name"]: row
            for row in sa.inspect(engine).get_indexes("conversation_messages")
        }

        assert indexes["uq_conversation_messages_assistant_source_run"]["unique"] is True
        predicate = str(
            indexes["uq_conversation_messages_assistant_source_run"]
            .get("dialect_options", {})
            .get("postgresql_where", "")
        )
        assert "assistant" in predicate
