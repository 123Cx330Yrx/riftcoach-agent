"""Offline tests for the candidate boundary-observation contract."""

from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError
from types import SimpleNamespace
from typing import Any

import pytest

from app.evaluation.candidate_stream_contract import (
    BoundaryObservation,
    CandidateAttemptKind,
    CandidateIdentityError,
    CandidateObservationError,
    CandidateRuntimeBinding,
    CandidateStreamBoundaryObserver,
    CandidateStreamTrace,
    CandidateTransportError,
    CandidateZhipuStreamTransport,
    FRESH_RECOVERY_CANDIDATE_BINDING,
    PRIMARY_CANDIDATE_BINDING,
    field_state,
    merge_field_states,
    observe_candidate_events,
)
from app.providers.models import ChatMessage, ChatRequest, MessageRole, TokenUsage
from app.providers.response_completion_policy import (
    ResponseCompletionMode,
    ResponseRequestContext,
)
from app.providers.stream_adapter_contract import ProviderStreamEvent, StreamToolCallDelta


MODEL = "glm-5.3-flash"
REQUEST_SHA = hashlib.sha256(b"fixture-request").hexdigest()


def event(
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


def request(*, max_tokens: int | None = None) -> ChatRequest:
    return ChatRequest(
        messages=(ChatMessage(MessageRole.USER, "offline fixture"),),
        max_tokens=max_tokens,
    )


def recovery_context() -> ResponseRequestContext:
    return ResponseRequestContext(
        phase="agent_initial",
        has_response_contract=False,
        has_tools=False,
        has_tool_side_effects=False,
        remaining_timeout_s=90,
        remaining_token_budget=8192,
    )


def test_binding_is_exact_and_attempt_kind_is_contiguous() -> None:
    assert CandidateRuntimeBinding.primary() is PRIMARY_CANDIDATE_BINDING
    assert CandidateRuntimeBinding.fresh_recovery() is FRESH_RECOVERY_CANDIDATE_BINDING
    assert PRIMARY_CANDIDATE_BINDING.attempt_kind is CandidateAttemptKind.PRIMARY
    assert FRESH_RECOVERY_CANDIDATE_BINDING.attempt_kind is CandidateAttemptKind.FRESH_RECOVERY
    with pytest.raises(FrozenInstanceError):
        PRIMARY_CANDIDATE_BINDING.model = "other"  # type: ignore[misc]
    with pytest.raises(CandidateIdentityError, match="candidate_attempt_mismatch"):
        CandidateRuntimeBinding(attempt_ordinal=1, attempt_kind="fresh_recovery")  # type: ignore[arg-type]
    with pytest.raises(CandidateIdentityError, match="candidate_identity_mismatch"):
        CandidateRuntimeBinding(model="glm-5.2")


def test_pre_open_failures_and_model_mismatch_stay_body_free() -> None:
    observer = CandidateStreamBoundaryObserver(clock=lambda: 1.0)
    observed = observer.finalize()
    assert observed.observation_state == "fail_closed"
    assert observed.error_code == "stream_not_opened"
    assert observed.close_state == "not_observed"

    observer = CandidateStreamBoundaryObserver(clock=lambda: (_ for _ in ()).throw(RuntimeError("secret")))
    observed = observe_candidate_events([], observer=observer)
    assert observed.error_code == "clock_unavailable"
    assert observed.close_state == "not_observed"
    assert "secret" not in repr(observed)

    observer = CandidateStreamBoundaryObserver(clock=lambda: 1.0)
    observer.open()
    with pytest.raises(CandidateObservationError, match="model_mismatch"):
        observer.accept(
            ProviderStreamEvent(
                model="glm-5.2",
                request_id_sha256=REQUEST_SHA,
            )
        )
    assert observer.snapshot().error_code == "model_mismatch"


def test_public_observation_cannot_forge_a_derived_state() -> None:
    common = dict(
        opened=True,
        eof_observed=True,
        terminal_observed=True,
        close_state="closed",
        finish_reason="stop",
        content_state="non_empty",
        reasoning_content_state="not_observed",
        usage_state="valid",
        input_tokens=1,
        output_tokens=1,
        cached_input_tokens=0,
        resolved_model=MODEL,
        request_id_sha256=REQUEST_SHA,
    )
    with pytest.raises(CandidateObservationError, match="state_lifecycle_mismatch"):
        BoundaryObservation(
            **common,
            observation_state="not_started",
            next_action="observe",
        )
    with pytest.raises(CandidateObservationError, match="state_action_mismatch"):
        BoundaryObservation(
            **common,
            observation_state="complete_text",
            next_action="observe",
        )


def test_cleanup_does_not_swallow_keyboard_interrupt() -> None:
    class InterruptingStream:
        def __iter__(self):
            return iter([event(content="done", finish="stop", usage=TokenUsage(1, 1, 0))])

        def close(self) -> None:
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        observe_candidate_events(InterruptingStream(), clock=lambda: 1.0)


def test_finalized_observer_is_immutable_and_snapshot_is_cached() -> None:
    observer = CandidateStreamBoundaryObserver(clock=lambda: 1.0)
    observer.open()
    observer.accept(event(content="done", finish="stop", usage=TokenUsage(1, 1, 0)))
    observer.mark_exhausted()
    observer.close()
    first = observer.finalize()
    assert observer.finalize() is first
    assert observer.snapshot() is first
    for operation in (
        lambda: observer.accept(event(content="late")),
        observer.mark_exhausted,
        observer.close,
        lambda: observer.abort("late_abort", "lifecycle"),
        lambda: observer.observe_field_states(content="secret"),
    ):
        with pytest.raises(CandidateObservationError, match="already_finalized"):
            operation()
    assert "secret" not in repr(observer.snapshot())


def test_field_state_observation_cannot_reopen_a_sealed_boundary() -> None:
    observer = CandidateStreamBoundaryObserver(clock=lambda: 1.0)
    observer.open()
    observer.accept(event(content="done", finish="stop", usage=TokenUsage(1, 1, 0)))
    observer.mark_exhausted()
    with pytest.raises(CandidateObservationError, match="boundary_sealed"):
        observer.observe_field_states(content="late")


def test_observer_poisoning_is_sticky_before_any_new_lifecycle_transition() -> None:
    observer = CandidateStreamBoundaryObserver(clock=lambda: 1.0)
    with pytest.raises(CandidateObservationError, match="stream_not_opened"):
        observer.accept(event(content="private"))
    assert observer.failed_code == "stream_not_opened"
    for operation in (observer.open, observer.mark_exhausted, observer.close):
        with pytest.raises(CandidateObservationError, match="stream_not_opened"):
            operation()
    observer.abort("different_error", "transport")
    assert observer.failed_code == "stream_not_opened"


def test_field_state_precedence_and_observation_serialization_are_body_free() -> None:
    assert field_state(None) == "null"
    assert field_state("") == "empty"
    assert field_state("  ") == "empty"
    assert field_state("private body") == "non_empty"
    assert field_state({"secret": "body"}) == "non_string"
    assert merge_field_states("not_observed", "empty") == "empty"
    assert merge_field_states("empty", "non_empty") == "non_empty"
    assert merge_field_states("non_empty", "empty") == "non_empty"

    payload = BoundaryObservation().as_dict()
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    assert "candidate_eligible" not in payload
    assert "content" not in payload
    assert "reasoning" not in payload
    assert "tool_arguments" not in payload
    assert "private body" not in encoded


def test_normalized_event_preserves_explicit_null_without_confusing_absence() -> None:
    absent = ProviderStreamEvent(model=MODEL, request_id_sha256=REQUEST_SHA)
    explicit_null = ProviderStreamEvent(
        model=MODEL,
        request_id_sha256=REQUEST_SHA,
        content_observed=True,
        reasoning_observed=True,
    )
    assert absent.content_observed is False
    assert absent.reasoning_observed is False
    assert explicit_null.content_observed is True
    assert explicit_null.reasoning_observed is True

    observed = observe_candidate_events(
        [
            explicit_null,
            event(reasoning="thinking", finish="length", sequence=2),
            event(usage=TokenUsage(1, 1, 0), sequence=3, model=None, request_id=None),
        ],
        clock=lambda: 1.0,
    )
    assert observed.content_state == "null"
    assert observed.reasoning_content_state == "non_empty"
    assert observed.error_code == "length_without_empty_content"


def test_complete_text_stream_is_observed_without_retaining_body() -> None:
    observed = observe_candidate_events(
        [
            event(content="answer"),
            event(content="", reasoning="private reasoning", finish="stop", sequence=2),
            event(usage=TokenUsage(12, 5, 2), sequence=3, model=None, request_id=None),
        ],
        clock=lambda: 1.0,
    )

    assert observed.observation_state == "complete_text"
    assert observed.next_action == "terminal_complete"
    assert observed.complete_boundary is True
    assert observed.content_state == "non_empty"
    assert observed.reasoning_content_state == "non_empty"
    assert observed.usage_state == "valid"
    assert observed.input_tokens == 12
    assert observed.output_tokens == 5
    assert observed.cached_input_tokens == 2
    assert observed.to_response_boundary_snapshot().finish_reason == "stop"
    assert "answer" not in json.dumps(observed.as_dict(), ensure_ascii=False)
    assert "private reasoning" not in repr(observed)


def test_length_reasoning_only_shape_is_classified_by_existing_policy() -> None:
    observed = observe_candidate_events(
        [
            event(content="", reasoning="hidden"),
            event(finish="length", sequence=2, usage=TokenUsage(20, 8192, 0)),
        ],
        clock=lambda: 1.0,
    )
    assert observed.observation_state == "candidate_shape"
    assert observed.next_action == "requires_registered_runtime"
    decision = observed.classify(context=recovery_context())
    assert decision.candidate_eligible is True
    assert decision.continuation_allowed is False
    assert decision.disposition.value == "candidate_eligible"
    assert "hidden" not in json.dumps(observed.as_dict(), ensure_ascii=False)


@pytest.mark.parametrize(
    ("events", "expected_code"),
    [
        ([event(content="partial")], "missing_terminal"),
        ([event(content="", reasoning="r"), event(finish="length", sequence=2)], "usage_unavailable"),
        ([event(content="done", finish="stop", request_id=None)], "request_identity_unobserved"),
    ],
)
def test_missing_lifecycle_or_usage_is_fail_closed(
    events: list[ProviderStreamEvent], expected_code: str
) -> None:
    # The third fixture intentionally has no request identity; all other
    # fixtures retain the default identity and therefore expose the first
    # missing boundary in the expected order.
    observed = observe_candidate_events(events, clock=lambda: 1.0)
    assert observed.observation_state == "fail_closed"
    assert observed.error_code == expected_code
    assert observed.complete_boundary is False


def test_missing_usage_remains_missing_not_invalid() -> None:
    observed = observe_candidate_events(
        [event(content="done", finish="stop")],
        clock=lambda: 1.0,
    )
    assert observed.error_code == "usage_unavailable"
    assert observed.usage_state == "missing"
    assert observed.input_tokens is None


def test_identity_sequence_and_payload_after_terminal_fail_closed_without_body() -> None:
    observer = CandidateStreamBoundaryObserver(clock=lambda: 1.0)
    observer.open()
    observer.accept(event(content="first", sequence=1))
    with pytest.raises(CandidateObservationError, match="sequence_conflict"):
        observer.accept(event(content="secret", sequence=3))
    observed = observer.snapshot()
    assert observed.error_code == "sequence_conflict"
    assert "secret" not in repr(observed)

    observer = CandidateStreamBoundaryObserver(clock=lambda: 1.0)
    observer.open()
    observer.accept(event(content="", reasoning="r", finish="length", sequence=1))
    with pytest.raises(CandidateObservationError, match="payload_after_terminal"):
        observer.accept(event(content="secret", sequence=2))
    assert observer.snapshot().error_code == "payload_after_terminal"


def test_tool_metadata_is_required_and_call_ids_are_unique() -> None:
    observed = observe_candidate_events(
        [
            event(
                tools=(StreamToolCallDelta(index=0, arguments_delta="{}"),),
            ),
            event(finish="tool_calls", sequence=2),
            event(usage=TokenUsage(2, 2, 0), sequence=3, model=None, request_id=None),
        ],
        clock=lambda: 1.0,
    )
    assert observed.error_code == "tool_call_metadata"

    duplicate_id = StreamToolCallDelta(index=0, call_id="same", name="a")
    duplicate_id_other = StreamToolCallDelta(index=1, call_id="same", name="b")
    observed = observe_candidate_events(
        [
            event(tools=(duplicate_id,)),
            event(tools=(duplicate_id_other,), sequence=2),
            event(finish="tool_calls", sequence=3),
            event(usage=TokenUsage(2, 2, 0), sequence=4, model=None, request_id=None),
        ],
        clock=lambda: 1.0,
    )
    assert observed.error_code == "tool_call_id_conflict"

    missing_arguments = observe_candidate_events(
        [
            event(tools=(StreamToolCallDelta(index=0, call_id="c", name="a"),)),
            event(finish="tool_calls", sequence=2),
            event(usage=TokenUsage(2, 2, 0), sequence=3, model=None, request_id=None),
        ],
        clock=lambda: 1.0,
    )
    assert missing_arguments.error_code == "tool_call_arguments"


def test_malformed_tool_event_does_not_partially_commit_prior_fragments() -> None:
    observer = CandidateStreamBoundaryObserver(clock=lambda: 1.0)
    observer.open()
    first = StreamToolCallDelta(index=0, call_id="one", name="a", arguments_delta="{")
    conflicting = StreamToolCallDelta(index=0, call_id="two", name="a", arguments_delta="}")
    with pytest.raises(CandidateObservationError, match="tool_call_metadata_conflict"):
        observer.accept(event(tools=(first, conflicting)))
    observed = observer.snapshot()
    assert observed.error_code == "tool_call_metadata_conflict"
    assert observed.tool_call_count == 0


def test_output_budget_is_fail_closed_even_with_valid_usage() -> None:
    observed = observe_candidate_events(
        [
            event(content="done", finish="stop"),
            event(
                usage=TokenUsage(2, 8193, 0),
                sequence=2,
                model=None,
                request_id=None,
            ),
        ],
        clock=lambda: 1.0,
    )
    assert observed.error_code == "output_budget_exceeded"
    assert observed.usage_state == "valid"
    assert observed.output_tokens == 8193


def test_tool_count_is_bounded_and_arguments_never_enter_observation() -> None:
    tools = (
        StreamToolCallDelta(
            index=0,
            call_id="call-1",
            name="knowledge.search",
            arguments_delta='{"secret":"private"}',
        ),
    )
    observed = observe_candidate_events(
        [event(tools=tools), event(finish="length", sequence=2, usage=TokenUsage(4, 4, 0))],
        clock=lambda: 1.0,
    )
    assert observed.observation_state == "fail_closed"
    assert observed.error_code == "length_without_empty_content"
    encoded = json.dumps(observed.as_dict(), ensure_ascii=False)
    assert "private" not in encoded
    assert "secret" not in encoded
    assert observed.tool_call_count == 1


def test_usage_unknown_never_claims_zero_and_close_cannot_make_eof() -> None:
    observer = CandidateStreamBoundaryObserver(clock=lambda: 1.0)
    observer.open()
    observer.accept(event(content="", reasoning="r", finish="length", sequence=1))
    with pytest.raises(CandidateObservationError, match="close_before_eof"):
        observer.close()
    observed = observer.snapshot()
    assert observed.close_state == "failed"
    assert observed.usage_state == "missing"
    assert observed.input_tokens is None
    assert observed.output_tokens is None
    assert observed.eof_observed is False


def test_elapsed_budget_and_trace_projection_are_bounded() -> None:
    ticks = iter([10.0, 10.1, 10.2, 10.3, 10.4, 10.5])
    observer = CandidateStreamBoundaryObserver(clock=lambda: next(ticks), max_elapsed_ms=500)
    observer.open()
    observer.accept(event(content="done", sequence=1))
    observer.accept(event(finish="stop", sequence=2))
    observer.accept(event(usage=TokenUsage(1, 1, 0), sequence=3, model=None, request_id=None))
    observer.mark_exhausted()
    observer.close()
    observed = observer.finalize()
    assert observed.observation_state == "complete_text"
    trace = CandidateStreamTrace(observation=observed)
    payload = trace.as_dict()
    assert payload["trace_schema_version"] == "1.0"
    assert payload["elapsed_ms"] >= 0
    assert "done" not in json.dumps(payload)


def test_injected_candidate_transport_clamps_cap_and_forces_zero_retries() -> None:
    calls: list[dict[str, Any]] = []

    def opener(**kwargs: Any) -> list[ProviderStreamEvent]:
        calls.append(kwargs)
        return []

    transport = CandidateZhipuStreamTransport(opener)
    stream = transport.open_stream(
        PRIMARY_CANDIDATE_BINDING,
        request(max_tokens=16_384),
    )
    assert list(stream) == []
    assert calls[0]["max_output_tokens"] == 8192
    assert calls[0]["request"].max_tokens == 8192
    assert calls[0]["request"].temperature == 1.0
    assert calls[0]["request"].top_p == 0.95
    assert calls[0]["request"].timeout_s == 90.0
    assert calls[0]["max_retries"] == 0
    # The transport accepts either exact attempt binding; it does not invent
    # a third slot or silently alter the identity.
    assert transport.open_stream(
        CandidateRuntimeBinding.for_attempt(2),
        request(),
    ) == []


def test_transport_rejects_mismatched_metadata_before_opener() -> None:
    calls = 0

    def opener(**_: Any) -> list[ProviderStreamEvent]:
        nonlocal calls
        calls += 1
        return []

    transport = CandidateZhipuStreamTransport(opener)
    bad_request = ChatRequest(
        messages=(ChatMessage(MessageRole.USER, "offline fixture"),),
        metadata={"model": "glm-5.2"},
    )
    with pytest.raises(CandidateTransportError, match="request_identity_mismatch"):
        transport.open_stream(PRIMARY_CANDIDATE_BINDING, bad_request)
    assert calls == 0


def test_transport_rejects_bad_bounds_and_never_retries_or_leaks_opener_error() -> None:
    calls = 0

    def opener(**_: Any) -> list[ProviderStreamEvent]:
        nonlocal calls
        calls += 1
        raise RuntimeError("SECRET_PROVIDER_BODY")

    transport = CandidateZhipuStreamTransport(opener)
    with pytest.raises(CandidateTransportError, match="invalid_output_cap"):
        transport.open_stream(PRIMARY_CANDIDATE_BINDING, request(), max_output_tokens=0)
    with pytest.raises(CandidateTransportError, match="transport_open_failed") as caught:
        transport.open_stream(PRIMARY_CANDIDATE_BINDING, request())
    assert str(caught.value) == "transport_open_failed"
    assert "SECRET_PROVIDER_BODY" not in repr(caught.value)
    assert calls == 1

    with pytest.raises(CandidateTransportError, match="transport_timeout_invalid"):
        transport.open_stream(
            PRIMARY_CANDIDATE_BINDING,
            request(),
            timeout_s=91.0,
        )


def test_iterator_failure_is_returned_as_safe_observation() -> None:
    class Broken:
        def __iter__(self):
            yield event(content="partial")
            raise RuntimeError("private provider body")

        def close(self) -> None:
            raise RuntimeError("private close body")

    observed = observe_candidate_events(Broken(), clock=lambda: 1.0)
    assert observed.observation_state == "fail_closed"
    assert observed.error_code == "stream_read_failed"
    assert observed.close_state == "failed"
    assert "private" not in repr(observed)


def test_outer_iterable_is_closed_when_it_owns_a_distinct_iterator() -> None:
    class Outer:
        def __init__(self) -> None:
            self.closed = False

        def __iter__(self):
            return iter([event(content="partial")])

        def close(self) -> None:
            self.closed = True

    outer = Outer()
    observed = observe_candidate_events(outer, clock=lambda: 1.0)
    assert observed.error_code == "missing_terminal"
    assert outer.closed is True
