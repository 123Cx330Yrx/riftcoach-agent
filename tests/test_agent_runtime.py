from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, replace
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.harness.steps import (
    CoachDraft,
    EvaluationRequest,
    EvaluationResult,
    EvaluationVerdict,
)
from app.providers.capabilities import ProviderCapabilities
from app.providers.errors import ProviderAuthenticationError
from app.providers.models import ChatRequest, ChatResponse, TokenUsage, ToolCall
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.runtime.models import (
    RuntimePolicySnapshot,
    RuntimePublicationStatus,
    RuntimeRunRequest,
    RuntimeStatus,
)
from app.runtime.runtime import AgentRuntimeV1, RuntimeExecutionFactory
from app.runtime.identity import LegacyRuntimeIdentityResolver
from app.runtime.composition import RuntimeCompositionRoot
from app.runtime.observer import RuntimeObservationError
from app.runtime.recorder import RuntimeRecorder, RuntimeRecorderError
from app.runtime.signals import (
    AgentRunTerminatedSignal,
    ContextBuiltSignal,
    EvaluationCompletedSignal,
    ProviderCallCompletedSignal,
    ProviderCallFailedSignal,
    ProviderCallStartedSignal,
    PublicationDecidedSignal,
    RunCompletedSignal,
    RunFailedSignal,
    RuntimeProviderPhase,
)
from app.runtime.store import RuntimeTraceStore
from app.skills.catalog import SkillCatalog
from app.skills.execution import (
    SkillExecutionRequest,
    SkillInputArtifactBinding,
)
from app.skills.recent_form_review import RecentFormReviewOutput
from app.skills.review_executor import SkillReviewExecutionError
from app.skills.router import DeterministicSkillRouter
from app.skills.routing_models import RouteOutcome, RouterDecision, RouterRequest
from app.skills.single_match_review import SingleMatchReviewOutput
from tests.test_agent_draft_preparer import demo_report, demo_summary


