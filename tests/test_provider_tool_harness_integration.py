from __future__ import annotations

import inspect
from dataclasses import dataclass

from app.harness.adapters import (
    ChatCoachGenerator,
    ChatCoachReviser,
    ChatEvaluationAdapter,
    LocalRagAdapter,
)
from app.harness.steps import (
    EvaluationRequest,
    EvaluationResult,
    EvaluationVerdict,
    GenerationRequest,
    KnowledgeEvidence,
    RetrievalRequest,
    RevisionRequest,
)
from app.providers.models import ChatResponse, TokenUsage
from app.rag.retriever import KnowledgeChunk
from app.tools.adapters import build_knowledge_tools, build_llm_tools
from app.tools.registry import ToolRegistry
from app.tools.runtime import ToolRuntime


class FakeRetriever:
    def search(self, query, top_k):
        return [
            KnowledgeChunk(
                source="review_rules.md",
                title="统计边界",
                content="相关性不能直接写成因果。",
                score=2.5,
            )
        ]


@dataclass
class QueueProvider:
    responses: list[str]
    provider_name: str = "fake-provider"

    def __post_init__(self):
        self.requests = []

    def chat(self, request):
        self.requests.append(request)
        return ChatResponse(
            content=self.responses.pop(0),
            model="fake-model",
            provider=self.provider_name,
            usage=TokenUsage(input_tokens=5, output_tokens=7),
        )


def build_runtime(provider):
    registry = ToolRegistry()
    for definition in (
        *build_knowledge_tools(FakeRetriever()),
        *build_llm_tools(provider),
    ):
        registry.register(definition)
    return ToolRuntime(
        registry,
        call_id_factory=lambda: "harness-call",
    )


def test_harness_adapters_use_provider_and_tool_contracts_not_sdk_shapes():
    provider = QueueProvider(
        responses=[
            "# RiftCoach 教练式复盘报告\n\n草稿",
            '{"score": 90}',
            "# RiftCoach 教练式复盘报告\n\n修订稿",
        ]
    )
    runtime = build_runtime(provider)

    retriever = LocalRagAdapter(
        runtime=runtime,
        query_builder=lambda summary: "统计边界",
        top_k=3,
    )
    evidence = retriever.retrieve(
        RetrievalRequest(
            player_summary={"recent_summary": {}},
            deterministic_report="facts",
        )
    )
    assert evidence.source_ids == ("review_rules.md",)
    assert "相关性不能直接写成因果" in evidence.context

    generator = ChatCoachGenerator(
        runtime=runtime,
        system_prompt="generator-system",
        summary_compactor=lambda summary: summary,
        prompt_builder=lambda summary, report, knowledge: "generate",
    )
    draft = generator.generate(
        GenerationRequest(
            player_summary={},
            deterministic_report="facts",
            knowledge=evidence,
        )
    )
    assert "草稿" in draft.report

    evaluator = ChatEvaluationAdapter(
        runtime=runtime,
        system_prompt="evaluator-system",
        fact_pack_builder=lambda summary: {"facts": True},
        prompt_builder=lambda facts, report: "evaluate",
        response_parser=lambda content: {
            "score": 90,
            "verdict": "pass",
            "issues": [],
            "passed_checks": ["facts"],
            "summary": content,
        },
    )
    evaluation = evaluator.evaluate(
        EvaluationRequest(
            player_summary={},
            deterministic_report="facts",
            knowledge=evidence,
            report=draft.report,
        )
    )
    assert evaluation.verdict is EvaluationVerdict.PASS

    reviser = ChatCoachReviser(
        runtime=runtime,
        system_prompt="reviser-system",
        prompt_builder=lambda report, evaluation: "revise",
        validator=lambda candidate, original: None,
    )
    revised = reviser.revise(
        RevisionRequest(
            player_summary={},
            deterministic_report="facts",
            knowledge=evidence,
            report=draft.report,
            evaluation=EvaluationResult(
                score=70,
                verdict=EvaluationVerdict.NEEDS_REVISION,
                issues=({"category": "causality"},),
            ),
        )
    )
    assert "修订稿" in revised.report

    assert len(provider.requests) == 3
    assert provider.requests[0].messages[0].content == "generator-system"
    adapter_source = inspect.getsource(
        __import__(
            "app.harness.adapters",
            fromlist=["adapters"],
        )
    )
    assert ".choices" not in adapter_source
    assert "chat.completions" not in adapter_source

