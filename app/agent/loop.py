"""A bounded, synchronous tool-calling loop for Stage 5A.

This module deliberately owns orchestration only. Provider adapters translate
model APIs, while ToolRuntime validates and executes local tools.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Callable, Mapping

from app.providers.capabilities import require_provider_capabilities
from app.providers.errors import ProviderError
from app.providers.models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    MessageRole,
    TokenUsage,
    ToolCall,
    ToolChoiceMode,
    ToolSpec,
)
from app.providers.protocol import LLMProvider
from app.runtime.observer import RuntimeSignalObserver, observe_runtime_signal
from app.runtime.signals import (
    AgentRunTerminatedSignal,
    RuntimeAgentStatus,
    RuntimeAgentStopReason,
    ToolCallCompletedSignal,
    ToolCallStartedSignal,
)
from app.tools.models import ToolResult
from app.tools.registry import ToolRegistry
from app.tools.runtime import ToolRuntime

from .context import ContextSizer, DeterministicContextSizer


class AgentRunStatus(str, Enum):
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"


class AgentStopReason(str, Enum):
    FINAL_RESPONSE = "final_response"
    MAX_ITERATIONS = "max_iterations"
    MAX_TOOL_CALLS = "max_tool_calls"
    DUPLICATE_TOOL_CALL = "duplicate_tool_call"
    TOOL_NOT_ALLOWED = "tool_not_allowed"
    PROVIDER_ERROR = "provider_error"
    INVALID_TOOL_CONFIGURATION = "invalid_tool_configuration"
    CONTEXT_BUDGET_EXCEEDED = "context_budget_exceeded"
    TIMEOUT = "timeout"


@dataclass(frozen=True)
class AgentRunRequest:
    """Immutable input and safety budgets for one loop run."""

    messages: tuple[ChatMessage, ...]
    allowed_tools: tuple[str, ...] = ()
    max_iterations: int = 4
    max_tool_calls: int = 8
    timeout_s: float = 30.0
    max_context_tokens: int = 200_000
    # Request-level model defaults are supplied only by trusted compilation
    # profiles.  Ordinary callers keep the historical conservative values.
    temperature: float = 0.0
    max_tokens: int | None = None
    top_p: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.messages:
            raise ValueError("messages must not be empty.")
        if not all(isinstance(message, ChatMessage) for message in self.messages):
            raise ValueError("messages must contain only ChatMessage values.")
        if len(set(self.allowed_tools)) != len(self.allowed_tools):
            raise ValueError("allowed_tools must not contain duplicates.")
        if any(not name.strip() for name in self.allowed_tools):
            raise ValueError("allowed tool names must not be blank.")
        if not 1 <= self.max_iterations <= 20:
            raise ValueError("max_iterations must be between 1 and 20.")
        if not 1 <= self.max_tool_calls <= 50:
            raise ValueError("max_tool_calls must be between 1 and 50.")
        if (
            isinstance(self.timeout_s, bool)
            or not isinstance(self.timeout_s, (int, float))
            or self.timeout_s <= 0
        ):
            raise ValueError("timeout_s must be greater than zero.")
        if (
            isinstance(self.max_context_tokens, bool)
            or not isinstance(self.max_context_tokens, int)
            or self.max_context_tokens <= 0
        ):
            raise ValueError("max_context_tokens must be a positive integer.")
        if isinstance(self.temperature, bool) or not isinstance(
            self.temperature, (int, float)
        ) or not 0 <= self.temperature <= 2:
            raise ValueError("temperature must be between 0 and 2.")
        if self.max_tokens is not None and (
            isinstance(self.max_tokens, bool)
            or not isinstance(self.max_tokens, int)
            or self.max_tokens <= 0
        ):
            raise ValueError("max_tokens must be a positive integer or None.")
        if self.top_p is not None and (
            isinstance(self.top_p, bool)
            or not isinstance(self.top_p, (int, float))
            or not 0 <= self.top_p <= 1
        ):
            raise ValueError("top_p must be between 0 and 1.")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True)
class ToolExecutionRecord:
    """Trace of one model-proposed tool call and its stable result envelope."""

    tool_call_id: str
    tool_name: str
    arguments: Mapping[str, Any]
    result: ToolResult


@dataclass(frozen=True)
class AgentRunResult:
    status: AgentRunStatus
    stop_reason: AgentStopReason
    messages: tuple[ChatMessage, ...]
    provider_responses: tuple[ChatResponse, ...]
    tool_executions: tuple[ToolExecutionRecord, ...]
    usage: TokenUsage
    iterations: int
    final_response: ChatResponse | None = None
    error_code: str | None = None


class AgentLoop:
    """Run one bounded tool-calling loop against a Provider and ToolRuntime."""

    def __init__(
        self,
        *,
        provider: LLMProvider,
        tool_registry: ToolRegistry,
        tool_runtime: ToolRuntime,
        context_sizer: ContextSizer | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.provider = provider
        self.tool_registry = tool_registry
        self.tool_runtime = tool_runtime
        self._context_sizer = context_sizer or DeterministicContextSizer()
        self._clock = clock

    def run(
        self,
        request: AgentRunRequest,
        *,
        observer: RuntimeSignalObserver | None = None,
    ) -> AgentRunResult:
        result = self._run(request, observer=observer)
        _observe_agent_terminal(observer, result)
        return result

    def _run(
        self,
        request: AgentRunRequest,
        *,
        observer: RuntimeSignalObserver | None,
    ) -> AgentRunResult:
        try:
            definitions = {
                name: self.tool_registry.get(name)
                for name in request.allowed_tools
            }
        except Exception:
            return self._result(
                request,
                status=AgentRunStatus.FAILED,
                stop_reason=AgentStopReason.INVALID_TOOL_CONFIGURATION,
                error_code="tool_not_found",
            )

        messages = list(request.messages)
        provider_responses: list[ChatResponse] = []
        tool_executions: list[ToolExecutionRecord] = []
        tool_ordinal = 0
        seen_calls: set[tuple[str, str]] = set()
        total_usage = TokenUsage()
        tool_specs = tuple(_to_tool_spec(definition) for definition in definitions.values())
        deadline = self._clock() + request.timeout_s

        for iteration in range(1, request.max_iterations + 1):
            if (
                self._context_sizer.estimate_messages(tuple(messages))
                > request.max_context_tokens
            ):
                return self._result(
                    request,
                    status=AgentRunStatus.STOPPED,
                    stop_reason=AgentStopReason.CONTEXT_BUDGET_EXCEEDED,
                    messages=messages,
                    provider_responses=provider_responses,
                    tool_executions=tool_executions,
                    usage=total_usage,
                    iterations=iteration - 1,
                )

            remaining_s = deadline - self._clock()
            if remaining_s <= 0:
                return self._result(
                    request,
                    status=AgentRunStatus.STOPPED,
                    stop_reason=AgentStopReason.TIMEOUT,
                    messages=messages,
                    provider_responses=provider_responses,
                    tool_executions=tool_executions,
                    usage=total_usage,
                    iterations=iteration - 1,
                )

            chat_request = ChatRequest(
                messages=tuple(messages),
                tools=tool_specs,
                tool_choice=(
                    ToolChoiceMode.AUTO
                    if tool_specs
                    else ToolChoiceMode.NONE
                ),
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                timeout_s=remaining_s,
                top_p=request.top_p,
                metadata={
                    **request.metadata,
                    "agent_loop_iteration": iteration,
                },
            )
            try:
                require_provider_capabilities(
                    provider_name=self.provider.provider_name,
                    capabilities=self.provider.capabilities,
                    request=chat_request,
                )
                response = self.provider.chat(chat_request)
            except ProviderError as exc:
                return self._result(
                    request,
                    status=AgentRunStatus.FAILED,
                    stop_reason=AgentStopReason.PROVIDER_ERROR,
                    messages=messages,
                    provider_responses=provider_responses,
                    tool_executions=tool_executions,
                    usage=total_usage,
                    iterations=iteration - 1,
                    error_code=exc.code,
                )

            provider_responses.append(response)
            total_usage = _sum_usage(total_usage, response.usage)
            messages.append(
                ChatMessage(
                    role=MessageRole.ASSISTANT,
                    content=response.content,
                    tool_calls=response.tool_calls,
                    reasoning_content=response.reasoning_content,
                )
            )

            if self._clock() >= deadline:
                return self._result(
                    request,
                    status=AgentRunStatus.STOPPED,
                    stop_reason=AgentStopReason.TIMEOUT,
                    messages=messages,
                    provider_responses=provider_responses,
                    tool_executions=tool_executions,
                    usage=total_usage,
                    iterations=iteration,
                )

            if not response.tool_calls:
                return self._result(
                    request,
                    status=AgentRunStatus.COMPLETED,
                    stop_reason=AgentStopReason.FINAL_RESPONSE,
                    messages=messages,
                    provider_responses=provider_responses,
                    tool_executions=tool_executions,
                    usage=total_usage,
                    iterations=iteration,
                    final_response=response,
                )

            if iteration >= request.max_iterations:
                return self._result(
                    request,
                    status=AgentRunStatus.STOPPED,
                    stop_reason=AgentStopReason.MAX_ITERATIONS,
                    messages=messages,
                    provider_responses=provider_responses,
                    tool_executions=tool_executions,
                    usage=total_usage,
                    iterations=iteration,
                )

            if len(tool_executions) + len(response.tool_calls) > request.max_tool_calls:
                return self._result(
                    request,
                    status=AgentRunStatus.STOPPED,
                    stop_reason=AgentStopReason.MAX_TOOL_CALLS,
                    messages=messages,
                    provider_responses=provider_responses,
                    tool_executions=tool_executions,
                    usage=total_usage,
                    iterations=iteration,
                )

            for tool_call in response.tool_calls:
                if tool_call.name not in definitions:
                    return self._result(
                        request,
                        status=AgentRunStatus.FAILED,
                        stop_reason=AgentStopReason.TOOL_NOT_ALLOWED,
                        messages=messages,
                        provider_responses=provider_responses,
                        tool_executions=tool_executions,
                        usage=total_usage,
                        iterations=iteration,
                        error_code="tool_not_allowed",
                    )
                signature = (tool_call.name, _canonical_json(tool_call.arguments))
                if signature in seen_calls:
                    return self._result(
                        request,
                        status=AgentRunStatus.STOPPED,
                        stop_reason=AgentStopReason.DUPLICATE_TOOL_CALL,
                        messages=messages,
                        provider_responses=provider_responses,
                        tool_executions=tool_executions,
                        usage=total_usage,
                        iterations=iteration,
                    )
                seen_calls.add(signature)

            for tool_call in response.tool_calls:
                remaining_s = deadline - self._clock()
                if remaining_s <= 0:
                    return self._result(
                        request,
                        status=AgentRunStatus.STOPPED,
                        stop_reason=AgentStopReason.TIMEOUT,
                        messages=messages,
                        provider_responses=provider_responses,
                        tool_executions=tool_executions,
                        usage=total_usage,
                        iterations=iteration,
                    )
                definition = definitions[tool_call.name]
                tool_ordinal += 1
                _observe_tool_started(
                    observer,
                    tool_name=definition.name,
                    tool_version=definition.version,
                    ordinal=tool_ordinal,
                    iteration=iteration,
                )
                result = self.tool_runtime.execute(
                    tool_call.name,
                    tool_call.arguments,
                    metadata={
                        **request.metadata,
                        "agent_loop_iteration": iteration,
                        "tool_call_id": tool_call.id,
                    },
                    timeout_cap_s=remaining_s,
                )
                _observe_tool_completed(
                    observer,
                    result=result,
                    ordinal=tool_ordinal,
                )
                tool_executions.append(
                    ToolExecutionRecord(
                        tool_call_id=tool_call.id,
                        tool_name=tool_call.name,
                        arguments=tool_call.arguments,
                        result=result,
                    )
                )
                messages.append(
                    ChatMessage(
                        role=MessageRole.TOOL,
                        content=_tool_result_content(result),
                        tool_call_id=tool_call.id,
                        name=tool_call.name,
                    )
                )
                if self._clock() >= deadline:
                    return self._result(
                        request,
                        status=AgentRunStatus.STOPPED,
                        stop_reason=AgentStopReason.TIMEOUT,
                        messages=messages,
                        provider_responses=provider_responses,
                        tool_executions=tool_executions,
                        usage=total_usage,
                        iterations=iteration,
                    )

        return self._result(
            request,
            status=AgentRunStatus.STOPPED,
            stop_reason=AgentStopReason.MAX_ITERATIONS,
            messages=messages,
            provider_responses=provider_responses,
            tool_executions=tool_executions,
            usage=total_usage,
            iterations=request.max_iterations,
        )

    @staticmethod
    def _result(
        request: AgentRunRequest,
        *,
        status: AgentRunStatus,
        stop_reason: AgentStopReason,
        messages: list[ChatMessage] | None = None,
        provider_responses: list[ChatResponse] | None = None,
        tool_executions: list[ToolExecutionRecord] | None = None,
        usage: TokenUsage | None = None,
        iterations: int = 0,
        final_response: ChatResponse | None = None,
        error_code: str | None = None,
    ) -> AgentRunResult:
        return AgentRunResult(
            status=status,
            stop_reason=stop_reason,
            messages=tuple(messages or request.messages),
            provider_responses=tuple(provider_responses or ()),
            tool_executions=tuple(tool_executions or ()),
            usage=usage or TokenUsage(),
            iterations=iterations,
            final_response=final_response,
            error_code=error_code,
        )


def _to_tool_spec(definition) -> ToolSpec:
    return ToolSpec(
        name=definition.name,
        description=definition.description,
        input_schema=definition.input_schema,
    )


def _sum_usage(left: TokenUsage, right: TokenUsage) -> TokenUsage:
    return TokenUsage(
        input_tokens=left.input_tokens + right.input_tokens,
        output_tokens=left.output_tokens + right.output_tokens,
        cached_input_tokens=(
            left.cached_input_tokens + right.cached_input_tokens
        ),
    )


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def _tool_result_content(result: ToolResult) -> str:
    payload: dict[str, Any] = {
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


_SAFE_TOOL_FAILURE_CODES = frozenset(
    {
        "circuit_open",
        "fallback_failed",
        "invalid_tool_input",
        "invalid_tool_output",
        "retry_budget_exhausted",
        "tool_execution_failed",
        "tool_not_found",
    }
)


def _observe_tool_started(
    observer: RuntimeSignalObserver | None,
    *,
    tool_name: str,
    tool_version: str,
    ordinal: int,
    iteration: int,
) -> None:
    if observer is None:
        return
    observe_runtime_signal(
        observer,
        ToolCallStartedSignal(
            tool_name=tool_name,
            tool_version=tool_version,
            ordinal=ordinal,
            iteration=iteration,
        ),
    )


def _observe_tool_completed(
    observer: RuntimeSignalObserver | None,
    *,
    result: ToolResult,
    ordinal: int,
) -> None:
    if observer is None:
        return
    failure_code = None
    if not result.success:
        raw_code = result.error.code if result.error is not None else None
        failure_code = (
            raw_code
            if raw_code in _SAFE_TOOL_FAILURE_CODES
            else "tool_failed"
        )
    observe_runtime_signal(
        observer,
        ToolCallCompletedSignal(
            tool_name=result.tool_name,
            tool_version=result.tool_version,
            ordinal=ordinal,
            success=result.success,
            failure_code=failure_code,
            attempts=result.attempts,
            latency_ms=result.latency_ms,
            cached=result.cached,
            fallback_used=result.fallback_used,
        ),
    )


def _observe_agent_terminal(
    observer: RuntimeSignalObserver | None,
    result: AgentRunResult,
) -> None:
    if observer is None:
        return
    observe_runtime_signal(
        observer,
        AgentRunTerminatedSignal(
            status=RuntimeAgentStatus(result.status.value),
            stop_reason=RuntimeAgentStopReason(result.stop_reason.value),
            iterations=result.iterations,
            error_code=_safe_agent_error_code(result),
        ),
    )


def _safe_agent_error_code(result: AgentRunResult) -> str | None:
    if result.status is not AgentRunStatus.FAILED:
        return None
    return {
        AgentStopReason.PROVIDER_ERROR: "provider_failed",
        AgentStopReason.TOOL_NOT_ALLOWED: "tool_not_allowed",
        AgentStopReason.INVALID_TOOL_CONFIGURATION: "tool_not_found",
    }[result.stop_reason]
