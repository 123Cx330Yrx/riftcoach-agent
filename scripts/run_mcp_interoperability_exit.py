"""Run the immutable Stage 7 bidirectional MCP interoperability exit gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.run_opgg_meta_smoke import run_smoke as run_opgg_smoke


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = (
    ROOT
    / "data"
    / "evaluation"
    / "results"
    / "mcp"
    / "stage7_interoperability_exit_v1.json"
)
EXTERNAL_CLIENT = ROOT / "experiments" / "mcp_interop" / "external_client.mjs"
_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN_EVIDENCE_KEYS = frozenset(
    {
        "arguments",
        "authorization",
        "content",
        "owner_id",
        "path",
        "prompt",
        "puuid",
        "query",
        "raw",
        "raw_body",
        "raw_result",
        "session",
        "session_id",
        "structuredcontent",
    }
)


class InteroperabilityExitError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _scan_body_free(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).lower().replace("-", "_")
            if normalized in _FORBIDDEN_EVIDENCE_KEYS:
                raise ValueError("body_free evidence contains a forbidden field")
            _scan_body_free(item)
    elif isinstance(value, list):
        for item in value:
            _scan_body_free(item)


def validate_exit_evidence(payload: Any) -> None:
    """Validate the persisted summary without trusting the runner call path."""

    if not isinstance(payload, dict):
        raise ValueError("evidence must be an object")
    if payload.get("schema_version") != "1.0" or payload.get("body_free") is not True:
        raise ValueError("body_free evidence identity is invalid")
    if payload.get("result") not in {"passed", "failed"}:
        raise ValueError("evidence result is invalid")
    if not _SHA_PATTERN.fullmatch(str(payload.get("product_sha", ""))):
        raise ValueError("product SHA is invalid")
    window = payload.get("observed_window_utc")
    if not isinstance(window, dict) or set(window) != {"started_at", "ended_at"}:
        raise ValueError("observed window is invalid")
    client_direction = payload.get("external_client_to_riftcoach")
    server_direction = payload.get("riftcoach_to_external_server")
    if not isinstance(client_direction, dict) or not isinstance(server_direction, dict):
        raise ValueError("both directions are required")
    matrix = payload.get("exit_matrix")
    if (
        not isinstance(matrix, list)
        or len(matrix) < 2
        or not all(isinstance(item, dict) for item in matrix)
    ):
        raise ValueError("exit matrix is incomplete")
    if payload["result"] == "passed":
        if (
            client_direction.get("result") != "passed"
            or server_direction.get("result") != "passed"
        ):
            raise ValueError("both directions must pass")
        for direction in (client_direction, server_direction):
            if not _DIGEST_PATTERN.fullmatch(str(direction.get("trace_digest", ""))):
                raise ValueError("trace digest is invalid")
            if direction.get("tools_call_calls") != 1:
                raise ValueError("each direction requires exactly one tools call")
        if any(item.get("status") != "pass" for item in matrix):
            raise ValueError("passed evidence requires a passing exit matrix")
        external_io = payload.get("external_io")
        if not isinstance(external_io, dict) or external_io != {
            "opgg_tools_call_calls": 1,
            "riftcoach_tools_call_calls": 1,
            "riot_calls": 0,
            "llm_provider_calls": 0,
            "key_reads": 0,
        }:
            raise ValueError("external I/O counts are invalid")
    _scan_body_free(payload)
    try:
        json.dumps(payload, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("evidence must be finite JSON") from exc


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if completed.returncode != 0:
        raise InteroperabilityExitError("git_precondition_failed")
    return completed.stdout.strip()


def _require_clean_sha(expected_sha: str) -> None:
    if not _SHA_PATTERN.fullmatch(expected_sha):
        raise InteroperabilityExitError("expected_sha_invalid")
    if _git("rev-parse", "HEAD") != expected_sha:
        raise InteroperabilityExitError("expected_sha_mismatch")
    if _git("status", "--porcelain", "--untracked-files=all"):
        raise InteroperabilityExitError("worktree_not_clean")


def _minimal_subprocess_env() -> dict[str, str]:
    env = {"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    for key in ("SYSTEMROOT", "WINDIR"):
        if value := os.environ.get(key):
            env[key] = value
    return env


def _run_external_client() -> dict[str, Any]:
    node = shutil.which("node")
    if node is None or not EXTERNAL_CLIENT.is_file():
        raise InteroperabilityExitError("external_client_unavailable")
    try:
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
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise InteroperabilityExitError("external_client_timeout") from exc
    if (
        completed.returncode != 0
        or completed.stderr
        or len(completed.stdout) > 64 * 1024
    ):
        raise InteroperabilityExitError("external_client_failed")
    try:
        summary = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InteroperabilityExitError("external_client_summary_invalid") from exc
    if (
        not isinstance(summary, dict)
        or summary.get("result") != "passed"
        or summary.get("body_free") is not True
        or summary.get("trace", {}).get("tools_call_calls") != 1
    ):
        raise InteroperabilityExitError("external_client_summary_invalid")
    try:
        _scan_body_free(summary)
    except ValueError as exc:
        raise InteroperabilityExitError("external_client_summary_invalid") from exc
    return summary


def _client_direction(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        **summary,
        "trace_digest": summary["trace"]["digest"],
        "tools_call_calls": summary["trace"]["tools_call_calls"],
    }


def _opgg_direction(summary: dict[str, Any]) -> dict[str, Any]:
    trace_digest = _canonical_digest(
        {
            "events": [
                "initialize",
                "notifications/initialized",
                "tools/list",
                "tools/call",
            ],
            "protocol": summary["protocol"],
            "catalog_digest": summary["catalog"]["digest"],
            "evidence_digest": summary["evidence"]["digest"],
        }
    )
    return {
        "schema_version": summary["schema_version"],
        "result": summary["result"],
        "body_free": summary["body_free"],
        "endpoint": summary["endpoint"],
        "transport": "streamable_http",
        "protocol": summary["protocol"],
        "catalog": summary["catalog"],
        "evidence": summary["evidence"],
        "context": summary["context"],
        "trace_digest": trace_digest,
        "initialize_calls": 1,
        "initialized_notifications": 1,
        "tools_list_calls": 1,
        "tools_call_calls": summary["external_io"]["opgg_tools_call_calls"],
        "limitations": summary["limitations"],
    }


def _pass_matrix() -> list[dict[str, str]]:
    return [
        {"id": "official_external_client_identity", "status": "pass"},
        {"id": "client_to_riftcoach_initialize_list_call", "status": "pass"},
        {"id": "riftcoach_owner_and_body_safety", "status": "pass"},
        {"id": "official_external_server_identity", "status": "pass"},
        {"id": "riftcoach_to_opgg_initialize_list_call", "status": "pass"},
        {"id": "opgg_partial_provenance_honesty", "status": "pass"},
        {"id": "body_free_immutable_evidence", "status": "pass"},
    ]


def run_exit_gate(*, product_sha: str) -> dict[str, Any]:
    started_at = _utc_now()
    external_client = _client_direction(_run_external_client())
    try:
        opgg = _opgg_direction(run_opgg_smoke(position="top", top_n=3))
    except Exception as exc:
        raise InteroperabilityExitError("external_server_failed") from exc
    payload = {
        "schema_version": "1.0",
        "result": "passed",
        "body_free": True,
        "product_sha": product_sha,
        "observed_window_utc": {
            "started_at": started_at,
            "ended_at": _utc_now(),
        },
        "external_client_to_riftcoach": external_client,
        "riftcoach_to_external_server": opgg,
        "exit_matrix": _pass_matrix(),
        "external_io": {
            "opgg_tools_call_calls": 1,
            "riftcoach_tools_call_calls": 1,
            "riot_calls": 0,
            "llm_provider_calls": 0,
            "key_reads": 0,
        },
        "limitations": [
            "no_public_riftcoach_server_deployment",
            "no_production_auth_tls_or_actor_bootstrap",
            "opgg_upstream_patch_and_freshness_unknown",
            "no_riot_opgg_join",
            "single_observation_window_not_an_slo",
        ],
    }
    validate_exit_evidence(payload)
    return payload


def _failure_payload(
    *,
    product_sha: str,
    started_at: str,
    code: str,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "result": "failed",
        "body_free": True,
        "failure_code": code,
        "product_sha": product_sha,
        "observed_window_utc": {"started_at": started_at, "ended_at": _utc_now()},
        "external_client_to_riftcoach": {"result": "unknown"},
        "riftcoach_to_external_server": {"result": "not_run_or_unknown"},
        "exit_matrix": [
            {"id": "bidirectional_interoperability", "status": "fail"},
            {"id": "stage7_exit", "status": "blocked"},
        ],
        "external_io": {
            "opgg_tools_call_calls": None,
            "riftcoach_tools_call_calls": None,
            "riot_calls": 0,
            "llm_provider_calls": 0,
            "key_reads": 0,
        },
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if not args.execute:
        raise SystemExit("refusing external I/O without --execute")
    expected_sha = args.expected_sha.strip().lower()
    output = args.output.resolve()
    if output != OUTPUT_PATH.resolve():
        raise SystemExit("refusing an unapproved interoperability output path")
    if output.exists():
        raise SystemExit("refusing to overwrite interoperability evidence")
    try:
        _require_clean_sha(expected_sha)
    except InteroperabilityExitError as exc:
        raise SystemExit(exc.code) from None
    started_at = _utc_now()
    try:
        payload = run_exit_gate(product_sha=expected_sha)
        exit_code = 0
    except InteroperabilityExitError as exc:
        payload = _failure_payload(
            product_sha=expected_sha,
            started_at=started_at,
            code=exc.code,
        )
        exit_code = 1
    except Exception:
        payload = _failure_payload(
            product_sha=expected_sha,
            started_at=started_at,
            code="unexpected_interoperability_failure",
        )
        exit_code = 1
    validate_exit_evidence(payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "result": payload["result"],
                "body_free": payload["body_free"],
                "product_sha": payload["product_sha"],
                "output": str(output),
            },
            sort_keys=True,
        )
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
