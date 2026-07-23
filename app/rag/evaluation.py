"""Deterministic retrieval metrics for RAG experiments."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from .models import KnowledgeQuery


@dataclass(frozen=True)
class RetrievalCase:
    case_id: str
    query: str
    relevant_source_ids: tuple[str, ...]
    top_k: int = 5

    @property
    def expects_answer(self) -> bool:
        return bool(self.relevant_source_ids)


@dataclass(frozen=True)
class RetrievalCaseResult:
    case_id: str
    retrieved_source_ids: tuple[str, ...]
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


def load_retrieval_cases(path: Path) -> tuple[RetrievalCase, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return tuple(
        RetrievalCase(
            case_id=row["case_id"],
            query=row["query"],
            relevant_source_ids=tuple(row.get("relevant_source_ids", [])),
            top_k=row.get("top_k", 5),
        )
        for row in payload["cases"]
    )


def evaluate_retrieval(provider, cases: tuple[RetrievalCase, ...]) -> RetrievalEvaluation:
    results = []
    for case in cases:
        search_result = provider.search(
            KnowledgeQuery(text=case.query, top_k=case.top_k)
        )
        retrieved = tuple(hit.metadata.source_id for hit in search_result.hits)
        results.append(_evaluate_case(case, retrieved))

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
    )


def _evaluate_case(
    case: RetrievalCase,
    retrieved_source_ids: tuple[str, ...],
) -> RetrievalCaseResult:
    relevant = set(case.relevant_source_ids)
    if not relevant:
        return RetrievalCaseResult(
            case_id=case.case_id,
            retrieved_source_ids=retrieved_source_ids,
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
        retrieved_source_ids=retrieved_source_ids,
        recall_at_k=round(recall, 6),
        reciprocal_rank=round(reciprocal_rank, 6),
        ndcg_at_k=round(dcg / ideal_dcg if ideal_dcg else 0.0, 6),
        false_positive=False,
    )


def _mean(values) -> float:
    rows = list(values)
    return round(sum(rows) / len(rows), 6) if rows else 0.0
