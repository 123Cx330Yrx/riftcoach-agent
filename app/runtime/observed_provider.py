"""Run-scoped observation around one provider-neutral chat adapter."""

from __future__ import annotations

from collections.abc import Callable

from app.providers.capabilities import require_provider_capabilities
from app.providers.error_safety import safe_provider_error_code
from app.providers.errors import ProviderError, ProviderResponseError
from app.providers.models import ChatRequest, ChatResponse
from app.providers.protocol import LLMProvider

from .observer import (
    RuntimeObservationError,
    RuntimeSignalObserver,
    observe_runtime_signal,
)
from .signals import (
    ProviderCallCompletedSignal,
    ProviderCallFailedSignal,
    ProviderCallStartedSignal,
    RuntimeFinishReason,
    RuntimeProviderPhase,
)


_HARNESS_PHASES = {
    "evaluate": RuntimeProviderPhase.EVALUATION,
    "evaluate_repair": RuntimeProviderPhase.EVALUATION_REPAIR,
    "revise": RuntimeProviderPhase.REVISION,
}
_FINISH_REASONS = {
    value.value: value
    for value in RuntimeFinishReason
    if value is not RuntimeFinishReason.OTHER
}


class ObservedLLMProvider:
    """Emit body-free signals around every real delegate call in one run."""

    def __init__(
        self,
        *,
        delegate: LLMProvider,
        observer: RuntimeSignalObserver,
        request_identity: Callable[[ChatRequest], tuple[str, str]] | None = None,
    ) -> None:
        if not isinstance(delegate, LLMProvider):
            raise TypeError("delegate must satisfy LLMProvider")
        if not isinstance(observer, RuntimeSignalObserver):
            raise TypeError("observer must satisfy RuntimeSignalObserver")
        if request_identity is not None and not callable(request_identity):
            raise TypeError("request_identity must be callable")
        self._request_identity = request_identity
        self._delegate = delegate
        self._observer = observer
        self._next_ordinal = 1
        self.provider_name = delegate.provider_name
        self.model_name = delegate.model_name
        self.capabilities = delegate.capabilities
        # A new observation wrapper never inherits a receipt from a delegate
        # that may have served an earlier run.  Only a fresh, fully observed
        # call can publish the delegate-owned object below.
        self._last_exchange = None

    @property
    def last_exchange(self):
        """Return the delegate's exact successful transport receipt, if any.

        A failed or observation-incomplete call clears the value.  The
        observation layer never constructs, copies, or reuses an Exchange.
        """

        return self._last_exchange

    @property
    def runtime_profile(self):
        """Expose an optional concrete model profile without widening the port."""

        return getattr(self._delegate, "runtime_profile", None)

    @property
    def source_projection(self):
        return getattr(self._delegate, "source_projection", None)

    @property
    def thinking_profile_id(self):
        return getattr(self._delegate, "thinking_profile_id", None)

    @property
    def sdk_max_retries(self):
        return getattr(self._delegate, "sdk_max_retries", None)

    def chat(self, request: ChatRequest) -> ChatResponse:
        if not isinstance(request, ChatRequest):
            raise TypeError("request must be a ChatRequest")

        previous_exchange = getattr(self._delegate, "last_exchange", None)
        self._last_exchange = None

        phase, iteration = _request_phase(request)
        require_provider_capabilities(
            provider_name=self.provider_name,
            capabilities=self.capabilities,
            request=request,
        )

        # The caller supplies a trusted contract-bound resolver for role routing.
        # Freeze identity once: start/completion/error must describe the same call
        # even if delegate attributes change while chat() is running.
        provider_name, model_name = self._identity_for_request(request)
        started = ProviderCallStartedSignal(
            provider_id=provider_name,
            model=model_name,
            ordinal=self._next_ordinal,
            phase=phase,
            iteration=iteration,
        )
        ordinal = self._next_ordinal
        self._next_ordinal += 1
        observe_runtime_signal(
            self._observer,
            started,
        )

        try:
            response = self._delegate.chat(request)
            if not isinstance(response, ChatResponse):
                raise ProviderResponseError(
                    provider=provider_name,
                    code="invalid_chat_response",
                )
            if (response.provider, response.model) != (provider_name, model_name):
                raise ProviderResponseError(
                    provider=provider_name,
                    code="response_identity_mismatch",
                )
            candidate_exchange = getattr(self._delegate, "last_exchange", None)
            if (
                candidate_exchange is previous_exchange
                or getattr(candidate_exchange, "response", None) is not response
            ):
                candidate_exchange = None
        except RuntimeObservationError:
            self._last_exchange = None
            raise
        except ProviderError as exc:
            self._last_exchange = None
            _observe_provider_failure(
                observer=self._observer,
                provider_name=provider_name,
                model_name=model_name,
                ordinal=ordinal,
                error=exc,
            )
            raise
        except Exception:
            self._last_exchange = None
            observe_runtime_signal(
                self._observer,
                ProviderCallFailedSignal(
                    provider_id=provider_name,
                    model=model_name,
                    ordinal=ordinal,
                    failure_code="provider_failed",
                    provider_error_code=None,
                ),
            )
            raise

        try:
            observe_runtime_signal(
                self._observer,
                ProviderCallCompletedSignal(
                    provider_id=provider_name,
                    model=model_name,
                    ordinal=ordinal,
                    finish_reason=_finish_reason(response.finish_reason),
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                ),
            )
        except RuntimeObservationError:
            self._last_exchange = None
            raise
        self._last_exchange = candidate_exchange
        return response

    def _identity_for_request(self, request: ChatRequest) -> tuple[str, str]:
        if self._request_identity is None:
            return self.provider_name, self.model_name
        identity = self._request_identity(request)
        if (
            not isinstance(identity, tuple)
            or len(identity) != 2
            or any(not isinstance(value, str) or not value for value in identity)
        ):
            raise RuntimeObservationError("runtime provider identity is invalid")
        return identity


