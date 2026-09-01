"""Isolated, fake/local evaluation harness for the GLM-5.3 candidate.

This module is deliberately a control-plane seam, not a product runtime.  It
coordinates the already existing candidate boundary observer and normalized
stream assembler while keeping response bodies in memory for one short-lived
evaluation only.  No provider registry, SDK, credential, retry, recovery
executor, or product trace is imported here.
"""

from __future__ import annotations

import hashlib
import re
import secrets
import time
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import Any, Literal, Protocol, TypeAlias, runtime_checkable

from app.providers.models import ChatRequest, ChatResponse
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
    RecoveryAttemptKind,
    RecoveryBudgetExceeded,
    RecoveryNotEligible,
    RecoveryStateError,
    ResponseAttemptOutcome,
    ResponseAttemptRecord,
    ResponseAttemptReservation,
    ResponseAttemptSpec,
    ResponseRecoveryRuntimeProfile,
)
from app.providers.stream_adapter_contract import (
    ProviderStreamAssembler,
    ProviderStreamEvent,
    StreamAdapterError,
    StreamAssemblyResult,
)

from .candidate_stream_contract import (
    CANDIDATE_MODEL,
    CANDIDATE_POLICY_ID,
    CANDIDATE_POLICY_VERSION,
    CANDIDATE_PROVIDER_ID,
    CANDIDATE_RUNTIME_PROFILE_ID,
    CANDIDATE_RUNTIME_PROFILE_VERSION,
    CandidateAttemptKind,
    CandidateBoundaryContractError,
    CandidateIdentityError,
    CandidateObservationError,
    CandidateRuntimeBinding,
    CandidateStreamBoundaryObserver,
    CandidateStreamTrace,
    CandidateStreamTransport,
    CandidateTransportError,
    PRIMARY_CANDIDATE_BINDING,
)


CANDIDATE_EVALUATION_SCHEMA_VERSION = "1.0"
CANDIDATE_EVALUATION_RECEIPT_SCHEMA = "candidate-evaluation-harness/1.0"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SAFE_CODE = re.compile(r"^[a-z][a-z0-9_.-]{0,95}$")
_SAFE_ID = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")

UsageCertainty: TypeAlias = Literal["complete", "partial", "unknown"]
BudgetState: TypeAlias = Literal["within", "exceeded", "unknown"]
LedgerTerminalState: TypeAlias = Literal[
    "awaiting_primary",
    "awaiting_recovery",
    "complete_text",
    "tool_calls_ready",
    "fail_closed",
]
LedgerNextAction: TypeAlias = Literal[
    "observe",
    "requires_registered_runtime",
    "terminal_complete",
    "terminal_tool_calls",
    "terminal_fail_closed",
]


class CandidateActivationGate(StrEnum):
    """The only activation value currently constructible for this seam.

    Keeping this as an enum instead of a boolean prevents request metadata or
    a casual ``True`` argument from silently enabling a second provider call.
    A future enabled gate must be introduced by a separately reviewed
    contract; this implementation intentionally has no enabled member.
    """

    DISABLED = "disabled"

    @property
    def execution_allowed(self) -> bool:
        return False


DISABLED_CANDIDATE_ACTIVATION = CandidateActivationGate.DISABLED


class CandidateEvaluationError(CandidateBoundaryContractError):
    """Safe state/coordination error for the isolated evaluation seam."""


@runtime_checkable
class CandidateContentConsumer(Protocol):
    """Explicit, in-memory consumer for a complete evaluation response."""

    def accept(self, response: ChatResponse) -> Any:
        """Inspect one temporary response; never execute product tools."""


def _new_run_id_sha256() -> str:
    """Hash a local nonce; no prompt, body, or provider identifier is used."""

    return hashlib.sha256(secrets.token_bytes(32)).hexdigest()


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
class CandidateEvaluationRunSpec:
    """Immutable exact identity and trusted context for one evaluation run."""

    primary_binding: CandidateRuntimeBinding = field(
        default_factory=CandidateRuntimeBinding.primary
    )
    policy: ResponseCompletionPolicy = (
        GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1
    )
    runtime_profile: ResponseRecoveryRuntimeProfile = (
        GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1
    )
    context: ResponseRequestContext = field(default_factory=_default_context)
    run_id_sha256: str = field(default_factory=_new_run_id_sha256)

    @classmethod
    def new(
        cls,
        *,
        context: ResponseRequestContext | None = None,
    ) -> "CandidateEvaluationRunSpec":
        """Create a run id from a local nonce and bind the exact candidate."""

        return cls(context=context or _default_context())

    def __post_init__(self) -> None:
        if type(self.primary_binding) is not CandidateRuntimeBinding:
            raise CandidateIdentityError("candidate_binding_type", "identity")
        if self.primary_binding is not PRIMARY_CANDIDATE_BINDING:
            raise CandidateIdentityError("candidate_primary_binding_mismatch", "identity")
        if type(self.policy) is not type(GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1):
            raise CandidateIdentityError("candidate_policy_type", "identity")
        if self.policy != GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1:
            raise CandidateIdentityError("candidate_policy_mismatch", "identity")
        if type(self.runtime_profile) is not type(
            GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1
        ):
            raise CandidateIdentityError("candidate_profile_type", "identity")
        if (
            self.runtime_profile
            != GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1
            or not self.runtime_profile.matches_policy(self.policy)
        ):
            raise CandidateIdentityError("candidate_profile_mismatch", "identity")
        if not isinstance(self.context, ResponseRequestContext):
            raise TypeError("context must be a ResponseRequestContext")
        if not isinstance(self.run_id_sha256, str) or not _SHA256.fullmatch(
            self.run_id_sha256
        ):
            raise CandidateEvaluationError("run_identity_invalid", "identity")

    def as_dict(self) -> dict[str, Any]:
        """Return only non-sensitive run identity and bounded context fields."""

        return {
            "schema_version": CANDIDATE_EVALUATION_SCHEMA_VERSION,
            "run_id_sha256": self.run_id_sha256,
            "provider_id": self.primary_binding.provider_id,
            "model": self.primary_binding.model,
            "runtime_profile_id": self.primary_binding.runtime_profile_id,
            "runtime_profile_version": self.primary_binding.runtime_profile_version,
            "policy_id": self.primary_binding.policy_id,
            "policy_version": self.primary_binding.policy_version,
            "phase": self.context.phase,
            "has_response_contract": self.context.has_response_contract,
            "has_tools": self.context.has_tools,
            "has_tool_side_effects": self.context.has_tool_side_effects,
            "remaining_timeout_s": self.context.remaining_timeout_s,
            "remaining_token_budget": self.context.remaining_token_budget,
        }


