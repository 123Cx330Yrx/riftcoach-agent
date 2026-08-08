"""Provider-neutral model contracts and implementations."""

from .capabilities import (
    CapabilityNegotiation,
    ProviderCapabilities,
    ProviderCapability,
    negotiate_capabilities,
    require_provider_capabilities,
    required_capabilities_for,
)
from .config import (
    ProviderRegistrySettings,
    ZhipuSettings,
    create_provider_registry,
    create_zhipu_provider,
    load_provider_registry_settings,
    load_zhipu_settings,
)
from .errors import (
    ProviderAuthenticationError,
    ProviderCapabilityError,
    ProviderConfigurationError,
    ProviderError,
    ProviderRateLimitError,
    ProviderRegistryError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from .models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    MessageRole,
    StructuredResponseContract,
    TokenUsage,
    ToolCall,
    ToolChoiceMode,
    ToolSpec,
)
from .protocol import LLMProvider
from .registry import (
    ProviderDescriptor,
    ProviderRegistry,
    ProviderSelection,
)
from .zhipu import ZhipuProvider
from .structured import (
    StructuredDecodeResult,
    StructuredRepairRequest,
    contract_for_model,
    decode_structured_response,
)

__all__ = [
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "CapabilityNegotiation",
    "LLMProvider",
    "MessageRole",
    "ProviderAuthenticationError",
    "ProviderCapabilities",
    "ProviderCapability",
    "ProviderCapabilityError",
    "ProviderConfigurationError",
    "ProviderError",
    "ProviderRateLimitError",
    "ProviderDescriptor",
    "ProviderRegistry",
    "ProviderRegistryError",
    "ProviderRegistrySettings",
    "ProviderResponseError",
    "ProviderTimeoutError",
    "ProviderUnavailableError",
    "ProviderSelection",
    "StructuredResponseContract",
    "StructuredDecodeResult",
    "StructuredRepairRequest",
    "TokenUsage",
    "ToolCall",
    "ToolChoiceMode",
    "ToolSpec",
    "ZhipuProvider",
    "ZhipuSettings",
    "create_provider_registry",
    "create_zhipu_provider",
    "contract_for_model",
    "decode_structured_response",
    "load_provider_registry_settings",
    "load_zhipu_settings",
    "negotiate_capabilities",
    "require_provider_capabilities",
    "required_capabilities_for",
]
