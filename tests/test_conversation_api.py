from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.actor import StaticActorContextProvider
from app.api.main import create_app
from app.api.task_models import ReadinessResult
from app.conversations.models import (
    AppendUserMessageCommand,
    ConversationCreateDisposition,
    ConversationCreateResult,
    ConversationMessagePage,
    ConversationMessageRole,
    ConversationMessageView,
    ConversationStatus,
    ConversationView,
    CreateConversationCommand,
)
from app.conversations.service import ConversationServiceError
from app.players.models import RelationshipRole
from app.tasks.observability import TaskObservability
from tests.player_link_api_stubs import UnusedPlayerLinkService


NOW = datetime(2026, 8, 20, 10, 0, 0, tzinfo=timezone.utc)
CONVERSATION_ID = UUID("61000000-0000-4000-8000-000000000001")
RELATIONSHIP_ID = UUID("62000000-0000-4000-8000-000000000001")
MESSAGE_ID = UUID("63000000-0000-4000-8000-000000000001")
CONTENT = "I lost lane after the first recall."


def conversation_view(
    *,
    status: ConversationStatus = ConversationStatus.ACTIVE,
) -> ConversationView:
    return ConversationView(
        schema_version="1.0",
        conversation_id=CONVERSATION_ID,
        relationship_id=RELATIONSHIP_ID,
        relationship_role=RelationshipRole.SELF,
        status=status,
        created_at=NOW,
        updated_at=NOW,
        last_message_at=None,
    )


def message_view() -> ConversationMessageView:
    return ConversationMessageView(
        message_id=MESSAGE_ID,
        conversation_id=CONVERSATION_ID,
        sequence_no=1,
        role=ConversationMessageRole.USER,
        content=CONTENT,
        content_sha256=(
            "0cc5d73adccc0650eabbf2f6cdb352bb32b7adc63f867d0dabf7bc92c77ac6e5"
        ),
        created_at=NOW,
    )


class FakeConversationService:
    def __init__(self) -> None:
        self.created = ConversationCreateResult(
            disposition=ConversationCreateDisposition.CREATED,
            conversation=conversation_view(),
        )
        self.conversation = conversation_view()
        self.message = message_view()
        self.page = ConversationMessagePage(
            items=(self.message,),
            limit=50,
            after_sequence=0,
            has_more=False,
            next_after_sequence=None,
        )
        self.error: Exception | None = None
        self.create_commands: list[CreateConversationCommand] = []
        self.append_commands: list[AppendUserMessageCommand] = []
        self.calls: list[tuple[Any, ...]] = []

    def create(
        self,
        command: CreateConversationCommand,
    ) -> ConversationCreateResult:
        self.create_commands.append(command)
        if self.error is not None:
            raise self.error
        return self.created

    def get_conversation(
        self,
        *,
        owner_id: str,
        conversation_id: UUID,
    ) -> ConversationView:
        self.calls.append(("get", owner_id, conversation_id))
        if self.error is not None:
            raise self.error
        return self.conversation

    def append_user_message(
        self,
        command: AppendUserMessageCommand,
    ) -> ConversationMessageView:
        self.append_commands.append(command)
        if self.error is not None:
            raise self.error
        return self.message

    def list_messages(
        self,
        *,
        owner_id: str,
        conversation_id: UUID,
        limit: int = 50,
        after_sequence: int = 0,
    ) -> ConversationMessagePage:
        self.calls.append(
            ("list", owner_id, conversation_id, limit, after_sequence)
        )
        if self.error is not None:
            raise self.error
        item = self.message.model_copy(
            update={"sequence_no": after_sequence + 1}
        )
        return ConversationMessagePage(
            items=(item,),
            limit=limit,
            after_sequence=after_sequence,
            has_more=False,
            next_after_sequence=None,
        )

    def archive_conversation(
        self,
        *,
        owner_id: str,
        conversation_id: UUID,
    ) -> ConversationView:
        self.calls.append(("archive", owner_id, conversation_id))
        if self.error is not None:
            raise self.error
        return conversation_view(status=ConversationStatus.ARCHIVED)

    def hide_conversation(
        self,
        *,
        owner_id: str,
        conversation_id: UUID,
    ) -> ConversationView:
        self.calls.append(("hide", owner_id, conversation_id))
        if self.error is not None:
            raise self.error
        return conversation_view(status=ConversationStatus.HIDDEN)


