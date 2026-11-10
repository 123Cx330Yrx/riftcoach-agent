from __future__ import annotations

from dataclasses import FrozenInstanceError, asdict
import json

import pytest

from app.providers.models import TokenUsage
from app.providers.stream_adapter_contract import (
    ProviderStreamEvent,
    StreamAdapterError,
    StreamAssemblyResult,
    StreamAssemblyTrace,
    StreamToolCallDelta,
    ProviderStreamAssembler,
    validate_provider_stream_event,
)


def _event(
    *,
    content: str | None = None,
    reasoning: str | None = None,
    finish: str | None = None,
    usage: TokenUsage | None = None,
    model: str | None = "glm-5.3-flash",
    tools: tuple[StreamToolCallDelta, ...] = (),
    sequence: int | None = None,
    request_id_sha256: str | None = None,
) -> ProviderStreamEvent:
    return ProviderStreamEvent(
        content_delta=content,
        reasoning_delta=reasoning,
        finish_reason=finish,
        usage=usage,
        model=model,
        tool_call_deltas=tools,
        sequence=sequence,
        request_id_sha256=request_id_sha256,
    )


def _usage(*, input_tokens: int = 10, output_tokens: int = 7) -> TokenUsage:
    return TokenUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


def _assembler(*, cap: int | None = None) -> ProviderStreamAssembler:
    return ProviderStreamAssembler(
        provider_id="zhipu",
        requested_model="glm-5.3-flash",
        max_output_tokens=cap,
    )


def _finish(assembler: ProviderStreamAssembler) -> StreamAssemblyResult:
    assembler.mark_exhausted()
    return assembler.finalize()


def test_normalized_event_is_frozen_and_rejects_raw_or_malformed_values():
    event = _event(content="ok")
    with pytest.raises(FrozenInstanceError):
        event.content_delta = "secret"  # type: ignore[misc]

    with pytest.raises(ValueError, match="safe finish"):
        _event(finish="raw finish reason")
    with pytest.raises(ValueError, match="tool_call_deltas"):
        ProviderStreamEvent(tool_call_deltas=(object(),))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="hard safety bound"):
        StreamToolCallDelta(index=0, arguments_delta="x" * 256_001)
    with pytest.raises(ValueError, match="bounded string"):
        ProviderStreamEvent(content_delta="x" * 4_000_001)
    with pytest.raises(TypeError):
        ProviderStreamEvent(raw_response="secret")  # type: ignore[call-arg]
    with pytest.raises(ValueError, match="SHA-256"):
        _event(request_id_sha256="raw-request-id")
    with pytest.raises(ValueError, match="SHA-256"):
        StreamAssemblyTrace(
            provider_id="zhipu",
            requested_model="glm-5.3-flash",
            resolved_model="glm-5.3-flash",
            request_id_sha256=123,  # type: ignore[arg-type]
            chunk_count=1,
            terminal_chunk_ordinal=1,
            usage_chunk_ordinal=1,
            finish_reason="stop",
        )

    with pytest.raises(ValueError, match="custom stream error message"):
        StreamAdapterError("stream_failed", "SECRET_BODY_MARKER")
    safe_error = StreamAdapterError("stream_failed", "safe_detail")
    assert str(safe_error) == "stream_failed"


def test_shared_event_validator_is_used_for_both_boundary_paths():
    valid = _event(content="ok", finish="stop", usage=_usage(), sequence=1)
    validate_provider_stream_event(valid, ordinal=1)
    with pytest.raises(StreamAdapterError, match="sequence_conflict"):
        validate_provider_stream_event(valid, ordinal=2)
    with pytest.raises(StreamAdapterError, match="content_limit"):
        validate_provider_stream_event(
            _event(content="ok"),
            ordinal=1,
            max_content_chars=1,
        )
    with pytest.raises(StreamAdapterError, match="stream_event_limit"):
        validate_provider_stream_event(valid, ordinal=1, max_events=0)


