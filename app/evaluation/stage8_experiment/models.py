"""Strict, body-free contracts for the Stage 8 three-path experiment."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


SafeCode = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z][a-z0-9._-]{0,127}$"),
]
Sha256Text = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
GitShaText = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
ToolName = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z][a-z0-9_.]{0,127}$"),
]


class ExperimentSplit(str, Enum):
    DEVELOPMENT = "development"
    HOLDOUT = "holdout"


class StrategyId(str, Enum):
    SERIAL = "single-runtime-serial-v1"
    BOUNDED_PARALLEL = "bounded-parallel-evidence-v1"
    ROLE_ISOLATED_MULTI_AGENT = "role-isolated-multi-agent-v1"


class ArtifactReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    artifact_kind: Literal["knowledge_evidence", "meta_evidence"]
    producer_role: SafeCode
    tool_name: ToolName
    payload_sha256: Sha256Text
    provenance_sha256: Sha256Text
    context_sha256: Sha256Text


class RoleContextReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    role_id: SafeCode
    context_sha256: Sha256Text
    allowed_tools: tuple[ToolName, ...]
    can_publish: bool


class HardGateCounters(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    unauthorized_tool_calls: int = Field(ge=0)
    cross_role_context_leaks: int = Field(ge=0)
    unprovenanced_evidence: int = Field(ge=0)
    unsafe_publications: int = Field(ge=0)
    terminal_identity_mismatches: int = Field(ge=0)
    real_external_io_calls: int = Field(ge=0)
    result_overwrites: int = Field(ge=0)
    experiment_identity_drifts: int = Field(ge=0)

    @property
    def total(self) -> int:
        return sum(
            (
                self.unauthorized_tool_calls,
                self.cross_role_context_leaks,
                self.unprovenanced_evidence,
                self.unsafe_publications,
                self.terminal_identity_mismatches,
                self.real_external_io_calls,
                self.result_overwrites,
                self.experiment_identity_drifts,
            )
        )


class ExperimentCaseResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    case_id: SafeCode
    strategy_id: StrategyId
    expected_terminal: Literal["published", "degraded", "failed"]
    terminal_status: Literal["published", "degraded", "failed"]
    terminal_matches_expected: bool
    error_code: SafeCode | None = None
    preserved_artifacts: tuple[ArtifactReference, ...]
    role_contexts: tuple[RoleContextReference, ...]
    independent_contexts: bool
    modeled_latency_units: int = Field(gt=0)
    token_units: int = Field(ge=0)
    provider_calls: int = Field(ge=0)
    harness_status: Literal["published", "degraded", "rejected"] | None
    harness_decision: Literal["published", "deterministic_fallback", "rejected"] | None
    final_artifact_sha256: Sha256Text | None = None
    hard_gates: HardGateCounters

    @model_validator(mode="after")
    def validate_terminal(self) -> "ExperimentCaseResult":
        expected_match = self.terminal_status == self.expected_terminal
        if self.terminal_matches_expected is not expected_match:
            raise ValueError("terminal match flag is inconsistent")
        if self.terminal_status == "failed":
            if self.harness_status is not None or self.harness_decision is not None:
                raise ValueError("pre-Harness failure cannot claim a Harness terminal")
            if self.final_artifact_sha256 is not None:
                raise ValueError("failed case cannot reference a final artifact")
        elif self.harness_status != self.terminal_status:
            raise ValueError("Harness and experiment terminal status must match")
        if self.hard_gates.total != 0:
            raise ValueError("persisted experiment case cannot contain a hard-gate breach")
        return self


class StrategyMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    strategy_id: StrategyId
    harness_decision_match_rate: float = Field(ge=0.0, le=1.0)
    safe_degraded_rate: float = Field(ge=0.0, le=1.0)
    failure_isolation_rate: float = Field(ge=0.0, le=1.0)
    modeled_latency_units: int = Field(gt=0)
    modeled_latency_improvement_ratio: float = Field(ge=0.0, le=1.0)
    total_token_units: int = Field(ge=0)
    total_token_ratio: float = Field(ge=0.0)
    total_provider_calls: int = Field(ge=0)
    max_extra_provider_calls_per_case: int = Field(ge=0)
    hard_gate_total: Literal[0] = 0


class ExperimentRecord(BaseModel):
    """Persistable evidence containing identity and metrics, never case bodies."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["1.0"] = "1.0"
    experiment_id: Sha256Text
    split: ExperimentSplit
    code_sha: GitShaText
    public_ci_sha: GitShaText | None = None
    gate_digest: Sha256Text
    case_set_sha256: Sha256Text
    input_fixture_sha256s: tuple[Sha256Text, Sha256Text]
    strategy_ids: tuple[StrategyId, StrategyId, StrategyId]
    cases: tuple[ExperimentCaseResult, ...]
    metrics: tuple[StrategyMetrics, StrategyMetrics, StrategyMetrics]
    verdict: Literal["eligible_for_holdout", "reject_multi_agent"]
    reason_codes: tuple[SafeCode, ...] = Field(min_length=1, max_length=8)
    external_io_calls: Literal[0] = 0
    retry_count: Literal[0] = 0
    holdout_executions: Literal[0, 1]

    @model_validator(mode="after")
    def validate_composition(self) -> "ExperimentRecord":
        expected_strategies = tuple(StrategyId)
        if self.strategy_ids != expected_strategies:
            raise ValueError("experiment strategies must keep their frozen order")
        if tuple(row.strategy_id for row in self.metrics) != expected_strategies:
            raise ValueError("strategy metrics must keep their frozen order")
        case_strategies: dict[str, set[StrategyId]] = {}
        for row in self.cases:
            case_strategies.setdefault(row.case_id, set()).add(row.strategy_id)
        if not case_strategies or any(
            strategies != set(expected_strategies)
            for strategies in case_strategies.values()
        ):
            raise ValueError("every case must execute all frozen strategies")
        if self.split is ExperimentSplit.DEVELOPMENT:
            if self.public_ci_sha is not None or self.holdout_executions != 0:
                raise ValueError("development cannot claim holdout or public-CI execution")
        elif self.public_ci_sha != self.code_sha or self.holdout_executions != 1:
            raise ValueError("holdout must bind one execution to its public-CI SHA")
        return self


class HoldoutAdmission(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["1.0"] = "1.0"
    admission_id: Sha256Text
    holdout_experiment_id: Sha256Text
    development_experiment_id: Sha256Text
    code_sha: GitShaText
    public_ci_sha: GitShaText
    gate_digest: Sha256Text
    case_set_sha256: Sha256Text
    external_io_calls: Literal[0] = 0
    holdout_executions: Literal[0] = 0


__all__ = [
    "ArtifactReference",
    "ExperimentCaseResult",
    "ExperimentRecord",
    "ExperimentSplit",
    "HardGateCounters",
    "HoldoutAdmission",
    "RoleContextReference",
    "StrategyId",
    "StrategyMetrics",
]
