"""7-5 tests for real external MCP interoperability and exit evidence."""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

import pytest

from app.api.actor import ActorContext
from app.mcp.server import RiftCoachMcpServer
from app.mcp.stdio import serve_stdio
from scripts.run_mcp_interoperability_exit import validate_exit_evidence


ROOT = Path(__file__).resolve().parents[1]
EXTERNAL_CLIENT = ROOT / "experiments" / "mcp_interop" / "external_client.mjs"
SDK_PACKAGE = (
    ROOT
    / "experiments"
    / "mcp_interop"
    / "node_modules"
    / "@modelcontextprotocol"
    / "sdk"
    / "package.json"
)
SDK_LOCK = ROOT / "experiments" / "mcp_interop" / "package-lock.json"
SDK_INTEGRITY = (
    "sha512-xKd8OIzlqNzcqcNumGAa6g+PW2kjD5vrpcKOnfldAUPP3j7lnqMPwlTXQm8gF+"
    "UwH72z0lqaRbjr9hqGz0eITA=="
)


class InteropFacade:
    def recent_summary(self, *, actor: ActorContext, run_id: str):
        raise AssertionError("unexpected recent_summary call")

    def single_match_review(self, *, actor: ActorContext, run_id: str):
        raise AssertionError("unexpected single_match_review call")

    def knowledge_search(
        self,
        *,
        actor: ActorContext,
        query: str,
        top_k: int,
        filters: Mapping[str, object],
    ):
        assert actor.owner_id == "stage7-interop-owner"
        assert query == "bounded interop query"
        assert top_k == 1
        assert filters == {}
        return {
            "provider": "interop-fixture",
            "abstained": False,
            "count": 1,
            "attributions": [
                {
                    "chunk_id": "interop-chunk",
                    "source_id": "interop-source",
                    "title": "Interop fixture",
                    "version": "1.0",
                }
            ],
        }

    def report_evaluation(self, *, actor: ActorContext, run_id: str):
        raise AssertionError("unexpected report_evaluation call")


def _server() -> RiftCoachMcpServer:
    return RiftCoachMcpServer(
        facade=InteropFacade(),
        actor_provider=lambda: ActorContext(owner_id="stage7-interop-owner"),
    )


def _initialize(protocol_version: str = "2025-11-25") -> dict[str, object]:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": protocol_version,
            "capabilities": {},
            "clientInfo": {
                "name": "official-external-client",
                "version": "1.30.0",
            },
        },
    }


def test_server_negotiates_its_supported_version_with_newer_client_proposal():
    response = _server().new_session().handle(_initialize())

    assert response is not None
    assert response["result"]["protocolVersion"] == "2025-06-18"
    assert "error" not in response


def test_stdio_server_runs_full_lifecycle_and_notification_is_silent():
    frames = [
        _initialize(),
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "riftcoach.knowledge_search",
                "arguments": {"query": "bounded interop query", "top_k": 1},
            },
        },
    ]
    reader = io.BytesIO(
        b"".join(
            json.dumps(frame, separators=(",", ":")).encode("utf-8") + b"\n"
            for frame in frames
        )
    )
    writer = io.BytesIO()
    session = _server().new_session(session_id="not-persisted")

    serve_stdio(session, reader=reader, writer=writer)

    responses = [json.loads(line) for line in writer.getvalue().splitlines()]
    assert len(responses) == 3
    assert responses[0]["result"]["protocolVersion"] == "2025-06-18"
    assert len(responses[1]["result"]["tools"]) == 4
    result = responses[2]["result"]
    assert result.get("isError", False) is False
    assert result["structuredContent"]["provider"] == "interop-fixture"
    assert "owner_id" not in json.dumps(result)
    assert session.handle(
        {"jsonrpc": "2.0", "id": 4, "method": "tools/list", "params": {}}
    )["error"]["code"] == -32001


@pytest.mark.parametrize(
    "frame",
    [
        b"{not-json}\n",
        b'{"jsonrpc":"2.0","id":1,"id":2,"method":"initialize"}\n',
        b"\xff\n",
        b"[]\n",
    ],
)
def test_stdio_server_rejects_invalid_frames_without_echoing_body(frame: bytes):
    writer = io.BytesIO()

    serve_stdio(_server().new_session(), reader=io.BytesIO(frame), writer=writer)

    body = writer.getvalue().decode("utf-8")
    response = json.loads(body)
    assert response["error"]["code"] in {-32700, -32600}
    assert "not-json" not in body
    assert "initialize" not in body


