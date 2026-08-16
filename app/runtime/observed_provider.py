"""Run-scoped observation around one provider-neutral chat adapter."""

from __future__ import annotations

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
    ) -> None:
        if not isinstance(delegate, LLMProvider):
            raise TypeError("delegate must satisfy LLMProvider")
        if not isinstance(observer, RuntimeSignalObserver):
            raise TypeError("observer must satisfy RuntimeSignalObserver")
        self._delegate = delegate
        self._observer = observer
        self._next_ordinal = 1
        self.provider_name = delegate.provider_name
        self.model_name = delegate.model_name
        self.capabilities = delegate.capabilities

    def chat(self, request: ChatRequest) -> ChatResponse:
        if not isinstance(request, ChatRequest):
            raise TypeError("request must be a ChatRequest")

        phase, iteration = _request_phase(request)
        require_provider_capabilities(
            provider_name=self.provider_name,
            capabilities=self.capabilities,
            request=request,
        )

        ordinal = self._next_ordinal
        self._next_ordinal += 1
        observe_runtime_signal(
            self._observer,
            ProviderCallStartedSignal(
                provider_id=self.provider_name,
                model=self.model_name,
                ordinal=ordinal,
                phase=phase,
                iteration=iteration,
            ),
        )

        try:
            response = self._delegate.chat(request)
            if not isinstance(response, ChatResponse):
                raise ProviderResponseError(
                    provider=self.provider_name,
                    code="invalid_chat_response",
                )
        except RuntimeObservationError:
            raise
        except ProviderError as exc:
            _observe_provider_failure(
                observer=self._observer,
                provider_name=self.provider_name,
                model_name=self.model_name,
                ordinal=ordinal,
                error=exc,
            )
            raise
        except Exception:
            observe_runtime_signal(
                self._observer,
                ProviderCallFailedSignal(
                    provider_id=self.provider_name,
                    model=self.model_name,
                    ordinal=ordinal,
                    failure_code="provider_failed",
                    provider_error_code=None,
                ),
            )
            raise

        observe_runtime_signal(
            self._observer,
            ProviderCallCompletedSignal(
                provider_id=self.provider_name,
                model=self.model_name,
                ordinal=ordinal,
                finish_reason=_finish_reason(response.finish_reason),
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            ),
        )
        return response


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
