"""Trusted Python controller for the isolated Pi Agent Core sidecar."""

from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import threading
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, ValidationError

from app.tools.registry import ToolRegistry
from app.tools.runtime import ToolRuntime

from .models import (
    MAX_FRAME_BYTES,
    PI_AGENT_CORE_VERSION,
    PROTOCOL_VERSION,
    PiContractModel,
    PiSafeEvent,
    PiScriptedUsage,
    PiSpikeRunRequest,
    PiSpikeRunResult,
    PiToolExecutionProjection,
    build_runtime_usage,
)
from .protocol import PiProtocolError, decode_frame, encode_frame


_MAX_STDERR_BYTES = 8 * 1024
_SAFE_TOOL_FAILURE_CODES = frozenset(
    {
        "circuit_open",
        "fallback_failed",
        "invalid_tool_input",
        "invalid_tool_output",
        "retry_budget_exhausted",
        "tool_execution_failed",
        "tool_not_found",
    }
)


class PiSidecarError(RuntimeError):
    """Controller failure with a stable public-safe code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class _PiChildResult(PiContractModel):
    status: Literal["completed", "stopped", "failed"]
    stop_reason: Literal[
        "final_response",
        "max_iterations",
        "max_tool_calls",
        "duplicate_tool_call",
        "tool_not_allowed",
        "invalid_tool_input",
        "tool_failed",
        "provider_error",
        "provider_aborted",
        "context_budget_exceeded",
        "timeout",
        "protocol_error",
        "process_error",
    ]
    iterations: int = Field(ge=0, le=20)
    final_text: str | None = None
    error_code: str | None = None
    provider_calls_attempted: int = Field(ge=0)
    response_usages: tuple[PiScriptedUsage | None, ...] = ()
    tool_executions: tuple[PiToolExecutionProjection, ...] = ()


def default_sidecar_path() -> Path:
    return Path(__file__).resolve().parents[3] / "experiments" / "pi_runtime" / "sidecar.mjs"


def build_safe_environment(source: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return the tiny environment needed to start Node without credentials."""

    source = source or os.environ
    names = (
        "PATH",
        "SystemRoot",
        "WINDIR",
        "ComSpec",
        "PATHEXT",
        "TEMP",
        "TMP",
        "TMPDIR",
        "LANG",
        "LC_ALL",
    )
    safe = {name: source[name] for name in names if source.get(name)}
    safe["RIFTCOACH_PI_SPIKE"] = "1"
    return safe


