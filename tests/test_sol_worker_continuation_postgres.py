"""Actual SQL/API/ordinary composition, scripted models and disposable DB only."""
from pathlib import Path
from uuid import UUID

import pytest
import sqlalchemy as sa

from app.evaluation import sol_review_contract
from app.providers.zhipu_profiles import ZHIPU_GLM53_FLASH_MODEL, ZHIPU_STANDARD_BASE_URL
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.tasks.continuation import WORKER_SOL_PROFILE
from app.tasks.reliable_runtime import TaskLeasePolicy
from app.workers.composition import compose_continuation_executor, load_worker_composition_settings
from app.workers.review_worker import ReviewWorker
from tests.test_evidence_product_api_postgres import migrated_product_api
from tests.test_natural_duty_worker_postgres import no_external_services
from tests.test_sol_natural_candidate import application
from tests.test_native_editor_product_budget import SummaryBuilder
from tests.test_worker_composition import valid_environment


@pytest.fixture
def continued_api(migrated_product_api):
    try:
        yield migrated_product_api
    finally:
        # The disposable fixture downgrades through the old enum constraint.
        # New-history databases deliberately refuse that destructive downgrade.
        repo = migrated_product_api[2]
        with repo._session_factory() as session, session.begin():
            session.execute(sa.text("DELETE FROM review_task_events WHERE event_kind = 'continuation_resumed'"))


def setup_worker(tmp_path, monkeypatch, repository, *, mode="pass", statuses=()):
    env = valid_environment(tmp_path)
    env.update(LLM_MODEL=ZHIPU_GLM53_FLASH_MODEL, LLM_BASE_URL=ZHIPU_STANDARD_BASE_URL,
        RIFTCOACH_RUNS_ROOT=str(tmp_path), RIFTCOACH_WORKER_EXECUTION_PROFILE=WORKER_SOL_PROFILE,
        RIFTCOACH_SOL_REVIEW_API_KEY="OFFLINE_SENTINEL")
    settings = load_worker_composition_settings(env)
    _, probe, _, _ = application(tmp_path / "probe", mode=mode, candidate=sol_review_contract)

    class Summary(SummaryBuilder):
        reads = 0
        def build(self, **kwargs):
            self.reads += 1
            return super().build(**kwargs)

    summary = Summary(probe.descriptor.generator.req.player_summary)
    factories, requests = [], []

    def factory(**kwargs):
        assert kwargs["contract_module"] is sol_review_contract
        # Every reconstruction is a fresh provider instance; transport receipts
        # and CandidateSession alone carry successful state across leases.
        _, value, _, calls = application(Path(kwargs["transport_root"]).parent,
            mode=mode, statuses=statuses if not factories else (), candidate=sol_review_contract)
        factories.append(value)
        requests.append(calls)
        return value

    monkeypatch.setattr("app.runtime.sol_natural_provider.SolNaturalProviderFactory", factory)

    class Legacy:
        def execute(self, task):
            pytest.fail("candidate task reached legacy application")

    def worker():
        executor = compose_continuation_executor(settings, repository=repository,
            legacy=Legacy(), summary_builder=summary,
            knowledge=LocalHybridKnowledgeProvider.from_directory(Path("data/rag_docs")))
        return ReviewWorker(repository=repository, executor=executor, worker_id="sol-continuation-worker",
            continuation_store=executor.store,
            lease_policy=TaskLeasePolicy(lease_seconds=360, heartbeat_seconds=60)), executor

    return worker, summary, factories, requests


def create(owner):
    response = owner.post("/reviews/recent", headers={"Idempotency-Key": "sol-continuation"},
        json={"riot_id": "DemoPlayer#TEST", "routing_region": "asia", "focus": "overall"})
    assert response.status_code == 202
    return response.json()["task_id"], response.json()["run_id"]


def resume(owner, task, pin, key, manual=False):
    return owner.post(f"/tasks/{task}/resume", headers={"Idempotency-Key": key},
        json={"checkpoint_sha256": pin, "manual_retry": manual})


