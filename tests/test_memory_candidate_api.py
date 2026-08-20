from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.actor import StaticActorContextProvider
from app.api.main import create_app
from app.api.task_models import ReadinessResult
from app.memory.models import (
    CandidateKind,
    CandidateStatus,
    CreateMemoryCandidateCommand,
    MemoryCandidateView,
    MemoryOperation,
    TargetScope,
)
from app.memory.service import MemoryCandidateServiceError


NOW = datetime(2026, 8, 20, 16, 0, tzinfo=timezone.utc)
OWNER = "memory-api-owner"
CONVERSATION_ID = UUID("86000000-0000-4000-8000-000000000001")
CANDIDATE_ID = UUID("86000000-0000-4000-8000-000000000002")


class UnusedTaskService:
    def create(self, command):
        raise AssertionError("task service must not be called")

    def get_task(self, *, owner_id, task_id):
        raise AssertionError("task service must not be called")

    def get_task_by_run_id(self, *, owner_id, run_id):
        raise AssertionError("task service must not be called")


class UnusedPlayerLinkService:
    def create(self, command):
        raise AssertionError("player link service must not be called")

    def get_link(self, *, owner_id, link_task_id):
        raise AssertionError("player link service must not be called")


class UnusedRunQuery:
    def get_run(self, run_id):
        raise AssertionError("run query must not be called")

    def get_report(self, run_id):
        raise AssertionError("run query must not be called")


class ReadyProbe:
    def check(self) -> ReadinessResult:
        return ReadinessResult.ready()


def view(*, status: CandidateStatus = CandidateStatus.PENDING) -> MemoryCandidateView:
    decided = None if status is CandidateStatus.PENDING else NOW + timedelta(minutes=1)
    return MemoryCandidateView(
        candidate_id=CANDIDATE_ID,
        conversation_id=CONVERSATION_ID,
        target_scope=TargetScope.OWNER_GLOBAL,
        candidate_kind=CandidateKind.OWNER_PREFERENCE,
        memory_key="report_language",
        operation=MemoryOperation.SET,
        requires_confirmation=False,
        status=status,
        gate_policy_version="memory-gate-v1",
        created_at=NOW,
        expires_at=NOW + timedelta(days=30),
        decided_at=decided,
        decision_reason_code=(
            None
            if status is CandidateStatus.PENDING
            else "user_confirmed" if status is CandidateStatus.ACCEPTED else "user_rejected"
        ),
    )


class FakeMemoryCandidateService:
    def __init__(self) -> None:
        self.commands: list[CreateMemoryCandidateCommand] = []
        self.calls: list[tuple[object, ...]] = []
        self.error: Exception | None = None

    def _result(self, result: MemoryCandidateView) -> MemoryCandidateView:
        if self.error is not None:
            raise self.error
        return result

    def create(self, command: CreateMemoryCandidateCommand) -> MemoryCandidateView:
        self.commands.append(command)
        return self._result(view())

    def get(self, *, owner_id: str, candidate_id: UUID) -> MemoryCandidateView:
        self.calls.append(("get", owner_id, candidate_id))
        return self._result(view())

    def accept(self, *, owner_id: str, candidate_id: UUID, actor_id: str) -> MemoryCandidateView:
        self.calls.append(("accept", owner_id, candidate_id, actor_id))
        return self._result(view(status=CandidateStatus.ACCEPTED))

    def reject(self, *, owner_id: str, candidate_id: UUID, actor_id: str) -> MemoryCandidateView:
        self.calls.append(("reject", owner_id, candidate_id, actor_id))
        return self._result(view(status=CandidateStatus.REJECTED))


def client(service: FakeMemoryCandidateService | None = None, *, inject: bool = True) -> TestClient:
    kwargs = {}
    if inject:
        kwargs["memory_candidate_service"] = service or FakeMemoryCandidateService()
    return TestClient(
        create_app(
            task_service=UnusedTaskService(),
            player_link_service=UnusedPlayerLinkService(),
            query_service=UnusedRunQuery(),
            actor_provider=StaticActorContextProvider(owner_id=OWNER, profile="test"),
            readiness_probe=ReadyProbe(),
            **kwargs,
        )
    )


def create_candidate(http: TestClient, **overrides):
    payload = {
        "target_scope": "owner_global",
        "candidate_kind": "owner_preference",
        "memory_key": "report_language",
        "operation": "set",
        "proposal_payload": {"value": "zh-CN"},
    }
    payload.update(overrides)
    return http.post(
        f"/conversations/{CONVERSATION_ID}/memory-candidates",
        headers={"Idempotency-Key": "candidate-request-1"},
        json=payload,
    )


