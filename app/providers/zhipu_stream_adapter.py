"""Explicit, provider-local translation from Zhipu stream chunks to neutral events.

The normal RiftCoach provider port is synchronous.  This module is a narrow
candidate seam for callers that explicitly ask a :class:`ZhipuProvider` for a
stream adapter.  It does not advertise a streaming capability, retry a
request, or wire the stream into the AgentLoop.  The provider-specific part of
the job is limited to validating the OpenAI-compatible chunk shape and
translating it into ``ProviderStreamEvent`` values; the neutral assembler
continues to own completion and privacy boundaries.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass, replace
from hashlib import sha256
from threading import Lock
from typing import Any, Literal, Protocol, TypeAlias, runtime_checkable

from .errors import ProviderError
from .models import ChatRequest, TokenUsage
from .stream_adapter_contract import (
    ProviderStreamAssembler,
    ProviderStreamEvent,
    StreamAdapterError,
    StreamAssemblyResult,
    StreamToolCallDelta,
)


_MAX_TOOL_METADATA_CHARS = 256
_MAX_REQUEST_ID_CHARS = 512
_MAX_TOOL_CALL_DELTAS_PER_EVENT = 128
_EXPECTED_PROVIDER_NAME = "zhipu"

ZhipuCloseResourceState: TypeAlias = Literal[
    "not_observed", "closed", "failed"
]
ZhipuCloseCompositeState: TypeAlias = Literal[
    "not_observed", "closed", "failed"
]
_ZHIPU_CLOSE_STATES = frozenset({"not_observed", "closed", "failed"})


@dataclass(frozen=True, slots=True)
class ZhipuStreamCloseReport:
    """Body-free cleanup facts for one explicitly owned candidate stream.

    ``sdk_stream_state`` refers to the outer SDK stream wrapper, while
    ``iterator_state`` refers to the iterator obtained from it.  This is not
    a claim about a deeper HTTP response unless the SDK hook itself exposes
    that fact.  A provider may return the same object for both roles;
    ``shared_resource`` makes that aliasing explicit so two role fields are
    never mistaken for two physical close operations.  This report is an
    in-memory provider seam only.  The versioned candidate receipt
    deliberately keeps its legacy composite ``close_state`` until a
    separately reviewed schema is introduced.
    """

    iterator_state: ZhipuCloseResourceState = "not_observed"
    sdk_stream_state: ZhipuCloseResourceState = "not_observed"
    composite_state: ZhipuCloseCompositeState = "not_observed"
    shared_resource: bool = False

    def __post_init__(self) -> None:
        for field_name in (
            "iterator_state",
            "sdk_stream_state",
            "composite_state",
        ):
            value = getattr(self, field_name)
            if value not in _ZHIPU_CLOSE_STATES:
                raise ValueError(f"{field_name} is not a supported close state")
        if not isinstance(self.shared_resource, bool):
            raise TypeError("shared_resource must be a boolean")
        if self.composite_state == "failed" and not (
            self.iterator_state == "failed"
            or self.sdk_stream_state == "failed"
        ):
            raise ValueError("failed composite state needs a failed resource")
        if self.composite_state == "closed" and (
            self.iterator_state != "closed"
            or self.sdk_stream_state != "closed"
        ):
            raise ValueError("closed composite state needs closed resources")

    @property
    def close_failed(self) -> bool:
        """Whether at least one owned resource failed its close operation."""

        return self.composite_state == "failed"

    def as_dict(self) -> dict[str, object]:
        """Return the small allow-listed projection used by offline tests."""

        return {
            "iterator_state": self.iterator_state,
            "sdk_stream_state": self.sdk_stream_state,
            "composite_state": self.composite_state,
            "shared_resource": self.shared_resource,
        }


@runtime_checkable
class _ZhipuStreamProvider(Protocol):
    """Private provider port used by the explicit adapter seam."""

    provider_name: str
    model_name: str

    def _open_stream_for_adapter(
        self,
        request: ChatRequest,
        *,
        tool_stream: bool,
        include_usage_tail: bool = False,
    ) -> tuple[Iterable[Any], Callable[[str], str]]:
        """Open one raw stream and return a request-local tool-name decoder."""


class ZhipuStreamSession:
    """Eager, owned Zhipu stream used by the candidate deadline seam.

    The OpenAI-compatible SDK exposes a synchronous iterator and a response
    close hook. This wrapper makes ownership explicit: ``cancel`` is
    idempotent and requests a close of the raw response, while ``close``
    releases both the iterator and outer stream exactly once. The candidate
    hard-deadline contract still requires the concrete SDK close operation to
    be non-blocking and to wake a pending read; that property is a separate
    provider-level verification gate, not assumed from this wrapper alone.
    It does not retry and never stores provider payloads outside the event
    being translated.
    """

    def __init__(
        self,
        adapter: "ZhipuStreamAdapter",
        request: ChatRequest,
        *,
        include_usage_tail: bool,
    ) -> None:
        self._adapter = adapter
        self._request = request
        self._include_usage_tail = include_usage_tail
        self._raw_stream: Iterable[Any] | None = None
        self._raw_iterator: Iterator[Any] | None = None
        self._decode_tool_name: Callable[[str], str] | None = None
        self._ordinal = 0
        self._cancelled = False
        self._closed = False
        self._close_failed = False
        self._resources_shared = False
        self._close_report = ZhipuStreamCloseReport()
        self._lock = Lock()
        self._open()

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def close_failed(self) -> bool:
        """Whether any owned raw resource reported a close failure."""

        return self._close_failed

    @property
    def close_report(self) -> ZhipuStreamCloseReport:
        """Return body-free per-resource cleanup facts for this session."""

        return self._close_report

    def __iter__(self) -> "ZhipuStreamSession":
        return self

    def __next__(self) -> ProviderStreamEvent:
        if self._closed or self._cancelled:
            raise StopIteration
        iterator = self._raw_iterator
        decode_tool_name = self._decode_tool_name
        if iterator is None or decode_tool_name is None:
            raise StreamAdapterError("zhipu_stream_open")
        try:
            chunk = next(iterator)
        except StopIteration:
            raise
        except (GeneratorExit, KeyboardInterrupt, SystemExit):
            raise
        except StreamAdapterError:
            raise
        except ProviderError:
            raise
        except Exception as error:
            translated = _translate_provider_error(self._adapter._provider, error)
            if translated is not None:
                raise translated from None
            raise StreamAdapterError("zhipu_stream_read") from None
        self._ordinal += 1
        event = _translate_chunk(
            chunk,
            decode_tool_name=decode_tool_name,
            ordinal=self._ordinal,
        )
        if event.model is not None and event.model != self._adapter.model_name:
            raise StreamAdapterError("zhipu_model_mismatch")
        return event

    def cancel(self, code: str = "elapsed_limit") -> None:
        """Request cancellation and run the owned cleanup path once.

        The report records cleanup attempts but does not claim that a vendor
        close operation was non-blocking or woke a pending read.  Those are
        provider-level facts that still require an explicit real observation.
        """

        if not isinstance(code, str) or not re.fullmatch(
            r"^[a-z][a-z0-9_.-]{0,95}$", code
        ):
            raise StreamAdapterError("zhipu_cancel_code")
        with self._lock:
            if self._cancelled:
                return
            self._cancelled = True
        # ``close`` is deliberately idempotent. If the SDK reports a close
        # error, let the supervisor record it as a secondary cleanup failure.
        self.close()

    def close(self) -> None:
        """Release raw iterator and stream once, without leaking SDK text."""

        with self._lock:
            if self._closed:
                return
            self._closed = True
            raw_iterator = self._raw_iterator
            raw_stream = self._raw_stream
        close_failed = False
        iterator_state: ZhipuCloseResourceState = "not_observed"
        sdk_stream_state: ZhipuCloseResourceState = "not_observed"
        control_error: BaseException | None = None
        seen: set[int] = set()
        resources = (
            ("iterator", raw_iterator),
            ("sdk_stream", raw_stream),
        )
        for role, resource in resources:
            if resource is None or id(resource) in seen:
                continue
            seen.add(id(resource))
            try:
                state = _close_resource_state(resource)
            except (GeneratorExit, KeyboardInterrupt, SystemExit):
                state = "failed"
                close_failed = True
                if control_error is None:
                    control_error = sys.exc_info()[1]
            if role == "iterator":
                iterator_state = state
            else:
                sdk_stream_state = state
            if state == "failed":
                # A hostile SDK getter/close hook must not escape with body
                # text; retain only the safe failure bit.
                close_failed = True
        if raw_iterator is not None and raw_iterator is raw_stream:
            sdk_stream_state = iterator_state
        if close_failed:
            composite_state: ZhipuCloseCompositeState = "failed"
        elif iterator_state == "closed" and sdk_stream_state == "closed":
            composite_state = "closed"
        else:
            # A resource without a close/context-manager hook was not
            # observed as released.  Preserve the legacy no-error behavior,
            # but do not call that an observed composite close.
            composite_state = "not_observed"
        self._raw_iterator = None
        self._raw_stream = None
        with self._lock:
            self._close_failed = close_failed
            self._close_report = ZhipuStreamCloseReport(
                iterator_state=iterator_state,
                sdk_stream_state=sdk_stream_state,
                composite_state=composite_state,
                shared_resource=(raw_iterator is not None and raw_iterator is raw_stream),
            )
        if control_error is not None:
            raise control_error
        if close_failed:
            raise StreamAdapterError("zhipu_stream_close")

    def _open(self) -> None:
        try:
            raw_stream, decode_tool_name = self._adapter._provider._open_stream_for_adapter(
                self._request,
                tool_stream=self._adapter._tool_stream,
                include_usage_tail=self._include_usage_tail,
            )
        except StreamAdapterError:
            raise
        except ProviderError:
            raise
        except ValueError:
            raise StreamAdapterError("zhipu_stream_open") from None
        except Exception:
            raise StreamAdapterError("zhipu_stream_open") from None
        if raw_stream is None or not callable(decode_tool_name):
            raise StreamAdapterError("zhipu_stream_open")
        try:
            raw_iterator = iter(raw_stream)
        except Exception:
            _close_stream(raw_stream)
            raise StreamAdapterError("zhipu_stream_read") from None
        self._raw_stream = raw_stream
        self._raw_iterator = raw_iterator
        self._resources_shared = raw_iterator is raw_stream
        self._close_report = replace(
            self._close_report,
            shared_resource=self._resources_shared,
        )
        self._decode_tool_name = decode_tool_name


class ZhipuStreamAdapter:
    """Translate one explicitly requested Zhipu stream into neutral events.

    ``tool_stream`` is bound when the adapter is created, so a caller cannot
    accidentally change the request shape halfway through one stream.  The
    adapter is intentionally not an ``LLMProvider`` and has no implicit retry
    or recovery path.
    """

    def __init__(
        self,
        provider: _ZhipuStreamProvider,
        *,
        tool_stream: bool = False,
        default_max_output_tokens: int | None = None,
    ) -> None:
        if not isinstance(provider, _ZhipuStreamProvider):
            raise TypeError("provider must expose the explicit Zhipu stream port")
        if getattr(provider, "provider_name", None) != _EXPECTED_PROVIDER_NAME:
            raise ValueError("provider must be zhipu")
        if not isinstance(tool_stream, bool):
            raise ValueError("tool_stream must be a boolean")
        provider_bound_cap = _provider_bound_output_cap(provider)
        if default_max_output_tokens is not None:
            _validate_positive_limit(
                default_max_output_tokens,
                "default_max_output_tokens",
            )
            if (
                provider_bound_cap is not None
                and default_max_output_tokens > provider_bound_cap
            ):
                raise ValueError(
                    "default_max_output_tokens exceeds the provider-bound cap"
                )
        elif provider_bound_cap is not None:
            # Do not let the public constructor bypass a trusted profile just
            # because the caller did not use ZhipuProvider.stream_adapter().
            default_max_output_tokens = provider_bound_cap
        self._provider = provider
        self.provider_name = _safe_identifier(provider.provider_name, "provider_name")
        self.model_name = _safe_identifier(provider.model_name, "model_name")
        self._tool_stream = tool_stream
        self._default_max_output_tokens = default_max_output_tokens

    @property
    def tool_stream(self) -> bool:
        """Whether this adapter emits a tool-enabled request shape."""

        return self._tool_stream

    @property
    def default_max_output_tokens(self) -> int | None:
        """The trusted provider-bound output cap, if one is available."""

        return self._default_max_output_tokens

    def _effective_output_cap(
        self,
        request: ChatRequest,
        *,
        explicit_cap: int | None,
    ) -> int | None:
        """Return the tightest trusted/request cap for one candidate turn."""

        request_cap = request.max_tokens
        if request_cap is not None:
            _validate_positive_limit(request_cap, "request.max_tokens")
        if explicit_cap is not None:
            _validate_positive_limit(explicit_cap, "max_output_tokens")
        cap = explicit_cap
        if cap is None:
            cap = self._default_max_output_tokens
        if request_cap is not None:
            cap = request_cap if cap is None else min(cap, request_cap)
        return cap

    def _bound_request(
        self,
        request: ChatRequest,
        *,
        cap: int | None = None,
    ) -> ChatRequest:
        """Clamp the transport request to the adapter's trusted output cap."""

        effective_cap = self._effective_output_cap(
            request,
            explicit_cap=cap,
        )
        if effective_cap is None or (
            request.max_tokens is not None
            and request.max_tokens <= effective_cap
        ):
            return request
        return replace(request, max_tokens=effective_cap)

    def stream_events(
        self,
        request: ChatRequest,
    ) -> Iterable[ProviderStreamEvent]:
        """Yield body-free normalized events for one raw Zhipu stream.

        The returned generator closes the vendor iterator in ``finally``.  A
        normal iterator exhaustion is deliberately left to the caller (or to
        :meth:`assemble`) to seal with ``mark_exhausted()``; an exception is
        never mistaken for EOF.
        """

        if not isinstance(request, ChatRequest):
            raise TypeError("request must be a ChatRequest")
        return self._iter_events(self._bound_request(request))

    def stream_session(
        self,
        request: ChatRequest,
        *,
        include_usage_tail: bool = False,
    ) -> "ZhipuStreamSession":
        """Open an owned, explicitly cancellable candidate stream session.

        This is separate from ``stream_events`` so existing provider callers
        retain their lazy-generator behavior.  The session opens eagerly,
        owns the vendor iterator/response, and exposes idempotent
        ``cancel``/``close`` methods for the evaluation hard-deadline seam.
        ``include_usage_tail`` is opt-in and only changes the provider payload
        for callers that explicitly request a Usage-only terminal tail.
        """

        if not isinstance(request, ChatRequest):
            raise TypeError("request must be a ChatRequest")
        if not isinstance(include_usage_tail, bool):
            raise ValueError("include_usage_tail must be a boolean")
        return ZhipuStreamSession(
            self,
            self._bound_request(request),
            include_usage_tail=include_usage_tail,
        )

    def assemble(
        self,
        request: ChatRequest,
        *,
        max_output_tokens: int | None = None,
        require_request_identity: bool = True,
    ) -> StreamAssemblyResult:
        """Consume one stream and return a complete response plus safe trace.

        This helper performs exactly one stream open.  It does not retry,
        recover, invoke tools, or turn a partial stream into a successful
        response.  ``max_output_tokens`` is an explicit caller cap; when it is
        omitted, a trusted provider-bound cap is used if available.
        """

        if not isinstance(request, ChatRequest):
            raise TypeError("request must be a ChatRequest")
        if not isinstance(require_request_identity, bool):
            raise ValueError("require_request_identity must be a boolean")
        effective_cap = (
            self._default_max_output_tokens
            if max_output_tokens is None
            else max_output_tokens
        )
        if effective_cap is not None:
            _validate_positive_limit(effective_cap, "max_output_tokens")
        if (
            self._default_max_output_tokens is not None
            and max_output_tokens is not None
            and max_output_tokens > self._default_max_output_tokens
        ):
            raise ValueError("max_output_tokens exceeds the provider-bound cap")

        # The caller's request is itself a lower bound on what the transport
        # may ask for.  Pass the tightest cap into the provider as well as the
        # assembler so a generous vendor response cannot spend past it.
        effective_cap = self._effective_output_cap(
            request,
            explicit_cap=effective_cap,
        )
        stream_request = self._bound_request(request, cap=effective_cap)

        assembler = ProviderStreamAssembler(
            provider_id=self.provider_name,
            requested_model=self.model_name,
            max_output_tokens=effective_cap,
            require_request_identity=require_request_identity,
        )
        events: Iterator[ProviderStreamEvent] | None = None
        try:
            events = iter(self.stream_events(stream_request))
            for event in events:
                assembler.accept(event)
        except BaseException:
            # The assembler must not remain usable as an accidental recovery
            # path after an SDK, iterator, cancellation, or translation error.
            try:
                assembler.abort("stream_aborted")
            except StreamAdapterError:
                pass
            raise
        finally:
            close_failed = _close_iterator(events)
            if close_failed and sys.exc_info()[0] is None:
                try:
                    assembler.abort("stream_aborted")
                except StreamAdapterError:
                    pass
                raise StreamAdapterError("zhipu_stream_close")

        # Only a normally exhausted iterator reaches this point.  If a caller
        # closes the generator or an iterator raises, the branch above runs.
        assembler.mark_exhausted()
        result = assembler.finalize()
        validate_response = getattr(
            self._provider,
            "_validate_stream_response_for_adapter",
            None,
        )
        if callable(validate_response):
            try:
                validate_response(result.response)
            except ProviderError:
                raise
            except Exception:
                raise StreamAdapterError("zhipu_response_validation") from None
        return result

    def _iter_events(
        self,
        request: ChatRequest,
    ) -> Iterator[ProviderStreamEvent]:
        raw_stream: Iterable[Any] | None = None
        raw_iterator: Iterator[Any] | None = None
        decode_tool_name: Callable[[str], str] | None = None
        opening = True
        try:
            try:
                raw_stream, decode_tool_name = (
                    self._provider._open_stream_for_adapter(
                        request,
                        tool_stream=self._tool_stream,
                    )
                )
            except ProviderError:
                raise
            except ValueError:
                # Provider-side validation messages are not part of the
                # neutral error contract; expose only a safe adapter code.
                raise StreamAdapterError("zhipu_stream_open") from None
            except Exception:
                raise StreamAdapterError("zhipu_stream_open") from None

            if raw_stream is None or not callable(decode_tool_name):
                raise StreamAdapterError("zhipu_stream_open")
            opening = False
            try:
                raw_iterator = iter(raw_stream)
            except Exception:
                raise StreamAdapterError("zhipu_stream_read") from None
            for ordinal, chunk in enumerate(raw_iterator, start=1):
                event = _translate_chunk(
                    chunk,
                    decode_tool_name=decode_tool_name,
                    ordinal=ordinal,
                )
                if event.model is not None and event.model != self.model_name:
                    raise StreamAdapterError("zhipu_model_mismatch")
                yield event
        except StreamAdapterError:
            raise
        except ProviderError:
            raise
        except (GeneratorExit, KeyboardInterrupt, SystemExit):
            raise
        except ValueError:
            if opening:
                raise StreamAdapterError("zhipu_stream_open") from None
            raise StreamAdapterError("zhipu_stream_read") from None
        except Exception as error:
            # Preserve the provider's existing typed error taxonomy when a
            # vendor iterator exposes one; otherwise keep a neutral safe code.
            translated = _translate_provider_error(self._provider, error)
            if translated is not None:
                raise translated from None
            # Never copy an SDK/HTTP exception or its body into diagnostics.
            raise StreamAdapterError("zhipu_stream_read") from None
        finally:
            close_failed = _close_stream(raw_iterator)
            if raw_iterator is not raw_stream:
                close_failed = _close_stream(raw_stream) or close_failed
            if close_failed and sys.exc_info()[0] is None:
                raise StreamAdapterError("zhipu_stream_close")


