from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from app.evaluation.glm53_bounded_revision_budget import (
    BoundedRevisionBudgetError,
    BoundedRevisionBudgetState,
    BoundedRevisionBudgetedProvider,
    V3_CASE_MAX_CALLS,
    V3_CASE_MAX_TOKENS,
    V3_DOMAIN_MAX_CALLS,
    V3_DOMAIN_MAX_TOKENS,
)
from app.evaluation.glm53_flash_candidate_profile import MODEL, PROVIDER_ID
from app.evaluation.glm53_low_profile_budget import (
    CANDIDATE_CASE_MAX_CALLS,
    CANDIDATE_CASE_MAX_TOKENS,
    CANDIDATE_DOMAIN_MAX_CALLS,
    CANDIDATE_DOMAIN_MAX_TOKENS,
)
from app.providers.capabilities import ProviderCapabilities
from app.providers.models import ChatMessage, ChatRequest, ChatResponse, MessageRole, TokenUsage


@dataclass
class RecordingProvider:
    input_tokens: int = 10
    output_tokens: int = 5
    provider_name: str = PROVIDER_ID
    model_name: str = MODEL
    capabilities: ProviderCapabilities = ProviderCapabilities(
        text_chat=True,
        tool_calling=True,
        structured_output=True,
    )
    requests: list[ChatRequest] = field(default_factory=list)

    def chat(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        return ChatResponse(
            content="bounded response",
            provider=self.provider_name,
            model=self.model_name,
            finish_reason="stop",
            usage=TokenUsage(
                input_tokens=self.input_tokens,
                output_tokens=self.output_tokens,
            ),
        )


def request() -> ChatRequest:
    return ChatRequest(
        messages=(ChatMessage(MessageRole.USER, "offline budget probe"),),
        max_tokens=4096,
    )


def wrapped(provider=None, *, state=None, case_id="case_a"):
    ledger = state or BoundedRevisionBudgetState()
    if case_id not in ledger.cases:
        ledger.register_case(case_id)
    base = provider or RecordingProvider()
    return (
        BoundedRevisionBudgetedProvider(
            provider=base,
            state=ledger,
            case_id=case_id,
            clock=lambda: 0.0,
        ),
        base,
        ledger,
    )


def test_v3_budget_is_new_and_v2_constants_remain_unchanged():
    assert (V3_CASE_MAX_CALLS, V3_DOMAIN_MAX_CALLS) == (9, 27)
    assert (V3_CASE_MAX_TOKENS, V3_DOMAIN_MAX_TOKENS) == (203_000, 608_000)
    assert (CANDIDATE_CASE_MAX_CALLS, CANDIDATE_DOMAIN_MAX_CALLS) == (4, 12)
    assert (CANDIDATE_CASE_MAX_TOKENS, CANDIDATE_DOMAIN_MAX_TOKENS) == (
        24_000,
        72_000,
    )


def test_ninth_case_call_is_allowed_and_tenth_stops_before_io():
    provider, base, state = wrapped()
    for _ in range(9):
        provider.chat(request())

    with pytest.raises(BoundedRevisionBudgetError) as exc_info:
        provider.chat(request())

    assert exc_info.value.code == "external_call_budget_exhausted"
    assert len(base.requests) == 9
    assert state.calls_used == 9
    assert state.cases["case_a"].calls_used == 9


def test_three_cases_share_exact_twenty_seven_call_wall():
    state = BoundedRevisionBudgetState()
    base = RecordingProvider()
    for case_id in ("case_a", "case_b", "case_c"):
        provider, _, _ = wrapped(base, state=state, case_id=case_id)
        for _ in range(9):
            provider.chat(request())

    assert len(base.requests) == 27
    assert state.calls_used == 27
    assert all(row.calls_used == 9 for row in state.cases.values())


def test_request_policy_and_call_are_reserved_before_provider_io():
    provider, base, state = wrapped()
    response = provider.chat(request())

    assert response.content == "bounded response"
    assert state.calls_used == 1
    prepared = base.requests[0]
    assert prepared.max_tokens == 4096
    assert prepared.temperature == 1.0
    assert prepared.top_p == 0.95
    assert prepared.metadata["evaluation_scope"] == "candidate-only"
    assert prepared.metadata["candidate_budget_contract"] == (
        "hardened-v3-bounded-revision"
    )


def test_usage_outside_request_envelope_fails_closed_without_retry():
    provider, base, state = wrapped(RecordingProvider(input_tokens=10_000))

    with pytest.raises(BoundedRevisionBudgetError) as exc_info:
        provider.chat(request())

    assert exc_info.value.code == "token_envelope_exceeded"
    assert len(base.requests) == 1
    assert state.stop_code == "token_envelope_exceeded"


def test_exhausted_token_wall_stops_before_provider_io():
    state = BoundedRevisionBudgetState()
    provider, base, _ = wrapped(state=state)
    state.input_tokens = V3_CASE_MAX_TOKENS - 1
    state.cases["case_a"].input_tokens = V3_CASE_MAX_TOKENS - 1

    with pytest.raises(BoundedRevisionBudgetError) as exc_info:
        provider.chat(request())

    assert exc_info.value.code == "token_budget_exhausted"
    assert base.requests == []
    assert state.calls_used == 0