@dataclass(frozen=True, slots=True)
class CandidateEvaluationLedgerSnapshot:
    """Body-free state/resource view of a staged candidate ledger."""

    calls_reserved: int
    calls_settled: int
    attempts: tuple[ResponseAttemptRecord, ...]
    terminal_state: LedgerTerminalState
    next_action: LedgerNextAction
    input_tokens: int | None
    output_tokens: int | None
    elapsed_ms: int
    unknown_usage_attempts: int
    usage_certainty: UsageCertainty
    budget_state: BudgetState
    budget_exceeded: bool

    def __post_init__(self) -> None:
        if not isinstance(self.attempts, tuple) or not all(
            isinstance(row, ResponseAttemptRecord) for row in self.attempts
        ):
            raise TypeError("attempts must contain ResponseAttemptRecord values")
        for name in ("calls_reserved", "calls_settled", "unknown_usage_attempts", "elapsed_ms"):
            _require_non_negative_int(getattr(self, name), name)
        if self.calls_settled != len(self.attempts):
            raise CandidateEvaluationError("ledger_count_mismatch", "ledger")
        if self.calls_settled > self.calls_reserved or self.calls_reserved > 2:
            raise CandidateEvaluationError("ledger_count_invalid", "ledger")
        expected_input = _known_total([row.outcome.input_tokens for row in self.attempts])
        expected_output = _known_total([row.outcome.output_tokens for row in self.attempts])
        expected_elapsed = sum(row.outcome.elapsed_ms for row in self.attempts)
        if (
            self.input_tokens != expected_input
            or self.output_tokens != expected_output
            or self.elapsed_ms != expected_elapsed
        ):
            raise CandidateEvaluationError("ledger_resource_mismatch", "resource")
        if tuple(row.ordinal for row in self.attempts) != tuple(
            range(1, len(self.attempts) + 1)
        ):
            raise CandidateEvaluationError("ledger_ordinal_invalid", "attempt")
        if self.terminal_state not in {
            "awaiting_primary",
            "awaiting_recovery",
            "complete_text",
            "tool_calls_ready",
            "fail_closed",
        }:
            raise CandidateEvaluationError("ledger_state_invalid", "state")
        if self.next_action not in {
            "observe",
            "requires_registered_runtime",
            "terminal_complete",
            "terminal_tool_calls",
            "terminal_fail_closed",
        }:
            raise CandidateEvaluationError("ledger_action_invalid", "state")
        if self.usage_certainty not in {"complete", "partial", "unknown"}:
            raise CandidateEvaluationError("usage_certainty_invalid", "usage")
        if self.budget_state not in {"within", "exceeded", "unknown"}:
            raise CandidateEvaluationError("budget_state_invalid", "budget")
        if not isinstance(self.budget_exceeded, bool):
            raise CandidateEvaluationError("budget_state_invalid", "budget")
        for name in ("input_tokens", "output_tokens"):
            value = getattr(self, name)
            if value is not None:
                _require_non_negative_int(value, name)

    def as_dict(self) -> dict[str, Any]:
        return {
            "calls_reserved": self.calls_reserved,
            "calls_settled": self.calls_settled,
            "attempts": [_record_as_dict(row) for row in self.attempts],
            "terminal_state": self.terminal_state,
            "next_action": self.next_action,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "elapsed_ms": self.elapsed_ms,
            "unknown_usage_attempts": self.unknown_usage_attempts,
            "usage_certainty": self.usage_certainty,
            "budget_state": self.budget_state,
            "budget_exceeded": self.budget_exceeded,
        }


# A named trace alias keeps the ledger's external vocabulary explicit without
# creating a second serialization shape.
CandidateEvaluationLedgerTrace = CandidateEvaluationLedgerSnapshot


