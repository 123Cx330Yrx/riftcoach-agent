"""Body-free Provider error details shared by runtime and evaluation layers."""

from __future__ import annotations

from types import MappingProxyType

from .errors import ProviderError


_SAFE_PROVIDER_ERROR_CODES = MappingProxyType(
    {
        "deepseek": frozenset(
            {
                "authentication_failed",
                "connection_failed",
                "incomplete_chat_response",
                "invalid_chat_response",
                "invalid_finish_reason",
                "invalid_tool_call_request",
                "invalid_tool_call_response",
                "invalid_tool_name",
                "provider_usage_unavailable",
                "rate_limited",
                "request_rejected",
                "resolved_model_mismatch",
                "service_unavailable",
                "timeout",
                "tool_name_alias_conflict",
                "unexpected_reasoning_content",
                "unexpected_sdk_error",
                "unknown_tool_name",
            }
        ),
        "zhipu": frozenset(
            {
                "authentication_failed",
                "connection_failed",
                "invalid_chat_response",
                "invalid_tool_call_request",
                "invalid_tool_call_response",
                "invalid_tool_name",
                "provider_usage_unavailable",
                "rate_limited",
                "request_rejected",
                "service_unavailable",
                "timeout",
                "tool_name_alias_conflict",
                "unexpected_reasoning_content",
                "unexpected_sdk_error",
                "unknown_tool_name",
                "unsupported_parallel_tool_calls",
            }
        ),
        "orcarouter": frozenset(
            {
                "authentication_failed",
                "connection_failed",
                "incomplete_chat_response",
                "invalid_chat_response",
                "invalid_finish_reason",
                "invalid_tool_call_request",
                "invalid_tool_call_response",
                "invalid_tool_name",
                "provider_usage_unavailable",
                "rate_limited",
                "request_rejected",
                "service_unavailable",
                "timeout",
                "tool_name_alias_conflict",
                "unexpected_sdk_error",
                "unknown_tool_name",
            }
        ),
    }
)


def is_safe_provider_error_code(provider_id: str, code: str) -> bool:
    """Return whether an adapter-owned constant may cross a public boundary."""

    return (
        isinstance(provider_id, str)
        and isinstance(code, str)
        and code in _SAFE_PROVIDER_ERROR_CODES.get(provider_id, frozenset())
    )


def safe_provider_error_code(error: ProviderError) -> str | None:
    """Project an allowlisted detail or ``None`` without forwarding raw text."""

    if not isinstance(error, ProviderError):
        raise TypeError("error must be a ProviderError")
    if is_safe_provider_error_code(error.provider, error.code):
        return error.code
    return None


__all__ = ["is_safe_provider_error_code", "safe_provider_error_code"]
