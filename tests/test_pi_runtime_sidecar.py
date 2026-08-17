from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from app.evaluation.pi_runtime import (
    PiAllowedTool,
    PiInputMessage,
    PiScriptedAssistantStep,
    PiScriptedFailureStep,
    PiScriptedToolCall,
    PiScriptedUsage,
    PiSpikePolicy,
    PiSpikeRunRequest,
)
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.tools.adapters import build_knowledge_tools
from app.tools.models import RetryPolicy, ToolDefinition, ToolPolicy
from app.tools.registry import ToolRegistry
from app.tools.runtime import ToolRuntime

from app.evaluation.pi_runtime.controller import (
    PiSidecarController,
    build_safe_environment,
)
from app.evaluation.pi_runtime.protocol import encode_frame
from app.evaluation.pi_runtime.models import PROTOCOL_VERSION


KNOWLEDGE_INPUT = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "minLength": 1},
        "top_k": {"type": "integer", "minimum": 1, "maximum": 20},
    },
    "required": ["query", "top_k"],
    "additionalProperties": False,
}
KNOWLEDGE_OUTPUT = {
    "type": "object",
    "properties": {"answer": {"type": "string"}},
    "required": ["answer"],
    "additionalProperties": False,
}


def fake_knowledge_registry(handler=None):
    calls: list[dict] = []

    def search(params, _context):
        calls.append(dict(params))
        if handler is not None:
            return handler(params)
        return {"answer": params["query"]}

    definition = ToolDefinition(
        name="knowledge.search",
        version="2.0.0",
        description="Search attributable coaching knowledge.",
        handler=search,
        input_schema=KNOWLEDGE_INPUT,
        output_schema=KNOWLEDGE_OUTPUT,
        policy=ToolPolicy(retry=RetryPolicy(max_attempts=1)),
    )
    registry = ToolRegistry()
    registry.register(definition)
    return registry, ToolRuntime(registry), calls, definition


def request_for(definition, *, script, policy=None):
    return PiSpikeRunRequest(
        run_id="pi_spike_sidecar_001",
        system_prompt="Use only the declared coaching knowledge tool.",
        messages=(
            PiInputMessage(
                role="user",
                content="Review the frozen recent-form context.",
            ),
        ),
        allowed_tools=(
            PiAllowedTool(
                name="knowledge.search",
                version="2.0.0",
                description=definition.description,
                input_schema=definition.input_schema,
            ),
        ),
        script=tuple(script),
        policy=policy
        or PiSpikePolicy(
            max_iterations=4,
            max_tool_calls=8,
            timeout_s=5.0,
            max_context_chars=20_000,
        ),
    )


def tool_call(*, call_id="call_1", name="knowledge.search", query="lane deaths"):
    return PiScriptedToolCall(
        id=call_id,
        name=name,
        arguments={"query": query, "top_k": 1},
    )


def final_step(text="safe final draft"):
    return PiScriptedAssistantStep(
        content=text,
        usage=PiScriptedUsage(input_tokens=7, output_tokens=4),
    )


def tool_step(*calls):
    return PiScriptedAssistantStep(
        content=None,
        tool_calls=tuple(calls),
        usage=PiScriptedUsage(input_tokens=6, output_tokens=3),
    )


def run_controller(request, registry, runtime):
    return PiSidecarController(
        tool_registry=registry,
        tool_runtime=runtime,
    ).run(request)


def _valid_child_result_frame(run_id: str) -> bytes:
    return encode_frame(
        {
            "protocol_version": PROTOCOL_VERSION,
            "type": "run.result",
            "run_id": run_id,
            "result": {
                "status": "completed",
                "stop_reason": "final_response",
                "iterations": 0,
                "final_text": "safe final",
                "error_code": None,
                "provider_calls_attempted": 0,
                "response_usages": [],
                "tool_executions": [],
            },
        }
    )


def _run_python_sidecar(request, registry, runtime, tmp_path, body: str):
    sidecar = tmp_path / "fake_sidecar.py"
    sidecar.write_text(body, encoding="utf-8")
    return PiSidecarController(
        tool_registry=registry,
        tool_runtime=runtime,
        sidecar_path=sidecar,
        node_executable=sys.executable,
        use_permission_model=False,
    ).run(request)


def test_sidecar_can_finish_direct_final_without_provider_io():
    registry, runtime, calls, definition = fake_knowledge_registry()

    result = run_controller(
        request_for(definition, script=(final_step(),)),
        registry,
        runtime,
    )

    assert result.status == "completed"
    assert result.stop_reason == "final_response"
    assert result.final_text == "safe final draft"
    assert result.external_provider_calls == 0
    assert result.usage.provider_calls_attempted == 1
    assert result.usage.input_tokens == 7
    assert calls == []


