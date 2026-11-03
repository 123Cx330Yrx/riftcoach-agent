"""Offline response-profile/terminal/recovery split for GLM-5.3-Flash.

This module composes the already-frozen candidate boundary observer and
response-completion policies into one deterministic fixture matrix.  It is an
evaluation seam only: it never loads credentials, constructs an SDK client,
opens a socket, or changes the registered Flash runtime.

The matrix keeps four questions separate:

* which thinking/profile shape was requested;
* whether a normalized stream reached a terminal boundary;
* whether a valid Usage tail was observed; and
* what strict versus candidate policy would decide.

Only sanitized states and safe codes enter the receipt.  Fixture event bodies
exist briefly in memory so the existing observer can be exercised, but they
are never included in a representation or persisted result.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from math import isfinite
from pathlib import Path
from typing import Literal

from app.providers.models import TokenUsage
from app.providers.response_completion_policy import (
    GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1,
    GLM53_FLASH_RESPONSE_COMPLETION_POLICY_V1,
    ResponseBoundarySnapshot,
    ResponseCompletionDecision,
    ResponseDisposition,
    ResponseRequestContext,
)
from app.providers.stream_adapter_contract import ProviderStreamEvent, StreamToolCallDelta
from app.providers.zhipu_profiles import ZHIPU_GLM53_FLASH_MODEL, ZhipuThinkingProfile

from .candidate_stream_contract import (
    CandidateStreamBoundaryObserver,
    observe_candidate_events,
)


PROTOCOL_ID = "glm-5.3-flash-response-profile-terminal-recovery-split"
SCHEMA_VERSION = "1.0.0"
EVIDENCE_ORIGIN = "offline_fixture"
MODEL = ZHIPU_GLM53_FLASH_MODEL
DEFAULT_OUTPUT = Path(
    "data/evaluation/results/offline/"
    "zhipu_glm53_flash_response_profile_terminal_recovery_split_rq220_v1.json"
)

_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SAFE_ID = re.compile(r"^[a-z][a-z0-9_.-]{0,95}$")
_SAFE_CODE = re.compile(r"^[a-z][a-z0-9_.-]{0,95}$")
_FORBIDDEN_KEYS = frozenset(
    {
        "body",
        "content",
        "reasoning",
        "reasoning_content",
        "tool_arguments",
        "tool_results",
        "prompt",
        "messages",
        "headers",
        "authorization",
        "api_key",
        "secret",
        "request_id",
        "sdk_response",
        "response_body",
    }
)

_RECEIPT_KEYS = frozenset(
    {
        "schema_version",
        "protocol_id",
        "evidence_origin",
        "real_provider_observed",
        "provider_call_count",
        "network_used",
        "model",
        "strict_policy_id",
        "strict_policy_version",
        "candidate_policy_id",
        "candidate_policy_version",
        "candidate_activation_state",
        "candidate_execution_allowed",
        "implementation_sha",
        "diagnostic_code_sha",
        "input_plan_sha",
        "fixture_catalog_sha256",
        "case_count",
        "cases",
        "all_cases_passed",
        "next_action",
    }
)
_CASE_KEYS = frozenset(
    {
        "case_id",
        "profile_id",
        "reasoning_effort",
        "clear_thinking",
        "max_output_tokens",
        "agent_timeout_s",
        "boundary_source",
        "terminal_observation",
        "usage_observation",
        "observed_state",
        "observed_error_code",
        "strict_disposition",
        "strict_reason_code",
        "candidate_disposition",
        "candidate_reason_code",
        "candidate_continuation_allowed",
        "recovery_action",
        "passed",
    }
)

BoundarySource = Literal["stream_observer", "policy_snapshot"]
FixtureKind = Literal[
    "complete_stop",
    "candidate_length",
    "tool_calls",
    "missing_usage",
    "elapsed_timeout",
    "partial_length",
    "invalid_usage",
]
TerminalObservation = Literal[
    "stop",
    "tool_calls",
    "length",
    "missing",
    "timeout",
]
UsageObservation = Literal["valid", "missing", "invalid"]
ObservedState = Literal[
    "complete_text",
    "tool_calls_ready",
    "candidate_shape",
    "fail_closed",
]
RecoveryAction = Literal[
    "none",
    "blocked_activation",
    "not_eligible",
    "boundary_incomplete",
]


class ResponseProfileSplitError(ValueError):
    """Machine-safe error for fixture and receipt validation."""

    def __init__(self, code: str, field_name: str | None = None) -> None:
        if not isinstance(code, str) or _SAFE_CODE.fullmatch(code) is None:
            code = "profile_split_error"
        self.code = code
        self.field_name = field_name
        super().__init__(code)


def _require_git_sha(value: object, field_name: str) -> str:
    if not isinstance(value, str) or _GIT_SHA.fullmatch(value) is None:
        raise ResponseProfileSplitError("invalid_git_sha", field_name)
    return value


def _require_sha256(value: object, field_name: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ResponseProfileSplitError("invalid_sha256", field_name)
    return value


def _require_safe_id(value: object, field_name: str) -> str:
    if not isinstance(value, str) or _SAFE_ID.fullmatch(value) is None:
        raise ResponseProfileSplitError("invalid_identifier", field_name)
    return value


def _canonical_json(value: object) -> bytes:
    try:
        return (
            json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError):
        raise ResponseProfileSplitError("json_not_serializable", "serialize") from None


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _assert_body_free(value: object) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str) and key.strip().lower() in _FORBIDDEN_KEYS:
                raise ResponseProfileSplitError("receipt_field_forbidden", "serialize")
            _assert_body_free(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            _assert_body_free(item)


@dataclass(frozen=True, slots=True)
class ResponseProfileSplitFixture:
    """A fixed fixture descriptor; event payloads are intentionally private."""

    case_id: str
    profile_id: str
    reasoning_effort: Literal["low", "max"]
    clear_thinking: bool
    max_output_tokens: Literal[2048, 8192]
    agent_timeout_s: float
    kind: FixtureKind
    expected_terminal_observation: TerminalObservation
    expected_usage_observation: UsageObservation
    expected_state: ObservedState
    expected_error_code: str | None
    expected_strict_disposition: str | None
    expected_strict_reason_code: str | None
    expected_candidate_disposition: str | None
    expected_candidate_reason_code: str | None
    expected_candidate_continuation_allowed: bool
    expected_recovery_action: RecoveryAction
    _events: tuple[ProviderStreamEvent, ...] = field(default=(), repr=False, compare=False)
    _snapshot: ResponseBoundarySnapshot | None = field(
        default=None, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        _require_safe_id(self.case_id, "case_id")
        _require_safe_id(self.profile_id, "profile_id")
        if self.reasoning_effort not in {"low", "max"}:
            raise ResponseProfileSplitError("reasoning_effort_invalid", "reasoning_effort")
        if not isinstance(self.clear_thinking, bool):
            raise ResponseProfileSplitError("clear_thinking_invalid", "clear_thinking")
        if self.max_output_tokens not in {2048, 8192}:
            raise ResponseProfileSplitError("output_cap_invalid", "max_output_tokens")
        if not isinstance(self.agent_timeout_s, (int, float)) or isinstance(
            self.agent_timeout_s, bool
        ) or not 0 < self.agent_timeout_s <= 90:
            raise ResponseProfileSplitError("timeout_invalid", "agent_timeout_s")
        if self.expected_state not in {
            "complete_text",
            "tool_calls_ready",
            "candidate_shape",
            "fail_closed",
        }:
            raise ResponseProfileSplitError("state_invalid", "expected_state")
        for field_name in (
            "expected_error_code",
            "expected_strict_reason_code",
            "expected_candidate_reason_code",
        ):
            value = getattr(self, field_name)
            if value is not None and _SAFE_CODE.fullmatch(value) is None:
                raise ResponseProfileSplitError("unsafe_code", field_name)
        if self.kind in {"complete_stop", "candidate_length", "tool_calls", "missing_usage", "elapsed_timeout"}:
            if self._snapshot is not None:
                raise ResponseProfileSplitError("fixture_source_conflict", "snapshot")
        elif self._snapshot is None:
            raise ResponseProfileSplitError("fixture_snapshot_required", "snapshot")

    def descriptor(self) -> dict[str, object]:
        """Return the public, body-free fixture shape used for the catalog hash."""

        return {
            "case_id": self.case_id,
            "profile_id": self.profile_id,
            "reasoning_effort": self.reasoning_effort,
            "clear_thinking": self.clear_thinking,
            "max_output_tokens": self.max_output_tokens,
            "agent_timeout_s": self.agent_timeout_s,
            "kind": self.kind,
            "expected_terminal_observation": self.expected_terminal_observation,
            "expected_usage_observation": self.expected_usage_observation,
            "expected_state": self.expected_state,
            "expected_error_code": self.expected_error_code,
            "expected_strict_disposition": self.expected_strict_disposition,
            "expected_strict_reason_code": self.expected_strict_reason_code,
            "expected_candidate_disposition": self.expected_candidate_disposition,
            "expected_candidate_reason_code": self.expected_candidate_reason_code,
            "expected_candidate_continuation_allowed": self.expected_candidate_continuation_allowed,
            "expected_recovery_action": self.expected_recovery_action,
        }


@dataclass(frozen=True, slots=True)
class ResponseProfileSplitCase:
    """Sanitized result for one fixture."""

    case_id: str
    profile_id: str
    reasoning_effort: Literal["low", "max"]
    clear_thinking: bool
    max_output_tokens: Literal[2048, 8192]
    agent_timeout_s: float
    boundary_source: BoundarySource
    terminal_observation: TerminalObservation
    usage_observation: UsageObservation
    observed_state: ObservedState
    observed_error_code: str | None
    strict_disposition: str | None
    strict_reason_code: str | None
    candidate_disposition: str | None
    candidate_reason_code: str | None
    candidate_continuation_allowed: bool
    recovery_action: RecoveryAction
    passed: bool

    def __post_init__(self) -> None:
        _require_safe_id(self.case_id, "case_id")
        _require_safe_id(self.profile_id, "profile_id")
        if self.reasoning_effort not in {"low", "max"}:
            raise ResponseProfileSplitError("reasoning_effort_invalid", "reasoning_effort")
        if not isinstance(self.clear_thinking, bool):
            raise ResponseProfileSplitError("clear_thinking_invalid", "clear_thinking")
        if self.max_output_tokens not in {2048, 8192}:
            raise ResponseProfileSplitError("output_cap_invalid", "max_output_tokens")
        if (
            isinstance(self.agent_timeout_s, bool)
            or not isinstance(self.agent_timeout_s, (int, float))
            or not isfinite(self.agent_timeout_s)
            or not 0 < self.agent_timeout_s <= 90
        ):
            raise ResponseProfileSplitError("timeout_invalid", "agent_timeout_s")
        if self.boundary_source not in {"stream_observer", "policy_snapshot"}:
            raise ResponseProfileSplitError("boundary_source_invalid", "boundary_source")
        if self.terminal_observation not in {"stop", "tool_calls", "length", "missing", "timeout"}:
            raise ResponseProfileSplitError("terminal_observation_invalid", "terminal_observation")
        if self.usage_observation not in {"valid", "missing", "invalid"}:
            raise ResponseProfileSplitError("usage_observation_invalid", "usage_observation")
        if self.observed_state not in {"complete_text", "tool_calls_ready", "candidate_shape", "fail_closed"}:
            raise ResponseProfileSplitError("state_invalid", "observed_state")
        for field_name in (
            "observed_error_code",
            "strict_reason_code",
            "candidate_reason_code",
        ):
            value = getattr(self, field_name)
            if value is not None and _SAFE_CODE.fullmatch(value) is None:
                raise ResponseProfileSplitError("unsafe_code", field_name)
        for field_name in ("strict_disposition", "candidate_disposition"):
            value = getattr(self, field_name)
            if value is not None and value not in {
                "complete_text",
                "tool_calls_ready",
                "fail_closed",
                "candidate_eligible",
            }:
                raise ResponseProfileSplitError("disposition_invalid", field_name)
        if self.recovery_action not in {
            "none",
            "blocked_activation",
            "not_eligible",
            "boundary_incomplete",
        }:
            raise ResponseProfileSplitError("recovery_action_invalid", "recovery_action")
        if not isinstance(self.candidate_continuation_allowed, bool):
            raise ResponseProfileSplitError("continuation_flag_invalid", "candidate_continuation_allowed")
        if not isinstance(self.passed, bool):
            raise ResponseProfileSplitError("passed_invalid", "passed")

    def as_dict(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "profile_id": self.profile_id,
            "reasoning_effort": self.reasoning_effort,
            "clear_thinking": self.clear_thinking,
            "max_output_tokens": self.max_output_tokens,
            "agent_timeout_s": self.agent_timeout_s,
            "boundary_source": self.boundary_source,
            "terminal_observation": self.terminal_observation,
            "usage_observation": self.usage_observation,
            "observed_state": self.observed_state,
            "observed_error_code": self.observed_error_code,
            "strict_disposition": self.strict_disposition,
            "strict_reason_code": self.strict_reason_code,
            "candidate_disposition": self.candidate_disposition,
            "candidate_reason_code": self.candidate_reason_code,
            "candidate_continuation_allowed": self.candidate_continuation_allowed,
            "recovery_action": self.recovery_action,
            "passed": self.passed,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "ResponseProfileSplitCase":
        if not isinstance(value, Mapping) or set(value) != _CASE_KEYS:
            raise ResponseProfileSplitError("case_fields_invalid", "case")
        _assert_body_free(value)
        try:
            result = cls(**dict(value))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            raise ResponseProfileSplitError("case_shape_invalid", "case") from None
        if result.passed is not True:
            raise ResponseProfileSplitError("case_not_passed", "passed")
        return result


@dataclass(frozen=True, slots=True)
class ResponseProfileSplitReceipt:
    """Immutable, body-free offline evidence for the split matrix."""

    implementation_sha: str
    diagnostic_code_sha: str
    input_plan_sha: str
    fixture_catalog_sha256: str
    cases: tuple[ResponseProfileSplitCase, ...]
    all_cases_passed: bool
    schema_version: str = SCHEMA_VERSION
    protocol_id: str = PROTOCOL_ID
    evidence_origin: str = EVIDENCE_ORIGIN
    real_provider_observed: bool = False
    provider_call_count: int = 0
    network_used: bool = False
    model: str = MODEL
    strict_policy_id: str = GLM53_FLASH_RESPONSE_COMPLETION_POLICY_V1.policy_id
    strict_policy_version: str = GLM53_FLASH_RESPONSE_COMPLETION_POLICY_V1.version
    candidate_policy_id: str = GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1.policy_id
    candidate_policy_version: str = GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1.version
    candidate_activation_state: Literal["candidate"] = "candidate"
    candidate_execution_allowed: Literal[False] = False
    next_action: Literal["split_complete_review_next"] = "split_complete_review_next"

    def __post_init__(self) -> None:
        _require_git_sha(self.implementation_sha, "implementation_sha")
        _require_git_sha(self.diagnostic_code_sha, "diagnostic_code_sha")
        _require_git_sha(self.input_plan_sha, "input_plan_sha")
        _require_sha256(self.fixture_catalog_sha256, "fixture_catalog_sha256")
        if self.schema_version != SCHEMA_VERSION or self.protocol_id != PROTOCOL_ID:
            raise ResponseProfileSplitError("receipt_identity_invalid", "identity")
        if self.evidence_origin != EVIDENCE_ORIGIN:
            raise ResponseProfileSplitError("evidence_origin_invalid", "evidence_origin")
        if self.real_provider_observed or self.network_used or self.provider_call_count != 0:
            raise ResponseProfileSplitError("provider_claim_forbidden", "provider_call_count")
        if self.model != MODEL:
            raise ResponseProfileSplitError("model_invalid", "model")
        if self.strict_policy_id != GLM53_FLASH_RESPONSE_COMPLETION_POLICY_V1.policy_id:
            raise ResponseProfileSplitError("strict_policy_invalid", "strict_policy_id")
        if self.strict_policy_version != GLM53_FLASH_RESPONSE_COMPLETION_POLICY_V1.version:
            raise ResponseProfileSplitError("strict_policy_invalid", "strict_policy_version")
        if self.candidate_policy_id != GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1.policy_id:
            raise ResponseProfileSplitError("candidate_policy_invalid", "candidate_policy_id")
        if self.candidate_policy_version != GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1.version:
            raise ResponseProfileSplitError("candidate_policy_invalid", "candidate_policy_version")
        if self.candidate_activation_state != "candidate" or self.candidate_execution_allowed:
            raise ResponseProfileSplitError("candidate_activation_invalid", "candidate_activation_state")
        if not self.cases:
            raise ResponseProfileSplitError("cases_empty", "cases")
        if not all(isinstance(case, ResponseProfileSplitCase) for case in self.cases):
            raise ResponseProfileSplitError("cases_shape_invalid", "cases")
        if not isinstance(self.all_cases_passed, bool):
            raise ResponseProfileSplitError("aggregate_invalid", "all_cases_passed")
        if self.next_action != "split_complete_review_next":
            raise ResponseProfileSplitError("next_action_invalid", "next_action")
        if self.all_cases_passed != all(case.passed for case in self.cases):
            raise ResponseProfileSplitError("aggregate_mismatch", "all_cases_passed")

    @property
    def case_count(self) -> int:
        return len(self.cases)

    def as_dict(self) -> dict[str, object]:
        payload = {
            "schema_version": self.schema_version,
            "protocol_id": self.protocol_id,
            "evidence_origin": self.evidence_origin,
            "real_provider_observed": self.real_provider_observed,
            "provider_call_count": self.provider_call_count,
            "network_used": self.network_used,
            "model": self.model,
            "strict_policy_id": self.strict_policy_id,
            "strict_policy_version": self.strict_policy_version,
            "candidate_policy_id": self.candidate_policy_id,
            "candidate_policy_version": self.candidate_policy_version,
            "candidate_activation_state": self.candidate_activation_state,
            "candidate_execution_allowed": self.candidate_execution_allowed,
            "implementation_sha": self.implementation_sha,
            "diagnostic_code_sha": self.diagnostic_code_sha,
            "input_plan_sha": self.input_plan_sha,
            "fixture_catalog_sha256": self.fixture_catalog_sha256,
            "case_count": self.case_count,
            "cases": [case.as_dict() for case in self.cases],
            "all_cases_passed": self.all_cases_passed,
            "next_action": self.next_action,
        }
        _assert_body_free(payload)
        if set(payload) != _RECEIPT_KEYS:
            raise ResponseProfileSplitError("receipt_field_not_allowlisted", "receipt")
        return payload

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "ResponseProfileSplitReceipt":
        if not isinstance(value, Mapping) or set(value) != _RECEIPT_KEYS:
            raise ResponseProfileSplitError("receipt_fields_invalid", "receipt")
        _assert_body_free(value)
        raw_cases = value.get("cases")
        if not isinstance(raw_cases, list):
            raise ResponseProfileSplitError("cases_invalid", "cases")
        raw_case_count = value.get("case_count")
        if (
            isinstance(raw_case_count, bool)
            or not isinstance(raw_case_count, int)
            or raw_case_count != len(raw_cases)
        ):
            raise ResponseProfileSplitError("case_count_mismatch", "case_count")
        try:
            cases = tuple(ResponseProfileSplitCase.from_dict(item) for item in raw_cases)
            payload = dict(value)
            payload["cases"] = cases
            payload.pop("case_count", None)
            result = cls(**payload)  # type: ignore[arg-type]
        except ResponseProfileSplitError:
            raise
        except (TypeError, ValueError):
            raise ResponseProfileSplitError("receipt_shape_invalid", "receipt") from None
        if result.as_dict() != dict(value):
            raise ResponseProfileSplitError("receipt_round_trip_mismatch", "receipt")
        return result


def _profile(fixture: ResponseProfileSplitFixture) -> ZhipuThinkingProfile:
    """Build a local request profile without constructing a provider client."""

    return ZhipuThinkingProfile(
        profile_id=fixture.profile_id,
        model=MODEL,
        thinking_type="enabled",
        reasoning_effort=fixture.reasoning_effort,
        clear_thinking=fixture.clear_thinking,
    )


def _context() -> ResponseRequestContext:
    return ResponseRequestContext(
        phase="agent_initial",
        has_response_contract=False,
        has_tools=False,
        has_tool_side_effects=False,
        remaining_timeout_s=90.0,
        remaining_token_budget=8192,
    )


def _context_for(fixture: ResponseProfileSplitFixture) -> ResponseRequestContext:
    return ResponseRequestContext(
        phase="agent_initial",
        has_response_contract=False,
        has_tools=False,
        has_tool_side_effects=False,
        remaining_timeout_s=float(fixture.agent_timeout_s),
        remaining_token_budget=fixture.max_output_tokens,
    )


def _request_id_sha() -> str:
    return hashlib.sha256(b"offline-profile-terminal-recovery-request").hexdigest()


def _event_stream(kind: FixtureKind) -> tuple[ProviderStreamEvent, ...]:
    request_id = _request_id_sha()
    if kind == "complete_stop":
        return (
            ProviderStreamEvent(content_delta="", reasoning_delta="private fixture reasoning", sequence=1, model=MODEL, request_id_sha256=request_id),
            ProviderStreamEvent(content_delta="private fixture answer", sequence=2, model=MODEL, request_id_sha256=request_id),
            ProviderStreamEvent(finish_reason="stop", sequence=3, model=MODEL, request_id_sha256=request_id),
            ProviderStreamEvent(usage=TokenUsage(20, 12, 0), sequence=4, model=None, request_id_sha256=None),
        )
    if kind in {"candidate_length", "elapsed_timeout"}:
        return (
            ProviderStreamEvent(content_delta="", reasoning_delta="private fixture reasoning", sequence=1, model=MODEL, request_id_sha256=request_id),
            ProviderStreamEvent(finish_reason="length", sequence=2, model=MODEL, request_id_sha256=request_id),
            ProviderStreamEvent(usage=TokenUsage(20, 8192, 0), sequence=3, model=None, request_id_sha256=None),
        )
    if kind == "tool_calls":
        return (
            ProviderStreamEvent(
                tool_call_deltas=(
                    StreamToolCallDelta(index=0, call_id="fixture-call", name="knowledge.search", arguments_delta="{}"),
                ),
                sequence=1,
                model=MODEL,
                request_id_sha256=request_id,
            ),
            ProviderStreamEvent(finish_reason="tool_calls", sequence=2, model=MODEL, request_id_sha256=request_id),
            ProviderStreamEvent(usage=TokenUsage(20, 32, 0), sequence=3, model=None, request_id_sha256=None),
        )
    if kind == "missing_usage":
        return (
            ProviderStreamEvent(content_delta="private fixture answer", sequence=1, model=MODEL, request_id_sha256=request_id),
            ProviderStreamEvent(finish_reason="stop", sequence=2, model=MODEL, request_id_sha256=request_id),
        )
    raise ResponseProfileSplitError("stream_fixture_not_supported", "kind")


def _snapshot_fixture(kind: FixtureKind) -> ResponseBoundarySnapshot:
    if kind == "partial_length":
        return ResponseBoundarySnapshot(
            finish_reason="length",
            content_state="non_empty",
            reasoning_content_state="non_empty",
            tool_call_count=0,
            usage_state="valid",
        )
    if kind == "invalid_usage":
        return ResponseBoundarySnapshot(
            finish_reason="stop",
            content_state="non_empty",
            reasoning_content_state="non_empty",
            tool_call_count=0,
            usage_state="invalid",
        )
    raise ResponseProfileSplitError("snapshot_fixture_not_supported", "kind")


def _observe(fixture: ResponseProfileSplitFixture):
    if fixture.kind in {"partial_length", "invalid_usage"}:
        return None
    events = fixture._events
    if fixture.kind == "elapsed_timeout":
        observer = CandidateStreamBoundaryObserver(clock=lambda: 1.0)
        observer.open()
        observer.accept(events[0])
        observer.abort("elapsed_limit", "budget")
        return observer.finalize()
    return observe_candidate_events(events, clock=lambda: 1.0)


def _decision_dict(decision: ResponseCompletionDecision | None) -> tuple[str | None, str | None, bool]:
    if decision is None:
        return None, None, False
    return decision.disposition.value, decision.reason_code, decision.continuation_allowed


def _run_fixture(fixture: ResponseProfileSplitFixture) -> ResponseProfileSplitCase:
    profile = _profile(fixture)
    # Validate the request-shape side of the split without retaining its body.
    extra_body = profile.extra_body()
    if extra_body.get("thinking", {}).get("type") != "enabled":  # type: ignore[union-attr]
        raise ResponseProfileSplitError("profile_shape_invalid", "thinking_type")
    if extra_body.get("reasoning_effort") != fixture.reasoning_effort:
        raise ResponseProfileSplitError("profile_shape_invalid", "reasoning_effort")

    observation = _observe(fixture)
    boundary_source: BoundarySource
    observed_state: ObservedState
    observed_error_code: str | None
    terminal_observation: TerminalObservation
    usage_observation: UsageObservation
    snapshot: ResponseBoundarySnapshot | None
    if observation is not None:
        boundary_source = "stream_observer"
        observed_state = observation.observation_state  # type: ignore[assignment]
        observed_error_code = observation.error_code
        terminal_observation = (
            "stop"
            if observation.finish_reason == "stop"
            else "tool_calls"
            if observation.finish_reason == "tool_calls"
            else "length"
            if observation.finish_reason == "length"
            else "timeout"
            if fixture.kind == "elapsed_timeout"
            else "missing"
        )
        usage_observation = observation.usage_state
        snapshot = (
            observation.to_response_boundary_snapshot()
            if observation.complete_boundary
            else None
        )
    else:
        boundary_source = "policy_snapshot"
        snapshot = _snapshot_fixture(fixture.kind)
        observed_state = "fail_closed"
        observed_error_code = None
        terminal_observation = "length" if fixture.kind == "partial_length" else "stop"
        usage_observation = "invalid" if fixture.kind == "invalid_usage" else "valid"

    context = _context_for(fixture)
    strict_decision = (
        GLM53_FLASH_RESPONSE_COMPLETION_POLICY_V1.decide(snapshot, context)
        if snapshot is not None
        else None
    )
    candidate_decision = (
        GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1.decide(snapshot, context)
        if snapshot is not None
        else None
    )
    strict_disposition, strict_reason, _ = _decision_dict(strict_decision)
    candidate_disposition, candidate_reason, candidate_continue = _decision_dict(candidate_decision)
    if candidate_decision is None:
        recovery_action: RecoveryAction = "boundary_incomplete"
    elif candidate_decision.disposition is ResponseDisposition.CANDIDATE_ELIGIBLE:
        recovery_action = "blocked_activation"
    elif candidate_decision.disposition in {
        ResponseDisposition.COMPLETE_TEXT,
        ResponseDisposition.TOOL_CALLS_READY,
    }:
        recovery_action = "none"
    else:
        recovery_action = "not_eligible"

    passed = (
        fixture.expected_terminal_observation == terminal_observation
        and fixture.expected_usage_observation == usage_observation
        and fixture.expected_state == observed_state
        and fixture.expected_error_code == observed_error_code
        and fixture.expected_strict_disposition == strict_disposition
        and fixture.expected_strict_reason_code == strict_reason
        and fixture.expected_candidate_disposition == candidate_disposition
        and fixture.expected_candidate_reason_code == candidate_reason
        and fixture.expected_candidate_continuation_allowed == candidate_continue
        and fixture.expected_recovery_action == recovery_action
    )
    return ResponseProfileSplitCase(
        case_id=fixture.case_id,
        profile_id=fixture.profile_id,
        reasoning_effort=fixture.reasoning_effort,
        clear_thinking=fixture.clear_thinking,
        max_output_tokens=fixture.max_output_tokens,
        agent_timeout_s=fixture.agent_timeout_s,
        boundary_source=boundary_source,
        terminal_observation=terminal_observation,
        usage_observation=usage_observation,
        observed_state=observed_state,
        observed_error_code=observed_error_code,
        strict_disposition=strict_disposition,
        strict_reason_code=strict_reason,
        candidate_disposition=candidate_disposition,
        candidate_reason_code=candidate_reason,
        candidate_continuation_allowed=candidate_continue,
        recovery_action=recovery_action,
        passed=passed,
    )


def _fixture(
    *,
    case_id: str,
    profile_id: str,
    reasoning_effort: Literal["low", "max"],
    clear_thinking: bool,
    max_output_tokens: Literal[2048, 8192],
    agent_timeout_s: float,
    kind: FixtureKind,
    terminal: TerminalObservation,
    usage: UsageObservation,
    state: ObservedState,
    error: str | None,
    strict: tuple[str | None, str | None],
    candidate: tuple[str | None, str | None],
    continue_allowed: bool,
    action: RecoveryAction,
) -> ResponseProfileSplitFixture:
    events = _event_stream(kind) if kind not in {"partial_length", "invalid_usage"} else ()
    snapshot = _snapshot_fixture(kind) if kind in {"partial_length", "invalid_usage"} else None
    return ResponseProfileSplitFixture(
        case_id=case_id,
        profile_id=profile_id,
        reasoning_effort=reasoning_effort,
        clear_thinking=clear_thinking,
        max_output_tokens=max_output_tokens,
        agent_timeout_s=agent_timeout_s,
        kind=kind,
        expected_terminal_observation=terminal,
        expected_usage_observation=usage,
        expected_state=state,
        expected_error_code=error,
        expected_strict_disposition=strict[0],
        expected_strict_reason_code=strict[1],
        expected_candidate_disposition=candidate[0],
        expected_candidate_reason_code=candidate[1],
        expected_candidate_continuation_allowed=continue_allowed,
        expected_recovery_action=action,
        _events=events,
        _snapshot=snapshot,
    )


RESPONSE_PROFILE_SPLIT_FIXTURES: tuple[ResponseProfileSplitFixture, ...] = (
    _fixture(
        case_id="low-2048-complete-stop",
        profile_id="offline-glm53-flash-low-2048",
        reasoning_effort="low",
        clear_thinking=False,
        max_output_tokens=2048,
        agent_timeout_s=45.0,
        kind="complete_stop",
        terminal="stop",
        usage="valid",
        state="complete_text",
        error=None,
        strict=("complete_text", "complete_text"),
        candidate=("complete_text", "complete_text"),
        continue_allowed=False,
        action="none",
    ),
    _fixture(
        case_id="low-8192-candidate-length",
        profile_id="offline-glm53-flash-low-8192",
        reasoning_effort="low",
        clear_thinking=False,
        max_output_tokens=8192,
        agent_timeout_s=90.0,
        kind="candidate_length",
        terminal="length",
        usage="valid",
        state="candidate_shape",
        error=None,
        strict=("fail_closed", "length_reasoning_only"),
        candidate=("candidate_eligible", "fresh_recovery_shape_eligible"),
        continue_allowed=False,
        action="blocked_activation",
    ),
    _fixture(
        case_id="max-8192-candidate-length",
        profile_id="offline-glm53-flash-max-8192",
        reasoning_effort="max",
        clear_thinking=False,
        max_output_tokens=8192,
        agent_timeout_s=90.0,
        kind="candidate_length",
        terminal="length",
        usage="valid",
        state="candidate_shape",
        error=None,
        strict=("fail_closed", "length_reasoning_only"),
        candidate=("candidate_eligible", "fresh_recovery_shape_eligible"),
        continue_allowed=False,
        action="blocked_activation",
    ),
    _fixture(
        case_id="max-8192-clear-true-candidate-length",
        profile_id="offline-glm53-flash-max-8192-clear-true",
        reasoning_effort="max",
        clear_thinking=True,
        max_output_tokens=8192,
        agent_timeout_s=90.0,
        kind="candidate_length",
        terminal="length",
        usage="valid",
        state="candidate_shape",
        error=None,
        strict=("fail_closed", "length_reasoning_only"),
        candidate=("candidate_eligible", "fresh_recovery_shape_eligible"),
        continue_allowed=False,
        action="blocked_activation",
    ),
    _fixture(
        case_id="low-2048-terminal-without-usage",
        profile_id="offline-glm53-flash-low-2048-no-usage",
        reasoning_effort="low",
        clear_thinking=False,
        max_output_tokens=2048,
        agent_timeout_s=45.0,
        kind="missing_usage",
        terminal="stop",
        usage="missing",
        state="fail_closed",
        error="usage_unavailable",
        strict=(None, None),
        candidate=(None, None),
        continue_allowed=False,
        action="boundary_incomplete",
    ),
    _fixture(
        case_id="max-8192-elapsed-before-terminal",
        profile_id="offline-glm53-flash-max-8192-timeout",
        reasoning_effort="max",
        clear_thinking=False,
        max_output_tokens=8192,
        agent_timeout_s=90.0,
        kind="elapsed_timeout",
        terminal="timeout",
        usage="missing",
        state="fail_closed",
        error="elapsed_limit",
        strict=(None, None),
        candidate=(None, None),
        continue_allowed=False,
        action="boundary_incomplete",
    ),
    _fixture(
        case_id="max-8192-partial-content-length",
        profile_id="offline-glm53-flash-max-8192-partial",
        reasoning_effort="max",
        clear_thinking=False,
        max_output_tokens=8192,
        agent_timeout_s=90.0,
        kind="partial_length",
        terminal="length",
        usage="valid",
        state="fail_closed",
        error=None,
        strict=("fail_closed", "length_partial_content"),
        candidate=("fail_closed", "length_partial_content"),
        continue_allowed=False,
        action="not_eligible",
    ),
    _fixture(
        case_id="max-8192-invalid-usage",
        profile_id="offline-glm53-flash-max-8192-invalid-usage",
        reasoning_effort="max",
        clear_thinking=False,
        max_output_tokens=8192,
        agent_timeout_s=90.0,
        kind="invalid_usage",
        terminal="stop",
        usage="invalid",
        state="fail_closed",
        error=None,
        strict=("fail_closed", "usage_unavailable"),
        candidate=("fail_closed", "usage_unavailable"),
        continue_allowed=False,
        action="not_eligible",
    ),
    _fixture(
        case_id="max-8192-tool-calls-ready",
        profile_id="offline-glm53-flash-max-8192-tools",
        reasoning_effort="max",
        clear_thinking=False,
        max_output_tokens=8192,
        agent_timeout_s=90.0,
        kind="tool_calls",
        terminal="tool_calls",
        usage="valid",
        state="tool_calls_ready",
        error=None,
        strict=("tool_calls_ready", "tool_calls_ready"),
        candidate=("tool_calls_ready", "tool_calls_ready"),
        continue_allowed=False,
        action="none",
    ),
)

RESPONSE_PROFILE_SPLIT_FIXTURE_CATALOG_SHA256 = _sha256(
    [fixture.descriptor() for fixture in RESPONSE_PROFILE_SPLIT_FIXTURES]
)


def run_response_profile_terminal_recovery_split(
    *,
    implementation_sha: str,
    diagnostic_code_sha: str,
    input_plan_sha: str,
) -> ResponseProfileSplitReceipt:
    """Run the deterministic fixture matrix without network or credentials."""

    _require_git_sha(implementation_sha, "implementation_sha")
    _require_git_sha(diagnostic_code_sha, "diagnostic_code_sha")
    _require_git_sha(input_plan_sha, "input_plan_sha")
    cases = tuple(_run_fixture(fixture) for fixture in RESPONSE_PROFILE_SPLIT_FIXTURES)
    return ResponseProfileSplitReceipt(
        implementation_sha=implementation_sha,
        diagnostic_code_sha=diagnostic_code_sha,
        input_plan_sha=input_plan_sha,
        fixture_catalog_sha256=RESPONSE_PROFILE_SPLIT_FIXTURE_CATALOG_SHA256,
        cases=cases,
        all_cases_passed=all(case.passed for case in cases),
    )


def canonical_receipt_bytes(receipt: ResponseProfileSplitReceipt) -> bytes:
    if not isinstance(receipt, ResponseProfileSplitReceipt):
        raise TypeError("receipt must be a ResponseProfileSplitReceipt")
    return _canonical_json(receipt.as_dict())


def write_response_profile_terminal_recovery_receipt(
    output: Path,
    receipt: ResponseProfileSplitReceipt,
    *,
    offline_root: Path,
) -> Path:
    """Write one immutable receipt inside the dedicated offline tree."""

    if not isinstance(output, Path) or not isinstance(offline_root, Path):
        raise ResponseProfileSplitError("path_type_invalid", "output")
    try:
        root = offline_root.resolve()
        target = output.resolve()
    except OSError:
        raise ResponseProfileSplitError("output_path_invalid", "output") from None
    if target.suffix.lower() != ".json" or not target.is_relative_to(root):
        raise ResponseProfileSplitError("offline_path_required", "output")
    if target.exists():
        raise FileExistsError("immutable offline receipt already exists")
    _assert_body_free(receipt.as_dict())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(canonical_receipt_bytes(receipt))
    return target


__all__ = [
    "DEFAULT_OUTPUT",
    "EVIDENCE_ORIGIN",
    "MODEL",
    "PROTOCOL_ID",
    "RESPONSE_PROFILE_SPLIT_FIXTURES",
    "RESPONSE_PROFILE_SPLIT_FIXTURE_CATALOG_SHA256",
    "ResponseProfileSplitCase",
    "ResponseProfileSplitError",
    "ResponseProfileSplitFixture",
    "ResponseProfileSplitReceipt",
    "SCHEMA_VERSION",
    "canonical_receipt_bytes",
    "run_response_profile_terminal_recovery_split",
    "write_response_profile_terminal_recovery_receipt",
]
