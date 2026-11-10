"""Fail-closed resource wall for the GLM-5.3 low-profile candidate.

The wrapper in this module is an evaluation boundary, not a product runtime.
It is intentionally small: reserve a call before provider I/O, force the
candidate request policy at the last boundary, settle observed usage, and
stop the whole run on the first unsafe or over-budget response.  It does not
retry, recover, publish, or retain response bodies.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.model_runtime import CandidateEvaluationRequestPolicy
from app.providers.errors import ProviderError, ProviderResponseError
from app.providers.models import ChatRequest, ChatResponse
from app.providers.protocol import LLMProvider

from .glm53_flash_candidate_profile import (
    GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY,
    require_glm53_flash_low_candidate_request_policy,
)


CANDIDATE_CASE_MAX_CALLS = 4
CANDIDATE_DOMAIN_MAX_CALLS = 12
CANDIDATE_CASE_MAX_TOKENS = 24_000
CANDIDATE_DOMAIN_MAX_TOKENS = 72_000


class CandidateEvaluationBudgetError(ProviderResponseError):
    """A safe, non-retryable candidate budget/response boundary failure."""


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
class CandidateEvaluationBudgetState:
    """Mutable call/token ledger shared by one candidate domain run."""

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
        self.cases[normalized] = _CaseBudget()

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
        """Return body-free counters suitable for an offline test receipt."""

        return {
            "calls_used": self.calls_used,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "latency_ms": self.latency_ms,
            "stop_code": self.stop_code,
            "provider_error_code": self.provider_error_code,
            "cases": {
                case_id: self.case_snapshot(case_id)
                for case_id in self.cases
            },
        }

    def stop(self, code: str, *, provider_error_code: str | None = None) -> None:
        self.stop_code = self.stop_code or code
        if provider_error_code is not None:
            self.provider_error_code = self.provider_error_code or provider_error_code


class CandidateEvaluationBudgetedProvider:
    """Wrap one provider with the low-profile call/token walls."""

    def __init__(
        self,
        *,
        provider: LLMProvider,
        state: CandidateEvaluationBudgetState,
        case_id: str,
        request_policy: CandidateEvaluationRequestPolicy = (
            GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY
        ),
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not callable(getattr(provider, "chat", None)):
            raise TypeError("provider must provide chat()")
        if not isinstance(state, CandidateEvaluationBudgetState):
            raise TypeError("state must be a CandidateEvaluationBudgetState")
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
    def state(self) -> CandidateEvaluationBudgetState:
        return self._state

    def chat(self, request: ChatRequest) -> ChatResponse:
        if not isinstance(request, ChatRequest):
            raise TypeError("request must be a ChatRequest")
        prepared = self._reserve(request)
        started = self._clock()
        try:
            response = self._provider.chat(prepared)
        except ProviderError as exc:
            self._state.stop(
                "provider_error",
                provider_error_code=exc.code,
            )
            raise
        except Exception:
            self._state.stop("provider_error", provider_error_code="unexpected_sdk_error")
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
        self._settle(response, latency_ms)
        return response

    def _reserve(self, request: ChatRequest) -> ChatRequest:
        if self._state.stop_code is not None:
            self._block(self._state.stop_code)
        case = self._state.cases[self._case_id]
        if self._state.calls_used >= CANDIDATE_DOMAIN_MAX_CALLS:
            self._block("external_call_budget_exhausted")
        if case.calls_used >= CANDIDATE_CASE_MAX_CALLS:
            self._block("external_call_budget_exhausted")
        remaining = min(
            CANDIDATE_DOMAIN_MAX_TOKENS - self._state.total_tokens,
            CANDIDATE_CASE_MAX_TOKENS - case.total_tokens,
        )
        if remaining <= 0:
            self._block("token_budget_exhausted")
        requested = (
            self._policy.max_output_tokens
            if request.max_tokens is None
            else request.max_tokens
        )
        max_tokens = min(requested, self._policy.max_output_tokens, remaining)
        if max_tokens <= 0:
            self._block("token_budget_exhausted")
        metadata = dict(request.metadata)
        metadata.update(self._policy.metadata())
        metadata.update(
            {
                "candidate_profile_id": "glm-5.3-flash-candidate-low-4096",
                "candidate_profile_version": "1.0.0",
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
        # Reserve before opening provider I/O.  A failed call therefore still
        # consumes one bounded slot and cannot be retried by this wrapper.
        self._state.calls_used += 1
        case.calls_used += 1
        return prepared

    def _settle(self, response: ChatResponse, latency_ms: int) -> None:
        case = self._state.cases[self._case_id]
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        self._state.input_tokens += input_tokens
        self._state.output_tokens += output_tokens
        self._state.latency_ms += latency_ms
        case.input_tokens += input_tokens
        case.output_tokens += output_tokens
        case.latency_ms += latency_ms
        if output_tokens > self._policy.max_output_tokens:
            self._block("token_budget_exhausted")
        if self._state.total_tokens > CANDIDATE_DOMAIN_MAX_TOKENS:
            self._block("token_budget_exhausted")
        if case.total_tokens > CANDIDATE_CASE_MAX_TOKENS:
            self._block("token_budget_exhausted")

    def _block(self, code: str) -> None:
        self._state.stop(code)
        raise CandidateEvaluationBudgetError(
            provider=self.provider_name,
            code=code,
        )


__all__ = [
    "CANDIDATE_CASE_MAX_CALLS",
    "CANDIDATE_CASE_MAX_TOKENS",
    "CANDIDATE_DOMAIN_MAX_CALLS",
    "CANDIDATE_DOMAIN_MAX_TOKENS",
    "CandidateEvaluationBudgetError",
    "CandidateEvaluationBudgetState",
    "CandidateEvaluationBudgetedProvider",
]
