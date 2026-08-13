"""Bounded real-Provider admission for the recent-form Skill control flow."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from app.agent.context import ContextBuilderV1
from app.agent.draft import SkillAgentDraftPreparer
from app.agent.loop import AgentLoop, AgentRunStatus, AgentStopReason
from app.evaluation.coach_report import (
    EVALUATOR_SYSTEM_PROMPT,
    REVISER_SYSTEM_PROMPT,
    build_evaluation_prompt,
    build_fact_pack,
    build_revision_prompt,
    validate_revised_report,
)
from app.harness.adapters import ChatCoachReviser, ChatEvaluationAdapter
from app.providers.errors import ProviderError
from app.providers.models import ChatRequest, ChatResponse
from app.providers.protocol import LLMProvider
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.skills.catalog import SkillCatalog
from app.skills.execution import (
    SkillExecutionBoundary,
    SkillExecutionRequest,
    SkillInputArtifactBinding,
)
from app.skills.review_executor import SkillReviewExecutor
from app.skills.router import DeterministicSkillRouter
from app.skills.routing_models import RouterRequest
from app.tools.adapters import build_knowledge_tools, build_llm_tools
from app.tools.models import CachePolicy, RetryPolicy
from app.tools.registry import ToolRegistry
from app.tools.runtime import ToolRuntime

from .provider_adapter_protocol import (
    AdapterProtocolSliceReport,
    BudgetedProvider,
)
from .provider_capability_gate import (
    CodeShaText,
    ExternalCallBudget,
    NonBlankText,
    Sha256Text,
)


_CUMULATIVE_MAX_CALLS = 7
_PRIOR_PROTOCOL_CALLS = 3
_DOMAIN_MAX_CALLS = _CUMULATIVE_MAX_CALLS - _PRIOR_PROTOCOL_CALLS
_DOMAIN_RUN_ID = "zhipu_recent_form_domain_slice"
_DOMAIN_UTTERANCE = "分析我最近几局的状态"
_PHASES = ("agent", "evaluation", "evaluation_repair", "revision")
_CODE_SHA_ADAPTER = TypeAdapter(CodeShaText)


class PriorAdapterEvidence(BaseModel):
    """Strict identity and digest of the already admitted protocol result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider_id: NonBlankText
    requested_model: NonBlankText
    code_sha: CodeShaText
    calls_used: Literal[3] = _PRIOR_PROTOCOL_CALLS
    result_sha256: Sha256Text


