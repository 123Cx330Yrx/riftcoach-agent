"""Tool adapter exposing the provider-neutral chat port."""

from __future__ import annotations

from typing import Any, Mapping

from app.providers.models import ChatMessage, ChatRequest, MessageRole

from ..models import (
    CircuitBreakerPolicy,
    RetryPolicy,
    ToolContext,
    ToolDefinition,
    ToolPolicy,
)


def build_llm_tools(provider: Any) -> tuple[ToolDefinition, ...]:
    def chat_handler(
        params: Mapping[str, Any],
        context: ToolContext,
    ) -> Mapping[str, Any]:
        request = ChatRequest(
            messages=tuple(
                ChatMessage(
                    role=MessageRole(message["role"]),
                    content=message["content"],
                )
                for message in params["messages"]
            ),
            temperature=params.get("temperature", 0.0),
            max_tokens=params.get("max_tokens"),
            timeout_s=max(0.001, context.remaining_s()),
            metadata=context.metadata,
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
                timeout_s=60.0,
                retry=RetryPolicy(
                    max_attempts=3,
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