class UnusedTaskService:
    def create(self, command: object) -> object:
        del command
        raise AssertionError("task service must not be called")

    def get_task(self, *, owner_id: str, task_id: UUID) -> object:
        del owner_id, task_id
        raise AssertionError("task service must not be called")

    def get_task_by_run_id(self, *, owner_id: str, run_id: str) -> object:
        del owner_id, run_id
        raise AssertionError("task service must not be called")


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


def client(
    service: FakeConversationService | None = None,
    *,
    inject_service: bool = True,
    observability: TaskObservability | None = None,
) -> TestClient:
    kwargs: dict[str, Any] = {}
    if inject_service:
        kwargs["conversation_service"] = service or FakeConversationService()
    return TestClient(
        create_app(
            task_service=UnusedTaskService(),
            player_link_service=UnusedPlayerLinkService(),
            query_service=UnusedRunQuery(),
            actor_provider=StaticActorContextProvider(
                owner_id="conversation-owner",
                profile="test",
            ),
            readiness_probe=ReadyProbe(),
            observability=observability,
            **kwargs,
        )
    )


def create_conversation(http: TestClient, **overrides: Any):
    payload: dict[str, Any] = {"player_profile_id": str(RELATIONSHIP_ID)}
    payload.update(overrides)
    return http.post(
        "/conversations",
        headers={"Idempotency-Key": "conversation-request-1"},
        json=payload,
    )


