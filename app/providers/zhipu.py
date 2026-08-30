from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

import openai

from .capabilities import ProviderCapabilities, require_provider_capabilities
from .errors import (
    ProviderAuthenticationError,
    ProviderCapabilityError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from .models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    MessageRole,
    TokenUsage,
    ToolCall,
    ToolChoiceMode,
    ToolSpec,
)
from .zhipu_profiles import (
    ZhipuThinkingProfile,
    resolve_zhipu_thinking_profile,
    validate_zhipu_profile_for_model,
)


_PROVIDER_TOOL_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


class ZhipuProvider:
    """Translate RiftCoach chat contracts to Zhipu's OpenAI-compatible API."""

    provider_name = "zhipu"
    capabilities = ProviderCapabilities(
        text_chat=True,
        tool_calling=True,
        structured_output=True,
    )

    def __init__(
        self,
        *,
        client: Any,
        model: str,
        profile: ZhipuThinkingProfile | None = None,
    ) -> None:
        if client is None:
            raise ValueError("client is required.")
        if not isinstance(model, str) or not model.strip():
            raise ValueError("model must not be empty.")
        normalized_model = model.strip()
        selected_profile = profile or resolve_zhipu_thinking_profile(
            normalized_model
        )
        try:
            selected_profile = validate_zhipu_profile_for_model(
                normalized_model,
                selected_profile,
            )
        except ValueError as error:
            raise ValueError(str(error)) from error
        self._client = client
        self.model_name = normalized_model
        self._thinking_profile = selected_profile

    @property
    def profile(self) -> ZhipuThinkingProfile:
        """The immutable model-specific thinking profile used for requests."""

        return self._thinking_profile

    @property
    def thinking_profile_id(self) -> str:
        """Stable profile identity for audit records and diagnostics."""

        return self._thinking_profile.profile_id

    def chat(self, request: ChatRequest) -> ChatResponse:
        require_provider_capabilities(
            provider_name=self.provider_name,
            capabilities=self.capabilities,
            request=request,
        )
        if request.tool_choice is ToolChoiceMode.REQUIRED:
            raise ProviderCapabilityError(
                provider=self.provider_name,
                missing_capabilities=("required_tool_choice",),
            )
        if (
            request.response_contract is not None
            and request.tools
            and request.tool_choice is ToolChoiceMode.AUTO
        ):
            raise ProviderCapabilityError(
                provider=self.provider_name,
                missing_capabilities=("structured_tool_combination",),
            )

        aliases = _ToolAliasMap.from_tools(request.tools)
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": [
                self._encode_message(message, aliases)
                for message in request.messages
            ],
            "temperature": request.temperature,
            "timeout": request.timeout_s,
            "extra_body": self._thinking_profile.extra_body(),
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.tools and request.tool_choice is ToolChoiceMode.AUTO:
            payload["tools"] = [
                self._encode_tool(tool, aliases) for tool in request.tools
            ]
            payload["tool_choice"] = "auto"
        if request.response_contract is not None:
            payload["response_format"] = {"type": "json_object"}

        try:
            raw_response = self._client.chat.completions.create(**payload)
        except Exception as error:
            raise self._translate_error(error) from None

        try:
            choice = raw_response.choices[0]
            message = choice.message
            raw_content = getattr(message, "content", None)
            if raw_content is not None and not isinstance(raw_content, str):
                raise ProviderResponseError(
                    provider=self.provider_name,
                    code="invalid_chat_response",
                )
            content = (
                raw_content.strip()
                if isinstance(raw_content, str) and raw_content.strip()
                else None
            )
            tool_calls = self._decode_tool_calls(
                getattr(message, "tool_calls", None),
                aliases,
            )
            self._validate_reasoning_content(
                getattr(message, "reasoning_content", None),
                has_tool_calls=bool(tool_calls),
            )

            model = getattr(raw_response, "model", None) or self.model_name
            finish_reason = getattr(choice, "finish_reason", None)
            if bool(tool_calls) != (finish_reason == "tool_calls"):
                raise ProviderResponseError(
                    provider=self.provider_name,
                    code="invalid_tool_call_response",
                )
            request_id = getattr(raw_response, "id", None)
            usage = self._normalize_usage(getattr(raw_response, "usage", None))
            return ChatResponse(
                content=content,
                model=model,
                provider=self.provider_name,
                tool_calls=tool_calls,
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

    def _validate_reasoning_content(
        self,
        reasoning_content: Any,
        *,
        has_tool_calls: bool,
    ) -> None:
        """Validate vendor reasoning without exposing it in neutral contracts."""

        if reasoning_content is None:
            return
        if not isinstance(reasoning_content, str):
            raise ProviderResponseError(
                provider=self.provider_name,
                code="unexpected_reasoning_content",
            )
        if not reasoning_content.strip():
            return
        if not self._thinking_profile.accepts_reasoning_content:
            raise ProviderResponseError(
                provider=self.provider_name,
                code="unexpected_reasoning_content",
            )
        # A tool round would need the opaque vendor reasoning state on the
        # next request.  The provider-neutral message contract intentionally
        # has no such field, so fail closed until a separate contract is
        # designed and admitted.
        if has_tool_calls:
            raise ProviderResponseError(
                provider=self.provider_name,
                code="unexpected_reasoning_content",
            )

    @staticmethod
    def _encode_message(
        message: ChatMessage,
        aliases: _ToolAliasMap,
    ) -> dict[str, Any]:
        encoded: dict[str, Any] = {
            "role": message.role.value,
            "content": message.content,
        }
        if message.role is MessageRole.ASSISTANT and message.tool_calls:
            if len(message.tool_calls) > 1:
                raise ProviderResponseError(
                    provider="zhipu",
                    code="unsupported_parallel_tool_calls",
                )
            try:
                encoded["tool_calls"] = [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": aliases.encode(call.name),
                            "arguments": json.dumps(
                                _copy_json(call.arguments),
                                allow_nan=False,
                                ensure_ascii=False,
                                separators=(",", ":"),
                                sort_keys=True,
                            ),
                        },
                    }
                    for call in message.tool_calls
                ]
            except (TypeError, ValueError):
                raise ProviderResponseError(
                    provider="zhipu",
                    code="invalid_tool_call_request",
                ) from None
        elif message.role is MessageRole.TOOL:
            encoded["tool_call_id"] = message.tool_call_id
        return encoded

    @staticmethod
    def _encode_tool(
        tool: ToolSpec,
        aliases: _ToolAliasMap,
    ) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": aliases.encode(tool.name),
                "description": tool.description,
                "parameters": _copy_json(tool.input_schema),
            },
        }

    def _decode_tool_calls(
        self,
        raw_tool_calls: Any,
        aliases: _ToolAliasMap,
    ) -> tuple[ToolCall, ...]:
        if raw_tool_calls is None:
            return ()
        try:
            values = list(raw_tool_calls)
        except TypeError:
            raise ProviderResponseError(
                provider=self.provider_name,
                code="invalid_tool_call_response",
            ) from None

        decoded: list[ToolCall] = []
        seen_ids: set[str] = set()
        for raw_call in values:
            call_id = getattr(raw_call, "id", None)
            call_type = getattr(raw_call, "type", None)
            function = getattr(raw_call, "function", None)
            provider_name = getattr(function, "name", None)
            raw_arguments = getattr(function, "arguments", None)
            if (
                not isinstance(call_id, str)
                or not call_id.strip()
                or call_type != "function"
                or not isinstance(provider_name, str)
                or not provider_name.strip()
                or not isinstance(raw_arguments, str)
            ):
                raise ProviderResponseError(
                    provider=self.provider_name,
                    code="invalid_tool_call_response",
                )
            normalized_call_id = call_id.strip()
            if normalized_call_id in seen_ids:
                raise ProviderResponseError(
                    provider=self.provider_name,
                    code="invalid_tool_call_response",
                )
            try:
                arguments = json.loads(
                    raw_arguments,
                    object_pairs_hook=_unique_json_object,
                    parse_constant=_reject_json_constant,
                )
            except (TypeError, ValueError):
                raise ProviderResponseError(
                    provider=self.provider_name,
                    code="invalid_tool_call_response",
                ) from None
            if not isinstance(arguments, dict):
                raise ProviderResponseError(
                    provider=self.provider_name,
                    code="invalid_tool_call_response",
                )
            try:
                internal_name = aliases.decode(provider_name)
                decoded_call = ToolCall(
                    id=normalized_call_id,
                    name=internal_name,
                    arguments=arguments,
                )
            except (KeyError, ValueError):
                raise ProviderResponseError(
                    provider=self.provider_name,
                    code="invalid_tool_call_response",
                ) from None
            seen_ids.add(normalized_call_id)
            decoded.append(decoded_call)
        if len(decoded) > 1:
            raise ProviderResponseError(
                provider=self.provider_name,
                code="unsupported_parallel_tool_calls",
            )
        return tuple(decoded)

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
            raise ProviderResponseError(
                provider="zhipu",
                code="provider_usage_unavailable",
            )
        input_tokens = getattr(raw_usage, "prompt_tokens", None)
        output_tokens = getattr(raw_usage, "completion_tokens", None)
        for value in (input_tokens, output_tokens):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ProviderResponseError(
                    provider="zhipu",
                    code="provider_usage_unavailable",
                )
        return TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )


