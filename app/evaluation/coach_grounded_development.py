"""Bounded development observations through the grounded product Runtime.

Known demo inputs are deliberately not held-out. No separate Agent loop,
protocol score, automatic retry, or production registration lives here.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
import tempfile
import time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.evaluation.coach_product_acceptance import digest
from app.evaluation.coach_product_acceptance_runner import (
    ProductCaseDiagnostics, REQUIRED_CI_JOBS, _CallCounter, _write_new, observe_product_result,
)
from app.evaluation.coach_report import REVISER_SYSTEM_PROMPT
from app.evaluation.domain_e2e import (
    ContractSnapshot, DomainCandidate, DomainCandidateCase, DomainCaseRequirements,
    DomainEvaluationCase, DomainEvaluationDataset, FailureCode, LayerVerdict, evaluate_domain_candidate,
)
from app.harness.runtime import _SAFE_FAILURE_CODES
from app.product.recent_review import RecentReviewProductRequest, RecentReviewRuntimeRequestCompiler
from app.providers.errors import ProviderError
from app.rag.coaching_query import RetrievalAttemptDiagnostics, Topic, _attempt, _topic
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.runtime.coach_context import CoachContextBuilder
from app.runtime.coach_contract import GROUNDED_COACH_CONTRACT as CONTRACT
from app.runtime.composition import RuntimeCompositionRoot
from app.skills.execution import SkillExecutionBoundary


Scenario = Literal["overall", "survival", "economy"]
RUN_PATTERN = r"^coach-grounded-dev-[a-z0-9][a-z0-9-]{0,60}$"
_EXTRA_SAFE_ERRORS = {"provider_error", "execution_error", "interrupted"}


@dataclass(frozen=True)
class DevelopmentPlan:
    run_id: str
    scenario: Scenario
    manifest: dict
    dataset: DomainEvaluationDataset
    composition: RuntimeCompositionRoot
    request: object
    builder: CoachContextBuilder

    @property
    def sha256(self):
        return digest(self.manifest)


def prepare_observation(project_root: Path, *, scenario: Scenario = "economy",
                        run_id: str = "coach-grounded-dev-preview") -> DevelopmentPlan:
    """Read only local public fixtures; never read credentials or construct clients."""
    if scenario not in ("overall", "survival", "economy") or not re.fullmatch(RUN_PATTERN, run_id):
        raise ValueError("development_identity_invalid")
    root = RuntimeCompositionRoot.from_directories(
        skills_root=project_root / "examples/runtime_profiles/flash_v2/skills",
        prompt_programs_root=project_root / "examples/runtime_profiles/flash_v2_repair/prompt_programs",
        coach_contract=CONTRACT,
    )
    fixture = project_root / "examples/fixtures/player_summary_demo.json"
    report = project_root / "examples/fixtures/deterministic_report_demo.md"
    summary = json.loads(fixture.read_text(encoding="utf-8"))
    if summary["metadata"]["source"] != "synthetic_fixture" or len(summary["matches"]) != 2:
        raise ValueError("development_demo_identity_drift")
    # Product count has a minimum of five. Preserve the actual two available
    # matches, all aggregates, and the explicit incomplete-sample disclosure.
    summary["metadata"]["matches_requested"] = summary["request"]["count"] = 5
    request = RecentReviewRuntimeRequestCompiler(root.skill_catalog, coach_contract=CONTRACT).compile(
        RecentReviewProductRequest(riot_id=summary["player"]["riot_id"], routing_region="asia", count=5, focus=scenario),
        player_summary=summary,
        deterministic_report="开发观察：请求5局，仅有2局公开合成demo样本；未调用Riot API，不补造其余比赛。\n\n" + report.read_text(encoding="utf-8"),
        run_id=run_id,
    )
    builder = CoachContextBuilder(coach_contract=CONTRACT)
    execution = SkillExecutionBoundary(root.skill_catalog).validate(request.execution_request)
    context = builder.build(execution, max_context_tokens=request.policy.max_context_tokens)
    corpus = {p.relative_to(project_root).as_posix(): hashlib.sha256(p.read_text(encoding="utf-8").encode()).hexdigest()
              for p in sorted((project_root / "data/rag_docs").rglob("*")) if p.is_file()}
    if not corpus:
        raise ValueError("development_corpus_empty")
    manifest = {
        "schema_version": "1.0", "scope": "development_not_admission", "run_id": run_id, "scenario": scenario,
        "fixture_sha256": digest(summary), "report_sha256": hashlib.sha256(report.read_text(encoding="utf-8").encode()).hexdigest(),
        "request_sha256": digest(request.model_dump(mode="json")), "context_sha256": digest(asdict(context)),
        "corpus": corpus, "coach_contract": CONTRACT.snapshot().model_dump(mode="json"),
        "program_sha256": root.prompt_program_resolver.resolve("recent-form-review", "0.3.0").manifest.program_sha256,
        "budget": CONTRACT.descriptor(),
    }
    requirements = DomainCaseRequirements(
        minimum_normalized_responses=3, expected_agent_status="completed", expected_agent_stop_reason="final_response",
        required_tool_names=("knowledge.search",), minimum_successful_tool_executions=1, minimum_evidence_sources=1,
        require_fact_check=True, require_citation_check=True, require_injection_check=True,
        require_validated_evaluation=True, minimum_evaluation_score=85, allowed_terminal_statuses=("published",),
        maximum_provider_calls=9, maximum_total_tokens=CONTRACT.descriptor()["total_tokens"],
    )
    dataset = DomainEvaluationDataset(
        schema_version="1.2", dataset_id="coach-grounded-known-demo-development", dataset_version="1.0.0",
        role="development", calibration_excluded=False, created_at="2026-09-06", case_count=1,
        contract_snapshot=ContractSnapshot(
            skill_name="recent-form-review", skill_version="0.3.0", context_contract="context-builder-v1@1.0.0",
            evaluation_contract="coach_evaluation@1.2.0", prompt_context_snapshot_id="grounded-development-context-v1",
            prompt_context_snapshot_sha256=digest(manifest)),
        contamination_notes=("Known public two-match demo used in prior development; not independent quality evidence.",),
        lifecycle_policy="Development debugging only. Create-only execution identity; no admission claim.",
        cases=(DomainEvaluationCase(case_id=run_id, category=scenario, expect_task_success=True,
            expected_primary_failure=None, requirements=requirements, contamination_sources=("public_demo",)),),
    )
    manifest["assessment_sha256"] = digest(dataset.model_dump(mode="json"))
    return DevelopmentPlan(run_id, scenario, manifest, dataset, root, request, builder)


class DevelopmentEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    implementation_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    plan_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    public_ci_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


def verify_development_ci(plan, *, implementation_sha, ci):
    jobs = ci.get("jobs", [])
    if (ci.get("headSha") != implementation_sha or ci.get("status") != "completed" or ci.get("conclusion") != "success"
            or not re.fullmatch(r"https://github\.com/123Cx330Yrx/riftcoach-agent/actions/runs/[0-9]+", ci.get("url", ""))
            or len(jobs) != len(REQUIRED_CI_JOBS) or {j.get("name") for j in jobs} != REQUIRED_CI_JOBS
            or any(j.get("status") != "completed" or j.get("conclusion") != "success" for j in jobs)):
        raise ValueError("development_public_ci_mismatch")
    return DevelopmentEvidence(implementation_sha=implementation_sha, plan_sha256=plan.sha256, public_ci_sha256=digest(ci))


class CallDiagnostic(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    ordinal: int = Field(ge=1, le=9)
    phase: Literal["agent", "evaluation", "revision"]
    response_received: bool
    finish_reason: Literal["stop", "length", "tool_calls", "content_filter", "other"] | None = None
    content_characters: int = Field(default=0, ge=0)
    tool_call_count: int = Field(default=0, ge=0)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    elapsed_ms: int = Field(ge=0)
    error_code: str | None = None

    @model_validator(mode="after")
    def safe_fields(self):
        if self.error_code is not None and self.error_code not in _SAFE_FAILURE_CODES | _EXTRA_SAFE_ERRORS:
            raise ValueError("development_unknown_error_code")
        if self.response_received:
            if self.error_code is not None:
                raise ValueError("development_response_error_mismatch")
        elif (self.error_code is None or self.finish_reason is not None
              or any((self.content_characters, self.tool_call_count, self.input_tokens, self.output_tokens))):
            raise ValueError("development_missing_response_mismatch")
        return self


class DevelopmentCounter(_CallCounter):
    """Observe the unmodified call; the product still owns all resource limits."""
    def __init__(self, provider, *, on_call=None):
        super().__init__(provider)
        self.call_diagnostics = []
        self.on_call = on_call

    def chat(self, request):
        start = time.monotonic()
        phase = ("evaluation" if request.response_contract else "revision"
                 if any(m.content == REVISER_SYSTEM_PROMPT for m in request.messages) else "agent")
        response, error = None, None
        try:
            response = super().chat(request)
            return response
        except BaseException as exc:
            error = ("interrupted" if isinstance(exc, (KeyboardInterrupt, SystemExit)) else
                     exc.code if isinstance(exc, ProviderError) and exc.code in _SAFE_FAILURE_CODES else
                     "provider_error" if isinstance(exc, ProviderError) else "execution_error")
            raise
        finally:
            reason = response.finish_reason if response else None
            if reason not in (None, "stop", "length", "tool_calls", "content_filter"):
                reason = "other"
            row = CallDiagnostic(
                ordinal=self.calls, phase=phase, response_received=response is not None,
                finish_reason=reason, content_characters=len(response.content or "") if response else 0,
                tool_call_count=len(response.tool_calls) if response else 0,
                input_tokens=response.usage.input_tokens if response else 0,
                output_tokens=response.usage.output_tokens if response else 0,
                elapsed_ms=max(0, round((time.monotonic() - start) * 1000)), error_code=error,
            )
            self.call_diagnostics.append(row)
            if self.on_call:
                self.on_call(row)


class RetrievalDiagnostic(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    ordinal: int = Field(ge=1)
    topic: Topic
    result: RetrievalAttemptDiagnostics


class DevelopmentKnowledge:
    """Observe local searches unchanged, including the existing single recovery."""
    def __init__(self, provider, on_attempt=None):
        self.provider = provider
        self.provider_name = provider.provider_name
        self.attempts = []
        self.on_attempt = on_attempt

    def search(self, query):
        result = self.provider.search(query)
        row = RetrievalDiagnostic(ordinal=len(self.attempts) + 1, topic=_topic(query.text)[0], result=_attempt(result))
        self.attempts.append(row)
        if self.on_attempt:
            self.on_attempt(row)
        return result


class DevelopmentReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["1.0"] = "1.0"
    scope: Literal["development_not_admission"] = "development_not_admission"
    run_id: str = Field(pattern=RUN_PATTERN)
    scenario: Scenario
    plan_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_origin: Literal["offline_fake", "real_provider"]
    real_evidence: DevelopmentEvidence | None = None
    network_used: bool
    passed: bool
    failure_codes: tuple[FailureCode | Literal["incomplete_evidence"], ...]
    observation: DomainCandidateCase
    diagnostics: ProductCaseDiagnostics
    calls: tuple[CallDiagnostic, ...]
    retrieval_attempts: tuple[RetrievalDiagnostic, ...]
    provider_calls: int = Field(ge=0, le=9)
    observed_input_tokens: int = Field(ge=0)
    observed_output_tokens: int = Field(ge=0)
    candidate_registered: Literal[False] = False
    production_admitted: Literal[False] = False

    @model_validator(mode="after")
    def cross_check(self):
        real = self.evidence_origin == "real_provider"
        if real != (self.real_evidence is not None) or self.network_used != (real and self.provider_calls > 0):
            raise ValueError("development_origin_mismatch")
        if self.real_evidence and self.real_evidence.plan_sha256 != self.plan_sha256:
            raise ValueError("development_real_plan_mismatch")
        if (self.observation.case_id != self.run_id or self.observation.provider_calls != self.provider_calls
                or tuple(c.ordinal for c in self.calls) != tuple(range(1, self.provider_calls + 1))
                or self.observed_input_tokens != sum(c.input_tokens for c in self.calls)
                or self.observed_output_tokens != sum(c.output_tokens for c in self.calls)
                or self.passed != (not self.failure_codes)):
            raise ValueError("development_receipt_counts_mismatch")
        ordinals = tuple(d.call_ordinal for d in self.diagnostics.evaluation_responses)
        expected = tuple(c.ordinal for c in self.calls if c.phase == "evaluation" and c.response_received)
        if ordinals != expected or len(ordinals) > 4:
            raise ValueError("development_evaluation_diagnostics_mismatch")
        if tuple(r.ordinal for r in self.retrieval_attempts) != tuple(range(1, len(self.retrieval_attempts) + 1)):
            raise ValueError("development_retrieval_ordinals_mismatch")
        return self


def _assess(plan, observation, *, real):
    dataset = plan.dataset
    candidate = DomainCandidate(
        schema_version="1.2", candidate_id="coach-grounded-product-development",
        candidate_kind="real_provider_recorded" if real else "offline_executable", dataset_id=dataset.dataset_id,
        dataset_version=dataset.dataset_version, contract_snapshot=dataset.contract_snapshot,
        external_provider_calls=observation.provider_calls if real else 0, case_count=1, cases=(observation,),
    )
    result = evaluate_domain_candidate(dataset, candidate).cases[0]
    passed = result.task_succeeded and result.layers.resources.verdict is LayerVerdict.PASS
    return passed, tuple(c.value for c in result.failure_codes) or (() if passed else ("incomplete_evidence",))


def validate_receipt(receipt, plan):
    receipt = DevelopmentReceipt.model_validate_json(receipt.model_dump_json())
    if (receipt.plan_sha256 != plan.sha256 or receipt.run_id != plan.run_id or receipt.scenario != plan.scenario
            or digest(plan.dataset.model_dump(mode="json")) != plan.manifest["assessment_sha256"]):
        raise ValueError("development_receipt_plan_mismatch")
    passed, failures = _assess(plan, receipt.observation, real=receipt.real_evidence is not None)
    if receipt.passed != passed or tuple(receipt.failure_codes) != failures:
        raise ValueError("development_receipt_outcome_mismatch")
    return receipt


def _fresh_plan(project_root, plan):
    fresh = prepare_observation(project_root, scenario=plan.scenario, run_id=plan.run_id)
    if fresh.sha256 != plan.sha256:
        raise ValueError("development_plan_drift")
    return fresh


def run_observation(project_root: Path, *, provider, plan: DevelopmentPlan, real_evidence=None, on_phase=None, on_retrieval=None):
    plan = _fresh_plan(project_root, plan)
    if real_evidence is not None:
        real_evidence = DevelopmentEvidence.model_validate_json(real_evidence.model_dump_json())
        if real_evidence.plan_sha256 != plan.sha256:
            raise ValueError("development_real_plan_mismatch")
    CONTRACT.require_provider(provider)
    counter = provider if isinstance(provider, DevelopmentCounter) else DevelopmentCounter(provider)
    original_build = plan.builder.build
    def checked_build(*args, **kwargs):
        context = original_build(*args, **kwargs)
        if digest(asdict(context)) != plan.manifest["context_sha256"]:
            raise ValueError("development_context_drift")
        return context
    plan.builder.build = checked_build
    knowledge = DevelopmentKnowledge(LocalHybridKnowledgeProvider.from_directory(project_root / "data/rag_docs"), on_retrieval)
    with tempfile.TemporaryDirectory(prefix="riftcoach-grounded-dev-") as temporary:
        runtime = plan.composition.build_offline_coach_runtime(
            runs_root=temporary, provider=counter, context_builder=plan.builder,
            knowledge_provider=knowledge)
        if on_phase: on_phase("runtime_execution")
        result = runtime.run(plan.request)
        if on_phase: on_phase("observation_projection")
        diagnostics = []
        observation = observe_product_result(temporary, result, {"case_id": plan.run_id, "forbidden_output_markers": []},
            request=plan.request, context_commitment=plan.manifest, diagnostics_sink=diagnostics.append)
        if observation.provider_calls != counter.calls:
            raise ValueError("development_runtime_call_count_mismatch")
        diagnostic = diagnostics[0].model_copy(update={"evaluation_responses": tuple(counter.evaluation_responses)})
        passed, failures = _assess(plan, observation, real=real_evidence is not None)
        receipt = DevelopmentReceipt(
            run_id=plan.run_id, scenario=plan.scenario, plan_sha256=plan.sha256,
            evidence_origin="real_provider" if real_evidence else "offline_fake", real_evidence=real_evidence,
            network_used=real_evidence is not None and counter.calls > 0, passed=passed, failure_codes=failures,
            observation=observation, diagnostics=diagnostic, calls=tuple(counter.call_diagnostics),
            retrieval_attempts=tuple(knowledge.attempts),
            provider_calls=counter.calls, observed_input_tokens=counter.input_tokens, observed_output_tokens=counter.output_tokens)
        return validate_receipt(receipt, plan)


def execute_once(project_root: Path, *, plan, provider_factory, real_evidence=None):
    plan = _fresh_plan(project_root, plan)
    if real_evidence is not None and (not isinstance(real_evidence, DevelopmentEvidence) or real_evidence.plan_sha256 != plan.sha256):
        raise ValueError("development_real_plan_mismatch")
    base = project_root.resolve() / "data/runs/coach_grounded_development"
    state = base / plan.run_id
    if not state.resolve().is_relative_to(base):
        raise ValueError("development_output_outside_namespace")
    state.parent.mkdir(parents=True, exist_ok=True)
    state.mkdir(exist_ok=False)
    _write_new(state / "reservation.json", {"scope": "development_not_admission", "plan": plan.manifest,
        "real_evidence": real_evidence.model_dump(mode="json") if real_evidence else None})
    counter = None
    phase = "provider_setup"
    def on_phase(value):
        nonlocal phase
        phase = value
    try:
        counter = DevelopmentCounter(provider_factory(), on_call=lambda row:
            _write_new(state / f"call_{row.ordinal:02d}.json", row.model_dump(mode="json")))
        receipt = run_observation(project_root, provider=counter, plan=plan, real_evidence=real_evidence, on_phase=on_phase,
            on_retrieval=lambda row: _write_new(state / f"retrieval_{row.ordinal:02d}.json", row.model_dump(mode="json")))
        phase = "receipt_write"
        _write_new(state / "receipt.json", receipt.model_dump(mode="json"))
        return receipt
    except BaseException:
        _write_new(state / "failure.json", {
            "status": "interrupted_or_failed", "phase": phase, "retry_allowed": False,
            "provider_calls": counter.calls if counter else 0,
            "observed_input_tokens": counter.input_tokens if counter else 0,
            "observed_output_tokens": counter.output_tokens if counter else 0,
            "calls": [c.model_dump(mode="json") for c in counter.call_diagnostics] if counter else [],
            "evaluation_responses": [d.model_dump(mode="json") for d in counter.evaluation_responses] if counter else [],
        })
        raise
