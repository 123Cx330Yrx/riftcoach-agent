"""Offline-safe controls for the bounded second-Provider admission experiment."""

from __future__ import annotations

import re
import time
from pathlib import Path
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from decimal import Decimal
from enum import Enum
from types import MappingProxyType
from typing import Callable

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.agent.draft import AgentFailureObservation
from app.agent.loop import AgentStopReason
from app.providers.errors import (
    ProviderAuthenticationError,
    ProviderCapabilityError,
    ProviderError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.providers.models import ChatRequest, ChatResponse
from app.providers.protocol import LLMProvider

from .domain_e2e import DomainDatasetRole, load_domain_dataset
from .prompt_context_identity import prepare_domain_experiment


_CODE_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_EXPECTED_HELD_OUT_ID = "domain-e2e-v1-1-secure-held-out"
_EXPECTED_HELD_OUT_VERSION = "1.0.0"
_EXPECTED_HELD_OUT_CASES = (
    "heldout_recent_form_normal",
    "heldout_user_request_instruction",
    "heldout_retrieved_evidence_instruction",
)


class ExperimentFailureCode(str, Enum):
    EXPERIMENT_IDENTITY_MISMATCH = "experiment_identity_mismatch"
    DATASET_NOT_FROZEN = "dataset_not_frozen"
    PUBLIC_CI_SHA_MISMATCH = "public_ci_sha_mismatch"
    PROVIDER_CONFIGURATION_INVALID = "provider_configuration_invalid"

    PROVIDER_AUTHENTICATION_FAILED = "provider_authentication_failed"
    PROVIDER_RATE_LIMITED = "provider_rate_limited"
    PROVIDER_TIMEOUT = "provider_timeout"
    PROVIDER_SERVICE_UNAVAILABLE = "provider_service_unavailable"
    PROVIDER_REQUEST_REJECTED = "provider_request_rejected"
    PROVIDER_CAPABILITY_MISMATCH = "provider_capability_mismatch"
    PROVIDER_RESPONSE_INVALID = "provider_response_invalid"
    PROVIDER_USAGE_UNAVAILABLE = "provider_usage_unavailable"
    PROVIDER_ERROR_UNKNOWN = "provider_error_unknown"

    AGENT_PROVIDER_FAILED = "agent_provider_failed"
    AGENT_CONTROL_FLOW_INCOMPLETE = "agent_control_flow_incomplete"
    TOOL_ROUND_TRIP_INCOMPLETE = "tool_round_trip_incomplete"
    TOOL_EXECUTION_FAILED = "tool_execution_failed"
    EVIDENCE_MISSING_OR_INVALID = "evidence_missing_or_invalid"

    STRUCTURED_EVALUATION_FAILED = "structured_evaluation_failed"
    FACT_OR_CITATION_CHECK_FAILED = "fact_or_citation_check_failed"
    INJECTION_RESISTANCE_FAILED = "injection_resistance_failed"
    TERMINAL_STATUS_MISMATCH = "terminal_status_mismatch"
    UNSAFE_PUBLICATION = "unsafe_publication"
    DOMAIN_CASE_OUTCOME_MISMATCH = "domain_case_outcome_mismatch"
    DOMAIN_CASE_OBSERVATION_INVALID = "domain_case_observation_invalid"

    EXTERNAL_CALL_BUDGET_EXHAUSTED = "external_call_budget_exhausted"
    TOKEN_BUDGET_EXHAUSTED = "token_budget_exhausted"
    COST_BUDGET_EXHAUSTED = "cost_budget_exhausted"
    LATENCY_BUDGET_EXHAUSTED = "latency_budget_exhausted"


class ProviderExperimentPreparationError(RuntimeError):
    """Safe no-I/O experiment preparation failure."""

    def __init__(self, code: ExperimentFailureCode) -> None:
        self.code = code
        super().__init__(f"provider experiment preparation failed: {code.value}")


@dataclass(frozen=True)
class ProviderBudgetPolicy:
    provider_id: str
    model: str
    currency: str
    max_calls: int
    scope_call_limits: Mapping[str, int]
    max_observed_tokens: int
    max_output_tokens_per_request: int
    input_cost_per_million: Decimal
    output_cost_per_million: Decimal
    max_estimated_cost: Decimal
    scope_token_limits: Mapping[str, int] | None = None
    max_latency_ms: int | None = None

    def __post_init__(self) -> None:
        for label, value in (
            ("provider_id", self.provider_id),
            ("model", self.model),
            ("currency", self.currency),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{label} must not be empty")
        for label, value in (
            ("max_calls", self.max_calls),
            ("max_observed_tokens", self.max_observed_tokens),
            (
                "max_output_tokens_per_request",
                self.max_output_tokens_per_request,
            ),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{label} must be a positive integer")
        scopes = dict(self.scope_call_limits)
        if not scopes or any(
            not isinstance(name, str)
            or not name.strip()
            or isinstance(limit, bool)
            or not isinstance(limit, int)
            or limit <= 0
            for name, limit in scopes.items()
        ):
            raise ValueError("scope_call_limits must contain positive limits")
        if any(limit > self.max_calls for limit in scopes.values()):
            raise ValueError("scope call limit cannot exceed Provider max_calls")
        scope_token_limits = (
            {scope: self.max_observed_tokens for scope in scopes}
            if self.scope_token_limits is None
            else dict(self.scope_token_limits)
        )
        if set(scope_token_limits) != set(scopes) or any(
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or limit <= 0
            or limit > self.max_observed_tokens
            for limit in scope_token_limits.values()
        ):
            raise ValueError(
                "scope_token_limits must match scopes and contain valid limits"
            )
        for label, value in (
            ("input_cost_per_million", self.input_cost_per_million),
            ("output_cost_per_million", self.output_cost_per_million),
            ("max_estimated_cost", self.max_estimated_cost),
        ):
            if not isinstance(value, Decimal) or value < 0:
                raise ValueError(f"{label} must be a non-negative Decimal")
        if self.max_estimated_cost <= 0:
            raise ValueError("max_estimated_cost must be greater than zero")
        if self.max_latency_ms is not None and (
            isinstance(self.max_latency_ms, bool)
            or not isinstance(self.max_latency_ms, int)
            or self.max_latency_ms <= 0
        ):
            raise ValueError("max_latency_ms must be positive or None")
        object.__setattr__(
            self,
            "scope_call_limits",
            MappingProxyType(scopes),
        )
        object.__setattr__(
            self,
            "scope_token_limits",
            MappingProxyType(scope_token_limits),
        )


def deepseek_experiment_policy() -> ProviderBudgetPolicy:
    return ProviderBudgetPolicy(
        provider_id="deepseek",
        model="deepseek-v4-pro",
        currency="USD",
        max_calls=15,
        scope_call_limits={"adapter_protocol": 3, "domain": 12},
        max_observed_tokens=16_000,
        max_output_tokens_per_request=1024,
        input_cost_per_million=Decimal("1.32"),
        output_cost_per_million=Decimal("3.96"),
        max_estimated_cost=Decimal("0.10"),
        scope_token_limits={"adapter_protocol": 4000, "domain": 12_000},
    )


def zhipu_experiment_policy() -> ProviderBudgetPolicy:
    return ProviderBudgetPolicy(
        provider_id="zhipu",
        model="glm-5.2",
        currency="CNY",
        max_calls=12,
        scope_call_limits={"domain": 12},
        max_observed_tokens=12_000,
        max_output_tokens_per_request=1024,
        input_cost_per_million=Decimal("8"),
        output_cost_per_million=Decimal("28"),
        max_estimated_cost=Decimal("0.50"),
        scope_token_limits={"domain": 12_000},
    )


class ScopeCallCount(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    scope: str
    calls_used: int = Field(ge=0)
    max_calls: int = Field(gt=0)


class ScopeTokenCount(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    scope: str
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    max_observed_tokens: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_total(self) -> "ScopeTokenCount":
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("scope total_tokens must equal input plus output")
        return self


class CaseResourceCount(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    calls_used: int = Field(ge=0)
    max_calls: int = Field(gt=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    max_observed_tokens: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_total(self) -> "CaseResourceCount":
        if not self.case_id.strip():
            raise ValueError("case_id must not be blank")
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("case total_tokens must equal input plus output")
        return self


class ResourceLedgerSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider_id: str
    model: str
    currency: str
    calls_used: int = Field(ge=0)
    max_calls: int = Field(gt=0)
    scope_calls: tuple[ScopeCallCount, ...]
    scope_tokens: tuple[ScopeTokenCount, ...] = ()
    case_resources: tuple[CaseResourceCount, ...] = ()
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    max_observed_tokens: int = Field(gt=0)
    estimated_cost: Decimal = Field(ge=0)
    max_estimated_cost: Decimal = Field(gt=0)
    latency_ms: int = Field(ge=0)
    stop_code: ExperimentFailureCode | None = None

    @model_validator(mode="after")
    def validate_totals(self) -> ResourceLedgerSnapshot:
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("total_tokens must equal input plus output")
        if self.scope_tokens and (
            sum(row.input_tokens for row in self.scope_tokens)
            != self.input_tokens
            or sum(row.output_tokens for row in self.scope_tokens)
            != self.output_tokens
        ):
            raise ValueError("scope token totals must match the resource total")
        for label, values in (
            ("scope calls", tuple(row.scope for row in self.scope_calls)),
            ("scope tokens", tuple(row.scope for row in self.scope_tokens)),
            ("case resources", tuple(row.case_id for row in self.case_resources)),
        ):
            if len(set(values)) != len(values):
                raise ValueError(f"{label} identities must be unique")
        return self


class ProviderStopObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider_id: str
    failure_code: ExperimentFailureCode


class AgentFailureClassification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    failure_code: ExperimentFailureCode
    provider_failure_code: ExperimentFailureCode | None = None


class ExperimentControlSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    global_stop: ExperimentFailureCode | None = None
    provider_stops: tuple[ProviderStopObservation, ...] = ()


class ExperimentPreparationReport(BaseModel):
    """Public, no-I/O proof that local experiment prerequisites match."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0"
    provider_id: str
    requested_model: str
    base_url: str
    sdk_max_retries: int = Field(ge=0)
    stream: bool
    thinking: str
    code_sha: str
    public_ci_sha: str
    public_ci_success_confirmed: bool
    dataset_id: str
    dataset_version: str
    dataset_sha256: str
    prompt_context_snapshot_id: str
    prompt_context_snapshot_sha256: str
    evaluation_contract: str
    protocol_max_calls: int = Field(gt=0)
    domain_max_calls: int = Field(gt=0)
    cumulative_max_calls: int = Field(gt=0)
    maximum_total_tokens: int = Field(gt=0)
    maximum_output_tokens_per_request: int = Field(gt=0)
    maximum_estimated_cost: Decimal = Field(gt=0)
    currency: str
    external_provider_calls: int = Field(ge=0)
    held_out_executed: bool
    local_preflight_passed: bool

    @model_validator(mode="after")
    def validate_no_io_claim(self) -> ExperimentPreparationReport:
        if self.external_provider_calls != 0 or self.held_out_executed:
            raise ValueError("preparation report must remain no-I/O")
        if not self.local_preflight_passed:
            raise ValueError("preparation report must represent a passed preflight")
        if self.cumulative_max_calls != (
            self.protocol_max_calls + self.domain_max_calls
        ):
            raise ValueError("cumulative call budget must equal protocol plus domain")
        return self


class ExperimentStopController:
    """Deterministic stop state shared by all candidate Provider runs."""

    def __init__(self, *, allowed_provider_ids: tuple[str, ...]) -> None:
        if not allowed_provider_ids or len(set(allowed_provider_ids)) != len(
            allowed_provider_ids
        ):
            raise ValueError("allowed_provider_ids must be non-empty and unique")
        if any(not value.strip() for value in allowed_provider_ids):
            raise ValueError("allowed Provider IDs must not be blank")
        self._allowed = frozenset(allowed_provider_ids)
        self._global_stop: ExperimentFailureCode | None = None
        self._provider_stops: dict[str, ExperimentFailureCode] = {}

    def require_permitted(self, provider_id: str) -> None:
        self._require_known(provider_id)
        code = self._global_stop or self._provider_stops.get(provider_id)
        if code is not None:
            raise ProviderResponseError(
                provider=provider_id,
                code=code.value,
            )

    def stop_provider(
        self,
        provider_id: str,
        failure_code: ExperimentFailureCode,
    ) -> None:
        self._require_known(provider_id)
        self._provider_stops.setdefault(provider_id, failure_code)

    def stop_global(self, failure_code: ExperimentFailureCode) -> None:
        if self._global_stop is None:
            self._global_stop = failure_code

    def record_case_failures(
        self,
        *,
        provider_id: str,
        failure_codes: tuple[ExperimentFailureCode, ...],
    ) -> None:
        self._require_known(provider_id)
        if ExperimentFailureCode.UNSAFE_PUBLICATION in failure_codes:
            self.stop_global(ExperimentFailureCode.UNSAFE_PUBLICATION)

    def snapshot(self) -> ExperimentControlSnapshot:
        return ExperimentControlSnapshot(
            global_stop=self._global_stop,
            provider_stops=tuple(
                ProviderStopObservation(
                    provider_id=provider_id,
                    failure_code=code,
                )
                for provider_id, code in sorted(self._provider_stops.items())
            ),
        )

    def _require_known(self, provider_id: str) -> None:
        if provider_id not in self._allowed:
            raise ValueError("Provider is outside the experiment allowlist")


class ProviderResourceLedger:
    """Reserve before I/O, then settle from normalized Provider usage."""

    def __init__(
        self,
        policy: ProviderBudgetPolicy,
        *,
        initial_snapshot: ResourceLedgerSnapshot | None = None,
    ) -> None:
        if not isinstance(policy, ProviderBudgetPolicy):
            raise TypeError("policy must be a ProviderBudgetPolicy")
        self.policy = policy
        self._calls_used = 0
        self._scope_calls = {scope: 0 for scope in policy.scope_call_limits}
        self._scope_input_tokens = {
            scope: 0 for scope in policy.scope_call_limits
        }
        self._scope_output_tokens = {
            scope: 0 for scope in policy.scope_call_limits
        }
        self._case_limits: dict[str, tuple[int, int]] = {}
        self._case_calls: dict[str, int] = {}
        self._case_input_tokens: dict[str, int] = {}
        self._case_output_tokens: dict[str, int] = {}
        self._input_tokens = 0
        self._output_tokens = 0
        self._estimated_cost = Decimal("0")
        self._latency_ms = 0
        self._stop_code: ExperimentFailureCode | None = None

        if initial_snapshot is not None:
            self._seed(initial_snapshot)

    def register_case(
        self,
        case_id: str,
        *,
        max_calls: int,
        max_observed_tokens: int,
    ) -> None:
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError("case_id must not be blank")
        if case_id in self._case_limits:
            raise ValueError("case resource boundary is already registered")
        for label, value in (
            ("max_calls", max_calls),
            ("max_observed_tokens", max_observed_tokens),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{label} must be a positive integer")
        if max_calls > self.policy.scope_call_limits["domain"]:
            raise ValueError("case call limit exceeds the domain scope")
        if max_observed_tokens > self.policy.scope_token_limits["domain"]:
            raise ValueError("case token limit exceeds the domain scope")
        self._case_limits[case_id] = (max_calls, max_observed_tokens)
        self._case_calls[case_id] = 0
        self._case_input_tokens[case_id] = 0
        self._case_output_tokens[case_id] = 0

    def reserve(
        self,
        request: ChatRequest,
        *,
        scope: str,
        case_id: str | None = None,
    ) -> ChatRequest:
        if scope not in self.policy.scope_call_limits:
            raise ValueError("scope is outside the Provider budget policy")
        if self._stop_code is not None:
            self._raise(self._stop_code)
        if (
            self._calls_used >= self.policy.max_calls
            or self._scope_calls[scope] >= self.policy.scope_call_limits[scope]
        ):
            self._block(ExperimentFailureCode.EXTERNAL_CALL_BUDGET_EXHAUSTED)

        max_tokens = (
            self.policy.max_output_tokens_per_request
            if request.max_tokens is None
            else request.max_tokens
        )
        if max_tokens > self.policy.max_output_tokens_per_request:
            self._block(ExperimentFailureCode.TOKEN_BUDGET_EXHAUSTED)
        if (
            self._input_tokens + self._output_tokens + max_tokens
            > self.policy.max_observed_tokens
        ):
            self._block(ExperimentFailureCode.TOKEN_BUDGET_EXHAUSTED)
        if (
            self._scope_input_tokens[scope]
            + self._scope_output_tokens[scope]
            + max_tokens
            > self.policy.scope_token_limits[scope]
        ):
            self._block(ExperimentFailureCode.TOKEN_BUDGET_EXHAUSTED)
        if case_id is not None:
            if scope != "domain" or case_id not in self._case_limits:
                raise ValueError("case_id requires a registered domain boundary")
            max_case_calls, max_case_tokens = self._case_limits[case_id]
            if self._case_calls[case_id] >= max_case_calls:
                self._block(
                    ExperimentFailureCode.EXTERNAL_CALL_BUDGET_EXHAUSTED
                )
            if (
                self._case_input_tokens[case_id]
                + self._case_output_tokens[case_id]
                + max_tokens
                > max_case_tokens
            ):
                self._block(ExperimentFailureCode.TOKEN_BUDGET_EXHAUSTED)
        worst_output_cost = self._cost(output_tokens=max_tokens)
        if (
            self._estimated_cost + worst_output_cost
            > self.policy.max_estimated_cost
        ):
            self._block(ExperimentFailureCode.COST_BUDGET_EXHAUSTED)

        self._calls_used += 1
        self._scope_calls[scope] += 1
        if case_id is not None:
            self._case_calls[case_id] += 1
        return replace(request, max_tokens=max_tokens)

    def settle(
        self,
        response: ChatResponse,
        *,
        latency_ms: int,
        scope: str,
        case_id: str | None = None,
    ) -> None:
        if not isinstance(response, ChatResponse):
            self._block(ExperimentFailureCode.PROVIDER_RESPONSE_INVALID)
        if (
            response.provider != self.policy.provider_id
            or response.model != self.policy.model
        ):
            self._block(ExperimentFailureCode.PROVIDER_RESPONSE_INVALID)
        if isinstance(latency_ms, bool) or not isinstance(latency_ms, int) or latency_ms < 0:
            raise ValueError("latency_ms must be a non-negative integer")

        self._input_tokens += response.usage.input_tokens
        self._output_tokens += response.usage.output_tokens
        self._scope_input_tokens[scope] += response.usage.input_tokens
        self._scope_output_tokens[scope] += response.usage.output_tokens
        if case_id is not None:
            self._case_input_tokens[case_id] += response.usage.input_tokens
            self._case_output_tokens[case_id] += response.usage.output_tokens
        self._estimated_cost += self._cost(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
        self._latency_ms += latency_ms
        if (
            self._input_tokens + self._output_tokens
            > self.policy.max_observed_tokens
        ):
            self._block(ExperimentFailureCode.TOKEN_BUDGET_EXHAUSTED)
        if (
            self._scope_input_tokens[scope]
            + self._scope_output_tokens[scope]
            > self.policy.scope_token_limits[scope]
        ):
            self._block(ExperimentFailureCode.TOKEN_BUDGET_EXHAUSTED)
        if case_id is not None:
            max_case_tokens = self._case_limits[case_id][1]
            if (
                self._case_input_tokens[case_id]
                + self._case_output_tokens[case_id]
                > max_case_tokens
            ):
                self._block(ExperimentFailureCode.TOKEN_BUDGET_EXHAUSTED)
        if self._estimated_cost > self.policy.max_estimated_cost:
            self._block(ExperimentFailureCode.COST_BUDGET_EXHAUSTED)
        if (
            self.policy.max_latency_ms is not None
            and self._latency_ms > self.policy.max_latency_ms
        ):
            self._block(ExperimentFailureCode.LATENCY_BUDGET_EXHAUSTED)

    def snapshot(self) -> ResourceLedgerSnapshot:
        return ResourceLedgerSnapshot(
            provider_id=self.policy.provider_id,
            model=self.policy.model,
            currency=self.policy.currency,
            calls_used=self._calls_used,
            max_calls=self.policy.max_calls,
            scope_calls=tuple(
                ScopeCallCount(
                    scope=scope,
                    calls_used=self._scope_calls[scope],
                    max_calls=limit,
                )
                for scope, limit in sorted(
                    self.policy.scope_call_limits.items()
                )
            ),
            scope_tokens=tuple(
                ScopeTokenCount(
                    scope=scope,
                    input_tokens=self._scope_input_tokens[scope],
                    output_tokens=self._scope_output_tokens[scope],
                    total_tokens=(
                        self._scope_input_tokens[scope]
                        + self._scope_output_tokens[scope]
                    ),
                    max_observed_tokens=self.policy.scope_token_limits[scope],
                )
                for scope in sorted(self.policy.scope_token_limits)
            ),
            case_resources=tuple(
                CaseResourceCount(
                    case_id=case_id,
                    calls_used=self._case_calls[case_id],
                    max_calls=self._case_limits[case_id][0],
                    input_tokens=self._case_input_tokens[case_id],
                    output_tokens=self._case_output_tokens[case_id],
                    total_tokens=(
                        self._case_input_tokens[case_id]
                        + self._case_output_tokens[case_id]
                    ),
                    max_observed_tokens=self._case_limits[case_id][1],
                )
                for case_id in self._case_limits
            ),
            input_tokens=self._input_tokens,
            output_tokens=self._output_tokens,
            total_tokens=self._input_tokens + self._output_tokens,
            max_observed_tokens=self.policy.max_observed_tokens,
            estimated_cost=self._estimated_cost,
            max_estimated_cost=self.policy.max_estimated_cost,
            latency_ms=self._latency_ms,
            stop_code=self._stop_code,
        )

    def _seed(self, snapshot: ResourceLedgerSnapshot) -> None:
        if not isinstance(snapshot, ResourceLedgerSnapshot):
            raise TypeError("initial_snapshot must be a ResourceLedgerSnapshot")
        expected_scope_calls = {
            scope: limit for scope, limit in self.policy.scope_call_limits.items()
        }
        actual_scope_calls = {
            row.scope: row.max_calls for row in snapshot.scope_calls
        }
        if (
            snapshot.provider_id != self.policy.provider_id
            or snapshot.model != self.policy.model
            or snapshot.currency != self.policy.currency
            or snapshot.max_calls != self.policy.max_calls
            or snapshot.max_observed_tokens != self.policy.max_observed_tokens
            or snapshot.max_estimated_cost != self.policy.max_estimated_cost
            or actual_scope_calls != expected_scope_calls
            or snapshot.stop_code is not None
            or snapshot.case_resources
        ):
            raise ValueError("initial resource snapshot does not match policy")

        self._calls_used = snapshot.calls_used
        self._scope_calls = {
            row.scope: row.calls_used for row in snapshot.scope_calls
        }
        self._input_tokens = snapshot.input_tokens
        self._output_tokens = snapshot.output_tokens
        self._estimated_cost = snapshot.estimated_cost
        self._latency_ms = snapshot.latency_ms

        if snapshot.scope_tokens:
            actual_token_limits = {
                row.scope: row.max_observed_tokens
                for row in snapshot.scope_tokens
            }
            if actual_token_limits != dict(self.policy.scope_token_limits):
                raise ValueError("initial scope token limits do not match policy")
            self._scope_input_tokens = {
                row.scope: row.input_tokens for row in snapshot.scope_tokens
            }
            self._scope_output_tokens = {
                row.scope: row.output_tokens for row in snapshot.scope_tokens
            }
            return

        active_scopes = [
            scope for scope, calls in self._scope_calls.items() if calls > 0
        ]
        if snapshot.total_tokens and len(active_scopes) != 1:
            raise ValueError(
                "legacy resource snapshot cannot safely attribute scope tokens"
            )
        if active_scopes:
            only_scope = active_scopes[0]
            self._scope_input_tokens[only_scope] = snapshot.input_tokens
            self._scope_output_tokens[only_scope] = snapshot.output_tokens

    def _cost(
        self,
        *,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> Decimal:
        million = Decimal("1000000")
        return (
            Decimal(input_tokens) * self.policy.input_cost_per_million
            + Decimal(output_tokens) * self.policy.output_cost_per_million
        ) / million

    def _block(self, code: ExperimentFailureCode) -> None:
        self._stop_code = self._stop_code or code
        self._raise(code)

    def _raise(self, code: ExperimentFailureCode) -> None:
        raise ProviderResponseError(
            provider=self.policy.provider_id,
            code=code.value,
        )


class ExperimentBudgetedProvider:
    """Apply experiment stop and resource gates before delegating."""

    def __init__(
        self,
        *,
        provider: LLMProvider,
        ledger: ProviderResourceLedger,
        controller: ExperimentStopController,
        scope: str,
        case_id: str | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if provider.provider_name != ledger.policy.provider_id:
            raise ValueError("Provider ID does not match budget policy")
        if provider.model_name != ledger.policy.model:
            raise ValueError("Provider model does not match budget policy")
        if scope not in ledger.policy.scope_call_limits:
            raise ValueError("scope is outside the Provider budget policy")
        if case_id is not None and scope != "domain":
            raise ValueError("case_id is only valid for the domain scope")
        self._provider = provider
        self._ledger = ledger
        self._controller = controller
        self._scope = scope
        self._case_id = case_id
        self._clock = clock
        self.provider_name = provider.provider_name
        self.model_name = provider.model_name
        self.capabilities = provider.capabilities

    def chat(self, request: ChatRequest) -> ChatResponse:
        try:
            self._controller.require_permitted(self.provider_name)
            prepared = self._ledger.reserve(
                request,
                scope=self._scope,
                case_id=self._case_id,
            )
            started = self._clock()
            response = self._provider.chat(prepared)
            latency_ms = max(0, round((self._clock() - started) * 1000))
            self._ledger.settle(
                response,
                latency_ms=latency_ms,
                scope=self._scope,
                case_id=self._case_id,
            )
            return response
        except ProviderError as exc:
            self._controller.stop_provider(
                self.provider_name,
                classify_provider_error(exc),
            )
            raise


def classify_provider_error(error: ProviderError) -> ExperimentFailureCode:
    try:
        return ExperimentFailureCode(error.code)
    except ValueError:
        pass
    if isinstance(error, ProviderAuthenticationError):
        return ExperimentFailureCode.PROVIDER_AUTHENTICATION_FAILED
    if isinstance(error, ProviderRateLimitError):
        return ExperimentFailureCode.PROVIDER_RATE_LIMITED
    if isinstance(error, ProviderTimeoutError):
        return ExperimentFailureCode.PROVIDER_TIMEOUT
    if isinstance(error, ProviderUnavailableError):
        if error.code in {"connection_failed", "service_unavailable"}:
            return ExperimentFailureCode.PROVIDER_SERVICE_UNAVAILABLE
        return ExperimentFailureCode.PROVIDER_ERROR_UNKNOWN
    if isinstance(error, ProviderCapabilityError):
        return ExperimentFailureCode.PROVIDER_CAPABILITY_MISMATCH
    if isinstance(error, ProviderResponseError):
        if error.code == "provider_usage_unavailable":
            return ExperimentFailureCode.PROVIDER_USAGE_UNAVAILABLE
        if error.code == "request_rejected":
            return ExperimentFailureCode.PROVIDER_REQUEST_REJECTED
        return ExperimentFailureCode.PROVIDER_RESPONSE_INVALID
    return ExperimentFailureCode.PROVIDER_ERROR_UNKNOWN


def classify_agent_failure(
    observation: AgentFailureObservation,
) -> AgentFailureClassification:
    if not isinstance(observation, AgentFailureObservation):
        raise TypeError("observation must be an AgentFailureObservation")
    if observation.stop_reason is not AgentStopReason.PROVIDER_ERROR:
        return AgentFailureClassification(
            failure_code=ExperimentFailureCode.AGENT_CONTROL_FLOW_INCOMPLETE,
        )
    provider_codes = {
        "authentication_failed": (
            ExperimentFailureCode.PROVIDER_AUTHENTICATION_FAILED
        ),
        "rate_limited": ExperimentFailureCode.PROVIDER_RATE_LIMITED,
        "timeout": ExperimentFailureCode.PROVIDER_TIMEOUT,
        "connection_failed": (
            ExperimentFailureCode.PROVIDER_SERVICE_UNAVAILABLE
        ),
        "service_unavailable": (
            ExperimentFailureCode.PROVIDER_SERVICE_UNAVAILABLE
        ),
        "request_rejected": (
            ExperimentFailureCode.PROVIDER_REQUEST_REJECTED
        ),
        "unsupported_capability": (
            ExperimentFailureCode.PROVIDER_CAPABILITY_MISMATCH
        ),
        "provider_usage_unavailable": (
            ExperimentFailureCode.PROVIDER_USAGE_UNAVAILABLE
        ),
        "external_call_budget_exhausted": (
            ExperimentFailureCode.EXTERNAL_CALL_BUDGET_EXHAUSTED
        ),
        "token_budget_exhausted": (
            ExperimentFailureCode.TOKEN_BUDGET_EXHAUSTED
        ),
        "cost_budget_exhausted": (
            ExperimentFailureCode.COST_BUDGET_EXHAUSTED
        ),
        "latency_budget_exhausted": (
            ExperimentFailureCode.LATENCY_BUDGET_EXHAUSTED
        ),
    }
    provider_failure = provider_codes.get(
        observation.error_code or "",
        ExperimentFailureCode.PROVIDER_ERROR_UNKNOWN,
    )
    return AgentFailureClassification(
        failure_code=ExperimentFailureCode.AGENT_PROVIDER_FAILED,
        provider_failure_code=provider_failure,
    )


def prepare_second_provider_experiment(
    *,
    project_root: str | Path,
    dataset_path: str | Path,
    snapshot_path: str | Path,
    code_sha: str,
    public_ci_sha: str,
    confirm_public_ci_success: bool,
    provider_id: str = "deepseek",
    model: str = "deepseek-v4-pro",
    base_url: str = "https://api.deepseek.com",
    sdk_max_retries: int = 0,
) -> ExperimentPreparationReport:
    """Rebuild frozen identities without creating a Provider or reading a Key."""

    if (
        provider_id != "deepseek"
        or model != "deepseek-v4-pro"
        or base_url != "https://api.deepseek.com"
        or sdk_max_retries != 0
    ):
        raise ProviderExperimentPreparationError(
            ExperimentFailureCode.PROVIDER_CONFIGURATION_INVALID
        )
    if (
        not _CODE_SHA_PATTERN.fullmatch(code_sha)
        or not _CODE_SHA_PATTERN.fullmatch(public_ci_sha)
        or code_sha != public_ci_sha
        or not confirm_public_ci_success
    ):
        raise ProviderExperimentPreparationError(
            ExperimentFailureCode.PUBLIC_CI_SHA_MISMATCH
        )

    root = Path(project_root).resolve()
    dataset_file = Path(dataset_path).resolve()
    snapshot_file = Path(snapshot_path).resolve()
    try:
        dataset = load_domain_dataset(dataset_file)
    except (OSError, ValueError) as exc:
        raise ProviderExperimentPreparationError(
            ExperimentFailureCode.DATASET_NOT_FROZEN
        ) from exc
    if (
        dataset.role is not DomainDatasetRole.HELD_OUT
        or not dataset.calibration_excluded
        or dataset.dataset_id != _EXPECTED_HELD_OUT_ID
        or dataset.dataset_version != _EXPECTED_HELD_OUT_VERSION
        or tuple(row.case_id for row in dataset.cases)
        != _EXPECTED_HELD_OUT_CASES
    ):
        raise ProviderExperimentPreparationError(
            ExperimentFailureCode.DATASET_NOT_FROZEN
        )
    try:
        admission = prepare_domain_experiment(
            project_root=root,
            dataset_path=dataset_file,
            snapshot_path=snapshot_file,
        )
    except (OSError, ValueError) as exc:
        raise ProviderExperimentPreparationError(
            ExperimentFailureCode.EXPERIMENT_IDENTITY_MISMATCH
        ) from exc

    policy = deepseek_experiment_policy()
    return ExperimentPreparationReport(
        provider_id=provider_id,
        requested_model=model,
        base_url=base_url,
        sdk_max_retries=sdk_max_retries,
        stream=False,
        thinking="disabled",
        code_sha=code_sha,
        public_ci_sha=public_ci_sha,
        public_ci_success_confirmed=True,
        dataset_id=admission.dataset_id,
        dataset_version=admission.dataset_version,
        dataset_sha256=admission.dataset_sha256,
        prompt_context_snapshot_id=admission.prompt_context_snapshot_id,
        prompt_context_snapshot_sha256=(
            admission.prompt_context_snapshot_sha256
        ),
        evaluation_contract=admission.evaluation_contract,
        protocol_max_calls=policy.scope_call_limits["adapter_protocol"],
        domain_max_calls=policy.scope_call_limits["domain"],
        cumulative_max_calls=policy.max_calls,
        maximum_total_tokens=policy.max_observed_tokens,
        maximum_output_tokens_per_request=(
            policy.max_output_tokens_per_request
        ),
        maximum_estimated_cost=policy.max_estimated_cost,
        currency=policy.currency,
        external_provider_calls=0,
        held_out_executed=False,
        local_preflight_passed=True,
    )
