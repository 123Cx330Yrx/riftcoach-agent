"""Offline contract tests for the versioned candidate recovery diagnostic.

These tests deliberately use a fake normalized stream.  The diagnostic is an
evidence/control-plane seam; it must not need a provider SDK or a credential
in order to prove its lifecycle and redaction rules.
"""

from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from app.evaluation.candidate_recovery_diagnostic_v2 import (
    CANDIDATE_RECOVERY_DIAGNOSTIC_PROTOCOL_ID,
    CANDIDATE_RECOVERY_DIAGNOSTIC_SCHEMA_VERSION,
    CandidateRecoveryDiagnostic,
    CandidateRecoveryDiagnosticError,
    CandidateRecoveryDiagnosticIdentity,
    CandidateRecoveryExecutionPermit,
    CandidateRecoveryRunSpec,
    CostObservation,
    DiagnosticActivationGate,
    DiagnosticFailureClass,
    DiagnosticLatency,
    PriceSnapshot,
    write_candidate_recovery_receipt,
    context_shape_sha256,
)
from app.evaluation.candidate_stream_contract import (
    CandidateAttemptKind,
    CandidateZhipuStreamTransport,
    FRESH_RECOVERY_CANDIDATE_BINDING,
    PRIMARY_CANDIDATE_BINDING,
)
from app.providers.models import ChatMessage, ChatRequest, MessageRole, TokenUsage
from app.providers.response_completion_policy import ResponseRequestContext
from app.providers.stream_adapter_contract import ProviderStreamEvent, StreamToolCallDelta


MODEL = "glm-5.3-flash"
REQUEST_SHA = hashlib.sha256(b"diagnostic-request").hexdigest()
GIT_SHA = "0123456789abcdef0123456789abcdef01234567"


def _identity(**overrides: str) -> CandidateRecoveryDiagnosticIdentity:
    values = dict(
        implementation_sha=GIT_SHA,
        diagnostic_code_sha=GIT_SHA,
        input_plan_sha=GIT_SHA,
        context_shape_sha=context_shape_sha256(_context()),
    )
    values.update(overrides)
    return CandidateRecoveryDiagnosticIdentity(**values)


def _context() -> ResponseRequestContext:
    return ResponseRequestContext(
        phase="agent_initial",
        has_response_contract=False,
        has_tools=False,
        has_tool_side_effects=False,
        remaining_timeout_s=90,
        remaining_token_budget=8192,
    )


def _run(**identity_overrides: str) -> CandidateRecoveryRunSpec:
    return CandidateRecoveryRunSpec(identity=_identity(**identity_overrides), context=_context())


def _request(*, max_tokens: int | None = None) -> ChatRequest:
    return ChatRequest(
        messages=(ChatMessage(MessageRole.USER, "private prompt body"),),
        max_tokens=max_tokens,
    )


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
        self.events = tuple(events)
        self.close_error = close_error
        self.closed = False

    def __iter__(self):
        return iter(self.events)

    def close(self) -> None:
        self.closed = True
        if self.close_error:
            raise self.close_error


class _Transport:
    def __init__(self, factory):
        self.factory = factory
        self.calls: list[dict] = []

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
        return self.factory()


def _complete_events():
    return [
        _event(content="PRIVATE ANSWER BODY", sequence=1),
        _event(
            finish="stop",
            sequence=2,
            model=None,
            request_id=None,
        ),
        _event(
            usage=TokenUsage(input_tokens=12, output_tokens=4, cached_input_tokens=2),
            sequence=3,
            model=None,
            request_id=None,
        ),
    ]


def _length_events():
    return [
        _event(content="", reasoning="PRIVATE REASONING", sequence=1),
        _event(
            finish="length",
            usage=TokenUsage(input_tokens=12, output_tokens=8192, cached_input_tokens=0),
            sequence=2,
            model=None,
            request_id=None,
        ),
    ]


def test_identity_is_versioned_and_allows_only_complete_sha_shapes():
    identity = _identity()
    assert identity.protocol_id == CANDIDATE_RECOVERY_DIAGNOSTIC_PROTOCOL_ID
    assert identity.schema_version == CANDIDATE_RECOVERY_DIAGNOSTIC_SCHEMA_VERSION
    assert len(identity.run_nonce_sha256) == 64
    with pytest.raises(CandidateRecoveryDiagnosticError, match="invalid_git_sha"):
        _identity(implementation_sha="bad")
    with pytest.raises(CandidateRecoveryDiagnosticError, match="protocol"):
        replace(identity, protocol_id="other-protocol")