def test_create_uses_trusted_owner_and_fixed_public_provenance() -> None:
    service = FakeMemoryCandidateService()
    response = create_candidate(client(service))
    assert response.status_code == 201
    command = service.commands[0]
    assert command.owner_id == OWNER
    assert command.provenance_kind.value == "user_structured_input"
    assert command.producer_id == "riftcoach-public-api"
    body = response.json()
    assert body["candidate_id"] == str(CANDIDATE_ID)
    assert body["status"] == "pending"
    for private_field in (
        "proposal_payload",
        "proposal_confidence",
        "producer_id",
        "player_subject_id",
        "relationship_id",
        "source_message_id",
    ):
        assert private_field not in body


def test_client_cannot_forge_owner_provenance_or_target_identity() -> None:
    service = FakeMemoryCandidateService()
    response = create_candidate(
        client(service),
        owner_id="attacker",
        provenance_kind="model_inference",
        player_subject_id=str(UUID("86000000-0000-4000-8000-000000000099")),
    )
    assert response.status_code == 422
    assert response.json() == {"code": "request_invalid"}
    assert service.commands == []


def test_get_accept_and_reject_use_owner_scoped_empty_body_commands() -> None:
    service = FakeMemoryCandidateService()
    http = client(service)
    fetched = http.get(f"/memory-candidates/{CANDIDATE_ID}")
    accepted = http.post(f"/memory-candidates/{CANDIDATE_ID}/accept")
    rejected = http.post(f"/memory-candidates/{CANDIDATE_ID}/reject")
    assert fetched.status_code == 200
    assert accepted.status_code == 200 and accepted.json()["status"] == "accepted"
    assert rejected.status_code == 200 and rejected.json()["status"] == "rejected"
    assert service.calls == [
        ("get", OWNER, CANDIDATE_ID),
        ("accept", OWNER, CANDIDATE_ID, OWNER),
        ("reject", OWNER, CANDIDATE_ID, OWNER),
    ]
    non_empty = http.post(
        f"/memory-candidates/{CANDIDATE_ID}/accept",
        json={"decision_actor_id": "attacker"},
    )
    assert non_empty.status_code == 422
    assert non_empty.json() == {"code": "request_invalid"}


def test_missing_materializer_maps_to_safe_409() -> None:
    service = FakeMemoryCandidateService()
    service.error = MemoryCandidateServiceError("memory_target_unavailable")
    response = client(service).post(f"/memory-candidates/{CANDIDATE_ID}/accept")
    assert response.status_code == 409
    assert response.json() == {"code": "memory_target_unavailable"}


@pytest.mark.parametrize(
    ("service_code", "status_code", "api_code"),
    [
        ("memory_payload_invalid", 422, "memory_payload_invalid"),
        ("memory_version_conflict", 409, "memory_version_conflict"),
    ],
)
def test_typed_target_failures_have_safe_http_mapping(
    service_code,
    status_code,
    api_code,
) -> None:
    service = FakeMemoryCandidateService()
    service.error = MemoryCandidateServiceError(service_code)
    response = client(service).post(f"/memory-candidates/{CANDIDATE_ID}/accept")
    assert response.status_code == status_code
    assert response.json() == {"code": api_code}


def test_routes_are_openapi_visible_and_optional_service_fails_closed(monkeypatch) -> None:
    original_getenv = os.getenv

    def guarded_getenv(key: str, default: str | None = None):
        if key in {"RIOT_API_KEY", "ZHIPU_API_KEY", "DEEPSEEK_API_KEY", "DATABASE_URL"}:
            raise AssertionError("OpenAPI must not read secrets")
        return original_getenv(key, default)

    monkeypatch.setattr("os.getenv", guarded_getenv)
    document = client(inject=False).get("/openapi.json").json()
    assert f"/conversations/{{conversation_id}}/memory-candidates" in document["paths"]
    assert "/memory-candidates/{candidate_id}" in document["paths"]
    assert "/memory-candidates/{candidate_id}/accept" in document["paths"]
    assert "/memory-candidates/{candidate_id}/reject" in document["paths"]
    unavailable = create_candidate(client(inject=False))
    assert unavailable.status_code == 503
    assert unavailable.json() == {"code": "service_unavailable"}
