"""Offline-safe resource calibration for a future DeepSeek domain V3 gate.

This module deliberately separates three kinds of evidence:

* development request shapes assembled by the production Skill path;
* offline Fake-Provider usage simulations used to test control flow;
* a deterministic budget formula that a later real calibration may reuse.

No function in the no-I/O preparation path constructs a Provider or reads an
API key.  Full request bodies remain in an internal dataclass and never enter
the public Pydantic snapshots.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_CEILING
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.agent.context import DeterministicContextSizer
from app.evaluation.coach_report import EvaluationResponseModelV11
from app.lol.summary_schema import validate_summary_document
from app.providers.capabilities import ProviderCapabilities
from app.providers.errors import ProviderError
from app.providers.models import (
    ChatRequest,
    ChatResponse,
    MessageRole,
    TokenUsage,
    ToolCall,
)
from app.providers.protocol import LLMProvider

from .provider_adoption import (
    ExperimentBudgetedProvider,
    ExperimentFailureCode,
    ExperimentStopController,
    ProviderBudgetPolicy,
    ProviderResourceLedger,
    ResourceLedgerSnapshot,
    classify_provider_error,
)
from .provider_domain_experiment import DomainCaseExecutionPlan
from .provider_domain_plan import (
    DomainCaseInput,
    DomainCaseInputPlanArtifact,
    DomainFixtureCommitment,
    LoadedDomainCaseInputPlan,
)
from .provider_domain_production import ProductionDomainCaseExecutor


NonBlankText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
Sha256Text = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
GitShaText = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]


class CalibrationStage(str, Enum):
    AGENT_INITIAL = "agent_initial"
    AGENT_AFTER_TOOL = "agent_after_tool"
    EVALUATION = "evaluation"
    EVALUATION_REPAIR = "evaluation_repair"


CALIBRATION_STAGES = (
    CalibrationStage.AGENT_INITIAL,
    CalibrationStage.AGENT_AFTER_TOOL,
    CalibrationStage.EVALUATION,
    CalibrationStage.EVALUATION_REPAIR,
)

_EXPECTED_PROFILE_IDS = ("baseline", "ceiling")
_CALIBRATION_OUTPUT_CAP = 64
_CALIBRATION_MAX_CALLS = 8
_CALIBRATION_MAX_TOKENS = 64_000
_CALIBRATION_MAX_COST = Decimal("0.10")
_HISTORICAL_PROTOCOL_TOKENS = 1428
_HISTORICAL_PROTOCOL_COST = Decimal("0.00221496")
_DOMAIN_CASE_COUNT = 3
_V3_OUTPUT_PER_REQUEST = 1024
_SKILL_AGENT_DEADLINE_MS = 30_000


class ResourceCalibrationProfile(BaseModel):
    """One public development-only request-shape profile."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    profile_id: Literal["baseline", "ceiling"]
    case_id: NonBlankText
    run_id: NonBlankText
    user_utterance: NonBlankText
    focus: Literal["overall", "laning", "survival", "economy", "vision"]
    player_summary: DomainFixtureCommitment
    deterministic_report: DomainFixtureCommitment
    knowledge_mode: Literal["standard", "append_injected_evidence"]
    injected_evidence_text: str | None = None
    tool_queries: tuple[NonBlankText, ...] = Field(min_length=1, max_length=3)
    draft_text: NonBlankText
    invalid_evaluation_text: NonBlankText

    @model_validator(mode="after")
    def validate_profile_shape(self) -> "ResourceCalibrationProfile":
        expected_queries = 1 if self.profile_id == "baseline" else 3
        if len(self.tool_queries) != expected_queries:
            raise ValueError("calibration profile tool count is not frozen")
        if self.knowledge_mode == "append_injected_evidence":
            if not self.injected_evidence_text or not self.injected_evidence_text.strip():
                raise ValueError("injected knowledge profile requires evidence text")
        elif self.injected_evidence_text is not None:
            raise ValueError("standard profile cannot inject evidence text")
        if len(set(self.tool_queries)) != len(self.tool_queries):
            raise ValueError("calibration tool queries must be unique")
        return self


class ResourceCalibrationArtifact(BaseModel):
    """Sealed public development artifact; never quality-admission evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    artifact_id: NonBlankText
    artifact_version: NonBlankText
    role: Literal["development"]
    quality_admission_excluded: Literal[True]
    provider_id: Literal["deepseek"]
    model: Literal["deepseek-v4-pro"]
    skill_name: Literal["recent-form-review"]
    skill_version: Literal["0.2.0"]
    sdk_max_retries: Literal[0]
    max_revisions: Literal[0]
    required_stages: tuple[CalibrationStage, ...]
    profile_count: Literal[2]
    profiles: tuple[ResourceCalibrationProfile, ...]

    @model_validator(mode="after")
    def validate_frozen_shape(self) -> "ResourceCalibrationArtifact":
        if self.required_stages != CALIBRATION_STAGES:
            raise ValueError("calibration stages do not match the frozen order")
        if len(self.profiles) != self.profile_count:
            raise ValueError("calibration profile_count does not match profiles")
        if tuple(row.profile_id for row in self.profiles) != _EXPECTED_PROFILE_IDS:
            raise ValueError("calibration profiles must be baseline then ceiling")
        identities = (
            tuple(row.case_id for row in self.profiles),
            tuple(row.run_id for row in self.profiles),
        )
        if any(len(set(values)) != len(values) for values in identities):
            raise ValueError("calibration case and run identities must be unique")
        return self


@dataclass(frozen=True)
class LoadedResourceCalibrationProfile:
    profile: ResourceCalibrationProfile
    summary_path: Path
    report_path: Path
    summary: dict
    report: str

    @property
    def profile_id(self) -> str:
        return self.profile.profile_id


@dataclass(frozen=True)
class LoadedResourceCalibrationArtifact:
    artifact: ResourceCalibrationArtifact
    artifact_path: Path
    artifact_sha256: str
    profiles: tuple[LoadedResourceCalibrationProfile, ...]


class CalibrationRequestEnvelope(BaseModel):
    """Body-free, publishable identity for one frozen ChatRequest."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    ordinal: int = Field(gt=0)
    profile_id: Literal["baseline", "ceiling"]
    stage: CalibrationStage
    request_sha256: Sha256Text
    message_count: int = Field(gt=0)
    message_roles: tuple[Literal["system", "user", "assistant", "tool"], ...]
    local_context_units: int = Field(gt=0)
    tool_names: tuple[NonBlankText, ...] = ()
    response_contract_name: str | None = None
    response_contract_version: str | None = None
    max_tokens: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_shape(self) -> "CalibrationRequestEnvelope":
        if self.message_count != len(self.message_roles):
            raise ValueError("message count must match message roles")
        if (self.response_contract_name is None) != (
            self.response_contract_version is None
        ):
            raise ValueError("response contract identity must be complete")
        return self