class DomainSkillSliceReport(BaseModel):
    """Sanitized evidence for one real recent-form domain admission run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    probe_scope: Literal["recent_form_domain"] = "recent_form_domain"
    provider_id: NonBlankText
    requested_model: NonBlankText
    code_sha: CodeShaText
    run_timestamp_utc: datetime
    fixture_sha256: Sha256Text
    prior_result_sha256: Sha256Text
    prior_code_sha: CodeShaText
    cumulative_max_calls: Literal[7] = _CUMULATIVE_MAX_CALLS
    prior_calls_used: Literal[3] = _PRIOR_PROTOCOL_CALLS
    remaining_calls: Literal[4] = _DOMAIN_MAX_CALLS
    domain_max_calls: Literal[4] = _DOMAIN_MAX_CALLS
    domain_calls_used: int = Field(ge=0, le=_DOMAIN_MAX_CALLS)
    cumulative_calls_used: int = Field(
        ge=_PRIOR_PROTOCOL_CALLS,
        le=_CUMULATIVE_MAX_CALLS,
    )
    admitted: bool
    error_code: NonBlankText | None = None
    agent_calls: int = Field(ge=0, le=_DOMAIN_MAX_CALLS)
    evaluation_calls: int = Field(ge=0, le=_DOMAIN_MAX_CALLS)
    evaluation_repair_calls: int = Field(ge=0, le=1)
    revision_calls: int = Field(ge=0, le=1)
    budget_block_count: int = Field(ge=0)
    response_count: int = Field(ge=0, le=_DOMAIN_MAX_CALLS)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    latency_ms: int = Field(ge=0)
    resolved_models: tuple[NonBlankText, ...] = ()
    finish_reasons: tuple[NonBlankText, ...] = ()
    request_id_sha256: tuple[Sha256Text, ...] = ()
    agent_status: Literal["completed", "stopped", "failed"] | None = None
    agent_stop_reason: NonBlankText | None = None
    tool_call_count: int = Field(ge=0)
    tool_execution_count: int = Field(ge=0)
    knowledge_source_count: int = Field(ge=0)
    evaluation_validated: bool
    evaluation_score: int | None = Field(default=None, ge=0, le=100)
    terminal_status: Literal["published", "degraded", "rejected"] | None = None
    typed_output_sha256: Sha256Text | None = None
    estimated_cost: float | None = Field(default=None, ge=0)
    cost_note: NonBlankText = "No verified unit-price snapshot was applied."

    @model_validator(mode="after")
    def validate_evidence(self) -> "DomainSkillSliceReport":
        if self.remaining_calls != self.cumulative_max_calls - self.prior_calls_used:
            raise ValueError("remaining calls must be derived from cumulative evidence.")
        if self.domain_max_calls != self.remaining_calls:
            raise ValueError("domain budget must equal the remaining cumulative budget.")
        if self.cumulative_calls_used != (
            self.prior_calls_used + self.domain_calls_used
        ):
            raise ValueError("cumulative calls must include prior and domain calls.")
        phase_total = sum(
            (
                self.agent_calls,
                self.evaluation_calls,
                self.evaluation_repair_calls,
                self.revision_calls,
            )
        )
        if phase_total != self.domain_calls_used:
            raise ValueError("domain calls must equal the sum of phase calls.")
        if len(self.resolved_models) != self.response_count:
            raise ValueError("every response needs one resolved model.")
        if len(self.finish_reasons) > self.response_count:
            raise ValueError("finish reasons cannot outnumber responses.")
        if len(self.request_id_sha256) > self.response_count:
            raise ValueError("request ID digests cannot outnumber responses.")
        if self.response_count > self.domain_calls_used:
            raise ValueError("responses cannot outnumber real domain calls.")
        if self.tool_execution_count > self.tool_call_count:
            raise ValueError("tool executions cannot outnumber proposed calls.")
        if self.evaluation_validated is not (self.evaluation_score is not None):
            raise ValueError("validated Evaluation requires a persisted score.")
        if self.terminal_status is None:
            if self.typed_output_sha256 is not None:
                raise ValueError("typed output digest requires a terminal status.")
        elif self.typed_output_sha256 is None:
            raise ValueError("terminal typed output requires a digest.")

        expected_admission = all(
            (
                self.error_code is None,
                self.response_count == self.domain_calls_used,
                self.agent_calls == 2,
                self.evaluation_calls == 1,
                self.evaluation_repair_calls in {0, 1},
                self.revision_calls == 0,
                self.tool_call_count == 1,
                self.tool_execution_count == 1,
                self.knowledge_source_count >= 1,
                self.evaluation_validated,
                self.terminal_status is not None,
                self.typed_output_sha256 is not None,
                self.agent_status == AgentRunStatus.COMPLETED.value,
                self.agent_stop_reason == AgentStopReason.FINAL_RESPONSE.value,
            )
        )
        if self.admitted is not expected_admission:
            raise ValueError("admitted must match mandatory domain evidence.")
        return self


def load_prior_adapter_evidence(
    path: str | Path,
    *,
    expected_provider_id: str,
    expected_model: str,
) -> PriorAdapterEvidence:
    """Strictly validate the prior result before any new Provider can be called."""

    result_path = Path(path)
    raw = result_path.read_bytes()
    try:
        report = AdapterProtocolSliceReport.model_validate_json(raw)
    except Exception as exc:
        raise ValueError("prior adapter result is not a valid admitted contract") from exc
    if not report.admitted or report.calls_used != _PRIOR_PROTOCOL_CALLS:
        raise ValueError("prior adapter result is not an admitted three-call slice")
    if (
        report.provider_id != expected_provider_id
        or report.requested_model != expected_model
    ):
        raise ValueError("prior adapter result identity does not match the domain run")
    return PriorAdapterEvidence(
        provider_id=report.provider_id,
        requested_model=report.requested_model,
        code_sha=report.code_sha,
        result_sha256=hashlib.sha256(raw).hexdigest(),
    )


class _ObservedBudgetedProvider:
    """Share one pre-I/O budget while collecting only sanitized call metadata."""

    def __init__(
        self,
        *,
        provider: LLMProvider,
        budget: ExternalCallBudget,
        clock=time.monotonic,
    ) -> None:
        self._budget = budget
        self._provider = BudgetedProvider(provider=provider, budget=budget)
        self._clock = clock
        self.provider_name = provider.provider_name
        self.model_name = provider.model_name
        self.capabilities = provider.capabilities
        self.phases: list[str] = []
        self.responses: list[ChatResponse] = []
        self.total_latency_ms = 0
        self.budget_block_count = 0

    def chat(self, request: ChatRequest) -> ChatResponse:
        phase = _request_phase(request)
        calls_before = self._budget.calls_used
        started = self._clock()
        try:
            response = self._provider.chat(request)
        except ProviderError as exc:
            if exc.code == "external_call_budget_exhausted":
                self.budget_block_count += 1
            raise
        finally:
            if self._budget.calls_used > calls_before:
                self.phases.append(phase)
                self.total_latency_ms += max(
                    0,
                    int(round((self._clock() - started) * 1000)),
                )
        self.responses.append(response)
        return response


class DomainSkillSliceRunner:
    """Compose the existing recent-form Skill and Harness under four calls."""

    def __init__(
        self,
        *,
        provider: LLMProvider,
        code_sha: str,
        prior_evidence: PriorAdapterEvidence,
        player_summary: dict[str, Any],
        deterministic_report: str,
        runs_root: str | Path,
        knowledge_dir: str | Path,
        skills_dir: str | Path = "skills",
        now=lambda: datetime.now(timezone.utc),
        clock=time.monotonic,
    ) -> None:
        if not isinstance(prior_evidence, PriorAdapterEvidence):
            raise TypeError("prior_evidence must be PriorAdapterEvidence")
        if (
            provider.provider_name != prior_evidence.provider_id
            or provider.model_name != prior_evidence.requested_model
        ):
            raise ValueError("Provider identity does not match prior adapter evidence")
        self._provider = provider
        self._code_sha = _CODE_SHA_ADAPTER.validate_python(code_sha)
        self._prior = prior_evidence
        self._summary = json.loads(json.dumps(player_summary, ensure_ascii=False))
        self._deterministic_report = deterministic_report
        self._runs_root = Path(runs_root)
        self._knowledge_dir = Path(knowledge_dir)
        self._skills_dir = Path(skills_dir)
        self._now = now
        self._clock = clock

    def run(self) -> DomainSkillSliceReport:
        budget = ExternalCallBudget(max_calls=_DOMAIN_MAX_CALLS)
        observed = _ObservedBudgetedProvider(
            provider=self._provider,
            budget=budget,
            clock=self._clock,
        )
        started = self._clock()
        result = None
        safe_error: str | None = None
        try:
            execution = self._build_execution()
            context = ContextBuilderV1().build(execution)
            knowledge_registry = ToolRegistry()
            knowledge_provider = LocalHybridKnowledgeProvider.from_directory(
                self._knowledge_dir
            )
            for definition in build_knowledge_tools(knowledge_provider):
                knowledge_registry.register(definition)
            agent_loop = AgentLoop(
                provider=observed,
                tool_registry=knowledge_registry,
                tool_runtime=ToolRuntime(knowledge_registry),
            )
            harness_runtime = _single_attempt_llm_runtime(observed)
            result = SkillReviewExecutor(
                runs_root=self._runs_root,
                draft_preparer=SkillAgentDraftPreparer(agent_loop),
                evaluator=ChatEvaluationAdapter(
                    runtime=harness_runtime,
                    system_prompt=EVALUATOR_SYSTEM_PROMPT,
                    fact_pack_builder=build_fact_pack,
                    prompt_builder=build_evaluation_prompt,
                ),
                reviser=ChatCoachReviser(
                    runtime=harness_runtime,
                    system_prompt=REVISER_SYSTEM_PROMPT,
                    prompt_builder=build_revision_prompt,
                    validator=validate_revised_report,
                ),
            ).execute(execution=execution, context=context)
        except Exception:
            safe_error = "domain_execution_failed"

        agent_run = result.agent_run if result is not None else None
        output = result.output if result is not None else None
        terminal_status = getattr(output, "status", None)
        evaluation_score = getattr(output, "evaluation_score", None)
        source_ids = tuple(getattr(output, "evidence_source_ids", ()))
        typed_output_digest = (
            _sha256(output.model_dump(mode="json")) if output is not None else None
        )
        tool_call_count = 0
        tool_execution_count = 0
        agent_status = None
        agent_stop_reason = None
        if agent_run is not None:
            tool_call_count = sum(
                len(response.tool_calls)
                for response in agent_run.provider_responses
            )
            tool_execution_count = len(agent_run.tool_executions)
            agent_status = agent_run.status.value
            agent_stop_reason = agent_run.stop_reason.value

        if safe_error is None:
            if (
                tool_call_count != 1
                or tool_execution_count != 1
                or not source_ids
            ):
                safe_error = "knowledge_round_trip_incomplete"
            elif evaluation_score is None:
                safe_error = "structured_evaluation_failed"
            elif observed.phases.count("revision"):
                safe_error = "revision_path_incomplete"

        phase_counts = {phase: observed.phases.count(phase) for phase in _PHASES}
        domain_calls = budget.calls_used
        admitted = all(
            (
                safe_error is None,
                phase_counts["agent"] == 2,
                phase_counts["evaluation"] == 1,
                phase_counts["evaluation_repair"] in {0, 1},
                phase_counts["revision"] == 0,
                tool_call_count == 1,
                tool_execution_count == 1,
                len(source_ids) >= 1,
                evaluation_score is not None,
                terminal_status is not None,
                typed_output_digest is not None,
                agent_status == AgentRunStatus.COMPLETED.value,
                agent_stop_reason == AgentStopReason.FINAL_RESPONSE.value,
            )
        )
        responses = tuple(observed.responses)
        return DomainSkillSliceReport(
            provider_id=observed.provider_name,
            requested_model=observed.model_name,
            code_sha=self._code_sha,
            run_timestamp_utc=self._now(),
            fixture_sha256=_sha256(
                {
                    "player_summary": self._summary,
                    "deterministic_report": self._deterministic_report,
                }
            ),
            prior_result_sha256=self._prior.result_sha256,
            prior_code_sha=self._prior.code_sha,
            domain_calls_used=domain_calls,
            cumulative_calls_used=self._prior.calls_used + domain_calls,
            admitted=admitted,
            error_code=safe_error,
            agent_calls=phase_counts["agent"],
            evaluation_calls=phase_counts["evaluation"],
            evaluation_repair_calls=phase_counts["evaluation_repair"],
            revision_calls=phase_counts["revision"],
            budget_block_count=observed.budget_block_count,
            response_count=len(responses),
            input_tokens=sum(response.usage.input_tokens for response in responses),
            output_tokens=sum(response.usage.output_tokens for response in responses),
            latency_ms=max(
                observed.total_latency_ms,
                int(round((self._clock() - started) * 1000)),
            ),
            resolved_models=tuple(response.model for response in responses),
            finish_reasons=tuple(
                response.finish_reason
                for response in responses
                if response.finish_reason is not None
            ),
            request_id_sha256=tuple(
                hashlib.sha256(response.request_id.encode("utf-8")).hexdigest()
                for response in responses
                if response.request_id is not None
            ),
            agent_status=agent_status,
            agent_stop_reason=agent_stop_reason,
            tool_call_count=tool_call_count,
            tool_execution_count=tool_execution_count,
            knowledge_source_count=len(source_ids),
            evaluation_validated=evaluation_score is not None,
            evaluation_score=evaluation_score,
            terminal_status=terminal_status,
            typed_output_sha256=typed_output_digest,
        )

    def _build_execution(self):
        catalog = SkillCatalog.from_directory(self._skills_dir)
        decision = DeterministicSkillRouter().route(
            RouterRequest(
                utterance=_DOMAIN_UTTERANCE,
                available_skills=catalog.route_candidates,
            )
        )
        if decision.selected_skill != "recent-form-review":
            raise ValueError("domain fixture did not select recent-form-review")
        skill = catalog.get("recent-form-review")
        if skill is None:
            raise ValueError("recent-form-review is not available")
        payload = {
            "player_summary": self._summary,
            "deterministic_report": self._deterministic_report,
            "focus": "survival",
        }
        typed_input = skill.input_model.model_validate(payload)
        binding = SkillInputArtifactBinding.from_content(
            run_id=_DOMAIN_RUN_ID,
            player_summary=typed_input.player_summary,
            deterministic_report=typed_input.deterministic_report,
        )
        return SkillExecutionBoundary(catalog).validate(
            SkillExecutionRequest(
                run_id=_DOMAIN_RUN_ID,
                user_utterance=_DOMAIN_UTTERANCE,
                router_decision=decision,
                input_payload=payload,
                input_artifacts=binding,
            )
        )


def _single_attempt_llm_runtime(provider: LLMProvider) -> ToolRuntime:
    registry = ToolRegistry()
    definition = build_llm_tools(provider)[0]
    policy = replace(
        definition.policy,
        retry=RetryPolicy(max_attempts=1),
        cache=CachePolicy(ttl_s=0.0),
    )
    registry.register(replace(definition, policy=policy, fallback=None))
    return ToolRuntime(registry)


def _request_phase(request: ChatRequest) -> str:
    if "agent_loop_iteration" in request.metadata:
        return "agent"
    harness_step = request.metadata.get("harness_step")
    if harness_step in {"evaluate", "evaluate_repair", "revise"}:
        return {
            "evaluate": "evaluation",
            "evaluate_repair": "evaluation_repair",
            "revise": "revision",
        }[harness_step]
    raise ValueError("domain Provider request has an unknown phase")


def _sha256(value: Any) -> str:
    if isinstance(value, str):
        data = value.encode("utf-8")
    else:
        data = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


__all__ = [
    "DomainSkillSliceReport",
    "DomainSkillSliceRunner",
    "PriorAdapterEvidence",
    "load_prior_adapter_evidence",
]
