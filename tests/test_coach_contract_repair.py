"""Deterministic bad responses through the product Runtime; never real calls."""
from dataclasses import replace
import json
import socket

import pytest

from app.evaluation.coach_report import REVISER_SYSTEM_PROMPT
from tests.test_offline_coach_runtime import CoachProvider, compose as legacy_compose, request, ROOT
from app.runtime.coach_contract import GROUNDED_COACH_CONTRACT
from app.runtime.composition import RuntimeCompositionRoot
from app.product.recent_review import RecentReviewRuntimeRequestCompiler
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.harness.store import FileRunStore
from app.runtime.store import RuntimeTraceStore
from app.providers.zhipu_profiles import ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE, ZHIPU_GLM53_FLASH_LOW_CANDIDATE_PROFILE


def compose(tmp_path, stub):
    root = RuntimeCompositionRoot.from_directories(
        skills_root=ROOT / "examples/runtime_profiles/flash_v2/skills",
        prompt_programs_root=ROOT / "examples/runtime_profiles/flash_v2_repair/prompt_programs",
        coach_contract=GROUNDED_COACH_CONTRACT,
    )
    runtime = root.build_offline_coach_runtime(runs_root=tmp_path, provider=stub,
        knowledge_provider=LocalHybridKnowledgeProvider.from_directory(ROOT / "data/rag_docs"))
    return runtime, RecentReviewRuntimeRequestCompiler(root.skill_catalog, coach_contract=GROUNDED_COACH_CONTRACT), stub


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("repair regression must remain offline")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


class GroundedProvider(CoachProvider):
    thinking_profile_id = ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE.profile_id


class RepairProvider(GroundedProvider):
    def __init__(self, *, problem):
        super().__init__(provider_name="zhipu", model_name="glm-5.3-flash")
        self.problem = problem

    def chat(self, value):
        response = super().chat(value)
        if value.response_contract:
            payload = json.loads(response.content)
            if self.evaluation_attempts == 1:
                if self.problem == "pass_with_issues":
                    payload["verdict"] = "pass"
                elif self.problem == "revision_without_issues":
                    payload["issues"] = []
                else:
                    payload.update(score=95, verdict="pass", issues=[])
            return replace(response, content=json.dumps(payload))
        revising = any(m.content == REVISER_SYSTEM_PROMPT for m in value.messages)
        if response.content and self.problem == "missing_citation" and not revising:
            return replace(response, content=response.content.replace("[K1]", ""))
        return response


@pytest.mark.parametrize("problem", ["pass_with_issues", "revision_without_issues", "missing_citation"])
def test_recoverable_response_reaches_a_grounded_product_report(tmp_path, problem):
    stub = RepairProvider(problem=problem)
    runtime, compiler, _ = compose(tmp_path, stub)
    result = runtime.run(request(compiler))
    assert result.publication_status.value == "published", result.terminal_reason
    assert "[K1]" in result.output.report
    assert len(stub.requests) == (5 if problem == "missing_citation" else 4)
    trace = RuntimeTraceStore(tmp_path, result.run_id).read_trace(result.trace_reference)
    assert trace.identity.coach_contract == GROUNDED_COACH_CONTRACT.snapshot()
    assert trace.policy.coach_contract.version == "1.1.0"
    assert trace.identity.prompt_profile_version == "2.1.0"
    assert result.output.evaluation_score == 95
    evaluations = [r for r in stub.requests if r.response_contract]
    assert all(r.response_contract.version == "1.2.0" for r in evaluations)
    assert all(r.max_tokens == 8192 and r.timeout_s <= 60 for r in stub.requests)
    if problem == "missing_citation":
        revision = next(r for r in stub.requests if any(m.content == REVISER_SYSTEM_PROMPT for m in r.messages))
        data = json.loads(revision.messages[-1].content.split("[UNTRUSTED REVISION DATA-ONLY]\n")[1])
        assert data["knowledge"]["citations"][0]["citation_id"] == "K1"
        assert data["knowledge"]["citations"][0]["content"]
        assert data["evaluation"]["score"] == 95  # No score alteration to drive revision.
    else:
        assert "DETERMINISTIC FACT PACK" in evaluations[-1].messages[-1].content
        assert "only correction attempt" in evaluations[-1].messages[-1].content


