from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from app.evidence.ports import EvidenceSnapshotRepositoryError
from app.evidence.storage import (
    EvidenceBundleSnapshot,
    EvidenceSnapshotFreshness,
    ProductRunStateValue,
)
from app.evidence.service import EvidenceProductService, EvidenceProductServiceError
from app.tasks.models import (
    ReviewTaskView,
    TaskPublicationStatus,
    TaskStatus,
)
from app.tasks.service import TaskServiceError
from tests.test_evidence_snapshot_contracts import bundle


NOW = datetime(2026, 8, 23, 9, 5, tzinfo=timezone.utc)
TASK_ID = UUID("94000000-0000-4000-8000-000000000001")
SNAPSHOT_ID = UUID("95000000-0000-4000-8000-000000000001")
RUN_ID = "review_evidence_service_1"


def task(
    status: TaskStatus = TaskStatus.SUCCEEDED,
    *,
    publication: TaskPublicationStatus | None = TaskPublicationStatus.PUBLISHED,
) -> ReviewTaskView:
    terminal = status in {
        TaskStatus.SUCCEEDED,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
    }
    return ReviewTaskView(
        schema_version="1.0",
        task_id=TASK_ID,
        run_id=RUN_ID,
        status=status,
        created_at=NOW - timedelta(minutes=10),
        updated_at=NOW - timedelta(minutes=1),
        claimed_at=NOW - timedelta(minutes=9) if status is not TaskStatus.QUEUED else None,
        finished_at=NOW - timedelta(minutes=1) if terminal else None,
        terminal_reason="quality_gate_passed" if terminal else None,
        publication_status=publication if status is TaskStatus.SUCCEEDED else None,
        report_available=status is TaskStatus.SUCCEEDED,
    )


def snapshot() -> EvidenceBundleSnapshot:
    return EvidenceBundleSnapshot.create(
        snapshot_id=SNAPSHOT_ID,
        task_id=TASK_ID,
        run_id=RUN_ID,
        owner_id="owner-1",
        revision=3,
        refresh_id="refresh-3",
        bundle=bundle(),
        stored_at=NOW - timedelta(minutes=5),
    )


class Tasks:
    def __init__(self, value: ReviewTaskView | Exception) -> None:
        self.value = value
        self.calls: list[tuple[str, str]] = []

    def get_task_by_run_id(self, *, owner_id: str, run_id: str) -> ReviewTaskView:
        self.calls.append((owner_id, run_id))
        if isinstance(self.value, Exception):
            raise self.value
        return self.value


class Snapshots:
    def __init__(self, value: EvidenceBundleSnapshot | None | Exception) -> None:
        self.value = value
        self.calls: list[tuple[str, str]] = []

    def get_latest(self, *, owner_id: str, run_id: str):
        self.calls.append((owner_id, run_id))
        if isinstance(self.value, Exception):
            raise self.value
        return self.value


def service(task_value, snapshot_value) -> EvidenceProductService:
    return EvidenceProductService(
        task_service=Tasks(task_value),
        repository=Snapshots(snapshot_value),
        clock=lambda: NOW,
    )


def test_evidence_view_is_owner_scoped_and_query_time_expiry_removes_meta_claims() -> None:
    value = snapshot()
    current = service(task(), value).get_evidence(owner_id="owner-1", run_id=RUN_ID)
    expired = EvidenceProductService(
        task_service=Tasks(task()),
        repository=Snapshots(value),
        clock=lambda: NOW + timedelta(hours=1),
    ).get_evidence(owner_id="owner-1", run_id=RUN_ID)

    assert current.revision == 3
    assert current.freshness is EvidenceSnapshotFreshness.CURRENT
    assert expired.freshness is EvidenceSnapshotFreshness.EXPIRED
    assert "current_meta_recommendation" not in {
        claim.value for claim in expired.usable_claims
    }


def test_product_state_combines_task_publication_and_latest_snapshot() -> None:
    published = service(task(), snapshot()).get_product_state(
        owner_id="owner-1", run_id=RUN_ID
    )
    missing = service(task(), None).get_product_state(
        owner_id="owner-1", run_id=RUN_ID
    )
    active = service(
        task(TaskStatus.RUNNING, publication=None), None
    ).get_product_state(owner_id="owner-1", run_id=RUN_ID)

    assert published.state is ProductRunStateValue.PUBLISHED
    assert missing.state is ProductRunStateValue.DEGRADED
    assert active.state is ProductRunStateValue.NOT_READY


def test_missing_evidence_and_cross_owner_run_are_distinct_safe_errors() -> None:
    with pytest.raises(EvidenceProductServiceError) as missing:
        service(task(), None).get_evidence(owner_id="owner-1", run_id=RUN_ID)
    with pytest.raises(EvidenceProductServiceError) as hidden:
        service(TaskServiceError("task_not_found"), snapshot()).get_product_state(
            owner_id="owner-2", run_id=RUN_ID
        )

    assert missing.value.code == "evidence_not_available"
    assert hidden.value.code == "run_not_found"


def test_repository_and_task_failures_are_allowlisted_without_original_cause() -> None:
    with pytest.raises(EvidenceProductServiceError) as repository:
        service(
            task(),
            EvidenceSnapshotRepositoryError(
                "postgresql://secret@private C:\\private\\evidence.json"
            ),
        ).get_product_state(owner_id="owner-1", run_id=RUN_ID)
    with pytest.raises(EvidenceProductServiceError) as tasks:
        service(
            TaskServiceError("task_persistence_failed"), snapshot()
        ).get_product_state(owner_id="owner-1", run_id=RUN_ID)

    assert repository.value.code == "evidence_unavailable"
    assert tasks.value.code == "evidence_unavailable"
    assert "secret" not in str(repository.value) + str(tasks.value)


def test_snapshot_identity_drift_fails_closed() -> None:
    drifted = snapshot().model_copy(update={"run_id": "review_other_1"})

    with pytest.raises(EvidenceProductServiceError) as error:
        service(task(), drifted).get_evidence(owner_id="owner-1", run_id=RUN_ID)

    assert error.value.code == "evidence_integrity_failed"
