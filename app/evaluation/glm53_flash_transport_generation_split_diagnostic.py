"""Bounded, body-free transport-versus-generation probes for GLM-5.3-Flash.

RQ-187 used the candidate's full synchronous request window and observed no
response.  This module does not retry that request.  It sends three separately
identified probes instead:

* a tiny, thinking-disabled non-stream control for basic endpoint reachability;
* the frozen held-out context with a small non-stream output cap; and
* the same frozen context as a stream, stopping after the first observed chunk.

The probes are evaluation-only.  They retain only allowlisted states, timings,
token counts and digests; prompt/response/reasoning/tool bodies, credentials and
raw request identifiers never enter the report.  No provider-neutral runtime or
production registration is changed by this module.
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
from typing import Annotated, Any, Literal

import openai
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.providers.models import ChatMessage, MessageRole
from app.evaluation.domain_e2e import (
    DomainDatasetRole,
    load_domain_dataset,
    validate_domain_dataset_usage,
)
from app.evaluation.glm53_flash_response_recovery_diagnostic import (
    _build_frozen_context,
)
from app.evaluation.provider_domain_plan import load_domain_case_input_plan
from app.evaluation.glm53_flash_capability_matrix import (
    MatrixSourceIdentity,
    collect_source_identity,
)
from app.providers.config import load_zhipu_settings
from app.providers.zhipu_profiles import (
    ZHIPU_GLM53_FLASH_MODEL,
    ZHIPU_GLM53_FLASH_THINKING_PROFILE,
)


PROVIDER_ID = "zhipu"
MODEL = ZHIPU_GLM53_FLASH_MODEL
BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"
CASE_ID = "flash_gate_baseline_01"
SCHEMA_VERSION = "1.0"
EXPERIMENT_NAME = "g53-8-transport-generation-split-v1"
DEFAULT_OUTPUT = Path(
    "data/evaluation/results/provider_capabilities/"
    "zhipu_glm53_flash_transport_generation_split_diagnostic_v1.json"
)

# These are deliberately fixed for one comparable diagnostic batch.  The
# full-window 90-second observation already exists as RQ-187 and is linked by
# digest below, so it is not repeated here.
MINIMAL_MAX_TOKENS = 16
MINIMAL_TIMEOUT_S = 15.0
SHORT_MAX_TOKENS = 256
SHORT_TIMEOUT_S = 30.0
STREAM_MAX_TOKENS = 8192
STREAM_TIMEOUT_S = 45.0
CLIENT_TIMEOUT_S = 60.0
MAX_REAL_CALLS = 3
MAX_OBSERVED_TOKENS = 64_000
BASELINE_EXPERIMENT_ID = "a3895dd12c506f493efcd9c7842e8ab6e3ef1a8f099204ca07779a8e4c316245"
BASELINE_RESULT_SHA256 = "3d8d4744da3286b921d894684bfffcbf19d56d2c945821703ae1d4282fd80263"
CONTROL_MARKER = "RIFTCOACH_TRANSPORT_OK"

ProbeVariant = Literal[
    "minimal_transport_control",
    "frozen_short_nonstream",
    "frozen_stream_first_chunk",
]
ProbeStatus = Literal["observed", "failed", "skipped"]
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
CompletionState = Literal["complete", "partial", "not_observed"]
ChunkShape = Literal[
    "not_observed",
    "choices_empty",
    "delta_content",
    "delta_reasoning",
    "delta_other",
    "malformed",
]

SafeSha = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
GitSha = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
SafeCode = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_.-]{0,95}$")]
SafeModel = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"),
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
_STOP_CODES = frozenset(
    {"authentication_failed", "permission_denied", "rate_limited"}
)


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


@dataclass(frozen=True)
class FrozenContextSnapshot:
    """Exact messages plus public identities needed by the diagnostic."""

    messages: tuple[ChatMessage, ...]
    input_plan_sha256: str
    prompt_context_snapshot_sha256: str


class ProbeRequestSummary(_FrozenModel):
    ordinal: int = Field(ge=1, le=MAX_REAL_CALLS)
    variant: ProbeVariant
    message_count: int = Field(ge=1, le=128)
    message_roles: tuple[str, ...]
    message_shape_sha256: SafeSha
    max_tokens: int = Field(ge=1, le=STREAM_MAX_TOKENS)
    timeout_s: float = Field(gt=0, le=90)
    stream: bool
    temperature: float = Field(ge=0, le=2)
    top_p: float = Field(ge=0, le=1)
    thinking_type: Literal["disabled", "enabled"]
    reasoning_effort: Literal["low", "max"]


class ProbeObservation(_FrozenModel):
    ordinal: int = Field(ge=1, le=MAX_REAL_CALLS)
    variant: ProbeVariant
    status: ProbeStatus
    request: ProbeRequestSummary
    external_calls: Literal[0, 1]
    skip_reason: SafeCode | None = None
    response_received: bool = False
    stream_opened: bool = False
    first_chunk_observed: bool = False
    generation_observed: bool = False
    marker_match: bool | None = None
    create_latency_ms: int = Field(ge=0)
    first_chunk_latency_ms: int | None = Field(default=None, ge=0)
    sdk_latency_ms: int = Field(ge=0)
    elapsed_ms: int = Field(ge=0)
    completion_state: CompletionState = "not_observed"
    finish_reason: FinishReason | None = None
    content_state: FieldState = "not_observed"
    reasoning_state: FieldState = "not_observed"
    usage_state: UsageState = "missing"
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cached_input_tokens: int | None = Field(default=None, ge=0)
    chunk_count: int = Field(default=0, ge=0)
    first_chunk_shape: ChunkShape = "not_observed"
    resolved_model: SafeModel | None = None
    request_id_sha256: SafeSha | None = None
    sdk_error_class: SdkErrorClass | None = None
    error_code: SafeCode | None = None
    error_stage: SafeCode | None = None

    @model_validator(mode="after")
    def validate_observation(self) -> "ProbeObservation":
        if self.external_calls == 0 and self.status != "skipped":
            raise ValueError("zero-call observations must be skipped")
        if self.status == "skipped":
            if self.skip_reason is None or self.external_calls != 0:
                raise ValueError("skipped observations need a reason and zero calls")
            if (
                self.response_received
                or self.stream_opened
                or self.first_chunk_observed
                or self.generation_observed
            ):
                raise ValueError("skipped observations cannot claim execution")
        else:
            if self.external_calls != 1 or self.skip_reason is not None:
                raise ValueError("executed observations need exactly one call")
        if self.first_chunk_observed:
            if not self.request.stream or not self.stream_opened:
                raise ValueError("first chunk requires an opened stream")
            if self.first_chunk_latency_ms is None:
                raise ValueError("first chunk needs a latency")
        if self.request.stream and self.generation_observed and not self.first_chunk_observed:
            raise ValueError("stream generation requires a first chunk")
        if self.usage_state == "valid":
            if self.input_tokens is None or self.output_tokens is None:
                raise ValueError("valid usage needs input and output counts")
            if self.cached_input_tokens is None:
                raise ValueError("valid usage needs cache count")
            if self.cached_input_tokens > self.input_tokens:
                raise ValueError("cached input cannot exceed input")
        elif any(
            value is not None
            for value in (self.input_tokens, self.output_tokens, self.cached_input_tokens)
        ):
            raise ValueError("unavailable usage cannot carry token counts")
        if self.status == "failed" and self.error_code is None:
            raise ValueError("failed observations need an error code")
        if self.status != "failed" and self.error_code is not None:
            raise ValueError("only failed observations may carry an error code")
        if self.status == "observed" and not (
            self.response_received or self.first_chunk_observed
        ):
            raise ValueError("observed observations need a response or first chunk")
        if self.first_chunk_shape != "not_observed" and not self.first_chunk_observed:
            raise ValueError("chunk shape requires a first chunk")
        return self


class SplitBudget(_FrozenModel):
    max_real_calls: Literal[MAX_REAL_CALLS] = MAX_REAL_CALLS
    max_observed_tokens: Literal[MAX_OBSERVED_TOKENS] = MAX_OBSERVED_TOKENS
    max_output_tokens_per_request: Literal[STREAM_MAX_TOKENS] = STREAM_MAX_TOKENS
    sdk_max_retries: Literal[0] = 0


class SplitResources(_FrozenModel):
    calls_used: int = Field(ge=0, le=MAX_REAL_CALLS)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cached_input_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0, le=MAX_OBSERVED_TOKENS)
    latency_ms: int = Field(ge=0)
    within_token_budget: bool

    @model_validator(mode="after")
    def validate_resources(self) -> "SplitResources":
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("resource total mismatch")
        if self.cached_input_tokens > self.input_tokens:
            raise ValueError("cached input cannot exceed input")
        if self.within_token_budget != (self.total_tokens <= MAX_OBSERVED_TOKENS):
            raise ValueError("token budget status mismatch")
        return self


class SplitVerdicts(_FrozenModel):
    minimal_control_observed: bool
    minimal_control_marker_match: bool | None
    transport_reachable: bool
    frozen_short_generation_observed: bool
    stream_first_chunk_observed: bool
    long_window_baseline_observed: Literal[False] = False
    interpretation_code: SafeCode
    candidate_registered: Literal[False] = False
    production_admitted: Literal[False] = False


class TransportGenerationSplitReport(_FrozenModel):
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
    case_id: Literal[CASE_ID] = CASE_ID
    baseline_experiment_id: Literal[BASELINE_EXPERIMENT_ID] = BASELINE_EXPERIMENT_ID
    baseline_result_sha256: Literal[BASELINE_RESULT_SHA256] = BASELINE_RESULT_SHA256
    input_plan_sha256: SafeSha
    prompt_context_snapshot_sha256: SafeSha
    observation_scope: Literal["vendor_raw_transport_only"] = "vendor_raw_transport_only"
    thinking_profile_id: Literal[ZHIPU_GLM53_FLASH_THINKING_PROFILE.profile_id] = (
        ZHIPU_GLM53_FLASH_THINKING_PROFILE.profile_id
    )
    explicit_real_call_confirmed: Literal[True] = True
    source_identity: MatrixSourceIdentity
    source_identity_after: MatrixSourceIdentity
    source_identity_stable: bool
    budget: SplitBudget
    resources: SplitResources
    calls_attempted: int = Field(ge=0, le=MAX_REAL_CALLS)
    cost_status: Literal["unknown"] = "unknown"
    run_timestamp_utc: datetime
    observations: tuple[ProbeObservation, ...]
    unsupported_boundaries: tuple[str, ...]
    verdicts: SplitVerdicts

    @model_validator(mode="after")
    def validate_report(self) -> "TransportGenerationSplitReport":
        expected = (
            "minimal_transport_control",
            "frozen_short_nonstream",
            "frozen_stream_first_chunk",
        )
        if tuple(row.variant for row in self.observations) != expected:
            raise ValueError("probe variants must use canonical order")
        if self.calls_attempted != sum(row.external_calls for row in self.observations):
            raise ValueError("call count mismatch")
        if self.resources.calls_used != self.calls_attempted:
            raise ValueError("resource call count mismatch")
        if self.resources.input_tokens != sum(
            row.input_tokens or 0 for row in self.observations
        ):
            raise ValueError("resource input mismatch")
        if self.resources.output_tokens != sum(
            row.output_tokens or 0 for row in self.observations
        ):
            raise ValueError("resource output mismatch")
        if self.resources.cached_input_tokens != sum(
            row.cached_input_tokens or 0 for row in self.observations
        ):
            raise ValueError("resource cache mismatch")
        if self.resources.latency_ms != sum(row.elapsed_ms for row in self.observations):
            raise ValueError("resource latency mismatch")
        if self.verdicts.production_admitted or self.verdicts.candidate_registered:
            raise ValueError("diagnostic cannot admit production or register candidate")
        return self


def run_transport_generation_split_diagnostic(
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
) -> TransportGenerationSplitReport:
    """Run exactly one bounded three-variant diagnostic batch.

    The caller must explicitly confirm real I/O.  Authentication, permission
    and rate-limit failures stop the remaining probes; timeouts and ordinary
    transport failures do not silently retry and allow the independent probes
    to continue.
    """

    if confirm_real_call is not True:
        raise RuntimeError("transport-generation diagnostics require explicit confirmation")
    root = Path(repository_root).resolve()
    _validate_sha(implementation_sha, "implementation_sha")
    diagnostic_code_sha = diagnostic_code_sha or _read_head_sha(root)
    _validate_sha(diagnostic_code_sha, "diagnostic_code_sha")
    output_path = _inside_results(root, output)
    if output_path.exists():
        raise FileExistsError("diagnostic evidence is immutable")

    context = (context_loader or _load_frozen_context)(root)
    _validate_context(context)
    load_environment = environment_loader or _load_environment
    settings = load_zhipu_settings(load_environment(Path(env_file) if env_file else None))
    if settings.model != MODEL or settings.base_url.rstrip("/") != BASE_URL.rstrip("/"):
        raise ValueError("diagnostic settings must target GLM-5.3 Flash")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Reserve before opening the client so a second process cannot reuse the
    # same evidence name.  The reserved path is included in both source
    # identities, keeping the dirty-worktree comparison stable.
    output_path.touch(exist_ok=False)
    source_identity = (source_identity_loader or collect_source_identity)(root)
    client = client_factory(
        api_key=settings.api_key,
        base_url=settings.base_url,
        timeout=CLIENT_TIMEOUT_S,
        max_retries=0,
    )

    observations: list[ProbeObservation] = []
    stop_code: str | None = None
    for ordinal, (
        variant,
        messages,
        max_tokens,
        timeout_s,
        stream,
        thinking_type,
        reasoning_effort,
    ) in enumerate(
        _probe_specs(context),
        start=1,
    ):
        request = _request_summary(
            ordinal=ordinal,
            variant=variant,
            messages=messages,
            max_tokens=max_tokens,
            timeout_s=timeout_s,
            stream=stream,
            thinking_type=thinking_type,
            reasoning_effort=reasoning_effort,
        )
        if stop_code is not None:
            observations.append(_skipped_observation(request, stop_code))
            continue
        payload = _request_payload(
            messages=messages,
            max_tokens=max_tokens,
            timeout_s=timeout_s,
            stream=stream,
            thinking_type=thinking_type,
            reasoning_effort=reasoning_effort,
        )
        if stream:
            observation = _run_stream_probe(
                client,
                request=request,
                payload=payload,
            )
        else:
            observation = _run_nonstream_probe(
                client,
                request=request,
                payload=payload,
                expected_marker=(CONTROL_MARKER if variant == "minimal_transport_control" else None),
            )
        observations.append(observation)
        if observation.error_code in _STOP_CODES:
            stop_code = observation.error_code

    source_identity_after = (source_identity_loader or collect_source_identity)(root)
    resources = _resources(observations)
    verdicts = _verdicts(observations)
    report = TransportGenerationSplitReport(
        experiment_id=_experiment_id(source_identity, now()),
        implementation_sha=implementation_sha,
        diagnostic_code_sha=diagnostic_code_sha,
        input_plan_sha256=context.input_plan_sha256,
        prompt_context_snapshot_sha256=context.prompt_context_snapshot_sha256,
        source_identity=source_identity,
        source_identity_after=source_identity_after,
        source_identity_stable=source_identity == source_identity_after,
        budget=SplitBudget(),
        resources=resources,
        calls_attempted=sum(row.external_calls for row in observations),
        run_timestamp_utc=now(),
        observations=tuple(observations),
        unsupported_boundaries=(
            "RQ-187 full-window baseline remains unresolved between proxy/read and server generation",
            "stream probe stops after first chunk and is not a complete provider-neutral stream contract",
            "no tool is supplied or executed; no response body or reasoning text is retained",
            "candidate remains unregistered; production security/deployment/compliance gates remain open",
        ),
        verdicts=verdicts,
    )
    _assert_body_free(report.model_dump())
    output_path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return report


def _load_frozen_context(root: Path) -> FrozenContextSnapshot:
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
    # Reuse the exact frozen context constructor used by the previous
    # diagnostic; it intentionally removes knowledge tools and performs no I/O.
    context_bundle = _build_frozen_context(root, loaded_plan, case)
    return FrozenContextSnapshot(
        messages=tuple(context_bundle.messages),
        input_plan_sha256=loaded_plan.execution_plan.plan_sha256,
        prompt_context_snapshot_sha256=loaded_plan.artifact.prompt_context_snapshot_sha256
        or _zero_sha(),
    )


def _validate_context(context: FrozenContextSnapshot) -> None:
    if not isinstance(context, FrozenContextSnapshot):
        raise TypeError("context_loader must return FrozenContextSnapshot")
    for name, value in (
        ("input_plan_sha256", context.input_plan_sha256),
        ("prompt_context_snapshot_sha256", context.prompt_context_snapshot_sha256),
    ):
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError(f"{name} must be a full lowercase SHA-256")
    if not context.messages:
        raise ValueError("frozen context must contain messages")
    for message in context.messages:
        if not isinstance(message, ChatMessage) or message.role not in {
            MessageRole.SYSTEM,
            MessageRole.USER,
        }:
            raise ValueError("diagnostic context must contain only system/user text messages")
        if not isinstance(message.content, str) or not message.content.strip():
            raise ValueError("diagnostic context messages must contain text")


def _probe_specs(context: FrozenContextSnapshot):
    yield (
        "minimal_transport_control",
        (ChatMessage(MessageRole.USER, CONTROL_MARKER),),
        MINIMAL_MAX_TOKENS,
        MINIMAL_TIMEOUT_S,
        False,
        "enabled",
        "low",
    )
    yield (
        "frozen_short_nonstream",
        context.messages,
        SHORT_MAX_TOKENS,
        SHORT_TIMEOUT_S,
        False,
        "enabled",
        "max",
    )
    yield (
        "frozen_stream_first_chunk",
        context.messages,
        STREAM_MAX_TOKENS,
        STREAM_TIMEOUT_S,
        True,
        "enabled",
        "max",
    )


def _request_summary(
    *,
    ordinal: int,
    variant: ProbeVariant,
    messages: tuple[ChatMessage, ...],
    max_tokens: int,
    timeout_s: float,
    stream: bool,
    thinking_type: Literal["disabled", "enabled"],
    reasoning_effort: Literal["low", "max"],
) -> ProbeRequestSummary:
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
    return ProbeRequestSummary(
        ordinal=ordinal,
        variant=variant,
        message_count=len(messages),
        message_roles=tuple(message.role.value for message in messages),
        message_shape_sha256=digest,
        max_tokens=max_tokens,
        timeout_s=timeout_s,
        stream=stream,
        temperature=1.0,
        top_p=0.95,
        thinking_type=thinking_type,
        reasoning_effort=reasoning_effort,
    )


def _request_payload(
    *,
    messages: tuple[ChatMessage, ...],
    max_tokens: int,
    timeout_s: float,
    stream: bool,
    thinking_type: Literal["disabled", "enabled"],
    reasoning_effort: Literal["low", "max"],
) -> dict[str, Any]:
    encoded_messages = [
        {"role": message.role.value, "content": message.content}
        for message in messages
    ]
    extra_body: dict[str, Any]
    if thinking_type == "disabled":
        extra_body = {"thinking": {"type": "disabled"}}
    else:
        if reasoning_effort == "max":
            extra_body = ZHIPU_GLM53_FLASH_THINKING_PROFILE.extra_body()
        else:
            extra_body = {
                "thinking": {"type": "enabled"},
                "reasoning_effort": reasoning_effort,
            }
    return {
        "model": MODEL,
        "messages": encoded_messages,
        "temperature": 1.0,
        "top_p": 0.95,
        "max_tokens": max_tokens,
        "timeout": timeout_s,
        "stream": stream,
        "extra_body": extra_body,
    }


def _run_nonstream_probe(
    client: Any,
    *,
    request: ProbeRequestSummary,
    payload: Mapping[str, Any],
    expected_marker: str | None,
) -> ProbeObservation:
    started = time.monotonic()
    try:
        raw = client.chat.completions.create(**dict(payload))
    except Exception as error:
        elapsed = _elapsed_ms(started)
        error_class, error_code = _classify_error(error)
        return _failed_observation(
            request,
            elapsed_ms=elapsed,
            create_latency_ms=elapsed,
            sdk_error_class=error_class,
            error_code=error_code,
            error_stage="create",
        )
    elapsed = _elapsed_ms(started)
    state = _raw_response_state(raw)
    if state["malformed"]:
        return _failed_observation(
            request,
            elapsed_ms=elapsed,
            create_latency_ms=elapsed,
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
    content_value = state["content_value"]
    marker_match = None
    if expected_marker is not None:
        marker_match = isinstance(content_value, str) and content_value.strip() == expected_marker
    return ProbeObservation(
        ordinal=request.ordinal,
        variant=request.variant,
        status="observed",
        request=request,
        external_calls=1,
        response_received=True,
        generation_observed=True,
        marker_match=marker_match,
        create_latency_ms=elapsed,
        sdk_latency_ms=elapsed,
        elapsed_ms=elapsed,
        completion_state=(
            "complete" if state["finish_reason"] not in {None, "missing", "unknown"} else "partial"
        ),
        finish_reason=state["finish_reason"],
        content_state=state["content_state"],
        reasoning_state=state["reasoning_state"],
        usage_state=state["usage_state"],
        input_tokens=state["input_tokens"],
        output_tokens=state["output_tokens"],
        cached_input_tokens=state["cached_input_tokens"],
        chunk_count=0,
        resolved_model=state["resolved_model"],
        request_id_sha256=state["request_id_sha256"],
    )


def _run_stream_probe(
    client: Any,
    *,
    request: ProbeRequestSummary,
    payload: Mapping[str, Any],
) -> ProbeObservation:
    started = time.monotonic()
    try:
        raw_stream = client.chat.completions.create(**dict(payload))
    except Exception as error:
        elapsed = _elapsed_ms(started)
        error_class, error_code = _classify_error(error)
        return _failed_observation(
            request,
            elapsed_ms=elapsed,
            create_latency_ms=elapsed,
            sdk_error_class=error_class,
            error_code=error_code,
            error_stage="create",
        )

    create_latency = _elapsed_ms(started)
    try:
        iterator = iter(raw_stream)
    except Exception:
        _close_stream(raw_stream)
        elapsed = _elapsed_ms(started)
        return _failed_observation(
            request,
            elapsed_ms=elapsed,
            create_latency_ms=create_latency,
            stream_opened=True,
            error_code="invalid_stream_iterator",
            error_stage="first_chunk",
        )

    try:
        first = next(iterator)
    except StopIteration:
        elapsed = _elapsed_ms(started)
        _close_stream(raw_stream)
        return _failed_observation(
            request,
            elapsed_ms=elapsed,
            create_latency_ms=create_latency,
            stream_opened=True,
            error_code="empty_stream",
            error_stage="first_chunk",
        )
    except Exception as error:
        elapsed = _elapsed_ms(started)
        _close_stream(raw_stream)
        error_class, error_code = _classify_error(error)
        return _failed_observation(
            request,
            elapsed_ms=elapsed,
            create_latency_ms=create_latency,
            stream_opened=True,
            sdk_error_class=error_class,
            error_code=error_code,
            error_stage="first_chunk",
        )
    finally:
        _close_stream(raw_stream)

    elapsed = _elapsed_ms(started)
    state = _stream_chunk_state(first)
    if state["malformed"]:
        return _failed_observation(
            request,
            elapsed_ms=elapsed,
            create_latency_ms=create_latency,
            first_chunk_latency_ms=elapsed,
            response_received=True,
            stream_opened=True,
            first_chunk_observed=True,
            generation_observed=True,
            chunk_count=1,
            first_chunk_shape="malformed",
            content_state=state["content_state"],
            reasoning_state=state["reasoning_state"],
            usage_state=state["usage_state"],
            input_tokens=state["input_tokens"],
            output_tokens=state["output_tokens"],
            cached_input_tokens=state["cached_input_tokens"],
            finish_reason=state["finish_reason"],
            resolved_model=state["resolved_model"],
            request_id_sha256=state["request_id_sha256"],
            error_code="invalid_stream_chunk",
            error_stage="response_shape",
        )
    return ProbeObservation(
        ordinal=request.ordinal,
        variant=request.variant,
        status="observed",
        request=request,
        external_calls=1,
        response_received=True,
        stream_opened=True,
        first_chunk_observed=True,
        generation_observed=True,
        create_latency_ms=create_latency,
        first_chunk_latency_ms=elapsed,
        sdk_latency_ms=elapsed,
        elapsed_ms=elapsed,
        completion_state="not_observed",
        finish_reason=state["finish_reason"],
        content_state=state["content_state"],
        reasoning_state=state["reasoning_state"],
        usage_state=state["usage_state"],
        input_tokens=state["input_tokens"],
        output_tokens=state["output_tokens"],
        cached_input_tokens=state["cached_input_tokens"],
        chunk_count=1,
        first_chunk_shape=state["chunk_shape"],
        resolved_model=state["resolved_model"],
        request_id_sha256=state["request_id_sha256"],
    )


def _raw_response_state(raw: Any) -> dict[str, Any]:
    choices = getattr(raw, "choices", _MISSING)
    state: dict[str, Any] = {
        "malformed": False,
        "content_value": None,
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
        state["content_state"] = "missing"
        state["reasoning_state"] = "missing"
        state["usage_state"], state["input_tokens"], state["output_tokens"], state["cached_input_tokens"] = _usage_state(
            getattr(raw, "usage", _MISSING)
        )
        return state
    choice = choices[0]
    message = getattr(choice, "message", _MISSING)
    if message is _MISSING or message is None:
        state["malformed"] = True
    else:
        content = getattr(message, "content", _MISSING)
        state["content_value"] = content if isinstance(content, str) else None
        state["content_state"] = _field_state(content)
        state["reasoning_state"] = _field_state(
            getattr(message, "reasoning_content", _MISSING)
        )
    state["finish_reason"] = _finish_reason(getattr(choice, "finish_reason", _MISSING))
    if state["finish_reason"] == "unknown":
        state["malformed"] = True
    state["usage_state"], state["input_tokens"], state["output_tokens"], state["cached_input_tokens"] = _usage_state(
        getattr(raw, "usage", _MISSING)
    )
    return state


def _stream_chunk_state(raw: Any) -> dict[str, Any]:
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
        "chunk_shape": "malformed",
        "resolved_model": _safe_model(getattr(raw, "model", None)),
        "request_id_sha256": _request_digest(getattr(raw, "id", None)),
    }
    state["usage_state"], state["input_tokens"], state["output_tokens"], state["cached_input_tokens"] = _usage_state(
        getattr(raw, "usage", _MISSING)
    )
    if not isinstance(choices, (list, tuple)):
        state["malformed"] = True
        return state
    if not choices:
        state["chunk_shape"] = "choices_empty"
        return state
    if len(choices) != 1:
        state["malformed"] = True
        return state
    choice = choices[0]
    delta = getattr(choice, "delta", _MISSING)
    if delta is _MISSING or delta is None:
        state["malformed"] = True
        return state
    content = getattr(delta, "content", _MISSING)
    reasoning = getattr(delta, "reasoning_content", _MISSING)
    state["content_state"] = _field_state(content)
    state["reasoning_state"] = _field_state(reasoning)
    state["finish_reason"] = _finish_reason(getattr(choice, "finish_reason", _MISSING))
    if content is not _MISSING and content not in (None, ""):
        state["chunk_shape"] = "delta_content"
    elif reasoning is not _MISSING and reasoning not in (None, ""):
        state["chunk_shape"] = "delta_reasoning"
    else:
        state["chunk_shape"] = "delta_other"
    return state


def _failed_observation(
    request: ProbeRequestSummary,
    *,
    elapsed_ms: int,
    create_latency_ms: int,
    error_code: str,
    error_stage: str,
    response_received: bool = False,
    stream_opened: bool = False,
    first_chunk_observed: bool = False,
    generation_observed: bool = False,
    first_chunk_latency_ms: int | None = None,
    sdk_error_class: SdkErrorClass | None = None,
    content_state: FieldState = "not_observed",
    reasoning_state: FieldState = "not_observed",
    usage_state: UsageState = "missing",
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    cached_input_tokens: int | None = None,
    finish_reason: FinishReason | None = None,
    chunk_count: int = 0,
    first_chunk_shape: ChunkShape = "not_observed",
    resolved_model: str | None = None,
    request_id_sha256: str | None = None,
) -> ProbeObservation:
    return ProbeObservation(
        ordinal=request.ordinal,
        variant=request.variant,
        status="failed",
        request=request,
        external_calls=1,
        response_received=response_received,
        stream_opened=stream_opened,
        first_chunk_observed=first_chunk_observed,
        generation_observed=generation_observed,
        create_latency_ms=max(0, create_latency_ms),
        first_chunk_latency_ms=first_chunk_latency_ms,
        sdk_latency_ms=max(0, elapsed_ms),
        elapsed_ms=max(0, elapsed_ms),
        completion_state="partial" if response_received else "not_observed",
        finish_reason=finish_reason,
        content_state=content_state,
        reasoning_state=reasoning_state,
        usage_state=usage_state,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_input_tokens=cached_input_tokens,
        chunk_count=chunk_count,
        first_chunk_shape=first_chunk_shape,
        resolved_model=resolved_model,
        request_id_sha256=request_id_sha256,
        sdk_error_class=sdk_error_class,
        error_code=_safe_code(error_code) or "probe_failed",
        error_stage=_safe_code(error_stage) or "unknown",
    )


def _skipped_observation(request: ProbeRequestSummary, reason: str) -> ProbeObservation:
    return ProbeObservation(
        ordinal=request.ordinal,
        variant=request.variant,
        status="skipped",
        request=request,
        external_calls=0,
        skip_reason=_safe_code(reason) or "prior_probe_failed",
        create_latency_ms=0,
        sdk_latency_ms=0,
        elapsed_ms=0,
    )


def _resources(observations: list[ProbeObservation]) -> SplitResources:
    input_tokens = sum(row.input_tokens or 0 for row in observations)
    output_tokens = sum(row.output_tokens or 0 for row in observations)
    cached = sum(row.cached_input_tokens or 0 for row in observations)
    total = input_tokens + output_tokens
    return SplitResources(
        calls_used=sum(row.external_calls for row in observations),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_input_tokens=cached,
        total_tokens=total,
        latency_ms=sum(row.elapsed_ms for row in observations),
        within_token_budget=total <= MAX_OBSERVED_TOKENS,
    )


def _verdicts(observations: list[ProbeObservation]) -> SplitVerdicts:
    control, short, stream = observations
    minimal_observed = control.generation_observed
    marker_match = control.marker_match
    # A valid frozen response or a first stream chunk is itself proof that the
    # endpoint and model path were reachable, even if the tiny marker control
    # was rejected for a model-specific request-shape reason.
    reachable = minimal_observed or short.generation_observed or stream.first_chunk_observed
    short_seen = short.generation_observed
    stream_seen = stream.first_chunk_observed
    if minimal_observed and stream_seen:
        interpretation = "transport_reachable_first_byte_observed"
    elif reachable and stream_seen and not minimal_observed:
        interpretation = "endpoint_reachable_control_variant_rejected"
    elif reachable and short_seen:
        interpretation = "transport_reachable_generation_observed_stream_unresolved"
    elif reachable:
        interpretation = "transport_reachable_long_generation_unresolved"
    else:
        interpretation = "transport_path_not_observed"
    return SplitVerdicts(
        minimal_control_observed=minimal_observed,
        minimal_control_marker_match=marker_match,
        transport_reachable=reachable,
        frozen_short_generation_observed=short_seen,
        stream_first_chunk_observed=stream_seen,
        interpretation_code=interpretation,
    )


def _usage_state(raw_usage: Any) -> tuple[UsageState, int | None, int | None, int | None]:
    if raw_usage is _MISSING or raw_usage is None:
        return "missing", None, None, None
    input_tokens = getattr(raw_usage, "prompt_tokens", _MISSING)
    output_tokens = getattr(raw_usage, "completion_tokens", _MISSING)
    if not _nonnegative_int(input_tokens) or not _nonnegative_int(output_tokens):
        return "invalid", None, None, None
    details = getattr(raw_usage, "prompt_tokens_details", None)
    cached = (
        details.get("cached_tokens", 0)
        if isinstance(details, Mapping)
        else getattr(details, "cached_tokens", 0)
    )
    cached = 0 if cached is None else cached
    if not _nonnegative_int(cached) or cached > input_tokens:
        return "invalid", None, None, None
    return "valid", input_tokens, output_tokens, cached


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


def _safe_model(value: Any) -> str | None:
    if isinstance(value, str) and _MODEL_PATTERN.fullmatch(value.strip()):
        return value.strip()
    return None


def _request_digest(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return hashlib.sha256(value.encode("utf-8")).hexdigest()
    return None


def _classify_error(error: Exception) -> tuple[SdkErrorClass, str]:
    name = type(error).__name__.lower()
    if isinstance(error, (openai.AuthenticationError,)) or "authentication" in name:
        return "authentication", "authentication_failed"
    if isinstance(error, openai.PermissionDeniedError) or "permission" in name:
        return "permission", "permission_denied"
    if isinstance(error, openai.RateLimitError) or "ratelimit" in name or "rate_limit" in name:
        return "rate_limit", "rate_limited"
    if isinstance(error, (openai.APITimeoutError, TimeoutError)) or "timeout" in name:
        return "timeout", "timeout"
    if isinstance(error, openai.APIConnectionError) or "connection" in name:
        return "connection", "connection_failed"
    if isinstance(error, openai.APIStatusError) or "status" in name or "http" in name:
        return "http_status", "http_status"
    return "sdk_error", "sdk_error"


def _close_stream(raw_stream: Any) -> None:
    close = getattr(raw_stream, "close", None)
    if callable(close):
        try:
            close()
        except Exception:
            pass


def _elapsed_ms(started: float) -> int:
    return max(0, round((time.monotonic() - started) * 1000))


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


def _assert_body_free(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).lower() in _FORBIDDEN_KEYS:
                raise ValueError("diagnostic payload contains a forbidden body field")
            _assert_body_free(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _assert_body_free(item)


def _inside_results(root: Path, value: str | Path) -> Path:
    path = (Path(value) if Path(value).is_absolute() else root / value).resolve()
    allowed = (root / "data/evaluation/results/provider_capabilities").resolve()
    if not path.is_relative_to(allowed) or path.suffix.lower() != ".json":
        raise ValueError("output must remain in provider capability results")
    return path


def _load_environment(path: Path | None) -> Mapping[str, str]:
    if path is not None:
        load_dotenv(path)
    return os.environ


def _read_head_sha(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    ).stdout.strip()


def _validate_sha(value: str, name: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise ValueError(f"{name} must be a full lowercase git SHA")


def _safe_code(value: Any) -> str | None:
    if isinstance(value, str) and re.fullmatch(
        r"[a-z][a-z0-9_.-]{0,95}", value.strip().lower()
    ):
        return value.strip().lower()
    return None


def _zero_sha() -> str:
    return "0" * 64


def _nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


__all__ = [
    "BASE_URL",
    "BASELINE_RESULT_SHA256",
    "CASE_ID",
    "DEFAULT_OUTPUT",
    "FrozenContextSnapshot",
    "MODEL",
    "MINIMAL_MAX_TOKENS",
    "SHORT_MAX_TOKENS",
    "STREAM_MAX_TOKENS",
    "TransportGenerationSplitReport",
    "run_transport_generation_split_diagnostic",
]


