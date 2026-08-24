from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.actor import StaticActorContextProvider
from app.api.main import create_app
from app.api.task_models import ReadinessResult
from app.product.latest_review import (
    LatestProfileReview,
    LatestProfileReviewResult,
    LatestProfileReviewServiceError,
)
from app.product.run_query import (
    RecentAveragesView,
    RecentComparisonRowView,
    RecentSummaryView,
    RecentWinLossComparisonView,
    RunTimelineMatchView,
    RunTimelineView,
    RunQueryError,
    RunView,
)
from app.runtime.models import RuntimeStatus
from app.runtime.signals import RuntimePublicationStatus
from app.tasks.models import (
    ReviewTaskView,
    TaskPublicationStatus,
    TaskStatus,
)
from app.tasks.service import TaskServiceError
from tests.player_link_api_stubs import UnusedPlayerLinkService


NOW = datetime(2026, 8, 23, 11, 0, 0, tzinfo=timezone.utc)
PROFILE_ID = UUID("95000000-0000-4000-8000-000000000001")
TASK_ID = UUID("96000000-0000-4000-8000-000000000001")
RUN_ID = "review_live_workbench_1"


def task(
    status: TaskStatus,
    *,
    publication: TaskPublicationStatus | None = None,
    report_available: bool = False,
) -> ReviewTaskView:
    terminal = status.is_terminal
    return ReviewTaskView(
        schema_version="2.0",
        task_id=TASK_ID,
        run_id=RUN_ID,
        status=status,
        created_at=NOW,
        updated_at=NOW + timedelta(seconds=2),
        claimed_at=(NOW + timedelta(seconds=1) if status is not TaskStatus.QUEUED else None),
        finished_at=(NOW + timedelta(seconds=2) if terminal else None),
        terminal_reason=("review_finished" if terminal else None),
        publication_status=publication,
        report_available=report_available,
    )


def recent_summary(
    publication: RuntimePublicationStatus = RuntimePublicationStatus.PUBLISHED,
) -> RecentSummaryView:
    row = RecentComparisonRowView(
        cs_per_min=8.0,
        gold_per_min=410.0,
        damage_per_min=550.0,
        vision_score=21.0,
        deaths_before_15=0.5,
    )
    return RecentSummaryView(
        run_id=RUN_ID,
        skill_version="0.2.0",
        runtime_status=RuntimeStatus.COMPLETED,
        publication_status=publication,
        terminal_reason=(
            "quality_gate_passed"
            if publication is RuntimePublicationStatus.PUBLISHED
            else "deterministic_fallback"
        ),
        games_analyzed=2,
        wins=1,
        losses=1,
        win_rate=50.0,
        main_role="MIDDLE",
        main_champions=("Ahri", "Akali"),
        averages=RecentAveragesView(
            kda=3.2,
            cs_per_min=8.0,
            gold_per_min=410.0,
            damage_per_min=550.0,
            vision_score=21.0,
            kill_participation_percent=62.0,
            damage_share_percent=27.0,
            gold_share_percent=24.0,
            deaths_before_15=0.5,
        ),
        win_loss_comparison=RecentWinLossComparisonView(
            wins=row,
            losses=row,
        ),
    )


def run_timeline() -> RunTimelineView:
    return RunTimelineView(
        run_id=RUN_ID,
        skill_version="0.2.0",
        runtime_status=RuntimeStatus.COMPLETED,
        publication_status=RuntimePublicationStatus.PUBLISHED,
        terminal_reason="quality_gate_passed",
        timeline_status="available",
        total_matches=1,
        projected_matches=1,
        matches=(
            RunTimelineMatchView(
                match_id="EUW1_123",
                champion_name="Ahri",
                role="MIDDLE",
                win=True,
                game_duration_seconds=1800,
                included_in_aggregate=True,
                timeline_status="available",
                unavailable_reason=None,
                total_events=0,
                projected_events=0,
                events_truncated=False,
                events=(),
            ),
        ),
    )


class ReadyProbe:
    def check(self) -> ReadinessResult:
        return ReadinessResult.ready()


