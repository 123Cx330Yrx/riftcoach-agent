"""Transport-neutral standard MCP envelopes and schema snapshots."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from collections.abc import Mapping, Set
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, TypeVar

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from .errors import (
    McpCapabilityError,
    McpContractError,
    McpEnvelopeError,
    McpErrorInfo,
    McpProtocolVersionError,
    McpRemoteError,
    McpResultError,
    McpSchemaDriftError,
    McpToolCatalogError,
    McpToolCallError,
)


JSONRPC_VERSION = "2.0"
_TOOL_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_PROTOCOL_VERSION_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ErrorT = TypeVar("_ErrorT", bound=McpContractError)


def _error(
    error_type: type[_ErrorT],
    code: str,
    *,
    request_id: str | int | None = None,
    remote_code: int | None = None,
    retryable: bool = False,
) -> _ErrorT:
    return error_type(
        McpErrorInfo(
            code=code,
            retryable=retryable,
            request_id=request_id,
            remote_code=remote_code,
        )
    )


def _is_request_id(value: Any) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        or isinstance(value, str)
        and bool(value.strip())
    )


def _validate_request_id(value: Any) -> None:
    if not _is_request_id(value):
        raise ValueError("request_id must be a non-blank string or integer.")


def _same_request_id(left: str | int, right: str | int) -> bool:
    return type(left) is type(right) and left == right


def _freeze_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("JSON object keys must be strings.")
            frozen[key] = _freeze_json(item)
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise ValueError("value is not finite JSON data.")


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return copy.deepcopy(value)


def _canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            _thaw_json(_freeze_json(value)),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("value cannot be encoded as canonical JSON.") from exc


def _mapping_or_error(
    value: Any,
    *,
    error_type: type[_ErrorT],
    code: str,
    request_id: str | int | None = None,
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or not all(
        isinstance(key, str) for key in value
    ):
        raise _error(error_type, code, request_id=request_id)
    return value


def _exact_fields(
    value: Mapping[str, Any],
    *,
    required: frozenset[str],
    optional: frozenset[str] = frozenset(),
    error_type: type[_ErrorT],
    code: str,
    request_id: str | int | None = None,
) -> None:
    keys = frozenset(value)
    if not required.issubset(keys) or not keys.issubset(required | optional):
        raise _error(error_type, code, request_id=request_id)


def _parse_response_envelope(
    wire: Any,
    *,
    expected_request_id: str | int,
) -> Mapping[str, Any]:
    envelope = _mapping_or_error(
        wire,
        error_type=McpEnvelopeError,
        code="mcp_envelope_invalid",
        request_id=expected_request_id,
    )
    keys = frozenset(envelope)
    result_keys = frozenset({"jsonrpc", "id", "result"})
    error_keys = frozenset({"jsonrpc", "id", "error"})
    if keys not in (result_keys, error_keys):
        raise _error(
            McpEnvelopeError,
            "mcp_envelope_invalid",
            request_id=expected_request_id,
        )
    if envelope.get("jsonrpc") != JSONRPC_VERSION:
        raise _error(
            McpEnvelopeError,
            "mcp_envelope_invalid",
            request_id=expected_request_id,
        )
    response_id = envelope.get("id")
    if not _is_request_id(response_id):
        raise _error(
            McpEnvelopeError,
            "mcp_envelope_invalid",
            request_id=expected_request_id,
        )
    if not _same_request_id(response_id, expected_request_id):
        raise _error(
            McpEnvelopeError,
            "mcp_request_id_mismatch",
            request_id=expected_request_id,
        )
    if "error" in envelope:
        remote = _mapping_or_error(
            envelope["error"],
            error_type=McpEnvelopeError,
            code="mcp_envelope_invalid",
            request_id=expected_request_id,
        )
        _exact_fields(
            remote,
            required=frozenset({"code", "message"}),
            optional=frozenset({"data"}),
            error_type=McpEnvelopeError,
            code="mcp_envelope_invalid",
            request_id=expected_request_id,
        )
        remote_code = remote["code"]
        remote_message = remote["message"]
        if (
            isinstance(remote_code, bool)
            or not isinstance(remote_code, int)
            or not isinstance(remote_message, str)
        ):
            raise _error(
                McpEnvelopeError,
                "mcp_envelope_invalid",
                request_id=expected_request_id,
            )
        if "data" in remote:
            try:
                _freeze_json(remote["data"])
            except ValueError as exc:
                raise _error(
                    McpEnvelopeError,
                    "mcp_envelope_invalid",
                    request_id=expected_request_id,
                ) from exc
        raise _error(
            McpRemoteError,
            "mcp_remote_error",
            request_id=expected_request_id,
            remote_code=remote_code,
        )
    return _mapping_or_error(
        envelope["result"],
        error_type=McpEnvelopeError,
        code="mcp_envelope_invalid",
        request_id=expected_request_id,
    )


def _validate_object_schema(
    value: Any,
    *,
    error_type: type[_ErrorT],
    code: str,
    request_id: str | int | None = None,
) -> Mapping[str, Any]:
    schema = _mapping_or_error(
        value,
        error_type=error_type,
        code=code,
        request_id=request_id,
    )
    if schema.get("type") != "object":
        raise _error(error_type, code, request_id=request_id)
    try:
        Draft202012Validator.check_schema(dict(schema))
        return _freeze_json(schema)
    except (SchemaError, ValueError) as exc:
        raise _error(error_type, code, request_id=request_id) from exc


@dataclass(frozen=True)
class McpContractLimits:
    max_tools: int = 128
    max_catalog_bytes: int = 256 * 1024
    max_schema_bytes: int = 64 * 1024
    max_argument_bytes: int = 64 * 1024
    max_result_bytes: int = 1024 * 1024
    max_content_items: int = 128
    max_cursor_chars: int = 1024
    max_description_chars: int = 4096

    def __post_init__(self) -> None:
        for name, value in (
            ("max_tools", self.max_tools),
            ("max_catalog_bytes", self.max_catalog_bytes),
            ("max_schema_bytes", self.max_schema_bytes),
            ("max_argument_bytes", self.max_argument_bytes),
            ("max_result_bytes", self.max_result_bytes),
            ("max_content_items", self.max_content_items),
            ("max_cursor_chars", self.max_cursor_chars),
            ("max_description_chars", self.max_description_chars),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer.")


@dataclass(frozen=True)
class McpImplementation:
    name: str
    version: str

    def __post_init__(self) -> None:
        for field_name, value in (("name", self.name), ("version", self.version)):
            if (
                not isinstance(value, str)
                or not value.strip()
                or len(value) > 128
            ):
                raise ValueError(f"implementation {field_name} is invalid.")
            object.__setattr__(self, field_name, value.strip())

    def to_wire(self) -> dict[str, str]:
        return {"name": self.name, "version": self.version}


@dataclass(frozen=True)
class McpToolsCapability:
    list_changed: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.list_changed, bool):
            raise ValueError("list_changed must be a boolean.")


@dataclass(frozen=True)
class McpInitializeRequest:
    request_id: str | int
    protocol_version: str
    capabilities: Mapping[str, Any] = field(repr=False)
    client_info: McpImplementation

    def __post_init__(self) -> None:
        _validate_request_id(self.request_id)
        if (
            not isinstance(self.protocol_version, str)
            or not _PROTOCOL_VERSION_PATTERN.fullmatch(self.protocol_version)
        ):
            raise ValueError("protocol_version must use YYYY-MM-DD.")
        if not isinstance(self.capabilities, Mapping):
            raise ValueError("capabilities must be a mapping.")
        if not isinstance(self.client_info, McpImplementation):
            raise ValueError("client_info must be McpImplementation.")
        try:
            frozen = _freeze_json(self.capabilities)
        except ValueError as exc:
            raise ValueError("capabilities must be finite JSON data.") from exc
        object.__setattr__(self, "capabilities", frozen)

    def to_wire(self) -> dict[str, Any]:
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": self.request_id,
            "method": "initialize",
            "params": {
                "protocolVersion": self.protocol_version,
                "capabilities": _thaw_json(self.capabilities),
                "clientInfo": self.client_info.to_wire(),
            },
        }


@dataclass(frozen=True)
class McpInitializeResult:
    request_id: str | int
    protocol_version: str
    server_info: McpImplementation
    tools: McpToolsCapability | None
    capabilities: Mapping[str, Any] = field(repr=False)
    instructions: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        _validate_request_id(self.request_id)
        if (
            not isinstance(self.protocol_version, str)
            or not _PROTOCOL_VERSION_PATTERN.fullmatch(self.protocol_version)
        ):
            raise ValueError("protocol_version must use YYYY-MM-DD.")
        if not isinstance(self.server_info, McpImplementation):
            raise ValueError("server_info must be McpImplementation.")
        if self.tools is not None and not isinstance(
            self.tools, McpToolsCapability
        ):
            raise ValueError("tools must be McpToolsCapability or None.")
        if not isinstance(self.capabilities, Mapping):
            raise ValueError("capabilities must be a mapping.")
        object.__setattr__(self, "capabilities", _freeze_json(self.capabilities))
        if self.instructions is not None and not isinstance(
            self.instructions, str
        ):
            raise ValueError("instructions must be a string or None.")

    @classmethod
    def from_wire(
        cls,
        wire: Any,
        *,
        expected_request_id: str | int,
        supported_protocol_versions: Set[str],
    ) -> "McpInitializeResult":
        _validate_request_id(expected_request_id)
        if (
            isinstance(supported_protocol_versions, (str, bytes))
            or not isinstance(supported_protocol_versions, Set)
            or not supported_protocol_versions
            or not all(
                isinstance(version, str)
                and _PROTOCOL_VERSION_PATTERN.fullmatch(version)
                for version in supported_protocol_versions
            )
        ):
            raise ValueError("supported_protocol_versions must be a non-empty set.")
        result = _parse_response_envelope(
            wire,
            expected_request_id=expected_request_id,
        )
        _exact_fields(
            result,
            required=frozenset(
                {"protocolVersion", "capabilities", "serverInfo"}
            ),
            optional=frozenset({"instructions"}),
            error_type=McpEnvelopeError,
            code="mcp_envelope_invalid",
            request_id=expected_request_id,
        )
        protocol_version = result["protocolVersion"]
        if (
            not isinstance(protocol_version, str)
            or not _PROTOCOL_VERSION_PATTERN.fullmatch(protocol_version)
        ):
            raise _error(
                McpEnvelopeError,
                "mcp_envelope_invalid",
                request_id=expected_request_id,
            )
        if protocol_version not in supported_protocol_versions:
            raise _error(
                McpProtocolVersionError,
                "mcp_protocol_version_unsupported",
                request_id=expected_request_id,
            )
        server_raw = _mapping_or_error(
            result["serverInfo"],
            error_type=McpEnvelopeError,
            code="mcp_envelope_invalid",
            request_id=expected_request_id,
        )
        _exact_fields(
            server_raw,
            required=frozenset({"name", "version"}),
            error_type=McpEnvelopeError,
            code="mcp_envelope_invalid",
            request_id=expected_request_id,
        )
        try:
            server_info = McpImplementation(
                name=server_raw["name"],
                version=server_raw["version"],
            )
        except (TypeError, ValueError) as exc:
            raise _error(
                McpEnvelopeError,
                "mcp_envelope_invalid",
                request_id=expected_request_id,
            ) from exc
        capabilities = _mapping_or_error(
            result["capabilities"],
            error_type=McpEnvelopeError,
            code="mcp_envelope_invalid",
            request_id=expected_request_id,
        )
        allowed_capabilities = frozenset(
            {
                "completions",
                "experimental",
                "logging",
                "prompts",
                "resources",
                "tasks",
                "tools",
            }
        )
        if not frozenset(capabilities).issubset(allowed_capabilities):
            raise _error(
                McpEnvelopeError,
                "mcp_envelope_invalid",
                request_id=expected_request_id,
            )
        tools: McpToolsCapability | None = None
        if "tools" in capabilities:
            tools_raw = _mapping_or_error(
                capabilities["tools"],
                error_type=McpEnvelopeError,
                code="mcp_envelope_invalid",
                request_id=expected_request_id,
            )
            _exact_fields(
                tools_raw,
                required=frozenset(),
                optional=frozenset({"listChanged"}),
                error_type=McpEnvelopeError,
                code="mcp_envelope_invalid",
                request_id=expected_request_id,
            )
            list_changed = tools_raw.get("listChanged", False)
            if not isinstance(list_changed, bool):
                raise _error(
                    McpEnvelopeError,
                    "mcp_envelope_invalid",
                    request_id=expected_request_id,
                )
            tools = McpToolsCapability(list_changed=list_changed)
        instructions = result.get("instructions")
        if instructions is not None and (
            not isinstance(instructions, str)
            or not instructions.strip()
            or len(instructions) > 8192
        ):
            raise _error(
                McpEnvelopeError,
                "mcp_envelope_invalid",
                request_id=expected_request_id,
            )
        try:
            frozen_capabilities = _freeze_json(capabilities)
        except ValueError as exc:
            raise _error(
                McpEnvelopeError,
                "mcp_envelope_invalid",
                request_id=expected_request_id,
            ) from exc
        return cls(
            request_id=expected_request_id,
            protocol_version=protocol_version,
            server_info=server_info,
            tools=tools,
            capabilities=frozen_capabilities,
            instructions=instructions,
        )

    def require_tools(self) -> McpToolsCapability:
        if self.tools is None:
            raise _error(
                McpCapabilityError,
                "mcp_tools_capability_missing",
                request_id=self.request_id,
            )
        return self.tools


@dataclass(frozen=True)
class McpListToolsRequest:
    request_id: str | int
    cursor: str | None = None

    def __post_init__(self) -> None:
        _validate_request_id(self.request_id)
        if self.cursor is not None and (
            not isinstance(self.cursor, str)
            or not self.cursor.strip()
            or len(self.cursor) > 1024
        ):
            raise ValueError("cursor must be a bounded non-blank string or None.")

    def to_wire(self) -> dict[str, Any]:
        params = {} if self.cursor is None else {"cursor": self.cursor}
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": self.request_id,
            "method": "tools/list",
            "params": params,
        }


@dataclass(frozen=True)
class McpToolDescriptor:
    name: str
    description: str = field(repr=False)
    input_schema: Mapping[str, Any] = field(repr=False)
    output_schema: Mapping[str, Any] | None = field(default=None, repr=False)
    schema_digest: str = ""
    title: str | None = field(default=None, repr=False)
    annotations: Mapping[str, Any] | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not _TOOL_NAME_PATTERN.fullmatch(
            self.name
        ):
            raise ValueError("MCP tool name is invalid.")
        if not isinstance(self.description, str):
            raise ValueError("MCP tool description must be a string.")
        if self.title is not None and not isinstance(self.title, str):
            raise ValueError("MCP tool title must be a string or None.")
        if not isinstance(self.input_schema, Mapping):
            raise ValueError("MCP input schema must be a mapping.")
        object.__setattr__(self, "input_schema", _freeze_json(self.input_schema))
        if self.output_schema is not None:
            if not isinstance(self.output_schema, Mapping):
                raise ValueError("MCP output schema must be a mapping or None.")
            object.__setattr__(
                self,
                "output_schema",
                _freeze_json(self.output_schema),
            )
        expected_digest = hashlib.sha256(
            _canonical_json_bytes(
                {
                    "inputSchema": self.input_schema,
                    "outputSchema": self.output_schema,
                }
            )
        ).hexdigest()
        if self.schema_digest != expected_digest:
            raise ValueError("schema_digest does not match the tool schemas.")
        if self.annotations is not None:
            if not isinstance(self.annotations, Mapping):
                raise ValueError("annotations must be a mapping or None.")
            object.__setattr__(self, "annotations", _freeze_json(self.annotations))


@dataclass(frozen=True)
class McpToolCatalog:
    protocol_version: str
    server_info: McpImplementation
    tools: tuple[McpToolDescriptor, ...]
    digest: str
    next_cursor: str | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.protocol_version, str)
            or not _PROTOCOL_VERSION_PATTERN.fullmatch(self.protocol_version)
        ):
            raise ValueError("protocol_version must use YYYY-MM-DD.")
        if not isinstance(self.server_info, McpImplementation):
            raise ValueError("server_info must be McpImplementation.")
        if not isinstance(self.tools, tuple) or not all(
            isinstance(tool, McpToolDescriptor) for tool in self.tools
        ):
            raise ValueError("tools must be a tuple of McpToolDescriptor values.")
        if len({tool.name for tool in self.tools}) != len(self.tools):
            raise ValueError("MCP tool names must be unique in a catalog.")
        expected_digest = hashlib.sha256(
            _canonical_json_bytes(
                {
                    "protocolVersion": self.protocol_version,
                    "serverInfo": self.server_info.to_wire(),
                    "tools": [
                        {
                            "name": item.name,
                            "schemaDigest": item.schema_digest,
                        }
                        for item in self.tools
                    ],
                }
            )
        ).hexdigest()
        if self.digest != expected_digest:
            raise ValueError("catalog digest does not match the catalog snapshot.")
        if self.next_cursor is not None and (
            not isinstance(self.next_cursor, str) or not self.next_cursor.strip()
        ):
            raise ValueError("next_cursor must be a non-blank string or None.")

    @classmethod
    def from_wire(
        cls,
        wire: Any,
        *,
        initialization: McpInitializeResult,
        expected_request_id: str | int,
        limits: McpContractLimits,
        allowed_tools: Set[str] | None = None,
    ) -> "McpToolCatalog":
        if not isinstance(initialization, McpInitializeResult):
            raise TypeError("initialization must be McpInitializeResult.")
        if not isinstance(limits, McpContractLimits):
            raise TypeError("limits must be McpContractLimits.")
        if allowed_tools is not None and (
            isinstance(allowed_tools, (str, bytes))
            or not isinstance(allowed_tools, Set)
            or not all(isinstance(item, str) for item in allowed_tools)
        ):
            raise TypeError("allowed_tools must be a set of strings or None.")
        initialization.require_tools()
        result = _parse_response_envelope(
            wire,
            expected_request_id=expected_request_id,
        )
        _exact_fields(
            result,
            required=frozenset({"tools"}),
            optional=frozenset({"nextCursor", "_meta"}),
            error_type=McpToolCatalogError,
            code="mcp_tool_catalog_invalid",
            request_id=expected_request_id,
        )
        try:
            result_size = len(_canonical_json_bytes(result))
        except ValueError as exc:
            raise _error(
                McpToolCatalogError,
                "mcp_tool_catalog_invalid",
                request_id=expected_request_id,
            ) from exc
        tools_raw = result["tools"]
        if not isinstance(tools_raw, list):
            raise _error(
                McpToolCatalogError,
                "mcp_tool_catalog_invalid",
                request_id=expected_request_id,
            )
        if result_size > limits.max_catalog_bytes or len(tools_raw) > limits.max_tools:
            raise _error(
                McpToolCatalogError,
                "mcp_tool_catalog_too_large",
                request_id=expected_request_id,
            )
        descriptors: list[McpToolDescriptor] = []
        seen_names: set[str] = set()
        for raw in tools_raw:
            if allowed_tools is not None:
                if not isinstance(raw, Mapping):
                    continue
                candidate_name = raw.get("name")
                if candidate_name not in allowed_tools:
                    continue
            descriptor_raw = _mapping_or_error(
                raw,
                error_type=McpToolCatalogError,
                code="mcp_tool_catalog_invalid",
                request_id=expected_request_id,
            )
            _exact_fields(
                descriptor_raw,
                required=frozenset({"name", "inputSchema"}),
                optional=frozenset(
                    {
                        "title",
                        "description",
                        "outputSchema",
                        "annotations",
                        "_meta",
                    }
                ),
                error_type=McpToolCatalogError,
                code="mcp_tool_catalog_invalid",
                request_id=expected_request_id,
            )
            name = descriptor_raw["name"]
            if not isinstance(name, str) or not _TOOL_NAME_PATTERN.fullmatch(name):
                raise _error(
                    McpToolCatalogError,
                    "mcp_tool_catalog_invalid",
                    request_id=expected_request_id,
                )
            if name in seen_names:
                raise _error(
                    McpToolCatalogError,
                    "mcp_tool_catalog_invalid",
                    request_id=expected_request_id,
                )
            seen_names.add(name)
            description = descriptor_raw.get("description", "")
            if not isinstance(description, str) or len(description) > limits.max_description_chars:
                raise _error(
                    McpToolCatalogError,
                    "mcp_tool_catalog_invalid",
                    request_id=expected_request_id,
                )
            title = descriptor_raw.get("title")
            if title is not None and (
                not isinstance(title, str)
                or not title.strip()
                or len(title) > 256
            ):
                raise _error(
                    McpToolCatalogError,
                    "mcp_tool_catalog_invalid",
                    request_id=expected_request_id,
                )
            annotations = None
            if "annotations" in descriptor_raw:
                annotations_raw = _mapping_or_error(
                    descriptor_raw["annotations"],
                    error_type=McpToolCatalogError,
                    code="mcp_tool_catalog_invalid",
                    request_id=expected_request_id,
                )
                _exact_fields(
                    annotations_raw,
                    required=frozenset(),
                    optional=frozenset(
                        {
                            "title",
                            "readOnlyHint",
                            "destructiveHint",
                            "idempotentHint",
                            "openWorldHint",
                        }
                    ),
                    error_type=McpToolCatalogError,
                    code="mcp_tool_catalog_invalid",
                    request_id=expected_request_id,
                )
                annotation_title = annotations_raw.get("title")
                if annotation_title is not None and (
                    not isinstance(annotation_title, str)
                    or not annotation_title.strip()
                    or len(annotation_title) > 256
                ):
                    raise _error(
                        McpToolCatalogError,
                        "mcp_tool_catalog_invalid",
                        request_id=expected_request_id,
                    )
                for hint_name in (
                    "readOnlyHint",
                    "destructiveHint",
                    "idempotentHint",
                    "openWorldHint",
                ):
                    hint = annotations_raw.get(hint_name)
                    if hint is not None and not isinstance(hint, bool):
                        raise _error(
                            McpToolCatalogError,
                            "mcp_tool_catalog_invalid",
                            request_id=expected_request_id,
                        )
                annotations = _freeze_json(annotations_raw)
            input_schema = _validate_object_schema(
                descriptor_raw["inputSchema"],
                error_type=McpToolCatalogError,
                code="mcp_tool_catalog_invalid",
                request_id=expected_request_id,
            )
            output_schema = None
            if "outputSchema" in descriptor_raw:
                output_schema = _validate_object_schema(
                    descriptor_raw["outputSchema"],
                    error_type=McpToolCatalogError,
                    code="mcp_tool_catalog_invalid",
                    request_id=expected_request_id,
                )
            schema_bytes = _canonical_json_bytes(
                {
                    "inputSchema": input_schema,
                    "outputSchema": output_schema,
                }
            )
            if len(schema_bytes) > limits.max_schema_bytes:
                raise _error(
                    McpToolCatalogError,
                    "mcp_tool_catalog_too_large",
                    request_id=expected_request_id,
                )
            descriptors.append(
                McpToolDescriptor(
                    name=name,
                    title=title,
                    description=description,
                    input_schema=input_schema,
                    output_schema=output_schema,
                    schema_digest=hashlib.sha256(schema_bytes).hexdigest(),
                    annotations=annotations,
                )
            )
        next_cursor = result.get("nextCursor")
        if next_cursor is not None and (
            not isinstance(next_cursor, str)
            or not next_cursor.strip()
            or len(next_cursor) > limits.max_cursor_chars
        ):
            raise _error(
                McpToolCatalogError,
                "mcp_tool_catalog_invalid",
                request_id=expected_request_id,
            )
        sorted_descriptors = tuple(sorted(descriptors, key=lambda item: item.name))
        catalog_bytes = _canonical_json_bytes(
            {
                "protocolVersion": initialization.protocol_version,
                "serverInfo": initialization.server_info.to_wire(),
                "tools": [
                    {
                        "name": item.name,
                        "schemaDigest": item.schema_digest,
                    }
                    for item in sorted_descriptors
                ],
            }
        )
        return cls(
            protocol_version=initialization.protocol_version,
            server_info=initialization.server_info,
            tools=sorted_descriptors,
            digest=hashlib.sha256(catalog_bytes).hexdigest(),
            next_cursor=next_cursor,
        )

    def get(self, tool_name: str) -> McpToolDescriptor | None:
        for descriptor in self.tools:
            if descriptor.name == tool_name:
                return descriptor
        return None


@dataclass(frozen=True)
class McpToolCallRequest:
    request_id: str | int
    tool_name: str
    arguments: Mapping[str, Any] = field(repr=False)
    catalog_digest: str
    tool_schema_digest: str
    input_schema: Mapping[str, Any] = field(repr=False)
    output_schema: Mapping[str, Any] | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        _validate_request_id(self.request_id)
        if not isinstance(self.tool_name, str) or not _TOOL_NAME_PATTERN.fullmatch(
            self.tool_name
        ):
            raise ValueError("tool_name is invalid.")
        if not isinstance(self.arguments, Mapping):
            raise ValueError("arguments must be a mapping.")
        object.__setattr__(self, "arguments", _freeze_json(self.arguments))
        for field_name, digest in (
            ("catalog_digest", self.catalog_digest),
            ("tool_schema_digest", self.tool_schema_digest),
        ):
            if not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError(f"{field_name} must be a lowercase SHA-256 digest.")
        if not isinstance(self.input_schema, Mapping):
            raise ValueError("input_schema must be a mapping.")
        object.__setattr__(self, "input_schema", _freeze_json(self.input_schema))
        if self.output_schema is not None:
            if not isinstance(self.output_schema, Mapping):
                raise ValueError("output_schema must be a mapping or None.")
            object.__setattr__(
                self,
                "output_schema",
                _freeze_json(self.output_schema),
            )

    @classmethod
    def from_catalog(
        cls,
        *,
        request_id: str | int,
        catalog: McpToolCatalog,
        tool_name: str,
        arguments: Mapping[str, Any],
        allowed_tools: Set[str],
        limits: McpContractLimits | None = None,
    ) -> "McpToolCallRequest":
        _validate_request_id(request_id)
        if not isinstance(catalog, McpToolCatalog):
            raise TypeError("catalog must be McpToolCatalog.")
        actual_limits = limits or McpContractLimits()
        if not isinstance(actual_limits, McpContractLimits):
            raise TypeError("limits must be McpContractLimits or None.")
        if not isinstance(tool_name, str):
            raise _error(
                McpToolCallError,
                "mcp_tool_not_discovered",
                request_id=request_id,
            )
        descriptor = catalog.get(tool_name)
        if descriptor is None:
            raise _error(
                McpToolCallError,
                "mcp_tool_not_discovered",
                request_id=request_id,
            )
        if (
            isinstance(allowed_tools, (str, bytes))
            or not isinstance(allowed_tools, Set)
            or not all(isinstance(name, str) for name in allowed_tools)
        ):
            raise ValueError("allowed_tools must be a set of strings.")
        if tool_name not in allowed_tools:
            raise _error(
                McpToolCallError,
                "mcp_tool_not_allowed",
                request_id=request_id,
            )
        if not isinstance(arguments, Mapping):
            raise _error(
                McpToolCallError,
                "mcp_tool_arguments_invalid",
                request_id=request_id,
            )
        try:
            frozen_arguments = _freeze_json(arguments)
            if (
                len(_canonical_json_bytes(frozen_arguments))
                > actual_limits.max_argument_bytes
            ):
                raise _error(
                    McpToolCallError,
                    "mcp_tool_arguments_invalid",
                    request_id=request_id,
                )
            Draft202012Validator(descriptor.input_schema).validate(
                _thaw_json(frozen_arguments)
            )
        except McpToolCallError:
            raise
        except (ValueError, ValidationError) as exc:
            raise _error(
                McpToolCallError,
                "mcp_tool_arguments_invalid",
                request_id=request_id,
            ) from exc
        return cls(
            request_id=request_id,
            tool_name=tool_name,
            arguments=frozen_arguments,
            catalog_digest=catalog.digest,
            tool_schema_digest=descriptor.schema_digest,
            input_schema=descriptor.input_schema,
            output_schema=descriptor.output_schema,
        )

    def to_wire(self) -> dict[str, Any]:
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": self.request_id,
            "method": "tools/call",
            "params": {
                "name": self.tool_name,
                "arguments": _thaw_json(self.arguments),
            },
        }

    def require_current_catalog(self, catalog: McpToolCatalog) -> None:
        if not isinstance(catalog, McpToolCatalog):
            raise TypeError("catalog must be McpToolCatalog.")
        current = catalog.get(self.tool_name)
        if (
            catalog.digest != self.catalog_digest
            or current is None
            or current.schema_digest != self.tool_schema_digest
        ):
            raise _error(
                McpSchemaDriftError,
                "mcp_tool_schema_drift",
                request_id=self.request_id,
            )


@dataclass(frozen=True)
class McpToolCallResult:
    success: bool
    request_id: str | int
    tool_name: str
    content: tuple[Mapping[str, Any], ...] = field(default=(), repr=False)
    structured_content: Mapping[str, Any] | None = field(default=None, repr=False)
    error: McpErrorInfo | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.success, bool):
            raise ValueError("success must be a boolean.")
        if self.success and self.error is not None:
            raise ValueError("successful MCP results cannot carry an error.")
        if not self.success and self.error is None:
            raise ValueError("failed MCP results must carry an error.")
        _validate_request_id(self.request_id)
        if not isinstance(self.tool_name, str) or not _TOOL_NAME_PATTERN.fullmatch(
            self.tool_name
        ):
            raise ValueError("tool_name is invalid.")
        if not isinstance(self.content, tuple) or not all(
            isinstance(item, Mapping) for item in self.content
        ):
            raise ValueError("content must be a tuple of mappings.")
        object.__setattr__(
            self,
            "content",
            tuple(_freeze_json(item) for item in self.content),
        )
        if self.structured_content is not None:
            if not isinstance(self.structured_content, Mapping):
                raise ValueError("structured_content must be a mapping or None.")
            object.__setattr__(
                self,
                "structured_content",
                _freeze_json(self.structured_content),
            )
        if self.error is not None and not isinstance(self.error, McpErrorInfo):
            raise ValueError("error must be McpErrorInfo or None.")

    @classmethod
    def from_wire(
        cls,
        wire: Any,
        *,
        request: McpToolCallRequest,
        limits: McpContractLimits,
    ) -> "McpToolCallResult":
        if not isinstance(request, McpToolCallRequest):
            raise TypeError("request must be McpToolCallRequest.")
        if not isinstance(limits, McpContractLimits):
            raise TypeError("limits must be McpContractLimits.")
        try:
            payload_size = len(_canonical_json_bytes(wire))
        except ValueError as exc:
            raise _error(
                McpResultError,
                "mcp_result_invalid",
                request_id=request.request_id,
            ) from exc
        if payload_size > limits.max_result_bytes:
            raise _error(
                McpResultError,
                "mcp_result_too_large",
                request_id=request.request_id,
            )
        result = _parse_response_envelope(
            wire,
            expected_request_id=request.request_id,
        )
        _exact_fields(
            result,
            required=frozenset({"content"}),
            optional=frozenset({"structuredContent", "isError", "_meta"}),
            error_type=McpResultError,
            code="mcp_result_invalid",
            request_id=request.request_id,
        )
        is_error = result.get("isError", False)
        if not isinstance(is_error, bool):
            raise _error(
                McpResultError,
                "mcp_result_invalid",
                request_id=request.request_id,
            )
        content_raw = result["content"]
        if not isinstance(content_raw, list) or len(content_raw) > limits.max_content_items:
            raise _error(
                McpResultError,
                "mcp_result_invalid",
                request_id=request.request_id,
            )
        frozen_content: list[Mapping[str, Any]] = []
        try:
            for item in content_raw:
                item_mapping = _mapping_or_error(
                    item,
                    error_type=McpResultError,
                    code="mcp_result_invalid",
                    request_id=request.request_id,
                )
                content_type = item_mapping.get("type")
                if not isinstance(content_type, str) or not content_type.strip():
                    raise _error(
                        McpResultError,
                        "mcp_result_invalid",
                        request_id=request.request_id,
                    )
                frozen_content.append(_freeze_json(item_mapping))
        except ValueError as exc:
            raise _error(
                McpResultError,
                "mcp_result_invalid",
                request_id=request.request_id,
            ) from exc
        if is_error:
            return cls(
                success=False,
                request_id=request.request_id,
                tool_name=request.tool_name,
                error=McpErrorInfo(
                    code="mcp_tool_error",
                    retryable=False,
                    request_id=request.request_id,
                ),
            )
        structured_content = result.get("structuredContent")
        frozen_structured = None
        if structured_content is not None:
            if not isinstance(structured_content, Mapping):
                raise _error(
                    McpResultError,
                    "mcp_result_invalid",
                    request_id=request.request_id,
                )
            try:
                frozen_structured = _freeze_json(structured_content)
            except ValueError as exc:
                raise _error(
                    McpResultError,
                    "mcp_result_invalid",
                    request_id=request.request_id,
                ) from exc
        if request.output_schema is not None:
            if frozen_structured is None:
                raise _error(
                    McpResultError,
                    "mcp_result_invalid",
                    request_id=request.request_id,
                )
            try:
                Draft202012Validator(request.output_schema).validate(
                    _thaw_json(frozen_structured)
                )
            except ValidationError as exc:
                raise _error(
                    McpResultError,
                    "mcp_result_invalid",
                    request_id=request.request_id,
                ) from exc
        return cls(
            success=True,
            request_id=request.request_id,
            tool_name=request.tool_name,
            content=tuple(frozen_content),
            structured_content=frozen_structured,
        )
