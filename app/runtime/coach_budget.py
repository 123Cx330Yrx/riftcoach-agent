"""Per-run call, usage and elapsed limits for explicit Coach composition."""
from dataclasses import replace
import time

from app.providers.errors import ProviderResponseError
from app.providers.models import ChatResponse
from .coach_contract import COACH_CONTRACT


class CoachBudgetedProvider:
    def __init__(self, provider, *, clock=time.monotonic):
        COACH_CONTRACT.require_provider(provider)
        self.provider = provider
        self.provider_name, self.model_name = provider.provider_name, provider.model_name
        self.capabilities = provider.capabilities
        self.thinking_profile_id = provider.thinking_profile_id
        self.sdk_max_retries = provider.sdk_max_retries
        self.runtime_profile = None
        self.clock, self.started = clock, clock()
        self.calls = self.tokens = 0
        self.stopped = False

    def _fail(self, code):
        self.stopped = True
        raise ProviderResponseError(provider=self.provider_name, code=code)

    def chat(self, request):
        from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
        limits = COACH_CONTRACT.descriptor()
        remaining = limits["execution_timeout_s"] - (self.clock() - self.started)
        if self.stopped or self.calls >= limits["max_calls"]:
            self._fail("external_call_budget_exhausted")
        if remaining <= 0:
            self._fail("timeout")
        request = replace(request, max_tokens=min(request.max_tokens or limits["max_output_tokens"], limits["max_output_tokens"]),
                          timeout_s=min(request.timeout_s, limits["request_timeout_s"], remaining),
                          temperature=1.0, top_p=0.95,
                          metadata={**request.metadata, "coach_budget_contract": "coach-bounded-review-v1"})
        ceiling = estimate_runtime_request_input_ceiling(request)
        if ceiling > limits["max_input_tokens"] or self.tokens + ceiling + request.max_tokens > limits["total_tokens"]:
            self._fail("token_budget_exhausted")
        self.calls += 1
        try:
            response = self.provider.chat(request)
        except Exception:
            self.stopped = True
            raise
        if not isinstance(response, ChatResponse):
            self._fail("invalid_chat_response")
        if response.provider != self.provider_name or response.model != self.model_name:
            self._fail("invalid_chat_response")
        self.tokens += response.usage.input_tokens + response.usage.output_tokens
        if response.usage.input_tokens > ceiling or response.usage.output_tokens > request.max_tokens:
            self._fail("token_envelope_exceeded")
        if self.clock() - self.started >= limits["execution_timeout_s"]:
            self._fail("timeout")
        return response