@dataclass
class RuntimeProvider:
    """A deterministic model double; only local RAG is real in these tests."""

    behavior: str = "success"
    provider_name: str = "fake-runtime-provider"
    model_name: str = "fake-runtime-model"
    capabilities: ProviderCapabilities = ProviderCapabilities(
        text_chat=True,
        tool_calling=True,
    )
    requests: list[ChatRequest] = field(default_factory=list)

    def chat(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        iteration = request.metadata.get("agent_loop_iteration")
        harness_step = request.metadata.get("harness_step")

        if self.behavior == "agent_failure" and iteration == 1:
            raise ProviderAuthenticationError(
                provider=self.provider_name,
                code="authentication_failed",
            )
        if self.behavior == "evaluation_failure" and harness_step == "evaluate":
            raise ProviderAuthenticationError(
                provider=self.provider_name,
                code="authentication_failed",
            )

        if iteration == 1:
            return ChatResponse(
                content=None,
                model=self.model_name,
                provider=self.provider_name,
                tool_calls=(
                    ToolCall(
                        id="runtime-knowledge-call",
                        name="knowledge.search",
                        arguments={
                            "query": "Data Dragon 能提供英雄胜率吗",
                            "top_k": 2,
                        },
                    ),
                ),
                usage=TokenUsage(input_tokens=11, output_tokens=5),
            )
        if iteration == 2:
            return ChatResponse(
                content="# Coach draft\n\n基于可归因知识给出谨慎建议。",
                model=self.model_name,
                provider=self.provider_name,
                usage=TokenUsage(input_tokens=17, output_tokens=8),
            )
        return ChatResponse(
            content="evaluation acknowledged",
            model=self.model_name,
            provider=self.provider_name,
            usage=TokenUsage(input_tokens=7, output_tokens=3),
        )


class ProviderBackedEvaluator:
    def __init__(
        self,
        runtime,
        *,
        needs_revision_first: bool = False,
        blocking: bool = False,
    ) -> None:
        self.runtime = runtime
        self.needs_revision_first = needs_revision_first
        self.blocking = blocking
        self.requests: list[EvaluationRequest] = []

    def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        self.requests.append(request)
        result = self.runtime.execute(
            "llm.chat",
            {
                "messages": [
                    {"role": "system", "content": "Return a bounded evaluation."},
                    {"role": "user", "content": "Evaluate the draft."},
                ],
                "temperature": 0.0,
            },
            metadata={"harness_step": "evaluate"},
        )
        if not result.success:
            raise RuntimeError("evaluation provider call failed")
        if self.blocking:
            return EvaluationResult(
                score=99,
                verdict=EvaluationVerdict.NEEDS_REVISION,
                issues=({"category": "prompt_injection", "quote": "private"},),
            )
        if self.needs_revision_first and len(self.requests) == 1:
            return EvaluationResult(
                score=70,
                verdict=EvaluationVerdict.NEEDS_REVISION,
                issues=({"category": "grounding"},),
            )
        return EvaluationResult(score=94, verdict=EvaluationVerdict.PASS)


class ProviderBackedReviser:
    def __init__(self, runtime, *, enabled: bool) -> None:
        self.runtime = runtime
        self.enabled = enabled
        self.requests = []

    def revise(self, request):
        if not self.enabled:
            raise AssertionError("the passing vertical slice must not revise")
        self.requests.append(request)
        result = self.runtime.execute(
            "llm.chat",
            {
                "messages": [
                    {"role": "system", "content": "Revise within the evidence."},
                    {"role": "user", "content": "Revise the draft."},
                ],
                "temperature": 0.0,
            },
            metadata={"harness_step": "revise"},
        )
        if not result.success:
            raise RuntimeError("revision provider call failed")
        return CoachDraft(report=result.data["content"])


@dataclass
class FactoryProbe:
    revision: bool = False
    blocking: bool = False
    evaluators: list[ProviderBackedEvaluator] = field(default_factory=list)
    revisers: list[ProviderBackedReviser] = field(default_factory=list)

    def evaluator_factory(self, runtime):
        evaluator = ProviderBackedEvaluator(
            runtime,
            needs_revision_first=self.revision,
            blocking=self.blocking,
        )
        self.evaluators.append(evaluator)
        return evaluator

    def reviser_factory(self, runtime):
        reviser = ProviderBackedReviser(runtime, enabled=self.revision)
        self.revisers.append(reviser)
        return reviser


class RaisingContextBuilder:
    def build(self, execution, *, max_context_tokens=None):
        raise ValueError("private context details")


def _policy(
    *,
    event_budget: int = 256,
    max_revisions: int = 1,
    allow_deterministic_fallback: bool = True,
) -> RuntimePolicySnapshot:
    return RuntimePolicySnapshot(
        policy_version="1.0.0",
        event_budget=event_budget,
        max_iterations=4,
        max_tool_calls=3,
        timeout_s=30.0,
        max_context_tokens=16_000,
        publish_score_threshold=85,
        max_revisions=max_revisions,
        allow_deterministic_fallback=allow_deterministic_fallback,
    )


def _request(run_id: str, *, single: bool = False) -> RuntimeRunRequest:
    catalog = SkillCatalog.from_directory("skills")
    utterance = "深入复盘这一场的表现" if single else "分析我最近十局的状态"
    payload = {
        "player_summary": demo_summary(),
        "deterministic_report": demo_report(),
        "focus": "laning" if single else "survival",
    }
    if single:
        payload["target_match_id"] = "SYNTHETIC_WIN_001"
    decision = DeterministicSkillRouter().route(
        RouterRequest(
            utterance=utterance,
            available_skills=catalog.route_candidates,
        )
    )
    assert decision.outcome is RouteOutcome.SELECTED
    typed_skill = catalog.get(decision.selected_skill)
    assert typed_skill is not None
    typed_input = typed_skill.input_model.model_validate(payload)
    binding = SkillInputArtifactBinding.from_content(
        run_id=run_id,
        player_summary=typed_input.player_summary,
        deterministic_report=typed_input.deterministic_report,
    )
    execution_request = SkillExecutionRequest(
        run_id=run_id,
        user_utterance=utterance,
        router_decision=decision,
        input_payload=payload,
        input_artifacts=binding,
    )
    return RuntimeRunRequest(
        execution_request=execution_request,
        policy=_policy(),
    )


def _rejected_execution_request(run_id: str) -> SkillExecutionRequest:
    catalog = SkillCatalog.from_directory("skills")
    decision = DeterministicSkillRouter().route(
        RouterRequest(
            utterance="天气怎么样",
            available_skills=catalog.route_candidates,
        )
    )
    assert decision.outcome is RouteOutcome.REJECTED
    binding = SkillInputArtifactBinding.from_content(
        run_id=run_id,
        player_summary=demo_summary(),
        deterministic_report=demo_report(),
    )
    return SkillExecutionRequest(
        run_id=run_id,
        user_utterance="天气怎么样",
        router_decision=decision,
        input_payload={
            "player_summary": demo_summary(),
            "deterministic_report": demo_report(),
        },
        input_artifacts=binding,
    )


def _version_mismatch_request(run_id: str) -> RuntimeRunRequest:
    original = _request(run_id)
    execution = original.execution_request
    decision_payload = execution.router_decision.model_dump(mode="python")
    decision_payload["selected_skill_version"] = "9.9.9"
    decision = RouterDecision.model_validate(decision_payload)
    return RuntimeRunRequest(
        execution_request=SkillExecutionRequest(
            run_id=execution.run_id,
            user_utterance=execution.user_utterance,
            router_decision=decision,
            input_payload=execution.input_payload,
            input_artifacts=execution.input_artifacts,
        ),
        policy=original.policy,
    )


def _runtime(
    tmp_path: Path,
    provider: RuntimeProvider,
    probe=None,
    *,
    context_builder=None,
    catalog: SkillCatalog | None = None,
):
    probe = probe or FactoryProbe()
    factory = RuntimeExecutionFactory(
        knowledge_provider=LocalHybridKnowledgeProvider.from_directory(
            Path("data/rag_docs")
        ),
        evaluator_factory=probe.evaluator_factory,
        reviser_factory=probe.reviser_factory,
    )
    return AgentRuntimeV1(
        runs_root=tmp_path,
        catalog=catalog or SkillCatalog.from_directory("skills"),
        provider=provider,
        execution_factory=factory,
        context_builder=context_builder,
        prompt_program_resolver=LegacyRuntimeIdentityResolver(),
    )


def test_product_composition_uses_verified_prompt_program_identity(
    tmp_path: Path,
):
    probe = FactoryProbe()
    provider = RuntimeProvider()
    factory = RuntimeExecutionFactory(
        knowledge_provider=LocalHybridKnowledgeProvider.from_directory(
            Path("data/rag_docs")
        ),
        evaluator_factory=probe.evaluator_factory,
        reviser_factory=probe.reviser_factory,
    )
    composition = RuntimeCompositionRoot.from_directories(
        skills_root="skills",
        prompt_programs_root="prompt_programs",
    )

    runtime = composition.build_runtime(
        runs_root=tmp_path,
        provider=provider,
        execution_factory=factory,
    )
    result = runtime.run(_request("product_prompt_program_identity"))
    trace = _trace(tmp_path, result)

    assert trace.identity.prompt_profile_id == "recent-form-review-coach"
    assert trace.identity.prompt_profile_version == "1.0.0"
    assert trace.identity.context_contract_version == "1.0.0"


def _catalog_with_fallback(enabled: bool) -> SkillCatalog:
    catalog = SkillCatalog.from_directory("skills")
    skills = tuple(
        replace(
            skill,
            manifest=skill.manifest.model_copy(
                update={
                    "quality_gate": skill.manifest.quality_gate.model_copy(
                        update={"allow_deterministic_fallback": enabled}
                    )
                }
            ),
        )
        for skill in catalog.skills
    )
    return SkillCatalog(root=catalog.root, _skills=skills)


def _trace(tmp_path: Path, result):
    assert result.trace_reference is not None
    return RuntimeTraceStore(tmp_path, result.run_id).read_trace(
        result.trace_reference
    )


def test_runtime_run_publishes_recent_form_and_observes_shared_provider(tmp_path):
    provider = RuntimeProvider()
    probe = FactoryProbe()
    result = _runtime(tmp_path, provider, probe).run(_request("runtime_recent"))

    assert result.runtime_status is RuntimeStatus.COMPLETED
    assert result.publication_status is RuntimePublicationStatus.PUBLISHED
    assert isinstance(result.output, RecentFormReviewOutput)
    assert result.output.status == "published"

    trace = _trace(tmp_path, result)
    signals = [event.signal for event in trace.events]
    assert isinstance(signals[-1], RunCompletedSignal)
    assert not isinstance(signals[-1], RunFailedSignal)
    assert any(isinstance(signal, AgentRunTerminatedSignal) for signal in signals)
    assert any(isinstance(signal, EvaluationCompletedSignal) for signal in signals)
    assert any(isinstance(signal, PublicationDecidedSignal) for signal in signals)
    assert trace.usage.provider_calls_attempted == 3
    assert trace.usage.provider_responses_observed == 3
    assert trace.usage.input_tokens == 35
    assert trace.usage.output_tokens == 16

    assert [signal.kind for signal in signals] == [
        "run_started",
        "execution_validated",
        "context_built",
        "harness_transitioned",
        "provider_call_started",
        "provider_call_completed",
        "tool_call_started",
        "tool_call_completed",
        "provider_call_started",
        "provider_call_completed",
        "agent_run_terminated",
        "harness_transitioned",
        "harness_transitioned",
        "harness_transitioned",
        "provider_call_started",
        "provider_call_completed",
        "evaluation_completed",
        "harness_transitioned",
        "harness_transitioned",
        "publication_decided",
        "run_completed",
    ]

    provider_phases = [
        signal.phase
        for signal in signals
        if isinstance(signal, ProviderCallStartedSignal)
    ]
    assert provider_phases == [
        RuntimeProviderPhase.AGENT,
        RuntimeProviderPhase.AGENT,
        RuntimeProviderPhase.EVALUATION,
    ]
    assert len(probe.evaluators) == 1
    assert "Coach draft" not in (tmp_path / "runtime_recent" / "runtime_trace.json").read_text()
    for reference in trace.artifacts:
        artifact_path = tmp_path / trace.run_id / reference.relative_path
        assert hashlib.sha256(artifact_path.read_bytes()).hexdigest() == reference.sha256
    publication = next(
        signal for signal in signals if isinstance(signal, PublicationDecidedSignal)
    )
    final_report_digests = {
        reference.sha256
        for reference in trace.artifacts
        if reference.kind == "final_report"
    }
    assert set(publication.artifact_sha256s) == final_report_digests


def test_same_runtime_entry_supports_single_match_skill(tmp_path):
    provider = RuntimeProvider()
    result = _runtime(tmp_path, provider).run(
        _request("runtime_single", single=True)
    )

    assert result.runtime_status is RuntimeStatus.COMPLETED
    assert isinstance(result.output, SingleMatchReviewOutput)
    assert result.output.target_match_id == "SYNTHETIC_WIN_001"
    trace = _trace(tmp_path, result)
    assert trace.identity.skill_name == "single-match-review"


def test_revision_path_keeps_provider_ordinals_and_attempts_in_one_trace(tmp_path):
    provider = RuntimeProvider()
    probe = FactoryProbe(revision=True)
    result = _runtime(tmp_path, provider, probe).run(
        _request("runtime_revision")
    )

    assert result.runtime_status is RuntimeStatus.COMPLETED
    assert result.publication_status is RuntimePublicationStatus.PUBLISHED
    trace = _trace(tmp_path, result)
    starts = [
        event.signal
        for event in trace.events
        if isinstance(event.signal, ProviderCallStartedSignal)
    ]
    assert [signal.ordinal for signal in starts] == [1, 2, 3, 4, 5]
    assert [signal.phase for signal in starts] == [
        RuntimeProviderPhase.AGENT,
        RuntimeProviderPhase.AGENT,
        RuntimeProviderPhase.EVALUATION,
        RuntimeProviderPhase.REVISION,
        RuntimeProviderPhase.EVALUATION,
    ]
    evaluations = [
        event.signal
        for event in trace.events
        if isinstance(event.signal, EvaluationCompletedSignal)
    ]
    assert [signal.attempt for signal in evaluations] == [0, 1]
    assert len(probe.revisers[0].requests) == 1


def test_runtime_policy_zero_revision_is_applied_to_harness(tmp_path):
    provider = RuntimeProvider()
    probe = FactoryProbe(revision=True)
    request = _request("runtime_zero_revision")
    request = RuntimeRunRequest(
        execution_request=request.execution_request,
        policy=_policy(max_revisions=0),
    )

    result = _runtime(tmp_path, provider, probe).run(request)

    assert result.runtime_status is RuntimeStatus.COMPLETED
    assert result.publication_status is RuntimePublicationStatus.DEGRADED
    assert probe.revisers[0].requests == []
    trace = _trace(tmp_path, result)
    assert not any(
        isinstance(event.signal, ProviderCallStartedSignal)
        and event.signal.phase is RuntimeProviderPhase.REVISION
        for event in trace.events
    )


def test_agent_provider_failure_is_observed_and_harness_falls_back_safely(tmp_path):
    provider = RuntimeProvider(behavior="agent_failure")
    result = _runtime(tmp_path, provider).run(_request("runtime_agent_failure"))

    assert result.runtime_status is RuntimeStatus.COMPLETED
    assert result.publication_status is RuntimePublicationStatus.DEGRADED
    assert isinstance(result.output, RecentFormReviewOutput)
    assert result.output.status == "degraded"
    trace = _trace(tmp_path, result)
    signals = [event.signal for event in trace.events]
    assert any(isinstance(signal, ProviderCallFailedSignal) for signal in signals)
    assert any(
        isinstance(signal, AgentRunTerminatedSignal)
        and signal.status.value == "failed"
        for signal in signals
    )
    assert not any(isinstance(signal, EvaluationCompletedSignal) for signal in signals)
    assert trace.usage.token_observation.value == "unknown"


def test_evaluation_provider_failure_is_observed_and_harness_falls_back(tmp_path):
    provider = RuntimeProvider(behavior="evaluation_failure")
    result = _runtime(tmp_path, provider).run(_request("runtime_eval_failure"))

    assert result.runtime_status is RuntimeStatus.COMPLETED
    assert result.publication_status is RuntimePublicationStatus.DEGRADED
    trace = _trace(tmp_path, result)
    signals = [event.signal for event in trace.events]
    assert any(
        isinstance(signal, ProviderCallFailedSignal)
        and signal.ordinal == 3
        for signal in signals
    )
    assert not any(isinstance(signal, EvaluationCompletedSignal) for signal in signals)
    assert trace.usage.provider_calls_attempted == 3
    assert trace.usage.provider_responses_observed == 2


def test_prompt_injection_blocking_is_projected_without_private_issue_text(tmp_path):
    provider = RuntimeProvider()
    probe = FactoryProbe(blocking=True)
    result = _runtime(tmp_path, provider, probe).run(
        _request("runtime_prompt_injection")
    )

    assert result.runtime_status is RuntimeStatus.COMPLETED
    assert result.publication_status is RuntimePublicationStatus.DEGRADED
    trace = _trace(tmp_path, result)
    evaluation = next(
        event.signal
        for event in trace.events
        if isinstance(event.signal, EvaluationCompletedSignal)
    )
    assert evaluation.blocking_categories == ("prompt_injection",)
    assert "private" not in repr(trace)


def test_harness_can_reject_without_exposing_a_report(tmp_path):
    provider = RuntimeProvider(behavior="evaluation_failure")
    catalog = _catalog_with_fallback(False)
    request = _request("runtime_rejected_publication")
    request = RuntimeRunRequest(
        execution_request=request.execution_request,
        policy=_policy(allow_deterministic_fallback=False),
    )

    result = _runtime(tmp_path, provider, catalog=catalog).run(request)

    assert result.runtime_status is RuntimeStatus.COMPLETED
    assert result.publication_status is RuntimePublicationStatus.REJECTED
    assert isinstance(result.output, RecentFormReviewOutput)
    assert result.output.status == "rejected"
    assert result.output.report is None
    trace = _trace(tmp_path, result)
    publication = next(
        event.signal
        for event in trace.events
        if isinstance(event.signal, PublicationDecidedSignal)
    )
    assert publication.artifact_sha256s == ()


def test_runtime_request_contract_rejects_non_selected_router_result():
    with pytest.raises(ValidationError, match="selected Router decision"):
        RuntimeRunRequest(
            execution_request=_rejected_execution_request("runtime_rejected"),
            policy=_policy(),
        )


def test_selected_version_drift_creates_boundary_failure_trace_without_io(tmp_path):
    provider = RuntimeProvider()
    result = _runtime(tmp_path, provider).run(
        _version_mismatch_request("runtime_version_drift")
    )

    assert result.runtime_status is RuntimeStatus.FAILED
    assert result.terminal_reason == "execution_validation_failed"
    assert provider.requests == []
    trace = _trace(tmp_path, result)
    assert [event.signal.kind for event in trace.events] == [
        "run_started",
        "run_failed",
    ]


def test_context_failure_is_safe_and_does_not_call_provider(tmp_path):
    provider = RuntimeProvider()
    result = _runtime(
        tmp_path,
        provider,
        context_builder=RaisingContextBuilder(),
    ).run(_request("runtime_context_failure"))

    assert result.runtime_status is RuntimeStatus.FAILED
    assert result.terminal_reason == "context_build_failed"
    assert provider.requests == []
    trace = _trace(tmp_path, result)
    signals = [event.signal for event in trace.events]
    assert isinstance(signals[-1], RunFailedSignal)
    assert not any(isinstance(signal, ProviderCallStartedSignal) for signal in signals)
    assert "private" not in repr(trace)


def test_observation_failure_after_provider_io_returns_safe_failed_result(
    tmp_path,
    monkeypatch,
):
    provider = RuntimeProvider()
    real_emit = RuntimeRecorder.emit

    def fail_completion(self, signal):
        if isinstance(signal, ProviderCallCompletedSignal):
            raise RuntimeObservationError("private recorder failure")
        return real_emit(self, signal)

    monkeypatch.setattr(RuntimeRecorder, "emit", fail_completion)
    result = _runtime(tmp_path, provider).run(
        _request("runtime_observation_failure")
    )

    assert result.runtime_status is RuntimeStatus.FAILED
    assert result.publication_status is None
    assert result.terminal_reason == "observation_failed"
    assert result.output is None
    assert result.trace_reference is None
    assert len(provider.requests) == 1
    assert "private" not in repr(result)


def test_direct_recorder_failure_is_not_misclassified_as_context_failure(
    tmp_path,
    monkeypatch,
):
    provider = RuntimeProvider()
    real_emit = RuntimeRecorder.emit

    def fail_context_event(self, signal):
        if isinstance(signal, ContextBuiltSignal):
            raise RuntimeRecorderError("private recorder failure")
        return real_emit(self, signal)

    monkeypatch.setattr(RuntimeRecorder, "emit", fail_context_event)
    result = _runtime(tmp_path, provider).run(
        _request("runtime_context_observation_failure")
    )

    assert result.runtime_status is RuntimeStatus.FAILED
    assert result.terminal_reason == "observation_failed"
    assert result.publication_status is None
    assert result.trace_reference is None
    assert provider.requests == []


def test_observation_failure_after_terminal_manifest_preserves_publication(
    tmp_path,
    monkeypatch,
):
    provider = RuntimeProvider()
    real_emit = RuntimeRecorder.emit

    def fail_publication(self, signal):
        if isinstance(signal, PublicationDecidedSignal):
            raise RuntimeObservationError("private recorder failure")
        return real_emit(self, signal)

    monkeypatch.setattr(RuntimeRecorder, "emit", fail_publication)
    result = _runtime(tmp_path, provider).run(
        _request("runtime_publication_observation_failure")
    )

    assert result.runtime_status is RuntimeStatus.FAILED
    assert result.publication_status is RuntimePublicationStatus.PUBLISHED
    assert result.terminal_reason == "observation_failed"
    assert result.output is None
    assert result.trace_reference is None


def test_typed_output_failure_preserves_persisted_publication_in_failed_trace(
    tmp_path,
    monkeypatch,
):
    provider = RuntimeProvider()

    def fail_output(self, *, execution, store):
        raise SkillReviewExecutionError("private output failure")

    monkeypatch.setattr(
        "app.skills.review_executor.SkillTerminalOutputBuilder.build",
        fail_output,
    )
    result = _runtime(tmp_path, provider).run(
        _request("runtime_output_failure")
    )

    assert result.runtime_status is RuntimeStatus.FAILED
    assert result.publication_status is RuntimePublicationStatus.PUBLISHED
    assert result.terminal_reason == "typed_output_build_failed"
    assert result.output is None
    trace = _trace(tmp_path, result)
    assert isinstance(trace.events[-1].signal, RunFailedSignal)
    assert trace.events[-1].signal.publication_status is RuntimePublicationStatus.PUBLISHED


def test_harness_execution_failure_is_not_misclassified_as_output_failure(
    tmp_path,
    monkeypatch,
):
    provider = RuntimeProvider()

    def fail_harness(self, **kwargs):
        raise RuntimeError("private Harness failure")

    monkeypatch.setattr("app.skills.review_executor.ReviewHarness.run", fail_harness)
    result = _runtime(tmp_path, provider).run(
        _request("runtime_harness_failure")
    )

    assert result.runtime_status is RuntimeStatus.FAILED
    assert result.publication_status is None
    assert result.terminal_reason == "harness_execution_failed"
    assert result.output is None
    trace = _trace(tmp_path, result)
    assert isinstance(trace.events[-1].signal, RunFailedSignal)
    assert trace.events[-1].signal.failure_stage.value == "harness"
    assert "private" not in repr(trace)


def test_event_budget_rejection_happens_before_provider_or_tool_io(tmp_path):
    provider = RuntimeProvider()
    request = _request("runtime_event_budget")
    assert AgentRuntimeV1._required_event_budget(_policy()) == 61
    constrained = RuntimeRunRequest(
        execution_request=request.execution_request,
        policy=_policy(event_budget=60),
    )

    result = _runtime(tmp_path, provider).run(constrained)

    assert result.runtime_status is RuntimeStatus.FAILED
    assert result.terminal_reason == "runtime_policy_rejected"
    assert provider.requests == []
    trace = _trace(tmp_path, result)
    assert [event.signal.kind for event in trace.events] == [
        "run_started",
        "run_failed",
    ]


def test_trace_write_failure_commits_only_in_memory_run_failed(tmp_path, monkeypatch):
    provider = RuntimeProvider()
    runtime = _runtime(tmp_path, provider)
    committed = []
    real_commit = RuntimeRecorder.commit_terminal

    def fail_write(self, trace):
        raise OSError("private trace persistence failure")

    def capture_commit(self, candidate):
        committed.append(candidate.event.signal)
        return real_commit(self, candidate)

    monkeypatch.setattr("app.runtime.runtime.RuntimeTraceStore.write_trace", fail_write)
    monkeypatch.setattr(RuntimeRecorder, "commit_terminal", capture_commit)
    result = runtime.run(_request("runtime_trace_failure"))

    assert result.runtime_status is RuntimeStatus.FAILED
    assert result.terminal_reason == "trace_persistence_failed"
    assert result.trace_reference is None
    assert len(committed) == 1
    assert isinstance(committed[0], RunFailedSignal)
    assert committed[0].failure_code == "trace_persistence_failed"
    assert not (tmp_path / "runtime_trace_failure" / "runtime_trace.json").exists()
