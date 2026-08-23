"""Typed external Meta evidence and source-specific adapters."""

from .models import (
    LaneMetaChampionFact,
    MetaEvidence,
    MetaProvenance,
    MetaUseCase,
)
from .opgg import (
    OPGG_LANE_META_LOCAL_TOOL,
    OPGG_LANE_META_REMOTE_TOOL,
    OPGGMetaSchemaDiagnostic,
    OPGGLaneMetaAdapter,
    OPGGMetaError,
)

__all__ = [
    "LaneMetaChampionFact",
    "MetaEvidence",
    "MetaProvenance",
    "MetaUseCase",
    "OPGG_LANE_META_LOCAL_TOOL",
    "OPGG_LANE_META_REMOTE_TOOL",
    "OPGGMetaSchemaDiagnostic",
    "OPGGLaneMetaAdapter",
    "OPGGMetaError",
]
