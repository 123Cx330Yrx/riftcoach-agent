from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.actor import StaticActorContextProvider
from app.api.main import create_app
from app.api.task_models import ReadinessResult
from app.players.models import (
    CreatePlayerLinkCommand,
    OwnerPlayerRelationshipRef,
    PlayerLinkCreateDisposition,
    PlayerLinkCreateResult,
    PlayerLinkFailure,
    PlayerLinkStatus,
    PlayerLinkTaskView,
    RelationshipRole,
    RoutingRegion,
    VerificationStatus,
)
from app.players.service import PlayerLinkServiceError


NOW = datetime(2026, 8, 19, 16, 0, 0, tzinfo=timezone.utc)
LINK_TASK_ID = UUID("50000000-0000-4000-8000-000000000001")
SUBJECT_ID = UUID("50000000-0000-4000-8000-000000000002")
RELATIONSHIP_ID = UUID("50000000-0000-4000-8000-000000000003")


def link_view(
    status: PlayerLinkStatus = PlayerLinkStatus.QUEUED,
    *,
    failure: PlayerLinkFailure | None = None,
) -> PlayerLinkTaskView:
    claimed_at = NOW + timedelta(seconds=1) if status is not PlayerLinkStatus.QUEUED else None
    finished_at = (
        NOW + timedelta(seconds=2)
        if status in {PlayerLinkStatus.SUCCEEDED, PlayerLinkStatus.FAILED}
        else None
    )
    relationship = (
        OwnerPlayerRelationshipRef(
            relationship_id=RELATIONSHIP_ID,
            player_subject_id=SUBJECT_ID,
            relationship_role=RelationshipRole.SELF,
            verification_status=VerificationStatus.UNVERIFIED_CLAIM,
        )
        if status is PlayerLinkStatus.SUCCEEDED
        else None
    )
    return PlayerLinkTaskView(
        schema_version="1.0",
        link_task_id=LINK_TASK_ID,
        status=status,
        created_at=NOW,
        updated_at=finished_at or claimed_at or NOW,
        claimed_at=claimed_at,
        finished_at=finished_at,
        relationship_role=RelationshipRole.SELF,
        verification_status=VerificationStatus.UNVERIFIED_CLAIM,
        player_subject_id=SUBJECT_ID if relationship is not None else None,
        relationship=relationship,
        confirmed_riot_id=(
            "Confirmed Player#KR1" if relationship is not None else None
        ),
        failure=failure,
    )


class FakePlayerLinkService:
    def __init__(self) -> None:
        self.view = link_view()
        self.disposition = PlayerLinkCreateDisposition.CREATED
        self.error: Exception | None = None
        self.commands: list[CreatePlayerLinkCommand] = []
        self.get_calls: list[tuple[str, UUID]] = []

    def create(self, command: CreatePlayerLinkCommand) -> PlayerLinkCreateResult:
        self.commands.append(command)
        if self.error is not None:
            raise self.error
        return PlayerLinkCreateResult(
            disposition=self.disposition,
            task=self.view,
        )

    def get_link(self, *, owner_id: str, link_task_id: UUID) -> PlayerLinkTaskView:
        self.get_calls.append((owner_id, link_task_id))
        if self.error is not None:
            raise self.error
        return self.view


class UnusedTaskService:
    def create(self, command: object) -> object:
        del command
        raise AssertionError("review task service must not be called")

    def get_task(self, *, owner_id: str, task_id: UUID) -> object:
        del owner_id, task_id
        raise AssertionError("review task service must not be called")

    def get_task_by_run_id(self, *, owner_id: str, run_id: str) -> object:
        del owner_id, run_id
        raise AssertionError("review task service must not be called")


class UnusedRunQuery:
    def get_run(self, run_id: str) -> object:
        del run_id
        raise AssertionError("run query must not be called")

    def get_report(self, run_id: str) -> str:
        del run_id
        raise AssertionError("run query must not be called")


class ReadyProbe:
    def check(self) -> ReadinessResult:
        return ReadinessResult.ready()


