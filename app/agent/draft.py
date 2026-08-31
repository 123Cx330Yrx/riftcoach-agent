"""Evidence-aware draft preparation for one validated Skill execution."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.model_runtime import (
    ModelRuntimeProfile,
    require_registered_model_runtime_profile,
)
from app.harness.knowledge import (
    KnowledgeEvidenceBuildError,
    knowledge_evidence_from_search_payloads,
)
from app.harness.steps import CoachDraft, KnowledgeEvidence
from app.skills.execution import ValidatedSkillExecution

from .compiler import AgentRunCompileError, AgentRunCompiler
from .context import ContextBundle
from .loop import (
    AgentLoop,
    AgentRunResult,
    AgentRunStatus,
    AgentStopReason,
)
from app.runtime.observer import (
    RuntimeObservationError,
    RuntimeSignalObserver,
)


_KNOWLEDGE_TOOL_NAME = "knowledge.search"
_SAFE_ERROR_CODE = re.compile(r"^[a-z][a-z0-9_]{0,127}$")


class AgentDraftPreparationError(RuntimeError):
    """Raised when an Agent run cannot safely become a Harness draft input."""

    def __init__(
        self,
        message: str,
        *,
        failure: AgentFailureObservation | None = None,
    ) -> None:
        if not isinstance(message, str) or not message.strip():
            raise ValueError("message must not be empty")
        if failure is not None and not isinstance(
            failure,
            AgentFailureObservation,
        ):
            raise TypeError("failure must be an AgentFailureObservation or None")
        self.failure = failure
        super().__init__(message)


@dataclass(frozen=True)
class AgentFailureObservation:
    """Safe Agent terminal metadata without prompts or Provider payloads."""

    status: AgentRunStatus
    stop_reason: AgentStopReason
    error_code: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, AgentRunStatus):
            raise TypeError("status must be an AgentRunStatus")
        if not isinstance(self.stop_reason, AgentStopReason):
            raise TypeError("stop_reason must be an AgentStopReason")
        if self.error_code is not None and not _SAFE_ERROR_CODE.fullmatch(
            self.error_code
        ):
            raise ValueError("error_code must be a safe snake-case code")

    @classmethod
    def from_agent_run(
        cls,
        agent_run: AgentRunResult,
    ) -> AgentFailureObservation:
        if not isinstance(agent_run, AgentRunResult):
            raise TypeError("agent_run must be an AgentRunResult")
        return cls(
            status=agent_run.status,
            stop_reason=agent_run.stop_reason,
            error_code=agent_run.error_code,
        )


@dataclass(frozen=True)
class AgentDraftPreparationResult:
    """Unpublished draft, attributable evidence, and its exact Agent run."""

    draft: CoachDraft
    knowledge: KnowledgeEvidence
    agent_run: AgentRunResult

    def __post_init__(self) -> None:
        if not isinstance(self.draft, CoachDraft):
            raise TypeError("draft must be a CoachDraft")
        if not isinstance(self.knowledge, KnowledgeEvidence):
            raise TypeError("knowledge must be KnowledgeEvidence")
        if not isinstance(self.agent_run, AgentRunResult):
            raise TypeError("agent_run must be an AgentRunResult")


class SkillAgentDraftPreparer:
    """Compile and run one Skill without evaluating or publishing its draft."""

    def __init__(
        self,
        agent_loop: AgentLoop,
        *,
        observer: RuntimeSignalObserver | None = None,
        runtime_profile: ModelRuntimeProfile | None = None,
    ) -> None:
        if not callable(getattr(agent_loop, "run", None)):
            raise TypeError("agent_loop must provide run()")
        self._agent_loop = agent_loop
        self._observer = observer
        if runtime_profile is not None:
            runtime_profile = require_registered_model_runtime_profile(
                runtime_profile
            )
            provider_name = getattr(agent_loop.provider, "provider_name", None)
            model_name = getattr(agent_loop.provider, "model_name", None)
            if not runtime_profile.matches(provider_name, model_name):
                raise ValueError(
                    "runtime_profile does not match the Agent Provider"
                )
        self._compiler = AgentRunCompiler(
            agent_loop.tool_registry,
            runtime_profile=runtime_profile,
        )

    def prepare(
        self,
        execution: ValidatedSkillExecution,
        context: ContextBundle,
    ) -> AgentDraftPreparationResult:
        try:
            request = self._compiler.compile(execution, context)
        except AgentRunCompileError as exc:
            raise AgentDraftPreparationError(
                f"agent request compilation failed: {exc}"
            ) from exc

        try:
            if self._observer is None:
                agent_run = self._agent_loop.run(request)
            else:
                agent_run = self._agent_loop.run(
                    request,
                    observer=self._observer,
                )
        except RuntimeObservationError:
            raise
        except Exception as exc:
            raise AgentDraftPreparationError(
                "agent loop raised an unexpected error"
            ) from exc

        _require_completed_final_response(agent_run)
        knowledge = _knowledge_from_actual_tool_executions(agent_run)
        final_response = agent_run.final_response
        if final_response is None or final_response.content is None:
            raise AgentDraftPreparationError(
                "completed agent run did not provide final text"
            )

        return AgentDraftPreparationResult(
            draft=CoachDraft(report=final_response.content),
            knowledge=knowledge,
            agent_run=agent_run,
        )


def _require_completed_final_response(agent_run: AgentRunResult) -> None:
    if not isinstance(agent_run, AgentRunResult):
        raise AgentDraftPreparationError(
            "agent loop returned an invalid result contract"
        )
    if (
        agent_run.status is not AgentRunStatus.COMPLETED
        or agent_run.stop_reason is not AgentStopReason.FINAL_RESPONSE
    ):
        safe_error = (
            f"; error_code={agent_run.error_code}"
            if agent_run.error_code
            else ""
        )
        raise AgentDraftPreparationError(
            "agent run did not complete: "
            f"status={agent_run.status.value}; "
            f"stop_reason={agent_run.stop_reason.value}"
            f"{safe_error}",
            failure=AgentFailureObservation.from_agent_run(agent_run),
        )
    if (
        agent_run.final_response is None
        or agent_run.final_response.content is None
        or not agent_run.final_response.content.strip()
    ):
        raise AgentDraftPreparationError(
            "completed agent run did not provide final text"
        )


def _knowledge_from_actual_tool_executions(
    agent_run: AgentRunResult,
) -> KnowledgeEvidence:
    payloads = []
    for execution in agent_run.tool_executions:
        if execution.tool_name != _KNOWLEDGE_TOOL_NAME:
            raise AgentDraftPreparationError(
                "agent run contains an unsupported tool execution"
            )
        if execution.result.tool_name != execution.tool_name:
            raise AgentDraftPreparationError(
                "agent tool execution identity mismatch"
            )
        if not execution.result.success:
            code = (
                execution.result.error.code
                if execution.result.error is not None
                else "unknown"
            )
            raise AgentDraftPreparationError(
                "knowledge.search failed with safe code: " + code
            )
        if execution.result.data is None:
            raise AgentDraftPreparationError(
                "knowledge.search returned no data"
            )
        payloads.append(execution.result.data)

    try:
        return knowledge_evidence_from_search_payloads(payloads)
    except KnowledgeEvidenceBuildError as exc:
        raise AgentDraftPreparationError(
            "knowledge.search returned invalid attributable evidence"
        ) from exc
