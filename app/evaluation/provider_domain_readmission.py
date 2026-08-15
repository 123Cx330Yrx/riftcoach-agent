"""Fresh DeepSeek domain readmission contracts with no Provider I/O surface."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from .domain_e2e import (
    DomainDatasetRole,
    DomainEvaluationDataset,
    validate_domain_dataset_usage,
)
from .prompt_context_identity import (
    PromptContextSnapshot,
    case_context_sha256,
)
from .provider_adoption import (
    ExperimentPreparationReport,
    deepseek_experiment_policy,
)
from .provider_domain_experiment import (
    DeepSeekDomainRunAdmission,
    DomainCaseExecutionPlan,
    ProviderDomainExperimentRecord,
    domain_dataset_sha256,
    load_protocol_artifact,
    prepare_deepseek_fresh_domain_heldout_run,
)
from .provider_domain_plan import (
    DomainCaseContextCommitment,
    LoadedDomainCaseInputPlan,
)
from .provider_protocol_experiment import ProviderAdapterProtocolExperimentRecord


GitShaText = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
Sha256Text = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
NonBlankText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

_EXPECTED_PROTOCOL_SHA256 = (
    "575e8f5423bde6b34a692c63f90764313ba820772ae974109a4328b3dba086e1"
)
_EXPECTED_REJECTED_DOMAIN_SHA256 = (
    "fbd1251af98daa9e767de56a35100025807ce96026d6b3b3497e33dd30ad989e"
)
_EXPECTED_REPAIR_SHA = "037a47fecf058b2430efeeb59858e24cdb3b28eb"
_EXPECTED_REPAIR_CI_RUN_ID = 31817798170
_EXPECTED_REJECTION_ERROR = "unsupported_parallel_tool_calls"
_EXPECTED_FRESH_ASSET_SHA = "1e44b130f4f054e06ab92fcc437dcd1fa74a13e8"
_EXPECTED_FRESH_ASSET_CI_RUN_ID = 31861960565
_EXPECTED_FRESH_DATASET_FILE_SHA256 = (
    "db95ac300aebf82bd92279f18ad5de26f539eac385c798741967b9f81d60da3c"
)
_EXPECTED_FRESH_DATASET_SHA256 = (
    "87e9f567514573dabc7685b3a7634c49db99cadbad32bef7b9d51b92289fd05c"
)
_EXPECTED_FRESH_PLAN_FILE_SHA256 = (
    "878d3ec47ddfa5cc98c13b0a183b1f665b7d7a0bbc8864665fab976864794987"
)
_EXPECTED_FRESH_SNAPSHOT_FILE_SHA256 = (
    "45bd09b41ef7a984489dc4e833c8dc2737253e2e99958d2c97be47a2f5888a0f"
)
_EXPECTED_FRESH_SUMMARY_FILE_SHA256 = (
    "96757726eaa2bba44cb416ee3d6696c8dcb8ce6a457c27655f991a667a35323c"
)
_EXPECTED_FRESH_REPORT_FILE_SHA256 = (
    "a8434b0f85031ee75da055c267cb9ab81866de5c3ded8fa07e2b711e2524b4b5"
)
_EXPECTED_FRESH_DATASET_ID = "domain-e2e-v2-secure-held-out"
_EXPECTED_FRESH_DATASET_VERSION = "2.0.0"
_EXPECTED_FRESH_CASES = (
    "adoption_v2_form_baseline",
    "adoption_v2_user_note_boundary",
    "adoption_v2_knowledge_note_boundary",
)


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class MultiToolRepairEvidence(_FrozenModel):
    """Public exact-SHA evidence for the development-only batch fix."""

    code_sha: GitShaText
    public_ci_sha: GitShaText
    public_ci_run_id: int = Field(gt=0)
    public_ci_success_confirmed: Literal[True]

    @model_validator(mode="after")
    def validate_frozen_repair(self) -> "MultiToolRepairEvidence":
        if (
            self.code_sha != _EXPECTED_REPAIR_SHA
            or self.public_ci_sha != self.code_sha
            or self.public_ci_run_id != _EXPECTED_REPAIR_CI_RUN_ID
        ):
            raise ValueError("multi-ToolCall repair evidence does not match ADR-0022")
        return self


class HistoricalDomainEvidence(_FrozenModel):
    """Safe summary of immutable protocol and rejected domain result bytes."""

    protocol_result_sha256: Sha256Text
    rejected_domain_result_sha256: Sha256Text
    protocol_calls: Literal[3]
    protocol_input_tokens: Literal[1303]
    protocol_output_tokens: Literal[125]
    protocol_total_tokens: Literal[1428]
    protocol_estimated_cost: Decimal = Field(ge=0)
    rejected_domain_calls: Literal[1]
    total_historical_calls: Literal[4]
    rejected_domain_usage_status: Literal["unknown_before_normalization"]
    rejected_domain_total_tokens: None = None
    rejected_domain_estimated_cost: None = None
    rejection_error_code: Literal["unsupported_parallel_tool_calls"]
    multi_tool_repair: MultiToolRepairEvidence

    @model_validator(mode="after")
    def validate_history(self) -> "HistoricalDomainEvidence":
        if self.protocol_result_sha256 != _EXPECTED_PROTOCOL_SHA256:
            raise ValueError("historical protocol bytes do not match the frozen result")
        if self.rejected_domain_result_sha256 != _EXPECTED_REJECTED_DOMAIN_SHA256:
            raise ValueError(
                "historical rejected domain bytes do not match the frozen result"
            )
        if self.total_historical_calls != (
            self.protocol_calls + self.rejected_domain_calls
        ):
            raise ValueError("historical call accounting is inconsistent")
        if self.protocol_total_tokens != (
            self.protocol_input_tokens + self.protocol_output_tokens
        ) or self.protocol_estimated_cost != Decimal("0.00221496"):
            raise ValueError("historical protocol resource evidence has drifted")
        return self


class FreshDomainAssetFreezeEvidence(_FrozenModel):
    """Exact public evidence for the Fresh-Gate 3 static asset bundle."""

    code_sha: GitShaText
    public_ci_sha: GitShaText
    public_ci_run_id: int = Field(gt=0)
    public_ci_success_confirmed: Literal[True]
    dataset_file_sha256: Sha256Text
    input_plan_file_sha256: Sha256Text
    prompt_context_snapshot_file_sha256: Sha256Text
    player_summary_file_sha256: Sha256Text
    deterministic_report_file_sha256: Sha256Text

    @model_validator(mode="after")
    def validate_asset_freeze(self) -> "FreshDomainAssetFreezeEvidence":
        expected = {
            "code_sha": _EXPECTED_FRESH_ASSET_SHA,
            "public_ci_sha": _EXPECTED_FRESH_ASSET_SHA,
            "public_ci_run_id": _EXPECTED_FRESH_ASSET_CI_RUN_ID,
            "dataset_file_sha256": _EXPECTED_FRESH_DATASET_FILE_SHA256,
            "input_plan_file_sha256": _EXPECTED_FRESH_PLAN_FILE_SHA256,
            "prompt_context_snapshot_file_sha256": (
                _EXPECTED_FRESH_SNAPSHOT_FILE_SHA256
            ),
            "player_summary_file_sha256": _EXPECTED_FRESH_SUMMARY_FILE_SHA256,
            "deterministic_report_file_sha256": _EXPECTED_FRESH_REPORT_FILE_SHA256,
        }
        if any(getattr(self, key) != value for key, value in expected.items()):
            raise ValueError("Fresh-Gate 3 asset freeze evidence has drifted")
        return self


class FreshDomainHeldOutAdmission(_FrozenModel):
    """Complete no-I/O identity for one explicitly confirmed fresh run."""

    schema_version: Literal["1.0"] = "1.0"
    experiment_id: Sha256Text
    historical: HistoricalDomainEvidence
    asset_freeze: FreshDomainAssetFreezeEvidence
    preparation: ExperimentPreparationReport
    dataset_role: Literal["held_out"]
    dataset_sha256: Sha256Text
    skill_name: Literal["recent-form-review"]
    skill_version: NonBlankText
    evaluation_contract: Literal["coach_evaluation@1.1.0"]
    prompt_context_snapshot_id: NonBlankText
    prompt_context_snapshot_sha256: Sha256Text
    execution_plan: DomainCaseExecutionPlan
    case_context_commitments: tuple[DomainCaseContextCommitment, ...]
    run_admission: DeepSeekDomainRunAdmission
    external_provider_calls: Literal[0] = 0
    held_out_executed: Literal[False] = False
    provider_construction_authorized: Literal[False] = False
    ready_for_explicit_confirmation: Literal[True] = True

    @model_validator(mode="after")
    def validate_identity(self) -> "FreshDomainHeldOutAdmission":
        if tuple(row.case_id for row in self.case_context_commitments) != (
            self.execution_plan.case_ids
        ):
            raise ValueError("held-out Context commitment case order has drifted")
        if (
            self.run_admission.preparation != self.preparation
            or self.run_admission.execution_plan != self.execution_plan
        ):
            raise ValueError("base domain admission does not match fresh evidence")
        expected = _fresh_heldout_experiment_id(
            historical=self.historical,
            asset_freeze=self.asset_freeze,
            preparation=self.preparation,
            run_admission=self.run_admission,
            dataset_sha256=self.dataset_sha256,
            prompt_context_snapshot_sha256=self.prompt_context_snapshot_sha256,
            case_context_commitments=self.case_context_commitments,
        )
        if self.experiment_id != expected:
            raise ValueError("fresh held-out experiment identity is inconsistent")
        return self


class FreshProviderDomainExperimentRecord(_FrozenModel):
    """Immutable envelope preserving readmission and the original domain result."""

    schema_version: Literal["2.0"] = "2.0"
    experiment_id: Sha256Text
    admission: FreshDomainHeldOutAdmission
    domain_result: ProviderDomainExperimentRecord
    explicit_real_call_confirmed: Literal[True]
    held_out_executed: bool
    admitted: bool

    @model_validator(mode="after")
    def validate_result(self) -> "FreshProviderDomainExperimentRecord":
        if self.experiment_id != self.admission.experiment_id:
            raise ValueError("fresh result experiment identity has drifted")
        if self.domain_result.experiment_id != (
            self.admission.run_admission.experiment_id
        ):
            raise ValueError("domain result does not match its base admission")
        if self.held_out_executed is not self.domain_result.held_out_executed:
            raise ValueError("fresh result held-out state is inconsistent")
        if self.admitted is not self.domain_result.admitted:
            raise ValueError("fresh result admission state is inconsistent")
        return self


class FreshDomainDevelopmentAdmission(_FrozenModel):
    """Development-only proof; deliberately incapable of authorizing I/O."""

    schema_version: Literal["1.0"] = "1.0"
    experiment_id: Sha256Text
    historical: HistoricalDomainEvidence
    preparation: ExperimentPreparationReport
    dataset_role: Literal["development"]
    dataset_sha256: Sha256Text
    skill_name: Literal["recent-form-review"]
    skill_version: NonBlankText
    evaluation_contract: Literal["coach_evaluation@1.1.0"]
    prompt_context_snapshot_id: NonBlankText
    prompt_context_snapshot_sha256: Sha256Text
    execution_plan: DomainCaseExecutionPlan
    case_context_commitments: tuple[DomainCaseContextCommitment, ...]
    external_provider_calls: Literal[0] = 0
    held_out_executed: Literal[False] = False
    provider_construction_authorized: Literal[False] = False
    admitted: Literal[True] = True

    @model_validator(mode="after")
    def validate_identity(self) -> "FreshDomainDevelopmentAdmission":
        if not self.case_context_commitments:
            raise ValueError("development admission requires case Context commitments")
        if tuple(row.case_id for row in self.case_context_commitments) != (
            self.execution_plan.case_ids
        ):
            raise ValueError("admission Context commitment case order has drifted")
        expected = _fresh_experiment_id(
            historical=self.historical,
            preparation=self.preparation,
            dataset_sha256=self.dataset_sha256,
            execution_plan=self.execution_plan,
            prompt_context_snapshot_sha256=(
                self.prompt_context_snapshot_sha256
            ),
            case_context_commitments=self.case_context_commitments,
        )
        if self.experiment_id != expected:
            raise ValueError("fresh development experiment identity is inconsistent")
        return self


def load_historical_domain_evidence(
    *,
    protocol_result_path: str | Path,
    rejected_domain_result_path: str | Path,
    multi_tool_repair: MultiToolRepairEvidence,
) -> HistoricalDomainEvidence:
    """Reread exact historical bytes and reduce them to a safe evidence chain."""

    if not isinstance(multi_tool_repair, MultiToolRepairEvidence):
        raise TypeError("multi_tool_repair must use MultiToolRepairEvidence")
    protocol_path = Path(protocol_result_path)
    rejected_path = Path(rejected_domain_result_path)
    protocol_raw = protocol_path.read_bytes()
    rejected_raw = rejected_path.read_bytes()
    protocol_sha = hashlib.sha256(protocol_raw).hexdigest()
    rejected_sha = hashlib.sha256(rejected_raw).hexdigest()
    if protocol_sha != _EXPECTED_PROTOCOL_SHA256:
        raise ValueError("historical protocol bytes do not match the frozen result")
    if rejected_sha != _EXPECTED_REJECTED_DOMAIN_SHA256:
        raise ValueError(
            "historical rejected domain bytes do not match the frozen result"
        )

    protocol = load_protocol_artifact(protocol_path).record
    rejected = ProviderDomainExperimentRecord.model_validate_json(rejected_raw)
    first_case = rejected.cases[0] if rejected.cases else None
    first_observation = first_case.observation if first_case is not None else None
    if (
        not protocol.protocol.admitted
        or protocol.protocol.calls_used != 3
        or protocol.held_out_executed
        or rejected.prior_protocol.result_sha256 != protocol_sha
        or rejected.admitted
        or not rejected.held_out_executed
        or rejected.domain_calls_used != 1
        or rejected.candidate is not None
        or rejected.evaluation is not None
        or first_observation is None
        or first_observation.safe_provider_error_code != _EXPECTED_REJECTION_ERROR
        or tuple(row.status for row in rejected.cases) != (
            "executed",
            "skipped",
            "skipped",
        )
    ):
        raise ValueError("historical DeepSeek evidence semantics have drifted")

    return HistoricalDomainEvidence(
        protocol_result_sha256=protocol_sha,
        rejected_domain_result_sha256=rejected_sha,
        protocol_calls=3,
        protocol_input_tokens=protocol.resources.input_tokens,
        protocol_output_tokens=protocol.resources.output_tokens,
        protocol_total_tokens=protocol.resources.total_tokens,
        protocol_estimated_cost=protocol.resources.estimated_cost,
        rejected_domain_calls=1,
        total_historical_calls=4,
        rejected_domain_usage_status="unknown_before_normalization",
        rejected_domain_total_tokens=None,
        rejected_domain_estimated_cost=None,
        rejection_error_code=_EXPECTED_REJECTION_ERROR,
        multi_tool_repair=multi_tool_repair,
    )


def load_fresh_domain_asset_freeze_evidence(
    *,
    dataset_path: str | Path,
    input_plan_path: str | Path,
    snapshot_path: str | Path,
    loaded_input_plan: LoadedDomainCaseInputPlan,
) -> FreshDomainAssetFreezeEvidence:
    """Read exact Fresh-Gate 3 bytes without exposing any body in the result."""

    if not isinstance(loaded_input_plan, LoadedDomainCaseInputPlan):
        raise TypeError("loaded_input_plan must be a validated input plan")
    evidence = FreshDomainAssetFreezeEvidence(
        code_sha=_EXPECTED_FRESH_ASSET_SHA,
        public_ci_sha=_EXPECTED_FRESH_ASSET_SHA,
        public_ci_run_id=_EXPECTED_FRESH_ASSET_CI_RUN_ID,
        public_ci_success_confirmed=True,
        dataset_file_sha256=_file_sha256(dataset_path),
        input_plan_file_sha256=_file_sha256(input_plan_path),
        prompt_context_snapshot_file_sha256=_file_sha256(snapshot_path),
        player_summary_file_sha256=_file_sha256(
            loaded_input_plan.player_summary_path
        ),
        deterministic_report_file_sha256=_file_sha256(
            loaded_input_plan.deterministic_report_path
        ),
    )
    if evidence.input_plan_file_sha256 != (
        loaded_input_plan.execution_plan.plan_sha256
    ):
        raise ValueError("Fresh-Gate 3 input plan identity has drifted")
    return evidence


def build_fresh_domain_preparation(
    *,
    code_sha: str,
    public_ci_sha: str,
    confirm_public_ci_success: bool,
    dataset: DomainEvaluationDataset,
    frozen_snapshot: PromptContextSnapshot,
) -> ExperimentPreparationReport:
    """Build current-code evidence for V2 without Provider or credential inputs."""

    if (
        not _is_git_sha(code_sha)
        or not _is_git_sha(public_ci_sha)
        or code_sha != public_ci_sha
        or not confirm_public_ci_success
    ):
        raise ValueError("current code/public CI no-I/O preparation is not admitted")
    validate_domain_dataset_usage(
        dataset,
        DomainDatasetRole.HELD_OUT,
        confirm_rules_frozen=True,
    )
    dataset_sha = domain_dataset_sha256(dataset)
    contract = dataset.contract_snapshot
    if (
        dataset.dataset_id != _EXPECTED_FRESH_DATASET_ID
        or dataset.dataset_version != _EXPECTED_FRESH_DATASET_VERSION
        or tuple(row.case_id for row in dataset.cases) != _EXPECTED_FRESH_CASES
        or dataset_sha != _EXPECTED_FRESH_DATASET_SHA256
        or frozen_snapshot.schema_version != "1.1"
        or contract.prompt_context_snapshot_id != frozen_snapshot.snapshot_id
        or contract.prompt_context_snapshot_sha256
        != frozen_snapshot.snapshot_sha256
        or contract.skill_name != frozen_snapshot.skill_name
        or contract.skill_version != frozen_snapshot.skill_version
        or contract.context_contract != frozen_snapshot.context_contract
        or contract.evaluation_contract != frozen_snapshot.evaluation_contract
    ):
        raise ValueError("fresh held-out Dataset or Context identity has drifted")
    policy = deepseek_experiment_policy()
    return ExperimentPreparationReport(
        provider_id=policy.provider_id,
        requested_model=policy.model,
        base_url="https://api.deepseek.com",
        sdk_max_retries=0,
        stream=False,
        thinking="disabled",
        code_sha=code_sha,
        public_ci_sha=public_ci_sha,
        public_ci_success_confirmed=True,
        dataset_id=dataset.dataset_id,
        dataset_version=dataset.dataset_version,
        dataset_sha256=dataset_sha,
        prompt_context_snapshot_id=frozen_snapshot.snapshot_id,
        prompt_context_snapshot_sha256=frozen_snapshot.snapshot_sha256,
        evaluation_contract=frozen_snapshot.evaluation_contract,
        protocol_max_calls=policy.scope_call_limits["adapter_protocol"],
        domain_max_calls=policy.scope_call_limits["domain"],
        cumulative_max_calls=policy.max_calls,
        maximum_total_tokens=policy.max_observed_tokens,
        maximum_output_tokens_per_request=policy.max_output_tokens_per_request,
        maximum_estimated_cost=policy.max_estimated_cost,
        currency=policy.currency,
        external_provider_calls=0,
        held_out_executed=False,
        local_preflight_passed=True,
    )


def prepare_fresh_domain_heldout_admission(
    *,
    historical: HistoricalDomainEvidence,
    asset_freeze: FreshDomainAssetFreezeEvidence,
    preparation: ExperimentPreparationReport,
    dataset: DomainEvaluationDataset,
    loaded_input_plan: LoadedDomainCaseInputPlan,
    frozen_snapshot: PromptContextSnapshot,
    current_snapshot: PromptContextSnapshot,
    protocol_record: ProviderAdapterProtocolExperimentRecord,
    protocol_result_sha256: str,
) -> FreshDomainHeldOutAdmission:
    """Bind the complete fresh evidence chain before any Provider can exist."""

    if not isinstance(historical, HistoricalDomainEvidence):
        raise TypeError("historical must use HistoricalDomainEvidence")
    if not isinstance(asset_freeze, FreshDomainAssetFreezeEvidence):
        raise TypeError("asset_freeze must use FreshDomainAssetFreezeEvidence")
    if not isinstance(preparation, ExperimentPreparationReport):
        raise TypeError("preparation must use ExperimentPreparationReport")
    if not isinstance(loaded_input_plan, LoadedDomainCaseInputPlan):
        raise TypeError("loaded_input_plan must be a validated input plan")
    if not isinstance(frozen_snapshot, PromptContextSnapshot) or not isinstance(
        current_snapshot, PromptContextSnapshot
    ):
        raise TypeError("Prompt/Context snapshots must use the frozen contract")

    _require_fresh_development_preparation(preparation)
    validate_domain_dataset_usage(
        dataset,
        DomainDatasetRole.HELD_OUT,
        confirm_rules_frozen=True,
    )
    if current_snapshot != frozen_snapshot:
        raise ValueError("Prompt/Context snapshot mismatch")
    artifact = loaded_input_plan.artifact
    plan = loaded_input_plan.execution_plan
    expected_commitments = tuple(
        DomainCaseContextCommitment(
            case_id=row.case_id,
            context_sha256=case_context_sha256(row),
        )
        for row in frozen_snapshot.case_contexts
    )
    if (
        frozen_snapshot.schema_version != "1.1"
        or len(frozen_snapshot.case_contexts) != 3
        or artifact.schema_version != "1.1"
        or artifact.case_context_commitments != expected_commitments
        or artifact.prompt_context_snapshot_id != frozen_snapshot.snapshot_id
        or artifact.prompt_context_snapshot_sha256
        != frozen_snapshot.snapshot_sha256
        or tuple(row.case_id for row in dataset.cases) != plan.case_ids
        or tuple(row.case_id for row in frozen_snapshot.case_contexts)
        != plan.case_ids
    ):
        raise ValueError("fresh held-out plan or Context commitments have drifted")
    dataset_sha = domain_dataset_sha256(dataset)
    contract = dataset.contract_snapshot
    if (
        dataset_sha != _EXPECTED_FRESH_DATASET_SHA256
        or dataset_sha != preparation.dataset_sha256
        or (dataset.dataset_id, dataset.dataset_version)
        != (preparation.dataset_id, preparation.dataset_version)
        or contract.prompt_context_snapshot_id != frozen_snapshot.snapshot_id
        or contract.prompt_context_snapshot_sha256
        != frozen_snapshot.snapshot_sha256
        or preparation.prompt_context_snapshot_id != frozen_snapshot.snapshot_id
        or preparation.prompt_context_snapshot_sha256
        != frozen_snapshot.snapshot_sha256
        or contract.skill_name != frozen_snapshot.skill_name
        or contract.skill_version != frozen_snapshot.skill_version
        or contract.evaluation_contract != frozen_snapshot.evaluation_contract
        or preparation.evaluation_contract != frozen_snapshot.evaluation_contract
        or artifact.skill_name != frozen_snapshot.skill_name
        or artifact.skill_version != frozen_snapshot.skill_version
    ):
        raise ValueError("fresh Dataset, Skill or Evaluation identity has drifted")
    if (
        asset_freeze.input_plan_file_sha256 != plan.plan_sha256
        or asset_freeze.player_summary_file_sha256 != artifact.player_summary.sha256
        or asset_freeze.deterministic_report_file_sha256
        != artifact.deterministic_report.sha256
        or historical.protocol_result_sha256 != protocol_result_sha256
    ):
        raise ValueError("fresh asset or historical evidence binding has drifted")

    run_admission = prepare_deepseek_fresh_domain_heldout_run(
        preparation=preparation,
        protocol_record=protocol_record,
        protocol_result_sha256=protocol_result_sha256,
        dataset=dataset,
        execution_plan=plan,
    )
    experiment_id = _fresh_heldout_experiment_id(
        historical=historical,
        asset_freeze=asset_freeze,
        preparation=preparation,
        run_admission=run_admission,
        dataset_sha256=dataset_sha,
        prompt_context_snapshot_sha256=frozen_snapshot.snapshot_sha256,
        case_context_commitments=expected_commitments,
    )
    return FreshDomainHeldOutAdmission(
        experiment_id=experiment_id,
        historical=historical,
        asset_freeze=asset_freeze,
        preparation=preparation,
        dataset_role="held_out",
        dataset_sha256=dataset_sha,
        skill_name=frozen_snapshot.skill_name,
        skill_version=frozen_snapshot.skill_version,
        evaluation_contract=frozen_snapshot.evaluation_contract,
        prompt_context_snapshot_id=frozen_snapshot.snapshot_id,
        prompt_context_snapshot_sha256=frozen_snapshot.snapshot_sha256,
        execution_plan=plan,
        case_context_commitments=expected_commitments,
        run_admission=run_admission,
    )


def finalize_fresh_domain_experiment(
    *,
    admission: FreshDomainHeldOutAdmission,
    domain_result: ProviderDomainExperimentRecord,
    explicit_real_call_confirmed: bool,
) -> FreshProviderDomainExperimentRecord:
    """Wrap the existing domain verdict with the complete readmission evidence."""

    if not isinstance(admission, FreshDomainHeldOutAdmission):
        raise TypeError("admission must use FreshDomainHeldOutAdmission")
    if not isinstance(domain_result, ProviderDomainExperimentRecord):
        raise TypeError("domain_result must use ProviderDomainExperimentRecord")
    if explicit_real_call_confirmed is not True:
        raise ValueError("fresh domain result requires explicit real-call confirmation")
    return FreshProviderDomainExperimentRecord(
        experiment_id=admission.experiment_id,
        admission=admission,
        domain_result=domain_result,
        explicit_real_call_confirmed=True,
        held_out_executed=domain_result.held_out_executed,
        admitted=domain_result.admitted,
    )


def prepare_fresh_domain_development_admission(
    *,
    historical: HistoricalDomainEvidence,
    preparation: ExperimentPreparationReport,
    dataset: DomainEvaluationDataset,
    loaded_input_plan: LoadedDomainCaseInputPlan,
    frozen_snapshot: PromptContextSnapshot,
    current_snapshot: PromptContextSnapshot,
) -> FreshDomainDevelopmentAdmission:
    """Validate Fresh-Gate 1 identities without accepting a Provider or API key."""

    if not isinstance(historical, HistoricalDomainEvidence):
        raise TypeError("historical must use HistoricalDomainEvidence")
    if not isinstance(preparation, ExperimentPreparationReport):
        raise TypeError("preparation must use ExperimentPreparationReport")
    if not isinstance(loaded_input_plan, LoadedDomainCaseInputPlan):
        raise TypeError("loaded_input_plan must be a validated input plan")
    if not isinstance(frozen_snapshot, PromptContextSnapshot) or not isinstance(
        current_snapshot, PromptContextSnapshot
    ):
        raise TypeError("Prompt/Context snapshots must use the frozen contract")

    _require_fresh_development_preparation(preparation)
    validate_domain_dataset_usage(dataset, DomainDatasetRole.DEVELOPMENT)
    dataset_sha = domain_dataset_sha256(dataset)
    artifact = loaded_input_plan.artifact
    plan = loaded_input_plan.execution_plan

    if frozen_snapshot.schema_version != "1.1":
        raise ValueError("fresh admission requires Prompt/Context schema 1.1")
    if current_snapshot != frozen_snapshot:
        raise ValueError("Prompt/Context snapshot mismatch")
    if len(frozen_snapshot.case_contexts) != 3:
        raise ValueError("fresh development snapshot must contain exactly three cases")
    expected_commitments = tuple(
        DomainCaseContextCommitment(
            case_id=row.case_id,
            context_sha256=case_context_sha256(row),
        )
        for row in frozen_snapshot.case_contexts
    )
    if artifact.schema_version != "1.1":
        raise ValueError("fresh admission requires input-plan schema 1.1")
    if artifact.case_context_commitments != expected_commitments:
        raise ValueError("input plan case Context commitments do not match snapshot")
    if (
        artifact.prompt_context_snapshot_id != frozen_snapshot.snapshot_id
        or artifact.prompt_context_snapshot_sha256
        != frozen_snapshot.snapshot_sha256
    ):
        raise ValueError("input plan Prompt/Context identity does not match snapshot")

    dataset_case_ids = tuple(row.case_id for row in dataset.cases)
    snapshot_case_ids = tuple(row.case_id for row in frozen_snapshot.case_contexts)
    if dataset_case_ids != plan.case_ids or snapshot_case_ids != plan.case_ids:
        raise ValueError("Dataset, plan and Context case order do not match")
    contract = dataset.contract_snapshot
    if (
        dataset_sha != preparation.dataset_sha256
        or (dataset.dataset_id, dataset.dataset_version)
        != (preparation.dataset_id, preparation.dataset_version)
        or contract.prompt_context_snapshot_id != frozen_snapshot.snapshot_id
        or contract.prompt_context_snapshot_sha256
        != frozen_snapshot.snapshot_sha256
        or preparation.prompt_context_snapshot_id != frozen_snapshot.snapshot_id
        or preparation.prompt_context_snapshot_sha256
        != frozen_snapshot.snapshot_sha256
        or contract.skill_name != frozen_snapshot.skill_name
        or contract.skill_version != frozen_snapshot.skill_version
        or contract.context_contract != frozen_snapshot.context_contract
        or contract.evaluation_contract != frozen_snapshot.evaluation_contract
        or preparation.evaluation_contract != frozen_snapshot.evaluation_contract
        or artifact.skill_name != frozen_snapshot.skill_name
        or artifact.skill_version != frozen_snapshot.skill_version
    ):
        raise ValueError("fresh Dataset, Skill or Evaluation identity has drifted")

    experiment_id = _fresh_experiment_id(
        historical=historical,
        preparation=preparation,
        dataset_sha256=dataset_sha,
        execution_plan=plan,
        prompt_context_snapshot_sha256=frozen_snapshot.snapshot_sha256,
        case_context_commitments=expected_commitments,
    )
    return FreshDomainDevelopmentAdmission(
        experiment_id=experiment_id,
        historical=historical,
        preparation=preparation,
        dataset_role="development",
        dataset_sha256=dataset_sha,
        skill_name=frozen_snapshot.skill_name,
        skill_version=frozen_snapshot.skill_version,
        evaluation_contract=frozen_snapshot.evaluation_contract,
        prompt_context_snapshot_id=frozen_snapshot.snapshot_id,
        prompt_context_snapshot_sha256=frozen_snapshot.snapshot_sha256,
        execution_plan=plan,
        case_context_commitments=expected_commitments,
    )


def _require_fresh_development_preparation(
    preparation: ExperimentPreparationReport,
) -> None:
    if (
        preparation.provider_id != "deepseek"
        or preparation.requested_model != "deepseek-v4-pro"
        or preparation.base_url != "https://api.deepseek.com"
        or not _is_git_sha(preparation.code_sha)
        or not _is_git_sha(preparation.public_ci_sha)
        or preparation.code_sha != preparation.public_ci_sha
        or not preparation.public_ci_success_confirmed
        or not preparation.local_preflight_passed
        or preparation.external_provider_calls != 0
        or preparation.held_out_executed
    ):
        raise ValueError("current code/public CI no-I/O preparation is not admitted")
    if (
        preparation.sdk_max_retries != 0
        or preparation.stream
        or preparation.thinking != "disabled"
        or preparation.protocol_max_calls != 3
        or preparation.domain_max_calls != 12
        or preparation.cumulative_max_calls != 15
        or preparation.maximum_total_tokens != 16_000
        or preparation.maximum_output_tokens_per_request != 1024
        or str(preparation.maximum_estimated_cost) != "0.10"
        or preparation.currency != "USD"
    ):
        raise ValueError("fresh development preparation resource policy has drifted")


def _fresh_experiment_id(
    *,
    historical: HistoricalDomainEvidence,
    preparation: ExperimentPreparationReport,
    dataset_sha256: str,
    execution_plan: DomainCaseExecutionPlan,
    prompt_context_snapshot_sha256: str,
    case_context_commitments: tuple[DomainCaseContextCommitment, ...],
) -> str:
    return _digest_json(
        {
            "historical": historical.model_dump(mode="json"),
            "current_code_sha": preparation.code_sha,
            "current_public_ci_sha": preparation.public_ci_sha,
            "dataset_sha256": dataset_sha256,
            "execution_plan": execution_plan.model_dump(mode="json"),
            "prompt_context_snapshot_sha256": prompt_context_snapshot_sha256,
            "case_context_commitments": [
                row.model_dump(mode="json") for row in case_context_commitments
            ],
        }
    )


def _fresh_heldout_experiment_id(
    *,
    historical: HistoricalDomainEvidence,
    asset_freeze: FreshDomainAssetFreezeEvidence,
    preparation: ExperimentPreparationReport,
    run_admission: DeepSeekDomainRunAdmission,
    dataset_sha256: str,
    prompt_context_snapshot_sha256: str,
    case_context_commitments: tuple[DomainCaseContextCommitment, ...],
) -> str:
    return _digest_json(
        {
            "historical": historical.model_dump(mode="json"),
            "asset_freeze": asset_freeze.model_dump(mode="json"),
            "current_code_sha": preparation.code_sha,
            "current_public_ci_sha": preparation.public_ci_sha,
            "dataset_sha256": dataset_sha256,
            "execution_plan": run_admission.execution_plan.model_dump(mode="json"),
            "base_run_experiment_id": run_admission.experiment_id,
            "prompt_context_snapshot_sha256": prompt_context_snapshot_sha256,
            "case_context_commitments": [
                row.model_dump(mode="json") for row in case_context_commitments
            ],
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


def _is_git_sha(value: str) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(character in "0123456789abcdef" for character in value)
    )


def _file_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


__all__ = [
    "FreshDomainAssetFreezeEvidence",
    "FreshDomainDevelopmentAdmission",
    "FreshDomainHeldOutAdmission",
    "FreshProviderDomainExperimentRecord",
    "HistoricalDomainEvidence",
    "MultiToolRepairEvidence",
    "build_fresh_domain_preparation",
    "finalize_fresh_domain_experiment",
    "load_fresh_domain_asset_freeze_evidence",
    "load_historical_domain_evidence",
    "prepare_fresh_domain_development_admission",
    "prepare_fresh_domain_heldout_admission",
]