class _ToolAliasMap:
    """One request-local, reversible mapping for provider-safe tool names."""

    def __init__(
        self,
        *,
        internal_to_provider: Mapping[str, str],
        provider_to_internal: Mapping[str, str],
    ) -> None:
        self._internal_to_provider = dict(internal_to_provider)
        self._provider_to_internal = dict(provider_to_internal)

    @classmethod
    def from_tools(cls, tools: tuple[ToolSpec, ...]) -> _ToolAliasMap:
        internal_to_provider: dict[str, str] = {}
        provider_to_internal: dict[str, str] = {}
        for tool in tools:
            provider_name = _provider_safe_tool_name(tool.name)
            existing = provider_to_internal.get(provider_name)
            if existing is not None and existing != tool.name:
                raise ProviderResponseError(
                    provider="zhipu",
                    code="tool_name_alias_conflict",
                )
            internal_to_provider[tool.name] = provider_name
            provider_to_internal[provider_name] = tool.name
        return cls(
            internal_to_provider=internal_to_provider,
            provider_to_internal=provider_to_internal,
        )

    def encode(self, internal_name: str) -> str:
        try:
            return self._internal_to_provider[internal_name]
        except KeyError:
            raise ProviderResponseError(
                provider="zhipu",
                code="unknown_tool_name",
            ) from None

    def decode(self, provider_name: str) -> str:
        return self._provider_to_internal[provider_name]


def _provider_safe_tool_name(internal_name: str) -> str:
    if _PROVIDER_TOOL_NAME_PATTERN.fullmatch(internal_name):
        return internal_name
    encoded = re.sub(r"[^A-Za-z0-9_-]", "_", internal_name)
    if not encoded or not _PROVIDER_TOOL_NAME_PATTERN.fullmatch(encoded):
        raise ProviderResponseError(
            provider="zhipu",
            code="invalid_tool_name",
        )
    return encoded


def _copy_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _copy_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_copy_json(item) for item in value]
    if isinstance(value, list):
        return [_copy_json(item) for item in value]
    return value


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"invalid JSON constant: {value}")


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON object key")
        value[key] = item
    return value
