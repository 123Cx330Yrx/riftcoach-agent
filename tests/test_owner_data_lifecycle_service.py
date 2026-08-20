from datetime import datetime, timezone
from uuid import UUID

import pytest

from app.lifecycle.models import (
    OwnerDataAffectedCounts,
    OwnerDataDeleteCommand,
    OwnerDataDeleteScope,
    OwnerDataDeletionMarker,
    OwnerDataDeletionStatus,
    OwnerDataExport,
    OwnerDataExportSection,
    OwnerDataPurgeSummary,
    OwnerDataRetentionSummary,
)
from app.lifecycle.service import (
    OwnerDataLifecycleError,
    OwnerDataLifecycleService,
)


NOW = datetime(2026, 8, 21, tzinfo=timezone.utc)
MARKER_ID = UUID("99100000-0000-4000-8000-000000000001")
CONVERSATION_ID = UUID("99100000-0000-4000-8000-000000000002")


def command() -> OwnerDataDeleteCommand:
    return OwnerDataDeleteCommand(
        owner_id="owner-a",
        idempotency_key="delete-1",
        scope=OwnerDataDeleteScope.CONVERSATION_ONLY,
        conversation_id=CONVERSATION_ID,
        requested_at=NOW,
    )


def marker(
    *, status: OwnerDataDeletionStatus = OwnerDataDeletionStatus.CLEANUP_PENDING
) -> OwnerDataDeletionMarker:
    return OwnerDataDeletionMarker(
        marker_id=MARKER_ID,
        owner_id="owner-a",
        idempotency_key="delete-1",
        scope=OwnerDataDeleteScope.CONVERSATION_ONLY,
        conversation_id=CONVERSATION_ID,
        affected=OwnerDataAffectedCounts(conversations=1, messages=2),
        status=status,
        safe_reason=None,
        created_at=NOW,
        updated_at=NOW,
        completed_at=NOW if status is OwnerDataDeletionStatus.COMPLETE else None,
    )


class Repository:
    def __init__(self) -> None:
        self.current = marker()
        self.complete_calls = []
        self.failed_calls = []

    def export_owner_data(self, *, owner_id, generated_at, limit_per_section):
        return OwnerDataExport(
            owner_id=owner_id,
            generated_at=generated_at,
            policy_version="owner-data-export-v1",
            sections=(OwnerDataExportSection(name="messages", records=()),),
            total_record_count=0,
        )

    def hide_owner_data(self, value):
        assert value == command()
        return self.current

    def get_deletion_marker(self, *, owner_id, marker_id):
        if owner_id == "owner-a" and marker_id == MARKER_ID:
            return self.current
        return None

    def complete_deletion(self, *, owner_id, marker_id, completed_at):
        self.complete_calls.append((owner_id, marker_id, completed_at))
        self.current = marker(status=OwnerDataDeletionStatus.COMPLETE)
        return self.current

    def mark_cleanup_failed(self, *, owner_id, marker_id, safe_reason, updated_at):
        self.failed_calls.append((owner_id, marker_id, safe_reason, updated_at))
        self.current = self.current.model_copy(
            update={"safe_reason": safe_reason, "updated_at": updated_at}
        )
        return self.current

    def apply_retention(self, *, evaluated_at, batch_size):
        return OwnerDataRetentionSummary(
            evaluated_at=evaluated_at,
            batch_size=batch_size,
            expired_candidates=1,
            hidden_records=2,
        )

    def purge_hidden(self, *, evaluated_at, batch_size):
        return OwnerDataPurgeSummary(
            evaluated_at=evaluated_at,
            batch_size=batch_size,
            purged_records=2,
            blocked_records=0,
        )


class Cleaner:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls = []

    def cleanup(self, value):
        self.calls.append(value.marker_id)
        if self.fail:
            raise RuntimeError("private path detail")


def test_delete_completes_only_after_cleanup() -> None:
    repository = Repository()
    cleaner = Cleaner()
    service = OwnerDataLifecycleService(
        repository=repository,
        cleaner=cleaner,
        clock=lambda: NOW,
    )

    result = service.delete(command())

    assert result.status is OwnerDataDeletionStatus.COMPLETE
    assert cleaner.calls == [MARKER_ID]
    assert repository.complete_calls == [("owner-a", MARKER_ID, NOW)]


def test_delete_cleanup_failure_keeps_body_free_pending_marker() -> None:
    repository = Repository()
    service = OwnerDataLifecycleService(
        repository=repository,
        cleaner=Cleaner(fail=True),
        clock=lambda: NOW,
    )

    result = service.delete(command())

    assert result.cleanup_pending
    assert result.safe_reason == "cleanup_failed"
    assert "private" not in result.model_dump_json()


def test_replay_of_complete_deletion_does_not_cleanup_again() -> None:
    repository = Repository()
    repository.current = marker(status=OwnerDataDeletionStatus.COMPLETE)
    cleaner = Cleaner()
    service = OwnerDataLifecycleService(repository=repository, cleaner=cleaner)

    result = service.delete(command())

    assert result.status is OwnerDataDeletionStatus.COMPLETE
    assert cleaner.calls == []


def test_retry_is_owner_scoped_and_idempotent() -> None:
    repository = Repository()
    cleaner = Cleaner()
    service = OwnerDataLifecycleService(
        repository=repository,
        cleaner=cleaner,
        clock=lambda: NOW,
    )

    result = service.retry(owner_id="owner-a", marker_id=MARKER_ID)

    assert result.status is OwnerDataDeletionStatus.COMPLETE
    with pytest.raises(OwnerDataLifecycleError) as exc_info:
        service.retry(owner_id="owner-b", marker_id=MARKER_ID)
    assert exc_info.value.code == "deletion_not_found"


def test_export_retention_and_purge_delegate_with_bounded_inputs() -> None:
    service = OwnerDataLifecycleService(
        repository=Repository(),
        cleaner=Cleaner(),
        clock=lambda: NOW,
    )

    assert service.export(owner_id="owner-a").owner_id == "owner-a"
    assert service.apply_retention(batch_size=100).hidden_records == 2
    assert service.purge(batch_size=100).purged_records == 2
    with pytest.raises(TypeError):
        service.apply_retention(batch_size=True)
