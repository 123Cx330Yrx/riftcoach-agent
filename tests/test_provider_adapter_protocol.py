from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from app.evaluation.provider_adapter_protocol import (
    AdapterProtocolSliceRunner,
    BudgetedProvider,
)
from app.evaluation.provider_capability_gate import ExternalCallBudget
from app.model_runtime import GLM53_FLASH_RUNTIME_PROFILE
from app.providers.capabilities import ProviderCapabilities
from app.providers.errors import ProviderResponseError
from app.providers.models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    MessageRole,
    TokenUsage,
    ToolCall,
)


VALID_EVALUATION = json.dumps(
    {
        "score": 100,
        "verdict": "pass",
        "issues": [],
        "passed_checks": ["protocol contract"],
        "summary": "Structured protocol is valid.",
    }
)


@dataclass
class ScriptedProvider:
    responses: list[ChatResponse]
    provider_name: str = "fake-protocol-provider"
    model_name: str = "fake-protocol-model"
    capabilities: ProviderCapabilities = ProviderCapabilities(
        text_chat=True,
        tool_calling=True,
        structured_output=True,
    )

    def __post_init__(self) -> None:
        self.requests = []

    def chat(self, request):
        self.requests.append(request)
        return self.responses.pop(0)


def structured_response(content: str = VALID_EVALUATION) -> ChatResponse:
    return ChatResponse(
        content=content,
        model="fake-protocol-model-resolved",
        provider="fake-protocol-provider",
        finish_reason="stop",
        usage=TokenUsage(input_tokens=10, output_tokens=5),
        request_id="RAW_STRUCTURED_REQUEST_ID",
    )


def tool_response(arguments=None) -> ChatResponse:
    return ChatResponse(
        content=None,
        model="fake-protocol-model-resolved",
        provider="fake-protocol-provider",
        finish_reason="tool_calls",
        tool_calls=(
            ToolCall(
                id="RAW_TOOL_CALL_ID",
                name="knowledge.search",
                arguments=arguments
                or {"query": "reduce deaths before 15 minutes", "top_k": 1},
            ),
        ),
        usage=TokenUsage(input_tokens=20, output_tokens=4),
        request_id="RAW_TOOL_REQUEST_ID",
    )


def final_response(content: str = "RIFTCOACH_TOOL_ROUNDTRIP_OK") -> ChatResponse:
    return ChatResponse(
        content=content,
        model="fake-protocol-model-resolved",
        provider="fake-protocol-provider",
        finish_reason="stop",
        usage=TokenUsage(input_tokens=30, output_tokens=3),
        request_id="RAW_FINAL_REQUEST_ID",
    )


def build_runner(provider: ScriptedProvider) -> AdapterProtocolSliceRunner:
    return AdapterProtocolSliceRunner(
        provider=provider,
        code_sha="a" * 40,
        clock=lambda: 100.0,
        now=lambda: datetime(2026, 8, 13, tzinfo=timezone.utc),
    )


def test_protocol_slice_composes_structured_and_agent_round_trip() -> None:
    provider = ScriptedProvider(
        responses=[structured_response(), tool_response(), final_response()]
    )

    report = build_runner(provider).run()

    assert report.admitted is True
    assert report.calls_used == report.max_calls == 3
    assert [case.status for case in report.cases] == ["passed", "passed"]
    structured_case, agent_case = report.cases
    assert structured_case.external_calls == 1
    assert agent_case.external_calls == 2
    assert agent_case.tool_call_count == 1
    assert agent_case.tool_execution_count == 1
    assert agent_case.tool_arguments_sha256 is not None
    assert agent_case.tool_result_sha256 is not None

    assert provider.requests[0].response_contract is not None
    assert '"additionalProperties":false' in provider.requests[0].messages[0].content
    assert provider.requests[1].tools[0].name == "knowledge.search"
    assert provider.requests[2].messages[-1].role.value == "tool"

    serialized = report.model_dump_json()
    assert "RAW_" not in serialized
    assert "reduce deaths before 15 minutes" not in serialized
    assert "RIFTCOACH_TOOL_ROUNDTRIP_OK" not in serialized