class LatestService:
    def __init__(self, result=None, error=None) -> None:
        self.result = result
        self.error = error
        self.calls: list[tuple[str, UUID]] = []

    def get_latest(self, *, owner_id: str, player_profile_id: UUID):
        self.calls.append((owner_id, player_profile_id))
        if self.error is not None:
            raise self.error
        return self.result


class TaskService:
    def __init__(self, value: ReviewTaskView | None = None, error=None) -> None:
        self.value = value or task(TaskStatus.QUEUED)
        self.error = error

    def create(self, command):
        del command
        raise AssertionError("POST is not part of this test")

    def get_task(self, *, owner_id: str, task_id: UUID):
        del owner_id, task_id
        return self.value

    def get_task_by_run_id(self, *, owner_id: str, run_id: str):
        del owner_id, run_id
        if self.error is not None:
            raise self.error
        return self.value


class QueryService:
    def __init__(self, value: RecentSummaryView | None = None, error=None) -> None:
        self.value = value or recent_summary()
        self.error = error
        self.summary_calls: list[str] = []
        self.timeline_calls: list[str] = []

    def get_run(self, run_id: str) -> RunView:
        del run_id
        raise AssertionError("run endpoint is not part of this test")

    def get_report(self, run_id: str) -> str:
        del run_id
        raise AssertionError("report endpoint is not part of this test")

    def get_recent_summary(self, run_id: str) -> RecentSummaryView:
        self.summary_calls.append(run_id)
        if self.error is not None:
            raise self.error
        return self.value

    def get_timeline(self, run_id: str) -> RunTimelineView:
        self.timeline_calls.append(run_id)
        if self.error is not None:
            raise self.error
        return run_timeline()


def client(
    *,
    latest_service=None,
    task_service=None,
    query_service=None,
) -> TestClient:
    return TestClient(
        create_app(
            task_service=task_service or TaskService(),
            player_link_service=UnusedPlayerLinkService(),
            query_service=query_service or QueryService(),
            latest_profile_review_service=latest_service,
            actor_provider=StaticActorContextProvider(
                owner_id="live-owner",
                profile="test",
            ),
            readiness_probe=ReadyProbe(),
        )
    )


def locator_result(
    latest: LatestProfileReview | None,
) -> LatestProfileReviewResult:
    return LatestProfileReviewResult(
        player_profile_id=PROFILE_ID,
        latest_review=latest,
    )


def test_latest_locator_returns_null_as_legal_empty_state() -> None:
    service = LatestService(locator_result(None))

    response = client(latest_service=service).get(
        f"/player-profiles/{PROFILE_ID}/reviews/recent/latest"
    )

    assert response.status_code == 200
    assert response.json() == {
        "schema_version": "1.0",
        "player_profile_id": str(PROFILE_ID),
        "latest_review": None,
    }
    assert service.calls == [("live-owner", PROFILE_ID)]


def test_latest_locator_builds_only_relative_allowlisted_links() -> None:
    latest = LatestProfileReview(
        task_id=TASK_ID,
        run_id=RUN_ID,
        status=TaskStatus.RUNNING,
        created_at=NOW,
        updated_at=NOW + timedelta(seconds=1),
        publication_status=None,
        report_available=False,
    )

    response = client(
        latest_service=LatestService(locator_result(latest))
    ).get(f"/player-profiles/{PROFILE_ID}/reviews/recent/latest")

    assert response.status_code == 200
    body = response.json()
    assert body["latest_review"]["task_id"] == str(TASK_ID)
    assert body["latest_review"]["run_id"] == RUN_ID
    assert body["latest_review"]["status"] == "running"
    assert body["latest_review"]["links"] == {
        "task": f"/tasks/{TASK_ID}",
        "events": f"/tasks/{TASK_ID}/events",
        "stream": f"/tasks/{TASK_ID}/events/stream",
        "run": f"/runs/{RUN_ID}",
        "summary": f"/runs/{RUN_ID}/recent-summary",
        "timeline": f"/runs/{RUN_ID}/timeline",
        "report": f"/runs/{RUN_ID}/report",
        "product_state": f"/runs/{RUN_ID}/product-state",
        "evidence": f"/runs/{RUN_ID}/evidence",
    }
    serialized = response.text
    for forbidden in ("owner", "puuid", "conversation", "worker", "lease", "path"):
        assert forbidden not in serialized.lower()


