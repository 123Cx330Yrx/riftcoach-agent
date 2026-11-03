"""Versioned, body-free response-completion decisions.

The provider-neutral chat contract accepts only a complete ``ChatResponse``.
This module deliberately stays one layer below that contract: it classifies a
small, sanitized snapshot of a provider response and records whether a future
bounded recovery strategy could even be considered.  It does not perform
network I/O, retry a request, replay reasoning, or turn hidden reasoning into
user-visible content.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from typing import Literal


_SAFE_CODE = re.compile(r"^[a-z][a-z0-9_.-]{0,95}$")
_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")

ResponseFieldState = Literal[
    "not_observed",
    "missing",
    "null",
    "empty",
    "non_empty",
    "non_string",
]
ResponseUsageState = Literal["valid", "missing", "invalid"]
ResponsePhase = Literal[
    "agent_initial",
    "agent_after_tool",
    "evaluate",
    "repair",
    "revise",
]
ActivationState = Literal["registered", "candidate"]

_FIELD_STATES = frozenset(
    {"not_observed", "missing", "null", "empty", "non_empty", "non_string"}
)
_USAGE_STATES = frozenset({"valid", "missing", "invalid"})
_PHASES = frozenset(
    {"agent_initial", "agent_after_tool", "evaluate", "repair", "revise"}
)
_INCOMPLETE_FINISH_REASONS = frozenset(
    {"length", "content_filter", "insufficient_system_resource"}
)


class ResponseCompletionMode(StrEnum):
    """How a policy treats a non-deliverable provider response."""

    STRICT = "strict"
    CANDIDATE_FRESH_RECOVERY = "candidate_fresh_recovery"


class ResponseDisposition(StrEnum):
    """The only decisions a policy classifier can return."""

    COMPLETE_TEXT = "complete_text"
    TOOL_CALLS_READY = "tool_calls_ready"
    FAIL_CLOSED = "fail_closed"
    CANDIDATE_ELIGIBLE = "candidate_eligible"


@dataclass(frozen=True, slots=True)
class ResponseBoundarySnapshot:
    """Sanitized response shape; never stores response or reasoning text."""

    finish_reason: str | None
    content_state: ResponseFieldState
    reasoning_content_state: ResponseFieldState
    tool_call_count: int
    usage_state: ResponseUsageState

    def __post_init__(self) -> None:
        if self.finish_reason is not None:
            if not isinstance(self.finish_reason, str):
                raise ValueError("finish_reason must be a safe code or None")
            normalized_finish_reason = self.finish_reason.strip().lower()
            if not _SAFE_CODE.fullmatch(normalized_finish_reason):
                raise ValueError("finish_reason must be a safe code or None")
            object.__setattr__(self, "finish_reason", normalized_finish_reason)

        for field_name in ("content_state", "reasoning_content_state"):
            value = getattr(self, field_name)
            if value not in _FIELD_STATES:
                raise ValueError(f"{field_name} must be a sanitized field state")

        if (
            isinstance(self.tool_call_count, bool)
            or not isinstance(self.tool_call_count, int)
            or self.tool_call_count < 0
        ):
            raise ValueError("tool_call_count must be a non-negative integer")
        if self.usage_state not in _USAGE_STATES:
            raise ValueError("usage_state must be valid, missing, or invalid")


@dataclass(frozen=True, slots=True)
class ResponseRequestContext:
    """Trusted, bounded context used only for future recovery eligibility."""

    phase: ResponsePhase
    has_response_contract: bool
    has_tools: bool
    has_tool_side_effects: bool
    remaining_timeout_s: float
    remaining_token_budget: int

    def __post_init__(self) -> None:
        if self.phase not in _PHASES:
            raise ValueError("phase is not an allowed response phase")
        for field_name in (
            "has_response_contract",
            "has_tools",
            "has_tool_side_effects",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise ValueError(f"{field_name} must be a boolean")
        if (
            isinstance(self.remaining_timeout_s, bool)
            or not isinstance(self.remaining_timeout_s, (int, float))
            or not isfinite(self.remaining_timeout_s)
            or self.remaining_timeout_s < 0
            or self.remaining_timeout_s > 300
        ):
            raise ValueError("remaining_timeout_s must be in [0, 300]")
        if (
            isinstance(self.remaining_token_budget, bool)
            or not isinstance(self.remaining_token_budget, int)
            or self.remaining_token_budget < 0
        ):
            raise ValueError("remaining_token_budget must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class ResponseCompletionDecision:
    """Body-free result of applying one completion policy."""

    disposition: ResponseDisposition
    reason_code: str
    error_code: str | None
    candidate_eligible: bool
    continuation_allowed: bool
    max_additional_calls: int

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, ResponseDisposition):
            raise ValueError("disposition must be a ResponseDisposition")
        if not isinstance(self.reason_code, str) or not _SAFE_CODE.fullmatch(
            self.reason_code
        ):
            raise ValueError("reason_code must be a safe code")
        if self.error_code is not None and (
            not isinstance(self.error_code, str)
            or not _SAFE_CODE.fullmatch(self.error_code)
        ):
            raise ValueError("error_code must be a safe code or None")
        if not isinstance(self.candidate_eligible, bool):
            raise ValueError("candidate_eligible must be a boolean")
        if not isinstance(self.continuation_allowed, bool):
            raise ValueError("continuation_allowed must be a boolean")
        if (
            isinstance(self.max_additional_calls, bool)
            or not isinstance(self.max_additional_calls, int)
            or not 0 <= self.max_additional_calls <= 1
        ):
            raise ValueError("max_additional_calls must be 0 or 1")
        if self.continuation_allowed and not self.candidate_eligible:
            raise ValueError(
                "continuation_allowed requires candidate_eligible"
            )
        if self.continuation_allowed and self.max_additional_calls != 1:
            raise ValueError(
                "continuation_allowed requires one additional call"
            )
        if self.disposition is ResponseDisposition.FAIL_CLOSED:
            if self.error_code is None:
                raise ValueError("fail-closed decisions require an error code")
            if self.candidate_eligible or self.continuation_allowed:
                raise ValueError("fail-closed decisions cannot be recoverable")
        if self.disposition is ResponseDisposition.CANDIDATE_ELIGIBLE:
            if not self.candidate_eligible:
                raise ValueError("candidate disposition requires eligibility")
            if self.error_code != "incomplete_chat_response":
                raise ValueError(
                    "candidate disposition must retain the incomplete error"
                )


@dataclass(frozen=True, slots=True)
class ResponseCompletionPolicy:
    """Immutable policy bound to one exact model runtime identity.

    ``activation_state='candidate'`` is intentionally not a runtime
    registration.  It lets offline tests prove the narrow recovery shape
    without granting a caller permission to make a second provider request.
    """

    policy_id: str
    version: str
    provider_id: str
    model: str
    runtime_profile_id: str
    runtime_profile_version: str
    mode: ResponseCompletionMode
    activation_state: ActivationState
    max_output_tokens: int
    max_additional_calls: int
    minimum_recovery_timeout_s: float
    minimum_recovery_token_budget: int
    allow_partial_content: bool = False
    require_exact_reasoning_replay: bool = True

    def __post_init__(self) -> None:
        for field_name in (
            "policy_id",
            "provider_id",
            "model",
            "runtime_profile_id",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not _SAFE_CODE.fullmatch(value.strip().lower()):
                raise ValueError(f"{field_name} must be a safe identifier")
            object.__setattr__(self, field_name, value.strip().lower())
        for field_name in ("version", "runtime_profile_version"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not _SEMVER.fullmatch(value.strip()):
                raise ValueError(f"{field_name} must be semantic version")
            object.__setattr__(self, field_name, value.strip())
        if not isinstance(self.mode, ResponseCompletionMode):
            raise ValueError("mode must be a ResponseCompletionMode")
        if self.activation_state not in {"registered", "candidate"}:
            raise ValueError("activation_state must be registered or candidate")
        if (
            isinstance(self.max_output_tokens, bool)
            or not isinstance(self.max_output_tokens, int)
            or not 1 <= self.max_output_tokens <= 131072
        ):
            raise ValueError("max_output_tokens must be between 1 and 131072")
        if (
            isinstance(self.max_additional_calls, bool)
            or not isinstance(self.max_additional_calls, int)
            or not 0 <= self.max_additional_calls <= 1
        ):
            raise ValueError("max_additional_calls must be 0 or 1")
        if self.mode is ResponseCompletionMode.STRICT and self.max_additional_calls:
            raise ValueError("strict policy cannot allow additional calls")
        if (
            isinstance(self.minimum_recovery_timeout_s, bool)
            or not isinstance(self.minimum_recovery_timeout_s, (int, float))
            or not isfinite(self.minimum_recovery_timeout_s)
            or not 0 < self.minimum_recovery_timeout_s <= 300
        ):
            raise ValueError("minimum_recovery_timeout_s must be in (0, 300]")
        if (
            isinstance(self.minimum_recovery_token_budget, bool)
            or not isinstance(self.minimum_recovery_token_budget, int)
            or self.minimum_recovery_token_budget < 1
        ):
            raise ValueError("minimum_recovery_token_budget must be positive")
        if not isinstance(self.allow_partial_content, bool):
            raise ValueError("allow_partial_content must be a boolean")
        if not isinstance(self.require_exact_reasoning_replay, bool):
            raise ValueError(
                "require_exact_reasoning_replay must be a boolean"
            )

    def matches_runtime(
        self,
        *,
        provider_id: str,
        model: str,
        runtime_profile_id: str,
        runtime_profile_version: str,
    ) -> bool:
        """Require exact identity; metadata cannot select a policy."""

        return (
            isinstance(provider_id, str)
            and isinstance(model, str)
            and isinstance(runtime_profile_id, str)
            and isinstance(runtime_profile_version, str)
            and provider_id.strip().lower() == self.provider_id
            and model.strip().lower() == self.model
            and runtime_profile_id.strip().lower() == self.runtime_profile_id
            and runtime_profile_version.strip() == self.runtime_profile_version
        )

    def clamp_output_tokens(self, requested: int | None) -> int:
        """Apply the policy cap without allowing caller-side escalation."""

        if requested is None:
            return self.max_output_tokens
        if (
            isinstance(requested, bool)
            or not isinstance(requested, int)
            or requested < 1
        ):
            raise ValueError("requested output tokens must be a positive integer")
        return min(requested, self.max_output_tokens)

    def decide(
        self,
        snapshot: ResponseBoundarySnapshot,
        context: ResponseRequestContext,
    ) -> ResponseCompletionDecision:
        """Classify one sanitized response without performing any I/O."""

        if not isinstance(snapshot, ResponseBoundarySnapshot):
            raise TypeError("snapshot must be a ResponseBoundarySnapshot")
        if not isinstance(context, ResponseRequestContext):
            raise TypeError("context must be a ResponseRequestContext")

        if snapshot.usage_state != "valid":
            return _failed("usage_unavailable", "provider_usage_unavailable")

        finish_reason = snapshot.finish_reason
        if finish_reason is None:
            return _failed("missing_finish_reason", "invalid_chat_response")

        if finish_reason == "stop":
            if snapshot.tool_call_count:
                return _failed(
                    "stop_with_tool_calls",
                    "invalid_tool_call_response",
                )
            if snapshot.content_state != "non_empty":
                return _failed("stop_without_text", "invalid_chat_response")
            return _decision(
                ResponseDisposition.COMPLETE_TEXT,
                reason_code="complete_text",
            )

        if finish_reason == "tool_calls":
            if snapshot.tool_call_count == 0:
                return _failed(
                    "tool_finish_without_calls",
                    "invalid_tool_call_response",
                )
            return _decision(
                ResponseDisposition.TOOL_CALLS_READY,
                reason_code="tool_calls_ready",
            )

        if finish_reason in _INCOMPLETE_FINISH_REASONS:
            if finish_reason == "length":
                candidate_reason = self._candidate_rejection_reason(
                    snapshot,
                    context,
                )
                if candidate_reason is None:
                    continuation_allowed = (
                        self.activation_state == "registered"
                        and self.mode is ResponseCompletionMode.CANDIDATE_FRESH_RECOVERY
                        and self.max_additional_calls == 1
                    )
                    return ResponseCompletionDecision(
                        disposition=ResponseDisposition.CANDIDATE_ELIGIBLE,
                        reason_code="fresh_recovery_shape_eligible",
                        error_code="incomplete_chat_response",
                        candidate_eligible=True,
                        continuation_allowed=continuation_allowed,
                        max_additional_calls=(1 if continuation_allowed else 0),
                    )
                if self.mode is ResponseCompletionMode.STRICT:
                    candidate_reason = _strict_length_reason(snapshot)
                return _failed(candidate_reason, "incomplete_chat_response")
            return _failed(finish_reason, "incomplete_chat_response")

        return _failed("unknown_finish_reason", "invalid_finish_reason")

    def _candidate_rejection_reason(
        self,
        snapshot: ResponseBoundarySnapshot,
        context: ResponseRequestContext,
    ) -> str | None:
        if self.mode is not ResponseCompletionMode.CANDIDATE_FRESH_RECOVERY:
            return _strict_length_reason(snapshot)
        if snapshot.content_state != "empty":
            return (
                "length_partial_content"
                if snapshot.content_state == "non_empty"
                else "length_content_state_not_empty"
            )
        if snapshot.reasoning_content_state != "non_empty":
            return "length_without_reasoning"
        if snapshot.tool_call_count:
            return "length_with_tool_calls"
        if context.phase != "agent_initial":
            return "recovery_phase_not_allowed"
        if context.has_response_contract:
            return "recovery_response_contract_present"
        if context.has_tools:
            return "recovery_tools_present"
        if context.has_tool_side_effects:
            return "recovery_tool_side_effects_present"
        if context.remaining_timeout_s < self.minimum_recovery_timeout_s:
            return "recovery_timeout_insufficient"
        if context.remaining_token_budget < self.minimum_recovery_token_budget:
            return "recovery_token_budget_insufficient"
        if not self.require_exact_reasoning_replay:
            return "recovery_reasoning_replay_unbound"
        return None


def _strict_length_reason(snapshot: ResponseBoundarySnapshot) -> str:
    if snapshot.tool_call_count:
        return "length_with_tool_calls"
    if snapshot.content_state == "non_empty":
        return "length_partial_content"
    if snapshot.content_state == "empty" and snapshot.reasoning_content_state == "non_empty":
        return "length_reasoning_only"
    return "length_without_deliverable"


def _failed(reason_code: str, error_code: str) -> ResponseCompletionDecision:
    return ResponseCompletionDecision(
        disposition=ResponseDisposition.FAIL_CLOSED,
        reason_code=reason_code,
        error_code=error_code,
        candidate_eligible=False,
        continuation_allowed=False,
        max_additional_calls=0,
    )


def _decision(
    disposition: ResponseDisposition,
    *,
    reason_code: str,
) -> ResponseCompletionDecision:
    return ResponseCompletionDecision(
        disposition=disposition,
        reason_code=reason_code,
        error_code=None,
        candidate_eligible=False,
        continuation_allowed=False,
        max_additional_calls=0,
    )


# The strict policy is the only policy registered with the current runtime.
GLM53_FLASH_RESPONSE_COMPLETION_POLICY_V1 = ResponseCompletionPolicy(
    policy_id="glm-5.3-flash-response-completion-v1",
    version="1.0.0",
    provider_id="zhipu",
    model="glm-5.3-flash",
    runtime_profile_id="glm-5.3-flash-runtime-v1",
    runtime_profile_version="1.0.0",
    mode=ResponseCompletionMode.STRICT,
    activation_state="registered",
    max_output_tokens=2048,
    max_additional_calls=0,
    minimum_recovery_timeout_s=30.0,
    minimum_recovery_token_budget=2048,
)

# This object is deliberately a candidate only.  Its larger request cap and
# one-call recovery slot need a new runtime profile, budget ledger, and trace
# contract before they can be activated or used for a real diagnostic.
GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1 = ResponseCompletionPolicy(
    policy_id="glm-5.3-flash-fresh-recovery-candidate-v1",
    version="1.0.0",
    provider_id="zhipu",
    model="glm-5.3-flash",
    runtime_profile_id="glm-5.3-flash-runtime-v2-candidate",
    runtime_profile_version="2.0.0",
    mode=ResponseCompletionMode.CANDIDATE_FRESH_RECOVERY,
    activation_state="candidate",
    max_output_tokens=8192,
    max_additional_calls=1,
    minimum_recovery_timeout_s=30.0,
    minimum_recovery_token_budget=8192,
)


def resolve_response_completion_policy(
    *,
    provider_id: str,
    model: str,
    runtime_profile_id: str,
    runtime_profile_version: str,
) -> ResponseCompletionPolicy | None:
    """Resolve only the currently registered exact policy."""

    policy = GLM53_FLASH_RESPONSE_COMPLETION_POLICY_V1
    if policy.matches_runtime(
        provider_id=provider_id,
        model=model,
        runtime_profile_id=runtime_profile_id,
        runtime_profile_version=runtime_profile_version,
    ):
        return policy
    return None


def require_registered_response_completion_policy(
    policy: ResponseCompletionPolicy,
) -> ResponseCompletionPolicy:
    """Reject candidate or forged policies at a future composition boundary."""

    if not isinstance(policy, ResponseCompletionPolicy):
        raise TypeError("policy must be a ResponseCompletionPolicy")
    registered = resolve_response_completion_policy(
        provider_id=policy.provider_id,
        model=policy.model,
        runtime_profile_id=policy.runtime_profile_id,
        runtime_profile_version=policy.runtime_profile_version,
    )
    if registered is None or policy != registered:
        raise ValueError("response completion policy is not registered")
    return registered


__all__ = [
    "GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1",
    "GLM53_FLASH_RESPONSE_COMPLETION_POLICY_V1",
    "ResponseBoundarySnapshot",
    "ResponseCompletionDecision",
    "ResponseCompletionMode",
    "ResponseCompletionPolicy",
    "ResponseDisposition",
    "ResponseFieldState",
    "ResponseRequestContext",
    "ResponseUsageState",
    "require_registered_response_completion_policy",
    "resolve_response_completion_policy",
]