class ResourceCalibrationRequestSnapshot(BaseModel):
    """Public request-set snapshot without any Prompt or response body."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    artifact_id: NonBlankText
    artifact_sha256: Sha256Text
    provider_id: Literal["deepseek"]
    requested_model: Literal["deepseek-v4-pro"]
    role: Literal["development"]
    quality_admission_excluded: Literal[True]
    request_count: Literal[8]
    envelopes: tuple[CalibrationRequestEnvelope, ...]
    request_set_sha256: Sha256Text

    @model_validator(mode="after")
    def validate_request_set(self) -> "ResourceCalibrationRequestSnapshot":
        if len(self.envelopes) != self.request_count:
            raise ValueError("request snapshot must contain exactly eight envelopes")
        expected = tuple(
            (profile_id, stage)
            for profile_id in _EXPECTED_PROFILE_IDS
            for stage in CALIBRATION_STAGES
        )
        actual = tuple((row.profile_id, row.stage) for row in self.envelopes)
        if actual != expected:
            raise ValueError("request snapshot profile/stage order is incomplete")
        if tuple(row.ordinal for row in self.envelopes) != tuple(range(1, 9)):
            raise ValueError("request snapshot ordinals must be contiguous")
        return self


@dataclass(frozen=True)
class FrozenCalibrationRequest:
    profile_id: str
    stage: CalibrationStage
    request: ChatRequest


@dataclass(frozen=True)
class FrozenCalibrationRequestSet:
    """Internal full requests plus their safe public snapshot."""

    requests: tuple[FrozenCalibrationRequest, ...]
    snapshot: ResourceCalibrationRequestSnapshot


class ResourceCalibrationUsageObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ordinal: int = Field(gt=0)
    profile_id: Literal["baseline", "ceiling"]
    stage: CalibrationStage
    provider_id: Literal["deepseek"]
    requested_model: Literal["deepseek-v4-pro"]
    resolved_model: NonBlankText
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0, le=_CALIBRATION_OUTPUT_CAP)
    latency_ms: int = Field(ge=0)
    finish_reason: str | None = None
    request_id_sha256: Sha256Text | None = None


class CalibrationSimulationResult(BaseModel):
    """Safe offline result; explicitly excluded from model-quality claims."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    status: Literal["completed", "stopped"]
    provider_id: Literal["deepseek"]
    requested_model: Literal["deepseek-v4-pro"]
    request_set_sha256: Sha256Text
    expected_calls: Literal[8]
    replay_calls_used: int = Field(ge=0, le=8)
    responses_completed: int = Field(ge=0, le=8)
    observations: tuple[ResourceCalibrationUsageObservation, ...]
    ledger: ResourceLedgerSnapshot
    failure_code: ExperimentFailureCode | None = None
    external_provider_calls: Literal[0]
    quality_admission_excluded: Literal[True]

    @model_validator(mode="after")
    def validate_terminal_result(self) -> "CalibrationSimulationResult":
        if self.responses_completed != len(self.observations):
            raise ValueError("responses_completed must match observations")
        if self.replay_calls_used != self.ledger.calls_used:
            raise ValueError("replay call count must match the ledger")
        if self.status == "completed":
            if (
                self.failure_code is not None
                or self.replay_calls_used != self.expected_calls
                or self.responses_completed != self.expected_calls
            ):
                raise ValueError("completed simulation requires a full clean replay")
        elif self.failure_code is None:
            raise ValueError("stopped simulation requires a safe failure code")
        return self


class ResourceCalibrationAdmission(BaseModel):
    """No-I/O proof for a later, separately authorized calibration run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    provider_id: Literal["deepseek"]
    requested_model: Literal["deepseek-v4-pro"]
    code_sha: GitShaText
    public_ci_sha: GitShaText
    public_ci_success_confirmed: Literal[True]
    artifact_id: NonBlankText
    artifact_sha256: Sha256Text
    request_set_sha256: Sha256Text
    maximum_calls: Literal[8]
    maximum_output_tokens_per_request: Literal[64]
    maximum_observed_tokens: Literal[64000]
    maximum_estimated_cost: Decimal
    currency: Literal["USD"]
    sdk_max_retries: Literal[0]
    external_provider_calls: Literal[0]
    held_out_created: Literal[False]
    provider_construction_authorized: Literal[False]
    local_preflight_passed: Literal[True]

    @model_validator(mode="after")
    def validate_exact_ci_identity(self) -> "ResourceCalibrationAdmission":
        if self.code_sha != self.public_ci_sha:
            raise ValueError("no-I/O admission must bind exact public CI SHA")
        return self


class ResourceCalibrationRunAdmission(BaseModel):
    """Explicit upgrade from no-I/O proof to one bounded real replay."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    experiment_id: Sha256Text
    no_io_admission: ResourceCalibrationAdmission
    result_relative_path: NonBlankText
    explicit_real_call_confirmed: Literal[True]
    maximum_calls: Literal[8]
    provider_construction_authorized: Literal[True]
    external_provider_calls_before_run: Literal[0]
    held_out_created: Literal[False]
    quality_admission_excluded: Literal[True]

    @model_validator(mode="after")
    def validate_run_identity(self) -> "ResourceCalibrationRunAdmission":
        no_io = self.no_io_admission
        normalized_path = _validate_resource_result_relative_path(
            self.result_relative_path
        )
        if (
            no_io.maximum_calls != self.maximum_calls
            or no_io.provider_id != "deepseek"
            or no_io.requested_model != "deepseek-v4-pro"
            or no_io.provider_construction_authorized is not False
        ):
            raise ValueError("real replay admission does not match no-I/O proof")
        if normalized_path != self.result_relative_path:
            raise ValueError("real replay result path is not canonical")
        expected_id = _resource_calibration_experiment_id(
            admission=no_io,
            result_relative_path=normalized_path,
            maximum_calls=self.maximum_calls,
        )
        if self.experiment_id != expected_id:
            raise ValueError("real replay experiment identity drifted")
        return self