def test_conversation_routes_are_import_and_openapi_no_io(monkeypatch) -> None:
    original_getenv = os.getenv

    def guarded_getenv(key: str, default: str | None = None):
        if key in {
            "RIOT_API_KEY",
            "ZHIPU_API_KEY",
            "DEEPSEEK_API_KEY",
            "DATABASE_URL",
        }:
            raise AssertionError("explicit app factory must not read secrets")
        return original_getenv(key, default)

    def forbidden_io(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("app construction/OpenAPI must not perform I/O")

    monkeypatch.setattr("os.getenv", guarded_getenv)
    monkeypatch.setattr("psycopg.connect", forbidden_io)
    monkeypatch.setattr("requests.sessions.Session.request", forbidden_io)

    document = client(inject_service=False).get("/openapi.json").json()
    paths = document["paths"]
    assert "/conversations" in paths
    assert "/conversations/{conversation_id}" in paths
    assert "/conversations/{conversation_id}/messages" in paths
    assert "/conversations/{conversation_id}/archive" in paths
    assert "/conversations/{conversation_id}/hide" in paths
    for operation in ("archive", "hide"):
        validation_schema = paths[
            f"/conversations/{{conversation_id}}/{operation}"
        ]["post"]["responses"]["422"]["content"]["application/json"][
            "schema"
        ]
        assert validation_schema == {
            "$ref": "#/components/schemas/ConversationErrorResponse"
        }

    unavailable = create_conversation(client(inject_service=False))
    assert unavailable.status_code == 503
    assert unavailable.json() == {"code": "service_unavailable"}


def test_create_uses_trusted_owner_and_returns_201_safe_projection() -> None:
    service = FakeConversationService()

    response = create_conversation(client(service))

    assert response.status_code == 201
    assert response.json() == {
        "schema_version": "1.0",
        "disposition": "created",
        "conversation_id": str(CONVERSATION_ID),
        "relationship_id": str(RELATIONSHIP_ID),
        "relationship_role": "self",
        "status": "active",
        "created_at": NOW.isoformat().replace("+00:00", "Z"),
        "updated_at": NOW.isoformat().replace("+00:00", "Z"),
        "last_message_at": None,
    }
    assert service.create_commands == [
        CreateConversationCommand(
            owner_id="conversation-owner",
            idempotency_key="conversation-request-1",
            relationship_id=RELATIONSHIP_ID,
        )
    ]
    assert not {
        "owner_id",
        "player_subject_id",
        "puuid",
        "idempotency_key",
        "request_fingerprint",
    }.intersection(response.json())


def test_create_accepts_legacy_relationship_alias_but_rejects_both_selectors() -> None:
    service = FakeConversationService()
    http = client(service)

    legacy = http.post(
        "/conversations",
        headers={"Idempotency-Key": "legacy-selection"},
        json={"relationship_id": str(RELATIONSHIP_ID)},
    )
    ambiguous = create_conversation(
        http,
        relationship_id=str(RELATIONSHIP_ID),
    )

    assert legacy.status_code == 201
    assert legacy.json()["relationship_id"] == str(RELATIONSHIP_ID)
    assert ambiguous.status_code == 422
    assert ambiguous.json() == {"code": "request_invalid"}
    assert len(service.create_commands) == 1


def test_create_replay_returns_200_without_a_second_contract_shape() -> None:
    service = FakeConversationService()
    service.created = service.created.model_copy(
        update={"disposition": ConversationCreateDisposition.REPLAYED}
    )

    response = create_conversation(client(service))

    assert response.status_code == 200
    assert response.json()["disposition"] == "replayed"
    assert response.json()["conversation_id"] == str(CONVERSATION_ID)


def test_create_rejects_missing_key_and_privileged_or_unknown_body_fields() -> None:
    service = FakeConversationService()
    http = client(service)

    missing_key = http.post(
        "/conversations",
        json={"player_profile_id": str(RELATIONSHIP_ID)},
    )
    privileged = create_conversation(
        http,
        owner_id="attacker-owner",
        player_subject_id="64000000-0000-4000-8000-000000000001",
        puuid="not-client-authoritative",
        relationship_role="self",
    )

    assert missing_key.status_code == privileged.status_code == 422
    assert missing_key.json() == privileged.json() == {"code": "request_invalid"}
    assert service.create_commands == []


@pytest.mark.parametrize(
    ("error_code", "status", "public_code"),
    (
        (
            "conversation_idempotency_conflict",
            409,
            "conversation_idempotency_conflict",
        ),
        ("conversation_not_found", 404, "conversation_not_found"),
        ("request_invalid", 422, "request_invalid"),
        ("service_unavailable", 503, "service_unavailable"),
    ),
)
def test_create_maps_domain_failures_to_bounded_errors(
    error_code: str,
    status: int,
    public_code: str,
) -> None:
    service = FakeConversationService()
    service.error = ConversationServiceError(error_code)  # type: ignore[arg-type]

    response = create_conversation(client(service))

    assert response.status_code == status
    assert response.json() == {"code": public_code}


def test_get_is_owner_scoped_and_invalid_or_hidden_is_safe_404() -> None:
    service = FakeConversationService()
    http = client(service)

    found = http.get(f"/conversations/{CONVERSATION_ID}")
    invalid = http.get("/conversations/not-a-uuid")
    service.error = ConversationServiceError("conversation_not_found")
    hidden = http.get(f"/conversations/{CONVERSATION_ID}")

    assert found.status_code == 200
    assert found.json()["conversation_id"] == str(CONVERSATION_ID)
    assert service.calls[0] == (
        "get",
        "conversation-owner",
        CONVERSATION_ID,
    )
    assert invalid.status_code == hidden.status_code == 404
    assert invalid.json() == hidden.json() == {"code": "conversation_not_found"}


def test_append_accepts_only_user_content_and_returns_server_sequence_digest() -> None:
    service = FakeConversationService()

    response = client(service).post(
        f"/conversations/{CONVERSATION_ID}/messages",
        json={"content": CONTENT},
    )

    assert response.status_code == 201
    assert response.json() == {
        "schema_version": "1.0",
        "message_id": str(MESSAGE_ID),
        "conversation_id": str(CONVERSATION_ID),
        "sequence_no": 1,
        "role": "user",
        "content": CONTENT,
        "content_sha256": (
            "0cc5d73adccc0650eabbf2f6cdb352bb32b7adc63f867d0dabf7bc92c77ac6e5"
        ),
        "created_at": NOW.isoformat().replace("+00:00", "Z"),
    }
    assert service.append_commands == [
        AppendUserMessageCommand(
            owner_id="conversation-owner",
            conversation_id=CONVERSATION_ID,
            content=CONTENT,
        )
    ]


@pytest.mark.parametrize(
    "extra",
    (
        {"role": "assistant"},
        {"owner_id": "attacker-owner"},
        {"player_subject_id": "64000000-0000-4000-8000-000000000001"},
        {"puuid": "client-controlled"},
        {"source_task_id": "65000000-0000-4000-8000-000000000001"},
        {"source_run_id": "forged-run"},
    ),
)
def test_append_dto_cannot_forge_assistant_identity_or_sources(
    extra: dict[str, str],
) -> None:
    service = FakeConversationService()
    payload = {"content": CONTENT, **extra}

    response = client(service).post(
        f"/conversations/{CONVERSATION_ID}/messages",
        json=payload,
    )

    assert response.status_code == 422
    assert response.json() == {"code": "request_invalid"}
    assert service.append_commands == []


def test_archived_append_is_409_and_database_failure_is_sanitized() -> None:
    service = FakeConversationService()
    http = client(service)
    service.error = ConversationServiceError("conversation_archived")

    archived = http.post(
        f"/conversations/{CONVERSATION_ID}/messages",
        json={"content": CONTENT},
    )
    service.error = RuntimeError(
        "postgresql://secret@private.example/riftcoach body=" + CONTENT
    )
    unavailable = http.post(
        f"/conversations/{CONVERSATION_ID}/messages",
        json={"content": CONTENT},
    )

    assert archived.status_code == 409
    assert archived.json() == {"code": "conversation_archived"}
    assert unavailable.status_code == 503
    assert unavailable.json() == {"code": "service_unavailable"}
    assert "private.example" not in unavailable.text
    assert CONTENT not in unavailable.text


def test_message_body_never_enters_observability_or_logs(caplog) -> None:
    service = FakeConversationService()
    observability = TaskObservability(logger_name="riftcoach.test.conversation")
    caplog.set_level(logging.INFO, logger="riftcoach.test.conversation")

    response = client(service, observability=observability).post(
        f"/conversations/{CONVERSATION_ID}/messages",
        json={"content": CONTENT},
    )

    assert response.status_code == 201
    assert CONTENT not in caplog.text
    assert all(
        CONTENT not in str(event.metadata)
        for event in observability.events
    )


def test_list_messages_is_bounded_cursor_ordered_and_owner_scoped() -> None:
    service = FakeConversationService()
    http = client(service)

    response = http.get(
        f"/conversations/{CONVERSATION_ID}/messages",
        params={"limit": 25, "after_sequence": 7},
    )
    too_large = http.get(
        f"/conversations/{CONVERSATION_ID}/messages",
        params={"limit": 101},
    )
    negative_cursor = http.get(
        f"/conversations/{CONVERSATION_ID}/messages",
        params={"after_sequence": -1},
    )

    assert response.status_code == 200
    assert response.json()["limit"] == 25
    assert response.json()["after_sequence"] == 7
    assert response.json()["items"][0]["sequence_no"] == 8
    assert response.json()["has_more"] is False
    assert response.json()["next_after_sequence"] is None
    assert service.calls == [
        ("list", "conversation-owner", CONVERSATION_ID, 25, 7)
    ]
    assert too_large.status_code == negative_cursor.status_code == 422
    assert too_large.json() == negative_cursor.json() == {"code": "request_invalid"}


def test_archive_returns_readable_archived_view_and_hide_returns_no_body() -> None:
    service = FakeConversationService()
    http = client(service)

    archived = http.post(f"/conversations/{CONVERSATION_ID}/archive")
    hidden = http.post(f"/conversations/{CONVERSATION_ID}/hide")

    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
    assert hidden.status_code == 204
    assert hidden.content == b""
    assert service.calls == [
        ("archive", "conversation-owner", CONVERSATION_ID),
        ("hide", "conversation-owner", CONVERSATION_ID),
    ]


@pytest.mark.parametrize("operation", ("archive", "hide"))
def test_lifecycle_endpoints_reject_all_client_body_fields(operation: str) -> None:
    service = FakeConversationService()

    response = client(service).post(
        f"/conversations/{CONVERSATION_ID}/{operation}",
        json={"owner_id": "attacker-owner", "status": "hidden"},
    )

    assert response.status_code == 422
    assert response.json() == {"code": "request_invalid"}
    assert service.calls == []


@pytest.mark.parametrize(
    "path",
    (
        f"/conversations/{CONVERSATION_ID}/archive",
        f"/conversations/{CONVERSATION_ID}/hide",
    ),
)
def test_lifecycle_hidden_unowned_or_missing_is_safe_404(path: str) -> None:
    service = FakeConversationService()
    service.error = ConversationServiceError("conversation_not_found")

    response = client(service).post(path)

    assert response.status_code == 404
    assert response.json() == {"code": "conversation_not_found"}
