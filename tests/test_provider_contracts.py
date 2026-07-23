import unittest

from app.providers.errors import (
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.providers.models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    MessageRole,
    TokenUsage,
)
from app.providers.protocol import LLMProvider


class ProviderModelTests(unittest.TestCase):
    def test_chat_request_accepts_bounded_provider_neutral_fields(self) -> None:
        request = ChatRequest(
            messages=(
                ChatMessage(MessageRole.SYSTEM, "你是 RiftCoach。"),
                ChatMessage(MessageRole.USER, "复盘最近两局。"),
            ),
            temperature=0.2,
            max_tokens=800,
            timeout_s=15.0,
            metadata={"operation": "coach_generation"},
        )

        self.assertEqual(2, len(request.messages))
        self.assertEqual("coach_generation", request.metadata["operation"])

    def test_chat_request_rejects_empty_messages(self) -> None:
        with self.assertRaises(ValueError):
            ChatRequest(messages=())

    def test_chat_message_rejects_invalid_role_and_empty_content(self) -> None:
        with self.assertRaises(ValueError):
            ChatMessage("user", "content")  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            ChatMessage(MessageRole.USER, "   ")

    def test_chat_request_rejects_invalid_generation_bounds(self) -> None:
        message = (ChatMessage(MessageRole.USER, "hello"),)
        for temperature in (-0.1, 2.1):
            with self.subTest(temperature=temperature):
                with self.assertRaises(ValueError):
                    ChatRequest(messages=message, temperature=temperature)
        with self.assertRaises(ValueError):
            ChatRequest(messages=message, max_tokens=0)
        with self.assertRaises(ValueError):
            ChatRequest(messages=message, timeout_s=0)

    def test_token_usage_validates_counts_and_computes_total(self) -> None:
        usage = TokenUsage(input_tokens=12, output_tokens=8)
        self.assertEqual(20, usage.total_tokens)

        with self.assertRaises(ValueError):
            TokenUsage(input_tokens=-1, output_tokens=0)

    def test_chat_response_requires_attributable_non_empty_content(self) -> None:
        response = ChatResponse(
            content="报告内容",
            model="glm-test",
            provider="zhipu",
            finish_reason="stop",
            usage=TokenUsage(input_tokens=10, output_tokens=5),
            request_id="request-1",
        )
        self.assertEqual("报告内容", response.content)
        self.assertEqual(15, response.usage.total_tokens)

        for kwargs in (
            {"content": "", "model": "glm", "provider": "zhipu"},
            {"content": "ok", "model": "", "provider": "zhipu"},
            {"content": "ok", "model": "glm", "provider": ""},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    ChatResponse(**kwargs)


class FakeProvider:
    provider_name = "fake"

    def chat(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(
            content=request.messages[-1].content,
            model="fake-model",
            provider=self.provider_name,
        )


class ProviderProtocolTests(unittest.TestCase):
    def test_protocol_supports_replaceable_provider_implementations(self) -> None:
        provider = FakeProvider()
        self.assertIsInstance(provider, LLMProvider)
        response = provider.chat(
            ChatRequest(messages=(ChatMessage(MessageRole.USER, "hello"),))
        )
        self.assertEqual("hello", response.content)


class ProviderErrorTests(unittest.TestCase):
    def test_error_taxonomy_exposes_safe_operational_metadata(self) -> None:
        errors = [
            ProviderConfigurationError(provider="zhipu", code="missing_model"),
            ProviderAuthenticationError(provider="zhipu", code="unauthorized"),
            ProviderRateLimitError(provider="zhipu", code="rate_limited"),
            ProviderTimeoutError(provider="zhipu", code="timeout"),
            ProviderUnavailableError(provider="zhipu", code="unavailable"),
            ProviderResponseError(provider="zhipu", code="empty_content"),
        ]

        for error in errors:
            with self.subTest(error=type(error).__name__):
                self.assertIsInstance(error, ProviderError)
                self.assertEqual("zhipu", error.provider)
                self.assertNotIn("sk-secret", str(error))
                self.assertNotIn("raw prompt", str(error))

        self.assertFalse(errors[0].retryable)
        self.assertFalse(errors[1].retryable)
        self.assertTrue(errors[2].retryable)
        self.assertTrue(errors[3].retryable)
        self.assertTrue(errors[4].retryable)
        self.assertFalse(errors[5].retryable)

    def test_error_constructor_does_not_accept_credentials_or_raw_request(self) -> None:
        with self.assertRaises(TypeError):
            ProviderError(  # type: ignore[call-arg]
                provider="zhipu",
                code="bad",
                credential="sk-secret",
            )
        with self.assertRaises(TypeError):
            ProviderError(  # type: ignore[call-arg]
                provider="zhipu",
                code="bad",
                raw_request="raw prompt",
            )


if __name__ == "__main__":
    unittest.main()
