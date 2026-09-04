from __future__ import annotations

import hashlib
import json
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

from app.evaluation.domain_e2e import load_domain_dataset
from app.evaluation.coach_report import REVISER_SYSTEM_PROMPT
from app.evaluation.provider_domain_experiment import DomainCaseExecutionPlan
from app.evaluation.provider_domain_plan import (
    DomainCaseInput,
    DomainCaseInputPlanArtifact,
    DomainFixtureCommitment,
    LoadedDomainCaseInputPlan,
    load_domain_case_input_plan,
)
from app.evaluation.provider_domain_production import (
    ProductionDomainCaseExecutor,
)
from app.evaluation.glm53_flash_candidate_profile import (
    GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY,
)
from app.providers.capabilities import ProviderCapabilities
from app.providers.config import DEEPSEEK_MODEL
from app.providers.deepseek import DeepSeekProvider
from app.providers.errors import ProviderAuthenticationError
from app.providers.models import ChatRequest, ChatResponse, TokenUsage, ToolCall


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/evaluation/domain_e2e_v1_1_secure_held_out_cases.json"
PLAN = ROOT / "data/evaluation/deepseek_v4_pro_domain_heldout_input_plan.json"


class FakeDeepSeekCompletions:
    def __init__(self, responses) -> None:
        self.responses = list(responses)
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if not self.responses:
            raise AssertionError("unexpected extra fake SDK call")
        return self.responses.pop(0)


class FakeDeepSeekClient:
    def __init__(self, responses) -> None:
        self.completions = FakeDeepSeekCompletions(responses)
        self.chat = SimpleNamespace(completions=self.completions)


def fake_deepseek_tool_call(*, call_id: str, query: str):
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(
            name="knowledge_search",
            arguments=json.dumps(
                {"query": query, "top_k": 2},
                ensure_ascii=False,
                separators=(",", ":"),
            ),
        ),
    )


def fake_deepseek_response(
    *,
    content: str | None,
    finish_reason: str,
    tool_calls=(),
):
    return SimpleNamespace(
        id="development-fake-response",
        model=DEEPSEEK_MODEL,
        choices=[
            SimpleNamespace(
                finish_reason=finish_reason,
                message=SimpleNamespace(
                    content=content,
                    tool_calls=list(tool_calls),
                    reasoning_content=None,
                ),
            )
        ],
        usage=SimpleNamespace(prompt_tokens=20, completion_tokens=10),
    )


def development_multi_tool_input_plan() -> LoadedDomainCaseInputPlan:
    summary = ROOT / "examples/fixtures/player_summary_demo.json"
    report = ROOT / "examples/fixtures/deterministic_report_demo.md"
    case_id = "development_multi_tool_recent_form"
    artifact = DomainCaseInputPlanArtifact(
        plan_id="deepseek-multi-tool-development",
        plan_version="1.0.0",
        dataset_id="domain-e2e-multi-tool-development",
        dataset_version="1.0.0",
        skill_name="recent-form-review",
        skill_version="0.2.0",
        player_summary=DomainFixtureCommitment(
            relative_path="examples/fixtures/player_summary_demo.json",
            sha256=hashlib.sha256(summary.read_bytes()).hexdigest(),
        ),
        deterministic_report=DomainFixtureCommitment(
            relative_path="examples/fixtures/deterministic_report_demo.md",
            sha256=hashlib.sha256(report.read_bytes()).hexdigest(),
        ),
        sdk_max_retries=0,
        max_revisions=0,
        case_count=1,
        cases=(
            DomainCaseInput(
                case_id=case_id,
                run_id="development-multi-tool-recent-form",
                user_utterance=(
                    "分析一下我最近十局的状态，给出前期生存和补刀训练重点。"
                ),
                focus="overall",
                knowledge_mode="standard",
            ),
        ),
    )
    return LoadedDomainCaseInputPlan(
        artifact=artifact,
        execution_plan=DomainCaseExecutionPlan(
            plan_id=artifact.plan_id,
            plan_version=artifact.plan_version,
            plan_sha256="d" * 64,
            case_ids=(case_id,),
        ),
        player_summary_path=summary,
        deterministic_report_path=report,
    )


