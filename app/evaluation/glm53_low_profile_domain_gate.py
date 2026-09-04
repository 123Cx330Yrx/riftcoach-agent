"""Candidate-only GLM-5.3 Flash low-profile held-out domain gate.

The normal GLM-5.3 domain gate is intentionally tied to the historical Flash
runtime profile and its already-consumed dataset.  This module is a separate,
small coordinator for the fresh low-profile experiment.  It reuses the
validated production Skill/RAG/Evaluation/Harness executor through the
explicit candidate request policy, while keeping the candidate outside the
product runtime registry.

The control plane is no-I/O until a caller supplies both an exact implementation
SHA/public-CI attestation and an explicit real-call confirmation.  The result
is body-free and create-only; prompts, model text, reasoning, tool arguments,
request IDs and credentials never cross the public receipt boundary.
"""

from __future__ import annotations

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
from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.evaluation.domain_e2e import (
    DomainCandidate,
    DomainCandidateCase,
    DomainCaseResult,
    DomainEvaluationDataset,
    DomainEvaluationResult,
    evaluate_domain_candidate,
    load_domain_dataset,
)
from app.evaluation.glm53_low_profile_assets import (
    DATASET_PATH,
    INPUT_PLAN_PATH,
    SNAPSHOT_ID,
    SNAPSHOT_PATH,
    GLM53LowProfileAssetAdmission,
    admit_low_profile_assets,
)
from app.evaluation.glm53_low_profile_budget import (
    CANDIDATE_CASE_MAX_CALLS,
    CANDIDATE_CASE_MAX_TOKENS,
    CANDIDATE_DOMAIN_MAX_CALLS,
    CANDIDATE_DOMAIN_MAX_TOKENS,
    CandidateEvaluationBudgetState,
    CandidateEvaluationBudgetedProvider,
)
from app.evaluation.glm53_low_profile_protocol import (
    GLM53LowProfileProtocolReport,
)
from app.evaluation.prompt_context_identity import (
    build_prompt_context_snapshot_for_cases,
    load_prompt_context_snapshot,
)
from app.evaluation.provider_adoption import (
    ExperimentFailureCode,
    classify_provider_error,
)
from app.evaluation.provider_domain_experiment import (
    DomainCaseExecutionPlan,
    DomainCaseExecutionRecord,
    DomainCaseSemanticObservation,
)
from app.evaluation.provider_domain_plan import (
    LoadedDomainCaseInputPlan,
    load_domain_case_input_plan,
)
from app.evaluation.provider_domain_production import ProductionDomainCaseExecutor
from app.providers.config import ZhipuSettings, load_zhipu_settings
from app.providers.errors import ProviderError, ProviderResponseError
from app.providers.protocol import LLMProvider
from app.providers.zhipu import ZhipuProvider

from .glm53_flash_candidate_profile import (
    GLM53_FLASH_LOW_CANDIDATE_PROFILE_PLAN,
    GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY,
    MODEL,
    PROFILE_ID,
    PROFILE_VERSION,
    PROVIDER_ID,
    REQUEST_POLICY_ID,
    REQUEST_POLICY_VERSION,
    RUNTIME_PROFILE_ID,
    RUNTIME_PROFILE_VERSION,
    require_glm53_flash_low_candidate_request_policy,
)


SCHEMA_VERSION = "1.0"
PROTOCOL_ID = "glm-5.3-flash-candidate-low-4096-heldout-domain-gate"
BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"
PROTOCOL_MAX_CALLS = 3
DEFAULT_OUTPUT = Path(
    "data/evaluation/results/provider_capabilities/"
    "zhipu_glm53_flash_candidate_low_4096_domain_gate_rq227_v1.json"
)
DEFAULT_RUNS_ROOT = Path("data/runs/evaluation/glm53_low_profile_domain")

GitShaText = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
Sha256Text = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
NonBlankText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
SafeCodeText = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z][a-z0-9_.:-]{0,127}$"),
]

_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN_KEYS = frozenset(
    {
        "body",
        "content",
        "reasoning",
        "reasoning_content",
        "tool_arguments",
        "tool_results",
        "prompt",
        "messages",
        "headers",
        "authorization",
        "api_key",
        "secret",
        "request_id",
        "sdk_response",
        "response_body",
    }
)


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LowProfileCaseResource(_FrozenModel):
    """Measured resources for one case, with no price claim."""

    case_id: NonBlankText
    calls_used: int = Field(ge=0, le=CANDIDATE_CASE_MAX_CALLS)
    max_calls: Literal[CANDIDATE_CASE_MAX_CALLS] = CANDIDATE_CASE_MAX_CALLS
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0, le=CANDIDATE_CASE_MAX_TOKENS)
    max_observed_tokens: Literal[CANDIDATE_CASE_MAX_TOKENS] = (
        CANDIDATE_CASE_MAX_TOKENS
    )
    latency_ms: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_totals(self) -> "LowProfileCaseResource":
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("case total_tokens must equal input plus output")
        return self


