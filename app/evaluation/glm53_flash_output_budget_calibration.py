"""Bounded, body-free output-budget calibration for GLM-5.3-Flash.

This evaluation-only diagnostic holds the frozen context and sampling mode
constant while comparing two output caps and two legal reasoning efforts in
three synchronous probes. It never changes the provider-neutral runtime or
candidate registration.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, Literal

import openai
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.providers.models import ChatMessage, MessageRole
from app.providers.config import load_zhipu_settings
from app.providers.zhipu_profiles import (
    ZHIPU_GLM53_FLASH_MODEL,
)
from app.evaluation.glm53_flash_capability_matrix import (
    MatrixSourceIdentity,
    collect_source_identity,
)
from app.evaluation.glm53_flash_transport_generation_split_diagnostic import (
    _assert_body_free,
    _classify_error,
    _elapsed_ms,
    _field_state,
    _finish_reason,
    _inside_results,
    _load_environment,
    _load_frozen_context,
    _request_digest,
    _safe_model,
    _usage_state,
    _validate_context,
    _validate_sha,
    FrozenContextSnapshot,
)


PROVIDER_ID = "zhipu"
MODEL = ZHIPU_GLM53_FLASH_MODEL
BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"
SCHEMA_VERSION = "1.0"
EXPERIMENT_NAME = "g53-9-output-budget-calibration-v1"
DEFAULT_OUTPUT = Path(
    "data/evaluation/results/provider_capabilities/"
    "zhipu_glm53_flash_output_budget_calibration_rq189_v1.json"
)
LOW_MAX_TOKENS = 2048
HIGH_MAX_TOKENS = 8192
REQUEST_TIMEOUT_S = 45.0
CLIENT_TIMEOUT_S = 60.0
MAX_REAL_CALLS = 3
MAX_OBSERVED_TOKENS = 32_000
PARENT_EXPERIMENT_ID = (
    "41901515decc6d8768abd56ee3fd49ac1d1a4402f3cc1cef497720995fa80c8e"
)
PARENT_RESULT_SHA256 = (
    "60073a5f0d0d0324d0fe4deb588d4a49becc607ebfe6b1d008bf04d60a2faf51"
)

CalibrationVariant = Literal[
    "frozen_low_2048_nonstream",
    "frozen_low_8192_nonstream",
    "frozen_max_8192_nonstream",
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
FinishReason = Literal[
    "stop",
    "tool_calls",
    "length",
    "content_filter",
    "insufficient_system_resource",
    "missing",
    "unknown",
]
SdkErrorClass = Literal[
    "authentication",
    "permission",
    "rate_limit",
    "timeout",
    "connection",
    "http_status",
    "sdk_error",
]
ProbeStatus = Literal["observed", "failed", "skipped"]

SafeSha = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
GitSha = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
SafeCode = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_.-]{0,95}$")]
SafeModel = Annotated[
    str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
]
_MISSING = object()
_STOP_CODES = frozenset({"authentication_failed", "permission_denied", "rate_limited"})


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CalibrationRequestSummary(_FrozenModel):
    ordinal: int = Field(ge=1, le=MAX_REAL_CALLS)
    variant: CalibrationVariant
    message_count: int = Field(ge=1, le=128)
    message_roles: tuple[str, ...]
    message_shape_sha256: SafeSha
    max_tokens: Literal[LOW_MAX_TOKENS, HIGH_MAX_TOKENS]
    timeout_s: float = Field(gt=0, le=REQUEST_TIMEOUT_S)
    stream: Literal[False] = False
    temperature: float = Field(ge=0, le=2)
    top_p: float = Field(ge=0, le=1)
    thinking_type: Literal["enabled"] = "enabled"
    reasoning_effort: Literal["low", "max"] = "low"


class CalibrationObservation(_FrozenModel):
    ordinal: int = Field(ge=1, le=MAX_REAL_CALLS)
    variant: CalibrationVariant
    status: ProbeStatus
    request: CalibrationRequestSummary
    external_calls: Literal[0, 1]
    skip_reason: SafeCode | None = None
    response_received: bool = False
    generation_observed: bool = False
    visible_content_observed: bool = False
    create_latency_ms: int = Field(ge=0)
    sdk_latency_ms: int = Field(ge=0)
    elapsed_ms: int = Field(ge=0)
    finish_reason: FinishReason | None = None
    content_state: FieldState = "not_observed"
    reasoning_state: FieldState = "not_observed"
    usage_state: UsageState = "missing"
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cached_input_tokens: int | None = Field(default=None, ge=0)
    resolved_model: SafeModel | None = None
    request_id_sha256: SafeSha | None = None
    sdk_error_class: SdkErrorClass | None = None
    error_code: SafeCode | None = None
    error_stage: SafeCode | None = None

    @model_validator(mode="after")
    def validate_observation(self) -> "CalibrationObservation":
        if self.external_calls == 0 and self.status != "skipped":
            raise ValueError("zero-call observations must be skipped")
        if self.status == "skipped":
            if self.skip_reason is None or self.external_calls != 0:
                raise ValueError("skipped observations need a reason and zero calls")
            if self.response_received or self.generation_observed:
                raise ValueError("skipped observations cannot claim execution")
        else:
            if self.external_calls != 1 or self.skip_reason is not None:
                raise ValueError("executed observations need exactly one call")
        if self.visible_content_observed != (self.content_state == "non_empty"):
            raise ValueError("visible content flag must match content state")
        if self.status == "observed" and not self.response_received:
            raise ValueError("observed observations need a response")
        if self.status == "failed" and self.error_code is None:
            raise ValueError("failed observations need an error code")
        if self.status != "failed" and self.error_code is not None:
            raise ValueError("only failed observations may carry an error code")
        if self.usage_state == "valid":
            if self.input_tokens is None or self.output_tokens is None:
                raise ValueError("valid usage needs input/output counts")
            if self.cached_input_tokens is None:
                raise ValueError("valid usage needs cache count")
            if self.cached_input_tokens > self.input_tokens:
                raise ValueError("cached input cannot exceed input")
        elif any(
            value is not None
            for value in (self.input_tokens, self.output_tokens, self.cached_input_tokens)
        ):
            raise ValueError("unavailable usage cannot carry token counts")
        return self


class CalibrationResources(_FrozenModel):
    calls_used: int = Field(ge=0, le=MAX_REAL_CALLS)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cached_input_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0, le=MAX_OBSERVED_TOKENS)
    latency_ms: int = Field(ge=0)
    within_token_budget: bool

    @model_validator(mode="after")
    def validate_resources(self) -> "CalibrationResources":
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("resource total mismatch")
        if self.cached_input_tokens > self.input_tokens:
            raise ValueError("cached input cannot exceed input")
        if self.within_token_budget != (self.total_tokens <= MAX_OBSERVED_TOKENS):
            raise ValueError("token budget status mismatch")
        return self


class CalibrationBudget(_FrozenModel):
    max_real_calls: Literal[MAX_REAL_CALLS] = MAX_REAL_CALLS
    max_observed_tokens: Literal[MAX_OBSERVED_TOKENS] = MAX_OBSERVED_TOKENS
    max_output_tokens_per_request: Literal[HIGH_MAX_TOKENS] = HIGH_MAX_TOKENS
    sdk_max_retries: Literal[0] = 0


class CalibrationVerdicts(_FrozenModel):
    transport_reachable: bool
    visible_content_observed: bool
    low_2048_visible_content: bool
    low_8192_visible_content: bool
    max_8192_visible_content: bool
    interpretation_code: SafeCode
    candidate_registered: Literal[False] = False
    production_admitted: Literal[False] = False


class OutputBudgetCalibrationReport(_FrozenModel):
    schema_version: Literal[SCHEMA_VERSION] = SCHEMA_VERSION
    experiment_id: SafeSha
    experiment_name: Literal[EXPERIMENT_NAME] = EXPERIMENT_NAME
    evidence_class: Literal["dirty_worktree_real_api_observation"] = (
        "dirty_worktree_real_api_observation"
    )
    provider_id: Literal[PROVIDER_ID] = PROVIDER_ID
    requested_model: Literal[MODEL] = MODEL
    base_url: Literal[BASE_URL] = BASE_URL
    implementation_sha: GitSha
    diagnostic_code_sha: GitSha
    parent_experiment_id: Literal[PARENT_EXPERIMENT_ID] = PARENT_EXPERIMENT_ID
    parent_result_sha256: Literal[PARENT_RESULT_SHA256] = PARENT_RESULT_SHA256
    input_plan_sha256: SafeSha
    prompt_context_snapshot_sha256: SafeSha
    observation_scope: Literal["vendor_raw_transport_only"] = "vendor_raw_transport_only"
    explicit_real_call_confirmed: Literal[True] = True
    source_identity: MatrixSourceIdentity
    source_identity_after: MatrixSourceIdentity
    source_identity_stable: bool
    budget: CalibrationBudget
    resources: CalibrationResources
    calls_attempted: int = Field(ge=0, le=MAX_REAL_CALLS)
    cost_status: Literal["unknown"] = "unknown"
    run_timestamp_utc: datetime
    observations: tuple[CalibrationObservation, ...]
    unsupported_boundaries: tuple[str, ...]
    verdicts: CalibrationVerdicts

    @model_validator(mode="after")
    def validate_report(self) -> "OutputBudgetCalibrationReport":
        expected = (
            "frozen_low_2048_nonstream",
            "frozen_low_8192_nonstream",
            "frozen_max_8192_nonstream",
        )
        if tuple(row.variant for row in self.observations) != expected:
            raise ValueError("calibration variants must use canonical order")
        if self.calls_attempted != sum(row.external_calls for row in self.observations):
            raise ValueError("call count mismatch")
        if self.resources.calls_used != self.calls_attempted:
            raise ValueError("resource call count mismatch")
        if self.resources.input_tokens != sum(row.input_tokens or 0 for row in self.observations):
            raise ValueError("resource input mismatch")
        if self.resources.output_tokens != sum(row.output_tokens or 0 for row in self.observations):
            raise ValueError("resource output mismatch")
        if self.resources.cached_input_tokens != sum(row.cached_input_tokens or 0 for row in self.observations):
            raise ValueError("resource cache mismatch")
        if self.resources.latency_ms != sum(row.elapsed_ms for row in self.observations):
            raise ValueError("resource latency mismatch")
        if self.verdicts.candidate_registered or self.verdicts.production_admitted:
            raise ValueError("calibration cannot admit or register")
        return self


def run_output_budget_calibration(
    *,
    repository_root: str | Path,
    implementation_sha: str,
    diagnostic_code_sha: str | None = None,
    output: str | Path = DEFAULT_OUTPUT,
    env_file: str | Path | None = None,
    confirm_real_call: bool = False,
    environment_loader: Callable[[Path | None], Mapping[str, str]] | None = None,
    client_factory: Callable[..., Any] = OpenAI,
    context_loader: Callable[[Path], FrozenContextSnapshot] | None = None,
    source_identity_loader: Callable[[Path], MatrixSourceIdentity] | None = None,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    probe_limit: int = MAX_REAL_CALLS,
    probe_ordinal: int | None = None,
) -> OutputBudgetCalibrationReport:
    if confirm_real_call is not True:
        raise RuntimeError("output-budget calibration requires explicit confirmation")
    root = Path(repository_root).resolve()
    if isinstance(probe_limit, bool) or not isinstance(probe_limit, int):
        raise ValueError("probe_limit must be an integer between 1 and 3")
    if not 1 <= probe_limit <= MAX_REAL_CALLS:
        raise ValueError("probe_limit must be an integer between 1 and 3")
    if probe_ordinal is not None:
        if isinstance(probe_ordinal, bool) or not isinstance(probe_ordinal, int):
            raise ValueError("probe_ordinal must be an integer between 1 and 3")
        if not 1 <= probe_ordinal <= MAX_REAL_CALLS:
            raise ValueError("probe_ordinal must be an integer between 1 and 3")
        if probe_limit != MAX_REAL_CALLS:
            raise ValueError("probe_ordinal cannot be combined with probe_limit")
    _validate_sha(implementation_sha, "implementation_sha")
    diagnostic_code_sha = diagnostic_code_sha or _read_head_sha(root)
    _validate_sha(diagnostic_code_sha, "diagnostic_code_sha")
    output_path = _inside_results(root, output)
    if output_path.exists():
        raise FileExistsError("calibration evidence is immutable")
    context = (context_loader or _load_frozen_context)(root)
    _validate_context(context)
    load_environment = environment_loader or _load_environment
    settings = load_zhipu_settings(load_environment(Path(env_file) if env_file else None))
    if settings.model != MODEL or settings.base_url.rstrip("/") != BASE_URL.rstrip("/"):
        raise ValueError("calibration settings must target GLM-5.3 Flash")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    source_loader = source_identity_loader or collect_source_identity
    source_identity = source_loader(root)
    client = client_factory(
        api_key=settings.api_key,
        base_url=settings.base_url,
        timeout=CLIENT_TIMEOUT_S,
        max_retries=0,
    )
    observations: list[CalibrationObservation] = []
    stop_code: str | None = None
    for ordinal, (variant, max_tokens, reasoning_effort) in enumerate(
        _probe_specs(context), start=1
    ):
        request = _request_summary(
            ordinal=ordinal,
            variant=variant,
            messages=context.messages,
            max_tokens=max_tokens,
            reasoning_effort=reasoning_effort,
        )
        if probe_ordinal is not None and ordinal != probe_ordinal:
            observations.append(_skipped_observation(request, "probe_selection_excluded"))
            continue
        if ordinal > probe_limit:
            observations.append(_skipped_observation(request, "probe_limit_exhausted"))
            continue
        if stop_code is not None:
            observations.append(_skipped_observation(request, stop_code))
            continue
        observation = _run_nonstream(
            client,
            request=request,
            messages=context.messages,
            max_tokens=max_tokens,
            reasoning_effort=reasoning_effort,
        )
        observations.append(observation)
        if observation.error_code in _STOP_CODES:
            stop_code = observation.error_code
    source_identity_after = source_loader(root)
    resources = _resources(observations)
    timestamp = now()
    report = OutputBudgetCalibrationReport(
        experiment_id=_experiment_id(source_identity, timestamp),
        implementation_sha=implementation_sha,
        diagnostic_code_sha=diagnostic_code_sha,
        input_plan_sha256=context.input_plan_sha256,
        prompt_context_snapshot_sha256=context.prompt_context_snapshot_sha256,
        source_identity=source_identity,
        source_identity_after=source_identity_after,
        source_identity_stable=source_identity == source_identity_after,
        budget=CalibrationBudget(),
        resources=resources,
        calls_attempted=sum(row.external_calls for row in observations),
        run_timestamp_utc=timestamp,
        observations=tuple(observations),
        unsupported_boundaries=(
            "RQ-188 stream probe stopped after first chunk; this batch is synchronous only",
            "long-window completion and full provider-neutral stream contract remain unobserved",
            "no tool is supplied or executed; no response body or reasoning text is retained",
            "candidate remains unregistered; production security/deployment/compliance gates remain open",
        ),
        verdicts=_verdicts(observations),
    )
    _assert_body_free(report.model_dump())
    _write_immutable_report(output_path, report.model_dump_json(indent=2) + "\n")
    return report


def _probe_specs(context: FrozenContextSnapshot):
    yield ("frozen_low_2048_nonstream", LOW_MAX_TOKENS, "low")
    yield ("frozen_low_8192_nonstream", HIGH_MAX_TOKENS, "low")
    yield ("frozen_max_8192_nonstream", HIGH_MAX_TOKENS, "max")


def _request_summary(
    *,
    ordinal: int,
    variant: CalibrationVariant,
    messages: tuple[ChatMessage, ...],
    max_tokens: int,
    reasoning_effort: Literal["low", "max"],
) -> CalibrationRequestSummary:
    shape = [
        {
            "role": message.role.value,
            "has_content": message.content is not None,
            "content_length": len(message.content or ""),
            "has_reasoning": message.reasoning_content is not None,
            "tool_call_count": len(message.tool_calls),
        }
        for message in messages
    ]
    digest = hashlib.sha256(
        json.dumps(shape, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return CalibrationRequestSummary(
        ordinal=ordinal,
        variant=variant,
        message_count=len(messages),
        message_roles=tuple(message.role.value for message in messages),
        message_shape_sha256=digest,
        max_tokens=max_tokens,
        timeout_s=REQUEST_TIMEOUT_S,
        temperature=1.0,
        top_p=0.95,
        reasoning_effort=reasoning_effort,
    )


def _run_nonstream(
    client: Any,
    *,
    request: CalibrationRequestSummary,
    messages: tuple[ChatMessage, ...],
    max_tokens: int,
    reasoning_effort: Literal["low", "max"],
) -> CalibrationObservation:
    started = time.monotonic()
    payload = {
        "model": MODEL,
        "messages": [
            {"role": message.role.value, "content": message.content}
            for message in messages
        ],
        "temperature": 1.0,
        "top_p": 0.95,
        "max_tokens": max_tokens,
        "timeout": REQUEST_TIMEOUT_S,
        "stream": False,
        "extra_body": {
            "thinking": {"type": "enabled"},
            "reasoning_effort": reasoning_effort,
        },
    }
    try:
        raw = client.chat.completions.create(**payload)
    except Exception as error:
        elapsed = _elapsed_ms(started)
        error_class, error_code = _classify_error(error)
        return _failed_observation(
            request,
            elapsed_ms=elapsed,
            sdk_error_class=error_class,
            error_code=error_code,
            error_stage="create",
        )
    elapsed = _elapsed_ms(started)
    state = _response_state(raw)
    if state["malformed"]:
        return _failed_observation(
            request,
            elapsed_ms=elapsed,
            response_received=True,
            generation_observed=False,
            content_state=state["content_state"],
            reasoning_state=state["reasoning_state"],
            usage_state=state["usage_state"],
            input_tokens=state["input_tokens"],
            output_tokens=state["output_tokens"],
            cached_input_tokens=state["cached_input_tokens"],
            finish_reason=state["finish_reason"],
            resolved_model=state["resolved_model"],
            request_id_sha256=state["request_id_sha256"],
            error_code="invalid_response_shape",
            error_stage="response_shape",
        )
    return CalibrationObservation(
        ordinal=request.ordinal,
        variant=request.variant,
        status="observed",
        request=request,
        external_calls=1,
        response_received=True,
        generation_observed=True,
        visible_content_observed=state["content_state"] == "non_empty",
        create_latency_ms=elapsed,
        sdk_latency_ms=elapsed,
        elapsed_ms=elapsed,
        finish_reason=state["finish_reason"],
        content_state=state["content_state"],
        reasoning_state=state["reasoning_state"],
        usage_state=state["usage_state"],
        input_tokens=state["input_tokens"],
        output_tokens=state["output_tokens"],
        cached_input_tokens=state["cached_input_tokens"],
        resolved_model=state["resolved_model"],
        request_id_sha256=state["request_id_sha256"],
    )


def _failed_observation(
    request: CalibrationRequestSummary,
    *,
    elapsed_ms: int,
    error_code: str,
    error_stage: str,
    response_received: bool = False,
    generation_observed: bool = False,
    content_state: FieldState = "not_observed",
    reasoning_state: FieldState = "not_observed",
    usage_state: UsageState = "missing",
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    cached_input_tokens: int | None = None,
    finish_reason: FinishReason | None = None,
    resolved_model: str | None = None,
    request_id_sha256: str | None = None,
    sdk_error_class: SdkErrorClass | None = None,
) -> CalibrationObservation:
    return CalibrationObservation(
        ordinal=request.ordinal,
        variant=request.variant,
        status="failed",
        request=request,
        external_calls=1,
        response_received=response_received,
        generation_observed=generation_observed,
        visible_content_observed=content_state == "non_empty",
        create_latency_ms=max(0, elapsed_ms),
        sdk_latency_ms=max(0, elapsed_ms),
        elapsed_ms=max(0, elapsed_ms),
        finish_reason=finish_reason,
        content_state=content_state,
        reasoning_state=reasoning_state,
        usage_state=usage_state,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_input_tokens=cached_input_tokens,
        resolved_model=resolved_model,
        request_id_sha256=request_id_sha256,
        sdk_error_class=sdk_error_class,
        error_code=error_code,
        error_stage=error_stage,
    )


def _skipped_observation(request: CalibrationRequestSummary, reason: str) -> CalibrationObservation:
    return CalibrationObservation(
        ordinal=request.ordinal,
        variant=request.variant,
        status="skipped",
        request=request,
        external_calls=0,
        skip_reason=reason,
        create_latency_ms=0,
        sdk_latency_ms=0,
        elapsed_ms=0,
    )


def _response_state(raw: Any) -> dict[str, Any]:
    choices = getattr(raw, "choices", _MISSING)
    state: dict[str, Any] = {
        "malformed": False,
        "content_state": "missing",
        "reasoning_state": "missing",
        "usage_state": "missing",
        "input_tokens": None,
        "output_tokens": None,
        "cached_input_tokens": None,
        "finish_reason": "missing",
        "resolved_model": _safe_model(getattr(raw, "model", None)),
        "request_id_sha256": _request_digest(getattr(raw, "id", None)),
    }
    if not isinstance(choices, (list, tuple)) or not choices:
        state["malformed"] = True
    else:
        choice = choices[0]
        message = getattr(choice, "message", _MISSING)
        if message is _MISSING or message is None:
            state["malformed"] = True
        else:
            state["content_state"] = _field_state(getattr(message, "content", _MISSING))
            state["reasoning_state"] = _field_state(
                getattr(message, "reasoning_content", _MISSING)
            )
        state["finish_reason"] = _finish_reason(
            getattr(choice, "finish_reason", _MISSING)
        )
        if state["finish_reason"] == "unknown":
            state["malformed"] = True
    (
        state["usage_state"],
        state["input_tokens"],
        state["output_tokens"],
        state["cached_input_tokens"],
    ) = _usage_state(getattr(raw, "usage", _MISSING))
    return state


def _resources(observations: list[CalibrationObservation]) -> CalibrationResources:
    input_tokens = sum(row.input_tokens or 0 for row in observations)
    output_tokens = sum(row.output_tokens or 0 for row in observations)
    cached = sum(row.cached_input_tokens or 0 for row in observations)
    total = input_tokens + output_tokens
    return CalibrationResources(
        calls_used=sum(row.external_calls for row in observations),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_input_tokens=cached,
        total_tokens=total,
        latency_ms=sum(row.elapsed_ms for row in observations),
        within_token_budget=total <= MAX_OBSERVED_TOKENS,
    )


def _verdicts(observations: list[CalibrationObservation]) -> CalibrationVerdicts:
    low, low_high, max_high = observations
    reachable = (
        low.generation_observed
        or low_high.generation_observed
        or max_high.generation_observed
    )
    visible_low = low.visible_content_observed
    visible_low_high = low_high.visible_content_observed
    visible_max_high = max_high.visible_content_observed
    if visible_low_high:
        interpretation = "low_effort_high_budget_visible_content"
    elif visible_low:
        interpretation = "low_effort_2048_visible_content"
    elif visible_max_high:
        interpretation = "max_effort_high_budget_visible_content"
    elif reachable:
        interpretation = "generation_observed_without_visible_content"
    else:
        interpretation = "transport_path_not_observed"
    return CalibrationVerdicts(
        transport_reachable=reachable,
        visible_content_observed=visible_low or visible_low_high or visible_max_high,
        low_2048_visible_content=visible_low,
        low_8192_visible_content=visible_low_high,
        max_8192_visible_content=visible_max_high,
        interpretation_code=interpretation,
    )


def _experiment_id(identity: MatrixSourceIdentity, timestamp: datetime) -> str:
    payload = {
        "experiment": EXPERIMENT_NAME,
        "head_sha": identity.head_sha,
        "patch_sha256": identity.worktree_patch_sha256,
        "timestamp": timestamp.isoformat(),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _read_head_sha(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    ).stdout.strip()


def _write_immutable_report(path: Path, text: str) -> None:
    """Create the finished report without reserving a zero-byte placeholder."""

    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def _validate_context_snapshot(context: FrozenContextSnapshot) -> None:
    _validate_context(context)


__all__ = [
    "BASE_URL",
    "DEFAULT_OUTPUT",
    "FrozenContextSnapshot",
    "HIGH_MAX_TOKENS",
    "LOW_MAX_TOKENS",
    "MODEL",
    "OutputBudgetCalibrationReport",
    "run_output_budget_calibration",
]


