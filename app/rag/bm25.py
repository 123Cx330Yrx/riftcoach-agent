"""Small, deterministic BM25 index for local RiftCoach knowledge."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

from .documents import ChildChunk
from .retriever import tokenize


@dataclass(frozen=True)
class RankedChild:
    child: ChildChunk
    score: float
    rank: int


class BM25Index:
    def __init__(
        self,
        children: tuple[ChildChunk, ...],
        *,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        if not children:
            raise ValueError("BM25 index requires at least one child chunk.")
        if k1 <= 0:
            raise ValueError("BM25 k1 must be positive.")
        if not 0 <= b <= 1:
            raise ValueError("BM25 b must be between 0 and 1.")

        self.children = children
        self.k1 = k1
        self.b = b
        self._tokens = [Counter(tokenize(child.content)) for child in children]
        self._lengths = [sum(tokens.values()) for tokens in self._tokens]
        self._average_length = sum(self._lengths) / len(self._lengths)
        self._document_frequency: Counter[str] = Counter()
        for tokens in self._tokens:
            self._document_frequency.update(tokens.keys())

    def search(self, query: str, top_k: int) -> tuple[RankedChild, ...]:
        if top_k <= 0:
            return ()
        query_terms = Counter(tokenize(query))
        if not query_terms:
            return ()

        scored: list[tuple[ChildChunk, float]] = []
        total = len(self.children)
        for child, tokens, document_length in zip(
            self.children,
            self._tokens,
            self._lengths,
        ):
            score = 0.0
            for term, query_frequency in query_terms.items():
                frequency = tokens.get(term, 0)
                if not frequency:
                    continue
                document_frequency = self._document_frequency[term]
                inverse_document_frequency = math.log(
                    1 + (total - document_frequency + 0.5) / (document_frequency + 0.5)
                )
                length_normalization = 1 - self.b + self.b * (
                    document_length / self._average_length
                )
                saturated_frequency = (
                    frequency * (self.k1 + 1)
                    / (frequency + self.k1 * length_normalization)
                )
                score += (
                    inverse_document_frequency
                    * saturated_frequency
                    * query_frequency
                )
            if score > 0:
                scored.append((child, score))

        scored.sort(key=lambda item: (-item[1], item[0].child_id))
        return tuple(
            RankedChild(
                child=child,
                score=round(score, 8),
                rank=rank,
            )
            for rank, (child, score) in enumerate(scored[:top_k], start=1)
        )