def test_sidecar_round_trips_real_python_tool_runtime():
    registry, runtime, calls, definition = fake_knowledge_registry()
    request = request_for(
        definition,
        script=(tool_step(tool_call()), final_step("evidence received")),
    )

    result = run_controller(request, registry, runtime)

    assert result.status == "completed"
    assert result.stop_reason == "final_response"
    assert result.final_text == "evidence received"
    assert calls == [{"query": "lane deaths", "top_k": 1}]
    assert len(result.tool_executions) == 1
    assert result.tool_executions[0].success is True
    assert result.usage.tool_calls == 1
    safe_json = result.model_dump_json()
    assert "lane deaths" not in safe_json
    assert "answer" not in safe_json
    assert [event.event_type for event in result.safe_events] == [
        "provider_started",
        "provider_completed",
        "tool_started",
        "tool_completed",
        "provider_started",
        "provider_completed",
        "agent_completed",
    ]
    event_json = json.dumps(
        [event.model_dump(mode="json") for event in result.safe_events]
    )
    assert "Use only the declared coaching knowledge tool" not in event_json
    assert "Review the frozen recent-form context" not in event_json
    assert "lane deaths" not in event_json
    assert "evidence received" not in event_json


def test_sidecar_rejects_unauthorized_batch_before_python_tool_io():
    registry, runtime, calls, definition = fake_knowledge_registry()
    request = request_for(
        definition,
        script=(
            tool_step(
                tool_call(call_id="allowed"),
                tool_call(call_id="forbidden", name="filesystem.read"),
            ),
        ),
    )

    result = run_controller(request, registry, runtime)

    assert result.status == "failed"
    assert result.stop_reason == "tool_not_allowed"
    assert result.error_code == "tool_not_allowed"
    assert calls == []
    assert result.tool_executions == ()


def test_sidecar_rejects_over_budget_batch_before_python_tool_io():
    registry, runtime, calls, definition = fake_knowledge_registry()
    request = request_for(
        definition,
        script=(
            tool_step(tool_call(call_id="first"), tool_call(call_id="second")),
        ),
        policy=PiSpikePolicy(
            max_iterations=4,
            max_tool_calls=1,
            timeout_s=5.0,
            max_context_chars=20_000,
        ),
    )

    result = run_controller(request, registry, runtime)

    assert result.status == "stopped"
    assert result.stop_reason == "max_tool_calls"
    assert calls == []


def test_sidecar_rejects_duplicate_batch_and_cross_turn_before_second_execution():
    registry, runtime, calls, definition = fake_knowledge_registry()
    batch = request_for(
        definition,
        script=(tool_step(tool_call(), tool_call(call_id="call_2")),),
    )
    batch_result = run_controller(batch, registry, runtime)
    assert batch_result.stop_reason == "duplicate_tool_call"
    assert calls == []

    registry, runtime, calls, definition = fake_knowledge_registry()
    repeated = request_for(
        definition,
        script=(
            tool_step(tool_call()),
            tool_step(tool_call(call_id="call_2")),
            final_step(),
        ),
    )
    repeated_result = run_controller(repeated, registry, runtime)
    assert repeated_result.stop_reason == "duplicate_tool_call"
    assert len(calls) == 1


def test_sidecar_rejects_invalid_schema_before_python_tool_io():
    registry, runtime, calls, definition = fake_knowledge_registry()
    invalid = request_for(
        definition,
        script=(tool_step(tool_call(query="")),),
    )

    result = run_controller(invalid, registry, runtime)

    assert result.status == "failed"
    assert result.stop_reason == "invalid_tool_input"
    assert result.error_code == "invalid_tool_input"
    assert calls == []


def test_sidecar_tool_failure_is_projected_and_can_still_finish():
    def fail(_params):
        raise RuntimeError("RAW handler exception must not escape")

    registry, runtime, calls, definition = fake_knowledge_registry(handler=fail)
    request = request_for(
        definition,
        script=(tool_step(tool_call()), final_step("safe fallback after tool error")),
    )

    result = run_controller(request, registry, runtime)

    assert result.status == "completed"
    assert result.final_text == "safe fallback after tool error"
    assert result.tool_executions[0].success is False
    assert result.tool_executions[0].failure_code == "tool_execution_failed"
    assert "RAW handler exception" not in result.model_dump_json()


