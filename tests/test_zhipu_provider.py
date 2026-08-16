import unittest
from types import SimpleNamespace

import httpx
import openai

from app.providers.config import (
    ZhipuSettings,
    create_zhipu_provider,
    load_zhipu_settings,
)
from app.providers.errors import (
    ProviderAuthenticationError,
    ProviderCapabilityError,
    ProviderConfigurationError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
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
from app.providers.zhipu import ZhipuProvider


def sdk_response(
    *,
    content: str | None = "教练报告",
    model: str = "glm-test-resolved",
    prompt_tokens: int = 12,
    completion_tokens: int = 8,
    tool_calls: list[SimpleNamespace] | None = None,
    reasoning_content: object | None = None,
    finish_reason: str = "stop",
):
    return SimpleNamespace(
        id="request-123",
        model=model,
        choices=[
            SimpleNamespace(
                finish_reason=finish_reason,
                message=SimpleNamespace(
                    content=content,
                    tool_calls=tool_calls or [],
                    reasoning_content=reasoning_content,
                ),
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        ),
    )


def sdk_tool_call(
    *,
    call_id: str = "call-1",
    call_type: str = "function",
    name: str = "knowledge_search",
    arguments: str = '{"query":"前15分钟死亡","top_k":1}',
) -> SimpleNamespace:
    return SimpleNamespace(
        id=call_id,
        type=call_type,
        function=SimpleNamespace(name=name, arguments=arguments),
    )


def knowledge_search_spec(name: str = "knowledge.search") -> ToolSpec:
    return ToolSpec(
        name=name,
        description="检索英雄联盟复盘知识。",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer", "minimum": 1},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
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


class ZhipuProviderMappingTests(unittest.TestCase):
    def test_maps_provider_neutral_request_and_normalizes_response(self) -> None:
        client = FakeClient(sdk_response())
        provider = ZhipuProvider(client=client, model="glm-test")
        request = ChatRequest(
            messages=(
                ChatMessage(MessageRole.SYSTEM, "你是教练。"),
                ChatMessage(MessageRole.USER, "请复盘。"),
            ),
            temperature=0.2,
            max_tokens=600,
            timeout_s=17.5,
            metadata={"operation": "coach_generation", "secret": "not-sent"},
        )

        response = provider.chat(request)

        self.assertEqual("教练报告", response.content)
        self.assertEqual("glm-test-resolved", response.model)
        self.assertEqual("zhipu", response.provider)
        self.assertEqual("stop", response.finish_reason)
        self.assertEqual("request-123", response.request_id)
        self.assertEqual(20, response.usage.total_tokens)

        call = client.completions.calls[0]
        self.assertEqual("glm-test", call["model"])
        self.assertEqual(
            [
                {"role": "system", "content": "你是教练。"},
                {"role": "user", "content": "请复盘。"},
            ],
            call["messages"],
        )
        self.assertEqual(0.2, call["temperature"])
        self.assertEqual(600, call["max_tokens"])
        self.assertEqual(17.5, call["timeout"])
        self.assertEqual(
            {"thinking": {"type": "disabled"}},
            call["extra_body"],
        )
        self.assertNotIn("metadata", call)
        self.assertNotIn("secret", str(call))

    def test_omits_optional_max_tokens_with_valid_usage(self) -> None:
        client = FakeClient(sdk_response(prompt_tokens=0, completion_tokens=0))
        provider = ZhipuProvider(client=client, model="glm-test")

        response = provider.chat(
            ChatRequest(
                messages=(ChatMessage(MessageRole.USER, "hello"),),
                max_tokens=None,
            )
        )

        self.assertNotIn("max_tokens", client.completions.calls[0])
        self.assertEqual(0, response.usage.total_tokens)

    def test_missing_or_malformed_usage_is_a_safe_response_error(self) -> None:
        cases = (
            None,
            SimpleNamespace(completion_tokens=1),
            SimpleNamespace(prompt_tokens=1),
            SimpleNamespace(prompt_tokens=None, completion_tokens=1),
            SimpleNamespace(prompt_tokens=True, completion_tokens=1),
            SimpleNamespace(prompt_tokens="1", completion_tokens=1),
            SimpleNamespace(prompt_tokens=-1, completion_tokens=1),
        )

        for usage in cases:
            with self.subTest(usage=usage):
                raw = sdk_response()
                raw.usage = usage
                provider = ZhipuProvider(client=FakeClient(raw), model="glm-test")

                with self.assertRaises(ProviderResponseError) as captured:
                    provider.chat(
                        ChatRequest(
                            messages=(ChatMessage(MessageRole.USER, "hello"),)
                        )
                    )

                self.assertEqual(
                    "provider_usage_unavailable",
                    captured.exception.code,
                )

    def test_empty_or_malformed_sdk_response_becomes_safe_response_error(self) -> None:
        malformed_responses = [
            SimpleNamespace(choices=[]),
            SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=""))],
                usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1),
            ),
            SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=None))],
                usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1),
            ),
        ]

        for raw in malformed_responses:
            with self.subTest(raw=raw):
                provider = ZhipuProvider(client=FakeClient(raw), model="glm-test")
                with self.assertRaises(ProviderResponseError) as captured:
                    provider.chat(
                        ChatRequest(
                            messages=(ChatMessage(MessageRole.USER, "hello"),)
                        )
                    )
                self.assertEqual("invalid_chat_response", captured.exception.code)

    def test_maps_all_message_roles_tools_and_restores_internal_tool_name(
        self,
    ) -> None:
        client = FakeClient(
            sdk_response(
                content=None,
                finish_reason="tool_calls",
                tool_calls=[sdk_tool_call()],
            )
        )
        provider = ZhipuProvider(client=client, model="glm-test")
        request = ChatRequest(
            messages=(
                ChatMessage(MessageRole.SYSTEM, "你是教练。"),
                ChatMessage(MessageRole.USER, "检索前15分钟死亡知识。"),
                ChatMessage(
                    MessageRole.ASSISTANT,
                    None,
                    tool_calls=(
                        ToolCall(
                            id="previous-call",
                            name="knowledge.search",
                            arguments={"query": "兵线", "top_k": 1},
                        ),
                    ),
                ),
                ChatMessage(
                    MessageRole.TOOL,
                    '{"success":true}',
                    tool_call_id="previous-call",
                    name="knowledge.search",
                ),
            ),
            tools=(knowledge_search_spec(),),
            tool_choice=ToolChoiceMode.AUTO,
        )

        response = provider.chat(request)

        call = client.completions.calls[0]
        self.assertEqual(
            "knowledge_search",
            call["tools"][0]["function"]["name"],
        )
        self.assertEqual("auto", call["tool_choice"])
        self.assertEqual(
            "knowledge_search",
            call["messages"][2]["tool_calls"][0]["function"]["name"],
        )
        self.assertEqual(
            '{"query":"兵线","top_k":1}',
            call["messages"][2]["tool_calls"][0]["function"]["arguments"],
        )
        self.assertEqual(
            {
                "role": "tool",
                "content": '{"success":true}',
                "tool_call_id": "previous-call",
            },
            call["messages"][3],
        )
        self.assertIsNone(response.content)
        self.assertEqual("knowledge.search", response.tool_calls[0].name)
        self.assertEqual(
            {"query": "前15分钟死亡", "top_k": 1},
            response.tool_calls[0].arguments,
        )

    def test_none_tool_choice_omits_tool_transport(self) -> None:
        client = FakeClient(sdk_response())
        provider = ZhipuProvider(client=client, model="glm-test")

        provider.chat(
            ChatRequest(
                messages=(ChatMessage(MessageRole.USER, "直接回答。"),),
                tools=(knowledge_search_spec(),),
                tool_choice=ToolChoiceMode.NONE,
            )
        )

        call = client.completions.calls[0]
        self.assertNotIn("tools", call)
        self.assertNotIn("tool_choice", call)

    def test_maps_structured_contract_to_json_object_mode(
        self,
    ) -> None:
        client = FakeClient(sdk_response(content='{"score":90}'))
        provider = ZhipuProvider(client=client, model="glm-test")
        request = ChatRequest(
            messages=(ChatMessage(MessageRole.USER, "返回评测 JSON。"),),
            response_contract=StructuredResponseContract(
                name="coach_evaluation",
                version="1.0.0",
                json_schema={
                    "type": "object",
                    "properties": {"score": {"type": "integer"}},
                    "required": ["score"],
                    "additionalProperties": False,
                },
            ),
        )

        response = provider.chat(request)

        self.assertEqual(
            {"type": "json_object"},
            client.completions.calls[0]["response_format"],
        )
        self.assertEqual('{"score":90}', response.content)

    def test_required_tool_choice_is_rejected_before_sdk_call(self) -> None:
        client = FakeClient(sdk_response())
        provider = ZhipuProvider(client=client, model="glm-test")

        with self.assertRaises(ProviderCapabilityError) as captured:
            provider.chat(
                ChatRequest(
                    messages=(ChatMessage(MessageRole.USER, "必须检索。"),),
                    tools=(knowledge_search_spec(),),
                    tool_choice=ToolChoiceMode.REQUIRED,
                )
            )

        self.assertEqual("unsupported_capability", captured.exception.code)
        self.assertEqual(
            ("required_tool_choice",),
            captured.exception.missing_capabilities,
        )
        self.assertEqual([], client.completions.calls)

    def test_rejects_unadmitted_structured_tool_combination_before_sdk_call(
        self,
    ) -> None:
        client = FakeClient(sdk_response())
        provider = ZhipuProvider(client=client, model="glm-test")

        with self.assertRaises(ProviderCapabilityError) as captured:
            provider.chat(
                ChatRequest(
                    messages=(ChatMessage(MessageRole.USER, "检索后返回 JSON。"),),
                    tools=(knowledge_search_spec(),),
                    response_contract=StructuredResponseContract(
                        name="tool_evaluation",
                        version="1.0.0",
                        json_schema={
                            "type": "object",
                            "properties": {"answer": {"type": "string"}},
                            "required": ["answer"],
                            "additionalProperties": False,
                        },
                    ),
                )
            )

        self.assertEqual(
            ("structured_tool_combination",),
            captured.exception.missing_capabilities,
        )
        self.assertEqual([], client.completions.calls)

    def test_rejects_invalid_or_array_tool_arguments(self) -> None:
        for arguments in (
            "not-json",
            '[{"query":"兵线"}]',
            '{"query":NaN}',
            '{"query":"兵线","query":"视野"}',
        ):
            with self.subTest(arguments=arguments):
                provider = ZhipuProvider(
                    client=FakeClient(
                        sdk_response(
                            content=None,
                            finish_reason="tool_calls",
                            tool_calls=[sdk_tool_call(arguments=arguments)],
                        )
                    ),
                    model="glm-test",
                )
                with self.assertRaises(ProviderResponseError) as captured:
                    provider.chat(
                        ChatRequest(
                            messages=(ChatMessage(MessageRole.USER, "检索。"),),
                            tools=(knowledge_search_spec(),),
                        )
                    )
                self.assertEqual(
                    "invalid_tool_call_response",
                    captured.exception.code,
                )

    def test_rejects_non_json_historical_tool_arguments_before_sdk_call(
        self,
    ) -> None:
        client = FakeClient(sdk_response())
        provider = ZhipuProvider(client=client, model="glm-test")

        with self.assertRaises(ProviderResponseError) as captured:
            provider.chat(
                ChatRequest(
                    messages=(
                        ChatMessage(MessageRole.USER, "检索。"),
                        ChatMessage(
                            MessageRole.ASSISTANT,
                            None,
                            tool_calls=(
                                ToolCall(
                                    id="call-1",
                                    name="knowledge.search",
                                    arguments={"top_k": float("nan")},
                                ),
                            ),
                        ),
                    ),
                    tools=(knowledge_search_spec(),),
                )
            )

        self.assertEqual("invalid_tool_call_request", captured.exception.code)
        self.assertEqual([], client.completions.calls)

    def test_rejects_unadmitted_parallel_historical_tool_calls_before_sdk(
        self,
    ) -> None:
        client = FakeClient(sdk_response())
        provider = ZhipuProvider(client=client, model="glm-test")

        with self.assertRaises(ProviderResponseError) as captured:
            provider.chat(
                ChatRequest(
                    messages=(
                        ChatMessage(MessageRole.USER, "检索。"),
                        ChatMessage(
                            MessageRole.ASSISTANT,
                            None,
                            tool_calls=(
                                ToolCall(
                                    id="call-1",
                                    name="knowledge.search",
                                    arguments={"query": "兵线"},
                                ),
                                ToolCall(
                                    id="call-2",
                                    name="knowledge.search",
                                    arguments={"query": "视野"},
                                ),
                            ),
                        ),
                    ),
                    tools=(knowledge_search_spec(),),
                )
            )

        self.assertEqual("unsupported_parallel_tool_calls", captured.exception.code)
        self.assertEqual([], client.completions.calls)

    def test_rejects_non_function_tool_call_response(self) -> None:
        provider = ZhipuProvider(
            client=FakeClient(
                sdk_response(
                    content=None,
                    finish_reason="tool_calls",
                    tool_calls=[sdk_tool_call(call_type="custom")],
                )
            ),
            model="glm-test",
        )

        with self.assertRaises(ProviderResponseError) as captured:
            provider.chat(
                ChatRequest(
                    messages=(ChatMessage(MessageRole.USER, "检索。"),),
                    tools=(knowledge_search_spec(),),
                )
            )

        self.assertEqual("invalid_tool_call_response", captured.exception.code)

    def test_rejects_unknown_tool_alias_or_empty_tool_name(self) -> None:
        for name in ("unknown_alias", ""):
            with self.subTest(name=name):
                provider = ZhipuProvider(
                    client=FakeClient(
                        sdk_response(
                            content=None,
                            finish_reason="tool_calls",
                            tool_calls=[sdk_tool_call(name=name)],
                        )
                    ),
                    model="glm-test",
                )
                with self.assertRaises(ProviderResponseError) as captured:
                    provider.chat(
                        ChatRequest(
                            messages=(ChatMessage(MessageRole.USER, "检索。"),),
                            tools=(knowledge_search_spec(),),
                        )
                    )
                self.assertEqual(
                    "invalid_tool_call_response",
                    captured.exception.code,
                )

    def test_rejects_duplicate_returned_tool_call_ids(self) -> None:
        provider = ZhipuProvider(
            client=FakeClient(
                sdk_response(
                    content=None,
                    finish_reason="tool_calls",
                    tool_calls=[
                        sdk_tool_call(call_id="duplicate"),
                        sdk_tool_call(call_id=" duplicate "),
                    ],
                )
            ),
            model="glm-test",
        )

        with self.assertRaises(ProviderResponseError) as captured:
            provider.chat(
                ChatRequest(
                    messages=(ChatMessage(MessageRole.USER, "检索。"),),
                    tools=(knowledge_search_spec(),),
                )
            )

        self.assertEqual("invalid_tool_call_response", captured.exception.code)

    def test_rejects_unadmitted_parallel_tool_calls(self) -> None:
        provider = ZhipuProvider(
            client=FakeClient(
                sdk_response(
                    content=None,
                    finish_reason="tool_calls",
                    tool_calls=[
                        sdk_tool_call(call_id="call-1"),
                        sdk_tool_call(call_id="call-2"),
                    ],
                )
            ),
            model="glm-test",
        )

        with self.assertRaises(ProviderResponseError) as captured:
            provider.chat(
                ChatRequest(
                    messages=(ChatMessage(MessageRole.USER, "检索。"),),
                    tools=(knowledge_search_spec(),),
                )
            )

        self.assertEqual("unsupported_parallel_tool_calls", captured.exception.code)

    def test_rejects_tool_call_with_inconsistent_finish_reason(self) -> None:
        provider = ZhipuProvider(
            client=FakeClient(
                sdk_response(
                    content=None,
                    finish_reason="stop",
                    tool_calls=[sdk_tool_call()],
                )
            ),
            model="glm-test",
        )

        with self.assertRaises(ProviderResponseError) as captured:
            provider.chat(
                ChatRequest(
                    messages=(ChatMessage(MessageRole.USER, "检索。"),),
                    tools=(knowledge_search_spec(),),
                )
            )

        self.assertEqual("invalid_tool_call_response", captured.exception.code)

    def test_rejects_tool_finish_reason_without_tool_call(self) -> None:
        provider = ZhipuProvider(
            client=FakeClient(sdk_response(finish_reason="tool_calls")),
            model="glm-test",
        )

        with self.assertRaises(ProviderResponseError) as captured:
            provider.chat(
                ChatRequest(
                    messages=(ChatMessage(MessageRole.USER, "检索。"),),
                    tools=(knowledge_search_spec(),),
                )
            )

        self.assertEqual("invalid_tool_call_response", captured.exception.code)

    def test_rejects_deterministic_tool_alias_collisions_before_sdk_call(
        self,
    ) -> None:
        client = FakeClient(sdk_response())
        provider = ZhipuProvider(client=client, model="glm-test")

        with self.assertRaises(ProviderResponseError) as captured:
            provider.chat(
                ChatRequest(
                    messages=(ChatMessage(MessageRole.USER, "检索。"),),
                    tools=(
                        knowledge_search_spec("knowledge.search"),
                        knowledge_search_spec("knowledge_search"),
                    ),
                )
            )

        self.assertEqual("tool_name_alias_conflict", captured.exception.code)
        self.assertEqual([], client.completions.calls)

    def test_rejects_reasoning_content_that_cannot_be_replayed(self) -> None:
        for reasoning_content in ("hidden state", {"hidden": "state"}):
            with self.subTest(reasoning_content=reasoning_content):
                provider = ZhipuProvider(
                    client=FakeClient(
                        sdk_response(reasoning_content=reasoning_content)
                    ),
                    model="glm-test",
                )

                with self.assertRaises(ProviderResponseError) as captured:
                    provider.chat(
                        ChatRequest(
                            messages=(ChatMessage(MessageRole.USER, "回答。"),)
                        )
                    )

                self.assertEqual(
                    "unexpected_reasoning_content",
                    captured.exception.code,
                )

    def test_rejects_non_string_content_even_when_tool_call_exists(self) -> None:
        provider = ZhipuProvider(
            client=FakeClient(
                sdk_response(
                    content={"unexpected": "shape"},  # type: ignore[arg-type]
                    finish_reason="tool_calls",
                    tool_calls=[sdk_tool_call()],
                )
            ),
            model="glm-test",
        )

        with self.assertRaises(ProviderResponseError) as captured:
            provider.chat(
                ChatRequest(
                    messages=(ChatMessage(MessageRole.USER, "检索。"),),
                    tools=(knowledge_search_spec(),),
                )
            )

        self.assertEqual("invalid_chat_response", captured.exception.code)


class ZhipuProviderErrorMappingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.request = httpx.Request("POST", "https://example.invalid/chat")
        self.chat_request = ChatRequest(
            messages=(ChatMessage(MessageRole.USER, "safe prompt"),)
        )

    def test_maps_known_sdk_errors_without_leaking_sdk_message(self) -> None:
        response_401 = httpx.Response(401, request=self.request)
        response_429 = httpx.Response(429, request=self.request)
        response_503 = httpx.Response(503, request=self.request)
        cases = [
            (
                openai.AuthenticationError(
                    "contains sk-secret",
                    response=response_401,
                    body=None,
                ),
                ProviderAuthenticationError,
                "authentication_failed",
            ),
            (
                openai.RateLimitError(
                    "raw prompt and sk-secret",
                    response=response_429,
                    body=None,
                ),
                ProviderRateLimitError,
                "rate_limited",
            ),
            (
                openai.APITimeoutError(request=self.request),
                ProviderTimeoutError,
                "timeout",
            ),
            (
                openai.APIConnectionError(request=self.request),
                ProviderUnavailableError,
                "connection_failed",
            ),
            (
                openai.APIStatusError(
                    "upstream contains sk-secret",
                    response=response_503,
                    body=None,
                ),
                ProviderUnavailableError,
                "service_unavailable",
            ),
        ]

        for sdk_error, expected_type, expected_code in cases:
            with self.subTest(expected_type=expected_type.__name__):
                provider = ZhipuProvider(
                    client=FakeClient(sdk_error),
                    model="glm-test",
                )
                with self.assertRaises(expected_type) as captured:
                    provider.chat(self.chat_request)
                self.assertEqual(expected_code, captured.exception.code)
                self.assertNotIn("sk-secret", str(captured.exception))
                self.assertNotIn("raw prompt", str(captured.exception))

    def test_non_retryable_bad_request_maps_to_response_error(self) -> None:
        response = httpx.Response(400, request=self.request)
        provider = ZhipuProvider(
            client=FakeClient(
                openai.BadRequestError(
                    "bad raw prompt",
                    response=response,
                    body=None,
                )
            ),
            model="glm-test",
        )

        with self.assertRaises(ProviderResponseError) as captured:
            provider.chat(self.chat_request)

        self.assertEqual("request_rejected", captured.exception.code)
        self.assertFalse(captured.exception.retryable)

    def test_unknown_sdk_exception_is_sanitized(self) -> None:
        provider = ZhipuProvider(
            client=FakeClient(RuntimeError("sk-secret and raw prompt")),
            model="glm-test",
        )

        with self.assertRaises(ProviderUnavailableError) as captured:
            provider.chat(self.chat_request)

        self.assertEqual("unexpected_sdk_error", captured.exception.code)
        self.assertNotIn("sk-secret", str(captured.exception))