@pytest.mark.parametrize("cancel_paused", [False, True])
def test_timeout_owner_resume_retains_success_and_cost(continued_api, tmp_path, monkeypatch, cancel_paused):
    owner, other, repo, _ = continued_api
    task, run = create(owner)
    make, summary, factories, requests = setup_worker(tmp_path, monkeypatch, repo, statuses=(524,))
    worker, _ = make()
    assert worker.run_once().status.value == "paused"
    paused = owner.get(f"/tasks/{task}/continuation")
    assert paused.status_code == 200, paused.text
    original = paused.json()
    assert original["reason"] == "session_timeout_awaiting_manual_retry"
    assert original["session_accounting"]["known_tokens"] == 40
    assert original["session_accounting"]["requests_reserved"] == 3
    unknown = original["session_accounting"]["unknown_token_reservation"]
    assert unknown > 0
    assert other.get(f"/tasks/{task}/continuation").status_code == 404
    assert resume(other, task, original["checkpoint_sha256"], "foreign", True).status_code == 404
    assert resume(owner, task, "0" * 64, "stale", True).status_code == 409
    assert worker.run_once().status.value == "idle"
    if cancel_paused:
        cancelled = owner.post(f"/tasks/{task}/cancel", headers={"Idempotency-Key": "cancel-paused"})
        assert cancelled.status_code == 200, cancelled.text
        assert cancelled.json()["status"] == "cancelled"
        assert resume(owner, task, original["checkpoint_sha256"], "after-cancel").status_code == 409
    else:
        assert resume(owner, task, original["checkpoint_sha256"], "ordinary").status_code == 200
        worker, _ = make()
        assert worker.run_once().status.value == "paused"
        assert requests == [[524], []]
        current = owner.get(f"/tasks/{task}/continuation").json()
        assert resume(owner, task, current["checkpoint_sha256"], "manual", True).status_code == 200
        duplicate = resume(owner, task, current["checkpoint_sha256"], "manual", True)
        assert duplicate.status_code == 200 and duplicate.json()["replayed"]
        worker, _ = make()
        assert worker.run_once().status.value == "succeeded"
        assert requests == [[524], [], [200, 200]]
        assert worker.run_once().status.value == "idle"
        # No duplicate final claim, even when a client retries the resume POST.
        assert resume(owner, task, current["checkpoint_sha256"], "manual", True).json()["replayed"]
        events = owner.get(f"/tasks/{task}/events?limit=100")
        assert events.status_code == 200, events.text
        assert [v["event_kind"] for v in events.json()["events"]].count("continuation_resumed") == 2
    assert summary.reads == 1
    usage = owner.get(f"/runs/{run}/usage")
    assert usage.status_code == 200, usage.text
    assert usage.json()["usage"] is None
    total = usage.json()["session_accounting"]
    assert total["known_tokens"] == (40 if cancel_paused else 80)
    assert total["unknown_token_reservation"] == unknown
    assert total["requests_reserved"] == (3 if cancel_paused else 5)
    assert total["retries"] == (0 if cancel_paused else 1)
    assert other.get(f"/runs/{run}/usage").status_code == 404
    assert not repo.get_by_task_id(owner_id="owner-1", task_id=UUID(task)).report_available


def test_repair_across_worker_restart_keeps_one_application(continued_api, tmp_path, monkeypatch):
    owner, _, repo, _ = continued_api
    task, run = create(owner)
    make, summary, _, requests = setup_worker(tmp_path, monkeypatch, repo, mode="repair")
    first, route = make()
    route.candidate.max_new_models = 3
    assert first.run_once().status.value == "paused"
    pin = owner.get(f"/tasks/{task}/continuation").json()["checkpoint_sha256"]
    assert resume(owner, task, pin, "continue").status_code == 200
    second, _ = make()
    assert second.run_once().status.value == "succeeded"
    assert summary.reads == 1 and requests == [[200], [200, 200, 200]]
    private = tmp_path / run / ".continuation"
    assert len(list((private / "journal").glob("application.json"))) == 1
    total = owner.get(f"/runs/{run}/usage").json()["session_accounting"]
    assert (total["requests_reserved"], total["known_tokens"], total["unknown_token_reservation"]) == (6, 120, 0)


