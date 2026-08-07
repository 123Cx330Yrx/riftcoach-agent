"""Evidence-aware draft preparation for one validated Skill execution."""

from __future__ import annotations

from dataclasses import dataclass

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


_KNOWLEDGE_TOOL_NAME = "knowledge.search"


class AgentDraftPreparationError(RuntimeError):
    """Raised when an Agent run cannot safely become a Harness draft input."""


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

    def __init__(self, agent_loop: AgentLoop) -> None:
        if not callable(getattr(agent_loop, "run", None)):
            raise TypeError("agent_loop must provide run()")
        self._agent_loop = agent_loop
        self._compiler = AgentRunCompiler(agent_loop.tool_registry)

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
            agent_run = self._agent_loop.run(request)
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
            f"{safe_error}"
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