def test_result_repr_keeps_response_body_and_tool_arguments_private():
    assembler = _assembler()
    assembler.accept(
        _event(
            content="SECRET_BODY_MARKER",
            finish="stop",
            usage=_usage(),
        )
    )

    rendered = repr(_finish(assembler))

    assert "SECRET_BODY_MARKER" not in rendered
    assert "response=" not in rendered


def test_text_stream_assembles_reasoning_content_terminal_and_usage():
    assembler = _assembler()
    assembler.accept(_event(model="glm-5.3-flash", reasoning="think "))
    assembler.accept(_event(content="RIFT"))
    assembler.accept(_event(content="COACH", finish="stop"))
    assembler.accept(_event(usage=_usage()))

    result = _finish(assembler)

    assert isinstance(result, StreamAssemblyResult)
    assert result.response.content == "RIFTCOACH"
    assert result.response.reasoning_content == "think "
    assert result.response.provider == "zhipu"
    assert result.response.model == "glm-5.3-flash"
    assert result.response.finish_reason == "stop"
    assert result.response.usage.total_tokens == 17
    trace = result.trace.as_dict()
    assert trace["chunk_count"] == 4
    assert trace["content_chunk_count"] == 2
    assert trace["reasoning_chunk_count"] == 1
    assert trace["first_visible_chunk_ordinal"] == 2
    assert trace["terminal_chunk_ordinal"] == 3
    assert trace["usage_chunk_ordinal"] == 4
    assert trace["complete"] is True


def test_visible_content_preserves_leading_and_trailing_whitespace():
    assembler = _assembler()
    assembler.accept(
        _event(content="  answer\n", finish="stop", usage=_usage())
    )

    assert _finish(assembler).response.content == "  answer\n"


def test_terminal_and_usage_can_share_one_normalized_event():
    assembler = _assembler()
    assembler.accept(_event(content="done", finish="stop", usage=_usage()))

    result = _finish(assembler)

    assert result.trace.usage_chunk_ordinal == 1
    assert result.trace.terminal_chunk_ordinal == 1


def test_terminal_prefix_cannot_finalize_before_source_exhaustion():
    assembler = _assembler()
    assembler.accept(_event(content="done", finish="stop", usage=_usage()))

    with pytest.raises(StreamAdapterError, match="stream_not_exhausted") as exc:
        assembler.finalize()
    assert exc.value.code == "stream_not_exhausted"
    # This lifecycle check is non-poisoning; the caller can seal after EOF.
    assert _finish(assembler).response.content == "done"


def test_finalize_is_idempotent_after_success():
    assembler = _assembler()
    assembler.accept(_event(content="done", finish="stop", usage=_usage()))

    first = _finish(assembler)
    second = assembler.finalize()

    assert first is second


def test_usage_before_terminal_is_rejected():
    assembler = _assembler()
    with pytest.raises(StreamAdapterError, match="usage_before_terminal") as exc:
        assembler.accept(_event(usage=_usage()))
    assert exc.value.code == "usage_before_terminal"


def test_post_terminal_payload_is_rejected_but_usage_only_is_allowed():
    assembler = _assembler()
    assembler.accept(_event(content="done", finish="stop"))
    with pytest.raises(StreamAdapterError, match="payload_after_terminal") as exc:
        assembler.accept(_event(content="late"))
    assert exc.value.code == "payload_after_terminal"

    # A clean stream may put Usage in one trailing usage-only frame.
    clean = _assembler()
    clean.accept(_event(content="done", finish="stop"))
    clean.accept(_event(usage=_usage()))
    assert _finish(clean).response.content == "done"


def test_post_terminal_usage_tail_is_single_use_and_empty_frames_are_rejected():
    assembler = _assembler()
    assembler.accept(_event(content="done", finish="stop"))
    assembler.accept(_event(usage=_usage()))
    with pytest.raises(StreamAdapterError, match="duplicate_usage") as exc:
        assembler.accept(_event(usage=_usage()))
    assert exc.value.code == "duplicate_usage"

    empty = _assembler()
    empty.accept(_event(content="done", finish="stop"))
    with pytest.raises(StreamAdapterError, match="payload_after_terminal"):
        empty.accept(_event())


