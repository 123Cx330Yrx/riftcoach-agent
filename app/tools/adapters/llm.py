"""Tool adapter exposing the provider-neutral chat port."""

from __future__ import annotations

from typing import Any, Mapping

from app.model_runtime import (
    ModelRuntimeProfile,
    require_registered_model_runtime_profile,
)
from app.providers.models import (
    ChatMessage,
    ChatRequest,
    MessageRole,
    StructuredResponseContract,
)

from ..models import (
    CircuitBreakerPolicy,
    RetryPolicy,
    ToolContext,
    ToolDefinition,
    ToolPolicy,
)


LLM_CHAT_RETRY_MAX_ATTEMPTS = 3


def build_llm_tools(
    provider: Any,
    *,
    runtime_profile: ModelRuntimeProfile | None = None,
) -> tuple[ToolDefinition, ...]:
    if runtime_profile is not None:
        runtime_profile = require_registered_model_runtime_profile(
            runtime_profile
        )
        if not runtime_profile.matches(
            getattr(provider, "provider_name", None),
            getattr(provider, "model_name", None),
        ):
            raise ValueError("runtime_profile does not match the Provider")

    def chat_handler(
        params: Mapping[str, Any],
        context: ToolContext,
    ) -> Mapping[str, Any]:
        raw_contract = params.get("response_contract")
        response_contract = (
            StructuredResponseContract(
                name=raw_contract["name"],
                version=raw_contract["version"],
                json_schema=raw_contract["json_schema"],
                strict=raw_contract.get("strict", True),
            )
            if raw_contract is not None
            else None
        )
        requested_max_tokens = params.get("max_tokens")
        if runtime_profile is not None:
            max_tokens = (
                runtime_profile.max_output_tokens
                if requested_max_tokens is None
                else min(
                    requested_max_tokens,
                    runtime_profile.max_output_tokens,
                )
            )
            # The model can propose tool arguments, but it cannot raise or
            # otherwise override the trusted model profile's sampling policy.
            temperature = runtime_profile.temperature
            top_p = runtime_profile.top_p
        else:
            max_tokens = requested_max_tokens
            temperature = params.get("temperature", 0.0)
            top_p = params.get("top_p")

        request_metadata = dict(context.metadata)
        request_timeout = max(0.001, context.remaining_s())
        if runtime_profile is not None:
            request_timeout = min(
                request_timeout,
                runtime_profile.llm_tool_timeout_s,
            )
            request_metadata.update(
                {
                    "runtime_profile_id": runtime_profile.profile_id,
                    "runtime_profile_version": runtime_profile.version,
                }
            )

        request = ChatRequest(
            messages=tuple(
                ChatMessage(
                    role=MessageRole(message["role"]),
                    content=message["content"],
                )
                for message in params["messages"]
            ),
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_s=request_timeout,
            response_contract=response_contract,
            metadata=request_metadata,
            top_p=top_p,
        )
        response = provider.chat(request)
        return {
            "content": response.content,
            "model": response.model,
            "provider": response.provider,
            "finish_reason": response.finish_reason,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            "request_id": response.request_id,
        }

    nullable_string = {"type": ["string", "null"]}
    return (
        ToolDefinition(
            name="llm.chat",
            version="1.0.0",
            description="Send one provider-neutral chat completion request.",
            handler=chat_handler,
            input_schema={
                "type": "object",
                "properties": {
                    "messages": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {
                                    "type": "string",
                                    "enum": [
                                        "system",
                                        "user",
                                        "assistant",
                                        "tool",
                                    ],
                                },
                                "content": {
                                    "type": "string",
                                    "minLength": 1,
                                },
                            },
                            "required": ["role", "content"],
                            "additionalProperties": False,
                        },
                    },
                    "temperature": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 2,
                    },
                    "max_tokens": {
                        "type": ["integer", "null"],
                        "minimum": 1,
                    },
                    "top_p": {
                        "type": ["number", "null"],
                        "minimum": 0,
                        "maximum": 1,
                    },
                    "response_contract": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "minLength": 1},
                            "version": {
                                "type": "string",
                                "pattern": "^\\d+\\.\\d+\\.\\d+$",
                            },
                            "json_schema": {"type": "object"},
                            "strict": {"const": True},
                        },
                        "required": [
                            "name",
                            "version",
                            "json_schema",
                            "strict",
                        ],
                        "additionalProperties": False,
                    },
                },
                "required": ["messages"],
                "additionalProperties": False,
            },
            output_schema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "minLength": 1},
                    "model": {"type": "string", "minLength": 1},
                    "provider": {"type": "string", "minLength": 1},
                    "finish_reason": nullable_string,
                    "usage": {
                        "type": "object",
                        "properties": {
                            "input_tokens": {
                                "type": "integer",
                                "minimum": 0,
                            },
                            "output_tokens": {
                                "type": "integer",
                                "minimum": 0,
                            },
                            "total_tokens": {
                                "type": "integer",
                                "minimum": 0,
                            },
                        },
                        "required": [
                            "input_tokens",
                            "output_tokens",
                            "total_tokens",
                        ],
                        "additionalProperties": False,
                    },
                    "request_id": nullable_string,
                },
                "required": [
                    "content",
                    "model",
                    "provider",
                    "finish_reason",
                    "usage",
                    "request_id",
                ],
                "additionalProperties": False,
            },
            policy=ToolPolicy(
                timeout_s=(
                    runtime_profile.llm_tool_timeout_s
                    if runtime_profile is not None
                    else 60.0
                ),
                retry=RetryPolicy(
                    max_attempts=LLM_CHAT_RETRY_MAX_ATTEMPTS,
                    base_delay_s=0.5,
                    max_delay_s=2.0,
                ),
                circuit_breaker=CircuitBreakerPolicy(
                    failure_threshold=3,
                    recovery_s=30.0,
                ),
            ),
        ),
    )
