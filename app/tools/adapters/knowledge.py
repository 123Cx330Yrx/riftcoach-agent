"""Tool adapter for provider-neutral RiftCoach knowledge retrieval."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Callable, Mapping

from app.rag.legacy_provider import LegacyLocalKnowledgeProvider
from app.rag.models import KnowledgeQuery
from app.rag.provider import KnowledgeProvider

from ..models import CachePolicy, ToolContext, ToolDefinition, ToolPolicy


def build_knowledge_tools(
    knowledge: Any, *, include_retrieval_time: bool = False,
    utc_now: Callable[[], datetime] | None = None,
) -> tuple[ToolDefinition, ...]:
    provider: KnowledgeProvider = (
        knowledge
        if isinstance(knowledge, KnowledgeProvider)
        else LegacyLocalKnowledgeProvider(knowledge)
    )

    def search_handler(
        params: Mapping[str, Any],
        context: ToolContext,
    ) -> Mapping[str, Any]:
        result = provider.search(
            KnowledgeQuery(
                text=params["query"],
                top_k=params["top_k"],
                filters=params.get("filters", {}),
            )
        )
        rows = [_serialize_hit(hit) for hit in result.hits]
        payload = {
            "provider": result.provider,
            "abstained": result.abstained,
            "diagnostics": dict(result.diagnostics),
            "chunks": rows,
            "count": len(rows),
        }
        if include_retrieval_time:
            # Host-owned completion time, never provider diagnostics or as_of.
            # ToolRuntime caches this payload intact, including this timestamp.
            now = utc_now() if utc_now is not None else datetime.now(timezone.utc)
            if not isinstance(now, datetime) or now.utcoffset() is None:
                raise ValueError("knowledge retrieval clock must return an aware datetime")
            payload["retrieved_at"] = now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        return payload

    nullable_string = {"type": ["string", "null"]}
    chunk_schema = {
        "type": "object",
        "properties": {
            "chunk_id": {"type": "string"},
            "parent_id": nullable_string,
            "source_id": {"type": "string"},
            "title": {"type": "string"},
            "content": {"type": "string"},
            "matched_content": nullable_string,
            "score": {"type": "number"},
            "rank": {"type": "integer", "minimum": 1},
            "knowledge_type": {"type": "string"},
            "version": nullable_string,
            "updated_at": nullable_string,
            "valid_from": nullable_string,
            "valid_until": nullable_string,
            "positions": {
                "type": "array",
                "items": {"type": "string"},
            },
            "attributes": {"type": "object"},
        },
        "required": [
            "chunk_id",
            "parent_id",
            "source_id",
            "title",
            "content",
            "matched_content",
            "score",
            "rank",
            "knowledge_type",
            "version",
            "updated_at",
            "valid_from",
            "valid_until",
            "positions",
            "attributes",
        ],
        "additionalProperties": False,
    }
    return (
        ToolDefinition(
            name="knowledge.search",
            version="2.1.0" if include_retrieval_time else "2.0.0",
            description="Search attributable RiftCoach coaching knowledge.",
            handler=search_handler,
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "minLength": 1},
                    "top_k": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 20,
                    },
                    "filters": {
                        "type": "object",
                        "properties": {
                            "version": {"type": "string"},
                            "position": {"type": "string"},
                            "as_of": {
                                "type": "string",
                                "pattern": r"^\d{4}-\d{2}-\d{2}$",
                            },
                        },
                        "additionalProperties": False,
                    },
                },
                "required": ["query", "top_k"],
                "additionalProperties": False,
            },
            output_schema={
                "type": "object",
                "properties": {
                    "provider": {"type": "string"},
                    "abstained": {"type": "boolean"},
                    "diagnostics": {"type": "object"},
                    "chunks": {
                        "type": "array",
                        "items": chunk_schema,
                    },
                    "count": {"type": "integer", "minimum": 0},
                    **({"retrieved_at": {
                        "type": "string", "format": "date-time",
                        "description": "Host UTC search completion time; retained on cache hits. Not document updated_at or another source's retrieval time.",
                    }} if include_retrieval_time else {}),
                },
                "required": [
                    "provider",
                    "abstained",
                    "diagnostics",
                    "chunks",
                    "count",
                    *(["retrieved_at"] if include_retrieval_time else []),
                ],
                "additionalProperties": False,
            },
            policy=ToolPolicy(cache=CachePolicy(ttl_s=300.0)),
        ),
    )


def _serialize_hit(hit) -> dict[str, Any]:
    metadata = hit.metadata
    return {
        "chunk_id": hit.chunk_id,
        "parent_id": hit.parent_id,
        "source_id": metadata.source_id,
        "title": metadata.title,
        "content": hit.content,
        "matched_content": hit.matched_content,
        "score": hit.score,
        "rank": hit.rank,
        "knowledge_type": metadata.knowledge_type,
        "version": metadata.version,
        "updated_at": _date_text(metadata.updated_at),
        "valid_from": _date_text(metadata.valid_from),
        "valid_until": _date_text(metadata.valid_until),
        "positions": list(metadata.positions),
        "attributes": dict(metadata.attributes),
    }


def _date_text(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None