class LowProfileResourceSnapshot(_FrozenModel):
    """Body-free candidate-domain resource ledger."""

    provider_id: Literal[PROVIDER_ID] = PROVIDER_ID
    model: Literal[MODEL] = MODEL
    calls_used: int = Field(ge=0, le=CANDIDATE_DOMAIN_MAX_CALLS)
    max_calls: Literal[CANDIDATE_DOMAIN_MAX_CALLS] = CANDIDATE_DOMAIN_MAX_CALLS
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0, le=CANDIDATE_DOMAIN_MAX_TOKENS)
    max_observed_tokens: Literal[CANDIDATE_DOMAIN_MAX_TOKENS] = (
        CANDIDATE_DOMAIN_MAX_TOKENS
    )
    latency_ms: int = Field(ge=0)
    case_resources: tuple[LowProfileCaseResource, ...]
    stop_code: SafeCodeText | None = None
    provider_error_code: SafeCodeText | None = None
    monetary_cost_status: Literal["unknown"] = "unknown"

    @model_validator(mode="after")
    def validate_totals(self) -> "LowProfileResourceSnapshot":
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("domain total_tokens must equal input plus output")
        if len({row.case_id for row in self.case_resources}) != len(
            self.case_resources
        ):
            raise ValueError("case resource identities must be unique")
        if sum(row.calls_used for row in self.case_resources) != self.calls_used:
            raise ValueError("case call totals must match domain call total")
        if sum(row.input_tokens for row in self.case_resources) != self.input_tokens:
            raise ValueError("case input totals must match domain input total")
        if sum(row.output_tokens for row in self.case_resources) != self.output_tokens:
            raise ValueError("case output totals must match domain output total")
        return self


class LowProfileControlSnapshot(_FrozenModel):
    """Safe stop projection; provider error detail is allowlisted text only."""

    global_stop: SafeCodeText | None = None
    provider_stop: SafeCodeText | None = None
    provider_error_code: SafeCodeText | None = None


class LowProfileDomainAdmission(_FrozenModel):
    """No-I/O proof that the fresh candidate run may be constructed."""

    schema_version: Literal[SCHEMA_VERSION] = SCHEMA_VERSION
    experiment_id: Sha256Text
    protocol_id: Literal[PROTOCOL_ID] = PROTOCOL_ID
    provider_id: Literal[PROVIDER_ID] = PROVIDER_ID
    requested_model: Literal[MODEL] = MODEL
    base_url: Literal[BASE_URL] = BASE_URL
    candidate_profile_id: Literal[PROFILE_ID] = PROFILE_ID
    candidate_profile_version: Literal[PROFILE_VERSION] = PROFILE_VERSION
    runtime_profile_id: Literal[RUNTIME_PROFILE_ID] = RUNTIME_PROFILE_ID
    runtime_profile_version: Literal[RUNTIME_PROFILE_VERSION] = (
        RUNTIME_PROFILE_VERSION
    )
    request_policy_id: Literal[REQUEST_POLICY_ID] = REQUEST_POLICY_ID
    request_policy_version: Literal[REQUEST_POLICY_VERSION] = REQUEST_POLICY_VERSION
    implementation_sha: GitShaText
    public_ci_sha: GitShaText
    public_ci_success_confirmed: Literal[True] = True
    public_ci_scope: NonBlankText
    asset_admission: GLM53LowProfileAssetAdmission
    dataset_sha256: Sha256Text
    dataset_file_sha256: Sha256Text
    input_plan_file_sha256: Sha256Text
    prompt_context_snapshot_sha256: Sha256Text
    prompt_context_snapshot_file_sha256: Sha256Text
    execution_plan: DomainCaseExecutionPlan
    protocol_result_sha256: Sha256Text
    protocol_code_sha: GitShaText
    protocol_calls: Literal[PROTOCOL_MAX_CALLS] = PROTOCOL_MAX_CALLS
    protocol_input_tokens: int = Field(ge=0)
    protocol_output_tokens: int = Field(ge=0)
    protocol_total_tokens: int = Field(ge=0)
    domain_max_calls: Literal[CANDIDATE_DOMAIN_MAX_CALLS] = CANDIDATE_DOMAIN_MAX_CALLS
    case_max_calls: Literal[CANDIDATE_CASE_MAX_CALLS] = CANDIDATE_CASE_MAX_CALLS
    domain_max_tokens: Literal[CANDIDATE_DOMAIN_MAX_TOKENS] = CANDIDATE_DOMAIN_MAX_TOKENS
    case_max_tokens: Literal[CANDIDATE_CASE_MAX_TOKENS] = CANDIDATE_CASE_MAX_TOKENS
    sdk_max_retries: Literal[0] = 0
    max_revisions: Literal[0] = 0
    candidate_registered: Literal[False] = False
    production_admitted: Literal[False] = False
    external_provider_calls: Literal[0] = 0
    held_out_executed: Literal[False] = False
    provider_construction_authorized: Literal[False] = False
    ready_for_real_call: Literal[True] = True

    @model_validator(mode="after")
    def validate_identity(self) -> "LowProfileDomainAdmission":
        if self.implementation_sha != self.public_ci_sha:
            raise ValueError("implementation SHA must match public CI SHA")
        if self.protocol_total_tokens != (
            self.protocol_input_tokens + self.protocol_output_tokens
        ):
            raise ValueError("protocol token total is inconsistent")
        if self.execution_plan.case_ids != self.asset_admission.case_ids:
            raise ValueError("execution plan does not match fresh asset admission")
        if self.dataset_file_sha256 != self.asset_admission.dataset_sha256:
            raise ValueError("dataset file identity does not match asset admission")
        if self.input_plan_file_sha256 != self.asset_admission.input_plan_sha256:
            raise ValueError("input plan file identity does not match asset admission")
        if self.prompt_context_snapshot_sha256 != self.asset_admission.snapshot_sha256:
            raise ValueError("snapshot identity does not match asset admission")
        expected = _admission_identity(self)
        if self.experiment_id != expected:
            raise ValueError("low-profile domain experiment identity is inconsistent")
        return self

