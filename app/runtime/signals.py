"""Typed, body-free signals emitted by components during one runtime run."""

from __future__ import annotations

import re
from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


_SAFE_CODE_PATTERN = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
_SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_SKILL_NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_TOOL_NAME_PATTERN = re.compile(
    r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$"
)


class RuntimePublicationStatus(str, Enum):
    PUBLISHED = "published"
    DEGRADED = "degraded"
    REJECTED = "rejected"


class RuntimeFailureStage(str, Enum):
    BOUNDARY = "boundary"
    CONTEXT = "context"
    AGENT = "agent"
    TOOL = "tool"
    EVALUATION = "evaluation"
    PUBLICATION = "publication"
    OBSERVABILITY = "observability"


class RuntimeHarnessStatus(str, Enum):
    CREATED = "created"
    FACTS_READY = "facts_ready"
    KNOWLEDGE_READY = "knowledge_ready"
    DRAFT_READY = "draft_ready"
    EVALUATING = "evaluating"
    NEEDS_REVISION = "needs_revision"
    REVISING = "revising"
    RE_EVALUATING = "re_evaluating"
    PASSED = "passed"
    PUBLISHED = "published"
    DEGRADED = "degraded"
    REJECTED = "rejected"


class RuntimeEvaluationVerdict(str, Enum):
    PASS = "pass"
    NEEDS_REVISION = "needs_revision"
    FAIL = "fail"


class RuntimeSignalModel(BaseModel):
    """Strict base class that prevents arbitrary data entering a Trace."""

    model_config = ConfigDict(extra="forbid", frozen=True)


def _validate_safe_code(value: str, *, field_name: str) -> str:
    if not _SAFE_CODE_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be a lowercase safe code")
    return value


def _validate_semver(value: str, *, field_name: str) -> str:
    if not _SEMVER_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must use MAJOR.MINOR.PATCH")
    return value


def _validate_sha256s(values: tuple[str, ...]) -> tuple[str, ...]:
    if any(not _SHA256_PATTERN.fullmatch(value) for value in values):
        raise ValueError("artifact SHA-256 values must be lowercase hex digests")
    if len(set(values)) != len(values):
        raise ValueError("artifact SHA-256 values must be unique")
    return values


class RunStartedSignal(RuntimeSignalModel):
    kind: Literal["run_started"] = "run_started"
    skill_name: str
    skill_version: str
    runtime_policy_version: str

    @field_validator("skill_name")
    @classmethod
    def validate_skill_name(cls, value: str) -> str:
        if not _SKILL_NAME_PATTERN.fullmatch(value):
            raise ValueError("skill_name must use lowercase hyphen-case")
        return value

    @field_validator("skill_version", "runtime_policy_version")
    @classmethod
    def validate_versions(cls, value: str, info) -> str:
        return _validate_semver(value, field_name=info.field_name)


