"""Definition catalog for tools; execution belongs to the future runtime."""

from __future__ import annotations

from .errors import DuplicateToolError, ToolNotFoundError
from .models import ToolDefinition
from .schema import check_tool_schemas


class ToolRegistry:
    def __init__(self) -> None:
        self._definitions: dict[str, ToolDefinition] = {}

    def register(self, definition: ToolDefinition) -> None:
        check_tool_schemas(definition)
        if definition.name in self._definitions:
            raise DuplicateToolError(
                f"tool '{definition.name}' is already registered",
                tool_name=definition.name,
                code="duplicate_tool",
            )
        self._definitions[definition.name] = definition

    def get(self, tool_name: str) -> ToolDefinition:
        try:
            return self._definitions[tool_name]
        except KeyError as exc:
            raise ToolNotFoundError(
                f"tool '{tool_name}' is not registered",
                tool_name=tool_name,
                code="tool_not_found",
            ) from exc

    def list_tools(self) -> tuple[ToolDefinition, ...]:
        return tuple(
            self._definitions[name] for name in sorted(self._definitions)
        )

    def __len__(self) -> int:
        return len(self._definitions)

