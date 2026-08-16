import unittest

from app.providers.capabilities import ProviderCapabilities
from app.providers.config import (
    ProviderRegistrySettings,
    create_provider_registry,
    load_provider_registry_settings,
)
from app.providers.errors import (
    ProviderConfigurationError,
    ProviderRegistryError,
)
from app.providers.models import ChatRequest, ChatResponse, TokenUsage


class FakeProvider:
    provider_name = "fake"
    model_name = "fake-model"
    capabilities = ProviderCapabilities()

    def chat(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(
            content="ok",
            model=self.model_name,
            provider=self.provider_name,
            usage=TokenUsage(input_tokens=0, output_tokens=0),
        )


class ProviderRegistrySettingsTests(unittest.TestCase):
    def test_prefers_explicit_default_provider_setting(self) -> None:
        settings = load_provider_registry_settings(
            {
                "LLM_PROVIDER": "legacy-zhipu",
                "LLM_DEFAULT_PROVIDER": "zhipu-primary",
            }
        )

        self.assertEqual("zhipu-primary", settings.default_provider_id)

    def test_falls_back_to_existing_provider_setting_for_compatibility(self) -> None:
        settings = load_provider_registry_settings(
            {"LLM_PROVIDER": "zhipu"}
        )

        self.assertEqual("zhipu", settings.default_provider_id)

    def test_rejects_blank_default_provider_setting(self) -> None:
        with self.assertRaises(ProviderConfigurationError) as captured:
            load_provider_registry_settings({"LLM_DEFAULT_PROVIDER": ""})

        self.assertEqual(
            "missing_default_provider_id",
            captured.exception.code,
        )

    def test_factory_registers_providers_and_applies_default(self) -> None:
        provider = FakeProvider()
        registry = create_provider_registry(
            {"fake-primary": provider},
            ProviderRegistrySettings(default_provider_id="fake-primary"),
        )

        self.assertIs(provider, registry.resolve())

    def test_factory_fails_when_configured_default_is_not_registered(self) -> None:
        with self.assertRaises(ProviderRegistryError) as captured:
            create_provider_registry(
                {"fake-primary": FakeProvider()},
                ProviderRegistrySettings(default_provider_id="missing"),
            )

        self.assertEqual("unknown_provider_id", captured.exception.code)


if __name__ == "__main__":
    unittest.main()
