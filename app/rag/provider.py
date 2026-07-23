"""Knowledge retrieval provider boundary."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import KnowledgeQuery, KnowledgeSearchResult


@runtime_checkable
class KnowledgeProvider(Protocol):
    provider_name: str

    def search(self, query: KnowledgeQuery) -> KnowledgeSearchResult:
        """Return ranked, attributable evidence for a bounded query."""