class RealResourceCalibrationResult(BaseModel):
    """Safe immutable result of the separately authorized real replay."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    experiment_id: Sha256Text
    admission: ResourceCalibrationRunAdmission
    status: Literal["completed", "stopped"]
    provider_id: Literal["deepseek"]
    requested_model: Literal["deepseek-v4-pro"]
    request_set_sha256: Sha256Text
    expected_calls: Literal[8]
    replay_calls_used: int = Field(ge=0, le=8)
    responses_completed: int = Field(ge=0, le=8)
    observations: tuple[ResourceCalibrationUsageObservation, ...]
    ledger: ResourceLedgerSnapshot
    failure_code: ExperimentFailureCode | None = None
    external_provider_calls: int = Field(ge=0, le=8)
    v3_budget_derivation_ready: bool
    quality_admission_excluded: Literal[True]
    model_quality_evaluated: Literal[False]
    held_out_executed: Literal[False]

    @model_validator(mode="after")
    def validate_terminal_result(self) -> "RealResourceCalibrationResult":
        if self.experiment_id != self.admission.experiment_id:
            raise ValueError("real result does not match the admitted experiment")
        if self.request_set_sha256 != (
            self.admission.no_io_admission.request_set_sha256
        ):
            raise ValueError("real result request identity drifted")
        if self.responses_completed != len(self.observations):
            raise ValueError("responses_completed must match observations")
        if (
            self.replay_calls_used != self.ledger.calls_used
            or self.external_provider_calls != self.replay_calls_used
        ):
            raise ValueError("real call count must match the resource ledger")
        if (
            self.ledger.provider_id != self.provider_id
            or self.ledger.model != self.requested_model
            or self.ledger.max_calls != self.expected_calls
        ):
            raise ValueError("real result ledger identity drifted")
        expected_observations = tuple(
            (profile_id, stage)
            for profile_id in _EXPECTED_PROFILE_IDS
            for stage in CALIBRATION_STAGES
        )
        actual_observations = tuple(
            (row.profile_id, row.stage) for row in self.observations
        )
        if actual_observations != expected_observations[: len(self.observations)]:
            raise ValueError("real result observations are not a frozen prefix")
        if tuple(row.ordinal for row in self.observations) != tuple(
            range(1, len(self.observations) + 1)
        ):
            raise ValueError("real result observation ordinals are not contiguous")
        completed = self.status == "completed"
        if completed:
            if (
                self.failure_code is not None
                or self.replay_calls_used != self.expected_calls
                or self.responses_completed != self.expected_calls
            ):
                raise ValueError("completed real replay requires clean 8/8 usage")
        elif self.failure_code is None:
            raise ValueError("stopped real replay requires a safe failure code")
        if self.v3_budget_derivation_ready != completed:
            raise ValueError("budget readiness must match replay completeness")
        return self


class V3StageResourceBudget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    stage: CalibrationStage
    observed_input_max: int = Field(ge=0)
    input_ceiling: int = Field(gt=0)
    observed_latency_max_ms: int = Field(ge=0)


class V3ResourceBudgetDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    stage_budgets: tuple[V3StageResourceBudget, ...]
    case_input_ceiling: int = Field(gt=0)
    case_output_ceiling: Literal[4096]
    case_token_limit: int = Field(gt=0)
    domain_token_limit: int = Field(gt=0)
    historical_protocol_tokens: Literal[1428]
    global_token_limit: int = Field(gt=0)
    case_cost_ceiling: Decimal = Field(gt=0)
    historical_protocol_cost: Decimal = Field(gt=0)
    global_cost_ceiling: Decimal = Field(gt=0)
    cost_stop_line: Decimal = Field(gt=0)
    agent_latency_with_margin_ms: int = Field(ge=0)
    skill_agent_deadline_ms: Literal[30000]
    case_latency_limit_ms: int = Field(gt=0)
    v3_gate_creation_allowed: bool
    rejection_reasons: tuple[
        Literal["cost_ceiling_exceeded", "skill_agent_deadline_unreachable"],
        ...,
    ] = ()

    @model_validator(mode="after")
    def validate_decision(self) -> "V3ResourceBudgetDecision":
        if self.v3_gate_creation_allowed == bool(self.rejection_reasons):
            raise ValueError("V3 decision and rejection reasons disagree")
        return self


class V3ResourceBudgetRecord(BaseModel):
    """Public proof that a budget was derived without another Provider call."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    calibration_experiment_id: Sha256Text
    calibration_result_sha256: Sha256Text
    code_sha: GitShaText
    public_ci_sha: GitShaText
    request_set_sha256: Sha256Text
    calibration_external_provider_calls: Literal[8]
    external_provider_calls: Literal[0]
    held_out_created: Literal[False]
    quality_admission_excluded: Literal[True]
    decision: V3ResourceBudgetDecision


