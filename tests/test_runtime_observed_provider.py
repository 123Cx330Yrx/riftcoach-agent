from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.providers.capabilities import ProviderCapabilities
from app.providers.errors import (
    ProviderAuthenticationError,
    ProviderCapabilityError,
    ProviderResponseError,
)
from app.providers.models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    MessageRole,
    TokenUsage,
    ToolChoiceMode,
    ToolSpec,
)
from app.runtime.observed_provider import ObservedLLMProvider
from app.runtime.observer import RuntimeObservationError
from app.runtime.signals import (
    ProviderCallCompletedSignal,
    ProviderCallFailedSignal,
    ProviderCallStartedSignal,
    RuntimeFinishReason,
    RuntimeProviderPhase,
)
from app.tools.adapters.llm import build_llm_tools
from app.tools.registry import ToolRegistry
from app.tools.runtime import ToolRuntime


def _request(**metadata) -> ChatRequest:
    return ChatRequest(
        messages=(ChatMessage(role=MessageRole.USER, content="private prompt"),),
        metadata=metadata,
    )


def _response(*, finish_reason: str | None = "stop") -> ChatResponse:
    return ChatResponse(
        content="private response",
        model="glm-5.2",
        provider="zhipu",
        usage=TokenUsage(input_tokens=11, output_tokens=7),
        finish_reason=finish_reason,
        request_id="private-request-id",
    )


class RecordingObserver:
    def __init__(self) -> None:
        self.signals = []

    def observe(self, signal) -> None:
        self.signals.append(signal)


class SelectiveFailingObserver(RecordingObserver):
    def __init__(self, signal_type: type) -> None:
        super().__init__()
        self.signal_type = signal_type

    def observe(self, signal) -> None:
        if isinstance(signal, self.signal_type):
            raise RuntimeError("private observer failure")
        super().observe(signal)