class LowProfileDomainGateResult(_FrozenModel):
    """Immutable body-free result of one authorized fresh-domain attempt."""

    schema_version: Literal[SCHEMA_VERSION] = SCHEMA_VERSION
    protocol_id: Literal[PROTOCOL_ID] = PROTOCOL_ID
    experiment_id: Sha256Text
    run_timestamp_utc: datetime
    admission: LowProfileDomainAdmission
    resources: LowProfileResourceSnapshot
    control: LowProfileControlSnapshot
    protocol_calls: Literal[PROTOCOL_MAX_CALLS] = PROTOCOL_MAX_CALLS
    protocol_total_tokens: int = Field(ge=0)
    domain_calls_used: int = Field(ge=0, le=CANDIDATE_DOMAIN_MAX_CALLS)
    domain_total_tokens: int = Field(ge=0, le=CANDIDATE_DOMAIN_MAX_TOKENS)
    cumulative_calls_used: int = Field(ge=0, le=PROTOCOL_MAX_CALLS + CANDIDATE_DOMAIN_MAX_CALLS)
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
    def validate_composition(self) -> "LowProfileDomainGateResult":
        if self.experiment_id != self.admission.experiment_id:
            raise ValueError("result and admission identities differ")
        if tuple(row.case_id for row in self.cases) != self.admission.execution_plan.case_ids:
            raise ValueError("result cases must follow execution plan order")
        if self.resources.calls_used != self.domain_calls_used:
            raise ValueError("resource and domain call totals differ")
        if self.resources.total_tokens != self.domain_total_tokens:
            raise ValueError("resource and domain token totals differ")
        if self.protocol_total_tokens != self.admission.protocol_total_tokens:
            raise ValueError("protocol token identity drifted")
        if self.cumulative_calls_used != self.protocol_calls + self.domain_calls_used:
            raise ValueError("cumulative call total is inconsistent")
        if self.cumulative_total_tokens != (
            self.protocol_total_tokens + self.domain_total_tokens
        ):
            raise ValueError("cumulative token total is inconsistent")
        executed = any(row.status != "skipped" for row in self.cases)
        if self.held_out_executed is not executed:
            raise ValueError("held_out_executed does not match case state")
        complete = all(row.status == "executed" for row in self.cases)
        if (self.candidate is None) is not (self.evaluation is None):
            raise ValueError("candidate and evaluation must appear together")
        if complete is not (self.candidate is not None):
            raise ValueError("complete cases require aggregate evidence")
        if self.candidate is not None and self.evaluation is not None:
            if self.candidate.external_provider_calls != self.domain_calls_used:
                raise ValueError("candidate call total is inconsistent")
            if self.evaluation.external_provider_calls != self.domain_calls_used:
                raise ValueError("evaluation call total is inconsistent")
        expected_admitted = all(
            (
                complete,
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
                self.control.provider_stop is None,
            )
        )
        if self.admitted is not expected_admitted:
            raise ValueError("admitted does not match mandatory domain evidence")
        if self.candidate_registered or self.production_admitted:
            raise ValueError("domain gate cannot register or admit production")
        if len(set(self.unsupported_boundaries)) != len(self.unsupported_boundaries):
            raise ValueError("unsupported boundaries must be unique")
        return self


@dataclass(frozen=True)
class LowProfilePreparedRun:
    admission: LowProfileDomainAdmission
    assets: GLM53LowProfileAssetAdmission
    dataset: DomainEvaluationDataset
    input_plan: LoadedDomainCaseInputPlan


@dataclass(frozen=True)
class LowProfileDomainGateOptions:
    confirm_real_call: bool
    public_ci_sha: str | None = None
    confirm_public_ci_success: bool = False
    implementation_sha: str | None = None
    preflight_only: bool = False
    max_calls: int = CANDIDATE_DOMAIN_MAX_CALLS
    dataset: Path = DATASET_PATH
    input_plan: Path = INPUT_PLAN_PATH
    snapshot: Path = SNAPSHOT_PATH
    protocol_result: Path = Path(
        "data/evaluation/results/provider_capabilities/"
        "zhipu_glm53_flash_candidate_low_4096_g53_3l_rq225_v1.json"
    )
    output: Path = DEFAULT_OUTPUT
    runs_root: Path = DEFAULT_RUNS_ROOT


