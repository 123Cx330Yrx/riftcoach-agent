"""Factories exposing existing RiftCoach capabilities as local tools."""

from __future__ import annotations

from typing import Any

from ..registry import ToolRegistry
from .data_dragon import build_data_dragon_tools
from .knowledge import build_knowledge_tools
from .llm import build_llm_tools
from .riot import build_riot_tools


def register_riftcoach_tools(
    registry: ToolRegistry,
    *,
    riot_client: Any,
    data_dragon: Any,
    retriever: Any,
    llm_provider: Any,
) -> None:
    definitions = (
        *build_riot_tools(riot_client),
        *build_data_dragon_tools(data_dragon),
        *build_knowledge_tools(retriever),
        *build_llm_tools(llm_provider),
    )
    for definition in definitions:
        registry.register(definition)


__all__ = [
    "build_data_dragon_tools",
    "build_knowledge_tools",
    "build_llm_tools",
    "build_riot_tools",
    "register_riftcoach_tools",
]
