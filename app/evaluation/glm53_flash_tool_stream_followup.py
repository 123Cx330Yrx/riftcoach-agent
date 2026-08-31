"""One separately identified GLM-5.3-Flash tool-stream diagnostic.

The main G53-5 matrix deliberately uses a small per-request output cap.  This
module provides one *new* one-call observation with a larger cap so a length
truncation can be distinguished from a tool-stream protocol failure.  It is
vendor/adapter evidence only: no tool is executed and production admission is
always false.  Only allowlisted, body-free observations are persisted.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Annotated, Any, Literal

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.evaluation.provider_capability_gate import (
    ExternalCallBudget,
    ExternalCallBudgetExceeded,
)
from app.providers.errors import ProviderError, ProviderResponseError
from app.providers.models import ChatMessage, ChatRequest, MessageRole
from app.providers.zhipu import ZhipuProvider
from app.providers.zhipu_profiles import (
    ZHIPU_GLM53_FLASH_MODEL,
    ZHIPU_GLM53_FLASH_THINKING_PROFILE,
)

from .glm53_flash_capability_matrix import (
    MatrixSourceIdentity,
    _tool_spec,
    collect_source_identity,
    reserve_output,
)


FOLLOWUP_EXPERIMENT_NAME = "g53-5-fresh-flash-tool-stream-followup-v1"
FOLLOWUP_MAX_CALLS = 1
FOLLOWUP_MAX_OUTPUT_TOKENS = 2_048
FOLLOWUP_MAX_OBSERVED_TOKENS = 8_000
FOLLOWUP_CASE_ID = "F7_tool_stream_larger_cap_diagnostic"
FOLLOWUP_REQUEST_TIMEOUT_S = 30.0
FOLLOWUP_CLIENT_TIMEOUT_S = 90.0
PARENT_MATRIX_EXPERIMENT_ID = (
    "4e2d14f9e2b294ec2898b22a4275dbbd706c28ca7f3b061a655d1a613a7aaefb"
)
PARENT_MATRIX_RESULT_SHA256 = (
    "bfff564cf4c6e7b2dd05f88542fd7a872d1565442b6d35c795ec6892cc84be0c"
)

NonBlankText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Sha256Text = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
FieldState = Literal["not_observed", "missing", "empty", "non_empty"]


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FollowupBudget(_FrozenModel):
    max_real_calls: Literal[1] = FOLLOWUP_MAX_CALLS
    max_observed_tokens: Literal[8000] = FOLLOWUP_MAX_OBSERVED_TOKENS
    max_output_tokens_per_request: Literal[2048] = FOLLOWUP_MAX_OUTPUT_TOKENS
    sdk_max_retries: Literal[0] = 0


class FollowupCaseResult(_FrozenModel):
    case_id: Literal[FOLLOWUP_CASE_ID] = FOLLOWUP_CASE_ID
    capability: Literal["tool_streaming"] = "tool_streaming"
    status: Literal["passed", "failed"]
    error_code: NonBlankText | None = None
    external_calls: Literal[0, 1]
    response_count: int = Field(ge=0, le=1)
    response_received: bool = False
    normalized_response_state: Literal["complete", "incomplete", "not_observed"] = (
        "not_observed"
    )
    usage_state: Literal["observed", "unavailable"] = "unavailable"
    finish_reason: NonBlankText | None = None
    tool_call_count: int = Field(ge=0)
    tool_execution_count: Literal[0] = 0
    tool_order_sha256: Sha256Text | None = None
    tool_arguments_sha256: Sha256Text | None = None
    output_sha256: Sha256Text | None = None
    reasoning_state: FieldState = "not_observed"
    reasoning_sha256: Sha256Text | None = None
    request_id_sha256: Sha256Text | None = None
    resolved_model: NonBlankText | None = None
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cached_input_tokens: int = Field(ge=0)
    latency_ms: int = Field(ge=0)
    chunk_count: int = Field(ge=0)
    content_chunk_count: int = Field(ge=0)
    reasoning_chunk_count: int = Field(ge=0)
    tool_call_chunk_count: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_case(self) -> "FollowupCaseResult":
        if self.cached_input_tokens > self.input_tokens:
            raise ValueError("cached input cannot exceed input")
        if self.reasoning_state == "non_empty" and self.reasoning_sha256 is None:
            raise ValueError("non-empty reasoning needs a digest")
        if self.reasoning_state != "non_empty" and self.reasoning_sha256 is not None:
            raise ValueError("reasoning digest requires non-empty reasoning")
        if self.status == "passed":
            if self.error_code is not None or self.output_sha256 is None:
                raise ValueError("passed follow-up needs only a digest")
            if self.external_calls != 1 or self.response_count != 1:
                raise ValueError("passed follow-up needs one completed response")
            if self.response_received is not True:
                raise ValueError("passed follow-up needs a received response")
            if self.normalized_response_state != "complete" or self.usage_state != "observed":
                raise ValueError("passed follow-up needs complete observed usage")
            if self.finish_reason != "tool_calls" or self.tool_call_count < 1:
                raise ValueError("passed follow-up needs a tool-call finish")
            if self.tool_order_sha256 is None or self.tool_arguments_sha256 is None:
                raise ValueError("passed follow-up needs tool digests")
            if self.resolved_model is None or self.request_id_sha256 is None:
                raise ValueError("passed follow-up needs model and request identity")
        else:
            if self.error_code is None or self.output_sha256 is not None:
                raise ValueError("failed follow-up needs an error and no digest")
            if self.usage_state != "unavailable":
                if self.normalized_response_state != "complete":
                    raise ValueError("failed incomplete follow-up must mark usage unavailable")
            if self.response_received and self.normalized_response_state != "complete":
                raise ValueError("received response must be complete")
        if self.tool_execution_count != 0:
            raise ValueError("vendor diagnostic cannot execute tools")
        return self


class FollowupResources(_FrozenModel):
    calls_used: Literal[0, 1]
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cached_input_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    within_token_budget: bool
    latency_ms: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_resources(self) -> "FollowupResources":
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("resource total mismatch")
        if self.cached_input_tokens > self.input_tokens:
            raise ValueError("cached input cannot exceed input")
        if self.within_token_budget != (
            self.total_tokens <= FOLLOWUP_MAX_OBSERVED_TOKENS
        ):
            raise ValueError("token budget status mismatch")
        return self


class FollowupVerdict(_FrozenModel):
    tool_stream_observed: bool
    production_admitted: Literal[False] = False


class ToolStreamFollowupReport(_FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    experiment_id: Sha256Text
    experiment_name: Literal[FOLLOWUP_EXPERIMENT_NAME] = FOLLOWUP_EXPERIMENT_NAME
    evidence_class: Literal["dirty_worktree_real_api_observation"] = (
        "dirty_worktree_real_api_observation"
    )
    provider_id: Literal["zhipu"] = "zhipu"
    requested_model: Literal[ZHIPU_GLM53_FLASH_MODEL] = ZHIPU_GLM53_FLASH_MODEL
    base_url: NonBlankText
    thinking_profile_id: Literal[
        ZHIPU_GLM53_FLASH_THINKING_PROFILE.profile_id
    ] = ZHIPU_GLM53_FLASH_THINKING_PROFILE.profile_id
    parent_matrix_experiment_id: Literal[PARENT_MATRIX_EXPERIMENT_ID] = (
        PARENT_MATRIX_EXPERIMENT_ID
    )
    parent_matrix_result_sha256: Literal[PARENT_MATRIX_RESULT_SHA256] = (
        PARENT_MATRIX_RESULT_SHA256
    )
    source_identity: MatrixSourceIdentity
    source_identity_after: MatrixSourceIdentity
    source_identity_stable: bool
    observation_scope: Literal["vendor_raw_transport_only"] = (
        "vendor_raw_transport_only"
    )
    request_contract_sha256: Sha256Text
    prompt_sha256: Sha256Text
    tool_schema_sha256: Sha256Text
    thinking_type: Literal["enabled"] = "enabled"
    reasoning_effort: Literal["max"] = "max"
    clear_thinking: Literal[False] = False
    request_timeout_s: Literal[30.0] = FOLLOWUP_REQUEST_TIMEOUT_S
    client_timeout_s: Literal[90.0] = FOLLOWUP_CLIENT_TIMEOUT_S
    public_ci_confirmed: Literal[False] = False
    domain_admitted: Literal[False] = False
    cost_status: Literal["unknown"] = "unknown"
    write_once: Literal[True] = True
    budget: FollowupBudget
    resources: FollowupResources
    run_timestamp_utc: datetime
    case: FollowupCaseResult
    unsupported_boundaries: tuple[NonBlankText, ...]
    verdicts: FollowupVerdict

    @model_validator(mode="after")
    def validate_report(self) -> "ToolStreamFollowupReport":
        if self.resources.calls_used != self.case.external_calls:
            raise ValueError("resource call mismatch")
        if self.resources.input_tokens != self.case.input_tokens:
            raise ValueError("resource input mismatch")
        if self.resources.output_tokens != self.case.output_tokens:
            raise ValueError("resource output mismatch")
        if self.resources.cached_input_tokens != self.case.cached_input_tokens:
            raise ValueError("resource cache mismatch")
        if self.resources.latency_ms != self.case.latency_ms:
            raise ValueError("resource latency mismatch")
        if self.case.status == "passed" and not self.resources.within_token_budget:
            raise ValueError("passed follow-up cannot exceed token budget")
        if self.verdicts.production_admitted is not False:
            raise ValueError("follow-up cannot admit production")
        if self.verdicts.tool_stream_observed != (self.case.status == "passed"):
            raise ValueError("tool-stream verdict mismatch")
        return self


def _sha(value: Any) -> str:
    if isinstance(value, str):
        payload = value.encode("utf-8")
    else:
        payload = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _experiment_id(identity: MatrixSourceIdentity, now: datetime) -> str:
    return _sha(
        {
            "name": FOLLOWUP_EXPERIMENT_NAME,
            "head": identity.head_sha,
            "patch": identity.worktree_patch_sha256,
            "timestamp": now.isoformat(),
        }
    )


class _CountingCompletions:
    """Count transport create invocations without retaining request bodies."""

    def __init__(self, delegate: Any) -> None:
        self._delegate = delegate
        self.create_calls = 0

    def create(self, **kwargs: Any) -> Any:
        self.create_calls += 1
        return self._delegate.create(**kwargs)


class _CountingClient:
    def __init__(self, delegate: Any) -> None:
        self.completions = _CountingCompletions(delegate.chat.completions)
        self.chat = SimpleNamespace(completions=self.completions)


def _error_code(error: Exception) -> str:
    if isinstance(error, ProviderError):
        return error.code
    return "followup_case_error"


def _failed_case(code: str, *, latency_ms: int, calls: int = 1) -> FollowupCaseResult:
    return FollowupCaseResult(
        status="failed",
        error_code=code,
        external_calls=0 if calls == 0 else 1,
        response_count=0,
        response_received=False,
        normalized_response_state=(
            "incomplete" if code == "incomplete_chat_response" else "not_observed"
        ),
        usage_state="unavailable",
        tool_call_count=0,
        input_tokens=0,
        output_tokens=0,
        cached_input_tokens=0,
        latency_ms=max(0, latency_ms),
        chunk_count=0,
        content_chunk_count=0,
        reasoning_chunk_count=0,
        tool_call_chunk_count=0,
    )


def _stream_case(
    result: Any,
    *,
    status: Literal["passed", "failed"],
    error_code: str | None = None,
    output_digest: bool = False,
    latency_ms: int,
) -> FollowupCaseResult:
    """Project a complete adapter response to the allowlisted case schema."""

    response = result.response
    names = tuple(call.name for call in response.tool_calls)
    arguments = tuple(call.arguments for call in response.tool_calls)
    reasoning = response.reasoning_content
    return FollowupCaseResult(
        status=status,
        error_code=error_code,
        external_calls=1,
        response_count=1,
        response_received=True,
        normalized_response_state="complete",
        usage_state="observed",
        finish_reason=response.finish_reason,
        tool_call_count=len(response.tool_calls),
        tool_order_sha256=_sha(names) if names else None,
        tool_arguments_sha256=_sha(arguments) if arguments else None,
        output_sha256=(
            _sha({"finish_reason": response.finish_reason, "tool_count": len(names)})
            if output_digest
            else None
        ),
        reasoning_state=("non_empty" if reasoning else "missing"),
        reasoning_sha256=_sha(reasoning) if reasoning else None,
        request_id_sha256=_sha(response.request_id) if response.request_id else None,
        resolved_model=response.model,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        cached_input_tokens=response.usage.cached_input_tokens,
        latency_ms=max(0, latency_ms),
        chunk_count=result.chunk_count,
        content_chunk_count=result.content_chunk_count,
        reasoning_chunk_count=result.reasoning_chunk_count,
        tool_call_chunk_count=result.tool_call_chunk_count,
    )


def run_real_tool_stream_followup(
    *,
    repository_root: Path,
    output: Path,
    api_key: str,
    base_url: str,
    model: str,
) -> ToolStreamFollowupReport:
    """Make exactly one new call and write a body-free, non-overwriting report."""

    if not api_key.strip():
        raise ValueError("missing_api_key")
    if base_url.rstrip("/") != "https://open.bigmodel.cn/api/paas/v4":
        raise ValueError("invalid_base_url")
    if model != ZHIPU_GLM53_FLASH_MODEL:
        raise ValueError("invalid_model")
    allowed = (repository_root / "data/evaluation/results/provider_capabilities").resolve()
    resolved_output = output.resolve()
    if not resolved_output.is_relative_to(allowed):
        raise ValueError("output must remain inside provider capability results")
    reserve_output(output)
    identity = collect_source_identity(repository_root)
    started = time.monotonic()
    call_budget = ExternalCallBudget(max_calls=FOLLOWUP_MAX_CALLS)
    case: FollowupCaseResult
    request_text = "必须调用 matrix.lookup_alpha，不要直接回答。"
    request_schema = _tool_spec("matrix.lookup_alpha")
    transport_client: _CountingClient | None = None
    try:
        raw_client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=FOLLOWUP_CLIENT_TIMEOUT_S,
            max_retries=0,
        )
        transport_client = _CountingClient(raw_client)
        provider = ZhipuProvider(
            client=transport_client,
            model=model,
            profile=ZHIPU_GLM53_FLASH_THINKING_PROFILE,
        )
        result = call_budget.run(
            provider.chat_stream,
            ChatRequest(
                messages=(
                    ChatMessage(
                        MessageRole.USER,
                        request_text,
                    ),
                ),
                tools=(request_schema,),
                temperature=1.0,
                top_p=0.95,
                max_tokens=FOLLOWUP_MAX_OUTPUT_TOKENS,
                timeout_s=FOLLOWUP_REQUEST_TIMEOUT_S,
            ),
            tool_stream=True,
        )
        response = result.response
        names = tuple(call.name for call in response.tool_calls)
        mismatch_code = None
        if response.model != model:
            mismatch_code = "resolved_model_mismatch"
        elif not isinstance(response.request_id, str) or not response.request_id.strip():
            mismatch_code = "missing_request_id"
        elif response.content is not None:
            mismatch_code = "tool_stream_contract_mismatch"
        elif response.finish_reason != "tool_calls" or names != ("matrix.lookup_alpha",):
            mismatch_code = "tool_stream_contract_mismatch"
        elif not isinstance(response.tool_calls[0].arguments, dict):
            mismatch_code = "invalid_tool_arguments"
        over_budget = response.usage.total_tokens > FOLLOWUP_MAX_OBSERVED_TOKENS
        if mismatch_code is not None:
            case = _stream_case(
                result,
                status="failed",
                error_code=mismatch_code,
                latency_ms=round((time.monotonic() - started) * 1000),
            )
        elif over_budget:
            case = _stream_case(
                result,
                status="failed",
                error_code="observed_token_budget_exceeded",
                latency_ms=round((time.monotonic() - started) * 1000),
            )
        else:
            case = _stream_case(
                result,
                status="passed",
                output_digest=True,
                latency_ms=round((time.monotonic() - started) * 1000),
            )
        if transport_client is None or transport_client.completions.create_calls != 1:
            raise ProviderResponseError(
                provider="zhipu",
                code="unexpected_transport_call_count",
            )
    except ExternalCallBudgetExceeded:
        case = _failed_case(
            "external_call_budget_exhausted",
            latency_ms=round((time.monotonic() - started) * 1000),
            calls=call_budget.calls_used,
        )
    except ProviderError as error:
        case = _failed_case(
            error.code,
            latency_ms=round((time.monotonic() - started) * 1000),
            calls=call_budget.calls_used,
        )
    except Exception as error:
        case = _failed_case(
            _error_code(error),
            latency_ms=round((time.monotonic() - started) * 1000),
            calls=call_budget.calls_used,
        )
    identity_after = collect_source_identity(repository_root)
    source_identity_stable = identity == identity_after
    if not source_identity_stable and case.status == "passed":
        case = _failed_case(
            "worktree_changed_during_test",
            latency_ms=case.latency_ms,
            calls=call_budget.calls_used,
        )
    resources = FollowupResources(
        calls_used=case.external_calls,
        input_tokens=case.input_tokens,
        output_tokens=case.output_tokens,
        cached_input_tokens=case.cached_input_tokens,
        total_tokens=case.input_tokens + case.output_tokens,
        within_token_budget=(
            case.input_tokens + case.output_tokens
            <= FOLLOWUP_MAX_OBSERVED_TOKENS
        ),
        latency_ms=case.latency_ms,
    )
    report = ToolStreamFollowupReport(
        experiment_id=_experiment_id(identity, datetime.now(timezone.utc)),
        base_url=base_url,
        parent_matrix_experiment_id=PARENT_MATRIX_EXPERIMENT_ID,
        parent_matrix_result_sha256=PARENT_MATRIX_RESULT_SHA256,
        source_identity=identity,
        source_identity_after=identity_after,
        source_identity_stable=source_identity_stable,
        request_contract_sha256=_sha(
            {
                "stream": True,
                "tool_stream": True,
                "tool_choice": "auto",
                "max_tokens": FOLLOWUP_MAX_OUTPUT_TOKENS,
                "temperature": 1.0,
                "top_p": 0.95,
                "timeout_s": FOLLOWUP_REQUEST_TIMEOUT_S,
                "client_timeout_s": FOLLOWUP_CLIENT_TIMEOUT_S,
                "sdk_max_retries": 0,
                "max_real_calls": FOLLOWUP_MAX_CALLS,
            }
        ),
        prompt_sha256=_sha(request_text),
        tool_schema_sha256=_sha(
            {
                "name": request_schema.name,
                "description": request_schema.description,
                "input_schema": request_schema.input_schema,
            }
        ),
        budget=FollowupBudget(),
        resources=resources,
        run_timestamp_utc=datetime.now(timezone.utc),
        case=case,
        unsupported_boundaries=(
            "vendor/adapter observation only; no provider-neutral streaming contract",
            "tool arguments are not persisted and no tool is executed",
            "production security/deployment/compliance gates remain open",
        ),
        verdicts=FollowupVerdict(tool_stream_observed=case.status == "passed"),
    )
    output.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


__all__ = [
    "FOLLOWUP_CASE_ID",
    "FOLLOWUP_EXPERIMENT_NAME",
    "FOLLOWUP_MAX_OBSERVED_TOKENS",
    "FOLLOWUP_MAX_OUTPUT_TOKENS",
    "ToolStreamFollowupReport",
    "run_real_tool_stream_followup",
]