@pytest.mark.parametrize("problem", ["pass_with_issues", "revision_without_issues", "missing_citation"])
def test_legacy_behavior_and_frozen_identity_are_not_rewritten(tmp_path, problem):
    from app.runtime.coach_contract import COACH_CONTRACT
    stub = RepairProvider(problem=problem)
    stub.thinking_profile_id = ZHIPU_GLM53_FLASH_LOW_CANDIDATE_PROFILE.profile_id
    runtime, compiler, _ = legacy_compose(tmp_path, stub)
    result = runtime.run(request(compiler))
    assert len(stub.requests) == 3
    if problem == "missing_citation":
        assert result.publication_status.value == "published"
        assert "[K1]" not in result.output.report  # Documents the actual old defect.
    else:
        assert result.terminal_reason == "evaluation_failed"
    assert COACH_CONTRACT.snapshot().sha256 == "968c8dc8e2d745ed82bb4cdc1486bde0388d6782603bd833abdba067701e35d1"


@pytest.mark.parametrize("failure,expected_calls,reason", [
    ("contradiction_forever", 4, "evaluation_failed"),
    ("malformed_forever", 4, "evaluation_failed"),
    ("missing_forever", 5, "revision_budget_exhausted"),
    ("unknown_citation", 2, "draft_validation_failed"),
    ("injection", 3, "security_policy_blocked"),
    ("low_score", 3, "evaluation_failed"),
    ("missing_source", 1, "evidence_required"),
])
def test_quality_failures_do_not_get_laundered_or_loop(tmp_path, failure, expected_calls, reason):
    class BadProvider(RepairProvider):
        def chat(self, value):
            response = super().chat(value)
            if failure == "missing_source" and len(self.requests) == 1:
                from tests.test_provider_domain_production import REVISION_REPORT
                return self._text(REVISION_REPORT)
            if value.response_contract:
                if failure == "malformed_forever":
                    return self._text("not json")
                payload = json.loads(response.content)
                if failure == "contradiction_forever":
                    payload.update(verdict="needs_revision", issues=[])
                if failure == "low_score":
                    payload.update(score=84, verdict="pass", issues=[])
                if failure == "injection":
                    payload.update(score=99, verdict="pass", issues=[{
                        "severity": "high", "category": "prompt_injection", "quote": "untrusted",
                        "evidence": "untrusted", "explanation": "instruction followed",
                        "suggested_correction": "must not publish"}])
                return replace(response, content=json.dumps(payload))
            if response.content and failure == "missing_forever":
                return replace(response, content=response.content.replace("[K1]", ""))
            if response.content and failure == "unknown_citation":
                return replace(response, content=response.content.replace("[K1]", "[K999]"))
            return response
    stub = BadProvider(problem="missing_citation" if failure == "missing_forever" else "none")
    runtime, compiler, _ = compose(tmp_path, stub)
    result = runtime.run(request(compiler))
    assert result.publication_status.value == "rejected"
    assert result.terminal_reason == reason
    assert len(stub.requests) == expected_calls
    manifest = FileRunStore(tmp_path, result.run_id).read_manifest()
    assert not any(a["kind"] == "final_report" for a in manifest.artifacts)
    if failure in {"contradiction_forever", "malformed_forever"}:
        assert manifest.failure_code == "invalid_structured_output"


