from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from app.evaluation.glm53_flash_candidate_profile import (
    GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY,
)
from app.evaluation.glm53_low_profile_protocol import (
    GLM53LowProfileProtocolReport,
    canonical_report_bytes,
    run_glm53_low_profile_protocol,
    write_report_create_only,
)
from app.providers.capabilities import ProviderCapabilities
from app.providers.models import (
    ChatRequest,
    ChatResponse,
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
    provider_name: str = "zhipu"
    model_name: str = "glm-5.3-flash"
    capabilities: ProviderCapabilities = ProviderCapabilities(
        text_chat=True,
        tool_calling=True,
        structured_output=True,
    )

    def __post_init__(self) -> None:
        self.requests: list[ChatRequest] = []

    def chat(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        return self.responses.pop(0)


class AdvancingClock:
    """Expose protocol overhead that a constant fake clock would hide."""

    def __init__(self) -> None:
        self._value = 100.0

    def __call__(self) -> float:
        self._value += 0.001
        return self._value


def _response(
    *,
    content: str | None,
    finish_reason: str,
    input_tokens: int,
    output_tokens: int,
    tool_calls: tuple[ToolCall, ...] = (),
) -> ChatResponse:
    return ChatResponse(
        content=content,
        model="glm-5.3-flash",
        provider="zhipu",
        finish_reason=finish_reason,
        tool_calls=tool_calls,
        usage=TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        ),
        request_id="request-id-not-persisted",
    )


def _successful_provider() -> ScriptedProvider:
    return ScriptedProvider(
        responses=[
            _response(
                content=VALID_EVALUATION,
                finish_reason="stop",
                input_tokens=20,
                output_tokens=10,
            ),
            _response(
                content=None,
                finish_reason="tool_calls",
                input_tokens=30,
                output_tokens=8,
                tool_calls=(
                    ToolCall(
                        id="tool-call-not-persisted",
                        name="knowledge.search",
                        arguments={
                            "query": "reduce deaths before 15 minutes",
                            "top_k": 1,
                        },
                    ),
                ),
            ),
            _response(
                content="RIFTCOACH_TOOL_ROUNDTRIP_OK",
                finish_reason="stop",
                input_tokens=40,
                output_tokens=6,
            ),
        ]
    )


def test_low_profile_protocol_uses_candidate_policy_and_is_admitted() -> None:
    provider = _successful_provider()
    report = run_glm53_low_profile_protocol(
        provider=provider,
        implementation_sha="a" * 40,
        now=lambda: datetime(2026, 9, 4, tzinfo=timezone.utc),
        clock=lambda: 100.0,
    )

    assert isinstance(report, GLM53LowProfileProtocolReport)
    assert report.protocol.admitted is True
    assert report.provider_call_count == 3
    assert report.network_used is False
    assert report.explicit_real_call_confirmed is False
    assert report.request_policy_id == GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY.policy_id
    assert all(request.max_tokens == 4096 for request in provider.requests)
    assert all(request.temperature == 1.0 for request in provider.requests)
    assert all(request.top_p == 0.95 for request in provider.requests)
    assert all(request.timeout_s == 90.0 for request in provider.requests)
    assert all(
        request.metadata["evaluation_scope"] == "candidate-only"
        for request in provider.requests
    )

    serialized = canonical_report_bytes(report).decode("utf-8")
    assert "request-id-not-persisted" not in serialized
    assert "RIFTCOACH_TOOL_ROUNDTRIP_OK" not in serialized
    assert "reduce deaths before 15 minutes" not in serialized
    assert "content" not in serialized


def test_low_profile_protocol_reports_end_to_end_case_latency() -> None:
    report = run_glm53_low_profile_protocol(
        provider=_successful_provider(),
        implementation_sha="e" * 40,
        clock=AdvancingClock(),
    )

    assert report.protocol.admitted is True
    assert report.latency_ms == sum(row.latency_ms for row in report.protocol.cases)
    assert report.latency_ms > 0


def test_low_profile_protocol_requires_confirmation_for_real_origin() -> None:
    with pytest.raises(RuntimeError, match="explicit confirmation"):
        run_glm53_low_profile_protocol(
            provider=_successful_provider(),
            implementation_sha="b" * 40,
            evidence_origin="real_provider",
        )


def test_low_profile_protocol_create_only_writer(tmp_path) -> None:
    report = run_glm53_low_profile_protocol(
        provider=_successful_provider(),
        implementation_sha="c" * 40,
        now=lambda: datetime(2026, 9, 4, tzinfo=timezone.utc),
        clock=lambda: 100.0,
    )
    output = write_report_create_only(
        report,
        repository_root=tmp_path,
        output="data/evaluation/results/provider_capabilities/report.json",
    )
    assert output.is_file()
    with pytest.raises(FileExistsError):
        write_report_create_only(
            report,
            repository_root=tmp_path,
            output="data/evaluation/results/provider_capabilities/report.json",
        )


def test_low_profile_protocol_rejects_forged_policy() -> None:
    from dataclasses import replace

    with pytest.raises(ValueError, match="unsupported GLM-5.3 low candidate request policy"):
        run_glm53_low_profile_protocol(
            provider=_successful_provider(),
            implementation_sha="d" * 40,
            request_policy=replace(
                GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY,
                max_output_tokens=2048,
            ),
        )
