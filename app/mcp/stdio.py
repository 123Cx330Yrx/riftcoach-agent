"""Bounded newline-delimited stdio adapter for the RiftCoach MCP Server."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, BinaryIO

from .server import McpServerSession


DEFAULT_MAX_STDIO_FRAME_BYTES = 256 * 1024
_MIN_STDIO_FRAME_BYTES = 128


def _rpc_error(code: int, message: str) -> dict[str, object]:
    return {
        "jsonrpc": "2.0",
        "id": None,
        "error": {"code": code, "message": message},
    }


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON object key")
        value[key] = item
    return value


def _decode_frame(frame: bytes) -> Mapping[str, Any]:
    try:
        decoded = json.loads(
            frame.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                ValueError("non-finite JSON number")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError("invalid JSON frame") from exc
    if not isinstance(decoded, Mapping):
        raise TypeError("JSON-RPC frame must be an object")
    return decoded


def _encode_response(response: Mapping[str, Any]) -> bytes:
    try:
        return json.dumps(
            dict(response),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid JSON response") from exc


def _write_response(
    writer: BinaryIO,
    response: Mapping[str, Any],
    *,
    max_frame_bytes: int,
) -> bool:
    try:
        payload = _encode_response(response)
        if len(payload) > max_frame_bytes:
            payload = _encode_response(
                _rpc_error(-32603, "MCP response exceeded the stdio frame limit.")
            )
        writer.write(payload + b"\n")
        writer.flush()
    except (OSError, ValueError):
        return False
    return True


def _discard_to_newline(reader: BinaryIO, *, chunk_size: int = 8192) -> None:
    while True:
        chunk = reader.readline(chunk_size)
        if not chunk or chunk.endswith(b"\n"):
            return


def serve_stdio(
    session: McpServerSession,
    *,
    reader: BinaryIO,
    writer: BinaryIO,
    max_frame_bytes: int = DEFAULT_MAX_STDIO_FRAME_BYTES,
) -> None:
    """Serve one MCP session until EOF without writing logs or remote bodies.

    The official MCP stdio transport uses one JSON-RPC object per line.  A
    malformed frame receives a stable body-free error; an oversized frame is
    discarded through its newline so its tail cannot become another request.
    """

    if not isinstance(session, McpServerSession):
        raise TypeError("session must be McpServerSession")
    if not hasattr(reader, "readline") or not hasattr(writer, "write"):
        raise TypeError("reader and writer must be binary streams")
    if (
        isinstance(max_frame_bytes, bool)
        or not isinstance(max_frame_bytes, int)
        or max_frame_bytes < _MIN_STDIO_FRAME_BYTES
    ):
        raise ValueError("max_frame_bytes must be an integer of at least 128")

    try:
        while True:
            frame = reader.readline(max_frame_bytes + 2)
            if not frame:
                break
            if len(frame) > max_frame_bytes + 1 or not frame.endswith(b"\n"):
                if not frame.endswith(b"\n"):
                    _discard_to_newline(reader)
                if not _write_response(
                    writer,
                    _rpc_error(-32600, "MCP stdio frame exceeded the limit."),
                    max_frame_bytes=max_frame_bytes,
                ):
                    break
                continue
            payload = frame[:-1]
            if payload.endswith(b"\r"):
                payload = payload[:-1]
            if len(payload) > max_frame_bytes:
                if not _write_response(
                    writer,
                    _rpc_error(-32600, "MCP stdio frame exceeded the limit."),
                    max_frame_bytes=max_frame_bytes,
                ):
                    break
                continue
            try:
                message = _decode_frame(payload)
            except TypeError:
                response: Mapping[str, Any] = _rpc_error(
                    -32600, "Invalid MCP JSON-RPC request."
                )
            except ValueError:
                response = _rpc_error(-32700, "Invalid MCP JSON frame.")
            else:
                response = session.handle(message)
                if response is None:
                    continue
            if not _write_response(
                writer,
                response,
                max_frame_bytes=max_frame_bytes,
            ):
                break
    finally:
        session.close()


__all__ = ["DEFAULT_MAX_STDIO_FRAME_BYTES", "serve_stdio"]
