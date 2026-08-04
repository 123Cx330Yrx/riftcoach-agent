from __future__ import annotations

from typing import Protocol, runtime_checkable

from .capabilities import ProviderCapabilities
from .models import ChatRequest, ChatResponse


@runtime_checkable
class LLMProvider(Protocol):
    """Provider-neutral outbound port for one synchronous chat request."""

    provider_name: str
    model_name: str
    capabilities: ProviderCapabilities

    def chat(self, request: ChatRequest) -> ChatResponse:
        """Return a normalized response or raise a typed ProviderError."""
