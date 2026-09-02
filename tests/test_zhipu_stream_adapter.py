"""Focused tests for the explicit Zhipu-to-neutral stream seam."""

from __future__ import annotations

import json
from hashlib import sha256
from types import SimpleNamespace
from typing import Any

import httpx
import openai
import pytest

from app.providers import (
    ChatMessage,
    ChatRequest,
    MessageRole,
    ProviderStreamAdapter,
    StreamAdapterError,
    ZhipuProvider,
    ZhipuStreamAdapter,
)
from app.providers.config import ZhipuSettings, create_zhipu_provider
from app.providers.errors import (
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.providers.models import ToolSpec


MODEL = "glm-5.3-flash"


def usage(input_tokens: int = 10, output_tokens: int = 7) -> SimpleNamespace:
    return SimpleNamespace(
        prompt_tokens=input_tokens,
        completion_tokens=output_tokens,
        prompt_tokens_details=SimpleNamespace(cached_tokens=0),
    )


def chunk(
    *,
    content: object = None,
    reasoning: object = None,
    tool_calls: object = None,
    finish_reason: object = None,
    raw_usage: object = None,
    model: object = MODEL,
    request_id: object = "stream-id",
    choices: object | None = None,
) -> SimpleNamespace:
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
        usage=raw_usage,
    )


def tool_fragment(
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


def request(
    *,
    tools: tuple[ToolSpec, ...] = (),
    max_tokens: int | None = None,
) -> ChatRequest:
    return ChatRequest(
        messages=(ChatMessage(MessageRole.USER, "safe fixture prompt"),),
        tools=tools,
        max_tokens=max_tokens,
    )


def lookup_tool(name: str = "knowledge.search") -> ToolSpec:
    return ToolSpec(
        name=name,
        description="Read one fixed fixture.",
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
            "additionalProperties": False,
        },
    )


class ClosableStream:
    def __init__(
        self,
        values: list[Any],
        error: BaseException | None = None,
        close_error: BaseException | None = None,
    ) -> None:
        self._values = values
        self._error = error
        self._close_error = close_error
        self.closed = False

    def __iter__(self) -> "ClosableStream":
        return self

    def __next__(self) -> Any:
        if self._values:
            return self._values.pop(0)
        if self._error is not None:
            error, self._error = self._error, None
            raise error
        raise StopIteration

    def close(self) -> None:
        self.closed = True
        if self._close_error is not None:
            error, self._close_error = self._close_error, None
            raise error


class FakeCompletions:
    def __init__(self, stream: ClosableStream) -> None:
        self.stream = stream
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> ClosableStream:
        self.calls.append(kwargs)
        return self.stream


class FakeClient:
    def __init__(self, stream: ClosableStream) -> None:
        completions = FakeCompletions(stream)
        self.completions = completions
        self.chat = SimpleNamespace(completions=completions)


def test_explicit_adapter_assembles_text_and_keeps_trace_body_free() -> None:
    raw = ClosableStream(
        [
            chunk(reasoning="private "),
            chunk(content="  answer"),
            chunk(content="\n", finish_reason="stop"),
            chunk(raw_usage=usage()),
        ]
    )
    client = FakeClient(raw)
    provider = ZhipuProvider(client=client, model=MODEL)
    adapter = provider.stream_adapter()

    assert isinstance(adapter, ZhipuStreamAdapter)
    assert isinstance(adapter, ProviderStreamAdapter)
    result = adapter.assemble(request())

    assert result.response.content == "  answer\n"
    assert result.response.reasoning_content == "private "
    assert result.response.request_id is None
    assert result.trace.request_id_sha256 == sha256(b"stream-id").hexdigest()
    encoded = json.dumps(result.trace.as_dict(), ensure_ascii=False)
    assert "answer" not in encoded
    assert "private" not in encoded
    assert raw.closed is True
    assert client.completions.calls[0]["stream"] is True
    assert client.completions.calls[0]["extra_body"] == {
        "thinking": {"type": "enabled", "clear_thinking": False},
        "reasoning_effort": "max",
    }


