from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.providers.zhipu_probe import ZhipuCapabilityProbe
from app.providers.zhipu_profiles import ZHIPU_GLM53_FLASH_MODEL


MISSING = object()


def sdk_response(
    *,
    content: object = MISSING,
    reasoning_content: object = MISSING,
    tool_calls: list[SimpleNamespace] | None = None,
    finish_reason: str = "stop",
    request_id: str = "request-secret-id",
) -> SimpleNamespace:
    message_fields = {"tool_calls": tool_calls or []}
    if content is not MISSING:
        message_fields["content"] = content
    if reasoning_content is not MISSING:
        message_fields["reasoning_content"] = reasoning_content
    return SimpleNamespace(
        id=request_id,
        model="glm-test-resolved",
        choices=[
            SimpleNamespace(
                finish_reason=finish_reason,
                message=SimpleNamespace(**message_fields),
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


def build_probe(
    client: FakeClient,
    *,
    scope: str = "p1_p5",
    max_calls: int = 5,
    model: str = "glm-test",
) -> ZhipuCapabilityProbe:
    timestamps = iter([0.0, 0.01, 1.0, 1.02, 2.0, 2.03, 3.0, 3.04, 4.0, 4.05])
    return ZhipuCapabilityProbe(
        client=client,
        model=model,
        code_sha="a" * 40,
        scope=scope,
        max_calls=max_calls,
        clock=lambda: next(timestamps),
        now=lambda: datetime(2026, 8, 9, tzinfo=timezone.utc),
    )


def test_flash_diagnostic_uses_enabled_low_and_drops_reasoning_body() -> None:
    client = FakeClient(
        [
            sdk_response(
                content="RIFTCOACH_PROVIDER_OK",
                reasoning_content="RAW_FLASH_REASONING",
            )
        ]
    )

    report = build_probe(
        client,
        scope="p1_diagnostic",
        max_calls=1,
        model=ZHIPU_GLM53_FLASH_MODEL,
    ).run()

    assert report.cases[0].status == "passed"
    assert report.cases[0].reasoning_content_state == "non_empty"
    assert client.completions.calls[0]["extra_body"] == {
        "thinking": {"type": "enabled"},
        "reasoning_effort": "low",
    }
    assert "RAW_FLASH_REASONING" not in report.model_dump_json()


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
    assert all(
        call["extra_body"] == {"thinking": {"type": "disabled"}}
        for call in calls
    )
    assert calls[1]["response_format"] == {"type": "json_object"}
    assert calls[2]["response_format"] == {"type": "json_object"}
    assert calls[3]["tools"][0]["function"]["name"] == "knowledge_search"
    assert calls[3]["tool_choice"] == "auto"
    assert calls[4]["messages"][-1]["role"] == "tool"
    assert calls[4]["messages"][-1]["tool_call_id"] == "call-123"


def test_tool_arguments_are_validated_by_contract_not_fixture_wording() -> None:
    client = FakeClient(
        [
            sdk_response(content="RIFTCOACH_PROVIDER_OK"),
            sdk_response(content=PASS_JSON),
            sdk_response(content=ISSUE_JSON),
            sdk_response(
                content=None,
                tool_calls=[
                    tool_call(
                        arguments=(
                            '{"query":"检索前15分钟死亡相关复盘知识",'
                            '"top_k":1}'
                        )
                    )
                ],
                finish_reason="tool_calls",
            ),
            sdk_response(content="根据工具结果生成最终回答"),
        ]
    )

    report = build_probe(client).run()

    assert report.admitted is True
    forwarded_arguments = json.loads(
        client.completions.calls[4]["messages"][2]["tool_calls"][0][
            "function"
        ]["arguments"]
    )
    assert forwarded_arguments == {
        "query": "检索前15分钟死亡相关复盘知识",
        "top_k": 1,
    }


@pytest.mark.parametrize(
    "arguments",
    [
        '{"query":"前15分钟死亡","top_k":1,"extra":true}',
        '{"query":"前15分钟死亡","top_k":"1"}',
        '{"query":"前15分钟死亡","top_k":0}',
        '{"query":"装备选择","top_k":1}',
    ],
)
def test_tool_arguments_fail_closed_on_schema_or_topic_mismatch(
    arguments: str,
) -> None:
    client = FakeClient(
        [
            sdk_response(content="RIFTCOACH_PROVIDER_OK"),
            sdk_response(content=PASS_JSON),
            sdk_response(content=ISSUE_JSON),
            sdk_response(
                content=None,
                tool_calls=[tool_call(arguments=arguments)],
                finish_reason="tool_calls",
            ),
        ]
    )

    report = build_probe(client).run()

    assert report.calls_used == 4
    assert report.cases[3].status == "failed"
    assert report.cases[3].error_code == "invalid_tool_arguments"
    assert report.cases[4].error_code == "p4_tool_request_failed"


def test_non_empty_reasoning_after_disabled_thinking_stops_before_p5() -> None:
    client = FakeClient(
        [
            sdk_response(content="RIFTCOACH_PROVIDER_OK"),
            sdk_response(content=PASS_JSON),
            sdk_response(content=ISSUE_JSON),
            sdk_response(
                content=None,
                reasoning_content="RAW_REASONING_SECRET",
                tool_calls=[tool_call()],
                finish_reason="tool_calls",
            ),
        ]
    )

    report = build_probe(client).run()

    assert report.calls_used == 4
    assert report.cases[3].error_code == "unexpected_reasoning_content"
    assert report.cases[3].reasoning_content_state == "non_empty"
    assert report.cases[4].status == "skipped"
    assert "RAW_REASONING_SECRET" not in report.model_dump_json()


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


def test_invalid_text_preserves_only_safe_response_observation() -> None:
    client = FakeClient(
        [
            sdk_response(
                content=None,
                reasoning_content="RAW_REASONING_SECRET",
                finish_reason="length",
            )
        ]
    )

    report = build_probe(client).run()
    case = report.cases[0]

    assert case.status == "failed"
    assert case.error_code == "invalid_text_response"
    assert case.response_received is True
    assert case.content_state == "null"
    assert case.reasoning_content_state == "non_empty"
    assert case.resolved_model == "glm-test-resolved"
    assert case.finish_reason == "length"
    assert case.input_tokens == 10
    assert case.output_tokens == 5
    assert case.request_id_sha256 is not None
    serialized = report.model_dump_json()
    assert "RAW_REASONING_SECRET" not in serialized
    assert "request-secret-id" not in serialized


@pytest.mark.parametrize(
    ("content", "expected_state"),
    [
        (MISSING, "missing"),
        ("", "empty"),
        (123, "non_string"),
    ],
)
def test_content_shape_is_classified_without_persisting_value(
    content: object,
    expected_state: str,
) -> None:
    client = FakeClient([sdk_response(content=content)])

    report = build_probe(client).run()

    assert report.cases[0].content_state == expected_state
    assert "123" not in report.model_dump_json()


def test_sdk_error_records_that_no_response_was_received() -> None:
    client = FakeClient([RuntimeError("RAW_SECRET upstream")])

    report = build_probe(client).run()
    case = report.cases[0]

    assert case.response_received is False
    assert case.content_state == "not_observed"
    assert case.reasoning_content_state == "not_observed"
    assert case.input_tokens == 0
    assert case.output_tokens == 0


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


def test_p1_diagnostic_scope_stops_after_one_successful_call() -> None:
    client = FakeClient(
        [
            sdk_response(content="RIFTCOACH_PROVIDER_OK"),
            sdk_response(content=PASS_JSON),
        ]
    )

    report = build_probe(
        client,
        scope="p1_diagnostic",
        max_calls=1,
    ).run()

    assert report.schema_version == "1.1"
    assert report.probe_scope == "p1_diagnostic"
    assert report.calls_used == 1
    assert report.admitted is False
    assert [case.case_id for case in report.cases] == ["P1_text_baseline"]
    assert len(client.completions.calls) == 1


@pytest.mark.parametrize(
    ("scope", "max_calls"),
    [("p1_diagnostic", 5), ("p1_p5", 1)],
)
def test_probe_scope_requires_its_exact_budget(
    scope: str,
    max_calls: int,
) -> None:
    with pytest.raises(ValueError, match="requires exactly"):
        ZhipuCapabilityProbe(
            client=FakeClient([]),
            model="glm-test",
            code_sha="a" * 40,
            scope=scope,
            max_calls=max_calls,
        )
