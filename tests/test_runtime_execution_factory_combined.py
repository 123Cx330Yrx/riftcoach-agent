from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from app.providers.capabilities import ProviderCapabilities
from app.providers.errors import ProviderResponseError
from app.providers.models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    MessageRole,
    TokenUsage,
)
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.runtime.coach_budget import CoachBudgetedProvider
from app.runtime.coach_contract import CONTEXT_COACH_CONTRACT, COACH_CONTRACT
from app.runtime.observed_provider import ObservedLLMProvider
from app.runtime.runtime import RuntimeCompositionError, RuntimeExecutionFactory


class _NoopObserver:
    def observe(self, signal) -> None:
        return None


@dataclass
class _Exchange:
    response: ChatResponse


@dataclass
class _Provider:
    provider_name: str = "fake-runtime-provider"
    model_name: str = "fake-runtime-model"
    capabilities: ProviderCapabilities = ProviderCapabilities(text_chat=True)
    transport_calls: int = 0
    last_exchange: _Exchange | None = None

    def chat(self, request):
        self.transport_calls += 1
        response = ChatResponse(
            content="ok",
            model=self.model_name,
            provider=self.provider_name,
            usage=TokenUsage(input_tokens=1, output_tokens=1),
        )
        self.last_exchange = _Exchange(response=response)
        return response


class _Workflow:
    def __init__(self, runtime, provider) -> None:
        self.runtime = runtime
        self.provider = provider

    def evaluate(self, request):
        return None

    def revise(self, request):
        return None


class _Evaluator:
    def evaluate(self, request):
        return None


class _Reviser:
    def revise(self, request):
        return None


def _factory(**kwargs):
    return RuntimeExecutionFactory(
        knowledge_provider=LocalHybridKnowledgeProvider.from_directory(
            Path("data/rag_docs")
        ),
        **kwargs,
    )


def test_combined_workflow_is_one_fresh_object_per_build_and_shares_provider():
    seen = []

    def make_workflow(runtime, provider):
        workflow = _Workflow(runtime, provider)
        seen.append(workflow)
        return workflow

    factory = _factory(review_workflow_factory=make_workflow)
    first = factory.build(
        provider=ObservedLLMProvider(delegate=_Provider(), observer=_NoopObserver()),
        observer=_NoopObserver(),
    )
    second = factory.build(
        provider=ObservedLLMProvider(delegate=_Provider(), observer=_NoopObserver()),
        observer=_NoopObserver(),
    )

    assert first.evaluator is first.reviser is seen[0]
    assert second.evaluator is second.reviser is seen[1]
    assert seen[0] is not seen[1]
    assert seen[0].runtime is not seen[1].runtime
    assert seen[0].provider is first.draft_preparer._agent_loop.provider
    assert seen[1].provider is second.draft_preparer._agent_loop.provider


def test_combined_workflow_receives_the_single_existing_budget_gate():
    seen = []
    factory = _factory(
        review_workflow_factory=lambda runtime, provider: seen.append(provider)
        or _Workflow(runtime, provider),
        coach_contract=COACH_CONTRACT,
    )
    coach_provider = _Provider(
        provider_name="zhipu",
        model_name="glm-5.3-flash",
    )
    coach_provider.thinking_profile_id = "glm-5.3-flash-candidate-enabled-low-replay"
    coach_provider.sdk_max_retries = 0
    coach_provider.runtime_profile = None
    observed = ObservedLLMProvider(delegate=coach_provider, observer=_NoopObserver())
    bundle = factory.build(provider=observed, observer=_NoopObserver())

    assert isinstance(seen[0], CoachBudgetedProvider)
    assert seen[0] is bundle.draft_preparer._agent_loop.provider
    assert seen[0].provider is observed
    assert seen[0].last_exchange is None
    assert seen[0].calls == 0


def test_combined_workflow_and_generation_share_the_high_five_call_budget():
    seen = []
    factory = _factory(
        review_workflow_factory=lambda runtime, provider: seen.append(provider)
        or _Workflow(runtime, provider),
        coach_contract=CONTEXT_COACH_CONTRACT,
    )
    coach_provider = _Provider(
        provider_name="zhipu",
        model_name="glm-5.3-flash",
    )
    coach_provider.thinking_profile_id = "glm-5.3-flash-candidate-enabled-high-replay"
    coach_provider.sdk_max_retries = 0
    coach_provider.runtime_profile = None
    observed = ObservedLLMProvider(delegate=coach_provider, observer=_NoopObserver())
    bundle = factory.build(provider=observed, observer=_NoopObserver())
    budgeted = seen[0]

    def call(metadata):
        return budgeted.chat(
            ChatRequest(
                messages=(
                    ChatMessage(role=MessageRole.USER, content="bounded call"),
                ),
                max_tokens=1,
                metadata=metadata,
            )
        )

    generated = [call({"agent_loop_iteration": index}) for index in (1, 2)]
    reviewed = [call({"harness_step": "evaluate"}) for _ in range(3)]
    latest = reviewed[-1]

    assert generated and reviewed
    assert budgeted is bundle.draft_preparer._agent_loop.provider
    assert budgeted.calls == 5
    assert coach_provider.transport_calls == 5
    assert budgeted.last_exchange is observed.last_exchange
    assert budgeted.last_exchange.response is latest

    with pytest.raises(ProviderResponseError, match="external_call_budget_exhausted"):
        call({"harness_step": "revise"})

    assert budgeted.calls == 5
    assert coach_provider.transport_calls == 5
    assert budgeted.last_exchange.response is latest


def test_legacy_factory_pair_keeps_the_original_budget_provider_type():
    factory = _factory(
        evaluator_factory=lambda runtime: _Evaluator(),
        reviser_factory=lambda runtime: _Reviser(),
        coach_contract=COACH_CONTRACT,
    )
    coach_provider = _Provider(
        provider_name="zhipu",
        model_name="glm-5.3-flash",
    )
    coach_provider.thinking_profile_id = "glm-5.3-flash-candidate-enabled-low-replay"
    coach_provider.sdk_max_retries = 0
    coach_provider.runtime_profile = None
    observed = ObservedLLMProvider(delegate=coach_provider, observer=_NoopObserver())

    bundle = factory.build(provider=observed, observer=_NoopObserver())

    assert type(bundle.draft_preparer._agent_loop.provider) is CoachBudgetedProvider


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"evaluator_factory": lambda runtime: object()},
        {"reviser_factory": lambda runtime: object()},
        {
            "evaluator_factory": lambda runtime: object(),
            "review_workflow_factory": lambda runtime, provider: _Workflow(runtime, provider),
        },
        {
            "reviser_factory": lambda runtime: object(),
            "review_workflow_factory": lambda runtime, provider: _Workflow(runtime, provider),
        },
        {
            "evaluator_factory": lambda runtime: object(),
            "reviser_factory": lambda runtime: object(),
            "review_workflow_factory": lambda runtime, provider: _Workflow(runtime, provider),
        },
    ],
)
def test_factory_rejects_incomplete_or_mixed_review_wiring(kwargs):
    with pytest.raises(ValueError):
        _factory(**kwargs)


def test_combined_factory_rejects_non_callable_hook():
    with pytest.raises(TypeError, match="review_workflow_factory"):
        _factory(review_workflow_factory=object())


def test_combined_workflow_must_implement_both_operations():
    factory = _factory(review_workflow_factory=lambda runtime, provider: object())
    with pytest.raises(RuntimeCompositionError, match="invalid workflow"):
        factory.build(
            provider=ObservedLLMProvider(delegate=_Provider(), observer=_NoopObserver()),
            observer=_NoopObserver(),
        )
