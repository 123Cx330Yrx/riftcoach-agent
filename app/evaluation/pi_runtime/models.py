"""Strict, public-safe contracts for the isolated Pi runtime spike."""

from __future__ import annotations

import re
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from app.runtime.models import (
    CostObservation,
    RuntimeUsage,
    TokenObservation,
)


PROTOCOL_VERSION = "1.0"
PI_AGENT_CORE_VERSION = "0.84.2"
MAX_FRAME_BYTES = 256 * 1024

_SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SAFE_CODE_PATTERN = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")

NonBlankText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
SafeCode = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$"),
]


class PiContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class PiAllowedTool(PiContractModel):
    name: Literal["knowledge.search"]
    version: Literal["2.0.0"]
    description: NonBlankText
    input_schema: dict[str, Any]

    @model_validator(mode="after")
    def validate_schema(self) -> "PiAllowedTool":
        if self.input_schema.get("type") != "object":
            raise ValueError("knowledge.search input_schema must be an object")
        return self


class PiInputMessage(PiContractModel):
    role: Literal["user", "assistant"]
    content: NonBlankText


class PiScriptedUsage(PiContractModel):
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)


class PiScriptedToolCall(PiContractModel):
    id: NonBlankText
    name: str
    arguments: dict[str, Any]

    @model_validator(mode="after")
    def validate_identity(self) -> "PiScriptedToolCall":
        if not _SAFE_ID_PATTERN.fullmatch(self.id):
            raise ValueError("tool call id must be a safe identifier")
        if not _SAFE_CODE_PATTERN.fullmatch(self.name):
            raise ValueError("tool name must be a safe code")
        return self


class PiScriptedAssistantStep(PiContractModel):
    kind: Literal["assistant"] = "assistant"
    content: NonBlankText | None = None
    tool_calls: tuple[PiScriptedToolCall, ...] = ()
    usage: PiScriptedUsage | None = None

    @model_validator(mode="after")
    def validate_payload(self) -> "PiScriptedAssistantStep":
        if self.content is None and not self.tool_calls:
            raise ValueError("assistant step requires content or at least one tool call")
        ids = tuple(call.id for call in self.tool_calls)
        if len(ids) != len(set(ids)):
            raise ValueError("tool call ids must be unique within one response")
        return self


class PiScriptedFailureStep(PiContractModel):
    kind: Literal["provider_error", "provider_abort"]
    error_code: SafeCode

    @model_validator(mode="after")
    def validate_code_for_kind(self) -> "PiScriptedFailureStep":
        expected = {
            "provider_error": "scripted_provider_error",
            "provider_abort": "scripted_provider_abort",
        }[self.kind]
        if self.error_code != expected:
            raise ValueError("error_code does not match scripted failure kind")
        return self


PiScriptStep = Annotated[
    PiScriptedAssistantStep | PiScriptedFailureStep,
    Field(discriminator="kind"),
]


class PiSpikePolicy(PiContractModel):
    max_iterations: int = Field(ge=1, le=20)
    max_tool_calls: int = Field(ge=1, le=50)
    timeout_s: float = Field(gt=0, le=300)
    max_context_chars: int = Field(ge=1, le=2_000_000)


class PiSpikeRunRequest(PiContractModel):
    protocol_version: Literal["1.0"] = PROTOCOL_VERSION
    pi_agent_core_version: Literal["0.84.2"] = PI_AGENT_CORE_VERSION
    run_id: NonBlankText
    system_prompt: NonBlankText
    messages: tuple[PiInputMessage, ...] = Field(min_length=1)
    allowed_tools: tuple[PiAllowedTool, ...]
    script: tuple[PiScriptStep, ...] = Field(min_length=1)
    policy: PiSpikePolicy

    @model_validator(mode="after")
    def validate_run_contract(self) -> "PiSpikeRunRequest":
        if not _SAFE_ID_PATTERN.fullmatch(self.run_id):
            raise ValueError("run_id must be a safe identifier")
        if len(self.allowed_tools) != 1:
            raise ValueError("5F-2 requires exactly one knowledge.search tool")
        if self.allowed_tools[0].name != "knowledge.search":
            raise ValueError("5F-2 only permits knowledge.search")
        if len(self.messages) != 1 or self.messages[0].role != "user":
            raise ValueError("5F-2 requires exactly one frozen user message")
        return self


class PiToolExecutionProjection(PiContractModel):
    tool_name: Literal["knowledge.search"]
    tool_version: Literal["2.0.0"]
    ordinal: int = Field(ge=1)
    success: bool
    failure_code: SafeCode | None = None
    attempts: int = Field(ge=0)
    latency_ms: float = Field(ge=0)
    cached: bool
    fallback_used: bool

    @model_validator(mode="after")
    def validate_failure(self) -> "PiToolExecutionProjection":
        if self.success and self.failure_code is not None:
            raise ValueError("successful tool execution cannot have a failure_code")
        if not self.success and self.failure_code is None:
            raise ValueError("failed tool execution requires a failure_code")
        return self


