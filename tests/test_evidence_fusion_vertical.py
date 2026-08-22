from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.evidence.adapters import riot_match_from_summary_row
from app.evidence.fusion import (
    DataDragonSnapshot,
    EvidenceBundleDisposition,
    EvidenceClaim,
    EvidenceConfidence,
    EvidenceJoinStatus,
    OfficialPatchEvidence,
    fuse_evidence,
)
from app.meta.models import (
    LaneMetaChampionFact,
    MetaEvidence,
    MetaProvenance,
    MetaUseCase,
)


NOW = datetime(2026, 8, 23, 8, 0, tzinfo=timezone.utc)


def _summary_row() -> dict[str, object]:
    return {
        "match_id": "ASIA1_9876543210",
        "game_version": "15.16.1",
        "queue_id": 420,
        "champion_id": 75,
        "champion_name": "Nasus",
        "role": "TOP",
        "win": True,
        "game_duration_seconds": 2040,
        "timeline_status": "available",
        "generated_at_utc": NOW.isoformat(),
        "puuid": "must-not-enter-evidence",
        "raw_body": "must-not-enter-evidence",
    }


def _meta(*, patch: str | None = None) -> MetaEvidence:
    complete = patch is not None
    return MetaEvidence(
        source="opgg",
        remote_tool="lol_list_lane_meta_champions",
        position="top",
        facts=(
            LaneMetaChampionFact(
                champion="Nasus",
                win_rate=0.53,
                pick_rate=0.1,
                ban_rate=0.02,
                tier=0,
                rank=1,
                rank_previous=2,
                rank_previous_patch=2,
            ),
        ),
        provenance=(MetaProvenance.COMPLETE if complete else MetaProvenance.PARTIAL),
        upstream_patch=patch,
        source_generated_at=NOW if complete else None,
        retrieved_at=NOW,
        expires_at=NOW + timedelta(minutes=15),
        allowed_uses=(
            frozenset(
                {
                    MetaUseCase.CURRENT_SNAPSHOT_RECOMMENDATION,
                    MetaUseCase.EXACT_PATCH_ATTRIBUTION,
                }
            )
            if complete
            else frozenset({MetaUseCase.CURRENT_SNAPSHOT_RECOMMENDATION})
        ),
        catalog_digest="b" * 64,
        tool_schema_digest="c" * 64,
    )


def _static() -> DataDragonSnapshot:
    return DataDragonSnapshot(
        version="15.16.1",
        language="zh_CN",
        catalog_digest="d" * 64,
        retrieved_at=NOW,
    )


def _patch() -> OfficialPatchEvidence:
    return OfficialPatchEvidence(
        patch_version="15.16",
        update_id="patch-15-16",
        published_at=NOW - timedelta(days=1),
        retrieved_at=NOW,
        expires_at=NOW + timedelta(days=7),
        source_digest="e" * 64,
    )


def test_no_io_vertical_projects_existing_riot_and_partial_opgg_safely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def forbidden(*_args, **_kwargs):
        calls.append("external")
        raise AssertionError("external I/O is forbidden")

    monkeypatch.setattr("requests.sessions.Session.request", forbidden)
    monkeypatch.setattr("os.getenv", forbidden)

    riot = riot_match_from_summary_row(_summary_row(), routing_region="asia")
    bundle = fuse_evidence(
        riot_matches=(riot,),
        data_dragon=_static(),
        official_patch=_patch(),
        meta_evidence=(_meta(),),
        now=NOW,
    )
    projection = bundle.to_public_projection()

    assert calls == []
    assert bundle.disposition is EvidenceBundleDisposition.COMPLETE
    assert bundle.confidence is EvidenceConfidence.MEDIUM
    assert bundle.joins[0].status is EvidenceJoinStatus.JOINED_PARTIAL
    assert EvidenceClaim.CURRENT_META_RECOMMENDATION in bundle.claims
    assert EvidenceClaim.EXACT_PATCH_META_COMPARISON not in bundle.claims
    assert len(bundle.digest) == 64
    serialized = str(projection).lower()
    assert "must-not-enter-evidence" not in serialized
    assert "puuid" not in serialized
    assert "raw_body" not in serialized


def test_complete_meta_with_wrong_patch_is_retained_as_conflict() -> None:
    riot = riot_match_from_summary_row(_summary_row(), routing_region="asia")
    bundle = fuse_evidence(
        riot_matches=(riot,),
        data_dragon=_static(),
        official_patch=_patch(),
        meta_evidence=(_meta(patch="15.17"),),
        now=NOW,
    )

    assert bundle.disposition is EvidenceBundleDisposition.DEGRADED
    assert bundle.confidence is EvidenceConfidence.LOW
    assert bundle.joins[0].status is EvidenceJoinStatus.CONFLICT
    assert [row.code for row in bundle.conflicts] == ["meta_patch_mismatch"]
    assert EvidenceClaim.CURRENT_META_RECOMMENDATION in bundle.claims
    assert EvidenceClaim.EXACT_PATCH_META_COMPARISON not in bundle.claims


def test_duplicate_riot_fact_identity_fails_before_fusion_side_effects() -> None:
    riot = riot_match_from_summary_row(_summary_row(), routing_region="asia")

    with pytest.raises(ValueError, match="duplicate Riot match id"):
        fuse_evidence(
            riot_matches=(riot, riot),
            data_dragon=_static(),
            official_patch=_patch(),
            meta_evidence=(_meta(),),
            now=NOW,
        )
