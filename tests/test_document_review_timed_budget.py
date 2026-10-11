"""Complete public requests + real shared accounting; no network or SDK calls."""
from dataclasses import replace
import hashlib
import socket

import pytest

from app.evaluation import document_review_timing_adapter as timed
from app.evaluation.document_review_identity import request_identity as old_identity
from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_stream_bridge import validate_request, REVIEW_MODEL_TRANSPORT_ID
from app.evaluation.role_qualification import frozen_cases
from app.providers.models import ChatResponse, TokenUsage
from app.providers.errors import ProviderResponseError
from app.runtime.review_sender import SharedBudgetReviewSender
from scripts.report_contrast_review import ContrastDocumentWorkflow as Workflow
from scripts.report_block_keyed_editor import edit_request
from tests.test_coarse_revision_editor import cases
from tests.test_document_review_budget import router
from tests.test_reviewer_role_proposal import compiled
from tests.test_native_editor_product_budget import offline


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("offline timing candidate must not connect")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


class Clock:
    now = 0
    def __call__(self):
        return self.now


def review():
    return timed.prepare_request(Workflow.make_request(Workflow.build_inputs(frozen_cases()[0][0][1])))


def provider(monkeypatch, clock, *, fault=None, duration=0):
    value = router("success")
    value.request_timing_identity = timed.TIMED_IDENTITY
    seen = []
    def chat(request):
        seen.append(request)
        clock.now += duration
        if fault == "unknown":
            raise ProviderResponseError(provider="zhipu", code="stream_deadline")
        response = ChatResponse(content="Synthetic timing response, not business acceptance",
            provider="zhipu", model=timed.request_identity(request)[1], usage=TokenUsage(10, 20))
        if fault == "model": response = replace(response, model="wrong-model")
        if fault == "usage": response = replace(response, usage=TokenUsage(10, 32769))
        issued = replace(request, timeout_s=1) if fault == "issued" else request
        sha = "0" * 64 if fault == "digest" else hashlib.sha256(timed.request_bytes(issued)).hexdigest()
        value.last_exchange = Exchange(issued, response, sha)
        return response
    monkeypatch.setattr(value, "chat", chat)
    return value, seen


def test_all_fifteen_complete_policy_source_and_schema_preserved():
    for _, source in frozen_cases()[0]:
        original = Workflow.make_request(Workflow.build_inputs(source))
        request = timed.prepare_request(original)
        assert request.messages == original.messages and request.tools == original.tools
        assert request.timeout_s == 600 and timed.request_identity(request) == ("zhipu", "glm-5.3")
        assert timed.METADATA in request.metadata
        with pytest.raises(ValueError): old_identity(request)
        with pytest.raises(ProviderResponseError): validate_request(request, transport_id=REVIEW_MODEL_TRANSPORT_ID)
        with pytest.raises(ValueError): timed.request_identity(original)


@pytest.mark.parametrize("fault", ["marker", "policy", "schema", "elapsed", "nan", "infinity", "overcap"])
def test_invalid_full_requests_stop_before_delegation(monkeypatch, fault):
    clock = Clock(); value, seen = provider(monkeypatch, clock)
    budget = timed.TimedDocumentBudget(value, clock=clock)
    request = review()
    if fault == "marker": request = replace(request, metadata={**request.metadata, timed.METADATA: "other"})
    if fault == "elapsed": request = replace(request, metadata={**request.metadata, "task_elapsed_s": 0})
    if fault == "policy": request = replace(request, messages=(replace(request.messages[0], content="wrong policy"), *request.messages[1:]))
    if fault == "schema": request = replace(request, tools=())
    if fault in ("nan", "infinity", "overcap"):
        request = replace(request, timeout_s={"nan": float("nan"), "infinity": float("inf"), "overcap": 601}[fault])
    with pytest.raises(ValueError): budget.chat(request)
    assert budget.stopped and budget.calls == 0 and not seen


def test_shared_generation_prefix_and_revision_consume_same_clock_and_ledger(compiled, monkeypatch):
    clock = Clock(); value, seen = provider(monkeypatch, clock, duration=80)
    budget = timed.TimedDocumentBudget(value, clock=clock)
    for request in compiled[0]:
        budget.chat(timed.prepare_request(request))
    initial = review()
    sender = SharedBudgetReviewSender(budget)
    assert sender(initial) is budget.last_exchange
    _, inputs, accepted, _ = cases()["claim-scope:4"]
    edit = timed.prepare_request(edit_request(inputs, accepted))
    budget.chat(edit)
    clock.now = 800
    sender(initial)
    assert [r.timeout_s for r in seen] == [300, 300, 600, 300, 100]
    assert budget.calls == 5 and budget.tokens == 150 and budget.reserved_tokens == 0
    with pytest.raises(ProviderResponseError): budget.chat(initial)
    assert len(seen) == 5


