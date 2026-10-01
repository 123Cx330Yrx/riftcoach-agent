from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.evaluation.provider_domain_skill import (
    DomainSkillSliceReport,
    DomainSkillSliceRunner,
    load_prior_adapter_evidence,
)
from app.providers.capabilities import ProviderCapabilities
from app.providers.errors import ProviderRateLimitError
from app.providers.models import ChatRequest, ChatResponse, TokenUsage, ToolCall


PROTOCOL_RESULT = Path(
    "data/evaluation/results/provider_capabilities/zhipu_adapter_slice.json"
)
FIXTURES = Path("examples/fixtures")


def summary_fixture() -> dict:
    return json.loads(
        (FIXTURES / "player_summary_demo.json").read_text(encoding="utf-8")
    )


def report_fixture() -> str:
    return (FIXTURES / "deterministic_report_demo.md").read_text(
        encoding="utf-8"
    )


def coach_report(label: str = "initial") -> str:
    return f"""# RiftCoach 教练式复盘报告
## 1. 总体结论
{label}：两局合成样本只适合提出复盘假设。
## 2. 当前表现亮点
赢局的前15分钟死亡为 0。
## 3. 主要风险点
输局的前15分钟死亡为 1。
## 4. 赢局与输局差异
仅描述样本内共同变化。
## 5. 下一步复盘建议
检查早期死亡窗口。
## 6. 训练计划
记录后续对局的死亡时间。
## 7. 数据边界与知识来源
样本量为 2，不能证明因果。
"""


def evaluation_json(
    *,
    score: int = 94,
    verdict: str = "pass",
    issues: list[dict] | None = None,
) -> str:
    return json.dumps(
        {
            "score": score,
            "verdict": verdict,
            "issues": issues or [],
            "passed_checks": ["facts checked"],
            "summary": "The report respects the supplied facts.",
        },
        ensure_ascii=False,
    )


def revision_issue() -> dict:
    return {
        "severity": "medium",
        "category": "causality",
        "quote": "错误因果句",
        "evidence": "输入只支持相关变化",
        "explanation": "不能从两局样本证明因果",
        "suggested_correction": "改为待验证假设",
    }


def tool_response() -> ChatResponse:
    return ChatResponse(
        content=None,
        model="glm-5.2",
        provider="zhipu",
        finish_reason="tool_calls",
        tool_calls=(
            ToolCall(
                id="RAW_DOMAIN_TOOL_ID",
                name="knowledge.search",
                arguments={
                    "query": "15分钟前死亡指标应如何谨慎解释",
                    "top_k": 2,
                },
            ),
        ),
        usage=TokenUsage(input_tokens=100, output_tokens=20),
        request_id="RAW_DOMAIN_REQUEST_1",
    )


def text_response(content: str, request_id: str) -> ChatResponse:
    return ChatResponse(
        content=content,
        model="glm-5.2",
        provider="zhipu",
        finish_reason="stop",
        usage=TokenUsage(input_tokens=120, output_tokens=60),
        request_id=request_id,
    )


