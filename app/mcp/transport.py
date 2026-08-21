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
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Protocol
from urllib.parse import urlsplit

import requests

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


@dataclass(frozen=True)
class McpHttpResponse:
    """Bounded HTTP response projection with no endpoint-specific semantics."""

    status: int
    headers: Mapping[str, str] = field(repr=False)
    body: bytes = field(repr=False)

    def __post_init__(self) -> None:
        if isinstance(self.status, bool) or not isinstance(self.status, int):
            raise ValueError("HTTP status must be an integer")
        if not isinstance(self.headers, Mapping) or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in self.headers.items()
        ):
            raise ValueError("HTTP headers must be a string mapping")
        if not isinstance(self.body, bytes):
            raise ValueError("HTTP body must be bytes")
        object.__setattr__(self, "headers", MappingProxyType(dict(self.headers)))


class McpHttpSender(Protocol):
    def __call__(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes,
        timeout_s: float,
        max_response_bytes: int,
    ) -> McpHttpResponse: ...


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


class StreamableHttpMcpTransport:
    """Stateful MCP Streamable HTTP transport with bounded JSON/SSE frames.

    The transport owns only HTTP delivery and opaque session headers.  MCP
    method validation remains in ``McpClientSession``.  Redirects are disabled
    by the default sender so an opaque session value cannot cross origins.
    """

    _SESSION_MAX_CHARS = 1024

    def __init__(
        self,
        endpoint: str,
        *,
        sender: McpHttpSender | None = None,
        max_request_bytes: int = 256 * 1024,
        max_response_bytes: int = 1024 * 1024,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not isinstance(endpoint, str) or not endpoint.strip():
            raise ValueError("endpoint must be a non-blank HTTPS URL")
        endpoint = endpoint.strip()
        parsed = urlsplit(endpoint)
        if (
            parsed.scheme.lower() != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or bool(parsed.fragment)
        ):
            raise ValueError("MCP Streamable HTTP endpoint must use HTTPS")
        for name, value in (
            ("max_request_bytes", max_request_bytes),
            ("max_response_bytes", max_response_bytes),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if sender is not None and not callable(sender):
            raise TypeError("sender must be callable or None")
        if not callable(clock):
            raise TypeError("clock must be callable")
        self._endpoint = endpoint
        self._max_request_bytes = max_request_bytes
        self._max_response_bytes = max_response_bytes
        self._clock = clock
        self._http = requests.Session()
        self._sender = sender or self._send_with_requests
        self._session_value: str | None = None
        self._protocol_version: str | None = None
        self._generation = 0
        self._open = True
        self._lock = threading.Lock()

    @property
    def generation(self) -> int:
        return self._generation

    @property
    def is_open(self) -> bool:
        return self._open

    def _error(
        self,
        code: str,
        *,
        retryable: bool,
        request_id: str | int | None,
        frame: bool = False,
    ) -> McpTransportError:
        error_type = McpTransportFrameError if frame else McpTransportError
        return error_type(
            _transport_info(
                code,
                retryable=retryable,
                request_id=request_id,
            )
        )

    def _remaining(
        self,
        deadline_monotonic: float,
        *,
        request_id: str | int | None,
    ) -> float:
        if isinstance(deadline_monotonic, bool) or not isinstance(
            deadline_monotonic, (int, float)
        ):
            raise ValueError("deadline_monotonic must be a number")
        remaining = float(deadline_monotonic) - self._clock()
        if remaining <= 0:
            raise McpTransportTimeout(
                _transport_info(
                    "mcp_transport_timeout",
                    retryable=True,
                    request_id=request_id,
                )
            )
        return remaining

    def _headers(self, *, content: bool) -> dict[str, str]:
        headers = {
            "Accept": "application/json, text/event-stream",
            "User-Agent": "riftcoach-agent/0.1.0",
        }
        if content:
            headers["Content-Type"] = "application/json"
        if self._session_value is not None:
            headers["Mcp-Session-Id"] = self._session_value
        if self._protocol_version is not None:
            headers["MCP-Protocol-Version"] = self._protocol_version
        return headers

    def bind_protocol_version(self, protocol_version: str) -> None:
        """Bind the already validated server-negotiated MCP version."""

        if (
            not isinstance(protocol_version, str)
            or not protocol_version
            or len(protocol_version) > 64
            or any(
                ord(character) < 0x21 or ord(character) > 0x7E
                for character in protocol_version
            )
        ):
            raise ValueError("protocol_version must be bounded visible ASCII")
        self._protocol_version = protocol_version

    def _encode(
        self,
        message: Mapping[str, Any],
        *,
        request_id: str | int | None,
    ) -> bytes:
        if not isinstance(message, Mapping):
            raise self._error(
                "mcp_transport_frame_invalid",
                retryable=False,
                request_id=request_id,
                frame=True,
            )
        try:
            payload = json.dumps(
                dict(message),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError):
            raise self._error(
                "mcp_transport_frame_invalid",
                retryable=False,
                request_id=request_id,
                frame=True,
            ) from None
        if len(payload) > self._max_request_bytes:
            raise self._error(
                "mcp_transport_frame_too_large",
                retryable=False,
                request_id=request_id,
                frame=True,
            )
        return payload

    @staticmethod
    def _header(headers: Mapping[str, str], name: str) -> str | None:
        wanted = name.lower()
        for key, value in headers.items():
            if key.lower() == wanted:
                return value
        return None

    def _capture_session(
        self,
        headers: Mapping[str, str],
        *,
        request_id: str | int | None,
    ) -> None:
        value = self._header(headers, "Mcp-Session-Id")
        if value is None:
            return
        if (
            not value
            or len(value) > self._SESSION_MAX_CHARS
            or any(ord(character) < 0x21 or ord(character) > 0x7E for character in value)
        ):
            raise self._error(
                "mcp_transport_session_invalid",
                retryable=False,
                request_id=request_id,
            )
        if self._session_value is not None and value != self._session_value:
            raise self._error(
                "mcp_transport_session_invalid",
                retryable=False,
                request_id=request_id,
            )
        self._session_value = value

    def _decode_json(
        self,
        body: bytes,
        *,
        request_id: str | int | None,
    ) -> Mapping[str, Any]:
        try:
            decoded = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise self._error(
                "mcp_transport_frame_invalid",
                retryable=False,
                request_id=request_id,
                frame=True,
            ) from None
        if not isinstance(decoded, Mapping):
            raise self._error(
                "mcp_transport_frame_invalid",
                retryable=False,
                request_id=request_id,
                frame=True,
            )
        return decoded

    def _decode_sse(
        self,
        body: bytes,
        *,
        request_id: str | int | None,
    ) -> Mapping[str, Any]:
        try:
            text = body.decode("utf-8").replace("\r\n", "\n")
        except UnicodeDecodeError:
            raise self._error(
                "mcp_transport_frame_invalid",
                retryable=False,
                request_id=request_id,
                frame=True,
            ) from None
        payloads: list[str] = []
        for event in text.split("\n\n"):
            data = [line[5:].lstrip() for line in event.splitlines() if line.startswith("data:")]
            if data:
                payloads.append("\n".join(data))
        if len(payloads) != 1:
            raise self._error(
                "mcp_transport_frame_invalid",
                retryable=False,
                request_id=request_id,
                frame=True,
            )
        return self._decode_json(payloads[0].encode("utf-8"), request_id=request_id)

    def _send_with_requests(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes,
        timeout_s: float,
        max_response_bytes: int,
    ) -> McpHttpResponse:
        response = self._http.request(
            method,
            url,
            headers=dict(headers),
            data=body or None,
            timeout=timeout_s,
            allow_redirects=False,
            stream=True,
        )
        try:
            chunks: list[bytes] = []
            size = 0
            for chunk in response.iter_content(chunk_size=16 * 1024):
                if not chunk:
                    continue
                size += len(chunk)
                if size > max_response_bytes:
                    raise ValueError("response_too_large")
                chunks.append(chunk)
            return McpHttpResponse(
                status=response.status_code,
                headers=dict(response.headers),
                body=b"".join(chunks),
            )
        finally:
            response.close()

    def _send(
        self,
        *,
        method: str,
        body: bytes,
        deadline_monotonic: float,
        request_id: str | int | None,
        response_required: bool,
    ) -> Mapping[str, Any] | None:
        if not self._open:
            raise self._error(
                "mcp_transport_disconnected",
                retryable=True,
                request_id=request_id,
            )
        remaining = self._remaining(
            deadline_monotonic,
            request_id=request_id,
        )
        try:
            response = self._sender(
                method=method,
                url=self._endpoint,
                headers=self._headers(content=bool(body)),
                body=body,
                timeout_s=remaining,
                max_response_bytes=self._max_response_bytes,
            )
        except requests.Timeout:
            raise McpTransportTimeout(
                _transport_info(
                    "mcp_transport_timeout",
                    retryable=True,
                    request_id=request_id,
                )
            ) from None
        except requests.RequestException:
            raise self._error(
                "mcp_transport_disconnected",
                retryable=True,
                request_id=request_id,
            ) from None
        except ValueError:
            raise self._error(
                "mcp_transport_frame_too_large",
                retryable=False,
                request_id=request_id,
                frame=True,
            ) from None
        if self._clock() > deadline_monotonic:
            raise McpTransportTimeout(
                _transport_info(
                    "mcp_transport_timeout",
                    retryable=True,
                    request_id=request_id,
                )
            )
        if not isinstance(response, McpHttpResponse):
            raise self._error(
                "mcp_transport_frame_invalid",
                retryable=False,
                request_id=request_id,
                frame=True,
            )
        if len(response.body) > self._max_response_bytes:
            raise self._error(
                "mcp_transport_frame_too_large",
                retryable=False,
                request_id=request_id,
                frame=True,
            )
        if not response_required:
            if response.status not in {200, 202, 204}:
                raise self._error(
                    "mcp_transport_notification_failed",
                    retryable=response.status in {408, 429} or response.status >= 500,
                    request_id=request_id,
                )
            self._capture_session(response.headers, request_id=request_id)
            return None
        if response.status != 200:
            raise self._error(
                "mcp_transport_http_status",
                retryable=response.status in {408, 429} or response.status >= 500,
                request_id=request_id,
            )
        self._capture_session(response.headers, request_id=request_id)
        content_type = (self._header(response.headers, "Content-Type") or "").split(
            ";", 1
        )[0].strip().lower()
        if content_type == "application/json":
            return self._decode_json(response.body, request_id=request_id)
        if content_type == "text/event-stream":
            return self._decode_sse(response.body, request_id=request_id)
        raise self._error(
            "mcp_transport_content_type_invalid",
            retryable=False,
            request_id=request_id,
            frame=True,
        )

    def request(
        self,
        message: Mapping[str, Any],
        *,
        deadline_monotonic: float,
    ) -> Mapping[str, Any]:
        request_id = message.get("id") if isinstance(message, Mapping) else None
        payload = self._encode(message, request_id=request_id)
        with self._lock:
            response = self._send(
                method="POST",
                body=payload,
                deadline_monotonic=deadline_monotonic,
                request_id=request_id,
                response_required=True,
            )
        assert response is not None
        return response

    send = request

    def notify(
        self,
        message: Mapping[str, Any],
        *,
        deadline_monotonic: float,
    ) -> None:
        request_id = message.get("id") if isinstance(message, Mapping) else None
        payload = self._encode(message, request_id=request_id)
        with self._lock:
            self._send(
                method="POST",
                body=payload,
                deadline_monotonic=deadline_monotonic,
                request_id=request_id,
                response_required=False,
            )

    def restart(self) -> None:
        if not self._open:
            self._http = requests.Session()
        self._session_value = None
        self._protocol_version = None
        self._generation += 1
        self._open = True

    def close(self) -> None:
        if not self._open:
            return
        session_present = self._session_value is not None
        if session_present:
            try:
                response = self._sender(
                    method="DELETE",
                    url=self._endpoint,
                    headers=self._headers(content=False),
                    body=b"",
                    timeout_s=2.0,
                    max_response_bytes=self._max_response_bytes,
                )
                if isinstance(response, McpHttpResponse) and response.status not in {
                    200,
                    202,
                    204,
                    405,
                }:
                    pass
            except Exception:
                pass
        self._session_value = None
        self._protocol_version = None
        self._open = False
        self._http.close()


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