class ZhipuSettingsTests(unittest.TestCase):
    def test_loads_settings_from_explicit_mapping(self) -> None:
        settings = load_zhipu_settings(
            {
                "LLM_PROVIDER": "zhipu",
                "LLM_API_KEY": "secret-value",
                "LLM_BASE_URL": "https://open.bigmodel.cn/api/paas/v4/",
                "LLM_MODEL": "glm-test",
                "LLM_TIMEOUT_SECONDS": "42.5",
            }
        )

        self.assertEqual("glm-test", settings.model)
        self.assertEqual(42.5, settings.default_timeout_s)
        self.assertNotIn("secret-value", repr(settings))

    def test_rejects_missing_or_wrong_provider_configuration(self) -> None:
        valid = {
            "LLM_PROVIDER": "zhipu",
            "LLM_API_KEY": "secret-value",
            "LLM_BASE_URL": "https://example.invalid/v1/",
            "LLM_MODEL": "glm-test",
        }
        cases = [
            {**valid, "LLM_API_KEY": ""},
            {**valid, "LLM_BASE_URL": ""},
            {**valid, "LLM_MODEL": ""},
            {**valid, "LLM_PROVIDER": "deepseek"},
            {**valid, "LLM_TIMEOUT_SECONDS": "not-a-number"},
            {**valid, "LLM_TIMEOUT_SECONDS": "0"},
        ]

        for values in cases:
            with self.subTest(values=values):
                with self.assertRaises(ProviderConfigurationError):
                    load_zhipu_settings(values)

    def test_factory_injects_settings_without_exposing_key(self) -> None:
        settings = ZhipuSettings(
            api_key="secret-value",
            base_url="https://example.invalid/v1/",
            model="glm-test",
            default_timeout_s=25.0,
        )
        factory_calls = []

        def client_factory(**kwargs):
            factory_calls.append(kwargs)
            return FakeClient(sdk_response())

        provider = create_zhipu_provider(
            settings,
            client_factory=client_factory,
        )

        self.assertIsInstance(provider, ZhipuProvider)
        self.assertEqual("glm-test", provider.model_name)
        self.assertEqual(
            [
                {
                    "api_key": "secret-value",
                    "base_url": "https://example.invalid/v1/",
                    "timeout": 25.0,
                }
            ],
            factory_calls,
        )


if __name__ == "__main__":
    unittest.main()