class CandidateEvaluationLedger:
    """Candidate-only staged ledger with reserve-before-I/O semantics."""

    def __init__(
        self,
        run: CandidateEvaluationRunSpec | None = None,
        *,
        runtime_profile: ResponseRecoveryRuntimeProfile = (
            GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1
        ),
        policy: ResponseCompletionPolicy = (
            GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1
        ),
        context: ResponseRequestContext | None = None,
        activation: CandidateActivationGate = DISABLED_CANDIDATE_ACTIVATION,
    ) -> None:
        if run is None:
            run = CandidateEvaluationRunSpec(
                runtime_profile=runtime_profile,
                policy=policy,
                context=context or _default_context(),
            )
        elif any(value is not None for value in (context,)):
            raise TypeError("context cannot be supplied together with run")
        if not isinstance(run, CandidateEvaluationRunSpec):
            raise TypeError("run must be a CandidateEvaluationRunSpec")
        if not isinstance(activation, CandidateActivationGate):
            raise CandidateEvaluationError("activation_gate_invalid", "activation")
        # The run spec performs exact identity validation.  Keep a second
        # identity check here so a future caller cannot swap fields by
        # subclassing or mutating an object after construction.
        if run.runtime_profile is not GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1:
            raise CandidateIdentityError("candidate_profile_mismatch", "identity")
        if run.policy is not GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1:
            raise CandidateIdentityError("candidate_policy_mismatch", "identity")
        self._run = run
        self._profile = run.runtime_profile
        self._policy = run.policy
        self._context = run.context
        self._activation = activation
        self._records: list[ResponseAttemptRecord] = []
        self._open_reservation: ResponseAttemptReservation | None = None
        self._next_reservation_id = 1
        self._calls_reserved = 0
        self._budget_exceeded = False

    @property
    def run(self) -> CandidateEvaluationRunSpec:
        return self._run

    @property
    def runtime_profile(self) -> ResponseRecoveryRuntimeProfile:
        return self._profile

    @property
    def policy(self) -> ResponseCompletionPolicy:
        return self._policy

    @property
    def context(self) -> ResponseRequestContext:
        return self._context

    @property
    def activation(self) -> CandidateActivationGate:
        return self._activation

    @property
    def records(self) -> tuple[ResponseAttemptRecord, ...]:
        return tuple(self._records)

    @property
    def open_reservation(self) -> ResponseAttemptReservation | None:
        return self._open_reservation

    def reserve_next(self) -> ResponseAttemptReservation:
        """Reserve a slot immediately before opening its provider stream."""

        if self._open_reservation is not None:
            raise RecoveryStateError("an attempt is already in flight")
        if self._budget_exceeded:
            raise RecoveryBudgetExceeded("cumulative budget is already exceeded")
        ordinal = len(self._records) + 1
        if ordinal == 1:
            spec = self._spec_for(1)
        elif ordinal == 2:
            if not self._records or not self._records[0].outcome.is_candidate_eligible:
                raise RecoveryNotEligible("first response is not eligible for recovery")
            if self._activation is DISABLED_CANDIDATE_ACTIVATION:
                raise RecoveryNotEligible("candidate activation is disabled")
            spec = self._spec_for(2)
        else:
            raise RecoveryBudgetExceeded("maximum attempt budget exhausted")

        if self._calls_reserved >= self._profile.max_attempts:
            raise RecoveryBudgetExceeded("maximum attempt budget exhausted")
        if (
            self._calls_reserved >= 1
            and self._calls_reserved - 1 >= self._profile.max_additional_calls
        ):
            raise RecoveryBudgetExceeded("additional-call budget exhausted")

        observed_outputs = [row.outcome.output_tokens for row in self._records]
        if any(value is None for value in observed_outputs):
            raise RecoveryBudgetExceeded("output token budget is unknown")
        remaining_output = self._profile.max_total_output_tokens - sum(
            value for value in observed_outputs if value is not None
        )
        if spec.max_output_tokens > remaining_output:
            raise RecoveryBudgetExceeded("output token budget cannot hold next attempt")
        observed_inputs = [row.outcome.input_tokens for row in self._records]
        if any(value is None for value in observed_inputs):
            raise RecoveryBudgetExceeded("input token budget is unknown")
        elapsed_known = sum(row.outcome.elapsed_ms for row in self._records)
        if sum(value for value in observed_inputs if value is not None) >= (
            self._profile.max_total_input_tokens
        ):
            raise RecoveryBudgetExceeded("input token budget is exhausted")
        if elapsed_known >= self._profile.max_total_elapsed_ms:
            raise RecoveryBudgetExceeded("elapsed-time budget is exhausted")

        reservation = ResponseAttemptReservation(
            reservation_id=self._next_reservation_id,
            spec=spec,
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
        """Settle a reserved slot exactly once; failed calls still count."""

        if self._open_reservation is None or reservation is not self._open_reservation:
            raise RecoveryStateError("unknown reservation or duplicate settlement")
        if not isinstance(outcome, ResponseAttemptOutcome):
            raise RecoveryStateError("settlement outcome is invalid")
        spec = reservation.spec
        if spec.ordinal != len(self._records) + 1:
            raise RecoveryStateError("settlement ordinal is out of order")
        if outcome.context != self._context:
            raise RecoveryStateError("attempt context does not match run")
        expected_decision = self._policy.decide(outcome.snapshot, outcome.context)
        if outcome.decision != expected_decision:
            raise RecoveryStateError("attempt decision does not match policy")
        if spec.ordinal == 2:
            if not self._records or not self._records[0].outcome.is_candidate_eligible:
                raise RecoveryNotEligible("recovery is not eligible")
            if self._activation is DISABLED_CANDIDATE_ACTIVATION:
                raise RecoveryNotEligible("candidate activation is disabled")

        input_total = _known_total(
            [row.outcome.input_tokens for row in self._records]
            + [outcome.input_tokens]
        )
        output_total = _known_total(
            [row.outcome.output_tokens for row in self._records]
            + [outcome.output_tokens]
        )
        elapsed_total = sum(row.outcome.elapsed_ms for row in self._records) + outcome.elapsed_ms
        budget_exceeded = (
            (
                outcome.output_tokens is not None
                and outcome.output_tokens > spec.max_output_tokens
            )
            or outcome.elapsed_ms > round(spec.timeout_s * 1000)
            or (input_total is not None and input_total > self._profile.max_total_input_tokens)
            or (output_total is not None and output_total > self._profile.max_total_output_tokens)
            or elapsed_total > self._profile.max_total_elapsed_ms
        )
        record = ResponseAttemptRecord(
            ordinal=spec.ordinal,
            kind=spec.kind,
            provider_id=self._profile.provider_id,
            model=self._profile.model,
            policy_id=self._profile.policy_id,
            policy_version=self._profile.policy_version,
            runtime_profile_id=self._profile.profile_id,
            runtime_profile_version=self._profile.version,
            outcome=outcome,
            budget_exceeded=budget_exceeded,
        )
        self._records.append(record)
        self._open_reservation = None
        self._budget_exceeded = self._budget_exceeded or budget_exceeded
        return record

    def snapshot(self) -> CandidateEvaluationLedgerSnapshot:
        attempts = tuple(self._records)
        terminal_state, next_action = self._state_for(attempts)
        usage_values = [row.outcome.snapshot.usage_state == "valid" for row in attempts]
        unknown_count = sum(not value for value in usage_values)
        if not attempts or unknown_count == len(attempts):
            usage_certainty: UsageCertainty = "unknown"
        elif unknown_count:
            usage_certainty = "partial"
        else:
            usage_certainty = "complete"
        input_tokens = _known_total([row.outcome.input_tokens for row in attempts])
        output_tokens = _known_total([row.outcome.output_tokens for row in attempts])
        if self._budget_exceeded:
            budget_state: BudgetState = "exceeded"
        elif unknown_count:
            budget_state = "unknown"
        else:
            budget_state = "within"
        return CandidateEvaluationLedgerSnapshot(
            calls_reserved=self._calls_reserved,
            calls_settled=len(attempts),
            attempts=attempts,
            terminal_state=terminal_state,
            next_action=next_action,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            elapsed_ms=sum(row.outcome.elapsed_ms for row in attempts),
            unknown_usage_attempts=unknown_count,
            usage_certainty=usage_certainty,
            budget_state=budget_state,
            budget_exceeded=self._budget_exceeded,
        )

    def trace(self) -> CandidateEvaluationLedgerSnapshot:
        """Return the same independent body-free ledger projection."""

        return self.snapshot()

    # Compatibility spellings remain aliases to the same state transition;
    # they do not create a second accounting path.
    reserve = reserve_next

    def _spec_for(self, ordinal: int) -> ResponseAttemptSpec:
        return ResponseAttemptSpec(
            ordinal=ordinal,
            kind=(
                RecoveryAttemptKind.PRIMARY
                if ordinal == 1
                else RecoveryAttemptKind.FRESH_RECOVERY
            ),
            max_output_tokens=self._profile.max_output_tokens,
            timeout_s=self._profile.agent_timeout_s,
            transport_timeout_s=self._profile.transport_timeout_s,
        )

    def _state_for(
        self,
        attempts: tuple[ResponseAttemptRecord, ...],
    ) -> tuple[LedgerTerminalState, LedgerNextAction]:
        if self._open_reservation is not None:
            return (
                "awaiting_primary" if not attempts else "awaiting_recovery",
                "observe",
            )
        if not attempts:
            return "awaiting_primary", "observe"
        if self._budget_exceeded:
            return "fail_closed", "terminal_fail_closed"
        last = attempts[-1].outcome
        if last.is_candidate_eligible:
            return "awaiting_recovery", "requires_registered_runtime"
        if last.decision.disposition is ResponseDisposition.COMPLETE_TEXT:
            return "complete_text", "terminal_complete"
        if last.decision.disposition is ResponseDisposition.TOOL_CALLS_READY:
            return "tool_calls_ready", "terminal_tool_calls"
        return "fail_closed", "terminal_fail_closed"


@dataclass(frozen=True, slots=True)
class CandidateEvaluationAttemptReceipt:
    """One body-free receipt row linked to one settled attempt."""

    ordinal: int
    attempt_kind: CandidateAttemptKind
    observation: CandidateStreamTrace
    disposition: ResponseDisposition
    reason_code: str
    error_code: str | None
    assembled_complete: bool
    input_tokens: int | None
    output_tokens: int | None
    elapsed_ms: int
    budget_exceeded: bool
    consumer_error_code: str | None = None

    def __post_init__(self) -> None:
        if (
            isinstance(self.ordinal, bool)
            or not isinstance(self.ordinal, int)
            or self.ordinal not in {1, 2}
        ):
            raise CandidateEvaluationError("attempt_ordinal_invalid", "attempt")
        expected_kind = (
            CandidateAttemptKind.PRIMARY
            if self.ordinal == 1
            else CandidateAttemptKind.FRESH_RECOVERY
        )
        if self.attempt_kind is not expected_kind:
            raise CandidateEvaluationError("attempt_kind_invalid", "attempt")
        if not isinstance(self.observation, CandidateStreamTrace):
            raise TypeError("observation must be CandidateStreamTrace")
        if self.observation.observation.binding.attempt_ordinal != self.ordinal:
            raise CandidateEvaluationError("attempt_identity_mismatch", "attempt")
        if not isinstance(self.disposition, ResponseDisposition):
            raise CandidateEvaluationError("disposition_invalid", "decision")
        _require_safe_code(self.reason_code, "reason_code")
        if self.error_code is not None:
            _require_safe_code(self.error_code, "error_code")
        if not isinstance(self.assembled_complete, bool):
            raise CandidateEvaluationError("assembly_state_invalid", "assembly")
        for name in ("input_tokens", "output_tokens"):
            value = getattr(self, name)
            if value is not None:
                _require_non_negative_int(value, name)
        _require_non_negative_int(self.elapsed_ms, "elapsed_ms")
        if not isinstance(self.budget_exceeded, bool):
            raise CandidateEvaluationError("budget_state_invalid", "budget")
        if self.consumer_error_code is not None:
            _require_safe_code(self.consumer_error_code, "consumer_error_code")
        observed = self.observation.observation
        if self.elapsed_ms != observed.elapsed_ms:
            raise CandidateEvaluationError("observation_elapsed_mismatch", "trace")
        if observed.usage_state == "valid":
            if self.input_tokens is None or self.output_tokens is None:
                raise CandidateEvaluationError("usage_projection_invalid", "usage")
            if (
                self.input_tokens != observed.input_tokens
                or self.output_tokens != observed.output_tokens
            ):
                raise CandidateEvaluationError("usage_projection_mismatch", "usage")
        elif self.input_tokens is not None or self.output_tokens is not None:
            raise CandidateEvaluationError("unknown_usage_has_tokens", "usage")

    def as_dict(self) -> dict[str, Any]:
        return {
            "ordinal": self.ordinal,
            "attempt_kind": self.attempt_kind.value,
            "observation": self.observation.as_dict(),
            "disposition": self.disposition.value,
            "reason_code": self.reason_code,
            "error_code": self.error_code,
            "assembled_complete": self.assembled_complete,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "elapsed_ms": self.elapsed_ms,
            "budget_exceeded": self.budget_exceeded,
            "consumer_error_code": self.consumer_error_code,
        }


@dataclass(frozen=True, slots=True)
class CandidateEvaluationResource:
    """Resource projection that preserves unknown Usage instead of zeroing it."""

    input_tokens: int | None
    output_tokens: int | None
    elapsed_ms: int
    usage_certainty: UsageCertainty
    budget_state: BudgetState
    unknown_usage_attempts: int

    def __post_init__(self) -> None:
        for name in ("input_tokens", "output_tokens"):
            value = getattr(self, name)
            if value is not None:
                _require_non_negative_int(value, name)
        _require_non_negative_int(self.elapsed_ms, "elapsed_ms")
        _require_non_negative_int(self.unknown_usage_attempts, "unknown_usage_attempts")
        if self.usage_certainty not in {"complete", "partial", "unknown"}:
            raise CandidateEvaluationError("usage_certainty_invalid", "usage")
        if self.budget_state not in {"within", "exceeded", "unknown"}:
            raise CandidateEvaluationError("budget_state_invalid", "budget")

    def as_dict(self) -> dict[str, Any]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "elapsed_ms": self.elapsed_ms,
            "usage_certainty": self.usage_certainty,
            "budget_state": self.budget_state,
            "unknown_usage_attempts": self.unknown_usage_attempts,
        }


