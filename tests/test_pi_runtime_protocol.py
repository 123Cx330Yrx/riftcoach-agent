from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from app.evaluation.pi_runtime import (
    MAX_FRAME_BYTES,
    PI_AGENT_CORE_VERSION,
    PROTOCOL_VERSION,
    PiAllowedTool,
    PiInputMessage,
    PiProtocolError,
    PiSafeEvent,
    PiScriptedAssistantStep,
    PiScriptedFailureStep,
    PiScriptedToolCall,
    PiScriptedUsage,
    PiSpikePolicy,
    PiSpikeRunRequest,
    PiSpikeRunResult,
    PiToolExecutionProjection,
    build_runtime_usage,
    decode_frame,
    encode_frame,
)
from app.runtime.models import CostObservation, TokenObservation


KNOWLEDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "minLength": 1},
        "top_k": {"type": "integer", "minimum": 1, "maximum": 20},
    },
    "required": ["query", "top_k"],
    "additionalProperties": False,
}


def knowledge_tool() -> PiAllowedTool:
    return PiAllowedTool(
        name="knowledge.search",
        version="2.0.0",
        description="Search attributable coaching knowledge.",
        input_schema=KNOWLEDGE_SCHEMA,
    )


def assistant_step(*, content="safe draft", tool_calls=(), usage=None):
    return PiScriptedAssistantStep(
        content=content,
        tool_calls=tool_calls,
        usage=usage or PiScriptedUsage(input_tokens=5, output_tokens=3),
    )


def run_request(*, script=None, tools=None) -> PiSpikeRunRequest:
    return PiSpikeRunRequest(
        run_id="pi_spike_001",
        system_prompt="Use evidence and obey the tool contract.",
        messages=(
            PiInputMessage(
                role="user",
                content="Review the frozen recent-form context.",
            ),
        ),
        allowed_tools=tuple(tools or (knowledge_tool(),)),
        script=tuple(script or (assistant_step(),)),
        policy=PiSpikePolicy(
            max_iterations=4,
            max_tool_calls=2,
            timeout_s=5.0,
            max_context_chars=20_000,
        ),
    )


def test_protocol_request_is_strict_and_frozen_to_one_knowledge_tool() -> None:
    request = run_request()

    assert request.protocol_version == PROTOCOL_VERSION == "1.0"
    assert request.pi_agent_core_version == PI_AGENT_CORE_VERSION == "0.84.2"
    assert request.allowed_tools[0].name == "knowledge.search"
    assert request.script[0].kind == "assistant"

    with pytest.raises(ValidationError, match="extra_forbidden"):
        PiInputMessage(role="user", content="x", raw_secret="no")

    with pytest.raises(ValidationError, match="knowledge.search"):
        run_request(
            tools=(
                PiAllowedTool(
                    name="filesystem.read",
                    version="1.0.0",
                    description="Forbidden.",
                    input_schema={"type": "object"},
                ),
            )
        )


def test_scripted_assistant_requires_content_or_tool_calls_and_unique_ids() -> None:
    with pytest.raises(ValidationError, match="content or at least one tool call"):
        PiScriptedAssistantStep(content=None, tool_calls=(), usage=None)

    duplicate = PiScriptedToolCall(
        id="call_1",
        name="knowledge.search",
        arguments={"query": "lane deaths", "top_k": 1},
    )
    with pytest.raises(ValidationError, match="tool call ids must be unique"):
        assistant_step(content=None, tool_calls=(duplicate, duplicate))


def test_scripted_failure_has_only_allowlisted_safe_error_codes() -> None:
    failure = PiScriptedFailureStep(
        kind="provider_error",
        error_code="scripted_provider_error",
    )
    assert failure.error_code == "scripted_provider_error"

    with pytest.raises(ValidationError, match="error_code"):
        PiScriptedFailureStep(
            kind="provider_error",
            error_code="RAW upstream exception with a secret",
        )


def test_runtime_usage_preserves_complete_partial_unknown_and_not_applicable() -> None:
    known_a = PiScriptedUsage(input_tokens=5, output_tokens=3)
    known_b = PiScriptedUsage(input_tokens=8, output_tokens=4)

    complete = build_runtime_usage(
        provider_calls_attempted=2,
        response_usages=(known_a, known_b),
        tool_executions=(),
    )
    assert complete.token_observation is TokenObservation.COMPLETE
    assert complete.input_tokens == complete.observed_input_tokens == 13
    assert complete.output_tokens == complete.observed_output_tokens == 7

    partial = build_runtime_usage(
        provider_calls_attempted=2,
        response_usages=(known_a, None),
        tool_executions=(),
    )
    assert partial.token_observation is TokenObservation.PARTIAL
    assert partial.observed_input_tokens == 5
    assert partial.input_tokens is None

    unknown = build_runtime_usage(
        provider_calls_attempted=1,
        response_usages=(None,),
        tool_executions=(),
    )
    assert unknown.token_observation is TokenObservation.UNKNOWN
    assert unknown.observed_input_tokens == 0
    assert unknown.input_tokens is None

    not_applicable = build_runtime_usage(
        provider_calls_attempted=0,
        response_usages=(),
        tool_executions=(),
    )
    assert not_applicable.token_observation is TokenObservation.NOT_APPLICABLE
    assert not_applicable.cost_observation is CostObservation.NOT_CONFIGURED