class ResourceCalibrationAdjudication(BaseModel):
    """Conservative interpretation of immutable real calibration evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    calibration_experiment_id: Sha256Text
    calibration_result_sha256: Sha256Text
    code_sha: GitShaText
    public_ci_sha: GitShaText
    request_set_sha256: Sha256Text
    status: Literal["complete", "incomplete"]
    failure_code: ExperimentFailureCode | None = None
    external_provider_calls_in_result: int = Field(ge=0, le=8)
    normalized_responses: int = Field(ge=0, le=8)
    unobserved_external_calls: int = Field(ge=0, le=8)
    ledger_recorded_input_tokens: int = Field(ge=0)
    ledger_recorded_output_tokens: int = Field(ge=0)
    ledger_recorded_tokens: int = Field(ge=0)
    ledger_recorded_cost: Decimal = Field(ge=0)
    ledger_recorded_latency_ms: int = Field(ge=0)
    usage_complete: bool
    billable_input_tokens: int | None = Field(default=None, ge=0)
    billable_output_tokens: int | None = Field(default=None, ge=0)
    billable_cost: Decimal | None = Field(default=None, ge=0)
    provider_error_detail_available: Literal[False]
    provider_error_detail_code: Literal[None]
    v3_budget_derivation_allowed: bool
    v3_held_out_creation_allowed: Literal[False]
    rerun_allowed: Literal[False]
    model_quality_conclusion: Literal["unknown"]
    external_provider_calls: Literal[0]
    quality_admission_excluded: Literal[True]

    @model_validator(mode="after")
    def validate_conservative_adjudication(
        self,
    ) -> "ResourceCalibrationAdjudication":
        if self.unobserved_external_calls != (
            self.external_provider_calls_in_result - self.normalized_responses
        ):
            raise ValueError("unobserved call count does not match the result")
        if self.ledger_recorded_tokens != (
            self.ledger_recorded_input_tokens
            + self.ledger_recorded_output_tokens
        ):
            raise ValueError("ledger token total does not match components")
        billable = (
            self.billable_input_tokens,
            self.billable_output_tokens,
            self.billable_cost,
        )
        complete = self.status == "complete"
        if complete:
            if (
                self.failure_code is not None
                or not self.usage_complete
                or any(value is None for value in billable)
                or not self.v3_budget_derivation_allowed
            ):
                raise ValueError("complete adjudication requires complete usage")
        elif (
            self.failure_code is None
            or self.usage_complete
            or any(value is not None for value in billable)
            or self.v3_budget_derivation_allowed
        ):
            raise ValueError("incomplete adjudication must keep billing unknown")
        return self


class ImmutableResourceCalibrationOutput:
    """Reserve one real result path before Key loading or Provider creation."""

    def __init__(self, path: Path, experiment_id: str, stream) -> None:
        self.path = path
        self.experiment_id = experiment_id
        self._stream = stream
        self._committed = False

    @classmethod
    def reserve(
        cls,
        path: str | Path,
        *,
        experiment_id: str,
    ) -> "ImmutableResourceCalibrationOutput":
        if not re.fullmatch(r"[0-9a-f]{64}", experiment_id):
            raise ValueError("experiment_id must be a SHA-256 digest")
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        stream = output.open("x", encoding="utf-8", newline="\n")
        return cls(output, experiment_id, stream)

    def commit(self, result: RealResourceCalibrationResult) -> None:
        if self._committed or self._stream.closed:
            raise RuntimeError("resource calibration output is already finalized")
        if not isinstance(result, RealResourceCalibrationResult):
            raise TypeError("result must be a RealResourceCalibrationResult")
        if result.experiment_id != self.experiment_id:
            raise ValueError("result does not match the reserved experiment")
        self._stream.write(result.model_dump_json(indent=2))
        self._stream.write("\n")
        self._stream.flush()
        self._stream.close()
        self._committed = True

    def abandon(self) -> None:
        """Retain the exclusive sentinel so a post-reservation crash cannot rerun."""

        if not self._stream.closed:
            self._stream.close()


@dataclass(frozen=True)
class _CalibrationReplayOutcome:
    status: Literal["completed", "stopped"]
    observations: tuple[ResourceCalibrationUsageObservation, ...]
    ledger: ResourceLedgerSnapshot
    failure_code: ExperimentFailureCode | None


class CalibrationIncompleteError(ValueError):
    """Raised when a partial simulation tries to produce a V3 budget."""


def deepseek_resource_calibration_policy() -> ProviderBudgetPolicy:
    return ProviderBudgetPolicy(
        provider_id="deepseek",
        model="deepseek-v4-pro",
        currency="USD",
        max_calls=_CALIBRATION_MAX_CALLS,
        scope_call_limits={"calibration": _CALIBRATION_MAX_CALLS},
        max_observed_tokens=_CALIBRATION_MAX_TOKENS,
        max_output_tokens_per_request=_CALIBRATION_OUTPUT_CAP,
        input_cost_per_million=Decimal("1.32"),
        output_cost_per_million=Decimal("3.96"),
        max_estimated_cost=_CALIBRATION_MAX_COST,
        scope_token_limits={"calibration": _CALIBRATION_MAX_TOKENS},
    )


def load_resource_calibration_profiles(
    path: str | Path,
    *,
    project_root: str | Path,
    protected_paths: tuple[str | Path, ...],
) -> LoadedResourceCalibrationArtifact:
    """Load exact profile bytes and reject protected V2 reuse before fixtures."""

    artifact_path = Path(path).resolve()
    raw = artifact_path.read_bytes()
    artifact = ResourceCalibrationArtifact.model_validate_json(raw)
    protected = _protected_values(protected_paths, Path(project_root).resolve())
    candidates = _calibration_sensitive_values(artifact)
    if candidates.intersection(protected):
        raise ValueError("calibration profile reuses protected V2 content")

    root = Path(project_root).resolve()
    loaded_profiles: list[LoadedResourceCalibrationProfile] = []
    for profile in artifact.profiles:
        summary_path = _verify_fixture(root, profile.player_summary)
        report_path = _verify_fixture(root, profile.deterministic_report)
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        validate_summary_document(summary)
        expected_matches = 3 if profile.profile_id == "baseline" else 10
        if len(summary["matches"]) != expected_matches:
            raise ValueError("calibration profile match projection is not frozen")
        report = report_path.read_text(encoding="utf-8")
        loaded_profiles.append(
            LoadedResourceCalibrationProfile(
                profile=profile,
                summary_path=summary_path,
                report_path=report_path,
                summary=summary,
                report=report,
            )
        )
    return LoadedResourceCalibrationArtifact(
        artifact=artifact,
        artifact_path=artifact_path,
        artifact_sha256=hashlib.sha256(raw).hexdigest(),
        profiles=tuple(loaded_profiles),
    )


@dataclass
class _ControlledCaptureProvider:
    profile: ResourceCalibrationProfile
    provider_name: str = "offline-resource-calibration"
    model_name: str = "offline-resource-calibration-control"
    capabilities: ProviderCapabilities = ProviderCapabilities(
        text_chat=True,
        tool_calling=True,
        structured_output=True,
        parallel_tool_calls=True,
    )
    requests: list[ChatRequest] = field(default_factory=list)
    _evaluation_calls: int = 0

    def chat(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        if request.response_contract is not None:
            self._evaluation_calls += 1
            if self._evaluation_calls == 1:
                return self._text(self.profile.invalid_evaluation_text)
            payload = EvaluationResponseModelV11(
                score=95,
                verdict="pass",
                issues=[],
                passed_checks=["facts", "citations", "security"],
                summary="controlled development calibration pass",
            )
            return self._text(payload.model_dump_json())
        if any(message.role is MessageRole.TOOL for message in request.messages):
            return self._text(self.profile.draft_text)
        calls = tuple(
            ToolCall(
                id=f"{self.profile.profile_id}-knowledge-{index}",
                name="knowledge.search",
                arguments={"query": query, "top_k": 1},
            )
            for index, query in enumerate(self.profile.tool_queries, start=1)
        )
        return ChatResponse(
            content=None,
            provider=self.provider_name,
            model=self.model_name,
            finish_reason="tool_calls",
            tool_calls=calls,
            usage=TokenUsage(input_tokens=1, output_tokens=1),
        )

    def _text(self, content: str) -> ChatResponse:
        return ChatResponse(
            content=content,
            provider=self.provider_name,
            model=self.model_name,
            finish_reason="stop",
            usage=TokenUsage(input_tokens=1, output_tokens=1),
        )


def capture_resource_calibration_requests(
    loaded: LoadedResourceCalibrationArtifact,
    *,
    project_root: str | Path,
    runs_root: str | Path,
) -> FrozenCalibrationRequestSet:
    """Generate all four request shapes per profile through production code."""

    if not isinstance(loaded, LoadedResourceCalibrationArtifact):
        raise TypeError("loaded must be a LoadedResourceCalibrationArtifact")
    captured: list[FrozenCalibrationRequest] = []
    envelopes: list[CalibrationRequestEnvelope] = []
    sizer = DeterministicContextSizer()

    for loaded_profile in loaded.profiles:
        profile = loaded_profile.profile
        provider = _ControlledCaptureProvider(profile)
        input_plan = _production_input_plan(loaded, loaded_profile)
        observation = ProductionDomainCaseExecutor(
            project_root=project_root,
            input_plan=input_plan,
            runs_root=runs_root,
        ).execute(case_id=profile.case_id, provider=provider)
        if observation.terminal_status != "published":
            raise ValueError("calibration production path did not publish")
        if len(provider.requests) != len(CALIBRATION_STAGES):
            raise ValueError("calibration production path is incomplete")
        stages = tuple(_request_stage(request) for request in provider.requests)
        if stages != CALIBRATION_STAGES:
            raise ValueError("calibration production stages drifted")

        for request, stage in zip(provider.requests, stages, strict=True):
            ordinal = len(captured) + 1
            captured.append(
                FrozenCalibrationRequest(
                    profile_id=profile.profile_id,
                    stage=stage,
                    request=request,
                )
            )
            contract = request.response_contract
            envelopes.append(
                CalibrationRequestEnvelope(
                    ordinal=ordinal,
                    profile_id=profile.profile_id,
                    stage=stage,
                    request_sha256=_request_digest(request),
                    message_count=len(request.messages),
                    message_roles=tuple(row.role.value for row in request.messages),
                    local_context_units=sizer.estimate_messages(request.messages),
                    tool_names=tuple(row.name for row in request.tools),
                    response_contract_name=(contract.name if contract else None),
                    response_contract_version=(
                        contract.version if contract else None
                    ),
                    max_tokens=request.max_tokens,
                )
            )

    request_set_sha256 = _digest_json(
        [row.model_dump(mode="json") for row in envelopes]
    )
    snapshot = ResourceCalibrationRequestSnapshot(
        artifact_id=loaded.artifact.artifact_id,
        artifact_sha256=loaded.artifact_sha256,
        provider_id=loaded.artifact.provider_id,
        requested_model=loaded.artifact.model,
        role=loaded.artifact.role,
        quality_admission_excluded=True,
        request_count=8,
        envelopes=tuple(envelopes),
        request_set_sha256=request_set_sha256,
    )
    return FrozenCalibrationRequestSet(
        requests=tuple(captured),
        snapshot=snapshot,
    )


def simulate_resource_calibration(
    frozen: FrozenCalibrationRequestSet,
    *,
    provider: LLMProvider,
    clock,
) -> CalibrationSimulationResult:
    """Exercise the replay gates with an explicitly marked offline fake only."""

    if not isinstance(frozen, FrozenCalibrationRequestSet):
        raise TypeError("frozen must be a FrozenCalibrationRequestSet")
    if getattr(provider, "is_offline_calibration_fake", False) is not True:
        raise ValueError("offline simulation requires an explicit fake Provider")
    outcome = _execute_resource_calibration_replay(
        frozen,
        provider=provider,
        clock=clock,
    )
    return CalibrationSimulationResult(
        status=outcome.status,
        provider_id="deepseek",
        requested_model="deepseek-v4-pro",
        request_set_sha256=frozen.snapshot.request_set_sha256,
        expected_calls=_CALIBRATION_MAX_CALLS,
        replay_calls_used=outcome.ledger.calls_used,
        responses_completed=len(outcome.observations),
        observations=outcome.observations,
        ledger=outcome.ledger,
        failure_code=outcome.failure_code,
        external_provider_calls=0,
        quality_admission_excluded=True,
    )


def run_real_resource_calibration(
    *,
    admission: ResourceCalibrationRunAdmission,
    frozen: FrozenCalibrationRequestSet,
    provider: LLMProvider,
    clock: Callable[[], float] = time.monotonic,
) -> RealResourceCalibrationResult:
    """Replay one admitted request set without retaining any response body."""

    if not isinstance(admission, ResourceCalibrationRunAdmission):
        raise TypeError("admission must be a ResourceCalibrationRunAdmission")
    if not isinstance(frozen, FrozenCalibrationRequestSet):
        raise TypeError("frozen must be a FrozenCalibrationRequestSet")
    if (
        admission.no_io_admission.request_set_sha256
        != frozen.snapshot.request_set_sha256
        or len(frozen.requests) != admission.maximum_calls
    ):
        raise ValueError("real replay request identity drifted")
    if (
        provider.provider_name != admission.no_io_admission.provider_id
        or provider.model_name != admission.no_io_admission.requested_model
    ):
        raise ValueError("real Provider identity does not match admission")

    outcome = _execute_resource_calibration_replay(
        frozen,
        provider=provider,
        clock=clock,
    )
    return RealResourceCalibrationResult(
        experiment_id=admission.experiment_id,
        admission=admission,
        status=outcome.status,
        provider_id="deepseek",
        requested_model="deepseek-v4-pro",
        request_set_sha256=frozen.snapshot.request_set_sha256,
        expected_calls=_CALIBRATION_MAX_CALLS,
        replay_calls_used=outcome.ledger.calls_used,
        responses_completed=len(outcome.observations),
        observations=outcome.observations,
        ledger=outcome.ledger,
        failure_code=outcome.failure_code,
        external_provider_calls=outcome.ledger.calls_used,
        v3_budget_derivation_ready=outcome.status == "completed",
        quality_admission_excluded=True,
        model_quality_evaluated=False,
        held_out_executed=False,
    )


def _execute_resource_calibration_replay(
    frozen: FrozenCalibrationRequestSet,
    *,
    provider: LLMProvider,
    clock: Callable[[], float],
) -> _CalibrationReplayOutcome:
    """Shared bounded replay engine; callers assign offline/real semantics."""

    policy = deepseek_resource_calibration_policy()
    ledger = ProviderResourceLedger(policy)
    controller = ExperimentStopController(allowed_provider_ids=(policy.provider_id,))
    budgeted = ExperimentBudgetedProvider(
        provider=provider,
        ledger=ledger,
        controller=controller,
        scope="calibration",
        clock=clock,
    )
    observations: list[ResourceCalibrationUsageObservation] = []
    failure_code: ExperimentFailureCode | None = None

    for ordinal, frozen_request in enumerate(frozen.requests, start=1):
        before = ledger.snapshot()
        try:
            response = budgeted.chat(frozen_request.request)
        except ProviderError as exc:
            failure_code = classify_provider_error(exc)
            break
        after = ledger.snapshot()
        observations.append(
            ResourceCalibrationUsageObservation(
                ordinal=ordinal,
                profile_id=frozen_request.profile_id,
                stage=frozen_request.stage,
                provider_id=policy.provider_id,
                requested_model=policy.model,
                resolved_model=response.model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                latency_ms=after.latency_ms - before.latency_ms,
                finish_reason=response.finish_reason,
                request_id_sha256=(
                    hashlib.sha256(response.request_id.encode("utf-8")).hexdigest()
                    if response.request_id
                    else None
                ),
            )
        )

    snapshot = ledger.snapshot()
    completed = (
        failure_code is None
        and len(observations) == _CALIBRATION_MAX_CALLS
        and snapshot.calls_used == _CALIBRATION_MAX_CALLS
    )
    return _CalibrationReplayOutcome(
        status="completed" if completed else "stopped",
        observations=tuple(observations),
        ledger=snapshot,
        failure_code=(
            None
            if completed
            else failure_code or ExperimentFailureCode.PROVIDER_RESPONSE_INVALID
        ),
    )


def derive_v3_resource_budget(
    result: CalibrationSimulationResult | RealResourceCalibrationResult,
) -> V3ResourceBudgetDecision:
    """Apply ADR-0026's integer/Decimal-only, upward-rounded formula."""

    if not isinstance(
        result,
        (CalibrationSimulationResult, RealResourceCalibrationResult),
    ):
        raise TypeError("result must be a calibration replay result")
    expected = tuple(
        (profile_id, stage)
        for profile_id in _EXPECTED_PROFILE_IDS
        for stage in CALIBRATION_STAGES
    )
    actual = tuple((row.profile_id, row.stage) for row in result.observations)
    if (
        result.status != "completed"
        or result.responses_completed != 8
        or actual != expected
    ):
        raise CalibrationIncompleteError(
            "complete 8/8 calibration usage is required for V3 budget derivation"
        )

    stage_budgets = []
    for stage in CALIBRATION_STAGES:
        rows = [row for row in result.observations if row.stage is stage]
        observed_input = max(row.input_tokens for row in rows)
        observed_latency = max(row.latency_ms for row in rows)
        stage_budgets.append(
            V3StageResourceBudget(
                stage=stage,
                observed_input_max=observed_input,
                input_ceiling=_round_up(
                    _multiply_ratio_up(observed_input, 5, 4),
                    256,
                ),
                observed_latency_max_ms=observed_latency,
            )
        )

    case_input = sum(row.input_ceiling for row in stage_budgets)
    case_output = len(CALIBRATION_STAGES) * _V3_OUTPUT_PER_REQUEST
    case_tokens = _round_up(case_input + case_output, 1024)
    domain_tokens = _DOMAIN_CASE_COUNT * case_tokens
    global_tokens = _HISTORICAL_PROTOCOL_TOKENS + domain_tokens
    million = Decimal("1000000")
    case_cost = (
        Decimal(case_input) * Decimal("1.32")
        + Decimal(case_output) * Decimal("3.96")
    ) / million
    global_cost = _round_decimal_up(
        _HISTORICAL_PROTOCOL_COST + Decimal(_DOMAIN_CASE_COUNT) * case_cost,
        Decimal("0.01"),
    )
    latency_sum = sum(row.observed_latency_max_ms for row in stage_budgets)
    case_latency = _round_up(_multiply_ratio_up(latency_sum, 5, 4), 5000)
    agent_latency = _multiply_ratio_up(
        stage_budgets[0].observed_latency_max_ms
        + stage_budgets[1].observed_latency_max_ms,
        5,
        4,
    )
    reasons: list[str] = []
    if global_cost > _CALIBRATION_MAX_COST:
        reasons.append("cost_ceiling_exceeded")
    if agent_latency > _SKILL_AGENT_DEADLINE_MS:
        reasons.append("skill_agent_deadline_unreachable")
    return V3ResourceBudgetDecision(
        stage_budgets=tuple(stage_budgets),
        case_input_ceiling=case_input,
        case_output_ceiling=case_output,
        case_token_limit=case_tokens,
        domain_token_limit=domain_tokens,
        historical_protocol_tokens=_HISTORICAL_PROTOCOL_TOKENS,
        global_token_limit=global_tokens,
        case_cost_ceiling=case_cost,
        historical_protocol_cost=_HISTORICAL_PROTOCOL_COST,
        global_cost_ceiling=global_cost,
        cost_stop_line=_CALIBRATION_MAX_COST,
        agent_latency_with_margin_ms=agent_latency,
        skill_agent_deadline_ms=_SKILL_AGENT_DEADLINE_MS,
        case_latency_limit_ms=case_latency,
        v3_gate_creation_allowed=not reasons,
        rejection_reasons=tuple(reasons),
    )