@dataclass(frozen=True, slots=True)
class CandidateEvaluationReceipt:
    """Independent, allow-listed envelope for one candidate evaluation."""

    schema_version: str
    run_id_sha256: str
    provider_id: str
    model: str
    runtime_profile_id: str
    runtime_profile_version: str
    policy_id: str
    policy_version: str
    activation_state: Literal["candidate"]
    activation_gate: str
    execution_allowed: bool
    attempts: tuple[CandidateEvaluationAttemptReceipt, ...]
    terminal_state: LedgerTerminalState
    next_action: LedgerNextAction
    calls_reserved: int
    calls_settled: int
    resource: CandidateEvaluationResource
    stream_observations: tuple[CandidateStreamTrace, ...]
    safe_error_code: str | None = None
    safe_error_stage: str | None = None
    consumer_error_code: str | None = None

    def __post_init__(self) -> None:
        if self.schema_version != CANDIDATE_EVALUATION_RECEIPT_SCHEMA:
            raise CandidateEvaluationError("unsupported_receipt_schema", "receipt")
        if not isinstance(self.run_id_sha256, str) or not _SHA256.fullmatch(
            self.run_id_sha256
        ):
            raise CandidateEvaluationError("run_identity_invalid", "identity")
        for name in (
            "provider_id",
            "model",
            "runtime_profile_id",
            "policy_id",
        ):
            _require_safe_identifier(getattr(self, name), name)
        for name in ("runtime_profile_version", "policy_version"):
            if not isinstance(getattr(self, name), str) or not re.fullmatch(
                r"\d+\.\d+\.\d+", getattr(self, name)
            ):
                raise CandidateEvaluationError("identity_version_invalid", "identity")
        if (
            self.provider_id,
            self.model,
            self.runtime_profile_id,
            self.runtime_profile_version,
            self.policy_id,
            self.policy_version,
        ) != (
            CANDIDATE_PROVIDER_ID,
            CANDIDATE_MODEL,
            CANDIDATE_RUNTIME_PROFILE_ID,
            CANDIDATE_RUNTIME_PROFILE_VERSION,
            CANDIDATE_POLICY_ID,
            CANDIDATE_POLICY_VERSION,
        ):
            raise CandidateIdentityError("candidate_identity_mismatch", "identity")
        if self.activation_state != "candidate":
            raise CandidateEvaluationError("candidate_activation_mismatch", "identity")
        if self.activation_gate != DISABLED_CANDIDATE_ACTIVATION.value:
            raise CandidateEvaluationError("activation_gate_invalid", "activation")
        if self.execution_allowed is not False:
            raise CandidateEvaluationError("candidate_execution_disabled", "activation")
        if self.terminal_state not in {
            "awaiting_primary",
            "awaiting_recovery",
            "complete_text",
            "tool_calls_ready",
            "fail_closed",
        }:
            raise CandidateEvaluationError("receipt_state_invalid", "state")
        if self.next_action not in {
            "observe",
            "requires_registered_runtime",
            "terminal_complete",
            "terminal_tool_calls",
            "terminal_fail_closed",
        }:
            raise CandidateEvaluationError("receipt_action_invalid", "state")
        if not isinstance(self.attempts, tuple) or not all(
            isinstance(row, CandidateEvaluationAttemptReceipt)
            for row in self.attempts
        ):
            raise TypeError("attempts must contain CandidateEvaluationAttemptReceipt values")
        if tuple(row.ordinal for row in self.attempts) != tuple(
            range(1, len(self.attempts) + 1)
        ):
            raise CandidateEvaluationError("receipt_ordinal_invalid", "attempt")
        if len(self.attempts) > 2:
            raise CandidateEvaluationError("receipt_third_attempt", "budget")
        if (
            isinstance(self.calls_reserved, bool)
            or not isinstance(self.calls_reserved, int)
            or self.calls_reserved > 2
            or isinstance(self.calls_settled, bool)
            or not isinstance(self.calls_settled, int)
            or self.calls_reserved != self.calls_settled
            or self.calls_settled != len(self.attempts)
        ):
            raise CandidateEvaluationError("receipt_count_mismatch", "ledger")
        _require_non_negative_int(self.calls_reserved, "calls_reserved")
        if not isinstance(self.stream_observations, tuple) or self.stream_observations != tuple(
            row.observation for row in self.attempts
        ):
            raise CandidateEvaluationError("receipt_observation_mismatch", "trace")
        if not isinstance(self.resource, CandidateEvaluationResource):
            raise TypeError("resource must be CandidateEvaluationResource")
        if self.safe_error_code is not None:
            _require_safe_code(self.safe_error_code, "safe_error_code")
        if self.safe_error_stage is not None:
            _require_safe_code(self.safe_error_stage, "safe_error_stage")
            if self.safe_error_code is None:
                raise CandidateEvaluationError("error_stage_without_error", "receipt")
        if self.consumer_error_code is not None:
            _require_safe_code(self.consumer_error_code, "consumer_error_code")
        expected_provider_identity = (
            CANDIDATE_PROVIDER_ID,
            CANDIDATE_MODEL,
            CANDIDATE_RUNTIME_PROFILE_ID,
            CANDIDATE_RUNTIME_PROFILE_VERSION,
            CANDIDATE_POLICY_ID,
            CANDIDATE_POLICY_VERSION,
        )
        for row in self.attempts:
            row_identity = (
                row.observation.observation.binding.provider_id,
                row.observation.observation.binding.model,
                row.observation.observation.binding.runtime_profile_id,
                row.observation.observation.binding.runtime_profile_version,
                row.observation.observation.binding.policy_id,
                row.observation.observation.binding.policy_version,
            )
            if row_identity != expected_provider_identity:
                raise CandidateIdentityError("candidate_identity_mismatch", "identity")
        expected_input = _known_total([row.input_tokens for row in self.attempts])
        expected_output = _known_total([row.output_tokens for row in self.attempts])
        expected_elapsed = sum(row.elapsed_ms for row in self.attempts)
        expected_unknown = sum(
            row.observation.observation.usage_state != "valid"
            for row in self.attempts
        )
        expected_certainty: UsageCertainty
        if not self.attempts or expected_unknown == len(self.attempts):
            expected_certainty = "unknown"
        elif expected_unknown:
            expected_certainty = "partial"
        else:
            expected_certainty = "complete"
        expected_budget: BudgetState
        if any(row.budget_exceeded for row in self.attempts):
            expected_budget = "exceeded"
        elif expected_unknown:
            expected_budget = "unknown"
        else:
            expected_budget = "within"
        if (
            self.resource.input_tokens != expected_input
            or self.resource.output_tokens != expected_output
            or self.resource.elapsed_ms != expected_elapsed
            or self.resource.unknown_usage_attempts != expected_unknown
            or self.resource.usage_certainty != expected_certainty
            or self.resource.budget_state != expected_budget
        ):
            raise CandidateEvaluationError("receipt_resource_mismatch", "resource")

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "run_id_sha256": self.run_id_sha256,
            "provider_id": self.provider_id,
            "model": self.model,
            "runtime_profile_id": self.runtime_profile_id,
            "runtime_profile_version": self.runtime_profile_version,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "activation_state": self.activation_state,
            "activation_gate": self.activation_gate,
            "execution_allowed": self.execution_allowed,
            "attempts": [row.as_dict() for row in self.attempts],
            "terminal_state": self.terminal_state,
            "next_action": self.next_action,
            "calls_reserved": self.calls_reserved,
            "calls_settled": self.calls_settled,
            "resource": self.resource.as_dict(),
            "stream_observations": [trace.as_dict() for trace in self.stream_observations],
            "safe_error_code": self.safe_error_code,
            "safe_error_stage": self.safe_error_stage,
            "consumer_error_code": self.consumer_error_code,
        }
        if not set(payload).issubset(_RECEIPT_KEYS):
            raise CandidateEvaluationError("receipt_field_not_allowlisted", "receipt")
        return payload

    to_dict = as_dict