@pytest.mark.parametrize(
    ("path_id", "service_error", "status", "code"),
    (
        ("not-a-uuid", None, 404, "player_profile_not_found"),
        (
            str(PROFILE_ID),
            LatestProfileReviewServiceError("player_profile_not_found"),
            404,
            "player_profile_not_found",
        ),
        (
            str(PROFILE_ID),
            LatestProfileReviewServiceError("latest_review_unavailable"),
            503,
            "service_unavailable",
        ),
    ),
)
def test_latest_locator_maps_not_found_and_unavailable_body_free(
    path_id: str,
    service_error,
    status: int,
    code: str,
) -> None:
    response = client(
        latest_service=LatestService(error=service_error)
    ).get(f"/player-profiles/{path_id}/reviews/recent/latest")

    assert response.status_code == status
    assert response.json() == {"code": code}


@pytest.mark.parametrize(
    ("task_value", "expected_status", "expected_code"),
    (
        (task(TaskStatus.QUEUED), 409, "run_not_ready"),
        (task(TaskStatus.RUNNING), 409, "run_not_ready"),
        (task(TaskStatus.RECOVERY_REQUIRED), 409, "run_not_ready"),
        (task(TaskStatus.FAILED), 409, "run_not_available"),
        (task(TaskStatus.CANCELLED), 409, "run_not_available"),
        (
            task(
                TaskStatus.SUCCEEDED,
                publication=TaskPublicationStatus.REJECTED,
                report_available=False,
            ),
            409,
            "report_not_available",
        ),
    ),
)
def test_recent_summary_obeys_task_and_publication_state(
    task_value: ReviewTaskView,
    expected_status: int,
    expected_code: str,
) -> None:
    query = QueryService()

    response = client(
        task_service=TaskService(task_value),
        query_service=query,
    ).get(f"/runs/{RUN_ID}/recent-summary")

    assert response.status_code == expected_status
    assert response.json() == {"code": expected_code, "run_id": RUN_ID}
    assert query.summary_calls == []


def test_timeline_is_owner_gated_and_projects_a_typed_safe_response() -> None:
    service = QueryService()

    response = client(
        task_service=TaskService(
            task(
                TaskStatus.SUCCEEDED,
                publication=TaskPublicationStatus.PUBLISHED,
                report_available=True,
            )
        ),
        query_service=service,
    ).get(f"/runs/{RUN_ID}/timeline")

    assert response.status_code == 200
    assert response.json() == {
        "schema_version": "1.0",
        "run_id": RUN_ID,
        "skill_name": "recent-form-review",
        "skill_version": "0.2.0",
        "runtime_status": "completed",
        "publication_status": "published",
        "terminal_reason": "quality_gate_passed",
        "source": "riot_match_v5_timeline",
        "timeline_status": "available",
        "total_matches": 1,
        "projected_matches": 1,
        "matches_truncated": False,
        "matches": [
            {
                "match_id": "EUW1_123",
                "champion_name": "Ahri",
                "role": "MIDDLE",
                "win": True,
                "game_duration_seconds": 1800,
                "included_in_aggregate": True,
                "timeline_status": "available",
                "unavailable_reason": None,
                "total_events": 0,
                "projected_events": 0,
                "events_truncated": False,
                "events": [],
            }
        ],
    }
    assert service.timeline_calls == [RUN_ID]
    for forbidden in ("owner", "puuid", "artifact", "path", "timeline_error"):
        assert forbidden not in response.text.lower()


