from datetime import datetime, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.lifecycle.models import (
    OwnerDataAffectedCounts,
    OwnerDataDeleteCommand,
    OwnerDataDeleteScope,
    OwnerDataDeletionMarker,
    OwnerDataDeletionStatus,
    OwnerDataExport,
    OwnerDataExportRecord,
    OwnerDataExportSection,
    OwnerDataPurgeSummary,
    OwnerDataRetentionSummary,
)


NOW = datetime(2026, 8, 21, tzinfo=timezone.utc)
CONVERSATION_ID = UUID("99000000-0000-4000-8000-000000000001")
RELATIONSHIP_ID = UUID("99000000-0000-4000-8000-000000000002")


@pytest.mark.parametrize(
    ("scope", "conversation_id", "relationship_id"),
    (
        (OwnerDataDeleteScope.CONVERSATION_ONLY, CONVERSATION_ID, None),
        (
            OwnerDataDeleteScope.CONVERSATION_AND_DERIVED_MEMORY,
            CONVERSATION_ID,
            None,
        ),
        (
            OwnerDataDeleteScope.RELATIONSHIP_PRIVATE_DATA,
            None,
            RELATIONSHIP_ID,
        ),
    ),
)
def test_delete_command_accepts_exact_target_shape(
    scope, conversation_id, relationship_id
) -> None:
    command = OwnerDataDeleteCommand(
        owner_id="owner-a",
        idempotency_key="delete-request-1",
        scope=scope,
        conversation_id=conversation_id,
        relationship_id=relationship_id,
        requested_at=NOW,
    )

    assert command.scope is scope


@pytest.mark.parametrize(
    ("scope", "conversation_id", "relationship_id"),
    (
        (OwnerDataDeleteScope.CONVERSATION_ONLY, None, None),
        (OwnerDataDeleteScope.CONVERSATION_ONLY, CONVERSATION_ID, RELATIONSHIP_ID),
        (OwnerDataDeleteScope.RELATIONSHIP_PRIVATE_DATA, CONVERSATION_ID, None),
    ),
)
def test_delete_command_rejects_ambiguous_target_shape(
    scope, conversation_id, relationship_id
) -> None:
    with pytest.raises(ValidationError):
        OwnerDataDeleteCommand(
            owner_id="owner-a",
            idempotency_key="delete-request-1",
            scope=scope,
            conversation_id=conversation_id,
            relationship_id=relationship_id,
            requested_at=NOW,
        )


def test_export_has_fixed_sections_counts_and_no_unknown_fields() -> None:
    record = OwnerDataExportRecord(
        record_kind="message",
        record_id=CONVERSATION_ID,
        conversation_id=CONVERSATION_ID,
        relationship_id=RELATIONSHIP_ID,
        relationship_role="self",
        status="visible",
        data={"role": "user", "content": "review this game"},
    )
    export = OwnerDataExport(
        owner_id="owner-a",
        generated_at=NOW,
        policy_version="owner-data-export-v1",
        sections=(OwnerDataExportSection(name="messages", records=(record,)),),
        total_record_count=1,
    )

    assert export.schema_version == "1.0"
    assert export.total_record_count == 1
    assert "puuid" not in export.model_dump_json().lower()
    with pytest.raises(ValidationError):
        OwnerDataExportRecord(
            record_kind="message",
            record_id=CONVERSATION_ID,
            status="visible",
            data={},
            secret="forbidden",
        )


def test_export_rejects_mismatched_total_and_oversized_section() -> None:
    with pytest.raises(ValidationError):
        OwnerDataExport(
            owner_id="owner-a",
            generated_at=NOW,
            policy_version="owner-data-export-v1",
            sections=(OwnerDataExportSection(name="messages", records=()),),
            total_record_count=1,
        )

    records = tuple(
        OwnerDataExportRecord(
            record_kind="message",
            record_id=UUID(f"99000000-0000-4000-8000-{index:012d}"),
            status="visible",
            data={"content": "x"},
        )
        for index in range(501)
    )
    with pytest.raises(ValidationError):
        OwnerDataExportSection(name="messages", records=records)


def test_marker_counts_status_and_safe_reason_are_consistent() -> None:
    marker = OwnerDataDeletionMarker(
        marker_id=UUID("99000000-0000-4000-8000-000000000003"),
        owner_id="owner-a",
        idempotency_key="delete-request-1",
        scope=OwnerDataDeleteScope.CONVERSATION_ONLY,
        conversation_id=CONVERSATION_ID,
        affected=OwnerDataAffectedCounts(conversations=1, messages=2),
        status=OwnerDataDeletionStatus.CLEANUP_PENDING,
        safe_reason="cleanup_failed",
        created_at=NOW,
        updated_at=NOW,
    )

    assert marker.cleanup_pending
    with pytest.raises(ValidationError):
        marker.model_copy(update={"status": "complete"}, deep=True).model_validate(
            {
                **marker.model_dump(mode="python"),
                "status": "complete",
                "safe_reason": "cleanup_failed",
                "completed_at": NOW,
            }
        )


def test_retention_and_purge_summaries_are_bounded_and_aware() -> None:
    retention = OwnerDataRetentionSummary(
        evaluated_at=NOW,
        batch_size=100,
        expired_candidates=2,
        hidden_records=5,
    )
    purge = OwnerDataPurgeSummary(
        evaluated_at=NOW,
        batch_size=100,
        purged_records=4,
        blocked_records=1,
    )

    assert retention.hidden_records == 5
    assert purge.blocked_records == 1
    with pytest.raises(ValidationError):
        OwnerDataRetentionSummary(
            evaluated_at=NOW.replace(tzinfo=None),
            batch_size=100,
            expired_candidates=0,
            hidden_records=0,
        )