@dataclass
class SafeProvider:
    provider_name: str = "offline-production-provider"
    model_name: str = "offline-production-model"
    capabilities: ProviderCapabilities = ProviderCapabilities(
        text_chat=True,
        tool_calling=True,
        structured_output=True,
    )
    requests: list[ChatRequest] = field(default_factory=list)

    def chat(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        if request.response_contract is not None:
            content = json.dumps(
                {
                    "score": 95,
                    "verdict": "pass",
                    "issues": [],
                    "passed_checks": ["facts", "citations", "security"],
                    "summary": "controlled pass",
                },
                ensure_ascii=False,
            )
            return self._text(content)
        if any(message.role.value == "tool" for message in request.messages):
            return self._text(
                "# RiftCoach 复盘\n\n建议优先练习前期生存，并以 [K1] 作为知识依据。"
            )
        return ChatResponse(
            content=None,
            provider=self.provider_name,
            model=self.model_name,
            finish_reason="tool_calls",
            tool_calls=(
                ToolCall(
                    id="production-knowledge-1",
                    name="knowledge.search",
                    arguments={"query": "早期死亡", "top_k": 2},
                ),
            ),
            usage=TokenUsage(input_tokens=20, output_tokens=5),
        )

    def _text(self, content: str) -> ChatResponse:
        return ChatResponse(
            content=content,
            provider=self.provider_name,
            model=self.model_name,
            finish_reason="stop",
            usage=TokenUsage(input_tokens=20, output_tokens=10),
        )


@dataclass
class InjectionAwareProvider(SafeProvider):
    marker: str = ""

    def chat(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        combined = "\n".join(message.content or "" for message in request.messages)
        if request.response_contract is not None:
            if self.marker in combined:
                return self._text(
                    json.dumps(
                        {
                            "score": 20,
                            "verdict": "fail",
                            "issues": [
                                {
                                    "severity": "high",
                                    "category": "prompt_injection",
                                    "quote": "controlled marker",
                                    "evidence": "draft followed untrusted data",
                                    "explanation": "security policy blocked",
                                    "suggested_correction": "fallback",
                                }
                            ],
                            "passed_checks": ["schema"],
                            "summary": "blocked",
                        },
                        ensure_ascii=False,
                    )
                )
        if any(message.role.value == "tool" for message in request.messages):
            return self._text(f"# 复盘\n\n[K1] {self.marker}")
        return ChatResponse(
            content=None,
            provider=self.provider_name,
            model=self.model_name,
            finish_reason="tool_calls",
            tool_calls=(
                ToolCall(
                    id="injection-knowledge-1",
                    name="knowledge.search",
                    arguments={"query": "早期死亡", "top_k": 2},
                ),
            ),
            usage=TokenUsage(input_tokens=20, output_tokens=5),
        )


@dataclass
class NeedsRevisionProvider(SafeProvider):
    def chat(self, request: ChatRequest) -> ChatResponse:
        if request.response_contract is None:
            return super().chat(request)
        self.requests.append(request)
        return self._text(
            json.dumps(
                {
                    "score": 70,
                    "verdict": "needs_revision",
                    "issues": [
                        {
                            "severity": "medium",
                            "category": "fact_error",
                            "quote": "controlled",
                            "evidence": "controlled",
                            "explanation": "controlled",
                            "suggested_correction": "controlled",
                        }
                    ],
                    "passed_checks": ["schema"],
                    "summary": "revision requested",
                },
                ensure_ascii=False,
            )
        )


@dataclass
class AuthenticationFailingProvider(SafeProvider):
    def chat(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        raise ProviderAuthenticationError(
            provider="deepseek",
            code="authentication_failed",
        )


def test_production_executor_runs_real_local_skill_rag_and_harness():
    dataset = load_domain_dataset(DATASET)
    plan = load_domain_case_input_plan(
        PLAN,
        project_root=ROOT,
        dataset=dataset,
    )
    provider = SafeProvider()
    with tempfile.TemporaryDirectory() as directory:
        executor = ProductionDomainCaseExecutor(
            project_root=ROOT,
            input_plan=plan,
            runs_root=directory,
        )
        observation = executor.execute(
            case_id="heldout_recent_form_normal",
            provider=provider,
        )

    assert observation.case_id == "heldout_recent_form_normal"
    assert observation.agent_status == "completed"
    assert observation.agent_stop_reason == "final_response"
    assert observation.proposed_tool_names == ("knowledge.search",)
    assert observation.successful_tool_names == ("knowledge.search",)
    assert observation.evidence_source_ids
    assert observation.evidence_diagnostics.search_calls == 1
    assert observation.evidence_diagnostics.successful_search_calls == 1
    assert observation.evidence_diagnostics.payloads_with_data == 1
    assert observation.evidence_diagnostics.chunks_returned >= 1
    assert observation.evidence_diagnostics.source_count == len(
        observation.evidence_source_ids
    )
    assert observation.evidence_diagnostics.artifact_present is True
    assert observation.fact_check_passed is True
    assert observation.citation_check_passed is True
    assert observation.injection_check_passed is True
    assert observation.evaluation_validated is True
    assert observation.evaluation_score == 95
    assert observation.terminal_status == "published"
    assert observation.normalized_response_count == 3
    assert len(provider.requests) == 3


def test_quality_hardening_requires_explicit_candidate_policy() -> None:
    plan = development_multi_tool_input_plan()
    with tempfile.TemporaryDirectory() as directory:
        try:
            ProductionDomainCaseExecutor(
                project_root=ROOT,
                input_plan=plan,
                runs_root=directory,
                quality_hardening=True,
            )
        except ValueError as exc:
            assert "explicit candidate request policy" in str(exc)
        else:
            raise AssertionError("quality hardening must not use a product default")

        executor = ProductionDomainCaseExecutor(
            project_root=ROOT,
            input_plan=plan,
            runs_root=directory,
            request_policy=GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY,
            quality_hardening=True,
        )
        assert executor.quality_hardening is True


REVISION_REPORT = """# RiftCoach 教练式复盘报告

## 1. 总体结论
当前两局合成样本只支持谨慎复盘，知识依据见 [K1]。

## 2. 当前表现亮点
赢局补刀表现较稳定，但样本不足以外推。

## 3. 主要风险点
输局前期死亡较多，需要回看录像验证。

## 4. 赢局与输局差异
这里只描述样本差异，不声称存在因果关系。

## 5. 下一步复盘建议
优先检查前十五分钟的决策节点。

## 6. 训练计划
用小样本记录前期死亡与补刀节奏。

## 7. 数据边界与知识来源
玩家数据来自匿名合成 fixture，知识来源见 [K1]。
"""


@dataclass
class OneRevisionProvider(SafeProvider):
    second_verdict: str = "pass"
    evaluation_attempts: int = 0

    def chat(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        if request.response_contract is not None:
            self.evaluation_attempts += 1
            if self.evaluation_attempts == 1:
                payload = {
                    "score": 70,
                    "verdict": "needs_revision",
                    "issues": [
                        {
                            "severity": "medium",
                            "category": "fact_error",
                            "quote": "controlled",
                            "evidence": "controlled",
                            "explanation": "controlled",
                            "suggested_correction": "controlled",
                        }
                    ],
                    "passed_checks": ["schema"],
                    "summary": "revision requested",
                }
            elif self.second_verdict == "pass":
                payload = {
                    "score": 95,
                    "verdict": "pass",
                    "issues": [],
                    "passed_checks": ["facts", "citations", "security"],
                    "summary": "controlled pass",
                }
            else:
                payload = {
                    "score": 80,
                    "verdict": "fail",
                    "issues": [
                        {
                            "severity": "low",
                            "category": "other",
                            "quote": "controlled",
                            "evidence": "controlled",
                            "explanation": "controlled",
                            "suggested_correction": "controlled",
                        }
                    ],
                    "passed_checks": ["schema", "citations"],
                    "summary": "controlled rejection",
                }
            return self._text(json.dumps(payload, ensure_ascii=False))
        if any(
            message.content == REVISER_SYSTEM_PROMPT
            for message in request.messages
        ):
            return self._text(REVISION_REPORT.replace("较多", "需要核验"))
        if any(message.role.value == "tool" for message in request.messages):
            return self._text(REVISION_REPORT)
        return ChatResponse(
            content=None,
            provider=self.provider_name,
            model=self.model_name,
            finish_reason="tool_calls",
            tool_calls=(
                ToolCall(
                    id="revision-knowledge-1",
                    name="knowledge.search",
                    arguments={"query": "早期死亡", "top_k": 2},
                ),
            ),
            usage=TokenUsage(input_tokens=20, output_tokens=5),
        )


def test_deepseek_multi_tool_development_path_reaches_rag_and_harness():
    evaluation = json.dumps(
        {
            "score": 95,
            "verdict": "pass",
            "issues": [],
            "passed_checks": ["facts", "citations", "security"],
            "summary": "development multi-tool path passed",
        },
        ensure_ascii=False,
    )
    client = FakeDeepSeekClient(
        [
            fake_deepseek_response(
                content=None,
                finish_reason="tool_calls",
                tool_calls=(
                    fake_deepseek_tool_call(
                        call_id="development-call-a",
                        query="前15分钟死亡训练",
                    ),
                    fake_deepseek_tool_call(
                        call_id="development-call-b",
                        query="补刀趋势训练",
                    ),
                ),
            ),
            fake_deepseek_response(
                content=(
                    "# RiftCoach 开发复盘\n\n"
                    "优先减少前15分钟死亡，再稳定补刀节奏；训练依据见 [K1]。"
                ),
                finish_reason="stop",
            ),
            fake_deepseek_response(
                content=evaluation,
                finish_reason="stop",
            ),
        ]
    )
    provider = DeepSeekProvider(client=client, model=DEEPSEEK_MODEL)
    plan = development_multi_tool_input_plan()
    case_id = plan.execution_plan.case_ids[0]

    with tempfile.TemporaryDirectory() as directory:
        observation = ProductionDomainCaseExecutor(
            project_root=ROOT,
            input_plan=plan,
            runs_root=directory,
        ).execute(case_id=case_id, provider=provider)

    assert observation.case_id == "development_multi_tool_recent_form"
    assert observation.agent_status == "completed"
    assert observation.agent_stop_reason == "final_response"
    assert observation.proposed_tool_names == ("knowledge.search",)
    assert observation.successful_tool_names == ("knowledge.search",)
    assert observation.evidence_source_ids
    assert observation.fact_check_passed is True
    assert observation.citation_check_passed is True
    assert observation.injection_check_passed is True
    assert observation.evaluation_validated is True
    assert observation.evaluation_score == 95
    assert observation.terminal_status == "published"
    assert observation.normalized_response_count == 3
    assert len(client.completions.calls) == 3

    agent_follow_up = client.completions.calls[1]["messages"]
    assistant_batch = agent_follow_up[-3]
    assert [row["id"] for row in assistant_batch["tool_calls"]] == [
        "development-call-a",
        "development-call-b",
    ]
    assert [row["tool_call_id"] for row in agent_follow_up[-2:]] == [
        "development-call-a",
        "development-call-b",
    ]
    assert client.completions.calls[2]["response_format"] == {
        "type": "json_object"
    }


def test_production_executor_keeps_case_input_private_from_executor_method():
    dataset = load_domain_dataset(DATASET)
    plan = load_domain_case_input_plan(
        PLAN,
        project_root=ROOT,
        dataset=dataset,
    )
    executor = ProductionDomainCaseExecutor(
        project_root=ROOT,
        input_plan=plan,
        runs_root=ROOT / "tmp" / "production-test-runs",
    )

    assert executor.execution_plan.case_ids == tuple(
        row.case_id for row in dataset.cases
    )
    assert not hasattr(executor, "dataset")


def test_production_executor_observes_user_and_knowledge_injection_markers():
    dataset = load_domain_dataset(DATASET)
    plan = load_domain_case_input_plan(
        PLAN,
        project_root=ROOT,
        dataset=dataset,
    )
    for case_id, marker in (
        ("heldout_user_request_instruction", "USER_INJECTION_ACCEPTED"),
        ("heldout_retrieved_evidence_instruction", "KNOWLEDGE_INJECTION_ACCEPTED"),
    ):
        provider = InjectionAwareProvider(marker=marker)
        with tempfile.TemporaryDirectory() as directory:
            observation = ProductionDomainCaseExecutor(
                project_root=ROOT,
                input_plan=plan,
                runs_root=directory,
            ).execute(case_id=case_id, provider=provider)
        assert observation.injection_check_passed is False
        assert observation.terminal_status == "degraded"
        assert observation.terminal_reason == "security_policy_blocked"
        assert observation.evaluation_validated is True
        assert observation.evaluation_score == 20


def test_production_executor_preserves_safe_agent_failure_provenance():
    dataset = load_domain_dataset(DATASET)
    plan = load_domain_case_input_plan(
        PLAN,
        project_root=ROOT,
        dataset=dataset,
    )
    provider = AuthenticationFailingProvider()
    with tempfile.TemporaryDirectory() as directory:
        observation = ProductionDomainCaseExecutor(
            project_root=ROOT,
            input_plan=plan,
            runs_root=directory,
        ).execute(
            case_id="heldout_recent_form_normal",
            provider=provider,
        )

    assert observation.agent_status == "failed"
    assert observation.agent_stop_reason == "provider_error"
    assert observation.safe_provider_error_code == "authentication_failed"
    assert observation.normalized_response_count == 0
    assert observation.terminal_status == "degraded"
    assert observation.terminal_reason == "draft_preparation_failed"


def test_production_executor_disables_revision_calls_for_heldout():
    dataset = load_domain_dataset(DATASET)
    plan = load_domain_case_input_plan(
        PLAN,
        project_root=ROOT,
        dataset=dataset,
    )
    provider = NeedsRevisionProvider()
    with tempfile.TemporaryDirectory() as directory:
        observation = ProductionDomainCaseExecutor(
            project_root=ROOT,
            input_plan=plan,
            runs_root=directory,
        ).execute(
            case_id="heldout_recent_form_normal",
            provider=provider,
        )

    assert observation.normalized_response_count == 3
    assert len(provider.requests) == 3
    assert observation.terminal_status == "degraded"
    assert observation.terminal_reason == "revision_budget_exhausted"


def test_production_executor_exposes_default_closed_revision_budget():
    plan = development_multi_tool_input_plan()
    with tempfile.TemporaryDirectory() as directory:
        executor = ProductionDomainCaseExecutor(
            project_root=ROOT,
            input_plan=plan,
            runs_root=directory,
        )
        assert executor.max_revisions == 0

        for invalid in (-1, 4, True, 1.5):
            try:
                ProductionDomainCaseExecutor(
                    project_root=ROOT,
                    input_plan=plan,
                    runs_root=directory,
                    max_revisions=invalid,
                )
            except (TypeError, ValueError):
                pass
            else:
                raise AssertionError("invalid revision budget must fail closed")


def test_production_executor_can_publish_after_one_bounded_revision():
    plan = development_multi_tool_input_plan()
    provider = OneRevisionProvider()
    with tempfile.TemporaryDirectory() as directory:
        observation = ProductionDomainCaseExecutor(
            project_root=ROOT,
            input_plan=plan,
            runs_root=directory,
            max_revisions=1,
        ).execute(
            case_id=plan.execution_plan.case_ids[0],
            provider=provider,
        )

    assert len(provider.requests) == 5
    assert observation.normalized_response_count == 5
    assert observation.revision_count == 1
    assert observation.terminal_status == "published"
    assert [row.attempt_id for row in observation.evaluation_diagnostics.attempts] == [
        0,
        1,
    ]
    first, second = observation.evaluation_diagnostics.attempts
    assert first.score == 70
    assert first.verdict == "needs_revision"
    assert first.passed_check_count == 1
    assert first.issue_category_counts[0].name == "fact_error"
    assert first.issue_category_counts[0].count == 1
    assert first.severity_counts[0].name == "medium"
    assert second.score == 95
    assert second.verdict == "pass"
    assert second.passed_check_count == 3
    assert second.issue_category_counts == ()
    assert second.severity_counts == ()
    assert "controlled" not in observation.evaluation_diagnostics.model_dump_json()


def test_production_executor_rejects_when_one_revision_still_fails():
    plan = development_multi_tool_input_plan()
    provider = OneRevisionProvider(second_verdict="fail")
    with tempfile.TemporaryDirectory() as directory:
        observation = ProductionDomainCaseExecutor(
            project_root=ROOT,
            input_plan=plan,
            runs_root=directory,
            max_revisions=1,
        ).execute(
            case_id=plan.execution_plan.case_ids[0],
            provider=provider,
        )

    assert len(provider.requests) == 5
    assert observation.revision_count == 1
    assert observation.terminal_status == "degraded"
    assert observation.terminal_reason == "evaluation_failed"
    assert [row.score for row in observation.evaluation_diagnostics.attempts] == [
        70,
        80,
    ]


def test_prompt_injection_blocks_without_revision_even_when_enabled():
    dataset = load_domain_dataset(DATASET)
    plan = load_domain_case_input_plan(PLAN, project_root=ROOT, dataset=dataset)
    provider = InjectionAwareProvider(marker="USER_INJECTION_ACCEPTED")
    with tempfile.TemporaryDirectory() as directory:
        observation = ProductionDomainCaseExecutor(
            project_root=ROOT,
            input_plan=plan,
            runs_root=directory,
            max_revisions=1,
        ).execute(
            case_id="heldout_user_request_instruction",
            provider=provider,
        )

    assert len(provider.requests) == 3
    assert observation.revision_count == 0
    assert observation.terminal_status == "degraded"
    assert observation.terminal_reason == "security_policy_blocked"
