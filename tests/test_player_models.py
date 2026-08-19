from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.players.models import (
    CreatePlayerLinkCommand,
    OwnerPlayerRelationshipRef,
    PlayerLinkFailure,
    PlayerLinkStatus,
    PlayerLinkTask,
    PlayerLinkTaskView,
    RelationshipRole,
    RoutingRegion,
    VerificationStatus,
)


NOW = datetime(2026, 8, 19, 12, 0, 0, tzinfo=timezone.utc)
LINK_TASK_ID = UUID("20000000-0000-4000-8000-000000000001")
SUBJECT_ID = UUID("20000000-0000-4000-8000-000000000002")
RELATIONSHIP_ID = UUID("20000000-0000-4000-8000-000000000003")


def queued_task(**changes: object) -> PlayerLinkTask:
    values: dict[str, object] = {
        "link_task_id": LINK_TASK_ID,
        "task_kind": "player_link",
        "schema_version": "1.0",
        "owner_id": "owner-1",
        "idempotency_key": "link-1",
        "request_fingerprint": "a" * 64,
        "routing_region": RoutingRegion.ASIA,
        "relationship_role": RelationshipRole.SELF,
        "verification_status": VerificationStatus.UNVERIFIED_CLAIM,
        "game_name": "DemoPlayer",
        "tag_line": "KR1",
        "alias_hash": "b" * 64,
        "status": PlayerLinkStatus.QUEUED,
        "created_at": NOW,
        "updated_at": NOW,
        "claimed_at": None,
        "finished_at": None,
        "worker_id": None,
        "subject_id": None,
        "relationship": None,
        "confirmed_game_name": None,
        "confirmed_tag_line": None,
        "failure": None,
    }
    values.update(changes)
    return PlayerLinkTask(**values)  # type: ignore[arg-type]


def failure(*, code: str = "riot_rate_limited", retryable: bool = True) -> PlayerLinkFailure:
    return PlayerLinkFailure(code=code, retryable=retryable)


def relationship_ref(
    *,
    role: RelationshipRole = RelationshipRole.SELF,
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED_CLAIM,
) -> OwnerPlayerRelationshipRef:
    return OwnerPlayerRelationshipRef(
        relationship_id=RELATIONSHIP_ID,
        player_subject_id=SUBJECT_ID,
        relationship_role=role,
        verification_status=verification_status,
    )


def test_routing_region_allowlist_rejects_cn_and_zh_cn() -> None:
    assert tuple(region.value for region in RoutingRegion) == (
        "americas",
        "asia",
        "europe",
        "sea",
    )

    with pytest.raises(ValidationError):
        CreatePlayerLinkCommand(
            owner_id="owner-1",
            idempotency_key="link-1",
            riot_id="DemoPlayer#KR1",
            routing_region="cn",
            relationship_role="self",
        )
    with pytest.raises(ValidationError):
        CreatePlayerLinkCommand(
            owner_id="owner-1",
            idempotency_key="link-1",
            riot_id="DemoPlayer#KR1",
            routing_region="zh_CN",
            relationship_role="self",
        )


def test_riot_id_is_nfc_trimmed_and_control_or_length_invalid() -> None:
    command = CreatePlayerLinkCommand(
        owner_id="owner-1",
        idempotency_key="link-1",
        riot_id="  Cafe\u0301#  TAG  ",
        routing_region=RoutingRegion.AMERICAS,
        relationship_role=RelationshipRole.OBSERVED,
    )

    assert command.riot_id == "Caf\u00e9#TAG"
    assert command.game_name == "Caf\u00e9"
    assert command.tag_line == "TAG"

    with pytest.raises(ValidationError, match="control"):
        CreatePlayerLinkCommand(
            owner_id="owner-1",
            idempotency_key="link-1",
            riot_id="Demo\u0000Player#KR1",
            routing_region=RoutingRegion.ASIA,
            relationship_role=RelationshipRole.SELF,
        )
    with pytest.raises(ValidationError, match="game name"):
        CreatePlayerLinkCommand(
            owner_id="owner-1",
            idempotency_key="link-1",
            riot_id=f"{'A' * 65}#KR1",
            routing_region=RoutingRegion.ASIA,
            relationship_role=RelationshipRole.SELF,
        )
    with pytest.raises(ValidationError, match="tag line"):
        CreatePlayerLinkCommand(
            owner_id="owner-1",
            idempotency_key="link-1",
            riot_id=f"DemoPlayer#{'T' * 33}",
            routing_region=RoutingRegion.ASIA,
            relationship_role=RelationshipRole.SELF,
        )


