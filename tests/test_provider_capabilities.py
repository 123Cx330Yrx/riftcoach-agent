import unittest

from app.providers.capabilities import (
    ProviderCapabilities,
    ProviderCapability,
    negotiate_capabilities,
    require_provider_capabilities,
    required_capabilities_for,
)
from app.providers.errors import ProviderCapabilityError
from app.providers.models import (
    ChatMessage,
    ChatRequest,
    MessageRole,
    StructuredResponseContract,
    ToolChoiceMode,
    ToolSpec,
)


def user_message() -> tuple[ChatMessage, ...]:
    return (ChatMessage(MessageRole.USER, "复盘最近十局。"),)


def tool_spec() -> ToolSpec:
    return ToolSpec(
        name="riot.recent_match_ids",
        description="查询玩家最近的对局 ID。",
        input_schema={
            "type": "object",
            "properties": {"puuid": {"type": "string"}},
            "required": ["puuid"],
            "additionalProperties": False,
        },
    )


def response_contract() -> StructuredResponseContract:
    return StructuredResponseContract(
        name="coach_evaluation",
        version="1.0.0",
        json_schema={
            "type": "object",
            "properties": {"score": {"type": "integer"}},
            "required": ["score"],
            "additionalProperties": False,
        },
    )


class ProviderCapabilitiesTests(unittest.TestCase):
    def test_defaults_describe_a_text_only_adapter(self) -> None:
        capabilities = ProviderCapabilities()

        self.assertEqual(
            frozenset({ProviderCapability.TEXT_CHAT}),
            capabilities.supported,
        )

    def test_parallel_calls_cannot_exist_without_tool_calling(self) -> None:
        with self.assertRaises(ValueError):
            ProviderCapabilities(
                tool_calling=False,
                parallel_tool_calls=True,
            )

    def test_capability_flags_must_be_real_booleans(self) -> None:
        with self.assertRaises(ValueError):
            ProviderCapabilities(tool_calling=1)  # type: ignore[arg-type]


class CapabilityNegotiationTests(unittest.TestCase):
    def test_text_request_only_requires_text_chat(self) -> None:
        request = ChatRequest(messages=user_message())

        self.assertEqual(
            frozenset({ProviderCapability.TEXT_CHAT}),
            required_capabilities_for(request),
        )
        self.assertTrue(
            negotiate_capabilities(ProviderCapabilities(), request).compatible
        )

    def test_auto_tools_require_tool_calling_support(self) -> None:
        request = ChatRequest(
            messages=user_message(),
            tools=(tool_spec(),),
            tool_choice=ToolChoiceMode.AUTO,
        )

        decision = negotiate_capabilities(ProviderCapabilities(), request)

        self.assertFalse(decision.compatible)
        self.assertEqual(
            frozenset({ProviderCapability.TOOL_CALLING}),
            decision.missing,
        )

    def test_none_policy_does_not_require_tool_calling(self) -> None:
        request = ChatRequest(
            messages=user_message(),
            tools=(tool_spec(),),
            tool_choice=ToolChoiceMode.NONE,
        )

        decision = negotiate_capabilities(ProviderCapabilities(), request)

        self.assertTrue(decision.compatible)
        self.assertNotIn(
            ProviderCapability.TOOL_CALLING,
            decision.required,
        )

    def test_response_contract_requires_structured_output_support(self) -> None:
        request = ChatRequest(
            messages=user_message(),
            response_contract=response_contract(),
        )

        decision = negotiate_capabilities(ProviderCapabilities(), request)

        self.assertFalse(decision.compatible)
        self.assertEqual(
            frozenset({ProviderCapability.STRUCTURED_OUTPUT}),
            decision.missing,
        )

    def test_structured_output_capability_satisfies_response_contract(self) -> None:
        request = ChatRequest(
            messages=user_message(),
            response_contract=response_contract(),
        )

        decision = require_provider_capabilities(
            provider_name="fake",
            capabilities=ProviderCapabilities(structured_output=True),
            request=request,
        )

        self.assertTrue(decision.compatible)

    def test_supported_tool_request_passes_negotiation(self) -> None:
        request = ChatRequest(
            messages=user_message(),
            tools=(tool_spec(),),
            tool_choice=ToolChoiceMode.REQUIRED,
        )
        capabilities = ProviderCapabilities(tool_calling=True)

        decision = require_provider_capabilities(
            provider_name="fake",
            capabilities=capabilities,
            request=request,
        )

        self.assertTrue(decision.compatible)

    def test_missing_capability_raises_safe_typed_error(self) -> None:
        request = ChatRequest(
            messages=user_message(),
            tools=(tool_spec(),),
        )

        with self.assertRaises(ProviderCapabilityError) as captured:
            require_provider_capabilities(
                provider_name="text-only",
                capabilities=ProviderCapabilities(),
                request=request,
            )

        error = captured.exception
        self.assertEqual("unsupported_capability", error.code)
        self.assertEqual(("tool_calling",), error.missing_capabilities)
        self.assertFalse(error.retryable)


if __name__ == "__main__":
    unittest.main()
