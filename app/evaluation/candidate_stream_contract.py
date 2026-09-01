"""Candidate-only, body-free stream boundary contracts.

This module is the first implementation step after the GLM-5.3 candidate
runtime wiring design.  It deliberately lives below the product runtime:

* ``CandidateRuntimeBinding`` accepts one exact candidate identity and one
  attempt ordinal.
* ``CandidateStreamBoundaryObserver`` consumes already-normalized provider
  events without retaining response text, reasoning, or tool arguments.
* ``CandidateZhipuStreamTransport`` is an injected/fake-only port.  It does
  not import an SDK and cannot discover a product provider from a registry.

The complete-response contract remains ``ProviderStreamAssembler``.  This
module only observes the narrow boundary around a stream so a later,
separately authorized harness can decide what to do.  No recovery request is
performed here and the candidate profile remains execution-disabled.
"""

from __future__ import annotations

import hashlib
import re
import time
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass, field, replace
from enum import StrEnum
from math import isfinite
from typing import Any, Literal, Protocol, TypeAlias, runtime_checkable

from app.providers.models import ChatRequest, TokenUsage
from app.providers.response_completion_policy import (
    GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1,
    ResponseBoundarySnapshot,
    ResponseCompletionDecision,
    ResponseCompletionPolicy,
    ResponseDisposition,
    ResponseFieldState,
    ResponseRequestContext,
    ResponseUsageState,
)
from app.providers.response_recovery_contract import (
    GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1,
)
from app.providers.stream_adapter_contract import (
    ProviderStreamEvent,
    StreamAdapterError,
    StreamToolCallDelta,
    validate_provider_stream_event,
)


