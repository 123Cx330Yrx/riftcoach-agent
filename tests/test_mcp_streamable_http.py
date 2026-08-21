from __future__ import annotations

import json
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import pytest

from app.mcp.client import McpClientSession
from app.mcp.errors import McpTransportError, McpTransportFrameError
from app.mcp.models import McpImplementation
from app.mcp.transport import McpHttpResponse, StreamableHttpMcpTransport


PROTOCOL_VERSION = "2025-06-18"
ENDPOINT = "https://mcp-api.op.gg/mcp"


@dataclass(frozen=True)
class SentHttpRequest:
    method: str
    url: str
    headers: Mapping[str, str]
    body: bytes
    timeout_s: float


class ScriptedHttpSender:
    def __init__(self, responses: list[McpHttpResponse]) -> None:
        self.responses = list(responses)
        self.calls: list[SentHttpRequest] = []

    def __call__(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes,
        timeout_s: float,
        max_response_bytes: int,
    ) -> McpHttpResponse:
        self.calls.append(
            SentHttpRequest(
                method=method,
                url=url,
                headers=dict(headers),
                body=body,
                timeout_s=timeout_s,
            )
        )
        assert max_response_bytes > 0
        return self.responses.pop(0)


def json_response(payload: dict[str, Any], *, session: str | None = None):
    headers = {"Content-Type": "application/json"}
    if session is not None:
        headers["Mcp-Session-Id"] = session
    return McpHttpResponse(
        status=200,
        headers=headers,
        body=json.dumps(payload).encode("utf-8"),
    )


def initialize_result(*, protocol_version: str = PROTOCOL_VERSION) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "protocolVersion": protocol_version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "OP.GG MCP Server", "version": "1.0.0"},
        },
    }


def tool_descriptor() -> dict:
    return {
        "name": "lol_list_lane_meta_champions",
        "description": "Untrusted remote description.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "lang": {"type": "string"},
                "position": {
                    "type": "string",
                    "enum": ["all", "top", "mid", "jungle", "adc", "support"],
                },
                "desired_output_fields": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["desired_output_fields"],
        },
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    }


def test_streamable_http_runs_initialize_notification_discovery_call_and_close() -> None:
    session_token = "opaque-session-value"
    sender = ScriptedHttpSender(
        [
            json_response(initialize_result(), session=session_token),
            McpHttpResponse(status=202, headers={}, body=b""),
            json_response(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "result": {"tools": [tool_descriptor()]},
                }
            ),
            json_response(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "result": {
                        "content": [{"type": "text", "text": "bounded meta"}]
                    },
                }
            ),
            McpHttpResponse(status=405, headers={}, body=b""),
        ]
    )
    transport = StreamableHttpMcpTransport(ENDPOINT, sender=sender)
    client = McpClientSession(
        transport,
        client_info=McpImplementation(name="riftcoach", version="0.1.0"),
        supported_protocol_versions=frozenset({PROTOCOL_VERSION}),
        allowed_tools=frozenset({"lol_list_lane_meta_champions"}),
    )

    initialized = client.initialize(timeout_s=2)
    catalog = client.discover(timeout_s=2)
    result = client.call(
        "lol_list_lane_meta_champions",
        {"desired_output_fields": ["lang"]},
        timeout_s=2,
    )
    client.close()

    assert initialized.server_info.name == "OP.GG MCP Server"
    assert catalog.get("lol_list_lane_meta_champions") is not None
    assert result.success is True
    posted = [
        json.loads(call.body)
        for call in sender.calls
        if call.method == "POST"
    ]
    assert [payload["method"] for payload in posted] == [
        "initialize",
        "notifications/initialized",
        "tools/list",
        "tools/call",
    ]
    assert sender.calls[-1].method == "DELETE"
    for call in sender.calls[1:]:
        assert call.headers["Mcp-Session-Id"] == session_token
        assert call.headers["MCP-Protocol-Version"] == PROTOCOL_VERSION
    assert session_token not in repr(transport)