def test_sidecar_counts_failed_tool_attempt_against_later_batch_budget():
    def fail(_params):
        raise RuntimeError("first tool fails")

    registry, runtime, calls, definition = fake_knowledge_registry(handler=fail)
    request = request_for(
        definition,
        script=(
            tool_step(tool_call(query="first query")),
            tool_step(tool_call(call_id="call_2", query="second query")),
        ),
        policy=PiSpikePolicy(
            max_iterations=4,
            max_tool_calls=1,
            timeout_s=5.0,
            max_context_chars=20_000,
        ),
    )

    result = run_controller(request, registry, runtime)

    assert result.status == "stopped"
    assert result.stop_reason == "max_tool_calls"
    assert calls == [{"query": "first query", "top_k": 1}]
    assert len(result.tool_executions) == 1
    assert result.tool_executions[0].success is False


@pytest.mark.parametrize(
    ("failure", "status", "reason"),
    [
        (
            PiScriptedFailureStep(
                kind="provider_error", error_code="scripted_provider_error"
            ),
            "failed",
            "provider_error",
        ),
        (
            PiScriptedFailureStep(
                kind="provider_abort", error_code="scripted_provider_abort"
            ),
            "stopped",
            "provider_aborted",
        ),
    ],
)
def test_sidecar_provider_failures_are_safe_and_usage_is_unknown(
    failure, status, reason
):
    registry, runtime, calls, definition = fake_knowledge_registry()
    result = run_controller(
        request_for(definition, script=(failure,)),
        registry,
        runtime,
    )

    assert result.status == status
    assert result.stop_reason == reason
    assert result.usage.token_observation.value == "unknown"
    assert result.usage.input_tokens is None
    assert calls == []


def test_sidecar_marks_usage_partial_after_observed_response_then_provider_error():
    registry, runtime, calls, definition = fake_knowledge_registry()
    result = run_controller(
        request_for(
            definition,
            script=(
                tool_step(tool_call()),
                PiScriptedFailureStep(
                    kind="provider_error",
                    error_code="scripted_provider_error",
                ),
            ),
        ),
        registry,
        runtime,
    )

    assert result.status == "failed"
    assert result.stop_reason == "provider_error"
    assert result.usage.provider_calls_attempted == 2
    assert result.usage.provider_responses_observed == 1
    assert result.usage.token_observation.value == "partial"
    assert result.usage.observed_input_tokens == 6
    assert result.usage.observed_output_tokens == 3
    assert result.usage.input_tokens is None
    assert result.usage.output_tokens is None
    assert calls == [{"query": "lane deaths", "top_k": 1}]


def test_sidecar_stops_before_provider_when_context_or_iteration_budget_is_exceeded():
    registry, runtime, calls, definition = fake_knowledge_registry()
    context_result = run_controller(
        request_for(
            definition,
            script=(final_step(),),
            policy=PiSpikePolicy(
                max_iterations=4,
                max_tool_calls=8,
                timeout_s=5.0,
                max_context_chars=1,
            ),
        ),
        registry,
        runtime,
    )
    assert context_result.stop_reason == "context_budget_exceeded"
    assert context_result.usage.provider_calls_attempted == 0

    registry, runtime, calls, definition = fake_knowledge_registry()
    iteration_result = run_controller(
        request_for(
            definition,
            script=(tool_step(tool_call()), final_step()),
            policy=PiSpikePolicy(
                max_iterations=1,
                max_tool_calls=8,
                timeout_s=5.0,
                max_context_chars=20_000,
            ),
        ),
        registry,
        runtime,
    )
    assert iteration_result.stop_reason == "max_iterations"
    assert calls == []


def test_sidecar_uses_real_local_knowledge_provider_without_network():
    provider = LocalHybridKnowledgeProvider.from_directory(Path("data/rag_docs"))
    definitions = build_knowledge_tools(provider)
    registry = ToolRegistry()
    for definition in definitions:
        registry.register(definition)
    definition = definitions[0]
    request = request_for(
        definition,
        script=(
            PiScriptedAssistantStep(
                content=None,
                tool_calls=(
                    PiScriptedToolCall(
                        id="knowledge_1",
                        name="knowledge.search",
                        arguments={"query": "Data Dragon 能提供英雄胜率吗", "top_k": 2},
                    ),
                ),
                usage=PiScriptedUsage(input_tokens=12, output_tokens=5),
            ),
            final_step("local evidence returned"),
        ),
    )

    result = run_controller(request, registry, ToolRuntime(registry))

    assert result.status == "completed"
    assert result.tool_executions[0].success is True
    assert result.usage.tool_calls == 1
    assert result.final_text == "local evidence returned"


def test_sidecar_fail_closes_on_invalid_json_from_child(tmp_path):
    registry, runtime, calls, definition = fake_knowledge_registry()
    result = _run_python_sidecar(
        request_for(definition, script=(final_step(),)),
        registry,
        runtime,
        tmp_path,
        'import sys\nsys.stdout.write("not-json\\n")\nsys.stdout.flush()\n',
    )

    assert result.status == "failed"
    assert result.stop_reason == "protocol_error"
    assert result.error_code == "invalid_json"
    assert calls == []


