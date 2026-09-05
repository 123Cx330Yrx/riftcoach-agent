"""Oracle-blind production Skill/RAG/Harness execution for domain cases."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.agent.context import (
    CANDIDATE_CONTEXT_SAFETY_POLICY_V1,
    ContextBuilderV1,
)
from app.agent.draft import AgentFailureObservation, SkillAgentDraftPreparer
from app.agent.draft_safety import sanitize_forbidden_markers
from app.agent.loop import AgentLoop, AgentRunResult
from app.model_runtime import (
    CandidateEvaluationRequestPolicy,
    ModelRuntimeProfile,
    require_candidate_evaluation_request_policy,
    require_registered_model_runtime_profile,
)
from app.evaluation.coach_report import (
    EVALUATOR_SYSTEM_PROMPT,
    REVISER_SYSTEM_PROMPT,
    EvaluationResponseModelV11,
    build_fact_pack,
    build_revision_prompt,
    validate_revised_report,
)
from app.harness.adapters import ChatCoachReviser, SecureChatEvaluationAdapter
from app.harness.models import ArtifactKind, RunManifest
from app.harness.steps import CoachDraft
from app.harness.store import ArtifactIntegrityError, FileRunStore
from app.providers.models import ChatRequest, ChatResponse
from app.providers.protocol import LLMProvider
from app.rag.coaching_query import CoachingQueryKnowledgeProvider
from app.rag.coaching_query import CoachingRetrievalDiagnostics
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.rag.models import KnowledgeSearchResult
from app.rag.provider import KnowledgeProvider
from app.skills.catalog import SkillCatalog
from app.skills.execution import (
    SkillExecutionBoundary,
    SkillExecutionRequest,
    SkillInputArtifactBinding,
)
from app.skills.review_executor import SkillReviewExecutor
from app.skills.router import DeterministicSkillRouter
from app.skills.routing_models import RouterRequest
from app.tools.adapters.knowledge import build_knowledge_tools
from app.tools.adapters.llm import build_llm_tools
from app.tools.models import RetryPolicy
from app.tools.registry import ToolRegistry
from app.tools.runtime import ToolRuntime

from .domain_e2e import (
    EVALUATION_ISSUE_CATEGORY_ORDER,
    EVALUATION_ISSUE_SEVERITY_ORDER,
    EvidenceDiagnostics,
    EvaluationAttemptDiagnostics,
    EvaluationDiagnostics,
    EvaluationIssueCount,
    EvaluationSeverityCount,
)
from .provider_domain_experiment import DomainCaseSemanticObservation
from .provider_domain_plan import LoadedDomainCaseInputPlan


_CITATION = re.compile(r"\[(K\d+)\]")
_FACT_ISSUE_CATEGORIES = {
    "fact_error",
    "derived_math",
    "causality",
    "meta_hallucination",
    "unsupported_comparison",
}

CANDIDATE_QUALITY_HARDENING_VERSION = "glm53-flash-domain-quality-v1"


@dataclass
class _ObservedProvider:
    """Read-only response counter around the coordinator's budgeted Provider."""

    delegate: LLMProvider
    requests: list[ChatRequest]
    responses: list[ChatResponse]

    @property
    def provider_name(self) -> str:
        return self.delegate.provider_name

    @property
    def model_name(self) -> str:
        return self.delegate.model_name

    @property
    def capabilities(self):
        return self.delegate.capabilities

    def chat(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        response = self.delegate.chat(request)
        self.responses.append(response)
        return response


class _PlanInjectedKnowledgeProvider:
    provider_name = "local-hybrid-rrf-plan-injected"

    def __init__(self, base: KnowledgeProvider, evidence_text: str) -> None:
        self._base = base
        self._evidence_text = evidence_text

    def search(self, query) -> KnowledgeSearchResult:
        result = self._base.search(query)
        return replace(
            result,
            provider=self.provider_name,
            hits=tuple(
                replace(
                    hit,
                    content=f"{hit.content}\n\n{self._evidence_text}",
                )
                for hit in result.hits
            ),
        )


class ProductionDomainCaseExecutor:
    """Run one frozen input plan case without access to Dataset oracle fields."""

    def __init__(
        self,
        *,
        project_root: str | Path,
        input_plan: LoadedDomainCaseInputPlan,
        runs_root: str | Path,
        runtime_profile: ModelRuntimeProfile | None = None,
        request_policy: CandidateEvaluationRequestPolicy | None = None,
        quality_hardening: bool = False,
        retrieval_hardening: bool = False,
        max_revisions: int = 0,
    ) -> None:
        if not isinstance(input_plan, LoadedDomainCaseInputPlan):
            raise TypeError("input_plan must be a loaded input plan")
        self._root = Path(project_root).resolve()
        self._input_plan = input_plan
        self._runs_root = Path(runs_root).resolve()
        if runtime_profile is not None and not isinstance(
            runtime_profile,
            ModelRuntimeProfile,
        ):
            raise TypeError("runtime_profile must be a ModelRuntimeProfile")
        if runtime_profile is not None and request_policy is not None:
            raise ValueError(
                "runtime_profile and request_policy are mutually exclusive"
            )
        if runtime_profile is not None:
            runtime_profile = require_registered_model_runtime_profile(
                runtime_profile
            )
        self._runtime_profile = runtime_profile
        self._request_policy = (
            require_candidate_evaluation_request_policy(request_policy)
            if request_policy is not None
            else None
        )
        if not isinstance(quality_hardening, bool):
            raise TypeError("quality_hardening must be a bool")
        if quality_hardening and self._request_policy is None:
            raise ValueError(
                "quality hardening requires an explicit candidate request policy"
            )
        self._quality_hardening = quality_hardening
        if not isinstance(retrieval_hardening, bool):
            raise TypeError("retrieval_hardening must be a bool")
        if retrieval_hardening and not quality_hardening:
            raise ValueError(
                "retrieval hardening requires candidate quality hardening"
            )
        self._retrieval_hardening = retrieval_hardening
        if isinstance(max_revisions, bool) or not isinstance(max_revisions, int):
            raise TypeError("max_revisions must be an integer")
        if not 0 <= max_revisions <= 3:
            raise ValueError("max_revisions must be between 0 and 3")
        self._max_revisions = max_revisions
        self.execution_plan = input_plan.execution_plan

    @property
    def runtime_profile(self) -> ModelRuntimeProfile | None:
        """The trusted request profile bound to this executor, if any."""

        return self._runtime_profile

    @property
    def request_policy(self) -> CandidateEvaluationRequestPolicy | None:
        """The explicit candidate evaluation policy, if bound."""

        return self._request_policy

    @property
    def quality_hardening(self) -> bool:
        """Whether the opt-in candidate quality boundary is active."""

        return self._quality_hardening

    @property
    def retrieval_hardening(self) -> bool:
        """Whether the versioned candidate query recovery wrapper is active."""

        return self._retrieval_hardening

    @property
    def max_revisions(self) -> int:
        """The explicit Harness revision budget for this case executor."""

        return self._max_revisions

    def execute(
        self,
        *,
        case_id: str,
        provider: LLMProvider,
    ) -> DomainCaseSemanticObservation:
        if self._request_policy is not None:
            require_candidate_evaluation_request_policy(
                self._request_policy,
                provider_id=getattr(provider, "provider_name", None),
                model=getattr(provider, "model_name", None),
            )
        case = self._input_plan.artifact.case(case_id)
        execution = self._build_execution(case)
        context = ContextBuilderV1().build(
            execution,
            policy_addendum=(
                CANDIDATE_CONTEXT_SAFETY_POLICY_V1
                if self._quality_hardening
                else None
            ),
        )
        base_knowledge = LocalHybridKnowledgeProvider.from_directory(
            self._root / "data/rag_docs"
        )
        knowledge: KnowledgeProvider = base_knowledge
        if case.knowledge_mode == "append_injected_evidence":
            assert case.injected_evidence_text is not None
            knowledge = _PlanInjectedKnowledgeProvider(
                base_knowledge,
                case.injected_evidence_text,
            )
        if self._retrieval_hardening:
            knowledge = CoachingQueryKnowledgeProvider(knowledge)

        observed = _ObservedProvider(provider, [], [])
        registry = ToolRegistry()
        for definition in build_knowledge_tools(knowledge):
            registry.register(definition)
        loop = AgentLoop(
            provider=observed,
            tool_registry=registry,
            tool_runtime=ToolRuntime(
                registry,
                call_id_factory=lambda: f"{case_id}-knowledge-runtime",
            ),
        )
        llm_runtime = _single_attempt_llm_runtime(
            observed,
            case_id,
            runtime_profile=self._runtime_profile,
            request_policy=self._request_policy,
        )
        evaluator = SecureChatEvaluationAdapter(
            runtime=llm_runtime,
            system_prompt=EVALUATOR_SYSTEM_PROMPT,
            fact_pack_builder=build_fact_pack,
        )
        reviser = ChatCoachReviser(
            runtime=llm_runtime,
            system_prompt=REVISER_SYSTEM_PROMPT,
            prompt_builder=build_revision_prompt,
            validator=validate_revised_report,
        )
        result = SkillReviewExecutor(
            runs_root=self._runs_root,
            draft_preparer=SkillAgentDraftPreparer(
                loop,
                runtime_profile=self._runtime_profile,
                request_policy=self._request_policy,
            ),
            evaluator=evaluator,
            reviser=reviser,
            max_revisions=self._max_revisions,
            allow_deterministic_fallback=(
                False if self._request_policy is not None else None
            ),
            minimum_evidence_sources=(
                1 if self._quality_hardening else None
            ),
            draft_guard=(
                (
                    lambda draft, _knowledge: _guard_candidate_draft(
                        draft,
                        case.forbidden_output_markers,
                    )
                )
                if self._quality_hardening
                else None
            ),
        ).execute(execution=execution, context=context)
        store = FileRunStore(self._runs_root, execution.run_id)
        return _semantic_observation(
            case_id=case_id,
            case=case,
            provider_requests=observed.requests,
            provider_responses=observed.responses,
            agent_run=result.agent_run,
            agent_failure=result.agent_failure,
            output=result.output,
            manifest=result.manifest,
            store=store,
            use_persisted_report=self._quality_hardening,
        )

    def _build_execution(self, case) -> Any:
        catalog = SkillCatalog.from_directory(self._root / "skills")
        decision = DeterministicSkillRouter().route(
            RouterRequest(
                utterance=case.user_utterance,
                available_skills=catalog.route_candidates,
            )
        )
        if decision.selected_skill != self._input_plan.artifact.skill_name:
            raise ValueError("held-out input did not select its frozen Skill")
        skill = catalog.get(self._input_plan.artifact.skill_name)
        if skill is None:
            raise ValueError("frozen Skill is unavailable")
        summary = json.loads(
            self._input_plan.player_summary_path.read_text(encoding="utf-8")
        )
        report = self._input_plan.deterministic_report_path.read_text(
            encoding="utf-8"
        )
        payload = {
            "player_summary": summary,
            "deterministic_report": report,
            "focus": case.focus,
        }
        typed_input = skill.input_model.model_validate(payload)
        binding = SkillInputArtifactBinding.from_content(
            run_id=case.run_id,
            player_summary=typed_input.player_summary,
            deterministic_report=typed_input.deterministic_report,
        )
        return SkillExecutionBoundary(catalog).validate(
            SkillExecutionRequest(
                run_id=case.run_id,
                user_utterance=case.user_utterance,
                router_decision=decision,
                input_payload=payload,
                input_artifacts=binding,
            )
        )


def _single_attempt_llm_runtime(
    provider: LLMProvider,
    case_id: str,
    *,
    runtime_profile: ModelRuntimeProfile | None = None,
    request_policy: CandidateEvaluationRequestPolicy | None = None,
):
    if runtime_profile is not None and request_policy is not None:
        raise ValueError(
            "runtime_profile and request_policy are mutually exclusive"
        )
    registry = ToolRegistry()
    definition = build_llm_tools(
        provider,
        runtime_profile=runtime_profile,
        request_policy=request_policy,
    )[0]
    registry.register(
        replace(
            definition,
            policy=replace(definition.policy, retry=RetryPolicy()),
        )
    )
    return ToolRuntime(
        registry,
        call_id_factory=lambda: f"{case_id}-llm-runtime",
    )


def _semantic_observation(
    *,
    case_id: str,
    case,
    provider_requests: list[ChatRequest],
    provider_responses: list[ChatResponse],
    agent_run: AgentRunResult | None,
    agent_failure: AgentFailureObservation | None,
    output,
    manifest: RunManifest,
    store: FileRunStore,
    use_persisted_report: bool = False,
) -> DomainCaseSemanticObservation:
    draft = ""
    proposed: tuple[str, ...] = ()
    successful: tuple[str, ...] = ()
    agent_status = None
    agent_stop_reason = None
    error_code = None
    if agent_run is not None:
        agent_status = agent_run.status.value
        agent_stop_reason = agent_run.stop_reason.value
        error_code = agent_run.error_code
        proposed = _unique(
            call.name
            for response in agent_run.provider_responses
            for call in response.tool_calls
        )
        successful = _unique(
            row.tool_name
            for row in agent_run.tool_executions
            if row.result.success
        )
        if agent_run.final_response is not None:
            draft = agent_run.final_response.content or ""
    # When a candidate boundary redacts a clearly quoted refusal, evaluate the
    # persisted post-guard draft rather than the private raw Provider text.
    # Rejected runs have no final report, so the raw draft remains available
    # only for the local semantic failure calculation.
    final_records = [
        row
        for row in manifest.artifacts
        if row.get("kind") == ArtifactKind.FINAL_REPORT.value
    ]
    if (
        use_persisted_report
        and len(final_records) == 1
        and manifest.status.value in {"published", "degraded"}
    ):
        try:
            draft = store.read_artifact(final_records[0]).decode("utf-8")
        except (ArtifactIntegrityError, UnicodeDecodeError, KeyError, OSError):
            pass
    elif agent_failure is not None:
        agent_status = agent_failure.status.value
        agent_stop_reason = agent_failure.stop_reason.value
        error_code = agent_failure.error_code

    evidence_source_ids = tuple(getattr(output, "evidence_source_ids", ()))
    evidence_diagnostics = _evidence_diagnostics(
        agent_run=agent_run,
        evidence_source_ids=evidence_source_ids,
        manifest=manifest,
        store=store,
    )
    allowed_citations = _evidence_citation_ids(manifest, store)
    cited = set(_CITATION.findall(draft))
    citation_check = None if not draft else not cited.difference(allowed_citations)
    injection_check = (
        None
        if not draft
        else not any(marker in draft for marker in case.forbidden_output_markers)
    )
    evaluation_diagnostics, evaluation_payload = _evaluation_observation(
        manifest,
        store,
    )
    fact_check = None
    evaluation_validated = False
    evaluation_score = getattr(output, "evaluation_score", None)
    if evaluation_payload is not None:
        evaluation_validated = _valid_evaluation_payload(evaluation_payload)
        fact_check = not any(
            str(issue.get("category", "")) in _FACT_ISSUE_CATEGORIES
            for issue in evaluation_payload.get("issues", ())
        )
    terminal_status = getattr(output, "status", None)
    terminal_reason = _terminal_reason(manifest)
    provenance = _sha256(
        {
            "case_id": case_id,
            "request_sha256": tuple(
                _request_digest(row)
                for row in provider_requests
            ),
            "response_count": len(provider_responses),
            "artifact_sha256": tuple(
                (row["kind"], row["path"], row["sha256"])
                for row in manifest.artifacts
            ),
            "agent_status": agent_status,
            "agent_stop_reason": agent_stop_reason,
            "error_code": error_code,
            "terminal_status": terminal_status,
            "terminal_reason": terminal_reason,
            "revision_count": manifest.revision_count,
            "evaluation_diagnostics": evaluation_diagnostics.model_dump(
                mode="json"
            ),
            "fact_check_passed": fact_check,
            "citation_check_passed": citation_check,
            "injection_check_passed": injection_check,
        }
    )
    return DomainCaseSemanticObservation(
        case_id=case_id,
        normalized_response_count=len(provider_responses),
        safe_provider_error_code=error_code,
        agent_status=agent_status,
        agent_stop_reason=agent_stop_reason,
        proposed_tool_names=proposed,
        successful_tool_names=successful,
        evidence_source_ids=evidence_source_ids,
        evidence_diagnostics=evidence_diagnostics,
        revision_count=manifest.revision_count,
        evaluation_diagnostics=evaluation_diagnostics,
        fact_check_passed=fact_check,
        citation_check_passed=citation_check,
        injection_check_passed=injection_check,
        evaluation_validated=evaluation_validated,
        evaluation_score=evaluation_score if evaluation_validated else None,
        terminal_status=terminal_status,
        terminal_reason=terminal_reason,
        provenance_sha256=provenance,
    )


def _evidence_citation_ids(manifest: RunManifest, store: FileRunStore) -> set[str]:
    records = [
        row for row in manifest.artifacts
        if row.get("kind") == ArtifactKind.RETRIEVAL_EVIDENCE.value
    ]
    if not records:
        return set()
    payload = json.loads(store.read_artifact(records[0]).decode("utf-8"))
    return {
        str(row["citation_id"])
        for row in payload.get("citations", ())
        if isinstance(row, dict) and row.get("citation_id")
    }


def _evidence_diagnostics(
    *,
    agent_run: AgentRunResult | None,
    evidence_source_ids: tuple[str, ...],
    manifest: RunManifest,
    store: FileRunStore,
) -> EvidenceDiagnostics:
    """Project retrieval state into safe counters only."""

    executions = tuple(
        row
        for row in (agent_run.tool_executions if agent_run is not None else ())
        if row.tool_name == "knowledge.search"
    )
    successful = tuple(row for row in executions if row.result.success)
    payloads = tuple(
        row.result.data
        for row in successful
        if isinstance(row.result.data, Mapping)
    )
    chunks_returned = 0
    abstained: bool | None = None
    reason: str | None = None
    recovery_attempts = 0
    recovery_recovered: bool | None = None
    recovery_topics: set[str] = set()
    for payload in payloads:
        chunks = payload.get("chunks")
        if isinstance(chunks, (list, tuple)):
            chunks_returned += len(chunks)
        if isinstance(payload.get("abstained"), bool):
            abstained = bool(payload["abstained"])
        diagnostics = payload.get("diagnostics")
        if isinstance(diagnostics, Mapping):
            candidate_reason = diagnostics.get("reason")
            if isinstance(candidate_reason, str) and re.fullmatch(
                r"[a-z][a-z0-9_]{0,127}", candidate_reason
            ):
                reason = candidate_reason
            recovery = diagnostics.get("query_recovery")
            if isinstance(recovery, Mapping):
                try:
                    parsed = CoachingRetrievalDiagnostics.model_validate(
                        recovery
                    )
                except ValidationError:
                    # Raw diagnostics are untrusted Provider/tool data.  Do
                    # not project a malformed payload into the safe receipt.
                    continue
                recovery_attempts += len(parsed.attempts)
                if len(parsed.attempts) == 2:
                    recovered = parsed.attempts[-1].returned_count > 0
                    recovery_recovered = (
                        recovered
                        if recovery_recovered is None
                        else recovery_recovered or recovered
                    )
                recovery_topics.add(parsed.topic)
    artifact_present = any(
        row.get("kind") == ArtifactKind.RETRIEVAL_EVIDENCE.value
        for row in manifest.artifacts
    )
    return EvidenceDiagnostics(
        search_calls=len(executions),
        successful_search_calls=len(successful),
        payloads_with_data=len(payloads),
        chunks_returned=chunks_returned,
        source_count=len(evidence_source_ids),
        artifact_present=artifact_present,
        abstained=abstained,
        reason=reason,
        query_recovery_attempts=recovery_attempts,
        query_recovery_recovered=recovery_recovered,
        query_recovery_topic=(
            next(iter(recovery_topics)) if len(recovery_topics) == 1 else None
        ),
    )


def _evaluation_observation(
    manifest: RunManifest,
    store: FileRunStore,
) -> tuple[EvaluationDiagnostics, dict | None]:
    empty = EvaluationDiagnostics()
    records = [
        row for row in manifest.artifacts
        if row.get("kind") == ArtifactKind.EVALUATION_RESULT.value
    ]
    if not records:
        return empty, None
    if manifest.attempt_id not in (0, 1) or manifest.revision_count != manifest.attempt_id:
        return empty, None
    expected_paths = tuple(
        f"evaluations/evaluation_attempt_{attempt_id}.json"
        for attempt_id in range(manifest.attempt_id + 1)
    )
    if len(records) != len(expected_paths):
        return empty, None

    attempts = []
    latest_payload: dict | None = None
    try:
        for attempt_id, expected_path in enumerate(expected_paths):
            matching = [row for row in records if row.get("path") == expected_path]
            if len(matching) != 1:
                return empty, None
            record = matching[0]
            if (
                record.get("run_id") != manifest.run_id
                or record.get("schema_version") != "1.0"
                or record.get("producer") != "evaluator"
            ):
                return empty, None
            payload = json.loads(store.read_artifact(record).decode("utf-8"))
            evaluation = EvaluationResponseModelV11.model_validate(
                payload,
                strict=True,
            )
            category_counts = Counter(row.category for row in evaluation.issues)
            severity_counts = Counter(row.severity for row in evaluation.issues)
            attempts.append(
                EvaluationAttemptDiagnostics(
                    attempt_id=attempt_id,
                    score=evaluation.score,
                    verdict=evaluation.verdict,
                    passed_check_count=len(evaluation.passed_checks),
                    issue_category_counts=tuple(
                        EvaluationIssueCount(name=name, count=category_counts[name])
                        for name in EVALUATION_ISSUE_CATEGORY_ORDER
                        if category_counts[name]
                    ),
                    severity_counts=tuple(
                        EvaluationSeverityCount(name=name, count=severity_counts[name])
                        for name in EVALUATION_ISSUE_SEVERITY_ORDER
                        if severity_counts[name]
                    ),
                )
            )
            latest_payload = evaluation.model_dump(mode="json")
    except (
        ArtifactIntegrityError,
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ):
        return empty, None
    return EvaluationDiagnostics(attempts=tuple(attempts)), latest_payload


def _valid_evaluation_payload(payload: dict) -> bool:
    try:
        EvaluationResponseModelV11.model_validate(payload, strict=True)
        return True
    except (TypeError, ValueError):
        return False


def _terminal_reason(manifest: RunManifest) -> str | None:
    if not manifest.transitions:
        return None
    reason = manifest.transitions[-1].get("reason")
    return reason.split(":", 1)[0] if isinstance(reason, str) and reason else None


def _request_digest(request: ChatRequest) -> str:
    return _sha256({
        "messages": [
            {"role": row.role.value, "content": row.content}
            for row in request.messages
        ],
        "tools": [row.name for row in request.tools],
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
        "timeout_s": request.timeout_s,
        "top_p": request.top_p,
        "response_contract": (
            request.response_contract.schema_dict()
            if request.response_contract is not None
            else None
        ),
        "metadata": dict(request.metadata),
    })


def _sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _unique(values) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value) for value in values))


def _guard_candidate_draft(
    draft: CoachDraft,
    forbidden_markers: tuple[str, ...],
) -> CoachDraft:
    """Apply the candidate-only marker boundary without leaking raw text."""

    if not isinstance(draft, CoachDraft):
        raise TypeError("draft guard requires CoachDraft")
    result = sanitize_forbidden_markers(draft.report, forbidden_markers)
    return CoachDraft(report=result.report)


__all__ = [
    "CANDIDATE_QUALITY_HARDENING_VERSION",
    "ProductionDomainCaseExecutor",
]
