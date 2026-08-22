"""Strict, body-free contracts for the Stage 8 advanced adoption gate."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


SafeCode = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z][a-z0-9._-]{0,127}$"),
]
Sha256Text = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
GitShaText = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
NonBlankText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=512),
]


class CaseSplit(str, Enum):
    DEVELOPMENT = "development"
    HOLDOUT = "holdout"


class EvidenceLevel(str, Enum):
    OBSERVED = "observed"
    HYPOTHESIS = "hypothesis"


class ExpectedTerminal(str, Enum):
    PUBLISHED = "published"
    DEGRADED = "degraded"
    FAILED = "failed"


class CandidateDisposition(str, Enum):
    BASELINE = "baseline"
    EVALUATE = "evaluate"
    DEFERRED = "deferred"


class CandidateKind(str, Enum):
    SERIAL_BASELINE = "serial_baseline"
    BOUNDED_PARALLEL = "bounded_parallel"
    ROLE_ISOLATED_MULTI_AGENT = "role_isolated_multi_agent"
    THIRD_PARTY_DAG_RUNTIME = "third_party_dag_runtime"
    AGENTIC_RETRIEVAL = "agentic_retrieval"


class CandidateOutcome(str, Enum):
    BASELINE = "baseline"
    CANDIDATE = "candidate"
    DEFERRED = "deferred"


class CalibrationPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    development_may_shape_implementation: bool
    holdout_calibration_excluded: bool
    holdout_max_executions: int = Field(ge=0, le=1)
    holdout_result_overwrite_allowed: bool


class AdoptionCase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    case_id: SafeCode
    split: CaseSplit
    calibration_excluded: bool
    bad_case_id: Annotated[
        str,
        StringConstraints(pattern=r"^BC-8A-[0-9]{2}$"),
    ]
    evidence_level: EvidenceLevel
    scenario: NonBlankText = Field(repr=False)
    knowledge_latency_units: int = Field(gt=0, le=10_000)
    meta_latency_units: int = Field(gt=0, le=10_000)
    fault: SafeCode
    expected_terminal: ExpectedTerminal
    expected_preserved_artifacts: tuple[SafeCode, ...]
    expected_error_code: SafeCode | None = None


class AdoptionCaseSet(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["1.0"]
    case_set_id: SafeCode
    product_slice_id: SafeCode
    source_product_sha: GitShaText
    calibration_policy: CalibrationPolicy
    cases: tuple[AdoptionCase, ...] = Field(min_length=1, max_length=64)


class CaseSetReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    case_set_id: SafeCode
    path: Annotated[
        str,
        StringConstraints(
            pattern=r"^data/evaluation/stage8/[a-z0-9_./-]+\.json$",
        ),
    ]
    sha256: Sha256Text


class ComparisonContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    baseline_id: SafeCode
    primary_candidate_id: SafeCode
    comparator_ids: tuple[SafeCode, ...] = Field(min_length=1, max_length=4)
    skill_name: Literal["recent-form-review"]
    skill_version: Literal["0.2.0"]
    context_contract_version: Literal["1.0.0"]
    max_context_tokens: Literal[16000]
    harness_policy_id: SafeCode
    publish_score_threshold: Literal[85]
    input_fixture_sha256s: tuple[Sha256Text, ...] = Field(min_length=2, max_length=2)
    tool_fixture_ids: tuple[SafeCode, ...] = Field(min_length=2, max_length=2)
    external_io_budget: int = Field(ge=0)
    retry_budget: int = Field(ge=0)
    holdout_max_executions: int = Field(ge=0)
    result_overwrite_allowed: bool


class BenefitThresholds(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    min_harness_decision_match_rate: float = Field(ge=0.0, le=1.0)
    min_safe_degraded_rate: float = Field(ge=0.0, le=1.0)
    min_modeled_latency_improvement_ratio: float = Field(ge=0.0, le=1.0)
    max_total_token_ratio: float = Field(ge=1.0, le=10.0)
    max_extra_provider_calls: int = Field(ge=0, le=10)
    allow_failure_isolation_instead_of_latency: bool


class RoleContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    role_id: SafeCode
    context_scopes: tuple[SafeCode, ...] = Field(min_length=1, max_length=16)
    allowed_tools: tuple[SafeCode, ...] = Field(max_length=8)
    independent_context: bool
    can_publish: bool


class CandidateDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    candidate_id: SafeCode
    kind: CandidateKind
    disposition: CandidateDisposition
    target_bad_case_ids: tuple[
        Annotated[str, StringConstraints(pattern=r"^BC-8A-[0-9]{2}$")], ...
    ]
    roles: tuple[RoleContract, ...] = Field(max_length=8)
    expected_benefit_metrics: tuple[SafeCode, ...] = Field(max_length=16)
    deferred_reason_codes: tuple[SafeCode, ...] = Field(max_length=16)
    production_dependency_allowed: bool
    product_runtime_changes_allowed: bool


class AdvancedAdoptionGate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["1.0"]
    gate_id: SafeCode
    product_slice_id: SafeCode
    source_product_sha: GitShaText
    case_set: CaseSetReference
    comparison_contract: ComparisonContract
    hard_gate_metrics: tuple[SafeCode, ...] = Field(min_length=1, max_length=16)
    benefit_thresholds: BenefitThresholds
    stop_condition_codes: tuple[SafeCode, ...] = Field(min_length=1, max_length=32)
    candidates: tuple[CandidateDefinition, ...] = Field(min_length=3, max_length=12)


@dataclass(frozen=True)
class LoadedAdoptionGate:
    gate: AdvancedAdoptionGate
    case_set: AdoptionCaseSet
    gate_path: Path
    case_set_path: Path
    gate_file_sha256: str
    case_set_file_sha256: str


class CandidateDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    candidate_id: SafeCode
    outcome: CandidateOutcome
    reason_codes: tuple[SafeCode, ...] = Field(min_length=1, max_length=16)


class AdvancedAdoptionDecision(BaseModel):
    """Body-free result: identities and reason codes, never case contents."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["1.0"] = "1.0"
    gate_id: SafeCode
    gate_digest: Sha256Text
    case_set_sha256: Sha256Text
    baseline_id: SafeCode
    primary_candidate_id: SafeCode
    comparator_ids: tuple[SafeCode, ...]
    candidates: tuple[CandidateDecision, ...]
    external_io_calls: Literal[0] = 0
    holdout_executions: Literal[0] = 0
