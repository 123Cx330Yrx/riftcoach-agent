"""Offline conformance checks for the Zhipu stream-to-neutral seam.

These tests deliberately keep the provider-specific translator local to the
test module.  The product still exposes only the existing synchronous
``ZhipuProvider.chat_stream`` surface; this file checks that representative
OpenAI-compatible chunks can be translated into the candidate neutral stream
contract without making a network call or changing the production adapter.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from hashlib import sha256
from types import SimpleNamespace
from typing import Any

import pytest

from app.providers.models import (
    ChatMessage,
    ChatRequest,
    MessageRole,
    TokenUsage,
    ToolSpec,
)
from app.providers.stream_adapter_contract import (
    ProviderStreamAdapter,
    ProviderStreamAssembler,
    ProviderStreamEvent,
    StreamAdapterError,
    StreamAssemblyResult,
    StreamToolCallDelta,
)
from app.providers.zhipu import ZhipuProvider, _ToolAliasMap


_MODEL = "glm-5.3-flash"


def _usage(
    *,
    prompt_tokens: int = 10,
    completion_tokens: int = 7,
    cached_tokens: int = 0,
) -> SimpleNamespace:
    return SimpleNamespace(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        prompt_tokens_details=SimpleNamespace(cached_tokens=cached_tokens),
    )


def _chunk(
    *,
    content: object = None,
    reasoning: object = None,
    tool_calls: object = None,
    finish_reason: object = None,
    usage: object = None,
    model: object = _MODEL,
    request_id: object = "fixture-stream-id",
    choices: object | None = None,
) -> SimpleNamespace:
    """Build one SDK-shaped chunk, including intentionally malformed values."""

    if choices is None:
        has_delta = (
            content is not None
            or reasoning is not None
            or tool_calls is not None
            or finish_reason is not None
        )
        choices = (
            [
                SimpleNamespace(
                    finish_reason=finish_reason,
                    delta=SimpleNamespace(
                        content=content,
                        reasoning_content=reasoning,
                        tool_calls=tool_calls,
                    ),
                )
            ]
            if has_delta
            else []
        )
    return SimpleNamespace(
        id=request_id,
        model=model,
        choices=choices,
        usage=usage,
    )


def _tool_fragment(
    *,
    index: int = 0,
    call_id: object = None,
    call_type: object = None,
    name: object = None,
    arguments: object = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        index=index,
        id=call_id,
        type=call_type,
        function=SimpleNamespace(name=name, arguments=arguments),
    )


def _lookup_tool(name: str = "knowledge.search") -> ToolSpec:
    return ToolSpec(
        name=name,
        description="Read one fixed coaching fixture.",
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
            "additionalProperties": False,
        },
    )


class _FixtureZhipuStreamAdapter:
    """Test-only translator from Zhipu-shaped chunks to neutral events."""

    provider_name = "zhipu"
    model_name = _MODEL

    def __init__(
        self,
        stream_factory: Callable[[ChatRequest], Iterable[Any]],
    ) -> None:
        self._stream_factory = stream_factory

    def stream_events(
        self,
        request: ChatRequest,
    ) -> Iterable[ProviderStreamEvent]:
        aliases = _ToolAliasMap.from_tools(request.tools)
        raw_stream = self._stream_factory(request)
        for ordinal, chunk in enumerate(raw_stream, start=1):
            yield _translate_chunk(chunk, aliases=aliases, ordinal=ordinal)


def _translate_chunk(
    chunk: Any,
    *,
    aliases: _ToolAliasMap,
    ordinal: int,
) -> ProviderStreamEvent:
    """Translate one fixture chunk while retaining only safe neutral fields."""

    raw_model = getattr(chunk, "model", None)
    if raw_model is not None and (
        not isinstance(raw_model, str) or not raw_model.strip()
    ):
        raise StreamAdapterError("zhipu_chunk_shape")
    raw_request_id = getattr(chunk, "id", None)
    if raw_request_id is not None and (
        not isinstance(raw_request_id, str) or not raw_request_id.strip()
    ):
        raise StreamAdapterError("zhipu_chunk_shape")
    request_id_sha256 = (
        sha256(raw_request_id.encode("utf-8")).hexdigest()
        if raw_request_id is not None
        else None
    )

    choices = getattr(chunk, "choices", None)
    if not isinstance(choices, (list, tuple)):
        raise StreamAdapterError("zhipu_choices_shape")
    raw_usage = getattr(chunk, "usage", None)
    if not choices:
        # In the OpenAI-compatible shape, an empty choices frame is the
        # usage-only tail.  Do not silently turn an empty non-usage frame into
        # a successful EOF signal.
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
    delta = getattr(choice, "delta", None)
    if delta is None:
        raise StreamAdapterError("zhipu_delta_shape")

    content = getattr(delta, "content", None)
    reasoning = getattr(delta, "reasoning_content", None)
    if content is not None and not isinstance(content, str):
        raise StreamAdapterError("zhipu_content_shape")
    if reasoning is not None and not isinstance(reasoning, str):
        raise StreamAdapterError("zhipu_reasoning_shape")
    finish_reason = getattr(choice, "finish_reason", None)
    if finish_reason is not None and not isinstance(finish_reason, str):
        raise StreamAdapterError("zhipu_finish_shape")

    raw_tool_calls = getattr(delta, "tool_calls", None)
    tool_deltas: list[StreamToolCallDelta] = []
    if raw_tool_calls is not None:
        try:
            calls = list(raw_tool_calls)
        except TypeError:
            raise StreamAdapterError("zhipu_tool_shape") from None
        for raw_call in calls:
            tool_deltas.append(_translate_tool_call(raw_call, aliases))

    usage = _normalize_usage(raw_usage) if raw_usage is not None else None
    try:
        return ProviderStreamEvent(
            content_delta=content,
            reasoning_delta=reasoning,
            tool_call_deltas=tuple(tool_deltas),
            finish_reason=finish_reason,
            usage=usage,
            model=raw_model,
            sequence=ordinal,
            request_id_sha256=request_id_sha256,
        )
    except (TypeError, ValueError) as error:
        # Never expose a vendor object/value in the conformance error path.
        raise StreamAdapterError("zhipu_chunk_shape") from error


def _translate_tool_call(
    raw_call: Any,
    aliases: _ToolAliasMap,
) -> StreamToolCallDelta:
    index = getattr(raw_call, "index", None)
    if isinstance(index, bool) or not isinstance(index, int) or index < 0:
        raise StreamAdapterError("zhipu_tool_shape")
    call_type = getattr(raw_call, "type", None)
    if call_type is not None and call_type != "function":
        raise StreamAdapterError("zhipu_tool_shape")
    call_id = getattr(raw_call, "id", None)
    if call_id is not None and (
        not isinstance(call_id, str) or not call_id.strip()
    ):
        raise StreamAdapterError("zhipu_tool_shape")
    function = getattr(raw_call, "function", None)
    if function is None:
        raise StreamAdapterError("zhipu_tool_shape")
    provider_name = getattr(function, "name", None)
    if provider_name is not None and (
        not isinstance(provider_name, str) or not provider_name.strip()
    ):
        raise StreamAdapterError("zhipu_tool_shape")
    internal_name: str | None = None
    if provider_name is not None:
        try:
            internal_name = aliases.decode(provider_name.strip())
        except KeyError:
            raise StreamAdapterError("zhipu_tool_name") from None
    arguments = getattr(function, "arguments", None)
    if arguments is not None and not isinstance(arguments, str):
        raise StreamAdapterError("zhipu_tool_shape")
    try:
        return StreamToolCallDelta(
            index=index,
            call_id=call_id.strip() if isinstance(call_id, str) else None,
            name=internal_name,
            arguments_delta=arguments,
        )
    except (TypeError, ValueError) as error:
        raise StreamAdapterError("zhipu_tool_shape") from error


def _normalize_usage(raw_usage: Any) -> TokenUsage:
    input_tokens = getattr(raw_usage, "prompt_tokens", None)
    output_tokens = getattr(raw_usage, "completion_tokens", None)
    details = getattr(raw_usage, "prompt_tokens_details", None)
    if isinstance(details, dict):
        cached_tokens = details.get("cached_tokens", 0)
    else:
        cached_tokens = getattr(details, "cached_tokens", 0) if details else 0
    if cached_tokens is None:
        cached_tokens = 0
    try:
        return TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=cached_tokens,
        )
    except (TypeError, ValueError) as error:
        raise StreamAdapterError("zhipu_usage_shape") from error


class _FakeCompletions:
    def __init__(self, stream_factory: Callable[[], Iterable[Any]]) -> None:
        self._stream_factory = stream_factory
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Iterable[Any]:
        self.calls.append(kwargs)
        return self._stream_factory()


class _FakeClient:
    def __init__(self, stream_factory: Callable[[], Iterable[Any]]) -> None:
        completions = _FakeCompletions(stream_factory)
        self.completions = completions
        self.chat = SimpleNamespace(completions=completions)


def _request(*, tools: tuple[ToolSpec, ...] = ()) -> ChatRequest:
    return ChatRequest(
        messages=(ChatMessage(MessageRole.USER, "fixture prompt"),),
        tools=tools,
    )


def _assemble(
    adapter: ProviderStreamAdapter,
    request: ChatRequest,
    *,
    require_request_identity: bool = True,
) -> StreamAssemblyResult:
    assembler = ProviderStreamAssembler(
        provider_id=adapter.provider_name,
        requested_model=adapter.model_name,
        require_request_identity=require_request_identity,
    )
    for event in adapter.stream_events(request):
        assembler.accept(event)
    assembler.mark_exhausted()
    return assembler.finalize()


def test_text_chunks_conform_and_match_existing_zhipu_assembly() -> None:
    chunks = (
        _chunk(reasoning="think "),
        _chunk(content="RIFT"),
        _chunk(content="COACH", finish_reason="stop"),
        _chunk(usage=_usage()),
    )
    request = _request()
    adapter = _FixtureZhipuStreamAdapter(lambda _request: iter(chunks))

    assert isinstance(adapter, ProviderStreamAdapter)
    neutral = _assemble(adapter, request)
    legacy = ZhipuProvider(
        client=_FakeClient(lambda: iter(chunks)),
        model=_MODEL,
    ).chat_stream(request)

    assert neutral.response.content == legacy.response.content == "RIFTCOACH"
    assert neutral.response.reasoning_content == legacy.response.reasoning_content == "think "
    assert neutral.response.model == legacy.response.model == _MODEL
    assert neutral.response.usage == legacy.response.usage
    assert neutral.response.finish_reason == legacy.response.finish_reason == "stop"
    assert neutral.trace.chunk_count == legacy.chunk_count == 4
    assert neutral.trace.content_chunk_count == legacy.content_chunk_count == 2
    assert neutral.trace.reasoning_chunk_count == legacy.reasoning_chunk_count == 1
    assert neutral.trace.request_id_sha256 == sha256(
        b"fixture-stream-id"
    ).hexdigest()
    trace_text = json.dumps(neutral.trace.as_dict(), ensure_ascii=False)
    assert "RIFTCOACH" not in trace_text
    assert "think" not in trace_text

    # The neutral adapter is purely local and never receives a client or
    # secret; the legacy comparison above is the only fake provider call.


def test_tool_fragments_decode_aliases_and_match_existing_zhipu_assembly() -> None:
    tool = _lookup_tool()
    chunks = (
        _chunk(
            reasoning="private ",
            tool_calls=[
                _tool_fragment(
                    call_id="call-1",
                    call_type="function",
                    name="knowledge_search",
                    arguments='{"query":"',
                )
            ],
        ),
        _chunk(tool_calls=[_tool_fragment(arguments="兵线")]),
        _chunk(
            tool_calls=[_tool_fragment(arguments='"}')],
            finish_reason="tool_calls",
        ),
        _chunk(usage=_usage(prompt_tokens=12, completion_tokens=5)),
    )
    request = _request(tools=(tool,))
    adapter = _FixtureZhipuStreamAdapter(lambda _request: iter(chunks))
    neutral = _assemble(adapter, request)
    legacy = ZhipuProvider(
        client=_FakeClient(lambda: iter(chunks)),
        model=_MODEL,
    ).chat_stream(request, tool_stream=True)

    assert neutral.response.content is None
    assert neutral.response.tool_calls == legacy.response.tool_calls
    assert neutral.response.tool_calls[0].name == "knowledge.search"
    assert neutral.response.tool_calls[0].arguments == {"query": "兵线"}
    assert neutral.response.reasoning_content == legacy.response.reasoning_content == "private "
    assert neutral.response.finish_reason == legacy.response.finish_reason == "tool_calls"
    assert neutral.trace.tool_call_chunk_count == legacy.tool_call_chunk_count == 3
    assert neutral.trace.tool_call_count == 1
    trace_text = json.dumps(neutral.trace.as_dict(), ensure_ascii=False)
    assert "兵线" not in trace_text
    assert "knowledge.search" not in trace_text


@pytest.mark.parametrize(
    ("bad_chunk", "expected_code"),
    (
        (_chunk(choices="not-a-list"), "zhipu_choices_shape"),
        (
            _chunk(
                choices=[
                    SimpleNamespace(delta=SimpleNamespace()),
                    SimpleNamespace(delta=SimpleNamespace()),
                ]
            ),
            "zhipu_choices_shape",
        ),
        (
            _chunk(
                choices=[SimpleNamespace(finish_reason=None, delta=None)]
            ),
            "zhipu_delta_shape",
        ),
        (_chunk(content={"body": "must not leak"}), "zhipu_content_shape"),
        (_chunk(reasoning=["private"]), "zhipu_reasoning_shape"),
        (
            _chunk(
                tool_calls=[
                    _tool_fragment(
                        call_id="call-1",
                        call_type="not-function",
                        name="lookup",
                        arguments="{}",
                    )
                ]
            ),
            "zhipu_tool_shape",
        ),
        (_chunk(usage=_usage(prompt_tokens=-1)), "zhipu_usage_shape"),
    ),
)
def test_malformed_zhipu_shapes_fail_closed_without_raw_body(
    bad_chunk: Any,
    expected_code: str,
) -> None:
    request = _request(tools=(_lookup_tool("lookup"),))
    adapter = _FixtureZhipuStreamAdapter(lambda _request: iter((bad_chunk,)))

    with pytest.raises(StreamAdapterError) as caught:
        list(adapter.stream_events(request))

    assert caught.value.code == expected_code
    assert "must not leak" not in str(caught.value)
    assert "body" not in str(caught.value)


def test_unknown_tool_alias_and_empty_non_usage_frame_are_rejected() -> None:
    request = _request(tools=(_lookup_tool("knowledge.search"),))
    unknown = _chunk(
        tool_calls=[
            _tool_fragment(
                call_id="call-1",
                call_type="function",
                name="not_declared",
                arguments="{}",
            )
        ]
    )
    empty = _chunk()

    for chunk, code in ((unknown, "zhipu_tool_name"), (empty, "zhipu_empty_choices")):
        adapter = _FixtureZhipuStreamAdapter(lambda _request, chunk=chunk: iter((chunk,)))
        with pytest.raises(StreamAdapterError, match=code):
            list(adapter.stream_events(request))


def test_assembler_enforces_model_identity_and_terminal_payload_boundary() -> None:
    request = _request()
    chunks = (
        _chunk(content="done", finish_reason="stop"),
        _chunk(content="late"),
    )
    adapter = _FixtureZhipuStreamAdapter(lambda _request: iter(chunks))
    assembler = ProviderStreamAssembler(
        provider_id="zhipu",
        requested_model=_MODEL,
        require_request_identity=True,
    )
    events = iter(adapter.stream_events(request))
    assembler.accept(next(events))
    with pytest.raises(StreamAdapterError, match="payload_after_terminal") as caught:
        assembler.accept(next(events))
    assert caught.value.code == "payload_after_terminal"
    with pytest.raises(StreamAdapterError, match="payload_after_terminal"):
        assembler.finalize()

    conflict_chunks = (
        _chunk(content="one"),
        _chunk(content="two", model="other-model"),
    )
    conflict = _FixtureZhipuStreamAdapter(
        lambda _request: iter(conflict_chunks)
    )
    conflict_assembler = ProviderStreamAssembler(
        provider_id="zhipu",
        requested_model=_MODEL,
    )
    conflict_events = iter(conflict.stream_events(request))
    conflict_assembler.accept(next(conflict_events))
    with pytest.raises(StreamAdapterError, match="model_conflict"):
        conflict_assembler.accept(next(conflict_events))


def test_source_exception_requires_abort_and_cannot_be_reinterpreted_as_eof() -> None:
    request = _request()

    def broken_stream(_request: ChatRequest) -> Iterable[Any]:
        def generate() -> Iterable[Any]:
            yield _chunk(content="partial")
            raise RuntimeError("secret transport body")

        return generate()

    adapter = _FixtureZhipuStreamAdapter(broken_stream)
    assembler = ProviderStreamAssembler(
        provider_id="zhipu",
        requested_model=_MODEL,
    )
    with pytest.raises(RuntimeError):
        for event in adapter.stream_events(request):
            assembler.accept(event)

    assembler.abort("stream_read_error")
    with pytest.raises(StreamAdapterError, match="stream_read_error") as caught:
        assembler.finalize()
    assert "secret transport body" not in str(caught.value)


def test_neutral_contract_preserves_content_whitespace_while_legacy_surface_strips() -> None:
    chunks = (_chunk(content="  answer\n", finish_reason="stop", usage=_usage()),)
    request = _request()
    neutral = _assemble(
        _FixtureZhipuStreamAdapter(lambda _request: iter(chunks)),
        request,
        require_request_identity=True,
    )
    legacy = ZhipuProvider(
        client=_FakeClient(lambda: iter(chunks)),
        model=_MODEL,
    ).chat_stream(request)

    assert neutral.response.content == "  answer\n"
    assert legacy.response.content == "answer"