class ExecutionValidatedSignal(RuntimeSignalModel):
    kind: Literal["execution_validated"] = "execution_validated"
    input_artifact_sha256s: tuple[str, ...] = Field(min_length=1)

    @field_validator("input_artifact_sha256s")
    @classmethod
    def validate_artifact_sha256s(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return _validate_sha256s(values)


class ContextBuiltSignal(RuntimeSignalModel):
    kind: Literal["context_built"] = "context_built"
    context_contract_version: str
    estimated_context_units: int = Field(ge=0)
    omitted_item_ids: tuple[str, ...] = ()

    @field_validator("context_contract_version")
    @classmethod
    def validate_contract_version(cls, value: str) -> str:
        return _validate_semver(value, field_name="context_contract_version")

    @field_validator("omitted_item_ids")
    @classmethod
    def validate_omitted_items(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(
            _validate_safe_code(value, field_name="omitted_item_ids")
            for value in values
        )
        if len(set(normalized)) != len(normalized):
            raise ValueError("omitted_item_ids must be unique")
        return normalized


class ProviderCallStartedSignal(RuntimeSignalModel):
    kind: Literal["provider_call_started"] = "provider_call_started"
    provider_id: str
    model: str
    ordinal: int = Field(ge=1)
    iteration: int = Field(ge=1)

    @field_validator("provider_id", "model")
    @classmethod
    def validate_identity(cls, value: str, info) -> str:
        return _validate_safe_code(value, field_name=info.field_name)


class ProviderCallCompletedSignal(RuntimeSignalModel):
    kind: Literal["provider_call_completed"] = "provider_call_completed"
    provider_id: str
    model: str
    ordinal: int = Field(ge=1)
    finish_reason: str
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)

    @field_validator("provider_id", "model", "finish_reason")
    @classmethod
    def validate_codes(cls, value: str, info) -> str:
        return _validate_safe_code(value, field_name=info.field_name)


class ProviderCallFailedSignal(RuntimeSignalModel):
    kind: Literal["provider_call_failed"] = "provider_call_failed"
    provider_id: str
    model: str
    ordinal: int = Field(ge=1)
    failure_code: str
    provider_error_code: str | None = None

    @field_validator(
        "provider_id",
        "model",
        "failure_code",
        "provider_error_code",
    )
    @classmethod
    def validate_codes(cls, value: str | None, info) -> str | None:
        if value is None:
            return None
        return _validate_safe_code(value, field_name=info.field_name)


class ToolCallStartedSignal(RuntimeSignalModel):
    kind: Literal["tool_call_started"] = "tool_call_started"
    tool_name: str
    tool_version: str
    ordinal: int = Field(ge=1)
    iteration: int = Field(ge=1)

    @field_validator("tool_name")
    @classmethod
    def validate_tool_name(cls, value: str) -> str:
        if not _TOOL_NAME_PATTERN.fullmatch(value):
            raise ValueError("tool_name must use a namespaced machine name")
        return value

    @field_validator("tool_version")
    @classmethod
    def validate_tool_version(cls, value: str) -> str:
        return _validate_semver(value, field_name="tool_version")


class ToolCallCompletedSignal(RuntimeSignalModel):
    kind: Literal["tool_call_completed"] = "tool_call_completed"
    tool_name: str
    tool_version: str
    ordinal: int = Field(ge=1)
    success: bool
    attempts: int = Field(ge=0)
    latency_ms: float = Field(ge=0)
    cached: bool
    fallback_used: bool

    @field_validator("tool_name")
    @classmethod
    def validate_tool_name(cls, value: str) -> str:
        if not _TOOL_NAME_PATTERN.fullmatch(value):
            raise ValueError("tool_name must use a namespaced machine name")
        return value

    @field_validator("tool_version")
    @classmethod
    def validate_tool_version(cls, value: str) -> str:
        return _validate_semver(value, field_name="tool_version")

    @field_validator("fallback_used")
    @classmethod
    def reject_cached_fallback(cls, value: bool, info) -> bool:
        if value and info.data.get("cached"):
            raise ValueError("tool result cannot be cached and fallback-generated")
        return value


class HarnessTransitionedSignal(RuntimeSignalModel):
    kind: Literal["harness_transitioned"] = "harness_transitioned"
    from_status: RuntimeHarnessStatus
    to_status: RuntimeHarnessStatus
    revision_count: int = Field(ge=0, le=3)


class EvaluationCompletedSignal(RuntimeSignalModel):
    kind: Literal["evaluation_completed"] = "evaluation_completed"
    attempt: int = Field(ge=1)
    score: int = Field(ge=0, le=100)
    verdict: RuntimeEvaluationVerdict
    blocking_categories: tuple[str, ...] = ()

    @field_validator("blocking_categories")
    @classmethod
    def validate_blocking_categories(
        cls,
        values: tuple[str, ...],
    ) -> tuple[str, ...]:
        normalized = tuple(
            _validate_safe_code(value, field_name="blocking_categories")
            for value in values
        )
        if len(set(normalized)) != len(normalized):
            raise ValueError("blocking_categories must be unique")
        return normalized


class PublicationDecidedSignal(RuntimeSignalModel):
    kind: Literal["publication_decided"] = "publication_decided"
    publication_status: RuntimePublicationStatus
    terminal_reason: str
    artifact_sha256s: tuple[str, ...] = ()

    @field_validator("terminal_reason")
    @classmethod
    def validate_terminal_reason(cls, value: str) -> str:
        return _validate_safe_code(value, field_name="terminal_reason")

    @field_validator("artifact_sha256s")
    @classmethod
    def validate_artifact_sha256s(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return _validate_sha256s(values)


class RunCompletedSignal(RuntimeSignalModel):
    kind: Literal["run_completed"] = "run_completed"
    publication_status: RuntimePublicationStatus
    terminal_reason: str

    @field_validator("terminal_reason")
    @classmethod
    def validate_terminal_reason(cls, value: str) -> str:
        return _validate_safe_code(value, field_name="terminal_reason")


class RunFailedSignal(RuntimeSignalModel):
    kind: Literal["run_failed"] = "run_failed"
    failure_stage: RuntimeFailureStage
    failure_code: str
    publication_status: RuntimePublicationStatus | None = None

    @field_validator("failure_code")
    @classmethod
    def validate_failure_code(cls, value: str) -> str:
        return _validate_safe_code(value, field_name="failure_code")


RuntimeSignal = Annotated[
    Union[
        RunStartedSignal,
        ExecutionValidatedSignal,
        ContextBuiltSignal,
        ProviderCallStartedSignal,
        ProviderCallCompletedSignal,
        ProviderCallFailedSignal,
        ToolCallStartedSignal,
        ToolCallCompletedSignal,
        HarnessTransitionedSignal,
        EvaluationCompletedSignal,
        PublicationDecidedSignal,
        RunCompletedSignal,
        RunFailedSignal,
    ],
    Field(discriminator="kind"),
]


RUNTIME_SIGNAL_TYPES = (
    RunStartedSignal,
    ExecutionValidatedSignal,
    ContextBuiltSignal,
    ProviderCallStartedSignal,
    ProviderCallCompletedSignal,
    ProviderCallFailedSignal,
    ToolCallStartedSignal,
    ToolCallCompletedSignal,
    HarnessTransitionedSignal,
    EvaluationCompletedSignal,
    PublicationDecidedSignal,
    RunCompletedSignal,
    RunFailedSignal,
)
TERMINAL_SIGNAL_TYPES = (RunCompletedSignal, RunFailedSignal)
