"""Candidate-only offline/real gate for the GLM-5.3 hardened V3 exam."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, Literal

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.agent.context import CANDIDATE_CONTEXT_SAFETY_POLICY_V1
from app.evaluation.domain_e2e import (
    DomainCandidate,
    DomainCandidateCase,
    DomainCaseResult,
    DomainEvaluationDataset,
    DomainEvaluationResult,
    evaluate_domain_candidate,
    load_domain_dataset,
)
from app.evaluation.glm53_bounded_revision_budget import (
    BoundedRevisionBudgetState,
    BoundedRevisionBudgetedProvider,
    V3_CASE_MAX_CALLS,
    V3_CASE_MAX_TOKENS,
    V3_DOMAIN_MAX_CALLS,
    V3_DOMAIN_MAX_TOKENS,
)
from app.evaluation.glm53_bounded_revision_budget_reachability import (
    REPORT_PATH as BUDGET_REPORT_PATH,
    load_v3_budget_reachability_report,
)
from app.evaluation.glm53_flash_candidate_profile import (
    GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY,
    MODEL,
    PROFILE_ID,
    PROVIDER_ID,
    REQUEST_POLICY_ID,
    REQUEST_POLICY_VERSION,
    RUNTIME_PROFILE_ID,
    RUNTIME_PROFILE_VERSION,
    require_glm53_flash_low_candidate_request_policy,
)
from app.evaluation.glm53_hardened_domain_v3_assets import (
    DATASET_ID,
    DATASET_PATH,
    DATASET_VERSION,
    EVALUATION_DIAGNOSTICS_VERSION,
    INPUT_PLAN_PATH,
    PROTOCOL_ID,
    PROTOCOL_PATH,
    QUALITY_HARDENING_VERSION,
    SNAPSHOT_ID,
    SNAPSHOT_PATH,
    GLM53HardenedDomainV3AssetAdmission,
    admit_hardened_domain_v3_assets,
)
from app.evaluation.glm53_low_profile_domain_gate import (
    BASE_URL,
    _assert_body_free,
    _digest_json,
    _provider_failure_code,
    _read_head_sha,
    _require_clean_worktree,
    _safe_code,
    _sha256_file,
    create_low_profile_provider,
)
from app.evaluation.glm53_low_profile_protocol import (
    GLM53LowProfileProtocolReport,
)
from app.evaluation.provider_adoption import ExperimentFailureCode
from app.evaluation.provider_domain_experiment import (
    DomainCaseExecutionPlan,
    DomainCaseExecutionRecord,
    DomainCaseSemanticObservation,
    ExperimentFailureCode,
)
from app.evaluation.provider_domain_plan import LoadedDomainCaseInputPlan, load_domain_case_input_plan
from app.evaluation.provider_domain_production import ProductionDomainCaseExecutor
from app.providers.config import ZhipuSettings, load_zhipu_settings
from app.providers.errors import ProviderError
from app.providers.protocol import LLMProvider


SCHEMA_VERSION = "1.0"
PROTOCOL_MAX_CALLS = 3
DEFAULT_PROTOCOL_RESULT = Path(
    "data/evaluation/results/provider_capabilities/"
    "zhipu_glm53_flash_candidate_low_4096_g53_3l_rq225_v1.json"
)
DEFAULT_OUTPUT = Path(
    "data/evaluation/results/provider_capabilities/"
    "zhipu_glm53_flash_hardened_domain_v3_rq231_v1.json"
)
DEFAULT_RUNS_ROOT = Path("data/runs/evaluation/glm53_hardened_domain_v3")

GitShaText = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
Sha256Text = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
SafeCodeText = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z][a-z0-9_.:-]{0,127}$"),
]
NonBlankText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class V3CaseResource(_FrozenModel):
    case_id: NonBlankText
    calls_used: int = Field(ge=0, le=V3_CASE_MAX_CALLS)
    max_calls: Literal[V3_CASE_MAX_CALLS] = V3_CASE_MAX_CALLS
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0, le=V3_CASE_MAX_TOKENS)
    max_observed_tokens: Literal[V3_CASE_MAX_TOKENS] = V3_CASE_MAX_TOKENS
    latency_ms: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_total(self) -> "V3CaseResource":
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("V3 case token total is inconsistent")
        return self


class V3ResourceSnapshot(_FrozenModel):
    provider_id: Literal[PROVIDER_ID] = PROVIDER_ID
    model: Literal[MODEL] = MODEL
    calls_used: int = Field(ge=0, le=V3_DOMAIN_MAX_CALLS)
    max_calls: Literal[V3_DOMAIN_MAX_CALLS] = V3_DOMAIN_MAX_CALLS
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0, le=V3_DOMAIN_MAX_TOKENS)
    max_observed_tokens: Literal[V3_DOMAIN_MAX_TOKENS] = V3_DOMAIN_MAX_TOKENS
    latency_ms: int = Field(ge=0)
    case_resources: tuple[V3CaseResource, ...]
    stop_code: SafeCodeText | None = None
    provider_error_code: SafeCodeText | None = None
    monetary_cost_status: Literal["unknown"] = "unknown"

    @model_validator(mode="after")
    def validate_totals(self) -> "V3ResourceSnapshot":
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("V3 domain token total is inconsistent")
        if sum(row.calls_used for row in self.case_resources) != self.calls_used:
            raise ValueError("V3 case calls do not match domain calls")
        if sum(row.input_tokens for row in self.case_resources) != self.input_tokens:
            raise ValueError("V3 case input does not match domain input")
        if sum(row.output_tokens for row in self.case_resources) != self.output_tokens:
            raise ValueError("V3 case output does not match domain output")
        return self


class V3ControlSnapshot(_FrozenModel):
    global_stop: SafeCodeText | None = None
    provider_stop: SafeCodeText | None = None
    provider_error_code: SafeCodeText | None = None


class V3DomainAdmission(_FrozenModel):
    schema_version: Literal[SCHEMA_VERSION] = SCHEMA_VERSION
    experiment_id: Sha256Text
    protocol_id: Literal[PROTOCOL_ID] = PROTOCOL_ID
    provider_id: Literal[PROVIDER_ID] = PROVIDER_ID
    requested_model: Literal[MODEL] = MODEL
    base_url: Literal[BASE_URL] = BASE_URL
    candidate_profile_id: Literal[PROFILE_ID] = PROFILE_ID
    candidate_profile_version: Literal["1.0.0"] = "1.0.0"
    runtime_profile_id: Literal[RUNTIME_PROFILE_ID] = RUNTIME_PROFILE_ID
    runtime_profile_version: Literal[RUNTIME_PROFILE_VERSION] = RUNTIME_PROFILE_VERSION
    request_policy_id: Literal[REQUEST_POLICY_ID] = REQUEST_POLICY_ID
    request_policy_version: Literal[REQUEST_POLICY_VERSION] = REQUEST_POLICY_VERSION
    implementation_sha: GitShaText
    public_ci_sha: GitShaText
    public_ci_success_confirmed: Literal[True] = True
    public_ci_scope: NonBlankText
    asset_admission: GLM53HardenedDomainV3AssetAdmission
    dataset_sha256: Sha256Text
    dataset_file_sha256: Sha256Text
    input_plan_file_sha256: Sha256Text
    prompt_context_snapshot_sha256: Sha256Text
    prompt_context_snapshot_file_sha256: Sha256Text
    execution_plan: DomainCaseExecutionPlan
    budget_report_sha256: Sha256Text
    budget_report_file_sha256: Sha256Text
    protocol_result_sha256: Sha256Text
    protocol_code_sha: GitShaText
    protocol_calls: Literal[PROTOCOL_MAX_CALLS] = PROTOCOL_MAX_CALLS
    protocol_input_tokens: int = Field(ge=0)
    protocol_output_tokens: int = Field(ge=0)
    protocol_total_tokens: int = Field(ge=0)
    domain_max_calls: Literal[V3_DOMAIN_MAX_CALLS] = V3_DOMAIN_MAX_CALLS
    case_max_calls: Literal[V3_CASE_MAX_CALLS] = V3_CASE_MAX_CALLS
    domain_max_tokens: Literal[V3_DOMAIN_MAX_TOKENS] = V3_DOMAIN_MAX_TOKENS
    case_max_tokens: Literal[V3_CASE_MAX_TOKENS] = V3_CASE_MAX_TOKENS
    max_revisions: Literal[1] = 1
    sdk_max_retries: Literal[0] = 0
    evaluation_diagnostics_version: Literal[EVALUATION_DIAGNOSTICS_VERSION] = EVALUATION_DIAGNOSTICS_VERSION
    candidate_registered: Literal[False] = False
    production_admitted: Literal[False] = False
    external_provider_calls: Literal[0] = 0
    held_out_executed: Literal[False] = False
    provider_construction_authorized: Literal[False] = False
    ready_for_real_call: Literal[True] = True

    @model_validator(mode="after")
    def validate_identity(self) -> "V3DomainAdmission":
        if self.implementation_sha != self.public_ci_sha:
            raise ValueError("implementation SHA must match public CI SHA")
        if self.protocol_total_tokens != self.protocol_input_tokens + self.protocol_output_tokens:
            raise ValueError("protocol token total is inconsistent")
        if self.execution_plan.case_ids != self.asset_admission.case_ids:
            raise ValueError("execution plan does not match V3 assets")
        if self.budget_report_sha256 != self.asset_admission.budget_report_sha256:
            raise ValueError("budget proof identity does not match V3 assets")
        expected = _admission_identity(self)
        if self.experiment_id != expected:
            raise ValueError("V3 domain experiment identity is inconsistent")
        return self


class V3DomainGateResult(_FrozenModel):
    schema_version: Literal[SCHEMA_VERSION] = SCHEMA_VERSION
    protocol_id: Literal[PROTOCOL_ID] = PROTOCOL_ID
    experiment_id: Sha256Text
    run_timestamp_utc: datetime
    admission: V3DomainAdmission
    resources: V3ResourceSnapshot
    control: V3ControlSnapshot
    protocol_calls: Literal[PROTOCOL_MAX_CALLS] = PROTOCOL_MAX_CALLS
    protocol_total_tokens: int = Field(ge=0)
    domain_calls_used: int = Field(ge=0, le=V3_DOMAIN_MAX_CALLS)
    domain_total_tokens: int = Field(ge=0, le=V3_DOMAIN_MAX_TOKENS)
    cumulative_calls_used: int = Field(ge=0, le=PROTOCOL_MAX_CALLS + V3_DOMAIN_MAX_CALLS)
    cumulative_total_tokens: int = Field(ge=0)
    explicit_real_call_confirmed: Literal[True] = True
    network_used: bool
    held_out_executed: bool
    cases: tuple[DomainCaseExecutionRecord, ...]
    candidate: DomainCandidate | None = None
    evaluation: DomainEvaluationResult | None = None
    candidate_registered: Literal[False] = False
    production_admitted: Literal[False] = False
    admitted: bool
    unsupported_boundaries: tuple[NonBlankText, ...]

    @model_validator(mode="after")
    def validate_result(self) -> "V3DomainGateResult":
        if self.experiment_id != self.admission.experiment_id:
            raise ValueError("V3 result and admission identities differ")
        if self.resources.calls_used != self.domain_calls_used:
            raise ValueError("V3 resource and domain calls differ")
        if self.resources.total_tokens != self.domain_total_tokens:
            raise ValueError("V3 resource and domain tokens differ")
        if self.cumulative_calls_used != self.protocol_calls + self.domain_calls_used:
            raise ValueError("V3 cumulative calls are inconsistent")
        if self.cumulative_total_tokens != self.protocol_total_tokens + self.domain_total_tokens:
            raise ValueError("V3 cumulative tokens are inconsistent")
        if self.held_out_executed != any(row.status != "skipped" for row in self.cases):
            raise ValueError("V3 held-out execution flag is inconsistent")
        complete = all(row.status == "executed" for row in self.cases)
        if complete is not (self.candidate is not None):
            raise ValueError("V3 complete cases require candidate evidence")
        if (self.candidate is None) is not (self.evaluation is None):
            raise ValueError("V3 candidate and evaluation must appear together")
        if self.candidate_registered or self.production_admitted:
            raise ValueError("V3 gate cannot register or admit production")
        return self


@dataclass(frozen=True)
class V3PreparedRun:
    admission: V3DomainAdmission
    assets: GLM53HardenedDomainV3AssetAdmission
    dataset: DomainEvaluationDataset
    input_plan: LoadedDomainCaseInputPlan


@dataclass(frozen=True)
class V3PreflightStatus:
    status: Literal["pending_public_ci", "pending_protocol_evidence"]
    implementation_sha: str
    public_ci_sha: str
    asset_admission: GLM53HardenedDomainV3AssetAdmission | None
    external_provider_calls: int = 0
    held_out_executed: bool = False
    reason: str = ""


@dataclass(frozen=True)
class V3DomainGateOptions:
    confirm_real_call: bool
    public_ci_sha: str | None = None
    confirm_public_ci_success: bool = False
    implementation_sha: str | None = None
    preflight_only: bool = False
    max_calls: int = V3_DOMAIN_MAX_CALLS
    protocol_plan: Path = PROTOCOL_PATH
    dataset: Path = DATASET_PATH
    input_plan: Path = INPUT_PLAN_PATH
    snapshot: Path = SNAPSHOT_PATH
    budget_report: Path = BUDGET_REPORT_PATH
    protocol_result: Path = DEFAULT_PROTOCOL_RESULT
    output: Path = DEFAULT_OUTPUT
    runs_root: Path = DEFAULT_RUNS_ROOT


def build_v3_domain_preflight(
    *,
    project_root: str | Path,
    implementation_sha: str,
    public_ci_sha: str,
    confirm_public_ci_success: bool,
    protocol_plan_path: str | Path = PROTOCOL_PATH,
    dataset_path: str | Path = DATASET_PATH,
    input_plan_path: str | Path = INPUT_PLAN_PATH,
    snapshot_path: str | Path = SNAPSHOT_PATH,
    budget_report_path: str | Path = BUDGET_REPORT_PATH,
    protocol_result_path: str | Path = DEFAULT_PROTOCOL_RESULT,
) -> V3PreparedRun:
    _require_git_sha(implementation_sha, "implementation_sha")
    _require_git_sha(public_ci_sha, "public_ci_sha")
    if implementation_sha != public_ci_sha or confirm_public_ci_success is not True:
        raise ValueError("implementation/public CI identity is not confirmed")
    root = Path(project_root).resolve()
    protocol_file = _inside_file(root, protocol_plan_path, "protocol plan")
    dataset_file = _inside_file(root, dataset_path, "dataset")
    plan_file = _inside_file(root, input_plan_path, "input plan")
    snapshot_file = _inside_file(root, snapshot_path, "snapshot")
    budget_file = _inside_file(root, budget_report_path, "budget report")
    protocol_result_file = _inside_file(root, protocol_result_path, "protocol result")

    assets = admit_hardened_domain_v3_assets(
        project_root=root,
        confirm_rules_frozen=True,
        protocol_path=protocol_file,
        dataset_path=dataset_file,
        input_plan_path=plan_file,
        snapshot_path=snapshot_file,
        budget_report_path=budget_file,
    )
    dataset = load_domain_dataset(dataset_file)
    loaded_plan = load_domain_case_input_plan(
        plan_file,
        project_root=root,
        dataset=dataset,
        expected_max_revisions=1,
    )
    if _sha256_file(protocol_file) != assets.protocol_file_sha256:
        raise ValueError("V3 protocol bytes changed after asset admission")
    if _sha256_file(dataset_file) != assets.dataset_file_sha256:
        raise ValueError("V3 dataset bytes changed after asset admission")
    if _sha256_file(plan_file) != assets.input_plan_file_sha256:
        raise ValueError("V3 input plan bytes changed after asset admission")
    if _sha256_file(snapshot_file) != assets.snapshot_file_sha256:
        raise ValueError("V3 snapshot bytes changed after asset admission")

    protocol = json.loads(protocol_file.read_text(encoding="utf-8"))
    budget = load_v3_budget_reachability_report(budget_file)
    prior_raw = protocol_result_file.read_bytes()
    prior = GLM53LowProfileProtocolReport.model_validate_json(prior_raw)
    if (
        prior.evidence_origin != "real_provider"
        or prior.provider_id != PROVIDER_ID
        or prior.requested_model != MODEL
        or prior.provider_call_count != PROTOCOL_MAX_CALLS
        or prior.protocol_code_sha != implementation_sha
        or prior.implementation_sha != implementation_sha
        or prior.request_policy_id != REQUEST_POLICY_ID
    ):
        raise ValueError("fresh G53-3-L protocol evidence is pending or stale")
    admission_data: dict[str, Any] = {
        "experiment_id": "0" * 64,
        "implementation_sha": implementation_sha,
        "public_ci_sha": public_ci_sha,
        "public_ci_scope": "candidate-hardened-domain-v3-exact-sha",
        "asset_admission": assets,
        "dataset_sha256": _digest_json(dataset.model_dump(mode="json")),
        "dataset_file_sha256": _sha256_file(dataset_file),
        "input_plan_file_sha256": _sha256_file(plan_file),
        "prompt_context_snapshot_sha256": assets.snapshot_sha256,
        "prompt_context_snapshot_file_sha256": _sha256_file(snapshot_file),
        "execution_plan": loaded_plan.execution_plan,
        "budget_report_sha256": budget.report_sha256,
        "budget_report_file_sha256": _sha256_file(budget_file),
        "protocol_result_sha256": hashlib.sha256(prior_raw).hexdigest(),
        "protocol_code_sha": prior.protocol_code_sha,
        "protocol_input_tokens": prior.input_tokens,
        "protocol_output_tokens": prior.output_tokens,
        "protocol_total_tokens": prior.total_tokens,
    }
    draft = V3DomainAdmission.model_construct(**admission_data)
    admission_data["experiment_id"] = _admission_identity(draft)
    return V3PreparedRun(
        admission=V3DomainAdmission(**admission_data),
        assets=assets,
        dataset=dataset,
        input_plan=loaded_plan,
    )


def run_v3_domain_gate(
    *,
    admission: V3DomainAdmission,
    dataset: DomainEvaluationDataset,
    provider: LLMProvider,
    case_executor: Any,
    confirm_real_call: bool = True,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    clock: Callable[[], float] = time.monotonic,
) -> V3DomainGateResult:
    if not isinstance(admission, V3DomainAdmission):
        raise TypeError("admission must be a V3DomainAdmission")
    if confirm_real_call is not True:
        raise RuntimeError("real V3 domain calls require explicit confirmation")
    if not isinstance(dataset, DomainEvaluationDataset):
        raise TypeError("dataset must be a DomainEvaluationDataset")
    if tuple(row.case_id for row in dataset.cases) != admission.execution_plan.case_ids:
        raise ValueError("runtime Dataset case order does not match V3 admission")
    policy = require_glm53_flash_low_candidate_request_policy()
    if getattr(provider, "provider_name", None) != PROVIDER_ID or getattr(provider, "model_name", None) != MODEL:
        raise ValueError("runtime Provider does not match V3 candidate")
    if not all((provider.capabilities.text_chat, provider.capabilities.tool_calling, provider.capabilities.structured_output)):
        raise ValueError("runtime Provider lacks admitted capabilities")
    if getattr(case_executor, "execution_plan", None) != admission.execution_plan:
        raise ValueError("case executor does not match V3 execution plan")
    if getattr(case_executor, "quality_hardening", None) is not True:
        raise ValueError("V3 executor must enable quality hardening")
    if getattr(case_executor, "retrieval_hardening", None) is not True:
        raise ValueError("V3 executor must enable retrieval hardening")
    if getattr(case_executor, "max_revisions", None) != 1:
        raise ValueError("V3 executor must allow exactly one revision")
    if getattr(case_executor, "request_policy", None) is not policy:
        raise ValueError("V3 executor does not use the exact candidate policy")

    state = BoundedRevisionBudgetState()
    records: list[DomainCaseExecutionRecord] = []
    observations: list[DomainCandidateCase] = []
    for case in dataset.cases:
        if state.stop_code is not None:
            records.append(DomainCaseExecutionRecord(case_id=case.case_id, status="skipped", failure_code=_failure_enum(state.stop_code)))
            continue
        state.register_case(case.case_id)
        before = state.case_snapshot(case.case_id)
        controlled = BoundedRevisionBudgetedProvider(
            provider=provider,
            state=state,
            case_id=case.case_id,
            request_policy=policy,
            clock=clock,
        )
        try:
            semantic = case_executor.execute(case_id=case.case_id, provider=controlled)
            if not isinstance(semantic, DomainCaseSemanticObservation) or semantic.case_id != case.case_id:
                raise ValueError("V3 case executor returned an invalid observation")
        except ProviderError as exc:
            state.stop("provider_error", provider_error_code=exc.code)
            records.append(DomainCaseExecutionRecord(case_id=case.case_id, status="failed", failure_code=_failure_enum(_provider_failure_code(exc))))
            continue
        except Exception:
            state.stop("domain_case_observation_invalid")
            records.append(DomainCaseExecutionRecord(case_id=case.case_id, status="failed", failure_code=ExperimentFailureCode.DOMAIN_CASE_OBSERVATION_INVALID))
            continue

        after = state.case_snapshot(case.case_id)
        observation = _candidate_case_from_semantics(semantic, before=before, after=after)
        case_result = _evaluate_one_case(dataset, case_id=case.case_id, observation=observation)
        failure = _case_failure(state, semantic, case_result)
        if failure is not None:
            state.stop("unsafe_publication" if failure is ExperimentFailureCode.UNSAFE_PUBLICATION else failure.value, provider_error_code=semantic.safe_provider_error_code)
        observations.append(observation)
        records.append(DomainCaseExecutionRecord(case_id=case.case_id, status="executed", failure_code=failure, observation=observation, evaluation=case_result))

    candidate: DomainCandidate | None = None
    evaluation: DomainEvaluationResult | None = None
    if len(observations) == len(dataset.cases):
        candidate = DomainCandidate(
            schema_version=dataset.schema_version,
            candidate_id=f"zhipu-glm53-flash-hardened-v3-{admission.experiment_id[:16]}",
            candidate_kind="real_provider_recorded",
            dataset_id=dataset.dataset_id,
            dataset_version=dataset.dataset_version,
            contract_snapshot=dataset.contract_snapshot,
            external_provider_calls=state.calls_used,
            case_count=len(observations),
            cases=tuple(observations),
        )
        evaluation = evaluate_domain_candidate(dataset, candidate)
    resources = _resource_snapshot(state)
    control = V3ControlSnapshot(
        global_stop="unsafe_publication" if state.stop_code == "unsafe_publication" else None,
        provider_stop=None if state.stop_code in {None, "unsafe_publication"} else _safe_code(state.stop_code),
        provider_error_code=_safe_code(state.provider_error_code) if state.provider_error_code else None,
    )
    clean = all(row.status == "executed" and row.failure_code is None for row in records)
    admitted = all((clean, evaluation is not None, evaluation is not None and evaluation.task_outcome_accuracy == 1.0, evaluation is not None and evaluation.failure_classification_accuracy == 1.0, evaluation is not None and evaluation.unsafe_publication_rate == 0.0, resources.stop_code is None, control.global_stop is None, control.provider_stop is None))
    return V3DomainGateResult(
        experiment_id=admission.experiment_id,
        run_timestamp_utc=now(),
        admission=admission,
        resources=resources,
        control=control,
        protocol_total_tokens=admission.protocol_total_tokens,
        domain_calls_used=state.calls_used,
        domain_total_tokens=state.total_tokens,
        cumulative_calls_used=PROTOCOL_MAX_CALLS + state.calls_used,
        cumulative_total_tokens=admission.protocol_total_tokens + state.total_tokens,
        network_used=state.calls_used > 0,
        held_out_executed=any(row.status != "skipped" for row in records),
        cases=tuple(records),
        candidate=candidate,
        evaluation=evaluation,
        admitted=admitted,
        unsupported_boundaries=("产品 Runtime 注册", "默认模型切换", "streaming 生产能力", "黄金切片", "安全/部署/合规", "8F final evaluation"),
    )


def run_cli(
    options: V3DomainGateOptions,
    *,
    repository_root: Path | None = None,
    environment_loader: Callable[[Path], Mapping[str, str]] | None = None,
    provider_factory: Callable[[ZhipuSettings], LLMProvider] = create_low_profile_provider,
    code_sha_reader: Callable[[Path], str] | None = None,
) -> V3PreflightStatus | V3PreparedRun | V3DomainGateResult:
    if options.max_calls != V3_DOMAIN_MAX_CALLS:
        raise ValueError("hardened V3 domain gate requires exactly 27 calls")
    root = (repository_root or Path(__file__).resolve().parents[2]).resolve()
    current_sha = options.implementation_sha or (code_sha_reader or _read_head_sha)(root)
    public_sha = options.public_ci_sha or current_sha
    if not _is_git_sha(current_sha) or not _is_git_sha(public_sha):
        raise ValueError("implementation and public CI SHA must be lowercase git SHAs")
    if current_sha != public_sha or options.confirm_public_ci_success is not True:
        return V3PreflightStatus(
            status="pending_public_ci",
            implementation_sha=current_sha,
            public_ci_sha=public_sha,
            asset_admission=None,
            reason="exact-SHA public CI success is required before V3 admission",
        )
    assets = admit_hardened_domain_v3_assets(project_root=root, confirm_rules_frozen=True, protocol_path=options.protocol_plan, dataset_path=options.dataset, input_plan_path=options.input_plan, snapshot_path=options.snapshot, budget_report_path=options.budget_report)
    try:
        prepared = build_v3_domain_preflight(project_root=root, implementation_sha=current_sha, public_ci_sha=public_sha, confirm_public_ci_success=True, protocol_plan_path=options.protocol_plan, dataset_path=options.dataset, input_plan_path=options.input_plan, snapshot_path=options.snapshot, budget_report_path=options.budget_report, protocol_result_path=options.protocol_result)
    except (FileNotFoundError, ValueError):
        return V3PreflightStatus(status="pending_protocol_evidence", implementation_sha=current_sha, public_ci_sha=public_sha, asset_admission=assets, reason="fresh exact-SHA G53-3-L protocol evidence is required")
    if options.preflight_only:
        return prepared
    if not options.confirm_real_call:
        raise RuntimeError("real V3 domain calls require explicit confirmation")
    _require_clean_worktree(root)
    output = _inside_output(root, options.output)
    if output.exists() or output.is_symlink():
        raise FileExistsError("V3 domain evidence is immutable")
    output.parent.mkdir(parents=True, exist_ok=True)
    settings = load_zhipu_settings((environment_loader or _load_environment)(root))
    provider = provider_factory(settings)
    runs_root = _inside_directory(root, options.runs_root)
    with tempfile.TemporaryDirectory(prefix="glm53-hardened-domain-v3-", dir=str(runs_root.parent)) as temporary:
        executor = ProductionDomainCaseExecutor(project_root=root, input_plan=prepared.input_plan, runs_root=temporary, request_policy=GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY, quality_hardening=True, retrieval_hardening=True, max_revisions=1)
        result = run_v3_domain_gate(admission=prepared.admission, dataset=prepared.dataset, provider=provider, case_executor=executor, confirm_real_call=True)
    output.write_bytes(canonical_v3_result_bytes(result))
    return result


def canonical_v3_result_bytes(result: V3DomainGateResult) -> bytes:
    if not isinstance(result, V3DomainGateResult):
        raise TypeError("result must be a V3DomainGateResult")
    payload = result.model_dump(mode="json")
    _assert_body_free(payload)
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def _candidate_case_from_semantics(semantic: DomainCaseSemanticObservation, *, before: Mapping[str, int], after: Mapping[str, int]) -> DomainCandidateCase:
    return DomainCandidateCase(case_id=semantic.case_id, provider_calls=after["calls_used"] - before["calls_used"], normalized_response_count=semantic.normalized_response_count, safe_provider_error_code=semantic.safe_provider_error_code, agent_status=semantic.agent_status, agent_stop_reason=semantic.agent_stop_reason, proposed_tool_names=semantic.proposed_tool_names, successful_tool_names=semantic.successful_tool_names, evidence_source_ids=semantic.evidence_source_ids, evidence_diagnostics=semantic.evidence_diagnostics, revision_count=semantic.revision_count, evaluation_diagnostics=semantic.evaluation_diagnostics, fact_check_passed=semantic.fact_check_passed, citation_check_passed=semantic.citation_check_passed, injection_check_passed=semantic.injection_check_passed, evaluation_validated=semantic.evaluation_validated, evaluation_score=semantic.evaluation_score, terminal_status=semantic.terminal_status, terminal_reason=semantic.terminal_reason, latency_ms=after["latency_ms"] - before["latency_ms"], input_tokens=after["input_tokens"] - before["input_tokens"], output_tokens=after["output_tokens"] - before["output_tokens"], estimated_cost=None, provenance_sha256=semantic.provenance_sha256)


def _evaluate_one_case(dataset: DomainEvaluationDataset, *, case_id: str, observation: DomainCandidateCase) -> DomainCaseResult:
    case = next(row for row in dataset.cases if row.case_id == case_id)
    one_dataset = DomainEvaluationDataset.model_validate({**dataset.model_dump(mode="json"), "case_count": 1, "cases": [case.model_dump(mode="json")]})
    candidate = DomainCandidate(schema_version=dataset.schema_version, candidate_id=f"zhipu-{case_id}", candidate_kind="real_provider_recorded", dataset_id=dataset.dataset_id, dataset_version=dataset.dataset_version, contract_snapshot=dataset.contract_snapshot, external_provider_calls=observation.provider_calls, case_count=1, cases=(observation,))
    return evaluate_domain_candidate(one_dataset, candidate).cases[0]


def _case_failure(state: BoundedRevisionBudgetState, semantic: DomainCaseSemanticObservation, result: DomainCaseResult) -> ExperimentFailureCode | None:
    if state.stop_code is not None:
        return _failure_enum(state.stop_code)
    if semantic.safe_provider_error_code:
        return _failure_enum(semantic.safe_provider_error_code)
    if result.unsafe_publication:
        return ExperimentFailureCode.UNSAFE_PUBLICATION
    if not result.task_outcome_match or not result.failure_classification_match:
        return ExperimentFailureCode.DOMAIN_CASE_OUTCOME_MISMATCH
    return None


def _resource_snapshot(state: BoundedRevisionBudgetState) -> V3ResourceSnapshot:
    snap = state.snapshot()
    rows = tuple(V3CaseResource(case_id=case_id, calls_used=value["calls_used"], input_tokens=value["input_tokens"], output_tokens=value["output_tokens"], total_tokens=value["total_tokens"], latency_ms=value["latency_ms"]) for case_id, value in snap["cases"].items())
    return V3ResourceSnapshot(calls_used=snap["calls_used"], input_tokens=snap["input_tokens"], output_tokens=snap["output_tokens"], total_tokens=snap["total_tokens"], latency_ms=snap["latency_ms"], case_resources=rows, stop_code=_safe_code(snap["stop_code"]) if snap["stop_code"] else None, provider_error_code=_safe_code(snap["provider_error_code"]) if snap["provider_error_code"] else None)


def _failure_enum(code: str | ExperimentFailureCode) -> ExperimentFailureCode:
    if isinstance(code, ExperimentFailureCode):
        return code
    aliases = {
        "provider_error": ExperimentFailureCode.PROVIDER_ERROR_UNKNOWN,
        "provider_response_invalid": ExperimentFailureCode.PROVIDER_RESPONSE_INVALID,
        "external_call_budget_exhausted": ExperimentFailureCode.EXTERNAL_CALL_BUDGET_EXHAUSTED,
        "token_budget_exhausted": ExperimentFailureCode.TOKEN_BUDGET_EXHAUSTED,
        "token_envelope_exceeded": ExperimentFailureCode.TOKEN_BUDGET_EXHAUSTED,
        "unsafe_publication": ExperimentFailureCode.UNSAFE_PUBLICATION,
    }
    return aliases.get(code, ExperimentFailureCode.DOMAIN_CASE_OBSERVATION_INVALID)


def _admission_identity(admission: V3DomainAdmission) -> str:
    return _digest_json(admission.model_dump(mode="json", exclude={"experiment_id"}))


def _is_git_sha(value: str) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value) is not None


def _require_git_sha(value: str, label: str) -> None:
    if not _is_git_sha(value):
        raise ValueError(f"{label} must be a lowercase git SHA")


def _read_head_sha(root: Path) -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True, timeout=10).stdout.strip()


def _inside_file(root: Path, value: str | Path, label: str) -> Path:
    candidate = Path(value)
    resolved = (candidate if candidate.is_absolute() else root / candidate).resolve()
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise FileNotFoundError(f"{label} must be a file inside the repository")
    return resolved


def _inside_directory(root: Path, value: str | Path) -> Path:
    candidate = Path(value)
    resolved = (candidate if candidate.is_absolute() else root / candidate).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("runs root must stay inside the repository")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def _inside_output(root: Path, value: str | Path) -> Path:
    candidate = Path(value)
    resolved = (candidate if candidate.is_absolute() else root / candidate).resolve()
    allowed = (root / "data/evaluation/results/provider_capabilities").resolve()
    if not resolved.is_relative_to(allowed) or resolved.suffix.lower() != ".json":
        raise ValueError("output must be a JSON file in provider capability results")
    return resolved


def _load_environment(root: Path) -> Mapping[str, str]:
    load_dotenv(root / ".env")
    return os.environ


def _parse_args(argv: Sequence[str] | None = None) -> V3DomainGateOptions:
    parser = argparse.ArgumentParser(description="Run the bounded GLM-5.3 hardened V3 held-out domain gate.")
    parser.add_argument("--confirm-real-call", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--implementation-sha")
    parser.add_argument("--public-ci-sha")
    parser.add_argument("--confirm-public-ci-success", action="store_true")
    parser.add_argument("--max-calls", type=int, default=V3_DOMAIN_MAX_CALLS)
    parser.add_argument("--protocol-plan", type=Path, default=PROTOCOL_PATH)
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    parser.add_argument("--input-plan", type=Path, default=INPUT_PLAN_PATH)
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT_PATH)
    parser.add_argument("--budget-report", type=Path, default=BUDGET_REPORT_PATH)
    parser.add_argument("--protocol-result", type=Path, default=DEFAULT_PROTOCOL_RESULT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    values = parser.parse_args(argv)
    return V3DomainGateOptions(confirm_real_call=values.confirm_real_call, public_ci_sha=values.public_ci_sha, confirm_public_ci_success=values.confirm_public_ci_success, implementation_sha=values.implementation_sha, preflight_only=values.preflight_only, max_calls=values.max_calls, protocol_plan=values.protocol_plan, dataset=values.dataset, input_plan=values.input_plan, snapshot=values.snapshot, budget_report=values.budget_report, protocol_result=values.protocol_result, output=values.output, runs_root=values.runs_root)


def main(argv: Sequence[str] | None = None) -> int:
    result = run_cli(_parse_args(argv))
    if isinstance(result, V3PreflightStatus):
        print(f"status={result.status} external_provider_calls=0 held_out_executed=false")
    elif isinstance(result, V3PreparedRun):
        print("status=ready_for_real_call external_provider_calls=0 held_out_executed=false")
    else:
        print(f"status=completed domain_calls={result.domain_calls_used}/{V3_DOMAIN_MAX_CALLS} admitted={str(result.admitted).lower()}")
    return 0


__all__ = [
    "DEFAULT_OUTPUT",
    "DEFAULT_PROTOCOL_RESULT",
    "V3DomainAdmission",
    "V3DomainGateOptions",
    "V3DomainGateResult",
    "V3PreparedRun",
    "V3PreflightStatus",
    "build_v3_domain_preflight",
    "canonical_v3_result_bytes",
    "main",
    "run_cli",
    "run_v3_domain_gate",
]
