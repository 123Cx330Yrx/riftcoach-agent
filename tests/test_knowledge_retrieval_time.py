"""Host timestamp attribution through the real cache and evidence boundaries."""
from datetime import date, datetime, timedelta, timezone
import json

import pytest

from app.harness.knowledge import KnowledgeEvidenceBuildError, knowledge_evidence_from_search_payloads, knowledge_projection
from app.harness.runtime import ReviewHarness
from app.rag.models import KnowledgeHit, KnowledgeMetadata, KnowledgeSearchResult
from app.tools.adapters.knowledge import build_knowledge_tools
from app.tools.registry import ToolRegistry
from app.tools.runtime import ToolRuntime


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
