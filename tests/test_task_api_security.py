from __future__ import annotations

from collections.abc import Mapping

import pytest
from fastapi.testclient import TestClient

from app.api.actor import StaticActorContextProvider
from app.api.composition import load_api_composition_settings
from app.api.main import create_app
from app.api.task_models import ReadinessResult
from app.product.run_query import RunView
from app.runtime.models import RuntimeStatus
from app.tasks.models import TaskCreateDisposition, TaskCreateResult, TaskStatus
from app.tasks.models import TaskDeleteDisposition, TaskDeletionResult
from uuid import UUID


def _fake_task_service():
    class Service:
        def create(self, command):
            del command
            from uuid import UUID
            from datetime import datetime, timezone
            from app.tasks.models import ReviewTaskView

            task = ReviewTaskView(
                task_id=UUID("30000000-0000-4000-8000-000000000001"),
                run_id="review_security_1",
                status=TaskStatus.QUEUED,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                claimed_at=None,
                finished_at=None,
                terminal_reason=None,
                publication_status=None,
                report_available=False,
            )
            return TaskCreateResult(
                disposition=TaskCreateDisposition.CREATED,
                task=task,
            )

        def get_task(self, *, owner_id, task_id):
            raise RuntimeError("postgres://secret@private")

        def get_task_by_run_id(self, *, owner_id, run_id):
            raise RuntimeError("postgres://secret@private")

    return Service()


class _Query:
    def get_run(self, run_id: str) -> RunView:
        raise RuntimeError("report body and provider secret")

    def get_report(self, run_id: str) -> str:
        raise RuntimeError("report body and provider secret")


class _Ready:
    def check(self) -> ReadinessResult:
        return ReadinessResult.ready()


class _Deletion:
    def __init__(self, disposition: TaskDeleteDisposition) -> None:
        self.disposition = disposition

    def delete(self, *, owner_id: str, task_id: UUID) -> TaskDeletionResult:
        del owner_id
        return TaskDeletionResult(
            disposition=self.disposition,
            task_id=task_id,
            run_id=(
                None
                if self.disposition is TaskDeleteDisposition.ALREADY_HIDDEN
                else "review_security_delete"
            ),
        )


def test_production_wildcard_credentials_is_rejected() -> None:
    with pytest.raises(ValueError, match="wildcard"):
        load_api_composition_settings(
            {
                "RIFTCOACH_API_PROFILE": "production",
                "RIFTCOACH_LOCAL_OWNER_ID": "",
                "RIFTCOACH_CORS_ORIGINS": "*",
                "RIFTCOACH_CORS_ALLOW_CREDENTIALS": "true",
            }
        )


def test_capacity_configuration_is_bounded_and_reaches_composition_settings() -> None:
    settings = load_api_composition_settings(
        {
            "RIFTCOACH_API_PROFILE": "test",
            "RIFTCOACH_LOCAL_OWNER_ID": "owner-1",
            "RIFTCOACH_TASK_OWNER_ACTIVE_LIMIT": "4",
            "RIFTCOACH_TASK_GLOBAL_ACTIVE_LIMIT": "20",
        }
    )

    assert settings.task_capacity.owner_active_limit == 4
    assert settings.task_capacity.global_active_limit == 20

    with pytest.raises(ValueError, match="positive integer"):
        load_api_composition_settings(
            {
                "RIFTCOACH_API_PROFILE": "test",
                "RIFTCOACH_LOCAL_OWNER_ID": "owner-1",
                "RIFTCOACH_TASK_OWNER_ACTIVE_LIMIT": "0",
            }
        )


def test_cors_is_closed_by_default_and_explicit_origins_are_reflected() -> None:
    app = create_app(
        task_service=_fake_task_service(),
        query_service=_Query(),
        actor_provider=StaticActorContextProvider(
            owner_id="owner-1", profile="test"
        ),
        readiness_probe=_Ready(),
    )
    with TestClient(app) as client:
        closed = client.get("/health/live", headers={"Origin": "https://evil.example"})
        assert "access-control-allow-origin" not in closed.headers

    configured = create_app(
        task_service=_fake_task_service(),
        query_service=_Query(),
        actor_provider=StaticActorContextProvider(
            owner_id="owner-1", profile="test"
        ),
        readiness_probe=_Ready(),
        cors_origins=("https://coach.example",),
    )
    with TestClient(configured) as client:
        response = client.get(
            "/health/live",
            headers={"Origin": "https://coach.example"},
        )
        assert response.headers["access-control-allow-origin"] == (
            "https://coach.example"
        )
        assert "access-control-allow-credentials" not in response.headers


def test_public_error_projection_does_not_echo_exception_body() -> None:
    app = create_app(
        task_service=_fake_task_service(),
        query_service=_Query(),
        actor_provider=StaticActorContextProvider(
            owner_id="owner-1", profile="test"
        ),
        readiness_probe=_Ready(),
    )
    with TestClient(app) as client:
        response = client.get("/tasks/not-a-uuid")

    assert response.status_code == 404
    assert "secret" not in response.text.lower()
    assert "private" not in response.text.lower()


def test_delete_endpoint_projects_active_conflict_without_canceling() -> None:
    app = create_app(
        task_service=_fake_task_service(),
        query_service=_Query(),
        actor_provider=StaticActorContextProvider(
            owner_id="owner-1", profile="test"
        ),
        readiness_probe=_Ready(),
        deletion_service=_Deletion(TaskDeleteDisposition.ACTIVE_CONFLICT),
    )
    with TestClient(app) as client:
        response = client.delete(
            "/tasks/30000000-0000-4000-8000-000000000001"
        )

    assert response.status_code == 409
    assert response.json() == {"code": "task_delete_conflict"}


@pytest.mark.parametrize(
    ("disposition", "status_code", "pending"),
    (
        (TaskDeleteDisposition.DELETED, 200, False),
        (TaskDeleteDisposition.CLEANUP_PENDING, 202, True),
        (TaskDeleteDisposition.ALREADY_HIDDEN, 200, False),
    ),
)
def test_delete_endpoint_distinguishes_hidden_and_cleanup_pending(
    disposition: TaskDeleteDisposition,
    status_code: int,
    pending: bool,
) -> None:
    app = create_app(
        task_service=_fake_task_service(),
        query_service=_Query(),
        actor_provider=StaticActorContextProvider(
            owner_id="owner-1", profile="test"
        ),
        readiness_probe=_Ready(),
        deletion_service=_Deletion(disposition),
    )
    with TestClient(app) as client:
        response = client.delete(
            "/tasks/30000000-0000-4000-8000-000000000001"
        )

    assert response.status_code == status_code
    assert response.json()["cleanup_pending"] is pending
