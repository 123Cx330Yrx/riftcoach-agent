from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.actor import StaticActorContextProvider
from app.api.main import create_app
from app.api.task_models import ReadinessResult
from app.lifecycle.models import (
    OwnerDataAffectedCounts,
    OwnerDataDeleteCommand,
    OwnerDataDeleteScope,
    OwnerDataDeletionMarker,
    OwnerDataDeletionStatus,
    OwnerDataExport,
    OwnerDataExportRecord,
    OwnerDataExportSection,
)
from tests.player_link_api_stubs import UnusedPlayerLinkService
from app.product.run_query import RunView
from app.tasks.models import ReviewTaskView, TaskStatus


NOW = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
TASK_ID = UUID("a0000000-0000-4000-8000-000000000001")


class _TaskService:
    def create(self, command):
        del command
        raise AssertionError("not used")

    def get_task(self, *, owner_id, task_id):
        del owner_id, task_id
        return ReviewTaskView(
            schema_version="1.0", task_id=TASK_ID, run_id="run", status=TaskStatus.QUEUED,
            created_at=NOW, updated_at=NOW, claimed_at=None, finished_at=None,
            terminal_reason=None, publication_status=None, report_available=False,
        )

    def get_task_by_run_id(self, *, owner_id, run_id):
        return self.get_task(owner_id=owner_id, task_id=TASK_ID)


class _Query:
    def get_run(self, run_id: str) -> RunView:
        raise AssertionError(run_id)

    def get_report(self, run_id: str) -> str:
        raise AssertionError(run_id)


class _Ready:
    def check(self) -> ReadinessResult:
        return ReadinessResult.ready()


class _Lifecycle:
    def __init__(self) -> None:
        self.commands: list[OwnerDataDeleteCommand] = []
        self.marker_id = uuid4()

    def export(self, *, owner_id: str) -> OwnerDataExport:
        return OwnerDataExport(
            owner_id=owner_id,
            generated_at=NOW,
            policy_version="owner-export-v1",
            sections=(
                OwnerDataExportSection(
                    name="conversations",
                    records=(
                        OwnerDataExportRecord(
                            record_kind="conversation", record_id=uuid4(), status="active", data={}
                        ),
                    ),
                ),
            ),
            total_record_count=1,
        )

    def delete(self, command: OwnerDataDeleteCommand) -> OwnerDataDeletionMarker:
        self.commands.append(command)
        return OwnerDataDeletionMarker(
            marker_id=self.marker_id,
            owner_id=command.owner_id,
            idempotency_key=command.idempotency_key,
            scope=command.scope,
            conversation_id=command.conversation_id,
            relationship_id=command.relationship_id,
            affected=OwnerDataAffectedCounts(conversations=1),
            status=OwnerDataDeletionStatus.COMPLETE,
            created_at=NOW,
            updated_at=NOW,
            completed_at=NOW,
        )

    def retry(self, *, owner_id: str, marker_id: UUID) -> OwnerDataDeletionMarker:
        return self.delete(
            OwnerDataDeleteCommand(
                owner_id=owner_id,
                idempotency_key="retry",
                scope=OwnerDataDeleteScope.CONVERSATION_ONLY,
                conversation_id=marker_id,
                requested_at=NOW,
            )
        )


def _client(lifecycle: _Lifecycle) -> TestClient:
    return TestClient(
        create_app(
            task_service=_TaskService(),
            player_link_service=UnusedPlayerLinkService(),
            query_service=_Query(),
            actor_provider=StaticActorContextProvider(owner_id="actor-owner", profile="test"),
            readiness_probe=_Ready(),
            owner_data_lifecycle_service=lifecycle,
        )
    )


def test_lifecycle_api_derives_owner_from_actor_and_is_body_safe() -> None:
    lifecycle = _Lifecycle()
    http = _client(lifecycle)

    exported = http.get("/owner-data/export")
    assert exported.status_code == 200
    assert exported.json()["owner_id"] == "actor-owner"

    response = http.post(
        "/owner-data/deletions",
        headers={"Idempotency-Key": "delete-1"},
        json={
            "scope": "conversation_only",
            "conversation_id": str(uuid4()),
            "owner_id": "attacker-owner",
        },
    )
    assert response.status_code == 422
    assert not lifecycle.commands

    conversation_id = uuid4()
    response = http.post(
        "/owner-data/deletions",
        headers={"Idempotency-Key": "delete-1"},
        json={"scope": "conversation_only", "conversation_id": str(conversation_id)},
    )
    assert response.status_code == 200
    assert lifecycle.commands[0].owner_id == "actor-owner"
    assert lifecycle.commands[0].conversation_id == conversation_id
    assert "owner_id" not in response.json().get("request", {})


def test_lifecycle_api_maps_invalid_marker_to_not_found() -> None:
    http = _client(_Lifecycle())
    response = http.post("/owner-data/deletions/not-a-uuid/retry")
    assert response.status_code == 404
    assert response.json() == {"code": "deletion_not_found"}