@dataclass(frozen=True, slots=True)
class CandidateEvaluationResult:
    """Body-free return value; any response body is only given to the consumer."""

    receipt: CandidateEvaluationReceipt
    consumer_delivered: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.receipt, CandidateEvaluationReceipt):
            raise TypeError("receipt must be a CandidateEvaluationReceipt")
        if not isinstance(self.consumer_delivered, bool):
            raise TypeError("consumer_delivered must be a boolean")

    @property
    def terminal_state(self) -> LedgerTerminalState:
        return self.receipt.terminal_state

    @property
    def next_action(self) -> LedgerNextAction:
        return self.receipt.next_action

    @property
    def attempts(self) -> tuple[CandidateEvaluationAttemptReceipt, ...]:
        return self.receipt.attempts

    @property
    def resource(self) -> CandidateEvaluationResource:
        return self.receipt.resource

    @property
    def safe_error_code(self) -> str | None:
        return self.receipt.safe_error_code

    @property
    def safe_error_stage(self) -> str | None:
        return self.receipt.safe_error_stage

    def as_dict(self) -> dict[str, Any]:
        return self.receipt.as_dict()

    to_dict = as_dict


@dataclass(slots=True)
class _AttemptExecution:
    observation: Any
    assembly: StreamAssemblyResult | None
    pending_control: BaseException | None = None


