"""Strict public contracts for the framework-neutral AgentRuntime V1."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import PurePosixPath
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.harness.run_ids import normalize_run_id
from app.skills.execution import SkillExecutionRequest

from .lifecycle import RuntimeHarnessLifecycleV11
from .signals import (
    AgentRunTerminatedSignal,
    ContextBuiltSignal,
    EvaluationCompletedSignal,
    ExecutionValidatedSignal,
    HarnessTransitionedSignal,
    ProviderCallCompletedSignal,
    ProviderCallFailedSignal,
    ProviderCallStartedSignal,
    PublicationDecidedSignal,
    RunCompletedSignal,
    RunFailedSignal,
    RunStartedSignal,
    RuntimeFailureStage,
    RuntimeFinishReason,
    RuntimeProviderPhase,
    RuntimePublicationStatus,
    RuntimeSignal,
    TERMINAL_SIGNAL_TYPES,
    ToolCallCompletedSignal,
    ToolCallStartedSignal,
)


_SAFE_CODE_PATTERN = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
_SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
_SCHEMA_VERSION_PATTERN = re.compile(r"^\d+\.\d+(?:\.\d+)?$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class RuntimeStatus(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"


class TokenObservation(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class CostObservation(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    UNKNOWN = "unknown"
    NOT_CONFIGURED = "not_configured"


class RuntimeContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _validate_semver(value: str, *, field_name: str) -> str:
    if not _SEMVER_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must use MAJOR.MINOR.PATCH")
    return value


def _validate_safe_code(value: str, *, field_name: str) -> str:
    if not _SAFE_CODE_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be a lowercase safe code")
    return value


def _validate_schema_version(value: str, *, field_name: str) -> str:
    if not _SCHEMA_VERSION_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be a numeric schema version")
    return value


def _validate_sha256(value: str) -> str:
    if not _SHA256_PATTERN.fullmatch(value):
        raise ValueError("sha256 must be a lowercase SHA-256 hex digest")
    return value


def _validate_utc(value: datetime, *, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError(f"{field_name} must be timezone-aware UTC")
    return value


class RuntimePolicySnapshot(RuntimeContractModel):
    policy_version: str
    event_budget: int = Field(default=256, ge=2, le=1024)
    max_iterations: int = Field(ge=1, le=20)
    max_tool_calls: int = Field(ge=1, le=50)
    timeout_s: float = Field(gt=0, le=300)
    max_context_tokens: int = Field(ge=1000, le=200_000)
    publish_score_threshold: int = Field(ge=0, le=100)
    max_revisions: int = Field(ge=0, le=3)
    allow_deterministic_fallback: bool

    @field_validator("policy_version")
    @classmethod
    def validate_policy_version(cls, value: str) -> str:
        return _validate_semver(value, field_name="policy_version")


class RuntimeIdentitySnapshot(RuntimeContractModel):
    skill_name: str
    skill_version: str
    context_contract_version: str
    prompt_profile_id: str
    prompt_profile_version: str
    provider_id: str
    provider_model: str
    harness_version: str

    @field_validator(
        "skill_name",
        "prompt_profile_id",
        "provider_id",
        "provider_model",
    )
    @classmethod
    def validate_identity(cls, value: str, info) -> str:
        if not _SAFE_ID_PATTERN.fullmatch(value):
            raise ValueError(f"{info.field_name} must be a safe identifier")
        return value

    @field_validator(
        "skill_version",
        "context_contract_version",
        "prompt_profile_version",
        "harness_version",
    )
    @classmethod
    def validate_versions(cls, value: str, info) -> str:
        return _validate_semver(value, field_name=info.field_name)


class RuntimePricingProfile(RuntimeContractModel):
    profile_id: str
    version: str
    provider_id: str
    model: str
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    input_cost_per_million: Decimal = Field(ge=0)
    output_cost_per_million: Decimal = Field(ge=0)

    @field_validator("profile_id", "provider_id", "model")
    @classmethod
    def validate_ids(cls, value: str, info) -> str:
        if not _SAFE_ID_PATTERN.fullmatch(value):
            raise ValueError(f"{info.field_name} must be a safe identifier")
        return value

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        return _validate_semver(value, field_name="version")


class RuntimeUsage(RuntimeContractModel):
    provider_calls_attempted: int = Field(ge=0)
    provider_responses_observed: int = Field(ge=0)
    observed_input_tokens: int = Field(ge=0)
    observed_output_tokens: int = Field(ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    token_observation: TokenObservation
    tool_calls: int = Field(ge=0)
    tool_attempts: int = Field(ge=0)
    tool_latency_ms: float = Field(ge=0)
    cost: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    pricing_profile_id: str | None = None
    pricing_profile_version: str | None = None
    cost_observation: CostObservation

    @field_validator("pricing_profile_id")
    @classmethod
    def validate_pricing_profile_id(cls, value: str | None) -> str | None:
        if value is not None and not _SAFE_ID_PATTERN.fullmatch(value):
            raise ValueError("pricing_profile_id must be a safe identifier")
        return value

    @field_validator("pricing_profile_version")
    @classmethod
    def validate_pricing_profile_version(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None
        return _validate_semver(value, field_name="pricing_profile_version")

    @model_validator(mode="after")
    def validate_completeness(self) -> "RuntimeUsage":
        if self.provider_responses_observed > self.provider_calls_attempted:
            raise ValueError("provider response count exceeds attempted calls")

        if self.token_observation is TokenObservation.COMPLETE:
            if (
                self.provider_calls_attempted == 0
                or self.provider_responses_observed
                != self.provider_calls_attempted
            ):
                raise ValueError(
                    "complete token usage requires every provider response"
                )
            if self.input_tokens is None or self.output_tokens is None:
                raise ValueError("complete token observation requires token totals")
            if (
                self.input_tokens != self.observed_input_tokens
                or self.output_tokens != self.observed_output_tokens
            ):
                raise ValueError(
                    "complete token totals must match observed token totals"
                )
        elif self.token_observation is TokenObservation.PARTIAL:
            if not (
                0
                < self.provider_responses_observed
                < self.provider_calls_attempted
            ):
                raise ValueError(
                    "partial token usage requires some missing responses"
                )
            if self.input_tokens is not None or self.output_tokens is not None:
                raise ValueError("partial token observation requires null totals")
        elif self.token_observation is TokenObservation.UNKNOWN:
            if (
                self.provider_calls_attempted == 0
                or self.provider_responses_observed != 0
                or self.observed_input_tokens != 0
                or self.observed_output_tokens != 0
            ):
                raise ValueError(
                    "unknown token usage requires calls with no observed response"
                )
            if self.input_tokens is not None or self.output_tokens is not None:
                raise ValueError("unknown token observation requires null totals")
        else:
            if self.provider_calls_attempted != 0:
                raise ValueError("not_applicable token usage requires no provider calls")
            if (
                self.provider_responses_observed != 0
                or self.observed_input_tokens != 0
                or self.observed_output_tokens != 0
                or self.input_tokens != 0
                or self.output_tokens != 0
            ):
                raise ValueError("not_applicable token totals must be zero")

        pricing_identity = (
            self.pricing_profile_id,
            self.pricing_profile_version,
        )
        if (pricing_identity[0] is None) != (pricing_identity[1] is None):
            raise ValueError("pricing profile identity must be all-or-none")
        if self.cost_observation is CostObservation.NOT_CONFIGURED:
            if any(value is not None for value in (*pricing_identity, self.currency, self.cost)):
                raise ValueError("unconfigured cost must not claim pricing or currency")
        else:
            if any(value is None for value in (*pricing_identity, self.currency)):
                raise ValueError("observed cost requires pricing identity and currency")
            if self.cost_observation is CostObservation.COMPLETE:
                if self.cost is None:
                    raise ValueError("complete cost observation requires a cost")
            elif self.cost is not None:
                raise ValueError("incomplete cost observation requires null cost")

            expected_cost_observation = {
                TokenObservation.COMPLETE: CostObservation.COMPLETE,
                TokenObservation.NOT_APPLICABLE: CostObservation.COMPLETE,
                TokenObservation.PARTIAL: CostObservation.PARTIAL,
                TokenObservation.UNKNOWN: CostObservation.UNKNOWN,
            }[self.token_observation]
            if self.cost_observation is not expected_cost_observation:
                raise ValueError(
                    "cost observation must match token completeness"
                )
        return self


class RuntimeArtifactReference(RuntimeContractModel):
    kind: str
    schema_version: str
    relative_path: str
    sha256: str
    producer: str

    @field_validator("kind", "producer")
    @classmethod
    def validate_codes(cls, value: str, info) -> str:
        return _validate_safe_code(value, field_name=info.field_name)

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value: str) -> str:
        return _validate_schema_version(value, field_name="schema_version")

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if (
            not value
            or "\\" in value
            or path.is_absolute()
            or value == "."
            or any(part in {"", ".", ".."} for part in path.parts)
            or re.match(r"^[A-Za-z]:", value)
        ):
            raise ValueError("relative_path must be a safe POSIX relative path")
        return path.as_posix()

    @field_validator("sha256")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        return _validate_sha256(value)


class RuntimeEvent(RuntimeContractModel):
    event_schema_version: Literal["1.0", "1.1"] = "1.1"
    run_id: str
    sequence: int = Field(ge=1)
    occurred_at_utc: datetime
    elapsed_ms: int = Field(ge=0)
    signal: RuntimeSignal

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        return normalize_run_id(value)

    @field_validator("occurred_at_utc")
    @classmethod
    def validate_occurred_at(cls, value: datetime) -> datetime:
        return _validate_utc(value, field_name="occurred_at_utc")

    @model_validator(mode="after")
    def validate_signal_for_event_schema(self) -> "RuntimeEvent":
        if self.event_schema_version == "1.1":
            signal = self.signal
            if isinstance(signal, ProviderCallCompletedSignal) and (
                signal.finish_reason is not None
                and not isinstance(signal.finish_reason, RuntimeFinishReason)
            ):
                raise ValueError(
                    "event_schema_version 1.1 requires a bounded finish_reason"
                )
            if isinstance(signal, ToolCallCompletedSignal):
                if signal.success and signal.failure_code is not None:
                    raise ValueError(
                        "successful tool completion requires null failure_code"
                    )
                if not signal.success and signal.failure_code is None:
                    raise ValueError(
                        "failed tool completion requires failure_code"
                    )
            if isinstance(signal, PublicationDecidedSignal):
                if signal.publication_status is RuntimePublicationStatus.REJECTED:
                    if signal.artifact_sha256s:
                        raise ValueError(
                            "rejected publication must not reference a report"
                        )
                elif len(signal.artifact_sha256s) != 1:
                    raise ValueError(
                        "published or degraded publication requires one report digest"
                    )
            return self
        signal = self.signal
        if isinstance(signal, AgentRunTerminatedSignal):
            raise ValueError("event_schema_version 1.0 has no Agent terminal")
        if isinstance(signal, ContextBuiltSignal) and any(
            ":" in value for value in signal.omitted_item_ids
        ):
            raise ValueError("event_schema_version 1.0 has no section-ID hierarchy")
        if isinstance(signal, ProviderCallStartedSignal) and (
            signal.phase is not RuntimeProviderPhase.AGENT
            or signal.iteration is None
        ):
            raise ValueError("event_schema_version 1.0 has no Provider phase")
        if isinstance(signal, ProviderCallCompletedSignal) and (
            signal.finish_reason is None
        ):
            raise ValueError("event_schema_version 1.0 requires finish_reason")
        if isinstance(signal, EvaluationCompletedSignal) and signal.attempt == 0:
            raise ValueError("event_schema_version 1.0 uses one-based Evaluation")
        if isinstance(signal, ToolCallCompletedSignal) and (
            signal.failure_code is not None
        ):
            raise ValueError("event_schema_version 1.0 has no Tool failure_code")
        if isinstance(signal, RunFailedSignal) and (
            signal.failure_stage is RuntimeFailureStage.HARNESS
        ):
            raise ValueError("event_schema_version 1.0 has no Harness failure stage")
        return self


class RuntimeRunRequest(RuntimeContractModel):
    execution_request: SkillExecutionRequest
    policy: RuntimePolicySnapshot

    @property
    def run_id(self) -> str:
        return self.execution_request.run_id


class RuntimeTraceReference(RuntimeContractModel):
    run_id: str
    trace_schema_version: Literal["1.0", "1.1"] = "1.1"
    relative_path: Literal["runtime_trace.json"] = "runtime_trace.json"
    sha256: str

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        return normalize_run_id(value)

    @field_validator("sha256")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        return _validate_sha256(value)


class RuntimeTrace(RuntimeContractModel):
    trace_schema_version: Literal["1.0", "1.1"] = "1.1"
    runtime_version: Literal["1.0"] = "1.0"
    event_schema_version: Literal["1.0", "1.1"] = "1.1"
    run_id: str
    identity: RuntimeIdentitySnapshot
    policy: RuntimePolicySnapshot
    events: tuple[RuntimeEvent, ...] = Field(min_length=2)
    usage: RuntimeUsage
    runtime_status: RuntimeStatus
    publication_status: RuntimePublicationStatus | None = None
    terminal_reason: str
    artifacts: tuple[RuntimeArtifactReference, ...] = ()
    started_at_utc: datetime
    completed_at_utc: datetime
    elapsed_ms: int = Field(ge=0)

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        return normalize_run_id(value)

    @field_validator("terminal_reason")
    @classmethod
    def validate_terminal_reason(cls, value: str) -> str:
        return _validate_safe_code(value, field_name="terminal_reason")

    @field_validator("started_at_utc", "completed_at_utc")
    @classmethod
    def validate_timestamps(cls, value: datetime, info) -> datetime:
        return _validate_utc(value, field_name=info.field_name)

    @model_validator(mode="after")
    def validate_trace_invariants(self) -> "RuntimeTrace":
        if self.trace_schema_version != self.event_schema_version:
            raise ValueError("Trace and Event schema versions must match")
        if len(self.events) > self.policy.event_budget:
            raise ValueError("events exceed the runtime event budget")
        if any(event.run_id != self.run_id for event in self.events):
            raise ValueError("every event run_id must match the trace run_id")
        if any(
            event.event_schema_version != self.event_schema_version
            for event in self.events
        ):
            raise ValueError(
                "every event_schema_version must match the Trace declaration"
            )

        sequences = tuple(event.sequence for event in self.events)
        if sequences != tuple(range(1, len(self.events) + 1)):
            raise ValueError("event sequence must be contiguous from 1")
        if any(
            later.elapsed_ms < earlier.elapsed_ms
            or later.occurred_at_utc < earlier.occurred_at_utc
            for earlier, later in zip(self.events, self.events[1:])
        ):
            raise ValueError("event time and elapsed values must be monotonic")

        if not isinstance(self.events[0].signal, RunStartedSignal):
            raise ValueError("first event must be run_started")
        terminal_indexes = [
            index
            for index, event in enumerate(self.events)
            if isinstance(event.signal, TERMINAL_SIGNAL_TYPES)
        ]
        if terminal_indexes != [len(self.events) - 1]:
            raise ValueError("trace requires exactly one final terminal event")

        start = self.events[0].signal
        terminal = self.events[-1].signal
        if start.skill_name != self.identity.skill_name:
            raise ValueError("trace Skill identity does not match run_started")
        if start.skill_version != self.identity.skill_version:
            raise ValueError("trace Skill version does not match run_started")
        if start.runtime_policy_version != self.policy.policy_version:
            raise ValueError("runtime policy version does not match run_started")

        contexts = [
            event.signal
            for event in self.events
            if isinstance(event.signal, ContextBuiltSignal)
        ]
        if contexts and any(
            signal.context_contract_version
            != self.identity.context_contract_version
            for signal in contexts
        ):
            raise ValueError("context identity does not match context event")

        publications = [
            event.signal
            for event in self.events
            if isinstance(event.signal, PublicationDecidedSignal)
        ]
        if len(publications) > 1:
            raise ValueError("trace may contain only one publication decision")

        execution_seen = False
        context_seen = False
        provider_open: dict[int, tuple[str, str]] = {}
        tool_open: dict[int, tuple[str, str]] = {}
        next_provider_ordinal = 1
        next_tool_ordinal = 1
        harness_lifecycle = RuntimeHarnessLifecycleV11()
        for index, event in enumerate(self.events):
            signal = event.signal
            if self.event_schema_version == "1.1":
                harness_lifecycle = harness_lifecycle.advance(
                    signal,
                    context_seen=context_seen,
                    has_open_calls=bool(provider_open or tool_open),
                )
            if isinstance(signal, RunStartedSignal):
                if index != 0:
                    raise ValueError("run_started may only be the first event")
            elif isinstance(signal, ExecutionValidatedSignal):
                if execution_seen:
                    raise ValueError("execution_validated may occur only once")
                execution_seen = True
            elif isinstance(signal, ContextBuiltSignal):
                if context_seen:
                    raise ValueError("context_built may occur only once")
                if not execution_seen:
                    raise ValueError(
                        "context_built requires validated execution"
                    )
                context_seen = True
            elif isinstance(signal, ProviderCallStartedSignal):
                if not context_seen:
                    raise ValueError("provider call requires built context")
                if signal.ordinal != next_provider_ordinal:
                    raise ValueError("provider call ordinal is not contiguous")
                if (
                    signal.provider_id != self.identity.provider_id
                    or signal.model != self.identity.provider_model
                ):
                    raise ValueError("provider call identity mismatch")
                provider_open[signal.ordinal] = (
                    signal.provider_id,
                    signal.model,
                )
                next_provider_ordinal += 1
            elif isinstance(
                signal,
                (ProviderCallCompletedSignal, ProviderCallFailedSignal),
            ):
                provider_identity = provider_open.get(signal.ordinal)
                if provider_identity is None:
                    raise ValueError("provider call is not open")
                if provider_identity != (signal.provider_id, signal.model):
                    raise ValueError("provider call identity mismatch")
                del provider_open[signal.ordinal]
            elif isinstance(signal, ToolCallStartedSignal):
                if not context_seen:
                    raise ValueError("tool call requires built context")
                if signal.ordinal != next_tool_ordinal:
                    raise ValueError("tool call ordinal is not contiguous")
                tool_open[signal.ordinal] = (
                    signal.tool_name,
                    signal.tool_version,
                )
                next_tool_ordinal += 1
            elif isinstance(signal, ToolCallCompletedSignal):
                tool_identity = tool_open.get(signal.ordinal)
                if tool_identity is None:
                    raise ValueError("tool call is not open")
                if tool_identity != (signal.tool_name, signal.tool_version):
                    raise ValueError("tool call identity mismatch")
                del tool_open[signal.ordinal]

        if provider_open or tool_open:
            raise ValueError("terminal trace cannot contain open calls")

        if isinstance(terminal, RunCompletedSignal):
            if not execution_seen or not context_seen:
                raise ValueError(
                    "completed runtime requires validated execution and context"
                )
            if self.runtime_status is not RuntimeStatus.COMPLETED:
                raise ValueError("completed terminal requires completed runtime status")
            if not publications:
                raise ValueError("completed terminal requires a publication decision")
            decision = publications[0]
            if (
                terminal.publication_status is not self.publication_status
                or decision.publication_status is not self.publication_status
                or terminal.terminal_reason != self.terminal_reason
                or decision.terminal_reason != self.terminal_reason
            ):
                raise ValueError("publication status or reason mismatch")
        else:
            if self.runtime_status is not RuntimeStatus.FAILED:
                raise ValueError("failed terminal requires failed runtime status")
            if terminal.publication_status is not self.publication_status:
                raise ValueError("failed terminal publication status mismatch")
            if terminal.failure_code != self.terminal_reason:
                raise ValueError("failed terminal reason mismatch")
            if publications:
                decision = publications[0]
                if decision.publication_status is not self.publication_status:
                    raise ValueError("publication decision mismatch on failed run")

        if self.started_at_utc != self.events[0].occurred_at_utc:
            raise ValueError("started_at_utc must match the first event")
        if self.completed_at_utc != self.events[-1].occurred_at_utc:
            raise ValueError("completed_at_utc must match the terminal event")
        if self.elapsed_ms != self.events[-1].elapsed_ms:
            raise ValueError("elapsed_ms must match the terminal event")
        if self.completed_at_utc < self.started_at_utc:
            raise ValueError("completed_at_utc must not precede started_at_utc")

        provider_starts = sum(
            isinstance(event.signal, ProviderCallStartedSignal)
            for event in self.events
        )
        provider_completes = [
            event.signal
            for event in self.events
            if isinstance(event.signal, ProviderCallCompletedSignal)
        ]
        if self.usage.provider_calls_attempted != provider_starts:
            raise ValueError("provider attempted-call usage does not match events")
        if self.usage.provider_responses_observed != len(provider_completes):
            raise ValueError("provider response usage does not match events")
        if self.usage.observed_input_tokens != sum(
            signal.input_tokens for signal in provider_completes
        ) or self.usage.observed_output_tokens != sum(
            signal.output_tokens for signal in provider_completes
        ):
            raise ValueError("observed token usage does not match events")

        tool_starts = sum(
            isinstance(event.signal, ToolCallStartedSignal)
            for event in self.events
        )
        tool_completes = [
            event.signal
            for event in self.events
            if isinstance(event.signal, ToolCallCompletedSignal)
        ]
        if self.usage.tool_calls != tool_starts:
            raise ValueError("tool call usage does not match events")
        if self.usage.tool_attempts != sum(
            signal.attempts for signal in tool_completes
        ) or self.usage.tool_latency_ms != sum(
            signal.latency_ms for signal in tool_completes
        ):
            raise ValueError("tool attempt or latency usage does not match events")

        artifact_paths = [artifact.relative_path for artifact in self.artifacts]
        if len(set(artifact_paths)) != len(artifact_paths):
            raise ValueError("artifact relative paths must be unique")
        if publications:
            if self.event_schema_version == "1.1":
                known_artifact_digests = {
                    artifact.sha256
                    for artifact in self.artifacts
                    if artifact.kind == "final_report"
                }
            else:
                known_artifact_digests = {
                    artifact.sha256 for artifact in self.artifacts
                }
            if not set(publications[0].artifact_sha256s).issubset(
                known_artifact_digests
            ):
                raise ValueError(
                    "publication artifact digest has no Trace reference"
                )
            if (
                self.event_schema_version == "1.1"
                and publications[0].publication_status
                is RuntimePublicationStatus.REJECTED
                and known_artifact_digests
            ):
                raise ValueError("rejected publication must not reference a report")
        return self


TOutput = TypeVar("TOutput", bound=BaseModel)


class RuntimeRunResult(RuntimeContractModel, Generic[TOutput]):
    run_id: str
    runtime_status: RuntimeStatus
    publication_status: RuntimePublicationStatus | None = None
    terminal_reason: str
    output: TOutput | None = None
    trace_reference: RuntimeTraceReference | None = None

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        return normalize_run_id(value)

    @field_validator("terminal_reason")
    @classmethod
    def validate_terminal_reason(cls, value: str) -> str:
        return _validate_safe_code(value, field_name="terminal_reason")

    @model_validator(mode="after")
    def validate_result(self) -> "RuntimeRunResult[TOutput]":
        if self.trace_reference is not None and self.trace_reference.run_id != self.run_id:
            raise ValueError("trace reference run_id must match result run_id")
        if self.runtime_status is RuntimeStatus.COMPLETED:
            if (
                self.publication_status is None
                or self.output is None
                or self.trace_reference is None
            ):
                raise ValueError(
                    "completed runtime result requires publication, output, and trace"
                )
        elif self.output is not None:
            raise ValueError("failed runtime result must not expose typed output")
        return self
