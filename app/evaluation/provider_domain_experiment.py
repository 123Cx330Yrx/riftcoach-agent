"""Fail-closed coordination for one frozen Provider domain held-out run."""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Literal, Protocol

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from app.providers.errors import ProviderError
from app.providers.protocol import LLMProvider

from .domain_e2e import (
    DomainCandidate,
    DomainCandidateCase,
    DomainDatasetRole,
    DomainEvaluationCase,
    DomainEvaluationDataset,
    DomainEvaluationResult,
    DomainCaseResult,
    evaluate_domain_candidate,
    validate_domain_dataset_usage,
)
from .provider_adoption import (
    ExperimentBudgetedProvider,
    ExperimentControlSnapshot,
    ExperimentFailureCode,
    ExperimentPreparationReport,
    ExperimentStopController,
    ProviderResourceLedger,
    ResourceLedgerSnapshot,
    classify_provider_error,
    deepseek_experiment_policy,
)
from .provider_protocol_experiment import (
    ProviderAdapterProtocolExperimentRecord,
)


NonBlankText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
SafeCodeText = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Za-z][A-Za-z0-9_.:-]*$"),
]
SafeRuntimeCodeText = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z][a-z0-9_]{0,127}$"),
]
SafeToolNameText = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z][a-z0-9_.]{0,127}$"),
]
SafeEvidenceIdText = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,255}$"),
]
Sha256Text = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]

_DOMAIN_SCOPE = "domain"
_PROTOCOL_SCOPE = "adapter_protocol"
_CASE_MAX_CALLS = 4
_CASE_MAX_TOKENS = 4000


class DomainCaseExecutionPlan(BaseModel):
    """Public identity of sealed case inputs, never their raw contents."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    plan_id: SafeCodeText
    plan_version: NonBlankText
    plan_sha256: Sha256Text
    case_ids: tuple[NonBlankText, ...]

    @model_validator(mode="after")
    def validate_cases(self) -> "DomainCaseExecutionPlan":
        if not self.case_ids or len(set(self.case_ids)) != len(self.case_ids):
            raise ValueError("execution plan case IDs must be non-empty and unique")
        return self


class DomainCaseSemanticObservation(BaseModel):
    """Allowlisted case semantics without prompts, reports or resource claims."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: NonBlankText
    normalized_response_count: int = Field(ge=0, le=_CASE_MAX_CALLS)
    safe_provider_error_code: SafeRuntimeCodeText | None = None
    agent_status: Literal["completed", "stopped", "failed"] | None = None
    agent_stop_reason: SafeRuntimeCodeText | None = None
    proposed_tool_names: tuple[SafeToolNameText, ...] = ()
    successful_tool_names: tuple[SafeToolNameText, ...] = ()
    evidence_source_ids: tuple[SafeEvidenceIdText, ...] = ()
    fact_check_passed: bool | None = None
    citation_check_passed: bool | None = None
    injection_check_passed: bool | None = None
    evaluation_validated: bool
    evaluation_score: int | None = Field(default=None, ge=0, le=100)
    terminal_status: Literal["published", "degraded", "rejected"] | None
    terminal_reason: SafeRuntimeCodeText | None = None
    provenance_sha256: Sha256Text

    @model_validator(mode="after")
    def validate_semantics(self) -> "DomainCaseSemanticObservation":
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
        if not set(self.proposed_tool_names).issubset({"knowledge.search"}):
            raise ValueError("case observation contains an unapproved tool name")
        if self.evaluation_validated is not (self.evaluation_score is not None):
            raise ValueError(
                "validated evaluation and score must appear together"
            )
        if self.terminal_status is None and self.terminal_reason is not None:
            raise ValueError("terminal reason requires a terminal status")
        return self


class DomainCaseExecutor(Protocol):
    execution_plan: DomainCaseExecutionPlan

    def execute(
        self,
        *,
        case: DomainEvaluationCase,
        provider: LLMProvider,
    ) -> DomainCaseSemanticObservation:
        """Run one case and return only allowlisted semantic observations."""


class PriorProtocolEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider_id: NonBlankText
    requested_model: NonBlankText
    code_sha: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
    result_sha256: Sha256Text
    calls_used: Literal[3]
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0, le=_CASE_MAX_TOKENS)
    estimated_cost: Decimal = Field(ge=0)

    @model_validator(mode="after")
    def validate_tokens(self) -> "PriorProtocolEvidence":
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("prior protocol token total is inconsistent")
        return self


class LoadedProtocolArtifact(BaseModel):
    """Parsed protocol evidence bound to the exact bytes read from disk."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    record: ProviderAdapterProtocolExperimentRecord
    result_sha256: Sha256Text


class DeepSeekDomainRunAdmission(BaseModel):
    """No-I/O control-plane result required before Provider construction."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    experiment_id: Sha256Text
    preparation: ExperimentPreparationReport
    prior_protocol: PriorProtocolEvidence
    execution_plan: DomainCaseExecutionPlan
    initial_resources: ResourceLedgerSnapshot

    @model_validator(mode="after")
    def validate_identity(self) -> "DeepSeekDomainRunAdmission":
        expected = _experiment_id(
            self.preparation,
            self.prior_protocol,
            self.execution_plan,
        )
        if self.experiment_id != expected:
            raise ValueError("domain admission experiment identity is inconsistent")
        return self


class DomainCaseExecutionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: NonBlankText
    status: Literal["executed", "failed", "skipped"]
    failure_code: ExperimentFailureCode | None = None
    observation: DomainCandidateCase | None = None
    evaluation: DomainCaseResult | None = None

    @model_validator(mode="after")
    def validate_status(self) -> "DomainCaseExecutionRecord":
        if self.status == "executed":
            if self.observation is None or self.evaluation is None:
                raise ValueError("executed case requires observation and evaluation")
        elif self.observation is not None or self.evaluation is not None:
            raise ValueError("failed or skipped case cannot claim an observation")
        if self.status in {"failed", "skipped"} and self.failure_code is None:
            raise ValueError("failed or skipped case requires a safe failure code")
        if self.observation is not None and self.observation.case_id != self.case_id:
            raise ValueError("case observation identity mismatch")
        if self.evaluation is not None and self.evaluation.case_id != self.case_id:
            raise ValueError("case evaluation identity mismatch")
        return self


