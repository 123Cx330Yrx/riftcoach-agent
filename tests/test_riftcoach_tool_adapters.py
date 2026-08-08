from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.providers.models import ChatResponse, TokenUsage
from app.rag.retriever import KnowledgeChunk
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.tools.adapters import (
    build_data_dragon_tools,
    build_knowledge_tools,
    build_llm_tools,
    build_riot_tools,
    register_riftcoach_tools,
)
from app.tools.models import ToolContext
from app.tools.registry import ToolRegistry
from app.tools.runtime import ToolRuntime


class FakeRiotClient:
    def __init__(self):
        self.calls = []

    def get_account_by_riot_id(self, game_name, tag_line, *, timeout_s):
        self.calls.append(("account", game_name, tag_line, timeout_s))
        return {
            "puuid": "masked-test-puuid",
            "gameName": game_name,
            "tagLine": tag_line,
        }

    def get_recent_match_ids(self, puuid, count, queue, *, timeout_s):
        self.calls.append(("matches", puuid, count, queue, timeout_s))
        return ["KR_1", "KR_2"]

    def get_match_detail(self, match_id, *, timeout_s):
        self.calls.append(("detail", match_id, timeout_s))
        return {"metadata": {"matchId": match_id}, "info": {}}

    def get_match_timeline(self, match_id, *, timeout_s):
        self.calls.append(("timeline", match_id, timeout_s))
        return {"metadata": {"matchId": match_id}, "info": {"frames": []}}


class FakeDataDragon:
    version = "16.14.1"
    language = "zh_CN"

    def get_champion_official_name(self, entity_id, fallback=""):
        return "阿狸"

    def get_item_name(self, entity_id):
        return "卢登的伙伴"

    def get_summoner_spell_name(self, entity_id):
        return "闪现"

    def get_rune_name(self, entity_id):
        return "电刑"


class FakeRetriever:
    def __init__(self):
        self.calls = []

    def search(self, query, top_k):
        self.calls.append((query, top_k))
        return [
            KnowledgeChunk(
                source="metric_rules.md",
                title="经济指标",
                content="经济/分钟只能作为相关性线索。",
                score=3.25,
            )
        ]


@dataclass
class FakeProvider:
    provider_name: str = "fake-zhipu"

    def __post_init__(self):
        self.requests = []

    def chat(self, request):
        self.requests.append(request)
        return ChatResponse(
            content="基于输入事实生成的报告。",
            model="glm-test",
            provider=self.provider_name,
            finish_reason="stop",
            usage=TokenUsage(input_tokens=12, output_tokens=8),
            request_id="req-test",
        )


def context(deadline=130.0):
    return ToolContext(
        call_id="call-test",
        attempt=1,
        deadline_monotonic=deadline,
        clock=lambda: 100.0,
    )


def by_name(definitions):
    return {definition.name: definition for definition in definitions}


def test_riot_adapters_define_stable_contracts_and_pass_remaining_budget():
    client = FakeRiotClient()
    tools = by_name(build_riot_tools(client))

    assert set(tools) == {
        "riot.account_by_riot_id",
        "riot.recent_match_ids",
        "riot.match_detail",
        "riot.match_timeline",
    }

    account = tools["riot.account_by_riot_id"].handler(
        {"game_name": "MIDKING", "tag_line": "asd"},
        context(),
    )
    matches = tools["riot.recent_match_ids"].handler(
        {
            "puuid": "masked-test-puuid",
            "count": 2,
            "queue": 420,
        },
        context(),
    )
    detail = tools["riot.match_detail"].handler(
        {"match_id": "KR_1"},
        context(),
    )
    timeline = tools["riot.match_timeline"].handler(
        {"match_id": "KR_1"},
        context(),
    )

    assert account["account"]["gameName"] == "MIDKING"
    assert matches == {"match_ids": ["KR_1", "KR_2"]}
    assert detail["match"]["metadata"]["matchId"] == "KR_1"
    assert timeline["timeline"]["info"]["frames"] == []
    assert client.calls == [
        ("account", "MIDKING", "asd", 30.0),
        ("matches", "masked-test-puuid", 2, 420, 30.0),
        ("detail", "KR_1", 30.0),
        ("timeline", "KR_1", 30.0),
    ]
    assert tools["riot.recent_match_ids"].policy.cache.ttl_s <= 30
    assert tools["riot.match_detail"].policy.cache.ttl_s >= 300


def test_data_dragon_lookup_is_one_cached_static_tool():
    tool = build_data_dragon_tools(FakeDataDragon())[0]

    assert tool.name == "data_dragon.lookup_name"
    assert tool.policy.cache.ttl_s >= 3600
    assert tool.handler(
        {"entity_type": "champion", "entity_id": 103},
        context(),
    ) == {
        "entity_type": "champion",
        "entity_id": 103,
        "official_name": "阿狸",
        "version": "16.14.1",
        "language": "zh_CN",
    }


