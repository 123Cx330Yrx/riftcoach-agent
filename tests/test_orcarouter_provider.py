from types import SimpleNamespace

import httpx
import openai
import pytest

from app.providers.config import (
    ORCAROUTER_BASE_URL,
    ORCAROUTER_MODEL,
    OrcaRouterSettings,
    create_orcarouter_provider,
    load_orcarouter_settings,
)
from app.providers.orcarouter import OrcaRouterProvider
from app.providers.errors import (
    ProviderAuthenticationError,
    ProviderCapabilityError,
    ProviderConfigurationError,
    ProviderResponseError,
    ProviderUnavailableError,
)
from app.providers.models import (
    ChatMessage,
    ChatRequest,
    MessageRole,
    StructuredResponseContract,
    ToolCall,
    ToolChoiceMode,
    ToolSpec,
)


class FakeCompletions:
    def __init__(self, result) -> None:
        self.result = result
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class FakeClient:
    def __init__(self, result) -> None:
        self.completions = FakeCompletions(result)
        self.chat = SimpleNamespace(completions=self.completions)


def sdk_tool_call(
    *,
    call_id: str = "call-1",
    name: str = "knowledge_search",
    arguments: str = '{"query":"前15分钟死亡","top_k":1}',
):
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(name=name, arguments=arguments),
    )


def sdk_response(
    *,
    content: str | None = "教练报告",
    model: str = "qwen3.6-flash",
    finish_reason: str = "stop",
    tool_calls=None,
    reasoning_content=None,
    usage=True,
):
    return SimpleNamespace(
        id="orcarouter-request-123",
        model=model,
        choices=[
            SimpleNamespace(
                finish_reason=finish_reason,
                message=SimpleNamespace(
                    content=content,
                    tool_calls=[] if tool_calls is None else tool_calls,
                    reasoning_content=reasoning_content,
                ),
            )
        ],
        usage=(
            SimpleNamespace(prompt_tokens=120, completion_tokens=30)
            if usage
            else None
        ),
    )


def knowledge_tool(name: str = "knowledge.search") -> ToolSpec:
    return ToolSpec(
        name=name,
        description="检索复盘知识。",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer"},
            },
            "required": ["query", "top_k"],
            "additionalProperties": False,
        },
    )


def text_request() -> ChatRequest:
    return ChatRequest(
        messages=(
            ChatMessage(MessageRole.SYSTEM, "你是教练。"),
            ChatMessage(MessageRole.USER, "请复盘。"),
        ),
        temperature=0.2,
        max_tokens=600,
        timeout_s=17.5,
        metadata={"secret": "must-not-be-sent"},
    )


def test_maps_text_request_with_gateway_resolved_model():
    client = FakeClient(sdk_response(reasoning_content="thinking"))
    response = OrcaRouterProvider(client=client, model=ORCAROUTER_MODEL).chat(
        text_request()
    )

    assert response.provider == "orcarouter"
    assert response.model == "qwen3.6-flash"
    assert response.content == "教练报告"
    assert response.usage.total_tokens == 150
    call = client.completions.calls[0]
    assert call == {
        "model": ORCAROUTER_MODEL,
        "messages": [
            {"role": "system", "content": "你是教练。"},
            {"role": "user", "content": "请复盘。"},
        ],
        "temperature": 0.2,
        "timeout": 17.5,
        "stream": False,
        "max_tokens": 600,
    }
    assert "secret" not in repr(call)


def test_maps_structured_output_to_json_mode():
    client = FakeClient(sdk_response(content='{"ok":true}'))
    contract = StructuredResponseContract(
        name="test_json",
        version="1.0.0",
        json_schema={
            "type": "object",
            "properties": {"ok": {"type": "boolean"}},
            "required": ["ok"],
            "additionalProperties": False,
        },
    )
    request = ChatRequest(
        messages=(ChatMessage(MessageRole.USER, "Return JSON."),),
        tool_choice=ToolChoiceMode.NONE,
        response_contract=contract,
        max_tokens=512,
    )

    OrcaRouterProvider(client=client, model=ORCAROUTER_MODEL).chat(request)

    assert client.completions.calls[0]["response_format"] == {
        "type": "json_object"
    }