def prepare_resource_calibration_admission(
    *,
    loaded: LoadedResourceCalibrationArtifact,
    frozen_requests: FrozenCalibrationRequestSet,
    code_sha: str,
    public_ci_sha: str,
    public_ci_success_confirmed: bool,
) -> ResourceCalibrationAdmission:
    """Bind local identities and exact-SHA CI without accepting a Provider."""

    if not isinstance(loaded, LoadedResourceCalibrationArtifact):
        raise TypeError("loaded must be a LoadedResourceCalibrationArtifact")
    if not isinstance(frozen_requests, FrozenCalibrationRequestSet):
        raise TypeError("frozen_requests must be a FrozenCalibrationRequestSet")
    if not re.fullmatch(r"[0-9a-f]{40}", code_sha):
        raise ValueError("code SHA must be a lowercase Git SHA")
    if code_sha != public_ci_sha or not public_ci_success_confirmed:
        raise ValueError("public CI SHA must exactly match a confirmed code SHA")
    snapshot = frozen_requests.snapshot
    if (
        snapshot.artifact_id != loaded.artifact.artifact_id
        or snapshot.artifact_sha256 != loaded.artifact_sha256
        or len(frozen_requests.requests) != _CALIBRATION_MAX_CALLS
    ):
        raise ValueError("calibration artifact or request identity drifted")
    policy = deepseek_resource_calibration_policy()
    return ResourceCalibrationAdmission(
        provider_id=policy.provider_id,
        requested_model=policy.model,
        code_sha=code_sha,
        public_ci_sha=public_ci_sha,
        public_ci_success_confirmed=True,
        artifact_id=loaded.artifact.artifact_id,
        artifact_sha256=loaded.artifact_sha256,
        request_set_sha256=snapshot.request_set_sha256,
        maximum_calls=policy.max_calls,
        maximum_output_tokens_per_request=policy.max_output_tokens_per_request,
        maximum_observed_tokens=policy.max_observed_tokens,
        maximum_estimated_cost=policy.max_estimated_cost,
        currency=policy.currency,
        sdk_max_retries=0,
        external_provider_calls=0,
        held_out_created=False,
        provider_construction_authorized=False,
        local_preflight_passed=True,
    )


