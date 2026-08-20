from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.actor import StaticActorContextProvider
from app.api.main import create_app
from app.api.task_models import ReadinessResult
from app.memory.training_models import TrainingPlanPage, TrainingProgressPage
from app.memory.training_service import TrainingQueryServiceError
from tests.test_training_service import RELATIONSHIP_ID, _plan, _progress


OWNER = "training-api-owner"


class UnusedTaskService:
    def create(self, command): raise AssertionError
    def get_task(self, **kwargs): raise AssertionError
    def get_task_by_run_id(self, **kwargs): raise AssertionError


class UnusedPlayerLinkService:
    def create(self, command): raise AssertionError
    def get_link(self, **kwargs): raise AssertionError


class UnusedRunQuery:
    def get_run(self, run_id): raise AssertionError
    def get_report(self, run_id): raise AssertionError


class ReadyProbe:
    def check(self): return ReadinessResult.ready()


class FakeTrainingQueryService:
    def __init__(self) -> None:
        self.calls = []
        self.error = None

    def plans(self, **kwargs):
        self.calls.append(("plans", kwargs))
        if self.error: raise self.error
        return TrainingPlanPage(plans=(_plan(),))

    def progress(self, **kwargs):
        self.calls.append(("progress", kwargs))
        if self.error: raise self.error
        return TrainingProgressPage(events=(_progress(),), trends=())


def _client(service=None, *, inject=True):
    kwargs = {}
    if inject:
        kwargs["training_query_service"] = service or FakeTrainingQueryService()
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


def test_training_routes_use_trusted_owner_and_bounded_query():
    service = FakeTrainingQueryService()
    http = _client(service)
    plan = http.get(f"/memory/players/{RELATIONSHIP_ID}/training-plan?include_history=true&limit=25")
    progress = http.get(f"/memory/players/{RELATIONSHIP_ID}/training-progress?metric_key=deaths_before_15&limit=10")
    assert plan.status_code == 200
    assert plan.json()["plans"][0]["status"] == "active"
    assert progress.status_code == 200
    assert progress.json()["events"][0]["source_artifact_sha256"] == "a" * 64
    assert service.calls[0][1]["owner_id"] == OWNER
    assert service.calls[1][1]["metric_key"] == "deaths_before_15"
    for body in (plan.json(), progress.json()):
        rendered = str(body).lower()
        assert "puuid" not in rendered
        assert "relative_path" not in rendered
        assert "source_candidate_id" not in rendered


def test_training_routes_fail_closed_and_validate_bounds():
    service = FakeTrainingQueryService()
    service.error = TrainingQueryServiceError("training_scope_not_found")
    missing = _client(service).get(f"/memory/players/{RELATIONSHIP_ID}/training-plan")
    assert missing.status_code == 404
    assert missing.json() == {"code": "training_scope_not_found"}
    unavailable = _client(inject=False).get(f"/memory/players/{RELATIONSHIP_ID}/training-plan")
    assert unavailable.status_code == 503
    assert unavailable.json() == {"code": "service_unavailable"}
    assert _client().get(f"/memory/players/{RELATIONSHIP_ID}/training-progress?limit=0").status_code == 422
    assert _client().get(f"/memory/players/{RELATIONSHIP_ID}/training-progress?metric_key=bad%20metric").status_code == 422


def test_training_openapi_has_two_read_only_routes():
    document = _client().get("/openapi.json").json()
    plan_path = "/memory/players/{relationship_id}/training-plan"
    progress_path = "/memory/players/{relationship_id}/training-progress"
    assert set(document["paths"][plan_path]) == {"get"}
    assert set(document["paths"][progress_path]) == {"get"}
