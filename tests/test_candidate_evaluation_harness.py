"""Offline tests for the isolated candidate evaluation harness."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

from app.evaluation.candidate_evaluation_harness import (
    CANDIDATE_EVALUATION_RECEIPT_SCHEMA,
    CandidateActivationGate,
    CandidateEvaluationError,
    CandidateEvaluationHarness,
    CandidateEvaluationLedger,
    CandidateEvaluationRunSpec,
    CandidateTransportError,
    DISABLED_CANDIDATE_ACTIVATION,
)
from app.evaluation.candidate_stream_contract import (
    CandidateIdentityError,
    CandidateObservationError,
    PRIMARY_CANDIDATE_BINDING,
)
from app.providers.models import ChatMessage, ChatRequest, MessageRole, TokenUsage
from app.providers.response_completion_policy import ResponseDisposition, ResponseRequestContext
from app.providers.response_recovery_contract import RecoveryStateError
from app.providers.stream_adapter_contract import (
    ProviderStreamEvent,
    StreamToolCallDelta,
)


MODEL = "glm-5.3-flash"
REQUEST_SHA = hashlib.sha256(b"candidate-harness-request").hexdigest()


def _request(*, max_tokens: int | None = None) -> ChatRequest:
    return ChatRequest(
        messages=(ChatMessage(MessageRole.USER, "offline fixture"),),
        max_tokens=max_tokens,
    )


def _context(
    *,
    phase: str = "agent_initial",
    response_contract: bool = False,
    tools: bool = False,
    tool_side_effects: bool = False,
    timeout_s: float = 90.0,
    token_budget: int = 8192,
) -> ResponseRequestContext:
    return ResponseRequestContext(
        phase=phase,
        has_response_contract=response_contract,
        has_tools=tools,
        has_tool_side_effects=tool_side_effects,
        remaining_timeout_s=timeout_s,
        remaining_token_budget=token_budget,
    )


def _run(*, context: ResponseRequestContext | None = None) -> CandidateEvaluationRunSpec:
    return CandidateEvaluationRunSpec.new(context=context or _context())


def _event(
    *,
    content: str | None = None,
    reasoning: str | None = None,
    finish: str | None = None,
    usage: TokenUsage | None = None,
    sequence: int | None = None,
    model: str | None = MODEL,
    request_id: str | None = REQUEST_SHA,
    tools: tuple[StreamToolCallDelta, ...] = (),
) -> ProviderStreamEvent:
    return ProviderStreamEvent(
        content_delta=content,
        reasoning_delta=reasoning,
        tool_call_deltas=tools,
        finish_reason=finish,
        usage=usage,
        model=model,
        sequence=sequence,
        request_id_sha256=request_id,
    )


class _Stream:
    def __init__(self, events, *, close_error: Exception | None = None):
        self._events = tuple(events)
        self.close_error = close_error
        self.closed = False
        self.iterations = 0

    def __iter__(self):
        self.iterations += 1
        if self.iterations > 1:
            raise AssertionError("stream was consumed more than once")
        return iter(self._events)

    def close(self) -> None:
        self.closed = True
        if self.close_error is not None:
            raise self.close_error


class _Transport:
    def __init__(self, stream_factory):
        self.stream_factory = stream_factory
        self.calls = []

    def open_stream(self, binding, request, *, max_output_tokens, timeout_s, transport_timeout_s):
        self.calls.append(
            {
                "binding": binding,
                "request": request,
                "max_output_tokens": max_output_tokens,
                "timeout_s": timeout_s,
                "transport_timeout_s": transport_timeout_s,
            }
        )
        return self.stream_factory()


class _Consumer:
    def __init__(self):
        self.responses = []

    def accept(self, response):
        self.responses.append(response)


class _FailingConsumer:
    def accept(self, response):
        raise RuntimeError("consumer body secret")


def _read_fail_stream():
    def _events():
        raise RuntimeError("provider body secret")
        yield  # pragma: no cover - keeps this a generator

    return _events()


def _complete_events():
    return [
        _event(content="visible secret", sequence=1),
        _event(
            finish="stop",
            usage=TokenUsage(input_tokens=12, output_tokens=3, cached_input_tokens=0),
            sequence=2,
            model=None,
            request_id=None,
        ),
    ]


def test_complete_text_is_assembled_once_and_consumer_is_ephemeral():
    stream = _Stream(_complete_events())
    transport = _Transport(lambda: stream)
    consumer = _Consumer()

    result = CandidateEvaluationHarness().evaluate(
        _request(),
        _run(),
        transport=transport,
        consumer=consumer,
    )

    receipt = result.receipt
    assert receipt.schema_version == CANDIDATE_EVALUATION_RECEIPT_SCHEMA
    assert receipt.terminal_state == "complete_text"
    assert receipt.calls_reserved == receipt.calls_settled == 1
    assert receipt.resource.input_tokens == 12
    assert receipt.resource.output_tokens == 3
    assert receipt.resource.usage_certainty == "complete"
    assert transport.calls[0]["max_output_tokens"] == 8192
    assert transport.calls[0]["timeout_s"] == 90.0
    assert transport.calls[0]["transport_timeout_s"] == 120.0
    assert transport.calls[0]["request"].max_tokens == 8192
    assert transport.calls[0]["request"].temperature == 1.0
    assert transport.calls[0]["request"].top_p == 0.95
    assert transport.calls[0]["request"].timeout_s == 90.0
    assert stream.closed is True
    assert len(consumer.responses) == 1
    assert consumer.responses[0].content == "visible secret"
    encoded = json.dumps(receipt.as_dict(), sort_keys=True)
    assert "visible secret" not in encoded
    assert "visible secret" not in repr(receipt)


def test_explicit_request_cap_is_enforced_by_both_stream_sinks():
    transport = _Transport(
        lambda: _Stream(
            [
                _event(content="visible", sequence=1),
                _event(
                    finish="stop",
                    usage=TokenUsage(input_tokens=2, output_tokens=4, cached_input_tokens=0),
                    sequence=2,
                    model=None,
                    request_id=None,
                ),
            ]
        )
    )

    result = CandidateEvaluationHarness().evaluate(
        _request(max_tokens=3),
        _run(),
        transport=transport,
    )

    assert transport.calls[0]["max_output_tokens"] == 3
    assert transport.calls[0]["request"].max_tokens == 3
    assert result.receipt.terminal_state == "fail_closed"
    assert result.receipt.safe_error_code == "output_budget_exceeded"


def test_tool_calls_are_observed_but_never_executed():
    stream = _Stream(
        [
            _event(
                tools=(
                    StreamToolCallDelta(
                        index=0,
                        call_id="call-1",
                        name="lookup",
                        arguments_delta="{}",
                    ),
                ),
                sequence=1,
            ),
            _event(
                finish="tool_calls",
                usage=TokenUsage(2, 2, 0),
                sequence=2,
                model=None,
                request_id=None,
            ),
        ]
    )
    consumer = _Consumer()
    result = CandidateEvaluationHarness().evaluate(
        _request(),
        _run(),
        transport=_Transport(lambda: stream),
        consumer=consumer,
    )

    assert result.receipt.terminal_state == "tool_calls_ready"
    assert result.receipt.attempts[0].observation.observation.tool_call_count == 1
    assert len(consumer.responses) == 1
    assert consumer.responses[0].tool_calls[0].name == "lookup"


def test_exact_candidate_length_shape_stops_at_disabled_activation():
    stream = _Stream(
        [
            _event(content="", reasoning="private reasoning", sequence=1),
            _event(
                finish="length",
                usage=TokenUsage(4, 8192, 0),
                sequence=2,
                model=None,
                request_id=None,
            ),
        ]
    )
    transport = _Transport(lambda: stream)

    result = CandidateEvaluationHarness().evaluate(
        _request(),
        _run(),
        transport=transport,
    )

    assert result.receipt.terminal_state == "awaiting_recovery"
    assert result.receipt.next_action == "requires_registered_runtime"
    assert result.receipt.calls_reserved == result.receipt.calls_settled == 1
    assert result.receipt.attempts[0].disposition.value == "candidate_eligible"
    assert result.receipt.activation_gate == "disabled"
    assert len(transport.calls) == 1


def test_partial_content_length_is_fail_closed_not_candidate():
    result = CandidateEvaluationHarness().evaluate(
        _request(),
        _run(),
        transport=_Transport(
            lambda: _Stream(
                [
                    _event(content="partial", reasoning="private", sequence=1),
                    _event(
                        finish="length",
                        usage=TokenUsage(1, 4, 0),
                        sequence=2,
                        model=None,
                        request_id=None,
                    ),
                ]
            )
        ),
    )

    assert result.receipt.terminal_state == "fail_closed"
    assert result.receipt.attempts[0].error_code == "incomplete_chat_response"
    assert result.receipt.attempts[0].reason_code == "length_partial_content"


@pytest.mark.parametrize(
    ("stream_factory", "error_code"),
    [
        (
            lambda: _Stream(
                [
                    _event(content="text", sequence=1),
                    _event(finish="stop", sequence=2, model=None, request_id=None),
                ]
            ),
            "usage_unavailable",
        ),
        (
            _read_fail_stream,
            "stream_read_failed",
        ),
    ],
)
def test_missing_usage_and_read_errors_are_body_free(stream_factory, error_code):
    result = CandidateEvaluationHarness().evaluate(
        _request(),
        _run(),
        transport=_Transport(stream_factory),
    )
    assert result.receipt.terminal_state == "fail_closed"
    assert result.receipt.safe_error_code == error_code
    encoded = json.dumps(result.receipt.as_dict(), sort_keys=True)
    assert "provider body secret" not in encoded


def test_open_and_close_errors_consume_the_reserved_slot():
    open_transport = _Transport(
        lambda: (_ for _ in ()).throw(RuntimeError("open body secret"))
    )
    opened = CandidateEvaluationHarness().evaluate(
        _request(),
        _run(),
        transport=open_transport,
    )
    assert opened.receipt.calls_reserved == opened.receipt.calls_settled == 1
    assert opened.receipt.safe_error_code == "transport_open_failed"

    closed_stream = _Stream(_complete_events(), close_error=RuntimeError("close body secret"))
    closed = CandidateEvaluationHarness().evaluate(
        _request(),
        _run(),
        transport=_Transport(lambda: closed_stream),
    )
    assert closed.receipt.terminal_state == "fail_closed"
    assert closed.receipt.safe_error_code == "stream_close_failed"
    assert closed_stream.closed is True


def test_staged_ledger_reserves_before_a_snapshot_exists_and_rejects_duplicates():
    ledger = CandidateEvaluationLedger(_run())
    reservation = ledger.reserve_next()
    snapshot = ledger.snapshot()
    assert snapshot.calls_reserved == 1
    assert snapshot.calls_settled == 0
    assert snapshot.attempts == ()
    with pytest.raises(RecoveryStateError):
        ledger.reserve_next()
    with pytest.raises(RecoveryStateError):
        ledger.settle(reservation, object())  # type: ignore[arg-type]


def test_run_spec_and_activation_are_not_caller_selectable():
    with pytest.raises(CandidateIdentityError):
        CandidateEvaluationRunSpec(
            primary_binding=replace(PRIMARY_CANDIDATE_BINDING, model="glm-5.2"),
            context=_context(),
            run_id_sha256=hashlib.sha256(b"run").hexdigest(),
        )
    assert DISABLED_CANDIDATE_ACTIVATION is CandidateActivationGate.DISABLED
    with pytest.raises(CandidateTransportError):
        CandidateEvaluationHarness().evaluate(
            _request(),
            _run(),
            transport=_Transport(lambda: _Stream(_complete_events())),
            activation=True,  # type: ignore[arg-type]
        )


def test_request_metadata_identity_mismatch_fails_before_provider_call():
    request = ChatRequest(
        messages=(ChatMessage(MessageRole.USER, "offline fixture"),),
        metadata={"model": "glm-5.2"},
    )
    transport = _Transport(lambda: _Stream(_complete_events()))
    with pytest.raises(CandidateTransportError, match="request_identity_mismatch"):
        CandidateEvaluationHarness().evaluate(request, _run(), transport=transport)
    assert transport.calls == []


def test_harness_is_single_use_and_result_exposes_no_response_body():
    harness = CandidateEvaluationHarness()
    transport = _Transport(lambda: _Stream(_complete_events()))
    result = harness.evaluate(_request(), _run(), transport=transport)
    assert result.terminal_state == "complete_text"
    assert "visible secret" not in repr(result)
    with pytest.raises(CandidateObservationError, match="harness_reused"):
        harness.evaluate(_request(), _run(), transport=transport)


def test_consumer_failure_is_independent_and_body_free():
    result = CandidateEvaluationHarness().evaluate(
        _request(),
        _run(),
        transport=_Transport(lambda: _Stream(_complete_events())),
        consumer=_FailingConsumer(),
    )
    assert result.receipt.terminal_state == "complete_text"
    assert result.receipt.consumer_error_code == "consumer_failed"
    assert result.consumer_delivered is False
    assert "consumer body secret" not in json.dumps(result.as_dict())


def test_receipt_state_and_top_level_error_are_derived_not_caller_selectable():
    result = CandidateEvaluationHarness().evaluate(
        _request(),
        _run(),
        transport=_Transport(lambda: _Stream(_complete_events())),
    )

    with pytest.raises(CandidateEvaluationError, match="receipt_state_mismatch"):
        replace(
            result.receipt,
            terminal_state="awaiting_recovery",
            next_action="requires_registered_runtime",
        )
    with pytest.raises(CandidateEvaluationError, match="receipt_error_mismatch"):
        replace(
            result.receipt,
            safe_error_code="forged_error",
            safe_error_stage="observe",
        )


def test_attempt_receipt_decision_and_assembly_are_bound_to_observation():
    result = CandidateEvaluationHarness().evaluate(
        _request(),
        _run(),
        transport=_Transport(lambda: _Stream(_complete_events())),
    )
    attempt = result.receipt.attempts[0]

    with pytest.raises(CandidateEvaluationError, match="attempt_decision_mismatch"):
        replace(
            attempt,
            disposition=ResponseDisposition.FAIL_CLOSED,
        )
    with pytest.raises(CandidateEvaluationError, match="assembly_state_mismatch"):
        replace(attempt, assembled_complete=False)
    with pytest.raises(CandidateEvaluationError, match="budget_projection_mismatch"):
        replace(attempt, budget_exceeded=True)


def test_single_attempt_timeout_is_enforced_before_cumulative_budget():
    ticks = iter((0.0, 91.0, 91.0))

    def clock():
        return next(ticks)

    result = CandidateEvaluationHarness().evaluate(
        _request(),
        _run(),
        transport=_Transport(lambda: _Stream(_complete_events())),
        clock=clock,
    )

    assert result.receipt.terminal_state == "fail_closed"
    assert result.receipt.safe_error_code == "elapsed_limit"


def test_explicit_null_content_is_not_silently_promoted_to_empty_candidate_shape():
    # ``content_observed=True`` with a null delta is distinct from an observed
    # empty string; the policy must reject it as missing candidate content.
    null_content = ProviderStreamEvent(
        content_delta=None,
        content_observed=True,
        reasoning_delta="private",
        reasoning_observed=True,
        sequence=1,
        model=MODEL,
        request_id_sha256=REQUEST_SHA,
    )
    result = CandidateEvaluationHarness().evaluate(
        _request(),
        _run(),
        transport=_Transport(
            lambda: _Stream(
                [
                    null_content,
                    _event(
                        finish="length",
                        usage=TokenUsage(1, 3, 0),
                        sequence=2,
                        model=None,
                        request_id=None,
                    ),
                ]
            )
        ),
    )
    assert result.receipt.terminal_state == "fail_closed"
    assert result.receipt.attempts[0].reason_code == "length_content_state_not_empty"


def test_clock_failure_is_settled_without_raw_clock_text():
    def bad_clock():
        raise RuntimeError("clock body secret")

    result = CandidateEvaluationHarness().evaluate(
        _request(),
        _run(),
        transport=_Transport(lambda: _Stream(_complete_events())),
        clock=bad_clock,
    )
    assert result.receipt.terminal_state == "fail_closed"
    assert result.receipt.safe_error_code == "clock_unavailable"
    assert "clock body secret" not in repr(result)