def test_tool_adapter_decodes_alias_and_adds_tool_stream_body() -> None:
    raw = ClosableStream(
        [
            chunk(
                tool_calls=[
                    tool_fragment(
                        call_id="call-1",
                        call_type="function",
                        name="knowledge_search",
                        arguments='{"query":"',
                    )
                ]
            ),
            chunk(tool_calls=[tool_fragment(arguments="兵线")]),
            chunk(
                tool_calls=[tool_fragment(arguments='"}')],
                finish_reason="tool_calls",
            ),
            chunk(raw_usage=usage(output_tokens=5)),
        ]
    )
    client = FakeClient(raw)
    provider = ZhipuProvider(client=client, model=MODEL)
    adapter = provider.stream_adapter(tool_stream=True)

    result = adapter.assemble(request(tools=(lookup_tool(),)))

    assert result.response.content is None
    assert result.response.tool_calls[0].name == "knowledge.search"
    assert result.response.tool_calls[0].arguments == {"query": "兵线"}
    assert client.completions.calls[0]["extra_body"]["tool_stream"] is True
    assert client.completions.calls[0]["tools"][0]["function"]["name"] == (
        "knowledge_search"
    )
    assert raw.closed is True


def test_runtime_bound_provider_clamps_stream_payload_to_registered_profile() -> None:
    raw = ClosableStream(
        [chunk(content="done", finish_reason="stop"), chunk(raw_usage=usage())]
    )
    client = FakeClient(raw)
    provider = create_zhipu_provider(
        ZhipuSettings(
            api_key="secret-value",
            base_url="https://open.bigmodel.cn/api/paas/v4/",
            model=MODEL,
        ),
        client_factory=lambda **_: client,
    )

    adapter = provider.stream_adapter()
    assert adapter.default_max_output_tokens == 2048
    result = adapter.assemble(
        request(),
        max_output_tokens=2048,
    )

    assert result.response.content == "done"
    payload = client.completions.calls[0]
    assert payload["max_tokens"] == 2048
    assert payload["temperature"] == 1.0
    assert payload["top_p"] == 0.95
    assert payload["timeout"] == 30.0


def test_direct_adapter_inherits_registered_runtime_cap_and_clamps_request() -> None:
    raw = ClosableStream(
        [chunk(content="done", finish_reason="stop"), chunk(raw_usage=usage())]
    )
    client = FakeClient(raw)
    provider = create_zhipu_provider(
        ZhipuSettings(
            api_key="secret-value",
            base_url="https://open.bigmodel.cn/api/paas/v4/",
            model=MODEL,
        ),
        client_factory=lambda **_: client,
    )

    adapter = ZhipuStreamAdapter(provider)
    assert adapter.default_max_output_tokens == 2048
    adapter.assemble(request(max_tokens=4096))
    assert client.completions.calls[0]["max_tokens"] == 2048


def test_request_output_cap_is_sent_and_enforced_by_assembler() -> None:
    raw = ClosableStream(
        [
            chunk(content="done", finish_reason="stop"),
            chunk(raw_usage=usage(output_tokens=8)),
        ]
    )
    client = FakeClient(raw)
    provider = ZhipuProvider(client=client, model=MODEL)

    with pytest.raises(StreamAdapterError) as caught:
        provider.stream_adapter().assemble(request(max_tokens=7))

    assert caught.value.code == "output_budget_exceeded"
    assert client.completions.calls[0]["max_tokens"] == 7
    assert raw.closed is True


@pytest.mark.parametrize(
    ("bad", "code"),
    [
        (chunk(choices="not-a-list"), "zhipu_choices_shape"),
        (chunk(content={"secret": "body"}), "zhipu_content_shape"),
        (chunk(), "zhipu_empty_choices"),
        (
            chunk(
                tool_calls=[
                    tool_fragment(
                        call_id="call-1",
                        call_type="custom",
                        name="knowledge_search",
                        arguments="{}",
                    )
                ]
            ),
            "zhipu_tool_shape",
        ),
    ],
)
def test_malformed_chunks_fail_closed_and_close_stream(bad: Any, code: str) -> None:
    raw = ClosableStream([bad])
    provider = ZhipuProvider(client=FakeClient(raw), model=MODEL)

    with pytest.raises(StreamAdapterError) as caught:
        list(provider.stream_adapter().stream_events(request(tools=(lookup_tool(),))))

    assert caught.value.code == code
    assert "secret" not in str(caught.value)
    assert raw.closed is True