def client(service: FakePlayerLinkService | None = None) -> TestClient:
    return TestClient(
        create_app(
            task_service=UnusedTaskService(),
            player_link_service=service or FakePlayerLinkService(),
            query_service=UnusedRunQuery(),
            actor_provider=StaticActorContextProvider(
                owner_id="owner-1",
                profile="test",
            ),
            readiness_probe=ReadyProbe(),
        )
    )


def post_link(http: TestClient, **overrides: Any):
    payload = {
        "riot_id": " Demo Player#KR1 ",
        "routing_region": "asia",
        "relationship_role": "self",
    }
    payload.update(overrides)
    return http.post(
        "/player-links",
        headers={"Idempotency-Key": "player-link-request-1"},
        json=payload,
    )


def test_openapi_has_strict_player_link_contract_without_puuid() -> None:
    document = client().get("/openapi.json").json()

    assert document["paths"]["/player-links"]["post"]["responses"].get("202")
    assert document["paths"]["/player-links/{link_task_id}"]["get"]
    serialized = json.dumps(document, sort_keys=True).lower()
    assert '"puuid"' not in serialized
    assert "verification_status" not in document["components"]["schemas"][
        "CreatePlayerLinkRequest"
    ]["properties"]


def test_app_factory_and_openapi_do_not_read_keys_or_open_io(monkeypatch) -> None:
    original_getenv = os.getenv

    def guarded_getenv(key: str, default: object = None):
        if key in {"RIOT_API_KEY", "DATABASE_URL"}:
            raise AssertionError("explicit app factory must not read secrets")
        return original_getenv(key, default)

    def forbidden_io(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("explicit app factory must not perform I/O")

    monkeypatch.setattr("os.getenv", guarded_getenv)
    monkeypatch.setattr("psycopg.connect", forbidden_io)
    monkeypatch.setattr("requests.sessions.Session.request", forbidden_io)

    document = client().get("/openapi.json").json()

    assert "/player-links" in document["paths"]


@pytest.mark.parametrize(
    ("disposition", "expected"),
    (
        (PlayerLinkCreateDisposition.CREATED, "created"),
        (PlayerLinkCreateDisposition.REPLAYED, "replayed"),
    ),
)
def test_post_enqueues_owner_scoped_link_and_returns_body_free_202(
    disposition: PlayerLinkCreateDisposition,
    expected: str,
) -> None:
    service = FakePlayerLinkService()
    service.disposition = disposition

    response = post_link(client(service))

    assert response.status_code == 202
    assert response.json() == {
        "schema_version": "1.0",
        "disposition": expected,
        "link_task_id": str(LINK_TASK_ID),
        "status": "queued",
        "link": f"/player-links/{LINK_TASK_ID}",
    }
    assert service.commands == [
        CreatePlayerLinkCommand(
            owner_id="owner-1",
            idempotency_key="player-link-request-1",
            riot_id="Demo Player#KR1",
            routing_region=RoutingRegion.ASIA,
            relationship_role=RelationshipRole.SELF,
        )
    ]
    assert "Demo Player" not in response.text
    assert "owner-1" not in response.text


@pytest.mark.parametrize(
    "headers,payload",
    (
        (
            {},
            {"riot_id": "Player#KR1", "routing_region": "asia", "relationship_role": "self"},
        ),
        (
            {"Idempotency-Key": "contains spaces"},
            {"riot_id": "Player#KR1", "routing_region": "asia", "relationship_role": "self"},
        ),
        (
            {"Idempotency-Key": "link-1"},
            {"riot_id": "Player#KR1", "routing_region": "cn", "relationship_role": "self"},
        ),
        (
            {"Idempotency-Key": "link-1"},
            {"riot_id": "Player#KR1", "routing_region": "zh_CN", "relationship_role": "self"},
        ),
        (
            {"Idempotency-Key": "link-1"},
            {
                "riot_id": "Player#KR1",
                "routing_region": "asia",
                "relationship_role": "verified_self",
            },
        ),
        (
            {"Idempotency-Key": "link-1"},
            {
                "riot_id": "Player#KR1",
                "routing_region": "asia",
                "relationship_role": "self",
                "owner_id": "attacker",
            },
        ),
        (
            {"Idempotency-Key": "link-1"},
            {
                "riot_id": "Player#KR1",
                "routing_region": "asia",
                "relationship_role": "self",
                "puuid": "attacker",
            },
        ),
        (
            {"Idempotency-Key": "link-1"},
            {
                "riot_id": "Player#KR1",
                "routing_region": "asia",
                "relationship_role": "self",
                "verification_status": "rso_verified",
            },
        ),
    ),
)
def test_post_rejects_invalid_or_privileged_input_before_service(
    headers: dict[str, str],
    payload: dict[str, str],
) -> None:
    service = FakePlayerLinkService()

    response = client(service).post(
        "/player-links",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 422
    assert response.json() == {"code": "request_invalid"}
    assert service.commands == []


@pytest.mark.parametrize(
    ("service_code", "status", "public_code"),
    (
        ("idempotency_conflict", 409, "idempotency_conflict"),
        ("owner_capacity_exceeded", 503, "player_link_capacity_exceeded"),
        ("global_capacity_exceeded", 503, "player_link_capacity_exceeded"),
        ("link_persistence_failed", 503, "service_unavailable"),
        ("link_identity_invalid", 503, "service_unavailable"),
    ),
)
def test_post_maps_service_failures_to_safe_http_errors(
    service_code: str,
    status: int,
    public_code: str,
) -> None:
    service = FakePlayerLinkService()
    service.error = PlayerLinkServiceError(service_code)  # type: ignore[arg-type]

    response = post_link(client(service))

    assert response.status_code == status
    assert response.json() == {"code": public_code}


@pytest.mark.parametrize(
    "view",
    (
        link_view(PlayerLinkStatus.QUEUED),
        link_view(PlayerLinkStatus.RUNNING),
        link_view(PlayerLinkStatus.SUCCEEDED),
        link_view(
            PlayerLinkStatus.FAILED,
            failure=PlayerLinkFailure(code="riot_rate_limited", retryable=True),
        ),
    ),
)
def test_get_is_owner_scoped_and_projects_each_state_without_puuid(
    view: PlayerLinkTaskView,
) -> None:
    service = FakePlayerLinkService()
    service.view = view

    response = client(service).get(f"/player-links/{LINK_TASK_ID}")

    assert response.status_code == 200
    body = response.json()
    assert body["link_task_id"] == str(LINK_TASK_ID)
    assert body["status"] == view.status.value
    assert "puuid" not in response.text.lower()
    assert "owner_id" not in body
    assert service.get_calls == [("owner-1", LINK_TASK_ID)]
    if view.status is PlayerLinkStatus.SUCCEEDED:
        assert body["player_subject_id"] == str(SUBJECT_ID)
        assert body["relationship_id"] == str(RELATIONSHIP_ID)
        assert body["confirmed_riot_id"] == "Confirmed Player#KR1"
    if view.status is PlayerLinkStatus.FAILED:
        assert body["failure"] == {
            "code": "riot_rate_limited",
            "retryable": True,
        }


def test_invalid_and_unowned_link_are_indistinguishable_not_found() -> None:
    service = FakePlayerLinkService()
    service.error = PlayerLinkServiceError("link_not_found")
    http = client(service)

    invalid = http.get("/player-links/not-a-uuid")
    hidden = http.get(f"/player-links/{LINK_TASK_ID}")

    assert invalid.status_code == hidden.status_code == 404
    assert invalid.json() == hidden.json() == {"code": "player_link_not_found"}


def test_get_persistence_or_invalid_service_result_fails_closed() -> None:
    service = FakePlayerLinkService()
    service.error = RuntimeError("postgresql://private:secret@host")

    failed = client(service).get(f"/player-links/{LINK_TASK_ID}")

    assert failed.status_code == 503
    assert failed.json() == {"code": "service_unavailable"}
    assert "private" not in failed.text
