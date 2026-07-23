from __future__ import annotations

from typing import Any

import openai

from .errors import (
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from .models import ChatRequest, ChatResponse, TokenUsage


class ZhipuProvider:
    """Translate RiftCoach chat contracts to Zhipu's OpenAI-compatible API."""

    provider_name = "zhipu"

    def __init__(self, *, client: Any, model: str) -> None:
        if client is None:
            raise ValueError("client is required.")
        if not model.strip():
            raise ValueError("model must not be empty.")
        self._client = client
        self._model = model

    def chat(self, request: ChatRequest) -> ChatResponse:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {
                    "role": message.role.value,
                    "content": message.content,
                }
                for message in request.messages
            ],
            "temperature": request.temperature,
            "timeout": request.timeout_s,
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens

        try:
            raw_response = self._client.chat.completions.create(**payload)
        except Exception as error:
            raise self._translate_error(error) from None

        try:
            choice = raw_response.choices[0]
            content = choice.message.content
            if not isinstance(content, str) or not content.strip():
                raise ValueError("empty content")

            model = getattr(raw_response, "model", None) or self._model
            finish_reason = getattr(choice, "finish_reason", None)
            request_id = getattr(raw_response, "id", None)
            usage = self._normalize_usage(getattr(raw_response, "usage", None))
            return ChatResponse(
                content=content.strip(),
                model=model,
                provider=self.provider_name,
                finish_reason=finish_reason,
                usage=usage,
                request_id=request_id,
            )
        except ProviderResponseError:
            raise
        except Exception:
            raise ProviderResponseError(
                provider=self.provider_name,
                code="invalid_chat_response",
            ) from None

    def _translate_error(self, error: Exception):
        if isinstance(
            error,
            (openai.AuthenticationError, openai.PermissionDeniedError),
        ):
            return ProviderAuthenticationError(
                provider=self.provider_name,
                code="authentication_failed",
            )
        if isinstance(error, openai.RateLimitError):
            return ProviderRateLimitError(
                provider=self.provider_name,
                code="rate_limited",
            )
        if isinstance(error, openai.APITimeoutError):
            return ProviderTimeoutError(
                provider=self.provider_name,
                code="timeout",
            )
        if isinstance(error, openai.APIConnectionError):
            return ProviderUnavailableError(
                provider=self.provider_name,
                code="connection_failed",
            )
        if isinstance(error, openai.APIStatusError):
            if error.status_code >= 500:
                return ProviderUnavailableError(
                    provider=self.provider_name,
                    code="service_unavailable",
                )
            return ProviderResponseError(
                provider=self.provider_name,
                code="request_rejected",
            )
        return ProviderUnavailableError(
            provider=self.provider_name,
            code="unexpected_sdk_error",
        )

    @staticmethod
    def _normalize_usage(raw_usage: Any) -> TokenUsage:
        if raw_usage is None:
            return TokenUsage()
        input_tokens = getattr(raw_usage, "prompt_tokens", 0) or 0
        output_tokens = getattr(raw_usage, "completion_tokens", 0) or 0
        return TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