@pytest.mark.parametrize("boundary", ["changed-evidence", "legacy-worker", "cancel-race"])
def test_pause_boundaries_do_not_start_another_request(continued_api, tmp_path, monkeypatch, boundary):
    owner, _, repo, _ = continued_api
    task, run = create(owner)
    make, _, _, requests = setup_worker(tmp_path, monkeypatch, repo)
    first, route = make()
    route.candidate.max_new_models = 0
    if boundary == "cancel-race":
        from app.persistence.task_continuations import PostgresTaskContinuations
        pause = PostgresTaskContinuations.pause
        def race(self, claimed, reason):
            response = owner.post(f"/tasks/{task}/cancel", headers={"Idempotency-Key": "pause-race"})
            assert response.status_code == 200
            return pause(self, claimed, reason)
        monkeypatch.setattr(PostgresTaskContinuations, "pause", race)
        assert first.run_once().status.value == "cancelled"
    else:
        assert first.run_once().status.value == "paused"
        pin = owner.get(f"/tasks/{task}/continuation").json()["checkpoint_sha256"]
        assert resume(owner, task, pin, "boundary").status_code == 200
        second, route = make()
        if boundary == "changed-evidence":
            original = tmp_path / run / ".continuation/session/operations/0001-result.json"
            original.write_bytes(original.read_bytes() + b" ")
        else:
            route.candidate = None
        assert second.run_once().status.value == "paused"
        if boundary == "legacy-worker":
            assert owner.get(f"/tasks/{task}/continuation").json()["reason"] == "continuation_profile_unavailable"
        else:
            assert owner.get(f"/tasks/{task}/continuation").status_code == 500
    assert requests == [[]]


def test_cancel_between_reservation_and_send_does_not_charge_unsent(continued_api, tmp_path, monkeypatch):
    owner, _, repo, _ = continued_api
    task, run = create(owner)
    make, _, _, requests = setup_worker(tmp_path, monkeypatch, repo)
    worker, route = make()
    original = route.store.pin
    def cancel_at_reservation(claimed, checkpoint, accounting):
        original(claimed, checkpoint, accounting)
        if checkpoint["phase"] == "attempt_reserved" and accounting["requests_reserved"] == 3:
            assert owner.post(f"/tasks/{task}/cancel", headers={"Idempotency-Key": "before-send"}).status_code == 200
    monkeypatch.setattr(route.store, "pin", cancel_at_reservation)
    assert worker.run_once().status.value == "cancelled"
    assert requests == [[]]
    response = owner.get(f"/runs/{run}/usage")
    assert response.status_code == 200, response.text
    total = response.json()["session_accounting"]
    assert (total["requests_reserved"], total["known_tokens"], total["unknown_token_reservation"]) == (2, 40, 0)


def test_projection_conflict_pauses_closed_session_without_resending(continued_api, tmp_path, monkeypatch):
    owner, _, repo, _ = continued_api
    task, run = create(owner)
    make, summary, _, requests = setup_worker(tmp_path, monkeypatch, repo)
    destination = tmp_path / run / "api_run_receipt.json"
    destination.parent.mkdir(parents=True)
    destination.write_text("existing conflicting bytes", encoding="utf-8")
    worker, _ = make()
    assert worker.run_once().status.value == "paused"
    state = owner.get(f"/tasks/{task}/continuation")
    assert state.status_code == 200, state.text
    assert state.json()["reason"] == "session_projection_changed"
    assert resume(owner, task, state.json()["checkpoint_sha256"], "projection-retry").status_code == 200
    worker, _ = make()
    assert worker.run_once().status.value == "paused"
    assert destination.read_text(encoding="utf-8") == "existing conflicting bytes"
    assert requests == [[200, 200]] and summary.reads == 1
