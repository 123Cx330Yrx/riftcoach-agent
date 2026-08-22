"""Public API for the isolated Stage 8 conditional Multi-Agent experiment."""

from .lifecycle import (
    ImmutableExperimentOutput,
    load_experiment_record,
    prepare_holdout_admission,
    write_experiment_record_exclusive,
)
from .models import (
    ArtifactReference,
    ExperimentCaseResult,
    ExperimentRecord,
    ExperimentSplit,
    HardGateCounters,
    HoldoutAdmission,
    RoleContextReference,
    StrategyId,
    StrategyMetrics,
)
from .runner import (
    ExperimentViolation,
    build_experiment_id,
    build_holdout_admission_id,
    run_stage8_experiment,
    validate_experiment_record,
)

__all__ = [
    "ArtifactReference",
    "ExperimentCaseResult",
    "ExperimentRecord",
    "ExperimentSplit",
    "ExperimentViolation",
    "HardGateCounters",
    "HoldoutAdmission",
    "ImmutableExperimentOutput",
    "RoleContextReference",
    "StrategyId",
    "StrategyMetrics",
    "build_experiment_id",
    "build_holdout_admission_id",
    "load_experiment_record",
    "prepare_holdout_admission",
    "run_stage8_experiment",
    "validate_experiment_record",
    "write_experiment_record_exclusive",
]
