"""Project-local Skill contracts and loading primitives."""

from .catalog import SkillCatalog, SkillCatalogError
from .loader import (
    LoadedSkill,
    SkillContractError,
    load_skill,
    validate_skill_tools,
)
from .models import (
    SkillBudgets,
    SkillManifest,
    SkillModelReferences,
    SkillPermissions,
    SkillQualityGate,
    SkillTriggerGroup,
    SkillTriggers,
)
from .router import DeterministicSkillRouter
from .routing_models import (
    RouteEvidence,
    RouteOutcome,
    RouteReason,
    RouterDecision,
    RouterRequest,
    SkillRouteCandidate,
)

__all__ = [
    "DeterministicSkillRouter",
    "LoadedSkill",
    "RouteEvidence",
    "RouteOutcome",
    "RouteReason",
    "RouterDecision",
    "RouterRequest",
    "SkillBudgets",
    "SkillCatalog",
    "SkillCatalogError",
    "SkillContractError",
    "SkillManifest",
    "SkillModelReferences",
    "SkillPermissions",
    "SkillQualityGate",
    "SkillRouteCandidate",
    "SkillTriggerGroup",
    "SkillTriggers",
    "load_skill",
    "validate_skill_tools",
]