def prepare_resource_calibration_run_admission(
    *,
    admission: ResourceCalibrationAdmission,
    frozen_requests: FrozenCalibrationRequestSet,
    explicit_real_call_confirmed: bool,
    maximum_calls: int,
    result_relative_path: str,
) -> ResourceCalibrationRunAdmission:
    """Authorize one real replay without accepting a Provider or API Key."""

    if not isinstance(admission, ResourceCalibrationAdmission):
        raise TypeError("admission must be a ResourceCalibrationAdmission")
    if not isinstance(frozen_requests, FrozenCalibrationRequestSet):
        raise TypeError("frozen_requests must be a FrozenCalibrationRequestSet")
    if not explicit_real_call_confirmed:
        raise RuntimeError("real calibration requires explicit confirmation")
    if maximum_calls != _CALIBRATION_MAX_CALLS:
        raise ValueError("real calibration requires exactly 8 calls")
    if (
        admission.maximum_calls != maximum_calls
        or admission.request_set_sha256
        != frozen_requests.snapshot.request_set_sha256
        or len(frozen_requests.requests) != maximum_calls
    ):
        raise ValueError("real calibration request identity drifted")
    normalized_path = _validate_resource_result_relative_path(
        result_relative_path
    )
    return ResourceCalibrationRunAdmission(
        experiment_id=_resource_calibration_experiment_id(
            admission=admission,
            result_relative_path=normalized_path,
            maximum_calls=maximum_calls,
        ),
        no_io_admission=admission,
        result_relative_path=normalized_path,
        explicit_real_call_confirmed=True,
        maximum_calls=_CALIBRATION_MAX_CALLS,
        provider_construction_authorized=True,
        external_provider_calls_before_run=0,
        held_out_created=False,
        quality_admission_excluded=True,
    )