def test_runtime_usage_rejects_impossible_response_count() -> None:
    with pytest.raises(ValueError, match="response usages cannot outnumber attempts"):
        build_runtime_usage(
            provider_calls_attempted=0,
            response_usages=(PiScriptedUsage(input_tokens=1, output_tokens=1),),
            tool_executions=(),
        )


def test_result_projection_is_body_free_but_can_return_unpublished_draft() -> None:
    execution = PiToolExecutionProjection(
        tool_name="knowledge.search",
        tool_version="2.0.0",
        ordinal=1,
        success=True,
        failure_code=None,
        attempts=1,
        latency_ms=2.5,
        cached=False,
        fallback_used=False,
    )
    usage = build_runtime_usage(
        provider_calls_attempted=1,
        response_usages=(PiScriptedUsage(input_tokens=5, output_tokens=3),),
        tool_executions=(execution,),
    )
    result = PiSpikeRunResult(
        run_id="pi_spike_001",
        status="completed",
        stop_reason="final_response",
        iterations=1,
        final_text="unpublished safe draft",
        usage=usage,
        safe_events=(
            PiSafeEvent(
                event_type="agent_completed",
                ordinal=1,
                iteration=1,
                success=True,
            ),
        ),
        tool_executions=(execution,),
    )

    serialized = result.model_dump_json()
    assert result.external_provider_calls == 0
    assert "unpublished safe draft" in serialized
    assert "query" not in serialized
    assert "chunks" not in serialized

    with pytest.raises(ValidationError, match="extra_forbidden"):
        PiSafeEvent(
            event_type="tool_completed",
            ordinal=1,
            iteration=1,
            success=True,
            arguments={"query": "must not persist"},
        )


def test_non_completed_result_cannot_claim_a_final_draft() -> None:
    usage = build_runtime_usage(
        provider_calls_attempted=0,
        response_usages=(),
        tool_executions=(),
    )
    with pytest.raises(ValidationError, match="only completed runs may expose final_text"):
        PiSpikeRunResult(
            run_id="pi_spike_001",
            status="failed",
            stop_reason="provider_error",
            iterations=0,
            final_text="unsafe",
            error_code="provider_failed",
            usage=usage,
        )


def test_jsonl_frame_round_trip_is_canonical_and_versioned() -> None:
    frame = {
        "protocol_version": PROTOCOL_VERSION,
        "type": "run.start",
        "run_id": "pi_spike_001",
        "request": run_request().model_dump(mode="json"),
    }

    encoded = encode_frame(frame)

    assert encoded.endswith(b"\n")
    assert len(encoded) <= MAX_FRAME_BYTES
    assert decode_frame(encoded) == frame
    assert encoded == (
        json.dumps(
            frame,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        (b"not-json\n", "invalid_json"),
        (b"[]\n", "invalid_frame"),
        (
            b'{"protocol_version":"9.9","type":"event","run_id":"x"}\n',
            "protocol_version_mismatch",
        ),
        (
            b'{"protocol_version":"1.0","type":"shell.exec","run_id":"x"}\n',
            "unsupported_frame_type",
        ),
    ],
)
def test_jsonl_frame_rejects_invalid_or_unknown_input(payload, code) -> None:
    with pytest.raises(PiProtocolError) as exc_info:
        decode_frame(payload)
    assert exc_info.value.code == code


def test_jsonl_frame_rejects_oversized_and_multi_line_input() -> None:
    with pytest.raises(PiProtocolError) as exc_info:
        decode_frame(b"{" + b"x" * MAX_FRAME_BYTES + b"}\n")
    assert exc_info.value.code == "frame_too_large"

    with pytest.raises(PiProtocolError) as exc_info:
        decode_frame(
            b'{"protocol_version":"1.0","type":"event","run_id":"x"}\n'
            b'{"protocol_version":"1.0","type":"event","run_id":"x"}\n'
        )
    assert exc_info.value.code == "invalid_frame"
