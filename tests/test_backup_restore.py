from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from app.harness import ArtifactKind, FileRunStore, HarnessConfig, RunManifest
from app.lifecycle.backup import (
    BackupRestoreError,
    BackupRestoreService,
    IdempotentDeletionMarkerReplayer,
    OwnerRunArtifactTraceCleaner,
    OwnerRunReference,
    build_backup_manifest,
)
from app.lifecycle.models import (
    OwnerDataAffectedCounts,
    OwnerDataDeleteScope,
    OwnerDataDeletionMarker,
    OwnerDataDeletionStatus,
)
from app.tasks.deletion import FileRunDataCleaner


NOW = datetime(2026, 8, 24, 6, 0, tzinfo=timezone.utc)
MARKER_ID = UUID("99400000-0000-4000-8000-000000000001")
MARKER_ID_2 = UUID("99400000-0000-4000-8000-000000000002")
CONVERSATION_ID = UUID("99400000-0000-4000-8000-000000000010")


def marker(marker_id: UUID = MARKER_ID) -> OwnerDataDeletionMarker:
    return OwnerDataDeletionMarker(
        marker_id=marker_id,
        owner_id="owner-a",
        idempotency_key=f"erase-{marker_id.int}",
        scope=OwnerDataDeleteScope.CONVERSATION_ONLY,
        conversation_id=CONVERSATION_ID,
        affected=OwnerDataAffectedCounts(conversations=1, messages=2),
        status=OwnerDataDeletionStatus.COMPLETE,
        created_at=NOW,
        updated_at=NOW,
        completed_at=NOW,
    )


class Replayer:
    def __init__(self, *, fail_on: UUID | None = None, fail_rollback: bool = False) -> None:
        self.fail_on = fail_on
        self.fail_rollback = fail_rollback
        self.replayed: list[UUID] = []
        self.rollbacks: list[tuple[UUID, ...]] = []

    def replay(self, value) -> None:
        if value.marker_id == self.fail_on:
            raise RuntimeError("private replay detail")
        self.replayed.append(value.marker_id)

    def rollback(self, marker_ids: tuple[UUID, ...]) -> None:
        self.rollbacks.append(marker_ids)
        if self.fail_rollback:
            raise RuntimeError("private rollback detail")


def test_manifest_is_deterministic_metadata_and_requires_external_encryption() -> None:
    manifest = build_backup_manifest(
        backup_id="backup_20260824",
        created_at=NOW,
        source_schema="schema_1_6",
        deletion_markers=(marker(MARKER_ID_2), marker(MARKER_ID)),
    )

    assert manifest.encryption == "external_kms_required"
    assert tuple(row.marker_id for row in manifest.deletion_markers) == (MARKER_ID, MARKER_ID_2)
    assert len(manifest.deletion_marker_digest) == 64
    assert "private replay detail" not in manifest.model_dump_json()


def test_restore_replays_markers_before_ready() -> None:
    replayer = Replayer()
    service = BackupRestoreService(replayer=replayer)
    manifest = build_backup_manifest(
        backup_id="backup_ready",
        created_at=NOW,
        source_schema="schema_1_6",
        deletion_markers=(marker(),),
    )

    result = service.restore(manifest)

    assert result.ready is True
    assert result.replayed_marker_ids == (MARKER_ID,)
    assert replayer.rollbacks == []


def test_restore_failure_compensates_prior_replays_and_never_returns_ready() -> None:
    replayer = Replayer(fail_on=MARKER_ID_2)
    service = BackupRestoreService(replayer=replayer)
    manifest = build_backup_manifest(
        backup_id="backup_partial",
        created_at=NOW,
        source_schema="schema_1_6",
        deletion_markers=(marker(), marker(MARKER_ID_2)),
    )

    with pytest.raises(BackupRestoreError, match="restore_erase_replay_failed"):
        service.restore(manifest)

    assert replayer.replayed == [MARKER_ID]
    assert replayer.rollbacks == [(MARKER_ID,)]


def test_restore_compensation_failure_and_readiness_failure_are_fail_closed() -> None:
    manifest = build_backup_manifest(
        backup_id="backup_not_ready",
        created_at=NOW,
        source_schema="schema_1_6",
        deletion_markers=(marker(),),
    )
    replayer = Replayer(fail_rollback=True)
    service = BackupRestoreService(replayer=replayer, ready_probe=lambda: False)

    with pytest.raises(BackupRestoreError, match="restore_compensation_failed"):
        service.restore(manifest)

    assert replayer.rollbacks == [(MARKER_ID,)]


def test_duplicate_marker_ids_are_rejected_before_restore() -> None:
    with pytest.raises(BackupRestoreError, match="backup_manifest_invalid"):
        build_backup_manifest(
            backup_id="backup_duplicate",
            created_at=NOW,
            source_schema="schema_1_6",
            deletion_markers=(marker(), marker()),
        )


