from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI

from .errors import ProviderConfigurationError
from .zhipu import ZhipuProvider


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


def create_zhipu_provider(
    settings: ZhipuSettings,
    *,
    client_factory: Callable[..., Any] = OpenAI,
) -> ZhipuProvider:
    client = client_factory(
        api_key=settings.api_key,
        base_url=settings.base_url,
        timeout=settings.default_timeout_s,
    )
    return ZhipuProvider(client=client, model=settings.model)
