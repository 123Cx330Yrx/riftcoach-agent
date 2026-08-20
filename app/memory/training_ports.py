from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.memory.models import MemoryCandidate
from app.memory.ports import MaterializationSession
from app.memory.training_models import (
    ParsedTrainingPlanWrite,
    ParsedTrainingProgressWrite,
)


class TrainingTargetWriter(Protocol):
    def write_plan(
        self,
        session: MaterializationSession,
        *,
        candidate: MemoryCandidate,
        parsed: ParsedTrainingPlanWrite,
    ) -> UUID: ...

    def write_progress(
        self,
        session: MaterializationSession,
        *,
        candidate: MemoryCandidate,
        parsed: ParsedTrainingProgressWrite,
    ) -> UUID: ...


__all__ = ["TrainingTargetWriter"]
