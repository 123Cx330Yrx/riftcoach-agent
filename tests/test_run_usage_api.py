"""Usage is visible to the owner without granting access to cancelled reports."""
import pytest

from app.product.run_query import RunQueryError, RunView
from app.runtime.models import RuntimeStatus, RuntimeUsage
from app.tasks.models import TaskStatus
from app.tasks.service import TaskServiceError
from tests.test_live_workbench_api import client, QueryService, TaskService, task, RUN_ID


class UsageQuery(QueryService):
    def __init__(self, *, error=None, usage=None, run_id=RUN_ID):
        super().__init__()
        self.failure, self.usage, self.run_id = error, usage, run_id
        self.calls = []

    def get_run(self, run_id):
        self.calls.append(run_id)
        if self.failure:
            raise self.failure
        return RunView(run_id=self.run_id, runtime_status=RuntimeStatus.FAILED,
            terminal_reason="task_dispatch_stopped", usage=self.usage, report_available=False)


@pytest.mark.parametrize("status", [TaskStatus.CANCELLED, TaskStatus.FAILED])
def test_stopped_task_exposes_observations_without_report(status):
    usage = RuntimeUsage(provider_calls_attempted=1, provider_responses_observed=0,
        observed_input_tokens=0, observed_output_tokens=0,
        input_tokens=None, output_tokens=None, token_observation="unknown",
        tool_calls=0, tool_attempts=0, tool_latency_ms=0, cost_observation="not_configured")
    query = UsageQuery(usage=usage)
    api = client(task_service=TaskService(task(status)), query_service=query)
    result = api.get(f"/runs/{RUN_ID}/usage")
    assert result.status_code == 200
    assert set(result.json()) == {"schema_version", "run_id", "task_status", "usage"}
    assert result.json()["task_status"] == status.value
    assert result.json()["usage"]["provider_calls_attempted"] == 1
    assert result.json()["usage"]["input_tokens"] is None
    assert result.json()["usage"]["cost"] is None
    assert api.get(f"/runs/{RUN_ID}").status_code == 409
    assert api.get(f"/runs/{RUN_ID}/report").status_code == 409
    assert query.calls == [RUN_ID]


@pytest.mark.parametrize("status", [TaskStatus.CANCELLED, TaskStatus.FAILED, TaskStatus.SUCCEEDED])
def test_missing_receipt_is_unknown_only_for_unsuccessful_task(status):
    api = client(task_service=TaskService(task(status)),
        query_service=UsageQuery(error=RunQueryError("run_not_found")))
    response = api.get(f"/runs/{RUN_ID}/usage")
    assert response.status_code == (500 if status is TaskStatus.SUCCEEDED else 200)
    if response.status_code == 200:
        assert response.json()["usage"] is None


@pytest.mark.parametrize("query", [UsageQuery(error=RunQueryError("run_integrity_failed")),
    UsageQuery(error=RuntimeError("private disk path must not escape")), UsageQuery(run_id="other_run")])
def test_corruption_or_wrong_run_is_not_hidden_as_unknown(query):
    response = client(task_service=TaskService(task(TaskStatus.CANCELLED)),
        query_service=query).get(f"/runs/{RUN_ID}/usage")
    assert response.status_code == 500
    assert response.json() == {"code": "run_integrity_failed", "run_id": RUN_ID}


@pytest.mark.parametrize("status", [TaskStatus.QUEUED, TaskStatus.RUNNING, TaskStatus.RECOVERY_REQUIRED])
def test_inflight_does_not_read_incomplete_disk_evidence(status):
    query = UsageQuery()
    response = client(task_service=TaskService(task(status)), query_service=query).get(f"/runs/{RUN_ID}/usage")
    assert response.status_code == 409
    assert not query.calls


def test_foreign_or_missing_task_does_not_read_disk():
    query = UsageQuery()
    response = client(task_service=TaskService(error=TaskServiceError("task_not_found")),
        query_service=query).get(f"/runs/{RUN_ID}/usage")
    assert response.status_code == 404
    assert not query.calls
