"""Tool adapter for the current lightweight local knowledge retriever."""

from __future__ import annotations

from typing import Any, Mapping

from ..models import CachePolicy, ToolContext, ToolDefinition, ToolPolicy


def build_knowledge_tools(retriever: Any) -> tuple[ToolDefinition, ...]:
    def search_handler(
        params: Mapping[str, Any],
        context: ToolContext,
    ) -> Mapping[str, Any]:
        chunks = retriever.search(params["query"], params["top_k"])
        rows = [
            {
                "source": chunk.source,
                "title": chunk.title,
                "content": chunk.content,
                "score": chunk.score,
            }
            for chunk in chunks
        ]
        return {"chunks": rows, "count": len(rows)}

    chunk_schema = {
        "type": "object",
        "properties": {
            "source": {"type": "string"},
            "title": {"type": "string"},
            "content": {"type": "string"},
            "score": {"type": "number"},
        },
        "required": ["source", "title", "content", "score"],
        "additionalProperties": False,
    }
    return (
        ToolDefinition(
            name="knowledge.search",
            version="1.0.0",
            description="Search local RiftCoach coaching knowledge.",
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
                },
                "required": ["query", "top_k"],
                "additionalProperties": False,
            },
            output_schema={
                "type": "object",
                "properties": {
                    "chunks": {
                        "type": "array",
                        "items": chunk_schema,
                    },
                    "count": {"type": "integer", "minimum": 0},
                },
                "required": ["chunks", "count"],
                "additionalProperties": False,
            },
            policy=ToolPolicy(cache=CachePolicy(ttl_s=300.0)),
        ),
    )
