"""Embedding boundary and deterministic local dense retrieval baseline."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from .bm25 import RankedChild
from .documents import ChildChunk
from .retriever import tokenize


Vector = tuple[float, ...]


@runtime_checkable
class EmbeddingProvider(Protocol):
    provider_name: str
    dimensions: int

    def embed(self, texts: tuple[str, ...]) -> tuple[Vector, ...]:
        """Embed texts in input order using a fixed dimensionality."""


class HashingEmbeddingProvider:
    """Dependency-free vector baseline; not a semantic language model."""

    provider_name = "local-hashing"

    def __init__(self, dimensions: int = 256) -> None:
        if dimensions < 32:
            raise ValueError("Hashing embedding dimensions must be at least 32.")
        self.dimensions = dimensions

    def embed(self, texts: tuple[str, ...]) -> tuple[Vector, ...]:
        return tuple(self._embed_one(text) for text in texts)

    def _embed_one(self, text: str) -> Vector:
        values = [0.0] * self.dimensions
        for token in tokenize(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:8], "big") % self.dimensions
            sign = 1.0 if digest[8] % 2 == 0 else -1.0
            values[index] += sign
        return _normalize(values)


@dataclass(frozen=True)
class DenseSearchResult:
    child: ChildChunk
    score: float
    rank: int


class DenseIndex:
    def __init__(
        self,
        children: tuple[ChildChunk, ...],
        provider: EmbeddingProvider,
    ) -> None:
        if not children:
            raise ValueError("Dense index requires at least one child chunk.")
        self.children = children
        self.provider = provider
        self._vectors = provider.embed(tuple(child.content for child in children))
        if len(self._vectors) != len(children):
            raise ValueError("Embedding provider returned the wrong vector count.")
        if any(len(vector) != provider.dimensions for vector in self._vectors):
            raise ValueError("Embedding provider returned an invalid dimension.")

    def search(self, query: str, top_k: int) -> tuple[DenseSearchResult, ...]:
        if top_k <= 0:
            return ()
        query_vectors = self.provider.embed((query,))
        if len(query_vectors) != 1 or len(query_vectors[0]) != self.provider.dimensions:
            raise ValueError("Embedding provider returned an invalid query vector.")
        query_vector = query_vectors[0]
        scored = [
            (child, _dot(query_vector, vector))
            for child, vector in zip(self.children, self._vectors)
        ]
        scored = [item for item in scored if item[1] > 0]
        scored.sort(key=lambda item: (-item[1], item[0].child_id))
        return tuple(
            DenseSearchResult(
                child=child,
                score=round(score, 8),
                rank=rank,
            )
            for rank, (child, score) in enumerate(scored[:top_k], start=1)
        )


def _normalize(values: list[float]) -> Vector:
    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0:
        return tuple(0.0 for _ in values)
    return tuple(value / norm for value in values)


def _dot(left: Vector, right: Vector) -> float:
    return sum(a * b for a, b in zip(left, right))