class CandidateEvaluationHarness:
    """Run one explicit fake/local candidate evaluation and then seal it."""

    def __init__(
        self,
        run: CandidateEvaluationRunSpec | None = None,
        *,
        transport: CandidateStreamTransport | None = None,
        activation: CandidateActivationGate = DISABLED_CANDIDATE_ACTIVATION,
        clock: Callable[[], float] = time.monotonic,
        consumer: CandidateContentConsumer | None = None,
    ) -> None:
        if run is not None and not isinstance(run, CandidateEvaluationRunSpec):
            raise TypeError("run must be a CandidateEvaluationRunSpec")
        self._run = run
        self._transport = transport
        self._activation = activation
        self._clock = clock
        self._consumer = consumer
        self._used = False

    def evaluate(
        self,
        request: ChatRequest,
        run: CandidateEvaluationRunSpec | None = None,
        *,
        transport: CandidateStreamTransport | None = None,
        activation: CandidateActivationGate | None = None,
        clock: Callable[[], float] | None = None,
        consumer: CandidateContentConsumer | None = None,
    ) -> CandidateEvaluationResult:
        """Evaluate one stream using only fake/local injected transport."""

        if self._used:
            raise CandidateObservationError("harness_reused", "lifecycle")
        self._used = True
        selected_run = run or self._run
        if not isinstance(selected_run, CandidateEvaluationRunSpec):
            raise TypeError("run must be a CandidateEvaluationRunSpec")
        selected_transport = transport or self._transport
        if selected_transport is None or not callable(
            getattr(selected_transport, "open_stream", None)
        ):
            raise CandidateTransportError("invalid_transport", "transport")
        selected_activation = activation if activation is not None else self._activation
        if not isinstance(selected_activation, CandidateActivationGate):
            raise CandidateTransportError("activation_gate_invalid", "activation")
        if selected_activation is not DISABLED_CANDIDATE_ACTIVATION:
            raise CandidateTransportError("activation_gate_invalid", "activation")
        selected_clock = clock or self._clock
        if not callable(selected_clock):
            raise CandidateEvaluationError("clock_invalid", "clock")
        selected_consumer = consumer if consumer is not None else self._consumer
        if selected_consumer is not None and not callable(
            getattr(selected_consumer, "accept", None)
        ):
            raise CandidateTransportError("invalid_consumer", "consumer")
        bounded_request = _bound_request(request, selected_run)
        ledger = CandidateEvaluationLedger(
            selected_run,
            activation=selected_activation,
        )
        reservation = ledger.reserve_next()
        execution = self._execute_attempt(
            request=bounded_request,
            run=selected_run,
            reservation=reservation,
            transport=selected_transport,
            clock=selected_clock,
            request_max_output_tokens=(
                bounded_request.max_tokens
                if bounded_request.max_tokens is not None
                else selected_run.runtime_profile.max_output_tokens
            ),
        )
        observation = execution.observation
        snapshot = _snapshot_from_observation(observation)
        decision = selected_run.policy.decide(snapshot, selected_run.context)
        # An explicit transport/assembly error must remain fail-closed even
        # if its partial fields happen to resemble a complete response.  A
        # derived shape error (for example ``length_partial_content``) is
        # already rejected by the policy and may retain its known Usage.
        effective_snapshot = snapshot
        if (
            observation.error_code is not None
            and decision.disposition
            in {ResponseDisposition.COMPLETE_TEXT, ResponseDisposition.TOOL_CALLS_READY,
                ResponseDisposition.CANDIDATE_ELIGIBLE}
        ):
            effective_snapshot = replace(snapshot, usage_state="invalid")
            decision = selected_run.policy.decide(
                effective_snapshot,
                selected_run.context,
            )
        outcome = ResponseAttemptOutcome(
            snapshot=effective_snapshot,
            context=selected_run.context,
            decision=decision,
            input_tokens=(
                observation.input_tokens
                if effective_snapshot.usage_state == "valid"
                else None
            ),
            output_tokens=(
                observation.output_tokens
                if effective_snapshot.usage_state == "valid"
                else None
            ),
            elapsed_ms=observation.elapsed_ms,
        )
        record = ledger.settle(reservation, outcome)

        consumer_error_code: str | None = None
        consumer_delivered = False
        if (
            execution.assembly is not None
            and decision.disposition
            in {ResponseDisposition.COMPLETE_TEXT, ResponseDisposition.TOOL_CALLS_READY}
            and selected_consumer is not None
        ):
            try:
                selected_consumer.accept(execution.assembly.response)
                consumer_delivered = True
            except (GeneratorExit, KeyboardInterrupt, SystemExit) as error:
                if execution.pending_control is None:
                    execution.pending_control = error
            except Exception:
                consumer_error_code = "consumer_failed"

        attempt_receipt = _attempt_receipt(
            record,
            observation=observation,
            assembled_complete=execution.assembly is not None,
            consumer_error_code=consumer_error_code,
        )
        ledger_state = ledger.snapshot()
        safe_error_code = observation.error_code
        safe_error_stage = observation.error_stage
        receipt = CandidateEvaluationReceipt(
            schema_version=CANDIDATE_EVALUATION_RECEIPT_SCHEMA,
            run_id_sha256=selected_run.run_id_sha256,
            provider_id=selected_run.runtime_profile.provider_id,
            model=selected_run.runtime_profile.model,
            runtime_profile_id=selected_run.runtime_profile.profile_id,
            runtime_profile_version=selected_run.runtime_profile.version,
            policy_id=selected_run.runtime_profile.policy_id,
            policy_version=selected_run.runtime_profile.policy_version,
            activation_state="candidate",
            activation_gate=selected_activation.value,
            execution_allowed=False,
            attempts=(attempt_receipt,),
            terminal_state=ledger_state.terminal_state,
            next_action=ledger_state.next_action,
            calls_reserved=ledger_state.calls_reserved,
            calls_settled=ledger_state.calls_settled,
            resource=CandidateEvaluationResource(
                input_tokens=ledger_state.input_tokens,
                output_tokens=ledger_state.output_tokens,
                elapsed_ms=ledger_state.elapsed_ms,
                usage_certainty=ledger_state.usage_certainty,
                budget_state=ledger_state.budget_state,
                unknown_usage_attempts=ledger_state.unknown_usage_attempts,
            ),
            stream_observations=(attempt_receipt.observation,),
            safe_error_code=safe_error_code,
            safe_error_stage=safe_error_stage,
            consumer_error_code=consumer_error_code,
        )
        # Drop the only temporary body-bearing object before returning.  The
        # receipt and result contain no reference to it.
        execution.assembly = None
        if execution.pending_control is not None:
            raise execution.pending_control
        return CandidateEvaluationResult(
            receipt=receipt,
            consumer_delivered=consumer_delivered,
        )

    # A short alias makes the one-shot nature obvious to callers that prefer
    # verb-style APIs while preserving the frozen ``evaluate`` contract.
    run = evaluate

    def _execute_attempt(
        self,
        *,
        request: ChatRequest,
        run: CandidateEvaluationRunSpec,
        reservation: ResponseAttemptReservation,
        transport: CandidateStreamTransport,
        clock: Callable[[], float],
        request_max_output_tokens: int,
    ) -> _AttemptExecution:
        binding = CandidateRuntimeBinding.for_attempt(reservation.spec.ordinal)
        observer = CandidateStreamBoundaryObserver(
            binding,
            clock=clock,
            max_output_tokens=request_max_output_tokens,
            max_elapsed_ms=run.runtime_profile.max_total_elapsed_ms,
            require_model_observation=True,
            require_request_identity=True,
        )
        assembler = ProviderStreamAssembler(
            provider_id=run.runtime_profile.provider_id,
            requested_model=run.runtime_profile.model,
            max_output_tokens=request_max_output_tokens,
            require_model_observation=True,
            require_request_identity=True,
        )
        stream: Iterable[ProviderStreamEvent] | None = None
        iterator: Iterator[ProviderStreamEvent] | None = None
        assembly: StreamAssemblyResult | None = None
        pending_control: BaseException | None = None
        normal_eof = False

        try:
            try:
                observer.open()
            except CandidateBoundaryContractError as error:
                _abort_pair(observer, assembler, error.code)

            if observer.failed_code is None:
                try:
                    stream = transport.open_stream(
                        binding,
                        request,
                        max_output_tokens=request_max_output_tokens,
                        timeout_s=reservation.spec.timeout_s,
                        transport_timeout_s=reservation.spec.transport_timeout_s,
                    )
                    if stream is None or not isinstance(stream, Iterable):
                        raise CandidateTransportError("transport_stream_invalid", "open")
                except (GeneratorExit, KeyboardInterrupt, SystemExit) as error:
                    pending_control = error
                    _abort_pair(observer, assembler, "stream_aborted")
                except CandidateBoundaryContractError as error:
                    _abort_pair(observer, assembler, error.code)
                except Exception:
                    _abort_pair(observer, assembler, "transport_open_failed")

            if stream is not None and observer.failed_code is None and pending_control is None:
                try:
                    iterator = iter(stream)
                    for event in iterator:
                        try:
                            observer.accept(event)
                        except CandidateBoundaryContractError as error:
                            _abort_pair(observer, assembler, error.code)
                            break
                        try:
                            assembler.accept(event)
                        except StreamAdapterError as error:
                            _abort_pair(observer, assembler, error.code, stage="assemble")
                            break
                    else:
                        normal_eof = True
                except (GeneratorExit, KeyboardInterrupt, SystemExit) as error:
                    pending_control = error
                    _abort_pair(observer, assembler, "stream_aborted")
                except CandidateBoundaryContractError as error:
                    _abort_pair(observer, assembler, error.code)
                except Exception:
                    _abort_pair(observer, assembler, "stream_read_failed", stage="read")

                if normal_eof and observer.failed_code is None:
                    try:
                        observer.mark_exhausted()
                    except CandidateBoundaryContractError as error:
                        _abort_pair(observer, assembler, error.code)
                if normal_eof and observer.failed_code is None:
                    try:
                        assembler.mark_exhausted()
                    except StreamAdapterError as error:
                        _abort_pair(observer, assembler, error.code, stage="assemble")
        except (GeneratorExit, KeyboardInterrupt, SystemExit) as error:
            # Control exceptions are never swallowed, but the already
            # reserved slot still receives a safe boundary observation after
            # the normal cleanup path below.
            pending_control = error
            _abort_pair(observer, assembler, "stream_aborted")
        finally:
            close_failed = False
            seen: set[int] = set()
            for resource in (iterator, stream):
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
            if close_failed:
                _abort_pair(observer, assembler, "stream_close_failed", stage="close")

            if observer.failed_code is None:
                try:
                    observer.close()
                except CandidateBoundaryContractError as error:
                    _abort_pair(observer, assembler, error.code)

            if observer.failed_code is None and normal_eof:
                try:
                    assembly = assembler.finalize()
                except StreamAdapterError as error:
                    # ``incomplete_stream`` is expected for the candidate
                    # length shape; the body-bearing assembler must not turn
                    # that shape into a ChatResponse.
                    if error.code != "incomplete_stream":
                        _abort_pair(observer, assembler, error.code, stage="assemble")

        try:
            observation = observer.finalize()
        except (GeneratorExit, KeyboardInterrupt, SystemExit) as error:
            # A clock or boundary hook may itself raise a control exception.
            # Convert the mutable observer to a safe failure first, then let
            # the caller re-raise the original control signal after settling.
            if pending_control is None:
                pending_control = error
            _abort_pair(observer, assembler, "stream_aborted")
            observation = observer.finalize()
        return _AttemptExecution(
            observation=observation,
            assembly=assembly,
            pending_control=pending_control,
        )


