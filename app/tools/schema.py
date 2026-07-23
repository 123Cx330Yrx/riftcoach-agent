"""JSON Schema checks for tool definitions, calls, and handler results."""

from __future__ import annotations

from typing import Any, Mapping

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from .errors import (
    ToolInputValidationError,
    ToolOutputValidationError,
    ToolSchemaDefinitionError,
)
from .models import ToolDefinition


def _validation_path(error: ValidationError) -> str:
    return ".".join(str(part) for part in error.absolute_path) or "<root>"


def _check_schema(
    schema: Mapping[str, Any],
    *,
    tool_name: str,
    schema_kind: str,
) -> None:
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise ToolSchemaDefinitionError(
            f"{schema_kind} schema is invalid",
            tool_name=tool_name,
            code=f"invalid_{schema_kind}_schema",
        ) from exc


def check_tool_schemas(definition: ToolDefinition) -> None:
    _check_schema(
        definition.input_schema,
        tool_name=definition.name,
        schema_kind="input",
    )
    _check_schema(
        definition.output_schema,
        tool_name=definition.name,
        schema_kind="output",
    )


def validate_tool_input(
    definition: ToolDefinition,
    params: Mapping[str, Any],
) -> None:
    try:
        Draft202012Validator(definition.input_schema).validate(params)
    except ValidationError as exc:
        raise ToolInputValidationError(
            f"tool input failed validation at {_validation_path(exc)}",
            tool_name=definition.name,
            code="invalid_tool_input",
        ) from exc


def validate_tool_output(
    definition: ToolDefinition,
    data: Mapping[str, Any],
) -> None:
    try:
        Draft202012Validator(definition.output_schema).validate(data)
    except ValidationError as exc:
        raise ToolOutputValidationError(
            f"tool output failed validation at {_validation_path(exc)}",
            tool_name=definition.name,
            code="invalid_tool_output",
        ) from exc