def test_flash_runtime_profile_is_applied_to_every_protocol_request() -> None:
    provider = ScriptedProvider(
        responses=[structured_response(), tool_response(), final_response()],
        provider_name="zhipu",
        model_name="glm-5.3-flash",
    )

    report = AdapterProtocolSliceRunner(
        provider=provider,
        code_sha="a" * 40,
        runtime_profile=GLM53_FLASH_RUNTIME_PROFILE,
        clock=lambda: 100.0,
        now=lambda: datetime(2026, 8, 13, tzinfo=timezone.utc),
    ).run()

    assert report.admitted is True
    assert len(provider.requests) == 3
    assert all(request.max_tokens == 2048 for request in provider.requests)
    assert all(request.temperature == 1.0 for request in provider.requests)
    assert all(request.top_p == 0.95 for request in provider.requests)
    assert all(request.timeout_s == 90.0 for request in provider.requests)
    assert all(
        request.metadata["runtime_profile_id"]
        == GLM53_FLASH_RUNTIME_PROFILE.profile_id
        for request in provider.requests
    )


def test_structured_failure_stops_before_agent_loop() -> None:
    provider = ScriptedProvider(
        responses=[structured_response("not-json RAW_MODEL_SECRET")]
    )

    report = build_runner(provider).run()

    assert report.admitted is False
    assert report.calls_used == 1
    assert report.cases[0].status == "failed"
    assert report.cases[0].error_code == "invalid_structured_output"
    assert report.cases[1].status == "skipped"
    assert report.cases[1].error_code == "structured_contract_failed"
    assert len(provider.requests) == 1
    assert "RAW_MODEL_SECRET" not in report.model_dump_json()


def test_agent_answer_without_tool_fails_without_spending_third_call() -> None:
    provider = ScriptedProvider(
        responses=[
            structured_response(),
            final_response("answered directly RAW_MODEL_SECRET"),
        ]
    )

    report = build_runner(provider).run()

    assert report.admitted is False
    assert report.calls_used == 2
    assert report.cases[0].status == "passed"
    assert report.cases[1].status == "failed"
    assert report.cases[1].error_code == "tool_round_trip_incomplete"
    assert len(provider.requests) == 2
    assert "RAW_MODEL_SECRET" not in report.model_dump_json()


def test_invalid_tool_arguments_are_observed_but_not_admitted() -> None:
    provider = ScriptedProvider(
        responses=[
            structured_response(),
            tool_response({"query": "x", "top_k": 2}),
            final_response(),
        ]
    )

    report = build_runner(provider).run()

    assert report.admitted is False
    assert report.calls_used == 3
    assert report.cases[1].status == "failed"
    assert report.cases[1].error_code == "tool_execution_failed"
    assert report.cases[1].tool_execution_count == 1


def test_unexpected_provider_exception_is_sanitized_and_fail_closed() -> None:
    class ExplodingProvider(ScriptedProvider):
        def chat(self, request):
            self.requests.append(request)
            raise RuntimeError("RAW_UPSTREAM_EXCEPTION_SECRET")

    provider = ExplodingProvider(responses=[])

    report = build_runner(provider).run()

    assert report.admitted is False
    assert report.calls_used == 1
    assert report.cases[0].status == "failed"
    assert report.cases[0].error_code == "protocol_runner_error"
    assert report.cases[1].status == "skipped"
    assert "RAW_UPSTREAM_EXCEPTION_SECRET" not in report.model_dump_json()


def test_budgeted_provider_blocks_fourth_call_before_delegate() -> None:
    provider = ScriptedProvider(
        responses=[structured_response(), structured_response(), structured_response()]
    )
    budgeted = BudgetedProvider(
        provider=provider,
        budget=ExternalCallBudget(max_calls=3),
    )
    request = ChatRequest(
        messages=(ChatMessage(role=MessageRole.USER, content="protocol"),)
    )

    for _ in range(3):
        budgeted.chat(request)

    with pytest.raises(ProviderResponseError) as error:
        budgeted.chat(request)

    assert error.value.code == "external_call_budget_exhausted"
    assert len(provider.requests) == 3


def test_final_marker_must_match_exactly() -> None:
    provider = ScriptedProvider(
        responses=[
            structured_response(),
            tool_response(),
            final_response("RIFTCOACH_TOOL_ROUNDTRIP_OK plus extra text"),
        ]
    )

    report = build_runner(provider).run()

    assert report.admitted is False
    assert report.calls_used == 3
    assert report.cases[1].error_code == "final_marker_mismatch"


def test_second_tool_request_is_recorded_as_failure_not_report_crash() -> None:
    provider = ScriptedProvider(
        responses=[structured_response(), tool_response(), tool_response()]
    )

    report = build_runner(provider).run()

    assert report.admitted is False
    assert report.calls_used == 3
    assert report.cases[1].status == "failed"
    assert report.cases[1].error_code == "max_iterations"
    assert report.cases[1].tool_call_count == 2
    assert report.cases[1].tool_execution_count == 1