def test_role_determines_current_verification_and_verified_path_is_future_only() -> None:
    self_command = CreatePlayerLinkCommand(
        owner_id="owner-1",
        idempotency_key="link-1",
        riot_id="DemoPlayer#KR1",
        routing_region=RoutingRegion.ASIA,
        relationship_role=RelationshipRole.SELF,
    )
    observed_command = CreatePlayerLinkCommand(
        owner_id="owner-1",
        idempotency_key="link-2",
        riot_id="DemoPlayer#KR1",
        routing_region=RoutingRegion.ASIA,
        relationship_role=RelationshipRole.OBSERVED,
    )

    assert self_command.derived_verification_status is VerificationStatus.UNVERIFIED_CLAIM
    assert observed_command.derived_verification_status is VerificationStatus.NOT_APPLICABLE
    assert "verification_status" not in CreatePlayerLinkCommand.model_fields
    assert VerificationStatus.RSO_VERIFIED.value == "rso_verified"


def test_relationship_role_and_verification_pairs_are_strict() -> None:
    assert relationship_ref().verification_status is VerificationStatus.UNVERIFIED_CLAIM
    assert relationship_ref(
        role=RelationshipRole.OBSERVED,
        verification_status=VerificationStatus.NOT_APPLICABLE,
    ).relationship_role is RelationshipRole.OBSERVED

    with pytest.raises(ValidationError):
        relationship_ref(verification_status=VerificationStatus.NOT_APPLICABLE)
    with pytest.raises(ValidationError):
        relationship_ref(
            role=RelationshipRole.OBSERVED,
            verification_status=VerificationStatus.UNVERIFIED_CLAIM,
        )


def test_link_task_status_shape_requires_success_identity_and_failed_has_none() -> None:
    queued = queued_task()
    assert queued.status is PlayerLinkStatus.QUEUED

    running = queued_task(
        status=PlayerLinkStatus.RUNNING,
        worker_id="worker-1",
        claimed_at=NOW,
    )
    assert running.status is PlayerLinkStatus.RUNNING

    succeeded = queued_task(
        status=PlayerLinkStatus.SUCCEEDED,
        worker_id="worker-1",
        claimed_at=NOW,
        finished_at=NOW,
        subject_id=SUBJECT_ID,
        relationship=relationship_ref(),
        confirmed_game_name="DemoPlayer",
        confirmed_tag_line="KR1",
    )
    assert succeeded.relationship is not None

    failed = queued_task(
        status=PlayerLinkStatus.FAILED,
        worker_id="worker-1",
        claimed_at=NOW,
        finished_at=NOW,
        failure=failure(code="player_not_found", retryable=False),
    )
    assert failed.failure is not None

    with pytest.raises(ValidationError):
        queued_task(
            status=PlayerLinkStatus.SUCCEEDED,
            worker_id="worker-1",
            claimed_at=NOW,
            finished_at=NOW,
            subject_id=SUBJECT_ID,
        )
    with pytest.raises(ValidationError):
        queued_task(
            status=PlayerLinkStatus.FAILED,
            worker_id="worker-1",
            claimed_at=NOW,
            finished_at=NOW,
            failure=failure(),
            subject_id=SUBJECT_ID,
            relationship=relationship_ref(),
        )


def test_public_link_view_is_body_free_and_hides_private_identity_inputs() -> None:
    task = queued_task(
        status=PlayerLinkStatus.SUCCEEDED,
        worker_id="worker-1",
        claimed_at=NOW,
        finished_at=NOW,
        subject_id=SUBJECT_ID,
        relationship=relationship_ref(),
        confirmed_game_name="VisibleName",
        confirmed_tag_line="TAG",
    )

    payload = PlayerLinkTaskView.from_task(task).model_dump(mode="json")

    assert payload["status"] == "succeeded"
    assert payload["player_subject_id"] == str(SUBJECT_ID)
    assert payload["relationship"]["relationship_id"] == str(RELATIONSHIP_ID)
    assert payload["confirmed_riot_id"] == "VisibleName#TAG"
    assert "game_name" not in payload
    assert "tag_line" not in payload
    assert "alias_hash" not in payload
    assert "request_fingerprint" not in payload
    assert "owner_id" not in payload
    assert "worker_id" not in payload
    assert "puuid" not in payload


def test_public_failure_projection_uses_allowlisted_retryable_reason_codes() -> None:
    retryable = failure(code="upstream_timeout", retryable=True)
    assert retryable.code == "upstream_timeout"
    assert retryable.retryable is True

    terminal = queued_task(
        status=PlayerLinkStatus.FAILED,
        worker_id="worker-1",
        claimed_at=NOW,
        finished_at=NOW,
        failure=retryable,
    )
    payload = PlayerLinkTaskView.from_task(terminal).model_dump(mode="json")
    assert payload["failure"] == {
        "code": "upstream_timeout",
        "retryable": True,
    }

    with pytest.raises(ValidationError):
        PlayerLinkFailure(code="raw_upstream_body", retryable=True)
