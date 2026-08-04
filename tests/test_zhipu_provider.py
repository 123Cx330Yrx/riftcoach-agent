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
    ToolSpec,
)
from app.providers.zhipu import ZhipuProvider


def sdk_response(
    *,
    content: str = "教练报告",
    model: str = "glm-test-resolved",
    prompt_tokens: int = 12,
    completion_tokens: int = 8,
):
    return SimpleNamespace(
        id="request-123",
        model=model,
        choices=[
            SimpleNamespace(
                finish_reason="stop",
                message=SimpleNamespace(content=content),
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        ),
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
        self.assertNotIn("metadata", call)
        self.assertNotIn("secret", str(call))

    def test_omits_optional_max_tokens_and_accepts_missing_usage(self) -> None:
        raw = sdk_response()
        raw.usage = None
        client = FakeClient(raw)
        provider = ZhipuProvider(client=client, model="glm-test")

        response = provider.chat(
            ChatRequest(
                messages=(ChatMessage(MessageRole.USER, "hello"),),
                max_tokens=None,
            )
        )

        self.assertNotIn("max_tokens", client.completions.calls[0])
        self.assertEqual(0, response.usage.total_tokens)

    def test_empty_or_malformed_sdk_response_becomes_safe_response_error(self) -> None:
        malformed_responses = [
            SimpleNamespace(choices=[]),
            SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=""))]
            ),
            SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=None))]
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

    def test_rejects_tool_request_before_calling_sdk_until_mapping_exists(self) -> None:
        client = FakeClient(sdk_response())
        provider = ZhipuProvider(client=client, model="glm-test")
        request = ChatRequest(
            messages=(ChatMessage(MessageRole.USER, "查询最近比赛。"),),
            tools=(
                ToolSpec(
                    name="riot.recent_match_ids",
                    description="查询最近比赛。",
                    input_schema={"type": "object", "properties": {}},
                ),
            ),
        )

        with self.assertRaises(ProviderCapabilityError) as captured:
            provider.chat(request)

        self.assertEqual(
            ("tool_calling",),
            captured.exception.missing_capabilities,
        )
        self.assertEqual([], client.completions.calls)


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