def test_knowledge_adapter_returns_structured_evidence_and_is_cached():
    retriever = FakeRetriever()
    tool = build_knowledge_tools(retriever)[0]

    result = tool.handler(
        {"query": "如何解释经济差异", "top_k": 3},
        context(),
    )

    assert tool.name == "knowledge.search"
    assert tool.policy.cache.ttl_s > 0
    assert retriever.calls == [("如何解释经济差异", 3)]
    assert result == {
        "provider": "legacy-local-tfidf",
        "abstained": False,
        "diagnostics": {},
        "chunks": [
            {
                "chunk_id": "metric_rules.md#经济指标",
                "parent_id": None,
                "source_id": "metric_rules.md",
                "title": "经济指标",
                "content": "经济/分钟只能作为相关性线索。",
                "matched_content": None,
                "score": 3.25,
                "rank": 1,
                "knowledge_type": "unknown",
                "version": None,
                "updated_at": None,
                "valid_from": None,
                "valid_until": None,
                "positions": [],
                "attributes": {},
            }
        ],
        "count": 1,
    }


def test_hybrid_knowledge_adapter_exposes_citations_and_abstention_diagnostics():
    provider = LocalHybridKnowledgeProvider.from_directory(Path("data/rag_docs"))
    tool = build_knowledge_tools(provider)[0]

    answered = tool.handler(
        {"query": "Data Dragon 能提供英雄胜率吗", "top_k": 3},
        context(),
    )
    abstained = tool.handler(
        {"query": "今天北京天气降雨概率", "top_k": 3},
        context(),
    )

    assert tool.version == "2.0.0"
    assert answered["abstained"] is False
    assert answered["chunks"][0]["source_id"] == "04_data_boundaries.md"
    assert answered["chunks"][0]["chunk_id"]
    assert answered["chunks"][0]["parent_id"]
    assert answered["chunks"][0]["matched_content"]
    assert answered["chunks"][0]["knowledge_type"] == "data_boundary"
    assert abstained["abstained"] is True
    assert abstained["chunks"] == []
    assert abstained["diagnostics"]["reason"] == "insufficient_evidence"


def test_llm_adapter_maps_messages_and_uses_context_budget():
    provider = FakeProvider()
    tool = build_llm_tools(provider)[0]

    result = tool.handler(
        {
            "messages": [
                {"role": "system", "content": "只使用输入事实。"},
                {"role": "user", "content": "生成报告。"},
            ],
            "temperature": 0.2,
            "max_tokens": 800,
        },
        context(deadline=112.5),
    )

    request = provider.requests[0]
    assert tool.name == "llm.chat"
    assert tool.policy.cache.ttl_s == 0
    assert request.messages[0].role.value == "system"
    assert request.temperature == 0.2
    assert request.max_tokens == 800
    assert request.timeout_s == 12.5
    assert result == {
        "content": "基于输入事实生成的报告。",
        "model": "glm-test",
        "provider": "fake-zhipu",
        "finish_reason": "stop",
        "usage": {
            "input_tokens": 12,
            "output_tokens": 8,
            "total_tokens": 20,
        },
        "request_id": "req-test",
    }


def test_llm_adapter_passes_structured_response_contract() -> None:
    provider = FakeProvider()
    tool = build_llm_tools(provider)[0]
    schema = {
        "type": "object",
        "properties": {"score": {"type": "integer"}},
        "required": ["score"],
        "additionalProperties": False,
    }

    tool.handler(
        {
            "messages": [{"role": "user", "content": "返回评测 JSON。"}],
            "response_contract": {
                "name": "coach_evaluation",
                "version": "1.0.0",
                "json_schema": schema,
                "strict": True,
            },
        },
        context(),
    )

    request = provider.requests[0]
    assert request.response_contract is not None
    assert request.response_contract.name == "coach_evaluation"
    assert request.response_contract.version == "1.0.0"
    assert request.response_contract.schema_dict() == schema


def test_all_adapters_register_and_execute_through_runtime():
    registry = ToolRegistry()
    provider = FakeProvider()
    register_riftcoach_tools(
        registry,
        riot_client=FakeRiotClient(),
        data_dragon=FakeDataDragon(),
        retriever=FakeRetriever(),
        llm_provider=provider,
    )
    runtime = ToolRuntime(
        registry,
        call_id_factory=lambda: "call-test",
    )

    names = [tool.name for tool in registry.list_tools()]
    assert names == [
        "data_dragon.lookup_name",
        "knowledge.search",
        "llm.chat",
        "riot.account_by_riot_id",
        "riot.match_detail",
        "riot.match_timeline",
        "riot.recent_match_ids",
    ]

    result = runtime.execute(
        "knowledge.search",
        {"query": "经济差异", "top_k": 1},
    )
    assert result.success is True
    assert result.data["count"] == 1
