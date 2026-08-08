from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .errors import ProviderCapabilityError
from .models import ChatRequest, ToolChoiceMode


class ProviderCapability(str, Enum):
    """One provider feature understood by the RiftCoach runtime."""

    TEXT_CHAT = "text_chat"
    TOOL_CALLING = "tool_calling"
    STRUCTURED_OUTPUT = "structured_output"
    STREAMING = "streaming"
    PARALLEL_TOOL_CALLS = "parallel_tool_calls"


@dataclass(frozen=True)
class ProviderCapabilities:
    """Features implemented end to end by one configured provider adapter."""

    text_chat: bool = True
    tool_calling: bool = False
    structured_output: bool = False
    streaming: bool = False
    parallel_tool_calls: bool = False

    def __post_init__(self) -> None:
        values = (
            self.text_chat,
            self.tool_calling,
            self.structured_output,
            self.streaming,
            self.parallel_tool_calls,
        )
        if not all(isinstance(value, bool) for value in values):
            raise ValueError("provider capabilities must be booleans.")
        if self.parallel_tool_calls and not self.tool_calling:
            raise ValueError(
                "parallel tool calls require tool calling support."
            )

    @property
    def supported(self) -> frozenset[ProviderCapability]:
        flags = {
            ProviderCapability.TEXT_CHAT: self.text_chat,
            ProviderCapability.TOOL_CALLING: self.tool_calling,
            ProviderCapability.STRUCTURED_OUTPUT: self.structured_output,
            ProviderCapability.STREAMING: self.streaming,
            ProviderCapability.PARALLEL_TOOL_CALLS: self.parallel_tool_calls,
        }
        return frozenset(feature for feature, enabled in flags.items() if enabled)


@dataclass(frozen=True)
class CapabilityNegotiation:
    """Result of comparing request requirements with adapter capabilities."""

    required: frozenset[ProviderCapability]
    supported: frozenset[ProviderCapability]
    missing: frozenset[ProviderCapability]

    @property
    def compatible(self) -> bool:
        return not self.missing


def required_capabilities_for(
    request: ChatRequest,
) -> frozenset[ProviderCapability]:
    """Derive explicit runtime requirements from a provider-neutral request."""

    required = {ProviderCapability.TEXT_CHAT}
    if request.tools and request.tool_choice is not ToolChoiceMode.NONE:
        required.add(ProviderCapability.TOOL_CALLING)
    if request.response_contract is not None:
        required.add(ProviderCapability.STRUCTURED_OUTPUT)
    return frozenset(required)


def negotiate_capabilities(
    capabilities: ProviderCapabilities,
    request: ChatRequest,
) -> CapabilityNegotiation:
    """Compare one request with one adapter without performing I/O."""

    if not isinstance(capabilities, ProviderCapabilities):
        raise ValueError("capabilities must be ProviderCapabilities.")
    if not isinstance(request, ChatRequest):
        raise ValueError("request must be a ChatRequest.")

    required = required_capabilities_for(request)
    supported = capabilities.supported
    return CapabilityNegotiation(
        required=required,
        supported=supported,
        missing=required - supported,
    )


def require_provider_capabilities(
    *,
    provider_name: str,
    capabilities: ProviderCapabilities,
    request: ChatRequest,
) -> CapabilityNegotiation:
    """Return a successful decision or fail before an external SDK call."""

    decision = negotiate_capabilities(capabilities, request)
    if decision.missing:
        raise ProviderCapabilityError(
            provider=provider_name,
            missing_capabilities=tuple(
                sorted(feature.value for feature in decision.missing)
            ),
        )
    return decision