@pytest.mark.parametrize("focus", ["overall", "survival", "economy"])
def test_grounded_product_normal_revision_and_nine_call_budget(tmp_path, focus):
    from scripts.check_glm53_report_contract_budget import _MeteredWorstPathProvider
    from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
    from app.providers.zhipu_profiles import ZHIPU_GLM53_FLASH_LOW_CANDIDATE_PROFILE
    stub = GroundedProvider(provider_name="zhipu", model_name="glm-5.3-flash")
    runtime, compiler, _ = compose(tmp_path / "normal", stub)
    result = runtime.run(request(compiler, focus=focus))
    assert result.publication_status.value == "published"
    assert len(stub.requests) == 5
    class Worst(_MeteredWorstPathProvider):
        thinking_profile_id = ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE.profile_id
        sdk_max_retries = 0
        def chat(self, value):
            result = super().chat(value)
            return replace(result, usage=replace(result.usage, output_tokens=8192))
    worst = Worst()
    runtime, compiler, _ = compose(tmp_path / "worst", worst)
    result = runtime.run(request(compiler, focus=focus))
    assert result.terminal_reason == "evaluation_failed"
    assert len(worst.requests) == 9
    estimates = [estimate_runtime_request_input_ceiling(r) for r in worst.requests]
    assert max(estimates) <= 64000
    assert sum(estimates) + 9 * 8192 <= 649728
    trace = RuntimeTraceStore(tmp_path / "worst", result.run_id).read_trace(result.trace_reference)
    assert trace.usage.input_tokens == sum(estimates)
    assert trace.usage.output_tokens == 9 * 8192


@pytest.mark.parametrize("wrong", ["old_manifest", "old_context", "old_policy", "unbound_new_manifest"])
def test_repair_contract_cannot_mix_with_old_program_or_context(tmp_path, wrong):
    from app.runtime.coach_contract import COACH_CONTRACT
    from app.runtime.coach_context import CoachContextBuilder
    if wrong in {"old_manifest", "unbound_new_manifest"}:
        with pytest.raises(ValueError):
            RuntimeCompositionRoot.from_directories(
                skills_root=ROOT / "examples/runtime_profiles/flash_v2/skills",
                prompt_programs_root=ROOT / ("examples/runtime_profiles/flash_v2/prompt_programs" if wrong == "old_manifest"
                    else "examples/runtime_profiles/flash_v2_repair/prompt_programs"),
                coach_contract=GROUNDED_COACH_CONTRACT if wrong == "old_manifest" else None)
        return
    stub = RepairProvider(problem="none")
    runtime, compiler, _ = compose(tmp_path, stub)
    value = request(compiler)
    if wrong == "old_context":
        runtime._context_builder = CoachContextBuilder()
        assert runtime.run(value).output is None
    else:
        from app.runtime.runtime import RuntimeCompositionError
        value = value.model_copy(update={"policy": value.policy.model_copy(update={"coach_contract": COACH_CONTRACT.snapshot()})})
        with pytest.raises(RuntimeCompositionError):
            runtime.run(value)
    assert not stub.requests


def test_high_profile_reaches_actual_sdk_serializer_with_relaxed_limits(tmp_path):
    from app.providers.zhipu import ZhipuProvider
    from tests.test_provider_domain_production import FakeDeepSeekClient, fake_deepseek_response, fake_deepseek_tool_call, REVISION_REPORT
    payload = {"score": 95, "verdict": "pass", "issues": [], "passed_checks": ["facts", "citations"], "summary": "offline pass"}
    responses = [
        fake_deepseek_response(content=None, finish_reason="tool_calls", tool_calls=(fake_deepseek_tool_call(call_id="grounded-sdk", query="早期死亡"),)),
        fake_deepseek_response(content=REVISION_REPORT, finish_reason="stop"),
        fake_deepseek_response(content=json.dumps(payload), finish_reason="stop"),
    ]
    for response in responses:
        response.model = "glm-5.3-flash"
        response.choices[0].message.reasoning_content = "private-thinking-never-record"
    client = FakeDeepSeekClient(responses)
    client.max_retries = 0
    stub = ZhipuProvider.from_candidate_profile(client=client, model="glm-5.3-flash", profile=ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE)
    runtime, compiler, _ = compose(tmp_path, stub)
    result = runtime.run(request(compiler))
    assert result.publication_status.value == "published"
    calls = client.chat.completions.calls
    assert len(calls) == 3
    assert all(r["max_tokens"] == 8192 and 59 < r["timeout"] <= 60 for r in calls)
    assert all(r["extra_body"]["reasoning_effort"] == "high" for r in calls)
    assert all(r["extra_body"]["thinking"] == {"type": "enabled", "clear_thinking": False} for r in calls)
    trace = RuntimeTraceStore(tmp_path, result.run_id).read_trace(result.trace_reference)
    assert "private-thinking-never-record" not in trace.model_dump_json()