def test_tool_alias_round_trip_and_all_message_roles():
    client = FakeClient(
        sdk_response(
            content=None,
            finish_reason="tool_calls",
            tool_calls=[sdk_tool_call()],
        )
    )
    request = ChatRequest(
        messages=(
            ChatMessage(MessageRole.SYSTEM, "policy"),
            ChatMessage(MessageRole.USER, "search"),
            ChatMessage(
                MessageRole.ASSISTANT,
                tool_calls=(
                    ToolCall(
                        id="previous-call",
                        name="knowledge.search",
                        arguments={"query": "死亡", "top_k": 1},
                    ),
                ),
            ),
            ChatMessage(
                MessageRole.TOOL,
                content='{"success":true}',
                tool_call_id="previous-call",
                name="knowledge.search",
            ),
        ),
        tools=(knowledge_tool(),),
        tool_choice=ToolChoiceMode.AUTO,
        max_tokens=1024,
    )

    response = OrcaRouterProvider(client=client, model=ORCAROUTER_MODEL).chat(
        request
    )

    assert response.tool_calls == (
        ToolCall(
            id="call-1",
            name="knowledge.search",
            arguments={"query": "前15分钟死亡", "top_k": 1},
        ),
    )
    call = client.completions.calls[0]
    assert call["tools"][0]["function"]["name"] == "knowledge_search"
    assert call["tool_choice"] == "auto"
    assert call["messages"][2]["tool_calls"][0]["function"]["name"] == (
        "knowledge_search"
    )
    assert call["messages"][3]["tool_call_id"] == "previous-call"


@pytest.mark.parametrize(
    ("response", "code"),
    (
        (sdk_response(usage=False), "provider_usage_unavailable"),
        (sdk_response(model=""), "invalid_chat_response"),
        (sdk_response(finish_reason="length"), "incomplete_chat_response"),
        (sdk_response(finish_reason="unknown"), "invalid_finish_reason"),
        (
            sdk_response(
                content=None,
                finish_reason="tool_calls",
                tool_calls=[
                    sdk_tool_call(arguments='{"query":"a","query":"b","top_k":1}')
                ],
            ),
            "invalid_tool_call_response",
        ),
    ),
)
def test_malformed_responses_fail_closed(response, code):
    provider = OrcaRouterProvider(
        client=FakeClient(response),
        model=ORCAROUTER_MODEL,
    )

    with pytest.raises(ProviderResponseError) as captured:
        provider.chat(text_request())

    assert captured.value.code == code


def test_gateway_reasoning_content_is_accepted():
    client = FakeClient(
        sdk_response(content="final", reasoning_content="chain of thought")
    )
    response = OrcaRouterProvider(client=client, model=ORCAROUTER_MODEL).chat(
        text_request()
    )

    assert response.content == "final"


def test_unknown_tool_alias_fails_closed():
    provider = OrcaRouterProvider(
        client=FakeClient(
            sdk_response(
                content=None,
                finish_reason="tool_calls",
                tool_calls=[sdk_tool_call(name="not_registered")],
            )
        ),
        model=ORCAROUTER_MODEL,
    )
    request = ChatRequest(
        messages=(ChatMessage(MessageRole.USER, "search"),),
        tools=(knowledge_tool(),),
        max_tokens=1024,
    )

    with pytest.raises(ProviderResponseError, match="invalid_tool_call_response"):
        provider.chat(request)


def test_multi_tool_call_batch_round_trip_preserves_order():
    client = FakeClient(
        sdk_response(
            content=None,
            finish_reason="tool_calls",
            tool_calls=[
                sdk_tool_call(
                    call_id="call-a",
                    arguments='{"query":"前15分钟死亡","top_k":1}',
                ),
                sdk_tool_call(
                    call_id="call-b",
                    arguments='{"query":"补刀趋势","top_k":2}',
                ),
            ],
        )
    )
    provider = OrcaRouterProvider(client=client, model=ORCAROUTER_MODEL)
    request = ChatRequest(
        messages=(ChatMessage(MessageRole.USER, "search twice"),),
        tools=(knowledge_tool(),),
        tool_choice=ToolChoiceMode.AUTO,
        max_tokens=1024,
    )

    response = provider.chat(request)

    assert response.tool_calls == (
        ToolCall(
            id="call-a",
            name="knowledge.search",
            arguments={"query": "前15分钟死亡", "top_k": 1},
        ),
        ToolCall(
            id="call-b",
            name="knowledge.search",
            arguments={"query": "补刀趋势", "top_k": 2},
        ),
    )


