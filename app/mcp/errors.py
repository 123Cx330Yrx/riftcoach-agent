"""Body-free errors for the pure MCP protocol contract boundary."""

from __future__ import annotations

import re
from dataclasses import dataclass


_ERROR_CODE_PATTERN = re.compile(r"^mcp_[a-z0-9_]{1,95}$")
_SAFE_MESSAGES = {
    "mcp_envelope_invalid": "MCP envelope is invalid.",
    "mcp_request_id_mismatch": "MCP response request id does not match.",
    "mcp_protocol_version_unsupported": "MCP protocol version is unsupported.",
    "mcp_tools_capability_missing": "MCP server did not advertise tools capability.",
    "mcp_tool_catalog_invalid": "MCP tool catalog is invalid.",
    "mcp_tool_catalog_too_large": "MCP tool catalog exceeds configured limits.",
    "mcp_tool_not_discovered": "MCP tool was not present in the discovered catalog.",
    "mcp_tool_not_allowed": "MCP tool is outside the caller allowlist.",
    "mcp_tool_arguments_invalid": "MCP tool arguments failed schema validation.",
    "mcp_tool_schema_drift": "MCP tool schema changed after discovery.",
    "mcp_result_invalid": "MCP tool result is invalid.",
    "mcp_result_too_large": "MCP tool result exceeds configured limits.",
    "mcp_tool_error": "MCP tool reported a safe execution failure.",
    "mcp_remote_error": "MCP peer returned a JSON-RPC error.",
    "mcp_session_not_initialized": "MCP session has not been initialized.",
    "mcp_session_not_discovered": "MCP session has not discovered tools.",
    "mcp_session_restarted": "MCP server restarted and the session snapshot is stale.",
    "mcp_transport_disconnected": "MCP transport is disconnected.",
    "mcp_transport_timeout": "MCP transport deadline expired.",
    "mcp_transport_frame_invalid": "MCP transport frame is invalid.",
    "mcp_transport_frame_too_large": "MCP transport frame exceeds configured limits.",
    "mcp_transport_write_failed": "MCP transport write failed.",
}


def _validate_request_id(value: str | int | None) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError("request_id must be a string, integer, or None.")
    if isinstance(value, str) and not value.strip():
        raise ValueError("request_id string must not be blank.")


@dataclass(frozen=True)
class McpErrorInfo:
    """Allowlisted operational metadata with no remote body or message fields."""

    code: str
    retryable: bool
    request_id: str | int | None = None
    remote_code: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not _ERROR_CODE_PATTERN.fullmatch(
            self.code
        ):
            raise ValueError("MCP error code is invalid.")
        if self.code not in _SAFE_MESSAGES:
            raise ValueError("MCP error code is not allowlisted.")
        if not isinstance(self.retryable, bool):
            raise ValueError("retryable must be a boolean.")
        _validate_request_id(self.request_id)
        if self.remote_code is not None and (
            isinstance(self.remote_code, bool)
            or not isinstance(self.remote_code, int)
        ):
            raise ValueError("remote_code must be an integer or None.")

    @property
    def message(self) -> str:
        return _SAFE_MESSAGES[self.code]


class McpContractError(RuntimeError):
    """Base exception whose string representation contains safe text only."""

    def __init__(self, info: McpErrorInfo) -> None:
        if not isinstance(info, McpErrorInfo):
            raise TypeError("info must be McpErrorInfo.")
        super().__init__(info.message)
        self.info = info
        self.code = info.code
        self.retryable = info.retryable
        self.request_id = info.request_id


class McpEnvelopeError(McpContractError):
    """A JSON-RPC envelope or owned MCP object is malformed."""


class McpProtocolVersionError(McpContractError):
    """The negotiated MCP protocol version is outside the allowlist."""


class McpCapabilityError(McpContractError):
    """A method was requested without its negotiated server capability."""


class McpToolCatalogError(McpContractError):
    """A tools/list result is invalid or exceeds configured limits."""


class McpToolCallError(McpContractError):
    """A tools/call request violates discovery, allowlist, or schema rules."""


class McpSchemaDriftError(McpContractError):
    """The current descriptor no longer matches the call's schema snapshot."""


class McpResultError(McpContractError):
    """A successful JSON-RPC response carries an unsafe tool result."""


class McpRemoteError(McpContractError):
    """A remote JSON-RPC error projected without message, data, or body."""


class McpTransportError(McpContractError):
    """A transport failed without exposing raw frame, process, or peer details."""

    default_code = "mcp_transport_disconnected"
    default_retryable = True

    def __init__(
        self,
        info_or_detail: McpErrorInfo | str,
        *,
        request_id: str | int | None = None,
    ) -> None:
        if isinstance(info_or_detail, McpErrorInfo):
            info = info_or_detail
        else:
            info = McpErrorInfo(
                code=self.default_code,
                retryable=self.default_retryable,
                request_id=request_id,
            )
        super().__init__(info)


class McpTransportTimeout(McpTransportError):
    """A transport request exceeded its caller-owned deadline."""

    default_code = "mcp_transport_timeout"


class McpTransportFrameError(McpTransportError):
    """A transport frame was malformed or exceeded its byte limit."""

    default_code = "mcp_transport_frame_invalid"
    default_retryable = False


class McpSessionError(McpContractError):
    """The client session state does not permit the requested operation."""