_SAFE_ID = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
_SAFE_CODE = re.compile(r"^[a-z][a-z0-9_.-]{0,95}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
_FINISH_REASONS = frozenset(
    {
        "stop",
        "tool_calls",
        "length",
        "content_filter",
        "insufficient_system_resource",
    }
)
_INCOMPLETE_FINISH_REASONS = frozenset(
    {"length", "content_filter", "insufficient_system_resource"}
)
_FIELD_STATES = frozenset(
    {"not_observed", "missing", "null", "empty", "non_empty", "non_string"}
)
_USAGE_STATES = frozenset({"valid", "missing", "invalid"})
_MAX_EVENTS = 131_072
_MAX_TEXT_CHARS = 4_000_000
_MAX_TOOL_INDEX = 4_096
_MAX_TOOL_CALLS = 128
_MAX_TOOL_ARGUMENT_CHARS = 256_000
_MAX_ELAPSED_MS = 180_000
_UNSET = object()

CandidateFieldState: TypeAlias = ResponseFieldState
CandidateUsageState: TypeAlias = ResponseUsageState
CandidateCloseState: TypeAlias = Literal[
    "not_observed", "open", "closed", "failed"
]
CandidateObservationState: TypeAlias = Literal[
    "not_started",
    "awaiting_primary",
    "observing_primary",
    "candidate_shape",
    "awaiting_recovery",
    "complete_text",
    "tool_calls_ready",
    "fail_closed",
]
CandidateNextAction: TypeAlias = Literal[
    "observe",
    "classify",
    "requires_registered_runtime",
    "terminal_complete",
    "terminal_tool_calls",
    "terminal_fail_closed",
]


class CandidateBoundaryContractError(ValueError):
    """Safe error raised by candidate boundary contracts.

    Only a bounded machine code and stage are retained.  Callers must not
    pass provider/HTTP exception text here.
    """

    def __init__(self, code: str, stage: str | None = None) -> None:
        _require_safe_code(code, "error code")
        if stage is not None:
            _require_safe_code(stage, "error stage")
        # Error values are machine-facing identifiers.  Normalize them once
        # at the boundary so a caller cannot create two spellings of the same
        # safe code in a trace or recovery decision.
        self.code = code.strip().lower()
        self.stage = stage.strip().lower() if stage is not None else None
        super().__init__(self.code)


class CandidateIdentityError(CandidateBoundaryContractError):
    """The exact candidate binding or attempt identity is invalid."""


class CandidateObservationError(CandidateBoundaryContractError):
    """A normalized stream violated the candidate observation contract."""


class CandidateTransportError(CandidateBoundaryContractError):
    """The injected candidate transport port was used incorrectly."""


class CandidateAttemptKind(StrEnum):
    """The only attempt kinds allowed by the candidate contract."""

    PRIMARY = "primary"
    FRESH_RECOVERY = "fresh_recovery"


CANDIDATE_SCHEMA_VERSION = "1.0"
CANDIDATE_PROVIDER_ID = "zhipu"
CANDIDATE_MODEL = "glm-5.3-flash"
CANDIDATE_RUNTIME_PROFILE_ID = (
    "glm-5.3-flash-runtime-v2-candidate"
)
CANDIDATE_RUNTIME_PROFILE_VERSION = "2.0.0"
CANDIDATE_POLICY_ID = "glm-5.3-flash-fresh-recovery-candidate-v1"
CANDIDATE_POLICY_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class CandidateRuntimeBinding:
    """Immutable identity for one candidate provider attempt.

    The defaults describe the primary attempt.  Every field is checked
    against trusted constants in ``__post_init__``; matching arbitrary
    metadata is not enough to create a usable binding.
    """

    provider_id: str = CANDIDATE_PROVIDER_ID
    model: str = CANDIDATE_MODEL
    runtime_profile_id: str = CANDIDATE_RUNTIME_PROFILE_ID
    runtime_profile_version: str = CANDIDATE_RUNTIME_PROFILE_VERSION
    policy_id: str = CANDIDATE_POLICY_ID
    policy_version: str = CANDIDATE_POLICY_VERSION
    attempt_ordinal: int = 1
    attempt_kind: CandidateAttemptKind = CandidateAttemptKind.PRIMARY
    activation_state: Literal["candidate"] = "candidate"
    execution_allowed: bool = False

    def __post_init__(self) -> None:
        for field_name in (
            "provider_id",
            "model",
            "runtime_profile_id",
            "policy_id",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not _SAFE_ID.fullmatch(value.strip().lower()):
                raise CandidateIdentityError("candidate_identity_mismatch", "identity")
            normalized = value.strip().lower()
            if value.strip() != normalized:
                raise CandidateIdentityError("candidate_identity_mismatch", "identity")
            object.__setattr__(self, field_name, normalized)
        for field_name in ("runtime_profile_version", "policy_version"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not _SEMVER.fullmatch(value.strip()):
                raise CandidateIdentityError("candidate_identity_mismatch", "identity")
            if value.strip() != value:
                raise CandidateIdentityError("candidate_identity_mismatch", "identity")
            object.__setattr__(self, field_name, value)
        try:
            kind = (
                self.attempt_kind
                if isinstance(self.attempt_kind, CandidateAttemptKind)
                else CandidateAttemptKind(self.attempt_kind)
            )
        except (TypeError, ValueError):
            raise CandidateIdentityError("candidate_attempt_mismatch", "attempt") from None
        object.__setattr__(self, "attempt_kind", kind)
        if (
            isinstance(self.attempt_ordinal, bool)
            or not isinstance(self.attempt_ordinal, int)
            or self.attempt_ordinal not in {1, 2}
        ):
            raise CandidateIdentityError("candidate_attempt_mismatch", "attempt")
        expected_kind = (
            CandidateAttemptKind.PRIMARY
            if self.attempt_ordinal == 1
            else CandidateAttemptKind.FRESH_RECOVERY
        )
        if kind is not expected_kind:
            raise CandidateIdentityError("candidate_attempt_mismatch", "attempt")
        if self.activation_state != "candidate":
            raise CandidateIdentityError("candidate_activation_mismatch", "identity")
        if self.execution_allowed is not False:
            raise CandidateIdentityError("candidate_execution_disabled", "identity")
        if self.identity_tuple != _CANDIDATE_IDENTITY:
            raise CandidateIdentityError("candidate_identity_mismatch", "identity")

    @property
    def identity_tuple(self) -> tuple[str, str, str, str, str, str]:
        return (
            self.provider_id,
            self.model,
            self.runtime_profile_id,
            self.runtime_profile_version,
            self.policy_id,
            self.policy_version,
        )

    @classmethod
    def primary(cls) -> "CandidateRuntimeBinding":
        return PRIMARY_CANDIDATE_BINDING

    @classmethod
    def fresh_recovery(cls) -> "CandidateRuntimeBinding":
        return FRESH_RECOVERY_CANDIDATE_BINDING

    @classmethod
    def for_attempt(cls, ordinal: int) -> "CandidateRuntimeBinding":
        if ordinal == 1:
            return cls.primary()
        if ordinal == 2:
            return cls.fresh_recovery()
        raise CandidateIdentityError("candidate_attempt_mismatch", "attempt")


_CANDIDATE_IDENTITY = (
    CANDIDATE_PROVIDER_ID,
    CANDIDATE_MODEL,
    CANDIDATE_RUNTIME_PROFILE_ID,
    CANDIDATE_RUNTIME_PROFILE_VERSION,
    CANDIDATE_POLICY_ID,
    CANDIDATE_POLICY_VERSION,
)


PRIMARY_CANDIDATE_BINDING = CandidateRuntimeBinding()
FRESH_RECOVERY_CANDIDATE_BINDING = CandidateRuntimeBinding(
    attempt_ordinal=2,
    attempt_kind=CandidateAttemptKind.FRESH_RECOVERY,
)


def require_exact_candidate_binding(
    binding: CandidateRuntimeBinding,
) -> CandidateRuntimeBinding:
    """Return a trusted binding or fail before any provider I/O."""

    if type(binding) is not CandidateRuntimeBinding:
        raise CandidateIdentityError("candidate_binding_type", "identity")
    expected = (
        PRIMARY_CANDIDATE_BINDING
        if binding.attempt_ordinal == 1
        else FRESH_RECOVERY_CANDIDATE_BINDING
    )
    if binding != expected:
        raise CandidateIdentityError("candidate_identity_mismatch", "identity")
    return binding


@dataclass(frozen=True, slots=True)
class BoundaryObservation:
    """One immutable, allow-listed observation with no response body.

    ``candidate_eligible`` is intentionally absent.  A complete observation
    may be converted to ``ResponseBoundarySnapshot`` and classified by the
    versioned policy; callers cannot inject a qualification bit.
    """

    binding: CandidateRuntimeBinding = field(default_factory=CandidateRuntimeBinding.primary)
    schema_version: Literal["1.0"] = CANDIDATE_SCHEMA_VERSION
    opened: bool = False
    eof_observed: bool = False
    terminal_observed: bool = False
    close_state: CandidateCloseState = "not_observed"
    finish_reason: str | None = None
    content_state: CandidateFieldState = "not_observed"
    reasoning_content_state: CandidateFieldState = "not_observed"
    tool_call_count: int = 0
    usage_state: CandidateUsageState = "missing"
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_input_tokens: int | None = None
    elapsed_ms: int = 0
    resolved_model: str | None = None
    request_id_sha256: str | None = None
    error_code: str | None = None
    error_stage: str | None = None
    observation_state: CandidateObservationState = "not_started"
    next_action: CandidateNextAction = "observe"

    def __post_init__(self) -> None:
        require_exact_candidate_binding(self.binding)
        if self.schema_version != CANDIDATE_SCHEMA_VERSION:
            raise CandidateObservationError("unsupported_observation_schema", "schema")
        for field_name in ("opened", "eof_observed", "terminal_observed"):
            if not isinstance(getattr(self, field_name), bool):
                raise CandidateObservationError("lifecycle_state_invalid", "lifecycle")
        if not isinstance(self.close_state, str) or self.close_state not in {
            "not_observed",
            "open",
            "closed",
            "failed",
        }:
            raise CandidateObservationError("close_state_invalid", "lifecycle")
        if not self.opened and self.close_state != "not_observed":
            raise CandidateObservationError("close_without_open", "lifecycle")
        if self.opened and self.close_state == "not_observed":
            raise CandidateObservationError("open_without_close_state", "lifecycle")
        if self.eof_observed and not self.opened:
            raise CandidateObservationError("eof_without_open", "lifecycle")
        if self.terminal_observed and not self.opened:
            raise CandidateObservationError("terminal_without_open", "lifecycle")
        if self.close_state != "not_observed" and not self.opened:
            raise CandidateObservationError("close_without_open", "lifecycle")
        if self.close_state == "closed" and not self.eof_observed:
            raise CandidateObservationError("close_before_eof", "lifecycle")
        if self.finish_reason is not None:
            _require_safe_code(self.finish_reason, "finish reason")
            normalized = self.finish_reason.strip().lower()
            if normalized not in _FINISH_REASONS:
                raise CandidateObservationError("invalid_finish_reason", "terminal")
            object.__setattr__(self, "finish_reason", normalized)
            if not self.terminal_observed:
                raise CandidateObservationError("finish_without_terminal", "terminal")
        if self.terminal_observed and self.finish_reason is None:
            raise CandidateObservationError("terminal_without_finish", "terminal")
        for field_name in ("content_state", "reasoning_content_state"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or value not in _FIELD_STATES:
                raise CandidateObservationError("field_state_invalid", "shape")
        if (
            isinstance(self.tool_call_count, bool)
            or not isinstance(self.tool_call_count, int)
            or not 0 <= self.tool_call_count <= _MAX_TOOL_CALLS
        ):
            raise CandidateObservationError("tool_count_invalid", "shape")
        if not isinstance(self.usage_state, str) or self.usage_state not in _USAGE_STATES:
            raise CandidateObservationError("usage_state_invalid", "usage")
        if self.usage_state == "valid":
            if not self.terminal_observed:
                raise CandidateObservationError("usage_before_terminal", "usage")
            for field_name in (
                "input_tokens",
                "output_tokens",
                "cached_input_tokens",
            ):
                _require_non_negative_int(getattr(self, field_name), field_name)
            if self.cached_input_tokens > self.input_tokens:  # type: ignore[operator]
                raise CandidateObservationError("invalid_usage", "usage")
        elif any(
            getattr(self, field_name) is not None
            for field_name in ("input_tokens", "output_tokens", "cached_input_tokens")
        ):
            raise CandidateObservationError("unknown_usage_has_tokens", "usage")
        _require_non_negative_int(self.elapsed_ms, "elapsed_ms")
        if self.elapsed_ms > _MAX_ELAPSED_MS:
            raise CandidateObservationError("elapsed_limit", "budget")
        if self.resolved_model is not None:
            _require_safe_identifier(self.resolved_model, "resolved_model")
            normalized_model = self.resolved_model.strip().lower()
            if normalized_model != self.binding.model:
                raise CandidateObservationError("model_mismatch", "identity")
            object.__setattr__(self, "resolved_model", normalized_model)
        if self.request_id_sha256 is not None:
            if not isinstance(self.request_id_sha256, str) or not _SHA256.fullmatch(
                self.request_id_sha256
            ):
                raise CandidateObservationError("request_identity_invalid", "identity")
        for field_name in ("error_code", "error_stage"):
            value = getattr(self, field_name)
            if value is not None:
                _require_safe_code(value, field_name)
                object.__setattr__(self, field_name, value.strip().lower())
        if not isinstance(self.observation_state, str) or self.observation_state not in {
            "not_started",
            "awaiting_primary",
            "observing_primary",
            "candidate_shape",
            "awaiting_recovery",
            "complete_text",
            "tool_calls_ready",
            "fail_closed",
        }:
            raise CandidateObservationError("observation_state_invalid", "state")
        if self.observation_state == "fail_closed" and self.error_code is None:
            raise CandidateObservationError("failed_state_without_error", "state")
        if self.observation_state != "fail_closed" and self.error_code is not None:
            raise CandidateObservationError("error_state_mismatch", "state")
        if self.error_stage is not None and self.error_code is None:
            raise CandidateObservationError("error_stage_without_error", "state")
        if not isinstance(self.next_action, str) or self.next_action not in {
            "observe",
            "classify",
            "requires_registered_runtime",
            "terminal_complete",
            "terminal_tool_calls",
            "terminal_fail_closed",
        }:
            raise CandidateObservationError("next_action_invalid", "state")
        if self.close_state == "failed" and self.error_code is None:
            raise CandidateObservationError("failed_close_without_error", "lifecycle")

        # ``observation_state`` and ``next_action`` are derived fields, not
        # caller-provided qualifications.  Keep the value object honest even
        # when somebody constructs it directly instead of using the observer.
        expected_action = {
            "not_started": "observe",
            "awaiting_primary": "observe",
            "observing_primary": "observe",
            "candidate_shape": "requires_registered_runtime",
            "awaiting_recovery": "requires_registered_runtime",
            "complete_text": "terminal_complete",
            "tool_calls_ready": "terminal_tool_calls",
            "fail_closed": "terminal_fail_closed",
        }[self.observation_state]
        if self.next_action != expected_action:
            raise CandidateObservationError("state_action_mismatch", "state")

        if self.observation_state == "not_started":
            if self.opened or self.error_code is not None:
                raise CandidateObservationError("state_lifecycle_mismatch", "state")
        elif self.observation_state == "awaiting_primary":
            if self.opened or self.error_code is not None:
                raise CandidateObservationError("state_lifecycle_mismatch", "state")
        elif self.observation_state == "observing_primary":
            if not self.opened or self.error_code is not None:
                raise CandidateObservationError("state_lifecycle_mismatch", "state")
        elif self.observation_state == "fail_closed":
            if self.error_code is None:
                raise CandidateObservationError("failed_state_without_error", "state")
        else:
            # Every positive boundary conclusion requires the same closed
            # lifecycle evidence used by ``complete_boundary``.
            if not self.complete_boundary:
                raise CandidateObservationError("state_boundary_incomplete", "state")
            if self.observation_state == "candidate_shape":
                if (
                    self.finish_reason != "length"
                    or self.content_state != "empty"
                    or self.reasoning_content_state != "non_empty"
                    or self.tool_call_count != 0
                ):
                    raise CandidateObservationError("state_shape_mismatch", "state")
            elif self.observation_state == "complete_text":
                if (
                    self.finish_reason != "stop"
                    or self.content_state != "non_empty"
                    or self.tool_call_count != 0
                ):
                    raise CandidateObservationError("state_shape_mismatch", "state")
            elif self.observation_state == "tool_calls_ready":
                if self.finish_reason != "tool_calls" or self.tool_call_count < 1:
                    raise CandidateObservationError("state_shape_mismatch", "state")

    @property
    def complete_boundary(self) -> bool:
        """Whether enough lifecycle/resource evidence exists for policy use."""

        return (
            self.opened
            and self.eof_observed
            and self.terminal_observed
            and self.close_state == "closed"
            and self.usage_state == "valid"
            and self.error_code is None
        )

    def to_response_boundary_snapshot(self) -> ResponseBoundarySnapshot:
        """Map only a fully closed observation to the existing policy shape."""

        if not self.complete_boundary:
            raise CandidateObservationError("observation_not_complete", "boundary")
        return ResponseBoundarySnapshot(
            finish_reason=self.finish_reason,
            content_state=self.content_state,
            reasoning_content_state=self.reasoning_content_state,
            tool_call_count=self.tool_call_count,
            usage_state=self.usage_state,
        )

    def classify(
        self,
        *,
        policy: ResponseCompletionPolicy = GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1,
        context: ResponseRequestContext,
    ) -> ResponseCompletionDecision:
        """Recompute a policy decision; never trust caller eligibility flags."""

        require_exact_candidate_binding(self.binding)
        if not isinstance(policy, ResponseCompletionPolicy):
            raise TypeError("policy must be a ResponseCompletionPolicy")
        if policy != GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1:
            raise CandidateIdentityError("candidate_policy_mismatch", "identity")
        if not policy.matches_runtime(
            provider_id=self.binding.provider_id,
            model=self.binding.model,
            runtime_profile_id=self.binding.runtime_profile_id,
            runtime_profile_version=self.binding.runtime_profile_version,
        ):
            raise CandidateIdentityError("candidate_policy_mismatch", "identity")
        return policy.decide(self.to_response_boundary_snapshot(), context)

    def as_dict(self) -> dict[str, Any]:
        """Return the explicit body-free serialization allow-list."""

        return {
            "schema_version": self.schema_version,
            "provider_id": self.binding.provider_id,
            "model": self.binding.model,
            "runtime_profile_id": self.binding.runtime_profile_id,
            "runtime_profile_version": self.binding.runtime_profile_version,
            "policy_id": self.binding.policy_id,
            "policy_version": self.binding.policy_version,
            "attempt_ordinal": self.binding.attempt_ordinal,
            "attempt_kind": self.binding.attempt_kind.value,
            "activation_state": self.binding.activation_state,
            "execution_allowed": self.binding.execution_allowed,
            "opened": self.opened,
            "eof_observed": self.eof_observed,
            "terminal_observed": self.terminal_observed,
            "close_state": self.close_state,
            "finish_reason": self.finish_reason,
            "content_state": self.content_state,
            "reasoning_content_state": self.reasoning_content_state,
            "tool_call_count": self.tool_call_count,
            "usage_state": self.usage_state,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cached_input_tokens": self.cached_input_tokens,
            "elapsed_ms": self.elapsed_ms,
            "resolved_model": self.resolved_model,
            "request_id_sha256": self.request_id_sha256,
            "error_code": self.error_code,
            "error_stage": self.error_stage,
            "observation_state": self.observation_state,
            "next_action": self.next_action,
        }


class CandidateStreamBoundaryObserver:
    """O(1) observer for normalized provider stream events.

    It validates lifecycle, identity, terminal, Usage, and tool metadata while
    retaining only booleans, field-state ranks, bounded counters, and hashes.
    Response text, reasoning text, and tool argument strings are never stored.
    """

    def __init__(
        self,
        binding: CandidateRuntimeBinding | None = None,
        *,
        clock: Callable[[], float] = time.monotonic,
        max_events: int = _MAX_EVENTS,
        max_output_tokens: int = 8192,
        max_content_chars: int = _MAX_TEXT_CHARS,
        max_reasoning_chars: int = _MAX_TEXT_CHARS,
        max_tool_calls: int = _MAX_TOOL_CALLS,
        max_tool_argument_chars: int = _MAX_TOOL_ARGUMENT_CHARS,
        max_elapsed_ms: int = _MAX_ELAPSED_MS,
        require_model_observation: bool = True,
        require_request_identity: bool = True,
    ) -> None:
        self._binding = require_exact_candidate_binding(
            binding or CandidateRuntimeBinding.primary()
        )
        self._clock = clock
        self._max_events = _require_bounded_int(max_events, 1, _MAX_EVENTS, "max_events")
        self._max_output_tokens = _require_bounded_int(
            max_output_tokens, 1, 8192, "max_output_tokens"
        )
        self._max_content_chars = _require_bounded_int(
            max_content_chars, 1, _MAX_TEXT_CHARS, "max_content_chars"
        )
        self._max_reasoning_chars = _require_bounded_int(
            max_reasoning_chars, 1, _MAX_TEXT_CHARS, "max_reasoning_chars"
        )
        self._max_tool_calls = _require_bounded_int(
            max_tool_calls, 1, _MAX_TOOL_CALLS, "max_tool_calls"
        )
        self._max_tool_argument_chars = _require_bounded_int(
            max_tool_argument_chars,
            1,
            _MAX_TOOL_ARGUMENT_CHARS,
            "max_tool_argument_chars",
        )
        self._max_elapsed_ms = _require_bounded_int(
            max_elapsed_ms, 1, _MAX_ELAPSED_MS, "max_elapsed_ms"
        )
        if not isinstance(require_model_observation, bool):
            raise ValueError("require_model_observation must be a boolean")
        if not isinstance(require_request_identity, bool):
            raise ValueError("require_request_identity must be a boolean")
        self._require_model_observation = require_model_observation
        self._require_request_identity = require_request_identity
        self._opened = False
        self._eof_observed = False
        self._terminal_observed = False
        self._close_state: CandidateCloseState = "not_observed"
        self._finish_reason: str | None = None
        self._resolved_model: str | None = None
        self._request_id_sha256: str | None = None
        self._usage: TokenUsage | None = None
        self._chunk_count = 0
        self._content_chars = 0
        self._reasoning_chars = 0
        self._content_state: CandidateFieldState = "not_observed"
        self._reasoning_state: CandidateFieldState = "not_observed"
        self._tool_indices: set[int] = set()
        self._tool_metadata_hashes: dict[int, tuple[str | None, str | None]] = {}
        self._tool_argument_seen: set[int] = set()
        self._tool_argument_chars = 0
        self._error_code: str | None = None
        self._error_stage: str | None = None
        self._started_at: float | None = None
        self._last_elapsed_ms = 0
        self._finalized = False
        self._final_observation: BoundaryObservation | None = None

    @property
    def binding(self) -> CandidateRuntimeBinding:
        return self._binding

    @property
    def failed_code(self) -> str | None:
        return self._error_code

    @property
    def chunk_count(self) -> int:
        return self._chunk_count

    def open(self) -> None:
        """Start observation after the caller has reserved a candidate slot."""

        self._ensure_healthy()
        if self._opened:
            self._fail_and_raise("duplicate_open", "lifecycle")
        self._started_at = self._read_clock()
        self._opened = True
        self._close_state = "open"

    def accept(self, event: ProviderStreamEvent) -> None:
        """Validate one normalized event without retaining its payload text."""

        self._ensure_healthy()
        if not self._opened:
            self._fail_and_raise("stream_not_opened", "lifecycle")
        if self._eof_observed:
            self._fail_and_raise("event_after_eof", "lifecycle")
        if not isinstance(event, ProviderStreamEvent):
            self._fail_and_raise("invalid_event", "translate")
        ordinal = self._chunk_count + 1
        try:
            validate_provider_stream_event(
                event,
                ordinal=ordinal,
                max_events=self._max_events,
                content_chars_before=self._content_chars,
                reasoning_chars_before=self._reasoning_chars,
                tool_argument_chars_before=self._tool_argument_chars,
                max_content_chars=self._max_content_chars,
                max_reasoning_chars=self._max_reasoning_chars,
                max_tool_calls_per_event=self._max_tool_calls,
                max_tool_argument_chars=self._max_tool_argument_chars,
            )
        except StreamAdapterError as error:
            stage = _stage_for_stream_error(error.code)
            self._fail_and_raise(error.code, stage)
        self._observe_identity(event, ordinal)

        if self._terminal_observed:
            # A provider may send exactly one Usage-only tail frame after the
            # terminal event.  Any body/tool/second terminal payload is unsafe.
            if event.finish_reason is not None:
                self._fail_and_raise("duplicate_terminal", "terminal")
            if (
                event.content_observed
                or event.reasoning_observed
                or event.tool_call_deltas
            ):
                self._fail_and_raise("payload_after_terminal", "terminal")
            if event.usage is None:
                self._fail_and_raise("payload_after_terminal", "terminal")
            if self._usage is not None:
                self._fail_and_raise("duplicate_usage", "usage")
            try:
                self._validate_usage(event.usage)
            except CandidateObservationError as error:
                self._fail_and_raise(error.code, error.stage or "usage")
            self._usage = event.usage
            self._chunk_count = ordinal
            return

        if event.finish_reason is not None:
            finish = event.finish_reason.strip().lower()
            if finish not in _FINISH_REASONS:
                self._fail_and_raise("invalid_finish_reason", "terminal")
            if self._finish_reason is not None:
                self._fail_and_raise("duplicate_terminal", "terminal")
        if event.usage is not None:
            try:
                self._validate_usage(event.usage)
            except CandidateObservationError as error:
                self._fail_and_raise(error.code, error.stage or "usage")
            if event.finish_reason is None:
                self._fail_and_raise("usage_before_terminal", "usage")
            if self._usage is not None:
                self._fail_and_raise("duplicate_usage", "usage")

        # Validate and stage tool metadata first.  The copy-on-write helper
        # ensures a malformed second delta cannot leave the first delta from
        # the same event partially committed.
        self._observe_tool_deltas(event.tool_call_deltas)
        self._observe_field(
            "content",
            event.content_delta,
            observed=event.content_observed,
        )
        self._observe_field(
            "reasoning",
            event.reasoning_delta,
            observed=event.reasoning_observed,
        )

        self._chunk_count = ordinal
        self._content_chars += len(event.content_delta or "")
        self._reasoning_chars += len(event.reasoning_delta or "")
        if event.finish_reason is not None:
            self._finish_reason = event.finish_reason.strip().lower()
            self._terminal_observed = True
        if event.usage is not None:
            self._usage = event.usage

    def mark_exhausted(self) -> None:
        """Record real iterator EOF; a terminal-looking prefix is insufficient."""

        self._ensure_healthy()
        if not self._opened:
            self._fail_and_raise("stream_not_opened", "lifecycle")
        if self._eof_observed:
            self._fail_and_raise("duplicate_eof", "lifecycle")
        self._eof_observed = True
        self._update_elapsed()

    def close(self, *, success: bool = True) -> None:
        """Close the observed stream; close cannot manufacture EOF."""

        self._ensure_healthy()
        if not self._opened:
            self._fail_and_raise("stream_not_opened", "lifecycle")
        if self._close_state in {"closed", "failed"}:
            self._fail_and_raise("duplicate_close", "lifecycle")
        if not isinstance(success, bool):
            self._fail_and_raise("close_state_invalid", "lifecycle")
        if not success:
            self._fail_and_raise("stream_close_failed", "close")
        if not self._eof_observed:
            self._fail_and_raise("close_before_eof", "close")
        self._update_elapsed()
        if self._error_code is not None:
            self._raise_current_error()
        self._close_state = "closed"

    def abort(self, code: str = "stream_aborted", stage: str = "transport") -> None:
        """Fail closed and retain only a safe code/stage."""

        self._ensure_mutable()
        if self._error_code is not None:
            # Poisoning is sticky.  A repeated abort cannot replace the
            # original safe error with a caller-selected code.
            return
        _require_safe_code(code, "error code")
        _require_safe_code(stage, "error stage")
        self._set_failure(code, stage)

    def finalize(self) -> BoundaryObservation:
        """Return a final observation, converting missing lifecycle evidence to fail-closed."""

        if self._final_observation is not None:
            return self._final_observation
        if not self._opened:
            self._set_failure("stream_not_opened", "lifecycle")
        elif self._error_code is None:
            if not self._eof_observed:
                self._set_failure("stream_not_exhausted", "eof")
            elif self._close_state != "closed":
                self._set_failure("stream_not_closed", "close")
            elif self._require_model_observation and self._resolved_model is None:
                self._set_failure("model_unobserved", "identity")
            elif self._require_request_identity and self._request_id_sha256 is None:
                self._set_failure("request_identity_unobserved", "identity")
            elif not self._terminal_observed:
                self._set_failure("missing_terminal", "terminal")
            elif self._usage is None:
                self._set_failure("usage_unavailable", "usage")
        final = self._snapshot_current()
        self._finalized = True
        self._final_observation = final
        return final

    def snapshot(self) -> BoundaryObservation:
        """Build a body-free snapshot from the current bounded state."""

        if self._final_observation is not None:
            return self._final_observation
        return self._snapshot_current()

    def _snapshot_current(self) -> BoundaryObservation:
        """Build a snapshot from mutable state before finalization."""

        self._update_elapsed()
        state, action, derived_error = self._derive_state()
        error_code = self._error_code or derived_error
        error_stage = self._error_stage
        if derived_error is not None and self._error_code is None:
            error_stage = "boundary"
        usage_state: CandidateUsageState
        input_tokens: int | None
        output_tokens: int | None
        cached_input_tokens: int | None
        if self._usage is not None and self._error_code is None:
            usage_state = "valid"
            input_tokens = self._usage.input_tokens
            output_tokens = self._usage.output_tokens
            cached_input_tokens = self._usage.cached_input_tokens
        else:
            usage_state = "invalid" if self._error_code and self._error_code in {
                "invalid_usage",
                "usage_before_terminal",
                "duplicate_usage",
            } else "missing"
            input_tokens = output_tokens = cached_input_tokens = None
        return BoundaryObservation(
            binding=self._binding,
            opened=self._opened,
            eof_observed=self._eof_observed,
            terminal_observed=self._terminal_observed,
            close_state=(
                "failed"
                if self._error_code is not None and self._opened
                else self._close_state
            ),
            finish_reason=self._finish_reason,
            content_state=self._content_state,
            reasoning_content_state=self._reasoning_state,
            tool_call_count=len(self._tool_indices),
            usage_state=usage_state,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=cached_input_tokens,
            elapsed_ms=self._last_elapsed_ms,
            resolved_model=self._resolved_model,
            request_id_sha256=self._request_id_sha256,
            error_code=error_code,
            error_stage=error_stage,
            observation_state=state,
            next_action=action,
        )

    observation = snapshot

    def _observe_identity(self, event: ProviderStreamEvent, ordinal: int) -> None:
        if event.model is not None:
            normalized_model = event.model.strip().lower()
            if normalized_model != self._binding.model:
                self._fail_and_raise("model_mismatch", "identity")
            if self._resolved_model is not None and self._resolved_model != normalized_model:
                self._fail_and_raise("model_conflict", "identity")
            self._resolved_model = normalized_model
        if event.request_id_sha256 is not None:
            if (
                self._request_id_sha256 is not None
                and self._request_id_sha256 != event.request_id_sha256
            ):
                self._fail_and_raise("request_identity_conflict", "identity")
            self._request_id_sha256 = event.request_id_sha256

    def _observe_field(
        self,
        field_name: str,
        value: object,
        *,
        observed: bool = True,
    ) -> None:
        if not observed:
            return
        state = _field_state(value)
        if field_name == "content":
            self._content_state = _merge_field_state(self._content_state, state)
        else:
            self._reasoning_state = _merge_field_state(self._reasoning_state, state)

    def observe_field_states(
        self,
        *,
        content: object = _UNSET,
        reasoning: object = _UNSET,
    ) -> None:
        """Observe explicit field values in offline tests without retaining them."""

        self._ensure_healthy()
        if self._eof_observed or self._close_state in {"closed", "failed"}:
            raise CandidateObservationError("boundary_sealed", "lifecycle")
        if content is not _UNSET:
            self._content_state = _merge_field_state(
                self._content_state, _field_state(content)
            )
        if reasoning is not _UNSET:
            self._reasoning_state = _merge_field_state(
                self._reasoning_state, _field_state(reasoning)
            )

    def _observe_tool_deltas(
        self,
        deltas: tuple[StreamToolCallDelta, ...],
    ) -> None:
        """Validate one event's tool fragments with copy-on-write state."""

        next_hashes = self._tool_metadata_hashes.copy()
        next_indices = self._tool_indices.copy()
        next_argument_seen = self._tool_argument_seen.copy()
        next_argument_chars = self._tool_argument_chars
        for delta in deltas:
            if not isinstance(delta, StreamToolCallDelta):
                self._fail_and_raise("tool_shape", "tool")
            if delta.index < 0 or delta.index > _MAX_TOOL_INDEX:
                self._fail_and_raise("tool_index", "tool")
            if (
                delta.index not in next_indices
                and len(next_indices) >= self._max_tool_calls
            ):
                self._fail_and_raise("tool_call_limit", "budget")
            old_hashes = next_hashes.get(delta.index, (None, None))
            id_hash = old_hashes[0]
            name_hash = old_hashes[1]
            if delta.call_id is not None:
                candidate_hash = _sha256_text(delta.call_id.strip())
                if id_hash is not None and id_hash != candidate_hash:
                    self._fail_and_raise("tool_call_metadata_conflict", "tool")
                if any(
                    index != delta.index and hashes[0] == candidate_hash
                    for index, hashes in next_hashes.items()
                ):
                    self._fail_and_raise("tool_call_id_conflict", "tool")
                id_hash = candidate_hash
            if delta.name is not None:
                candidate_hash = _sha256_text(delta.name.strip())
                if name_hash is not None and name_hash != candidate_hash:
                    self._fail_and_raise("tool_call_metadata_conflict", "tool")
                name_hash = candidate_hash
            next_hashes[delta.index] = (id_hash, name_hash)
            next_indices.add(delta.index)
            if delta.arguments_delta is not None:
                next_argument_seen.add(delta.index)
            next_argument_chars += len(delta.arguments_delta or "")
            if next_argument_chars > self._max_tool_argument_chars:
                self._fail_and_raise("tool_argument_limit", "budget")
        self._tool_metadata_hashes = next_hashes
        self._tool_indices = next_indices
        self._tool_argument_seen = next_argument_seen
        self._tool_argument_chars = next_argument_chars

    @staticmethod
    def _validate_usage(usage: TokenUsage | None) -> None:
        if not isinstance(usage, TokenUsage):
            raise CandidateObservationError("invalid_usage", "usage")
        if usage.cached_input_tokens > usage.input_tokens:
            raise CandidateObservationError("invalid_usage", "usage")

    def _derive_state(
        self,
    ) -> tuple[CandidateObservationState, CandidateNextAction, str | None]:
        if self._error_code is not None:
            return "fail_closed", "terminal_fail_closed", self._error_code
        if not self._opened:
            return "not_started", "observe", None
        if not self._eof_observed or self._close_state != "closed":
            return "observing_primary", "observe", None
        if self._require_model_observation and self._resolved_model is None:
            return "fail_closed", "terminal_fail_closed", "model_unobserved"
        if self._require_request_identity and self._request_id_sha256 is None:
            return "fail_closed", "terminal_fail_closed", "request_identity_unobserved"
        if not self._terminal_observed:
            return "fail_closed", "terminal_fail_closed", "missing_terminal"
        if self._usage is None:
            return "fail_closed", "terminal_fail_closed", "usage_unavailable"
        if self._usage.output_tokens > self._max_output_tokens:
            return "fail_closed", "terminal_fail_closed", "output_budget_exceeded"
        finish = self._finish_reason
        if finish == "stop":
            if self._tool_indices:
                return "fail_closed", "terminal_fail_closed", "stop_with_tool_calls"
            if self._content_state != "non_empty":
                return "fail_closed", "terminal_fail_closed", "missing_visible_content"
            return "complete_text", "terminal_complete", None
        if finish == "tool_calls":
            if self._content_state == "non_empty":
                return "fail_closed", "terminal_fail_closed", "tool_calls_with_content"
            if not self._tool_indices:
                return "fail_closed", "terminal_fail_closed", "missing_tool_calls"
            if sorted(self._tool_indices) != list(range(len(self._tool_indices))):
                return "fail_closed", "terminal_fail_closed", "tool_call_index"
            if any(
                self._tool_metadata_hashes.get(index, (None, None))[0] is None
                or self._tool_metadata_hashes.get(index, (None, None))[1] is None
                for index in self._tool_indices
            ):
                return "fail_closed", "terminal_fail_closed", "tool_call_metadata"
            if any(index not in self._tool_argument_seen for index in self._tool_indices):
                return "fail_closed", "terminal_fail_closed", "tool_call_arguments"
            if self._tool_argument_chars == 0:
                return "fail_closed", "terminal_fail_closed", "tool_call_arguments"
            return "tool_calls_ready", "terminal_tool_calls", None
        if finish in _INCOMPLETE_FINISH_REASONS:
            if finish == "length":
                if self._content_state != "empty":
                    return "fail_closed", "terminal_fail_closed", "length_without_empty_content"
                if self._reasoning_state != "non_empty":
                    return "fail_closed", "terminal_fail_closed", "length_without_reasoning"
                if self._tool_indices:
                    return "fail_closed", "terminal_fail_closed", "length_with_tool_calls"
                return "candidate_shape", "requires_registered_runtime", None
            return "fail_closed", "terminal_fail_closed", finish
        return "fail_closed", "terminal_fail_closed", "unknown_finish_reason"

    def _read_clock(self) -> float:
        try:
            value = self._clock()
        except Exception:
            self._set_failure("clock_unavailable", "clock")
            raise CandidateObservationError("clock_unavailable", "clock") from None
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
            self._set_failure("clock_invalid", "clock")
            raise CandidateObservationError("clock_invalid", "clock")
        return float(value)

    def _update_elapsed(self) -> None:
        if self._error_code is not None:
            return
        if self._finalized:
            return
        if self._close_state == "closed":
            return
        if self._started_at is None:
            self._last_elapsed_ms = 0
            return
        now = self._read_clock()
        elapsed = now - self._started_at
        if elapsed < 0:
            self._set_failure("clock_reversed", "clock")
            return
        elapsed_ms = round(elapsed * 1000)
        if elapsed_ms > self._max_elapsed_ms:
            self._set_failure("elapsed_limit", "budget")
            self._last_elapsed_ms = self._max_elapsed_ms
            return
        self._last_elapsed_ms = max(0, elapsed_ms)

    def _set_failure(self, code: str, stage: str) -> None:
        _require_safe_code(code, "error code")
        _require_safe_code(stage, "error stage")
        if self._error_code is None:
            self._error_code = code.strip().lower()
            self._error_stage = stage.strip().lower()
        # A pre-open failure (for example an unavailable monotonic clock)
        # has no stream to close.  Keep the lifecycle at ``not_observed`` so
        # the resulting BoundaryObservation remains structurally valid.
        if self._opened:
            self._close_state = "failed"

    def _fail_and_raise(self, code: str, stage: str) -> None:
        self._set_failure(code, stage)
        raise CandidateObservationError(code, stage)

    def _raise_current_error(self) -> None:
        raise CandidateObservationError(
            self._error_code or "stream_aborted",
            self._error_stage,
        )

    def _ensure_mutable(self) -> None:
        if self._finalized:
            raise CandidateObservationError("already_finalized", "lifecycle")

    def _ensure_healthy(self) -> None:
        self._ensure_mutable()
        if self._error_code is not None:
            self._raise_current_error()


# Short aliases keep the boundary contract discoverable without creating a
# second implementation or a second serialization shape.
CandidateBoundaryObserver = CandidateStreamBoundaryObserver


@runtime_checkable
class CandidateStreamTransport(Protocol):
    """Injected transport port; implementations must be fake/local for now."""

    def open_stream(
        self,
        binding: CandidateRuntimeBinding,
        request: ChatRequest,
        *,
        max_output_tokens: int,
        timeout_s: float,
        transport_timeout_s: float,
    ) -> Iterable[ProviderStreamEvent]:
        """Open one already-authorized candidate stream."""


class CandidateZhipuStreamTransport:
    """Candidate v2 transport port backed only by an injected opener.

    The opener is intentionally a callable supplied by a fake/local test.  A
    future real implementation must be introduced in a separately reviewed
    checkpoint; this class itself has no SDK or network dependency.
    """

    def __init__(
        self,
        opener: Callable[..., Iterable[ProviderStreamEvent]],
        *,
        runtime_profile: Any = GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1,
        policy: ResponseCompletionPolicy = GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1,
    ) -> None:
        if not callable(opener):
            raise TypeError("opener must be callable")
        if (
            type(runtime_profile)
            is not type(GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1)
            or runtime_profile != GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1
        ):
            raise CandidateIdentityError("candidate_profile_mismatch", "identity")
        if (
            type(policy) is not type(GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1)
            or policy != GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1
        ):
            raise CandidateIdentityError("candidate_policy_mismatch", "identity")
        self._opener = opener
        self.runtime_profile = runtime_profile
        self.policy = policy

    def open_stream(
        self,
        binding: CandidateRuntimeBinding,
        request: ChatRequest,
        *,
        max_output_tokens: int | None = None,
        timeout_s: float | None = None,
        transport_timeout_s: float | None = None,
    ) -> Iterable[ProviderStreamEvent]:
        require_exact_candidate_binding(binding)
        if not isinstance(request, ChatRequest):
            raise CandidateTransportError("invalid_request", "request")
        if (
            type(self.runtime_profile)
            is not type(GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1)
            or self.runtime_profile != GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1
        ):
            raise CandidateIdentityError("candidate_profile_mismatch", "identity")
        if (
            type(self.policy) is not type(GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1)
            or self.policy != GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1
        ):
            raise CandidateIdentityError("candidate_policy_mismatch", "identity")
        cap = self.runtime_profile.max_output_tokens
        if max_output_tokens is not None:
            try:
                cap = _require_bounded_int(
                    max_output_tokens, 1, cap, "max_output_tokens"
                )
            except (TypeError, ValueError):
                raise CandidateTransportError("invalid_output_cap", "budget") from None
        requested_cap = request.max_tokens
        if requested_cap is not None:
            if isinstance(requested_cap, bool) or not isinstance(requested_cap, int) or requested_cap < 1:
                raise CandidateTransportError("invalid_output_cap", "budget")
            cap = min(cap, requested_cap)
        if timeout_s is None:
            # The candidate transport owns its longer evaluation window; the
            # product ChatRequest default (30s) must not silently collapse the
            # v2 90s profile.  A caller can still opt into a shorter window by
            # supplying the explicit method argument.
            timeout = self.runtime_profile.agent_timeout_s
        else:
            timeout = _bounded_float(
                timeout_s,
                0.001,
                self.runtime_profile.agent_timeout_s,
                "timeout_s",
            )
        transport_timeout = (
            self.runtime_profile.transport_timeout_s
            if transport_timeout_s is None
            else _bounded_float(
                transport_timeout_s,
                timeout,
                self.runtime_profile.transport_timeout_s,
                "transport_timeout_s",
            )
        )
        try:
            bounded_request = replace(
                request,
                max_tokens=(
                    cap
                    if request.max_tokens is None or request.max_tokens > cap
                    else request.max_tokens
                ),
                # Candidate v2 owns these sampling knobs.  A caller cannot
                # silently fall back to the product v1 defaults by passing a
                # different temperature/top_p on the request.
                temperature=self.runtime_profile.temperature,
                top_p=self.runtime_profile.top_p,
                timeout_s=timeout,
            )
        except (TypeError, ValueError):
            raise CandidateTransportError("invalid_request", "request") from None
        metadata = bounded_request.metadata
        if not isinstance(metadata, Mapping):
            raise CandidateTransportError("invalid_request_metadata", "identity")
        for key, expected in (
            ("provider_id", CANDIDATE_PROVIDER_ID),
            ("model", CANDIDATE_MODEL),
            ("runtime_profile_id", CANDIDATE_RUNTIME_PROFILE_ID),
            ("runtime_profile_version", CANDIDATE_RUNTIME_PROFILE_VERSION),
            ("policy_id", CANDIDATE_POLICY_ID),
            ("policy_version", CANDIDATE_POLICY_VERSION),
        ):
            try:
                mismatch = key in metadata and metadata[key] != expected
            except Exception:
                raise CandidateTransportError("invalid_request_metadata", "identity") from None
            if mismatch:
                raise CandidateTransportError("request_identity_mismatch", "identity")
        try:
            stream = self._opener(
                binding=binding,
                request=bounded_request,
                max_output_tokens=cap,
                timeout_s=timeout,
                transport_timeout_s=transport_timeout,
                max_retries=0,
            )
        except CandidateBoundaryContractError:
            raise
        except Exception:
            raise CandidateTransportError("transport_open_failed", "open") from None
        if stream is None or not isinstance(stream, Iterable):
            raise CandidateTransportError("transport_stream_invalid", "open")
        return stream


def observe_candidate_events(
    events: Iterable[ProviderStreamEvent],
    *,
    binding: CandidateRuntimeBinding | None = None,
    clock: Callable[[], float] = time.monotonic,
    observer: CandidateStreamBoundaryObserver | None = None,
) -> BoundaryObservation:
    """Consume a fake/local normalized stream and return one safe observation."""

    selected = observer or CandidateStreamBoundaryObserver(binding, clock=clock)
    if observer is not None and binding is not None and observer.binding != binding:
        raise CandidateIdentityError("candidate_binding_mismatch", "identity")
    iterator: Iterator[ProviderStreamEvent] | None = None
    open_succeeded = False
    try:
        selected.open()
        open_succeeded = True
        iterator = iter(events)
        for event in iterator:
            selected.accept(event)
        selected.mark_exhausted()
    except CandidateBoundaryContractError as error:
        # The observation is the safe failure product of this helper.  The
        # selected observer has already validated its exact binding; all
        # stream/open errors are therefore represented by a safe code rather
        # than by vendor/provider exception text.
        if selected.failed_code is None:
            selected.abort(error.code, error.stage or "observe")
    except (GeneratorExit, KeyboardInterrupt, SystemExit):
        selected.abort("stream_aborted", "transport")
        raise
    except Exception:
        selected.abort("stream_read_failed", "read")
    finally:
        close_failed = _close_candidate_resource(iterator)
        if events is not iterator:
            close_failed = _close_candidate_resource(events) or close_failed
        if close_failed and selected.failed_code is None and open_succeeded:
            selected.abort("stream_close_failed", "close")
    if selected.failed_code is None:
        try:
            selected.close()
        except CandidateBoundaryContractError:
            # ``close`` failure is already represented in the observer.
            pass
    return selected.finalize()


@dataclass(frozen=True, slots=True)
class CandidateStreamTrace:
    """Independent allow-list trace projection for one observation."""

    schema_version: Literal["1.0"] = CANDIDATE_SCHEMA_VERSION
    observation: BoundaryObservation = field(repr=False, default_factory=BoundaryObservation)

    def __post_init__(self) -> None:
        if self.schema_version != CANDIDATE_SCHEMA_VERSION:
            raise CandidateObservationError("unsupported_trace_schema", "trace")
        if not isinstance(self.observation, BoundaryObservation):
            raise TypeError("observation must be a BoundaryObservation")
        require_exact_candidate_binding(self.observation.binding)

    def as_dict(self) -> dict[str, Any]:
        payload = self.observation.as_dict()
        payload["trace_schema_version"] = self.schema_version
        if not set(payload).issubset(_CANDIDATE_BODY_FREE_KEYS):
            raise CandidateObservationError("trace_field_not_allowlisted", "trace")
        return payload


CandidateBoundaryObservation = BoundaryObservation
CandidateBoundaryTrace = CandidateStreamTrace


def field_state(value: object, *, observed: bool = True) -> CandidateFieldState:
    """Classify a field without retaining its value."""

    if not observed:
        return "not_observed"
    return _field_state(value)


def merge_field_states(
    current: CandidateFieldState,
    observed: CandidateFieldState,
) -> CandidateFieldState:
    """Apply the deterministic field-state precedence from ADR-0076."""

    if current not in _FIELD_STATES or observed not in _FIELD_STATES:
        raise ValueError("field states must be sanitized")
    return _merge_field_state(current, observed)


_FIELD_RANK = {
    "not_observed": 0,
    "missing": 1,
    "null": 2,
    "empty": 3,
    "non_empty": 4,
    "non_string": 5,
}
_CANDIDATE_BODY_FREE_KEYS = frozenset(
    {
        "schema_version",
        "provider_id",
        "model",
        "runtime_profile_id",
        "runtime_profile_version",
        "policy_id",
        "policy_version",
        "attempt_ordinal",
        "attempt_kind",
        "activation_state",
        "execution_allowed",
        "opened",
        "eof_observed",
        "terminal_observed",
        "close_state",
        "finish_reason",
        "content_state",
        "reasoning_content_state",
        "tool_call_count",
        "usage_state",
        "input_tokens",
        "output_tokens",
        "cached_input_tokens",
        "elapsed_ms",
        "resolved_model",
        "request_id_sha256",
        "error_code",
        "error_stage",
        "observation_state",
        "next_action",
        "trace_schema_version",
    }
)


def _field_state(value: object) -> CandidateFieldState:
    if value is None:
        return "null"
    if not isinstance(value, str):
        return "non_string"
    return "non_empty" if value.strip() else "empty"


def _merge_field_state(
    current: CandidateFieldState,
    observed: CandidateFieldState,
) -> CandidateFieldState:
    if _FIELD_RANK[observed] > _FIELD_RANK[current]:
        return observed
    return current


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _require_safe_identifier(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value.strip().lower()):
        raise CandidateObservationError("unsafe_identifier", field_name)


def _require_safe_code(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not _SAFE_CODE.fullmatch(value.strip().lower()):
        raise CandidateBoundaryContractError("unsafe_code", field_name)


def _require_non_negative_int(value: object, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CandidateObservationError("invalid_integer", field_name)


def _require_bounded_int(value: object, lower: int, upper: int, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not lower <= value <= upper:
        raise ValueError(f"{field_name} is outside the supported bound")
    return value


def _bounded_float(value: object, lower: float, upper: float, field_name: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(value)
        or value < lower
        or value > upper
    ):
        raise CandidateTransportError("transport_timeout_invalid", field_name)
    return float(value)


def _close_candidate_resource(resource: object) -> bool:
    """Close an iterator/outer stream without leaking provider exception text."""

    if resource is None:
        return False
    close = getattr(resource, "close", None)
    if callable(close):
        try:
            close()
        except Exception:
            return True
        return False
    exit_method = getattr(resource, "__exit__", None)
    if callable(exit_method):
        try:
            exit_method(None, None, None)
        except Exception:
            return True
    return False


def _stage_for_stream_error(code: str) -> str:
    """Map a shared neutral error to the candidate observation stage."""

    if code in {
        "stream_event_limit",
        "content_limit",
        "reasoning_limit",
        "tool_call_limit",
        "tool_argument_limit",
        "output_budget_exceeded",
    }:
        return "budget"
    if code in {"sequence_conflict", "model_conflict", "request_identity_conflict"}:
        return "identity"
    if code in {"invalid_finish_reason", "duplicate_terminal", "payload_after_terminal"}:
        return "terminal"
    if code in {"invalid_usage", "usage_before_terminal", "duplicate_usage"}:
        return "usage"
    if code.startswith("tool_"):
        return "tool"
    if code == "invalid_event":
        return "translate"
    return "observe"


__all__ = [
    "BoundaryObservation",
    "CandidateBoundaryObservation",
    "CandidateBoundaryObserver",
    "CandidateBoundaryTrace",
    "CandidateAttemptKind",
    "CandidateBoundaryContractError",
    "CandidateCloseState",
    "CandidateFieldState",
    "CandidateIdentityError",
    "CandidateNextAction",
    "CandidateObservationError",
    "CandidateObservationState",
    "CandidateRuntimeBinding",
    "CandidateStreamBoundaryObserver",
    "CandidateStreamTrace",
    "CandidateStreamTransport",
    "CandidateTransportError",
    "CandidateUsageState",
    "CandidateZhipuStreamTransport",
    "CANDIDATE_MODEL",
    "CANDIDATE_POLICY_ID",
    "CANDIDATE_POLICY_VERSION",
    "CANDIDATE_PROVIDER_ID",
    "CANDIDATE_RUNTIME_PROFILE_ID",
    "CANDIDATE_RUNTIME_PROFILE_VERSION",
    "CANDIDATE_SCHEMA_VERSION",
    "FRESH_RECOVERY_CANDIDATE_BINDING",
    "PRIMARY_CANDIDATE_BINDING",
    "field_state",
    "merge_field_states",
    "observe_candidate_events",
    "require_exact_candidate_binding",
]
