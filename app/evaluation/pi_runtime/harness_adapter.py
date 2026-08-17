"""Evaluation-only Pi adapter for the existing Skill/Harness seam."""

from __future__ import annotations

import json
from collections.abc import Sequence

from app.agent.compiler import AgentRunCompileError, AgentRunCompiler
from app.agent.context import ContextBundle
from app.agent.draft import (
    AgentDraftPreparationError,
    AgentDraftPreparationResult,
    AgentFailureObservation,
)
from app.agent.loop import (
    AgentRunResult,
    AgentRunStatus,
    AgentStopReason,
    ToolExecutionRecord,
)
from app.harness.knowledge import (
    KnowledgeEvidenceBuildError,
    knowledge_evidence_from_search_payloads,
)
from app.harness.steps import CoachDraft
from app.providers.models import (
    ChatMessage,
    ChatResponse,
    MessageRole,
    TokenUsage,
    ToolCall,
)
from app.runtime.models import TokenObservation
from app.runtime.observer import (
    RuntimeObservationError,
    RuntimeSignalObserver,
    observe_runtime_signal,
)
from app.skills.execution import ValidatedSkillExecution

from .controller import PiSidecarController, PiSidecarExecution
from .models import (
    PiAllowedTool,
    PiInputMessage,
    PiScriptStep,
    PiScriptedAssistantStep,
    PiSpikePolicy,
    PiSpikeRunRequest,
)
from .signal_projector import PiRuntimeSignalProjector, PiTraceParityError


class PiSkillDraftPreparer:
    """Run Pi as an unpublished draft producer under existing contracts."""

    context_policy_parity = "approximate_char_guard"

    def __init__(
        self,
        *,
        controller: PiSidecarController,
        script: Sequence[PiScriptStep],
        max_context_chars: int,
        observer: RuntimeSignalObserver | None = None,
        signal_projector: PiRuntimeSignalProjector | None = None,
    ) -> None:
        if not isinstance(controller, PiSidecarController):
            raise TypeError("controller must be a PiSidecarController")
        normalized_script = tuple(script)
        if not normalized_script:
            raise ValueError("script must not be empty")
        if isinstance(max_context_chars, bool) or not isinstance(
            max_context_chars, int
        ):
            raise TypeError("max_context_chars must be an integer")
        if not 1 <= max_context_chars <= 2_000_000:
            raise ValueError("max_context_chars must be between 1 and 2000000")
        self._controller = controller
        self._script = normalized_script
        self._max_context_chars = max_context_chars
        self._observer = observer
        self._projector = signal_projector or PiRuntimeSignalProjector()
        self._compiler = AgentRunCompiler(controller.tool_registry)
        self.last_execution: PiSidecarExecution | None = None
        self.last_request: PiSpikeRunRequest | None = None

    def prepare(
        self,
        execution: ValidatedSkillExecution,
        context: ContextBundle,
    ) -> AgentDraftPreparationResult:
        try:
            agent_request = self._compiler.compile(execution, context)
        except AgentRunCompileError as exc:
            raise AgentDraftPreparationError(
                "Pi request compilation failed"
            ) from exc
        if len(agent_request.messages) != 2:
            raise AgentDraftPreparationError(
                "Pi evaluation requires canonical system and user messages"
            )
        system_message, user_message = agent_request.messages
        if system_message.role.value != "system" or user_message.role.value != "user":
            raise AgentDraftPreparationError(
                "Pi evaluation requires canonical system and user messages"
            )
        if (
            system_message.content is None
            or user_message.content is None
            or agent_request.allowed_tools != ("knowledge.search",)
        ):
            raise AgentDraftPreparationError(
                "Pi evaluation requires one knowledge.search Tool"
            )
        definition = self._controller.tool_registry.get("knowledge.search")
        pi_request = PiSpikeRunRequest(
            run_id=execution.run_id,
            system_prompt=system_message.content,
            messages=(PiInputMessage(role="user", content=user_message.content),),
            allowed_tools=(
                PiAllowedTool(
                    name="knowledge.search",
                    version="2.0.0",
                    description=definition.description,
                    input_schema=dict(definition.input_schema),
                ),
            ),
            script=self._script,
            policy=PiSpikePolicy(
                max_iterations=agent_request.max_iterations,
                max_tool_calls=agent_request.max_tool_calls,
                timeout_s=agent_request.timeout_s,
                max_context_chars=self._max_context_chars,
            ),
        )
        self.last_request = pi_request
        detailed = self._controller.run_with_tool_records(pi_request)
        self.last_execution = detailed

        if self._observer is not None:
            try:
                signals = self._projector.project(detailed.result)
            except PiTraceParityError as exc:
                raise RuntimeObservationError(
                    "Pi result cannot be projected into Runtime Trace"
                ) from exc
            for signal in signals:
                observe_runtime_signal(self._observer, signal)

        if detailed.result.status != "completed":
            raise AgentDraftPreparationError(
                "Pi runtime did not complete the unpublished draft",
                failure=_failure_observation(detailed),
            )
        if detailed.result.final_text is None:
            raise AgentDraftPreparationError(
                "completed Pi runtime did not provide final text"
            )

        knowledge = _knowledge_from_records(detailed.tool_records)
        agent_run = _agent_run_from_pi(
            request=agent_request,
            detailed=detailed,
            script=self._script,
        )
        return AgentDraftPreparationResult(
            draft=CoachDraft(report=detailed.result.final_text),
            knowledge=knowledge,
            agent_run=agent_run,
        )


