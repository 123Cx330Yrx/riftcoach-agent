"""Deterministic runtime primitives for RiftCoach review workflows."""

from .models import ArtifactKind, HarnessConfig, RunManifest, RunStatus
from .store import ArtifactIntegrityError, FileRunStore
from .state_machine import (
    ALLOWED_TRANSITIONS,
    IllegalTransitionError,
    StaleAttemptError,
    advance,
)

__all__ = [
    "ArtifactKind",
    "ArtifactIntegrityError",
    "ALLOWED_TRANSITIONS",
    "FileRunStore",
    "HarnessConfig",
    "RunManifest",
    "RunStatus",
    "IllegalTransitionError",
    "StaleAttemptError",
    "advance",
]
