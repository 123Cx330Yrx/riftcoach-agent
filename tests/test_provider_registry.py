import unittest

from app.providers.capabilities import ProviderCapabilities
from app.providers.errors import (
    ProviderCapabilityError,
    ProviderRegistryError,
)
from app.providers.models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    MessageRole,
    ToolSpec,
)
from app.providers.registry import ProviderRegistry


class FakeProvider:
    def __init__(
        self,
        *,
        provider_name: str,
        model_name: str,
        capabilities: ProviderCapabilities,
    ) -> None:
        self.provider_name = provider_name
        self.model_name = model_name
        self.capabilities = capabilities

    def chat(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(
            content=request.messages[-1].content,
            model=self.model_name,
            provider=self.provider_name,
        )


def text_provider(name: str = "text") -> FakeProvider:
    return FakeProvider(
        provider_name=name,
        model_name=f"{name}-model",
        capabilities=ProviderCapabilities(text_chat=True),
    )


def tool_provider(name: str = "tool") -> FakeProvider:
    return FakeProvider(
        provider_name=name,
        model_name=f"{name}-model",
        capabilities=ProviderCapabilities(
            text_chat=True,
            tool_calling=True,
        ),
    )


def text_request() -> ChatRequest:
    return ChatRequest(
        messages=(ChatMessage(MessageRole.USER, "复盘最近十局。"),)
    )


def tool_request() -> ChatRequest:
    return ChatRequest(
        messages=(ChatMessage(MessageRole.USER, "查询最近十局。"),),
        tools=(
            ToolSpec(
                name="riot.recent_match_ids",
                description="查询最近比赛。",
                input_schema={"type": "object", "properties": {}},
            ),
        ),
    )


class ProviderRegistryTests(unittest.TestCase):
    def test_registers_and_resolves_explicit_and_default_providers(self) -> None:
        registry = ProviderRegistry()
        first = text_provider("zhipu")
        second = tool_provider("other")
        registry.register("zhipu-primary", first)
        registry.register("other-tools", second)
        registry.set_default("zhipu-primary")

        self.assertIs(first, registry.resolve())
        self.assertIs(second, registry.resolve("other-tools"))
        self.assertEqual("zhipu-primary", registry.default_provider_id)

    def test_rejects_duplicate_unknown_and_invalid_provider_ids(self) -> None:
        registry = ProviderRegistry()
        registry.register("zhipu-primary", text_provider())

        with self.assertRaises(ProviderRegistryError) as duplicate:
            registry.register("zhipu-primary", text_provider("other"))
        self.assertEqual("duplicate_provider_id", duplicate.exception.code)

        with self.assertRaises(ProviderRegistryError) as unknown:
            registry.resolve("missing")
        self.assertEqual("unknown_provider_id", unknown.exception.code)

        with self.assertRaises(ValueError):
            registry.register("Zhipu Primary", text_provider())

    def test_requires_an_explicit_default_before_implicit_resolution(self) -> None:
        registry = ProviderRegistry()
        registry.register("zhipu", text_provider())

        with self.assertRaises(ProviderRegistryError) as captured:
            registry.resolve()

        self.assertEqual(
            "default_provider_not_configured",
            captured.exception.code,
        )

    def test_rejects_objects_that_do_not_implement_provider_protocol(self) -> None:
        registry = ProviderRegistry()

        with self.assertRaises(ProviderRegistryError) as captured:
            registry.register("invalid", object())  # type: ignore[arg-type]

        self.assertEqual("invalid_provider_contract", captured.exception.code)

        malformed = text_provider()
        malformed.capabilities = "tool-calling"  # type: ignore[assignment]
        with self.assertRaises(ProviderRegistryError):
            registry.register("malformed", malformed)

    def test_explicit_blank_id_does_not_fall_back_to_default(self) -> None:
        registry = ProviderRegistry()
        registry.register("zhipu", text_provider())
        registry.set_default("zhipu")

        with self.assertRaises(ValueError):
            registry.resolve("")
        with self.assertRaises(ValueError):
            registry.select(text_request(), "")

    def test_selection_is_explicit_and_does_not_silently_fallback(self) -> None:
        registry = ProviderRegistry()
        registry.register("text-only", text_provider())
        registry.register("tool-ready", tool_provider())
        registry.set_default("text-only")

        with self.assertRaises(ProviderCapabilityError):
            registry.select(tool_request())

        self.assertEqual(
            ("tool-ready",),
            registry.compatible_provider_ids(tool_request()),
        )
        selection = registry.select(tool_request(), "tool-ready")
        self.assertEqual("tool-ready", selection.provider_id)
        self.assertTrue(selection.negotiation.compatible)

    def test_descriptors_are_safe_sorted_snapshots(self) -> None:
        registry = ProviderRegistry()
        registry.register("z-second", tool_provider("second"))
        registry.register("a-first", text_provider("first"))
        registry.set_default("a-first")

        descriptors = registry.descriptors()

        self.assertEqual(
            ("a-first", "z-second"),
            tuple(item.provider_id for item in descriptors),
        )
        self.assertTrue(descriptors[0].is_default)
        self.assertEqual("first-model", descriptors[0].model_name)
        self.assertNotIn("api_key", repr(descriptors))


if __name__ == "__main__":
    unittest.main()
