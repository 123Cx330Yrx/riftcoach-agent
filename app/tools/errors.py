"""Typed, redaction-safe errors for the tool runtime."""

from __future__ import annotations


class ToolError(RuntimeError):
    """Base error carrying machine-readable metadata without raw tool values."""

    def __init__(
        self,
        message: str,
        *,
        tool_name: str,
        code: str,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.tool_name = tool_name
        self.code = code
        self.retryable = retryable


class ToolSchemaDefinitionError(ToolError):
    """A tool author supplied an invalid JSON Schema."""


class ToolInputValidationError(ToolError):
    """Caller input does not satisfy a tool's declared contract."""


class ToolOutputValidationError(ToolError):
    """A handler returned data that violates its declared contract."""


class DuplicateToolError(ToolError):
    """The registry already contains a tool with the same stable name."""


class ToolNotFoundError(ToolError):
    """A requested tool is not present in the registry."""

