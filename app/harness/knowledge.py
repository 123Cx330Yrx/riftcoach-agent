"""Shared fail-closed conversion from knowledge tool payloads to evidence."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .steps import KnowledgeCitation, KnowledgeEvidence


class KnowledgeEvidenceBuildError(ValueError):
    """Raised when a knowledge tool payload cannot be safely attributed."""


def knowledge_evidence_from_search_payloads(
    payloads: Iterable[Mapping[str, Any]],
) -> KnowledgeEvidence:
    """Build stable evidence from one or more actual knowledge search results."""

    search_payloads = tuple(payloads)
    if not search_payloads:
        return KnowledgeEvidence.empty()

    unique_chunks: list[dict[str, Any]] = []
    seen_chunks: dict[str, tuple[Any, ...]] = {}
    search_diagnostics: list[dict[str, Any]] = []
    abstained_values: list[bool] = []

    for search_index, payload in enumerate(search_payloads, start=1):
        if not isinstance(payload, Mapping):
            raise KnowledgeEvidenceBuildError(
                f"search payload {search_index} must be a mapping"
            )
        provider = _required_text(payload.get("provider"), "provider")
        abstained = payload.get("abstained")
        if not isinstance(abstained, bool):
            raise KnowledgeEvidenceBuildError("abstained must be a boolean")
        diagnostics = payload.get("diagnostics")
        if not isinstance(diagnostics, Mapping):
            raise KnowledgeEvidenceBuildError("diagnostics must be a mapping")
        chunks = payload.get("chunks")
        if not isinstance(chunks, (list, tuple)):
            raise KnowledgeEvidenceBuildError("chunks must be an array")
        count = payload.get("count")
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise KnowledgeEvidenceBuildError(
                "count must be a non-negative integer"
            )
        if count != len(chunks):
            raise KnowledgeEvidenceBuildError(
                "count must equal the number of chunks"
            )
        if abstained and chunks:
            raise KnowledgeEvidenceBuildError(
                "abstained search payload cannot contain chunks"
            )

        normalized_chunks = [
            _normalize_chunk(chunk, search_index=search_index)
            for chunk in chunks
        ]
        normalized_chunks.sort(key=lambda chunk: chunk["rank"])
        for chunk in normalized_chunks:
            chunk_id = chunk["chunk_id"]
            identity = _attribution_identity(chunk)
            previous = seen_chunks.get(chunk_id)
            if previous is not None:
                if previous != identity:
                    raise KnowledgeEvidenceBuildError(
                        f"conflicting attributable content for chunk {chunk_id!r}"
                    )
                continue
            seen_chunks[chunk_id] = identity
            unique_chunks.append(chunk)

        abstained_values.append(abstained)
        search_diagnostics.append(
            {
                "provider": provider,
                "abstained": abstained,
                "count": count,
                "diagnostics": dict(diagnostics),
            }
        )

    citations = tuple(
        KnowledgeCitation(
            citation_id=f"K{index}",
            chunk_id=chunk["chunk_id"],
            parent_id=chunk["parent_id"],
            source_id=chunk["source_id"],
            title=chunk["title"],
            content=chunk["content"],
            matched_content=chunk["matched_content"],
            version=chunk["version"],
            updated_at=chunk["updated_at"],
        )
        for index, chunk in enumerate(unique_chunks, start=1)
    )
    source_ids = tuple(
        dict.fromkeys(citation.source_id for citation in citations)
    )
    diagnostics: Mapping[str, Any]
    if len(search_diagnostics) == 1:
        diagnostics = search_diagnostics[0]["diagnostics"]
    else:
        diagnostics = {"searches": tuple(search_diagnostics)}

    return KnowledgeEvidence(
        context=_format_citations(citations),
        source_ids=source_ids,
        citations=citations,
        abstained=not citations and all(abstained_values),
        diagnostics=diagnostics,
    )


def _normalize_chunk(
    value: Any,
    *,
    search_index: int,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise KnowledgeEvidenceBuildError(
            f"search payload {search_index} chunks must contain mappings"
        )
    rank = value.get("rank")
    if isinstance(rank, bool) or not isinstance(rank, int) or rank < 1:
        raise KnowledgeEvidenceBuildError("chunk rank must be a positive integer")
    return {
        "chunk_id": _required_text(value.get("chunk_id"), "chunk_id"),
        "parent_id": _optional_text(value.get("parent_id"), "parent_id"),
        "source_id": _required_text(value.get("source_id"), "source_id"),
        "title": _required_text(value.get("title"), "title"),
        "content": _required_text(value.get("content"), "content"),
        "matched_content": _optional_text(
            value.get("matched_content"),
            "matched_content",
        ),
        "version": _optional_text(value.get("version"), "version"),
        "updated_at": _optional_text(
            value.get("updated_at"),
            "updated_at",
        ),
        "rank": rank,
    }


def _attribution_identity(chunk: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        chunk["parent_id"],
        chunk["source_id"],
        chunk["title"],
        chunk["content"],
        chunk["version"],
        chunk["updated_at"],
    )


def _required_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise KnowledgeEvidenceBuildError(f"{field_name} must not be blank")
    return value.strip()


def _optional_text(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise KnowledgeEvidenceBuildError(
            f"{field_name} must be a non-blank string or null"
        )
    return value.strip()


def _format_citations(citations: tuple[KnowledgeCitation, ...]) -> str:
    if not citations:
        return "未检索到足够相关的可用知识；不得用相近但不相关的内容补足。"
    sections = []
    for citation in citations:
        version_text = f"；版本：{citation.version}" if citation.version else ""
        sections.append(
            f"[{citation.citation_id}] 来源：{citation.source_id}；"
            f"章节：{citation.title}{version_text}\n"
            f"{citation.content}"
        )
    return "\n\n".join(sections)