def test_rejects_required_and_structured_tool_combination_before_sdk():
    client = FakeClient(sdk_response())
    provider = OrcaRouterProvider(client=client, model=ORCAROUTER_MODEL)
    contract = StructuredResponseContract(
        name="test_json",
        version="1.0.0",
        json_schema={
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    )
    required = ChatRequest(
        messages=(ChatMessage(MessageRole.USER, "search"),),
        tools=(knowledge_tool(),),
        tool_choice=ToolChoiceMode.REQUIRED,
    )
    combined = ChatRequest(
        messages=(ChatMessage(MessageRole.USER, "json search"),),
        tools=(knowledge_tool(),),
        response_contract=contract,
    )

    with pytest.raises(ProviderCapabilityError):
        provider.chat(required)
    with pytest.raises(ProviderCapabilityError):
        provider.chat(combined)

    assert client.completions.calls == []


def test_sdk_errors_are_typed_and_sanitized():
    request = httpx.Request("POST", "https://api.orcarouter.ai/v1/chat/completions")
    response = httpx.Response(401, request=request)
    authentication = openai.AuthenticationError(
        "raw prompt and sk-secret",
        response=response,
        body=None,
    )
    provider = OrcaRouterProvider(
        client=FakeClient(authentication),
        model=ORCAROUTER_MODEL,
    )

    with pytest.raises(ProviderAuthenticationError) as captured:
        provider.chat(text_request())

    assert captured.value.code == "authentication_failed"
    assert "sk-secret" not in str(captured.value)
    assert "raw prompt" not in str(captured.value)

    unknown = OrcaRouterProvider(
        client=FakeClient(RuntimeError("raw body sk-secret")),
        model=ORCAROUTER_MODEL,
    )
    with pytest.raises(ProviderUnavailableError) as captured_unknown:
        unknown.chat(text_request())
    assert captured_unknown.value.code == "unexpected_sdk_error"
    assert "sk-secret" not in str(captured_unknown.value)


def test_orcarouter_settings_are_exact_and_factory_forces_zero_retries():
    values = {
        "ORCAROUTER_API_KEY": "secret-value",
        "ORCAROUTER_BASE_URL": ORCAROUTER_BASE_URL,
        "ORCAROUTER_MODEL": ORCAROUTER_MODEL,
        "ORCAROUTER_TIMEOUT_SECONDS": "42",
        "ORCAROUTER_MAX_RETRIES": "0",
    }
    settings = load_orcarouter_settings(values)
    factory_calls = []

    def factory(**kwargs):
        factory_calls.append(kwargs)
        return FakeClient(sdk_response())

    provider = create_orcarouter_provider(settings, client_factory=factory)

    assert isinstance(provider, OrcaRouterProvider)
    assert "secret-value" not in repr(settings)
    assert factory_calls == [
        {
            "api_key": "secret-value",
            "base_url": ORCAROUTER_BASE_URL,
            "timeout": 42.0,
            "max_retries": 0,
        }
    ]


@pytest.mark.parametrize(
    "overrides",
    (
        {"ORCAROUTER_API_KEY": ""},
        {"ORCAROUTER_BASE_URL": "https://example.invalid"},
        {"ORCAROUTER_MODEL": "orcarouter/free"},
        {"ORCAROUTER_MAX_RETRIES": "1"},
        {"ORCAROUTER_TIMEOUT_SECONDS": "0"},
    ),
)
def test_orcarouter_settings_reject_drift_before_client_creation(overrides):
    values = {
        "ORCAROUTER_API_KEY": "secret-value",
        "ORCAROUTER_BASE_URL": ORCAROUTER_BASE_URL,
        "ORCAROUTER_MODEL": ORCAROUTER_MODEL,
        "ORCAROUTER_TIMEOUT_SECONDS": "30",
        "ORCAROUTER_MAX_RETRIES": "0",
        **overrides,
    }

    with pytest.raises(ProviderConfigurationError):
        load_orcarouter_settings(values)


def test_settings_dataclass_rejects_nonzero_retry_even_without_loader():
    with pytest.raises(ProviderConfigurationError):
        OrcaRouterSettings(
            api_key="secret-value",
            base_url=ORCAROUTER_BASE_URL,
            model=ORCAROUTER_MODEL,
            sdk_max_retries=1,
        )