@pytest.mark.parametrize(
    ("events", "code"),
    [
        ((), "missing_terminal"),
        ((_event(content="done", finish="stop"),), "usage_unavailable"),
        ((_event(usage=_usage()),), "usage_before_terminal"),
        (
            (_event(content="partial", finish="length", usage=_usage()),),
            "incomplete_stream",
        ),
    ],
)
def test_incomplete_or_unterminated_stream_fails_closed(events, code):
    assembler = _assembler()
    for event in events:
        if event.usage is not None and event.finish_reason is None:
            with pytest.raises(StreamAdapterError):
                assembler.accept(event)
        else:
            assembler.accept(event)
    if code == "usage_before_terminal":
        # The invalid early Usage event poisons the stream before EOF.
        with pytest.raises(StreamAdapterError, match=code) as exc:
            assembler.finalize()
        assert exc.value.code == code
        return
    assembler.mark_exhausted()
    with pytest.raises(StreamAdapterError, match=code) as exc:
        assembler.finalize()
    assert exc.value.code == code


def test_model_identity_is_stable_and_conflicts_fail_closed():
    assembler = _assembler()
    assembler.accept(_event(model="glm-5.3-flash", content="done"))
    with pytest.raises(StreamAdapterError, match="model_conflict") as exc:
        assembler.accept(_event(model="other-model", finish="stop"))
    assert exc.value.code == "model_conflict"


def test_explicit_sequence_and_request_identity_must_remain_stable():
    request_digest = "a" * 64
    assembler = _assembler()
    assembler.accept(
        _event(
            sequence=1,
            request_id_sha256=request_digest,
            content="done",
            finish="stop",
            usage=_usage(),
        )
    )
    with pytest.raises(StreamAdapterError, match="sequence_conflict") as exc:
        assembler.accept(_event(sequence=3))
    assert exc.value.code == "sequence_conflict"

    other = _assembler()
    other.accept(_event(sequence=1, request_id_sha256=request_digest))
    with pytest.raises(StreamAdapterError, match="request_identity_conflict") as exc:
        other.accept(
            _event(
                sequence=2,
                request_id_sha256="b" * 64,
                content="done",
                finish="stop",
                usage=_usage(),
            )
        )
    assert exc.value.code == "request_identity_conflict"


def test_abort_is_fail_closed_and_does_not_open_a_recovery_path():
    assembler = _assembler()
    assembler.accept(_event(reasoning="private"))
    assembler.abort("read_timeout")
    with pytest.raises(StreamAdapterError, match="read_timeout") as exc:
        assembler.finalize()
    assert exc.value.code == "read_timeout"
    with pytest.raises(StreamAdapterError, match="read_timeout"):
        assembler.accept(_event(content="late"))


def test_rejected_event_is_atomic_and_poisons_the_stream():
    assembler = _assembler()
    with pytest.raises(StreamAdapterError, match="usage_before_terminal"):
        assembler.accept(_event(model="glm-5.3-flash", usage=_usage()))

    # The rejected event did not partially commit, but the stream is poisoned
    # and cannot be used as an implicit recovery path.
    with pytest.raises(StreamAdapterError, match="usage_before_terminal"):
        assembler.accept(
            _event(
                sequence=1,
                model="glm-5.3-flash",
                content="done",
                finish="stop",
                usage=_usage(),
            )
        )


def test_invalid_event_type_poisons_the_stream_instead_of_opening_recovery():
    assembler = _assembler()
    with pytest.raises(StreamAdapterError, match="invalid_event") as exc:
        assembler.accept({"content_delta": "bad"})  # type: ignore[arg-type]
    assert exc.value.code == "invalid_event"

    with pytest.raises(StreamAdapterError, match="invalid_event") as later:
        assembler.accept(
            _event(content="done", finish="stop", usage=_usage())
        )
    assert later.value.code == "invalid_event"


def test_invalid_cached_usage_is_rejected_before_state_changes():
    assembler = _assembler()
    with pytest.raises(StreamAdapterError, match="invalid_usage"):
        assembler.accept(
            _event(
                content="done",
                finish="stop",
                usage=TokenUsage(
                    input_tokens=2,
                    output_tokens=1,
                    cached_input_tokens=3,
                ),
            )
        )
    with pytest.raises(StreamAdapterError, match="invalid_usage"):
        assembler.finalize()