@pytest.mark.parametrize("elapsed,expected", [(0, 600), (500, 400), (900, None)])
def test_request_truncated_by_owned_task_clock(monkeypatch, elapsed, expected):
    clock = Clock(); value, seen = provider(monkeypatch, clock)
    budget = timed.TimedDocumentBudget(value, clock=clock)
    clock.now = elapsed
    if expected is None:
        with pytest.raises(ProviderResponseError, match="timeout"): budget.chat(review())
        assert budget.calls == 0 and not seen
    else:
        exchange = SharedBudgetReviewSender(budget)(review())
        assert seen[-1].timeout_s == expected
        assert exchange.receipt_request_sha256 == hashlib.sha256(timed.request_bytes(seen[-1])).hexdigest()


def test_unknown_failure_keeps_reservation_and_prevents_retry(monkeypatch):
    clock = Clock(); value, seen = provider(monkeypatch, clock, fault="unknown")
    budget = timed.TimedDocumentBudget(value, clock=clock)
    with pytest.raises(ProviderResponseError): budget.chat(review())
    reservation = budget.reserved_tokens
    assert budget.calls == 1 and budget.tokens == 0 and reservation > 32768
    with pytest.raises(ProviderResponseError): budget.chat(review())
    assert len(seen) == 1 and budget.reserved_tokens == reservation and budget.last_exchange is None


@pytest.mark.parametrize("fault,code", [("model", "invalid_chat_response"), ("usage", "token_envelope_exceeded")])
def test_response_identity_and_usage_envelope_failure_stop_task(monkeypatch, fault, code):
    clock = Clock(); value, seen = provider(monkeypatch, clock, fault=fault)
    budget = timed.TimedDocumentBudget(value, clock=clock)
    with pytest.raises(ProviderResponseError, match=code): budget.chat(review())
    assert budget.calls == 1 and budget.stopped and budget.last_exchange is None
    assert budget.reserved_tokens > 0 if fault == "model" else budget.tokens == 32779
    with pytest.raises(ProviderResponseError): budget.chat(review())
    assert len(seen) == 1


def test_completion_after_task_deadline_not_exposed_to_workflow(monkeypatch):
    clock = Clock(); value, seen = provider(monkeypatch, clock, duration=901)
    budget = timed.TimedDocumentBudget(value, clock=clock)
    with pytest.raises(ProviderResponseError, match="timeout"): budget.chat(review())
    assert len(seen) == 1 and budget.tokens == 30 and budget.reserved_tokens == 0
    assert budget.stopped and budget.last_exchange is None


def test_legacy_provider_and_caller_elapsed_cannot_choose_candidate(monkeypatch):
    clock = Clock(); value, _ = provider(monkeypatch, clock)
    value.request_timing_identity = timed.LEGACY_IDENTITY
    with pytest.raises(ValueError, match="timed_provider_identity"):
        timed.TimedDocumentBudget(value, clock=clock)


def test_oversized_input_never_reaches_delegate(monkeypatch):
    clock = Clock(); value, seen = provider(monkeypatch, clock)
    budget = timed.TimedDocumentBudget(value, clock=clock)
    request = review()
    request = replace(request, messages=(*request.messages[:-1], replace(request.messages[-1], content="x" * 350000)))
    with pytest.raises(ValueError, match="timed_request_input_budget"): budget.chat(request)
    assert budget.calls == 0 and not seen and budget.stopped


@pytest.mark.parametrize("fault", ["issued", "digest"])
def test_receipt_bound_to_actual_budgeted_bytes(monkeypatch, fault):
    clock = Clock(); value, seen = provider(monkeypatch, clock, fault=fault)
    budget = timed.TimedDocumentBudget(value, clock=clock)
    with pytest.raises(ProviderResponseError, match="timed_receipt_binding"): budget.chat(review())
    assert budget.calls == 1 and budget.stopped and budget.last_exchange is None


def test_token_wall_and_clock_regression_stop_before_send(monkeypatch):
    clock = Clock(); value, seen = provider(monkeypatch, clock)
    budget = timed.TimedDocumentBudget(value, clock=clock)
    budget.tokens = 401920
    with pytest.raises(ProviderResponseError, match="token_budget_exhausted"): budget.chat(review())
    assert not seen and budget.calls == 0
    budget = timed.TimedDocumentBudget(value, clock=clock)
    clock.now = 10; budget.chat(review()); clock.now = 0
    with pytest.raises(ProviderResponseError, match="timed_clock_regressed"): budget.chat(review())
    assert len(seen) == 1


@pytest.mark.parametrize("role,value", [("bogus", 300), ("review", float("nan")), ("review", float("inf")), ("review", True)])
def test_scalar_helper_does_not_accept_invalid_role_or_numbers(role, value):
    with pytest.raises(ValueError): timed.validate(timed.TimingRequest(timed.TIMED_IDENTITY, role, value, 0, timed.TIMED_MARKER))
