"""Side-effect-free production composition for typed Memory materializers."""

from __future__ import annotations

from types import MappingProxyType

from app.memory.models import CandidateKind
from app.memory.ports import MaterializerRegistry
from app.memory.typed_materializers import (
    OwnerPreferenceMaterializer,
    PlayerProfileMaterializer,
    ReviewMemoryMaterializer,
)
from app.persistence.typed_memory_writer import PostgresTypedMemoryTargetWriter


def build_typed_memory_materializers() -> MaterializerRegistry:
    """Build the complete 6B-6 registry without opening a database connection."""

    writer = PostgresTypedMemoryTargetWriter()
    return MappingProxyType(
        {
            CandidateKind.OWNER_PREFERENCE: OwnerPreferenceMaterializer(writer),
            CandidateKind.PLAYER_PROFILE: PlayerProfileMaterializer(writer),
            CandidateKind.REVIEW_MEMORY: ReviewMemoryMaterializer(writer),
        }
    )


__all__ = ["build_typed_memory_materializers"]
