"""Host timestamp attribution through the real cache and evidence boundaries."""
from datetime import date, datetime, timedelta, timezone
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

import pytest

from app.harness.knowledge import KnowledgeEvidenceBuildError, knowledge_evidence_from_search_payloads, knowledge_projection
from app.harness.runtime import ReviewHarness
from app.rag.models import KnowledgeHit, KnowledgeMetadata, KnowledgeSearchResult
from app.tools.adapters.knowledge import build_knowledge_tools
from app.tools.registry import ToolRegistry
from app.tools.runtime import ToolRuntime
from app.runtime.coach_contract import (
    NATIVE_COACH_CONTRACT, ROLE_COACH_CONTRACT, COARSE_ROLE_COACH_CONTRACT,
    CORRECTION_SCOPE_COACH_CONTRACT,
)
from app.runtime.observed_provider import ObservedLLMProvider


class Provider:
    provider_name = "test-knowledge"

    def __init__(self):
        self.calls = 0

    def search(self, query):
        self.calls += 1
        return KnowledgeSearchResult(query=query, provider=self.provider_name,
            hits=(KnowledgeHit(chunk_id="guide:1", parent_id=None, content="Check the replay.",
                score=1, rank=1, metadata=KnowledgeMetadata(source_id="guide.md", title="Guide",
                    updated_at=date(2026, 7, 23), version="evergreen")),),
            diagnostics={"retrieved_at": "2026-09-10T00:00:00Z"})


def runtime(*, clock, utc_now):
    provider = Provider()
    tool = build_knowledge_tools(provider, include_retrieval_time=True, utc_now=utc_now)[0]
    registry = ToolRegistry()
    registry.register(tool)
    return provider, ToolRuntime(registry, clock=clock)


def test_real_cache_preserves_origin_and_expiry_records_a_new_search():
    monotonic = [0.0]
    wall = [datetime(2026, 9, 23, 12, tzinfo=timezone(timedelta(hours=8)))]
    provider, tools = runtime(clock=lambda: monotonic[0], utc_now=lambda: wall[0])
    query = dict(query="review", top_k=1, filters={"as_of": "2026-09-10"})
    first = tools.execute("knowledge.search", query)
    wall[0] += timedelta(minutes=1)
    monotonic[0] = 60
    cached = tools.execute("knowledge.search", query)
    wall[0] += timedelta(minutes=5)
    monotonic[0] = 360
    renewed = tools.execute("knowledge.search", query)
    assert first.success and cached.success and renewed.success
    assert provider.calls == 2
    assert not first.cached and cached.cached and not renewed.cached
    assert first.data == cached.data
    assert first.data["retrieved_at"] == "2026-09-23T04:00:00Z"
    assert renewed.data["retrieved_at"] == "2026-09-23T04:06:00Z"
    evidence = knowledge_evidence_from_search_payloads(r.data for r in (first, cached, renewed))
    assert len(evidence.citations) == 1
    assert evidence.citations[0].updated_at == "2026-07-23"
    assert [r.retrieved_at for r in evidence.retrievals] == [
        "2026-09-23T04:00:00Z", "2026-09-23T04:00:00Z", "2026-09-23T04:06:00Z"]
    assert all(r.chunk_ids == ("guide:1",) for r in evidence.retrievals)
    projection = knowledge_projection(evidence)
    assert projection['citations'][0]['retrievals'] == [
        {'provider': 'test-knowledge', 'retrieved_at': timestamp}
        for timestamp in ('2026-09-23T04:00:00Z', '2026-09-23T04:00:00Z', '2026-09-23T04:06:00Z')
    ]
    assert "2026-09-10" not in json.dumps(projection)
    stored = json.loads(ReviewHarness._knowledge_bytes(evidence))
    stored.pop("diagnostics")
    assert stored == projection


