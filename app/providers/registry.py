from __future__ import annotations

import re
from dataclasses import dataclass

from .capabilities import (
    CapabilityNegotiation,
    ProviderCapabilities,
    negotiate_capabilities,
    require_provider_capabilities,
)
from .errors import ProviderRegistryError
from .models import ChatRequest
from .protocol import LLMProvider


_PROVIDER_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


def _validate_provider_id(provider_id: str) -> str:
    if not isinstance(provider_id, str) or not _PROVIDER_ID_PATTERN.fullmatch(
        provider_id
    ):
        raise ValueError(
            "provider_id must use lowercase letters, digits, '.', '_' or '-'."
        )
    return provider_id


@dataclass(frozen=True)
class ProviderDescriptor:
    """Safe, immutable metadata exposed by the registry."""

    provider_id: str
    provider_name: str
    model_name: str
    capabilities: ProviderCapabilities
    is_default: bool


@dataclass(frozen=True)
class ProviderSelection:
    """One explicit provider choice plus its request capability decision."""

    provider_id: str
    provider: LLMProvider
    negotiation: CapabilityNegotiation


class ProviderRegistry:
    """Explicit directory of configured provider adapter instances."""

    def __init__(self) -> None:
        self._providers: dict[str, LLMProvider] = {}
        self._default_provider_id: str | None = None

    @property
    def default_provider_id(self) -> str | None:
        return self._default_provider_id

    def register(self, provider_id: str, provider: LLMProvider) -> None:
        provider_id = _validate_provider_id(provider_id)
        if (
            not isinstance(provider, LLMProvider)
            or not isinstance(provider.provider_name, str)
            or not provider.provider_name.strip()
            or not isinstance(provider.model_name, str)
            or not provider.model_name.strip()
            or not isinstance(provider.capabilities, ProviderCapabilities)
        ):
            raise ProviderRegistryError(
                provider="registry",
                code="invalid_provider_contract",
            )
        if provider_id in self._providers:
            raise ProviderRegistryError(
                provider="registry",
                code="duplicate_provider_id",
            )
        self._providers[provider_id] = provider

    def set_default(self, provider_id: str) -> None:
        provider_id = _validate_provider_id(provider_id)
        if provider_id not in self._providers:
            raise ProviderRegistryError(
                provider="registry",
                code="unknown_provider_id",
            )
        self._default_provider_id = provider_id

    def resolve(self, provider_id: str | None = None) -> LLMProvider:
        resolved_id = (
            self._default_provider_id if provider_id is None else provider_id
        )
        if resolved_id is None:
            raise ProviderRegistryError(
                provider="registry",
                code="default_provider_not_configured",
            )
        resolved_id = _validate_provider_id(resolved_id)
        try:
            return self._providers[resolved_id]
        except KeyError:
            raise ProviderRegistryError(
                provider="registry",
                code="unknown_provider_id",
            ) from None

    def select(
        self,
        request: ChatRequest,
        provider_id: str | None = None,
    ) -> ProviderSelection:
        resolved_id = (
            self._default_provider_id if provider_id is None else provider_id
        )
        if resolved_id is None:
            raise ProviderRegistryError(
                provider="registry",
                code="default_provider_not_configured",
            )
        provider = self.resolve(resolved_id)
        negotiation = require_provider_capabilities(
            provider_name=provider.provider_name,
            capabilities=provider.capabilities,
            request=request,
        )
        return ProviderSelection(
            provider_id=resolved_id,
            provider=provider,
            negotiation=negotiation,
        )

    def compatible_provider_ids(self, request: ChatRequest) -> tuple[str, ...]:
        compatible = (
            provider_id
            for provider_id, provider in self._providers.items()
            if negotiate_capabilities(provider.capabilities, request).compatible
        )
        return tuple(sorted(compatible))

    def descriptors(self) -> tuple[ProviderDescriptor, ...]:
        return tuple(
            ProviderDescriptor(
                provider_id=provider_id,
                provider_name=provider.provider_name,
                model_name=provider.model_name,
                capabilities=provider.capabilities,
                is_default=provider_id == self._default_provider_id,
            )
            for provider_id, provider in sorted(self._providers.items())
        )