def _request_phase(
    request: ChatRequest,
) -> tuple[RuntimeProviderPhase, int | None]:
    metadata = request.metadata
    iteration = metadata.get("agent_loop_iteration")
    harness_step = metadata.get("harness_step")
    if iteration is not None:
        if (
            isinstance(iteration, bool)
            or not isinstance(iteration, int)
            or iteration < 1
            or harness_step is not None
        ):
            raise RuntimeObservationError("runtime provider phase is invalid")
        return RuntimeProviderPhase.AGENT, iteration
    if isinstance(harness_step, str) and harness_step in _HARNESS_PHASES:
        return _HARNESS_PHASES[harness_step], None
    raise RuntimeObservationError("runtime provider phase is unavailable")


def _finish_reason(value: str | None) -> RuntimeFinishReason | None:
    if value is None:
        return None
    return _FINISH_REASONS.get(value, RuntimeFinishReason.OTHER)


def _observe_provider_failure(
    *,
    observer: RuntimeSignalObserver,
    provider_name: str,
    model_name: str,
    ordinal: int,
    error: ProviderError,
) -> None:
    # A trusted transport/router can fail receipt validation after an actual
    # response arrived. Preserve its already-known usage, but still propagate
    # the original failure and never expose an Exchange. A response from a
    # different model/provider cannot safely be attributed to the started call.
    observed_response = getattr(error, "observed_response", None)
    if (
        error.provider == provider_name
        and isinstance(observed_response, ChatResponse)
        and (observed_response.provider, observed_response.model)
        == (provider_name, model_name)
    ):
        observe_runtime_signal(
            observer,
            ProviderCallCompletedSignal(
                provider_id=provider_name,
                model=model_name,
                ordinal=ordinal,
                finish_reason=_finish_reason(observed_response.finish_reason),
                input_tokens=observed_response.usage.input_tokens,
                output_tokens=observed_response.usage.output_tokens,
            ),
        )
        return
    detail = (
        safe_provider_error_code(error)
        if error.provider == provider_name
        else None
    )
    observe_runtime_signal(
        observer,
        ProviderCallFailedSignal(
            provider_id=provider_name,
            model=model_name,
            ordinal=ordinal,
            failure_code="provider_failed",
            provider_error_code=detail,
        ),
    )


__all__ = ["ObservedLLMProvider"]
