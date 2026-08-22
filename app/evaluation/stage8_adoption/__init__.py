"""Public contracts for the offline Stage 8 advanced adoption gate."""

from .gate import AdoptionGateError, evaluate_adoption_gate, load_adoption_gate
from .models import (
    AdvancedAdoptionDecision,
    AdvancedAdoptionGate,
    CandidateOutcome,
    LoadedAdoptionGate,
)

__all__ = [
    "AdoptionGateError",
    "AdvancedAdoptionDecision",
    "AdvancedAdoptionGate",
    "CandidateOutcome",
    "LoadedAdoptionGate",
    "evaluate_adoption_gate",
    "load_adoption_gate",
]
