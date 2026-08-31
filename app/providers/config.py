from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI

from app.model_runtime import resolve_model_runtime_profile

from .errors import ProviderConfigurationError
from .deepseek import (
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    DeepSeekProvider,
)
from .protocol import LLMProvider
from .registry import ProviderRegistry
from .zhipu import ZhipuProvider
from .zhipu_profiles import (
    ZHIPU_STANDARD_BASE_URL,
    ZhipuThinkingProfile,
    resolve_zhipu_thinking_profile,
)


@dataclass(frozen=True)
class ZhipuSettings:
    api_key: str = field(repr=False)
    base_url: str
    model: str
    default_timeout_s: float = 30.0

    def __post_init__(self) -> None:
        for name, value in (
            ("api_key", self.api_key),
            ("base_url", self.base_url),
            ("model", self.model),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ProviderConfigurationError(
                    provider="zhipu",
                    code=f"missing_{name}",
                )
        if (
            isinstance(self.default_timeout_s, bool)
            or not isinstance(self.default_timeout_s, (int, float))
            or self.default_timeout_s <= 0
        ):
            raise ProviderConfigurationError(
                provider="zhipu",
                code="invalid_default_timeout",
            )

    @property
    def thinking_profile(self) -> ZhipuThinkingProfile:
        """Return the immutable profile selected by the exact model ID."""

        try:
            return resolve_zhipu_thinking_profile(self.model)
        except ValueError as error:
            raise ProviderConfigurationError(
                provider="zhipu",
                code="invalid_model",
            ) from error

    @property
    def thinking_profile_id(self) -> str:
        """Expose a stable, auditable profile identity."""

        return self.thinking_profile.profile_id


@dataclass(frozen=True)
class DeepSeekSettings:
    api_key: str = field(repr=False)
    base_url: str = DEEPSEEK_BASE_URL
    model: str = DEEPSEEK_MODEL
    default_timeout_s: float = 30.0
    sdk_max_retries: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.api_key, str) or not self.api_key.strip():
            raise ProviderConfigurationError(
                provider="deepseek",
                code="missing_api_key",
            )
        if self.base_url != DEEPSEEK_BASE_URL:
            raise ProviderConfigurationError(
                provider="deepseek",
                code="invalid_base_url",
            )
        if self.model != DEEPSEEK_MODEL:
            raise ProviderConfigurationError(
                provider="deepseek",
                code="invalid_model",
            )
        if (
            isinstance(self.default_timeout_s, bool)
            or not isinstance(self.default_timeout_s, (int, float))
            or self.default_timeout_s <= 0
        ):
            raise ProviderConfigurationError(
                provider="deepseek",
                code="invalid_default_timeout",
            )
        if self.sdk_max_retries != 0:
            raise ProviderConfigurationError(
                provider="deepseek",
                code="invalid_sdk_retries",
            )


@dataclass(frozen=True)
class ProviderRegistrySettings:
    default_provider_id: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.default_provider_id, str)
            or not self.default_provider_id.strip()
        ):
            raise ProviderConfigurationError(
                provider="registry",
                code="missing_default_provider_id",
            )


def load_zhipu_settings(
    environ: Mapping[str, str] | None = None,
) -> ZhipuSettings:
    values = os.environ if environ is None else environ
    provider = values.get("LLM_PROVIDER", "zhipu").strip().lower()
    if provider != "zhipu":
        raise ProviderConfigurationError(
            provider="zhipu",
            code="provider_mismatch",
        )

    timeout_text = values.get("LLM_TIMEOUT_SECONDS", "30")
    try:
        timeout_s = float(timeout_text)
    except (TypeError, ValueError):
        raise ProviderConfigurationError(
            provider="zhipu",
            code="invalid_default_timeout",
        ) from None

    return ZhipuSettings(
        api_key=values.get("LLM_API_KEY", ""),
        base_url=values.get("LLM_BASE_URL", ""),
        model=values.get("LLM_MODEL", ""),
        default_timeout_s=timeout_s,
    )


def load_provider_registry_settings(
    environ: Mapping[str, str] | None = None,
) -> ProviderRegistrySettings:
    values = os.environ if environ is None else environ
    default_provider_id = values.get(
        "LLM_DEFAULT_PROVIDER",
        values.get("LLM_PROVIDER", "zhipu"),
    )
    return ProviderRegistrySettings(default_provider_id=default_provider_id)


def load_deepseek_settings(
    environ: Mapping[str, str] | None = None,
) -> DeepSeekSettings:
    values = os.environ if environ is None else environ
    timeout_text = values.get("DEEPSEEK_TIMEOUT_SECONDS", "30")
    retries_text = values.get("DEEPSEEK_MAX_RETRIES", "0")
    try:
        timeout_s = float(timeout_text)
        sdk_max_retries = int(retries_text)
    except (TypeError, ValueError):
        raise ProviderConfigurationError(
            provider="deepseek",
            code="invalid_numeric_configuration",
        ) from None
    return DeepSeekSettings(
        api_key=values.get("DEEPSEEK_API_KEY", ""),
        base_url=values.get("DEEPSEEK_BASE_URL", DEEPSEEK_BASE_URL),
        model=values.get("DEEPSEEK_MODEL", DEEPSEEK_MODEL),
        default_timeout_s=timeout_s,
        sdk_max_retries=sdk_max_retries,
    )


def create_zhipu_provider(
    settings: ZhipuSettings,
    *,
    client_factory: Callable[..., Any] = OpenAI,
) -> ZhipuProvider:
    runtime_profile = resolve_model_runtime_profile("zhipu", settings.model)
    if (
        runtime_profile is not None
        and settings.base_url.rstrip("/")
        != ZHIPU_STANDARD_BASE_URL.rstrip("/")
    ):
        raise ProviderConfigurationError(
            provider="zhipu",
            code="invalid_base_url_for_runtime_profile",
        )
    client = client_factory(
        api_key=settings.api_key,
        base_url=settings.base_url,
        timeout=(
            runtime_profile.transport_timeout_s
            if runtime_profile is not None
            else settings.default_timeout_s
        ),
        max_retries=0,
    )
    return ZhipuProvider(
        client=client,
        model=settings.model,
        profile=settings.thinking_profile,
        runtime_profile=runtime_profile,
    )


def create_deepseek_provider(
    settings: DeepSeekSettings,
    *,
    client_factory: Callable[..., Any] = OpenAI,
) -> DeepSeekProvider:
    client = client_factory(
        api_key=settings.api_key,
        base_url=settings.base_url,
        timeout=settings.default_timeout_s,
        max_retries=settings.sdk_max_retries,
    )
    return DeepSeekProvider(client=client, model=settings.model)


def create_provider_registry(
    providers: Mapping[str, LLMProvider],
    settings: ProviderRegistrySettings,
) -> ProviderRegistry:
    registry = ProviderRegistry()
    for provider_id, provider in providers.items():
        registry.register(provider_id, provider)
    registry.set_default(settings.default_provider_id)
    return registry