def _bound_request(
    request: ChatRequest,
    run: CandidateEvaluationRunSpec,
) -> ChatRequest:
    if not isinstance(request, ChatRequest):
        raise CandidateTransportError("invalid_request", "request")
    metadata = request.metadata
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
    cap = run.runtime_profile.max_output_tokens
    if request.max_tokens is not None:
        cap = min(cap, request.max_tokens)
    try:
        return replace(
            request,
            max_tokens=cap,
            temperature=run.runtime_profile.temperature,
            top_p=run.runtime_profile.top_p,
            timeout_s=run.runtime_profile.agent_timeout_s,
        )
    except (TypeError, ValueError):
        raise CandidateTransportError("invalid_request", "request") from None


def _snapshot_from_observation(observation: Any) -> ResponseBoundarySnapshot:
    """Map an observation without ever copying response-bearing fields."""

    if observation.complete_boundary:
        return observation.to_response_boundary_snapshot()
    return ResponseBoundarySnapshot(
        finish_reason=observation.finish_reason,
        content_state=observation.content_state,
        reasoning_content_state=observation.reasoning_content_state,
        tool_call_count=observation.tool_call_count,
        usage_state=observation.usage_state,
    )


def _attempt_receipt(
    record: ResponseAttemptRecord,
    *,
    observation: Any,
    assembled_complete: bool,
    consumer_error_code: str | None,
) -> CandidateEvaluationAttemptReceipt:
    return CandidateEvaluationAttemptReceipt(
        ordinal=record.ordinal,
        attempt_kind=CandidateAttemptKind(record.kind.value),
        observation=CandidateStreamTrace(observation=observation),
        disposition=record.outcome.decision.disposition,
        reason_code=record.outcome.decision.reason_code,
        error_code=record.outcome.decision.error_code,
        assembled_complete=assembled_complete,
        input_tokens=record.outcome.input_tokens,
        output_tokens=record.outcome.output_tokens,
        elapsed_ms=record.outcome.elapsed_ms,
        budget_exceeded=record.budget_exceeded,
        consumer_error_code=consumer_error_code,
    )


