from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import openai

from app.model_runtime import (
    ModelRuntimeProfile,
    require_registered_model_runtime_profile,
)

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
    validate_zhipu_candidate_profile_for_model,
    validate_zhipu_profile_for_model,
)

if TYPE_CHECKING:
    from .zhipu_stream_adapter import ZhipuStreamAdapter


_PROVIDER_TOOL_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
_TERMINAL_FINISH_REASONS = frozenset({"stop", "tool_calls"})
_INCOMPLETE_FINISH_REASONS = frozenset(
    {"length", "content_filter", "insufficient_system_resource"}
)
_CANDIDATE_PROFILE_TOKEN = object()


@dataclass(frozen=True)
class ZhipuStreamResult:
    """One fully assembled provider stream plus body-free diagnostics.

    RiftCoach's provider-neutral runtime remains synchronous.  This opt-in
    adapter surface exists so transport streaming and streamed tool calls can
    be verified without pretending that the product already exposes live
    token streaming end to end.
    """

    response: ChatResponse
    chunk_count: int
    content_chunk_count: int
    reasoning_chunk_count: int
    tool_call_chunk_count: int


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
        runtime_profile: ModelRuntimeProfile | None = None,
        _profile_scope: object | None = None,
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
            if _profile_scope is _CANDIDATE_PROFILE_TOKEN:
                if runtime_profile is not None:
                    raise ValueError(
                        "candidate profile cannot bind a product runtime profile"
                    )
                selected_profile = validate_zhipu_candidate_profile_for_model(
                    normalized_model,
                    selected_profile,
                )
            elif _profile_scope is not None:
                raise ValueError("unknown Zhipu profile scope")
            else:
                selected_profile = validate_zhipu_profile_for_model(
                    normalized_model,
                    selected_profile,
                )
        except ValueError as error:
            raise ValueError(str(error)) from error
        if runtime_profile is not None:
            runtime_profile = require_registered_model_runtime_profile(
                runtime_profile
            )
            if not runtime_profile.matches(self.provider_name, normalized_model):
                raise ValueError(
                    "runtime_profile does not match the Zhipu model"
                )
        self._client = client
        self.model_name = normalized_model
        self._thinking_profile = selected_profile
        self._runtime_profile = runtime_profile

    @classmethod
    def from_candidate_profile(
        cls,
        *,
        client: Any,
        model: str,
        profile: ZhipuThinkingProfile,
    ) -> "ZhipuProvider":
        """Construct an explicitly selected, candidate-only provider profile.

        This escape hatch is deliberately separate from the normal
        constructor and cannot attach a product ``ModelRuntimeProfile``.  It
        exists for isolated evaluation probes; environment/model metadata
        never selects it automatically.
        """

        return cls(
            client=client,
            model=model,
            profile=profile,
            _profile_scope=_CANDIDATE_PROFILE_TOKEN,
        )

    @property
    def profile(self) -> ZhipuThinkingProfile:
        """The immutable model-specific thinking profile used for requests."""

        return self._thinking_profile

    @property
    def thinking_profile_id(self) -> str:
        """Stable profile identity for audit records and diagnostics."""

        return self._thinking_profile.profile_id

    @property
    def runtime_profile(self) -> ModelRuntimeProfile | None:
        """The optional product execution profile bound to this Provider."""

        return self._runtime_profile

    def stream_adapter(self, *, tool_stream: bool = False) -> ZhipuStreamAdapter:
        """Return an explicit candidate-only neutral stream adapter.

        The returned object is deliberately separate from ``LLMProvider`` and
        does not change this provider's ``capabilities.streaming`` flag.  A
        caller must opt in for every adapter instance; the normal synchronous
        ``chat``/``chat_stream`` paths and the AgentLoop remain unchanged.
        """

        if not isinstance(tool_stream, bool):
            raise ValueError("tool_stream must be a boolean.")
        # Local import keeps the provider-neutral adapter module independent
        # from this implementation and avoids an import cycle.
        from .zhipu_stream_adapter import ZhipuStreamAdapter

        return ZhipuStreamAdapter(
            self,
            tool_stream=tool_stream,
            default_max_output_tokens=(
                self._runtime_profile.max_output_tokens
                if self._runtime_profile is not None
                else None
            ),
        )

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
        runtime_profile = self._runtime_profile
        effective_temperature = (
            runtime_profile.temperature
            if runtime_profile is not None
            else request.temperature
        )
        effective_top_p = (
            runtime_profile.top_p
            if runtime_profile is not None
            else request.top_p
        )
        effective_max_tokens = request.max_tokens
        effective_timeout = request.timeout_s
        if runtime_profile is not None:
            effective_max_tokens = (
                runtime_profile.max_output_tokens
                if effective_max_tokens is None
                else min(effective_max_tokens, runtime_profile.max_output_tokens)
            )
            effective_timeout = min(
                effective_timeout,
                runtime_profile.llm_tool_timeout_s,
            )
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": [
                self._encode_message(message, aliases)
                for message in request.messages
            ],
            "temperature": effective_temperature,
            "timeout": effective_timeout,
            "stream": False,
            "extra_body": self._thinking_profile.extra_body(),
        }
        if effective_top_p is not None:
            payload["top_p"] = effective_top_p
        if effective_max_tokens is not None:
            payload["max_tokens"] = effective_max_tokens
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
            reasoning_content = self._validate_reasoning_content(
                getattr(message, "reasoning_content", None),
                has_tool_calls=bool(tool_calls),
            )

            model = getattr(raw_response, "model", None) or self.model_name
            finish_reason = getattr(choice, "finish_reason", None)
            self._validate_finish_reason(finish_reason)
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
                reasoning_content=reasoning_content,
            )
        except ProviderResponseError:
            raise
        except Exception:
            raise ProviderResponseError(
                provider=self.provider_name,
                code="invalid_chat_response",
            ) from None

    def chat_stream(
        self,
        request: ChatRequest,
        *,
        tool_stream: bool = False,
    ) -> ZhipuStreamResult:
        """Consume one official SSE response and normalize the assembled turn.

        The method deliberately returns a complete response instead of leaking
        vendor chunks into the provider-neutral contract.  It is currently an
        adapter/evaluation surface; ``capabilities.streaming`` stays false
        until live chunks are wired through the whole product runtime.
        """

        if not isinstance(tool_stream, bool):
            raise ValueError("tool_stream must be a boolean.")
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
        if tool_stream and not request.tools:
            raise ValueError("tool_stream requires at least one tool.")

        aliases = _ToolAliasMap.from_tools(request.tools)
        extra_body = self._thinking_profile.extra_body()
        if tool_stream:
            extra_body["tool_stream"] = True
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": [
                self._encode_message(message, aliases)
                for message in request.messages
            ],
            "temperature": request.temperature,
            "timeout": request.timeout_s,
            "stream": True,
            "extra_body": extra_body,
        }
        if request.top_p is not None:
            payload["top_p"] = request.top_p
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
            raw_stream = self._client.chat.completions.create(**payload)
            return self._consume_stream(raw_stream, aliases)
        except ProviderResponseError:
            raise
        except Exception as error:
            raise self._translate_error(error) from None

    def _open_stream_for_adapter(
        self,
        request: ChatRequest,
        *,
        tool_stream: bool,
        include_usage_tail: bool = False,
    ) -> tuple[Any, Callable[[str], str]]:
        """Open one raw stream for the explicit neutral adapter seam.

        This method is intentionally private.  It centralizes request
        validation and applies a bound runtime profile when one is present,
        while leaving the historical ``chat_stream`` payload behavior intact.
        The adapter receives only a request-local tool-name decoder; raw IDs,
        SDK objects and payloads never enter the neutral trace.
        """

        if not isinstance(request, ChatRequest):
            raise TypeError("request must be a ChatRequest")
        if not isinstance(tool_stream, bool):
            raise ValueError("tool_stream must be a boolean.")
        if not isinstance(include_usage_tail, bool):
            raise ValueError("include_usage_tail must be a boolean.")
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
        if tool_stream and not request.tools:
            raise ValueError("tool_stream requires at least one tool.")

        aliases = _ToolAliasMap.from_tools(request.tools)
        runtime_profile = self._runtime_profile
        effective_temperature = (
            runtime_profile.temperature
            if runtime_profile is not None
            else request.temperature
        )
        effective_top_p = (
            runtime_profile.top_p
            if runtime_profile is not None
            else request.top_p
        )
        effective_max_tokens = request.max_tokens
        effective_timeout = request.timeout_s
        if runtime_profile is not None:
            effective_max_tokens = (
                runtime_profile.max_output_tokens
                if effective_max_tokens is None
                else min(effective_max_tokens, runtime_profile.max_output_tokens)
            )
            effective_timeout = min(
                effective_timeout,
                runtime_profile.llm_tool_timeout_s,
            )

        extra_body = self._thinking_profile.extra_body()
        if tool_stream:
            extra_body["tool_stream"] = True
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": [
                self._encode_message(message, aliases)
                for message in request.messages
            ],
            "temperature": effective_temperature,
            "timeout": effective_timeout,
            "stream": True,
            "extra_body": extra_body,
        }
        if effective_top_p is not None:
            payload["top_p"] = effective_top_p
        if effective_max_tokens is not None:
            payload["max_tokens"] = effective_max_tokens
        if include_usage_tail:
            # OpenAI-compatible providers emit Usage in a final empty-choice
            # frame only when explicitly requested.  Keep this opt-in so the
            # historical provider and product paths retain their payload.
            payload["stream_options"] = {"include_usage": True}
        if request.tools and request.tool_choice is ToolChoiceMode.AUTO:
            payload["tools"] = [
                self._encode_tool(tool, aliases) for tool in request.tools
            ]
            payload["tool_choice"] = "auto"
        if request.response_contract is not None:
            payload["response_format"] = {"type": "json_object"}

        try:
            raw_stream = self._client.chat.completions.create(**payload)
        except ProviderResponseError:
            raise
        except Exception as error:
            raise self._translate_error(error) from None
        return raw_stream, aliases.decode

    def _validate_stream_response_for_adapter(
        self,
        response: ChatResponse,
    ) -> None:
        """Apply the model's reasoning replay rules to a neutral response."""

        if not isinstance(response, ChatResponse):
            raise ProviderResponseError(
                provider=self.provider_name,
                code="invalid_stream_response",
            )
        self._validate_reasoning_content(
            response.reasoning_content,
            has_tool_calls=bool(response.tool_calls),
        )

    def _consume_stream(
        self,
        raw_stream: Any,
        aliases: _ToolAliasMap,
    ) -> ZhipuStreamResult:
        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        tool_fragments: dict[int, dict[str, Any]] = {}
        usage: TokenUsage | None = None
        resolved_model: str | None = None
        request_id: str | None = None
        finish_reason: str | None = None
        chunk_count = 0
        content_chunk_count = 0
        reasoning_chunk_count = 0
        tool_call_chunk_count = 0

        for chunk in raw_stream:
            chunk_count += 1
            raw_model = getattr(chunk, "model", None)
            if raw_model is not None:
                if not isinstance(raw_model, str) or not raw_model.strip():
                    raise ProviderResponseError(
                        provider=self.provider_name,
                        code="invalid_stream_response",
                    )
                if resolved_model is not None and resolved_model != raw_model:
                    raise ProviderResponseError(
                        provider=self.provider_name,
                        code="invalid_stream_response",
                    )
                resolved_model = raw_model
            raw_request_id = getattr(chunk, "id", None)
            if raw_request_id is not None:
                if not isinstance(raw_request_id, str) or not raw_request_id.strip():
                    raise ProviderResponseError(
                        provider=self.provider_name,
                        code="invalid_stream_response",
                    )
                if request_id is not None and request_id != raw_request_id:
                    raise ProviderResponseError(
                        provider=self.provider_name,
                        code="invalid_stream_response",
                    )
                request_id = raw_request_id

            raw_usage = getattr(chunk, "usage", None)
            if raw_usage is not None:
                usage = self._normalize_usage(raw_usage)
            choices = getattr(chunk, "choices", None)
            if not isinstance(choices, (list, tuple)):
                raise ProviderResponseError(
                    provider=self.provider_name,
                    code="invalid_stream_response",
                )
            if not choices:
                continue
            if len(choices) != 1:
                raise ProviderResponseError(
                    provider=self.provider_name,
                    code="invalid_stream_response",
                )
            choice = choices[0]
            raw_finish_reason = getattr(choice, "finish_reason", None)
            if raw_finish_reason is not None:
                if (
                    finish_reason is not None
                    and finish_reason != raw_finish_reason
                ):
                    raise ProviderResponseError(
                        provider=self.provider_name,
                        code="invalid_stream_response",
                    )
                finish_reason = raw_finish_reason
            delta = getattr(choice, "delta", None)
            if delta is None:
                raise ProviderResponseError(
                    provider=self.provider_name,
                    code="invalid_stream_response",
                )
            raw_content = getattr(delta, "content", None)
            if raw_content is not None:
                if not isinstance(raw_content, str):
                    raise ProviderResponseError(
                        provider=self.provider_name,
                        code="invalid_stream_response",
                    )
                if raw_content:
                    content_parts.append(raw_content)
                    content_chunk_count += 1
            raw_reasoning = getattr(delta, "reasoning_content", None)
            if raw_reasoning is not None:
                if not isinstance(raw_reasoning, str):
                    raise ProviderResponseError(
                        provider=self.provider_name,
                        code="unexpected_reasoning_content",
                    )
                if raw_reasoning:
                    reasoning_parts.append(raw_reasoning)
                    reasoning_chunk_count += 1
            raw_tool_calls = getattr(delta, "tool_calls", None)
            if raw_tool_calls:
                try:
                    calls = list(raw_tool_calls)
                except TypeError:
                    raise ProviderResponseError(
                        provider=self.provider_name,
                        code="invalid_stream_tool_call",
                    ) from None
                for raw_call in calls:
                    self._append_stream_tool_fragment(
                        tool_fragments,
                        raw_call,
                    )
                    tool_call_chunk_count += 1

        if chunk_count == 0 or usage is None:
            raise ProviderResponseError(
                provider=self.provider_name,
                code="invalid_stream_response",
            )
        self._validate_finish_reason(finish_reason)
        tool_calls = self._decode_stream_tool_calls(tool_fragments, aliases)
        if bool(tool_calls) != (finish_reason == "tool_calls"):
            raise ProviderResponseError(
                provider=self.provider_name,
                code="invalid_stream_tool_call",
            )
        content_text = "".join(content_parts)
        content = content_text.strip() if content_text.strip() else None
        reasoning_text = "".join(reasoning_parts)
        reasoning_content = self._validate_reasoning_content(
            reasoning_text if reasoning_text.strip() else None,
            has_tool_calls=bool(tool_calls),
        )
        try:
            response = ChatResponse(
                content=content,
                model=resolved_model or self.model_name,
                provider=self.provider_name,
                usage=usage,
                tool_calls=tool_calls,
                finish_reason=finish_reason,
                request_id=request_id,
                reasoning_content=reasoning_content,
            )
        except ValueError:
            raise ProviderResponseError(
                provider=self.provider_name,
                code="invalid_stream_response",
            ) from None
        return ZhipuStreamResult(
            response=response,
            chunk_count=chunk_count,
            content_chunk_count=content_chunk_count,
            reasoning_chunk_count=reasoning_chunk_count,
            tool_call_chunk_count=tool_call_chunk_count,
        )

    def _append_stream_tool_fragment(
        self,
        fragments: dict[int, dict[str, Any]],
        raw_call: Any,
    ) -> None:
        index = getattr(raw_call, "index", None)
        if isinstance(index, bool) or not isinstance(index, int) or index < 0:
            raise ProviderResponseError(
                provider=self.provider_name,
                code="invalid_stream_tool_call",
            )
        state = fragments.setdefault(
            index,
            {"id": None, "type": None, "name": "", "arguments": ""},
        )
        for field_name in ("id", "type"):
            value = getattr(raw_call, field_name, None)
            if value is None:
                continue
            if not isinstance(value, str) or not value.strip():
                raise ProviderResponseError(
                    provider=self.provider_name,
                    code="invalid_stream_tool_call",
                )
            if state[field_name] is not None and state[field_name] != value:
                raise ProviderResponseError(
                    provider=self.provider_name,
                    code="invalid_stream_tool_call",
                )
            state[field_name] = value
        function = getattr(raw_call, "function", None)
        if function is None:
            return
        for field_name in ("name", "arguments"):
            value = getattr(function, field_name, None)
            if value is None:
                continue
            if not isinstance(value, str):
                raise ProviderResponseError(
                    provider=self.provider_name,
                    code="invalid_stream_tool_call",
                )
            state[field_name] += value

    def _decode_stream_tool_calls(
        self,
        fragments: dict[int, dict[str, Any]],
        aliases: _ToolAliasMap,
    ) -> tuple[ToolCall, ...]:
        if not fragments:
            return ()
        indexes = sorted(fragments)
        if indexes != list(range(len(indexes))):
            raise ProviderResponseError(
                provider=self.provider_name,
                code="invalid_stream_tool_call",
            )
        assembled = []
        for index in indexes:
            state = fragments[index]
            assembled.append(
                SimpleNamespace(
                    id=state["id"],
                    type=state["type"],
                    function=SimpleNamespace(
                        name=state["name"],
                        arguments=state["arguments"],
                    ),
                )
            )
        try:
            return self._decode_tool_calls(assembled, aliases)
        except ProviderResponseError:
            raise ProviderResponseError(
                provider=self.provider_name,
                code="invalid_stream_tool_call",
            ) from None

    def _validate_finish_reason(self, finish_reason: Any) -> None:
        if finish_reason is None:
            raise ProviderResponseError(
                provider=self.provider_name,
                code="invalid_chat_response",
            )
        if finish_reason in _INCOMPLETE_FINISH_REASONS:
            raise ProviderResponseError(
                provider=self.provider_name,
                code="incomplete_chat_response",
            )
        if finish_reason not in _TERMINAL_FINISH_REASONS:
            raise ProviderResponseError(
                provider=self.provider_name,
                code="invalid_finish_reason",
            )

    def _validate_reasoning_content(
        self,
        reasoning_content: Any,
        *,
        has_tool_calls: bool,
    ) -> str | None:
        """Validate and retain reasoning needed for a later tool replay.

        The value is kept only in the internal provider-neutral response/message
        path.  Public evidence builders deliberately project it away.
        """

        if reasoning_content is None:
            return None
        if not isinstance(reasoning_content, str):
            raise ProviderResponseError(
                provider=self.provider_name,
                code="unexpected_reasoning_content",
            )
        if not reasoning_content.strip():
            return None
        if not self._thinking_profile.accepts_reasoning_content:
            raise ProviderResponseError(
                provider=self.provider_name,
                code="unexpected_reasoning_content",
            )
        # Standard API preserved thinking must be explicitly enabled for a
        # tool round.  Without that profile flag we still fail closed rather
        # than silently dropping state that the vendor expects to see again.
        if has_tool_calls and not self._thinking_profile.preserves_reasoning_content:
            raise ProviderResponseError(
                provider=self.provider_name,
                code="unexpected_reasoning_content",
            )
        return reasoning_content

    @staticmethod
    def _encode_message(
        message: ChatMessage,
        aliases: _ToolAliasMap,
    ) -> dict[str, Any]:
        encoded: dict[str, Any] = {
            "role": message.role.value,
            "content": message.content,
        }
        if (
            message.role is MessageRole.ASSISTANT
            and message.reasoning_content is not None
        ):
            # Do not strip, normalize, or otherwise rewrite this string.  The
            # GLM preserved-thinking contract requires byte-for-byte replay.
            encoded["reasoning_content"] = message.reasoning_content
        if message.role is MessageRole.ASSISTANT and message.tool_calls:
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
        raw_details = getattr(raw_usage, "prompt_tokens_details", None)
        if isinstance(raw_details, Mapping):
            cached_input_tokens = raw_details.get("cached_tokens", 0)
        elif raw_details is None:
            cached_input_tokens = 0
        else:
            cached_input_tokens = getattr(raw_details, "cached_tokens", 0)
        if cached_input_tokens is None:
            cached_input_tokens = 0
        if (
            isinstance(cached_input_tokens, bool)
            or not isinstance(cached_input_tokens, int)
            or cached_input_tokens < 0
            or cached_input_tokens > input_tokens
        ):
            raise ProviderResponseError(
                provider="zhipu",
                code="provider_usage_unavailable",
            )
        return TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=cached_input_tokens,
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
