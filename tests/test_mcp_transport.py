from __future__ import annotations

import json
import sys
import textwrap
import time
from pathlib import Path

import pytest

from app.mcp import (
    McpCapabilityError,
    McpImplementation,
    McpRemoteError,
    McpToolCallResult,
)
from app.mcp.client import McpClientSession
from app.mcp.errors import (
    McpContractError,
    McpTransportError,
    McpTransportFrameError,
    McpTransportTimeout,
)
from app.mcp.transport import InMemoryMcpTransport, StdioMcpTransport
from app.tools.models import RetryPolicy, ToolPolicy
from app.tools.registry import ToolRegistry
from app.tools.runtime import ToolRuntime


ROOT = Path(__file__).parent
FIXTURE_PATH = ROOT / "fixtures" / "mcp_server_happy.json"


def load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def fixture_handler(fixture: dict, requests: list[dict]):
    def handle(request: dict) -> dict:
        requests.append(request)
        method = request["method"]
        request_id = request["id"]
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": fixture["protocolVersion"],
                    "capabilities": fixture["capabilities"],
                    "serverInfo": fixture["serverInfo"],
                },
            }
        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"tools": fixture["tools"]},
            }
        if method == "tools/call":
            name = request["params"]["name"]
            response = json.loads(json.dumps(fixture["callResults"][name]))
            response["structuredContent"]["echo"] = request["params"]["arguments"]["message"]
            return {"jsonrpc": "2.0", "id": request_id, "result": response}
        raise AssertionError(f"unexpected method: {method}")

    return handle


def make_client(
    transport,
    *,
    allowed_tools: set[str] | None = None,
    clock=time.monotonic,
) -> McpClientSession:
    return McpClientSession(
        transport,
        client_info=McpImplementation(name="riftcoach-test", version="1.0.0"),
        supported_protocol_versions={"2025-06-18"},
        allowed_tools=allowed_tools or {"fixture.echo"},
        clock=clock,
    )


def test_fixture_trace_initializes_discovers_and_calls_in_order():
    fixture = load_fixture()
    requests: list[dict] = []
    client = make_client(InMemoryMcpTransport(fixture_handler(fixture, requests)))

    initialized = client.initialize(timeout_s=1)
    catalog = client.discover(timeout_s=1)
    result = client.call("fixture.echo", {"message": "hello"}, timeout_s=1)

    assert initialized.protocol_version == "2025-06-18"
    assert catalog.get("fixture.echo") is not None
    assert result.success is True
    assert result.structured_content == {"echo": "hello"}
    assert [request["method"] for request in requests] == [
        "initialize",
        "tools/list",
        "tools/call",
    ]


def test_discovery_aggregates_bounded_cursor_pages_into_one_snapshot():
    fixture = load_fixture()
    second = json.loads(json.dumps(fixture["tools"][0]))
    second["name"] = "fixture.upper"
    requests: list[dict] = []

    def paged(request: dict) -> dict:
        requests.append(request)
        if request["method"] == "initialize":
            return fixture_handler(fixture, [])(request)
        if request["method"] == "tools/list":
            if request["params"].get("cursor") is None:
                result = {"tools": fixture["tools"], "nextCursor": "page-2"}
            else:
                result = {"tools": [second]}
            return {"jsonrpc": "2.0", "id": request["id"], "result": result}
        return fixture_handler(fixture, [])(request)

    client = make_client(
        InMemoryMcpTransport(paged),
        allowed_tools={"fixture.echo", "fixture.upper"},
    )
    client.initialize(timeout_s=1)
    catalog = client.discover(timeout_s=1)

    assert [tool.name for tool in catalog.tools] == ["fixture.echo", "fixture.upper"]
    assert [request["method"] for request in requests] == [
        "initialize",
        "tools/list",
        "tools/list",
    ]


def test_tool_definition_rejects_mcp_name_not_accepted_by_internal_runtime():
    fixture = load_fixture()
    fixture["tools"][0]["name"] = "Fixture.echo"
    client = make_client(
        InMemoryMcpTransport(fixture_handler(fixture, [])),
        allowed_tools={"Fixture.echo"},
    )
    client.initialize(timeout_s=1)
    client.discover(timeout_s=1)

    with pytest.raises(McpContractError) as exc_info:
        client.to_tool_definition("Fixture.echo")
    assert exc_info.value.info.code == "mcp_tool_not_allowed"


def test_discovery_requires_tools_capability():
    fixture = load_fixture()
    fixture["capabilities"] = {}
    client = make_client(InMemoryMcpTransport(fixture_handler(fixture, [])))

    client.initialize(timeout_s=1)

    with pytest.raises(McpCapabilityError) as exc_info:
        client.discover(timeout_s=1)

    assert exc_info.value.info.code == "mcp_tools_capability_missing"


def test_call_requires_discovery_and_refreshes_schema_snapshot():
    fixture = load_fixture()
    client = make_client(
        InMemoryMcpTransport(fixture_handler(fixture, [])),
    )
    client.initialize(timeout_s=1)

    with pytest.raises(McpContractError) as exc_info:
        client.call("fixture.echo", {"message": "before-list"}, timeout_s=1)
    assert exc_info.value.info.code == "mcp_session_not_discovered"

    client.discover(timeout_s=1)
    fixture["tools"][0]["inputSchema"]["properties"]["message"]["minLength"] = 2
    client.discover(timeout_s=1)
    with pytest.raises(McpContractError) as invalid:
        client.call("fixture.echo", {"message": "x"}, timeout_s=1)
    assert invalid.value.info.code == "mcp_tool_arguments_invalid"
    assert client.call("fixture.echo", {"message": "after-refresh"}, timeout_s=1).success


