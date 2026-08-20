from app.persistence.conversation_records import ConversationMessageRecord


def test_assistant_source_run_has_partial_unique_metadata_index() -> None:
    indexes = {index.name: index for index in ConversationMessageRecord.__table__.indexes}

    index = indexes["uq_conversation_messages_assistant_source_run"]
    assert index.unique is True
    assert tuple(column.name for column in index.columns) == (
        "conversation_id",
        "source_run_id",
    )
    assert "role = 'assistant'" in str(index.dialect_options["postgresql"]["where"])