def test_sidecar_fail_closes_on_child_run_id_mismatch(tmp_path):
    registry, runtime, calls, definition = fake_knowledge_registry()
    frame = _valid_child_result_frame("different_run")
    result = _run_python_sidecar(
        request_for(definition, script=(final_step(),)),
        registry,
        runtime,
        tmp_path,
        f"import sys\nsys.stdout.buffer.write({frame!r})\nsys.stdout.flush()\n",
    )

    assert result.status == "failed"
    assert result.stop_reason == "protocol_error"
    assert result.error_code == "run_id_mismatch"
    assert calls == []


def test_sidecar_fail_closes_on_child_crash(tmp_path):
    registry, runtime, calls, definition = fake_knowledge_registry()
    result = _run_python_sidecar(
        request_for(definition, script=(final_step(),)),
        registry,
        runtime,
        tmp_path,
        "raise SystemExit(1)\n",
    )

    assert result.status == "failed"
    assert result.stop_reason == "process_error"
    assert result.error_code == "process_error"
    assert calls == []


def test_sidecar_fail_closes_on_unexpected_stderr(tmp_path):
    registry, runtime, calls, definition = fake_knowledge_registry()
    frame = _valid_child_result_frame("pi_spike_sidecar_001")
    result = _run_python_sidecar(
        request_for(definition, script=(final_step(),)),
        registry,
        runtime,
        tmp_path,
        "import sys\n"
        "sys.stderr.write('private diagnostic\\n')\n"
        "sys.stderr.flush()\n"
        f"sys.stdout.buffer.write({frame!r})\n"
        "sys.stdout.flush()\n",
    )

    assert result.status == "failed"
    assert result.stop_reason == "protocol_error"
    assert result.error_code == "unexpected_stderr"
    assert "private diagnostic" not in result.model_dump_json()
    assert calls == []


def test_sidecar_terminates_child_after_total_deadline(tmp_path):
    registry, runtime, calls, definition = fake_knowledge_registry()
    request = request_for(
        definition,
        script=(final_step(),),
        policy=PiSpikePolicy(
            max_iterations=4,
            max_tool_calls=8,
            timeout_s=0.1,
            max_context_chars=20_000,
        ),
    )
    result = _run_python_sidecar(
        request,
        registry,
        runtime,
        tmp_path,
        "import time\ntime.sleep(1.0)\n",
    )

    assert result.status == "stopped"
    assert result.stop_reason == "timeout"
    assert result.error_code == "timeout"
    assert calls == []


def test_sidecar_environment_allowlist_excludes_credentials_and_home():
    safe = build_safe_environment(
        {
            "PATH": "path-value",
            "RIOT_API_KEY": "riot-secret",
            "DEEPSEEK_API_KEY": "deepseek-secret",
            "OPENAI_API_KEY": "openai-secret",
            "HOME": "private-home",
            "USERPROFILE": "private-profile",
        }
    )

    assert safe["PATH"] == "path-value"
    assert safe["RIFTCOACH_PI_SPIKE"] == "1"
    assert not {"RIOT_API_KEY", "DEEPSEEK_API_KEY", "OPENAI_API_KEY"} & safe.keys()
    assert "HOME" not in safe
    assert "USERPROFILE" not in safe


def test_sidecar_returns_safe_failure_before_spawn_on_tool_contract_drift():
    registry, runtime, calls, definition = fake_knowledge_registry()
    declared_request = request_for(definition, script=(final_step(),))
    drifted_definition = ToolDefinition(
        name="knowledge.search",
        version="2.0.0",
        description=definition.description,
        handler=lambda _params, _context: {"answer": "unused"},
        input_schema={
            **KNOWLEDGE_INPUT,
            "properties": {
                **KNOWLEDGE_INPUT["properties"],
                "source": {"type": "string"},
            },
        },
        output_schema=KNOWLEDGE_OUTPUT,
        policy=ToolPolicy(retry=RetryPolicy(max_attempts=1)),
    )
    drifted_registry = ToolRegistry()
    drifted_registry.register(drifted_definition)

    result = PiSidecarController(
        tool_registry=drifted_registry,
        tool_runtime=ToolRuntime(drifted_registry),
    ).run(declared_request)

    assert result.status == "failed"
    assert result.stop_reason == "protocol_error"
    assert result.error_code == "tool_contract_mismatch"
    assert result.usage.provider_calls_attempted == 0
    assert calls == []