def test_required_model_and_request_identity_are_observed_before_completion():
    missing_model = ProviderStreamAssembler(
        provider_id="zhipu",
        requested_model="glm-5.3-flash",
    )
    missing_model.accept(
        _event(model=None, content="done", finish="stop", usage=_usage())
    )
    missing_model.mark_exhausted()
    with pytest.raises(StreamAdapterError, match="model_unobserved"):
        missing_model.finalize()

    missing_identity = ProviderStreamAssembler(
        provider_id="zhipu",
        requested_model="glm-5.3-flash",
        require_request_identity=True,
    )
    missing_identity.accept(
        _event(content="done", finish="stop", usage=_usage())
    )
    missing_identity.mark_exhausted()
    with pytest.raises(StreamAdapterError, match="request_identity_unobserved"):
        missing_identity.finalize()


def test_configured_text_and_tool_bounds_fail_closed():
    text = ProviderStreamAssembler(
        provider_id="zhipu",
        requested_model="glm-5.3-flash",
        max_content_chars=3,
    )
    with pytest.raises(StreamAdapterError, match="content_limit"):
        text.accept(_event(content="four"))

    args = ProviderStreamAssembler(
        provider_id="zhipu",
        requested_model="glm-5.3-flash",
        max_tool_argument_chars=2,
    )
    with pytest.raises(StreamAdapterError, match="tool_argument_limit"):
        args.accept(
            _event(
                tools=(
                    StreamToolCallDelta(
                        index=0,
                        call_id="call-1",
                        name="tool",
                        arguments_delta="{}x",
                    ),
                )
            )
        )


def test_tool_fragments_are_assembled_in_index_order_and_json_is_decoded():
    assembler = _assembler()
    assembler.accept(
        _event(
            tools=(
                StreamToolCallDelta(
                    index=0,
                    call_id="call-1",
                    name="knowledge.search",
                    arguments_delta='{"query":"',
                ),
            )
        )
    )
    assembler.accept(
        _event(
            tools=(
                StreamToolCallDelta(index=0, arguments_delta="兵线"),
            )
        )
    )
    assembler.accept(
        _event(
            tools=(
                StreamToolCallDelta(index=0, arguments_delta='"}'),
            ),
            finish="tool_calls",
            usage=_usage(output_tokens=5),
        )
    )

    result = _finish(assembler)

    assert result.response.content is None
    assert result.response.tool_calls[0].id == "call-1"
    assert result.response.tool_calls[0].name == "knowledge.search"
    assert result.response.tool_calls[0].arguments == {"query": "兵线"}
    assert result.trace.tool_call_chunk_count == 3
    assert result.trace.tool_call_count == 1


def test_one_event_may_carry_multiple_parallel_tool_fragments():
    assembler = _assembler()
    assembler.accept(
        _event(
            tools=(
                StreamToolCallDelta(
                    index=0,
                    call_id="call-1",
                    name="first",
                    arguments_delta="{}",
                ),
                StreamToolCallDelta(
                    index=1,
                    call_id="call-2",
                    name="second",
                    arguments_delta="{}",
                ),
            ),
            finish="tool_calls",
            usage=_usage(),
        )
    )
    result = _finish(assembler)

    assert [call.name for call in result.response.tool_calls] == [
        "first",
        "second",
    ]
    assert result.trace.chunk_count == 1
    assert result.trace.tool_call_chunk_count == 2
    assert result.trace.tool_call_count == 2


