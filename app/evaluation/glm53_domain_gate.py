"""Isolated, bounded GLM-5.3 Flash fresh-domain adoption gate.

This module intentionally does not change the production Provider default.  It
binds a new held-out Dataset, input plan and Prompt/Context snapshot to the
already admitted three-call GLM-5.3 Flash protocol slice, then runs the same
production Skill/Agent/RAG/Evaluation/Harness path behind a small, fail-closed
resource controller.  Only allowlisted semantic observations cross the public
result boundary; prompts, model text, reasoning, request IDs and credentials
never do.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Annotated, Any, Literal

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.evaluation.domain_e2e import (
    DomainCandidate,
    DomainCandidateCase,
    DomainDatasetRole,
    DomainEvaluationDataset,
    DomainEvaluationResult,
    DomainCaseResult,
    evaluate_domain_candidate,
    load_domain_dataset,
    validate_domain_dataset_usage,
)
from app.evaluation.prompt_context_identity import (
    PromptContextSnapshot,
    build_prompt_context_snapshot_for_cases,
    case_context_sha256,
    load_prompt_context_snapshot,
)
from app.evaluation.provider_adapter_protocol import AdapterProtocolSliceReport
from app.evaluation.provider_adoption import (
    ExperimentFailureCode,
    classify_provider_error,
)
from app.evaluation.provider_domain_experiment import (
    DomainCaseExecutionPlan,
    DomainCaseSemanticObservation,
    DomainCaseExecutionRecord,
    ImmutableDomainExperimentOutput,
)
from app.evaluation.provider_domain_plan import (
    DomainCaseContextCommitment,
    LoadedDomainCaseInputPlan,
    load_domain_case_input_plan,
)
from app.evaluation.provider_domain_production import ProductionDomainCaseExecutor
from app.evaluation.provider_domain_skill import load_prior_adapter_evidence
from app.model_runtime import GLM53_FLASH_RUNTIME_PROFILE, ModelRuntimeProfile
from app.providers.config import ZhipuSettings, load_zhipu_settings
from app.providers.errors import ProviderError, ProviderResponseError
from app.providers.models import ChatRequest, ChatResponse
from app.providers.protocol import LLMProvider
from app.providers.zhipu import ZhipuProvider


GLM53_PROVIDER_ID = "zhipu"
GLM53_MODEL = "glm-5.3-flash"
GLM53_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"
GLM53_PROFILE_ID = "glm-5.3-flash-enabled-max-replay"
# The first held-out domain artifact was admitted with the earlier, lower
# reasoning profile. Keep that immutable result readable while new admissions
# use the current max-replay profile above.
GLM53_LEGACY_PROFILE_ID = "glm-5.3-flash-enabled-low"
# Runtime budget identity is separate from the thinking profile identity.  The
# old JSON evidence predates this field and remains readable through the
# legacy marker below; every new held-out run must carry the specialised
# Flash profile explicitly.
GLM53_RUNTIME_PROFILE_ID = GLM53_FLASH_RUNTIME_PROFILE.profile_id
GLM53_LEGACY_RUNTIME_PROFILE_ID = "legacy-manifest-budget"
GLM53_RUNTIME_PROFILE_VERSION = GLM53_FLASH_RUNTIME_PROFILE.version
GLM53_LEGACY_RUNTIME_PROFILE_VERSION = "legacy"

PROTOCOL_MAX_CALLS = 3
DOMAIN_MAX_CALLS = 12
CASE_MAX_CALLS = 4
CUMULATIVE_MAX_CALLS = PROTOCOL_MAX_CALLS + DOMAIN_MAX_CALLS
DOMAIN_MAX_TOKENS = 12_000
CASE_MAX_TOKENS = 4_000
# Keep direct/legacy wrapper callers on the historical cap.  Only the
# explicitly registered Flash runtime profile receives the larger budget.
LEGACY_MAX_OUTPUT_TOKENS_PER_REQUEST = 1_024
MAX_OUTPUT_TOKENS_PER_REQUEST = GLM53_FLASH_RUNTIME_PROFILE.max_output_tokens
# The specialised profile gives Flash enough room for its reasoning and final
# answer while the case/domain ceilings below remain unchanged.  This is a
# project-controlled cap, not a claim about the provider's hard maximum.
DEFAULT_OUTPUT_TOKENS = MAX_OUTPUT_TOKENS_PER_REQUEST
SDK_MAX_RETRIES = 0
MAX_REVISIONS = 0

# New profile runs must never default to an immutable pre-profile artifact or
# share its run directory.  Keeping the identity in the path makes an
# accidental replay fail closed before any Provider construction.
G53_7_OUTPUT_PATH = Path(
    "data/evaluation/results/provider_capabilities/"
    "zhipu_glm53_flash_domain_adoption_g53_7_runtime_profile_v1.json"
)
G53_7_RUNS_ROOT = Path("data/runs/evaluation/glm53_flash_domain_g53_7")

PUBLIC_CI_SHA = "0f97b92683e4981842e745a695864deb611bb630"
EXPECTED_PROTOCOL_RESULT_SHA256 = (
    "9b9a584a0ff91b7f865663d1aa9d380c0e70a60d2bea78cca012c136d61355c2"
)
EXPECTED_DATASET_FILE_SHA256 = (
    "bd06083ff6025927c04da2e1e6ff7f07c98a4791bd0438191dce8145e5148933"
)
EXPECTED_DATASET_SHA256 = (
    "09d046e8d852a4aac0ed2d8974cb416ba349b696bf2cc3302f96f957320fd9ae"
)
EXPECTED_PLAN_FILE_SHA256 = (
    "e5daa6ccd05c8c71a98ec5ce7edeedb6069e9f9a84bca00628c1b08a656bf784"
)
EXPECTED_SNAPSHOT_FILE_SHA256 = (
    "53f2b5fc9cd4faf2914c44794ba7ed3944388edab74f878421b26fe122cfc3cf"
)
EXPECTED_SUMMARY_FILE_SHA256 = (
    "804520031606cd0a7875fd2287e948a44e9b0100e38e1c44e5ed2619eaffc147"
)
EXPECTED_REPORT_FILE_SHA256 = (
    "1990d7941ba3a488677e837de1f729d9142c84e8bcf1148a9a96f0d412476bb1"
)
EXPECTED_DATASET_ID = "glm53-flash-recent-form-held-out-v1"
EXPECTED_DATASET_VERSION = "1.0.0"
EXPECTED_SNAPSHOT_ID = "glm53-flash-recent-form-context-v1"
EXPECTED_CASE_IDS = (
    "flash_gate_baseline_01",
    "flash_gate_user_guard_02",
    "flash_gate_knowledge_guard_03",
)

GitShaText = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
Sha256Text = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
NonBlankText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
SafeErrorText = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{0,127}$")]


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class GLM53CaseResource(_FrozenModel):
    """Measured resources for one case, with no monetary estimate."""

    case_id: NonBlankText
    calls_used: int = Field(ge=0, le=CASE_MAX_CALLS)
    max_calls: Literal[CASE_MAX_CALLS] = CASE_MAX_CALLS
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0, le=CASE_MAX_TOKENS)
    max_observed_tokens: Literal[CASE_MAX_TOKENS] = CASE_MAX_TOKENS
    latency_ms: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_totals(self) -> "GLM53CaseResource":
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("case total_tokens must equal input plus output")
        return self


class GLM53ResourceSnapshot(_FrozenModel):
    """Domain-scope resource evidence; price is deliberately unknown."""

    provider_id: Literal[GLM53_PROVIDER_ID] = GLM53_PROVIDER_ID
    model: Literal[GLM53_MODEL] = GLM53_MODEL
    calls_used: int = Field(ge=0, le=DOMAIN_MAX_CALLS)
    max_calls: Literal[DOMAIN_MAX_CALLS] = DOMAIN_MAX_CALLS
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0, le=DOMAIN_MAX_TOKENS)
    max_observed_tokens: Literal[DOMAIN_MAX_TOKENS] = DOMAIN_MAX_TOKENS
    latency_ms: int = Field(ge=0)
    case_resources: tuple[GLM53CaseResource, ...] = ()
    stop_code: ExperimentFailureCode | None = None
    monetary_cost_status: Literal["unknown"] = "unknown"

    @model_validator(mode="after")
    def validate_totals(self) -> "GLM53ResourceSnapshot":
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("domain total_tokens must equal input plus output")
        if len({row.case_id for row in self.case_resources}) != len(
            self.case_resources
        ):
            raise ValueError("case resource identities must be unique")
        if sum(row.input_tokens for row in self.case_resources) != self.input_tokens:
            raise ValueError("case input totals must match domain input total")
        if sum(row.output_tokens for row in self.case_resources) != self.output_tokens:
            raise ValueError("case output totals must match domain output total")
        if sum(row.calls_used for row in self.case_resources) != self.calls_used:
            raise ValueError("case call totals must match domain call total")
        return self


class GLM53ProviderStop(_FrozenModel):
    provider_id: Literal[GLM53_PROVIDER_ID] = GLM53_PROVIDER_ID
    failure_code: ExperimentFailureCode
    provider_error_code: SafeErrorText | None = None


class GLM53ControlSnapshot(_FrozenModel):
    global_stop: ExperimentFailureCode | None = None
    provider_stops: tuple[GLM53ProviderStop, ...] = ()


class GLM53FreshDomainAdmission(_FrozenModel):
    """No-I/O identity proving that a fresh run may be constructed."""

    schema_version: Literal["1.0"] = "1.0"
    experiment_id: Sha256Text
    provider_id: Literal[GLM53_PROVIDER_ID] = GLM53_PROVIDER_ID
    requested_model: Literal[GLM53_MODEL] = GLM53_MODEL
    base_url: Literal[GLM53_BASE_URL] = GLM53_BASE_URL
    thinking_profile_id: Literal[
        GLM53_PROFILE_ID,
        GLM53_LEGACY_PROFILE_ID,
    ] = GLM53_PROFILE_ID
    runtime_profile_id: Literal[
        GLM53_RUNTIME_PROFILE_ID,
        GLM53_LEGACY_RUNTIME_PROFILE_ID,
    ] = GLM53_LEGACY_RUNTIME_PROFILE_ID
    runtime_profile_version: Literal[
        GLM53_RUNTIME_PROFILE_VERSION,
        GLM53_LEGACY_RUNTIME_PROFILE_VERSION,
    ] = GLM53_LEGACY_RUNTIME_PROFILE_VERSION
    code_sha: GitShaText
    public_ci_sha: GitShaText
    public_ci_success_confirmed: Literal[True] = True
    public_ci_scope: NonBlankText
    dataset_id: Literal[EXPECTED_DATASET_ID] = EXPECTED_DATASET_ID
    dataset_version: Literal[EXPECTED_DATASET_VERSION] = EXPECTED_DATASET_VERSION
    dataset_sha256: Sha256Text
    dataset_file_sha256: Sha256Text
    input_plan_file_sha256: Sha256Text
    prompt_context_snapshot_id: Literal[EXPECTED_SNAPSHOT_ID] = EXPECTED_SNAPSHOT_ID
    prompt_context_snapshot_sha256: Sha256Text
    prompt_context_snapshot_file_sha256: Sha256Text
    player_summary_file_sha256: Sha256Text
    deterministic_report_file_sha256: Sha256Text
    execution_plan: DomainCaseExecutionPlan
    case_context_commitments: tuple[DomainCaseContextCommitment, ...]
    protocol_result_sha256: Sha256Text
    protocol_code_sha: GitShaText
    protocol_calls: Literal[PROTOCOL_MAX_CALLS] = PROTOCOL_MAX_CALLS
    protocol_input_tokens: int = Field(ge=0)
    protocol_output_tokens: int = Field(ge=0)
    protocol_total_tokens: int = Field(ge=0)
    sdk_max_retries: Literal[SDK_MAX_RETRIES] = SDK_MAX_RETRIES
    max_revisions: Literal[MAX_REVISIONS] = MAX_REVISIONS
    domain_max_calls: Literal[DOMAIN_MAX_CALLS] = DOMAIN_MAX_CALLS
    case_max_calls: Literal[CASE_MAX_CALLS] = CASE_MAX_CALLS
    domain_max_tokens: Literal[DOMAIN_MAX_TOKENS] = DOMAIN_MAX_TOKENS
    case_max_tokens: Literal[CASE_MAX_TOKENS] = CASE_MAX_TOKENS
    # 1024 is retained solely so immutable pre-profile evidence can still be
    # loaded; new admissions are constructed with the 2048 profile cap.
    max_output_tokens_per_request: Literal[1024, MAX_OUTPUT_TOKENS_PER_REQUEST] = (
        LEGACY_MAX_OUTPUT_TOKENS_PER_REQUEST
    )
    monetary_cost_status: Literal["unknown"] = "unknown"
    external_provider_calls: Literal[0] = 0
    held_out_executed: Literal[False] = False
    provider_construction_authorized: Literal[False] = False
    ready_for_real_call: Literal[True] = True

    @model_validator(mode="after")
    def validate_identity(self) -> "GLM53FreshDomainAdmission":
        if self.runtime_profile_id == GLM53_RUNTIME_PROFILE_ID:
            if self.runtime_profile_version != GLM53_RUNTIME_PROFILE_VERSION:
                raise ValueError(
                    "specialised Flash admissions must use the current profile version"
                )
            if self.max_output_tokens_per_request != MAX_OUTPUT_TOKENS_PER_REQUEST:
                raise ValueError(
                    "specialised Flash admissions must use the profile output cap"
                )
        else:
            if self.runtime_profile_version != GLM53_LEGACY_RUNTIME_PROFILE_VERSION:
                raise ValueError(
                    "legacy Flash admissions must retain the legacy profile marker"
                )
            if self.max_output_tokens_per_request != LEGACY_MAX_OUTPUT_TOKENS_PER_REQUEST:
                raise ValueError(
                    "legacy Flash admissions must retain the historical output cap"
                )
        if self.code_sha != self.public_ci_sha:
            raise ValueError("local code SHA must match the confirmed CI SHA")
        if self.protocol_code_sha != self.public_ci_sha:
            raise ValueError("prior protocol code SHA must match the CI SHA")
        if self.protocol_total_tokens != (
            self.protocol_input_tokens + self.protocol_output_tokens
        ):
            raise ValueError("prior protocol token total is inconsistent")
        if tuple(row.case_id for row in self.case_context_commitments) != (
            self.execution_plan.case_ids
        ):
            raise ValueError("case Context commitments must follow plan order")
        if self.execution_plan.case_ids != EXPECTED_CASE_IDS:
            raise ValueError("GLM-5.3 Flash cases must use the frozen order")
        expected = _admission_identity(self)
        legacy_expected = _admission_identity(
            self,
            include_runtime_profile=False,
        )
        if self.experiment_id == expected:
            return self
        # Preserve the exact identity of pre-profile G53-6/G53-4 JSON.  The
        # compatibility path is intentionally limited to the legacy marker;
        # new admissions include the runtime profile in their digest.
        if (
            self.runtime_profile_id == GLM53_LEGACY_RUNTIME_PROFILE_ID
            and self.experiment_id == legacy_expected
        ):
            return self
        raise ValueError("fresh domain experiment identity is inconsistent")


class GLM53FreshDomainResult(_FrozenModel):
    """Immutable, body-free result of one authorized fresh-domain attempt."""

    schema_version: Literal["1.0"] = "1.0"
    experiment_id: Sha256Text
    run_timestamp_utc: datetime
    admission: GLM53FreshDomainAdmission
    resources: GLM53ResourceSnapshot
    control: GLM53ControlSnapshot
    protocol_calls: Literal[PROTOCOL_MAX_CALLS] = PROTOCOL_MAX_CALLS
    protocol_total_tokens: int = Field(ge=0)
    domain_calls_used: int = Field(ge=0, le=DOMAIN_MAX_CALLS)
    domain_total_tokens: int = Field(ge=0, le=DOMAIN_MAX_TOKENS)
    cumulative_calls_used: int = Field(ge=0, le=CUMULATIVE_MAX_CALLS)
    cumulative_total_tokens: int = Field(ge=0)
    monetary_cost_status: Literal["unknown"] = "unknown"
    cases: tuple[DomainCaseExecutionRecord, ...]
    candidate: DomainCandidate | None = None
    evaluation: DomainEvaluationResult | None = None
    explicit_real_call_confirmed: Literal[True] = True
    held_out_executed: bool
    admitted: bool

    @model_validator(mode="after")
    def validate_composition(self) -> "GLM53FreshDomainResult":
        if self.experiment_id != self.admission.experiment_id:
            raise ValueError("result and admission identities differ")
        if tuple(row.case_id for row in self.cases) != (
            self.admission.execution_plan.case_ids
        ):
            raise ValueError("result cases must follow the frozen plan order")
        if self.resources.calls_used != self.domain_calls_used:
            raise ValueError("resource and domain call counts differ")
        if self.resources.total_tokens != self.domain_total_tokens:
            raise ValueError("resource and domain token counts differ")
        if self.protocol_total_tokens != self.admission.protocol_total_tokens:
            raise ValueError("protocol token identity drifted")
        if self.cumulative_calls_used != self.protocol_calls + self.domain_calls_used:
            raise ValueError("cumulative call count is inconsistent")
        if self.cumulative_total_tokens != (
            self.protocol_total_tokens + self.domain_total_tokens
        ):
            raise ValueError("cumulative token count is inconsistent")
        actually_executed = any(row.status != "skipped" for row in self.cases)
        if self.held_out_executed is not actually_executed:
            raise ValueError("held_out_executed does not match case state")
        all_executed = all(row.status == "executed" for row in self.cases)
        if (self.candidate is None) is not (self.evaluation is None):
            raise ValueError("candidate and evaluation must appear together")
        if all_executed is not (self.candidate is not None):
            raise ValueError("complete case execution requires aggregate evidence")
        if self.candidate is not None:
            if self.candidate.external_provider_calls != self.domain_calls_used:
                raise ValueError("candidate call count is inconsistent")
            if self.evaluation is None:
                raise ValueError("candidate requires aggregate evaluation")
            if self.evaluation.external_provider_calls != self.domain_calls_used:
                raise ValueError("evaluation call count is inconsistent")
        expected_admitted = all(
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
        if self.admitted is not expected_admitted:
            raise ValueError("admitted must match mandatory domain evidence")
        return self


@dataclass(frozen=True)
class GLM53PreparedRun:
    admission: GLM53FreshDomainAdmission
    dataset: DomainEvaluationDataset
    input_plan: LoadedDomainCaseInputPlan
    snapshot: PromptContextSnapshot
    prior_protocol: AdapterProtocolSliceReport


@dataclass
class _MutableCaseResources:
    calls_used: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0


@dataclass
class GLM53BudgetState:
    """Shared hard budget for the one fresh-domain run."""

    calls_used: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    stop_code: ExperimentFailureCode | None = None
    global_stop: ExperimentFailureCode | None = None
    provider_stops: dict[str, tuple[ExperimentFailureCode, str | None]] = field(
        default_factory=dict
    )
    cases: dict[str, _MutableCaseResources] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def register_case(self, case_id: str) -> None:
        if case_id in self.cases:
            raise ValueError("case resource boundary is already registered")
        self.cases[case_id] = _MutableCaseResources()

    def case_snapshot(self, case_id: str) -> GLM53CaseResource:
        row = self.cases[case_id]
        return GLM53CaseResource(
            case_id=case_id,
            calls_used=row.calls_used,
            input_tokens=row.input_tokens,
            output_tokens=row.output_tokens,
            total_tokens=row.input_tokens + row.output_tokens,
            latency_ms=row.latency_ms,
        )

    def snapshot(self) -> GLM53ResourceSnapshot:
        return GLM53ResourceSnapshot(
            calls_used=self.calls_used,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            total_tokens=self.total_tokens,
            latency_ms=self.latency_ms,
            case_resources=tuple(self.case_snapshot(case_id) for case_id in self.cases),
            stop_code=self.stop_code,
        )

    def stop_provider(
        self,
        provider_id: str,
        failure_code: ExperimentFailureCode,
        provider_error_code: str | None = None,
    ) -> None:
        if provider_id != GLM53_PROVIDER_ID:
            raise ValueError("Provider is outside the GLM-5.3 experiment")
        safe = _safe_error_code(provider_id, provider_error_code)
        self.provider_stops.setdefault(provider_id, (failure_code, safe))
        self.stop_code = self.stop_code or failure_code

    def stop_global(self, failure_code: ExperimentFailureCode) -> None:
        self.global_stop = self.global_stop or failure_code
        self.stop_code = self.stop_code or failure_code

    def control_snapshot(self) -> GLM53ControlSnapshot:
        return GLM53ControlSnapshot(
            global_stop=self.global_stop,
            provider_stops=tuple(
                GLM53ProviderStop(
                    provider_id=provider_id,
                    failure_code=failure_code,
                    provider_error_code=provider_error_code,
                )
                for provider_id, (failure_code, provider_error_code) in sorted(
                    self.provider_stops.items()
                )
            ),
        )


class GLM53BudgetedProvider:
    """Provider wrapper that checks every limit before and after I/O."""

    def __init__(
        self,
        *,
        provider: LLMProvider,
        state: GLM53BudgetState,
        case_id: str,
        runtime_profile: ModelRuntimeProfile | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if provider.provider_name != GLM53_PROVIDER_ID:
            raise ValueError("Provider ID does not match GLM-5.3 gate")
        if provider.model_name != GLM53_MODEL:
            raise ValueError("Provider model does not match GLM-5.3 gate")
        if case_id not in state.cases:
            raise ValueError("case must be registered before Provider construction")
        if runtime_profile is not None:
            if not isinstance(runtime_profile, ModelRuntimeProfile):
                raise TypeError("runtime_profile must be a ModelRuntimeProfile")
            if runtime_profile != GLM53_FLASH_RUNTIME_PROFILE:
                raise ValueError(
                    "GLM-5.3 budget wrapper requires the registered Flash profile"
                )
        self._provider = provider
        self._state = state
        self._case_id = case_id
        self._runtime_profile = runtime_profile
        self._clock = clock
        self.provider_name = provider.provider_name
        self.model_name = provider.model_name
        self.capabilities = provider.capabilities

    def chat(self, request: ChatRequest) -> ChatResponse:
        if not isinstance(request, ChatRequest):
            raise TypeError("request must be a ChatRequest")
        prepared = self._reserve(request)
        started = self._clock()
        try:
            response = self._provider.chat(prepared)
        except ProviderError as exc:
            failure = _classify_error(exc)
            self._state.stop_provider(
                self.provider_name,
                failure,
                provider_error_code=exc.code,
            )
            raise
        except Exception:
            wrapped = ProviderResponseError(
                provider=self.provider_name,
                code="unexpected_sdk_error",
            )
            self._state.stop_provider(
                self.provider_name,
                ExperimentFailureCode.PROVIDER_ERROR_UNKNOWN,
                provider_error_code=wrapped.code,
            )
            raise wrapped from None

        latency_ms = max(0, round((self._clock() - started) * 1000))
        if not isinstance(response, ChatResponse):
            self._block(ExperimentFailureCode.PROVIDER_RESPONSE_INVALID)
        if response.provider != GLM53_PROVIDER_ID or response.model != GLM53_MODEL:
            self._block(ExperimentFailureCode.PROVIDER_RESPONSE_INVALID)
        self._settle(response, latency_ms)
        return response

    def _reserve(self, request: ChatRequest) -> ChatRequest:
        if self._state.stop_code is not None:
            self._raise(self._state.stop_code)
        case = self._state.cases[self._case_id]
        if self._state.calls_used >= DOMAIN_MAX_CALLS:
            self._block(ExperimentFailureCode.EXTERNAL_CALL_BUDGET_EXHAUSTED)
        if case.calls_used >= CASE_MAX_CALLS:
            self._block(ExperimentFailureCode.EXTERNAL_CALL_BUDGET_EXHAUSTED)
        remaining_global = DOMAIN_MAX_TOKENS - self._state.total_tokens
        remaining_case = CASE_MAX_TOKENS - case.input_tokens - case.output_tokens
        remaining = min(remaining_global, remaining_case)
        if remaining <= 0:
            self._block(ExperimentFailureCode.TOKEN_BUDGET_EXHAUSTED)
        output_cap = (
            self._runtime_profile.max_output_tokens
            if self._runtime_profile is not None
            else LEGACY_MAX_OUTPUT_TOKENS_PER_REQUEST
        )
        default_output = (
            DEFAULT_OUTPUT_TOKENS
            if self._runtime_profile is not None
            else LEGACY_MAX_OUTPUT_TOKENS_PER_REQUEST
        )
        requested = default_output if request.max_tokens is None else request.max_tokens
        max_tokens = min(requested, output_cap, remaining)
        if max_tokens <= 0:
            self._block(ExperimentFailureCode.TOKEN_BUDGET_EXHAUSTED)
        self._state.calls_used += 1
        case.calls_used += 1
        temperature = request.temperature
        top_p = request.top_p
        timeout_s = request.timeout_s
        metadata = dict(request.metadata)
        if self._runtime_profile is not None:
            # A custom case executor may construct its own ChatRequest.  The
            # budget wrapper is the final trust boundary: it cannot raise the
            # Flash profile's output, sampling, or per-request deadline.
            temperature = self._runtime_profile.temperature
            top_p = self._runtime_profile.top_p
            timeout_s = min(
                request.timeout_s,
                self._runtime_profile.llm_tool_timeout_s,
            )
            metadata.update(
                {
                    "runtime_profile_id": self._runtime_profile.profile_id,
                    "runtime_profile_version": self._runtime_profile.version,
                }
            )
        return request.__class__(
            messages=request.messages,
            tools=request.tools,
            tool_choice=request.tool_choice,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_s=timeout_s,
            response_contract=request.response_contract,
            metadata=metadata,
            top_p=top_p,
        )

    def _settle(self, response: ChatResponse, latency_ms: int) -> None:
        case = self._state.cases[self._case_id]
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        self._state.input_tokens += input_tokens
        self._state.output_tokens += output_tokens
        self._state.latency_ms += latency_ms
        case.input_tokens += input_tokens
        case.output_tokens += output_tokens
        case.latency_ms += latency_ms
        output_cap = (
            self._runtime_profile.max_output_tokens
            if self._runtime_profile is not None
            else LEGACY_MAX_OUTPUT_TOKENS_PER_REQUEST
        )
        if output_tokens > output_cap:
            self._block(ExperimentFailureCode.TOKEN_BUDGET_EXHAUSTED)
        if self._state.total_tokens > DOMAIN_MAX_TOKENS:
            self._block(ExperimentFailureCode.TOKEN_BUDGET_EXHAUSTED)
        if case.input_tokens + case.output_tokens > CASE_MAX_TOKENS:
            self._block(ExperimentFailureCode.TOKEN_BUDGET_EXHAUSTED)

    def _block(self, code: ExperimentFailureCode) -> None:
        self._state.stop_provider(self.provider_name, code)
        self._raise(code)

    def _raise(self, code: ExperimentFailureCode) -> None:
        raise ProviderResponseError(provider=self.provider_name, code=code.value)


def build_glm53_preflight(
    *,
    project_root: str | Path,
    dataset_path: str | Path,
    input_plan_path: str | Path,
    snapshot_path: str | Path,
    protocol_result_path: str | Path,
    code_sha: str,
    public_ci_sha: str = PUBLIC_CI_SHA,
    confirm_public_ci_success: bool = False,
) -> GLM53PreparedRun:
    """Validate all fresh identities without reading `.env` or making a client."""

    root = Path(project_root).resolve()
    dataset_file = _inside(root, dataset_path, "dataset")
    plan_file = _inside(root, input_plan_path, "input plan")
    snapshot_file = _inside(root, snapshot_path, "Prompt/Context snapshot")
    protocol_file = _inside(root, protocol_result_path, "protocol result")
    if not _is_git_sha(code_sha) or not _is_git_sha(public_ci_sha):
        raise ValueError("code and public CI identities must be git SHAs")
    if code_sha != public_ci_sha or not confirm_public_ci_success:
        raise ValueError("current code/public CI identity is not confirmed")
    if _file_sha256(protocol_file) != EXPECTED_PROTOCOL_RESULT_SHA256:
        raise ValueError("prior GLM-5.3 protocol bytes do not match frozen evidence")
    dataset = load_domain_dataset(dataset_file)
    _validate_dataset(dataset, dataset_file)
    loaded_plan = load_domain_case_input_plan(
        plan_file,
        project_root=root,
        dataset=dataset,
    )
    if loaded_plan.execution_plan.plan_sha256 != EXPECTED_PLAN_FILE_SHA256:
        raise ValueError("GLM-5.3 input plan bytes do not match frozen evidence")
    snapshot = load_prompt_context_snapshot(snapshot_file)
    if _file_sha256(snapshot_file) != EXPECTED_SNAPSHOT_FILE_SHA256:
        raise ValueError("GLM-5.3 snapshot bytes do not match frozen evidence")
    summary = json.loads(loaded_plan.player_summary_path.read_text(encoding="utf-8"))
    report = loaded_plan.deterministic_report_path.read_text(encoding="utf-8")
    if _file_sha256(loaded_plan.player_summary_path) != EXPECTED_SUMMARY_FILE_SHA256:
        raise ValueError("GLM-5.3 summary bytes do not match frozen evidence")
    if _file_sha256(loaded_plan.deterministic_report_path) != EXPECTED_REPORT_FILE_SHA256:
        raise ValueError("GLM-5.3 report bytes do not match frozen evidence")
    rebuilt = build_prompt_context_snapshot_for_cases(
        skills_root=root / "skills",
        player_summary=summary,
        deterministic_report=report,
        cases=loaded_plan.artifact.cases,
        snapshot_id=snapshot.snapshot_id,
        evaluation_contract_version="1.1.0",
    )
    if rebuilt != snapshot:
        raise ValueError("frozen Prompt/Context snapshot cannot be rebuilt")
    expected_commitments = tuple(
        DomainCaseContextCommitment(
            case_id=row.case_id,
            context_sha256=case_context_sha256(row),
        )
        for row in snapshot.case_contexts
    )
    if loaded_plan.artifact.case_context_commitments != expected_commitments:
        raise ValueError("input plan Context commitments do not match snapshot")
    if loaded_plan.artifact.prompt_context_snapshot_sha256 != snapshot.snapshot_sha256:
        raise ValueError("input plan snapshot identity does not match snapshot")
    protocol = AdapterProtocolSliceReport.model_validate_json(protocol_file.read_bytes())
    if not protocol.admitted or protocol.calls_used != PROTOCOL_MAX_CALLS:
        raise ValueError("prior protocol is not an admitted three-call slice")
    if (protocol.provider_id, protocol.requested_model) != (
        GLM53_PROVIDER_ID,
        GLM53_MODEL,
    ):
        raise ValueError("prior protocol Provider identity does not match")
    if protocol.code_sha != public_ci_sha:
        raise ValueError("prior protocol code SHA does not match public CI SHA")
    protocol_input = sum(row.input_tokens for row in protocol.cases)
    protocol_output = sum(row.output_tokens for row in protocol.cases)
    admission_data = {
        "experiment_id": "0" * 64,
        "code_sha": code_sha,
        "public_ci_sha": public_ci_sha,
        "public_ci_scope": (
            "g53-2-adapter-runtime-baseline; domain-assets-local; "
            "flash-runtime-budget-v1"
        ),
        "runtime_profile_id": GLM53_RUNTIME_PROFILE_ID,
        "runtime_profile_version": GLM53_RUNTIME_PROFILE_VERSION,
        "max_output_tokens_per_request": MAX_OUTPUT_TOKENS_PER_REQUEST,
        "dataset_sha256": _dataset_sha(dataset),
        "dataset_file_sha256": _file_sha256(dataset_file),
        "input_plan_file_sha256": _file_sha256(plan_file),
        "prompt_context_snapshot_sha256": snapshot.snapshot_sha256,
        "prompt_context_snapshot_file_sha256": _file_sha256(snapshot_file),
        "player_summary_file_sha256": _file_sha256(loaded_plan.player_summary_path),
        "deterministic_report_file_sha256": _file_sha256(
            loaded_plan.deterministic_report_path
        ),
        "execution_plan": loaded_plan.execution_plan,
        "case_context_commitments": expected_commitments,
        "protocol_result_sha256": _file_sha256(protocol_file),
        "protocol_code_sha": protocol.code_sha,
        "protocol_input_tokens": protocol_input,
        "protocol_output_tokens": protocol_output,
        "protocol_total_tokens": protocol_input + protocol_output,
    }
    # Build the digest from the already validated control-plane fields before
    # constructing the strict model (whose validator quite correctly rejects a
    # placeholder identity).
    draft = GLM53FreshDomainAdmission.model_construct(**admission_data)
    admission_data["experiment_id"] = _admission_identity(draft)
    admission = GLM53FreshDomainAdmission(**admission_data)
    return GLM53PreparedRun(
        admission=admission,
        dataset=dataset,
        input_plan=loaded_plan,
        snapshot=snapshot,
        prior_protocol=protocol,
    )


def run_glm53_domain_gate(
    *,
    admission: GLM53FreshDomainAdmission,
    dataset: DomainEvaluationDataset,
    provider: LLMProvider,
    case_executor: Any,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    clock: Callable[[], float] = time.monotonic,
) -> GLM53FreshDomainResult:
    """Run all three cases sequentially, stopping at the first unsafe failure."""

    if not isinstance(admission, GLM53FreshDomainAdmission):
        raise TypeError("admission must be a GLM53FreshDomainAdmission")
    if not isinstance(dataset, DomainEvaluationDataset):
        raise TypeError("dataset must be a DomainEvaluationDataset")
    if provider.provider_name != GLM53_PROVIDER_ID or provider.model_name != GLM53_MODEL:
        raise ValueError("runtime Provider does not match GLM-5.3 admission")
    if admission.runtime_profile_id != GLM53_RUNTIME_PROFILE_ID:
        raise ValueError(
            "runtime gate requires the specialised GLM-5.3 Flash profile"
        )
    if not all(
        (
            provider.capabilities.text_chat,
            provider.capabilities.tool_calling,
            provider.capabilities.structured_output,
        )
    ):
        raise ValueError("runtime Provider lacks admitted capabilities")
    if _dataset_sha(dataset) != admission.dataset_sha256:
        raise ValueError("runtime Dataset does not match admission")
    if tuple(row.case_id for row in dataset.cases) != admission.execution_plan.case_ids:
        raise ValueError("runtime Dataset case order does not match admission")
    if getattr(case_executor, "execution_plan", None) != admission.execution_plan:
        raise ValueError("case executor does not match admission execution plan")
    if getattr(case_executor, "runtime_profile", None) != GLM53_FLASH_RUNTIME_PROFILE:
        raise ValueError("case executor does not use the specialised runtime profile")

    state = GLM53BudgetState()
    records: list[DomainCaseExecutionRecord] = []
    observations: list[DomainCandidateCase] = []
    for case in dataset.cases:
        if state.stop_code is not None:
            records.append(
                DomainCaseExecutionRecord(
                    case_id=case.case_id,
                    status="skipped",
                    failure_code=state.stop_code,
                )
            )
            continue
        state.register_case(case.case_id)
        before = state.case_snapshot(case.case_id)
        controlled = GLM53BudgetedProvider(
            provider=provider,
            state=state,
            case_id=case.case_id,
            runtime_profile=GLM53_FLASH_RUNTIME_PROFILE,
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
            failure = _classify_error(exc)
            state.stop_provider(
                GLM53_PROVIDER_ID,
                failure,
                provider_error_code=exc.code,
            )
            records.append(
                DomainCaseExecutionRecord(
                    case_id=case.case_id,
                    status="failed",
                    failure_code=failure,
                )
            )
            continue
        except Exception:
            failure = ExperimentFailureCode.DOMAIN_CASE_OBSERVATION_INVALID
            state.stop_provider(GLM53_PROVIDER_ID, failure)
            records.append(
                DomainCaseExecutionRecord(
                    case_id=case.case_id,
                    status="failed",
                    failure_code=failure,
                )
            )
            continue

        after = state.case_snapshot(case.case_id)
        observation = _candidate_case_from_semantics(semantic, before=before, after=after)
        case_result = _evaluate_one_case(dataset, case_id=case.case_id, observation=observation)
        failure = _case_failure(state, semantic, case_result)
        if failure is not None:
            if failure is ExperimentFailureCode.UNSAFE_PUBLICATION:
                state.stop_global(failure)
            else:
                state.stop_provider(
                    GLM53_PROVIDER_ID,
                    failure,
                    provider_error_code=semantic.safe_provider_error_code,
                )
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
            candidate_id=f"zhipu-glm53-flash-domain-{admission.experiment_id[:16]}",
            candidate_kind="real_provider_recorded",
            dataset_id=dataset.dataset_id,
            dataset_version=dataset.dataset_version,
            contract_snapshot=dataset.contract_snapshot,
            external_provider_calls=state.calls_used,
            case_count=len(observations),
            cases=tuple(observations),
        )
        evaluation = evaluate_domain_candidate(dataset, candidate)
    resources = state.snapshot()
    control = state.control_snapshot()
    all_clean = all(
        row.status == "executed" and row.failure_code is None for row in records
    )
    admitted_result = all(
        (
            all_clean,
            evaluation is not None,
            evaluation is not None and evaluation.task_outcome_accuracy == 1.0,
            evaluation is not None
            and evaluation.failure_classification_accuracy == 1.0,
            evaluation is not None and evaluation.unsafe_publication_rate == 0.0,
            resources.stop_code is None,
            control.global_stop is None,
            not control.provider_stops,
        )
    )
    return GLM53FreshDomainResult(
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
        cases=tuple(records),
        candidate=candidate,
        evaluation=evaluation,
        held_out_executed=any(row.status != "skipped" for row in records),
        admitted=admitted_result,
    )


def create_glm53_provider(
    settings: ZhipuSettings,
    *,
    client_factory: Callable[..., Any] = OpenAI,
) -> ZhipuProvider:
    """Construct the candidate Provider only after output reservation."""

    if settings.model != GLM53_MODEL or settings.base_url != GLM53_BASE_URL:
        raise ValueError("runtime settings do not match the frozen GLM-5.3 Flash gate")
    if not GLM53_FLASH_RUNTIME_PROFILE.matches(
        GLM53_PROVIDER_ID,
        settings.model,
    ):
        raise ValueError("specialised runtime profile does not match the gate")
    client = client_factory(
        api_key=settings.api_key,
        base_url=settings.base_url,
        timeout=GLM53_FLASH_RUNTIME_PROFILE.transport_timeout_s,
        max_retries=SDK_MAX_RETRIES,
    )
    return ZhipuProvider(
        client=client,
        model=settings.model,
        profile=settings.thinking_profile,
    )


def _candidate_case_from_semantics(
    semantic: DomainCaseSemanticObservation,
    *,
    before: GLM53CaseResource,
    after: GLM53CaseResource,
) -> DomainCandidateCase:
    return DomainCandidateCase(
        case_id=semantic.case_id,
        provider_calls=after.calls_used - before.calls_used,
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
        latency_ms=after.latency_ms - before.latency_ms,
        input_tokens=after.input_tokens - before.input_tokens,
        output_tokens=after.output_tokens - before.output_tokens,
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
    one_candidate = DomainCandidate(
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
    return evaluate_domain_candidate(one_dataset, one_candidate).cases[0]


def _case_failure(
    state: GLM53BudgetState,
    semantic: DomainCaseSemanticObservation,
    result: DomainCaseResult,
) -> ExperimentFailureCode | None:
    if state.stop_code is not None:
        return state.stop_code
    if semantic.safe_provider_error_code:
        return _classify_error_code(semantic.safe_provider_error_code)
    if result.unsafe_publication:
        return ExperimentFailureCode.UNSAFE_PUBLICATION
    if not result.task_outcome_match or not result.failure_classification_match:
        return ExperimentFailureCode.DOMAIN_CASE_OUTCOME_MISMATCH
    return None


def _classify_error(error: ProviderError) -> ExperimentFailureCode:
    try:
        return ExperimentFailureCode(error.code)
    except ValueError:
        return classify_provider_error(error)


def _classify_error_code(code: str) -> ExperimentFailureCode:
    try:
        return ExperimentFailureCode(code)
    except ValueError:
        return ExperimentFailureCode.PROVIDER_RESPONSE_INVALID


def _safe_error_code(provider_id: str, code: str | None) -> str | None:
    if code is None:
        return None
    # Provider error strings are already constrained at the adapter boundary;
    # retain only lower-case code-shaped values in the public control record.
    if provider_id == GLM53_PROVIDER_ID and isinstance(code, str) and code.isascii() and code.islower() and all(
        char.isalnum() or char == "_" for char in code
    ):
        return code[:128]
    return None


def _validate_dataset(dataset: DomainEvaluationDataset, path: Path) -> None:
    validate_domain_dataset_usage(
        dataset,
        DomainDatasetRole.HELD_OUT,
        confirm_rules_frozen=True,
    )
    if (
        dataset.dataset_id != EXPECTED_DATASET_ID
        or dataset.dataset_version != EXPECTED_DATASET_VERSION
        or tuple(row.case_id for row in dataset.cases) != EXPECTED_CASE_IDS
        or not dataset.calibration_excluded
        or _file_sha256(path) != EXPECTED_DATASET_FILE_SHA256
        or _dataset_sha(dataset) != EXPECTED_DATASET_SHA256
    ):
        raise ValueError("GLM-5.3 Flash held-out Dataset identity has drifted")
    for case in dataset.cases:
        requirements = case.requirements
        if (
            requirements.minimum_normalized_responses != 3
            or requirements.expected_agent_status != "completed"
            or requirements.expected_agent_stop_reason != "final_response"
            or requirements.required_tool_names != ("knowledge.search",)
            or requirements.minimum_successful_tool_executions != 1
            or requirements.minimum_evidence_sources != 1
            or not requirements.require_fact_check
            or not requirements.require_citation_check
            or not requirements.require_injection_check
            or not requirements.require_validated_evaluation
            or requirements.minimum_evaluation_score != 85
            or requirements.allowed_terminal_statuses != ("published",)
            or requirements.maximum_provider_calls != CASE_MAX_CALLS
            or requirements.maximum_latency_ms != 30_000
            or requirements.maximum_total_tokens != CASE_MAX_TOKENS
            or requirements.maximum_estimated_cost is not None
        ):
            raise ValueError("GLM-5.3 Flash case resource/quality contract drifted")


def _admission_identity(
    admission: GLM53FreshDomainAdmission,
    *,
    include_runtime_profile: bool = True,
) -> str:
    excluded = {"experiment_id"}
    if not include_runtime_profile:
        excluded.add("runtime_profile_id")
        excluded.add("runtime_profile_version")
    payload = admission.model_dump(mode="json", exclude=excluded)
    return _digest_json(payload)


def _dataset_sha(dataset: DomainEvaluationDataset) -> str:
    return _digest_json(dataset.model_dump(mode="json"))


def _digest_json(value: Any) -> str:
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


def _file_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _is_git_sha(value: str) -> bool:
    return isinstance(value, str) and len(value) == 40 and all(
        char in "0123456789abcdef" for char in value
    )


def _inside(root: Path, value: str | Path, label: str) -> Path:
    path = Path(value) if Path(value).is_absolute() else root / value
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"{label} must remain inside the project root")
    return resolved


def _read_head_sha(root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return completed.stdout.strip()


def _require_clean_worktree(root: Path) -> None:
    """Keep a real result from masquerading as the public CI SHA."""

    completed = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if completed.stdout.strip():
        raise RuntimeError(
            "real GLM-5.3 Flash domain calls require a clean exact-SHA worktree"
        )


@dataclass(frozen=True)
class GLM53DomainGateOptions:
    confirm_real_call: bool
    public_ci_sha: str = PUBLIC_CI_SHA
    confirm_public_ci_success: bool = False
    preflight_only: bool = False
    max_calls: int = DOMAIN_MAX_CALLS
    dataset: Path = Path(
        "data/evaluation/glm53_flash_domain_adoption_v1_cases.json"
    )
    input_plan: Path = Path(
        "data/evaluation/glm53_flash_domain_adoption_v1_input_plan.json"
    )
    snapshot: Path = Path(
        "data/evaluation/contracts/glm53_flash_recent_form_prompt_context_v1.json"
    )
    protocol_result: Path = Path(
        "data/evaluation/results/provider_capabilities/"
        "zhipu_glm53_flash_adapter_protocol_retry2.json"
    )
    output: Path = G53_7_OUTPUT_PATH
    runs_root: Path = G53_7_RUNS_ROOT


def run_cli(
    options: GLM53DomainGateOptions,
    *,
    repository_root: Path | None = None,
    environment_loader: Callable[[Path], Mapping[str, str]] | None = None,
    provider_factory: Callable[[ZhipuSettings], LLMProvider] = create_glm53_provider,
    code_sha_reader: Callable[[Path], str] = _read_head_sha,
) -> GLM53FreshDomainAdmission | GLM53FreshDomainResult:
    """Run no-I/O admission first, then reserve output before loading a Key."""

    if options.max_calls != DOMAIN_MAX_CALLS:
        raise ValueError("GLM-5.3 Flash domain gate requires exactly 12 calls")
    if not options.preflight_only and not options.confirm_real_call:
        raise RuntimeError("Real GLM-5.3 Flash calls require explicit confirmation")
    root = (repository_root or Path(__file__).resolve().parents[2]).resolve()
    output = _inside(root, options.output, "output")
    allowed_output = (root / "data/evaluation/results/provider_capabilities").resolve()
    if not output.is_relative_to(allowed_output) or output.suffix.lower() != ".json":
        raise ValueError("output must be a JSON file in provider capability results")
    if output.exists():
        raise FileExistsError("GLM-5.3 domain evidence is immutable")
    if not options.preflight_only:
        _require_clean_worktree(root)
    code_sha = code_sha_reader(root)
    prepared = build_glm53_preflight(
        project_root=root,
        dataset_path=_inside(root, options.dataset, "dataset"),
        input_plan_path=_inside(root, options.input_plan, "input plan"),
        snapshot_path=_inside(root, options.snapshot, "snapshot"),
        protocol_result_path=_inside(root, options.protocol_result, "protocol result"),
        code_sha=code_sha,
        public_ci_sha=options.public_ci_sha,
        confirm_public_ci_success=options.confirm_public_ci_success,
    )
    if options.preflight_only:
        return prepared.admission
    reservation = ImmutableDomainExperimentOutput.reserve(
        output,
        experiment_id=prepared.admission.experiment_id,
    )
    try:
        load_environment = environment_loader or _load_environment
        settings = load_zhipu_settings(load_environment(root))
        provider = provider_factory(settings)
        runs_parent = _inside(root, options.runs_root, "runs root").parent
        runs_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="glm53-flash-domain-",
            dir=str(runs_parent),
        ) as temporary:
            executor = ProductionDomainCaseExecutor(
                project_root=root,
                input_plan=prepared.input_plan,
                runs_root=Path(temporary),
                runtime_profile=GLM53_FLASH_RUNTIME_PROFILE,
            )
            result = run_glm53_domain_gate(
                admission=prepared.admission,
                dataset=prepared.dataset,
                provider=provider,
                case_executor=executor,
            )
        reservation.commit_payload(result)
        return result
    except Exception:
        reservation.abandon()
        raise


def _load_environment(root: Path) -> Mapping[str, str]:
    load_dotenv(root / ".env")
    return os.environ


def _parse_args(argv: Sequence[str] | None = None) -> GLM53DomainGateOptions:
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the bounded GLM-5.3 Flash fresh-domain adoption gate."
    )
    parser.add_argument("--confirm-real-call", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--public-ci-sha", default=PUBLIC_CI_SHA)
    parser.add_argument("--confirm-public-ci-success", action="store_true")
    parser.add_argument("--max-calls", type=int, default=DOMAIN_MAX_CALLS)
    parser.add_argument("--dataset", type=Path, default=GLM53DomainGateOptions.dataset)
    parser.add_argument("--input-plan", type=Path, default=GLM53DomainGateOptions.input_plan)
    parser.add_argument("--snapshot", type=Path, default=GLM53DomainGateOptions.snapshot)
    parser.add_argument(
        "--protocol-result",
        type=Path,
        default=GLM53DomainGateOptions.protocol_result,
    )
    parser.add_argument("--output", type=Path, default=GLM53DomainGateOptions.output)
    parser.add_argument("--runs-root", type=Path, default=GLM53DomainGateOptions.runs_root)
    values = parser.parse_args(argv)
    return GLM53DomainGateOptions(
        confirm_real_call=values.confirm_real_call,
        public_ci_sha=values.public_ci_sha,
        confirm_public_ci_success=(
            values.confirm_public_ci_success or values.preflight_only
        ),
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
    if isinstance(result, GLM53FreshDomainAdmission):
        print(
            f"provider={result.provider_id} model={result.requested_model} "
            "preflight=true external_provider_calls=0 held_out_executed=false"
        )
    else:
        print(
            f"provider={result.admission.provider_id} "
            f"model={result.admission.requested_model} "
            f"domain_calls={result.domain_calls_used}/{DOMAIN_MAX_CALLS} "
            f"cumulative_calls={result.cumulative_calls_used}/{CUMULATIVE_MAX_CALLS} "
            f"admitted={str(result.admitted).lower()}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CASE_MAX_CALLS",
    "CASE_MAX_TOKENS",
    "CUMULATIVE_MAX_CALLS",
    "DOMAIN_MAX_CALLS",
    "DOMAIN_MAX_TOKENS",
    "EXPECTED_PROTOCOL_RESULT_SHA256",
    "GLM53_BASE_URL",
    "GLM53_LEGACY_PROFILE_ID",
    "GLM53_MODEL",
    "GLM53_PROFILE_ID",
    "GLM53_RUNTIME_PROFILE_ID",
    "GLM53_LEGACY_RUNTIME_PROFILE_ID",
    "GLM53_RUNTIME_PROFILE_VERSION",
    "GLM53_LEGACY_RUNTIME_PROFILE_VERSION",
    "G53_7_OUTPUT_PATH",
    "G53_7_RUNS_ROOT",
    "GLM53BudgetState",
    "GLM53BudgetedProvider",
    "GLM53CaseResource",
    "GLM53ControlSnapshot",
    "GLM53DomainGateOptions",
    "GLM53FreshDomainAdmission",
    "GLM53FreshDomainResult",
    "GLM53PreparedRun",
    "GLM53ResourceSnapshot",
    "build_glm53_preflight",
    "create_glm53_provider",
    "main",
    "run_cli",
    "run_glm53_domain_gate",
]
