from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

from app.evaluation.provider_adapter_protocol import AdapterProtocolSliceRunner
from app.evaluation.provider_adoption import (
    ExperimentFailureCode,
    ExperimentPreparationReport,
)
from app.evaluation.provider_protocol_experiment import (
    run_deepseek_adapter_protocol_experiment,
)
from app.providers.capabilities import ProviderCapabilities
from app.providers.errors import ProviderAuthenticationError
from app.providers.models import ChatResponse, TokenUsage, ToolCall


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
    responses: list[ChatResponse | Exception]
    provider_name: str = "deepseek"
    model_name: str = "deepseek-v4-pro"
    capabilities: ProviderCapabilities = ProviderCapabilities(
        text_chat=True,
        tool_calling=True,
        structured_output=True,
    )

    def chat(self, request):
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def preparation() -> ExperimentPreparationReport:
    return ExperimentPreparationReport(
        provider_id="deepseek",
        requested_model="deepseek-v4-pro",
        base_url="https://api.deepseek.com",
        sdk_max_retries=0,
        stream=False,
        thinking="disabled",
        code_sha="a" * 40,
        public_ci_sha="a" * 40,
        public_ci_success_confirmed=True,
        dataset_id="domain-e2e-v1-1-secure-held-out",
        dataset_version="1.0.0",
        dataset_sha256="b" * 64,
        prompt_context_snapshot_id="recent-form-prompt-context-v1-1",
        prompt_context_snapshot_sha256="c" * 64,
        evaluation_contract="coach_evaluation@1.1.0",
        protocol_max_calls=3,
        domain_max_calls=12,
        cumulative_max_calls=15,
        maximum_total_tokens=16_000,
        maximum_output_tokens_per_request=1024,
        maximum_estimated_cost="0.10",
        currency="USD",
        external_provider_calls=0,
        held_out_executed=False,
        local_preflight_passed=True,
    )


def response(*, content=None, tool_calls=(), finish_reason="stop", usage=(10, 5)):
    return ChatResponse(
        content=content,
        model="deepseek-v4-pro",
        provider="deepseek",
        tool_calls=tool_calls,
        finish_reason=finish_reason,
        usage=TokenUsage(input_tokens=usage[0], output_tokens=usage[1]),
        request_id="RAW_REQUEST_ID",
    )


def successful_provider() -> ScriptedProvider:
    return ScriptedProvider(
        responses=[
            response(content=VALID_EVALUATION),
            response(
                tool_calls=(
                    ToolCall(
                        id="RAW_TOOL_CALL_ID",
                        name="knowledge.search",
                        arguments={
                            "query": "reduce deaths before 15 minutes",
                            "top_k": 1,
                        },
                    ),
                ),
                finish_reason="tool_calls",
                usage=(20, 4),
            ),
            response(content="RIFTCOACH_TOOL_ROUNDTRIP_OK", usage=(30, 3)),
        ]
    )


def test_experiment_composes_protocol_resource_and_stop_evidence() -> None:
    record = run_deepseek_adapter_protocol_experiment(
        preparation=preparation(),
        provider=successful_provider(),
        clock=lambda: 0.0,
        now=lambda: datetime(2026, 8, 14, tzinfo=timezone.utc),
    )

    assert record.protocol.admitted is True
    assert record.protocol.calls_used == 3
    assert record.resources.calls_used == 3
    assert record.resources.input_tokens == 60
    assert record.resources.output_tokens == 12
    assert record.resources.scope_calls[0].scope == "adapter_protocol"
    assert record.resources.scope_calls[0].calls_used == 3
    assert record.resources.scope_calls[1].scope == "domain"
    assert record.resources.scope_calls[1].calls_used == 0
    assert record.control.global_stop is None
    assert record.control.provider_stops == ()
    assert record.held_out_executed is False

    serialized = record.model_dump_json()
    for forbidden in (
        "RAW_REQUEST_ID",
        "RAW_TOOL_CALL_ID",
        "reduce deaths before 15 minutes",
        "RIFTCOACH_TOOL_ROUNDTRIP_OK",
    ):
        assert forbidden not in serialized


def test_provider_failure_is_sanitized_and_stops_candidate() -> None:
    provider = ScriptedProvider(
        responses=[
            ProviderAuthenticationError(
                provider="deepseek",
                code="authentication_failed",
            )
        ]
    )

    record = run_deepseek_adapter_protocol_experiment(
        preparation=preparation(),
        provider=provider,
        clock=lambda: 0.0,
        now=lambda: datetime(2026, 8, 14, tzinfo=timezone.utc),
    )

    assert record.protocol.admitted is False
    assert record.protocol.calls_used == 1
    assert record.protocol.cases[0].error_code == "authentication_failed"
    assert record.protocol.cases[1].status == "skipped"
    assert record.resources.calls_used == 1
    assert record.control.provider_stops[0].failure_code is (
        ExperimentFailureCode.PROVIDER_AUTHENTICATION_FAILED
    )


def test_mismatched_preparation_fails_before_provider() -> None:
    bad = preparation().model_copy(update={"code_sha": "d" * 40})
    provider = successful_provider()

    try:
        run_deepseek_adapter_protocol_experiment(
            preparation=bad,
            provider=provider,
        )
    except ValueError as exc:
        assert "public CI SHA" in str(exc)
    else:
        raise AssertionError("mismatched preparation must fail closed")

    assert len(provider.responses) == 3
