from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from app.evidence.fusion import (
    DataDragonSnapshot,
    EvidenceBundleDisposition,
    EvidenceClaim,
    EvidenceConfidence,
    OfficialPatchEvidence,
    RiotMatchEvidence,
    fuse_evidence,
)
from app.evidence.storage import (
    EvidenceBundleSnapshot,
    EvidenceSnapshotFreshness,
    ProductRunStateValue,
    ProductStateReason,
    bundle_from_storage_projection,
    bundle_to_storage_projection,
    project_evidence_snapshot,
    project_product_run_state,
)
from app.meta.models import (
    LaneMetaChampionFact,
    MetaEvidence,
    MetaProvenance,
    MetaUseCase,
)
from app.tasks.models import (
    ReviewTaskView,
    TaskPublicationStatus,
    TaskStatus,
)


NOW = datetime(2026, 8, 23, 9, 0, tzinfo=timezone.utc)
TASK_ID = UUID("91000000-0000-4000-8000-000000000001")
SNAPSHOT_ID = UUID("92000000-0000-4000-8000-000000000001")
RUN_ID = "review_evidence_product_1"


def bundle(*, disposition: EvidenceBundleDisposition = EvidenceBundleDisposition.COMPLETE):
    riot = RiotMatchEvidence(
        match_id="ASIA1_1234567890",
        routing_region="asia",
        queue_id=420,
        champion_id=75,
        champion_name="Nasus",
        position="top",
        patch_version="15.16",
        win=True,
        duration_seconds=1800,
        timeline_available=True,
        observed_at=NOW,
        source_digest="a" * 64,
    )
    meta = MetaEvidence(
        source="opgg",
        remote_tool="lol_list_lane_meta_champions",
        position="top",
        facts=(
            LaneMetaChampionFact(
                champion="Nasus",
                win_rate=0.53,
                pick_rate=0.10,
                ban_rate=0.02,
                tier=0,
                rank=1,
                rank_previous=2,
                rank_previous_patch=2,
            ),
        ),
        provenance=MetaProvenance.PARTIAL,
        upstream_patch=None,
        source_generated_at=None,
        retrieved_at=NOW,
        expires_at=NOW + timedelta(minutes=15),
        allowed_uses=frozenset(
            {MetaUseCase.CURRENT_SNAPSHOT_RECOMMENDATION}
        ),
        catalog_digest="b" * 64,
        tool_schema_digest="c" * 64,
    )
    data_dragon = DataDragonSnapshot(
        version="15.16.1",
        language="zh_CN",
        catalog_digest="d" * 64,
        retrieved_at=NOW,
    )
    patch = OfficialPatchEvidence(
        patch_version="15.16",
        update_id="patch-15-16",
        published_at=NOW - timedelta(days=1),
        retrieved_at=NOW,
        expires_at=NOW + timedelta(days=7),
        source_digest="e" * 64,
    )
    if disposition is EvidenceBundleDisposition.COMPLETE:
        return fuse_evidence(
            riot_matches=(riot,),
            data_dragon=data_dragon,
            official_patch=patch,
            meta_evidence=(meta,),
            now=NOW,
        )
    if disposition is EvidenceBundleDisposition.DEGRADED:
        return fuse_evidence(
            riot_matches=(riot,),
            data_dragon=data_dragon,
            official_patch=patch,
            meta_evidence=(),
            now=NOW,
        )
    return fuse_evidence(
        riot_matches=(),
        data_dragon=data_dragon,
        official_patch=patch,
        meta_evidence=(meta,),
        now=NOW,
    )


def snapshot(
    *,
    evidence=None,
    stored_at: datetime = NOW,
) -> EvidenceBundleSnapshot:
    return EvidenceBundleSnapshot.create(
        snapshot_id=SNAPSHOT_ID,
        task_id=TASK_ID,
        run_id=RUN_ID,
        owner_id="owner-1",
        revision=1,
        refresh_id="initial-fusion",
        bundle=evidence or bundle(),
        stored_at=stored_at,
    )


def task(
    status: TaskStatus,
    *,
    publication: TaskPublicationStatus | None = None,
    report_available: bool = False,
) -> ReviewTaskView:
    active = status in {TaskStatus.RUNNING, TaskStatus.RECOVERY_REQUIRED}
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
        created_at=NOW,
        updated_at=NOW + timedelta(seconds=2),
        claimed_at=NOW + timedelta(seconds=1) if active or terminal else None,
        finished_at=NOW + timedelta(seconds=2) if terminal else None,
        terminal_reason=(
            "quality_gate_passed"
            if status is TaskStatus.SUCCEEDED
            else "worker_execution_failed"
            if status is TaskStatus.FAILED
            else "user_requested"
            if status is TaskStatus.CANCELLED
            else None
        ),
        publication_status=publication,
        report_available=report_available,
    )


def test_full_storage_projection_round_trips_nested_meta_and_digests() -> None:
    original = bundle()

    stored = bundle_to_storage_projection(original)
    restored = bundle_from_storage_projection(stored)

    assert restored == original
    assert restored.digest == original.digest
    assert restored.meta_evidence[0].digest == original.meta_evidence[0].digest
    assert restored.has_valid_digest()
    serialized = str(stored).lower()
    for forbidden in ("puuid", "api_key", "authorization", "prompt", "raw_body"):
        assert forbidden not in serialized