@pytest.mark.parametrize("bad", ["2026-09-23", "2026-09-23T04:00:00", "2026-02-30T00:00:00Z", "", 42, True, {}, "2026-09-23T04:00:00+99:00"])
def test_invalid_retrieval_time_is_rejected_not_normalized_to_document_date(bad):
    from tests.test_knowledge_evidence_builder import payload
    with pytest.raises(KnowledgeEvidenceBuildError, match="retrieved_at"):
        knowledge_evidence_from_search_payloads([dict(payload([]), retrieved_at=bad)])


def test_mixed_old_and_new_searches_keep_unknown_membership_and_empty_search():
    from tests.test_knowledge_evidence_builder import chunk, payload
    first = payload([chunk("a", source_id="a.md", content="A")])
    second = dict(payload([chunk("b", source_id="b.md", content="B")]), retrieved_at="2026-09-23T04:00:00Z")
    empty = dict(payload([], abstained=True), retrieved_at="2026-09-23T04:00:01Z")
    evidence = knowledge_evidence_from_search_payloads([first, second, empty])
    assert [(r.retrieved_at, r.chunk_ids) for r in evidence.retrievals] == [
        (None, ("a",)), (second["retrieved_at"], ("b",)), (empty["retrieved_at"], ())]
    old = knowledge_evidence_from_search_payloads([first])
    assert old.retrievals == () and "retrievals" not in knowledge_projection(old)
    assert 'retrievals' not in knowledge_projection(old)['citations'][0]
    citations = knowledge_projection(evidence)['citations']
    assert citations[0]['retrievals'] == [{'provider': 'local-hybrid', 'retrieved_at': None}]
    assert citations[1]['retrievals'] == [{'provider': 'local-hybrid', 'retrieved_at': second['retrieved_at']}]
    explicit_unknown = knowledge_evidence_from_search_payloads([dict(first, retrieved_at=None)])
    assert explicit_unknown.retrievals[0].retrieved_at is None


def test_invalid_host_clock_fails_without_cached_success():
    provider, tools = runtime(clock=lambda: 0, utc_now=lambda: datetime(2026, 9, 23))
    for _ in range(2):
        result = tools.execute("knowledge.search", dict(query="review", top_k=1))
        assert not result.success and not result.cached
    assert provider.calls == 2


def test_initial_context_keeps_only_each_citations_retrieval_membership():
    from app.agent.context import _insert_knowledge_sections
    from tests.test_knowledge_evidence_builder import chunk, payload
    evidence = knowledge_evidence_from_search_payloads([
        dict(payload([chunk("a", source_id="a.md", content="A")]), retrieved_at="2026-09-23T04:00:00Z"),
        dict(payload([chunk("b", source_id="b.md", content="B")]), retrieved_at=None),
    ])
    sections = _insert_knowledge_sections((), evidence)
    rows = [json.loads(s.content) for s in sections]
    assert rows[0]["retrievals"] == [{"provider": "local-hybrid", "retrieved_at": "2026-09-23T04:00:00Z"}]
    assert rows[1]["retrievals"] == [{"provider": "local-hybrid", "retrieved_at": None}]
    assert [row['retrievals'] for row in rows] == [
        row['retrievals'] for row in knowledge_projection(evidence)['citations']]


def factory_knowledge_runtime(contract):
    from app.providers.zhipu_profiles import ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE
    from tests.test_runtime_execution_factory_combined import (
        _factory, _NoopObserver, _Provider, _Workflow,
    )
    delegate = _Provider()
    if contract is not None:
        descriptor = contract.descriptor()
        delegate.provider_name = "zhipu"
        delegate.model_name = contract.request_policy.model
        delegate.thinking_profile_id = descriptor.get("thinking_profile_id",
            ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE.profile_id)
        delegate.sdk_max_retries = 0
        delegate.runtime_profile = None
        delegate.source_projection = descriptor.get("source_projection")
    observer = _NoopObserver()
    bundle = _factory(coach_contract=contract, review_workflow_factory=_Workflow).build(
        provider=ObservedLLMProvider(delegate=delegate, observer=observer), observer=observer)
    return delegate, bundle.draft_preparer._agent_loop


