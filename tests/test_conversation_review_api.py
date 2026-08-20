from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.actor import StaticActorContextProvider
from app.api.main import create_app
from app.api.task_models import ReadinessResult
from app.product.recent_review import ConversationRecentReviewRequest
from app.tasks.models import (
    CreateConversationReviewTaskCommand,
    ReviewTaskView,
    TaskCreateDisposition,
    TaskCreateResult,
    TaskStatus,
)
from app.tasks.service import TaskServiceError
from tests.player_link_api_stubs import UnusedPlayerLinkService


NOW = datetime(2026, 8, 20, 8, 0, 0, tzinfo=timezone.utc)
TASK_ID = UUID("83000000-0000-4000-8000-000000000001")
CONVERSATION_ID = UUID("83000000-0000-4000-8000-000000000002")
RUN_ID = "review_conversation_api_1"


class Ready:
    def check(self) -> ReadinessResult:
        return ReadinessResult.ready()


class UnusedRunQuery:
    def get_run(self, _run_id: str):
        raise AssertionError("task creation cannot query run data")

    def get_report(self, _run_id: str):
        raise AssertionError("task creation cannot query report data")


class FakeTaskService:
    def __init__(self) -> None:
        self.commands: list[CreateConversationReviewTaskCommand] = []
        self.error: TaskServiceError | None = None

    def create(self, _command):
        raise AssertionError("conversation route must not call legacy create")

    def get_task(self, **_kwargs):
        raise AssertionError("not used")

    def get_task_by_run_id(self, **_kwargs):
        raise AssertionError("not used")

    def create_conversation_review(
        self,
        command: CreateConversationReviewTaskCommand,
    ) -> TaskCreateResult:
        self.commands.append(command)
        if self.error is not None:
            raise self.error
        return TaskCreateResult(
            disposition=TaskCreateDisposition.CREATED,
            task=ReviewTaskView(
                schema_version="2.0",
                task_id=TASK_ID,
                run_id=RUN_ID,
                status=TaskStatus.QUEUED,
                created_at=NOW,
                updated_at=NOW,
                claimed_at=None,
                finished_at=None,
                terminal_reason=None,
                publication_status=None,
                report_available=False,
            ),
        )


def client(service: FakeTaskService) -> TestClient:
    return TestClient(
        create_app(
            task_service=service,
            player_link_service=UnusedPlayerLinkService(),
            query_service=UnusedRunQuery(),
            actor_provider=StaticActorContextProvider(
                owner_id="owner-1",
                profile="test",
            ),
            readiness_probe=Ready(),
        )
    )


def post(http: TestClient, payload: dict | None = None):
    return http.post(
        f"/conversations/{CONVERSATION_ID}/reviews/recent",
        headers={"Idempotency-Key": "conversation-review-1"},
        json=payload
        or {"count": 5, "queue": 420, "focus": "survival"},
    )


def test_post_uses_actor_and_path_but_body_only_contains_review_parameters() -> None:
    service = FakeTaskService()

    response = post(client(service))

    assert response.status_code == 202
    assert response.json() == {
        "schema_version": "2.0",
        "disposition": "created",
        "conversation_id": str(CONVERSATION_ID),
        "task_id": str(TASK_ID),
        "run_id": RUN_ID,
        "status": "queued",
        "links": {
            "task": f"/tasks/{TASK_ID}",
            "run": f"/runs/{RUN_ID}",
            "report": f"/runs/{RUN_ID}/report",
        },
    }
    assert service.commands == [
        CreateConversationReviewTaskCommand(
            owner_id="owner-1",
            idempotency_key="conversation-review-1",
            conversation_id=CONVERSATION_ID,
            request=ConversationRecentReviewRequest(
                count=5,
                queue=420,
                focus="survival",
            ),
        )
    ]
    assert "owner-1" not in response.text
    assert "puuid" not in response.text.lower()
    assert "player_subject_id" not in response.text
    assert "relationship_id" not in response.text


@pytest.mark.parametrize(
    "privileged",
    (
        "riot_id",
        "owner_id",
        "conversation_id",
        "relationship_id",
        "player_subject_id",
        "relationship_role",
        "puuid",
    ),
)
def test_body_cannot_override_server_derived_identity(privileged: str) -> None:
    service = FakeTaskService()

    response = post(
        client(service),
        {"count": 5, "queue": 420, "focus": "overall", privileged: "x"},
    )

    assert response.status_code == 422
    assert response.json() == {"code": "request_invalid"}
    assert service.commands == []


def test_invalid_or_unavailable_conversation_is_owner_safe_404() -> None:
    service = FakeTaskService()
    http = client(service)
    invalid = http.post(
        "/conversations/not-a-uuid/reviews/recent",
        headers={"Idempotency-Key": "conversation-review-1"},
        json={"count": 5},
    )
    service.error = TaskServiceError("conversation_not_found")
    missing = post(http, {"count": 5})

    assert invalid.status_code == missing.status_code == 404
    assert invalid.json() == missing.json() == {"code": "conversation_not_found"}


@pytest.mark.parametrize(
    ("code", "status", "public_code"),
    (
        ("idempotency_conflict", 409, "idempotency_conflict"),
        ("owner_capacity_exceeded", 503, "task_capacity_exceeded"),
        ("task_persistence_failed", 503, "service_unavailable"),
    ),
)
def test_service_failures_have_allowlisted_http_projection(
    code: str,
    status: int,
    public_code: str,
) -> None:
    service = FakeTaskService()
    service.error = TaskServiceError(code)  # type: ignore[arg-type]

    response = post(client(service))

    assert response.status_code == status
    assert response.json() == {"code": public_code}


def test_openapi_request_schema_has_no_identity_fields() -> None:
    document = client(FakeTaskService()).get("/openapi.json").json()
    operation = document["paths"][
        "/conversations/{conversation_id}/reviews/recent"
    ]["post"]
    schema_ref = operation["requestBody"]["content"]["application/json"][
        "schema"
    ]["$ref"]
    schema_name = schema_ref.rsplit("/", 1)[-1]
    properties = document["components"]["schemas"][schema_name]["properties"]

    assert set(properties) == {"count", "queue", "focus"}