def test_request_summary_is_body_free_and_rejects_unknown_metadata():
    transport = _Transport(lambda: _Stream(_complete_events()))
    result = CandidateRecoveryDiagnostic(_run()).run(
        _request(),
        transport,
        clock=lambda: 1.0,
    )
    payload = result.as_dict()
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    assert "PRIVATE ANSWER BODY" not in encoded
    assert "PRIVATE REASONING" not in encoded
    assert "private prompt body" not in encoded
    assert payload["attempts"][0]["request"]["message_count"] == 1
    assert payload["attempts"][0]["request"]["roles"] == ["user"]
    assert payload["attempts"][0]["request"]["shape_sha256"]

    bad = replace(_request(), metadata={"secret": "do not accept"})
    with pytest.raises(CandidateRecoveryDiagnosticError, match="metadata"):
        CandidateRecoveryDiagnostic(_run()).run(bad, transport, clock=lambda: 1.0)
    assert len(transport.calls) == 1


def test_complete_attempt_has_segmented_latency_unknown_cost_and_body_free_repr():
    ticks = iter([10.0, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7])
    stream = _Stream(_complete_events())
    result = CandidateRecoveryDiagnostic(_run()).run(
        _request(),
        _Transport(lambda: stream),
        clock=lambda: next(ticks),
    )
    attempt = result.attempts[0]
    assert result.run_state == "complete_text"
    assert attempt.disposition == "complete_text"
    assert attempt.assembled_complete is True
    assert attempt.usage_state == "valid"
    assert attempt.input_tokens == 12
    assert attempt.output_tokens == 4
    assert attempt.latency.first_event_ms is not None
    assert attempt.latency.first_visible_content_ms is not None
    assert attempt.latency.terminal_ms is not None
    assert attempt.latency.close_elapsed_ms is not None
    assert attempt.cost.status == "unknown"
    assert attempt.cost.amount is None
    assert "PRIVATE ANSWER BODY" not in repr(result)


def test_exact_candidate_shape_is_recorded_but_activation_stays_disabled():
    transport = _Transport(lambda: _Stream(_length_events()))
    result = CandidateRecoveryDiagnostic(_run()).run(
        _request(), transport, clock=lambda: 2.0
    )
    assert result.run_state == "candidate_eligible"
    assert result.execution_allowed is False
    assert result.recovery_skip_reason == "activation_disabled"
    assert len(transport.calls) == 1
    assert result.attempts[0].attempt_kind == CandidateAttemptKind.PRIMARY.value
    assert result.attempts[0].failure_class is None


@pytest.mark.parametrize(
    ("events", "error_code", "failure_class"),
    [
        ([_event(content="partial", sequence=1)], "missing_terminal", "protocol"),
        ([_event(content="done", finish="stop", sequence=1)], "usage_unavailable", "usage"),
        ([_event(content="done", finish="stop", request_id=None)], "request_identity_unobserved", "identity"),
    ],
)
def test_missing_boundaries_are_fail_closed_and_classified(events, error_code, failure_class):
    result = CandidateRecoveryDiagnostic(_run()).run(
        _request(), _Transport(lambda: _Stream(events)), clock=lambda: 3.0
    )
    assert result.run_state == "fail_closed"
    assert result.attempts[0].error_code == error_code
    assert result.attempts[0].failure_class == failure_class
    assert result.first_failure["code"] == error_code


def test_open_read_close_and_control_failures_settle_the_reserved_primary():
    opened = CandidateRecoveryDiagnostic(_run()).run(
        _request(),
        _Transport(lambda: (_ for _ in ()).throw(RuntimeError("provider secret"))),
        clock=lambda: 4.0,
    )
    assert opened.calls_reserved == opened.calls_settled == 1
    assert opened.attempts[0].failure_class == "transport"
    assert opened.attempts[0].error_code == "transport_open_failed"

    closed_stream = _Stream(_complete_events(), close_error=RuntimeError("close secret"))
    closed = CandidateRecoveryDiagnostic(_run()).run(
        _request(), _Transport(lambda: closed_stream), clock=lambda: 4.0
    )
    assert closed.attempts[0].error_code == "stream_close_failed"
    assert closed.attempts[0].failure_class == "transport"
    assert closed_stream.closed is True