@pytest.mark.parametrize(
    ("task_value", "expected_status", "expected_code"),
    (
        (task(TaskStatus.RUNNING), 409, "run_not_ready"),
        (task(TaskStatus.FAILED), 409, "run_not_available"),
        (
            task(
                TaskStatus.SUCCEEDED,
                publication=TaskPublicationStatus.REJECTED,
                report_available=False,
            ),
            409,
            "report_not_available",
        ),
    ),
)
def test_timeline_obeys_terminal_publication_gate(
    task_value: ReviewTaskView,
    expected_status: int,
    expected_code: str,
) -> None:
    query = QueryService()
    response = client(
        task_service=TaskService(task_value),
        query_service=query,
    ).get(
        f"/runs/{RUN_ID}/timeline"
    )

    assert response.status_code == expected_status
    assert response.json() == {"code": expected_code, "run_id": RUN_ID}
    assert query.timeline_calls == []


def test_timeline_maps_cross_owner_and_projection_identity_failure_body_free() -> None:
    not_found = client(
        task_service=TaskService(error=TaskServiceError("task_not_found"))
    ).get(f"/runs/{RUN_ID}/timeline")
    mismatched = run_timeline().model_copy(update={"run_id": "review_other"})
    service = QueryService()
    service.get_timeline = lambda _run_id: mismatched
    integrity = client(
        task_service=TaskService(
            task(
                TaskStatus.SUCCEEDED,
                publication=TaskPublicationStatus.PUBLISHED,
                report_available=True,
            )
        ),
        query_service=service,
    ).get(f"/runs/{RUN_ID}/timeline")

    assert not_found.status_code == 404
    assert not_found.json() == {"code": "run_not_found"}
    assert integrity.status_code == 500
    assert integrity.json() == {"code": "run_integrity_failed", "run_id": RUN_ID}


@pytest.mark.parametrize(
    "publication",
    (TaskPublicationStatus.PUBLISHED, TaskPublicationStatus.DEGRADED),
)
def test_recent_summary_projects_verified_typed_view(
    publication: TaskPublicationStatus,
) -> None:
    runtime_publication = RuntimePublicationStatus(publication.value)
    query = QueryService(recent_summary(runtime_publication))

    response = client(
        task_service=TaskService(
            task(
                TaskStatus.SUCCEEDED,
                publication=publication,
                report_available=True,
            )
        ),
        query_service=query,
    ).get(f"/runs/{RUN_ID}/recent-summary")

    assert response.status_code == 200
    assert response.json()["run_id"] == RUN_ID
    assert response.json()["publication_status"] == publication.value
    assert response.json()["main_champions"] == ["Ahri", "Akali"]
    assert query.summary_calls == [RUN_ID]
    for forbidden in ("owner", "puuid", "artifact", "path", "prompt"):
        assert forbidden not in response.text.lower()


def test_recent_summary_maps_cross_owner_and_integrity_failure() -> None:
    not_found = client(
        task_service=TaskService(error=TaskServiceError("task_not_found"))
    ).get(f"/runs/{RUN_ID}/recent-summary")
    integrity = client(
        task_service=TaskService(
            task(
                TaskStatus.SUCCEEDED,
                publication=TaskPublicationStatus.PUBLISHED,
                report_available=True,
            )
        ),
        query_service=QueryService(
            error=RunQueryError("run_integrity_failed")
        ),
    ).get(f"/runs/{RUN_ID}/recent-summary")

    assert not_found.status_code == 404
    assert not_found.json() == {"code": "run_not_found"}
    assert integrity.status_code == 500
    assert integrity.json() == {"code": "run_integrity_failed", "run_id": RUN_ID}


def test_recent_summary_missing_optional_query_capability_fails_closed() -> None:
    class LegacyQuery:
        def get_run(self, run_id: str):
            del run_id

        def get_report(self, run_id: str):
            del run_id

    response = client(
        task_service=TaskService(
            task(
                TaskStatus.SUCCEEDED,
                publication=TaskPublicationStatus.PUBLISHED,
                report_available=True,
            )
        ),
        query_service=LegacyQuery(),
    ).get(f"/runs/{RUN_ID}/recent-summary")

    assert response.status_code == 503
    assert response.json() == {"code": "service_unavailable", "run_id": RUN_ID}
