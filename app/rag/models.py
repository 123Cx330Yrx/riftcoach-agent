"""Provider-neutral knowledge retrieval contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from types import MappingProxyType
from typing import Any, Mapping


def _immutable_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(value))


@dataclass(frozen=True)
class KnowledgeMetadata:
    """Attribution and applicability carried with every knowledge hit."""

    source_id: str
    title: str
    knowledge_type: str = "unknown"
    version: str | None = None
    updated_at: date | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    positions: tuple[str, ...] = ()
    language: str = "zh-CN"
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("Knowledge source_id must not be empty.")
        if not self.title.strip():
            raise ValueError("Knowledge title must not be empty.")
        if (
            self.valid_from is not None
            and self.valid_until is not None
            and self.valid_from > self.valid_until
        ):
            raise ValueError("Knowledge valid_from must not be after valid_until.")
        object.__setattr__(self, "attributes", _immutable_mapping(self.attributes))


@dataclass(frozen=True)
class KnowledgeQuery:
    text: str
    top_k: int = 5
    filters: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("Knowledge query text must not be empty.")
        if not 1 <= self.top_k <= 20:
            raise ValueError("Knowledge query top_k must be between 1 and 20.")
        object.__setattr__(self, "filters", _immutable_mapping(self.filters))


@dataclass(frozen=True)
class KnowledgeHit:
    chunk_id: str
    parent_id: str | None
    content: str
    score: float
    rank: int
    metadata: KnowledgeMetadata
    matched_content: str | None = None

    def __post_init__(self) -> None:
        if not self.chunk_id.strip():
            raise ValueError("Knowledge chunk_id must not be empty.")
        if not self.content.strip():
            raise ValueError("Knowledge hit content must not be empty.")
        if self.rank < 1:
            raise ValueError("Knowledge hit rank must start at 1.")


@dataclass(frozen=True)
class KnowledgeSearchResult:
    query: KnowledgeQuery
    hits: tuple[KnowledgeHit, ...]
    provider: str
    abstained: bool = False
    diagnostics: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ValueError("Knowledge provider name must not be empty.")
        if self.abstained and self.hits:
            raise ValueError("An abstained knowledge result must not contain hits.")
        expected_ranks = tuple(range(1, len(self.hits) + 1))
        actual_ranks = tuple(hit.rank for hit in self.hits)
        if actual_ranks != expected_ranks:
            raise ValueError("Knowledge hit ranks must be contiguous and ordered.")
        object.__setattr__(self, "diagnostics", _immutable_mapping(self.diagnostics))