def _translate_chunk(
    chunk: Any,
    *,
    decode_tool_name: Callable[[str], str],
    ordinal: int,
) -> ProviderStreamEvent:
    """Project one OpenAI-compatible Zhipu chunk into safe neutral fields."""

    try:
        raw_model = _read_field(chunk, "model")
        if raw_model is not None and (
            not isinstance(raw_model, str) or not raw_model.strip()
        ):
            raise StreamAdapterError("zhipu_chunk_shape")

        raw_request_id = _read_field(chunk, "id")
        if raw_request_id is not None and (
            not isinstance(raw_request_id, str) or not raw_request_id.strip()
        ):
            raise StreamAdapterError("zhipu_chunk_shape")
        if (
            isinstance(raw_request_id, str)
            and len(raw_request_id.strip()) > _MAX_REQUEST_ID_CHARS
        ):
            raise StreamAdapterError("zhipu_chunk_shape")
        request_id_sha256 = (
            sha256(raw_request_id.encode("utf-8")).hexdigest()
            if raw_request_id is not None
            else None
        )

        choices = _read_field(chunk, "choices")
        if not isinstance(choices, (list, tuple)):
            raise StreamAdapterError("zhipu_choices_shape")
        raw_usage = _read_field(chunk, "usage")
        if not choices:
            # Zhipu's usage-only tail uses an empty choices collection.  An
            # empty frame without Usage is not a successful EOF signal.
            if raw_usage is None:
                raise StreamAdapterError("zhipu_empty_choices")
            return ProviderStreamEvent(
                usage=_normalize_usage(raw_usage),
                model=raw_model,
                sequence=ordinal,
                request_id_sha256=request_id_sha256,
            )
        if len(choices) != 1:
            raise StreamAdapterError("zhipu_choices_shape")

        choice = choices[0]
        delta = _read_field(choice, "delta")
        if delta is None:
            raise StreamAdapterError("zhipu_delta_shape")
        content_observed, content = _read_field_with_presence(delta, "content")
        reasoning_observed, reasoning = _read_field_with_presence(
            delta, "reasoning_content"
        )
        if content is not None and not isinstance(content, str):
            raise StreamAdapterError("zhipu_content_shape")
        if reasoning is not None and not isinstance(reasoning, str):
            raise StreamAdapterError("zhipu_reasoning_shape")

        finish_reason = _read_field(choice, "finish_reason")
        if finish_reason is not None and not isinstance(finish_reason, str):
            raise StreamAdapterError("zhipu_finish_shape")

        raw_tool_calls = _read_field(delta, "tool_calls")
        tool_deltas: list[StreamToolCallDelta] = []
        if raw_tool_calls is not None:
            try:
                calls = iter(raw_tool_calls)
            except TypeError:
                raise StreamAdapterError("zhipu_tool_shape") from None
            for call_ordinal, raw_call in enumerate(calls, start=1):
                if call_ordinal > _MAX_TOOL_CALL_DELTAS_PER_EVENT:
                    raise StreamAdapterError("zhipu_tool_shape")
                tool_deltas.append(
                    _translate_tool_call(raw_call, decode_tool_name)
                )

        usage = _normalize_usage(raw_usage) if raw_usage is not None else None
        return ProviderStreamEvent(
            content_delta=content,
            reasoning_delta=reasoning,
            tool_call_deltas=tuple(tool_deltas),
            finish_reason=finish_reason,
            usage=usage,
            model=raw_model,
            sequence=ordinal,
            request_id_sha256=request_id_sha256,
            content_observed=content_observed,
            reasoning_observed=reasoning_observed,
        )
    except StreamAdapterError:
        raise
    except (TypeError, ValueError):
        # Event constructors and vendor objects are intentionally hidden from
        # the public failure surface.
        raise StreamAdapterError("zhipu_chunk_shape") from None


