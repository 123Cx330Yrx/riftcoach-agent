"""Local parent-child retrieval with BM25, dense search, and RRF fusion."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .bm25 import BM25Index
from .documents import KnowledgeCorpus, load_markdown_corpus
from .embedding import DenseIndex, EmbeddingProvider, HashingEmbeddingProvider
from .models import (
    KnowledgeHit,
    KnowledgeMetadata,
    KnowledgeQuery,
    KnowledgeSearchResult,
)


@dataclass
class _FusionRow:
    child: object
    rrf_score: float = 0.0
    bm25_rank: int | None = None
    bm25_score: float | None = None
    dense_rank: int | None = None
    dense_score: float | None = None


class LocalHybridKnowledgeProvider:
    provider_name = "local-hybrid-rrf"

    def __init__(
        self,
        corpus: KnowledgeCorpus,
        *,
        embedding_provider: EmbeddingProvider | None = None,
        rrf_k: int = 60,
        candidate_multiplier: int = 4,
        allow_embedding_fallback: bool = True,
    ) -> None:
        if rrf_k <= 0:
            raise ValueError("rrf_k must be positive.")
        if candidate_multiplier < 1:
            raise ValueError("candidate_multiplier must be at least 1.")
        self.corpus = corpus
        self.parents = corpus.parent_by_id()
        self.embedding_provider = embedding_provider or HashingEmbeddingProvider()
        self.rrf_k = rrf_k
        self.candidate_multiplier = candidate_multiplier
        self.allow_embedding_fallback = allow_embedding_fallback
        self.bm25 = BM25Index(corpus.children)
        self.dense = DenseIndex(corpus.children, self.embedding_provider)

    @classmethod
    def from_directory(
        cls,
        knowledge_dir: Path,
        **kwargs,
    ) -> "LocalHybridKnowledgeProvider":
        return cls(load_markdown_corpus(knowledge_dir), **kwargs)

    def search(self, query: KnowledgeQuery) -> KnowledgeSearchResult:
        candidate_count = min(
            len(self.corpus.children),
            query.top_k * self.candidate_multiplier,
        )
        lexical = self.bm25.search(query.text, candidate_count)
        embedding_fallback = False
        try:
            dense = self.dense.search(query.text, candidate_count)
        except Exception:
            if not self.allow_embedding_fallback:
                raise
            dense = ()
            embedding_fallback = True

        rows: dict[str, _FusionRow] = {}
        for result in lexical:
            row = rows.setdefault(
                result.child.child_id,
                _FusionRow(child=result.child),
            )
            row.rrf_score += 1 / (self.rrf_k + result.rank)
            row.bm25_rank = result.rank
            row.bm25_score = result.score
        for result in dense:
            row = rows.setdefault(
                result.child.child_id,
                _FusionRow(child=result.child),
            )
            row.rrf_score += 1 / (self.rrf_k + result.rank)
            row.dense_rank = result.rank
            row.dense_score = result.score

        ranked_children = sorted(
            rows.values(),
            key=lambda row: (-row.rrf_score, row.child.child_id),
        )
        parent_rows: list[_FusionRow] = []
        seen_parents: set[str] = set()
        for row in ranked_children:
            if row.child.parent_id in seen_parents:
                continue
            seen_parents.add(row.child.parent_id)
            parent_rows.append(row)
            if len(parent_rows) >= query.top_k:
                break

        hits = tuple(
            self._to_hit(
                row,
                rank=rank,
                embedding_fallback=embedding_fallback,
            )
            for rank, row in enumerate(parent_rows, start=1)
        )
        return KnowledgeSearchResult(
            query=query,
            hits=hits,
            provider=self.provider_name,
        )

    def _to_hit(
        self,
        row: _FusionRow,
        *,
        rank: int,
        embedding_fallback: bool,
    ) -> KnowledgeHit:
        child = row.child
        parent = self.parents[child.parent_id]
        metadata = parent.metadata
        attributes = dict(metadata.attributes)
        attributes.update(
            {
                "bm25_rank": row.bm25_rank,
                "bm25_score": row.bm25_score,
                "dense_rank": row.dense_rank,
                "dense_score": row.dense_score,
                "embedding_provider": self.embedding_provider.provider_name,
                "embedding_fallback": embedding_fallback,
            }
        )
        return KnowledgeHit(
            chunk_id=child.child_id,
            parent_id=parent.parent_id,
            content=parent.content,
            matched_content=child.content,
            score=round(row.rrf_score, 8),
            rank=rank,
            metadata=KnowledgeMetadata(
                source_id=metadata.source_id,
                title=metadata.title,
                knowledge_type=metadata.knowledge_type,
                version=metadata.version,
                updated_at=metadata.updated_at,
                positions=metadata.positions,
                language=metadata.language,
                attributes=attributes,
            ),
        )