def test_streamable_http_uses_the_server_negotiated_protocol_header() -> None:
    negotiated_version = "2024-11-05"
    sender = ScriptedHttpSender(
        [
            json_response(
                initialize_result(protocol_version=negotiated_version),
                session="opaque-session-value",
            ),
            McpHttpResponse(status=202, headers={}, body=b""),
        ]
    )
    transport = StreamableHttpMcpTransport(ENDPOINT, sender=sender)
    client = McpClientSession(
        transport,
        client_info=McpImplementation(name="riftcoach", version="0.1.0"),
        supported_protocol_versions=frozenset(
            {negotiated_version, PROTOCOL_VERSION}
        ),
        allowed_tools=frozenset(),
    )

    initialized = client.initialize(timeout_s=2)

    assert initialized.protocol_version == negotiated_version
    assert json.loads(sender.calls[0].body)["params"]["protocolVersion"] == PROTOCOL_VERSION
    assert sender.calls[1].headers["MCP-Protocol-Version"] == negotiated_version


def test_streamable_http_accepts_one_bounded_sse_json_message() -> None:
    payload = {"jsonrpc": "2.0", "id": "sse-1", "result": {"tools": []}}
    sender = ScriptedHttpSender(
        [
            McpHttpResponse(
                status=200,
                headers={"Content-Type": "text/event-stream; charset=utf-8"},
                body=(
                    "event: message\n"
                    f"data: {json.dumps(payload)}\n\n"
                ).encode("utf-8"),
            )
        ]
    )
    transport = StreamableHttpMcpTransport(ENDPOINT, sender=sender)

    response = transport.request(
        {"jsonrpc": "2.0", "id": "sse-1", "method": "tools/list", "params": {}},
        deadline_monotonic=time.monotonic() + 2,
    )

    assert response == payload


@pytest.mark.parametrize(
    ("response", "expected_code"),
    [
        (
            McpHttpResponse(
                status=302,
                headers={"Location": "https://evil.invalid"},
                body=b"secret body",
            ),
            "mcp_transport_http_status",
        ),
        (
            McpHttpResponse(
                status=200,
                headers={"Content-Type": "text/html"},
                body=b"secret body",
            ),
            "mcp_transport_content_type_invalid",
        ),
        (
            McpHttpResponse(
                status=200,
                headers={
                    "Content-Type": "application/json",
                    "Mcp-Session-Id": "bad\r\nsession",
                },
                body=b"{}",
            ),
            "mcp_transport_session_invalid",
        ),
    ],
)
def test_streamable_http_projects_status_content_type_and_session_failures(
    response: McpHttpResponse,
    expected_code: str,
) -> None:
    sender = ScriptedHttpSender([response])
    transport = StreamableHttpMcpTransport(ENDPOINT, sender=sender)

    with pytest.raises((McpTransportError, McpTransportFrameError)) as caught:
        transport.request(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            deadline_monotonic=time.monotonic() + 2,
        )

    assert caught.value.info.code == expected_code
    assert "secret body" not in str(caught.value)
    assert "secret body" not in repr(caught.value.info)


def test_streamable_http_rejects_non_https_and_oversized_frames() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        StreamableHttpMcpTransport("http://mcp-api.op.gg/mcp")

    sender = ScriptedHttpSender(
        [
            McpHttpResponse(
                status=200,
                headers={"Content-Type": "application/json"},
                body=b"{" + b"x" * 200 + b"}",
            )
        ]
    )
    transport = StreamableHttpMcpTransport(
        ENDPOINT,
        sender=sender,
        max_response_bytes=128,
    )
    with pytest.raises(McpTransportFrameError) as caught:
        transport.request(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            deadline_monotonic=time.monotonic() + 2,
        )
    assert caught.value.info.code == "mcp_transport_frame_too_large"


def test_http_response_repr_and_headers_are_body_free_and_immutable() -> None:
    response = McpHttpResponse(
        status=200,
        headers={"Mcp-Session-Id": "secret-session"},
        body=b"secret response body",
    )

    assert "secret-session" not in repr(response)
    assert "secret response body" not in repr(response)
    with pytest.raises(TypeError):
        response.headers["new"] = "value"