def _translate_tool_call(
    raw_call: Any,
    decode_tool_name: Callable[[str], str],
) -> StreamToolCallDelta:
    index = _read_field(raw_call, "index")
    if isinstance(index, bool) or not isinstance(index, int) or index < 0:
        raise StreamAdapterError("zhipu_tool_shape")
    call_type = _read_field(raw_call, "type")
    if call_type is not None and call_type != "function":
        raise StreamAdapterError("zhipu_tool_shape")

    call_id = _read_field(raw_call, "id")
    if call_id is not None and (
        not isinstance(call_id, str)
        or not call_id.strip()
        or len(call_id.strip()) > _MAX_TOOL_METADATA_CHARS
    ):
        raise StreamAdapterError("zhipu_tool_shape")

    function = _read_field(raw_call, "function")
    if function is None:
        raise StreamAdapterError("zhipu_tool_shape")
    provider_name = _read_field(function, "name")
    if provider_name is not None and (
        not isinstance(provider_name, str)
        or not provider_name.strip()
        or len(provider_name.strip()) > _MAX_TOOL_METADATA_CHARS
    ):
        raise StreamAdapterError("zhipu_tool_shape")
    internal_name: str | None = None
    if provider_name is not None:
        try:
            internal_name = decode_tool_name(provider_name.strip())
        except (KeyError, ValueError, TypeError):
            raise StreamAdapterError("zhipu_tool_name") from None
        if (
            not isinstance(internal_name, str)
            or not internal_name.strip()
            or len(internal_name.strip()) > _MAX_TOOL_METADATA_CHARS
        ):
            raise StreamAdapterError("zhipu_tool_name")
        internal_name = internal_name.strip()

    arguments = _read_field(function, "arguments")
    if arguments is not None and not isinstance(arguments, str):
        raise StreamAdapterError("zhipu_tool_shape")
    try:
        return StreamToolCallDelta(
            index=index,
            call_id=call_id.strip() if isinstance(call_id, str) else None,
            name=internal_name,
            arguments_delta=arguments,
        )
    except (TypeError, ValueError):
        raise StreamAdapterError("zhipu_tool_shape") from None


