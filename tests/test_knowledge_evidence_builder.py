from __future__ import annotations

import pytest

from app.harness.knowledge import (
    KnowledgeEvidenceBuildError,
    knowledge_evidence_from_search_payloads,
)


def chunk(
    chunk_id: str,
    *,
    source_id: str,
    content: str,
    rank: int = 1,
    score: float = 1.0,
) -> dict:
    return {
        "chunk_id": chunk_id,
        "parent_id": None,
        "source_id": source_id,
        "title": f"Title {chunk_id}",
        "content": content,
        "matched_content": content,
        "score": score,
        "rank": rank,
        "knowledge_type": "training",
        "version": "16.13",
        "updated_at": "2026-08-01",
        "valid_from": None,
        "valid_until": None,
        "positions": ["TOP"],
        "attributes": {},
    }


def payload(
    chunks: list[dict],
    *,
    provider: str = "local-hybrid",
    abstained: bool = False,
    diagnostics: dict | None = None,
) -> dict:
    return {
        "provider": provider,
        "abstained": abstained,
        "diagnostics": diagnostics or {"mode": "test"},
        "chunks": chunks,
        "count": len(chunks),
    }


def test_single_search_payload_preserves_legacy_citation_contract():
    evidence = knowledge_evidence_from_search_payloads(
        (
            payload(
                [
                    chunk(
                        "doc:1",
                        source_id="guide.md",
                        content="Use deaths as a review clue, not proof of cause.",
                    )
                ],
            ),
        )
    )

    assert evidence.source_ids == ("guide.md",)
    assert evidence.abstained is False
    assert evidence.diagnostics == {"mode": "test"}
    assert len(evidence.citations) == 1
    assert evidence.citations[0].citation_id == "K1"
    assert evidence.citations[0].chunk_id == "doc:1"
    assert "[K1]" in evidence.context
    assert "guide.md" in evidence.context


def test_multiple_searches_deduplicate_chunks_and_assign_stable_citations():
    first_a = chunk(
        "doc:a",
        source_id="a.md",
        content="A",
        rank=1,
        score=0.9,
    )
    first_b = chunk(
        "doc:b",
        source_id="b.md",
        content="B",
        rank=2,
        score=0.8,
    )
    repeated_b = {
        **first_b,
        "rank": 1,
        "score": 0.99,
    }
    second_c = chunk(
        "doc:c",
        source_id="a.md",
        content="C",
        rank=2,
    )

    evidence = knowledge_evidence_from_search_payloads(
        (
            payload([first_a, first_b], diagnostics={"query": 1}),
            payload([repeated_b, second_c], diagnostics={"query": 2}),
        )
    )

    assert [item.citation_id for item in evidence.citations] == [
        "K1",
        "K2",
        "K3",
    ]
    assert [item.chunk_id for item in evidence.citations] == [
        "doc:a",
        "doc:b",
        "doc:c",
    ]
    assert evidence.source_ids == ("a.md", "b.md")
    assert len(evidence.diagnostics["searches"]) == 2


def test_all_abstained_searches_preserve_explicit_no_answer_state():
    evidence = knowledge_evidence_from_search_payloads(
        (
            payload([], abstained=True),
            payload([], abstained=True),
        )
    )

    assert evidence.abstained is True
    assert evidence.citations == ()
    assert evidence.source_ids == ()
    assert "未检索到足够相关" in evidence.context


def test_search_payload_count_mismatch_fails_closed():
    bad = payload([])
    bad["count"] = 1

    with pytest.raises(KnowledgeEvidenceBuildError, match="count"):
        knowledge_evidence_from_search_payloads((bad,))


def test_conflicting_duplicate_chunk_id_fails_closed():
    original = chunk(
        "doc:conflict",
        source_id="guide.md",
        content="original",
    )
    conflict = {
        **original,
        "content": "changed",
    }

    with pytest.raises(KnowledgeEvidenceBuildError, match="conflicting"):
        knowledge_evidence_from_search_payloads(
            (payload([original]), payload([conflict]))
        )
