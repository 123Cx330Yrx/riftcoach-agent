"""Real PostgreSQL/API/Worker path; scripted model IO, no quality evidence.

Uses the existing disposable-database fixture. Never point the test database
environment at the product database: that fixture recreates the schema.
"""
from pathlib import Path
import socket
from uuid import UUID

import pytest

from app.evaluation.golden_coarse_source_projection import VERSION
from app.product.native_coach_composition import build_correction_scope_coach_application
from app.product.run_receipts import FileRunReceiptStore
from app.product.dispatch_trace import with_dispatch_trace
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.runtime.reviewer_roles import RoleRoutedProvider
from app.runtime.store import RuntimeTraceStore
from app.tasks.recent_review_executor import RecentReviewTaskExecutor
from app.tasks.reconciliation import RecentReviewTerminalEvidenceVerifier
from app.tasks.reliable_runtime import TaskLeasePolicy
from app.workers.review_worker import ReviewWorker
from tests.test_correction_scope_runtime import coarse_script_sources
from tests.test_evidence_product_api_postgres import migrated_product_api
from tests.test_native_editor_product_budget import SummaryBuilder
from tests.test_reviewer_role_proposal import providers


@pytest.fixture(autouse=True)
def no_external_services(monkeypatch):
    connect = socket.socket.connect

    def local_only(sock, address):
        if not isinstance(address, tuple) or address[0] not in ("127.0.0.1", "::1", "localhost"):
            raise AssertionError("dispatch integration must not contact external services")
        return connect(sock, address)

    monkeypatch.setattr(socket.socket, "connect", local_only)


@pytest.mark.parametrize("cancel_after,foreign", [
    (None, False), (1, False), (3, False), (4, False), (5, False), (1, True),
])
def test_api_cancel_fences_real_database_worker_before_next_model_send(
    tmp_path, migrated_product_api, coarse_script_sources, cancel_after, foreign,
):
    owner, other, repository, _ = migrated_product_api
    created = owner.post("/reviews/recent", headers={"Idempotency-Key": "dispatch-pg"}, json={
        "riot_id": "DK ShowMaker#KR1", "routing_region": "asia", "count": 5, "queue": 420,
    })
    assert created.status_code == 202
    task_id, run_id = created.json()["task_id"], created.json()["run_id"]
    cancellations = []

    class Factory:
        def __init__(self):
            self.descriptor = RoleRoutedProvider(*providers(), source_projection=VERSION)
            self.created = None

        def __call__(self, trusted_run_id):
            assert trusted_run_id == run_id
            self.created = RoleRoutedProvider(*providers(), source_projection=VERSION)
            delegate = self.created.chat

            def chat(request):
                response = delegate(request)
                if len(self.created.attempts) == cancel_after:
                    # Arrives while the current model call is still returning.
                    # Both the API and Worker use real SQL transactions.
                    client = other if foreign else owner
                    cancellations.append(client.post(f"/tasks/{task_id}/cancel",
                        headers={"Idempotency-Key": "cancel-dispatch-pg"}))
                return response

            self.created.chat = chat
            return self.created

    factory = Factory()
    application = build_correction_scope_coach_application(
        summary_builder=SummaryBuilder(factory.descriptor.generator.req.player_summary),
        provider_factory=factory,
        knowledge_provider=LocalHybridKnowledgeProvider.from_directory(Path("data/rag_docs")),
        runs_root=tmp_path,
    )
    application = with_dispatch_trace(application)
    executor = RecentReviewTaskExecutor(application_service=application,
        evidence_verifier=RecentReviewTerminalEvidenceVerifier(tmp_path))
    result = ReviewWorker(repository=repository, executor=executor, worker_id="dispatch-pg-worker",
        lease_policy=TaskLeasePolicy(lease_seconds=360, heartbeat_seconds=60)).run_once()

    cancelled = cancel_after is not None and not foreign
    expected_status = "cancelled" if cancelled else "succeeded"
    expected_calls = cancel_after if cancelled else 5
    assert result.status.value == expected_status
    assert result.task_id == UUID(task_id)
    assert [row["role"] for row in factory.created.attempts] == [
        "generation", "generation", "review", "revision", "review",
    ][:expected_calls]
    if cancel_after is not None:
        assert len(cancellations) == 1
        assert cancellations[0].status_code == (404 if foreign else 200)
        if not foreign:
            assert cancellations[0].json()["disposition"] == "requested"
    else:
        assert not cancellations

    stored = repository.get_by_task_id(owner_id="owner-1", task_id=UUID(task_id))
    assert stored is not None and stored.status.value == expected_status
    assert owner.get(f"/tasks/{task_id}").json()["status"] == expected_status
    events_response = owner.get(f"/tasks/{task_id}/events?limit=50")
    assert events_response.status_code == 200
    event_kinds = [event["event_kind"] for event in events_response.json()["events"]]
    assert event_kinds[-1] == expected_status
    assert event_kinds.count("cancel_requested") == int(cancelled)
    assert event_kinds.count("cancelled") == int(cancelled)
    assert event_kinds.count("succeeded") == int(not cancelled)
    assert "failed" not in event_kinds

    receipt = FileRunReceiptStore(tmp_path).read_receipt(run_id)
    assert receipt.trace_reference is not None
    trace = RuntimeTraceStore(tmp_path, run_id).read_trace(receipt.trace_reference)
    starts = [e for e in trace.events if e.signal.kind == "provider_call_started"]
    assert len(starts) == expected_calls
    assert trace.usage.provider_calls_attempted == expected_calls
    assert trace.usage.provider_responses_observed == expected_calls
    assert trace.usage.observed_input_tokens == expected_calls * 10
    assert trace.usage.observed_output_tokens == expected_calls * 10
    if cancelled and cancel_after < 5:
        assert receipt.runtime_status.value == "failed" and not receipt.report_available
        assert receipt.terminal_reason == "task_dispatch_stopped"
        assert trace.events[-1].signal.failure_code == "task_dispatch_stopped"
    if cancelled:
        assert stored.artifact_reference is None and stored.publication_status is None
        assert not stored.report_available
        assert owner.get(f"/runs/{run_id}/report").status_code == 409
        # A final-call cancellation may leave a local report; SQL still fences
        # visibility. Earlier cancellation must never reach the local publisher.
        assert bool(list(tmp_path.rglob("final_report.md"))) is (cancel_after == 5)
    else:
        assert stored.report_available
        assert owner.get(f"/runs/{run_id}/report").status_code == 200
    assert other.get(f"/tasks/{task_id}").status_code == 404
    assert other.get(f"/runs/{run_id}/report").status_code == 404

    if cancelled:
        replay = owner.post(f"/tasks/{task_id}/cancel",
            headers={"Idempotency-Key": "cancel-dispatch-pg"})
        assert replay.status_code == 200 and replay.json()["disposition"] == "already_terminal"
        after = owner.get(f"/tasks/{task_id}/events?limit=50")
        assert after.json() == events_response.json()
