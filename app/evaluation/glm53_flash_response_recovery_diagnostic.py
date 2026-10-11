"""One bounded, body-free diagnostic for the Flash recovery candidate.

This module is an evaluation seam, not a Provider retry implementation.  It
uses one frozen held-out context with the knowledge tools removed so the
candidate policy can be evaluated without tool side effects.  At most two
independent full requests are sent: one ``primary`` request and, only when the
sanitized candidate allowlist matches, one ``fresh_recovery`` request.

No prompt, response text, reasoning text, tool arguments/results, credentials,
or raw request identifiers are retained in the report.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path
from types import SimpleNamespace
from typing import Annotated, Any, Literal

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.agent.context import ContextBuilderV1, ContextBundle
from app.evaluation.domain_e2e import (
    DomainDatasetRole,
    load_domain_dataset,
    validate_domain_dataset_usage,
)
from app.evaluation.provider_domain_plan import load_domain_case_input_plan
from app.evaluation.provider_domain_production import ProductionDomainCaseExecutor
from app.providers.config import load_zhipu_settings
from app.providers.errors import ProviderError
from app.providers.models import ChatRequest, ChatResponse, ToolChoiceMode
from app.providers.response_completion_policy import (
    GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1,
    ResponseBoundarySnapshot,
    ResponseCompletionDecision,
    ResponseDisposition,
    ResponseRequestContext,
)
from app.providers.response_recovery_contract import (
    GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1,
    RecoveryAttemptKind,
    ResponseAttemptOutcome,
    ResponseRecoveryLedger,
    build_response_recovery_plan,
)
from app.providers.zhipu import ZhipuProvider


PROVIDER_ID = "zhipu"
MODEL = "glm-5.3-flash"
BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"
CASE_ID = "flash_gate_baseline_01"
SCHEMA_VERSION = "1.0"
DEFAULT_OUTPUT = Path(
    "data/evaluation/results/provider_capabilities/"
    "zhipu_glm53_flash_response_recovery_diagnostic_v1.json"
)

SafeSha = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
GitSha = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
SafeCode = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_.-]{0,95}$")]
SafeModel = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")]

FinishReason = Literal[
    "stop",
    "tool_calls",
    "length",
    "content_filter",
    "insufficient_system_resource",
    "missing",
    "unknown",
]
FieldState = Literal[
    "not_observed",
    "missing",
    "null",
    "empty",
    "non_empty",
    "non_string",
]
UsageState = Literal["valid", "missing", "invalid"]
SdkErrorClass = Literal[
    "authentication",
    "permission",
    "rate_limit",
    "timeout",
    "connection",
    "http_status",
    "sdk_error",
]

_MISSING = object()
_SAFE_FINISH_REASONS = frozenset(
    {"stop", "tool_calls", "length", "content_filter", "insufficient_system_resource"}
)
_MODEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_FORBIDDEN_KEYS = frozenset(
    {
        "prompt",
        "messages",
        "content",
        "reasoning",
        "reasoning_content",
        "tool_arguments",
        "tool_results",
        "request_id",
        "api_key",
    }
)


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RecoveryRequestSummary(_FrozenModel):
    """Request shape; message bodies are represented only by a digest."""

    ordinal: int = Field(ge=1, le=2)
    attempt_kind: Literal["primary", "fresh_recovery"]
    phase: Literal["agent_initial"] = "agent_initial"
    message_count: int = Field(ge=1, le=128)
    message_roles: tuple[str, ...]
    message_shape_sha256: SafeSha
    tool_definition_count: Literal[0] = 0
    tool_choice: Literal["none"] = "none"
    has_response_contract: Literal[False] = False
    requested_max_tokens: int = Field(ge=1, le=8192)
    timeout_s: float = Field(gt=0, le=300)
    temperature: float = Field(ge=0, le=2)
    top_p: float = Field(ge=0, le=1)


class DecisionSummary(_FrozenModel):
    disposition: Literal[
        "complete_text",
        "tool_calls_ready",
        "fail_closed",
        "candidate_eligible",
    ]
    reason_code: SafeCode
    error_code: SafeCode | None = None
    candidate_eligible: bool
    continuation_allowed: bool
    max_additional_calls: Literal[0, 1]


class ContextSummary(_FrozenModel):
    phase: Literal["agent_initial"] = "agent_initial"
    has_response_contract: Literal[False] = False
    has_tools: Literal[False] = False
    has_tool_side_effects: Literal[False] = False
    remaining_timeout_s: float = Field(ge=0, le=300)
    remaining_token_budget: int = Field(ge=0)


class RecoveryAttemptObservation(_FrozenModel):
    ordinal: int = Field(ge=1, le=2)
    attempt_kind: Literal["primary", "fresh_recovery"]
    request: RecoveryRequestSummary
    context: ContextSummary
    response_received: bool
    sdk_latency_ms: int = Field(ge=0)
    elapsed_ms: int = Field(ge=0)
    finish_reason: FinishReason | None = None
    content_state: FieldState = "not_observed"
    reasoning_content_state: FieldState = "not_observed"
    tool_calls_state: FieldState = "not_observed"
    tool_call_count: int = Field(ge=0, le=32)
    resolved_model: SafeModel | None = None
    usage_state: UsageState = "missing"
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cached_input_tokens: int | None = Field(default=None, ge=0)
    request_id_sha256: SafeSha | None = None
    sdk_error_class: SdkErrorClass | None = None
    adapter_error_code: SafeCode | None = None
    adapter_error_stage: SafeCode | None = None
    normalized: bool
    settled: bool
    decision: DecisionSummary


class CandidateRecoveryDiagnosticReport(_FrozenModel):
    """Immutable, body-free evidence for one candidate diagnostic."""

    schema_version: Literal["1.0"] = SCHEMA_VERSION
    experiment_id: SafeSha
    run_timestamp_utc: datetime
    provider_id: Literal["zhipu"] = PROVIDER_ID
    requested_model: Literal["glm-5.3-flash"] = MODEL
    base_url: Literal[BASE_URL] = BASE_URL
    implementation_sha: GitSha
    diagnostic_code_sha: GitSha
    runtime_profile_id: Literal["glm-5.3-flash-runtime-v2-candidate"]
    runtime_profile_version: Literal["2.0.0"]
    policy_id: Literal["glm-5.3-flash-fresh-recovery-candidate-v1"]
    policy_version: Literal["1.0.0"]
    activation_state: Literal["candidate"] = "candidate"
    execution_allowed: Literal[False] = False
    case_id: Literal[CASE_ID] = CASE_ID
    input_plan_sha256: SafeSha
    prompt_context_snapshot_sha256: SafeSha
    request_variant: Literal["frozen_context_without_tools"]
    reasoning_replay_mode: Literal["fresh_full_request_same_messages"]
    explicit_real_call_confirmed: Literal[True] = True
    max_attempts: Literal[2] = 2
    max_additional_calls: Literal[1] = 1
    provider_calls_attempted: int = Field(ge=1, le=2)
    candidate_eligible_observed: bool
    recovery_attempted: bool
    recovery_skip_reason: SafeCode | None = None
    terminal_state: Literal[
        "awaiting_primary",
        "awaiting_recovery",
        "complete_text",
        "tool_calls_ready",
        "fail_closed",
    ]
    input_tokens_observed: int = Field(ge=0)
    output_tokens_observed: int = Field(ge=0)
    elapsed_ms_observed: int = Field(ge=0)
    unknown_usage_attempts: int = Field(ge=0, le=2)
    budget_exceeded: bool
    cost_status: Literal["unknown"] = "unknown"
    trace: dict[str, Any]
    observations: tuple[RecoveryAttemptObservation, ...]

    @model_validator(mode="after")
    def validate_body_free_and_counts(self) -> "CandidateRecoveryDiagnosticReport":
        if len(self.observations) != self.provider_calls_attempted:
            raise ValueError("observation count must match provider calls")
        if self.recovery_attempted != (self.provider_calls_attempted == 2):
            raise ValueError("recovery flag must match call count")
        if self.recovery_attempted and self.recovery_skip_reason is not None:
            raise ValueError("recovery skip reason is invalid after recovery")
        _assert_body_free(self.trace)
        _assert_body_free(self.model_dump(mode="python", exclude={"trace"}))
        return self

    @classmethod
    def build(
        cls,
        *,
        implementation_sha: str,
        diagnostic_code_sha: str,
        input_plan_sha256: str,
        prompt_context_snapshot_sha256: str,
        observations: tuple[RecoveryAttemptObservation, ...],
        ledger: ResponseRecoveryLedger,
        candidate_eligible: bool,
        recovery_attempted: bool,
        recovery_skip_reason: str | None,
        now: datetime,
    ) -> "CandidateRecoveryDiagnosticReport":
        trace = ledger.trace().as_dict()
        body = {
            "schema_version": SCHEMA_VERSION,
            "run_timestamp_utc": now.isoformat(),
            "implementation_sha": implementation_sha,
            "diagnostic_code_sha": diagnostic_code_sha,
            "input_plan_sha256": input_plan_sha256,
            "prompt_context_snapshot_sha256": prompt_context_snapshot_sha256,
            "observations": [row.model_dump(mode="json") for row in observations],
            "trace": trace,
        }
        experiment_id = hashlib.sha256(
            json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        ).hexdigest()
        state = ledger.snapshot()
        return cls(
            experiment_id=experiment_id,
            run_timestamp_utc=now,
            implementation_sha=implementation_sha,
            diagnostic_code_sha=diagnostic_code_sha,
            runtime_profile_id=GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1.profile_id,
            runtime_profile_version=GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1.version,
            policy_id=GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1.policy_id,
            policy_version=GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1.version,
            input_plan_sha256=input_plan_sha256,
            prompt_context_snapshot_sha256=prompt_context_snapshot_sha256,
            request_variant="frozen_context_without_tools",
            reasoning_replay_mode="fresh_full_request_same_messages",
            provider_calls_attempted=state.calls_settled,
            candidate_eligible_observed=candidate_eligible,
            recovery_attempted=recovery_attempted,
            recovery_skip_reason=_safe_code(recovery_skip_reason),
            terminal_state=state.terminal_state,
            input_tokens_observed=state.input_tokens_observed,
            output_tokens_observed=state.output_tokens_observed,
            elapsed_ms_observed=state.elapsed_ms_observed,
            unknown_usage_attempts=state.unknown_usage_attempts,
            budget_exceeded=state.budget_exceeded,
            trace=trace,
            observations=observations,
        )


@dataclass
class _MutableAttempt:
    request: RecoveryRequestSummary
    response_received: bool = False
    sdk_latency_ms: int = 0
    elapsed_ms: int = 0
    finish_reason: FinishReason | None = None
    content_state: FieldState = "not_observed"
    reasoning_content_state: FieldState = "not_observed"
    tool_calls_state: FieldState = "not_observed"
    tool_call_count: int = 0
    resolved_model: str | None = None
    usage_state: UsageState = "missing"
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_input_tokens: int | None = None
    request_id_sha256: str | None = None
    sdk_error_class: SdkErrorClass | None = None
    adapter_error_code: str | None = None
    adapter_error_stage: str | None = None
    normalized: bool = False
    settled: bool = False
    context: ContextSummary | None = None
    decision: DecisionSummary | None = None

    def freeze(self) -> RecoveryAttemptObservation:
        if self.context is None or self.decision is None:
            raise RuntimeError("attempt decision is not bound")
        return RecoveryAttemptObservation(
            ordinal=self.request.ordinal,
            attempt_kind=self.request.attempt_kind,
            request=self.request,
            context=self.context,
            response_received=self.response_received,
            sdk_latency_ms=self.sdk_latency_ms,
            elapsed_ms=self.elapsed_ms,
            finish_reason=self.finish_reason,
            content_state=self.content_state,
            reasoning_content_state=self.reasoning_content_state,
            tool_calls_state=self.tool_calls_state,
            tool_call_count=self.tool_call_count,
            resolved_model=self.resolved_model,
            usage_state=self.usage_state,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            cached_input_tokens=self.cached_input_tokens,
            request_id_sha256=self.request_id_sha256,
            sdk_error_class=self.sdk_error_class,
            adapter_error_code=_safe_code(self.adapter_error_code),
            adapter_error_stage=_safe_code(self.adapter_error_stage),
            normalized=self.normalized,
            settled=self.settled,
            decision=self.decision,
        )


class _Recorder:
    """Observe one SDK boundary while retaining only sanitized fields."""

    def __init__(self) -> None:
        self._active: _MutableAttempt | None = None
        self._rows: list[_MutableAttempt] = []

    @property
    def active(self) -> _MutableAttempt | None:
        return self._active

    def start(self, request: ChatRequest, kind: RecoveryAttemptKind) -> None:
        if self._active is not None:
            raise RuntimeError("diagnostic attempt is already active")
        ordinal = len(self._rows) + 1
        self._active = _MutableAttempt(
            request=_request_summary(request, ordinal=ordinal, kind=kind)
        )
        self._rows.append(self._active)

    def note_sdk_response(self, raw: Any, elapsed_ms: int) -> None:
        target = self._require_active()
        target.response_received = True
        target.sdk_latency_ms = max(0, elapsed_ms)
        _capture_raw_response(target, raw)

    def note_sdk_exception(self, error: Exception, elapsed_ms: int) -> None:
        target = self._require_active()
        target.sdk_latency_ms = max(0, elapsed_ms)
        target.sdk_error_class = _sdk_error_class(error)

    def note_adapter_error(self, error: ProviderError) -> None:
        target = self._require_active()
        target.adapter_error_code = _safe_code(error.code)
        target.adapter_error_stage = _adapter_stage(error.code)

    def note_unknown_error(self, error: Exception) -> None:
        target = self._require_active()
        target.adapter_error_code = "unexpected_sdk_error"
        target.adapter_error_stage = "transport"
        target.sdk_error_class = target.sdk_error_class or _sdk_error_class(error)

    def note_normalized(self) -> None:
        self._require_active().normalized = True

    def finish(self, elapsed_ms: int) -> _MutableAttempt:
        target = self._require_active()
        target.elapsed_ms = max(0, elapsed_ms)
        self._active = None
        return target

    def mark_settled(self) -> None:
        if not self._rows:
            raise RuntimeError("no diagnostic attempt to settle")
        self._rows[-1].settled = True

    def observations(self) -> tuple[RecoveryAttemptObservation, ...]:
        return tuple(row.freeze() for row in self._rows)

    def _require_active(self) -> _MutableAttempt:
        if self._active is None:
            raise RuntimeError("diagnostic attempt is not active")
        return self._active


class _RecordingCompletions:
    def __init__(self, delegate: Any, recorder: _Recorder) -> None:
        self._delegate = delegate
        self._recorder = recorder

    def create(self, **kwargs: Any) -> Any:
        started = time.monotonic()
        try:
            raw = self._delegate.create(**kwargs)
        except Exception as error:
            self._recorder.note_sdk_exception(
                error,
                round((time.monotonic() - started) * 1000),
            )
            raise
        self._recorder.note_sdk_response(
            raw,
            round((time.monotonic() - started) * 1000),
        )
        return raw


class _RecordingClient:
    def __init__(self, client: Any, recorder: _Recorder) -> None:
        self.chat = SimpleNamespace(
            completions=_RecordingCompletions(client.chat.completions, recorder)
        )


def run_response_recovery_diagnostic(
    *,
    repository_root: str | Path,
    implementation_sha: str,
    diagnostic_code_sha: str | None = None,
    output: str | Path = DEFAULT_OUTPUT,
    env_file: str | Path | None = None,
    confirm_real_call: bool = False,
    request_timeout_s: float | None = None,
    environment_loader: Callable[[Path | None], Mapping[str, str]] | None = None,
    client_factory: Callable[..., Any] = OpenAI,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> CandidateRecoveryDiagnosticReport:
    """Run one primary and, if eligible, one fresh recovery request."""

    if confirm_real_call is not True:
        raise RuntimeError("candidate recovery diagnostics require explicit confirmation")
    root = Path(repository_root).resolve()
    _validate_sha(implementation_sha, "implementation_sha")
    diagnostic_code_sha = diagnostic_code_sha or _read_head_sha(root)
    _validate_sha(diagnostic_code_sha, "diagnostic_code_sha")
    output_path = _inside_results(root, output)
    if output_path.exists():
        raise FileExistsError("diagnostic evidence is immutable")

    dataset_path = root / "data/evaluation/glm53_flash_domain_adoption_v1_cases.json"
    plan_path = root / "data/evaluation/glm53_flash_domain_adoption_v1_input_plan.json"
    dataset = load_domain_dataset(dataset_path)
    validate_domain_dataset_usage(
        dataset,
        DomainDatasetRole.HELD_OUT,
        confirm_rules_frozen=True,
    )
    loaded_plan = load_domain_case_input_plan(plan_path, project_root=root, dataset=dataset)
    case = loaded_plan.artifact.case(CASE_ID)
    context_bundle = _build_frozen_context(root, loaded_plan, case)

    load_environment = environment_loader or _load_environment
    settings = load_zhipu_settings(load_environment(Path(env_file) if env_file else None))
    if settings.model != MODEL or settings.base_url.rstrip("/") != BASE_URL.rstrip("/"):
        raise ValueError("diagnostic settings must target GLM-5.3 Flash")
    profile = GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1
    effective_request_timeout_s = _bounded_request_timeout_s(
        request_timeout_s,
        profile=profile,
    )
    client = client_factory(
        api_key=settings.api_key,
        base_url=settings.base_url,
        timeout=profile.transport_timeout_s,
        max_retries=0,
    )
    recorder = _Recorder()
    provider = ZhipuProvider(
        client=_RecordingClient(client, recorder),
        model=settings.model,
        profile=settings.thinking_profile,
    )

    primary_request = _candidate_request(
        context_bundle,
        kind=RecoveryAttemptKind.PRIMARY,
        timeout_s=effective_request_timeout_s,
    )
    primary_row, primary_error = _call_once(provider, recorder, primary_request, RecoveryAttemptKind.PRIMARY)
    primary_context = _response_context(profile, primary_row)
    primary_snapshot = _snapshot(primary_row)
    primary_decision = GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1.decide(
        primary_snapshot,
        primary_context,
    )
    _bind_decision(primary_row, primary_context, primary_decision)

    plan = build_response_recovery_plan(
        policy=GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1,
        snapshot=primary_snapshot,
        context=primary_context,
        runtime_profile=profile,
    )
    ledger = ResponseRecoveryLedger(plan)
    _settle_row(ledger, primary_row, primary_snapshot, primary_context, primary_decision, recorder)

    recovery_attempted = False
    recovery_skip_reason: str | None = None
    if not primary_decision.candidate_eligible:
        recovery_skip_reason = "primary_not_candidate_eligible"
    elif plan.has_recovery_slot:
        try:
            reservation = ledger.reserve_next()
        except Exception as error:
            recovery_skip_reason = _safe_exception_code(error)
        else:
            recovery_attempted = True
            remaining_s = max(
                0.0,
                min(
                    profile.agent_timeout_s,
                    (profile.max_total_elapsed_ms - primary_row.elapsed_ms) / 1000.0,
                ),
            )
            recovery_request = _candidate_request(
                context_bundle,
                kind=RecoveryAttemptKind.FRESH_RECOVERY,
                timeout_s=max(
                    0.001,
                    min(effective_request_timeout_s, remaining_s),
                ),
            )
            recovery_row, _recovery_error = _call_once(
                provider,
                recorder,
                recovery_request,
                RecoveryAttemptKind.FRESH_RECOVERY,
            )
            recovery_context = _response_context(profile, recovery_row)
            recovery_snapshot = _snapshot(recovery_row)
            recovery_decision = GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1.decide(
                recovery_snapshot,
                recovery_context,
            )
            _bind_decision(recovery_row, recovery_context, recovery_decision)
            recovery_outcome = _outcome(
                recovery_row,
                recovery_snapshot,
                recovery_context,
                recovery_decision,
            )
            ledger.settle(reservation, recovery_outcome)
            recorder.mark_settled()

    report = CandidateRecoveryDiagnosticReport.build(
        implementation_sha=implementation_sha,
        diagnostic_code_sha=diagnostic_code_sha,
        input_plan_sha256=loaded_plan.execution_plan.plan_sha256,
        prompt_context_snapshot_sha256=loaded_plan.artifact.prompt_context_snapshot_sha256
        or _zero_sha(),
        observations=recorder.observations(),
        ledger=ledger,
        candidate_eligible=primary_decision.candidate_eligible,
        recovery_attempted=recovery_attempted,
        recovery_skip_reason=recovery_skip_reason,
        now=now(),
    )
    _write_immutable(output_path, report.model_dump_json(indent=2).encode("utf-8"))
    del primary_error
    return report


def _build_frozen_context(root: Path, loaded_plan: Any, case: Any) -> ContextBundle:
    """Build exact held-out messages, then intentionally omit tools for this probe."""

    executor = ProductionDomainCaseExecutor(
        project_root=root,
        input_plan=loaded_plan,
        runs_root=root / "data/runs/evaluation/glm53_flash_response_recovery_diagnostic",
        runtime_profile=None,
    )
    execution = executor._build_execution(case)  # noqa: SLF001 - diagnostic-only seam
    return ContextBuilderV1().build(execution)


def _candidate_request(
    context_bundle: ContextBundle,
    *,
    kind: RecoveryAttemptKind,
    timeout_s: float,
) -> ChatRequest:
    return ChatRequest(
        messages=context_bundle.messages,
        tools=(),
        tool_choice=ToolChoiceMode.NONE,
        temperature=GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1.temperature,
        top_p=GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1.top_p,
        max_tokens=GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1.max_output_tokens,
        timeout_s=timeout_s,
        metadata={
            "response_recovery_diagnostic": "candidate-v1",
            "recovery_attempt_kind": kind.value,
            "agent_loop_iteration": 1,
        },
    )


def _bounded_request_timeout_s(
    value: float | None,
    *,
    profile: Any,
) -> float:
    if value is None:
        return float(profile.agent_timeout_s)
    minimum = GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1.minimum_recovery_timeout_s
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(value)
        or value < minimum
        or value > profile.agent_timeout_s
    ):
        raise ValueError(
            "request_timeout_s must be finite and within the candidate request window"
        )
    return float(value)


def _call_once(
    provider: ZhipuProvider,
    recorder: _Recorder,
    request: ChatRequest,
    kind: RecoveryAttemptKind,
) -> tuple[_MutableAttempt, Exception | None]:
    recorder.start(request, kind)
    started = time.monotonic()
    error: Exception | None = None
    try:
        provider.chat(request)
        recorder.note_normalized()
    except ProviderError as caught:
        error = caught
        recorder.note_adapter_error(caught)
    except Exception as caught:  # never persist the exception text
        error = caught
        recorder.note_unknown_error(caught)
    row = recorder.finish(round((time.monotonic() - started) * 1000))
    return row, error


def _settle_row(
    ledger: ResponseRecoveryLedger,
    row: _MutableAttempt,
    snapshot: ResponseBoundarySnapshot,
    context: ResponseRequestContext,
    decision: ResponseCompletionDecision,
    recorder: _Recorder,
) -> None:
    reservation = ledger.reserve_next()
    ledger.settle(reservation, _outcome(row, snapshot, context, decision))
    recorder.mark_settled()


def _outcome(
    row: _MutableAttempt,
    snapshot: ResponseBoundarySnapshot,
    context: ResponseRequestContext,
    decision: ResponseCompletionDecision,
) -> ResponseAttemptOutcome:
    return ResponseAttemptOutcome(
        snapshot=snapshot,
        context=context,
        decision=decision,
        input_tokens=row.input_tokens,
        output_tokens=row.output_tokens,
        elapsed_ms=row.elapsed_ms,
    )


def _bind_decision(
    row: _MutableAttempt,
    context: ResponseRequestContext,
    decision: ResponseCompletionDecision,
) -> None:
    row.context = ContextSummary(
        remaining_timeout_s=context.remaining_timeout_s,
        remaining_token_budget=context.remaining_token_budget,
    )
    row.decision = DecisionSummary(
        disposition=decision.disposition.value,
        reason_code=decision.reason_code,
        error_code=decision.error_code,
        candidate_eligible=decision.candidate_eligible,
        continuation_allowed=decision.continuation_allowed,
        max_additional_calls=decision.max_additional_calls,
    )


def _snapshot(row: _MutableAttempt) -> ResponseBoundarySnapshot:
    return ResponseBoundarySnapshot(
        finish_reason=(None if row.finish_reason in {None, "missing"} else row.finish_reason),
        content_state=row.content_state,
        reasoning_content_state=row.reasoning_content_state,
        tool_call_count=row.tool_call_count,
        usage_state=row.usage_state,
    )


def _response_context(profile: Any, row: _MutableAttempt) -> ResponseRequestContext:
    used_output = row.output_tokens or 0
    remaining_output = max(0, profile.max_total_output_tokens - used_output)
    remaining_time = max(0.0, (profile.max_total_elapsed_ms - row.elapsed_ms) / 1000.0)
    return ResponseRequestContext(
        phase="agent_initial",
        has_response_contract=False,
        has_tools=False,
        has_tool_side_effects=False,
        remaining_timeout_s=min(profile.agent_timeout_s, remaining_time),
        remaining_token_budget=remaining_output,
    )


def _request_summary(
    request: ChatRequest,
    *,
    ordinal: int,
    kind: RecoveryAttemptKind,
) -> RecoveryRequestSummary:
    shape = [
        {
            "role": message.role.value,
            "has_content": message.content is not None,
            "content_length": len(message.content or ""),
            "has_reasoning": message.reasoning_content is not None,
            "tool_call_count": len(message.tool_calls),
        }
        for message in request.messages
    ]
    digest = hashlib.sha256(
        json.dumps(shape, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return RecoveryRequestSummary(
        ordinal=ordinal,
        attempt_kind=kind.value,
        message_count=len(request.messages),
        message_roles=tuple(message.role.value for message in request.messages),
        message_shape_sha256=digest,
        requested_max_tokens=request.max_tokens or 0,
        timeout_s=request.timeout_s,
        temperature=request.temperature,
        top_p=request.top_p or 0.0,
    )


def _capture_raw_response(target: _MutableAttempt, raw: Any) -> None:
    choices = getattr(raw, "choices", _MISSING)
    if not isinstance(choices, (list, tuple)) or not choices:
        target.finish_reason = "missing"
        target.content_state = "missing"
        target.reasoning_content_state = "missing"
        target.tool_calls_state = "missing"
        _capture_usage(target, getattr(raw, "usage", _MISSING))
        return
    choice = choices[0]
    message = getattr(choice, "message", _MISSING)
    if message is _MISSING or message is None:
        target.content_state = "missing"
        target.reasoning_content_state = "missing"
        target.tool_calls_state = "missing"
    else:
        target.content_state = _field_state(getattr(message, "content", _MISSING))
        target.reasoning_content_state = _field_state(
            getattr(message, "reasoning_content", _MISSING)
        )
        raw_tools = getattr(message, "tool_calls", _MISSING)
        target.tool_calls_state = _field_state(raw_tools)
        if isinstance(raw_tools, (list, tuple)):
            target.tool_call_count = min(len(raw_tools), 32)
    target.finish_reason = _finish_reason(getattr(choice, "finish_reason", _MISSING))
    model = getattr(raw, "model", None)
    if isinstance(model, str) and _MODEL_PATTERN.fullmatch(model.strip()):
        target.resolved_model = model.strip()
    request_id = getattr(raw, "id", None)
    if isinstance(request_id, str) and request_id.strip():
        target.request_id_sha256 = hashlib.sha256(request_id.encode("utf-8")).hexdigest()
    _capture_usage(target, getattr(raw, "usage", _MISSING))


def _capture_usage(target: _MutableAttempt, raw_usage: Any) -> None:
    if raw_usage is _MISSING or raw_usage is None:
        target.usage_state = "missing"
        return
    input_tokens = getattr(raw_usage, "prompt_tokens", _MISSING)
    output_tokens = getattr(raw_usage, "completion_tokens", _MISSING)
    if not _nonnegative_int(input_tokens) or not _nonnegative_int(output_tokens):
        target.usage_state = "invalid"
        return
    details = getattr(raw_usage, "prompt_tokens_details", None)
    cached = details.get("cached_tokens", 0) if isinstance(details, Mapping) else getattr(details, "cached_tokens", 0)
    cached = 0 if cached is None else cached
    if not _nonnegative_int(cached) or cached > input_tokens:
        target.usage_state = "invalid"
        return
    target.usage_state = "valid"
    target.input_tokens = input_tokens
    target.output_tokens = output_tokens
    target.cached_input_tokens = cached


def _field_state(value: Any) -> FieldState:
    if value is _MISSING:
        return "missing"
    if value is None:
        return "null"
    if not isinstance(value, str):
        return "non_string"
    return "non_empty" if value.strip() else "empty"


def _finish_reason(value: Any) -> FinishReason:
    if value is _MISSING or value is None:
        return "missing"
    if value in _SAFE_FINISH_REASONS:
        return value
    return "unknown"


def _sdk_error_class(error: Exception) -> SdkErrorClass:
    name = type(error).__name__.lower()
    if "authentication" in name:
        return "authentication"
    if "permission" in name:
        return "permission"
    if "ratelimit" in name or "rate_limit" in name:
        return "rate_limit"
    if "timeout" in name:
        return "timeout"
    if "connection" in name:
        return "connection"
    if "status" in name or "http" in name:
        return "http_status"
    return "sdk_error"


def _adapter_stage(code: str | None) -> str:
    if code in {"authentication_failed", "connection_failed", "service_unavailable", "timeout", "unexpected_sdk_error", "request_rejected"}:
        return "transport"
    if code in {"incomplete_chat_response", "invalid_finish_reason"}:
        return "finish_reason"
    if code == "unexpected_reasoning_content":
        return "reasoning"
    if code in {"invalid_tool_call_request", "invalid_tool_call_response"}:
        return "tool_calls"
    if code == "provider_usage_unavailable":
        return "usage"
    if code == "invalid_chat_response":
        return "response_shape"
    return "unknown"


def _safe_code(value: Any) -> str | None:
    if isinstance(value, str) and re.fullmatch(r"[a-z][a-z0-9_.-]{0,95}", value.strip().lower()):
        return value.strip().lower()
    return None


def _safe_exception_code(error: Exception) -> str:
    name = type(error).__name__.lower()
    if "budget" in name:
        return "budget_exhausted"
    if "eligible" in name:
        return "not_eligible"
    return "recovery_reservation_failed"


def _nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _assert_body_free(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).lower() in _FORBIDDEN_KEYS:
                raise ValueError("diagnostic payload contains a forbidden body field")
            _assert_body_free(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _assert_body_free(item)


def _load_environment(path: Path | None) -> Mapping[str, str]:
    if path is not None:
        load_dotenv(path)
    return os.environ


def _validate_sha(value: str, name: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise ValueError(f"{name} must be a full lowercase git SHA")


def _read_head_sha(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    ).stdout.strip()


def _inside_results(root: Path, value: str | Path) -> Path:
    path = (Path(value) if Path(value).is_absolute() else root / value).resolve()
    allowed = (root / "data/evaluation/results/provider_capabilities").resolve()
    if not path.is_relative_to(allowed) or path.suffix.lower() != ".json":
        raise ValueError("output must remain in provider capability results")
    return path


def _write_immutable(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(content)


def _zero_sha() -> str:
    return "0" * 64


__all__ = [
    "CandidateRecoveryDiagnosticReport",
    "DEFAULT_OUTPUT",
    "run_response_recovery_diagnostic",
]


