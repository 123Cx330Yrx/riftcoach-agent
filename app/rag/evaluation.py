"""Deterministic retrieval metrics for RAG experiments."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from types import MappingProxyType
from pathlib import Path
from typing import Any, Mapping

from .models import KnowledgeQuery


@dataclass(frozen=True)
class RetrievalCase:
    case_id: str
    query: str
    relevant_source_ids: tuple[str, ...]
    top_k: int = 5
    split: str = "development"
    category: str = "answerable"
    filters: Mapping[str, Any] = field(default_factory=dict)
    expected_abstained: bool | None = None
    citation_terms: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.case_id.strip():
            raise ValueError("retrieval case_id must not be empty.")
        if not self.query.strip():
            raise ValueError("retrieval query must not be empty.")
        if not self.split.strip():
            raise ValueError("retrieval split must not be empty.")
        if not self.category.strip():
            raise ValueError("retrieval category must not be empty.")
        if not 1 <= self.top_k <= 20:
            raise ValueError("retrieval top_k must be between 1 and 20.")
        if self.expected_abstained is not None and not isinstance(
            self.expected_abstained, bool
        ):
            raise ValueError("expected_abstained must be a boolean or None.")
        object.__setattr__(
            self,
            "filters",
            MappingProxyType(dict(self.filters or {})),
        )
        object.__setattr__(self, "citation_terms", tuple(self.citation_terms))

    @property
    def expects_answer(self) -> bool:
        return bool(self.relevant_source_ids)


@dataclass(frozen=True)
class RetrievalCaseResult:
    case_id: str
    split: str
    category: str
    retrieved_source_ids: tuple[str, ...]
    abstained: bool
    expected_abstained: bool | None
    abstention_match: bool | None
    citation_supported: bool | None
    recall_at_k: float
    reciprocal_rank: float
    ndcg_at_k: float
    false_positive: bool


@dataclass(frozen=True)
class RetrievalEvaluation:
    cases: tuple[RetrievalCaseResult, ...]
    recall_at_k: float
    mrr: float
    ndcg_at_k: float
    no_answer_false_positive_rate: float
    abstention_accuracy: float | None = None
    citation_support_rate: float | None = None


@dataclass(frozen=True)
class RetrievalDataset:
    """Versioned evaluation cases and their calibration boundary."""

    dataset_version: str
    role: str
    calibration_excluded: bool
    cases: tuple[RetrievalCase, ...]
    metadata: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not self.dataset_version.strip():
            raise ValueError("dataset_version must not be empty.")
        if not self.role.strip():
            raise ValueError("dataset role must not be empty.")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


def load_retrieval_dataset(path: Path) -> RetrievalDataset:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = tuple(
        RetrievalCase(
            case_id=row["case_id"],
            query=row["query"],
            relevant_source_ids=tuple(row.get("relevant_source_ids", [])),
            top_k=row.get("top_k", 5),
            split=row.get("split", "development"),
            category=row.get(
                "category",
                "no_answer" if not row.get("relevant_source_ids", []) else "answerable",
            ),
            filters=row.get("filters", {}),
            expected_abstained=row.get("expected_abstained"),
            citation_terms=tuple(row.get("citation_terms", [])),
        )
        for row in payload["cases"]
    )
    return RetrievalDataset(
        dataset_version=str(
            payload.get("dataset_version", payload.get("version", "unknown"))
        ),
        role=str(payload.get("role", "development")),
        calibration_excluded=bool(payload.get("calibration_excluded", False)),
        cases=cases,
        metadata={
            key: value
            for key, value in payload.items()
            if key not in {"cases", "dataset_version", "version", "role", "calibration_excluded"}
        },
    )


def load_retrieval_cases(path: Path) -> tuple[RetrievalCase, ...]:
    """Backward-compatible loader for callers that only need the cases."""

    return load_retrieval_dataset(path).cases


def evaluate_retrieval(provider, cases: tuple[RetrievalCase, ...]) -> RetrievalEvaluation:
    results = []
    for case in cases:
        search_result = provider.search(
            KnowledgeQuery(
                text=case.query,
                top_k=case.top_k,
                filters=case.filters,
            )
        )
        retrieved = tuple(hit.metadata.source_id for hit in search_result.hits)
        results.append(
            _evaluate_case(
                case,
                retrieved,
                abstained=search_result.abstained,
                hits=search_result.hits,
            )
        )

    answerable = [result for case, result in zip(cases, results) if case.expects_answer]
    no_answer = [result for case, result in zip(cases, results) if not case.expects_answer]
    return RetrievalEvaluation(
        cases=tuple(results),
        recall_at_k=_mean(result.recall_at_k for result in answerable),
        mrr=_mean(result.reciprocal_rank for result in answerable),
        ndcg_at_k=_mean(result.ndcg_at_k for result in answerable),
        no_answer_false_positive_rate=_mean(
            float(result.false_positive) for result in no_answer
        ),
        abstention_accuracy=_mean_optional(
            result.abstention_match
            for result in results
            if result.abstention_match is not None
        ),
        citation_support_rate=_mean_optional(
            float(result.citation_supported)
            for result in results
            if result.citation_supported is not None
        ),
    )


def _evaluate_case(
    case: RetrievalCase,
    retrieved_source_ids: tuple[str, ...],
    *,
    abstained: bool,
    hits,
) -> RetrievalCaseResult:
    relevant = set(case.relevant_source_ids)
    abstention_match = (
        None
        if case.expected_abstained is None
        else abstained == case.expected_abstained
    )
    citation_supported = (
        None
        if not case.citation_terms
        else _citation_terms_supported(case, hits)
    )
    if not relevant:
        return RetrievalCaseResult(
            case_id=case.case_id,
            split=case.split,
            category=case.category,
            retrieved_source_ids=retrieved_source_ids,
            abstained=abstained,
            expected_abstained=case.expected_abstained,
            abstention_match=abstention_match,
            citation_supported=citation_supported,
            recall_at_k=0.0,
            reciprocal_rank=0.0,
            ndcg_at_k=0.0,
            false_positive=bool(retrieved_source_ids),
        )

    matched = relevant.intersection(retrieved_source_ids)
    recall = len(matched) / len(relevant)
    first_rank = next(
        (
            rank
            for rank, source_id in enumerate(retrieved_source_ids, start=1)
            if source_id in relevant
        ),
        None,
    )
    reciprocal_rank = 1 / first_rank if first_rank is not None else 0.0
    credited_sources: set[str] = set()
    gains = []
    for source_id in retrieved_source_ids:
        is_new_relevant = (
            source_id in relevant and source_id not in credited_sources
        )
        gains.append(1.0 if is_new_relevant else 0.0)
        if is_new_relevant:
            credited_sources.add(source_id)
    dcg = sum(gain / math.log2(rank + 1) for rank, gain in enumerate(gains, start=1))
    ideal_hits = min(len(relevant), case.top_k)
    ideal_dcg = sum(
        1 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1)
    )
    return RetrievalCaseResult(
        case_id=case.case_id,
        split=case.split,
        category=case.category,
        retrieved_source_ids=retrieved_source_ids,
        abstained=abstained,
        expected_abstained=case.expected_abstained,
        abstention_match=abstention_match,
        citation_supported=citation_supported,
        recall_at_k=round(recall, 6),
        reciprocal_rank=round(reciprocal_rank, 6),
        ndcg_at_k=round(dcg / ideal_dcg if ideal_dcg else 0.0, 6),
        false_positive=False,
    )


def _citation_terms_supported(case: RetrievalCase, hits) -> bool:
    relevant_hits = tuple(
        hit
        for hit in hits
        if not case.relevant_source_ids
        or hit.metadata.source_id in set(case.relevant_source_ids)
    )
    evidence = "\n".join(
        (hit.matched_content or hit.content) for hit in relevant_hits
    ).casefold()
    return bool(relevant_hits) and all(
        term.casefold() in evidence for term in case.citation_terms
    )


def _mean(values) -> float:
    rows = list(values)
    return round(sum(rows) / len(rows), 6) if rows else 0.0


def _mean_optional(values) -> float | None:
    rows = list(values)
    return round(sum(rows) / len(rows), 6) if rows else None
