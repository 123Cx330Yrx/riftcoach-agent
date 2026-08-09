from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.providers.zhipu_probe import ZhipuCapabilityProbe


def sdk_response(
    *,
    content: str | None,
    tool_calls: list[SimpleNamespace] | None = None,
    finish_reason: str = "stop",
    request_id: str = "request-secret-id",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=request_id,
        model="glm-test-resolved",
        choices=[
            SimpleNamespace(
                finish_reason=finish_reason,
                message=SimpleNamespace(
                    content=content,
                    tool_calls=tool_calls or [],
                ),
            )
        ],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
    )


def tool_call(
    *,
    name: str = "knowledge_search",
    arguments: str = '{"query":"前15分钟死亡","top_k":1}',
) -> SimpleNamespace:
    return SimpleNamespace(
        id="call-123",
        type="function",
        function=SimpleNamespace(name=name, arguments=arguments),
    )


PASS_JSON = json.dumps(
    {
        "score": 100,
        "verdict": "pass",
        "issues": [],
        "passed_checks": ["schema"],
        "summary": "格式通过",
    },
    ensure_ascii=False,
)
ISSUE_JSON = json.dumps(
    {
        "score": 70,
        "verdict": "needs_revision",
        "issues": [
            {
                "severity": "high",
                "category": "fact_error",
                "quote": "错误数字",
                "evidence": "确定性数据",
                "explanation": "数字不一致",
                "suggested_correction": "改用确定性数字",
            }
        ],
        "passed_checks": ["结构完整"],
        "summary": "需要修订",
    },
    ensure_ascii=False,
)


class FakeCompletions:
    def __init__(self, responses: list[object]) -> None:
        self.responses = list(responses)
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeClient:
    def __init__(self, responses: list[object]) -> None:
        self.completions = FakeCompletions(responses)
        self.chat = SimpleNamespace(completions=self.completions)


def build_probe(client: FakeClient) -> ZhipuCapabilityProbe:
    timestamps = iter([0.0, 0.01, 1.0, 1.02, 2.0, 2.03, 3.0, 3.04, 4.0, 4.05])
    return ZhipuCapabilityProbe(
        client=client,
        model="glm-test",
        code_sha="a" * 40,
        clock=lambda: next(timestamps),
        now=lambda: datetime(2026, 8, 9, tzinfo=timezone.utc),
    )


def test_runs_p1_to_p5_and_exposes_only_sanitized_evidence() -> None:
    client = FakeClient(
        [
            sdk_response(content="RIFTCOACH_PROVIDER_OK"),
            sdk_response(content=PASS_JSON),
            sdk_response(content=ISSUE_JSON),
            sdk_response(
                content=None,
                tool_calls=[tool_call()],
                finish_reason="tool_calls",
            ),
            sdk_response(content="根据工具结果生成最终回答 RAW_SECRET"),
        ]
    )

    report = build_probe(client).run()

    assert report.admitted is True
    assert report.calls_used == 5
    assert [case.status for case in report.cases] == ["passed"] * 5
    serialized = report.model_dump_json()
    assert "RAW_SECRET" not in serialized
    assert "request-secret-id" not in serialized
    assert all(case.output_sha256 for case in report.cases)

    calls = client.completions.calls
    assert calls[1]["response_format"] == {"type": "json_object"}
    assert calls[2]["response_format"] == {"type": "json_object"}
    assert calls[3]["tools"][0]["function"]["name"] == "knowledge_search"
    assert calls[3]["tool_choice"] == "auto"
    assert calls[4]["messages"][-1]["role"] == "tool"
    assert calls[4]["messages"][-1]["tool_call_id"] == "call-123"


def test_p1_failure_skips_all_remaining_cases_without_more_calls() -> None:
    client = FakeClient([RuntimeError("RAW_SECRET upstream")])

    report = build_probe(client).run()

    assert report.admitted is False
    assert report.calls_used == 1
    assert [case.status for case in report.cases] == [
        "failed",
        "skipped",
        "skipped",
        "skipped",
        "skipped",
    ]
    assert "RAW_SECRET" not in report.model_dump_json()


def test_p1_semantic_mismatch_fails_closed_without_more_calls() -> None:
    client = FakeClient([sdk_response(content="almost ok RAW_SECRET")])

    report = build_probe(client).run()

    assert report.admitted is False
    assert report.calls_used == 1
    assert report.cases[0].error_code == "text_semantic_mismatch"
    assert "RAW_SECRET" not in report.model_dump_json()


def test_bad_tool_call_skips_p5_and_never_uses_the_fifth_call() -> None:
    client = FakeClient(
        [
            sdk_response(content="RIFTCOACH_PROVIDER_OK"),
            sdk_response(content=PASS_JSON),
            sdk_response(content=ISSUE_JSON),
            sdk_response(content="answered without tool"),
        ]
    )

    report = build_probe(client).run()

    assert report.admitted is False
    assert report.calls_used == 4
    assert report.cases[3].error_code == "tool_call_not_observed"
    assert report.cases[4].status == "skipped"
    assert len(client.completions.calls) == 4


def test_probe_requires_the_exact_five_call_budget() -> None:
    with pytest.raises(ValueError, match="exactly 5"):
        ZhipuCapabilityProbe(
            client=FakeClient([]),
            model="glm-test",
            code_sha="a" * 40,
            max_calls=4,
        )
