"""Scripted models through the real natural-duty Worker, SQL and usage API.

Software integration evidence only, not natural-model consumption or semantic
qualification. The imported fixture requires an operator-provided disposable
PostgreSQL database and recreates its schema; this module starts no services.
"""

import hashlib
import json
from pathlib import Path
import socket
from uuid import UUID

import pytest

from app.evaluation import natural_duty_contract, sol_review_contract
from app.product.natural_duty_candidate import build_natural_duty_candidate
from app.product.run_receipts import FileRunReceiptStore
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.runtime.store import RuntimeTraceStore
from app.tasks.recent_review_executor import RecentReviewTaskExecutor
from app.tasks.reconciliation import RecentReviewTerminalEvidenceVerifier
from app.tasks.reliable_runtime import TaskLeasePolicy
from app.workers.review_worker import ReviewWorker
from scripts import review_duty_composition as duty
from tests.test_evidence_product_api_postgres import migrated_product_api
from tests.test_native_editor_product_budget import SummaryBuilder
from tests.test_natural_duty_candidate import Factory
from tests.test_sol_natural_candidate import application as sol_application


@pytest.fixture(autouse=True)
def no_external_services(monkeypatch):
    connect = socket.socket.connect
    connect_ex = socket.socket.connect_ex
    create_connection = socket.create_connection

    def require_loopback(address):
        if not isinstance(address, tuple) or address[0] not in (
            "127.0.0.1", "::1", "localhost",
        ):
            raise AssertionError("natural-duty integration allows only loopback")

    def local_connect(sock, address):
        require_loopback(address)
        return connect(sock, address)

    def local_connect_ex(sock, address):
        require_loopback(address)
        return connect_ex(sock, address)

    def local_create_connection(address, *args, **kwargs):
        require_loopback(address)
        return create_connection(address, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", local_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", local_connect_ex)
    monkeypatch.setattr(socket, "create_connection", local_create_connection)