@dataclass
class ScriptedProvider:
    outcomes: list[ChatResponse | Exception]
    provider_name: str = "zhipu"
    model_name: str = "glm-5.2"
    capabilities: ProviderCapabilities = ProviderCapabilities(text_chat=True)

    def __post_init__(self) -> None:
        self.requests: list[ChatRequest] = []

    def chat(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def test_observed_provider_emits_continuous_ordinals_and_safe_phase_metadata():
    delegate = ScriptedProvider(
        outcomes=[
            _response(finish_reason="tool_calls"),
            _response(finish_reason="vendor_private_reason"),
            _response(finish_reason=None),
        ]
    )
    observer = RecordingObserver()
    provider = ObservedLLMProvider(delegate=delegate, observer=observer)

    provider.chat(_request(agent_loop_iteration=2))
    provider.chat(_request(harness_step="evaluate_repair"))
    provider.chat(_request(harness_step="revise"))

    started = [
        signal
        for signal in observer.signals
        if isinstance(signal, ProviderCallStartedSignal)
    ]
    completed = [
        signal
        for signal in observer.signals
        if isinstance(signal, ProviderCallCompletedSignal)
    ]
    assert [signal.ordinal for signal in started] == [1, 2, 3]
    assert [signal.ordinal for signal in completed] == [1, 2, 3]
    assert [(signal.phase, signal.iteration) for signal in started] == [
        (RuntimeProviderPhase.AGENT, 2),
        (RuntimeProviderPhase.EVALUATION_REPAIR, None),
        (RuntimeProviderPhase.REVISION, None),
    ]
    assert [signal.finish_reason for signal in completed] == [
        RuntimeFinishReason.TOOL_CALLS,
        RuntimeFinishReason.OTHER,
        None,
    ]
    assert provider.provider_name == delegate.provider_name
    assert provider.model_name == delegate.model_name
    assert provider.capabilities == delegate.capabilities


def test_observed_provider_emits_stable_failure_and_allowlisted_safe_detail():
    delegate = ScriptedProvider(
        outcomes=[
            ProviderAuthenticationError(
                provider="zhipu",
                code="authentication_failed",
            )
        ]
    )
    observer = RecordingObserver()
    provider = ObservedLLMProvider(delegate=delegate, observer=observer)

    with pytest.raises(ProviderAuthenticationError):
        provider.chat(_request(harness_step="evaluate"))

    assert len(observer.signals) == 2
    failed = observer.signals[-1]
    assert isinstance(failed, ProviderCallFailedSignal)
    assert failed.failure_code == "provider_failed"
    assert failed.provider_error_code == "authentication_failed"
    assert failed.ordinal == 1


def test_observed_provider_drops_unallowlisted_error_detail_and_raw_text():
    delegate = ScriptedProvider(
        outcomes=[
            ProviderResponseError(
                provider="zhipu",
                code="private_but_safe_looking_detail",
            )
        ]
    )
    observer = RecordingObserver()
    provider = ObservedLLMProvider(delegate=delegate, observer=observer)

    with pytest.raises(ProviderResponseError):
        provider.chat(_request(agent_loop_iteration=1))

    failed = observer.signals[-1]
    assert isinstance(failed, ProviderCallFailedSignal)
    assert failed.failure_code == "provider_failed"
    assert failed.provider_error_code is None
    assert "private_but_safe_looking_detail" not in failed.model_dump_json()


def test_unknown_delegate_exception_closes_provider_with_only_high_level_code():
    delegate = ScriptedProvider(outcomes=[RuntimeError("private sdk exception")])
    observer = RecordingObserver()
    provider = ObservedLLMProvider(delegate=delegate, observer=observer)

    with pytest.raises(RuntimeError, match="private sdk exception"):
        provider.chat(_request(agent_loop_iteration=1))

    failed = observer.signals[-1]
    assert isinstance(failed, ProviderCallFailedSignal)
    assert failed.failure_code == "provider_failed"
    assert failed.provider_error_code is None
    assert "private sdk exception" not in failed.model_dump_json()


def test_observed_provider_capability_failure_emits_no_attempted_call():
    delegate = ScriptedProvider(
        outcomes=[_response()],
        capabilities=ProviderCapabilities(text_chat=True),
    )
    observer = RecordingObserver()
    provider = ObservedLLMProvider(delegate=delegate, observer=observer)
    request = ChatRequest(
        messages=(ChatMessage(role=MessageRole.USER, content="use tool"),),
        tools=(
            ToolSpec(
                name="knowledge.search",
                description="Search knowledge.",
                input_schema={"type": "object", "additionalProperties": False},
            ),
        ),
        tool_choice=ToolChoiceMode.AUTO,
        metadata={"agent_loop_iteration": 1},
    )

    with pytest.raises(ProviderCapabilityError):
        provider.chat(request)

    assert delegate.requests == []
    assert observer.signals == []


@pytest.mark.parametrize(
    "metadata",
    [
        {},
        {"agent_loop_iteration": True},
        {"agent_loop_iteration": 0},
        {"agent_loop_iteration": 1, "harness_step": "evaluate"},
        {"harness_step": "generate"},
    ],
)
def test_invalid_or_unknown_provider_phase_fails_before_delegate(metadata):
    delegate = ScriptedProvider(outcomes=[_response()])
    observer = RecordingObserver()
    provider = ObservedLLMProvider(delegate=delegate, observer=observer)

    with pytest.raises(RuntimeObservationError):
        provider.chat(_request(**metadata))

    assert delegate.requests == []
    assert observer.signals == []


def test_started_observation_failure_prevents_provider_side_effect():
    delegate = ScriptedProvider(outcomes=[_response()])
    observer = SelectiveFailingObserver(ProviderCallStartedSignal)
    provider = ObservedLLMProvider(delegate=delegate, observer=observer)

    with pytest.raises(RuntimeObservationError) as captured:
        provider.chat(_request(agent_loop_iteration=1))

    assert delegate.requests == []
    assert "private observer failure" not in str(captured.value)


def test_completion_observation_failure_stops_after_exactly_one_provider_call():
    delegate = ScriptedProvider(outcomes=[_response(), _response()])
    observer = SelectiveFailingObserver(ProviderCallCompletedSignal)
    provider = ObservedLLMProvider(delegate=delegate, observer=observer)

    with pytest.raises(RuntimeObservationError):
        provider.chat(_request(agent_loop_iteration=1))

    assert len(delegate.requests) == 1
    assert [type(signal) for signal in observer.signals] == [
        ProviderCallStartedSignal
    ]


@pytest.mark.parametrize(
    ("failed_signal", "expected_provider_calls"),
    [
        (ProviderCallStartedSignal, 0),
        (ProviderCallCompletedSignal, 1),
    ],
)
def test_tool_runtime_never_retries_or_falls_back_observation_failure(
    failed_signal,
    expected_provider_calls,
):
    delegate = ScriptedProvider(outcomes=[_response(), _response(), _response()])
    observer = SelectiveFailingObserver(failed_signal)
    provider = ObservedLLMProvider(delegate=delegate, observer=observer)
    registry = ToolRegistry()
    registry.register(build_llm_tools(provider)[0])
    runtime = ToolRuntime(registry, sleep=lambda _: None)

    with pytest.raises(RuntimeObservationError):
        runtime.execute(
            "llm.chat",
            {
                "messages": [
                    {"role": "user", "content": "private harness prompt"}
                ]
            },
            metadata={"harness_step": "evaluate"},
        )

    assert len(delegate.requests) == expected_provider_calls


def test_provider_signals_never_include_request_or_response_bodies():
    delegate = ScriptedProvider(outcomes=[_response()])
    observer = RecordingObserver()
    provider = ObservedLLMProvider(delegate=delegate, observer=observer)

    provider.chat(_request(agent_loop_iteration=1))

    serialized = "\n".join(signal.model_dump_json() for signal in observer.signals)
    for forbidden in (
        "private prompt",
        "private response",
        "private-request-id",
        "messages",
        "request_id",
        "content",
        "reasoning",
        "arguments",
    ):
        assert forbidden not in serialized