@pytest.mark.parametrize(
    "mutator",
    [
        lambda value: value["riot_matches"][0].__setitem__("win", False),
        lambda value: value["meta_evidence"][0]["facts"][0].__setitem__(
            "win_rate", 0.99
        ),
        lambda value: value.__setitem__("digest", "f" * 64),
        lambda value: value.__setitem__("unexpected", "field"),
    ],
)
def test_storage_projection_rejects_tamper_and_unknown_fields(mutator) -> None:
    stored = copy.deepcopy(bundle_to_storage_projection(bundle()))
    mutator(stored)

    with pytest.raises(ValueError):
        bundle_from_storage_projection(stored)


def test_snapshot_identity_binds_task_revision_refresh_and_expiry() -> None:
    value = snapshot()

    assert value.revision == 1
    assert value.expires_at == NOW + timedelta(minutes=15)
    assert value.has_valid_digest()
    assert value.snapshot_digest != value.bundle.digest
    assert not value.model_copy(update={"revision": 2}).has_valid_digest()
    assert not value.model_copy(update={"refresh_id": "other"}).has_valid_digest()


def test_expiry_is_query_time_projection_without_mutating_snapshot() -> None:
    value = snapshot()

    current = project_evidence_snapshot(value, now=NOW + timedelta(minutes=14))
    expired = project_evidence_snapshot(value, now=NOW + timedelta(minutes=15))

    assert current.freshness is EvidenceSnapshotFreshness.CURRENT
    assert EvidenceClaim.CURRENT_META_RECOMMENDATION in current.usable_claims
    assert expired.freshness is EvidenceSnapshotFreshness.EXPIRED
    assert EvidenceClaim.CURRENT_META_RECOMMENDATION not in expired.usable_claims
    assert expired.bundle_digest == current.bundle_digest == value.bundle.digest
    assert value.has_valid_digest()


@pytest.mark.parametrize(
    "task_value,evidence,expected_state,expected_reason",
    [
        (
            task(TaskStatus.QUEUED),
            None,
            ProductRunStateValue.NOT_READY,
            ProductStateReason.TASK_PENDING,
        ),
        (
            task(TaskStatus.RUNNING),
            None,
            ProductRunStateValue.NOT_READY,
            ProductStateReason.TASK_PENDING,
        ),
        (
            task(TaskStatus.RECOVERY_REQUIRED),
            None,
            ProductRunStateValue.NOT_READY,
            ProductStateReason.RECOVERY_REQUIRED,
        ),
        (
            task(TaskStatus.FAILED),
            None,
            ProductRunStateValue.REJECTED,
            ProductStateReason.TASK_FAILED,
        ),
        (
            task(TaskStatus.CANCELLED),
            None,
            ProductRunStateValue.REJECTED,
            ProductStateReason.TASK_CANCELLED,
        ),
        (
            task(
                TaskStatus.SUCCEEDED,
                publication=TaskPublicationStatus.REJECTED,
            ),
            None,
            ProductRunStateValue.REJECTED,
            ProductStateReason.QUALITY_REJECTED,
        ),
        (
            task(
                TaskStatus.SUCCEEDED,
                publication=TaskPublicationStatus.PUBLISHED,
                report_available=True,
            ),
            None,
            ProductRunStateValue.DEGRADED,
            ProductStateReason.EVIDENCE_NOT_AVAILABLE,
        ),
        (
            task(
                TaskStatus.SUCCEEDED,
                publication=TaskPublicationStatus.DEGRADED,
                report_available=True,
            ),
            snapshot(),
            ProductRunStateValue.DEGRADED,
            ProductStateReason.QUALITY_DEGRADED,
        ),
        (
            task(
                TaskStatus.SUCCEEDED,
                publication=TaskPublicationStatus.PUBLISHED,
                report_available=True,
            ),
            snapshot(evidence=bundle(disposition=EvidenceBundleDisposition.DEGRADED)),
            ProductRunStateValue.DEGRADED,
            ProductStateReason.EVIDENCE_DEGRADED,
        ),
        (
            task(
                TaskStatus.SUCCEEDED,
                publication=TaskPublicationStatus.PUBLISHED,
                report_available=True,
            ),
            snapshot(evidence=bundle(disposition=EvidenceBundleDisposition.REJECTED)),
            ProductRunStateValue.DEGRADED,
            ProductStateReason.EVIDENCE_REJECTED,
        ),
        (
            task(
                TaskStatus.SUCCEEDED,
                publication=TaskPublicationStatus.PUBLISHED,
                report_available=True,
            ),
            snapshot(),
            ProductRunStateValue.PUBLISHED,
            ProductStateReason.READY,
        ),
    ],
)
def test_product_state_matrix_is_deterministic(
    task_value,
    evidence,
    expected_state,
    expected_reason,
) -> None:
    result = project_product_run_state(task_value, evidence, now=NOW)

    assert result.state is expected_state
    assert result.reason_code is expected_reason
    assert result.task_status is task_value.status
    assert result.run_id == RUN_ID


def test_expired_complete_snapshot_downgrades_published_product() -> None:
    result = project_product_run_state(
        task(
            TaskStatus.SUCCEEDED,
            publication=TaskPublicationStatus.PUBLISHED,
            report_available=True,
        ),
        snapshot(),
        now=NOW + timedelta(minutes=15),
    )

    assert result.state is ProductRunStateValue.DEGRADED
    assert result.reason_code is ProductStateReason.EVIDENCE_EXPIRED
    assert result.evidence_freshness is EvidenceSnapshotFreshness.EXPIRED
