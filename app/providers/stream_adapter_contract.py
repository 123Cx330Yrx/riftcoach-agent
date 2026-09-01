"""Offline provider-neutral contract for assembling normalized model streams.

The product's ``LLMProvider`` port is intentionally still synchronous.  This
module defines the seam a provider-specific transport adapter may use later:
it accepts already-normalized events, assembles one complete ``ChatResponse``,
and emits a body-free trace projection.  It imports no SDK, performs no I/O,
and does not change the registered provider capability flags.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from math import isfinite
from typing import Any, Literal, Protocol, runtime_checkable

from .models import ChatRequest, ChatResponse, TokenUsage, ToolCall


_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SAFE_CODE = re.compile(r"^[a-z][a-z0-9_.-]{0,95}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_FINISH_REASONS = frozenset(
    {
        "stop",
        "tool_calls",
        "length",
        "content_filter",
        "insufficient_system_resource",
    }
)
_INCOMPLETE_FINISH_REASONS = frozenset(
    {"length", "content_filter", "insufficient_system_resource"}
)
_MAX_TOOL_INDEX = 4096
_MAX_EVENTS = 131_072
_MAX_TEXT_CHARS = 4_000_000
_MAX_TOOL_CALLS = 128
_MAX_TOOL_ARGUMENT_CHARS = 256_000
_MAX_TOOL_METADATA_CHARS = 256
_MAX_JSON_DEPTH = 64

UsageState = Literal["missing", "valid"]


class StreamAdapterError(ValueError):
    """Fail-closed error raised by the normalized stream contract."""

    def __init__(self, code: str, message: str | None = None) -> None:
        if not isinstance(code, str) or not _SAFE_CODE.fullmatch(code):
            raise ValueError("stream error code must be a safe code")
        if message is not None and (
            not isinstance(message, str)
            or not _SAFE_CODE.fullmatch(message.strip())
        ):
            raise ValueError("custom stream error message must be a safe code")
        self.code = code
        # Keep the exception text body-free even if a caller supplies a
        # safe explanatory code; untrusted provider/SDK messages are rejected
        # above rather than copied into logs.
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class StreamToolCallDelta:
    """One provider-neutral fragment of a function tool call.

    Provider-specific adapters are responsible for translating vendor tool
    chunks into this shape.  ``arguments_delta`` is kept private to the
    assembler and is never copied into the public trace projection.
    """

    index: int
    call_id: str | None = None
    name: str | None = None
    arguments_delta: str | None = None

    def __post_init__(self) -> None:
        if (
            isinstance(self.index, bool)
            or not isinstance(self.index, int)
            or not 0 <= self.index <= _MAX_TOOL_INDEX
        ):
            raise ValueError("tool fragment index must be a bounded integer")
        for field_name in ("call_id", "name"):
            value = getattr(self, field_name)
            if value is not None and (
                not isinstance(value, str)
                or not value.strip()
                or len(value.strip()) > _MAX_TOOL_METADATA_CHARS
            ):
                raise ValueError(
                    f"{field_name} must be non-blank and bounded or None"
                )
        if self.arguments_delta is not None and not isinstance(
            self.arguments_delta, str
        ):
            raise ValueError("arguments_delta must be a string or None")
        if (
            self.arguments_delta is not None
            and len(self.arguments_delta) > _MAX_TOOL_ARGUMENT_CHARS
        ):
            raise ValueError("arguments_delta exceeds the hard safety bound")

    def __repr__(self) -> str:
        """Avoid putting tool argument text in accidental debug logs."""

        return (
            "StreamToolCallDelta("
            f"index={self.index}, "
            f"call_id_present={self.call_id is not None}, "
            f"name_present={self.name is not None}, "
            f"arguments_chars={len(self.arguments_delta or '')}"
            ")"
        )


@dataclass(frozen=True, slots=True)
class ProviderStreamEvent:
    """A normalized event produced by a provider-specific stream adapter."""

    content_delta: str | None = None
    reasoning_delta: str | None = None
    tool_call_deltas: tuple[StreamToolCallDelta, ...] = ()
    finish_reason: str | None = None
    usage: TokenUsage | None = None
    model: str | None = None
    sequence: int | None = None
    request_id_sha256: str | None = None
    # ``None`` is used for both an absent vendor field and an explicit JSON
    # null in the historical event shape.  These flags preserve that small
    # distinction for boundary observers without retaining vendor objects or
    # response text.  Non-None values always imply presence and are normalized
    # to ``True`` below, so existing callers remain source-compatible.
    content_observed: bool = False
    reasoning_observed: bool = False

    def __post_init__(self) -> None:
        for field_name in ("content_delta", "reasoning_delta"):
            value = getattr(self, field_name)
            if value is not None and (
                not isinstance(value, str) or len(value) > _MAX_TEXT_CHARS
            ):
                raise ValueError(
                    f"{field_name} must be a bounded string or None"
                )
        for field_name in ("content_observed", "reasoning_observed"):
            value = getattr(self, field_name)
            if not isinstance(value, bool):
                raise ValueError(f"{field_name} must be a boolean")
        if self.content_delta is not None and not self.content_observed:
            object.__setattr__(self, "content_observed", True)
        if self.reasoning_delta is not None and not self.reasoning_observed:
            object.__setattr__(self, "reasoning_observed", True)
        if not isinstance(self.tool_call_deltas, tuple) or not all(
            isinstance(delta, StreamToolCallDelta)
            for delta in self.tool_call_deltas
        ):
            raise ValueError(
                "tool_call_deltas must be a tuple of StreamToolCallDelta values"
            )
        if len(self.tool_call_deltas) > _MAX_TOOL_CALLS:
            raise ValueError("tool_call_deltas exceeds the hard safety bound")
        if self.finish_reason is not None:
            if not isinstance(self.finish_reason, str):
                raise ValueError("finish_reason must be a safe finish code")
            normalized = self.finish_reason.strip().lower()
            if not _SAFE_CODE.fullmatch(normalized):
                raise ValueError("finish_reason must be a safe finish code")
            object.__setattr__(self, "finish_reason", normalized)
        if self.usage is not None and not isinstance(self.usage, TokenUsage):
            raise ValueError("usage must be TokenUsage or None")
        if self.model is not None:
            if not isinstance(self.model, str) or not _SAFE_ID.fullmatch(
                self.model.strip()
            ):
                raise ValueError("model must be a safe identifier or None")
            object.__setattr__(self, "model", self.model.strip())
        if self.sequence is not None and (
            isinstance(self.sequence, bool)
            or not isinstance(self.sequence, int)
            or not 1 <= self.sequence <= _MAX_EVENTS
        ):
            raise ValueError("sequence must be a positive bounded integer")
        if self.request_id_sha256 is not None and (
            not isinstance(self.request_id_sha256, str)
            or not _SHA256.fullmatch(self.request_id_sha256)
        ):
            raise ValueError("request_id_sha256 must be a lowercase SHA-256")

    def __repr__(self) -> str:
        """Keep event representations body-free for safe diagnostics."""

        return (
            "ProviderStreamEvent("
            f"content_chars={len(self.content_delta or '')}, "
            f"reasoning_chars={len(self.reasoning_delta or '')}, "
            f"content_observed={self.content_observed}, "
            f"reasoning_observed={self.reasoning_observed}, "
            f"tool_delta_count={len(self.tool_call_deltas)}, "
            f"finish_reason={self.finish_reason!r}, "
            f"usage_present={self.usage is not None}, "
            f"model={self.model!r}, sequence={self.sequence}, "
            f"request_identity_present={self.request_id_sha256 is not None}"
            ")"
        )


def validate_provider_stream_event(
    event: ProviderStreamEvent,
    *,
    ordinal: int,
    max_events: int = _MAX_EVENTS,
    content_chars_before: int = 0,
    reasoning_chars_before: int = 0,
    tool_argument_chars_before: int = 0,
    max_content_chars: int = _MAX_TEXT_CHARS,
    max_reasoning_chars: int = _MAX_TEXT_CHARS,
    max_tool_calls_per_event: int = _MAX_TOOL_CALLS,
    max_tool_argument_chars: int = _MAX_TOOL_ARGUMENT_CHARS,
) -> None:
    """Run the provider-neutral, event-local safety checks once.

    Both the complete-response assembler and the candidate boundary observer
    call this helper before applying their own stateful rules.  Keeping the
    immutable event limits in one place prevents the two paths from drifting
    while allowing the observer to remain body-free.
    """

    _validate_shared_limit(max_events, _MAX_EVENTS, "stream_event_limit")
    _validate_shared_limit(max_content_chars, _MAX_TEXT_CHARS, "content_limit")
    _validate_shared_limit(max_reasoning_chars, _MAX_TEXT_CHARS, "reasoning_limit")
    _validate_shared_limit(
        max_tool_calls_per_event,
        _MAX_TOOL_CALLS,
        "tool_call_limit",
    )
    _validate_shared_limit(
        max_tool_argument_chars,
        _MAX_TOOL_ARGUMENT_CHARS,
        "tool_argument_limit",
    )
    if not isinstance(event, ProviderStreamEvent):
        raise StreamAdapterError("invalid_event")
    if (
        isinstance(ordinal, bool)
        or not isinstance(ordinal, int)
        or ordinal < 1
        or ordinal > max_events
    ):
        raise StreamAdapterError("stream_event_limit")
    if event.sequence is not None and event.sequence != ordinal:
        raise StreamAdapterError("sequence_conflict")
    if event.finish_reason is not None and event.finish_reason not in _FINISH_REASONS:
        raise StreamAdapterError("invalid_finish_reason")
    if event.usage is not None:
        _validate_usage(event.usage)
    if (
        isinstance(content_chars_before, bool)
        or not isinstance(content_chars_before, int)
        or content_chars_before < 0
        or content_chars_before + len(event.content_delta or "") > max_content_chars
    ):
        raise StreamAdapterError("content_limit")
    if (
        isinstance(reasoning_chars_before, bool)
        or not isinstance(reasoning_chars_before, int)
        or reasoning_chars_before < 0
        or reasoning_chars_before + len(event.reasoning_delta or "") > max_reasoning_chars
    ):
        raise StreamAdapterError("reasoning_limit")
    if len(event.tool_call_deltas) > max_tool_calls_per_event:
        raise StreamAdapterError("tool_call_limit")
    if (
        isinstance(tool_argument_chars_before, bool)
        or not isinstance(tool_argument_chars_before, int)
        or tool_argument_chars_before < 0
        or tool_argument_chars_before
        + sum(len(delta.arguments_delta or "") for delta in event.tool_call_deltas)
        > max_tool_argument_chars
    ):
        raise StreamAdapterError("tool_argument_limit")


@runtime_checkable
class ProviderStreamAdapter(Protocol):
    """Optional provider seam for yielding normalized events.

    This protocol is intentionally separate from ``LLMProvider``.  Defining
    it does not advertise streaming capability or make any network call.
    """

    provider_name: str
    model_name: str

    def stream_events(
        self,
        request: ChatRequest,
    ) -> Iterable[ProviderStreamEvent]:
        """Yield normalized events for one request."""


@dataclass(frozen=True, slots=True)
class StreamAssemblyTrace:
    """Body-free diagnostics for one completed normalized stream."""

    schema_version: Literal["1.0"] = "1.0"
    provider_id: str = ""
    requested_model: str = ""
    resolved_model: str = ""
    request_id_sha256: str | None = None
    chunk_count: int = 0
    content_chunk_count: int = 0
    reasoning_chunk_count: int = 0
    tool_call_chunk_count: int = 0
    tool_call_count: int = 0
    first_visible_chunk_ordinal: int | None = None
    first_reasoning_chunk_ordinal: int | None = None
    terminal_chunk_ordinal: int | None = None
    usage_chunk_ordinal: int | None = None
    finish_reason: str = ""
    usage_state: UsageState = "valid"
    complete: bool = True

    def __post_init__(self) -> None:
        if self.schema_version != "1.0":
            raise ValueError("unsupported stream trace schema")
        for field_name in (
            "provider_id",
            "requested_model",
            "resolved_model",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
                raise ValueError(f"{field_name} must be a safe identifier")
        if not isinstance(self.finish_reason, str) or not _SAFE_CODE.fullmatch(
            self.finish_reason
        ):
            raise ValueError("finish_reason must be a safe code")
        if self.finish_reason not in {"stop", "tool_calls"}:
            raise ValueError("completed trace must use a terminal finish reason")
        if self.usage_state != "valid":
            raise ValueError("completed stream trace requires valid usage")
        if self.complete is not True:
            raise ValueError("completed stream trace must be complete")
        if self.request_id_sha256 is not None and (
            not isinstance(self.request_id_sha256, str)
            or not _SHA256.fullmatch(self.request_id_sha256)
        ):
            raise ValueError("request_id_sha256 must be a lowercase SHA-256")
        for field_name in (
            "chunk_count",
            "content_chunk_count",
            "reasoning_chunk_count",
            "tool_call_chunk_count",
            "tool_call_count",
        ):
            value = getattr(self, field_name)
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(f"{field_name} must be non-negative")
        if self.chunk_count < 1 or self.chunk_count > _MAX_EVENTS:
            raise ValueError("chunk_count is outside the supported range")
        for field_name in (
            "first_visible_chunk_ordinal",
            "first_reasoning_chunk_ordinal",
            "terminal_chunk_ordinal",
            "usage_chunk_ordinal",
        ):
            value = getattr(self, field_name)
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 1 <= value <= self.chunk_count
            ):
                raise ValueError(f"{field_name} must point into the stream")
        if self.terminal_chunk_ordinal is None:
            raise ValueError("completed stream trace requires terminal ordinal")
        if self.usage_chunk_ordinal is None:
            raise ValueError("completed stream trace requires usage ordinal")
        if self.first_visible_chunk_ordinal is not None and (
            self.first_visible_chunk_ordinal > self.terminal_chunk_ordinal
        ):
            raise ValueError("first visible chunk must precede terminal")
        if self.first_reasoning_chunk_ordinal is not None and (
            self.first_reasoning_chunk_ordinal > self.terminal_chunk_ordinal
        ):
            raise ValueError("first reasoning chunk must precede terminal")
        if self.usage_chunk_ordinal < self.terminal_chunk_ordinal:
            raise ValueError("usage chunk must not precede terminal")
        if self.tool_call_count > self.tool_call_chunk_count:
            raise ValueError("tool calls cannot outnumber tool fragments")
        # Content/reasoning counters count events, while tool_call_chunk_count
        # counts individual fragments.  A single normalized event may carry
        # several parallel tool fragments, so that counter can legitimately
        # exceed chunk_count.
        if any(
            count > self.chunk_count
            for count in (
                self.content_chunk_count,
                self.reasoning_chunk_count,
            )
        ):
            raise ValueError("content/reasoning counters cannot exceed stream length")

    def as_dict(self) -> dict[str, Any]:
        """Return an explicitly allow-listed, body-free mapping."""

        return {
            "schema_version": self.schema_version,
            "provider_id": self.provider_id,
            "requested_model": self.requested_model,
            "resolved_model": self.resolved_model,
            "request_id_sha256": self.request_id_sha256,
            "chunk_count": self.chunk_count,
            "content_chunk_count": self.content_chunk_count,
            "reasoning_chunk_count": self.reasoning_chunk_count,
            "tool_call_chunk_count": self.tool_call_chunk_count,
            "tool_call_count": self.tool_call_count,
            "first_visible_chunk_ordinal": self.first_visible_chunk_ordinal,
            "first_reasoning_chunk_ordinal": self.first_reasoning_chunk_ordinal,
            "terminal_chunk_ordinal": self.terminal_chunk_ordinal,
            "usage_chunk_ordinal": self.usage_chunk_ordinal,
            "finish_reason": self.finish_reason,
            "usage_state": self.usage_state,
            "complete": self.complete,
        }


@dataclass(frozen=True, slots=True)
class StreamAssemblyResult:
    """Complete internal response plus its sanitized stream trace."""

    # The response contains model text and decoded tool arguments.  Keep it
    # out of the default representation so an accidental debug repr cannot
    # bypass the body-free trace boundary.
    response: ChatResponse = field(repr=False)
    trace: StreamAssemblyTrace


class ProviderStreamAssembler:
    """Assemble normalized events into one complete provider-neutral response.

    The assembler is deliberately single-use and fail-closed.  Callers must
    mark the source exhausted after the iterator ends; a terminal-looking
    prefix is never sufficient for completion.  A terminal event may be
    followed by exactly one Usage-only frame.  The assembler does not retry,
    recover, or expose vendor chunks.
    """

    def __init__(
        self,
        *,
        provider_id: str,
        requested_model: str,
        max_output_tokens: int | None = None,
        require_model_observation: bool = True,
        require_request_identity: bool = False,
        max_events: int = _MAX_EVENTS,
        max_content_chars: int = _MAX_TEXT_CHARS,
        max_reasoning_chars: int = _MAX_TEXT_CHARS,
        max_tool_calls: int = _MAX_TOOL_CALLS,
        max_tool_argument_chars: int = _MAX_TOOL_ARGUMENT_CHARS,
    ) -> None:
        self._provider_id = _validate_identifier(provider_id, "provider_id")
        self._requested_model = _validate_identifier(
            requested_model,
            "requested_model",
        )
        if max_output_tokens is not None and (
            isinstance(max_output_tokens, bool)
            or not isinstance(max_output_tokens, int)
            or max_output_tokens < 1
        ):
            raise ValueError("max_output_tokens must be positive or None")
        self._max_output_tokens = max_output_tokens
        self._require_model_observation = _validate_bool(
            require_model_observation,
            "require_model_observation",
        )
        self._require_request_identity = _validate_bool(
            require_request_identity,
            "require_request_identity",
        )
        self._max_events = _validate_limit(max_events, "max_events")
        self._max_content_chars = _validate_limit(
            max_content_chars,
            "max_content_chars",
        )
        self._max_reasoning_chars = _validate_limit(
            max_reasoning_chars,
            "max_reasoning_chars",
        )
        self._max_tool_calls = _validate_limit(max_tool_calls, "max_tool_calls")
        self._max_tool_argument_chars = _validate_limit(
            max_tool_argument_chars,
            "max_tool_argument_chars",
        )
        self._resolved_model: str | None = None
        self._request_id_sha256: str | None = None
        self._content_parts: list[str] = []
        self._reasoning_parts: list[str] = []
        self._content_chars = 0
        self._reasoning_chars = 0
        self._tool_argument_chars = 0
        self._tool_fragments: dict[int, dict[str, Any]] = {}
        self._finish_reason: str | None = None
        self._usage: TokenUsage | None = None
        self._chunk_count = 0
        self._content_chunk_count = 0
        self._reasoning_chunk_count = 0
        self._tool_call_chunk_count = 0
        self._first_visible_ordinal: int | None = None
        self._first_reasoning_ordinal: int | None = None
        self._terminal_ordinal: int | None = None
        self._usage_ordinal: int | None = None
        self._final_result: StreamAssemblyResult | None = None
        self._failed_code: str | None = None
        self._exhausted = False

    @property
    def request_id_sha256(self) -> str | None:
        """Return the optional body-free request identity observed so far."""

        return self._request_id_sha256

    def abort(self, code: str = "stream_aborted") -> None:
        """Poison the assembler for a transport/consumer abort."""

        if not isinstance(code, str) or not _SAFE_CODE.fullmatch(code):
            raise ValueError("abort code must be a safe code")
        if self._final_result is not None:
            raise StreamAdapterError("already_finalized")
        if self._failed_code is not None:
            if self._failed_code != code:
                raise StreamAdapterError(self._failed_code)
            return
        self._failed_code = code

    def mark_exhausted(self) -> None:
        """Seal input after the underlying iterator has reached EOF."""

        if self._final_result is not None:
            raise StreamAdapterError("already_finalized")
        if self._failed_code is not None:
            raise StreamAdapterError(self._failed_code)
        self._exhausted = True

    def accept(self, event: ProviderStreamEvent) -> None:
        """Validate and append one normalized event atomically."""

        if self._final_result is not None:
            raise StreamAdapterError("already_finalized")
        if self._failed_code is not None:
            raise StreamAdapterError(self._failed_code)
        if not isinstance(event, ProviderStreamEvent):
            self._poison("invalid_event")
        if self._exhausted:
            self._poison("stream_exhausted")
        try:
            self._accept_validated(event)
        except StreamAdapterError as error:
            if self._failed_code is None:
                self._failed_code = error.code
            raise

    def _accept_validated(self, event: ProviderStreamEvent) -> None:
        ordinal = self._chunk_count + 1
        try:
            validate_provider_stream_event(
                event,
                ordinal=ordinal,
                max_events=self._max_events,
                content_chars_before=self._content_chars,
                reasoning_chars_before=self._reasoning_chars,
                tool_argument_chars_before=self._tool_argument_chars,
                max_content_chars=self._max_content_chars,
                max_reasoning_chars=self._max_reasoning_chars,
                max_tool_calls_per_event=self._max_tool_calls,
                max_tool_argument_chars=self._max_tool_argument_chars,
            )
        except StreamAdapterError as error:
            self._poison(error.code)

        next_model = self._resolved_model
        if event.model is not None:
            if (
                self._resolved_model is not None
                and self._resolved_model != event.model
            ):
                self._poison("model_conflict")
            next_model = event.model

        if event.request_id_sha256 is not None:
            if (
                self._request_id_sha256 is not None
                and self._request_id_sha256 != event.request_id_sha256
            ):
                self._poison("request_identity_conflict")

        if self._terminal_ordinal is not None:
            if event.finish_reason is not None:
                self._poison("duplicate_terminal")
            if event.usage is None:
                self._poison("payload_after_terminal")
            if (
                event.content_observed
                or event.reasoning_observed
                or event.tool_call_deltas
            ):
                self._poison("payload_after_terminal")
            if self._usage is not None:
                self._poison("duplicate_usage")

        if event.finish_reason is not None:
            if self._finish_reason is not None:
                self._poison("duplicate_terminal")

        if event.usage is not None:
            if self._terminal_ordinal is None and event.finish_reason is None:
                self._poison("usage_before_terminal")
            if self._usage is not None:
                self._poison("duplicate_usage")

        next_content_chars = self._content_chars + len(event.content_delta or "")
        if next_content_chars > self._max_content_chars:
            self._poison("content_limit")
        next_reasoning_chars = self._reasoning_chars + len(
            event.reasoning_delta or ""
        )
        if next_reasoning_chars > self._max_reasoning_chars:
            self._poison("reasoning_limit")

        # Apply tool fragments to a copy-on-write map first.  Only indexes
        # touched by this event are copied; this keeps long argument streams
        # linear while preserving atomicity if a later fragment is malformed.
        next_tool_fragments = self._tool_fragments.copy()
        next_tool_argument_chars = self._tool_argument_chars
        copied_indexes: set[int] = set()
        for delta in event.tool_call_deltas:
            if delta.index not in copied_indexes:
                previous = self._tool_fragments.get(delta.index)
                if previous is None:
                    next_tool_fragments[delta.index] = {
                        "id": None,
                        "name": None,
                        "arguments_parts": [],
                    }
                else:
                    next_tool_fragments[delta.index] = {
                        "id": previous["id"],
                        "name": previous["name"],
                        "arguments_parts": list(previous["arguments_parts"]),
                    }
                copied_indexes.add(delta.index)
            self._apply_tool_delta(next_tool_fragments, delta)
            next_tool_argument_chars += len(delta.arguments_delta or "")
        if next_tool_argument_chars > self._max_tool_argument_chars:
            self._poison("tool_argument_limit")
        if len(next_tool_fragments) > self._max_tool_calls:
            self._poison("tool_call_limit")

        self._chunk_count = ordinal
        self._resolved_model = next_model
        if event.request_id_sha256 is not None:
            self._request_id_sha256 = event.request_id_sha256
        if event.finish_reason is not None:
            self._finish_reason = event.finish_reason
            self._terminal_ordinal = ordinal
        if event.usage is not None:
            self._usage_ordinal = ordinal
            self._usage = event.usage

        if event.content_delta is not None:
            if event.content_delta:
                self._content_parts.append(event.content_delta)
                self._content_chunk_count += 1
                self._content_chars = next_content_chars
                if (
                    self._first_visible_ordinal is None
                    and event.content_delta.strip()
                ):
                    self._first_visible_ordinal = ordinal
        if event.reasoning_delta is not None:
            if event.reasoning_delta:
                self._reasoning_parts.append(event.reasoning_delta)
                self._reasoning_chunk_count += 1
                self._reasoning_chars = next_reasoning_chars
                if self._first_reasoning_ordinal is None:
                    self._first_reasoning_ordinal = ordinal
        self._tool_fragments = next_tool_fragments
        self._tool_argument_chars = next_tool_argument_chars
        self._tool_call_chunk_count += len(event.tool_call_deltas)

    def finalize(self) -> StreamAssemblyResult:
        """Finalize only after input exhaustion and complete terminal evidence."""

        if self._final_result is not None:
            return self._final_result
        if self._failed_code is not None:
            raise StreamAdapterError(self._failed_code)
        if not self._exhausted:
            raise StreamAdapterError("stream_not_exhausted")
        try:
            return self._finalize_checked()
        except StreamAdapterError as error:
            if self._failed_code is None:
                self._failed_code = error.code
            raise

    def _finalize_checked(self) -> StreamAssemblyResult:
        if self._finish_reason is None:
            self._poison("missing_terminal")
        if self._usage is None:
            self._poison("usage_unavailable")
        if self._require_model_observation and self._resolved_model is None:
            self._poison("model_unobserved")
        if self._require_request_identity and self._request_id_sha256 is None:
            self._poison("request_identity_unobserved")
        if self._finish_reason in _INCOMPLETE_FINISH_REASONS:
            self._poison("incomplete_stream")
        if (
            self._max_output_tokens is not None
            and self._usage.output_tokens > self._max_output_tokens
        ):
            self._poison("output_budget_exceeded")

        tool_calls = self._decode_tool_calls()
        content_text = "".join(self._content_parts)
        # Use whitespace only to decide whether content is absent; preserve
        # the provider's actual visible text instead of silently rewriting it.
        content = content_text if content_text.strip() else None
        if self._finish_reason == "stop":
            if tool_calls:
                self._poison("stop_with_tool_calls")
            if content is None:
                self._poison("missing_visible_content")
        elif self._finish_reason == "tool_calls":
            if content is not None:
                self._poison("tool_calls_with_content")
            if not tool_calls:
                self._poison("missing_tool_calls")

        reasoning_text = "".join(self._reasoning_parts)
        reasoning_content = reasoning_text if reasoning_text.strip() else None
        try:
            response = ChatResponse(
                content=content,
                model=self._resolved_model or self._requested_model,
                provider=self._provider_id,
                usage=self._usage,
                tool_calls=tool_calls,
                finish_reason=self._finish_reason,
                reasoning_content=reasoning_content,
            )
        except (TypeError, ValueError):
            self._poison("invalid_assembled_response")

        trace = StreamAssemblyTrace(
            provider_id=self._provider_id,
            requested_model=self._requested_model,
            resolved_model=self._resolved_model or self._requested_model,
            request_id_sha256=self._request_id_sha256,
            chunk_count=self._chunk_count,
            content_chunk_count=self._content_chunk_count,
            reasoning_chunk_count=self._reasoning_chunk_count,
            tool_call_chunk_count=self._tool_call_chunk_count,
            tool_call_count=len(tool_calls),
            first_visible_chunk_ordinal=self._first_visible_ordinal,
            first_reasoning_chunk_ordinal=self._first_reasoning_ordinal,
            terminal_chunk_ordinal=self._terminal_ordinal,
            usage_chunk_ordinal=self._usage_ordinal,
            finish_reason=self._finish_reason,
        )
        self._final_result = StreamAssemblyResult(
            response=response,
            trace=trace,
        )
        return self._final_result

    @staticmethod
    def _apply_tool_delta(
        fragments: dict[int, dict[str, Any]],
        delta: StreamToolCallDelta,
    ) -> None:
        state = fragments.setdefault(
            delta.index,
            {"id": None, "name": None, "arguments_parts": []},
        )
        for field_name in ("call_id", "name"):
            value = getattr(delta, field_name)
            state_key = "id" if field_name == "call_id" else field_name
            if value is None:
                continue
            normalized = value.strip()
            if state[state_key] is not None and state[state_key] != normalized:
                raise StreamAdapterError("tool_call_metadata_conflict")
            state[state_key] = normalized
        if delta.arguments_delta is not None:
            state["arguments_parts"].append(delta.arguments_delta)

    def _decode_tool_calls(self) -> tuple[ToolCall, ...]:
        if not self._tool_fragments:
            return ()
        indexes = sorted(self._tool_fragments)
        if indexes != list(range(len(indexes))):
            self._poison("tool_call_index")
        decoded: list[ToolCall] = []
        seen_ids: set[str] = set()
        for index in indexes:
            state = self._tool_fragments[index]
            call_id = state["id"]
            name = state["name"]
            if not isinstance(call_id, str) or not call_id:
                self._poison("tool_call_metadata")
            if not isinstance(name, str) or not name:
                self._poison("tool_call_metadata")
            if call_id in seen_ids:
                self._poison("tool_call_id_conflict")
            seen_ids.add(call_id)
            try:
                arguments = json.loads(
                    "".join(state["arguments_parts"]),
                    object_pairs_hook=_unique_json_object,
                    parse_constant=_reject_json_constant,
                )
                _validate_json_depth(arguments)
            except (RecursionError, TypeError, ValueError):
                self._poison("tool_call_arguments")
            if not isinstance(arguments, Mapping):
                self._poison("tool_call_arguments")
            try:
                decoded.append(
                    ToolCall(
                        id=call_id,
                        name=name,
                        arguments=dict(arguments),
                    )
                )
            except (TypeError, ValueError):
                self._poison("tool_call_arguments")
        return tuple(decoded)

    def _poison(self, code: str) -> None:
        if self._failed_code is None:
            self._failed_code = code
        raise StreamAdapterError(self._failed_code)


def _validate_identifier(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value.strip()):
        raise ValueError(f"{field_name} must be a safe identifier")
    return value.strip()


def _validate_bool(value: bool, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be a boolean")
    return value


def _validate_limit(value: int, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field_name} must be a positive integer")
    upper_bounds = {
        "max_events": _MAX_EVENTS,
        "max_content_chars": _MAX_TEXT_CHARS,
        "max_reasoning_chars": _MAX_TEXT_CHARS,
        "max_tool_calls": _MAX_TOOL_CALLS,
        "max_tool_argument_chars": _MAX_TOOL_ARGUMENT_CHARS,
    }
    upper = upper_bounds.get(field_name)
    if upper is not None and value > upper:
        raise ValueError(f"{field_name} exceeds the hard safety bound")
    return value


def _validate_usage(usage: TokenUsage) -> None:
    if usage.cached_input_tokens > usage.input_tokens:
        raise StreamAdapterError("invalid_usage")


def _validate_shared_limit(value: object, upper: int, code: str) -> None:
    """Reject malformed caller limits with a safe contract code."""

    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 1
        or value > upper
    ):
        raise StreamAdapterError(code)


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"invalid JSON constant: {value}")


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON object key")
        value[key] = item
    return value


def _validate_json_depth(value: Any, *, depth: int = 0) -> None:
    if depth > _MAX_JSON_DEPTH:
        raise ValueError("JSON nesting exceeds the stream safety bound")
    if isinstance(value, float) and not isfinite(value):
        raise ValueError("JSON number must be finite")
    if isinstance(value, Mapping):
        for item in value.values():
            _validate_json_depth(item, depth=depth + 1)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _validate_json_depth(item, depth=depth + 1)