class ProviderDomainExperimentRecord(BaseModel):
    """Immutable public-safe result for one domain held-out attempt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    experiment_id: Sha256Text
    run_timestamp_utc: datetime
    preparation: ExperimentPreparationReport
    prior_protocol: PriorProtocolEvidence
    execution_plan: DomainCaseExecutionPlan
    resources: ResourceLedgerSnapshot
    control: ExperimentControlSnapshot
    domain_calls_used: int = Field(ge=0, le=12)
    domain_total_tokens: int = Field(ge=0)
    domain_estimated_cost: Decimal = Field(ge=0)
    cases: tuple[DomainCaseExecutionRecord, ...]
    candidate: DomainCandidate | None = None
    evaluation: DomainEvaluationResult | None = None
    held_out_executed: bool
    admitted: bool

    @model_validator(mode="after")
    def validate_composition(self) -> "ProviderDomainExperimentRecord":
        if tuple(row.case_id for row in self.cases) != self.execution_plan.case_ids:
            raise ValueError("record cases must follow the execution plan order")
        scope_calls = {row.scope: row.calls_used for row in self.resources.scope_calls}
        scope_tokens = {
            row.scope: row.total_tokens for row in self.resources.scope_tokens
        }
        if scope_calls.get(_PROTOCOL_SCOPE) != self.prior_protocol.calls_used:
            raise ValueError("resource ledger lost prior protocol calls")
        if scope_calls.get(_DOMAIN_SCOPE) != self.domain_calls_used:
            raise ValueError("domain call total does not match the ledger")
        if scope_tokens.get(_PROTOCOL_SCOPE) != self.prior_protocol.total_tokens:
            raise ValueError("resource ledger lost prior protocol tokens")
        if scope_tokens.get(_DOMAIN_SCOPE) != self.domain_total_tokens:
            raise ValueError("domain token total does not match the ledger")
        if self.resources.calls_used != (
            self.prior_protocol.calls_used + self.domain_calls_used
        ):
            raise ValueError("cumulative call count is inconsistent")
        if self.resources.estimated_cost != (
            self.prior_protocol.estimated_cost + self.domain_estimated_cost
        ):
            raise ValueError("cumulative estimated cost is inconsistent")
        actually_executed = any(row.status != "skipped" for row in self.cases)
        if self.held_out_executed is not actually_executed:
            raise ValueError("held_out_executed does not match case state")

        all_executed = all(row.status == "executed" for row in self.cases)
        if (self.candidate is not None or self.evaluation is not None) is not (
            self.candidate is not None and self.evaluation is not None
        ):
            raise ValueError("candidate and evaluation must appear together")
        if all_executed is not (self.candidate is not None):
            raise ValueError("complete cases and aggregate evidence must agree")

        expected_admission = all(
            (
                all_executed,
                all(row.failure_code is None for row in self.cases),
                self.evaluation is not None,
                self.evaluation is not None
                and self.evaluation.task_outcome_accuracy == 1.0,
                self.evaluation is not None
                and self.evaluation.failure_classification_accuracy == 1.0,
                self.evaluation is not None
                and self.evaluation.unsafe_publication_rate == 0.0,
                self.resources.stop_code is None,
                self.control.global_stop is None,
                not self.control.provider_stops,
            )
        )
        if self.admitted is not expected_admission:
            raise ValueError("admitted must match all mandatory domain evidence")
        return self


class ImmutableDomainExperimentOutput:
    """Reserve one output before I/O and leave a fail-closed sentinel on crash."""

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
    ) -> "ImmutableDomainExperimentOutput":
        if not _is_sha256(experiment_id):
            raise ValueError("experiment_id must be a SHA-256 digest")
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        stream = output.open("x", encoding="utf-8", newline="\n")
        return cls(output, experiment_id, stream)

    def commit(self, record: ProviderDomainExperimentRecord) -> None:
        if self._committed or self._stream.closed:
            raise RuntimeError("domain experiment output is already finalized")
        if not isinstance(record, ProviderDomainExperimentRecord):
            raise TypeError("record must be a ProviderDomainExperimentRecord")
        if record.experiment_id != self.experiment_id:
            raise ValueError("record does not match the reserved experiment")
        self._stream.write(record.model_dump_json(indent=2))
        self._stream.write("\n")
        self._stream.flush()
        self._stream.close()
        self._committed = True

    def abandon(self) -> None:
        """Close but retain the exclusive sentinel so a crash cannot rerun."""

        if not self._stream.closed:
            self._stream.close()


def domain_dataset_sha256(dataset: DomainEvaluationDataset) -> str:
    if not isinstance(dataset, DomainEvaluationDataset):
        raise TypeError("dataset must be a DomainEvaluationDataset")
    return _digest_json(dataset.model_dump(mode="json"))


def load_protocol_artifact(
    path: str | Path,
) -> LoadedProtocolArtifact:
    raw = Path(path).read_bytes()
    record = ProviderAdapterProtocolExperimentRecord.model_validate_json(raw)
    return LoadedProtocolArtifact(
        record=record,
        result_sha256=hashlib.sha256(raw).hexdigest(),
    )


def prepare_deepseek_domain_heldout_run(
    *,
    preparation: ExperimentPreparationReport,
    protocol_record: ProviderAdapterProtocolExperimentRecord,
    protocol_result_sha256: str,
    dataset: DomainEvaluationDataset,
    execution_plan: DomainCaseExecutionPlan,
) -> DeepSeekDomainRunAdmission:
    """Validate every local identity without accepting or constructing a Provider."""

    prior = _require_frozen_control_inputs(
        preparation=preparation,
        protocol_record=protocol_record,
        protocol_result_sha256=protocol_result_sha256,
        dataset=dataset,
        execution_plan=execution_plan,
    )
    return DeepSeekDomainRunAdmission(
        experiment_id=_experiment_id(preparation, prior, execution_plan),
        preparation=preparation,
        prior_protocol=prior,
        execution_plan=execution_plan,
        initial_resources=protocol_record.resources,
    )


def run_deepseek_domain_heldout_experiment(
    *,
    admission: DeepSeekDomainRunAdmission,
    dataset: DomainEvaluationDataset,
    provider: LLMProvider,
    case_executor: DomainCaseExecutor,
    clock: Callable[[], float] = time.monotonic,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> ProviderDomainExperimentRecord:
    """Run cases sequentially under inherited budgets and safe stop rules."""

    policy = deepseek_experiment_policy()
    if not isinstance(admission, DeepSeekDomainRunAdmission):
        raise TypeError("admission must be a DeepSeekDomainRunAdmission")
    preparation = admission.preparation
    prior = admission.prior_protocol
    execution_plan = admission.execution_plan
    if (
        provider.provider_name != policy.provider_id
        or provider.model_name != policy.model
    ):
        raise ValueError("runtime Provider does not match domain admission")
    if not all(
        (
            provider.capabilities.text_chat,
            provider.capabilities.tool_calling,
            provider.capabilities.structured_output,
        )
    ):
        raise ValueError("runtime Provider lacks admitted domain capabilities")
    if case_executor.execution_plan != execution_plan:
        raise ValueError("case executor does not match the admitted execution plan")
    if (
        domain_dataset_sha256(dataset) != preparation.dataset_sha256
        or tuple(row.case_id for row in dataset.cases) != execution_plan.case_ids
        or admission.experiment_id
        != _experiment_id(preparation, prior, execution_plan)
    ):
        raise ValueError("runtime Dataset does not match domain admission")
    ledger = ProviderResourceLedger(
        policy,
        initial_snapshot=admission.initial_resources,
    )
    controller = ExperimentStopController(
        allowed_provider_ids=(policy.provider_id,)
    )
    records: list[DomainCaseExecutionRecord] = []
    observations: list[DomainCandidateCase] = []
    stop_code: ExperimentFailureCode | None = None

    for case in dataset.cases:
        if stop_code is not None:
            records.append(
                DomainCaseExecutionRecord(
                    case_id=case.case_id,
                    status="skipped",
                    failure_code=stop_code,
                )
            )
            continue

        _require_case_resource_contract(case)
        ledger.register_case(
            case.case_id,
            max_calls=_CASE_MAX_CALLS,
            max_observed_tokens=_CASE_MAX_TOKENS,
        )
        before = ledger.snapshot()
        controlled = ExperimentBudgetedProvider(
            provider=provider,
            ledger=ledger,
            controller=controller,
            scope=_DOMAIN_SCOPE,
            case_id=case.case_id,
            clock=clock,
        )
        try:
            semantic = case_executor.execute(case=case, provider=controlled)
            if not isinstance(semantic, DomainCaseSemanticObservation):
                raise TypeError("case executor returned an invalid observation")
            if semantic.case_id != case.case_id:
                raise ValueError("case executor observation identity mismatch")
        except ProviderError as exc:
            stop_code = classify_provider_error(exc)
            controller.stop_provider(policy.provider_id, stop_code)
            records.append(
                DomainCaseExecutionRecord(
                    case_id=case.case_id,
                    status="failed",
                    failure_code=stop_code,
                )
            )
            continue
        except Exception:
            stop_code = ExperimentFailureCode.DOMAIN_CASE_OBSERVATION_INVALID
            controller.stop_provider(policy.provider_id, stop_code)
            records.append(
                DomainCaseExecutionRecord(
                    case_id=case.case_id,
                    status="failed",
                    failure_code=stop_code,
                )
            )
            continue

        after = ledger.snapshot()
        observation = _candidate_case_from_semantics(
            semantic,
            before=before,
            after=after,
        )
        case_result = _evaluate_one_case(
            dataset=dataset,
            case=case,
            observation=observation,
            provider_id=policy.provider_id,
        )
        failure_code = _case_stop_code(case_result)
        if failure_code is ExperimentFailureCode.UNSAFE_PUBLICATION:
            controller.record_case_failures(
                provider_id=policy.provider_id,
                failure_codes=(failure_code,),
            )
        elif failure_code is not None:
            controller.stop_provider(policy.provider_id, failure_code)
        stop_code = failure_code
        observations.append(observation)
        records.append(
            DomainCaseExecutionRecord(
                case_id=case.case_id,
                status="executed",
                failure_code=failure_code,
                observation=observation,
                evaluation=case_result,
            )
        )

    final_resources = ledger.snapshot()
    domain_scope = _scope_resources(final_resources, _DOMAIN_SCOPE)
    candidate = None
    evaluation = None
    if len(observations) == len(dataset.cases):
        candidate = DomainCandidate(
            schema_version=dataset.schema_version,
            candidate_id=(
                f"deepseek-v4-pro-domain-{admission.experiment_id[:16]}"
            ),
            candidate_kind="real_provider_recorded",
            dataset_id=dataset.dataset_id,
            dataset_version=dataset.dataset_version,
            contract_snapshot=dataset.contract_snapshot,
            external_provider_calls=domain_scope["calls"],
            case_count=len(observations),
            cases=tuple(observations),
        )
        evaluation = evaluate_domain_candidate(dataset, candidate)

    control = controller.snapshot()
    all_cases_clean = all(
        row.status == "executed" and row.failure_code is None
        for row in records
    )
    admitted = all(
        (
            all_cases_clean,
            evaluation is not None,
            evaluation is not None and evaluation.task_outcome_accuracy == 1.0,
            evaluation is not None
            and evaluation.failure_classification_accuracy == 1.0,
            evaluation is not None
            and evaluation.unsafe_publication_rate == 0.0,
            final_resources.stop_code is None,
            control.global_stop is None,
            not control.provider_stops,
        )
    )
    return ProviderDomainExperimentRecord(
        experiment_id=admission.experiment_id,
        run_timestamp_utc=now(),
        preparation=preparation,
        prior_protocol=prior,
        execution_plan=execution_plan,
        resources=final_resources,
        control=control,
        domain_calls_used=domain_scope["calls"],
        domain_total_tokens=domain_scope["tokens"],
        domain_estimated_cost=domain_scope["cost"],
        cases=tuple(records),
        candidate=candidate,
        evaluation=evaluation,
        held_out_executed=any(row.status != "skipped" for row in records),
        admitted=admitted,
    )


def write_immutable_domain_experiment_record(
    path: str | Path,
    record: ProviderDomainExperimentRecord,
) -> None:
    if not isinstance(record, ProviderDomainExperimentRecord):
        raise TypeError("record must be a ProviderDomainExperimentRecord")
    reservation = ImmutableDomainExperimentOutput.reserve(
        path,
        experiment_id=record.experiment_id,
    )
    reservation.commit(record)


def _require_frozen_control_inputs(
    *,
    preparation: ExperimentPreparationReport,
    protocol_record: ProviderAdapterProtocolExperimentRecord,
    protocol_result_sha256: str,
    dataset: DomainEvaluationDataset,
    execution_plan: DomainCaseExecutionPlan,
) -> PriorProtocolEvidence:
    policy = deepseek_experiment_policy()
    for value, expected, label in (
        (preparation.provider_id, policy.provider_id, "preparation Provider"),
        (preparation.requested_model, policy.model, "preparation model"),
    ):
        if value != expected:
            raise ValueError(f"{label} does not match the frozen experiment")
    if (
        preparation.code_sha != preparation.public_ci_sha
        or not preparation.public_ci_success_confirmed
        or not preparation.local_preflight_passed
        or preparation.external_provider_calls != 0
        or preparation.held_out_executed
    ):
        raise ValueError("current experiment preparation is not admitted")
    if (
        preparation.protocol_max_calls != 3
        or preparation.domain_max_calls != 12
        or preparation.cumulative_max_calls != 15
        or preparation.maximum_total_tokens != 16_000
        or preparation.maximum_output_tokens_per_request != 1024
        or preparation.maximum_estimated_cost != Decimal("0.10")
        or preparation.currency != "USD"
    ):
        raise ValueError("current preparation resource policy has drifted")

    validate_domain_dataset_usage(
        dataset,
        DomainDatasetRole.HELD_OUT,
        confirm_rules_frozen=True,
    )
    if (
        (dataset.dataset_id, dataset.dataset_version)
        != (preparation.dataset_id, preparation.dataset_version)
        or domain_dataset_sha256(dataset) != preparation.dataset_sha256
        or dataset.contract_snapshot.prompt_context_snapshot_id
        != preparation.prompt_context_snapshot_id
        or dataset.contract_snapshot.prompt_context_snapshot_sha256
        != preparation.prompt_context_snapshot_sha256
        or dataset.contract_snapshot.evaluation_contract
        != preparation.evaluation_contract
    ):
        raise ValueError("held-out Dataset identity does not match preparation")
    if execution_plan.case_ids != tuple(row.case_id for row in dataset.cases):
        raise ValueError("execution plan case order does not match held-out")
    for case in dataset.cases:
        _require_case_resource_contract(case)

    if not isinstance(protocol_record, ProviderAdapterProtocolExperimentRecord):
        raise TypeError("protocol_record must use the admitted record contract")
    if not _is_sha256(protocol_result_sha256):
        raise ValueError("protocol result SHA-256 is invalid")
    protocol = protocol_record.protocol
    resources = protocol_record.resources
    protocol_scope = {
        row.scope: row.calls_used for row in resources.scope_calls
    }
    if (
        not protocol.admitted
        or protocol.calls_used != 3
        or protocol_record.held_out_executed
        or protocol.provider_id != policy.provider_id
        or protocol.requested_model != policy.model
        or protocol_record.preparation.provider_id != policy.provider_id
        or protocol_record.preparation.requested_model != policy.model
        or protocol_record.preparation.dataset_id != dataset.dataset_id
        or protocol_record.preparation.dataset_version != dataset.dataset_version
        or protocol_record.preparation.dataset_sha256
        != preparation.dataset_sha256
        or protocol_record.preparation.prompt_context_snapshot_sha256
        != preparation.prompt_context_snapshot_sha256
        or protocol_record.preparation.evaluation_contract
        != preparation.evaluation_contract
        or resources.stop_code is not None
        or resources.calls_used != 3
        or resources.total_tokens > _CASE_MAX_TOKENS
        or resources.estimated_cost > policy.max_estimated_cost
        or protocol_scope.get(_PROTOCOL_SCOPE) != 3
        or protocol_scope.get(_DOMAIN_SCOPE) != 0
        or protocol_record.control.global_stop is not None
        or protocol_record.control.provider_stops
    ):
        raise ValueError("prior protocol evidence is not admitted for this run")

    return PriorProtocolEvidence(
        provider_id=protocol.provider_id,
        requested_model=protocol.requested_model,
        code_sha=protocol.code_sha,
        result_sha256=protocol_result_sha256,
        calls_used=3,
        input_tokens=resources.input_tokens,
        output_tokens=resources.output_tokens,
        total_tokens=resources.total_tokens,
        estimated_cost=resources.estimated_cost,
    )


def _require_case_resource_contract(case: DomainEvaluationCase) -> None:
    requirements = case.requirements
    if (
        requirements.maximum_provider_calls != _CASE_MAX_CALLS
        or requirements.maximum_total_tokens != _CASE_MAX_TOKENS
    ):
        raise ValueError("held-out case resource contract has drifted")


def _candidate_case_from_semantics(
    semantic: DomainCaseSemanticObservation,
    *,
    before: ResourceLedgerSnapshot,
    after: ResourceLedgerSnapshot,
) -> DomainCandidateCase:
    calls = after.calls_used - before.calls_used
    input_tokens = after.input_tokens - before.input_tokens
    output_tokens = after.output_tokens - before.output_tokens
    latency_ms = after.latency_ms - before.latency_ms
    estimated_cost = after.estimated_cost - before.estimated_cost
    return DomainCandidateCase(
        case_id=semantic.case_id,
        provider_calls=calls,
        normalized_response_count=semantic.normalized_response_count,
        safe_provider_error_code=semantic.safe_provider_error_code,
        agent_status=semantic.agent_status,
        agent_stop_reason=semantic.agent_stop_reason,
        proposed_tool_names=semantic.proposed_tool_names,
        successful_tool_names=semantic.successful_tool_names,
        evidence_source_ids=semantic.evidence_source_ids,
        fact_check_passed=semantic.fact_check_passed,
        citation_check_passed=semantic.citation_check_passed,
        injection_check_passed=semantic.injection_check_passed,
        evaluation_validated=semantic.evaluation_validated,
        evaluation_score=semantic.evaluation_score,
        terminal_status=semantic.terminal_status,
        terminal_reason=semantic.terminal_reason,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost=float(estimated_cost),
        provenance_sha256=semantic.provenance_sha256,
    )


def _evaluate_one_case(
    *,
    dataset: DomainEvaluationDataset,
    case: DomainEvaluationCase,
    observation: DomainCandidateCase,
    provider_id: str,
) -> DomainCaseResult:
    one_dataset = DomainEvaluationDataset.model_validate(
        {
            **dataset.model_dump(mode="json"),
            "case_count": 1,
            "cases": [case.model_dump(mode="json")],
        }
    )
    candidate = DomainCandidate(
        schema_version=dataset.schema_version,
        candidate_id=f"{provider_id}-{case.case_id}",
        candidate_kind="real_provider_recorded",
        dataset_id=dataset.dataset_id,
        dataset_version=dataset.dataset_version,
        contract_snapshot=dataset.contract_snapshot,
        external_provider_calls=observation.provider_calls,
        case_count=1,
        cases=(observation,),
    )
    return evaluate_domain_candidate(one_dataset, candidate).cases[0]


def _case_stop_code(
    result: DomainCaseResult,
) -> ExperimentFailureCode | None:
    if result.unsafe_publication:
        return ExperimentFailureCode.UNSAFE_PUBLICATION
    if not result.task_outcome_match or not result.failure_classification_match:
        return ExperimentFailureCode.DOMAIN_CASE_OUTCOME_MISMATCH
    return None


def _scope_resources(
    snapshot: ResourceLedgerSnapshot,
    scope: str,
) -> dict[str, int | Decimal]:
    calls = next(row.calls_used for row in snapshot.scope_calls if row.scope == scope)
    tokens = next(
        row.total_tokens for row in snapshot.scope_tokens if row.scope == scope
    )
    scope_input = next(
        row.input_tokens for row in snapshot.scope_tokens if row.scope == scope
    )
    scope_output = next(
        row.output_tokens for row in snapshot.scope_tokens if row.scope == scope
    )
    policy = deepseek_experiment_policy()
    cost = (
        Decimal(scope_input) * policy.input_cost_per_million
        + Decimal(scope_output) * policy.output_cost_per_million
    ) / Decimal("1000000")
    return {"calls": calls, "tokens": tokens, "cost": cost}


def _experiment_id(
    preparation: ExperimentPreparationReport,
    prior: PriorProtocolEvidence,
    plan: DomainCaseExecutionPlan,
) -> str:
    return _digest_json(
        {
            "provider_id": preparation.provider_id,
            "model": preparation.requested_model,
            "code_sha": preparation.code_sha,
            "dataset_sha256": preparation.dataset_sha256,
            "prompt_context_snapshot_sha256": (
                preparation.prompt_context_snapshot_sha256
            ),
            "protocol_result_sha256": prior.result_sha256,
            "execution_plan_sha256": plan.plan_sha256,
        }
    )


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


def _is_sha256(value: str) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


__all__ = [
    "DeepSeekDomainRunAdmission",
    "DomainCaseExecutionPlan",
    "DomainCaseExecutor",
    "DomainCaseSemanticObservation",
    "ImmutableDomainExperimentOutput",
    "LoadedProtocolArtifact",
    "PriorProtocolEvidence",
    "ProviderDomainExperimentRecord",
    "domain_dataset_sha256",
    "load_protocol_artifact",
    "prepare_deepseek_domain_heldout_run",
    "run_deepseek_domain_heldout_experiment",
    "write_immutable_domain_experiment_record",
]
