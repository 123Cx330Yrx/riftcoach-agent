"""Offline contracts for a bounded fresh-response recovery candidate.

This module is intentionally not a retry implementation.  It describes a
candidate runtime, the two possible provider-attempt slots, a small in-memory
budget ledger, and a body-free trace projection.  A future executor may use
these contracts only after a separately registered profile, public CI, and an
explicit real-call authorization exist.  No Provider, SDK, request body, or
credential is imported here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from typing import Any, Literal

from .response_completion_policy import (
    GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1,
    ResponseBoundarySnapshot,
    ResponseCompletionDecision,
    ResponseCompletionPolicy,
    ResponseCompletionMode,
    ResponseDisposition,
    ResponseFieldState,
    ResponseRequestContext,
    ResponseUsageState,
)


_SAFE_ID = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
_NEXT_ACTIONS = frozenset(
    {
        "requires_registered_runtime",
        "terminal_complete",
        "terminal_tool_calls",
        "terminal_fail_closed",
    }
)

ActivationState = Literal["candidate"]
RecoveryTerminalState = Literal[
    "awaiting_primary",
    "awaiting_recovery",
    "complete_text",
    "tool_calls_ready",
    "fail_closed",
]

_FIELD_STATES = frozenset(
    {"not_observed", "missing", "null", "empty", "non_empty", "non_string"}
)
_USAGE_STATES = frozenset({"valid", "missing", "invalid"})


class RecoveryAttemptKind(StrEnum):
    """The only two call identities this candidate can describe."""

    PRIMARY = "primary"
    FRESH_RECOVERY = "fresh_recovery"


class RecoveryContractError(ValueError):
    """Base error for invalid candidate plans or ledger transitions."""


class RecoveryBudgetExceeded(RecoveryContractError):
    """A provider-attempt or cumulative resource budget is exhausted."""


class RecoveryNotEligible(RecoveryContractError):
    """The first response does not satisfy the exact recovery allowlist."""


class RecoveryStateError(RecoveryContractError):
    """A caller attempted an out-of-order or duplicate ledger transition."""


@dataclass(frozen=True, slots=True)
class ResponseRecoveryRuntimeProfile:
    """Candidate-only runtime identity and hard limits.

    This is deliberately a distinct type from ``ModelRuntimeProfile``.  It is
    not registered with the product composition root and therefore cannot
    change the current Flash v1 runtime by metadata or model name alone.
    """

    profile_id: str
    version: str
    provider_id: str
    model: str
    policy_id: str
    policy_version: str
    agent_timeout_s: float
    llm_tool_timeout_s: float = 90.0
    transport_timeout_s: float = 120.0
    max_output_tokens: int = 8192
    max_attempts: int = 2
    max_additional_calls: int = 1
    max_total_input_tokens: int = 32_000
    max_total_output_tokens: int = 16_384
    max_total_elapsed_ms: int = 180_000
    temperature: float = 1.0
    top_p: float = 0.95
    activation_state: ActivationState = "candidate"

    def __post_init__(self) -> None:
        for field_name in (
            "profile_id",
            "provider_id",
            "model",
            "policy_id",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not _SAFE_ID.fullmatch(value.strip().lower()):
                raise ValueError(f"{field_name} must be a safe identifier")
            object.__setattr__(self, field_name, value.strip().lower())

        for field_name in ("version", "policy_version"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not _SEMVER.fullmatch(value.strip()):
                raise ValueError(f"{field_name} must be a semantic version")
            object.__setattr__(self, field_name, value.strip())

        if self.activation_state != "candidate":
            raise ValueError("response recovery runtime must remain a candidate")
        for field_name in (
            "agent_timeout_s",
            "llm_tool_timeout_s",
            "transport_timeout_s",
        ):
            value = getattr(self, field_name)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(value)
                or value <= 0
                or value > 300
            ):
                raise ValueError(f"{field_name} must be in (0, 300]")
        if self.llm_tool_timeout_s < self.agent_timeout_s:
            raise ValueError("llm_tool_timeout_s must cover agent timeout")
        if self.transport_timeout_s < self.llm_tool_timeout_s:
            raise ValueError("transport_timeout_s must cover tool timeout")

        _require_int_range(self.max_output_tokens, 1, 8192, "max_output_tokens")
        _require_int_range(self.max_attempts, 1, 2, "max_attempts")
        _require_int_range(
            self.max_additional_calls,
            0,
            1,
            "max_additional_calls",
        )
        if self.max_additional_calls > self.max_attempts - 1:
            raise ValueError("additional calls cannot exceed attempt slots")
        _require_positive_int(self.max_total_input_tokens, "max_total_input_tokens")
        _require_positive_int(
            self.max_total_output_tokens,
            "max_total_output_tokens",
        )
        if self.max_total_output_tokens < self.max_output_tokens:
            raise ValueError("total output budget must cover one attempt")
        _require_positive_int(self.max_total_elapsed_ms, "max_total_elapsed_ms")
        if not isinstance(self.temperature, (int, float)) or isinstance(
            self.temperature, bool
        ) or not isfinite(self.temperature) or not 0 <= self.temperature <= 2:
            raise ValueError("temperature must be between 0 and 2")
        if not isinstance(self.top_p, (int, float)) or isinstance(
            self.top_p, bool
        ) or not isfinite(self.top_p) or not 0 <= self.top_p <= 1:
            raise ValueError("top_p must be between 0 and 1")

    def matches_policy(self, policy: ResponseCompletionPolicy) -> bool:
        """Require every candidate identity field to match exactly."""

        return (
            self == GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1
            and policy == GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1
            and policy.mode is ResponseCompletionMode.CANDIDATE_FRESH_RECOVERY
            and policy.activation_state == self.activation_state
            and policy.provider_id == self.provider_id
            and policy.model == self.model
            and policy.policy_id == self.policy_id
            and policy.version == self.policy_version
            and policy.runtime_profile_id == self.profile_id
            and policy.runtime_profile_version == self.version
            and policy.max_output_tokens == self.max_output_tokens
            and policy.max_additional_calls == self.max_additional_calls
        )

    def budget(self) -> "ResponseRecoveryBudget":
        """Return the immutable cumulative budget attached to this profile."""

        return ResponseRecoveryBudget(
            max_attempts=self.max_attempts,
            max_additional_calls=self.max_additional_calls,
            max_total_input_tokens=self.max_total_input_tokens,
            max_total_output_tokens=self.max_total_output_tokens,
            max_total_elapsed_ms=self.max_total_elapsed_ms,
        )


@dataclass(frozen=True, slots=True)
class ResponseRecoveryBudget:
    """Hard cumulative limits for underlying provider attempts."""

    max_attempts: int = 2
    max_additional_calls: int = 1
    max_total_input_tokens: int = 32_000
    max_total_output_tokens: int = 16_384
    max_total_elapsed_ms: int = 180_000

    def __post_init__(self) -> None:
        _require_int_range(self.max_attempts, 1, 2, "max_attempts")
        _require_int_range(
            self.max_additional_calls,
            0,
            1,
            "max_additional_calls",
        )
        if self.max_additional_calls > self.max_attempts - 1:
            raise ValueError("additional calls cannot exceed attempt slots")
        _require_positive_int(self.max_total_input_tokens, "max_total_input_tokens")
        _require_positive_int(
            self.max_total_output_tokens,
            "max_total_output_tokens",
        )
        _require_positive_int(self.max_total_elapsed_ms, "max_total_elapsed_ms")


@dataclass(frozen=True, slots=True)
class ResponseAttemptSpec:
    """One bounded slot in a candidate plan."""

    ordinal: int
    kind: RecoveryAttemptKind
    max_output_tokens: int
    timeout_s: float
    transport_timeout_s: float

    def __post_init__(self) -> None:
        _require_int_range(self.ordinal, 1, 2, "ordinal")
        if not isinstance(self.kind, RecoveryAttemptKind):
            raise ValueError("kind must be a RecoveryAttemptKind")
        expected_kind = (
            RecoveryAttemptKind.PRIMARY
            if self.ordinal == 1
            else RecoveryAttemptKind.FRESH_RECOVERY
        )
        if self.kind is not expected_kind:
            raise ValueError("attempt kind and ordinal do not match")
        _require_int_range(self.max_output_tokens, 1, 8192, "max_output_tokens")
        for field_name in ("timeout_s", "transport_timeout_s"):
            value = getattr(self, field_name)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(value)
                or value <= 0
                or value > 300
            ):
                raise ValueError(f"{field_name} must be in (0, 300]")
        if self.transport_timeout_s < self.timeout_s:
            raise ValueError("transport timeout must cover attempt timeout")


@dataclass(frozen=True, slots=True)
class ResponseRecoveryPlan:
    """Offline description of the primary and optional recovery slots."""

    schema_version: str
    plan_id: str
    provider_id: str
    model: str
    policy_id: str
    policy_version: str
    runtime_profile_id: str
    runtime_profile_version: str
    activation_state: ActivationState
    execution_allowed: bool
    initial_snapshot: ResponseBoundarySnapshot
    initial_context: ResponseRequestContext
    initial_decision: ResponseCompletionDecision
    attempts: tuple[ResponseAttemptSpec, ...]
    budget: ResponseRecoveryBudget
    next_action: str

    def __post_init__(self) -> None:
        if self.schema_version != "1.0":
            raise ValueError("unsupported response recovery plan schema")
        if self.plan_id != "glm-5.3-flash-fresh-recovery-plan-v1":
            raise ValueError("unsupported response recovery plan identity")
        for field_name in (
            "plan_id",
            "provider_id",
            "model",
            "policy_id",
            "runtime_profile_id",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
                raise ValueError(f"{field_name} must be a safe identifier")
        for field_name in ("policy_version", "runtime_profile_version"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not _SEMVER.fullmatch(value):
                raise ValueError(f"{field_name} must be a semantic version")
        expected_profile = GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1
        if (
            self.provider_id,
            self.model,
            self.policy_id,
            self.policy_version,
            self.runtime_profile_id,
            self.runtime_profile_version,
        ) != (
            expected_profile.provider_id,
            expected_profile.model,
            expected_profile.policy_id,
            expected_profile.policy_version,
            expected_profile.profile_id,
            expected_profile.version,
        ):
            raise ValueError("plan identity does not match exact candidate profile")
        if self.activation_state != "candidate":
            raise ValueError("plan activation state must remain candidate")
        if self.execution_allowed is not False:
            raise ValueError("candidate plan cannot allow execution")
        if not isinstance(self.initial_snapshot, ResponseBoundarySnapshot):
            raise TypeError("initial_snapshot must be a ResponseBoundarySnapshot")
        if not isinstance(self.initial_context, ResponseRequestContext):
            raise TypeError("initial_context must be a ResponseRequestContext")
        if not isinstance(self.initial_decision, ResponseCompletionDecision):
            raise TypeError(
                "initial_decision must be a ResponseCompletionDecision"
            )
        if not isinstance(self.attempts, tuple) or not all(
            isinstance(spec, ResponseAttemptSpec) for spec in self.attempts
        ):
            raise TypeError("attempts must be a tuple of ResponseAttemptSpec")
        if not self.attempts:
            raise ValueError("plan must contain a primary attempt")
        if tuple(spec.ordinal for spec in self.attempts) != tuple(
            range(1, len(self.attempts) + 1)
        ):
            raise ValueError("plan attempt ordinals must be contiguous")
        if any(
            spec.max_output_tokens > expected_profile.max_output_tokens
            or spec.timeout_s > expected_profile.agent_timeout_s
            or spec.transport_timeout_s > expected_profile.transport_timeout_s
            for spec in self.attempts
        ):
            raise ValueError("plan attempt exceeds exact candidate profile limits")
        if len(self.attempts) > self.budget.max_attempts:
            raise ValueError("plan exceeds its attempt budget")
        if self.next_action not in _NEXT_ACTIONS:
            raise ValueError("next_action is not a safe terminal code")
        expected_decision = GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1.decide(
            self.initial_snapshot,
            self.initial_context,
        )
        if self.initial_decision != expected_decision:
            raise ValueError("plan initial decision does not match candidate policy")

    @property
    def has_recovery_slot(self) -> bool:
        return len(self.attempts) == 2


def build_response_recovery_plan(
    *,
    policy: ResponseCompletionPolicy,
    snapshot: ResponseBoundarySnapshot,
    context: ResponseRequestContext,
    runtime_profile: ResponseRecoveryRuntimeProfile
    | None = None,
) -> ResponseRecoveryPlan:
    """Classify one observed first response and build an offline plan.

    The policy is re-evaluated here instead of trusting a caller-provided
    Boolean.  This makes the plan deterministic and keeps the candidate
    allowlist at one boundary.  An eligible shape gets a *described* second
    slot, but the returned plan is always ``execution_allowed=False``.
    """

    if policy != GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1:
        raise ValueError("only the exact candidate policy is supported")
    if not isinstance(snapshot, ResponseBoundarySnapshot):
        raise TypeError("snapshot must be a ResponseBoundarySnapshot")
    if not isinstance(context, ResponseRequestContext):
        raise TypeError("context must be a ResponseRequestContext")
    profile = runtime_profile or GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1
    if not isinstance(profile, ResponseRecoveryRuntimeProfile):
        raise TypeError("runtime_profile must be a ResponseRecoveryRuntimeProfile")
    if not profile.matches_policy(policy):
        raise ValueError("candidate policy and runtime profile identity mismatch")

    decision = policy.decide(snapshot, context)
    budget = profile.budget()
    primary = ResponseAttemptSpec(
        ordinal=1,
        kind=RecoveryAttemptKind.PRIMARY,
        max_output_tokens=profile.max_output_tokens,
        timeout_s=profile.agent_timeout_s,
        transport_timeout_s=profile.transport_timeout_s,
    )
    attempts: tuple[ResponseAttemptSpec, ...]
    if decision.disposition is ResponseDisposition.CANDIDATE_ELIGIBLE:
        recovery = ResponseAttemptSpec(
            ordinal=2,
            kind=RecoveryAttemptKind.FRESH_RECOVERY,
            max_output_tokens=profile.max_output_tokens,
            timeout_s=profile.agent_timeout_s,
            transport_timeout_s=profile.transport_timeout_s,
        )
        attempts = (primary, recovery)
        next_action = "requires_registered_runtime"
    elif decision.disposition is ResponseDisposition.COMPLETE_TEXT:
        attempts = (primary,)
        next_action = "terminal_complete"
    elif decision.disposition is ResponseDisposition.TOOL_CALLS_READY:
        attempts = (primary,)
        next_action = "terminal_tool_calls"
    else:
        attempts = (primary,)
        next_action = "terminal_fail_closed"

    return ResponseRecoveryPlan(
        schema_version="1.0",
        plan_id="glm-5.3-flash-fresh-recovery-plan-v1",
        provider_id=profile.provider_id,
        model=profile.model,
        policy_id=policy.policy_id,
        policy_version=policy.version,
        runtime_profile_id=profile.profile_id,
        runtime_profile_version=profile.version,
        activation_state=profile.activation_state,
        execution_allowed=False,
        initial_snapshot=snapshot,
        initial_context=context,
        initial_decision=decision,
        attempts=attempts,
        budget=budget,
        next_action=next_action,
    )


@dataclass(frozen=True, slots=True)
class ResponseAttemptOutcome:
    """Sanitized result of one already-issued provider attempt."""

    snapshot: ResponseBoundarySnapshot
    context: ResponseRequestContext
    decision: ResponseCompletionDecision
    input_tokens: int | None
    output_tokens: int | None
    elapsed_ms: int

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot, ResponseBoundarySnapshot):
            raise TypeError("snapshot must be a ResponseBoundarySnapshot")
        if not isinstance(self.context, ResponseRequestContext):
            raise TypeError("context must be a ResponseRequestContext")
        if not isinstance(self.decision, ResponseCompletionDecision):
            raise TypeError("decision must be a ResponseCompletionDecision")
        if self.snapshot.usage_state == "valid":
            _require_non_negative_optional_int(
                self.input_tokens,
                "input_tokens",
                required=True,
            )
            _require_non_negative_optional_int(
                self.output_tokens,
                "output_tokens",
                required=True,
            )
        else:
            if self.input_tokens is not None or self.output_tokens is not None:
                raise ValueError(
                    "missing or invalid usage must not claim token totals"
                )
        _require_non_negative_int(self.elapsed_ms, "elapsed_ms")

    @property
    def is_candidate_eligible(self) -> bool:
        return (
            self.decision.disposition is ResponseDisposition.CANDIDATE_ELIGIBLE
            and self.decision.candidate_eligible
        )

    @property
    def terminal_state(self) -> RecoveryTerminalState:
        return _terminal_state_for_disposition(self.decision.disposition)


@dataclass(frozen=True, slots=True)
class ResponseAttemptReservation:
    """Opaque reservation returned immediately before a provider attempt."""

    reservation_id: int
    spec: ResponseAttemptSpec

    def __post_init__(self) -> None:
        _require_positive_int(self.reservation_id, "reservation_id")
        if not isinstance(self.spec, ResponseAttemptSpec):
            raise TypeError("spec must be a ResponseAttemptSpec")


@dataclass(frozen=True, slots=True)
class ResponseAttemptRecord:
    """Settled, body-free record for one underlying call."""

    ordinal: int
    kind: RecoveryAttemptKind
    provider_id: str
    model: str
    policy_id: str
    policy_version: str
    runtime_profile_id: str
    runtime_profile_version: str
    outcome: ResponseAttemptOutcome
    budget_exceeded: bool

    def __post_init__(self) -> None:
        _require_int_range(self.ordinal, 1, 2, "ordinal")
        if not isinstance(self.kind, RecoveryAttemptKind):
            raise ValueError("kind must be a RecoveryAttemptKind")
        expected_kind = (
            RecoveryAttemptKind.PRIMARY
            if self.ordinal == 1
            else RecoveryAttemptKind.FRESH_RECOVERY
        )
        if self.kind is not expected_kind:
            raise ValueError("attempt kind and ordinal do not match")
        for field_name in (
            "provider_id",
            "model",
            "policy_id",
            "runtime_profile_id",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
                raise ValueError(f"{field_name} must be a safe identifier")
        for field_name in ("policy_version", "runtime_profile_version"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not _SEMVER.fullmatch(value):
                raise ValueError(f"{field_name} must be a semantic version")
        if not isinstance(self.outcome, ResponseAttemptOutcome):
            raise TypeError("outcome must be a ResponseAttemptOutcome")
        if not isinstance(self.budget_exceeded, bool):
            raise ValueError("budget_exceeded must be a boolean")


@dataclass(frozen=True, slots=True)
class ResponseRecoveryLedgerSnapshot:
    """Immutable resource and state view of a recovery ledger."""

    calls_reserved: int
    calls_settled: int
    input_tokens_observed: int
    output_tokens_observed: int
    elapsed_ms_observed: int
    unknown_usage_attempts: int
    budget_exceeded: bool
    terminal_state: RecoveryTerminalState
    attempts: tuple[ResponseAttemptRecord, ...]


@dataclass(frozen=True, slots=True)
class ResponseRecoveryTraceAttempt:
    """Sanitized Trace row; no response/request bodies are representable."""

    ordinal: int
    attempt_kind: RecoveryAttemptKind
    provider_id: str
    model: str
    policy_id: str
    policy_version: str
    runtime_profile_id: str
    runtime_profile_version: str
    disposition: ResponseDisposition
    reason_code: str
    error_code: str | None
    finish_reason: str | None
    content_state: ResponseFieldState
    reasoning_content_state: ResponseFieldState
    tool_call_count: int
    usage_state: ResponseUsageState
    input_tokens: int | None
    output_tokens: int | None
    elapsed_ms: int

    def __post_init__(self) -> None:
        _require_int_range(self.ordinal, 1, 2, "ordinal")
        if not isinstance(self.attempt_kind, RecoveryAttemptKind):
            raise ValueError("attempt_kind must be a RecoveryAttemptKind")
        expected_kind = (
            RecoveryAttemptKind.PRIMARY
            if self.ordinal == 1
            else RecoveryAttemptKind.FRESH_RECOVERY
        )
        if self.attempt_kind is not expected_kind:
            raise ValueError("Trace attempt kind and ordinal do not match")
        for field_name in (
            "provider_id",
            "model",
            "policy_id",
            "runtime_profile_id",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
                raise ValueError(f"{field_name} must be a safe identifier")
        for field_name in ("policy_version", "runtime_profile_version"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not _SEMVER.fullmatch(value):
                raise ValueError(f"{field_name} must be a semantic version")
        if not isinstance(self.disposition, ResponseDisposition):
            raise ValueError("disposition must be a ResponseDisposition")
        if not isinstance(self.reason_code, str) or not _SAFE_ID.fullmatch(
            self.reason_code
        ):
            raise ValueError("reason_code must be a safe code")
        for field_name in ("error_code", "finish_reason"):
            value = getattr(self, field_name)
            if value is not None and (
                not isinstance(value, str) or not _SAFE_ID.fullmatch(value)
            ):
                raise ValueError(f"{field_name} must be a safe code or None")
        if self.content_state not in _FIELD_STATES:
            raise ValueError("content_state must be sanitized")
        if self.reasoning_content_state not in _FIELD_STATES:
            raise ValueError("reasoning_content_state must be sanitized")
        if self.usage_state not in _USAGE_STATES:
            raise ValueError("usage_state must be sanitized")
        _require_non_negative_int(self.tool_call_count, "tool_call_count")
        if self.usage_state == "valid":
            _require_non_negative_optional_int(
                self.input_tokens,
                "input_tokens",
                required=True,
            )
            _require_non_negative_optional_int(
                self.output_tokens,
                "output_tokens",
                required=True,
            )
        elif self.input_tokens is not None or self.output_tokens is not None:
            raise ValueError("unknown usage must not claim token totals")
        _require_non_negative_int(self.elapsed_ms, "elapsed_ms")

    def as_dict(self) -> dict[str, Any]:
        return {
            "ordinal": self.ordinal,
            "attempt_kind": self.attempt_kind.value,
            "provider_id": self.provider_id,
            "model": self.model,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "runtime_profile_id": self.runtime_profile_id,
            "runtime_profile_version": self.runtime_profile_version,
            "disposition": self.disposition.value,
            "reason_code": self.reason_code,
            "error_code": self.error_code,
            "finish_reason": self.finish_reason,
            "content_state": self.content_state,
            "reasoning_content_state": self.reasoning_content_state,
            "tool_call_count": self.tool_call_count,
            "usage_state": self.usage_state,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "elapsed_ms": self.elapsed_ms,
        }


@dataclass(frozen=True, slots=True)
class ResponseRecoveryTrace:
    """Aggregate body-free Trace for the candidate contract only."""

    schema_version: str
    provider_id: str
    model: str
    policy_id: str
    policy_version: str
    runtime_profile_id: str
    runtime_profile_version: str
    attempts: tuple[ResponseRecoveryTraceAttempt, ...]
    calls_attempted: int
    input_tokens_observed: int
    output_tokens_observed: int
    elapsed_ms_observed: int
    unknown_usage_attempts: int
    budget_exceeded: bool
    terminal_state: RecoveryTerminalState

    def __post_init__(self) -> None:
        if self.schema_version != "1.0":
            raise ValueError("unsupported response recovery trace schema")
        for field_name in (
            "provider_id",
            "model",
            "policy_id",
            "runtime_profile_id",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
                raise ValueError(f"{field_name} must be a safe identifier")
        for field_name in ("policy_version", "runtime_profile_version"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not _SEMVER.fullmatch(value):
                raise ValueError(f"{field_name} must be a semantic version")
        if not isinstance(self.attempts, tuple) or not all(
            isinstance(row, ResponseRecoveryTraceAttempt) for row in self.attempts
        ):
            raise TypeError(
                "attempts must be a tuple of ResponseRecoveryTraceAttempt"
            )
        if not self.attempts:
            raise ValueError("recovery Trace must contain an attempt")
        if tuple(row.ordinal for row in self.attempts) != tuple(
            range(1, len(self.attempts) + 1)
        ):
            raise ValueError("Trace attempt ordinals must be contiguous")
        if len(self.attempts) > 2:
            raise ValueError("Trace cannot contain a third attempt")
        if self.attempts[0].attempt_kind is not RecoveryAttemptKind.PRIMARY:
            raise ValueError("Trace must start with primary")
        if (
            len(self.attempts) == 2
            and self.attempts[1].attempt_kind is not RecoveryAttemptKind.FRESH_RECOVERY
        ):
            raise ValueError("second Trace row must be fresh_recovery")
        if self.terminal_state not in {
            "awaiting_primary",
            "awaiting_recovery",
            "complete_text",
            "tool_calls_ready",
            "fail_closed",
        }:
            raise ValueError("terminal_state is not a valid recovery state")
        identities = {
            (
                row.provider_id,
                row.model,
                row.policy_id,
                row.policy_version,
                row.runtime_profile_id,
                row.runtime_profile_version,
            )
            for row in self.attempts
        }
        if len(identities) != 1:
            raise ValueError("Trace attempt identities must remain stable")
        if (
            self.provider_id,
            self.model,
            self.policy_id,
            self.policy_version,
            self.runtime_profile_id,
            self.runtime_profile_version,
        ) != next(iter(identities)):
            raise ValueError("Trace identity does not match its attempt rows")
        _require_non_negative_int(self.calls_attempted, "calls_attempted")
        if self.calls_attempted != len(self.attempts):
            raise ValueError("Trace call count must match attempts")
        _require_non_negative_int(
            self.input_tokens_observed,
            "input_tokens_observed",
        )
        _require_non_negative_int(
            self.output_tokens_observed,
            "output_tokens_observed",
        )
        _require_non_negative_int(self.elapsed_ms_observed, "elapsed_ms_observed")
        _require_non_negative_int(
            self.unknown_usage_attempts,
            "unknown_usage_attempts",
        )
        if not isinstance(self.budget_exceeded, bool):
            raise ValueError("budget_exceeded must be a boolean")
        if self.input_tokens_observed != sum(
            row.input_tokens or 0 for row in self.attempts
        ):
            raise ValueError("Trace input totals do not match attempts")
        if self.output_tokens_observed != sum(
            row.output_tokens or 0 for row in self.attempts
        ):
            raise ValueError("Trace output totals do not match attempts")
        if self.elapsed_ms_observed != sum(row.elapsed_ms for row in self.attempts):
            raise ValueError("Trace elapsed totals do not match attempts")
        if self.unknown_usage_attempts != sum(
            row.usage_state != "valid" for row in self.attempts
        ):
            raise ValueError("Trace unknown usage count does not match attempts")

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "provider_id": self.provider_id,
            "model": self.model,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "runtime_profile_id": self.runtime_profile_id,
            "runtime_profile_version": self.runtime_profile_version,
            "attempts": [row.as_dict() for row in self.attempts],
            "calls_attempted": self.calls_attempted,
            "input_tokens_observed": self.input_tokens_observed,
            "output_tokens_observed": self.output_tokens_observed,
            "elapsed_ms_observed": self.elapsed_ms_observed,
            "unknown_usage_attempts": self.unknown_usage_attempts,
            "budget_exceeded": self.budget_exceeded,
            "terminal_state": self.terminal_state,
        }


class ResponseRecoveryLedger:
    """Small state machine for offline attempt accounting.

    ``reserve_next`` represents the moment immediately before a real provider
    call.  The caller must settle that reservation exactly once.  The class
    has no method accepting a Provider, callable, request, or response body.
    """

    def __init__(
        self,
        plan: ResponseRecoveryPlan,
        *,
        budget: ResponseRecoveryBudget | None = None,
    ) -> None:
        if not isinstance(plan, ResponseRecoveryPlan):
            raise TypeError("plan must be a ResponseRecoveryPlan")
        if budget is not None and not isinstance(budget, ResponseRecoveryBudget):
            raise TypeError("budget must be a ResponseRecoveryBudget")
        selected_budget = budget or plan.budget
        if selected_budget.max_attempts < len(plan.attempts):
            raise ValueError("budget cannot hold the planned attempt slots")
        if selected_budget.max_attempts > plan.budget.max_attempts:
            raise ValueError("budget cannot increase the planned attempt limit")
        if selected_budget.max_additional_calls > plan.budget.max_additional_calls:
            raise ValueError("budget cannot increase the planned additional-call limit")
        if selected_budget.max_total_input_tokens > plan.budget.max_total_input_tokens:
            raise ValueError("budget cannot increase the planned input limit")
        if selected_budget.max_total_output_tokens > plan.budget.max_total_output_tokens:
            raise ValueError("budget cannot increase the planned output limit")
        if selected_budget.max_total_elapsed_ms > plan.budget.max_total_elapsed_ms:
            raise ValueError("budget cannot increase the planned elapsed-time limit")
        self._plan = plan
        self._budget = selected_budget
        self._records: list[ResponseAttemptRecord] = []
        self._open_reservation: ResponseAttemptReservation | None = None
        self._next_reservation_id = 1
        self._calls_reserved = 0
        self._budget_exceeded = False

    @property
    def plan(self) -> ResponseRecoveryPlan:
        return self._plan

    def reserve_next(self) -> ResponseAttemptReservation:
        """Reserve exactly one next underlying call slot."""

        if self._open_reservation is not None:
            raise RecoveryStateError("an attempt is already in flight")
        if self._budget_exceeded:
            raise RecoveryBudgetExceeded("cumulative budget is already exceeded")
        next_spec = self._next_spec()
        if next_spec is None:
            if self._records and self._records[-1].outcome.is_candidate_eligible:
                raise RecoveryBudgetExceeded("maximum attempt slots exhausted")
            raise RecoveryNotEligible("first response is not eligible for recovery")
        if self._calls_reserved >= self._budget.max_attempts:
            raise RecoveryBudgetExceeded("maximum attempt budget exhausted")
        if (
            self._calls_reserved >= 1
            and self._calls_reserved - 1 >= self._budget.max_additional_calls
        ):
            raise RecoveryBudgetExceeded("additional-call budget exhausted")
        if self._calls_reserved >= 1 and not self._records:
            raise RecoveryStateError("a call cannot be reserved before primary")
        remaining_output = (
            self._budget.max_total_output_tokens
            - sum(row.outcome.output_tokens or 0 for row in self._records)
        )
        if next_spec.max_output_tokens > remaining_output:
            raise RecoveryBudgetExceeded("output token budget cannot hold next attempt")
        if (
            sum(row.outcome.elapsed_ms for row in self._records)
            >= self._budget.max_total_elapsed_ms
        ):
            raise RecoveryBudgetExceeded("elapsed-time budget is exhausted")

        reservation = ResponseAttemptReservation(
            reservation_id=self._next_reservation_id,
            spec=next_spec,
        )
        self._next_reservation_id += 1
        self._open_reservation = reservation
        self._calls_reserved += 1
        return reservation

    def settle(
        self,
        reservation: ResponseAttemptReservation,
        outcome: ResponseAttemptOutcome,
    ) -> ResponseAttemptRecord:
        """Settle one reservation; a failed call still consumes its slot."""

        if self._open_reservation is None or reservation is not self._open_reservation:
            raise RecoveryStateError("unknown reservation or duplicate settlement")
        if not isinstance(outcome, ResponseAttemptOutcome):
            raise TypeError("outcome must be a ResponseAttemptOutcome")
        spec = reservation.spec
        if spec.ordinal != len(self._records) + 1:
            raise RecoveryStateError("settlement ordinal is out of order")
        if spec.ordinal == 1 and outcome.snapshot != self._plan.initial_snapshot:
            raise RecoveryStateError("primary outcome does not match planned snapshot")
        if spec.ordinal == 1 and outcome.context != self._plan.initial_context:
            raise RecoveryStateError("primary outcome does not match planned context")
        if spec.ordinal == 1 and outcome.decision != self._plan.initial_decision:
            raise RecoveryStateError("primary outcome does not match planned decision")
        expected_decision = GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1.decide(
            outcome.snapshot,
            outcome.context,
        )
        if outcome.decision != expected_decision:
            raise RecoveryStateError("attempt decision does not match policy")

        input_total = sum(row.outcome.input_tokens or 0 for row in self._records) + (
            outcome.input_tokens or 0
        )
        output_total = sum(row.outcome.output_tokens or 0 for row in self._records) + (
            outcome.output_tokens or 0
        )
        elapsed_total = sum(row.outcome.elapsed_ms for row in self._records) + outcome.elapsed_ms
        budget_exceeded = (
            (outcome.output_tokens or 0) > spec.max_output_tokens
            or outcome.elapsed_ms > round(spec.timeout_s * 1000)
            or input_total > self._budget.max_total_input_tokens
            or output_total > self._budget.max_total_output_tokens
            or elapsed_total > self._budget.max_total_elapsed_ms
        )
        record = ResponseAttemptRecord(
            ordinal=spec.ordinal,
            kind=spec.kind,
            provider_id=self._plan.provider_id,
            model=self._plan.model,
            policy_id=self._plan.policy_id,
            policy_version=self._plan.policy_version,
            runtime_profile_id=self._plan.runtime_profile_id,
            runtime_profile_version=self._plan.runtime_profile_version,
            outcome=outcome,
            budget_exceeded=budget_exceeded,
        )
        self._records.append(record)
        self._open_reservation = None
        self._budget_exceeded = self._budget_exceeded or budget_exceeded
        return record

    def snapshot(self) -> ResponseRecoveryLedgerSnapshot:
        attempts = tuple(self._records)
        if self._open_reservation is not None:
            terminal_state: RecoveryTerminalState = (
                "awaiting_primary" if not attempts else "awaiting_recovery"
            )
        elif not attempts:
            terminal_state = "awaiting_primary"
        elif self._budget_exceeded:
            terminal_state = "fail_closed"
        elif (
            attempts[-1].outcome.is_candidate_eligible
            and len(attempts) < len(self._plan.attempts)
        ):
            terminal_state = "awaiting_recovery"
        else:
            terminal_state = attempts[-1].outcome.terminal_state
        return ResponseRecoveryLedgerSnapshot(
            calls_reserved=self._calls_reserved,
            calls_settled=len(attempts),
            input_tokens_observed=sum(row.outcome.input_tokens or 0 for row in attempts),
            output_tokens_observed=sum(row.outcome.output_tokens or 0 for row in attempts),
            elapsed_ms_observed=sum(row.outcome.elapsed_ms for row in attempts),
            unknown_usage_attempts=sum(
                row.outcome.snapshot.usage_state != "valid" for row in attempts
            ),
            budget_exceeded=self._budget_exceeded,
            terminal_state=terminal_state,
            attempts=attempts,
        )

    def trace(self) -> ResponseRecoveryTrace:
        snapshot = self.snapshot()
        rows = tuple(_trace_attempt(row) for row in snapshot.attempts)
        return ResponseRecoveryTrace(
            schema_version="1.0",
            provider_id=self._plan.provider_id,
            model=self._plan.model,
            policy_id=self._plan.policy_id,
            policy_version=self._plan.policy_version,
            runtime_profile_id=self._plan.runtime_profile_id,
            runtime_profile_version=self._plan.runtime_profile_version,
            attempts=rows,
            calls_attempted=len(rows),
            input_tokens_observed=snapshot.input_tokens_observed,
            output_tokens_observed=snapshot.output_tokens_observed,
            elapsed_ms_observed=snapshot.elapsed_ms_observed,
            unknown_usage_attempts=snapshot.unknown_usage_attempts,
            budget_exceeded=snapshot.budget_exceeded,
            terminal_state=snapshot.terminal_state,
        )

    def _next_spec(self) -> ResponseAttemptSpec | None:
        index = len(self._records)
        if index >= len(self._plan.attempts):
            return None
        if index == 1 and not self._records[0].outcome.is_candidate_eligible:
            return None
        return self._plan.attempts[index]


def _trace_attempt(record: ResponseAttemptRecord) -> ResponseRecoveryTraceAttempt:
    outcome = record.outcome
    snapshot = outcome.snapshot
    decision = outcome.decision
    return ResponseRecoveryTraceAttempt(
        ordinal=record.ordinal,
        attempt_kind=record.kind,
        provider_id=record.provider_id,
        model=record.model,
        policy_id=record.policy_id,
        policy_version=record.policy_version,
        runtime_profile_id=record.runtime_profile_id,
        runtime_profile_version=record.runtime_profile_version,
        disposition=decision.disposition,
        reason_code=decision.reason_code,
        error_code=decision.error_code,
        finish_reason=snapshot.finish_reason,
        content_state=snapshot.content_state,
        reasoning_content_state=snapshot.reasoning_content_state,
        tool_call_count=snapshot.tool_call_count,
        usage_state=snapshot.usage_state,
        input_tokens=outcome.input_tokens,
        output_tokens=outcome.output_tokens,
        elapsed_ms=outcome.elapsed_ms,
    )


def _terminal_state_for_disposition(
    disposition: ResponseDisposition,
) -> RecoveryTerminalState:
    if disposition is ResponseDisposition.COMPLETE_TEXT:
        return "complete_text"
    if disposition is ResponseDisposition.TOOL_CALLS_READY:
        return "tool_calls_ready"
    return "fail_closed"


def _require_positive_int(value: int, field_name: str) -> None:
    _require_int_range(value, 1, 2_000_000_000, field_name)


def _require_non_negative_int(value: int, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")


def _require_non_negative_optional_int(
    value: int | None,
    field_name: str,
    *,
    required: bool = False,
) -> None:
    if value is None:
        if required:
            raise ValueError(f"{field_name} is required for valid usage")
        return
    _require_non_negative_int(value, field_name)


def _require_int_range(value: int, lower: int, upper: int, field_name: str) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < lower
        or value > upper
    ):
        raise ValueError(f"{field_name} must be between {lower} and {upper}")


GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1 = ResponseRecoveryRuntimeProfile(
    profile_id="glm-5.3-flash-runtime-v2-candidate",
    version="2.0.0",
    provider_id="zhipu",
    model="glm-5.3-flash",
    policy_id="glm-5.3-flash-fresh-recovery-candidate-v1",
    policy_version="1.0.0",
    agent_timeout_s=90.0,
)


__all__ = [
    "GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1",
    "RecoveryAttemptKind",
    "RecoveryBudgetExceeded",
    "RecoveryContractError",
    "RecoveryNotEligible",
    "RecoveryStateError",
    "ResponseAttemptOutcome",
    "ResponseAttemptRecord",
    "ResponseAttemptReservation",
    "ResponseAttemptSpec",
    "ResponseRecoveryBudget",
    "ResponseRecoveryLedger",
    "ResponseRecoveryLedgerSnapshot",
    "ResponseRecoveryPlan",
    "ResponseRecoveryRuntimeProfile",
    "ResponseRecoveryTrace",
    "ResponseRecoveryTraceAttempt",
    "build_response_recovery_plan",
]