def _abort_pair(
    observer: CandidateStreamBoundaryObserver,
    assembler: ProviderStreamAssembler,
    code: str,
    *,
    stage: str | None = None,
) -> None:
    safe_code = code if _SAFE_CODE.fullmatch(code) else "stream_aborted"
    try:
        observer.abort(safe_code, stage or _stage_for_code(safe_code))
    except CandidateBoundaryContractError:
        pass
    try:
        assembler.abort(safe_code)
    except (StreamAdapterError, ValueError):
        pass


def _stage_for_code(code: str) -> str:
    return {
        "transport_open_failed": "open",
        "transport_stream_invalid": "open",
        "stream_read_failed": "read",
        "stream_aborted": "transport",
        "stream_close_failed": "close",
        "incomplete_stream": "assemble",
        "tool_call_arguments": "assemble",
        "invalid_assembled_response": "assemble",
    }.get(code, "observe")


def _record_as_dict(record: ResponseAttemptRecord) -> dict[str, Any]:
    outcome = record.outcome
    snapshot = outcome.snapshot
    decision = outcome.decision
    return {
        "ordinal": record.ordinal,
        "attempt_kind": record.kind.value,
        "provider_id": record.provider_id,
        "model": record.model,
        "policy_id": record.policy_id,
        "policy_version": record.policy_version,
        "runtime_profile_id": record.runtime_profile_id,
        "runtime_profile_version": record.runtime_profile_version,
        "disposition": decision.disposition.value,
        "reason_code": decision.reason_code,
        "error_code": decision.error_code,
        "finish_reason": snapshot.finish_reason,
        "content_state": snapshot.content_state,
        "reasoning_content_state": snapshot.reasoning_content_state,
        "tool_call_count": snapshot.tool_call_count,
        "usage_state": snapshot.usage_state,
        "input_tokens": outcome.input_tokens,
        "output_tokens": outcome.output_tokens,
        "elapsed_ms": outcome.elapsed_ms,
        "budget_exceeded": record.budget_exceeded,
    }


def _known_total(values: Iterable[int | None]) -> int | None:
    values = tuple(values)
    if any(value is None for value in values):
        return None
    return sum(value for value in values if value is not None)


def _require_safe_code(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not _SAFE_CODE.fullmatch(value):
        raise CandidateEvaluationError("unsafe_code", field_name)


def _require_safe_identifier(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
        raise CandidateEvaluationError("unsafe_identifier", field_name)


def _require_non_negative_int(value: object, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CandidateEvaluationError("invalid_integer", field_name)


_RECEIPT_KEYS = frozenset(
    {
        "schema_version",
        "run_id_sha256",
        "provider_id",
        "model",
        "runtime_profile_id",
        "runtime_profile_version",
        "policy_id",
        "policy_version",
        "activation_state",
        "activation_gate",
        "execution_allowed",
        "attempts",
        "terminal_state",
        "next_action",
        "calls_reserved",
        "calls_settled",
        "resource",
        "stream_observations",
        "safe_error_code",
        "safe_error_stage",
        "consumer_error_code",
    }
)


__all__ = [
    "BudgetState",
    "CANDIDATE_EVALUATION_RECEIPT_SCHEMA",
    "CANDIDATE_EVALUATION_SCHEMA_VERSION",
    "CandidateActivationGate",
    "CandidateContentConsumer",
    "CandidateEvaluationAttemptReceipt",
    "CandidateEvaluationError",
    "CandidateEvaluationHarness",
    "CandidateEvaluationLedger",
    "CandidateEvaluationLedgerSnapshot",
    "CandidateEvaluationLedgerTrace",
    "CandidateEvaluationReceipt",
    "CandidateEvaluationResource",
    "CandidateEvaluationResult",
    "CandidateEvaluationRunSpec",
    "CandidateTransportError",
    "DISABLED_CANDIDATE_ACTIVATION",
    "UsageCertainty",
]