def test_model_identity_mismatch_fails_closed_without_body() -> None:
    raw = ClosableStream([chunk(content="private", model="glm-5.2")])
    provider = ZhipuProvider(client=FakeClient(raw), model=MODEL)

    with pytest.raises(StreamAdapterError) as caught:
        list(provider.stream_adapter().stream_events(request()))

    assert caught.value.code == "zhipu_model_mismatch"
    assert "private" not in str(caught.value)
    assert raw.closed is True


def test_mapping_chunks_and_usage_are_supported_without_changing_trace() -> None:
    raw = ClosableStream(
        [
            {
                "id": "mapping-id",
                "model": MODEL,
                "choices": [
                    {
                        "delta": {"content": "done"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": None,
            },
            {
                "id": "mapping-id",
                "model": MODEL,
                "choices": [],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 2,
                    "prompt_tokens_details": {"cached_tokens": 1},
                },
            },
        ]
    )
    provider = ZhipuProvider(client=FakeClient(raw), model=MODEL)

    result = provider.stream_adapter().assemble(request())

    assert result.response.content == "done"
    assert result.response.usage.cached_input_tokens == 1
    assert result.trace.request_id_sha256 == sha256(b"mapping-id").hexdigest()


def test_explicit_null_delta_fields_keep_presence_for_candidate_observers() -> None:
    raw = ClosableStream(
        [
            SimpleNamespace(
                id="null-id",
                model=MODEL,
                choices=[
                    SimpleNamespace(
                        delta=SimpleNamespace(
                            content=None,
                            reasoning_content="thinking",
                            tool_calls=None,
                        ),
                        finish_reason=None,
                    )
                ],
                usage=None,
            )
        ]
    )
    provider = ZhipuProvider(client=FakeClient(raw), model=MODEL)
    event = next(iter(provider.stream_adapter().stream_events(request())))

    assert event.content_delta is None
    assert event.content_observed is True
    assert event.reasoning_delta == "thinking"
    assert event.reasoning_observed is True


def test_iterator_exception_is_not_mistaken_for_eof() -> None:
    raw = ClosableStream(
        [chunk(content="partial")],
        error=RuntimeError("vendor body must not leak"),
    )
    provider = ZhipuProvider(client=FakeClient(raw), model=MODEL)

    with pytest.raises(ProviderUnavailableError) as caught:
        provider.stream_adapter().assemble(request())

    assert caught.value.code == "unexpected_sdk_error"
    assert "vendor body" not in str(caught.value)
    assert raw.closed is True


def test_cleanup_preserves_keyboard_interrupt_from_provider_stream() -> None:
    raw = ClosableStream(
        [chunk(content="partial")],
        close_error=KeyboardInterrupt,
    )
    provider = ZhipuProvider(client=FakeClient(raw), model=MODEL)

    with pytest.raises(KeyboardInterrupt):
        list(provider.stream_adapter().stream_events(request()))


def test_provider_sdk_iterator_error_keeps_typed_error_without_body() -> None:
    raw = ClosableStream(
        [],
        error=openai.APITimeoutError(
            request=httpx.Request("GET", "https://example.invalid")
        ),
    )
    provider = ZhipuProvider(client=FakeClient(raw), model=MODEL)

    with pytest.raises(ProviderTimeoutError) as caught:
        provider.stream_adapter().assemble(request())

    assert caught.value.code == "timeout"
    assert raw.closed is True


def test_disabled_thinking_profile_rejects_reasoning_in_neutral_stream() -> None:
    raw = ClosableStream(
        [
            chunk(reasoning="private", model="glm-5.2"),
            chunk(content="done", finish_reason="stop", model="glm-5.2"),
            chunk(raw_usage=usage(), model="glm-5.2"),
        ]
    )
    provider = ZhipuProvider(client=FakeClient(raw), model="glm-5.2")

    with pytest.raises(ProviderResponseError) as caught:
        provider.stream_adapter().assemble(request())

    assert "private" not in str(caught.value)
    assert raw.closed is True


def test_consumer_close_closes_open_sdk_iterator_without_finalizing() -> None:
    raw = ClosableStream(
        [chunk(reasoning="private"), chunk(content="partial")]
    )
    provider = ZhipuProvider(client=FakeClient(raw), model=MODEL)
    events = iter(provider.stream_adapter().stream_events(request()))

    next(events)
    events.close()  # type: ignore[attr-defined]

    assert raw.closed is True


def test_explicit_candidate_session_requests_usage_tail_and_is_idempotently_closed() -> None:
    raw = ClosableStream(
        [
            chunk(content="done", finish_reason="stop"),
            chunk(raw_usage=usage(), choices=[]),
        ]
    )
    client = FakeClient(raw)
    provider = ZhipuProvider(client=client, model=MODEL)
    session = provider.stream_adapter().stream_session(
        request(),
        include_usage_tail=True,
    )

    events = list(session)
    assert events[-1].usage is not None
    assert client.completions.calls[0]["stream_options"] == {
        "include_usage": True
    }
    assert raw.closed is False

    session.close()
    session.close()
    assert raw.closed is True


def test_explicit_candidate_session_falls_back_to_context_manager_close() -> None:
    class ContextOnlyStream:
        def __init__(self) -> None:
            self.closed = False

        def __iter__(self):
            return iter(
                [
                    chunk(content="done", finish_reason="stop"),
                    chunk(raw_usage=usage(), choices=[]),
                ]
            )

        def __exit__(self, *_args) -> None:
            self.closed = True

    raw = ContextOnlyStream()
    provider = ZhipuProvider(client=FakeClient(raw), model=MODEL)
    session = provider.stream_adapter().stream_session(request())
    assert len(list(session)) == 2
    session.close()
    assert raw.closed is True


def test_close_failure_is_a_safe_error_on_normal_eof() -> None:
    raw = ClosableStream(
        [chunk(content="done", finish_reason="stop"), chunk(raw_usage=usage())],
        close_error=RuntimeError("vendor body must not leak"),
    )
    provider = ZhipuProvider(client=FakeClient(raw), model=MODEL)

    with pytest.raises(StreamAdapterError) as caught:
        provider.stream_adapter().assemble(request())

    assert caught.value.code == "zhipu_stream_close"
    assert "vendor body" not in str(caught.value)
    assert raw.closed is True


def test_session_close_getter_failure_is_body_free_and_retained() -> None:
    class HostileCloseStream(ClosableStream):
        def __getattribute__(self, name: str) -> Any:
            if name in {"close", "__exit__"}:
                raise RuntimeError("private provider body")
            return super().__getattribute__(name)

    raw = HostileCloseStream(
        [chunk(content="done", finish_reason="stop"), chunk(raw_usage=usage())]
    )
    provider = ZhipuProvider(client=FakeClient(raw), model=MODEL)
    session = provider.stream_adapter().stream_session(request())
    assert len(list(session)) == 2

    with pytest.raises(StreamAdapterError) as caught:
        session.close()

    assert caught.value.code == "zhipu_stream_close"
    assert "private provider body" not in str(caught.value)
    assert session.close_failed is True


def test_adapter_rejects_tool_stream_without_tools_before_opening_client() -> None:
    raw = ClosableStream([])
    client = FakeClient(raw)
    provider = ZhipuProvider(client=client, model=MODEL)

    with pytest.raises(StreamAdapterError, match="zhipu_stream_open") as caught:
        list(provider.stream_adapter(tool_stream=True).stream_events(request()))

    assert caught.value.code == "zhipu_stream_open"
    assert client.completions.calls == []
    assert raw.closed is False


def test_non_boolean_adapter_option_is_rejected() -> None:
    provider = ZhipuProvider(client=FakeClient(ClosableStream([])), model=MODEL)
    with pytest.raises(ValueError, match="tool_stream"):
        provider.stream_adapter(tool_stream="yes")  # type: ignore[arg-type]


def test_explicit_cap_cannot_escape_a_trusted_runtime_bound() -> None:
    raw = ClosableStream([])
    provider = ZhipuProvider(client=FakeClient(raw), model=MODEL)
    adapter = ZhipuStreamAdapter(
        provider,
        default_max_output_tokens=2048,
    )

    with pytest.raises(ValueError, match="provider-bound cap"):
        adapter.assemble(request(), max_output_tokens=8192)
    assert raw.closed is False


def test_capability_flag_and_legacy_provider_stream_remain_unchanged() -> None:
    raw = ClosableStream(
        [chunk(content="done", finish_reason="stop"), chunk(raw_usage=usage())]
    )
    provider = ZhipuProvider(client=FakeClient(raw), model=MODEL)

    assert provider.capabilities.streaming is False
    # The adapter is explicit and does not alter the old private capability
    # surface or make itself the provider's synchronous chat implementation.
    assert provider.stream_adapter().provider_name == "zhipu"
