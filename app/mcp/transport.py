"""Bounded, transport-neutral MCP message delivery.

The transport deliberately knows nothing about MCP methods or tool schemas.  It
only sends one JSON-compatible mapping and returns one mapping before the
caller-owned deadline.  Session and protocol validation live in ``client.py``.
"""

from __future__ import annotations

import json
import queue
import subprocess
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Protocol

from .errors import (
    McpErrorInfo,
    McpTransportError,
    McpTransportFrameError,
    McpTransportTimeout,
)


class McpTransport(Protocol):
    @property
    def generation(self) -> int: ...

    def request(
        self,
        message: Mapping[str, Any],
        *,
        deadline_monotonic: float,
    ) -> Mapping[str, Any]: ...

    def close(self) -> None: ...


def _transport_info(
    code: str,
    *,
    retryable: bool,
    request_id: str | int | None = None,
) -> McpErrorInfo:
    return McpErrorInfo(
        code=code,
        retryable=retryable,
        request_id=request_id,
    )


class InMemoryMcpTransport:
    """Deterministic fixture transport used to test the protocol boundary."""

    def __init__(
        self,
        handler: Callable[[Mapping[str, Any]], Mapping[str, Any]],
        *,
        clock: Callable[[], float] = time.monotonic,
        latency_s: float = 0.0,
    ) -> None:
        if not callable(handler):
            raise TypeError("handler must be callable")
        if isinstance(latency_s, bool) or not isinstance(latency_s, (int, float)):
            raise TypeError("latency_s must be a number")
        if latency_s < 0:
            raise ValueError("latency_s cannot be negative")
        self._handler = handler
        self._clock = clock
        self._latency_s = float(latency_s)
        self._open = True
        self._generation = 0
        self._lock = threading.Lock()

    @property
    def generation(self) -> int:
        return self._generation

    @property
    def is_open(self) -> bool:
        return self._open

    def open(self) -> None:
        self._open = True

    def disconnect(self) -> None:
        self._open = False

    def restart(self) -> None:
        self._generation += 1
        self._open = True

    def request(
        self,
        message: Mapping[str, Any],
        *,
        deadline_monotonic: float,
    ) -> Mapping[str, Any]:
        request_id = message.get("id") if isinstance(message, Mapping) else None
        if not self._open:
            raise McpTransportError(
                _transport_info(
                    "mcp_transport_disconnected",
                    retryable=True,
                    request_id=request_id,
                )
            )
        if self._clock() >= deadline_monotonic:
            raise McpTransportTimeout(
                _transport_info(
                    "mcp_transport_timeout",
                    retryable=True,
                    request_id=request_id,
                )
            )
        with self._lock:
            remaining = deadline_monotonic - self._clock()
            if self._latency_s > remaining:
                if remaining > 0:
                    time.sleep(remaining)
                raise McpTransportTimeout(
                    _transport_info(
                        "mcp_transport_timeout",
                        retryable=True,
                        request_id=request_id,
                    )
                )
            if self._latency_s:
                time.sleep(self._latency_s)
            if self._clock() >= deadline_monotonic:
                raise McpTransportTimeout(
                    _transport_info(
                        "mcp_transport_timeout",
                        retryable=True,
                        request_id=request_id,
                    )
                )
            try:
                response = self._handler(message)
            except (McpTransportError, McpTransportTimeout):
                raise
            except Exception as exc:
                raise McpTransportError(
                    _transport_info(
                        "mcp_transport_disconnected",
                        retryable=True,
                        request_id=request_id,
                    )
                ) from exc
        if not isinstance(response, Mapping):
            raise McpTransportFrameError(
                _transport_info(
                    "mcp_transport_frame_invalid",
                    retryable=False,
                    request_id=request_id,
                )
            )
        return response

    send = request

    def close(self) -> None:
        self._open = False


