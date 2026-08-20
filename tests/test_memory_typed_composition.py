from __future__ import annotations

import pytest

from app.memory.composition import build_typed_memory_materializers
from app.memory.models import CandidateKind
from app.memory.typed_materializers import (
    OwnerPreferenceMaterializer,
    PlayerProfileMaterializer,
    ReviewMemoryMaterializer,
)
from app.memory.training_materializers import (
    TrainingPlanMaterializer,
    TrainingProgressMaterializer,
)


def test_production_typed_materializer_registry_is_complete_and_immutable() -> None:
    registry = build_typed_memory_materializers()
    assert set(registry) == {
        CandidateKind.OWNER_PREFERENCE,
        CandidateKind.PLAYER_PROFILE,
        CandidateKind.REVIEW_MEMORY,
        CandidateKind.TRAINING_PLAN,
        CandidateKind.TRAINING_PROGRESS,
    }
    assert isinstance(registry[CandidateKind.OWNER_PREFERENCE], OwnerPreferenceMaterializer)
    assert isinstance(registry[CandidateKind.PLAYER_PROFILE], PlayerProfileMaterializer)
    assert isinstance(registry[CandidateKind.REVIEW_MEMORY], ReviewMemoryMaterializer)
    assert isinstance(registry[CandidateKind.TRAINING_PLAN], TrainingPlanMaterializer)
    assert isinstance(registry[CandidateKind.TRAINING_PROGRESS], TrainingProgressMaterializer)
    with pytest.raises(TypeError):
        registry[CandidateKind.TRAINING_PLAN] = registry[CandidateKind.OWNER_PREFERENCE]


def test_materializer_registry_build_is_side_effect_free(monkeypatch) -> None:
    def forbidden(*args, **kwargs):
        del args, kwargs
        raise AssertionError("registry composition must not open a database or read environment")

    monkeypatch.setattr("os.getenv", forbidden)
    registry = build_typed_memory_materializers()
    assert len(registry) == 5