def test_relaxed_budget_is_real_but_still_bounded():
    from app.runtime.coach_budget import CoachBudgetedProvider
    from app.providers.models import ChatRequest, ChatMessage, MessageRole
    from app.providers.errors import ProviderResponseError
    clock = [0.0]
    stub = GroundedProvider(provider_name="zhipu", model_name="glm-5.3-flash")
    budget = CoachBudgetedProvider(stub, clock=lambda: clock[0], coach_contract=GROUNDED_COACH_CONTRACT)
    limits = GROUNDED_COACH_CONTRACT.descriptor()
    assert limits["agent_timeout_s"] == GROUNDED_COACH_CONTRACT.request_policy.agent_timeout_s == 120
    assert limits["execution_timeout_s"] == 480 and limits["max_calls"] == 9
    assert limits["total_tokens"] == 649728
    clock[0] = 470
    def delayed(value):
        assert value.timeout_s == 10
        assert value.max_tokens == 8192
        clock[0] = 481
        return stub._text("late")
    stub.chat = delayed
    with pytest.raises(ProviderResponseError, match="timeout"):
        budget.chat(ChatRequest(messages=(ChatMessage(MessageRole.USER, "offline"),), timeout_s=120))
    assert budget.calls == 1 and budget.stopped


@pytest.mark.parametrize("code", ["external_call_budget_exhausted", "token_budget_exhausted", "token_envelope_exceeded", "timeout"])
def test_resource_failure_is_not_reported_as_quality_failure(tmp_path, code):
    from app.providers.errors import ProviderResponseError
    class ResourceFailure(GroundedProvider):
        def chat(self, value):
            if value.response_contract:
                self.requests.append(value)
                raise ProviderResponseError(provider="zhipu", code=code)
            return super().chat(value)
    stub = ResourceFailure(provider_name="zhipu", model_name="glm-5.3-flash")
    runtime, compiler, _ = compose(tmp_path, stub)
    result = runtime.run(request(compiler))
    manifest = FileRunStore(tmp_path, result.run_id).read_manifest()
    assert manifest.failure_code == code
    assert len(stub.requests) == 3 and result.output.report is None


def test_new_contract_can_be_observed_without_reusing_old_acceptance_assets(tmp_path):
    from app.evaluation.coach_product_acceptance_runner import observe_product_result, _CallCounter
    stub = _CallCounter(RepairProvider(problem="pass_with_issues"))
    runtime, compiler, _ = compose(tmp_path, stub)
    value = request(compiler)
    result = runtime.run(value)
    diagnostics = []
    observation = observe_product_result(tmp_path, result,
        {"case_id": value.run_id, "forbidden_output_markers": []}, request=value,
        context_commitment={"kind": "offline-development-test"}, diagnostics_sink=diagnostics.append)
    assert observation.provider_calls == 4 and observation.citation_check_passed
    assert observation.evaluation_validated
    assert diagnostics[0].evaluation_artifact_count == 1
    assert [d.consistency_error for d in stub.evaluation_responses] == ["pass_with_issues", None]
