"""No wall-clock sleeps: verify the allocation at the real Provider boundary."""
import pytest

from app.providers.errors import ProviderResponseError
from app.providers.models import ChatMessage, ChatRequest, ChatResponse, TokenUsage, MessageRole
from app.runtime.coach_budget import CoachBudgetedProvider
from app.runtime.coach_contract import SOURCE_COACH_CONTRACT, LATENCY_COACH_CONTRACT
from tests.test_coach_application_composition import dependencies


class Clock:
    value = 0.0
    def __call__(self):
        return self.value


class DelayedProvider:
    def __init__(self, clock, latency):
        self.base = dependencies()["provider"]
        self.clock, self.latency, self.requests = clock, latency, []
    def __getattr__(self, name):
        return getattr(self.base, name)
    def chat(self, request):
        self.requests.append(request)
        self.clock.value += min(self.latency, request.timeout_s)
        if self.latency > request.timeout_s:
            raise ProviderResponseError(provider=self.provider_name, code="timeout")
        return ChatResponse(content="offline", provider=self.provider_name, model=self.model_name,
                            finish_reason="stop", usage=TokenUsage(input_tokens=1, output_tokens=1))


def request(timeout=120):
    return ChatRequest(messages=(ChatMessage(role=MessageRole.USER, content="offline"),), timeout_s=timeout)


def test_75_second_response_is_rejected_by_old_allocation_and_fits_new_one():
    for contract, expected, passed in [(SOURCE_COACH_CONTRACT, 60, False), (LATENCY_COACH_CONTRACT, 90, True)]:
        clock = Clock()
        provider = DelayedProvider(clock, 75)
        controlled = CoachBudgetedProvider(provider, clock=clock, coach_contract=contract)
        if passed:
            assert controlled.chat(request()).content == "offline"
        else:
            with pytest.raises(ProviderResponseError):
                controlled.chat(request())
        assert provider.requests[0].timeout_s == expected
        assert controlled.calls == 1


@pytest.mark.parametrize("elapsed,caller_limit,expected", [(0, 12, 12), (475, 120, 5)])
def test_smaller_agent_or_execution_remainder_still_caps_the_call(elapsed, caller_limit, expected):
    clock = Clock()
    provider = DelayedProvider(clock, 20)
    controlled = CoachBudgetedProvider(provider, clock=clock, coach_contract=LATENCY_COACH_CONTRACT)
    clock.value = elapsed
    with pytest.raises(ProviderResponseError):
        controlled.chat(request(caller_limit))
    assert provider.requests[0].timeout_s == expected
    with pytest.raises(ProviderResponseError):
        controlled.chat(request())
    assert len(provider.requests) == 1


def test_time_reallocation_does_not_expand_overall_resource_or_quality_limits():
    old, new = SOURCE_COACH_CONTRACT.descriptor(), LATENCY_COACH_CONTRACT.descriptor()
    for key in ("max_calls", "max_input_tokens", "max_output_tokens", "total_tokens", "agent_timeout_s",
                "execution_timeout_s", "max_tool_calls", "max_revisions", "minimum_score", "max_context_tokens"):
        assert old[key] == new[key]
    assert new["request_timeout_s"] == 90
    assert SOURCE_COACH_CONTRACT.snapshot().sha256 == "f11f2755d19b2c670f86b54dce50ef60e1786fa29f0dacecb2c692572861d60f"