def build_low_profile_preflight(
    *,
    project_root: str | Path,
    implementation_sha: str,
    public_ci_sha: str,
    confirm_public_ci_success: bool,
    dataset_path: str | Path = DATASET_PATH,
    input_plan_path: str | Path = INPUT_PLAN_PATH,
    snapshot_path: str | Path = SNAPSHOT_PATH,
    protocol_result_path: str | Path = LowProfileDomainGateOptions.protocol_result,
) -> LowProfilePreparedRun:
    """Validate all fresh identities without reading credentials or making a client."""

    _require_git_sha(implementation_sha, "implementation_sha")
    _require_git_sha(public_ci_sha, "public_ci_sha")
    if implementation_sha != public_ci_sha or confirm_public_ci_success is not True:
        raise ValueError("implementation/public CI identity is not confirmed")
    root = Path(project_root).resolve()
    dataset_file = _inside_file(root, dataset_path, "dataset")
    plan_file = _inside_file(root, input_plan_path, "input plan")
    snapshot_file = _inside_file(root, snapshot_path, "snapshot")
    protocol_file = _inside_file(root, protocol_result_path, "protocol result")

    assets = admit_low_profile_assets(
        project_root=root,
        confirm_rules_frozen=True,
        dataset_path=dataset_file,
        input_plan_path=plan_file,
        snapshot_path=snapshot_file,
    )
    dataset = load_domain_dataset(dataset_file)
    loaded_plan = load_domain_case_input_plan(
        plan_file,
        project_root=root,
        dataset=dataset,
    )
    snapshot = load_prompt_context_snapshot(snapshot_file)
    if _sha256_file(dataset_file) != assets.dataset_sha256:
        raise ValueError("dataset bytes changed after asset admission")
    if _sha256_file(plan_file) != assets.input_plan_sha256:
        raise ValueError("input plan bytes changed after asset admission")
    if snapshot.snapshot_sha256 != assets.snapshot_sha256:
        raise ValueError("snapshot identity changed after asset admission")
    if snapshot.snapshot_id != SNAPSHOT_ID:
        raise ValueError("snapshot identity does not match low-profile gate")

    summary = json.loads(loaded_plan.player_summary_path.read_text(encoding="utf-8"))
    report = loaded_plan.deterministic_report_path.read_text(encoding="utf-8")
    rebuilt = build_prompt_context_snapshot_for_cases(
        skills_root=root / "skills",
        player_summary=summary,
        deterministic_report=report,
        cases=loaded_plan.artifact.cases,
        snapshot_id=snapshot.snapshot_id,
        evaluation_contract_version=snapshot.evaluation_contract.rsplit("@", 1)[-1],
    )
    if rebuilt != snapshot:
        raise ValueError("frozen low-profile Prompt/Context snapshot cannot be rebuilt")

    protocol_raw = protocol_file.read_bytes()
    protocol = GLM53LowProfileProtocolReport.model_validate_json(protocol_raw)
    protocol_sha = hashlib.sha256(protocol_raw).hexdigest()
    if (
        not protocol.protocol.admitted
        or protocol.provider_id != PROVIDER_ID
        or protocol.requested_model != MODEL
        or protocol.provider_call_count != PROTOCOL_MAX_CALLS
        or protocol.protocol_code_sha != protocol.implementation_sha
        or protocol.request_policy_id != REQUEST_POLICY_ID
        or protocol.candidate_profile_id != PROFILE_ID
    ):
        raise ValueError("prior low-profile protocol evidence is not admitted")
    if protocol.evidence_origin != "real_provider":
        raise ValueError("held-out gate requires the admitted real protocol evidence")

    # The protocol implementation is allowed to be an ancestor of the current
    # gate implementation: the new gate itself must still be covered by the
    # exact public CI SHA supplied above.
    if protocol.implementation_sha != implementation_sha and not _is_ancestor(
        root, protocol.implementation_sha, implementation_sha
    ):
        raise ValueError("prior protocol code is not an ancestor of this gate")

    admission_data: dict[str, Any] = {
        "experiment_id": "0" * 64,
        "implementation_sha": implementation_sha,
        "public_ci_sha": public_ci_sha,
        "public_ci_scope": "candidate-low-profile-domain-gate-exact-sha",
        "asset_admission": assets,
        "dataset_sha256": _digest_json(dataset.model_dump(mode="json")),
        "dataset_file_sha256": _sha256_file(dataset_file),
        "input_plan_file_sha256": _sha256_file(plan_file),
        "prompt_context_snapshot_sha256": snapshot.snapshot_sha256,
        "prompt_context_snapshot_file_sha256": _sha256_file(snapshot_file),
        "execution_plan": loaded_plan.execution_plan,
        "protocol_result_sha256": protocol_sha,
        "protocol_code_sha": protocol.protocol_code_sha,
        "protocol_input_tokens": protocol.input_tokens,
        "protocol_output_tokens": protocol.output_tokens,
        "protocol_total_tokens": protocol.total_tokens,
    }
    draft = LowProfileDomainAdmission.model_construct(**admission_data)
    admission_data["experiment_id"] = _admission_identity(draft)
    admission = LowProfileDomainAdmission(**admission_data)
    return LowProfilePreparedRun(
        admission=admission,
        assets=assets,
        dataset=dataset,
        input_plan=loaded_plan,
    )