def test_stdio_server_rejects_oversized_request_and_response_frames():
    oversized = b'{"private":"' + (b"x" * 200) + b'"}\n'
    request_writer = io.BytesIO()
    serve_stdio(
        _server().new_session(),
        reader=io.BytesIO(oversized),
        writer=request_writer,
        max_frame_bytes=128,
    )
    request_error = json.loads(request_writer.getvalue())
    assert request_error["error"]["code"] == -32600
    assert b"private" not in request_writer.getvalue()

    response_writer = io.BytesIO()
    serve_stdio(
        _server().new_session(),
        reader=io.BytesIO(
            json.dumps(_initialize("2025-06-18"), separators=(",", ":")).encode()
            + b"\n"
        ),
        writer=response_writer,
        max_frame_bytes=200,
    )
    response_error = json.loads(response_writer.getvalue())
    assert response_error["error"]["code"] == -32603


def _minimal_subprocess_env() -> dict[str, str]:
    env = {"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    for key in ("SYSTEMROOT", "WINDIR"):
        if value := os.environ.get(key):
            env[key] = value
    return env


def test_official_sdk_lock_identity_license_and_install_script_boundary():
    lock = json.loads(SDK_LOCK.read_text(encoding="utf-8"))
    packages = lock["packages"]
    sdk = packages["node_modules/@modelcontextprotocol/sdk"]

    assert lock["lockfileVersion"] == 3
    assert lock["packages"][""]["dependencies"] == {
        "@modelcontextprotocol/sdk": "1.30.0"
    }
    assert sdk["version"] == "1.30.0"
    assert sdk["license"] == "MIT"
    assert sdk["integrity"] == SDK_INTEGRITY
    assert all(package.get("hasInstallScript") is not True for package in packages.values())
    assert {
        package["license"]
        for package in packages.values()
        if package.get("license")
    } <= {"MIT", "ISC", "BSD-2-Clause", "BSD-3-Clause"}


def test_official_external_sdk_client_calls_riftcoach_over_real_stdio():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is unavailable")
    assert EXTERNAL_CLIENT.is_file()
    assert SDK_PACKAGE.is_file(), "run npm ci --ignore-scripts in experiments/mcp_interop"

    completed = subprocess.run(
        [
            node,
            str(EXTERNAL_CLIENT),
            "--python",
            sys.executable,
            "--repo-root",
            str(ROOT),
        ],
        cwd=ROOT,
        env=_minimal_subprocess_env(),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0
    assert completed.stderr == ""
    summary = json.loads(completed.stdout)
    assert summary["result"] == "passed"
    assert summary["body_free"] is True
    assert summary["client"]["package"] == "@modelcontextprotocol/sdk"
    assert summary["client"]["version"] == "1.30.0"
    assert summary["server"]["protocol_version"] == "2025-06-18"
    assert summary["catalog"]["tool_count"] == 4
    assert summary["call"]["tool"] == "riftcoach.knowledge_search"
    assert summary["trace"]["tools_call_calls"] == 1
    encoded = json.dumps(summary, sort_keys=True)
    for forbidden in (
        "stage7-interop-owner",
        "bounded interop query",
        "interop-chunk",
        "structuredContent",
        "session_id",
        "arguments",
    ):
        assert forbidden not in encoded


def test_exit_evidence_contract_is_body_free_and_requires_both_directions():
    payload = {
        "schema_version": "1.0",
        "result": "passed",
        "body_free": True,
        "product_sha": "a" * 40,
        "observed_window_utc": {
            "started_at": "2026-08-21T00:00:00Z",
            "ended_at": "2026-08-21T00:01:00Z",
        },
        "external_client_to_riftcoach": {
            "result": "passed",
            "trace_digest": "b" * 64,
            "tools_call_calls": 1,
        },
        "riftcoach_to_external_server": {
            "result": "passed",
            "trace_digest": "c" * 64,
            "tools_call_calls": 1,
        },
        "exit_matrix": [
            {"id": "external_client", "status": "pass"},
            {"id": "external_server", "status": "pass"},
        ],
        "external_io": {
            "opgg_tools_call_calls": 1,
            "riftcoach_tools_call_calls": 1,
            "riot_calls": 0,
            "llm_provider_calls": 0,
            "key_reads": 0,
        },
    }

    validate_exit_evidence(payload)

    leaked = json.loads(json.dumps(payload))
    leaked["external_client_to_riftcoach"]["raw_result"] = "private"
    with pytest.raises(ValueError, match="body_free"):
        validate_exit_evidence(leaked)

    partial = json.loads(json.dumps(payload))
    partial["riftcoach_to_external_server"]["result"] = "failed"
    with pytest.raises(ValueError, match="both directions"):
        validate_exit_evidence(partial)