def _normalize_usage(raw_usage: Any) -> TokenUsage:
    if raw_usage is None:
        raise StreamAdapterError("zhipu_usage_shape")
    input_tokens = _read_field(raw_usage, "prompt_tokens")
    output_tokens = _read_field(raw_usage, "completion_tokens")
    details = _read_field(raw_usage, "prompt_tokens_details")
    if isinstance(details, Mapping):
        cached_tokens = details.get("cached_tokens", 0)
    else:
        cached_tokens = _read_field(details, "cached_tokens", 0) if details else 0
    if cached_tokens is None:
        cached_tokens = 0
    try:
        usage = TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=cached_tokens,
        )
    except (TypeError, ValueError):
        raise StreamAdapterError("zhipu_usage_shape") from None
    if usage.cached_input_tokens > usage.input_tokens:
        raise StreamAdapterError("zhipu_usage_shape")
    return usage


def _safe_identifier(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty identifier")
    normalized = value.strip()
    if not re.fullmatch(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$", normalized):
        raise ValueError(f"{field_name} must be a safe identifier")
    return normalized


def _validate_positive_limit(value: int, field_name: str) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 1
        or value > 8192
    ):
        raise ValueError(f"{field_name} must be between 1 and 8192")


def _read_field(value: Any, name: str, default: Any = None) -> Any:
    """Read SDK/Pydantic attributes and fixture mappings uniformly."""

    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _read_field_with_presence(
    value: Any,
    name: str,
    default: Any = None,
) -> tuple[bool, Any]:
    """Read a vendor field while preserving missing versus explicit null."""

    if isinstance(value, Mapping):
        return name in value, value.get(name, default)
    try:
        return hasattr(value, name), getattr(value, name, default)
    except Exception:
        raise StreamAdapterError("zhipu_chunk_shape") from None


def _provider_bound_output_cap(provider: Any) -> int | None:
    """Read a trusted registered runtime cap without accepting ad-hoc input."""

    runtime_profile = getattr(provider, "runtime_profile", None)
    if runtime_profile is None:
        return None
    cap = getattr(runtime_profile, "max_output_tokens", None)
    if cap is None:
        raise ValueError("provider runtime profile has no output cap")
    _validate_positive_limit(cap, "provider runtime max_output_tokens")
    return cap


def _close_resource_state(resource: object | None) -> ZhipuCloseResourceState:
    """Close one owned object and retain only a safe lifecycle state."""

    if resource is None:
        return "not_observed"
    try:
        close = getattr(resource, "close", None)
    except (GeneratorExit, KeyboardInterrupt, SystemExit):
        raise
    except Exception:
        return "failed"
    if callable(close):
        try:
            close()
        except Exception:
            # Do not leak an SDK close exception; the caller decides whether
            # it may replace a normal EOF or must preserve an active error.
            return "failed"
        return "closed"
    try:
        exit_method = getattr(resource, "__exit__", None)
    except (GeneratorExit, KeyboardInterrupt, SystemExit):
        raise
    except Exception:
        return "failed"
    if callable(exit_method):
        try:
            exit_method(None, None, None)
        except Exception:
            return "failed"
        return "closed"
    return "not_observed"


def _close_iterator(iterator: Iterator[Any] | None) -> bool:
    return _close_resource_state(iterator) == "failed"


def _close_stream(raw_stream: Iterable[Any] | None) -> bool:
    return _close_resource_state(raw_stream) == "failed"


def _translate_provider_error(
    provider: Any,
    error: Exception,
) -> ProviderError | None:
    """Ask a bound provider to map a raw SDK error without exposing its body."""

    translator = getattr(provider, "_translate_error", None)
    if not callable(translator):
        return None
    try:
        translated = translator(error)
    except Exception:
        return None
    return translated if isinstance(translated, ProviderError) else None


__all__ = [
    "ZhipuCloseCompositeState",
    "ZhipuCloseResourceState",
    "ZhipuStreamAdapter",
    "ZhipuStreamCloseReport",
    "ZhipuStreamSession",
]