@pytest.mark.parametrize("contract,profile", [
    pytest.param(NATIVE_COACH_CONTRACT, "flash_v2_native", id="native"),
    pytest.param(ROLE_COACH_CONTRACT, "flash_glm_review_v1", id="role"),
    pytest.param(COARSE_ROLE_COACH_CONTRACT, "flash_glm_coarse_v1", id="coarse"),
    pytest.param(CORRECTION_SCOPE_COACH_CONTRACT, "flash_glm_correction_scope_v1", id="correction-scope"),
])
def test_actual_factory_knowledge_contract_matches_manifest_and_projects_host_time(contract, profile):
    delegate, agent = factory_knowledge_runtime(contract)
    tool = agent.tool_registry.get("knowledge.search")
    manifest = json.loads((Path(__file__).resolve().parents[1] / "examples/runtime_profiles"
        / profile / "prompt_programs/recent-form-review/manifest.json").read_bytes())
    declared = next(row for row in manifest["component_fingerprints"]
        if row["component_id"] == "knowledge_tool_contract")
    assert tool.version == "2.1.0"
    assert declared["source"] == f"app.tools.adapters.knowledge:knowledge.search@{tool.version}"
    assert "retrieved_at" in tool.output_schema["required"]
    assert tool.output_schema["properties"]["retrieved_at"]["format"] == "date-time"
    # Compare the registered executable definition, not a separately built probe.
    actual_contract = dict(name=tool.name, version=tool.version, description=tool.description,
        input_schema=dict(tool.input_schema), output_schema=dict(tool.output_schema),
        idempotent=tool.idempotent, policy=dict(timeout_s=tool.policy.timeout_s,
            retry=asdict(tool.policy.retry), cache_ttl_s=tool.policy.cache.ttl_s,
            circuit_breaker=asdict(tool.policy.circuit_breaker)))
    actual_sha = hashlib.sha256(json.dumps(actual_contract, ensure_ascii=False,
        sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    assert actual_sha == declared["sha256"]

    before = datetime.now(timezone.utc)
    result = agent.tool_runtime.execute("knowledge.search", dict(
        query="早期死亡", top_k=2, filters={"as_of": "2026-09-10"}))
    after = datetime.now(timezone.utc)
    assert result.success and not result.cached and result.tool_version == "2.1.0"
    assert result.data["chunks"]
    timestamp = result.data["retrieved_at"]
    assert timestamp.endswith("Z")
    retrieved = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    assert before <= retrieved <= after and retrieved.utcoffset() == timedelta(0)
    evidence = knowledge_evidence_from_search_payloads([result.data])
    assert evidence.retrievals[0].retrieved_at == timestamp
    assert evidence.retrievals[0].chunk_ids == tuple(c["chunk_id"] for c in result.data["chunks"])
    projection = knowledge_projection(evidence)
    assert projection["retrievals"][0]["retrieved_at"] == timestamp
    assert all(c["retrievals"] == [{"provider": result.data["provider"], "retrieved_at": timestamp}]
        for c in projection["citations"])
    assert delegate.transport_calls == 0


def test_actual_legacy_factory_keeps_untimed_knowledge_contract():
    delegate, agent = factory_knowledge_runtime(None)
    tool = agent.tool_registry.get("knowledge.search")
    assert tool.version == "2.0.0"
    assert "retrieved_at" not in tool.output_schema["properties"]
    assert "retrieved_at" not in tool.output_schema["required"]
    result = agent.tool_runtime.execute("knowledge.search", dict(query="早期死亡", top_k=2))
    assert result.success and result.tool_version == "2.0.0" and result.data["chunks"]
    assert "retrieved_at" not in result.data
    evidence = knowledge_evidence_from_search_payloads([result.data])
    assert evidence.retrievals == ()
    projection = knowledge_projection(evidence)
    assert "retrievals" not in projection
    assert all("retrievals" not in c for c in projection["citations"])
    assert delegate.transport_calls == 0
