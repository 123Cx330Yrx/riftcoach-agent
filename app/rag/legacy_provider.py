"""Compatibility adapter from the v0.1 retriever to the RAG v1 contract."""

from __future__ import annotations

from .models import (
    KnowledgeHit,
    KnowledgeMetadata,
    KnowledgeQuery,
    KnowledgeSearchResult,
)


class LegacyLocalKnowledgeProvider:
    """Keep the existing retriever usable while RAG v1 is built incrementally."""

    provider_name = "legacy-local-tfidf"

    def __init__(self, retriever) -> None:
        self.retriever = retriever

    def search(self, query: KnowledgeQuery) -> KnowledgeSearchResult:
        chunks = self.retriever.search(query.text, query.top_k)
        hits = tuple(
            KnowledgeHit(
                chunk_id=f"{chunk.source}#{chunk.title}",
                parent_id=None,
                content=chunk.content,
                score=chunk.score,
                rank=rank,
                metadata=KnowledgeMetadata(
                    source_id=chunk.source,
                    title=chunk.title,
                ),
            )
            for rank, chunk in enumerate(chunks, start=1)
        )
        return KnowledgeSearchResult(
            query=query,
            hits=hits,
            provider=self.provider_name,
        )