def build_v3_resource_budget_record(
    *,
    result: RealResourceCalibrationResult,
    calibration_result_sha256: str,
) -> V3ResourceBudgetRecord:
    """Bind ADR-0026's pure decision to exact immutable real-result bytes."""

    if not isinstance(result, RealResourceCalibrationResult):
        raise TypeError("result must be a RealResourceCalibrationResult")
    if not re.fullmatch(r"[0-9a-f]{64}", calibration_result_sha256):
        raise ValueError("calibration_result_sha256 must be a SHA-256 digest")
    decision = derive_v3_resource_budget(result)
    no_io = result.admission.no_io_admission
    return V3ResourceBudgetRecord(
        calibration_experiment_id=result.experiment_id,
        calibration_result_sha256=calibration_result_sha256,
        code_sha=no_io.code_sha,
        public_ci_sha=no_io.public_ci_sha,
        request_set_sha256=result.request_set_sha256,
        calibration_external_provider_calls=8,
        external_provider_calls=0,
        held_out_created=False,
        quality_admission_excluded=True,
        decision=decision,
    )


def build_resource_calibration_adjudication(
    *,
    result: RealResourceCalibrationResult,
    calibration_result_sha256: str,
) -> ResourceCalibrationAdjudication:
    """Interpret unnormalized calls as unknown billing, never as known zero."""

    if not isinstance(result, RealResourceCalibrationResult):
        raise TypeError("result must be a RealResourceCalibrationResult")
    if not re.fullmatch(r"[0-9a-f]{64}", calibration_result_sha256):
        raise ValueError("calibration_result_sha256 must be a SHA-256 digest")
    complete = result.status == "completed"
    ledger = result.ledger
    no_io = result.admission.no_io_admission
    return ResourceCalibrationAdjudication(
        calibration_experiment_id=result.experiment_id,
        calibration_result_sha256=calibration_result_sha256,
        code_sha=no_io.code_sha,
        public_ci_sha=no_io.public_ci_sha,
        request_set_sha256=result.request_set_sha256,
        status="complete" if complete else "incomplete",
        failure_code=result.failure_code,
        external_provider_calls_in_result=result.external_provider_calls,
        normalized_responses=result.responses_completed,
        unobserved_external_calls=(
            result.external_provider_calls - result.responses_completed
        ),
        ledger_recorded_input_tokens=ledger.input_tokens,
        ledger_recorded_output_tokens=ledger.output_tokens,
        ledger_recorded_tokens=ledger.total_tokens,
        ledger_recorded_cost=ledger.estimated_cost,
        ledger_recorded_latency_ms=ledger.latency_ms,
        usage_complete=complete,
        billable_input_tokens=ledger.input_tokens if complete else None,
        billable_output_tokens=ledger.output_tokens if complete else None,
        billable_cost=ledger.estimated_cost if complete else None,
        provider_error_detail_available=False,
        provider_error_detail_code=None,
        v3_budget_derivation_allowed=complete,
        v3_held_out_creation_allowed=False,
        rerun_allowed=False,
        model_quality_conclusion="unknown",
        external_provider_calls=0,
        quality_admission_excluded=True,
    )


def _validate_resource_result_relative_path(value: str) -> str:
    if not isinstance(value, str) or "\\" in value:
        raise ValueError("result path must be a safe project-relative JSON path")
    result_path = PurePosixPath(value)
    allowed_root = PurePosixPath(
        "data/evaluation/results/provider_capabilities"
    )
    if (
        result_path.is_absolute()
        or ".." in result_path.parts
        or result_path.suffix.lower() != ".json"
        or not result_path.is_relative_to(allowed_root)
    ):
        raise ValueError("result path must be a safe project-relative JSON path")
    return result_path.as_posix()


def _resource_calibration_experiment_id(
    *,
    admission: ResourceCalibrationAdmission,
    result_relative_path: str,
    maximum_calls: int,
) -> str:
    return _digest_json(
        {
            "no_io_admission": admission.model_dump(mode="json"),
            "result_relative_path": result_relative_path,
            "explicit_real_call_confirmed": True,
            "maximum_calls": maximum_calls,
        }
    )