class StdioMcpTransport:
    """Isolated newline-delimited JSON transport for a local MCP process.

    The process is intentionally supplied as an explicit argv sequence.  No
    shell is involved, stderr is discarded, and only one request is in flight
    so a response can never be attributed to a different call id.
    """

    def __init__(
        self,
        command: Sequence[str],
        *,
        max_frame_bytes: int = 256 * 1024,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if isinstance(command, (str, bytes)) or not command:
            raise ValueError("command must be a non-empty argv sequence")
        if not all(isinstance(part, str) and part for part in command):
            raise ValueError("command argv entries must be non-blank strings")
        if (
            isinstance(max_frame_bytes, bool)
            or not isinstance(max_frame_bytes, int)
            or max_frame_bytes <= 0
        ):
            raise ValueError("max_frame_bytes must be a positive integer")
        self._command = tuple(command)
        self._max_frame_bytes = max_frame_bytes
        self._clock = clock
        self._process: subprocess.Popen[bytes] | None = None
        self._generation = 0
        self._lock = threading.Lock()

    @property
    def generation(self) -> int:
        return self._generation

    @property
    def is_open(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def open(self) -> None:
        if self.is_open:
            return
        self._process = subprocess.Popen(
            self._command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

    def request(
        self,
        message: Mapping[str, Any],
        *,
        deadline_monotonic: float,
    ) -> Mapping[str, Any]:
        request_id = message.get("id") if isinstance(message, Mapping) else None
        self.open()
        process = self._process
        if process is None or process.stdin is None or process.stdout is None:
            raise McpTransportError(
                _transport_info(
                    "mcp_transport_disconnected",
                    retryable=True,
                    request_id=request_id,
                )
            )
        try:
            payload = json.dumps(
                dict(message),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise McpTransportFrameError(
                _transport_info(
                    "mcp_transport_frame_invalid",
                    retryable=False,
                    request_id=request_id,
                )
            ) from exc
        if len(payload) > self._max_frame_bytes:
            raise McpTransportFrameError(
                _transport_info(
                    "mcp_transport_frame_too_large",
                    retryable=False,
                    request_id=request_id,
                )
            )
        with self._lock:
            try:
                process.stdin.write(payload + b"\n")
                process.stdin.flush()
            except (OSError, ValueError) as exc:
                self.close()
                raise McpTransportError(
                    _transport_info(
                        "mcp_transport_write_failed",
                        retryable=True,
                        request_id=request_id,
                    )
                ) from exc

            frames: queue.Queue[bytes | BaseException] = queue.Queue(maxsize=1)

            def read_one() -> None:
                try:
                    line = process.stdout.readline(self._max_frame_bytes + 1)
                    frames.put(line)
                except BaseException as exc:  # pragma: no cover - OS-specific
                    frames.put(exc)

            reader = threading.Thread(target=read_one, daemon=True)
            reader.start()
            remaining = max(0.0, deadline_monotonic - self._clock())
            try:
                frame = frames.get(timeout=remaining)
            except queue.Empty as exc:
                self.close()
                raise McpTransportTimeout(
                    _transport_info(
                        "mcp_transport_timeout",
                        retryable=True,
                        request_id=request_id,
                    )
                ) from exc
            if isinstance(frame, BaseException):
                self.close()
                raise McpTransportError(
                    _transport_info(
                        "mcp_transport_disconnected",
                        retryable=True,
                        request_id=request_id,
                    )
                ) from frame
            if not frame:
                self.close()
                raise McpTransportError(
                    _transport_info(
                        "mcp_transport_disconnected",
                        retryable=True,
                        request_id=request_id,
                    )
                )
            if len(frame) > self._max_frame_bytes:
                self.close()
                raise McpTransportFrameError(
                    _transport_info(
                        "mcp_transport_frame_too_large",
                        retryable=False,
                        request_id=request_id,
                    )
                )
        try:
            decoded = json.loads(frame.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise McpTransportFrameError(
                _transport_info(
                    "mcp_transport_frame_invalid",
                    retryable=False,
                    request_id=request_id,
                )
            ) from exc
        if not isinstance(decoded, Mapping):
            raise McpTransportFrameError(
                _transport_info(
                    "mcp_transport_frame_invalid",
                    retryable=False,
                    request_id=request_id,
                )
            )
        return decoded

    send = request

    def restart(self) -> None:
        self.close()
        self._generation += 1

    def close(self) -> None:
        process = self._process
        self._process = None
        if process is None:
            return
        try:
            if process.stdin is not None:
                process.stdin.close()
        except OSError:
            pass
        try:
            process.terminate()
            process.wait(timeout=0.5)
        except (OSError, subprocess.TimeoutExpired):
            try:
                process.kill()
                process.wait(timeout=0.5)
            except (OSError, subprocess.TimeoutExpired):
                pass
