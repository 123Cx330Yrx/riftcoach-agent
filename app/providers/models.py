from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


_CONTRACT_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")
_SEMANTIC_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


def _freeze_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): _freeze_json(item) for key, item in value.items()}
        )
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)
    return value


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return copy.deepcopy(value)


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ToolChoiceMode(str, Enum):
    """Provider-neutral policy for whether a model may request tools."""

    AUTO = "auto"
    NONE = "none"
    REQUIRED = "required"


@dataclass(frozen=True)
class StructuredResponseContract:
    """One provider-neutral JSON object contract for a model response."""

    name: str
    version: str
    json_schema: Mapping[str, Any]
    strict: bool = True

    def __post_init__(self) -> None:
        name = self.name.strip()
        version = self.version.strip()
        if not _CONTRACT_NAME_PATTERN.fullmatch(name):
            raise ValueError("response contract name is invalid.")
        if not _SEMANTIC_VERSION_PATTERN.fullmatch(version):
            raise ValueError("response contract version must use MAJOR.MINOR.PATCH.")
        if not isinstance(self.json_schema, Mapping):
            raise ValueError("response contract json_schema must be a mapping.")

        schema = copy.deepcopy(dict(self.json_schema))
        if schema.get("type") != "object":
            raise ValueError("response contract must describe a JSON object.")
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as exc:
            raise ValueError("response contract json_schema is invalid.") from exc
        if self.strict is not True:
            raise ValueError("response contract strict mode must be enabled.")

        object.__setattr__(self, "name", name)
        object.__setattr__(self, "version", version)
        object.__setattr__(self, "json_schema", _freeze_json(schema))

    def schema_dict(self) -> dict[str, Any]:
        """Return a mutable transport copy without exposing internal state."""

        return _thaw_json(self.json_schema)


@dataclass(frozen=True)
class ToolCall:
    """One normalized tool request proposed by a model."""

    id: str
    name: str
    arguments: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("tool call id must not be empty.")
        if not self.name.strip():
            raise ValueError("tool call name must not be empty.")
        if not isinstance(self.arguments, Mapping):
            raise ValueError("tool call arguments must be a mapping.")


@dataclass(frozen=True)
class ToolSpec:
    """Provider-neutral tool description supplied to a model."""

    name: str
    description: str
    input_schema: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("tool name must not be empty.")
        if not self.description.strip():
            raise ValueError("tool description must not be empty.")
        if not isinstance(self.input_schema, Mapping):
            raise ValueError("tool input_schema must be a mapping.")
        if self.input_schema.get("type") != "object":
            raise ValueError("tool input_schema must describe a JSON object.")


@dataclass(frozen=True)
class ChatMessage:
    role: MessageRole
    content: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()
    tool_call_id: str | None = None
    name: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.role, MessageRole):
            raise ValueError("role must be a MessageRole.")
        if self.content is not None and not self.content.strip():
            raise ValueError("message content must be non-blank or None.")
        if not all(isinstance(call, ToolCall) for call in self.tool_calls):
            raise ValueError("tool_calls must contain only ToolCall values.")
        if len({call.id for call in self.tool_calls}) != len(self.tool_calls):
            raise ValueError("tool call ids must be unique within one message.")

        if self.role in {MessageRole.SYSTEM, MessageRole.USER}:
            if self.content is None:
                raise ValueError("system and user messages require content.")
            if self.tool_calls or self.tool_call_id is not None or self.name is not None:
                raise ValueError(
                    "system and user messages cannot carry tool metadata."
                )
        elif self.role is MessageRole.ASSISTANT:
            if self.content is None and not self.tool_calls:
                raise ValueError(
                    "assistant messages require content or at least one tool call."
                )
            if self.tool_call_id is not None or self.name is not None:
                raise ValueError(
                    "assistant messages cannot identify a tool result."
                )
        elif self.role is MessageRole.TOOL:
            if self.content is None:
                raise ValueError("tool messages require content.")
            if self.tool_call_id is None or not self.tool_call_id.strip():
                raise ValueError("tool messages require a tool_call_id.")
            if self.tool_calls:
                raise ValueError("tool messages cannot request more tools.")
            if self.name is not None and not self.name.strip():
                raise ValueError("tool message name must be non-blank or None.")


@dataclass(frozen=True)
class ChatRequest:
    messages: tuple[ChatMessage, ...]
    tools: tuple[ToolSpec, ...] = ()
    tool_choice: ToolChoiceMode = ToolChoiceMode.AUTO
    temperature: float = 0.0
    max_tokens: int | None = None
    timeout_s: float = 30.0
    response_contract: StructuredResponseContract | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.messages:
            raise ValueError("messages must not be empty.")
        if not all(isinstance(message, ChatMessage) for message in self.messages):
            raise ValueError("messages must contain only ChatMessage values.")
        if not all(isinstance(tool, ToolSpec) for tool in self.tools):
            raise ValueError("tools must contain only ToolSpec values.")
        if len({tool.name for tool in self.tools}) != len(self.tools):
            raise ValueError("tool names must be unique within one request.")
        if not isinstance(self.tool_choice, ToolChoiceMode):
            raise ValueError("tool_choice must be a ToolChoiceMode.")
        if self.tool_choice is ToolChoiceMode.REQUIRED and not self.tools:
            raise ValueError("required tool choice needs at least one tool.")
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
        if self.response_contract is not None and not isinstance(
            self.response_contract,
            StructuredResponseContract,
        ):
            raise ValueError(
                "response_contract must be StructuredResponseContract or None."
            )


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
    content: str | None
    model: str
    provider: str
    tool_calls: tuple[ToolCall, ...] = ()
    finish_reason: str | None = None
    usage: TokenUsage = field(default_factory=TokenUsage)
    request_id: str | None = None

    def __post_init__(self) -> None:
        if self.content is not None and not self.content.strip():
            raise ValueError("response content must be non-blank or None.")
        if not all(isinstance(call, ToolCall) for call in self.tool_calls):
            raise ValueError("tool_calls must contain only ToolCall values.")
        if len({call.id for call in self.tool_calls}) != len(self.tool_calls):
            raise ValueError("tool call ids must be unique within one response.")
        if self.content is None and not self.tool_calls:
            raise ValueError("response requires content or at least one tool call.")
        if not self.model.strip():
            raise ValueError("response model must not be empty.")
        if not self.provider.strip():
            raise ValueError("response provider must not be empty.")
        if not isinstance(self.usage, TokenUsage):
            raise ValueError("usage must be TokenUsage.")

    @property
    def requests_tools(self) -> bool:
        return bool(self.tool_calls)
