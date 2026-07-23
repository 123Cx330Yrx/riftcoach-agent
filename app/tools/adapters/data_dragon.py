"""Tool adapter for local Data Dragon static lookups."""

from __future__ import annotations

from typing import Any, Mapping

from ..models import CachePolicy, ToolContext, ToolDefinition, ToolPolicy


def build_data_dragon_tools(service: Any) -> tuple[ToolDefinition, ...]:
    lookup_methods = {
        "champion": service.get_champion_official_name,
        "item": service.get_item_name,
        "summoner_spell": service.get_summoner_spell_name,
        "rune": service.get_rune_name,
    }

    def lookup_handler(
        params: Mapping[str, Any],
        context: ToolContext,
    ) -> Mapping[str, Any]:
        entity_type = params["entity_type"]
        entity_id = params["entity_id"]
        return {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "official_name": lookup_methods[entity_type](entity_id),
            "version": service.version,
            "language": service.language,
        }

    return (
        ToolDefinition(
            name="data_dragon.lookup_name",
            version="1.0.0",
            description="Resolve a LoL static entity ID to its official name.",
            handler=lookup_handler,
            input_schema={
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "enum": [
                            "champion",
                            "item",
                            "summoner_spell",
                            "rune",
                        ],
                    },
                    "entity_id": {"type": "integer", "minimum": 1},
                },
                "required": ["entity_type", "entity_id"],
                "additionalProperties": False,
            },
            output_schema={
                "type": "object",
                "properties": {
                    "entity_type": {"type": "string"},
                    "entity_id": {"type": "integer"},
                    "official_name": {"type": "string"},
                    "version": {"type": "string"},
                    "language": {"type": "string"},
                },
                "required": [
                    "entity_type",
                    "entity_id",
                    "official_name",
                    "version",
                    "language",
                ],
                "additionalProperties": False,
            },
            policy=ToolPolicy(cache=CachePolicy(ttl_s=86_400.0)),
        ),
    )
