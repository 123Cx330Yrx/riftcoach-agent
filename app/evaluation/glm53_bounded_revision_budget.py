"""Fail-closed call and token wall for the GLM-5.3 hardened V3 gate."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.model_runtime import CandidateEvaluationRequestPolicy
from app.providers.errors import ProviderError, ProviderResponseError
from app.providers.models import ChatRequest, ChatResponse
from app.providers.protocol import LLMProvider

from .glm53_bounded_revision_budget_reachability import (
    CASE_MAX_CALLS,
    DOMAIN_MAX_CALLS,
    estimate_runtime_request_input_ceiling,
)
from .glm53_flash_candidate_profile import (
    GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY,
    require_glm53_flash_low_candidate_request_policy,
)


V3_CASE_MAX_CALLS = CASE_MAX_CALLS
V3_DOMAIN_MAX_CALLS = DOMAIN_MAX_CALLS
V3_CASE_MAX_TOKENS = 203_000
V3_DOMAIN_MAX_TOKENS = 608_000


class BoundedRevisionBudgetError(ProviderResponseError):
    """Safe, non-retryable V3 resource or response boundary failure."""


@dataclass
class _CaseBudget:
    calls_used: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class BoundedRevisionBudgetState:
    """Mutable body-free ledger shared by the three fixed V3 cases."""

    calls_used: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    stop_code: str | None = None
    provider_error_code: str | None = None
    cases: dict[str, _CaseBudget] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def register_case(self, case_id: str) -> None:
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError("case_id must not be blank")
        normalized = case_id.strip()
        if normalized in self.cases:
            raise ValueError("case is already registered")
        if len(self.cases) >= 3:
            raise ValueError("V3 budget accepts exactly three case namespaces")
        self.cases[normalized] = _CaseBudget()

    def stop(self, code: str, *, provider_error_code: str | None = None) -> None:
        self.stop_code = self.stop_code or code
        if provider_error_code is not None:
            self.provider_error_code = self.provider_error_code or provider_error_code

    def case_snapshot(self, case_id: str) -> dict[str, int]:
        row = self.cases[case_id]
        return {
            "calls_used": row.calls_used,
            "input_tokens": row.input_tokens,
            "output_tokens": row.output_tokens,
            "total_tokens": row.total_tokens,
            "latency_ms": row.latency_ms,
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "calls_used": self.calls_used,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "latency_ms": self.latency_ms,
            "stop_code": self.stop_code,
            "provider_error_code": self.provider_error_code,
            "cases": {
                case_id: self.case_snapshot(case_id) for case_id in self.cases
            },
        }


class BoundedRevisionBudgetedProvider:
    """Apply the V3 policy and reserve every call before Provider I/O."""

    def __init__(
        self,
        *,
        provider: LLMProvider,
        state: BoundedRevisionBudgetState,
        case_id: str,
        request_policy: CandidateEvaluationRequestPolicy = (
            GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY
        ),
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not callable(getattr(provider, "chat", None)):
            raise TypeError("provider must provide chat()")
        if not isinstance(state, BoundedRevisionBudgetState):
            raise TypeError("state must be a BoundedRevisionBudgetState")
        if case_id not in state.cases:
            raise ValueError("case must be registered before provider construction")
        self._policy = require_glm53_flash_low_candidate_request_policy(
            request_policy
        )
        if getattr(provider, "provider_name", None) != self._policy.provider_id:
            raise ValueError("Provider ID does not match candidate policy")
        if getattr(provider, "model_name", None) != self._policy.model:
            raise ValueError("Provider model does not match candidate policy")
        if not callable(clock):
            raise TypeError("clock must be callable")
        self._provider = provider
        self._state = state
        self._case_id = case_id
        self._clock = clock
        self.provider_name = provider.provider_name
        self.model_name = provider.model_name
        self.capabilities = provider.capabilities

    @property
    def request_policy(self) -> CandidateEvaluationRequestPolicy:
        return self._policy

    @property
    def state(self) -> BoundedRevisionBudgetState:
        return self._state

    def chat(self, request: ChatRequest) -> ChatResponse:
        if not isinstance(request, ChatRequest):
            raise TypeError("request must be a ChatRequest")
        prepared, input_ceiling = self._reserve(request)
        started = self._clock()
        try:
            response = self._provider.chat(prepared)
        except ProviderError as exc:
            self._state.stop("provider_error", provider_error_code=exc.code)
            raise
        except Exception:
            self._state.stop(
                "provider_error",
                provider_error_code="unexpected_sdk_error",
            )
            raise ProviderResponseError(
                provider=self.provider_name,
                code="unexpected_sdk_error",
            ) from None

        latency_ms = max(0, round((self._clock() - started) * 1000))
        if not isinstance(response, ChatResponse):
            self._block("provider_response_invalid")
        if (
            response.provider != self._policy.provider_id
            or response.model != self._policy.model
        ):
            self._block("provider_response_invalid")
        self._settle(response, latency_ms, input_ceiling=input_ceiling)
        return response

    def _reserve(self, request: ChatRequest) -> tuple[ChatRequest, int]:
        if self._state.stop_code is not None:
            self._block(self._state.stop_code)
        case = self._state.cases[self._case_id]
        if (
            self._state.calls_used >= V3_DOMAIN_MAX_CALLS
            or case.calls_used >= V3_CASE_MAX_CALLS
        ):
            self._block("external_call_budget_exhausted")
        remaining = min(
            V3_DOMAIN_MAX_TOKENS - self._state.total_tokens,
            V3_CASE_MAX_TOKENS - case.total_tokens,
        )
        if remaining <= 0:
            self._block("token_budget_exhausted")
        requested = (
            self._policy.max_output_tokens
            if request.max_tokens is None
            else request.max_tokens
        )
        max_tokens = min(requested, self._policy.max_output_tokens)
        metadata = dict(request.metadata)
        metadata.update(self._policy.metadata())
        metadata.update(
            {
                "candidate_profile_id": "glm-5.3-flash-candidate-low-4096",
                "candidate_profile_version": "1.0.0",
                "candidate_budget_contract": "hardened-v3-bounded-revision",
            }
        )
        prepared = ChatRequest(
            messages=request.messages,
            tools=request.tools,
            tool_choice=request.tool_choice,
            temperature=self._policy.temperature,
            max_tokens=max_tokens,
            timeout_s=min(request.timeout_s, self._policy.llm_tool_timeout_s),
            response_contract=request.response_contract,
            metadata=metadata,
            top_p=self._policy.top_p,
        )
        input_ceiling = estimate_runtime_request_input_ceiling(prepared)
        if input_ceiling + max_tokens > remaining:
            self._block("token_budget_exhausted")
        self._state.calls_used += 1
        case.calls_used += 1
        return prepared, input_ceiling

    def _settle(
        self,
        response: ChatResponse,
        latency_ms: int,
        *,
        input_ceiling: int,
    ) -> None:
        case = self._state.cases[self._case_id]
        usage = response.usage
        self._state.input_tokens += usage.input_tokens
        self._state.output_tokens += usage.output_tokens
        self._state.latency_ms += latency_ms
        case.input_tokens += usage.input_tokens
        case.output_tokens += usage.output_tokens
        case.latency_ms += latency_ms
        if (
            usage.input_tokens > input_ceiling
            or usage.output_tokens > self._policy.max_output_tokens
        ):
            self._block("token_envelope_exceeded")
        if (
            self._state.total_tokens > V3_DOMAIN_MAX_TOKENS
            or case.total_tokens > V3_CASE_MAX_TOKENS
        ):
            self._block("token_budget_exhausted")

    def _block(self, code: str) -> None:
        self._state.stop(code)
        raise BoundedRevisionBudgetError(
            provider=self.provider_name,
            code=code,
        )


__all__ = [
    "BoundedRevisionBudgetError",
    "BoundedRevisionBudgetState",
    "BoundedRevisionBudgetedProvider",
    "V3_CASE_MAX_CALLS",
    "V3_CASE_MAX_TOKENS",
    "V3_DOMAIN_MAX_CALLS",
    "V3_DOMAIN_MAX_TOKENS",
]
