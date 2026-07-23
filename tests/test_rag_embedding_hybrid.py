import math
from pathlib import Path

import pytest

from app.rag.documents import ChildChunk, KnowledgeCorpus, ParentChunk
from app.rag.embedding import DenseIndex, HashingEmbeddingProvider
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.rag.models import KnowledgeMetadata, KnowledgeQuery


def chunk_pair(name: str, content: str):
    metadata = KnowledgeMetadata(source_id=f"{name}.md", title=name)
    parent = ParentChunk(
        parent_id=f"parent-{name}",
        content=f"完整上下文：{content}",
        metadata=metadata,
    )
    child = ChildChunk(
        child_id=f"child-{name}",
        parent_id=parent.parent_id,
        content=content,
        metadata=metadata,
    )
    return parent, child


class FailingQueryEmbeddingProvider:
    provider_name = "failing"
    dimensions = 2

    def __init__(self):
        self.calls = 0

    def embed(self, texts):
        self.calls += 1
        if self.calls > 1:
            raise RuntimeError("remote embedding unavailable")
        return tuple((1.0, 0.0) for _ in texts)


def test_hashing_embedding_is_deterministic_and_normalized():
    provider = HashingEmbeddingProvider(dimensions=64)

    first, second = provider.embed(("视野分 信息准备", "视野分 信息准备"))

    assert first == second
    assert len(first) == 64
    assert math.sqrt(sum(value * value for value in first)) == pytest.approx(1.0)


def test_dense_index_returns_matching_text_first():
    vision_parent, vision = chunk_pair("vision", "视野分 真眼 信息准备")
    economy_parent, economy = chunk_pair("economy", "补刀 经济 发育")
    provider = HashingEmbeddingProvider(dimensions=128)
    index = DenseIndex((vision, economy), provider)

    results = index.search("视野分 信息准备", top_k=2)

    assert results[0].child.child_id == vision.child_id


def test_hybrid_provider_returns_parent_context_and_channel_trace():
    pairs = (
        chunk_pair("vision", "视野分 真眼 信息准备"),
        chunk_pair("economy", "补刀 经济 发育"),
    )
    corpus = KnowledgeCorpus(
        parents=tuple(pair[0] for pair in pairs),
        children=tuple(pair[1] for pair in pairs),
    )
    provider = LocalHybridKnowledgeProvider(corpus)

    result = provider.search(KnowledgeQuery(text="视野分 信息准备", top_k=1))

    assert result.provider == "local-hybrid-rrf"
    assert result.hits[0].metadata.source_id == "vision.md"
    assert result.hits[0].content.startswith("完整上下文")
    assert result.hits[0].matched_content == "视野分 真眼 信息准备"
    assert result.hits[0].metadata.attributes["bm25_rank"] == 1
    assert result.hits[0].metadata.attributes["dense_rank"] == 1
    assert result.hits[0].metadata.attributes["embedding_fallback"] is False


def test_hybrid_provider_degrades_to_bm25_when_query_embedding_fails():
    parent, child = chunk_pair("vision", "视野分 真眼 信息准备")
    provider = LocalHybridKnowledgeProvider(
        KnowledgeCorpus(parents=(parent,), children=(child,)),
        embedding_provider=FailingQueryEmbeddingProvider(),
        allow_embedding_fallback=True,
    )

    result = provider.search(KnowledgeQuery(text="视野分", top_k=1))

    assert result.hits[0].metadata.source_id == "vision.md"
    assert result.hits[0].metadata.attributes["embedding_fallback"] is True
    assert result.hits[0].metadata.attributes["dense_rank"] is None


def test_project_hybrid_provider_can_search_structured_knowledge():
    provider = LocalHybridKnowledgeProvider.from_directory(Path("data/rag_docs"))

    result = provider.search(
        KnowledgeQuery(text="Data Dragon 能提供英雄胜率吗", top_k=3)
    )

    assert result.hits[0].metadata.source_id == "04_data_boundaries.md"
    assert result.hits[0].metadata.knowledge_type == "data_boundary"
