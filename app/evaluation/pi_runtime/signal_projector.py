"""Strict body-free projection from Pi observations to Runtime signals."""

from __future__ import annotations

from app.runtime.models import TokenObservation
from app.runtime.signals import (
    AgentRunTerminatedSignal,
    ProviderCallCompletedSignal,
    ProviderCallFailedSignal,
    ProviderCallStartedSignal,
    RuntimeAgentStatus,
    RuntimeAgentStopReason,
    RuntimeFinishReason,
    RuntimeProviderPhase,
    RuntimeSignal,
    ToolCallCompletedSignal,
    ToolCallStartedSignal,
)

from .models import PiSafeEvent, PiSpikeRunResult, PiToolExecutionProjection


class PiTraceParityError(ValueError):
    """A Pi observation cannot be represented without changing its meaning."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class PiRuntimeSignalProjector:
    """Project only the subset exactly expressible by Runtime Signal V1.1."""

    provider_id = "riftcoach-scripted"
    provider_model = "riftcoach-scripted-model"

    def project(self, result: PiSpikeRunResult) -> tuple[RuntimeSignal, ...]:
        if not isinstance(result, PiSpikeRunResult):
            raise TypeError("result must be a PiSpikeRunResult")
        signals: list[RuntimeSignal] = []
        agent_events: list[PiSafeEvent] = []
        tool_projections = {
            projection.ordinal: projection
            for projection in result.tool_executions
        }
        for event in result.safe_events:
            signal = self._project_event(event, tool_projections)
            if event.event_type == "agent_completed":
                agent_events.append(event)
                continue
            if signal is not None:
                signals.append(signal)
        if result.status == "completed" and len(agent_events) != 1:
            raise PiTraceParityError("agent_event_mismatch")
        if agent_events:
            if len(agent_events) != 1:
                raise PiTraceParityError("agent_event_mismatch")
            agent_event = agent_events[0]
            if (
                agent_event.iteration != result.iterations
                or agent_event.success is not (result.status == "completed")
            ):
                raise PiTraceParityError("agent_event_mismatch")
        signals.append(self._project_terminal(result))
        return tuple(signals)

    def _project_event(
        self,
        event: PiSafeEvent,
        tool_projections: dict[int, PiToolExecutionProjection],
    ) -> RuntimeSignal | None:
        if event.event_type in {"provider_started", "tool_started"}:
            if event.iteration < 1:
                raise PiTraceParityError("invalid_iteration")
        if event.event_type == "provider_started":
            return ProviderCallStartedSignal(
                provider_id=self.provider_id,
                model=self.provider_model,
                ordinal=event.ordinal,
                phase=RuntimeProviderPhase.AGENT,
                iteration=event.iteration,
            )
        if event.event_type == "provider_completed":
            if event.success is False:
                return ProviderCallFailedSignal(
                    provider_id=self.provider_id,
                    model=self.provider_model,
                    ordinal=event.ordinal,
                    failure_code="provider_failed",
                    provider_error_code=event.failure_code,
                )
            if (
                event.token_observation is not TokenObservation.COMPLETE
                or event.input_tokens is None
                or event.output_tokens is None
                or event.finish_reason is None
            ):
                raise PiTraceParityError("missing_per_call_usage")
            return ProviderCallCompletedSignal(
                provider_id=self.provider_id,
                model=self.provider_model,
                ordinal=event.ordinal,
                finish_reason=RuntimeFinishReason(event.finish_reason),
                input_tokens=event.input_tokens,
                output_tokens=event.output_tokens,
            )
        if event.event_type == "tool_started":
            if event.tool_name is None or event.tool_version is None:
                raise PiTraceParityError("invalid_tool_event")
            return ToolCallStartedSignal(
                tool_name=event.tool_name,
                tool_version=event.tool_version,
                ordinal=event.ordinal,
                iteration=event.iteration,
            )
        if event.event_type == "tool_completed":
            if (
                event.tool_name is None
                or event.tool_version is None
                or event.success is None
            ):
                raise PiTraceParityError("invalid_tool_event")
            projection = tool_projections.get(event.ordinal)
            if projection is None:
                raise PiTraceParityError("tool_projection_missing")
            if (
                projection.tool_name != event.tool_name
                or projection.tool_version != event.tool_version
                or projection.success is not event.success
                or projection.failure_code != event.failure_code
            ):
                raise PiTraceParityError("tool_projection_mismatch")
            return ToolCallCompletedSignal(
                tool_name=projection.tool_name,
                tool_version=projection.tool_version,
                ordinal=projection.ordinal,
                success=projection.success,
                failure_code=projection.failure_code,
                attempts=projection.attempts,
                latency_ms=projection.latency_ms,
                cached=projection.cached,
                fallback_used=projection.fallback_used,
            )
        if event.event_type == "agent_completed":
            return None
        raise PiTraceParityError("unsupported_event")

    def _project_terminal(
        self,
        result: PiSpikeRunResult,
    ) -> AgentRunTerminatedSignal:
        try:
            stop_reason = RuntimeAgentStopReason(result.stop_reason)
        except ValueError:
            raise PiTraceParityError("unsupported_agent_terminal") from None
        if result.status == "completed":
            status = RuntimeAgentStatus.COMPLETED
            error_code = None
        elif result.status == "stopped":
            status = RuntimeAgentStatus.STOPPED
            error_code = None
        else:
            status = RuntimeAgentStatus.FAILED
            if stop_reason is RuntimeAgentStopReason.PROVIDER_ERROR:
                error_code = "provider_failed"
            elif stop_reason is RuntimeAgentStopReason.TOOL_NOT_ALLOWED:
                error_code = "tool_not_allowed"
            else:
                raise PiTraceParityError("unsupported_agent_terminal")
        try:
            return AgentRunTerminatedSignal(
                status=status,
                stop_reason=stop_reason,
                iterations=result.iterations,
                error_code=error_code,
            )
        except ValueError:
            raise PiTraceParityError("unsupported_agent_terminal") from None


__all__ = ["PiRuntimeSignalProjector", "PiTraceParityError"]