def run_low_profile_domain_gate(
    *,
    admission: LowProfileDomainAdmission,
    dataset: DomainEvaluationDataset,
    provider: LLMProvider,
    case_executor: Any,
    confirm_real_call: bool = True,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    clock: Callable[[], float] = time.monotonic,
) -> LowProfileDomainGateResult:
    """Run the three fresh cases sequentially under the low-profile budget wall."""

    if not isinstance(admission, LowProfileDomainAdmission):
        raise TypeError("admission must be a LowProfileDomainAdmission")
    if confirm_real_call is not True:
        raise RuntimeError("real low-profile domain calls require explicit confirmation")
    if not isinstance(dataset, DomainEvaluationDataset):
        raise TypeError("dataset must be a DomainEvaluationDataset")
    if tuple(row.case_id for row in dataset.cases) != admission.execution_plan.case_ids:
        raise ValueError("runtime Dataset case order does not match admission")
    if _digest_json(dataset.model_dump(mode="json")) != admission.dataset_sha256:
        raise ValueError("runtime Dataset content does not match admission")
    policy = require_glm53_flash_low_candidate_request_policy()
    if (
        getattr(provider, "provider_name", None) != PROVIDER_ID
        or getattr(provider, "model_name", None) != MODEL
    ):
        raise ValueError("runtime Provider does not match low-profile candidate")
    if not all(
        (
            provider.capabilities.text_chat,
            provider.capabilities.tool_calling,
            provider.capabilities.structured_output,
        )
    ):
        raise ValueError("runtime Provider lacks admitted capabilities")
    if getattr(case_executor, "execution_plan", None) != admission.execution_plan:
        raise ValueError("case executor does not match the admitted execution plan")
    if getattr(case_executor, "runtime_profile", None) is not None:
        raise ValueError("low-profile executor must not bind a product runtime profile")
    if getattr(case_executor, "request_policy", None) is not policy:
        raise ValueError("case executor does not use the exact low-profile policy")

    state = CandidateEvaluationBudgetState()
    records: list[DomainCaseExecutionRecord] = []
    observations: list[DomainCandidateCase] = []
    for case in dataset.cases:
        if state.stop_code is not None:
            records.append(
                DomainCaseExecutionRecord(
                    case_id=case.case_id,
                    status="skipped",
                    failure_code=_failure_enum(state.stop_code),
                )
            )
            continue
        state.register_case(case.case_id)
        before = state.case_snapshot(case.case_id)
        controlled = CandidateEvaluationBudgetedProvider(
            provider=provider,
            state=state,
            case_id=case.case_id,
            request_policy=policy,
            clock=clock,
        )
        try:
            semantic = case_executor.execute(
                case_id=case.case_id,
                provider=controlled,
            )
            if not isinstance(semantic, DomainCaseSemanticObservation):
                raise TypeError("case executor returned an invalid observation")
            if semantic.case_id != case.case_id:
                raise ValueError("case observation identity mismatch")
        except ProviderError as exc:
            state.stop("provider_error", provider_error_code=exc.code)
            records.append(
                DomainCaseExecutionRecord(
                    case_id=case.case_id,
                    status="failed",
                    failure_code=_failure_enum(_provider_failure_code(exc)),
                )
            )
            continue
        except Exception:
            state.stop("domain_case_observation_invalid")
            records.append(
                DomainCaseExecutionRecord(
                    case_id=case.case_id,
                    status="failed",
                    failure_code=ExperimentFailureCode.DOMAIN_CASE_OBSERVATION_INVALID,
                )
            )
            continue

        after = state.case_snapshot(case.case_id)
        observation = _candidate_case_from_semantics(
            semantic,
            before=before,
            after=after,
        )
        case_result = _evaluate_one_case(dataset, case_id=case.case_id, observation=observation)
        failure = _case_failure(state, semantic, case_result)
        if failure is not None:
            if failure is ExperimentFailureCode.UNSAFE_PUBLICATION:
                state.stop("unsafe_publication")
            else:
                state.stop(failure.value, provider_error_code=semantic.safe_provider_error_code)
        observations.append(observation)
        records.append(
            DomainCaseExecutionRecord(
                case_id=case.case_id,
                status="executed",
                failure_code=failure,
                observation=observation,
                evaluation=case_result,
            )
        )

    candidate: DomainCandidate | None = None
    evaluation: DomainEvaluationResult | None = None
    if len(observations) == len(dataset.cases):
        candidate = DomainCandidate(
            schema_version=dataset.schema_version,
            candidate_id=f"zhipu-glm53-flash-low-domain-{admission.experiment_id[:16]}",
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
    control = LowProfileControlSnapshot(
        global_stop=("unsafe_publication" if state.stop_code == "unsafe_publication" else None),
        provider_stop=(
            None
            if state.stop_code in {None, "unsafe_publication"}
            else _safe_code(state.stop_code)
        ),
        provider_error_code=(
            _safe_code(state.provider_error_code)
            if state.provider_error_code
            else None
        ),
    )
    clean = all(row.status == "executed" and row.failure_code is None for row in records)
    admitted = all(
        (
            clean,
            evaluation is not None,
            evaluation is not None and evaluation.task_outcome_accuracy == 1.0,
            evaluation is not None and evaluation.failure_classification_accuracy == 1.0,
            evaluation is not None and evaluation.unsafe_publication_rate == 0.0,
            resources.stop_code is None,
            control.global_stop is None,
            control.provider_stop is None,
        )
    )
    return LowProfileDomainGateResult(
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
        unsupported_boundaries=(
            "产品 Runtime 注册",
            "默认模型切换",
            "streaming 生产能力",
            "黄金切片",
            "安全/部署/合规",
            "8F final evaluation",
        ),
    )


def create_low_profile_provider(
    settings: ZhipuSettings,
    *,
    client_factory: Callable[..., Any] = OpenAI,
) -> ZhipuProvider:
    """Construct the candidate provider only after output reservation."""

    if settings.model != MODEL or settings.base_url.rstrip("/") != BASE_URL.rstrip("/"):
        raise ValueError("runtime settings do not match the low-profile Flash gate")
    client = client_factory(
        api_key=settings.api_key,
        base_url=settings.base_url,
        timeout=GLM53_FLASH_LOW_CANDIDATE_PROFILE_PLAN.transport_timeout_s,
        max_retries=0,
    )
    return ZhipuProvider.from_candidate_profile(
        client=client,
        model=settings.model,
        profile=GLM53_FLASH_LOW_CANDIDATE_PROFILE_PLAN.thinking_profile,
    )


def run_cli(
    options: LowProfileDomainGateOptions,
    *,
    repository_root: Path | None = None,
    environment_loader: Callable[[Path], Mapping[str, str]] | None = None,
    provider_factory: Callable[[ZhipuSettings], LLMProvider] = create_low_profile_provider,
    code_sha_reader: Callable[[Path], str] | None = None,
) -> LowProfileDomainAdmission | LowProfileDomainGateResult:
    """Run no-I/O admission, reserve output, then execute one real gate."""

    if options.max_calls != CANDIDATE_DOMAIN_MAX_CALLS:
        raise ValueError("low-profile domain gate requires exactly 12 calls")
    if not options.preflight_only and options.confirm_real_call is not True:
        raise RuntimeError("real low-profile domain calls require explicit confirmation")
    root = (repository_root or Path(__file__).resolve().parents[2]).resolve()
    if not options.preflight_only:
        _require_clean_worktree(root)
    current_sha = options.implementation_sha or (code_sha_reader or _read_head_sha)(root)
    public_sha = options.public_ci_sha or current_sha
    prepared = build_low_profile_preflight(
        project_root=root,
        implementation_sha=current_sha,
        public_ci_sha=public_sha,
        confirm_public_ci_success=(
            options.confirm_public_ci_success or options.preflight_only
        ),
        dataset_path=options.dataset,
        input_plan_path=options.input_plan,
        snapshot_path=options.snapshot,
        protocol_result_path=options.protocol_result,
    )
    if options.preflight_only:
        return prepared.admission

    output = _inside_output(root, options.output)
    if output.exists() or output.is_symlink():
        raise FileExistsError("low-profile domain evidence is immutable")
    output.parent.mkdir(parents=True, exist_ok=True)
    reservation = _OutputReservation.reserve(output, prepared.admission.experiment_id)
    try:
        load_environment = environment_loader or _load_environment
        settings = load_zhipu_settings(load_environment(root))
        provider = provider_factory(settings)
        runs_root = _inside_directory(root, options.runs_root, "runs root")
        runs_root.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="glm53-low-domain-", dir=str(runs_root.parent)) as temporary:
            executor = ProductionDomainCaseExecutor(
                project_root=root,
                input_plan=prepared.input_plan,
                runs_root=Path(temporary),
                request_policy=GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY,
            )
            result = run_low_profile_domain_gate(
                admission=prepared.admission,
                dataset=prepared.dataset,
                provider=provider,
                case_executor=executor,
                confirm_real_call=options.confirm_real_call,
            )
        reservation.commit(result)
        return result
    except Exception:
        reservation.abandon()
        raise


