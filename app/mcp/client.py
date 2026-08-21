"""MCP session state machine and discovery adapter.

This module composes the pure 7-1 envelopes with a transport.  It does not
implement reliability policy: an adapted tool handler performs one MCP call
and ``ToolRuntime`` remains the owner of retry, cache, breaker and fallback.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections.abc import Mapping, Set
from typing import Any, Callable

from app.tools.models import ToolDefinition, ToolPolicy
from app.tools.registry import ToolRegistry

from .errors import (
    McpCapabilityError,
    McpContractError,
    McpErrorInfo,
    McpRemoteError,
    McpSessionError,
    McpToolCatalogError,
    McpToolCallError,
    McpTransportTimeout,
)
from .models import (
    McpContractLimits,
    McpImplementation,
    McpInitializeRequest,
    McpInitializeResult,
    McpListToolsRequest,
    McpToolCallRequest,
    McpToolCallResult,
    McpToolCatalog,
    McpToolDescriptor,
)
from .transport import McpTransport


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _descriptor_wire(descriptor: McpToolDescriptor) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": descriptor.name,
        "description": descriptor.description,
        "inputSchema": _thaw(descriptor.input_schema),
    }
    if descriptor.title is not None:
        payload["title"] = descriptor.title
    if descriptor.output_schema is not None:
        payload["outputSchema"] = _thaw(descriptor.output_schema)
    if descriptor.annotations is not None:
        payload["annotations"] = _thaw(descriptor.annotations)
    return payload


def _catalog_wire(catalog: McpToolCatalog) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": 0,
        "result": {"tools": [_descriptor_wire(tool) for tool in catalog.tools]},
    }


def _catalog_digest(
    *,
    protocol_version: str,
    server_info: McpImplementation,
    tools: tuple[McpToolDescriptor, ...],
) -> str:
    payload = {
        "protocolVersion": protocol_version,
        "serverInfo": server_info.to_wire(),
        "tools": [
            {"name": tool.name, "schemaDigest": tool.schema_digest}
            for tool in tools
        ],
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class McpClientSession:
    """One initialize/discover/call session bound to one transport generation."""

    def __init__(
        self,
        transport: McpTransport,
        *,
        client_info: McpImplementation,
        supported_protocol_versions: Set[str],
        allowed_tools: Set[str],
        limits: McpContractLimits | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not isinstance(client_info, McpImplementation):
            raise TypeError("client_info must be McpImplementation")
        if isinstance(supported_protocol_versions, (str, bytes)) or not isinstance(
            supported_protocol_versions, Set
        ):
            raise TypeError("supported_protocol_versions must be a set")
        if not supported_protocol_versions:
            raise ValueError("supported_protocol_versions cannot be empty")
        if not all(isinstance(item, str) for item in supported_protocol_versions):
            raise ValueError("supported_protocol_versions must contain strings")
        if isinstance(allowed_tools, (str, bytes)) or not isinstance(allowed_tools, Set):
            raise TypeError("allowed_tools must be a set")
        if not all(isinstance(item, str) for item in allowed_tools):
            raise ValueError("allowed_tools must contain strings")
        self.transport = transport
        self.client_info = client_info
        self.supported_protocol_versions = frozenset(supported_protocol_versions)
        self.allowed_tools = frozenset(allowed_tools)
        self.limits = limits or McpContractLimits()
        self._clock = clock
        self._next_request_id = 0
        self._bound_generation: int | None = None
        self._initialization: McpInitializeResult | None = None
        self._catalog: McpToolCatalog | None = None

    @property
    def initialization(self) -> McpInitializeResult | None:
        return self._initialization

    @property
    def catalog(self) -> McpToolCatalog | None:
        return self._catalog

    @property
    def is_initialized(self) -> bool:
        return self._initialization is not None

    @property
    def is_discovered(self) -> bool:
        return self._catalog is not None

    def _request_id(self) -> int:
        self._next_request_id += 1
        return self._next_request_id

    def _deadline_from_clock(self, timeout_s: float) -> float:
        if isinstance(timeout_s, bool) or not isinstance(timeout_s, (int, float)):
            raise ValueError("timeout_s must be a positive number")
        if timeout_s <= 0:
            raise ValueError("timeout_s must be a positive number")
        return self._clock() + float(timeout_s)

    def _session_error(self, code: str, *, request_id: int | None = None) -> McpSessionError:
        return McpSessionError(
            McpErrorInfo(
                code=code,
                retryable=False,
                request_id=request_id,
            )
        )

    def _ensure_generation(self, *, request_id: int | None = None) -> None:
        if self._bound_generation is None:
            return
        if self.transport.generation != self._bound_generation:
            self._initialization = None
            self._catalog = None
            raise self._session_error(
                "mcp_session_restarted",
                request_id=request_id,
            )

    def _wire_request(
        self,
        wire: Mapping[str, Any],
        *,
        timeout_s: float | None = None,
        deadline_monotonic: float | None = None,
    ) -> Mapping[str, Any]:
        request_id = wire.get("id")
        if deadline_monotonic is None:
            if timeout_s is None:
                raise ValueError("timeout_s or deadline_monotonic is required")
            deadline = self._deadline_from_clock(timeout_s)
        else:
            deadline = deadline_monotonic
            if deadline <= self._clock():
                raise McpTransportTimeout(
                    McpErrorInfo(
                        code="mcp_transport_timeout",
                        retryable=True,
                        request_id=request_id,
                    )
                )
        response = self.transport.request(
            wire,
            deadline_monotonic=deadline,
        )
        if self._clock() > deadline:
            raise McpTransportTimeout(
                McpErrorInfo(
                    code="mcp_transport_timeout",
                    retryable=True,
                    request_id=request_id,
                )
            )
        return response

    def initialize(self, *, timeout_s: float = 30.0) -> McpInitializeResult:
        request = McpInitializeRequest(
            request_id=self._request_id(),
            protocol_version=sorted(self.supported_protocol_versions)[-1],
            capabilities={},
            client_info=self.client_info,
        )
        # A new initialize is the only operation allowed to bind a restarted
        # generation.  It also clears an old catalog before parsing the reply.
        self._initialization = None
        self._catalog = None
        self._bound_generation = self.transport.generation
        deadline = self._deadline_from_clock(timeout_s)
        response = self._wire_request(
            request.to_wire(),
            deadline_monotonic=deadline,
        )
        result = McpInitializeResult.from_wire(
            response,
            expected_request_id=request.request_id,
            supported_protocol_versions=self.supported_protocol_versions,
        )
        self._bound_generation = self.transport.generation
        self._initialization = result
        return result

    def discover(self, *, timeout_s: float = 30.0) -> McpToolCatalog:
        request_id = self._request_id()
        if self._initialization is None:
            raise self._session_error(
                "mcp_session_not_initialized",
                request_id=request_id,
            )
        self._ensure_generation(request_id=request_id)
        assert self._initialization is not None
        self._initialization.require_tools()
        pages: list[McpToolCatalog] = []
        cursor: str | None = None
        deadline = self._deadline_from_clock(timeout_s)
        while True:
            request = McpListToolsRequest(request_id=request_id, cursor=cursor)
            response = self._wire_request(
                request.to_wire(),
                deadline_monotonic=deadline,
            )
            page = McpToolCatalog.from_wire(
                response,
                initialization=self._initialization,
                expected_request_id=request_id,
                limits=self.limits,
            )
            pages.append(page)
            if page.next_cursor is None:
                break
            if len(pages) >= self.limits.max_tools:
                raise self._session_error(
                    "mcp_tool_catalog_too_large",
                    request_id=request_id,
                )
            cursor = page.next_cursor
            request_id = self._request_id()

        descriptors = tuple(
            descriptor
            for page in pages
            for descriptor in page.tools
        )
        if len(descriptors) > self.limits.max_tools:
            raise self._session_error(
                "mcp_tool_catalog_too_large",
                request_id=request_id,
            )
        if len(pages) > 1:
            sorted_descriptors = tuple(sorted(descriptors, key=lambda item: item.name))
            try:
                combined = McpToolCatalog(
                    protocol_version=self._initialization.protocol_version,
                    server_info=self._initialization.server_info,
                    tools=sorted_descriptors,
                    digest=_catalog_digest(
                        protocol_version=self._initialization.protocol_version,
                        server_info=self._initialization.server_info,
                        tools=sorted_descriptors,
                    ),
                )
            except ValueError as exc:
                raise McpToolCatalogError(
                    McpErrorInfo(
                        code="mcp_tool_catalog_invalid",
                        retryable=False,
                        request_id=request_id,
                    )
                ) from exc
        else:
            combined = pages[0]
        self._catalog = combined
        return combined

    def call(
        self,
        tool_name: str,
        arguments: Mapping[str, Any],
        *,
        timeout_s: float = 30.0,
    ) -> McpToolCallResult:
        request_id = self._request_id()
        if self._initialization is None:
            raise self._session_error(
                "mcp_session_not_initialized",
                request_id=request_id,
            )
        self._ensure_generation(request_id=request_id)
        if self._catalog is None:
            raise self._session_error(
                "mcp_session_not_discovered",
                request_id=request_id,
            )
        request = McpToolCallRequest.from_catalog(
            request_id=request_id,
            catalog=self._catalog,
            tool_name=tool_name,
            arguments=arguments,
            allowed_tools=self.allowed_tools,
            limits=self.limits,
        )
        # Bind the call to the exact snapshot at send time.  A refresh or
        # generation change cannot silently reinterpret these arguments.
        request.require_current_catalog(self._catalog)
        deadline = self._deadline_from_clock(timeout_s)
        response = self._wire_request(
            request.to_wire(),
            deadline_monotonic=deadline,
        )
        return McpToolCallResult.from_wire(
            response,
            request=request,
            limits=self.limits,
        )

    def to_tool_definition(
        self,
        tool_name: str,
        *,
        policy: ToolPolicy | None = None,
        version: str = "1.0.0",
    ) -> ToolDefinition:
        if self._catalog is None:
            raise self._session_error("mcp_session_not_discovered")
        descriptor = self._catalog.get(tool_name)
        if descriptor is None or tool_name not in self.allowed_tools:
            raise McpToolCallError(
                McpErrorInfo(
                    code="mcp_tool_not_allowed"
                    if descriptor is not None
                    else "mcp_tool_not_discovered",
                    retryable=False,
                )
            )
        if not re.fullmatch(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+", tool_name):
            raise McpToolCallError(
                McpErrorInfo(
                    code="mcp_tool_not_allowed",
                    retryable=False,
                )
            )
        output_schema = descriptor.output_schema or {
            "type": "object",
            "additionalProperties": True,
        }

        def handler(params: Mapping[str, Any], context: Any) -> Mapping[str, Any]:
            remaining = context.remaining_s()
            if remaining <= 0:
                raise McpTransportTimeout(
                    McpErrorInfo(
                        code="mcp_transport_timeout",
                        retryable=True,
                        request_id=None,
                    )
                )
            result = self.call(tool_name, params, timeout_s=remaining)
            if not result.success:
                assert result.error is not None
                raise McpRemoteError(result.error)
            if result.structured_content is not None:
                return _thaw(result.structured_content)
            return {"content": _thaw(result.content)}

        return ToolDefinition(
            name=tool_name,
            version=version,
            description=descriptor.description or f"Discovered MCP tool {tool_name}.",
            handler=handler,
            input_schema=_thaw(descriptor.input_schema),
            output_schema=_thaw(output_schema),
            policy=policy or ToolPolicy(),
        )

    def register_discovered_tools(
        self,
        registry: ToolRegistry,
        *,
        policy: ToolPolicy | None = None,
    ) -> tuple[ToolDefinition, ...]:
        if self._catalog is None:
            raise self._session_error("mcp_session_not_discovered")
        definitions = tuple(
            self.to_tool_definition(tool.name, policy=policy)
            for tool in self._catalog.tools
            if tool.name in self.allowed_tools
        )
        for definition in definitions:
            registry.register(definition)
        return definitions

    def close(self) -> None:
        self._initialization = None
        self._catalog = None
        self._bound_generation = None
        self.transport.close()


McpClient = McpClientSession

__all__ = ["McpClient", "McpClientSession"]
