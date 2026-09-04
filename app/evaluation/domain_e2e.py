"""Deterministic layered evaluation for recorded domain-Agent observations."""

from __future__ import annotations

from datetime import date
from enum import Enum
from pathlib import Path
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)


NonBlankText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Sha256Text = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
SafeCodeText = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Za-z][A-Za-z0-9_.:-]*$"),
]
SafeRuntimeCodeText = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z][a-z0-9_]{0,127}$"),
]
_CASE_MAX_CALLS = 4


def _omit_empty_evidence_diagnostics(value: object) -> bool:
    return (
        getattr(value, "search_calls", None) == 0
        and getattr(value, "successful_search_calls", None) == 0
        and getattr(value, "payloads_with_data", None) == 0
        and getattr(value, "chunks_returned", None) == 0
        and getattr(value, "source_count", None) == 0
        and getattr(value, "artifact_present", None) is None
        and getattr(value, "abstained", None) is None
        and getattr(value, "reason", None) is None
    )

DomainSchemaVersion = Literal["1.1", "1.2"]
DomainCandidateKind = Literal[
    "offline_recorded",
    "offline_executable",
    "real_provider_recorded",
]


class DomainDatasetRole(str, Enum):
    DEVELOPMENT = "development"
    HELD_OUT = "held_out"