class PiSafeEvent(PiContractModel):
    event_type: Literal[
        "provider_started",
        "provider_completed",
        "tool_started",
        "tool_completed",
        "agent_completed",
    ]
    ordinal: int = Field(ge=1)
    iteration: int = Field(ge=0)
    success: bool | None = None
    tool_name: Literal["knowledge.search"] | None = None
    tool_version: Literal["2.0.0"] | None = None
    failure_code: SafeCode | None = None
    token_observation: TokenObservation | None = None
    finish_reason: Literal["stop", "tool_calls"] | None = None
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_provider_usage(self) -> "PiSafeEvent":
        token_values = (self.input_tokens, self.output_tokens)
        if self.event_type in {"provider_completed", "tool_completed"}:
            if self.success is None:
                raise ValueError("completed events require a success value")
        if self.event_type != "provider_completed":
            if self.finish_reason is not None or any(
                value is not None for value in token_values
            ):
                raise ValueError(
                    "only provider_completed events may carry response metadata"
                )
            return self
        if self.success is True and self.finish_reason is None:
            raise ValueError(
                "successful provider event requires a finish_reason"
            )
        if self.success is not True and self.finish_reason is not None:
            raise ValueError(
                "failed provider event cannot carry a finish_reason"
            )
        if self.token_observation is TokenObservation.COMPLETE:
            if any(value is None for value in token_values):
                raise ValueError(
                    "complete provider event requires both token values"
                )
        elif any(value is not None for value in token_values):
            raise ValueError(
                "non-complete provider event cannot carry token values"
            )
        return self


PiSpikeStatus = Literal["completed", "stopped", "failed"]
PiSpikeStopReason = Literal[
    "final_response",
    "max_iterations",
    "max_tool_calls",
    "duplicate_tool_call",
    "tool_not_allowed",
    "invalid_tool_input",
    "tool_failed",
    "provider_error",
    "provider_aborted",
    "context_budget_exceeded",
    "timeout",
    "protocol_error",
    "process_error",
]


class PiSpikeRunResult(PiContractModel):
    protocol_version: Literal["1.0"] = PROTOCOL_VERSION
    pi_agent_core_version: Literal["0.84.2"] = PI_AGENT_CORE_VERSION
    run_id: NonBlankText
    status: PiSpikeStatus
    stop_reason: PiSpikeStopReason
    iterations: int = Field(ge=0, le=20)
    final_text: NonBlankText | None = None
    error_code: SafeCode | None = None
    usage: RuntimeUsage
    safe_events: tuple[PiSafeEvent, ...] = ()
    tool_executions: tuple[PiToolExecutionProjection, ...] = ()
    external_provider_calls: Literal[0] = 0

    @model_validator(mode="after")
    def validate_result(self) -> "PiSpikeRunResult":
        if not _SAFE_ID_PATTERN.fullmatch(self.run_id):
            raise ValueError("run_id must be a safe identifier")
        if self.status == "completed":
            if (
                self.stop_reason != "final_response"
                or self.final_text is None
                or self.error_code is not None
            ):
                raise ValueError(
                    "completed run requires final_response, final_text, and no error"
                )
        elif self.final_text is not None:
            raise ValueError("only completed runs may expose final_text")
        if self.status == "failed" and self.error_code is None:
            raise ValueError("failed run requires an error_code")
        if self.usage.tool_calls != len(self.tool_executions):
            raise ValueError("usage tool_calls must match tool execution projections")
        return self


def build_runtime_usage(
    *,
    provider_calls_attempted: int,
    response_usages: tuple[PiScriptedUsage | None, ...],
    tool_executions: tuple[PiToolExecutionProjection, ...],
) -> RuntimeUsage:
    """Map scripted observations without turning missing Usage into zero."""

    if isinstance(provider_calls_attempted, bool) or provider_calls_attempted < 0:
        raise ValueError("provider_calls_attempted must be a non-negative integer")
    if len(response_usages) > provider_calls_attempted:
        raise ValueError("response usages cannot outnumber attempts")

    observed = tuple(usage for usage in response_usages if usage is not None)
    observed_input = sum(usage.input_tokens for usage in observed)
    observed_output = sum(usage.output_tokens for usage in observed)

    if provider_calls_attempted == 0:
        observation = TokenObservation.NOT_APPLICABLE
        input_tokens: int | None = 0
        output_tokens: int | None = 0
    elif len(observed) == provider_calls_attempted:
        observation = TokenObservation.COMPLETE
        input_tokens = observed_input
        output_tokens = observed_output
    elif observed:
        observation = TokenObservation.PARTIAL
        input_tokens = None
        output_tokens = None
    else:
        observation = TokenObservation.UNKNOWN
        input_tokens = None
        output_tokens = None

    return RuntimeUsage(
        provider_calls_attempted=provider_calls_attempted,
        provider_responses_observed=len(observed),
        observed_input_tokens=observed_input,
        observed_output_tokens=observed_output,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        token_observation=observation,
        tool_calls=len(tool_executions),
        tool_attempts=sum(item.attempts for item in tool_executions),
        tool_latency_ms=sum(item.latency_ms for item in tool_executions),
        cost=None,
        currency=None,
        pricing_profile_id=None,
        pricing_profile_version=None,
        cost_observation=CostObservation.NOT_CONFIGURED,
    )