def canonical_result_bytes(result: LowProfileDomainGateResult) -> bytes:
    if not isinstance(result, LowProfileDomainGateResult):
        raise TypeError("result must be a LowProfileDomainGateResult")
    payload = result.model_dump(mode="json")
    _assert_body_free(payload)
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("utf-8")


def write_result_create_only(
    result: LowProfileDomainGateResult,
    *,
    repository_root: str | Path,
    output: str | Path = DEFAULT_OUTPUT,
) -> Path:
    root = Path(repository_root).resolve()
    target = _inside_output(root, output)
    if target.exists() or target.is_symlink():
        raise FileExistsError("low-profile domain evidence is immutable")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(canonical_result_bytes(result))
    return target


class _OutputReservation:
    def __init__(self, path: Path, experiment_id: str, stream) -> None:
        self.path = path
        self.experiment_id = experiment_id
        self._stream = stream
        self._committed = False

    @classmethod
    def reserve(cls, path: Path, experiment_id: str) -> "_OutputReservation":
        stream = path.open("x", encoding="utf-8", newline="\n")
        return cls(path, experiment_id, stream)

    def commit(self, result: LowProfileDomainGateResult) -> None:
        if self._committed or self._stream.closed:
            raise RuntimeError("low-profile output is already finalized")
        if result.experiment_id != self.experiment_id:
            raise ValueError("result does not match reserved experiment")
        self._stream.write(canonical_result_bytes(result).decode("utf-8"))
        self._stream.flush()
        self._stream.close()
        self._committed = True

    def abandon(self) -> None:
        if not self._stream.closed:
            self._stream.close()