@pytest.mark.parametrize('route', ['glm', 'sol-dual'])
@pytest.mark.parametrize(
    "mode,cancel_after,foreign",
    [
        pytest.param("pass", None, False, id="initial-pass-four-unpublished"),
        pytest.param("repair", None, False, id="repair-six-unpublished"),
        pytest.param("repair", 1, False, id="owner-cancel-after-generation"),
        pytest.param("repair", 4, False, id="owner-cancel-after-initial-reviews"),
        pytest.param("repair", 5, False, id="owner-cancel-after-fresh-facts"),
        pytest.param("repair", 6, False, id="owner-cancel-after-final-response"),
        pytest.param("repair", 4, True, id="foreign-cancel-cannot-stop-fresh"),
    ],
)
def test_natural_duty_worker_keeps_usage_but_never_publishes(
    tmp_path, migrated_product_api, monkeypatch, route, mode, cancel_after, foreign,
):
    owner, other, repository, _ = migrated_product_api
    created = owner.post(
        "/reviews/recent",
        headers={"Idempotency-Key": "natural-duty-worker-pg"},
        json={
            "riot_id": "DK ShowMaker#KR1", "routing_region": "asia",
            "count": 5, "queue": 420,
        },
    )
    assert created.status_code == 202
    task_id, run_id = created.json()["task_id"], created.json()["run_id"]
    cancellations = []
    review_requests = []
    contract = sol_review_contract if route == 'sol-dual' else natural_duty_contract

    if route == 'sol-dual':
        application, factory, _, _ = sol_application(
            tmp_path, mode=mode, candidate=contract, runs_root=tmp_path,
        )
    else:
        factory = Factory(mode=mode)
        application = build_natural_duty_candidate(
            summary_builder=SummaryBuilder(factory.descriptor.generator.req.player_summary),
            provider_factory=factory,
            knowledge_provider=LocalHybridKnowledgeProvider.from_directory(Path("data/rag_docs")),
            runs_root=tmp_path,
        )

    original_factory_call = type(factory).__call__

    def factory_call(self, trusted_run_id):
        assert trusted_run_id == run_id
        provider = original_factory_call(self, trusted_run_id)
        delegate = provider.chat

        def chat(request):
            response = delegate(request)
            if contract.role_for_request(request) == 'review':
                review_requests.append(request)
            if len(provider.attempts) == cancel_after:
                # Response usage exists; cancel through SQL before it returns
                # to Runtime, including cancellation after the last response.
                client = other if foreign else owner
                cancellations.append(client.post(
                    f"/tasks/{task_id}/cancel",
                    headers={"Idempotency-Key": "natural-duty-cancel-pg"},
                ))
            return response

        provider.chat = chat
        return provider

    monkeypatch.setattr(type(factory), '__call__', factory_call)
    # This candidate already constructs DispatchAwareRuntime. The older
    # with_dispatch_trace adapter deliberately refuses that Runtime subclass.
    worker = ReviewWorker(
        repository=repository,
        executor=RecentReviewTaskExecutor(
            application_service=application,
            evidence_verifier=RecentReviewTerminalEvidenceVerifier(tmp_path),
        ),
        worker_id="natural-duty-pg-worker",
        lease_policy=TaskLeasePolicy(lease_seconds=360, heartbeat_seconds=60),
    )
    result = worker.run_once()

    cancelled = cancel_after is not None and not foreign
    expected_status = "cancelled" if cancelled else "succeeded"
    expected_calls = cancel_after if cancelled else (4 if mode == "pass" else 6)
    provider = factory.providers[run_id]
    assert result.task_id == UUID(task_id)
    assert result.status.value == expected_status
    assert len(provider.attempts) == expected_calls
    assert [attempt["role"] for attempt in provider.attempts] == (
        ["generation", "generation", "review", "review", "review", "review"][:expected_calls]
    )
    assert all(attempt["status"] == "completed" for attempt in provider.attempts)
    assert [
        (request.metadata[duty.MARKER]["duty"], request.metadata[duty.MARKER]["stage"])
        for request in review_requests
    ] == [
        ("facts", "initial"), ("completion", "initial"),
        ("facts", "fresh"), ("completion", "fresh"),
    ][:max(0, expected_calls - 2)]
    if cancel_after is None:
        assert cancellations == []
    else:
        assert len(cancellations) == 1
        assert cancellations[0].status_code == (404 if foreign else 200)
        if cancelled:
            assert cancellations[0].json()["disposition"] == "requested"

    stored = repository.get_by_task_id(owner_id="owner-1", task_id=UUID(task_id))
    assert stored is not None and stored.status.value == expected_status
    assert not stored.report_available and stored.artifact_reference is None
    state = owner.get(f"/tasks/{task_id}")
    assert state.status_code == 200
    assert state.json()["status"] == expected_status
    assert state.json()["report_available"] is False
    events_response = owner.get(f"/tasks/{task_id}/events?limit=50")
    assert events_response.status_code == 200
    kinds = [event["event_kind"] for event in events_response.json()["events"]]
    assert kinds[-1] == expected_status
    assert kinds.count("cancel_requested") == int(cancelled)
    assert kinds.count("cancelled") == int(cancelled)
    assert kinds.count("succeeded") == int(not cancelled)
    assert "failed" not in kinds

    receipt = FileRunReceiptStore(tmp_path).read_receipt(run_id)
    assert receipt.trace_reference is not None and not receipt.report_available
    trace = RuntimeTraceStore(tmp_path, run_id).read_trace(receipt.trace_reference)
    assert trace.identity.coach_contract == contract.CONTRACT.snapshot()
    assert trace.identity.provider_model == contract.MODEL
    if route == 'sol-dual':
        assert {request.metadata[contract.CONTEXT]['version'] for request in review_requests} <= {contract.VERSION}
        assert all(contract.request_identity(request) == (contract.REVIEW_PROVIDER, contract.REVIEW_MODEL)
                   for request in review_requests)
        if expected_calls == 6:
            fresh = [request.metadata[contract.CONTEXT] for request in review_requests
                     if request.metadata[contract.CONTEXT]['stage'] == 'fresh']
            applied = json.loads((tmp_path / run_id / 'natural-duty-journal' / 'application.json').read_bytes())
            assert len(fresh) == 2 and fresh[0]['report'] == fresh[1]['report']
            assert hashlib.sha256(fresh[0]['report'].encode('utf-8')).hexdigest() == applied['report_sha256']
    starts = [event.signal for event in trace.events if event.signal.kind == "provider_call_started"]
    completes = [event.signal for event in trace.events if event.signal.kind == "provider_call_completed"]
    assert len(starts) == len(completes) == expected_calls
    assert [signal.ordinal for signal in starts] == list(range(1, expected_calls + 1))
    assert [signal.ordinal for signal in completes] == list(range(1, expected_calls + 1))
    assert trace.usage.provider_calls_attempted == expected_calls
    assert trace.usage.provider_responses_observed == expected_calls
    # Flash/GLM return 10/10; the Sol HTTP fixture returns 12/8. A pre-next-send stop must
    # neither invent an attempted call nor erase usage as unknown/zero.
    assert trace.usage.token_observation.value == "complete"
    sol_reviews = max(0, expected_calls - 2) if route == 'sol-dual' else 0
    assert trace.usage.observed_input_tokens == trace.usage.input_tokens == 10 * expected_calls + 2 * sol_reviews
    assert trace.usage.observed_output_tokens == trace.usage.output_tokens == 10 * expected_calls - 2 * sol_reviews
    usage = owner.get(f"/runs/{run_id}/usage")
    assert usage.status_code == 200
    assert usage.json()["run_id"] == run_id
    assert usage.json()["task_status"] == expected_status
    assert usage.json()["usage"] == trace.usage.model_dump(mode="json")
    if expected_calls >= 4:
        outcome = json.loads((tmp_path / run_id / "natural-duty-journal" / "outcome.json").read_bytes())
        assert outcome["calls"] == expected_calls
        assert outcome["known_tokens"] == 20 * expected_calls
        assert outcome["unknown_reserved_tokens"] == 0

    if cancelled:
        assert stored.publication_status is None
    else:
        # SQL succeeded means a verified execution terminal, not publication.
        assert stored.publication_status.value == "rejected"
    if cancelled and cancel_after < 6:
        assert receipt.runtime_status.value == "failed"
        assert receipt.terminal_reason == "task_dispatch_stopped"
        assert trace.events[-1].signal.failure_code == "task_dispatch_stopped"
    else:
        assert receipt.runtime_status.value == "completed"
        assert receipt.publication_status.value == "rejected"
        outcome = json.loads((tmp_path / run_id / "natural-duty-journal" / "outcome.json").read_bytes())
        assert outcome["outcome"] == (
            "candidate_initial_pass_unqualified" if mode == "pass"
            else "candidate_repaired_pass_unqualified"
        )

    # Even final-response cancellation cannot leave a published local report:
    # this candidate is unqualified independently of the SQL cancellation fence.
    assert not any(artifact.kind == "final_report" for artifact in trace.artifacts)
    assert not list((tmp_path / run_id).rglob("final_report.md"))
    assert owner.get(f"/runs/{run_id}/report").status_code == 409
    assert other.get(f"/runs/{run_id}/usage").status_code == 404
    assert other.get(f"/runs/{run_id}/report").status_code == 404
    assert other.get(f"/tasks/{task_id}").status_code == 404

    # Terminal work is never claimed again, including a cancelled last call.
    assert worker.run_once().status.value == "idle"
    assert len(provider.attempts) == expected_calls
    if cancelled:
        replay = owner.post(
            f"/tasks/{task_id}/cancel",
            headers={"Idempotency-Key": "natural-duty-cancel-pg"},
        )
        assert replay.status_code == 200
        assert replay.json()["disposition"] == "already_terminal"
        assert owner.get(f"/tasks/{task_id}/events?limit=50").json() == events_response.json()
