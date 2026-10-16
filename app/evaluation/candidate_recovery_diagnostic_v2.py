"""Versioned, body-free recovery diagnostics for the GLM-5.3 candidate.

This module is an evaluation-only control-plane seam.  It deliberately has no
provider SDK, network client, credential loader, product Runtime, or provider
registry import.  A caller supplies a fake/local normalized stream transport;
the module records only the facts needed to explain one bounded observation.

The implementation follows the frozen RQ-203 protocol:

``reserve -> open -> observe/assemble -> settle -> receipt``

The candidate activation gate is intentionally sealed ``disabled``.  Thus a
matching ``length`` shape is recorded as eligible evidence, but this module
cannot send a second request or silently turn the candidate into a product
runtime.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import tempfile
import time
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass, field, replace
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from enum import StrEnum
from math import isfinite
from pathlib import Path
from typing import Any, Literal, TypeAlias

from app.providers.models import (
    ChatMessage,
    ChatRequest,
    MessageRole,
    TokenUsage,
    ToolChoiceMode,
)
from app.providers.response_completion_policy import (
    GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1,
    ResponseBoundarySnapshot,
    ResponseCompletionDecision,
    ResponseCompletionPolicy,
    ResponseDisposition,
    ResponseRequestContext,
)
from app.providers.response_recovery_contract import (
    GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1,
    ResponseRecoveryRuntimeProfile,
)
from app.providers.stream_adapter_contract import (
    ProviderStreamAssembler,
    ProviderStreamEvent,
    StreamAdapterError,
    StreamAssemblyResult,
)

from .candidate_stream_contract import (
    BoundaryObservation,
    CANDIDATE_MODEL,
    CANDIDATE_POLICY_ID,
    CANDIDATE_POLICY_VERSION,
    CANDIDATE_PROVIDER_ID,
    CANDIDATE_RUNTIME_PROFILE_ID,
    CANDIDATE_RUNTIME_PROFILE_VERSION,
    CandidateAttemptKind,
    CandidateBoundaryContractError,
    CandidateRuntimeBinding,
    CandidateStreamBoundaryObserver,
    CandidateStreamDeadlineSupervisor,
    CandidateStreamSession,
    CandidateStreamTrace,
    CandidateStreamTransport,
    CandidateTransportError,
    FRESH_RECOVERY_CANDIDATE_BINDING,
    PRIMARY_CANDIDATE_BINDING,
    require_candidate_stream_session,
)


CANDIDATE_RECOVERY_DIAGNOSTIC_PROTOCOL_ID = (
    "glm-5.3-flash-candidate-recovery-diagnostic-v2"
)
CANDIDATE_RECOVERY_DIAGNOSTIC_SCHEMA_VERSION = "2.0.0"
CANDIDATE_RECOVERY_DIAGNOSTIC_RECEIPT_SCHEMA = (
    f"{CANDIDATE_RECOVERY_DIAGNOSTIC_PROTOCOL_ID}/{CANDIDATE_RECOVERY_DIAGNOSTIC_SCHEMA_VERSION}"
)

_SAFE_CODE = re.compile(r"^[a-z][a-z0-9_.-]{0,95}$")
_SAFE_ID = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
_CURRENCY = re.compile(r"^[A-Z]{3}$")
_FORBIDDEN_KEYS = frozenset(
    {
        "prompt",
        "body",
        "content",
        "reasoning",
        "reasoning_content",
        "tool_arguments",
        "tool_results",
        "api_key",
        "key",
        "secret",
        "request_id",
        "sdk_response",
    }
)

_RECEIPT_KEYS = frozenset(
    {
        "schema_version",
        "protocol_id",
        "provider_id",
        "model",
        "runtime_profile_id",
        "runtime_profile_version",
        "policy_id",
        "policy_version",
        "implementation_sha",
        "diagnostic_code_sha",
        "input_plan_sha",
        "context_shape_sha",
        "run_nonce_sha256",
        "activation_state",
        "activation_gate",
        "execution_allowed",
        "run_state",
        "attempts",
        "budget",
        "cost",
        "first_failure",
        "terminal_reason",
        "recovery_skip_reason",
    }
)
_REQUEST_SUMMARY_KEYS = frozenset(
    {
        "attempt_ordinal",
        "attempt_kind",
        "message_count",
        "roles",
        "messages",
        "tool_count",
        "tool_choice",
        "response_contract_present",
        "response_contract_name",
        "response_contract_version",
        "response_contract_shape_sha256",
        "output_cap",
        "agent_timeout_s",
        "transport_timeout_s",
        "temperature",
        "top_p",
        "sdk_retries",
        "shape_sha256",
        "candidate_identity",
    }
)
_MESSAGE_SHAPE_KEYS = frozenset(
    {
        "role",
        "content_present",
        "content_chars",
        "reasoning_present",
        "reasoning_chars",
        "tool_call_count",
        "tool_call_id_present_count",
        "tool_name_present_count",
        "tool_argument_key_count",
        "tool_result_id_present",
        "name_present",
    }
)
_OBSERVATION_KEYS = frozenset(
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
    }
)
_ATTEMPT_KEYS = frozenset(
    {
        "ordinal",
        "attempt_kind",
        "request",
        "observation",
        "latency",
        "cost",
        "disposition",
        "reason_code",
        "error_code",
        "error_stage",
        "failure_class",
        "assembled_complete",
        "settled",
        "input_tokens",
        "output_tokens",
        "cached_input_tokens",
        "usage_state",
        "budget_state",
        "consumer_error_code",
    }
)
_LATENCY_KEYS = frozenset(
    {
        "open_elapsed_ms",
        "first_event_ms",
        "first_visible_content_ms",
        "terminal_ms",
        "close_elapsed_ms",
        "total_elapsed_ms",
    }
)
_COST_KEYS = frozenset(
    {
        "status",
        "currency",
        "price_snapshot_id_sha256",
        "amount",
        "billing_evidence_sha256",
    }
)
_BUDGET_KEYS = frozenset(
    {
        "calls_reserved",
        "calls_settled",
        "input_tokens",
        "output_tokens",
        "elapsed_ms",
        "input_state",
        "output_state",
        "elapsed_state",
        "calls_state",
        "overall_state",
        "limits",
    }
)
_BUDGET_LIMIT_KEYS = frozenset(
    {
        "max_attempts",
        "max_additional_calls",
        "max_total_input_tokens",
        "max_total_output_tokens",
        "max_total_elapsed_ms",
    }
)

FailureClass: TypeAlias = Literal[
    "transport",
    "protocol",
    "identity",
    "usage",
    "budget",
    "completion",
    "consumer",
    "control",
]
RunState: TypeAlias = Literal[
    "complete_text",
    "tool_calls_ready",
    "candidate_eligible",
    "recovery_complete",
    "fail_closed",
    "interrupted",
]
BudgetState: TypeAlias = Literal["within", "exceeded", "unknown"]
CostState: TypeAlias = Literal["unknown", "estimated", "actual"]


class DiagnosticFailureClass(StrEnum):
    TRANSPORT = "transport"
    PROTOCOL = "protocol"
    IDENTITY = "identity"
    USAGE = "usage"
    BUDGET = "budget"
    COMPLETION = "completion"
    CONSUMER = "consumer"
    CONTROL = "control"


class DiagnosticActivationGate(StrEnum):
    """Only the sealed candidate gate is constructible in this version."""

    DISABLED = "disabled"

    @property
    def execution_allowed(self) -> bool:
        return False


class CandidateRecoveryDiagnosticError(ValueError):
    """Safe, body-free error raised by the diagnostic contract."""

    def __init__(self, code: str, stage: str | None = None) -> None:
        if not isinstance(code, str) or not _SAFE_CODE.fullmatch(code):
            raise ValueError("diagnostic error code must be a safe code")
        if stage is not None and (
            not isinstance(stage, str) or not _SAFE_CODE.fullmatch(stage)
        ):
            raise ValueError("diagnostic error stage must be a safe code")
        self.code = code
        self.stage = stage
        super().__init__(code)


def _require_safe_code(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not _SAFE_CODE.fullmatch(value):
        raise CandidateRecoveryDiagnosticError("unsafe_code", field_name)
    return value


def _require_safe_id(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
        raise CandidateRecoveryDiagnosticError("unsafe_identifier", field_name)
    return value


def _require_non_negative_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CandidateRecoveryDiagnosticError("invalid_integer", field_name)
    return value


def _require_sha256(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise CandidateRecoveryDiagnosticError("invalid_sha256", field_name)
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
        raise CandidateRecoveryDiagnosticError("json_not_serializable", "serialize") from None


def _assert_body_free(value: object) -> None:
    """Reject forbidden field names recursively before any JSON is emitted."""

    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str) and key.strip().lower() in _FORBIDDEN_KEYS:
                raise CandidateRecoveryDiagnosticError("receipt_field_forbidden", "serialize")
            _assert_body_free(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            _assert_body_free(item)


def _mapping(value: object, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CandidateRecoveryDiagnosticError("receipt_shape_invalid", field_name)
    if any(not isinstance(key, str) for key in value):
        raise CandidateRecoveryDiagnosticError("receipt_key_invalid", field_name)
    return value


def _exact_keys(value: Mapping[str, Any], expected: frozenset[str], field_name: str) -> None:
    if set(value) != expected:
        raise CandidateRecoveryDiagnosticError("receipt_field_not_allowlisted", field_name)


def _sha256_canonical(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _default_nonce_sha() -> str:
    return hashlib.sha256(secrets.token_bytes(32)).hexdigest()


@dataclass(frozen=True, slots=True)
class CandidateRecoveryDiagnosticIdentity:
    """Exact protocol/profile/policy and source identity for one run."""

    implementation_sha: str
    diagnostic_code_sha: str
    input_plan_sha: str
    context_shape_sha: str
    run_nonce_sha256: str = field(default_factory=_default_nonce_sha)
    protocol_id: str = CANDIDATE_RECOVERY_DIAGNOSTIC_PROTOCOL_ID
    schema_version: str = CANDIDATE_RECOVERY_DIAGNOSTIC_SCHEMA_VERSION
    provider_id: str = CANDIDATE_PROVIDER_ID
    model: str = CANDIDATE_MODEL
    runtime_profile_id: str = CANDIDATE_RUNTIME_PROFILE_ID
    runtime_profile_version: str = CANDIDATE_RUNTIME_PROFILE_VERSION
    policy_id: str = CANDIDATE_POLICY_ID
    policy_version: str = CANDIDATE_POLICY_VERSION

    def __post_init__(self) -> None:
        for name in (
            "implementation_sha",
            "diagnostic_code_sha",
            "input_plan_sha",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not _GIT_SHA.fullmatch(value):
                raise CandidateRecoveryDiagnosticError("invalid_git_sha", name)
        _require_sha256(self.context_shape_sha, "context_shape_sha")
        _require_sha256(self.run_nonce_sha256, "run_nonce_sha256")
        if self.protocol_id != CANDIDATE_RECOVERY_DIAGNOSTIC_PROTOCOL_ID:
            raise CandidateRecoveryDiagnosticError("protocol_identity_mismatch", "identity")
        if self.schema_version != CANDIDATE_RECOVERY_DIAGNOSTIC_SCHEMA_VERSION:
            raise CandidateRecoveryDiagnosticError("schema_identity_mismatch", "identity")
        expected = {
            "provider_id": CANDIDATE_PROVIDER_ID,
            "model": CANDIDATE_MODEL,
            "runtime_profile_id": CANDIDATE_RUNTIME_PROFILE_ID,
            "runtime_profile_version": CANDIDATE_RUNTIME_PROFILE_VERSION,
            "policy_id": CANDIDATE_POLICY_ID,
            "policy_version": CANDIDATE_POLICY_VERSION,
        }
        for name, wanted in expected.items():
            if getattr(self, name) != wanted:
                raise CandidateRecoveryDiagnosticError("candidate_identity_mismatch", "identity")

    def as_dict(self) -> dict[str, Any]:
        return {
            "protocol_id": self.protocol_id,
            "schema_version": self.schema_version,
            "provider_id": self.provider_id,
            "model": self.model,
            "runtime_profile_id": self.runtime_profile_id,
            "runtime_profile_version": self.runtime_profile_version,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "implementation_sha": self.implementation_sha,
            "diagnostic_code_sha": self.diagnostic_code_sha,
            "input_plan_sha": self.input_plan_sha,
            "context_shape_sha": self.context_shape_sha,
            "run_nonce_sha256": self.run_nonce_sha256,
        }


def context_shape_sha256(context: ResponseRequestContext) -> str:
    """Hash only bounded context flags; never hash or retain a prompt."""

    if not isinstance(context, ResponseRequestContext):
        raise TypeError("context must be a ResponseRequestContext")
    return _sha256_canonical(
        {
            "phase": context.phase,
            "has_response_contract": context.has_response_contract,
            "has_tools": context.has_tools,
            "has_tool_side_effects": context.has_tool_side_effects,
            "remaining_timeout_s": float(context.remaining_timeout_s),
            "remaining_token_budget": context.remaining_token_budget,
        }
    )


def _default_context() -> ResponseRequestContext:
    return ResponseRequestContext(
        phase="agent_initial",
        has_response_contract=False,
        has_tools=False,
        has_tool_side_effects=False,
        remaining_timeout_s=90.0,
        remaining_token_budget=8192,
    )


@dataclass(frozen=True, slots=True)
class CandidateRecoveryRunSpec:
    """Immutable trusted inputs for one diagnostic run."""

    identity: CandidateRecoveryDiagnosticIdentity
    context: ResponseRequestContext = field(default_factory=_default_context)
    runtime_profile: ResponseRecoveryRuntimeProfile = (
        GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1
    )
    policy: ResponseCompletionPolicy = GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1
    activation: DiagnosticActivationGate = DiagnosticActivationGate.DISABLED

    @classmethod
    def new(
        cls,
        *,
        implementation_sha: str,
        diagnostic_code_sha: str,
        input_plan_sha: str,
        context: ResponseRequestContext | None = None,
        run_nonce_sha256: str | None = None,
    ) -> "CandidateRecoveryRunSpec":
        selected = context or _default_context()
        return cls(
            identity=CandidateRecoveryDiagnosticIdentity(
                implementation_sha=implementation_sha,
                diagnostic_code_sha=diagnostic_code_sha,
                input_plan_sha=input_plan_sha,
                context_shape_sha=context_shape_sha256(selected),
                run_nonce_sha256=run_nonce_sha256 or _default_nonce_sha(),
            ),
            context=selected,
        )

    create = new

    def __post_init__(self) -> None:
        if not isinstance(self.identity, CandidateRecoveryDiagnosticIdentity):
            raise TypeError("identity must be CandidateRecoveryDiagnosticIdentity")
        if not isinstance(self.context, ResponseRequestContext):
            raise TypeError("context must be ResponseRequestContext")
        if self.identity.context_shape_sha != context_shape_sha256(self.context):
            raise CandidateRecoveryDiagnosticError("context_identity_mismatch", "identity")
        if self.runtime_profile is not GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1:
            raise CandidateRecoveryDiagnosticError("runtime_profile_mismatch", "identity")
        if self.policy is not GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1:
            raise CandidateRecoveryDiagnosticError("policy_identity_mismatch", "identity")
        if not self.runtime_profile.matches_policy(self.policy):
            raise CandidateRecoveryDiagnosticError("profile_policy_mismatch", "identity")
        if self.activation is not DiagnosticActivationGate.DISABLED:
            raise CandidateRecoveryDiagnosticError("activation_gate_invalid", "activation")

    def as_dict(self) -> dict[str, Any]:
        return {
            **self.identity.as_dict(),
            "activation_state": "candidate",
            "activation_gate": self.activation.value,
            "execution_allowed": False,
            "context": {
                "phase": self.context.phase,
                "has_response_contract": self.context.has_response_contract,
                "has_tools": self.context.has_tools,
                "has_tool_side_effects": self.context.has_tool_side_effects,
                "remaining_timeout_s": self.context.remaining_timeout_s,
                "remaining_token_budget": self.context.remaining_token_budget,
            },
        }


@dataclass(frozen=True, slots=True)
class CandidateRecoveryExecutionPermit:
    """A one-use permit value used only to explain future recovery gates.

    ``for_offline_test`` creates a synthetic permit for contract tests.  The
    current diagnostic runner still rejects it because activation is sealed
    disabled; no public constructor can turn that gate on.
    """

    permit_id_sha256: str
    binding: CandidateRuntimeBinding = field(
        default_factory=CandidateRuntimeBinding.fresh_recovery
    )
    issued_at_ms: int = 0
    expires_at_ms: int = 1
    purpose: str = "candidate-recovery-diagnostic"

    @classmethod
    def for_offline_test(
        cls,
        binding: CandidateRuntimeBinding = FRESH_RECOVERY_CANDIDATE_BINDING,
        *,
        now_ms: int = 0,
        ttl_ms: int = 60_000,
    ) -> "CandidateRecoveryExecutionPermit":
        if binding != FRESH_RECOVERY_CANDIDATE_BINDING:
            raise CandidateRecoveryDiagnosticError("permit_identity_mismatch", "activation")
        _require_non_negative_int(now_ms, "now_ms")
        if isinstance(ttl_ms, bool) or not isinstance(ttl_ms, int) or ttl_ms <= 0:
            raise CandidateRecoveryDiagnosticError("permit_ttl_invalid", "activation")
        return cls(
            permit_id_sha256=hashlib.sha256(secrets.token_bytes(32)).hexdigest(),
            binding=binding,
            issued_at_ms=now_ms,
            expires_at_ms=now_ms + ttl_ms,
        )

    def __post_init__(self) -> None:
        _require_sha256(self.permit_id_sha256, "permit_id_sha256")
        if self.binding != FRESH_RECOVERY_CANDIDATE_BINDING:
            raise CandidateRecoveryDiagnosticError("permit_identity_mismatch", "activation")
        _require_non_negative_int(self.issued_at_ms, "issued_at_ms")
        _require_non_negative_int(self.expires_at_ms, "expires_at_ms")
        if self.expires_at_ms <= self.issued_at_ms:
            raise CandidateRecoveryDiagnosticError("permit_expiry_invalid", "activation")
        _require_safe_code(self.purpose, "purpose")

    def verify(
        self,
        binding: CandidateRuntimeBinding,
        *,
        now_ms: int,
        used: bool = False,
        activation: DiagnosticActivationGate | None = None,
    ) -> Literal["valid", "activation_disabled", "expired", "reused", "identity_mismatch"]:
        if binding != self.binding:
            return "identity_mismatch"
        if activation is not None:
            if activation is not DiagnosticActivationGate.DISABLED:
                raise CandidateRecoveryDiagnosticError("activation_gate_invalid", "activation")
            return "activation_disabled"
        if used:
            return "reused"
        if isinstance(now_ms, bool) or not isinstance(now_ms, int):
            raise CandidateRecoveryDiagnosticError("invalid_integer", "now_ms")
        if now_ms < self.issued_at_ms or now_ms >= self.expires_at_ms:
            return "expired"
        return "valid"


@dataclass(frozen=True, slots=True)
class MessageShape:
    """Field-presence/length counts for one message; no message body."""

    role: str
    content_present: bool
    content_chars: int
    reasoning_present: bool
    reasoning_chars: int
    tool_call_count: int
    tool_call_id_present_count: int
    tool_name_present_count: int
    tool_argument_key_count: int
    tool_result_id_present: bool
    name_present: bool

    def __post_init__(self) -> None:
        _require_safe_id(self.role, "role")
        if self.role not in {role.value for role in MessageRole}:
            raise CandidateRecoveryDiagnosticError("role_invalid", "request")
        for name in (
            "content_chars",
            "reasoning_chars",
            "tool_call_count",
            "tool_call_id_present_count",
            "tool_name_present_count",
            "tool_argument_key_count",
        ):
            _require_non_negative_int(getattr(self, name), name)
        for name in (
            "content_present",
            "reasoning_present",
            "tool_result_id_present",
            "name_present",
        ):
            if not isinstance(getattr(self, name), bool):
                raise CandidateRecoveryDiagnosticError("shape_boolean_invalid", "request")
        if self.tool_call_id_present_count > self.tool_call_count:
            raise CandidateRecoveryDiagnosticError("shape_count_invalid", "request")
        if self.tool_name_present_count > self.tool_call_count:
            raise CandidateRecoveryDiagnosticError("shape_count_invalid", "request")
        if not self.content_present and self.content_chars != 0:
            raise CandidateRecoveryDiagnosticError("shape_presence_invalid", "request")
        if not self.reasoning_present and self.reasoning_chars != 0:
            raise CandidateRecoveryDiagnosticError("shape_presence_invalid", "request")

    def as_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "content_present": self.content_present,
            "content_chars": self.content_chars,
            "reasoning_present": self.reasoning_present,
            "reasoning_chars": self.reasoning_chars,
            "tool_call_count": self.tool_call_count,
            "tool_call_id_present_count": self.tool_call_id_present_count,
            "tool_name_present_count": self.tool_name_present_count,
            "tool_argument_key_count": self.tool_argument_key_count,
            "tool_result_id_present": self.tool_result_id_present,
            "name_present": self.name_present,
        }


def _message_shape(message: ChatMessage) -> MessageShape:
    if not isinstance(message, ChatMessage):
        raise CandidateRecoveryDiagnosticError("request_message_invalid", "request")
    return MessageShape(
        role=message.role.value,
        content_present=message.content is not None,
        content_chars=len(message.content or ""),
        reasoning_present=message.reasoning_content is not None,
        reasoning_chars=len(message.reasoning_content or ""),
        tool_call_count=len(message.tool_calls),
        tool_call_id_present_count=sum(bool(call.id) for call in message.tool_calls),
        tool_name_present_count=sum(bool(call.name) for call in message.tool_calls),
        tool_argument_key_count=sum(len(call.arguments) for call in message.tool_calls),
        tool_result_id_present=message.tool_call_id is not None,
        name_present=message.name is not None,
    )


@dataclass(frozen=True, slots=True)
class RequestShapeSummary:
    """Allow-listed request shape used by each attempt."""

    attempt_ordinal: int
    attempt_kind: CandidateAttemptKind
    message_count: int
    roles: tuple[str, ...]
    messages: tuple[MessageShape, ...]
    tool_count: int
    tool_choice: str
    response_contract_present: bool
    response_contract_name: str | None
    response_contract_version: str | None
    response_contract_shape_sha256: str | None
    output_cap: int
    agent_timeout_s: float
    transport_timeout_s: float
    temperature: float
    top_p: float
    sdk_retries: int
    shape_sha256: str

    @classmethod
    def from_request(
        cls,
        request: ChatRequest,
        *,
        attempt_ordinal: int,
        output_cap: int,
        agent_timeout_s: float,
        transport_timeout_s: float,
        temperature: float = 1.0,
        top_p: float = 0.95,
        sdk_retries: int = 0,
    ) -> "RequestShapeSummary":
        if not isinstance(request, ChatRequest):
            raise CandidateRecoveryDiagnosticError("request_invalid", "request")
        if attempt_ordinal not in {1, 2}:
            raise CandidateRecoveryDiagnosticError("attempt_ordinal_invalid", "request")
        kind = (
            CandidateAttemptKind.PRIMARY
            if attempt_ordinal == 1
            else CandidateAttemptKind.FRESH_RECOVERY
        )
        if isinstance(output_cap, bool) or not isinstance(output_cap, int) or not 1 <= output_cap <= 8192:
            raise CandidateRecoveryDiagnosticError("output_cap_invalid", "budget")
        for name, value in (
            ("agent_timeout_s", agent_timeout_s),
            ("transport_timeout_s", transport_timeout_s),
            ("temperature", temperature),
            ("top_p", top_p),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)):
                raise CandidateRecoveryDiagnosticError("sampling_or_timeout_invalid", "request")
        if float(agent_timeout_s) <= 0 or float(agent_timeout_s) > 90:
            raise CandidateRecoveryDiagnosticError("agent_timeout_invalid", "budget")
        if float(transport_timeout_s) < float(agent_timeout_s) or float(transport_timeout_s) > 120:
            raise CandidateRecoveryDiagnosticError("transport_timeout_invalid", "budget")
        if isinstance(sdk_retries, bool) or not isinstance(sdk_retries, int) or sdk_retries != 0:
            raise CandidateRecoveryDiagnosticError("sdk_retries_invalid", "request")
        metadata = request.metadata
        if not isinstance(metadata, Mapping):
            raise CandidateRecoveryDiagnosticError("request_metadata_invalid", "identity")
        allowed_metadata = {
            "provider_id": CANDIDATE_PROVIDER_ID,
            "model": CANDIDATE_MODEL,
            "runtime_profile_id": CANDIDATE_RUNTIME_PROFILE_ID,
            "runtime_profile_version": CANDIDATE_RUNTIME_PROFILE_VERSION,
            "policy_id": CANDIDATE_POLICY_ID,
            "policy_version": CANDIDATE_POLICY_VERSION,
        }
        for key in metadata:
            if key not in allowed_metadata:
                raise CandidateRecoveryDiagnosticError("request_metadata_unknown", "identity")
            if metadata[key] != allowed_metadata[key]:
                raise CandidateRecoveryDiagnosticError("request_identity_mismatch", "identity")

        message_shapes = tuple(_message_shape(message) for message in request.messages)
        roles = tuple(shape.role for shape in message_shapes)
        contract = request.response_contract
        contract_name = contract.name if contract is not None else None
        contract_version = contract.version if contract is not None else None
        contract_shape = (
            _sha256_canonical(contract.schema_dict()) if contract is not None else None
        )
        tool_choice = request.tool_choice.value
        shape_payload = {
            "message_count": len(message_shapes),
            "roles": roles,
            "messages": [shape.as_dict() for shape in message_shapes],
            "tool_count": len(request.tools),
            "tool_choice": tool_choice,
            "response_contract_present": contract is not None,
            "response_contract_name": contract_name,
            "response_contract_version": contract_version,
            "response_contract_shape_sha256": contract_shape,
        }
        return cls(
            attempt_ordinal=attempt_ordinal,
            attempt_kind=kind,
            message_count=len(message_shapes),
            roles=roles,
            messages=message_shapes,
            tool_count=len(request.tools),
            tool_choice=tool_choice,
            response_contract_present=contract is not None,
            response_contract_name=contract_name,
            response_contract_version=contract_version,
            response_contract_shape_sha256=contract_shape,
            output_cap=output_cap,
            agent_timeout_s=float(agent_timeout_s),
            transport_timeout_s=float(transport_timeout_s),
            temperature=float(temperature),
            top_p=float(top_p),
            sdk_retries=sdk_retries,
            shape_sha256=hashlib.sha256(_canonical_json(shape_payload)).hexdigest(),
        )

    def __post_init__(self) -> None:
        if isinstance(self.attempt_ordinal, bool) or self.attempt_ordinal not in {1, 2}:
            raise CandidateRecoveryDiagnosticError("attempt_ordinal_invalid", "request")
        expected_kind = CandidateAttemptKind.PRIMARY if self.attempt_ordinal == 1 else CandidateAttemptKind.FRESH_RECOVERY
        if self.attempt_kind is not expected_kind:
            raise CandidateRecoveryDiagnosticError("attempt_kind_invalid", "request")
        _require_non_negative_int(self.message_count, "message_count")
        if self.message_count != len(self.messages) or self.message_count != len(self.roles):
            raise CandidateRecoveryDiagnosticError("shape_count_invalid", "request")
        if not all(isinstance(shape, MessageShape) for shape in self.messages):
            raise CandidateRecoveryDiagnosticError("message_shape_invalid", "request")
        if self.roles != tuple(shape.role for shape in self.messages):
            raise CandidateRecoveryDiagnosticError("shape_roles_invalid", "request")
        if (
            isinstance(self.tool_count, bool)
            or not isinstance(self.tool_count, int)
            or self.tool_count < 0
            or self.tool_count > 128
        ):
            raise CandidateRecoveryDiagnosticError("tool_count_invalid", "request")
        _require_safe_code(self.tool_choice, "tool_choice")
        if self.tool_choice not in {choice.value for choice in ToolChoiceMode}:
            raise CandidateRecoveryDiagnosticError("tool_choice_invalid", "request")
        if not isinstance(self.response_contract_present, bool):
            raise CandidateRecoveryDiagnosticError("shape_boolean_invalid", "request")
        if self.response_contract_present is not (
            self.response_contract_name is not None
            and self.response_contract_version is not None
            and self.response_contract_shape_sha256 is not None
        ):
            raise CandidateRecoveryDiagnosticError("contract_presence_mismatch", "request")
        for name in ("response_contract_name", "response_contract_version", "response_contract_shape_sha256"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, str):
                raise CandidateRecoveryDiagnosticError("contract_shape_invalid", "request")
        if self.response_contract_name is not None:
            _require_safe_id(self.response_contract_name, "response_contract_name")
        if self.response_contract_version is not None and not _SEMVER.fullmatch(
            self.response_contract_version
        ):
            raise CandidateRecoveryDiagnosticError("contract_shape_invalid", "request")
        if self.response_contract_shape_sha256 is not None:
            _require_sha256(self.response_contract_shape_sha256, "response_contract_shape_sha256")
        if isinstance(self.output_cap, bool) or not isinstance(self.output_cap, int) or not 1 <= self.output_cap <= 8192:
            raise CandidateRecoveryDiagnosticError("output_cap_invalid", "budget")
        for name, value in (("agent_timeout_s", self.agent_timeout_s), ("transport_timeout_s", self.transport_timeout_s), ("temperature", self.temperature), ("top_p", self.top_p)):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)):
                raise CandidateRecoveryDiagnosticError("request_number_invalid", "request")
        if self.agent_timeout_s <= 0 or self.agent_timeout_s > 90 or self.transport_timeout_s < self.agent_timeout_s or self.transport_timeout_s > 120:
            raise CandidateRecoveryDiagnosticError("request_timeout_invalid", "budget")
        if not 0 <= self.temperature <= 2 or not 0 <= self.top_p <= 1:
            raise CandidateRecoveryDiagnosticError("sampling_invalid", "request")
        if isinstance(self.sdk_retries, bool) or not isinstance(self.sdk_retries, int) or self.sdk_retries != 0:
            raise CandidateRecoveryDiagnosticError("sdk_retries_invalid", "request")
        _require_sha256(self.shape_sha256, "shape_sha256")
        expected_shape = {
            "message_count": self.message_count,
            "roles": self.roles,
            "messages": [shape.as_dict() for shape in self.messages],
            "tool_count": self.tool_count,
            "tool_choice": self.tool_choice,
            "response_contract_present": self.response_contract_present,
            "response_contract_name": self.response_contract_name,
            "response_contract_version": self.response_contract_version,
            "response_contract_shape_sha256": self.response_contract_shape_sha256,
        }
        if self.shape_sha256 != hashlib.sha256(_canonical_json(expected_shape)).hexdigest():
            raise CandidateRecoveryDiagnosticError("shape_hash_mismatch", "request")

    def as_dict(self) -> dict[str, Any]:
        return {
            "attempt_ordinal": self.attempt_ordinal,
            "attempt_kind": self.attempt_kind.value,
            "message_count": self.message_count,
            "roles": list(self.roles),
            "messages": [shape.as_dict() for shape in self.messages],
            "tool_count": self.tool_count,
            "tool_choice": self.tool_choice,
            "response_contract_present": self.response_contract_present,
            "response_contract_name": self.response_contract_name,
            "response_contract_version": self.response_contract_version,
            "response_contract_shape_sha256": self.response_contract_shape_sha256,
            "output_cap": self.output_cap,
            "agent_timeout_s": self.agent_timeout_s,
            "transport_timeout_s": self.transport_timeout_s,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "sdk_retries": self.sdk_retries,
            "shape_sha256": self.shape_sha256,
            "candidate_identity": {
                "provider_id": CANDIDATE_PROVIDER_ID,
                "model": CANDIDATE_MODEL,
                "runtime_profile_id": CANDIDATE_RUNTIME_PROFILE_ID,
                "runtime_profile_version": CANDIDATE_RUNTIME_PROFILE_VERSION,
                "policy_id": CANDIDATE_POLICY_ID,
                "policy_version": CANDIDATE_POLICY_VERSION,
                "activation_state": "candidate",
                "execution_allowed": False,
            },
        }


@dataclass(frozen=True, slots=True)
class DiagnosticLatency:
    """Monotonic elapsed segments for one attempt."""

    open_elapsed_ms: int | None = None
    first_event_ms: int | None = None
    first_visible_content_ms: int | None = None
    terminal_ms: int | None = None
    close_elapsed_ms: int | None = None
    total_elapsed_ms: int | None = None

    def __post_init__(self) -> None:
        values = (
            self.open_elapsed_ms,
            self.first_event_ms,
            self.first_visible_content_ms,
            self.terminal_ms,
            self.close_elapsed_ms,
            self.total_elapsed_ms,
        )
        for value in values:
            if value is not None:
                _require_non_negative_int(value, "latency")
        ordered = [value for value in values if value is not None]
        if any(later < earlier for earlier, later in zip(ordered, ordered[1:])):
            raise CandidateRecoveryDiagnosticError("latency_not_monotonic", "latency")
        if self.total_elapsed_ms is not None and any(
            value is not None and value > self.total_elapsed_ms
            for value in values[:-1]
        ):
            raise CandidateRecoveryDiagnosticError("latency_total_invalid", "latency")

    def as_dict(self) -> dict[str, int | None]:
        return {
            "open_elapsed_ms": self.open_elapsed_ms,
            "first_event_ms": self.first_event_ms,
            "first_visible_content_ms": self.first_visible_content_ms,
            "terminal_ms": self.terminal_ms,
            "close_elapsed_ms": self.close_elapsed_ms,
            "total_elapsed_ms": self.total_elapsed_ms,
        }


def _decimal(value: object, field_name: str) -> Decimal:
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise CandidateRecoveryDiagnosticError("price_invalid", field_name) from None
    if not result.is_finite() or result < 0:
        raise CandidateRecoveryDiagnosticError("price_invalid", field_name)
    return result


@dataclass(frozen=True, slots=True)
class PriceSnapshot:
    """A public, pre-frozen and independently verified price snapshot."""

    snapshot_id_sha256: str
    currency: str
    input_per_million: Decimal
    output_per_million: Decimal
    verified: bool = True
    rounding_places: int = 6

    def __post_init__(self) -> None:
        _require_sha256(self.snapshot_id_sha256, "snapshot_id_sha256")
        if not isinstance(self.currency, str) or not _CURRENCY.fullmatch(self.currency):
            raise CandidateRecoveryDiagnosticError("currency_invalid", "cost")
        object.__setattr__(self, "input_per_million", _decimal(self.input_per_million, "input_per_million"))
        object.__setattr__(self, "output_per_million", _decimal(self.output_per_million, "output_per_million"))
        if not isinstance(self.verified, bool):
            raise CandidateRecoveryDiagnosticError("price_snapshot_verified_invalid", "cost")
        if isinstance(self.rounding_places, bool) or not isinstance(self.rounding_places, int) or not 0 <= self.rounding_places <= 12:
            raise CandidateRecoveryDiagnosticError("rounding_invalid", "cost")

    def as_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id_sha256": self.snapshot_id_sha256,
            "currency": self.currency,
            "input_per_million": str(self.input_per_million),
            "output_per_million": str(self.output_per_million),
            "verified": self.verified,
            "rounding_places": self.rounding_places,
        }


@dataclass(frozen=True, slots=True)
class CostObservation:
    """Unknown/estimated/actual cost with explicit evidence provenance."""

    status: CostState = "unknown"
    currency: str | None = None
    price_snapshot_id_sha256: str | None = None
    amount: Decimal | None = None
    billing_evidence_sha256: str | None = None

    @classmethod
    def unknown(cls) -> "CostObservation":
        return cls()

    @classmethod
    def estimated_from_usage(
        cls,
        usage: TokenUsage,
        snapshot: PriceSnapshot,
    ) -> "CostObservation":
        if not isinstance(usage, TokenUsage):
            raise CandidateRecoveryDiagnosticError("usage_invalid", "cost")
        if not isinstance(snapshot, PriceSnapshot):
            raise CandidateRecoveryDiagnosticError("price_snapshot_invalid", "cost")
        if not snapshot.verified:
            raise CandidateRecoveryDiagnosticError("price_snapshot_unverified", "cost")
        amount = (
            Decimal(usage.input_tokens) * snapshot.input_per_million
            + Decimal(usage.output_tokens) * snapshot.output_per_million
        ) / Decimal(1_000_000)
        quantum = Decimal(1).scaleb(-snapshot.rounding_places)
        amount = amount.quantize(quantum, rounding=ROUND_HALF_UP)
        return cls(
            status="estimated",
            currency=snapshot.currency,
            price_snapshot_id_sha256=snapshot.snapshot_id_sha256,
            amount=amount,
        )

    @classmethod
    def actual_from_billing(
        cls,
        *,
        amount: Decimal,
        currency: str,
        billing_evidence_sha256: str,
    ) -> "CostObservation":
        return cls(
            status="actual",
            amount=amount,
            currency=currency,
            billing_evidence_sha256=billing_evidence_sha256,
        )

    def __post_init__(self) -> None:
        if self.status not in {"unknown", "estimated", "actual"}:
            raise CandidateRecoveryDiagnosticError("cost_state_invalid", "cost")
        if self.status == "unknown":
            if any(value is not None for value in (self.currency, self.price_snapshot_id_sha256, self.amount, self.billing_evidence_sha256)):
                raise CandidateRecoveryDiagnosticError("unknown_cost_has_evidence", "cost")
            return
        if self.currency is None or not isinstance(self.currency, str) or not _CURRENCY.fullmatch(self.currency):
            raise CandidateRecoveryDiagnosticError("currency_invalid", "cost")
        if self.amount is None:
            raise CandidateRecoveryDiagnosticError("cost_amount_missing", "cost")
        object.__setattr__(self, "amount", _decimal(self.amount, "amount"))
        if self.status == "estimated":
            if self.price_snapshot_id_sha256 is None:
                raise CandidateRecoveryDiagnosticError("price_snapshot_missing", "cost")
            _require_sha256(self.price_snapshot_id_sha256, "price_snapshot_id_sha256")
            if self.billing_evidence_sha256 is not None:
                raise CandidateRecoveryDiagnosticError("estimated_cost_billing_mismatch", "cost")
        else:
            if self.billing_evidence_sha256 is None:
                raise CandidateRecoveryDiagnosticError("billing_evidence_missing", "cost")
            _require_sha256(self.billing_evidence_sha256, "billing_evidence_sha256")

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "currency": self.currency,
            "price_snapshot_id_sha256": self.price_snapshot_id_sha256,
            "amount": str(self.amount) if self.amount is not None else None,
            "billing_evidence_sha256": self.billing_evidence_sha256,
        }


@dataclass(frozen=True, slots=True)
class DiagnosticBudgetProjection:
    """Cumulative budget with unknown resources kept unknown."""

    calls_reserved: int
    calls_settled: int
    input_tokens: int | None
    output_tokens: int | None
    elapsed_ms: int | None
    input_state: BudgetState
    output_state: BudgetState
    elapsed_state: BudgetState
    calls_state: BudgetState
    overall_state: BudgetState
    max_attempts: int = 2
    max_additional_calls: int = 1
    max_total_input_tokens: int = 32_000
    max_total_output_tokens: int = 16_384
    max_total_elapsed_ms: int = 180_000

    def __post_init__(self) -> None:
        for name in (
            "calls_reserved",
            "calls_settled",
            "max_attempts",
            "max_additional_calls",
            "max_total_input_tokens",
            "max_total_output_tokens",
            "max_total_elapsed_ms",
        ):
            _require_non_negative_int(getattr(self, name), name)
        if not 1 <= self.max_attempts <= 2:
            raise CandidateRecoveryDiagnosticError("budget_limit_invalid", "budget")
        if not 0 <= self.max_additional_calls <= 1:
            raise CandidateRecoveryDiagnosticError("budget_limit_invalid", "budget")
        if self.max_additional_calls > self.max_attempts - 1:
            raise CandidateRecoveryDiagnosticError("budget_limit_invalid", "budget")
        if (
            self.max_total_input_tokens < 1
            or self.max_total_output_tokens < 1
            or self.max_total_elapsed_ms < 1
        ):
            raise CandidateRecoveryDiagnosticError("budget_limit_invalid", "budget")
        if self.calls_settled > self.calls_reserved or self.calls_reserved > self.max_attempts:
            raise CandidateRecoveryDiagnosticError("budget_count_invalid", "budget")
        if max(0, self.calls_reserved - 1) > self.max_additional_calls:
            raise CandidateRecoveryDiagnosticError("budget_count_invalid", "budget")
        for name in ("input_tokens", "output_tokens", "elapsed_ms"):
            value = getattr(self, name)
            if value is not None:
                _require_non_negative_int(value, name)
        for name in ("input_state", "output_state", "elapsed_state", "calls_state", "overall_state"):
            if getattr(self, name) not in {"within", "exceeded", "unknown"}:
                raise CandidateRecoveryDiagnosticError("budget_state_invalid", "budget")

        def expected_state(value: int | None, limit: int) -> BudgetState:
            if value is None:
                return "unknown"
            return "exceeded" if value > limit else "within"

        if self.input_state != expected_state(self.input_tokens, self.max_total_input_tokens):
            raise CandidateRecoveryDiagnosticError("budget_state_mismatch", "budget")
        if self.output_state != expected_state(self.output_tokens, self.max_total_output_tokens):
            raise CandidateRecoveryDiagnosticError("budget_state_mismatch", "budget")
        if self.elapsed_state != expected_state(self.elapsed_ms, self.max_total_elapsed_ms):
            raise CandidateRecoveryDiagnosticError("budget_state_mismatch", "budget")
        expected_calls = (
            "exceeded"
            if (
                self.calls_reserved > self.max_attempts
                or max(0, self.calls_reserved - 1) > self.max_additional_calls
            )
            else "within"
        )
        if self.calls_state != expected_calls:
            raise CandidateRecoveryDiagnosticError("budget_state_mismatch", "budget")
        states = (self.input_state, self.output_state, self.elapsed_state, self.calls_state)
        expected_overall: BudgetState = (
            "exceeded"
            if "exceeded" in states
            else ("unknown" if "unknown" in states else "within")
        )
        if self.overall_state != expected_overall:
            raise CandidateRecoveryDiagnosticError("budget_state_mismatch", "budget")

    @property
    def budget_state(self) -> BudgetState:
        return self.overall_state

    def as_dict(self) -> dict[str, Any]:
        return {
            "calls_reserved": self.calls_reserved,
            "calls_settled": self.calls_settled,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "elapsed_ms": self.elapsed_ms,
            "input_state": self.input_state,
            "output_state": self.output_state,
            "elapsed_state": self.elapsed_state,
            "calls_state": self.calls_state,
            "overall_state": self.overall_state,
            "limits": {
                "max_attempts": self.max_attempts,
                "max_additional_calls": self.max_additional_calls,
                "max_total_input_tokens": self.max_total_input_tokens,
                "max_total_output_tokens": self.max_total_output_tokens,
                "max_total_elapsed_ms": self.max_total_elapsed_ms,
            },
        }


def _snapshot_from_observation(observation: Any) -> ResponseBoundarySnapshot:
    """Project a boundary observation without copying response-bearing data."""

    if observation.complete_boundary:
        return observation.to_response_boundary_snapshot()
    return ResponseBoundarySnapshot(
        finish_reason=observation.finish_reason,
        content_state=observation.content_state,
        reasoning_content_state=observation.reasoning_content_state,
        tool_call_count=observation.tool_call_count,
        usage_state=observation.usage_state,
    )


def _decision_for_observation(
    observation: Any,
    *,
    policy: ResponseCompletionPolicy,
    context: ResponseRequestContext,
) -> ResponseCompletionDecision:
    """Recompute policy state and never trust a caller eligibility bit."""

    snapshot = _snapshot_from_observation(observation)
    decision = policy.decide(snapshot, context)
    # A transport/protocol/close error wins over a coincidentally complete
    # prefix.  Preserve the observation's safe error while making the policy
    # decision fail closed.
    if (
        observation.error_code is not None
        and decision.disposition
        in {
            ResponseDisposition.COMPLETE_TEXT,
            ResponseDisposition.TOOL_CALLS_READY,
            ResponseDisposition.CANDIDATE_ELIGIBLE,
        }
    ):
        decision = policy.decide(replace(snapshot, usage_state="invalid"), context)
    return decision


def _failure_class_for(
    *,
    error_code: str | None,
    error_stage: str | None,
    decision: ResponseCompletionDecision,
    consumer_error: str | None = None,
    control: bool = False,
) -> DiagnosticFailureClass | None:
    if control:
        return DiagnosticFailureClass.CONTROL
    if consumer_error is not None:
        return DiagnosticFailureClass.CONSUMER
    # ``incomplete_chat_response`` is the policy's explanatory code for the
    # exact candidate shape, not a failure.  The activation decision is
    # recorded separately at the run level.
    if (
        decision.disposition is ResponseDisposition.CANDIDATE_ELIGIBLE
        and error_code == "incomplete_chat_response"
        and consumer_error is None
        and not control
    ):
        return None
    if error_code is not None:
        if error_stage in {"open", "read", "close", "transport"} or error_code.startswith(
            ("transport_", "stream_")
        ):
            return DiagnosticFailureClass.TRANSPORT
        if error_stage in {"identity", "request"} or error_code.endswith("_mismatch") or "identity" in error_code:
            return DiagnosticFailureClass.IDENTITY
        if error_stage in {"usage"} or "usage" in error_code:
            return DiagnosticFailureClass.USAGE
        if error_stage in {"budget"} or "budget" in error_code or "limit" in error_code:
            return DiagnosticFailureClass.BUDGET
        if error_stage in {"terminal", "translate", "assemble", "shape", "tool", "protocol"}:
            return DiagnosticFailureClass.PROTOCOL
        return DiagnosticFailureClass.COMPLETION
    if decision.disposition is ResponseDisposition.FAIL_CLOSED:
        if decision.error_code and "usage" in decision.error_code:
            return DiagnosticFailureClass.USAGE
        return DiagnosticFailureClass.COMPLETION
    return None


def _attempt_budget_state(
    *,
    input_tokens: int | None,
    output_tokens: int | None,
    elapsed_ms: int | None,
    output_cap: int,
    agent_timeout_s: float,
) -> BudgetState:
    known_exceeded = (
        output_tokens is not None and output_tokens > output_cap
    ) or (
        elapsed_ms is not None and elapsed_ms > round(agent_timeout_s * 1000)
    )
    if known_exceeded:
        return "exceeded"
    if input_tokens is None or output_tokens is None or elapsed_ms is None:
        return "unknown"
    return "within"


@dataclass(frozen=True, slots=True)
class CandidateRecoveryAttemptDiagnostic:
    """One settled, body-free attempt row in a v2 diagnostic receipt."""

    ordinal: int
    attempt_kind: CandidateAttemptKind
    request: RequestShapeSummary
    observation: CandidateStreamTrace
    latency: DiagnosticLatency
    cost: CostObservation
    disposition: ResponseDisposition
    reason_code: str
    error_code: str | None
    error_stage: str | None
    failure_class: DiagnosticFailureClass | None
    assembled_complete: bool
    settled: bool
    input_tokens: int | None
    output_tokens: int | None
    cached_input_tokens: int | None
    usage_state: Literal["valid", "missing", "invalid"]
    budget_state: BudgetState
    consumer_error_code: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.ordinal, bool) or self.ordinal not in {1, 2}:
            raise CandidateRecoveryDiagnosticError("attempt_ordinal_invalid", "attempt")
        expected = CandidateAttemptKind.PRIMARY if self.ordinal == 1 else CandidateAttemptKind.FRESH_RECOVERY
        if self.attempt_kind is not expected:
            raise CandidateRecoveryDiagnosticError("attempt_kind_invalid", "attempt")
        if not isinstance(self.request, RequestShapeSummary):
            raise TypeError("request must be RequestShapeSummary")
        if self.request.attempt_ordinal != self.ordinal or self.request.attempt_kind is not self.attempt_kind:
            raise CandidateRecoveryDiagnosticError("attempt_identity_mismatch", "attempt")
        if not isinstance(self.observation, CandidateStreamTrace):
            raise TypeError("observation must be CandidateStreamTrace")
        if self.observation.observation.binding != CandidateRuntimeBinding.for_attempt(self.ordinal):
            raise CandidateRecoveryDiagnosticError("attempt_identity_mismatch", "attempt")
        if not isinstance(self.latency, DiagnosticLatency) or not isinstance(self.cost, CostObservation):
            raise TypeError("latency and cost must use diagnostic value objects")
        if not isinstance(self.disposition, ResponseDisposition):
            try:
                object.__setattr__(self, "disposition", ResponseDisposition(self.disposition))
            except (TypeError, ValueError):
                raise CandidateRecoveryDiagnosticError("disposition_invalid", "decision") from None
        _require_safe_code(self.reason_code, "reason_code")
        for name in ("error_code", "error_stage", "consumer_error_code"):
            value = getattr(self, name)
            if value is not None:
                _require_safe_code(value, name)
        if self.error_code is None and self.error_stage is not None:
            raise CandidateRecoveryDiagnosticError("error_stage_without_code", "error")
        if self.failure_class is not None and not isinstance(
            self.failure_class, DiagnosticFailureClass
        ):
            try:
                object.__setattr__(
                    self,
                    "failure_class",
                    DiagnosticFailureClass(self.failure_class),
                )
            except (TypeError, ValueError):
                raise CandidateRecoveryDiagnosticError("failure_class_invalid", "failure") from None
        if not isinstance(self.assembled_complete, bool) or self.assembled_complete != (
            self.disposition in {ResponseDisposition.COMPLETE_TEXT, ResponseDisposition.TOOL_CALLS_READY}
        ):
            raise CandidateRecoveryDiagnosticError("assembly_state_mismatch", "assembly")
        if self.settled is not True:
            raise CandidateRecoveryDiagnosticError("attempt_not_settled", "ledger")
        if self.usage_state not in {"valid", "missing", "invalid"}:
            raise CandidateRecoveryDiagnosticError("usage_state_invalid", "usage")
        for name in ("input_tokens", "output_tokens", "cached_input_tokens"):
            value = getattr(self, name)
            if value is not None:
                _require_non_negative_int(value, name)
        if self.usage_state == "valid":
            if self.input_tokens is None or self.output_tokens is None or self.cached_input_tokens is None:
                raise CandidateRecoveryDiagnosticError("usage_projection_invalid", "usage")
            if self.cached_input_tokens > self.input_tokens:
                raise CandidateRecoveryDiagnosticError("usage_projection_invalid", "usage")
        elif any(value is not None for value in (self.input_tokens, self.output_tokens, self.cached_input_tokens)):
            raise CandidateRecoveryDiagnosticError("unknown_usage_has_tokens", "usage")
        if self.usage_state != self.observation.observation.usage_state:
            raise CandidateRecoveryDiagnosticError("usage_projection_mismatch", "usage")
        if not isinstance(self.budget_state, str) or self.budget_state not in {"within", "exceeded", "unknown"}:
            raise CandidateRecoveryDiagnosticError("budget_state_invalid", "budget")
        inferred_identity_error = self.error_code in {"request_identity_unobserved", "model_unobserved"}
        if (
            self.error_code != self.observation.observation.error_code
            and self.observation.observation.error_code is not None
            and not inferred_identity_error
        ):
            raise CandidateRecoveryDiagnosticError("error_projection_mismatch", "error")
        candidate_policy_code = (
            self.disposition is ResponseDisposition.CANDIDATE_ELIGIBLE
            and self.error_code == "incomplete_chat_response"
        )
        if self.disposition is ResponseDisposition.FAIL_CLOSED:
            if self.observation.observation.observation_state != "fail_closed":
                raise CandidateRecoveryDiagnosticError("failed_state_mismatch", "decision")
            if self.error_code is None and self.consumer_error_code is None:
                raise CandidateRecoveryDiagnosticError("failure_code_missing", "failure")
        elif (
            self.error_code is not None
            and not candidate_policy_code
            and self.failure_class is not DiagnosticFailureClass.CONTROL
        ):
            raise CandidateRecoveryDiagnosticError("success_error_mismatch", "decision")
        if self.consumer_error_code is not None and self.failure_class is not DiagnosticFailureClass.CONSUMER:
            raise CandidateRecoveryDiagnosticError("consumer_failure_mismatch", "failure")
        if self.failure_class is DiagnosticFailureClass.CONTROL and self.error_code != "stream_aborted":
            raise CandidateRecoveryDiagnosticError("control_failure_mismatch", "failure")
        try:
            projected_decision = ResponseCompletionDecision(
                disposition=self.disposition,
                reason_code=self.reason_code,
                error_code=self.error_code,
                candidate_eligible=(
                    self.disposition is ResponseDisposition.CANDIDATE_ELIGIBLE
                ),
                continuation_allowed=False,
                max_additional_calls=0,
            )
        except (TypeError, ValueError):
            raise CandidateRecoveryDiagnosticError("decision_invalid", "decision") from None
        expected_failure = _failure_class_for(
            error_code=self.error_code,
            error_stage=self.error_stage,
            decision=projected_decision,
            consumer_error=self.consumer_error_code,
            control=(
                self.failure_class is DiagnosticFailureClass.CONTROL
                or (
                    self.error_code == "stream_aborted"
                    and self.error_stage == "control"
                )
            ),
        )
        if self.failure_class is not expected_failure:
            raise CandidateRecoveryDiagnosticError("failure_class_mismatch", "failure")
        if self.failure_class is None and (
            (self.error_code is not None and not candidate_policy_code)
            or self.consumer_error_code is not None
        ):
            raise CandidateRecoveryDiagnosticError("failure_class_missing", "failure")
        expected_budget_state = _attempt_budget_state(
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            elapsed_ms=self.latency.total_elapsed_ms,
            output_cap=self.request.output_cap,
            agent_timeout_s=self.request.agent_timeout_s,
        )
        if self.budget_state != expected_budget_state:
            raise CandidateRecoveryDiagnosticError("attempt_budget_mismatch", "budget")
        if self.disposition is ResponseDisposition.CANDIDATE_ELIGIBLE:
            if self.observation.observation.observation_state not in {"candidate_shape", "awaiting_recovery"}:
                raise CandidateRecoveryDiagnosticError("candidate_shape_mismatch", "decision")
            if self.assembled_complete or self.error_code != "incomplete_chat_response":
                raise CandidateRecoveryDiagnosticError("candidate_decision_mismatch", "decision")
        if self.disposition is ResponseDisposition.COMPLETE_TEXT and self.observation.observation.observation_state != "complete_text":
            raise CandidateRecoveryDiagnosticError("complete_decision_mismatch", "decision")
        if self.disposition is ResponseDisposition.TOOL_CALLS_READY and self.observation.observation.observation_state != "tool_calls_ready":
            raise CandidateRecoveryDiagnosticError("tool_decision_mismatch", "decision")

    @classmethod
    def from_execution(
        cls,
        *,
        ordinal: int,
        request: RequestShapeSummary,
        observation: Any,
        latency: DiagnosticLatency,
        policy: ResponseCompletionPolicy,
        context: ResponseRequestContext,
        cost: CostObservation,
        assembled_complete: bool,
        consumer_error_code: str | None = None,
        pending_control: bool = False,
    ) -> "CandidateRecoveryAttemptDiagnostic":
        decision = _decision_for_observation(observation, policy=policy, context=context)
        error_code = observation.error_code or decision.error_code
        error_stage = observation.error_stage
        # The shared observer reports the first terminal/resource failure it
        # encounters.  If request identity was never observed, identity is a
        # more specific and safer diagnosis than a generic Usage-unavailable
        # policy result.
        if (
            observation.opened
            and observation.terminal_observed
            and observation.request_id_sha256 is None
            and observation.error_code in {None, "usage_unavailable"}
        ):
            error_code = "request_identity_unobserved"
            error_stage = "identity"
        elif (
            observation.opened
            and observation.terminal_observed
            and observation.resolved_model is None
            and observation.error_code in {None, "usage_unavailable"}
        ):
            error_code = "model_unobserved"
            error_stage = "identity"
        if error_stage is None and error_code is not None:
            error_stage = "decision"
        usage_state = observation.usage_state
        input_tokens = observation.input_tokens if usage_state == "valid" else None
        output_tokens = observation.output_tokens if usage_state == "valid" else None
        cached = observation.cached_input_tokens if usage_state == "valid" else None
        failure = _failure_class_for(
            error_code=error_code,
            error_stage=error_stage,
            decision=decision,
            consumer_error=consumer_error_code,
            control=pending_control,
        )
        if pending_control:
            error_code = "stream_aborted"
            error_stage = "control"
        return cls(
            ordinal=ordinal,
            attempt_kind=CandidateAttemptKind.PRIMARY if ordinal == 1 else CandidateAttemptKind.FRESH_RECOVERY,
            request=request,
            observation=CandidateStreamTrace(observation=observation),
            latency=latency,
            cost=cost,
            disposition=decision.disposition,
            reason_code=decision.reason_code,
            error_code=error_code,
            error_stage=error_stage,
            failure_class=failure,
            assembled_complete=assembled_complete,
            settled=True,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=cached,
            usage_state=usage_state,
            budget_state=_attempt_budget_state(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                elapsed_ms=latency.total_elapsed_ms,
                output_cap=request.output_cap,
                agent_timeout_s=request.agent_timeout_s,
            ),
            consumer_error_code=consumer_error_code,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "ordinal": self.ordinal,
            "attempt_kind": self.attempt_kind.value,
            "request": self.request.as_dict(),
            "observation": self.observation.as_dict(),
            "latency": self.latency.as_dict(),
            "cost": self.cost.as_dict(),
            "disposition": self.disposition.value,
            "reason_code": self.reason_code,
            "error_code": self.error_code,
            "error_stage": self.error_stage,
            "failure_class": self.failure_class.value if self.failure_class else None,
            "assembled_complete": self.assembled_complete,
            "settled": self.settled,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cached_input_tokens": self.cached_input_tokens,
            "usage_state": self.usage_state,
            "budget_state": self.budget_state,
            "consumer_error_code": self.consumer_error_code,
        }


@dataclass(frozen=True, slots=True)
class CandidateRecoveryDiagnosticReservation:
    """Opaque reservation proving a slot was counted before I/O."""

    reservation_id: int
    ordinal: int
    attempt_kind: CandidateAttemptKind
    request: RequestShapeSummary

    def __post_init__(self) -> None:
        _require_non_negative_int(self.reservation_id, "reservation_id")
        if self.reservation_id < 1 or self.ordinal not in {1, 2}:
            raise CandidateRecoveryDiagnosticError("reservation_invalid", "ledger")
        expected = CandidateAttemptKind.PRIMARY if self.ordinal == 1 else CandidateAttemptKind.FRESH_RECOVERY
        if self.attempt_kind is not expected or self.request.attempt_ordinal != self.ordinal:
            raise CandidateRecoveryDiagnosticError("reservation_identity_invalid", "ledger")


class CandidateRecoveryDiagnosticLedger:
    """Small candidate-only staged ledger used by the diagnostic runner."""

    def __init__(self, run: CandidateRecoveryRunSpec) -> None:
        if not isinstance(run, CandidateRecoveryRunSpec):
            raise TypeError("run must be CandidateRecoveryRunSpec")
        self._run = run
        self._reserved: list[CandidateRecoveryDiagnosticReservation] = []
        self._settled: list[CandidateRecoveryAttemptDiagnostic] = []
        self._open: CandidateRecoveryDiagnosticReservation | None = None

    @property
    def calls_reserved(self) -> int:
        return len(self._reserved)

    @property
    def calls_settled(self) -> int:
        return len(self._settled)

    @property
    def attempts(self) -> tuple[CandidateRecoveryAttemptDiagnostic, ...]:
        return tuple(self._settled)

    def reserve(
        self,
        request: RequestShapeSummary,
        *,
        permit: CandidateRecoveryExecutionPermit | None = None,
        now_ms: int | None = None,
    ) -> CandidateRecoveryDiagnosticReservation:
        if self._open is not None:
            raise CandidateRecoveryDiagnosticError("reservation_in_flight", "ledger")
        ordinal = len(self._reserved) + 1
        if ordinal > 2:
            raise CandidateRecoveryDiagnosticError("third_attempt_forbidden", "budget")
        expected_kind = CandidateAttemptKind.PRIMARY if ordinal == 1 else CandidateAttemptKind.FRESH_RECOVERY
        if request.attempt_ordinal != ordinal or request.attempt_kind is not expected_kind:
            raise CandidateRecoveryDiagnosticError("reservation_identity_invalid", "ledger")
        if ordinal == 2:
            if not self._settled or self._settled[0].disposition is not ResponseDisposition.CANDIDATE_ELIGIBLE:
                raise CandidateRecoveryDiagnosticError("recovery_not_eligible", "activation")
            if self._run.activation is DiagnosticActivationGate.DISABLED:
                raise CandidateRecoveryDiagnosticError("activation_disabled", "activation")
            if permit is None or now_ms is None:
                raise CandidateRecoveryDiagnosticError("permit_missing", "activation")
            status = permit.verify(FRESH_RECOVERY_CANDIDATE_BINDING, now_ms=now_ms)
            if status != "valid":
                raise CandidateRecoveryDiagnosticError(f"permit_{status}", "activation")
        reservation = CandidateRecoveryDiagnosticReservation(
            reservation_id=len(self._reserved) + 1,
            ordinal=ordinal,
            attempt_kind=expected_kind,
            request=request,
        )
        self._reserved.append(reservation)
        self._open = reservation
        return reservation

    def settle(
        self,
        reservation: CandidateRecoveryDiagnosticReservation,
        attempt: CandidateRecoveryAttemptDiagnostic,
    ) -> None:
        if self._open is None or reservation is not self._open:
            raise CandidateRecoveryDiagnosticError("duplicate_settlement", "ledger")
        if attempt.ordinal != reservation.ordinal or attempt.request != reservation.request:
            raise CandidateRecoveryDiagnosticError("settlement_identity_mismatch", "ledger")
        if attempt.settled is not True:
            raise CandidateRecoveryDiagnosticError("attempt_not_settled", "ledger")
        self._settled.append(attempt)
        self._open = None


def _aggregate_budget(
    attempts: tuple[CandidateRecoveryAttemptDiagnostic, ...],
    *,
    calls_reserved: int,
    calls_settled: int,
    profile: ResponseRecoveryRuntimeProfile,
) -> DiagnosticBudgetProjection:
    input_values = [attempt.input_tokens for attempt in attempts]
    output_values = [attempt.output_tokens for attempt in attempts]
    elapsed_values = [attempt.latency.total_elapsed_ms for attempt in attempts]
    input_tokens = (
        sum(input_values)
        if attempts and all(value is not None for value in input_values)
        else None
    )
    output_tokens = (
        sum(output_values)
        if attempts and all(value is not None for value in output_values)
        else None
    )
    elapsed_ms = (
        sum(elapsed_values)
        if attempts and all(value is not None for value in elapsed_values)
        else None
    )

    def state(value: int | None, limit: int) -> BudgetState:
        if value is not None and value > limit:
            return "exceeded"
        return "within" if value is not None else "unknown"

    input_state = state(input_tokens, profile.max_total_input_tokens)
    output_state = state(output_tokens, profile.max_total_output_tokens)
    elapsed_state = state(elapsed_ms, profile.max_total_elapsed_ms)
    calls_state: BudgetState = (
        "exceeded"
        if (
            calls_reserved > profile.max_attempts
            or max(0, calls_reserved - 1) > profile.max_additional_calls
        )
        else "within"
    )
    states = (input_state, output_state, elapsed_state, calls_state)
    overall: BudgetState = "exceeded" if "exceeded" in states else ("unknown" if "unknown" in states else "within")
    return DiagnosticBudgetProjection(
        calls_reserved=calls_reserved,
        calls_settled=calls_settled,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        elapsed_ms=elapsed_ms,
        input_state=input_state,
        output_state=output_state,
        elapsed_state=elapsed_state,
        calls_state=calls_state,
        overall_state=overall,
        max_attempts=profile.max_attempts,
        max_additional_calls=profile.max_additional_calls,
        max_total_input_tokens=profile.max_total_input_tokens,
        max_total_output_tokens=profile.max_total_output_tokens,
        max_total_elapsed_ms=profile.max_total_elapsed_ms,
    )


def _aggregate_cost(attempts: tuple[CandidateRecoveryAttemptDiagnostic, ...]) -> CostObservation:
    if not attempts or any(attempt.cost.status == "unknown" for attempt in attempts):
        return CostObservation.unknown()
    statuses = {attempt.cost.status for attempt in attempts}
    if len(statuses) != 1:
        return CostObservation.unknown()
    status = next(iter(statuses))
    if status == "estimated":
        currencies = {attempt.cost.currency for attempt in attempts}
        snapshots = {attempt.cost.price_snapshot_id_sha256 for attempt in attempts}
        if len(currencies) != 1 or len(snapshots) != 1:
            return CostObservation.unknown()
        return CostObservation(
            status="estimated",
            currency=next(iter(currencies)),
            price_snapshot_id_sha256=next(iter(snapshots)),
            amount=sum((attempt.cost.amount or Decimal(0) for attempt in attempts), Decimal(0)),
        )
    # Actual billing evidence cannot be merged into a single claim without a
    # separate invoice contract.  Keep the aggregate unknown instead.
    return CostObservation.unknown()


def _derive_run_state(attempts: tuple[CandidateRecoveryAttemptDiagnostic, ...]) -> RunState:
    if not attempts:
        return "interrupted"
    last = attempts[-1]
    if last.failure_class is DiagnosticFailureClass.CONTROL:
        return "interrupted"
    if last.disposition is ResponseDisposition.CANDIDATE_ELIGIBLE:
        return "candidate_eligible"
    if last.disposition is ResponseDisposition.COMPLETE_TEXT:
        return "recovery_complete" if len(attempts) > 1 else "complete_text"
    if last.disposition is ResponseDisposition.TOOL_CALLS_READY:
        return "recovery_complete" if len(attempts) > 1 else "tool_calls_ready"
    return "fail_closed"


def _derive_first_failure(
    attempts: tuple[CandidateRecoveryAttemptDiagnostic, ...],
) -> dict[str, Any] | None:
    for attempt in attempts:
        if attempt.failure_class is not None:
            code = attempt.consumer_error_code or attempt.error_code
            if code is None:
                continue
            return {
                "attempt_ordinal": attempt.ordinal,
                "failure_class": attempt.failure_class.value,
                "code": code,
                "stage": attempt.error_stage or "decision",
            }
    return None


@dataclass(frozen=True, slots=True)
class CandidateRecoveryDiagnosticReceipt:
    """Immutable top-level, body-free v2 evidence envelope."""

    identity: CandidateRecoveryDiagnosticIdentity
    attempts: tuple[CandidateRecoveryAttemptDiagnostic, ...]
    budget: DiagnosticBudgetProjection
    cost: CostObservation
    run_state: RunState
    first_failure: Mapping[str, Any] | None
    terminal_reason: str
    recovery_skip_reason: str | None
    activation_state: Literal["candidate"] = "candidate"
    activation_gate: Literal["disabled"] = "disabled"
    execution_allowed: bool = False

    @property
    def calls_reserved(self) -> int:
        return self.budget.calls_reserved

    @property
    def calls_settled(self) -> int:
        return self.budget.calls_settled

    @property
    def budget_state(self) -> BudgetState:
        return self.budget.overall_state

    @classmethod
    def from_attempts(
        cls,
        identity: CandidateRecoveryDiagnosticIdentity,
        attempts: Iterable[CandidateRecoveryAttemptDiagnostic],
        *,
        calls_reserved: int | None = None,
        recovery_skip_reason: str | None = None,
    ) -> "CandidateRecoveryDiagnosticReceipt":
        rows = tuple(attempts)
        if not isinstance(identity, CandidateRecoveryDiagnosticIdentity):
            raise TypeError("identity must be CandidateRecoveryDiagnosticIdentity")
        profile = GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1
        reserved = calls_reserved if calls_reserved is not None else len(rows)
        budget = _aggregate_budget(rows, calls_reserved=reserved, calls_settled=len(rows), profile=profile)
        state = _derive_run_state(rows)
        first = _derive_first_failure(rows)
        terminal = "no_attempt"
        if rows:
            last = rows[-1]
            terminal = last.error_code or last.consumer_error_code or last.reason_code
        if rows and rows[-1].disposition is ResponseDisposition.CANDIDATE_ELIGIBLE and recovery_skip_reason is None:
            recovery_skip_reason = "activation_disabled"
        return cls(
            identity=identity,
            attempts=rows,
            budget=budget,
            cost=_aggregate_cost(rows),
            run_state=state,
            first_failure=first,
            terminal_reason=terminal,
            recovery_skip_reason=recovery_skip_reason,
        )

    def __post_init__(self) -> None:
        if not isinstance(self.identity, CandidateRecoveryDiagnosticIdentity):
            raise TypeError("identity must be CandidateRecoveryDiagnosticIdentity")
        if self.activation_state != "candidate" or self.activation_gate != "disabled" or self.execution_allowed is not False:
            raise CandidateRecoveryDiagnosticError("activation_state_invalid", "activation")
        if not isinstance(self.attempts, tuple) or not all(isinstance(row, CandidateRecoveryAttemptDiagnostic) for row in self.attempts):
            raise TypeError("attempts must contain CandidateRecoveryAttemptDiagnostic values")
        if len(self.attempts) > 2 or tuple(row.ordinal for row in self.attempts) != tuple(range(1, len(self.attempts) + 1)):
            raise CandidateRecoveryDiagnosticError("attempt_sequence_invalid", "ledger")
        for row in self.attempts:
            binding = row.observation.observation.binding
            if (
                binding.provider_id,
                binding.model,
                binding.runtime_profile_id,
                binding.runtime_profile_version,
                binding.policy_id,
                binding.policy_version,
            ) != (
                self.identity.provider_id,
                self.identity.model,
                self.identity.runtime_profile_id,
                self.identity.runtime_profile_version,
                self.identity.policy_id,
                self.identity.policy_version,
            ):
                raise CandidateRecoveryDiagnosticError("receipt_identity_mismatch", "identity")
        if not isinstance(self.budget, DiagnosticBudgetProjection) or not isinstance(self.cost, CostObservation):
            raise TypeError("budget and cost must use diagnostic value objects")
        expected_budget = _aggregate_budget(
            self.attempts,
            calls_reserved=self.budget.calls_reserved,
            calls_settled=len(self.attempts),
            profile=GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1,
        )
        if self.budget != expected_budget:
            raise CandidateRecoveryDiagnosticError("receipt_budget_mismatch", "budget")
        if self.cost != _aggregate_cost(self.attempts):
            raise CandidateRecoveryDiagnosticError("receipt_cost_mismatch", "cost")
        expected_state = _derive_run_state(self.attempts)
        if self.run_state != expected_state:
            raise CandidateRecoveryDiagnosticError("receipt_state_mismatch", "state")
        expected_first = _derive_first_failure(self.attempts)
        if self.first_failure != expected_first:
            raise CandidateRecoveryDiagnosticError("receipt_first_failure_mismatch", "failure")
        expected_terminal = "no_attempt" if not self.attempts else (
            self.attempts[-1].error_code or self.attempts[-1].consumer_error_code or self.attempts[-1].reason_code
        )
        if self.terminal_reason != expected_terminal:
            raise CandidateRecoveryDiagnosticError("receipt_terminal_mismatch", "state")
        if self.run_state not in {
            "complete_text",
            "tool_calls_ready",
            "candidate_eligible",
            "recovery_complete",
            "fail_closed",
            "interrupted",
        }:
            raise CandidateRecoveryDiagnosticError("run_state_invalid", "state")
        _require_safe_code(self.terminal_reason, "terminal_reason")
        if self.recovery_skip_reason is not None:
            _require_safe_code(self.recovery_skip_reason, "recovery_skip_reason")
        if self.run_state == "candidate_eligible" and self.recovery_skip_reason is None:
            raise CandidateRecoveryDiagnosticError("recovery_skip_reason_missing", "activation")
        if self.first_failure is not None and not isinstance(self.first_failure, Mapping):
            raise CandidateRecoveryDiagnosticError("first_failure_invalid", "failure")
        if self.first_failure is not None:
            expected_keys = {"attempt_ordinal", "failure_class", "code", "stage"}
            if set(self.first_failure) != expected_keys:
                raise CandidateRecoveryDiagnosticError("first_failure_invalid", "failure")
            if (
                isinstance(self.first_failure["attempt_ordinal"], bool)
                or not isinstance(self.first_failure["attempt_ordinal"], int)
                or self.first_failure["attempt_ordinal"] not in {1, 2}
            ):
                raise CandidateRecoveryDiagnosticError("first_failure_invalid", "failure")
            try:
                DiagnosticFailureClass(self.first_failure["failure_class"])
            except (TypeError, ValueError):
                raise CandidateRecoveryDiagnosticError("first_failure_invalid", "failure") from None
            _require_safe_code(self.first_failure["code"], "first_failure")
            _require_safe_code(self.first_failure["stage"], "first_failure")

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "schema_version": self.identity.schema_version,
            "protocol_id": self.identity.protocol_id,
            "provider_id": self.identity.provider_id,
            "model": self.identity.model,
            "runtime_profile_id": self.identity.runtime_profile_id,
            "runtime_profile_version": self.identity.runtime_profile_version,
            "policy_id": self.identity.policy_id,
            "policy_version": self.identity.policy_version,
            "implementation_sha": self.identity.implementation_sha,
            "diagnostic_code_sha": self.identity.diagnostic_code_sha,
            "input_plan_sha": self.identity.input_plan_sha,
            "context_shape_sha": self.identity.context_shape_sha,
            "run_nonce_sha256": self.identity.run_nonce_sha256,
            "activation_state": self.activation_state,
            "activation_gate": self.activation_gate,
            "execution_allowed": self.execution_allowed,
            "run_state": self.run_state,
            "attempts": [row.as_dict() for row in self.attempts],
            "budget": self.budget.as_dict(),
            "cost": self.cost.as_dict(),
            "first_failure": dict(self.first_failure) if self.first_failure is not None else None,
            "terminal_reason": self.terminal_reason,
            "recovery_skip_reason": self.recovery_skip_reason,
        }
        _assert_body_free(payload)
        if set(payload) != _RECEIPT_KEYS:
            raise CandidateRecoveryDiagnosticError("receipt_field_not_allowlisted", "serialize")
        return payload

    to_dict = as_dict

    def canonical_bytes(self) -> bytes:
        return _canonical_json(self.as_dict())

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CandidateRecoveryDiagnosticReceipt":
        """Parse one canonical body-free receipt through the trusted value objects."""

        return _parse_receipt_payload(payload)


def _parse_receipt_payload(
    payload: Mapping[str, Any],
) -> CandidateRecoveryDiagnosticReceipt:
    """Strictly parse a body-free receipt without accepting caller qualifications."""

    try:
        root = _mapping(payload, "serialize")
        _assert_body_free(root)
        _exact_keys(root, _RECEIPT_KEYS, "serialize")
        identity = CandidateRecoveryDiagnosticIdentity(
            protocol_id=root["protocol_id"],
            schema_version=root["schema_version"],
            provider_id=root["provider_id"],
            model=root["model"],
            runtime_profile_id=root["runtime_profile_id"],
            runtime_profile_version=root["runtime_profile_version"],
            policy_id=root["policy_id"],
            policy_version=root["policy_version"],
            implementation_sha=root["implementation_sha"],
            diagnostic_code_sha=root["diagnostic_code_sha"],
            input_plan_sha=root["input_plan_sha"],
            context_shape_sha=root["context_shape_sha"],
            run_nonce_sha256=root["run_nonce_sha256"],
        )
        raw_attempts = root["attempts"]
        if not isinstance(raw_attempts, (list, tuple)):
            raise CandidateRecoveryDiagnosticError("receipt_shape_invalid", "attempts")
        attempts = tuple(
            _parse_attempt_payload(item, identity=identity)
            for item in raw_attempts
        )
        budget = _parse_budget_payload(root["budget"])
        cost = _parse_cost_payload(root["cost"])
        first_failure = root["first_failure"]
        if first_failure is not None:
            first_failure = dict(_mapping(first_failure, "first_failure"))
        return CandidateRecoveryDiagnosticReceipt(
            identity=identity,
            attempts=attempts,
            budget=budget,
            cost=cost,
            run_state=root["run_state"],
            first_failure=first_failure,
            terminal_reason=root["terminal_reason"],
            recovery_skip_reason=root["recovery_skip_reason"],
            activation_state=root["activation_state"],
            activation_gate=root["activation_gate"],
            execution_allowed=root["execution_allowed"],
        )
    except CandidateRecoveryDiagnosticError:
        raise
    except (CandidateBoundaryContractError, TypeError, ValueError, KeyError, OverflowError):
        # Never surface provider/object details while parsing untrusted JSON.
        raise CandidateRecoveryDiagnosticError("receipt_parse_invalid", "serialize") from None


def _parse_attempt_payload(
    payload: object,
    *,
    identity: CandidateRecoveryDiagnosticIdentity,
) -> CandidateRecoveryAttemptDiagnostic:
    raw = _mapping(payload, "attempt")
    _exact_keys(raw, _ATTEMPT_KEYS, "attempt")
    request = _parse_request_summary_payload(raw["request"], identity=identity)
    observation = _parse_observation_payload(raw["observation"], identity=identity)
    latency_raw = _mapping(raw["latency"], "latency")
    _exact_keys(latency_raw, _LATENCY_KEYS, "latency")
    latency = DiagnosticLatency(**dict(latency_raw))
    cost = _parse_cost_payload(raw["cost"])
    try:
        attempt_kind = CandidateAttemptKind(raw["attempt_kind"])
        disposition = ResponseDisposition(raw["disposition"])
    except (TypeError, ValueError):
        raise CandidateRecoveryDiagnosticError("receipt_enum_invalid", "attempt") from None
    failure_class = raw["failure_class"]
    if failure_class is not None:
        try:
            failure_class = DiagnosticFailureClass(failure_class)
        except (TypeError, ValueError):
            raise CandidateRecoveryDiagnosticError("receipt_enum_invalid", "failure") from None
    return CandidateRecoveryAttemptDiagnostic(
        ordinal=raw["ordinal"],
        attempt_kind=attempt_kind,
        request=request,
        observation=CandidateStreamTrace(observation=observation),
        latency=latency,
        cost=cost,
        disposition=disposition,
        reason_code=raw["reason_code"],
        error_code=raw["error_code"],
        error_stage=raw["error_stage"],
        failure_class=failure_class,
        assembled_complete=raw["assembled_complete"],
        settled=raw["settled"],
        input_tokens=raw["input_tokens"],
        output_tokens=raw["output_tokens"],
        cached_input_tokens=raw["cached_input_tokens"],
        usage_state=raw["usage_state"],
        budget_state=raw["budget_state"],
        consumer_error_code=raw["consumer_error_code"],
    )


def _parse_request_summary_payload(
    payload: object,
    *,
    identity: CandidateRecoveryDiagnosticIdentity,
) -> RequestShapeSummary:
    raw = _mapping(payload, "request")
    _exact_keys(raw, _REQUEST_SUMMARY_KEYS, "request")
    identity_payload = _mapping(raw["candidate_identity"], "request_identity")
    expected_identity = {
        "provider_id": identity.provider_id,
        "model": identity.model,
        "runtime_profile_id": identity.runtime_profile_id,
        "runtime_profile_version": identity.runtime_profile_version,
        "policy_id": identity.policy_id,
        "policy_version": identity.policy_version,
        "activation_state": "candidate",
        "execution_allowed": False,
    }
    if set(identity_payload) != set(expected_identity) or dict(identity_payload) != expected_identity:
        raise CandidateRecoveryDiagnosticError("request_identity_mismatch", "identity")
    raw_messages = raw["messages"]
    if not isinstance(raw_messages, (list, tuple)):
        raise CandidateRecoveryDiagnosticError("receipt_shape_invalid", "messages")
    messages = []
    for item in raw_messages:
        item_mapping = _mapping(item, "message")
        _exact_keys(item_mapping, _MESSAGE_SHAPE_KEYS, "message")
        messages.append(MessageShape(**dict(item_mapping)))
    roles = raw["roles"]
    if not isinstance(roles, (list, tuple)):
        raise CandidateRecoveryDiagnosticError("receipt_shape_invalid", "roles")
    try:
        attempt_kind = CandidateAttemptKind(raw["attempt_kind"])
    except (TypeError, ValueError):
        raise CandidateRecoveryDiagnosticError("receipt_enum_invalid", "request") from None
    return RequestShapeSummary(
        attempt_ordinal=raw["attempt_ordinal"],
        attempt_kind=attempt_kind,
        message_count=raw["message_count"],
        roles=tuple(roles),
        messages=tuple(messages),
        tool_count=raw["tool_count"],
        tool_choice=raw["tool_choice"],
        response_contract_present=raw["response_contract_present"],
        response_contract_name=raw["response_contract_name"],
        response_contract_version=raw["response_contract_version"],
        response_contract_shape_sha256=raw["response_contract_shape_sha256"],
        output_cap=raw["output_cap"],
        agent_timeout_s=raw["agent_timeout_s"],
        transport_timeout_s=raw["transport_timeout_s"],
        temperature=raw["temperature"],
        top_p=raw["top_p"],
        sdk_retries=raw["sdk_retries"],
        shape_sha256=raw["shape_sha256"],
    )


def _parse_observation_payload(
    payload: object,
    *,
    identity: CandidateRecoveryDiagnosticIdentity,
) -> Any:
    raw = _mapping(payload, "observation")
    expected_keys = _OBSERVATION_KEYS | {"trace_schema_version"}
    _exact_keys(raw, expected_keys, "observation")
    if raw["trace_schema_version"] != "1.0":
        raise CandidateRecoveryDiagnosticError("unsupported_trace_schema", "observation")
    if (
        raw["provider_id"],
        raw["model"],
        raw["runtime_profile_id"],
        raw["runtime_profile_version"],
        raw["policy_id"],
        raw["policy_version"],
    ) != (
        identity.provider_id,
        identity.model,
        identity.runtime_profile_id,
        identity.runtime_profile_version,
        identity.policy_id,
        identity.policy_version,
    ):
        raise CandidateRecoveryDiagnosticError("receipt_identity_mismatch", "identity")
    try:
        binding = CandidateRuntimeBinding(
            provider_id=raw["provider_id"],
            model=raw["model"],
            runtime_profile_id=raw["runtime_profile_id"],
            runtime_profile_version=raw["runtime_profile_version"],
            policy_id=raw["policy_id"],
            policy_version=raw["policy_version"],
            attempt_ordinal=raw["attempt_ordinal"],
            attempt_kind=CandidateAttemptKind(raw["attempt_kind"]),
            activation_state=raw["activation_state"],
            execution_allowed=raw["execution_allowed"],
        )
    except (CandidateBoundaryContractError, TypeError, ValueError):
        raise CandidateRecoveryDiagnosticError("observation_identity_invalid", "identity") from None
    return BoundaryObservation(
        binding=binding,
        schema_version=raw["schema_version"],
        opened=raw["opened"],
        eof_observed=raw["eof_observed"],
        terminal_observed=raw["terminal_observed"],
        close_state=raw["close_state"],
        finish_reason=raw["finish_reason"],
        content_state=raw["content_state"],
        reasoning_content_state=raw["reasoning_content_state"],
        tool_call_count=raw["tool_call_count"],
        usage_state=raw["usage_state"],
        input_tokens=raw["input_tokens"],
        output_tokens=raw["output_tokens"],
        cached_input_tokens=raw["cached_input_tokens"],
        elapsed_ms=raw["elapsed_ms"],
        resolved_model=raw["resolved_model"],
        request_id_sha256=raw["request_id_sha256"],
        error_code=raw["error_code"],
        error_stage=raw["error_stage"],
        observation_state=raw["observation_state"],
        next_action=raw["next_action"],
    )


def _parse_cost_payload(payload: object) -> CostObservation:
    raw = _mapping(payload, "cost")
    _exact_keys(raw, _COST_KEYS, "cost")
    amount = raw["amount"]
    if amount is not None:
        try:
            amount = Decimal(str(amount))
        except (InvalidOperation, ValueError, TypeError):
            raise CandidateRecoveryDiagnosticError("cost_amount_invalid", "cost") from None
    return CostObservation(
        status=raw["status"],
        currency=raw["currency"],
        price_snapshot_id_sha256=raw["price_snapshot_id_sha256"],
        amount=amount,
        billing_evidence_sha256=raw["billing_evidence_sha256"],
    )


def _parse_budget_payload(payload: object) -> DiagnosticBudgetProjection:
    raw = _mapping(payload, "budget")
    _exact_keys(raw, _BUDGET_KEYS, "budget")
    limits = _mapping(raw["limits"], "budget_limits")
    _exact_keys(limits, _BUDGET_LIMIT_KEYS, "budget_limits")
    return DiagnosticBudgetProjection(
        calls_reserved=raw["calls_reserved"],
        calls_settled=raw["calls_settled"],
        input_tokens=raw["input_tokens"],
        output_tokens=raw["output_tokens"],
        elapsed_ms=raw["elapsed_ms"],
        input_state=raw["input_state"],
        output_state=raw["output_state"],
        elapsed_state=raw["elapsed_state"],
        calls_state=raw["calls_state"],
        overall_state=raw["overall_state"],
        max_attempts=limits["max_attempts"],
        max_additional_calls=limits["max_additional_calls"],
        max_total_input_tokens=limits["max_total_input_tokens"],
        max_total_output_tokens=limits["max_total_output_tokens"],
        max_total_elapsed_ms=limits["max_total_elapsed_ms"],
    )


class _MonotonicSampler:
    """Cache one validated monotonic reading for observer callbacks."""

    def __init__(self, clock: Callable[[], float]) -> None:
        if not callable(clock):
            raise CandidateRecoveryDiagnosticError("clock_invalid", "clock")
        self._clock = clock
        self._last: float | None = None

    @property
    def last(self) -> float | None:
        return self._last

    def sample(self) -> float:
        try:
            value = self._clock()
        except Exception:
            raise CandidateRecoveryDiagnosticError("clock_unavailable", "clock") from None
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)):
            raise CandidateRecoveryDiagnosticError("clock_invalid", "clock")
        value = float(value)
        if self._last is not None and value < self._last:
            raise CandidateRecoveryDiagnosticError("clock_reversed", "clock")
        self._last = value
        return value

    def cached(self) -> float:
        if self._last is None:
            return self.sample()
        return self._last


class _LatencyBuilder:
    def __init__(self, sampler: _MonotonicSampler) -> None:
        self._sampler = sampler
        # The slot has already been reserved when this object is created.  A
        # broken clock must therefore become a body-free latency gap, not an
        # exception that bypasses settlement.  The actual baseline is bound
        # lazily from the observer's successful open sample.
        self._start = sampler.last
        self._values: dict[str, int | None] = {
            "open_elapsed_ms": None,
            "first_event_ms": None,
            "first_visible_content_ms": None,
            "terminal_ms": None,
            "close_elapsed_ms": None,
            "total_elapsed_ms": None,
        }
        self.error_code: str | None = None

    def mark(self, name: str, *, sample: bool = True) -> None:
        if self._values[name] is not None:
            return
        try:
            if self._start is None:
                self._start = self._sampler.cached()
            now = self._sampler.sample() if sample else self._sampler.cached()
        except CandidateRecoveryDiagnosticError as error:
            self.error_code = error.code
            raise
        elapsed = round((now - self._start) * 1000)
        if elapsed < 0:
            self.error_code = "clock_reversed"
            raise CandidateRecoveryDiagnosticError("clock_reversed", "clock")
        self._values[name] = elapsed

    def finish(self) -> DiagnosticLatency:
        if self._start is None:
            return DiagnosticLatency(**self._values)
        if self._values["total_elapsed_ms"] is None:
            try:
                self.mark("total_elapsed_ms")
            except CandidateRecoveryDiagnosticError:
                # A clock failure is already represented by the attempt's
                # safe failure.  Unobserved latency remains explicitly null.
                self._values["total_elapsed_ms"] = None
        return DiagnosticLatency(**self._values)


def _safe_abort(
    observer: CandidateStreamBoundaryObserver,
    assembler: ProviderStreamAssembler,
    code: str,
    stage: str,
) -> None:
    safe_code = (
        code
        if isinstance(code, str) and _SAFE_CODE.fullmatch(code)
        else "stream_aborted"
    )
    safe_stage = (
        stage
        if isinstance(stage, str) and _SAFE_CODE.fullmatch(stage)
        else "transport"
    )
    try:
        observer.abort(safe_code, safe_stage)
    except CandidateBoundaryContractError:
        pass
    try:
        assembler.abort(safe_code)
    except (StreamAdapterError, ValueError):
        pass


def _stage_for_code(code: str) -> str:
    if code == "stream_aborted":
        return "control"
    if code.startswith("transport_") or code in {"stream_read_failed", "stream_close_failed"}:
        return "transport"
    if code in {"missing_terminal", "invalid_finish_reason", "payload_after_terminal", "incomplete_stream"}:
        return "protocol"
    if "identity" in code or code.endswith("_mismatch") or code in {"model_mismatch", "sequence_conflict"}:
        return "identity"
    if "usage" in code:
        return "usage"
    if "budget" in code or "limit" in code or code == "elapsed_limit":
        return "budget"
    return "observe"


@dataclass(slots=True)
class _AttemptExecution:
    observation: Any
    assembly: StreamAssemblyResult | None
    latency: DiagnosticLatency
    pending_control: BaseException | None


class CandidateRecoveryDiagnostic:
    """One-shot fake/local runner for the versioned diagnostic protocol."""

    def __init__(
        self,
        run: CandidateRecoveryRunSpec,
        *,
        price_snapshot: PriceSnapshot | None = None,
        clock: Callable[[], float] = time.monotonic,
        require_hard_deadline: bool = False,
        deadline_override_s: float | None = None,
    ) -> None:
        if not isinstance(run, CandidateRecoveryRunSpec):
            raise TypeError("run must be CandidateRecoveryRunSpec")
        if price_snapshot is not None and not isinstance(price_snapshot, PriceSnapshot):
            raise TypeError("price_snapshot must be PriceSnapshot or None")
        if not isinstance(require_hard_deadline, bool):
            raise TypeError("require_hard_deadline must be a boolean")
        if deadline_override_s is not None:
            if (
                isinstance(deadline_override_s, bool)
                or not isinstance(deadline_override_s, (int, float))
                or not isfinite(float(deadline_override_s))
                or float(deadline_override_s) <= 0
                or float(deadline_override_s) > run.runtime_profile.agent_timeout_s
            ):
                raise ValueError("deadline_override_s must be within the candidate timeout")
        self._run = run
        self._price_snapshot = price_snapshot
        self._clock = clock
        self._require_hard_deadline = require_hard_deadline
        self._deadline_override_s = (
            float(deadline_override_s) if deadline_override_s is not None else None
        )
        self._used = False
        self._last_receipt: CandidateRecoveryDiagnosticReceipt | None = None

    @property
    def run_spec(self) -> CandidateRecoveryRunSpec:
        return self._run

    @property
    def last_receipt(self) -> CandidateRecoveryDiagnosticReceipt | None:
        return self._last_receipt

    def run_once(
        self,
        request: ChatRequest,
        transport: CandidateStreamTransport,
        *,
        clock: Callable[[], float] | None = None,
        consumer: Any | None = None,
        permit: CandidateRecoveryExecutionPermit | None = None,
    ) -> CandidateRecoveryDiagnosticReceipt:
        """Run one primary attempt; a disabled gate never opens recovery."""

        if self._used:
            raise CandidateRecoveryDiagnosticError("diagnostic_reused", "lifecycle")
        self._used = True
        if not callable(getattr(transport, "open_stream", None)):
            raise CandidateTransportError("invalid_transport", "transport")
        if not isinstance(request, ChatRequest):
            raise CandidateRecoveryDiagnosticError("request_invalid", "request")
        selected_clock = _MonotonicSampler(clock or self._clock)
        profile = self._run.runtime_profile
        cap = profile.max_output_tokens
        if request.max_tokens is not None:
            if isinstance(request.max_tokens, bool) or not isinstance(request.max_tokens, int) or request.max_tokens < 1:
                raise CandidateRecoveryDiagnosticError("output_cap_invalid", "budget")
            cap = min(cap, request.max_tokens)
        try:
            effective_request = replace(
                request,
                max_tokens=cap,
                temperature=profile.temperature,
                top_p=profile.top_p,
                timeout_s=profile.agent_timeout_s,
            )
        except (TypeError, ValueError):
            raise CandidateRecoveryDiagnosticError("request_invalid", "request") from None
        summary = RequestShapeSummary.from_request(
            effective_request,
            attempt_ordinal=1,
            output_cap=cap,
            agent_timeout_s=profile.agent_timeout_s,
            transport_timeout_s=profile.transport_timeout_s,
            temperature=profile.temperature,
            top_p=profile.top_p,
            sdk_retries=0,
        )
        ledger = CandidateRecoveryDiagnosticLedger(self._run)
        reservation = ledger.reserve(summary)
        execution = self._execute_attempt(
            request=effective_request,
            summary=summary,
            reservation=reservation,
            transport=transport,
            sampler=selected_clock,
        )
        usage = None
        if execution.observation.usage_state == "valid":
            usage = TokenUsage(
                input_tokens=execution.observation.input_tokens,
                output_tokens=execution.observation.output_tokens,
                cached_input_tokens=execution.observation.cached_input_tokens,
            )
        cost = CostObservation.unknown()
        if usage is not None and self._price_snapshot is not None:
            try:
                cost = CostObservation.estimated_from_usage(
                    usage,
                    self._price_snapshot,
                )
            except CandidateRecoveryDiagnosticError:
                # An unverified or otherwise unusable price source must not
                # turn a settled model observation into a failed run.  Keep
                # the cost explicitly unknown.
                cost = CostObservation.unknown()
        consumer_error: str | None = None
        delivered = False
        if execution.assembly is not None and consumer is not None:
            if not callable(getattr(consumer, "accept", None)):
                consumer_error = "consumer_invalid"
            else:
                try:
                    consumer.accept(execution.assembly.response)
                    delivered = True
                except (GeneratorExit, KeyboardInterrupt, SystemExit) as error:
                    if execution.pending_control is None:
                        execution.pending_control = error
                except Exception:
                    consumer_error = "consumer_failed"
        attempt = CandidateRecoveryAttemptDiagnostic.from_execution(
            ordinal=reservation.ordinal,
            request=summary,
            observation=execution.observation,
            latency=execution.latency,
            policy=self._run.policy,
            context=self._run.context,
            cost=cost,
            assembled_complete=execution.assembly is not None,
            consumer_error_code=consumer_error,
            pending_control=execution.pending_control is not None,
        )
        ledger.settle(reservation, attempt)
        skip_reason: str | None = None
        if attempt.disposition is ResponseDisposition.CANDIDATE_ELIGIBLE:
            # The current gate is intentionally sealed.  Validate an optional
            # permit only for diagnostics, then refuse to issue a second call.
            if permit is None:
                skip_reason = "activation_disabled"
            else:
                try:
                    now_ms = round((selected_clock.last or 0.0) * 1000)
                    status = permit.verify(FRESH_RECOVERY_CANDIDATE_BINDING, now_ms=now_ms)
                    skip_reason = "activation_disabled" if status == "valid" else f"permit_{status}"
                except CandidateRecoveryDiagnosticError:
                    skip_reason = "permit_invalid"
        elif attempt.disposition is ResponseDisposition.FAIL_CLOSED:
            skip_reason = None
        receipt = CandidateRecoveryDiagnosticReceipt.from_attempts(
            self._run.identity,
            ledger.attempts,
            calls_reserved=ledger.calls_reserved,
            recovery_skip_reason=skip_reason,
        )
        self._last_receipt = receipt
        # Release the temporary body-bearing assembly before returning.
        execution.assembly = None
        if execution.pending_control is not None:
            raise execution.pending_control
        return receipt

    run = run_once
    evaluate = run_once

    def _execute_attempt(
        self,
        *,
        request: ChatRequest,
        summary: RequestShapeSummary,
        reservation: CandidateRecoveryDiagnosticReservation,
        transport: CandidateStreamTransport,
        sampler: _MonotonicSampler,
    ) -> _AttemptExecution:
        binding = CandidateRuntimeBinding.for_attempt(reservation.ordinal)
        observer = CandidateStreamBoundaryObserver(
            binding,
            clock=sampler.cached,
            max_output_tokens=summary.output_cap,
            max_elapsed_ms=min(
                self._run.runtime_profile.max_total_elapsed_ms,
                round(summary.agent_timeout_s * 1000),
            ),
            require_model_observation=True,
            require_request_identity=True,
        )
        assembler = ProviderStreamAssembler(
            provider_id=self._run.runtime_profile.provider_id,
            requested_model=self._run.runtime_profile.model,
            max_output_tokens=summary.output_cap,
            require_model_observation=True,
            require_request_identity=True,
        )
        latency = _LatencyBuilder(sampler)
        # The hard-deadline supervisor uses the real monotonic clock for the
        # wall-clock budget.  Capture it before opening the provider session so
        # a slow handshake cannot silently grant the stream a fresh budget.
        attempt_started_at = time.monotonic()
        stream: Iterable[ProviderStreamEvent] | None = None
        iterator: Iterator[ProviderStreamEvent] | None = None
        session: CandidateStreamSession | None = None
        supervisor: CandidateStreamDeadlineSupervisor | None = None
        assembly: StreamAssemblyResult | None = None
        pending_control: BaseException | None = None
        normal_eof = False

        try:
            try:
                observer.open()
            except CandidateBoundaryContractError as error:
                _safe_abort(observer, assembler, error.code, error.stage or "open")

            if observer.failed_code is None:
                try:
                    open_session = getattr(transport, "open_stream_session", None)
                    if self._require_hard_deadline and callable(open_session):
                        session = require_candidate_stream_session(
                            open_session(
                                binding,
                                request,
                                max_output_tokens=summary.output_cap,
                                timeout_s=summary.agent_timeout_s,
                                transport_timeout_s=summary.transport_timeout_s,
                            )
                        )
                        deadline = self._deadline_override_s or summary.agent_timeout_s
                        supervisor = CandidateStreamDeadlineSupervisor(
                            session,
                            deadline_s=deadline,
                            started_at=attempt_started_at,
                        )
                        stream = supervisor
                    elif self._require_hard_deadline:
                        raise CandidateTransportError(
                            "hard_deadline_unsupported",
                            "transport",
                        )
                    else:
                        stream = transport.open_stream(
                            binding,
                            request,
                            max_output_tokens=summary.output_cap,
                            timeout_s=summary.agent_timeout_s,
                            transport_timeout_s=summary.transport_timeout_s,
                        )
                        if stream is None or not isinstance(stream, Iterable):
                            raise CandidateTransportError("transport_stream_invalid", "open")
                    latency.mark("open_elapsed_ms")
                except (GeneratorExit, KeyboardInterrupt, SystemExit) as error:
                    pending_control = error
                    _safe_abort(observer, assembler, "stream_aborted", "control")
                except CandidateRecoveryDiagnosticError as error:
                    _safe_abort(observer, assembler, error.code, error.stage or "clock")
                except CandidateBoundaryContractError as error:
                    _safe_abort(observer, assembler, error.code, error.stage or "open")
                except Exception:
                    _safe_abort(observer, assembler, "transport_open_failed", "open")

            if stream is not None and observer.failed_code is None and pending_control is None:
                try:
                    iterator = iter(stream)
                    for event in iterator:
                        try:
                            sampler.sample()
                            latency.mark("first_event_ms", sample=False)
                        except CandidateRecoveryDiagnosticError as error:
                            _safe_abort(observer, assembler, error.code, "clock")
                            break
                        try:
                            observer.accept(event)
                        except CandidateBoundaryContractError as error:
                            _safe_abort(observer, assembler, error.code, error.stage or _stage_for_code(error.code))
                            break
                        if event.content_delta is not None and event.content_delta.strip():
                            latency.mark("first_visible_content_ms", sample=False)
                        if event.finish_reason is not None:
                            latency.mark("terminal_ms", sample=False)
                        try:
                            assembler.accept(event)
                        except StreamAdapterError as error:
                            # ``incomplete_stream`` is emitted only during
                            # finalization; event-level errors are protocol.
                            _safe_abort(observer, assembler, error.code, "protocol")
                            break
                    else:
                        normal_eof = True
                except (GeneratorExit, KeyboardInterrupt, SystemExit) as error:
                    pending_control = error
                    _safe_abort(observer, assembler, "stream_aborted", "control")
                except CandidateBoundaryContractError as error:
                    _safe_abort(observer, assembler, error.code, error.stage or "read")
                except Exception:
                    _safe_abort(observer, assembler, "stream_read_failed", "read")

                if normal_eof and observer.failed_code is None:
                    try:
                        observer.mark_exhausted()
                    except CandidateBoundaryContractError as error:
                        _safe_abort(observer, assembler, error.code, error.stage or "protocol")
                if normal_eof and observer.failed_code is None:
                    try:
                        assembler.mark_exhausted()
                    except StreamAdapterError as error:
                        if error.code != "incomplete_stream":
                            _safe_abort(observer, assembler, error.code, "protocol")
        except (GeneratorExit, KeyboardInterrupt, SystemExit) as error:
            pending_control = error
            _safe_abort(observer, assembler, "stream_aborted", "control")
        finally:
            close_failed = False
            seen: set[int] = set()
            # A deadline supervisor owns the session and its provider
            # resources.  Closing its iterator first runs the supervisor's
            # generator finally; the explicit supervisor close is idempotent.
            resources: tuple[object | None, ...] = (iterator, stream)
            for resource in resources:
                if resource is None or id(resource) in seen:
                    continue
                seen.add(id(resource))
                close_method = getattr(resource, "close", None)
                if not callable(close_method):
                    continue
                try:
                    close_method()
                except (GeneratorExit, KeyboardInterrupt, SystemExit) as error:
                    if pending_control is None:
                        pending_control = error
                    close_failed = True
                except Exception:
                    close_failed = True
            if supervisor is not None and supervisor.close_failed:
                close_failed = True
            if close_failed:
                _safe_abort(
                    observer,
                    assembler,
                    "stream_aborted" if pending_control is not None else "stream_close_failed",
                    "control" if pending_control is not None else "close",
                )
            if observer.failed_code is None:
                try:
                    observer.close()
                except CandidateBoundaryContractError as error:
                    _safe_abort(observer, assembler, error.code, error.stage or "close")
            if normal_eof and observer.failed_code is None:
                try:
                    assembly = assembler.finalize()
                except StreamAdapterError as error:
                    if error.code != "incomplete_stream":
                        _safe_abort(observer, assembler, error.code, "protocol")

            try:
                latency.mark("close_elapsed_ms")
            except CandidateRecoveryDiagnosticError:
                # Keep a prior lifecycle error; a clock failure itself is
                # surfaced by the observer on its next callback.
                pass

        try:
            observation = observer.finalize()
        except CandidateBoundaryContractError:
            # The observer's own state should always be finalizable.  If a
            # future hook violates that assumption, expose a safe synthetic
            # pre-open observation by reusing its cached snapshot.
            observation = observer.snapshot()
        latency_value = latency.finish()
        return _AttemptExecution(
            observation=observation,
            assembly=assembly,
            latency=latency_value,
            pending_control=pending_control,
        )


@dataclass(frozen=True, slots=True)
class WrittenDiagnosticReceipt:
    """Result of a create-only canonical receipt write."""

    path: Path
    sha256: str
    byte_length: int

    def __post_init__(self) -> None:
        if not isinstance(self.path, Path):
            raise TypeError("path must be a Path")
        _require_sha256(self.sha256, "sha256")
        _require_non_negative_int(self.byte_length, "byte_length")


def canonical_receipt_bytes(
    receipt: CandidateRecoveryDiagnosticReceipt | Any,
) -> bytes:
    """Return canonical UTF-8/LF bytes after the body-free allow-list check."""

    selected = receipt.receipt if hasattr(receipt, "receipt") else receipt
    if not isinstance(selected, CandidateRecoveryDiagnosticReceipt):
        raise TypeError("receipt must be CandidateRecoveryDiagnosticReceipt")
    payload = selected.as_dict()
    _assert_body_free(payload)
    return _canonical_json(payload)


def write_candidate_recovery_receipt(
    path: str | os.PathLike[str],
    receipt: CandidateRecoveryDiagnosticReceipt | Any,
) -> WrittenDiagnosticReceipt:
    """Atomically create one receipt without ever overwriting an existing file."""

    target = Path(path)
    if not target.name or target.name in {".", ".."}:
        raise CandidateRecoveryDiagnosticError("receipt_path_invalid", "serialize")
    if target.exists() or target.is_symlink():
        raise FileExistsError(str(target))
    parent = target.parent
    if not parent.exists() or not parent.is_dir():
        raise CandidateRecoveryDiagnosticError("receipt_parent_missing", "serialize")
    data = canonical_receipt_bytes(receipt)
    digest = hashlib.sha256(data).hexdigest()
    temp_name: str | None = None
    try:
        fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=str(parent))
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            # A hard link is an atomic, no-overwrite installation on the same
            # volume.  The temporary name is removed after the link succeeds.
            os.link(temp_name, target)
            os.unlink(temp_name)
            temp_name = None
        except FileExistsError:
            raise
        except OSError:
            # Filesystems without hard-link support still get create-only
            # semantics via O_EXCL.  The write is complete before the target
            # is opened, and an existing target can never be replaced.
            flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
            binary = getattr(os, "O_BINARY", 0)
            fd_target = os.open(str(target), flags | binary)
            try:
                with os.fdopen(fd_target, "wb") as handle:
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())
            except Exception:
                try:
                    os.unlink(target)
                except OSError:
                    pass
                raise
            os.unlink(temp_name)
            temp_name = None
    finally:
        if temp_name is not None:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
    return WrittenDiagnosticReceipt(path=target, sha256=digest, byte_length=len(data))


__all__ = [
    "BudgetState",
    "CANDIDATE_RECOVERY_DIAGNOSTIC_PROTOCOL_ID",
    "CANDIDATE_RECOVERY_DIAGNOSTIC_RECEIPT_SCHEMA",
    "CANDIDATE_RECOVERY_DIAGNOSTIC_SCHEMA_VERSION",
    "CandidateRecoveryAttemptDiagnostic",
    "CandidateRecoveryDiagnostic",
    "CandidateRecoveryDiagnosticError",
    "CandidateRecoveryDiagnosticIdentity",
    "CandidateRecoveryDiagnosticLedger",
    "CandidateRecoveryDiagnosticReceipt",
    "CandidateRecoveryDiagnosticReservation",
    "CandidateRecoveryExecutionPermit",
    "CandidateRecoveryRunSpec",
    "CostObservation",
    "DiagnosticActivationGate",
    "DiagnosticBudgetProjection",
    "DiagnosticFailureClass",
    "DiagnosticLatency",
    "MessageShape",
    "PriceSnapshot",
    "RequestShapeSummary",
    "WrittenDiagnosticReceipt",
    "canonical_receipt_bytes",
    "context_shape_sha256",
    "write_candidate_recovery_receipt",
]
