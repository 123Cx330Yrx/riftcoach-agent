from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import ChatRequest, ChatResponse


@runtime_checkable
class LLMProvider(Protocol):
    """Provider-neutral outbound port for one synchronous chat request."""

    provider_name: str

    def chat(self, request: ChatRequest) -> ChatResponse:
        """Return a normalized response or raise a typed ProviderError."""
