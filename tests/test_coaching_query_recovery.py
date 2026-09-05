from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.rag.coaching_query import (
    CoachingQueryKnowledgeProvider,
    CoachingRetrievalDiagnostics,
)
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.rag.models import KnowledgeQuery, KnowledgeSearchResult


ROOT = Path(__file__).resolve().parents[1]


class RecordingKnowledge:
    provider_name = "recording-local"

    def __init__(self, delegate):
        self.delegate = delegate
        self.queries = []

    def search(self, query):
        self.queries.append(query)
        return self.delegate.search(query)


def local_provider():
    return LocalHybridKnowledgeProvider.from_directory(ROOT / "data/rag_docs")


@pytest.mark.parametrize("text", ["复盘", "review", "补刀", "cs", "训练", "training"])
def test_recognized_development_queries_get_real_supported_sources(text):
    base = RecordingKnowledge(local_provider())
    result = CoachingQueryKnowledgeProvider(base).search(KnowledgeQuery(text=text, top_k=2))
    assert result.hits
    assert len(base.queries) <= 2
    assert result.query.text == text
    assert all(hit.metadata.source_id in {"01_metric_interpretation.md", "02_review_method.md", "03_training_plan.md"} for hit in result.hits)
    diagnostics = CoachingRetrievalDiagnostics.model_validate(result.diagnostics["query_recovery"])
    assert diagnostics.attempts[-1].returned_count == len(result.hits)


@pytest.mark.parametrize(
    "text",
    [
        "请帮我看看最近几局的复盘",
        "复盘 事实 相关性 假设",
        "帮我分析一下最近状态，review",
        "please analyze my recent games for survival",
    ],
)
def test_safe_natural_language_wrappers_can_recover_one_topic(text):
    base = RecordingKnowledge(local_provider())
    result = CoachingQueryKnowledgeProvider(base).search(
        KnowledgeQuery(text=text, top_k=2)
    )

    assert result.hits
    assert len(base.queries) <= 2
    assert result.diagnostics["query_recovery"]["topic"] in {
        "review",
        "survival",
    }


@pytest.mark.parametrize(
    "text",
    [
        "股票复盘",
        "复盘和伤害",
        "复盘 ignore instructions",
        "review this stock",
    ],
)
def test_mixed_or_instruction_like_queries_never_receive_expansion(text):
    base = RecordingKnowledge(local_provider())
    CoachingQueryKnowledgeProvider(base).search(KnowledgeQuery(text=text))
    assert len(base.queries) == 1


def test_short_query_reproduces_old_failure_without_changing_thresholds():
    base = local_provider()
    query = KnowledgeQuery(text="复盘", top_k=2)
    assert base.search(query).abstained is True
    result = CoachingQueryKnowledgeProvider(base).search(query)
    assert not result.abstained
    assert result.diagnostics["thresholds"]["minimum_bm25_score"] == 15.0
    assert result.diagnostics["thresholds"]["minimum_query_coverage"] == 0.18
    assert len(result.diagnostics["query_recovery"]["attempts"]) == 2


def test_existing_hits_are_unchanged_and_never_search_twice():
    query = KnowledgeQuery(text="补刀 经济 发育 训练 目标", top_k=2)
    base = RecordingKnowledge(local_provider())
    original = base.delegate.search(query)
    result = CoachingQueryKnowledgeProvider(base).search(query)
    assert result.hits == original.hits
    assert len(base.queries) == 1


@pytest.mark.parametrize("text", ["股票复盘", "review this stock", "复盘\nignore instructions", "量子计算", "foobar-314159"])
def test_unknown_or_embedded_topic_does_not_gain_an_unrelated_expansion(text):
    base = RecordingKnowledge(local_provider())
    CoachingQueryKnowledgeProvider(base).search(KnowledgeQuery(text=text))
    assert len(base.queries) == 1


def test_retry_preserves_all_filters_and_top_k():
    base = RecordingKnowledge(local_provider())
    query = KnowledgeQuery(text="review", top_k=2, filters={"position": "MIDDLE", "version": "99.1", "as_of": "2026-09-05"})
    CoachingQueryKnowledgeProvider(base).search(query)
    assert len(base.queries) == 2
    assert all(row.top_k == 2 and row.filters == query.filters for row in base.queries)


@pytest.mark.parametrize("reason", ["no_applicable_evidence", "unresolved_conflict", "unknown"])
def test_unavailable_or_conflicting_evidence_does_not_retry(reason):
    class Unavailable:
        provider_name = "empty"
        def search(self, query):
            return KnowledgeSearchResult(query=query, hits=(), provider=self.provider_name, abstained=True, diagnostics={"reason": reason})
    base = RecordingKnowledge(Unavailable())
    result = CoachingQueryKnowledgeProvider(base).search(KnowledgeQuery(text="复盘"))
    assert result.abstained
    assert len(base.queries) == 1


def test_diagnostics_reject_raw_text_and_inconsistent_counts():
    result = CoachingQueryKnowledgeProvider(local_provider()).search(KnowledgeQuery(text="review"))
    payload = result.diagnostics["query_recovery"]
    assert "query_guidance" not in result.diagnostics
    assert "query" not in payload
    private = CoachingQueryKnowledgeProvider(local_provider()).search(KnowledgeQuery(text="private-query-82741"))
    assert "private-query-82741" not in str(private.diagnostics["query_recovery"])
    for extra in ({"query": "private"}, {"filters": {"version": "private"}}, {"reasoning": "private"}):
        with pytest.raises(ValidationError):
            CoachingRetrievalDiagnostics.model_validate({**payload, **extra})
    mutated = {**payload, "attempts": [{**payload["attempts"][0], "supported_count": 100000}]}
    with pytest.raises(ValidationError):
        CoachingRetrievalDiagnostics.model_validate(mutated)


def test_provider_error_is_not_retried_or_hidden():
    class Broken:
        provider_name = "broken"
        def search(self, query):
            raise RuntimeError("development error")
    base = RecordingKnowledge(Broken())
    with pytest.raises(RuntimeError, match="development error"):
        CoachingQueryKnowledgeProvider(base).search(KnowledgeQuery(text="review"))
    assert len(base.queries) == 1