def test_permit_validation_distinguishes_disabled_expired_reused_and_identity_mismatch():
    permit = CandidateRecoveryExecutionPermit.for_offline_test(
        FRESH_RECOVERY_CANDIDATE_BINDING,
        now_ms=100,
        ttl_ms=100,
    )
    assert permit.verify(FRESH_RECOVERY_CANDIDATE_BINDING, now_ms=101) == "valid"
    assert permit.verify(FRESH_RECOVERY_CANDIDATE_BINDING, now_ms=201) == "expired"
    assert permit.verify(PRIMARY_CANDIDATE_BINDING, now_ms=101) == "identity_mismatch"
    assert permit.verify(FRESH_RECOVERY_CANDIDATE_BINDING, now_ms=101, used=True) == "reused"
    assert permit.verify(
        FRESH_RECOVERY_CANDIDATE_BINDING, now_ms=101, activation=DiagnosticActivationGate.DISABLED
    ) == "activation_disabled"


def test_cost_is_unknown_without_snapshot_and_estimated_only_with_verified_snapshot():
    usage = TokenUsage(input_tokens=1000, output_tokens=500, cached_input_tokens=0)
    unknown = CostObservation.unknown()
    assert unknown.status == "unknown" and unknown.amount is None
    snapshot = PriceSnapshot(
        snapshot_id_sha256=hashlib.sha256(b"price").hexdigest(),
        currency="USD",
        input_per_million=Decimal("1.00"),
        output_per_million=Decimal("2.00"),
    )
    estimated = CostObservation.estimated_from_usage(usage, snapshot)
    assert estimated.status == "estimated"
    assert estimated.amount == Decimal("0.002")
    with pytest.raises(CandidateRecoveryDiagnosticError, match="verified"):
        CostObservation.estimated_from_usage(
            usage,
            replace(snapshot, verified=False),
        )


def test_runner_keeps_unverified_price_as_unknown_without_losing_settlement():
    snapshot = PriceSnapshot(
        snapshot_id_sha256=hashlib.sha256(b"unverified-price").hexdigest(),
        currency="USD",
        input_per_million=Decimal("1"),
        output_per_million=Decimal("1"),
        verified=False,
    )
    result = CandidateRecoveryDiagnostic(_run(), price_snapshot=snapshot).run(
        _request(), _Transport(lambda: _Stream(_complete_events())), clock=lambda: 6.5
    )
    assert result.calls_reserved == result.calls_settled == 1
    assert result.cost.status == "unknown"


def test_latency_rejects_reverse_or_non_integer_negative_segments():
    with pytest.raises(CandidateRecoveryDiagnosticError, match="latency_not_monotonic"):
        DiagnosticLatency(
            open_elapsed_ms=10,
            first_event_ms=5,
            first_visible_content_ms=None,
            terminal_ms=None,
            close_elapsed_ms=None,
            total_elapsed_ms=10,
        )
    with pytest.raises(CandidateRecoveryDiagnosticError, match="invalid_integer"):
        DiagnosticLatency(
            open_elapsed_ms=-1,
            first_event_ms=None,
            first_visible_content_ms=None,
            terminal_ms=None,
            close_elapsed_ms=None,
            total_elapsed_ms=None,
        )


def test_receipt_json_is_canonical_create_only_and_never_overwrites(tmp_path: Path):
    result = CandidateRecoveryDiagnostic(_run()).run(
        _request(), _Transport(lambda: _Stream(_complete_events())), clock=lambda: 5.0
    )
    target = tmp_path / "receipt.json"
    written = write_candidate_recovery_receipt(target, result)
    assert target.read_bytes().endswith(b"\n")
    assert b"\r" not in target.read_bytes()
    assert written.sha256 == hashlib.sha256(target.read_bytes()).hexdigest()
    with pytest.raises(FileExistsError):
        write_candidate_recovery_receipt(target, result)
    assert json.loads(target.read_text(encoding="utf-8"))["schema_version"] == "2.0.0"


def test_receipt_rejects_forged_identity_and_unknown_body_fields():
    result = CandidateRecoveryDiagnostic(_run()).run(
        _request(), _Transport(lambda: _Stream(_complete_events())), clock=lambda: 6.0
    )
    with pytest.raises(CandidateRecoveryDiagnosticError, match="state"):
        replace(result, run_state="recovery_complete")
    payload = result.as_dict()
    payload["prompt"] = "secret prompt"
    with pytest.raises(CandidateRecoveryDiagnosticError, match="forbidden"):
        result.from_dict(payload)