def test_tool_fragments_require_contiguous_indexes_and_valid_json():
    assembler = _assembler()
    assembler.accept(
        _event(
            tools=(
                StreamToolCallDelta(
                    index=1,
                    call_id="call-2",
                    name="tool",
                    arguments_delta="{}",
                ),
            ),
            finish="tool_calls",
            usage=_usage(),
        )
    )
    assembler.mark_exhausted()
    with pytest.raises(StreamAdapterError, match="tool_call_index") as exc:
        assembler.finalize()
    assert exc.value.code == "tool_call_index"

    malformed = _assembler()
    malformed.accept(
        _event(
            tools=(
                StreamToolCallDelta(
                    index=0,
                    call_id="call-1",
                    name="tool",
                    arguments_delta='{"x":',
                ),
            ),
            finish="tool_calls",
            usage=_usage(),
        )
    )
    malformed.mark_exhausted()
    with pytest.raises(StreamAdapterError, match="tool_call_arguments") as exc:
        malformed.finalize()
    assert exc.value.code == "tool_call_arguments"

    non_finite = _assembler()
    non_finite.accept(
        _event(
            tools=(
                StreamToolCallDelta(
                    index=0,
                    call_id="call-1",
                    name="tool",
                    arguments_delta='{"x":1e1000000}',
                ),
            ),
            finish="tool_calls",
            usage=_usage(),
        )
    )
    non_finite.mark_exhausted()
    with pytest.raises(StreamAdapterError, match="tool_call_arguments") as exc:
        non_finite.finalize()
    assert exc.value.code == "tool_call_arguments"

    deep = _assembler()
    deep.accept(
        _event(
            tools=(
                StreamToolCallDelta(
                    index=0,
                    call_id="call-1",
                    name="tool",
                    arguments_delta='{"x":' + ("[" * 66) + "0" + ("]" * 66) + "}",
                ),
            ),
            finish="tool_calls",
            usage=_usage(),
        )
    )
    deep.mark_exhausted()
    with pytest.raises(StreamAdapterError, match="tool_call_arguments") as exc:
        deep.finalize()
    assert exc.value.code == "tool_call_arguments"


def test_tool_calls_and_visible_content_are_mutually_exclusive():
    assembler = _assembler()
    assembler.accept(
        _event(
            content="oops",
            tools=(
                StreamToolCallDelta(
                    index=0,
                    call_id="call-1",
                    name="tool",
                    arguments_delta="{}",
                ),
            ),
            finish="tool_calls",
            usage=_usage(),
        )
    )
    assembler.mark_exhausted()
    with pytest.raises(StreamAdapterError, match="tool_calls_with_content") as exc:
        assembler.finalize()
    assert exc.value.code == "tool_calls_with_content"


def test_output_budget_is_enforced_at_finalize():
    assembler = _assembler(cap=6)
    assembler.accept(_event(content="done", finish="stop", usage=_usage(output_tokens=7)))

    assembler.mark_exhausted()
    with pytest.raises(StreamAdapterError, match="output_budget_exceeded") as exc:
        assembler.finalize()
    assert exc.value.code == "output_budget_exceeded"


def test_trace_is_body_free_and_has_no_request_or_sdk_fields():
    assembler = _assembler()
    assembler.accept(_event(reasoning="private reasoning"))
    assembler.accept(_event(content="visible answer", finish="stop", usage=_usage()))
    trace = _finish(assembler).trace
    encoded = json.dumps(trace.as_dict(), ensure_ascii=False, sort_keys=True)

    assert "private reasoning" not in encoded
    assert "visible answer" not in encoded
    forbidden = {
        "content",
        "reasoning",
        "reasoning_content",
        "prompt",
        "messages",
        "request_id",
        "api_key",
        "raw_response",
        "tool_arguments",
    }
    assert forbidden.isdisjoint(trace.as_dict())
    assert forbidden.isdisjoint(asdict(trace))


def test_invalid_finish_reason_and_conflicting_terminal_are_rejected():
    assembler = _assembler()
    with pytest.raises(StreamAdapterError, match="invalid_finish_reason") as exc:
        assembler.accept(_event(content="done", finish="weird"))
    assert exc.value.code == "invalid_finish_reason"

    assembler = _assembler()
    assembler.accept(_event(content="done", finish="stop"))
    with pytest.raises(StreamAdapterError, match="duplicate_terminal") as exc:
        assembler.accept(_event(finish="stop"))
    assert exc.value.code == "duplicate_terminal"