def _knowledge_from_records(records: tuple[ToolExecutionRecord, ...]):
    payloads = []
    for record in records:
        if record.tool_name != "knowledge.search":
            raise AgentDraftPreparationError(
                "Pi detailed result contains an unsupported Tool"
            )
        if not record.result.success or record.result.data is None:
            raise AgentDraftPreparationError(
                "Pi knowledge Tool did not return attributable data"
            )
        payloads.append(record.result.data)
    try:
        return knowledge_evidence_from_search_payloads(payloads)
    except KnowledgeEvidenceBuildError as exc:
        raise AgentDraftPreparationError(
            "Pi knowledge Tool returned invalid attributable evidence"
        ) from exc


def _agent_run_from_pi(*, request, detailed, script) -> AgentRunResult:
    if detailed.result.usage.token_observation is not TokenObservation.COMPLETE:
        raise AgentDraftPreparationError(
            "completed Pi result has incomplete Usage"
        )
    responses: list[ChatResponse] = []
    messages = list(request.messages)
    records_by_id = {
        record.tool_call_id: record for record in detailed.tool_records
    }
    for step in tuple(script)[: detailed.result.iterations]:
        if not isinstance(step, PiScriptedAssistantStep):
            raise AgentDraftPreparationError(
                "completed Pi result contains a non-assistant script step"
            )
        usage = step.usage or PiScriptedUsage(input_tokens=0, output_tokens=0)
        response = ChatResponse(
            content=step.content,
            model="riftcoach-scripted-model",
            provider="riftcoach-scripted",
            usage=TokenUsage(
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
            ),
            tool_calls=tuple(
                ToolCall(
                    id=call.id,
                    name=call.name,
                    arguments=dict(call.arguments),
                )
                for call in step.tool_calls
            ),
            finish_reason="tool_calls" if step.tool_calls else "stop",
        )
        responses.append(response)
        messages.append(
            ChatMessage(
                role=MessageRole.ASSISTANT,
                content=response.content,
                tool_calls=response.tool_calls,
            )
        )
        for call in response.tool_calls:
            record = records_by_id.get(call.id)
            if record is None:
                raise AgentDraftPreparationError(
                    "Pi transcript is missing a Tool execution"
                )
            messages.append(
                ChatMessage(
                    role=MessageRole.TOOL,
                    content=_tool_result_content(record),
                    tool_call_id=call.id,
                    name=call.name,
                )
            )
    transcript_tool_ids = {
        call.id for response in responses for call in response.tool_calls
    }
    if transcript_tool_ids != set(records_by_id):
        raise AgentDraftPreparationError(
            "Pi transcript and Tool execution identities do not match"
        )
    if not responses or responses[-1].tool_calls:
        raise AgentDraftPreparationError(
            "completed Pi result has no final response"
        )
    observed = detailed.result.usage
    return AgentRunResult(
        status=AgentRunStatus.COMPLETED,
        stop_reason=AgentStopReason.FINAL_RESPONSE,
        messages=tuple(messages),
        provider_responses=tuple(responses),
        tool_executions=detailed.tool_records,
        usage=TokenUsage(
            input_tokens=observed.observed_input_tokens,
            output_tokens=observed.observed_output_tokens,
        ),
        iterations=detailed.result.iterations,
        final_response=responses[-1],
    )


def _tool_result_content(record: ToolExecutionRecord) -> str:
    result = record.result
    payload = {
        "success": result.success,
        "tool_name": result.tool_name,
        "tool_version": result.tool_version,
        "data": result.data,
    }
    if result.error is not None:
        payload["error"] = {
            "code": result.error.code,
            "message": result.error.message,
            "retryable": result.error.retryable,
        }
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def _failure_observation(
    detailed: PiSidecarExecution,
) -> AgentFailureObservation | None:
    result = detailed.result
    stopped = {
        "max_iterations": AgentStopReason.MAX_ITERATIONS,
        "max_tool_calls": AgentStopReason.MAX_TOOL_CALLS,
        "duplicate_tool_call": AgentStopReason.DUPLICATE_TOOL_CALL,
        "context_budget_exceeded": AgentStopReason.CONTEXT_BUDGET_EXCEEDED,
        "timeout": AgentStopReason.TIMEOUT,
    }
    if result.status == "stopped" and result.stop_reason in stopped:
        return AgentFailureObservation(
            status=AgentRunStatus.STOPPED,
            stop_reason=stopped[result.stop_reason],
        )
    if result.status == "failed" and result.stop_reason == "provider_error":
        return AgentFailureObservation(
            status=AgentRunStatus.FAILED,
            stop_reason=AgentStopReason.PROVIDER_ERROR,
            error_code=result.error_code or "provider_failed",
        )
    if result.status == "failed" and result.stop_reason == "tool_not_allowed":
        return AgentFailureObservation(
            status=AgentRunStatus.FAILED,
            stop_reason=AgentStopReason.TOOL_NOT_ALLOWED,
            error_code="tool_not_allowed",
        )
    return None


__all__ = ["PiSkillDraftPreparer"]