def test_receipt_round_trip_revalidates_every_nested_allowlist():
    result = CandidateRecoveryDiagnostic(_run()).run(
        _request(), _Transport(lambda: _Stream(_complete_events())), clock=lambda: 6.0
    )
    restored = result.from_dict(json.loads(result.canonical_bytes()))
    assert restored.as_dict() == result.as_dict()
    forged = json.loads(result.canonical_bytes())
    forged["attempts"][0]["request"]["candidate_identity"]["model"] = "other"
    with pytest.raises(CandidateRecoveryDiagnosticError, match="identity"):
        result.from_dict(forged)


def test_static_candidate_transport_is_the_only_transport_shape_used():
    calls = []

    def opener(**kwargs):
        calls.append(kwargs)
        return [_event(content="x", finish="stop", usage=TokenUsage(1, 1, 0))]

    transport = CandidateZhipuStreamTransport(opener)
    assert list(transport.open_stream(PRIMARY_CANDIDATE_BINDING, _request()))
    assert calls[0]["max_retries"] == 0


def test_tool_stream_is_assembled_but_never_executed_or_logged():
    events = [
        _event(
            tools=(
                StreamToolCallDelta(
                    index=0,
                    call_id="call-1",
                    name="lookup",
                    arguments_delta='{"q":"private"}',
                ),
            ),
            sequence=1,
        ),
        _event(finish="tool_calls", sequence=2, model=None, request_id=None),
        _event(
            usage=TokenUsage(input_tokens=5, output_tokens=3, cached_input_tokens=0),
            sequence=3,
            model=None,
            request_id=None,
        ),
    ]
    consumer_calls = []

    class Consumer:
        def accept(self, response):
            consumer_calls.append(response)

    result = CandidateRecoveryDiagnostic(_run()).run(
        _request(), _Transport(lambda: _Stream(events)), consumer=Consumer(), clock=lambda: 7.0
    )
    assert result.run_state == "tool_calls_ready"
    assert result.attempts[0].assembled_complete is True
    assert len(consumer_calls) == 1
    encoded = json.dumps(result.as_dict(), ensure_ascii=False)
    assert "private" not in encoded
    assert "lookup" not in encoded


def test_unknown_usage_keeps_cumulative_tokens_and_cost_unknown():
    events = [_event(content="partial", sequence=1)]
    result = CandidateRecoveryDiagnostic(_run()).run(
        _request(), _Transport(lambda: _Stream(events)), clock=lambda: 8.0
    )
    assert result.budget.input_tokens is None
    assert result.budget.output_tokens is None
    assert result.budget.input_state == "unknown"
    assert result.budget.output_state == "unknown"
    assert result.budget.overall_state == "unknown"
    assert result.cost.status == "unknown"


def test_clock_failure_after_reservation_still_settles_without_latency_fabrication():
    calls = iter([10.0, 9.0])
    result = CandidateRecoveryDiagnostic(_run()).run(
        _request(), _Transport(lambda: _Stream(_complete_events())), clock=lambda: next(calls)
    )
    assert result.calls_reserved == result.calls_settled == 1
    assert result.run_state == "fail_closed"
    assert result.attempts[0].error_code == "clock_reversed"
    assert result.attempts[0].latency.total_elapsed_ms is None


def test_consumer_control_error_is_rethrown_after_safe_interrupted_receipt():
    class Consumer:
        def accept(self, response):
            raise KeyboardInterrupt

    diagnostic = CandidateRecoveryDiagnostic(_run())
    with pytest.raises(KeyboardInterrupt):
        diagnostic.run(
            _request(),
            _Transport(lambda: _Stream(_complete_events())),
            consumer=Consumer(),
            clock=lambda: 9.0,
        )
    assert diagnostic.last_receipt is not None
    assert diagnostic.last_receipt.run_state == "interrupted"
    assert diagnostic.last_receipt.first_failure["failure_class"] == "control"


def test_request_cap_is_recorded_separately_from_profile_cap():
    result = CandidateRecoveryDiagnostic(_run()).run(
        _request(max_tokens=123),
        _Transport(lambda: _Stream(_complete_events())),
        clock=lambda: 10.0,
    )
    assert result.attempts[0].request.output_cap == 123
    assert result.attempts[0].request.output_cap < 8192


def test_module_has_no_product_runtime_sdk_or_network_imports():
    module_path = (
        Path(__file__).parents[1]
        / "app"
        / "evaluation"
        / "candidate_recovery_diagnostic_v2.py"
    )
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    forbidden = (
        "openai",
        "httpx",
        "requests",
        "dotenv",
        "app.providers.zhipu",
        "app.providers.config",
        "app.agent",
        "app.runtime",
    )
    assert not [name for name in imports if name.startswith(forbidden)]