def test_disconnect_and_restart_fail_closed_until_reinitialize():
    fixture = load_fixture()
    transport = InMemoryMcpTransport(fixture_handler(fixture, []))
    client = make_client(transport)
    client.initialize(timeout_s=1)
    client.discover(timeout_s=1)

    transport.disconnect()
    with pytest.raises(McpTransportError) as disconnected:
        client.call("fixture.echo", {"message": "offline"}, timeout_s=1)
    assert disconnected.value.info.code == "mcp_transport_disconnected"

    transport.restart()
    with pytest.raises(McpContractError) as restarted:
        client.call("fixture.echo", {"message": "stale"}, timeout_s=1)
    assert restarted.value.info.code == "mcp_session_restarted"

    client.initialize(timeout_s=1)
    client.discover(timeout_s=1)
    assert client.call("fixture.echo", {"message": "fresh"}, timeout_s=1).success


def test_transport_deadline_is_bounded_and_body_free():
    fixture = load_fixture()

    def slow(_: dict) -> dict:
        time.sleep(0.05)
        return fixture_handler(fixture, [])({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})

    client = make_client(InMemoryMcpTransport(slow))
    with pytest.raises(McpTransportTimeout) as exc_info:
        client.initialize(timeout_s=0.001)
    assert exc_info.value.info.code == "mcp_transport_timeout"
    assert "slow" not in str(exc_info.value)


def test_adapter_maps_discovered_tool_to_tool_runtime_without_copying_reliability():
    fixture = load_fixture()
    calls = 0

    def transient(request: dict) -> dict:
        nonlocal calls
        calls += 1
        if request["method"] == "tools/call" and calls == 3:
            raise McpTransportTimeout(
                "ignored raw detail",
                request_id=request["id"],
            )
        return fixture_handler(fixture, [])(request)

    transport = InMemoryMcpTransport(transient)
    client = make_client(transport)
    client.initialize(timeout_s=1)
    client.discover(timeout_s=1)
    definition = client.to_tool_definition(
        "fixture.echo",
        policy=ToolPolicy(retry=RetryPolicy(max_attempts=2)),
    )
    registry = ToolRegistry()
    registry.register(definition)

    result = ToolRuntime(registry).execute(
        "fixture.echo",
        {"message": "runtime retry"},
    )

    assert result.success is True
    assert result.attempts == 2
    assert calls == 4  # initialize, list, and exactly two runtime attempts


def _write_stdio_fixture_server(tmp_path: Path, *, mode: str = "normal") -> list[str]:
    script = tmp_path / "mcp_fixture_server.py"
    script.write_text(
        textwrap.dedent(
            """
            import json
            import sys
            import time
            from pathlib import Path

            fixture = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
            mode = sys.argv[2]
            for line in sys.stdin:
                if mode == "malformed":
                    sys.stdout.write("not-json\\n")
                    sys.stdout.flush()
                    break
                request = json.loads(line)
                method = request["method"]
                if mode == "slow" and method == "initialize":
                    time.sleep(0.2)
                if method == "initialize":
                    result = {
                        "protocolVersion": fixture["protocolVersion"],
                        "capabilities": fixture["capabilities"],
                        "serverInfo": fixture["serverInfo"],
                    }
                elif method == "tools/list":
                    result = {"tools": fixture["tools"]}
                else:
                    result = json.loads(json.dumps(fixture["callResults"][request["params"]["name"]]))
                    result["structuredContent"]["echo"] = request["params"]["arguments"]["message"]
                sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": request["id"], "result": result}) + "\\n")
                sys.stdout.flush()
            """
        ),
        encoding="utf-8",
    )
    return [sys.executable, "-u", str(script), str(FIXTURE_PATH), mode]


def test_isolated_stdio_transport_replays_the_same_trace(tmp_path: Path):
    transport = StdioMcpTransport(_write_stdio_fixture_server(tmp_path))
    client = make_client(transport)
    try:
        client.initialize(timeout_s=2)
        client.discover(timeout_s=2)
        result = client.call("fixture.echo", {"message": "stdio"}, timeout_s=2)
        assert result.success is True
        assert result.structured_content == {"echo": "stdio"}
    finally:
        client.close()


def test_stdio_malformed_frame_is_safe_error(tmp_path: Path):
    transport = StdioMcpTransport(_write_stdio_fixture_server(tmp_path, mode="malformed"))
    client = make_client(transport)
    with pytest.raises(McpTransportFrameError) as exc_info:
        client.initialize(timeout_s=2)
    assert exc_info.value.info.code == "mcp_transport_frame_invalid"
    client.close()


def test_stdio_timeout_terminates_isolated_process(tmp_path: Path):
    transport = StdioMcpTransport(_write_stdio_fixture_server(tmp_path, mode="slow"))
    client = make_client(transport)
    with pytest.raises(McpTransportTimeout):
        client.initialize(timeout_s=0.01)
    client.close()