def test_restore_rejects_a_tampered_marker_digest_before_replay() -> None:
    replayer = Replayer()
    manifest = build_backup_manifest(
        backup_id="backup_tampered",
        created_at=NOW,
        source_schema="schema_1_6",
        deletion_markers=(marker(),),
    ).model_copy(update={"deletion_marker_digest": "0" * 64})

    with pytest.raises(BackupRestoreError, match="backup_manifest_invalid"):
        BackupRestoreService(replayer=replayer).restore(manifest)

    assert replayer.replayed == []
    assert replayer.rollbacks == []


def test_restore_marker_replay_is_idempotent_across_repeated_drills() -> None:
    delegate = Replayer()
    replayer = IdempotentDeletionMarkerReplayer(delegate=delegate)
    manifest = build_backup_manifest(
        backup_id="backup_idempotent",
        created_at=NOW,
        source_schema="schema_1_6",
        deletion_markers=(marker(),),
    )
    service = BackupRestoreService(replayer=replayer)

    first = service.restore(manifest)
    second = service.restore(manifest)

    assert first.replayed_marker_ids == second.replayed_marker_ids == (MARKER_ID,)
    assert delegate.replayed == [MARKER_ID]


def test_idempotent_replayer_does_not_rollback_an_earlier_successful_restore() -> None:
    delegate = Replayer()
    replayer = IdempotentDeletionMarkerReplayer(delegate=delegate)
    manifest = build_backup_manifest(
        backup_id="backup_readiness_retry",
        created_at=NOW,
        source_schema="schema_1_6",
        deletion_markers=(marker(),),
    )
    BackupRestoreService(replayer=replayer).restore(manifest)

    with pytest.raises(BackupRestoreError, match="restore_not_ready"):
        BackupRestoreService(
            replayer=replayer,
            ready_probe=lambda: False,
        ).restore(manifest)

    assert delegate.replayed == [MARKER_ID]
    assert delegate.rollbacks == []


def test_owner_run_cleaner_deletes_only_marker_targeted_artifact_trace_runs() -> None:
    class Locator:
        def locate(self, value):
            assert value.marker_id == MARKER_ID
            return (
                OwnerRunReference(
                    owner_id="owner-a",
                    run_id="run-conversation",
                    conversation_id=value.conversation_id,
                    relationship_id=None,
                ),
            )

    class RunCleaner:
        def __init__(self):
            self.calls = []

        def cleanup(self, run_id: str) -> bool:
            self.calls.append(run_id)
            return True

    run_cleaner = RunCleaner()
    cleaner = OwnerRunArtifactTraceCleaner(
        locator=Locator(),
        run_cleaner=run_cleaner,
    )

    cleaner.cleanup(marker())

    assert run_cleaner.calls == ["run-conversation"]


def test_owner_run_cleaner_fails_closed_on_locator_owner_mismatch() -> None:
    class Locator:
        def locate(self, _value):
            return (
                OwnerRunReference(
                    owner_id="different-owner",
                    run_id="run-wrong-owner",
                    conversation_id=CONVERSATION_ID,
                    relationship_id=None,
                ),
            )

    class RunCleaner:
        def cleanup(self, _run_id: str) -> bool:
            pytest.fail("wrong-owner run must never be deleted")

    with pytest.raises(RuntimeError, match="owner_run_reference_invalid"):
        OwnerRunArtifactTraceCleaner(
            locator=Locator(),
            run_cleaner=RunCleaner(),
        ).cleanup(marker())


def test_owner_run_cleaner_removes_the_existing_artifact_trace_run_directory(tmp_path) -> None:
    run_id = "run-artifact-trace"
    store = FileRunStore(tmp_path, run_id)
    store.create_run(RunManifest.new(run_id, HarnessConfig()))
    artifact = store.write_artifact(
        kind=ArtifactKind.FINAL_REPORT,
        relative_path="final-report.txt",
        content="safe fixture",
        schema_version="1.0",
        producer="test",
    )
    trace_path = store.run_directory / "runtime_trace.json"
    trace_path.write_text('{"fixture":true}\n', encoding="utf-8")

    class Locator:
        def locate(self, value):
            return (
                OwnerRunReference(
                    owner_id=value.owner_id,
                    run_id=run_id,
                    conversation_id=value.conversation_id,
                    relationship_id=None,
                ),
            )

    OwnerRunArtifactTraceCleaner(
        locator=Locator(),
        run_cleaner=FileRunDataCleaner(tmp_path),
    ).cleanup(marker())

    assert artifact["path"] == "final-report.txt"
    assert not store.run_directory.exists()
