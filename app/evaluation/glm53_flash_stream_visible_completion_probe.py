"""Bounded, body-free first-visible-content probes for GLM-5.3-Flash.

RQ-188 only observed the first stream chunk and RQ-189 compared synchronous
output budgets.  This evaluation-only probe follows a raw OpenAI-compatible
stream until the first non-blank visible ``delta.content`` (or a bounded
terminal/failure), then closes it immediately.  The two fixed variants differ
only in ``clear_thinking``; callers select one variant per process so the
maximum external-call budget is one.

No provider-neutral runtime, registered profile, candidate activation, or
product surface is changed here.  Reports retain states, counts, timings,
Usage numbers when actually observed, and digests only; bodies and credentials
are never written.
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
from pathlib import Path
from typing import Annotated, Any, Literal

import openai
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

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
    _load_frozen_context,
    _request_digest,
    _safe_model,
    _usage_state,
    _validate_context,
    _validate_sha,
    FrozenContextSnapshot,
)
from app.providers.config import load_zhipu_settings
from app.providers.models import ChatMessage, MessageRole
from app.providers.zhipu_profiles import ZHIPU_GLM53_FLASH_MODEL


PROVIDER_ID = "zhipu"
MODEL = ZHIPU_GLM53_FLASH_MODEL
BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"
SCHEMA_VERSION = "1.0"
EXPERIMENT_NAME = "g53-10-stream-visible-completion-v1"
DEFAULT_OUTPUT = Path(
    "data/evaluation/results/provider_capabilities/"
    "zhipu_glm53_flash_stream_visible_completion_rq190_v1.json"
)
MAX_TOKENS = 2048
REQUEST_TIMEOUT_S = 45.0
CLIENT_TIMEOUT_S = 50.0
MAX_REAL_CALLS = 1
MAX_VARIANTS = 2
MAX_CHUNKS = 8192
MAX_OBSERVED_TOKENS = 12_000
PARENT_EXPERIMENT_ID = "2c8d83a95bd579e483237eeb31d1d5e447d1d95c4fbf2fa0bf9936c8dc7dc674"
PARENT_RESULT_SHA256 = "1e001b49370f734404bc56896610d73d94057203aebf8de172d54787728e7c32"

ProbeVariant = Literal[
    "frozen_low_2048_stream_clear_true",
    "frozen_low_2048_stream_clear_false",
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
StopReason = Literal[
    "visible_content_before_terminal",
    "terminal_without_visible_content",
    "stream_end_without_visible_content",
    "read_timeout",
    "malformed_chunk",
    "chunk_limit",
    "create_error",
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
_STOP_CODES = frozenset({"authentication_failed", "permission_denied", "rate_limited"})


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class StreamProbeRequestSummary(_FrozenModel):
    ordinal: int = Field(ge=1, le=MAX_VARIANTS)
    variant: ProbeVariant
    message_count: int = Field(ge=1, le=128)
    message_roles: tuple[str, ...]
    message_shape_sha256: SafeSha
    max_tokens: Literal[MAX_TOKENS] = MAX_TOKENS
    timeout_s: float = Field(gt=0, le=REQUEST_TIMEOUT_S)
    stream: Literal[True] = True
    temperature: float = Field(ge=0, le=2)
    top_p: float = Field(ge=0, le=1)
    thinking_type: Literal["enabled"] = "enabled"
    reasoning_effort: Literal["low"] = "low"
    clear_thinking: bool


class StreamProbeObservation(_FrozenModel):
    ordinal: int = Field(ge=1, le=MAX_VARIANTS)
    variant: ProbeVariant
    status: ProbeStatus
    request: StreamProbeRequestSummary
    external_calls: Literal[0, 1]
    skip_reason: SafeCode | None = None
    response_received: bool = False
    stream_opened: bool = False
    first_chunk_observed: bool = False
    generation_observed: bool = False
    visible_content_observed: bool = False

    terminal_observed: bool = False
    stopped_after_visible_content: bool = False
    first_chunk_latency_ms: int | None = Field(default=None, ge=0)
    first_reasoning_chunk_latency_ms: int | None = Field(default=None, ge=0)
    first_visible_content_latency_ms: int | None = Field(default=None, ge=0)
    sdk_latency_ms: int = Field(ge=0)
    elapsed_ms: int = Field(ge=0)
    finish_reason: FinishReason | None = None
    stop_reason: StopReason | None = None
    content_state: FieldState = "not_observed"
    reasoning_state: FieldState = "not_observed"
    usage_state: UsageState = "missing"
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cached_input_tokens: int | None = Field(default=None, ge=0)
    chunk_count: int = Field(default=0, ge=0, le=MAX_CHUNKS)
    reasoning_chunk_count: int = Field(default=0, ge=0, le=MAX_CHUNKS)
    content_chunk_count: int = Field(default=0, ge=0, le=MAX_CHUNKS)
    empty_or_other_chunk_count: int = Field(default=0, ge=0, le=MAX_CHUNKS)
    first_chunk_shape: Literal[
        "not_observed",
        "choices_empty",
        "delta_content",
        "delta_reasoning",
        "delta_other",
        "malformed",
    ] = "not_observed"
    resolved_model: SafeModel | None = None
    request_id_sha256: SafeSha | None = None
    sdk_error_class: SdkErrorClass | None = None
    error_code: SafeCode | None = None
    error_stage: SafeCode | None = None

    @model_validator(mode="after")
    def validate_observation(self) -> "StreamProbeObservation":
        if self.external_calls == 0 and self.status != "skipped":
            raise ValueError("zero-call observations must be skipped")
        if self.status == "skipped":
            if self.skip_reason is None or self.external_calls != 0:
                raise ValueError("skipped observations need a reason and zero calls")
            if self.response_received or self.stream_opened or self.first_chunk_observed:
                raise ValueError("skipped observations cannot claim execution")
        elif self.external_calls != 1 or self.skip_reason is not None:
            raise ValueError("executed observations need exactly one call")
        if self.first_chunk_observed:
            if not self.stream_opened or self.first_chunk_latency_ms is None:
                raise ValueError("first chunk needs an opened stream and latency")
        if self.visible_content_observed:
            if not self.stopped_after_visible_content:
                raise ValueError("visible content must stop before terminal in this probe")
            if self.first_visible_content_latency_ms is None:
                raise ValueError("visible content needs a latency")
            if self.content_state != "non_empty":
                raise ValueError("visible content flag must match content state")
        if self.stopped_after_visible_content and not self.visible_content_observed:
            raise ValueError("stop-after-content requires visible content")
        if self.terminal_observed and self.stopped_after_visible_content:
            raise ValueError("terminal cannot be observed after early close")
        if self.status == "observed" and not (self.response_received or self.first_chunk_observed):
            raise ValueError("observed observations need a response or first chunk")
        if self.status == "failed" and self.error_code is None:
            raise ValueError("failed observations need an error code")
        if self.status != "failed" and self.error_code is not None:
            raise ValueError("only failed observations may carry an error code")
        if self.usage_state == "valid":
            if self.input_tokens is None or self.output_tokens is None:
                raise ValueError("valid usage needs input/output counts")
            if self.cached_input_tokens is None or self.cached_input_tokens > self.input_tokens:
                raise ValueError("valid usage needs a valid cache count")
        elif any(value is not None for value in (self.input_tokens, self.output_tokens, self.cached_input_tokens)):
            raise ValueError("unavailable usage cannot carry token counts")
        return self


class StreamProbeBudget(_FrozenModel):
    max_real_calls: Literal[MAX_REAL_CALLS] = MAX_REAL_CALLS
    max_observed_tokens: Literal[MAX_OBSERVED_TOKENS] = MAX_OBSERVED_TOKENS
    max_output_tokens_per_request: Literal[MAX_TOKENS] = MAX_TOKENS
    sdk_max_retries: Literal[0] = 0


class StreamProbeResources(_FrozenModel):
    calls_used: int = Field(ge=0, le=MAX_REAL_CALLS)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cached_input_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0, le=MAX_OBSERVED_TOKENS)
    latency_ms: int = Field(ge=0)
    within_token_budget: bool | None

    @model_validator(mode="after")
    def validate_resources(self) -> "StreamProbeResources":
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("resource total mismatch")
        if self.cached_input_tokens > self.input_tokens:
            raise ValueError("cached input cannot exceed input")
        if self.within_token_budget is not None and self.within_token_budget != (
            self.total_tokens <= MAX_OBSERVED_TOKENS
        ):
            raise ValueError("token budget status mismatch")
        return self


class StreamProbeVerdicts(_FrozenModel):
    transport_reachable: bool
    stream_first_chunk_observed: bool
    visible_content_observed: bool
    terminal_observed: bool
    clear_thinking_shape_observed: bool
    interpretation_code: SafeCode
    candidate_registered: Literal[False] = False
    production_admitted: Literal[False] = False


class StreamVisibleCompletionReport(_FrozenModel):
    schema_version: Literal[SCHEMA_VERSION] = SCHEMA_VERSION
    experiment_id: SafeSha
    experiment_name: Literal[EXPERIMENT_NAME] = EXPERIMENT_NAME
    evidence_class: Literal["dirty_worktree_real_api_observation"] = "dirty_worktree_real_api_observation"
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
    budget: StreamProbeBudget
    resources: StreamProbeResources
    calls_attempted: int = Field(ge=0, le=MAX_REAL_CALLS)
    cost_status: Literal["unknown"] = "unknown"
    run_timestamp_utc: datetime
    observations: tuple[StreamProbeObservation, ...]
    unsupported_boundaries: tuple[str, ...]
    verdicts: StreamProbeVerdicts

    @model_validator(mode="after")
    def validate_report(self) -> "StreamVisibleCompletionReport":
        expected = (
            "frozen_low_2048_stream_clear_true",
            "frozen_low_2048_stream_clear_false",
        )
        if tuple(row.variant for row in self.observations) != expected:
            raise ValueError("stream probe variants must use canonical order")
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
            raise ValueError("probe cannot admit or register candidate")
        return self


def run_stream_visible_completion_probe(
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
    probe_ordinal: int = 1,
) -> StreamVisibleCompletionReport:

    if confirm_real_call is not True:
        raise RuntimeError("stream-visible probe requires explicit confirmation")
    if isinstance(probe_ordinal, bool) or not isinstance(probe_ordinal, int):
        raise ValueError("probe_ordinal must be 1 or 2")
    if probe_ordinal not in (1, 2):
        raise ValueError("probe_ordinal must be 1 or 2")
    root = Path(repository_root).resolve()
    _validate_sha(implementation_sha, "implementation_sha")
    diagnostic_code_sha = diagnostic_code_sha or _read_head_sha(root)
    _validate_sha(diagnostic_code_sha, "diagnostic_code_sha")
    output_path = _inside_results(root, output)
    if output_path.exists():
        raise FileExistsError("stream-visible evidence is immutable")
    context = (context_loader or _load_frozen_context)(root)
    _validate_context(context)
    load_environment = environment_loader or _load_environment
    settings = load_zhipu_settings(load_environment(Path(env_file) if env_file else None))
    if settings.model != MODEL or settings.base_url.rstrip("/") != BASE_URL.rstrip("/"):
        raise ValueError("stream-visible probe settings must target GLM-5.3 Flash")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    source_loader = source_identity_loader or collect_source_identity
    source_identity = source_loader(root)
    client = client_factory(
        api_key=settings.api_key,
        base_url=settings.base_url,
        timeout=CLIENT_TIMEOUT_S,
        max_retries=0,
    )

    observations: list[StreamProbeObservation] = []
    for ordinal, clear_thinking in enumerate((True, False), start=1):
        request = _request_summary(
            ordinal=ordinal,
            variant=(
                "frozen_low_2048_stream_clear_true"
                if clear_thinking
                else "frozen_low_2048_stream_clear_false"
            ),
            messages=context.messages,
            clear_thinking=clear_thinking,
        )
        if ordinal != probe_ordinal:
            observations.append(_skipped_observation(request))
            continue
        payload = _request_payload(
            messages=context.messages,
            clear_thinking=clear_thinking,
        )
        observations.append(_run_stream_probe(client, request=request, payload=payload))

    source_identity_after = source_loader(root)
    resources = _resources(observations)
    timestamp = now()
    report = StreamVisibleCompletionReport(
        experiment_id=_experiment_id(source_identity, timestamp),
        implementation_sha=implementation_sha,
        diagnostic_code_sha=diagnostic_code_sha,
        input_plan_sha256=context.input_plan_sha256,
        prompt_context_snapshot_sha256=context.prompt_context_snapshot_sha256,
        source_identity=source_identity,
        source_identity_after=source_identity_after,
        source_identity_stable=source_identity == source_identity_after,
        budget=StreamProbeBudget(),
        resources=resources,
        calls_attempted=sum(row.external_calls for row in observations),
        run_timestamp_utc=timestamp,
        observations=tuple(observations),
        unsupported_boundaries=(
            "early close after first visible content usually leaves terminal Usage unobserved",
            "clear_thinking is co-observed on a single-turn request; causal cross-turn semantics remain untested",
            "no tool is supplied or executed; no response body or reasoning text is retained",
            "candidate remains unregistered; production security/deployment/compliance gates remain open",
        ),
        verdicts=_verdicts(observations),
    )
    _assert_body_free(report.model_dump())
    _write_immutable_report(output_path, report.model_dump_json(indent=2) + "\n")
    return report


def _request_summary(
    *,
    ordinal: int,
    variant: ProbeVariant,
    messages: tuple[ChatMessage, ...],
    clear_thinking: bool,
) -> StreamProbeRequestSummary:
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
    return StreamProbeRequestSummary(
        ordinal=ordinal,
        variant=variant,
        message_count=len(messages),
        message_roles=tuple(message.role.value for message in messages),
        message_shape_sha256=digest,
        timeout_s=REQUEST_TIMEOUT_S,
        temperature=1.0,
        top_p=0.95,
        clear_thinking=clear_thinking,
    )


def _request_payload(
    *,
    messages: tuple[ChatMessage, ...],
    clear_thinking: bool,
) -> dict[str, Any]:
    return {
        "model": MODEL,
        "messages": [
            {"role": message.role.value, "content": message.content}
            for message in messages
        ],
        "temperature": 1.0,
        "top_p": 0.95,
        "max_tokens": MAX_TOKENS,
        "timeout": REQUEST_TIMEOUT_S,
        "stream": True,
        "extra_body": {
            "thinking": {"type": "enabled", "clear_thinking": clear_thinking},
            "reasoning_effort": "low",
        },
    }


def _run_stream_probe(
    client: Any,
    *,
    request: StreamProbeRequestSummary,
    payload: Mapping[str, Any],
) -> StreamProbeObservation:
    started = time.monotonic()
    try:
        raw_stream = client.chat.completions.create(**dict(payload))
    except Exception as error:
        elapsed = _elapsed_ms(started)
        error_class, error_code = _classify_error(error)
        return _failed_observation(
            request,
            elapsed_ms=elapsed,
            sdk_error_class=error_class,
            error_code=error_code,
            error_stage="create",
            stop_reason="create_error",
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
            error_code="malformed_chunk",
            error_stage="iterator",
            stop_reason="malformed_chunk",
        )

    chunk_count = 0
    reasoning_chunk_count = 0
    content_chunk_count = 0
    empty_or_other_chunk_count = 0
    first_chunk_latency: int | None = None
    first_reasoning_latency: int | None = None
    first_visible_latency: int | None = None

    first_shape = "not_observed"
    content_state: FieldState = "not_observed"
    reasoning_state: FieldState = "not_observed"
    usage_state: UsageState = "missing"
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_input_tokens: int | None = None
    finish_reason: FinishReason | None = None
    resolved_model: str | None = None
    request_id_sha256: str | None = None
    generation_observed = False
    terminal_observed = False
    try:
        while chunk_count < MAX_CHUNKS:
            raw_chunk = next(iterator)
            chunk_count += 1
            elapsed = _elapsed_ms(started)
            if first_chunk_latency is None:
                first_chunk_latency = elapsed
            if elapsed > round(REQUEST_TIMEOUT_S * 1000):
                return _failed_observation(
                    request,
                    elapsed_ms=elapsed,
                    create_latency_ms=create_latency,
                    stream_opened=True,
                    first_chunk_observed=True,
                    generation_observed=generation_observed,
                    first_chunk_latency_ms=first_chunk_latency,
                    finish_reason=finish_reason,
                    content_state=content_state,
                    reasoning_state=reasoning_state,
                    usage_state=usage_state,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cached_input_tokens=cached_input_tokens,
                    chunk_count=chunk_count,
                    reasoning_chunk_count=reasoning_chunk_count,
                    content_chunk_count=content_chunk_count,
                    empty_or_other_chunk_count=empty_or_other_chunk_count,
                    first_chunk_shape=first_shape,
                    resolved_model=resolved_model,
                    request_id_sha256=request_id_sha256,
                    error_code="timeout",
                    error_stage="deadline",
                    stop_reason="read_timeout",
                )
            model = _safe_model(getattr(raw_chunk, "model", None))
            raw_model = getattr(raw_chunk, "model", None)
            if raw_model is not None and model is None:
                return _failed_observation(
                    request,
                    elapsed_ms=elapsed,
                    create_latency_ms=create_latency,
                    stream_opened=True,
                    first_chunk_observed=True,
                    generation_observed=generation_observed,
                    first_chunk_latency_ms=first_chunk_latency,
                    chunk_count=chunk_count,
                    reasoning_chunk_count=reasoning_chunk_count,
                    content_chunk_count=content_chunk_count,
                    empty_or_other_chunk_count=empty_or_other_chunk_count,
                    first_chunk_shape="malformed",
                    error_code="malformed_chunk",
                    error_stage="model",
                    stop_reason="malformed_chunk",
                )
            if model is not None:
                if resolved_model is not None and resolved_model != model:
                    return _failed_observation(
                        request,
                        elapsed_ms=elapsed,
                        create_latency_ms=create_latency,
                        stream_opened=True,
                        first_chunk_observed=True,
                        generation_observed=generation_observed,
                        first_chunk_latency_ms=first_chunk_latency,
                        chunk_count=chunk_count,
                        reasoning_chunk_count=reasoning_chunk_count,
                        content_chunk_count=content_chunk_count,
                        empty_or_other_chunk_count=empty_or_other_chunk_count,
                        first_chunk_shape=first_shape if first_shape != "not_observed" else "malformed",
                        resolved_model=resolved_model,
                        error_code="malformed_chunk",
                        error_stage="model_identity",
                        stop_reason="malformed_chunk",
                    )
                resolved_model = model
            raw_id = getattr(raw_chunk, "id", None)
            current_id = _request_digest(raw_id)
            if raw_id is not None and current_id is None:
                return _failed_observation(
                    request,
                    elapsed_ms=elapsed,
                    create_latency_ms=create_latency,
                    stream_opened=True,
                    first_chunk_observed=True,
                    generation_observed=generation_observed,
                    first_chunk_latency_ms=first_chunk_latency,
                    chunk_count=chunk_count,
                    reasoning_chunk_count=reasoning_chunk_count,
                    content_chunk_count=content_chunk_count,
                    empty_or_other_chunk_count=empty_or_other_chunk_count,
                    first_chunk_shape="malformed",
                    error_code="malformed_chunk",
                    error_stage="request_identity",
                    stop_reason="malformed_chunk",
                )
            if current_id is not None:
                if request_id_sha256 is not None and request_id_sha256 != current_id:
                    return _failed_observation(
                        request,
                        elapsed_ms=elapsed,
                        create_latency_ms=create_latency,
                        stream_opened=True,
                        first_chunk_observed=True,
                        generation_observed=generation_observed,
                        first_chunk_latency_ms=first_chunk_latency,
                        chunk_count=chunk_count,
                        reasoning_chunk_count=reasoning_chunk_count,
                        content_chunk_count=content_chunk_count,
                        empty_or_other_chunk_count=empty_or_other_chunk_count,
                        first_chunk_shape=first_shape if first_shape != "not_observed" else "malformed",
                        resolved_model=resolved_model,
                        request_id_sha256=request_id_sha256,
                        error_code="malformed_chunk",
                        error_stage="request_identity",
                        stop_reason="malformed_chunk",
                    )
                request_id_sha256 = current_id
            usage = getattr(raw_chunk, "usage", _MISSING)
            chunk_usage, chunk_input, chunk_output, chunk_cached = _usage_state(usage)
            if chunk_usage == "invalid":
                return _failed_observation(
                    request,
                    elapsed_ms=elapsed,
                    create_latency_ms=create_latency,
                    stream_opened=True,
                    first_chunk_observed=True,
                    generation_observed=generation_observed,
                    first_chunk_latency_ms=first_chunk_latency,
                    chunk_count=chunk_count,
                    reasoning_chunk_count=reasoning_chunk_count,
                    content_chunk_count=content_chunk_count,
                    empty_or_other_chunk_count=empty_or_other_chunk_count,
                    first_chunk_shape=first_shape if first_shape != "not_observed" else "malformed",
                    usage_state="invalid",
                    error_code="malformed_chunk",
                    error_stage="usage",
                    stop_reason="malformed_chunk",
                )
            if chunk_usage == "valid":
                usage_state = "valid"
                input_tokens, output_tokens, cached_input_tokens = (
                    chunk_input,
                    chunk_output,
                    chunk_cached,
                )
            choices = getattr(raw_chunk, "choices", _MISSING)
            if not isinstance(choices, (list, tuple)):
                return _failed_observation(
                    request,
                    elapsed_ms=elapsed,
                    create_latency_ms=create_latency,
                    stream_opened=True,
                    first_chunk_observed=True,
                    generation_observed=generation_observed,
                    first_chunk_latency_ms=first_chunk_latency,
                    chunk_count=chunk_count,
                    reasoning_chunk_count=reasoning_chunk_count,
                    content_chunk_count=content_chunk_count,
                    empty_or_other_chunk_count=empty_or_other_chunk_count,
                    first_chunk_shape="malformed",
                    usage_state=usage_state,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cached_input_tokens=cached_input_tokens,
                    resolved_model=resolved_model,
                    request_id_sha256=request_id_sha256,
                    error_code="malformed_chunk",
                    error_stage="choices",

                    stop_reason="malformed_chunk",
                )
            if not choices:
                if first_shape == "not_observed":
                    first_shape = "choices_empty"
                empty_or_other_chunk_count += 1
                continue
            if len(choices) != 1:
                return _failed_observation(
                    request,
                    elapsed_ms=elapsed,
                    create_latency_ms=create_latency,
                    stream_opened=True,
                    first_chunk_observed=True,
                    generation_observed=generation_observed,
                    first_chunk_latency_ms=first_chunk_latency,
                    chunk_count=chunk_count,
                    reasoning_chunk_count=reasoning_chunk_count,
                    content_chunk_count=content_chunk_count,
                    empty_or_other_chunk_count=empty_or_other_chunk_count,
                    first_chunk_shape="malformed",
                    usage_state=usage_state,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cached_input_tokens=cached_input_tokens,
                    resolved_model=resolved_model,
                    request_id_sha256=request_id_sha256,
                    error_code="malformed_chunk",
                    error_stage="choices",
                    stop_reason="malformed_chunk",
                )
            choice = choices[0]
            raw_finish = getattr(choice, "finish_reason", None)
            if raw_finish is not None:
                finish_reason = _finish_reason(raw_finish)
                if finish_reason == "unknown":
                    return _failed_observation(
                        request,
                        elapsed_ms=elapsed,
                        create_latency_ms=create_latency,
                        stream_opened=True,
                        first_chunk_observed=True,
                        generation_observed=generation_observed,
                        first_chunk_latency_ms=first_chunk_latency,
                        chunk_count=chunk_count,
                        reasoning_chunk_count=reasoning_chunk_count,
                        content_chunk_count=content_chunk_count,
                        empty_or_other_chunk_count=empty_or_other_chunk_count,
                        first_chunk_shape="malformed",
                        finish_reason="unknown",
                        usage_state=usage_state,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        cached_input_tokens=cached_input_tokens,
                        resolved_model=resolved_model,
                        request_id_sha256=request_id_sha256,
                        error_code="malformed_chunk",
                        error_stage="finish_reason",
                        stop_reason="malformed_chunk",
                    )
                terminal_observed = True
            delta = getattr(choice, "delta", _MISSING)
            if delta is _MISSING or delta is None:
                return _failed_observation(
                    request,
                    elapsed_ms=elapsed,
                    create_latency_ms=create_latency,
                    stream_opened=True,
                    first_chunk_observed=True,
                    generation_observed=generation_observed,
                    first_chunk_latency_ms=first_chunk_latency,
                    chunk_count=chunk_count,
                    reasoning_chunk_count=reasoning_chunk_count,
                    content_chunk_count=content_chunk_count,
                    empty_or_other_chunk_count=empty_or_other_chunk_count,
                    first_chunk_shape="malformed",
                    finish_reason=finish_reason,
                    usage_state=usage_state,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cached_input_tokens=cached_input_tokens,
                    resolved_model=resolved_model,
                    request_id_sha256=request_id_sha256,
                    error_code="malformed_chunk",
                    error_stage="delta",
                    stop_reason="malformed_chunk",
                )
            raw_content = getattr(delta, "content", _MISSING)
            raw_reasoning = getattr(delta, "reasoning_content", _MISSING)
            if raw_content is not _MISSING and raw_content is not None and not isinstance(raw_content, str):
                return _failed_observation(
                    request,
                    elapsed_ms=elapsed,
                    create_latency_ms=create_latency,
                    stream_opened=True,
                    first_chunk_observed=True,
                    generation_observed=generation_observed,
                    first_chunk_latency_ms=first_chunk_latency,
                    chunk_count=chunk_count,
                    reasoning_chunk_count=reasoning_chunk_count,
                    content_chunk_count=content_chunk_count,
                    empty_or_other_chunk_count=empty_or_other_chunk_count,
                    first_chunk_shape="malformed",
                    finish_reason=finish_reason,
                    usage_state=usage_state,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cached_input_tokens=cached_input_tokens,
                    resolved_model=resolved_model,
                    request_id_sha256=request_id_sha256,
                    error_code="malformed_chunk",
                    error_stage="content",
                    stop_reason="malformed_chunk",
                )
            if raw_reasoning is not _MISSING and raw_reasoning is not None and not isinstance(raw_reasoning, str):
                return _failed_observation(
                    request,
                    elapsed_ms=elapsed,
                    create_latency_ms=create_latency,
                    stream_opened=True,
                    first_chunk_observed=True,
                    generation_observed=generation_observed,
                    first_chunk_latency_ms=first_chunk_latency,
                    chunk_count=chunk_count,
                    reasoning_chunk_count=reasoning_chunk_count,
                    content_chunk_count=content_chunk_count,
                    empty_or_other_chunk_count=empty_or_other_chunk_count,
                    first_chunk_shape="malformed",
                    finish_reason=finish_reason,
                    usage_state=usage_state,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cached_input_tokens=cached_input_tokens,
                    resolved_model=resolved_model,
                    request_id_sha256=request_id_sha256,
                    error_code="malformed_chunk",
                    error_stage="reasoning",
                    stop_reason="malformed_chunk",
                )
            content_state = _merge_field_state(content_state, _field_state(raw_content))
            reasoning_state = _merge_field_state(reasoning_state, _field_state(raw_reasoning))
            visible = isinstance(raw_content, str) and bool(raw_content.strip())
            reasoning = isinstance(raw_reasoning, str) and bool(raw_reasoning.strip())
            if first_shape == "not_observed":
                if visible:
                    first_shape = "delta_content"
                elif reasoning:
                    first_shape = "delta_reasoning"
                else:
                    first_shape = "delta_other"
            if visible:
                content_chunk_count += 1
                generation_observed = True
                if first_visible_latency is None:
                    first_visible_latency = elapsed
                _close_stream(raw_stream)
                return StreamProbeObservation(
                    ordinal=request.ordinal,
                    variant=request.variant,
                    status="observed",
                    request=request,
                    external_calls=1,
                    response_received=True,
                    stream_opened=True,
                    first_chunk_observed=True,
                    generation_observed=True,
                    visible_content_observed=True,
                    terminal_observed=False,
                    stopped_after_visible_content=True,
                    first_chunk_latency_ms=first_chunk_latency,
                    first_reasoning_chunk_latency_ms=first_reasoning_latency,
                    first_visible_content_latency_ms=first_visible_latency,
                    sdk_latency_ms=elapsed,
                    elapsed_ms=elapsed,
                    finish_reason=finish_reason,
                    stop_reason="visible_content_before_terminal",
                    content_state=content_state,
                    reasoning_state=reasoning_state,
                    usage_state=usage_state,
                    input_tokens=input_tokens,

                    output_tokens=output_tokens,
                    cached_input_tokens=cached_input_tokens,
                    chunk_count=chunk_count,
                    reasoning_chunk_count=reasoning_chunk_count,
                    content_chunk_count=content_chunk_count,
                    empty_or_other_chunk_count=empty_or_other_chunk_count,
                    first_chunk_shape=first_shape,
                    resolved_model=resolved_model,
                    request_id_sha256=request_id_sha256,
                )
            if reasoning:
                reasoning_chunk_count += 1
                generation_observed = True
                if first_reasoning_latency is None:
                    first_reasoning_latency = elapsed
            else:
                empty_or_other_chunk_count += 1
            if terminal_observed:
                _close_stream(raw_stream)
                return StreamProbeObservation(
                    ordinal=request.ordinal,
                    variant=request.variant,
                    status="observed",
                    request=request,
                    external_calls=1,
                    response_received=True,
                    stream_opened=True,
                    first_chunk_observed=True,
                    generation_observed=generation_observed,
                    visible_content_observed=False,
                    terminal_observed=True,
                    first_chunk_latency_ms=first_chunk_latency,
                    first_reasoning_chunk_latency_ms=first_reasoning_latency,
                    first_visible_content_latency_ms=None,
                    sdk_latency_ms=elapsed,
                    elapsed_ms=elapsed,
                    finish_reason=finish_reason,
                    stop_reason="terminal_without_visible_content",
                    content_state=content_state,
                    reasoning_state=reasoning_state,
                    usage_state=usage_state,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cached_input_tokens=cached_input_tokens,
                    chunk_count=chunk_count,
                    reasoning_chunk_count=reasoning_chunk_count,
                    content_chunk_count=content_chunk_count,
                    empty_or_other_chunk_count=empty_or_other_chunk_count,
                    first_chunk_shape=first_shape,
                    resolved_model=resolved_model,
                    request_id_sha256=request_id_sha256,
                )
        _close_stream(raw_stream)
        elapsed = _elapsed_ms(started)
        return _failed_observation(
            request,
            elapsed_ms=elapsed,
            create_latency_ms=create_latency,
            stream_opened=True,
            first_chunk_observed=chunk_count > 0,
            generation_observed=generation_observed,
            first_chunk_latency_ms=first_chunk_latency,
            finish_reason=finish_reason,
            content_state=content_state,
            reasoning_state=reasoning_state,
            usage_state=usage_state,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=cached_input_tokens,
            chunk_count=chunk_count,
            reasoning_chunk_count=reasoning_chunk_count,
            content_chunk_count=content_chunk_count,
            empty_or_other_chunk_count=empty_or_other_chunk_count,
            first_chunk_shape=first_shape,
            resolved_model=resolved_model,
            request_id_sha256=request_id_sha256,
            error_code="chunk_limit",
            error_stage="read",
            stop_reason="chunk_limit",
        )
    except StopIteration:
        elapsed = _elapsed_ms(started)
        _close_stream(raw_stream)
        return StreamProbeObservation(
            ordinal=request.ordinal,
            variant=request.variant,
            status="observed",
            request=request,
            external_calls=1,
            response_received=True,
            stream_opened=True,
            first_chunk_observed=chunk_count > 0,
            generation_observed=generation_observed,
            visible_content_observed=False,
            terminal_observed=terminal_observed,
            first_chunk_latency_ms=first_chunk_latency,
            first_reasoning_chunk_latency_ms=first_reasoning_latency,
            sdk_latency_ms=elapsed,
            elapsed_ms=elapsed,
            finish_reason=finish_reason,
            stop_reason="stream_end_without_visible_content",
            content_state=content_state,
            reasoning_state=reasoning_state,
            usage_state=usage_state,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=cached_input_tokens,
            chunk_count=chunk_count,
            reasoning_chunk_count=reasoning_chunk_count,
            content_chunk_count=content_chunk_count,
            empty_or_other_chunk_count=empty_or_other_chunk_count,
            first_chunk_shape=first_shape,
            resolved_model=resolved_model,
            request_id_sha256=request_id_sha256,
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
            first_chunk_observed=chunk_count > 0,
            generation_observed=generation_observed,
            first_chunk_latency_ms=first_chunk_latency,
            finish_reason=finish_reason,
            content_state=content_state,
            reasoning_state=reasoning_state,
            usage_state=usage_state,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=cached_input_tokens,
            chunk_count=chunk_count,
            reasoning_chunk_count=reasoning_chunk_count,
            content_chunk_count=content_chunk_count,
            empty_or_other_chunk_count=empty_or_other_chunk_count,
            first_chunk_shape=first_shape,
            resolved_model=resolved_model,
            request_id_sha256=request_id_sha256,
            sdk_error_class=error_class,
            error_code=error_code,
            error_stage="read",
            stop_reason=("read_timeout" if error_code == "timeout" else "create_error"),
        )
    finally:
        _close_stream(raw_stream)


def _failed_observation(
    request: StreamProbeRequestSummary,
    *,
    elapsed_ms: int,
    create_latency_ms: int | None = None,
    create_latency_ms_override: None = None,
    stream_opened: bool = False,
    first_chunk_observed: bool = False,
    generation_observed: bool = False,
    first_chunk_latency_ms: int | None = None,
    first_reasoning_chunk_latency_ms: int | None = None,
    first_visible_content_latency_ms: int | None = None,
    finish_reason: FinishReason | None = None,
    content_state: FieldState = "not_observed",
    reasoning_state: FieldState = "not_observed",
    usage_state: UsageState = "missing",
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    cached_input_tokens: int | None = None,
    chunk_count: int = 0,
    reasoning_chunk_count: int = 0,
    content_chunk_count: int = 0,
    empty_or_other_chunk_count: int = 0,
    first_chunk_shape: str = "not_observed",
    resolved_model: str | None = None,
    request_id_sha256: str | None = None,
    sdk_error_class: SdkErrorClass | None = None,
    error_code: str,
    error_stage: str,
    stop_reason: StopReason,

) -> StreamProbeObservation:
    del create_latency_ms_override
    return StreamProbeObservation(
        ordinal=request.ordinal,
        variant=request.variant,
        status="failed",
        request=request,
        external_calls=1,
        response_received=first_chunk_observed,
        stream_opened=stream_opened,
        first_chunk_observed=first_chunk_observed,
        generation_observed=generation_observed,
        first_chunk_latency_ms=first_chunk_latency_ms,
        first_reasoning_chunk_latency_ms=first_reasoning_chunk_latency_ms,
        first_visible_content_latency_ms=first_visible_content_latency_ms,
        sdk_latency_ms=max(0, elapsed_ms),
        elapsed_ms=max(0, elapsed_ms),
        finish_reason=finish_reason,
        stop_reason=stop_reason,
        content_state=content_state,
        reasoning_state=reasoning_state,
        usage_state=usage_state,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_input_tokens=cached_input_tokens,
        chunk_count=chunk_count,
        reasoning_chunk_count=reasoning_chunk_count,
        content_chunk_count=content_chunk_count,
        empty_or_other_chunk_count=empty_or_other_chunk_count,
        first_chunk_shape=first_chunk_shape,
        resolved_model=resolved_model,
        request_id_sha256=request_id_sha256,
        sdk_error_class=sdk_error_class,
        error_code=_safe_code(error_code) or "probe_failed",
        error_stage=_safe_code(error_stage) or "unknown",
    )


def _skipped_observation(request: StreamProbeRequestSummary) -> StreamProbeObservation:
    return StreamProbeObservation(
        ordinal=request.ordinal,
        variant=request.variant,
        status="skipped",
        request=request,
        external_calls=0,
        skip_reason="probe_selection_excluded",
        first_chunk_latency_ms=None,
        sdk_latency_ms=0,
        elapsed_ms=0,
    )


def _resources(observations: list[StreamProbeObservation]) -> StreamProbeResources:
    input_tokens = sum(row.input_tokens or 0 for row in observations)
    output_tokens = sum(row.output_tokens or 0 for row in observations)
    cached = sum(row.cached_input_tokens or 0 for row in observations)
    total = input_tokens + output_tokens
    usage_observed = any(row.usage_state == "valid" for row in observations)
    return StreamProbeResources(
        calls_used=sum(row.external_calls for row in observations),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_input_tokens=cached,
        total_tokens=total,
        latency_ms=sum(row.elapsed_ms for row in observations),
        within_token_budget=(total <= MAX_OBSERVED_TOKENS) if usage_observed else None,
    )


def _verdicts(observations: list[StreamProbeObservation]) -> StreamProbeVerdicts:
    executed = next((row for row in observations if row.external_calls == 1), None)
    if executed is None:
        return StreamProbeVerdicts(
            transport_reachable=False,
            stream_first_chunk_observed=False,
            visible_content_observed=False,
            terminal_observed=False,
            clear_thinking_shape_observed=False,
            interpretation_code="probe_not_executed",
        )
    if executed.visible_content_observed:
        interpretation = "stream_visible_content_before_terminal"
    elif executed.error_code == "timeout":
        interpretation = "stream_read_timeout"
    elif executed.terminal_observed:
        interpretation = "stream_terminal_without_visible_content"
    else:
        interpretation = "stream_observed_without_visible_content"
    return StreamProbeVerdicts(
        transport_reachable=executed.stream_opened,
        stream_first_chunk_observed=executed.first_chunk_observed,
        visible_content_observed=executed.visible_content_observed,
        terminal_observed=executed.terminal_observed,
        clear_thinking_shape_observed=executed.stream_opened,
        interpretation_code=interpretation,
    )


def _merge_field_state(current: FieldState, incoming: FieldState) -> FieldState:
    if incoming == "not_observed":
        return current
    rank = {
        "not_observed": 0,
        "missing": 1,
        "null": 2,
        "empty": 3,
        "non_string": 4,
        "non_empty": 5,
    }
    return incoming if rank[incoming] > rank[current] else current


def _load_environment(env_file: Path | None) -> Mapping[str, str]:
    if env_file is not None:
        load_dotenv(env_file, override=False)
    return os.environ


def _safe_code(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip().lower()
    return value if re.fullmatch(r"[a-z][a-z0-9_.-]{0,95}", value) else None


def _close_stream(raw_stream: Any) -> None:
    close = getattr(raw_stream, "close", None)
    if callable(close):
        try:
            close()
        except Exception:
            pass


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
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


__all__ = [
    "BASE_URL",
    "DEFAULT_OUTPUT",
    "FrozenContextSnapshot",
    "MAX_TOKENS",
    "MODEL",
    "StreamVisibleCompletionReport",
    "run_stream_visible_completion_probe",
]
