"""Per-run call, usage and elapsed limits for explicit Coach composition."""
from dataclasses import replace
import time

from app.providers.errors import ProviderError, ProviderResponseError
from app.providers.models import ChatResponse
from .observed_provider import ObservedLLMProvider
from .coach_contract import COACH_CONTRACT, require_coach_contract


class CoachBudgetedProvider:
    def __init__(self, provider, *, clock=time.monotonic, coach_contract=COACH_CONTRACT):
        self.contract = require_coach_contract(coach_contract)
        self.contract.require_provider(provider)
        self.provider = provider
        self.provider_name, self.model_name = provider.provider_name, provider.model_name
        self.capabilities = provider.capabilities
        self.thinking_profile_id = provider.thinking_profile_id
        self.sdk_max_retries = provider.sdk_max_retries
        self.runtime_profile = None
        self.clock, self.started = clock, clock()
        self.calls = self.tokens = 0
        # Actual usage and outstanding/unknown reservations are separate. An
        # interrupted or unreceipted call must not make its envelope available
        # again simply because no complete usage response was observed.
        self.reserved_tokens = 0
        self.stopped = False

    def _fail(self, code):
        self.stopped = True
        raise ProviderResponseError(provider=self.provider_name, code=code)

    def _provider_for_request(self, request):
        """Default composition uses its contract-validated single provider."""
        return self.provider

    def _settle_usage(self, response, *, reservation, expected_identity):
        if (not isinstance(response, ChatResponse)
                or (response.provider, response.model) != expected_identity):
            return False
        self.tokens += response.usage.input_tokens + response.usage.output_tokens
        self.reserved_tokens -= reservation
        return True

    def chat(self, request):
        try:
            return self._chat_once(request)
        except ProviderError as error:
            # Recovery is opt-in to this exact candidate. Every attempt still
            # passes through observation, reservations and the shared budget.
            from app.evaluation.sol_natural_contract import CONTRACT as sol_contract
            from app.evaluation.sol_necessity_contract import CONTRACT as necessity_contract
            from app.evaluation.sol_completion_contract import CONTRACT as completion_contract
            from app.evaluation.sol_review_contract import CONTRACT as dual_contract
            if self.contract not in (sol_contract, necessity_contract, completion_contract, dual_contract):
                raise
            delegate = self.provider._delegate if isinstance(self.provider, ObservedLLMProvider) else self.provider
            issued = getattr(self, '_last_issued', None)
            if (issued is None or self.calls >= self.contract.descriptor()['max_calls']
                    or not delegate.prepare_retry(error, issued)):
                raise
            self.stopped = False
            return self._chat_once(request)

    def _chat_once(self, request):
        from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
        limits = self.contract.descriptor()
        remaining = limits["execution_timeout_s"] - (self.clock() - self.started)
        if self.stopped or self.calls >= limits["max_calls"]:
            self._fail("external_call_budget_exhausted")
        if remaining <= 0:
            self._fail("timeout")
        request = replace(request, max_tokens=min(request.max_tokens or limits["max_output_tokens"], limits["max_output_tokens"]),
                          timeout_s=min(request.timeout_s, limits["request_timeout_s"], remaining),
                          temperature=1.0, top_p=0.95,
                          metadata={**request.metadata, "coach_budget_contract": "coach-bounded-review-v2" if self.contract.grounded else "coach-bounded-review-v1"})
        ceiling = estimate_runtime_request_input_ceiling(request)
        reservation = ceiling + request.max_tokens
        if ceiling > limits["max_input_tokens"] or self.tokens + self.reserved_tokens + reservation > limits["total_tokens"]:
            self._fail("token_budget_exhausted")
        try:
            provider = self._provider_for_request(request)
            expected_identity = (self.contract.request_identity(request) if callable(getattr(self.contract, "request_identity", None))
                                 else (provider.provider_name, provider.model_name))
        except Exception:
            self.stopped = True
            raise
        self._last_issued = request
        self.calls += 1
        self.reserved_tokens += reservation
        try:
            response = provider.chat(request)
        except BaseException as error:
            self.stopped = True
            if (isinstance(provider, ObservedLLMProvider)
                    and provider.stopped_before_send(error)):
                # The trusted start fence ran before the delegate. Release only
                # this unsent envelope; this run remains permanently stopped.
                self.calls -= 1
                self.reserved_tokens -= reservation
                raise
            from app.evaluation.sol_natural_contract import CONTRACT as sol_contract
            from app.evaluation.sol_necessity_contract import CONTRACT as necessity_contract
            from app.evaluation.sol_completion_contract import CONTRACT as completion_contract
            from app.evaluation.sol_review_contract import CONTRACT as dual_contract
            from app.product.sol_contract import CONTRACT as product_contract
            if self.contract in (sol_contract, necessity_contract, completion_contract, dual_contract, product_contract):
                delegate = provider._delegate if isinstance(provider, ObservedLLMProvider) else provider
                known = delegate.failure_usage(error, request)
                if known is not None:
                    self.tokens += known
                    self.reserved_tokens -= reservation
                    raise
            # A trusted transport/router may reject the receipt after receiving
            # a complete response. Only that response's matching actual identity
            # can settle the reservation; usage from another model stays unknown.
            if not isinstance(error, ProviderError) or error.provider == expected_identity[0]:
                self._settle_usage(getattr(error, "observed_response", None),
                    reservation=reservation, expected_identity=expected_identity)
            raise
        if not isinstance(response, ChatResponse):
            self._fail("invalid_chat_response")
        if (response.provider, response.model) != expected_identity:
            self._fail("invalid_chat_response")
        self._settle_usage(response, reservation=reservation, expected_identity=expected_identity)
        if response.usage.input_tokens > ceiling or response.usage.output_tokens > request.max_tokens:
            self._fail("token_envelope_exceeded")
        if self.clock() - self.started >= limits["execution_timeout_s"]:
            self._fail("timeout")
        return response
