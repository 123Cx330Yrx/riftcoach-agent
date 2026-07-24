"""Deterministic evidence policy for applicability, support, conflicts, and diversity."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import date
from typing import Any, Mapping

from .models import KnowledgeHit, KnowledgeMetadata, KnowledgeQuery
from .retriever import tokenize


@dataclass(frozen=True)
class EvidencePolicyConfig:
    minimum_bm25_score: float = 15.0
    minimum_query_coverage: float = 0.18
    max_hits_per_source: int = 1
    coverage_denominator_cap: int = 12

    def __post_init__(self) -> None:
        if self.minimum_bm25_score < 0:
            raise ValueError("minimum_bm25_score must not be negative.")
        if not 0 <= self.minimum_query_coverage <= 1:
            raise ValueError("minimum_query_coverage must be between 0 and 1.")
        if self.max_hits_per_source < 1:
            raise ValueError("max_hits_per_source must be at least 1.")
        if self.coverage_denominator_cap < 1:
            raise ValueError("coverage_denominator_cap must be at least 1.")


@dataclass(frozen=True)
class EvidencePolicyOutcome:
    hits: tuple[KnowledgeHit, ...]
    abstained: bool
    diagnostics: Mapping[str, Any]


class EvidenceSupportReranker:
    """Reorder supported hits using interpretable, deterministic signals."""

    def rerank(
        self,
        query: KnowledgeQuery,
        hits: tuple[KnowledgeHit, ...],
    ) -> tuple[KnowledgeHit, ...]:
        rescored = []
        for original_rank, hit in enumerate(hits, start=1):
            attributes = dict(hit.metadata.attributes)
            coverage = float(attributes.get("query_coverage", 0.0))
            bm25_rank = attributes.get("bm25_rank")
            dense_rank = attributes.get("dense_rank")
            rerank_score = (
                0.55 * coverage
                + 0.25 * _reciprocal(bm25_rank)
                + 0.15 * _reciprocal(dense_rank)
                + 0.05 * (1 / original_rank)
            )
            attributes["rerank_score"] = round(rerank_score, 8)
            rescored.append(
                replace(
                    hit,
                    metadata=_replace_attributes(hit.metadata, attributes),
                )
            )
        rescored.sort(
            key=lambda hit: (
                -float(hit.metadata.attributes["rerank_score"]),
                hit.chunk_id,
            )
        )
        return tuple(
            replace(hit, rank=rank)
            for rank, hit in enumerate(rescored, start=1)
        )


class EvidencePolicy:
    def __init__(
        self,
        config: EvidencePolicyConfig | None = None,
        *,
        reranker: EvidenceSupportReranker | None = None,
    ) -> None:
        self.config = config or EvidencePolicyConfig()
        self.reranker = reranker or EvidenceSupportReranker()

    def apply(
        self,
        query: KnowledgeQuery,
        hits: tuple[KnowledgeHit, ...],
    ) -> EvidencePolicyOutcome:
        applicable = tuple(hit for hit in hits if _is_applicable(hit, query.filters))
        supported = []
        rejected_for_support = 0
        for hit in applicable:
            coverage = query_coverage(
                query.text,
                hit.matched_content or hit.content,
                denominator_cap=self.config.coverage_denominator_cap,
            )
            attributes = dict(hit.metadata.attributes)
            attributes["query_coverage"] = round(coverage, 8)
            annotated = replace(
                hit,
                metadata=_replace_attributes(hit.metadata, attributes),
            )
            bm25_score = attributes.get("bm25_score")
            if (
                isinstance(bm25_score, (int, float))
                and bm25_score >= self.config.minimum_bm25_score
                and coverage >= self.config.minimum_query_coverage
            ):
                supported.append(annotated)
            else:
                rejected_for_support += 1

        resolved, conflicts = _resolve_knowledge_keys(tuple(supported), query.filters)
        reranked = self.reranker.rerank(query, resolved)
        diversified, rejected_for_diversity = _limit_per_source(
            reranked,
            self.config.max_hits_per_source,
            query.top_k,
        )
        abstained = not diversified
        if not applicable:
            reason = "no_applicable_evidence"
        elif not supported:
            reason = "insufficient_evidence"
        elif conflicts and not diversified:
            reason = "unresolved_conflict"
        else:
            reason = "evidence_available"
        diagnostics = {
            "reason": reason,
            "candidate_count": len(hits),
            "applicable_count": len(applicable),
            "supported_count": len(supported),
            "returned_count": len(diversified),
            "rejected_for_support": rejected_for_support,
            "rejected_for_diversity": rejected_for_diversity,
            "conflict_keys": list(conflicts),
            "thresholds": {
                "minimum_bm25_score": self.config.minimum_bm25_score,
                "minimum_query_coverage": self.config.minimum_query_coverage,
                "max_hits_per_source": self.config.max_hits_per_source,
                "coverage_denominator_cap": self.config.coverage_denominator_cap,
            },
        }
        return EvidencePolicyOutcome(
            hits=diversified,
            abstained=abstained,
            diagnostics=diagnostics,
        )


def query_coverage(
    query: str,
    content: str,
    *,
    denominator_cap: int = 12,
) -> float:
    query_terms = _informative_terms(query)
    if not query_terms:
        return 0.0
    content_terms = _informative_terms(content)
    denominator = min(len(query_terms), denominator_cap)
    return min(1.0, len(query_terms.intersection(content_terms)) / denominator)


def _informative_terms(text: str) -> set[str]:
    return {
        token
        for token in tokenize(text)
        if len(token) > 1 or token.isascii()
    }


def _is_applicable(hit: KnowledgeHit, filters: Mapping[str, Any]) -> bool:
    metadata = hit.metadata
    requested_version = filters.get("version")
    if (
        requested_version
        and metadata.version not in {"evergreen", str(requested_version)}
    ):
        return False

    requested_position = filters.get("position")
    if (
        requested_position
        and metadata.positions
        and "ALL" not in metadata.positions
        and str(requested_position) not in metadata.positions
    ):
        return False

    as_of = _filter_date(filters.get("as_of"))
    if as_of is not None:
        if metadata.valid_from is not None and as_of < metadata.valid_from:
            return False
        if metadata.valid_until is not None and as_of > metadata.valid_until:
            return False
    return True


def _resolve_knowledge_keys(
    hits: tuple[KnowledgeHit, ...],
    filters: Mapping[str, Any],
) -> tuple[tuple[KnowledgeHit, ...], tuple[str, ...]]:
    grouped: dict[str, list[KnowledgeHit]] = defaultdict(list)
    for hit in hits:
        key = str(
            hit.metadata.attributes.get(
                "knowledge_key",
                f"{hit.metadata.source_id}#{hit.metadata.title}",
            )
        )
        grouped[key].append(hit)

    resolved: list[KnowledgeHit] = []
    conflicts: list[str] = []
    requested_version = filters.get("version")
    for key, group in grouped.items():
        priorities = [
            (_knowledge_priority(hit, requested_version), hit)
            for hit in group
        ]
        best_priority = max(priority for priority, _ in priorities)
        best = [hit for priority, hit in priorities if priority == best_priority]
        if len({hit.content for hit in best}) > 1:
            conflicts.append(key)
            continue
        resolved.append(sorted(best, key=lambda hit: hit.chunk_id)[0])
    return tuple(resolved), tuple(sorted(conflicts))


def _knowledge_priority(
    hit: KnowledgeHit,
    requested_version: Any,
) -> tuple[int, int]:
    version_priority = 0
    if requested_version and hit.metadata.version == str(requested_version):
        version_priority = 2
    elif hit.metadata.version == "evergreen":
        version_priority = 1
    updated_ordinal = (
        hit.metadata.updated_at.toordinal()
        if hit.metadata.updated_at is not None
        else 0
    )
    return version_priority, updated_ordinal


def _limit_per_source(
    hits: tuple[KnowledgeHit, ...],
    max_per_source: int,
    top_k: int,
) -> tuple[tuple[KnowledgeHit, ...], int]:
    counts: dict[str, int] = defaultdict(int)
    selected = []
    rejected = 0
    for hit in hits:
        source_id = hit.metadata.source_id
        if counts[source_id] >= max_per_source:
            rejected += 1
            continue
        counts[source_id] += 1
        selected.append(hit)
        if len(selected) >= top_k:
            break
    return (
        tuple(replace(hit, rank=rank) for rank, hit in enumerate(selected, start=1)),
        rejected,
    )


def _replace_attributes(
    metadata: KnowledgeMetadata,
    attributes: Mapping[str, Any],
) -> KnowledgeMetadata:
    return replace(metadata, attributes=attributes)


def _filter_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError("Knowledge filter as_of must use YYYY-MM-DD.") from exc


def _reciprocal(rank: Any) -> float:
    return 1 / rank if isinstance(rank, int) and rank > 0 else 0.0