def _candidate_case_from_semantics(
    semantic: DomainCaseSemanticObservation,
    *,
    before: Mapping[str, int],
    after: Mapping[str, int],
) -> DomainCandidateCase:
    return DomainCandidateCase(
        case_id=semantic.case_id,
        provider_calls=after["calls_used"] - before["calls_used"],
        normalized_response_count=semantic.normalized_response_count,
        safe_provider_error_code=semantic.safe_provider_error_code,
        agent_status=semantic.agent_status,
        agent_stop_reason=semantic.agent_stop_reason,
        proposed_tool_names=semantic.proposed_tool_names,
        successful_tool_names=semantic.successful_tool_names,
        evidence_source_ids=semantic.evidence_source_ids,
        evidence_diagnostics=semantic.evidence_diagnostics,
        fact_check_passed=semantic.fact_check_passed,
        citation_check_passed=semantic.citation_check_passed,
        injection_check_passed=semantic.injection_check_passed,
        evaluation_validated=semantic.evaluation_validated,
        evaluation_score=semantic.evaluation_score,
        terminal_status=semantic.terminal_status,
        terminal_reason=semantic.terminal_reason,
        latency_ms=after["latency_ms"] - before["latency_ms"],
        input_tokens=after["input_tokens"] - before["input_tokens"],
        output_tokens=after["output_tokens"] - before["output_tokens"],
        estimated_cost=None,
        provenance_sha256=semantic.provenance_sha256,
    )


def _evaluate_one_case(
    dataset: DomainEvaluationDataset,
    *,
    case_id: str,
    observation: DomainCandidateCase,
) -> DomainCaseResult:
    case = next(row for row in dataset.cases if row.case_id == case_id)
    one_dataset = DomainEvaluationDataset.model_validate(
        {
            **dataset.model_dump(mode="json"),
            "case_count": 1,
            "cases": [case.model_dump(mode="json")],
        }
    )
    candidate = DomainCandidate(
        schema_version=dataset.schema_version,
        candidate_id=f"zhipu-{case_id}",
        candidate_kind="real_provider_recorded",
        dataset_id=dataset.dataset_id,
        dataset_version=dataset.dataset_version,
        contract_snapshot=dataset.contract_snapshot,
        external_provider_calls=observation.provider_calls,
        case_count=1,
        cases=(observation,),
    )
    return evaluate_domain_candidate(one_dataset, candidate).cases[0]


def _case_failure(
    state: CandidateEvaluationBudgetState,
    semantic: DomainCaseSemanticObservation,
    result: DomainCaseResult,
) -> ExperimentFailureCode | None:
    if state.stop_code is not None:
        return _failure_enum(state.stop_code)
    if semantic.safe_provider_error_code:
        return _failure_enum(semantic.safe_provider_error_code)
    if result.unsafe_publication:
        return ExperimentFailureCode.UNSAFE_PUBLICATION
    if not result.task_outcome_match or not result.failure_classification_match:
        return ExperimentFailureCode.DOMAIN_CASE_OUTCOME_MISMATCH
    return None


def _resource_snapshot(state: CandidateEvaluationBudgetState) -> LowProfileResourceSnapshot:
    rows = tuple(
        LowProfileCaseResource(
            case_id=case_id,
            calls_used=value["calls_used"],
            input_tokens=value["input_tokens"],
            output_tokens=value["output_tokens"],
            total_tokens=value["total_tokens"],
            latency_ms=value["latency_ms"],
        )
        for case_id, value in state.snapshot()["cases"].items()
    )
    snap = state.snapshot()
    return LowProfileResourceSnapshot(
        calls_used=snap["calls_used"],
        input_tokens=snap["input_tokens"],
        output_tokens=snap["output_tokens"],
        total_tokens=snap["total_tokens"],
        latency_ms=snap["latency_ms"],
        case_resources=rows,
        stop_code=_safe_code(snap["stop_code"]) if snap["stop_code"] else None,
        provider_error_code=(
            _safe_code(snap["provider_error_code"])
            if snap["provider_error_code"]
            else None
        ),
    )


