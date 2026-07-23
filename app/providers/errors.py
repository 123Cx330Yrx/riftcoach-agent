from __future__ import annotations


class ProviderError(RuntimeError):
    """Safe provider failure without credentials or raw prompt content."""

    retryable = False

    def __init__(self, *, provider: str, code: str) -> None:
        if not provider.strip():
            raise ValueError("provider must not be empty.")
        if not code.strip():
            raise ValueError("code must not be empty.")
        self.provider = provider
        self.code = code
        super().__init__(
            f"{type(self).__name__}(provider={provider!r}, code={code!r})"
        )


class ProviderConfigurationError(ProviderError):
    pass


class ProviderAuthenticationError(ProviderError):
    pass


class ProviderRateLimitError(ProviderError):
    retryable = True


class ProviderTimeoutError(ProviderError):
    retryable = True


class ProviderUnavailableError(ProviderError):
    retryable = True


class ProviderResponseError(ProviderError):
    pass