class PiSidecarController:
    """Run one no-I/O Pi process while Python keeps policy and ToolRuntime."""

    def __init__(
        self,
        *,
        tool_registry: ToolRegistry,
        tool_runtime: ToolRuntime,
        sidecar_path: Path | None = None,
        node_executable: str | None = None,
        use_permission_model: bool = True,
        clock=time.monotonic,
    ) -> None:
        self.tool_registry = tool_registry
        self.tool_runtime = tool_runtime
        self.sidecar_path = (sidecar_path or default_sidecar_path()).resolve()
        self.node_executable = node_executable or shutil.which("node")
        self.use_permission_model = use_permission_model
        self._clock = clock

    def run(self, request: PiSpikeRunRequest) -> PiSpikeRunResult:
        started = self._clock()
        deadline = started + request.policy.timeout_s
        events: list[PiSafeEvent] = []
        local_tools: list[PiToolExecutionProjection] = []
        provider_attempts = 0
        response_usages: tuple[PiScriptedUsage | None, ...] = ()
        process: subprocess.Popen[bytes] | None = None
        frames: queue.Queue[tuple[str, Any]] = queue.Queue()

        try:
            self._validate_tool_contract(request)
            process = self._start_process(frames)
            self._write_start(process, request)
            child: _PiChildResult | None = None
            stderr_data = b""

            while child is None:
                remaining = deadline - self._clock()
                if remaining <= 0:
                    raise PiSidecarError("timeout")
                try:
                    kind, payload = frames.get(timeout=min(remaining, 0.1))
                except queue.Empty:
                    continue

                if kind == "stderr":
                    stderr_data = payload
                    continue
                if kind == "stdout_eof":
                    raise PiSidecarError("process_error")
                if kind == "stdout_oversize":
                    raise PiSidecarError("frame_too_large")
                if kind != "stdout":
                    raise PiSidecarError("process_error")

                frame = self._decode_child_frame(payload, request.run_id)
                frame_type = frame["type"]
                if frame_type == "event":
                    event = self._parse_event(frame)
                    events.append(event)
                    if event.event_type == "provider_started":
                        provider_attempts = max(provider_attempts, event.ordinal)
                    continue
                if frame_type == "tool.request":
                    projection = self._handle_tool_request(
                        process,
                        frame,
                        request,
                        len(local_tools) + 1,
                        timeout_cap_s=remaining,
                    )
                    local_tools.append(projection)
                    continue
                if frame_type == "protocol.error":
                    raise PiSidecarError(str(frame.get("error_code", "protocol_error")))
                if frame_type != "run.result":
                    raise PiSidecarError("unsupported_frame_type")

                try:
                    # As with events, the child result is a JSON payload.  JSON
                    # mode is required for strict nested models such as the
                    # ``PiScriptedUsage`` entries in ``response_usages``.
                    result_payload = json.dumps(
                        frame.get("result"),
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                    child = _PiChildResult.model_validate_json(result_payload)
                except ValidationError:
                    raise PiSidecarError("invalid_result") from None
                response_usages = child.response_usages
                provider_attempts = child.provider_calls_attempted

            self._close_stdin(process)
            remaining = max(0.05, deadline - self._clock())
            try:
                return_code = process.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                raise PiSidecarError("timeout") from None
            stderr_data = self._collect_stderr(frames, stderr_data)
            if return_code != 0:
                raise PiSidecarError("process_error")
            if stderr_data:
                raise PiSidecarError("unexpected_stderr")
            if tuple(child.tool_executions) != tuple(local_tools):
                raise PiSidecarError("tool_projection_mismatch")

            usage = build_runtime_usage(
                provider_calls_attempted=provider_attempts,
                response_usages=response_usages,
                tool_executions=tuple(local_tools),
            )
            return PiSpikeRunResult(
                run_id=request.run_id,
                status=child.status,
                stop_reason=child.stop_reason,
                iterations=child.iterations,
                final_text=child.final_text,
                error_code=child.error_code,
                usage=usage,
                safe_events=tuple(events),
                tool_executions=tuple(local_tools),
            )
        except PiSidecarError as exc:
            if process is not None:
                self._terminate(process)
            if not response_usages:
                response_usages = ()
            reason, status = _controller_failure_mapping(exc.code)
            usage = build_runtime_usage(
                provider_calls_attempted=provider_attempts,
                response_usages=response_usages,
                tool_executions=tuple(local_tools),
            )
            return PiSpikeRunResult(
                run_id=request.run_id,
                status=status,
                stop_reason=reason,
                iterations=min(provider_attempts, request.policy.max_iterations),
                error_code=exc.code,
                usage=usage,
                safe_events=tuple(events),
                tool_executions=tuple(local_tools),
            )
        except Exception:
            if process is not None:
                self._terminate(process)
            usage = build_runtime_usage(
                provider_calls_attempted=provider_attempts,
                response_usages=response_usages,
                tool_executions=tuple(local_tools),
            )
            return PiSpikeRunResult(
                run_id=request.run_id,
                status="failed",
                stop_reason="process_error",
                iterations=min(provider_attempts, request.policy.max_iterations),
                error_code="process_error",
                usage=usage,
                safe_events=tuple(events),
                tool_executions=tuple(local_tools),
            )

    def _validate_tool_contract(self, request: PiSpikeRunRequest) -> None:
        try:
            definition = self.tool_registry.get("knowledge.search")
        except Exception:
            raise PiSidecarError("tool_not_found") from None
        declared = request.allowed_tools[0]
        if (
            definition.name != declared.name
            or definition.version != declared.version
            or _canonical_json(definition.input_schema)
            != _canonical_json(declared.input_schema)
        ):
            raise PiSidecarError("tool_contract_mismatch")

    def _start_process(self, frames: queue.Queue[tuple[str, Any]]):
        if not self.node_executable:
            raise PiSidecarError("node_not_found")
        if not self.sidecar_path.is_file():
            raise PiSidecarError("sidecar_not_found")
        args = [self.node_executable]
        if self.use_permission_model:
            args.extend(
                [
                    "--permission",
                    f"--allow-fs-read={self.sidecar_path.parent}",
                ]
            )
        args.append(str(self.sidecar_path))
        try:
            process = subprocess.Popen(
                args,
                cwd=str(self.sidecar_path.parent),
                env=build_safe_environment(),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except OSError:
            raise PiSidecarError("process_error") from None
        assert process.stdout is not None
        assert process.stderr is not None
        threading.Thread(
            target=_read_stdout,
            args=(process.stdout, frames),
            daemon=True,
        ).start()
        threading.Thread(
            target=_read_stderr,
            args=(process.stderr, frames),
            daemon=True,
        ).start()
        return process

    def _write_start(self, process, request: PiSpikeRunRequest) -> None:
        frame = encode_frame(
            {
                "protocol_version": PROTOCOL_VERSION,
                "type": "run.start",
                "run_id": request.run_id,
                "request": request.model_dump(mode="json"),
            }
        )
        self._write(process, frame)

    def _handle_tool_request(
        self,
        process,
        frame: Mapping[str, Any],
        request: PiSpikeRunRequest,
        expected_ordinal: int,
        *,
        timeout_cap_s: float,
    ) -> PiToolExecutionProjection:
        if frame.get("name") != "knowledge.search":
            raise PiSidecarError("tool_not_allowed")
        if frame.get("ordinal") != expected_ordinal:
            raise PiSidecarError("tool_ordinal_mismatch")
        arguments = frame.get("arguments")
        if not isinstance(arguments, Mapping):
            raise PiSidecarError("invalid_tool_input")
        try:
            result = self.tool_runtime.execute(
                "knowledge.search",
                dict(arguments),
                metadata={
                    "pi_runtime_spike": True,
                    "run_id": request.run_id,
                    "tool_call_id": frame.get("request_id"),
                },
                timeout_cap_s=timeout_cap_s,
            )
        except Exception:
            raise PiSidecarError("tool_execution_failed") from None

        failure_code = None
        if not result.success:
            raw_code = result.error.code if result.error is not None else None
            failure_code = (
                raw_code if raw_code in _SAFE_TOOL_FAILURE_CODES else "tool_failed"
            )
        projection = PiToolExecutionProjection(
            tool_name=result.tool_name,
            tool_version=result.tool_version,
            ordinal=expected_ordinal,
            success=result.success,
            failure_code=failure_code,
            attempts=result.attempts,
            latency_ms=result.latency_ms,
            cached=result.cached,
            fallback_used=result.fallback_used,
        )
        payload = {
            "protocol_version": PROTOCOL_VERSION,
            "type": "tool.response",
            "run_id": request.run_id,
            "request_id": frame.get("request_id"),
            "ordinal": expected_ordinal,
            "result": {
                "success": result.success,
                "tool_name": result.tool_name,
                "tool_version": result.tool_version,
                "data": dict(result.data or {}),
                "error_code": failure_code,
                "attempts": result.attempts,
                "latency_ms": result.latency_ms,
                "cached": result.cached,
                "fallback_used": result.fallback_used,
            },
        }
        self._write(process, encode_frame(payload))
        return projection

    def _decode_child_frame(
        self,
        payload: bytes,
        run_id: str,
    ) -> dict[str, Any]:
        try:
            frame = decode_frame(payload)
        except PiProtocolError as exc:
            raise PiSidecarError(exc.code) from None
        if frame.get("run_id") != run_id:
            raise PiSidecarError("run_id_mismatch")
        return frame

    def _parse_event(self, frame: Mapping[str, Any]) -> PiSafeEvent:
        try:
            # Frames have crossed a JSON boundary.  Use Pydantic's JSON mode so
            # enum values such as ``"complete"`` are decoded into the strict
            # ``TokenObservation`` type; ``model_validate(dict)`` would treat
            # them as already-typed Python values and reject them under the
            # contract's strict configuration.
            event_payload = json.dumps(
                frame.get("event"),
                ensure_ascii=False,
                separators=(",", ":"),
            )
            return PiSafeEvent.model_validate_json(event_payload)
        except ValidationError:
            raise PiSidecarError("invalid_event") from None

    @staticmethod
    def _write(process, payload: bytes) -> None:
        if process.stdin is None:
            raise PiSidecarError("process_error")
        try:
            process.stdin.write(payload)
            process.stdin.flush()
        except (BrokenPipeError, OSError):
            raise PiSidecarError("process_error") from None

    @staticmethod
    def _close_stdin(process) -> None:
        if process.stdin is not None:
            try:
                process.stdin.close()
            except OSError:
                pass

    @staticmethod
    def _collect_stderr(frames, current: bytes) -> bytes:
        # stdout and stderr are read by separate daemon threads, so the EOF
        # marker can arrive before the stderr reader has published its result.
        # Drain a bounded settling window instead of sampling one queue item;
        # otherwise a child that wrote stderr could be incorrectly accepted.
        deadline = time.monotonic() + 0.2
        pending: list[tuple[str, Any]] = []
        stderr_data = current
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                kind, payload = frames.get(timeout=remaining)
            except queue.Empty:
                break
            if kind == "stderr":
                stderr_data = payload
                # The stderr reader publishes exactly once after EOF, so its
                # bounded payload is complete and no settling delay remains.
                break
            elif kind == "stdout_eof":
                continue
            else:
                pending.append((kind, payload))
        for item in pending:
            frames.put(item)
        return stderr_data

    @staticmethod
    def _terminate(process) -> None:
        PiSidecarController._close_stdin(process)
        if process.poll() is not None:
            return
        try:
            process.terminate()
            process.wait(timeout=0.5)
        except (OSError, subprocess.TimeoutExpired):
            try:
                process.kill()
                process.wait(timeout=0.5)
            except (OSError, subprocess.TimeoutExpired):
                pass


def _controller_failure_mapping(code: str):
    if code == "timeout":
        return "timeout", "stopped"
    policy_codes = {
        "tool_not_allowed",
        "invalid_tool_input",
        "duplicate_tool_call",
        "max_tool_calls",
        "max_iterations",
        "context_budget_exceeded",
    }
    stopped_policy_codes = {
        "max_tool_calls",
        "max_iterations",
        "duplicate_tool_call",
        "context_budget_exceeded",
    }
    if code in policy_codes:
        return code, "stopped" if code in stopped_policy_codes else "failed"
    protocol_codes = {
        "invalid_event",
        "invalid_result",
        "unsupported_frame_type",
        "run_id_mismatch",
        "tool_ordinal_mismatch",
        "tool_contract_mismatch",
        "frame_too_large",
        "invalid_json",
        "invalid_frame",
        "protocol_version_mismatch",
        "unexpected_stderr",
        "tool_not_found",
    }
    reason = "protocol_error" if code in protocol_codes else "process_error"
    return reason, "failed"


def _read_stdout(stream, frames) -> None:
    while True:
        line = stream.readline(MAX_FRAME_BYTES + 1)
        if not line:
            frames.put(("stdout_eof", None))
            return
        if len(line) > MAX_FRAME_BYTES or not line.endswith(b"\n"):
            frames.put(("stdout_oversize", None))
            return
        frames.put(("stdout", line))


def _read_stderr(stream, frames) -> None:
    data = stream.read(_MAX_STDERR_BYTES + 1)
    frames.put(("stderr", data[:_MAX_STDERR_BYTES]))


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