@dataclass
class ScriptedProvider:
    responses: list[ChatResponse | Exception]
    provider_name: str = "zhipu"
    model_name: str = "glm-5.2"
    capabilities: ProviderCapabilities = ProviderCapabilities(
        text_chat=True,
        tool_calling=True,
        structured_output=True,
    )
    requests: list[ChatRequest] = field(default_factory=list)

    def chat(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        if not self.responses:
            raise AssertionError("RAW_PROVIDER_SHOULD_NOT_BE_CALLED")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def prior_evidence():
    return load_prior_adapter_evidence(
        PROTOCOL_RESULT,
        expected_provider_id="zhipu",
        expected_model="glm-5.2",
    )


def build_runner(
    provider: ScriptedProvider,
    *,
    runs_root: Path,
) -> DomainSkillSliceRunner:
    return DomainSkillSliceRunner(
        provider=provider,
        code_sha="b" * 40,
        prior_evidence=prior_evidence(),
        player_summary=summary_fixture(),
        deterministic_report=report_fixture(),
        runs_root=runs_root,
        knowledge_dir=Path("data/rag_docs"),
        now=lambda: datetime(2026, 8, 13, tzinfo=timezone.utc),
    )


def test_prior_adapter_evidence_is_strictly_loaded_and_hashed() -> None:
    evidence = prior_evidence()

    assert evidence.provider_id == "zhipu"
    assert evidence.requested_model == "glm-5.2"
    assert evidence.calls_used == 3
    assert len(evidence.result_sha256) == 64


def test_prior_adapter_evidence_rejects_provider_or_model_mismatch() -> None:
    with pytest.raises(ValueError, match="identity"):
        load_prior_adapter_evidence(
            PROTOCOL_RESULT,
            expected_provider_id="another-provider",
            expected_model="glm-5.2",
        )


def test_domain_report_rejects_broken_cumulative_call_accounting(
    tmp_path: Path,
) -> None:
    provider = ScriptedProvider(
        [
            tool_response(),
            text_response(coach_report(), "RAW_DOMAIN_REQUEST_2"),
            text_response(evaluation_json(), "RAW_DOMAIN_REQUEST_3"),
        ]
    )
    report = build_runner(provider, runs_root=tmp_path / "runs").run()
    payload = report.model_dump(mode="json")
    payload["cumulative_calls_used"] = 7

    with pytest.raises(ValidationError, match="cumulative"):
        DomainSkillSliceReport.model_validate(payload)


def test_admitted_report_requires_metadata_for_every_billed_call(
    tmp_path: Path,
) -> None:
    provider = ScriptedProvider(
        [
            tool_response(),
            text_response(coach_report(), "RAW_DOMAIN_REQUEST_2"),
            text_response(evaluation_json(), "RAW_DOMAIN_REQUEST_3"),
        ]
    )
    report = build_runner(provider, runs_root=tmp_path / "runs").run()
    payload = report.model_dump(mode="json")
    payload["response_count"] = 2
    payload["resolved_models"] = payload["resolved_models"][:2]
    payload["finish_reasons"] = payload["finish_reasons"][:2]
    payload["request_id_sha256"] = payload["request_id_sha256"][:2]

    with pytest.raises(ValidationError, match="admitted"):
        DomainSkillSliceReport.model_validate(payload)


def test_real_recent_form_control_flow_passes_in_three_domain_calls(
    tmp_path: Path,
) -> None:
    provider = ScriptedProvider(
        [
            tool_response(),
            text_response(coach_report(), "RAW_DOMAIN_REQUEST_2"),
            text_response(evaluation_json(), "RAW_DOMAIN_REQUEST_3"),
        ]
    )

    report = build_runner(provider, runs_root=tmp_path / "runs").run()

    assert report.admitted is True
    assert report.error_code is None
    assert report.prior_calls_used == 3
    assert report.remaining_calls == 4
    assert report.domain_calls_used == 3
    assert report.response_count == 3
    assert report.cumulative_calls_used == 6
    assert report.agent_calls == 2
    assert report.evaluation_calls == 1
    assert report.evaluation_repair_calls == 0
    assert report.revision_calls == 0
    assert report.tool_call_count == 1
    assert report.tool_execution_count == 1
    assert report.knowledge_source_count >= 1
    assert report.evaluation_validated is True
    assert report.evaluation_score == 94
    assert report.terminal_status == "published"
    assert report.typed_output_sha256 is not None
    assert len(provider.requests) == 3
    assert provider.requests[0].tools[0].name == "knowledge.search"
    assert provider.requests[1].messages[-1].role.value == "tool"
    assert provider.requests[2].response_contract is not None

    serialized = report.model_dump_json()
    assert "RAW_" not in serialized
    assert "15分钟前死亡指标应如何谨慎解释" not in serialized
    assert "RiftCoach 教练式复盘报告" not in serialized
    assert "The report respects the supplied facts" not in serialized


def test_direct_answer_is_terminal_but_not_domain_admitted(tmp_path: Path) -> None:
    provider = ScriptedProvider(
        [
            text_response(coach_report(), "RAW_DIRECT_REQUEST"),
            text_response(evaluation_json(), "RAW_DIRECT_EVALUATION"),
        ]
    )

    report = build_runner(provider, runs_root=tmp_path / "runs").run()

    assert report.admitted is False
    assert report.error_code == "knowledge_round_trip_incomplete"
    assert report.domain_calls_used == 2
    assert report.terminal_status == "published"
    assert report.tool_execution_count == 0
    assert len(provider.requests) == 2


def test_one_structured_repair_uses_the_fourth_and_final_domain_call(
    tmp_path: Path,
) -> None:
    provider = ScriptedProvider(
        [
            tool_response(),
            text_response(coach_report(), "RAW_REPAIR_DRAFT"),
            text_response("not-json RAW_MODEL_SECRET", "RAW_INVALID_EVAL"),
            text_response(evaluation_json(), "RAW_REPAIRED_EVAL"),
        ]
    )

    report = build_runner(provider, runs_root=tmp_path / "runs").run()

    assert report.admitted is True
    assert report.domain_calls_used == 4
    assert report.cumulative_calls_used == 7
    assert report.evaluation_calls == 1
    assert report.evaluation_repair_calls == 1
    assert report.terminal_status == "published"
    assert len(provider.requests) == 4
    assert "RAW_MODEL_SECRET" not in report.model_dump_json()


def test_evaluation_provider_failure_is_not_retried_by_llm_tool(
    tmp_path: Path,
) -> None:
    provider = ScriptedProvider(
        [
            tool_response(),
            text_response(coach_report(), "RAW_FAILURE_DRAFT"),
            ProviderRateLimitError(provider="zhipu", code="rate_limited"),
            text_response(evaluation_json(), "RAW_MUST_NOT_RETRY"),
        ]
    )

    report = build_runner(provider, runs_root=tmp_path / "runs").run()

    assert report.admitted is False
    assert report.error_code == "structured_evaluation_failed"
    assert report.domain_calls_used == 3
    assert report.evaluation_calls == 1
    assert report.evaluation_repair_calls == 0
    assert len(provider.requests) == 3
    assert len(provider.responses) == 1


def test_revision_branch_fails_closed_before_a_fifth_domain_call(
    tmp_path: Path,
) -> None:
    provider = ScriptedProvider(
        [
            tool_response(),
            text_response(coach_report(), "RAW_REVISION_DRAFT"),
            text_response(
                evaluation_json(
                    score=70,
                    verdict="needs_revision",
                    issues=[revision_issue()],
                ),
                "RAW_REVISION_EVAL",
            ),
            text_response(coach_report("revised"), "RAW_REVISION_RESPONSE"),
        ]
    )

    report = build_runner(provider, runs_root=tmp_path / "runs").run()

    assert report.admitted is False
    assert report.error_code == "structured_evaluation_failed"
    assert report.domain_calls_used == 4
    assert report.cumulative_calls_used == 7
    assert report.agent_calls == 2
    assert report.evaluation_calls == 1
    assert report.revision_calls == 1
    assert report.budget_block_count == 1
    assert len(provider.requests) == 4
    assert "RAW_PROVIDER_SHOULD_NOT_BE_CALLED" not in report.model_dump_json()