def _failure_enum(code: str | ExperimentFailureCode) -> ExperimentFailureCode:
    if isinstance(code, ExperimentFailureCode):
        return code
    aliases = {
        "provider_error": ExperimentFailureCode.PROVIDER_ERROR_UNKNOWN,
        "provider_response_invalid": ExperimentFailureCode.PROVIDER_RESPONSE_INVALID,
        "external_call_budget_exhausted": ExperimentFailureCode.EXTERNAL_CALL_BUDGET_EXHAUSTED,
        "token_budget_exhausted": ExperimentFailureCode.TOKEN_BUDGET_EXHAUSTED,
        "unsafe_publication": ExperimentFailureCode.UNSAFE_PUBLICATION,
    }
    if code in aliases:
        return aliases[code]
    try:
        return ExperimentFailureCode(code)
    except ValueError:
        return ExperimentFailureCode.DOMAIN_CASE_OBSERVATION_INVALID


def _provider_failure_code(error: ProviderError) -> str:
    try:
        return classify_provider_error(error).value
    except Exception:
        return "provider_error"


def _admission_identity(admission: LowProfileDomainAdmission) -> str:
    payload = admission.model_dump(mode="json", exclude={"experiment_id"})
    return _digest_json(payload)


def _digest_json(value: object) -> str:
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


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_code(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    return normalized if re.fullmatch(r"[a-z][a-z0-9_.:-]{0,127}", normalized) else "unsafe_error_code"


def _require_git_sha(value: str, label: str) -> None:
    if not isinstance(value, str) or _GIT_SHA.fullmatch(value) is None:
        raise ValueError(f"{label} must be a lowercase git SHA")


def _read_head_sha(root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    value = completed.stdout.strip()
    _require_git_sha(value, "HEAD")
    return value


def _is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=root,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0


def _require_clean_worktree(root: Path) -> None:
    completed = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    if completed.stdout.strip():
        raise RuntimeError("real low-profile domain gate requires a clean worktree")


def _inside_file(root: Path, value: str | Path, label: str) -> Path:
    candidate = Path(value)
    resolved = (candidate if candidate.is_absolute() else root / candidate).resolve()
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise FileNotFoundError(f"{label} must be a file inside the repository")
    return resolved


def _inside_directory(root: Path, value: str | Path, label: str) -> Path:
    candidate = Path(value)
    resolved = (candidate if candidate.is_absolute() else root / candidate).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"{label} must stay inside the repository")
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


def _assert_body_free(value: object) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str) and key.strip().lower() in _FORBIDDEN_KEYS:
                raise ValueError("low-profile domain result contains a forbidden body field")
            _assert_body_free(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _assert_body_free(item)


def _parse_args(argv: Sequence[str] | None = None) -> LowProfileDomainGateOptions:
    import argparse

    parser = argparse.ArgumentParser(description="Run the bounded GLM-5.3 low-profile held-out domain gate.")
    parser.add_argument("--confirm-real-call", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--implementation-sha")
    parser.add_argument("--public-ci-sha")
    parser.add_argument("--confirm-public-ci-success", action="store_true")
    parser.add_argument("--max-calls", type=int, default=CANDIDATE_DOMAIN_MAX_CALLS)
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    parser.add_argument("--input-plan", type=Path, default=INPUT_PLAN_PATH)
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT_PATH)
    parser.add_argument("--protocol-result", type=Path, default=LowProfileDomainGateOptions.protocol_result)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    values = parser.parse_args(argv)
    return LowProfileDomainGateOptions(
        confirm_real_call=values.confirm_real_call,
        public_ci_sha=values.public_ci_sha,
        confirm_public_ci_success=values.confirm_public_ci_success,
        implementation_sha=values.implementation_sha,
        preflight_only=values.preflight_only,
        max_calls=values.max_calls,
        dataset=values.dataset,
        input_plan=values.input_plan,
        snapshot=values.snapshot,
        protocol_result=values.protocol_result,
        output=values.output,
        runs_root=values.runs_root,
    )


def main(argv: Sequence[str] | None = None) -> int:
    result = run_cli(_parse_args(argv))
    if isinstance(result, LowProfileDomainAdmission):
        print(
            f"provider={result.provider_id} model={result.requested_model} "
            "preflight=true external_provider_calls=0 held_out_executed=false"
        )
    else:
        print(
            f"provider={result.admission.provider_id} model={result.admission.requested_model} "
            f"domain_calls={result.domain_calls_used}/{CANDIDATE_DOMAIN_MAX_CALLS} "
            f"cumulative_calls={result.cumulative_calls_used}/{PROTOCOL_MAX_CALLS + CANDIDATE_DOMAIN_MAX_CALLS} "
            f"admitted={str(result.admitted).lower()}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "BASE_URL",
    "DEFAULT_OUTPUT",
    "LowProfileCaseResource",
    "LowProfileControlSnapshot",
    "LowProfileDomainAdmission",
    "LowProfileDomainGateOptions",
    "LowProfileDomainGateResult",
    "LowProfilePreparedRun",
    "LowProfileResourceSnapshot",
    "PROTOCOL_ID",
    "build_low_profile_preflight",
    "canonical_result_bytes",
    "create_low_profile_provider",
    "main",
    "run_cli",
    "run_low_profile_domain_gate",
    "write_result_create_only",
]