class LayerVerdict(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class FailureCode(str, Enum):
    PROVIDER_RESPONSE_UNAVAILABLE = "provider_response_unavailable"
    AGENT_NOT_COMPLETED = "agent_not_completed"
    TOOL_SELECTION_MISSING = "tool_selection_missing"
    TOOL_EXECUTION_INCOMPLETE = "tool_execution_incomplete"
    EVIDENCE_MISSING = "evidence_missing"
    INJECTION_RESISTANCE_FAILED = "injection_resistance_failed"
    FACT_CHECK_FAILED = "fact_check_failed"
    CITATION_CHECK_FAILED = "citation_check_failed"
    EVALUATION_UNAVAILABLE = "evaluation_unavailable"
    QUALITY_GATE_FAILED = "quality_gate_failed"
    TERMINAL_STATUS_MISMATCH = "terminal_status_mismatch"
    RESOURCE_LIMIT_EXCEEDED = "resource_limit_exceeded"
    UNSAFE_PUBLICATION = "unsafe_publication"


class ContractSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    skill_name: NonBlankText
    skill_version: NonBlankText
    context_contract: NonBlankText
    evaluation_contract: NonBlankText
    prompt_context_snapshot_id: NonBlankText
    prompt_context_snapshot_sha256: Sha256Text


class DomainCaseRequirements(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    minimum_normalized_responses: int = Field(ge=0)
    expected_agent_status: Literal["completed", "stopped", "failed"] | None
    expected_agent_stop_reason: SafeCodeText | None
    required_tool_names: tuple[NonBlankText, ...]
    minimum_successful_tool_executions: int = Field(ge=0)
    minimum_evidence_sources: int = Field(ge=0)
    require_fact_check: bool
    require_citation_check: bool
    require_injection_check: bool
    require_validated_evaluation: bool
    minimum_evaluation_score: int | None = Field(default=None, ge=0, le=100)
    allowed_terminal_statuses: tuple[
        Literal["published", "degraded", "rejected"], ...
    ]
    maximum_provider_calls: int | None = Field(default=None, ge=0)
    maximum_latency_ms: int | None = Field(default=None, ge=0)
    maximum_total_tokens: int | None = Field(default=None, ge=0)
    maximum_estimated_cost: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_requirements(self) -> "DomainCaseRequirements":
        if len(set(self.required_tool_names)) != len(self.required_tool_names):
            raise ValueError("required tool names must be unique")
        if not self.allowed_terminal_statuses:
            raise ValueError("allowed terminal statuses must not be empty")
        if len(set(self.allowed_terminal_statuses)) != len(
            self.allowed_terminal_statuses
        ):
            raise ValueError("allowed terminal statuses must be unique")
        if (
            self.minimum_evaluation_score is not None
            and not self.require_validated_evaluation
        ):
            raise ValueError(
                "minimum evaluation score requires validated evaluation"
            )
        return self


class EvidenceDiagnostics(BaseModel):
    """Body-free retrieval counters for diagnosing an evidence gate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    search_calls: int = Field(ge=0, le=_CASE_MAX_CALLS, default=0)
    successful_search_calls: int = Field(ge=0, le=_CASE_MAX_CALLS, default=0)
    payloads_with_data: int = Field(ge=0, le=_CASE_MAX_CALLS, default=0)
    chunks_returned: int = Field(ge=0, default=0)
    source_count: int = Field(ge=0, default=0)
    artifact_present: bool | None = None
    abstained: bool | None = None
    reason: SafeRuntimeCodeText | None = None

    @model_validator(mode="after")
    def validate_counts(self) -> "EvidenceDiagnostics":
        if self.successful_search_calls > self.search_calls:
            raise ValueError("successful search calls cannot exceed search calls")
        if self.payloads_with_data > self.successful_search_calls:
            raise ValueError("payloads with data cannot exceed successful searches")
        if self.source_count > self.chunks_returned:
            raise ValueError("source count cannot exceed returned chunks")
        return self


class DomainEvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: NonBlankText
    category: NonBlankText
    expect_task_success: bool
    expected_primary_failure: FailureCode | None
    requirements: DomainCaseRequirements
    contamination_sources: tuple[NonBlankText, ...]

    @model_validator(mode="after")
    def validate_expected_outcome(self) -> "DomainEvaluationCase":
        if self.expect_task_success is (self.expected_primary_failure is not None):
            raise ValueError(
                "successful cases cannot expect a failure and failed cases must"
                " name a primary failure"
            )
        if len(set(self.contamination_sources)) != len(
            self.contamination_sources
        ):
            raise ValueError("contamination sources must be unique")
        return self


class DomainEvaluationDataset(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: DomainSchemaVersion = "1.1"
    dataset_id: NonBlankText
    dataset_version: NonBlankText
    role: DomainDatasetRole
    calibration_excluded: bool
    created_at: NonBlankText
    case_count: int = Field(gt=0)
    contract_snapshot: ContractSnapshot
    contamination_notes: tuple[NonBlankText, ...]
    lifecycle_policy: NonBlankText
    cases: tuple[DomainEvaluationCase, ...]

    @model_validator(mode="after")
    def validate_lifecycle(self) -> "DomainEvaluationDataset":
        try:
            date.fromisoformat(self.created_at)
        except ValueError as exc:
            raise ValueError("created_at must be an ISO date") from exc
        if self.case_count != len(self.cases):
            raise ValueError("case_count does not match cases")
        case_ids = tuple(case.case_id for case in self.cases)
        if len(set(case_ids)) != len(case_ids):
            raise ValueError("case IDs must be unique")
        if self.role is DomainDatasetRole.DEVELOPMENT:
            if self.calibration_excluded:
                raise ValueError(
                    "development dataset cannot be calibration-excluded"
                )
            if not self.contamination_notes:
                raise ValueError("development dataset must describe contamination")
        else:
            if not self.calibration_excluded:
                raise ValueError("held-out dataset must be calibration-excluded")
            if self.contamination_notes:
                raise ValueError("held-out dataset cannot contain contamination notes")
            if any(case.contamination_sources for case in self.cases):
                raise ValueError(
                    "held-out cases cannot contain contamination sources"
                )
        return self


class DomainCandidateCase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: NonBlankText
    provider_calls: int = Field(ge=0)
    normalized_response_count: int = Field(ge=0)
    safe_provider_error_code: SafeCodeText | None
    agent_status: Literal["completed", "stopped", "failed"] | None
    agent_stop_reason: SafeCodeText | None
    proposed_tool_names: tuple[NonBlankText, ...]
    successful_tool_names: tuple[NonBlankText, ...]
    evidence_source_ids: tuple[NonBlankText, ...]
    evidence_diagnostics: EvidenceDiagnostics = Field(
        default_factory=EvidenceDiagnostics,
        exclude_if=_omit_empty_evidence_diagnostics,
    )
    fact_check_passed: bool | None
    citation_check_passed: bool | None
    injection_check_passed: bool | None
    evaluation_validated: bool
    evaluation_score: int | None = Field(default=None, ge=0, le=100)
    terminal_status: Literal["published", "degraded", "rejected"] | None
    terminal_reason: SafeCodeText | None
    latency_ms: int | None = Field(default=None, ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    estimated_cost: float | None = Field(default=None, ge=0)
    provenance_sha256: Sha256Text | None

    @model_validator(mode="after")
    def validate_observation(self) -> "DomainCandidateCase":
        if self.normalized_response_count > self.provider_calls:
            raise ValueError("normalized responses cannot outnumber Provider calls")
        for label, values in (
            ("proposed tools", self.proposed_tool_names),
            ("successful tools", self.successful_tool_names),
            ("evidence sources", self.evidence_source_ids),
        ):
            if len(set(values)) != len(values):
                raise ValueError(f"{label} must be unique")
        if not set(self.successful_tool_names).issubset(
            set(self.proposed_tool_names)
        ):
            raise ValueError("successful tools must have been proposed")
        if self.evaluation_validated is not (self.evaluation_score is not None):
            raise ValueError(
                "validated evaluation and evaluation score must appear together"
            )
        if self.terminal_status is None and self.terminal_reason is not None:
            raise ValueError("terminal reason requires a terminal status")
        return self


class DomainCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: DomainSchemaVersion = "1.1"
    candidate_id: NonBlankText
    candidate_kind: DomainCandidateKind
    dataset_id: NonBlankText
    dataset_version: NonBlankText
    contract_snapshot: ContractSnapshot
    external_provider_calls: int = Field(ge=0)
    case_count: int = Field(gt=0)
    cases: tuple[DomainCandidateCase, ...]

    @model_validator(mode="after")
    def validate_cases(self) -> "DomainCandidate":
        if self.case_count != len(self.cases):
            raise ValueError("candidate case_count does not match cases")
        case_ids = tuple(case.case_id for case in self.cases)
        if len(set(case_ids)) != len(case_ids):
            raise ValueError("candidate case IDs must be unique")
        if self.candidate_kind.startswith("offline_") and self.external_provider_calls:
            raise ValueError(
                "offline candidate cannot make external Provider calls"
            )
        if self.candidate_kind == "offline_executable" and any(
            row.provenance_sha256 is None for row in self.cases
        ):
            raise ValueError(
                "offline executable cases require provenance_sha256"
            )
        if (
            self.candidate_kind == "offline_executable"
            and self.schema_version != "1.2"
        ):
            raise ValueError(
                "offline executable candidates require schema version 1.2"
            )
        return self


class LayerResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    verdict: LayerVerdict
    failure_codes: tuple[FailureCode, ...] = ()

    @model_validator(mode="after")
    def validate_failures(self) -> "LayerResult":
        if self.verdict is LayerVerdict.FAIL and not self.failure_codes:
            raise ValueError("failed layer requires a failure code")
        if self.verdict is not LayerVerdict.FAIL and self.failure_codes:
            raise ValueError("non-failed layer cannot contain failure codes")
        return self


class LayeredCaseResults(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider_agent: LayerResult
    tool: LayerResult
    evidence: LayerResult
    evaluation: LayerResult
    terminal: LayerResult
    resources: LayerResult


class DomainCaseResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: NonBlankText
    category: NonBlankText
    expected_task_success: bool
    task_succeeded: bool
    task_outcome_match: bool
    expected_primary_failure: FailureCode | None
    primary_failure: FailureCode | None
    failure_classification_match: bool
    failure_codes: tuple[FailureCode, ...]
    unsafe_publication: bool
    layers: LayeredCaseResults


class DomainEvaluationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: DomainSchemaVersion = "1.1"
    dataset_id: NonBlankText
    dataset_version: NonBlankText
    dataset_role: DomainDatasetRole
    calibration_excluded: bool
    candidate_id: NonBlankText
    candidate_kind: DomainCandidateKind
    contract_snapshot: ContractSnapshot
    external_provider_calls: int = Field(ge=0)
    case_count: int = Field(gt=0)
    task_outcome_accuracy: float = Field(ge=0, le=1)
    failure_classification_accuracy: float = Field(ge=0, le=1)
    unsafe_publication_rate: float = Field(ge=0, le=1)
    cases: tuple[DomainCaseResult, ...]


def load_domain_dataset(path: str | Path) -> DomainEvaluationDataset:
    return DomainEvaluationDataset.model_validate_json(Path(path).read_bytes())


def load_domain_candidate(path: str | Path) -> DomainCandidate:
    return DomainCandidate.model_validate_json(Path(path).read_bytes())


def validate_domain_dataset_usage(
    dataset: DomainEvaluationDataset,
    expected_role: DomainDatasetRole,
    *,
    confirm_rules_frozen: bool = False,
) -> None:
    if dataset.role is not expected_role:
        raise ValueError(
            f"dataset role is {dataset.role.value}, expected {expected_role.value}"
        )
    if (
        expected_role is DomainDatasetRole.HELD_OUT
        and not confirm_rules_frozen
    ):
        raise ValueError(
            "held-out evaluation requires explicit confirmation that rules are frozen"
        )


def evaluate_domain_candidate(
    dataset: DomainEvaluationDataset,
    candidate: DomainCandidate,
) -> DomainEvaluationResult:
    if candidate.schema_version != dataset.schema_version:
        raise ValueError("candidate and dataset schema version mismatch")
    if (candidate.dataset_id, candidate.dataset_version) != (
        dataset.dataset_id,
        dataset.dataset_version,
    ):
        raise ValueError("candidate dataset identity mismatch")
    if candidate.contract_snapshot != dataset.contract_snapshot:
        raise ValueError("candidate contract snapshot mismatch")

    expected = {case.case_id: case for case in dataset.cases}
    observed = {case.case_id: case for case in candidate.cases}
    if observed.keys() != expected.keys():
        raise ValueError("candidate case set does not match dataset")

    results = tuple(
        _evaluate_case(case, observed[case.case_id]) for case in dataset.cases
    )
    return DomainEvaluationResult(
        schema_version=dataset.schema_version,
        dataset_id=dataset.dataset_id,
        dataset_version=dataset.dataset_version,
        dataset_role=dataset.role,
        calibration_excluded=dataset.calibration_excluded,
        candidate_id=candidate.candidate_id,
        candidate_kind=candidate.candidate_kind,
        contract_snapshot=dataset.contract_snapshot,
        external_provider_calls=candidate.external_provider_calls,
        case_count=len(results),
        task_outcome_accuracy=_mean(row.task_outcome_match for row in results),
        failure_classification_accuracy=_mean(
            row.failure_classification_match for row in results
        ),
        unsafe_publication_rate=_mean(
            row.unsafe_publication for row in results
        ),
        cases=results,
    )


def _evaluate_case(
    case: DomainEvaluationCase,
    observed: DomainCandidateCase,
) -> DomainCaseResult:
    requirements = case.requirements
    provider_agent = _provider_agent_layer(requirements, observed)
    tool = _tool_layer(requirements, observed, provider_agent)
    evidence = _evidence_layer(requirements, observed, tool)
    evaluation = _evaluation_layer(requirements, observed, evidence)
    functional_layers = (provider_agent, tool, evidence, evaluation)
    terminal = _terminal_layer(requirements, observed, functional_layers)
    resources = _resource_layer(requirements, observed)
    layers = LayeredCaseResults(
        provider_agent=provider_agent,
        tool=tool,
        evidence=evidence,
        evaluation=evaluation,
        terminal=terminal,
        resources=resources,
    )
    failure_codes = _ordered_unique_failures(layers)
    primary_failure = failure_codes[0] if failure_codes else None
    task_succeeded = all(
        layer.verdict in {LayerVerdict.PASS, LayerVerdict.NOT_APPLICABLE}
        for layer in (*functional_layers, terminal)
    ) and resources.verdict is not LayerVerdict.FAIL
    unsafe_publication = FailureCode.UNSAFE_PUBLICATION in failure_codes
    return DomainCaseResult(
        case_id=case.case_id,
        category=case.category,
        expected_task_success=case.expect_task_success,
        task_succeeded=task_succeeded,
        task_outcome_match=task_succeeded is case.expect_task_success,
        expected_primary_failure=case.expected_primary_failure,
        primary_failure=primary_failure,
        failure_classification_match=(
            primary_failure is case.expected_primary_failure
        ),
        failure_codes=failure_codes,
        unsafe_publication=unsafe_publication,
        layers=layers,
    )


def _provider_agent_layer(
    requirements: DomainCaseRequirements,
    observed: DomainCandidateCase,
) -> LayerResult:
    if (
        requirements.minimum_normalized_responses == 0
        and requirements.expected_agent_status is None
        and requirements.expected_agent_stop_reason is None
    ):
        return LayerResult(verdict=LayerVerdict.NOT_APPLICABLE)
    failures = []
    if (
        observed.normalized_response_count
        < requirements.minimum_normalized_responses
    ):
        failures.append(FailureCode.PROVIDER_RESPONSE_UNAVAILABLE)
    elif (
        observed.agent_status is None
        or observed.agent_stop_reason is None
        or (
            requirements.expected_agent_status is not None
            and observed.agent_status != requirements.expected_agent_status
        )
        or (
            requirements.expected_agent_stop_reason is not None
            and observed.agent_stop_reason
            != requirements.expected_agent_stop_reason
        )
    ):
        failures.append(FailureCode.AGENT_NOT_COMPLETED)
    return _pass_or_fail(failures)


def _tool_layer(
    requirements: DomainCaseRequirements,
    observed: DomainCandidateCase,
    prerequisite: LayerResult,
) -> LayerResult:
    if (
        not requirements.required_tool_names
        and requirements.minimum_successful_tool_executions == 0
    ):
        return LayerResult(verdict=LayerVerdict.NOT_APPLICABLE)
    if prerequisite.verdict is not LayerVerdict.PASS:
        return LayerResult(verdict=LayerVerdict.UNKNOWN)
    required = set(requirements.required_tool_names)
    proposed = set(observed.proposed_tool_names)
    successful = set(observed.successful_tool_names)
    failures = []
    if not required.issubset(proposed):
        failures.append(FailureCode.TOOL_SELECTION_MISSING)
    if (
        not required.issubset(successful)
        or len(observed.successful_tool_names)
        < requirements.minimum_successful_tool_executions
    ):
        failures.append(FailureCode.TOOL_EXECUTION_INCOMPLETE)
    return _pass_or_fail(failures)


def _evidence_layer(
    requirements: DomainCaseRequirements,
    observed: DomainCandidateCase,
    prerequisite: LayerResult,
) -> LayerResult:
    if requirements.minimum_evidence_sources == 0:
        return LayerResult(verdict=LayerVerdict.NOT_APPLICABLE)
    if prerequisite.verdict is not LayerVerdict.PASS:
        return LayerResult(verdict=LayerVerdict.UNKNOWN)
    if len(observed.evidence_source_ids) < requirements.minimum_evidence_sources:
        return LayerResult(
            verdict=LayerVerdict.FAIL,
            failure_codes=(FailureCode.EVIDENCE_MISSING,),
        )
    return LayerResult(verdict=LayerVerdict.PASS)


def _evaluation_layer(
    requirements: DomainCaseRequirements,
    observed: DomainCandidateCase,
    prerequisite: LayerResult,
) -> LayerResult:
    required = any(
        (
            requirements.require_fact_check,
            requirements.require_citation_check,
            requirements.require_injection_check,
            requirements.require_validated_evaluation,
            requirements.minimum_evaluation_score is not None,
        )
    )
    if not required:
        return LayerResult(verdict=LayerVerdict.NOT_APPLICABLE)
    if prerequisite.verdict is not LayerVerdict.PASS:
        return LayerResult(verdict=LayerVerdict.UNKNOWN)
    failures = []
    unknown = False
    for is_required, value, failure in (
        (
            requirements.require_injection_check,
            observed.injection_check_passed,
            FailureCode.INJECTION_RESISTANCE_FAILED,
        ),
        (
            requirements.require_fact_check,
            observed.fact_check_passed,
            FailureCode.FACT_CHECK_FAILED,
        ),
        (
            requirements.require_citation_check,
            observed.citation_check_passed,
            FailureCode.CITATION_CHECK_FAILED,
        ),
    ):
        if not is_required:
            continue
        if value is None:
            unknown = True
        elif not value:
            failures.append(failure)
    if requirements.require_validated_evaluation:
        if not observed.evaluation_validated:
            failures.append(FailureCode.EVALUATION_UNAVAILABLE)
        elif (
            requirements.minimum_evaluation_score is not None
            and observed.evaluation_score is not None
            and observed.evaluation_score
            < requirements.minimum_evaluation_score
        ):
            failures.append(FailureCode.QUALITY_GATE_FAILED)
    if failures:
        return LayerResult(
            verdict=LayerVerdict.FAIL,
            failure_codes=tuple(failures),
        )
    if unknown:
        return LayerResult(verdict=LayerVerdict.UNKNOWN)
    return LayerResult(verdict=LayerVerdict.PASS)


def _terminal_layer(
    requirements: DomainCaseRequirements,
    observed: DomainCandidateCase,
    functional_layers: tuple[LayerResult, ...],
) -> LayerResult:
    if observed.terminal_status is None:
        return LayerResult(verdict=LayerVerdict.UNKNOWN)
    failures = []
    if observed.terminal_status not in requirements.allowed_terminal_statuses:
        failures.append(FailureCode.TERMINAL_STATUS_MISMATCH)
    if observed.terminal_status == "published" and any(
        layer.verdict is not LayerVerdict.PASS
        for layer in functional_layers
        if layer.verdict is not LayerVerdict.NOT_APPLICABLE
    ):
        failures.append(FailureCode.UNSAFE_PUBLICATION)
    return _pass_or_fail(failures)


def _resource_layer(
    requirements: DomainCaseRequirements,
    observed: DomainCandidateCase,
) -> LayerResult:
    checks = []
    unknown = False
    if requirements.maximum_provider_calls is not None:
        checks.append(
            observed.provider_calls <= requirements.maximum_provider_calls
        )
    for maximum, value in (
        (requirements.maximum_latency_ms, observed.latency_ms),
        (
            requirements.maximum_total_tokens,
            None
            if observed.input_tokens is None or observed.output_tokens is None
            else observed.input_tokens + observed.output_tokens,
        ),
        (requirements.maximum_estimated_cost, observed.estimated_cost),
    ):
        if maximum is None:
            continue
        if value is None:
            unknown = True
        else:
            checks.append(value <= maximum)
    if not checks and not unknown:
        return LayerResult(verdict=LayerVerdict.NOT_APPLICABLE)
    if any(not passed for passed in checks):
        return LayerResult(
            verdict=LayerVerdict.FAIL,
            failure_codes=(FailureCode.RESOURCE_LIMIT_EXCEEDED,),
        )
    if unknown:
        return LayerResult(verdict=LayerVerdict.UNKNOWN)
    return LayerResult(verdict=LayerVerdict.PASS)


def _pass_or_fail(failures: list[FailureCode]) -> LayerResult:
    if failures:
        return LayerResult(
            verdict=LayerVerdict.FAIL,
            failure_codes=tuple(dict.fromkeys(failures)),
        )
    return LayerResult(verdict=LayerVerdict.PASS)


def _ordered_unique_failures(
    layers: LayeredCaseResults,
) -> tuple[FailureCode, ...]:
    ordered = []
    for layer in (
        layers.provider_agent,
        layers.tool,
        layers.evidence,
        layers.evaluation,
        layers.terminal,
        layers.resources,
    ):
        for failure in layer.failure_codes:
            if failure not in ordered:
                ordered.append(failure)
    return tuple(ordered)


def _mean(values) -> float:
    rows = tuple(bool(value) for value in values)
    return round(sum(rows) / len(rows), 6) if rows else 0.0


__all__ = [
    "ContractSnapshot",
    "DomainCandidate",
    "DomainDatasetRole",
    "DomainEvaluationDataset",
    "DomainEvaluationResult",
    "EvidenceDiagnostics",
    "FailureCode",
    "LayerVerdict",
    "evaluate_domain_candidate",
    "load_domain_candidate",
    "load_domain_dataset",
    "validate_domain_dataset_usage",
]
