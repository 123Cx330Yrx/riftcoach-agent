from datetime import date

import pytest

from app.rag.evaluation import (
    RetrievalCase,
    evaluate_retrieval,
    load_retrieval_dataset,
)
from app.rag.legacy_provider import LegacyLocalKnowledgeProvider
from app.rag.models import (
    KnowledgeHit,
    KnowledgeMetadata,
    KnowledgeQuery,
    KnowledgeSearchResult,
)
from app.rag.provider import KnowledgeProvider
from app.rag.retriever import KnowledgeChunk


class FixedProvider:
    provider_name = "fixed"

    def __init__(self, source_ids):
        self.source_ids = source_ids

    def search(self, query):
        return KnowledgeSearchResult(
            query=query,
            provider=self.provider_name,
            hits=tuple(
                KnowledgeHit(
                    chunk_id=f"{source_id}#chunk",
                    parent_id=None,
                    content="evidence",
                    score=1 / rank,
                    rank=rank,
                    metadata=KnowledgeMetadata(
                        source_id=source_id,
                        title="section",
                        knowledge_type="review_rule",
                        version="16.13",
                        updated_at=date(2026, 7, 23),
                    ),
                )
                for rank, source_id in enumerate(self.source_ids, start=1)
            ),
        )


class AnnotatedProvider:
    provider_name = "annotated"

    def search(self, query):
        if query.text == "库外问题":
            return KnowledgeSearchResult(
                query=query,
                provider=self.provider_name,
                hits=(),
                abstained=True,
            )
        return KnowledgeSearchResult(
            query=query,
            provider=self.provider_name,
            hits=(
                KnowledgeHit(
                    chunk_id="boundaries#chunk",
                    parent_id="boundaries#parent",
                    content="Data Dragon 提供静态名称，不提供当前版本英雄胜率。",
                    matched_content="Data Dragon 不提供当前版本英雄胜率",
                    score=1.0,
                    rank=1,
                    metadata=KnowledgeMetadata(
                        source_id="boundaries.md",
                        title="边界",
                    ),
                ),
            ),
        )


class LegacyRetriever:
    def search(self, query, top_k):
        return [
            KnowledgeChunk(
                source="rules.md",
                title="边界",
                content="相关性不等于因果。",
                score=2.0,
            )
        ][:top_k]


def test_legacy_retriever_adapts_to_knowledge_provider_contract():
    provider = LegacyLocalKnowledgeProvider(LegacyRetriever())

    assert isinstance(provider, KnowledgeProvider)
    result = provider.search(KnowledgeQuery(text="因果边界", top_k=1))

    assert result.provider == "legacy-local-tfidf"
    assert result.hits[0].chunk_id == "rules.md#边界"
    assert result.hits[0].metadata.source_id == "rules.md"
    assert result.hits[0].metadata.knowledge_type == "unknown"


def test_knowledge_query_rejects_unbounded_top_k():
    with pytest.raises(ValueError, match="between 1 and 20"):
        KnowledgeQuery(text="vision", top_k=0)


def test_knowledge_metadata_attributes_are_immutable():
    metadata = KnowledgeMetadata(
        source_id="rules.md",
        title="rules",
        attributes={"owner": "riftcoach"},
    )
    with pytest.raises(TypeError):
        metadata.attributes["owner"] = "mutated"


def test_retrieval_metrics_measure_rank_and_no_answer_false_positive():
    provider = FixedProvider(("irrelevant.md", "relevant.md"))
    evaluation = evaluate_retrieval(
        provider,
        (
            RetrievalCase(
                case_id="answerable",
                query="query",
                relevant_source_ids=("relevant.md",),
                top_k=2,
            ),
            RetrievalCase(
                case_id="no-answer",
                query="unknown",
                relevant_source_ids=(),
                top_k=2,
            ),
        ),
    )

    assert evaluation.recall_at_k == 1.0
    assert evaluation.mrr == 0.5
    assert evaluation.ndcg_at_k == 0.63093
    assert evaluation.no_answer_false_positive_rate == 1.0


def test_search_result_rejects_non_contiguous_ranks():
    query = KnowledgeQuery(text="query")
    hit = KnowledgeHit(
        chunk_id="chunk",
        parent_id=None,
        content="content",
        score=1.0,
        rank=2,
        metadata=KnowledgeMetadata(source_id="source", title="title"),
    )
    with pytest.raises(ValueError, match="contiguous"):
        KnowledgeSearchResult(query=query, hits=(hit,), provider="test")


def test_ndcg_does_not_reward_duplicate_chunks_from_the_same_source():
    provider = FixedProvider(("relevant.md", "relevant.md", "irrelevant.md"))
    evaluation = evaluate_retrieval(
        provider,
        (
            RetrievalCase(
                case_id="duplicate-source",
                query="query",
                relevant_source_ids=("relevant.md",),
                top_k=3,
            ),
        ),
    )

    assert evaluation.ndcg_at_k == 1.0


def test_versioned_holdout_annotations_measure_abstention_and_citation_support(
    tmp_path,
):
    dataset_path = tmp_path / "holdout.json"
    dataset_path.write_text(
        """
        {
          "dataset_version": "test-holdout-1",
          "role": "held_out",
          "calibration_excluded": true,
          "cases": [
            {
              "case_id": "supported",
              "query": "supported",
              "relevant_source_ids": ["boundaries.md"],
              "citation_terms": ["Data Dragon", "英雄胜率"],
              "split": "held_out",
              "category": "citation_support"
            },
            {
              "case_id": "unknown",
              "query": "库外问题",
              "relevant_source_ids": [],
              "expected_abstained": true,
              "split": "held_out",
              "category": "no_answer"
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    dataset = load_retrieval_dataset(dataset_path)
    evaluation = evaluate_retrieval(AnnotatedProvider(), dataset.cases)

    assert dataset.dataset_version == "test-holdout-1"
    assert dataset.role == "held_out"
    assert dataset.calibration_excluded is True
    assert evaluation.abstention_accuracy == 1.0
    assert evaluation.citation_support_rate == 1.0
