from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(frozen=True)
class ChatMessage:
    role: MessageRole
    content: str

    def __post_init__(self) -> None:
        if not isinstance(self.role, MessageRole):
            raise ValueError("role must be a MessageRole.")
        if not self.content.strip():
            raise ValueError("message content must not be empty.")


@dataclass(frozen=True)
class ChatRequest:
    messages: tuple[ChatMessage, ...]
    temperature: float = 0.0
    max_tokens: int | None = None
    timeout_s: float = 30.0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.messages:
            raise ValueError("messages must not be empty.")
        if not all(isinstance(message, ChatMessage) for message in self.messages):
            raise ValueError("messages must contain only ChatMessage values.")
        if isinstance(self.temperature, bool) or not isinstance(
            self.temperature, (int, float)
        ):
            raise ValueError("temperature must be a number between 0 and 2.")
        if not 0 <= self.temperature <= 2:
            raise ValueError("temperature must be between 0 and 2.")
        if self.max_tokens is not None and (
            isinstance(self.max_tokens, bool)
            or not isinstance(self.max_tokens, int)
            or self.max_tokens <= 0
        ):
            raise ValueError("max_tokens must be a positive integer or None.")
        if (
            isinstance(self.timeout_s, bool)
            or not isinstance(self.timeout_s, (int, float))
            or self.timeout_s <= 0
        ):
            raise ValueError("timeout_s must be greater than zero.")


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0

    def __post_init__(self) -> None:
        for name, value in (
            ("input_tokens", self.input_tokens),
            ("output_tokens", self.output_tokens),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer.")

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True)
class ChatResponse:
    content: str
    model: str
    provider: str
    finish_reason: str | None = None
    usage: TokenUsage = field(default_factory=TokenUsage)
    request_id: str | None = None

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError("response content must not be empty.")
        if not self.model.strip():
            raise ValueError("response model must not be empty.")
        if not self.provider.strip():
            raise ValueError("response provider must not be empty.")
        if not isinstance(self.usage, TokenUsage):
            raise ValueError("usage must be TokenUsage.")