def _production_input_plan(
    loaded: LoadedResourceCalibrationArtifact,
    profile: LoadedResourceCalibrationProfile,
) -> LoadedDomainCaseInputPlan:
    row = profile.profile
    artifact = DomainCaseInputPlanArtifact(
        plan_id=f"resource-calibration-{row.profile_id}",
        plan_version=loaded.artifact.artifact_version,
        dataset_id=loaded.artifact.artifact_id,
        dataset_version=loaded.artifact.artifact_version,
        skill_name=loaded.artifact.skill_name,
        skill_version=loaded.artifact.skill_version,
        player_summary=row.player_summary,
        deterministic_report=row.deterministic_report,
        sdk_max_retries=0,
        max_revisions=0,
        case_count=1,
        cases=(
            DomainCaseInput(
                case_id=row.case_id,
                run_id=row.run_id,
                user_utterance=row.user_utterance,
                focus=row.focus,
                knowledge_mode=row.knowledge_mode,
                injected_evidence_text=row.injected_evidence_text,
            ),
        ),
    )
    return LoadedDomainCaseInputPlan(
        artifact=artifact,
        execution_plan=DomainCaseExecutionPlan(
            plan_id=artifact.plan_id,
            plan_version=artifact.plan_version,
            plan_sha256=_digest_json(artifact.model_dump(mode="json")),
            case_ids=(row.case_id,),
        ),
        player_summary_path=profile.summary_path,
        deterministic_report_path=profile.report_path,
    )


def _request_stage(request: ChatRequest) -> CalibrationStage:
    harness_step = request.metadata.get("harness_step")
    if harness_step == "evaluate":
        return CalibrationStage.EVALUATION
    if harness_step == "evaluate_repair":
        return CalibrationStage.EVALUATION_REPAIR
    if "agent_loop_iteration" in request.metadata:
        return (
            CalibrationStage.AGENT_AFTER_TOOL
            if any(row.role is MessageRole.TOOL for row in request.messages)
            else CalibrationStage.AGENT_INITIAL
        )
    raise ValueError("request does not belong to a frozen calibration stage")


def _request_digest(request: ChatRequest) -> str:
    return _digest_json(
        {
            "messages": [
                {
                    "role": row.role.value,
                    "content": row.content,
                    "tool_call_id": row.tool_call_id,
                    "name": row.name,
                    "tool_calls": [
                        {
                            "id": call.id,
                            "name": call.name,
                            "arguments": dict(call.arguments),
                        }
                        for call in row.tool_calls
                    ],
                }
                for row in request.messages
            ],
            "tools": [
                {
                    "name": row.name,
                    "description": row.description,
                    "input_schema": dict(row.input_schema),
                }
                for row in request.tools
            ],
            "tool_choice": request.tool_choice.value,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "response_contract": (
                {
                    "name": request.response_contract.name,
                    "version": request.response_contract.version,
                    "schema": request.response_contract.schema_dict(),
                }
                if request.response_contract
                else None
            ),
            "metadata": dict(request.metadata),
        }
    )


def _verify_fixture(root: Path, commitment: DomainFixtureCommitment) -> Path:
    path = (root / PurePosixPath(commitment.relative_path)).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError("calibration fixture must remain inside the project")
    if hashlib.sha256(path.read_bytes()).hexdigest() != commitment.sha256:
        raise ValueError("calibration fixture digest does not match")
    return path


def _protected_values(paths: tuple[str | Path, ...], root: Path) -> set[str]:
    values: set[str] = set()
    sensitive_keys = {
        "case_id",
        "run_id",
        "user_utterance",
        "injected_evidence_text",
        "forbidden_output_markers",
        "sha256",
    }

    def visit(value, key: str | None = None) -> None:
        if isinstance(value, dict):
            for child_key, child in value.items():
                visit(child, str(child_key))
        elif isinstance(value, list):
            for child in value:
                visit(child, key)
        elif key in sensitive_keys and isinstance(value, str) and value:
            values.add(value)

    for raw_path in paths:
        path = Path(raw_path).resolve()
        payload = json.loads(path.read_text(encoding="utf-8"))
        visit(payload)
        for relative in _relative_paths(payload):
            candidate = (root / PurePosixPath(relative)).resolve()
            if candidate.is_relative_to(root) and candidate.is_file():
                body = candidate.read_text(encoding="utf-8")
                values.add(body)
                values.add(hashlib.sha256(candidate.read_bytes()).hexdigest())
    return values


def _relative_paths(value) -> tuple[str, ...]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "relative_path" and isinstance(child, str):
                found.append(child)
            else:
                found.extend(_relative_paths(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_relative_paths(child))
    return tuple(found)


def _calibration_sensitive_values(
    artifact: ResourceCalibrationArtifact,
) -> set[str]:
    values: set[str] = set()
    for row in artifact.profiles:
        values.update(
            {
                row.case_id,
                row.run_id,
                row.user_utterance,
                row.draft_text,
                row.invalid_evaluation_text,
                row.player_summary.sha256,
                row.deterministic_report.sha256,
                *row.tool_queries,
            }
        )
        if row.injected_evidence_text:
            values.add(row.injected_evidence_text)
    return values


def _round_up(value: int, quantum: int) -> int:
    if value < 0 or quantum <= 0:
        raise ValueError("round-up inputs must be non-negative and positive")
    return ((value + quantum - 1) // quantum) * quantum


def _multiply_ratio_up(value: int, numerator: int, denominator: int) -> int:
    if value < 0 or numerator <= 0 or denominator <= 0:
        raise ValueError("ratio inputs are invalid")
    return (value * numerator + denominator - 1) // denominator


def _round_decimal_up(value: Decimal, quantum: Decimal) -> Decimal:
    return (value / quantum).to_integral_value(rounding=ROUND_CEILING) * quantum


def _digest_json(value) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
            default=str,
        ).encode("utf-8")
    ).hexdigest()


__all__ = [
    "CALIBRATION_STAGES",
    "CalibrationIncompleteError",
    "CalibrationSimulationResult",
    "CalibrationStage",
    "FrozenCalibrationRequestSet",
    "ImmutableResourceCalibrationOutput",
    "RealResourceCalibrationResult",
    "ResourceCalibrationAdjudication",
    "ResourceCalibrationAdmission",
    "ResourceCalibrationRequestSnapshot",
    "ResourceCalibrationRunAdmission",
    "ResourceCalibrationUsageObservation",
    "V3ResourceBudgetDecision",
    "V3ResourceBudgetRecord",
    "build_resource_calibration_adjudication",
    "build_v3_resource_budget_record",
    "capture_resource_calibration_requests",
    "deepseek_resource_calibration_policy",
    "derive_v3_resource_budget",
    "load_resource_calibration_profiles",
    "prepare_resource_calibration_admission",
    "prepare_resource_calibration_run_admission",
    "run_real_resource_calibration",
    "simulate_resource_calibration",
]
