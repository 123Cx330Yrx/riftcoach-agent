"""One bounded real-call probe for the explicit GLM-5.3 low-thinking candidate.

This is deliberately smaller than G53-7.  It answers one question only:
whether the allowlisted low-reasoning/4096 request profile can produce a
normalized response on the frozen, body-free diagnostic context.  It does not
run the AgentLoop, use tools, retry, recover, register the profile, or alter
the product runtime.  A later domain gate must remain a separate experiment.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, Literal

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.providers.config import load_zhipu_settings
from app.providers.errors import ProviderError
from app.providers.models import ChatMessage, ChatRequest, MessageRole, ToolChoiceMode
from app.providers.zhipu import ZhipuProvider

from .glm53_flash_candidate_profile import (
    GLM53_FLASH_LOW_CANDIDATE_PROFILE_PLAN,
    FlashCandidateProfilePlan,
)
from .glm53_flash_transport_generation_split_diagnostic import (
    FrozenContextSnapshot,
    _load_frozen_context,
)


PROTOCOL_ID = "glm-5.3-flash-candidate-low-4096-profile-probe"
SCHEMA_VERSION = "1.0"
PROVIDER_ID = "zhipu"
MODEL = "glm-5.3-flash"
BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"
MAX_REAL_CALLS = 1
DEFAULT_OUTPUT = Path(
    "data/evaluation/results/provider_capabilities/"
    "zhipu_glm53_flash_candidate_low_4096_profile_probe_rq221_v1.json"
)

SafeSha = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
GitSha = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
SafeCode = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_.-]{0,95}$")]

_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
_SAFE_CODE = re.compile(r"^[a-z][a-z0-9_.-]{0,95}$")
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


FieldState = Literal["not_observed", "empty", "non_empty", "non_string"]
UsageState = Literal["valid", "missing", "invalid"]
ProbeStatus = Literal["observed", "failed"]
FinishReason = Literal[
    "stop",
    "tool_calls",
    "length",
    "content_filter",
    "insufficient_system_resource",
    "missing",
    "unknown",
]


class CandidateProfileProbeObservation(_FrozenModel):
    status: ProbeStatus
    external_calls: Literal[0, 1]
    response_received: bool
    content_state: FieldState
    reasoning_state: FieldState
    finish_reason: FinishReason | None = None
    usage_state: UsageState
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    latency_ms: int = Field(ge=0)
    request_id_sha256: SafeSha | None = None
    error_code: SafeCode | None = None

    @model_validator(mode="after")
    def validate_observation(self) -> "CandidateProfileProbeObservation":
        if self.external_calls == 0:
            if self.status != "failed" or self.response_received:
                raise ValueError("zero-call observation must be a failed no-response")
        else:
            if self.status not in {"observed", "failed"}:
                raise ValueError("one-call observation has an invalid status")
        if self.status == "failed" and self.error_code is None:
            raise ValueError("failed observation needs a safe error code")
        if self.status == "observed" and not self.response_received:
            raise ValueError("observed response must be marked received")
        if self.usage_state == "valid":
            if self.input_tokens is None or self.output_tokens is None:
                raise ValueError("valid usage needs token counts")
        elif self.input_tokens is not None or self.output_tokens is not None:
            raise ValueError("unavailable usage cannot claim token counts")
        if self.content_state == "non_string" or self.reasoning_state == "non_string":
            raise ValueError("provider normalization must reject non-string fields")
        return self


class CandidateProfileProbeReport(_FrozenModel):
    schema_version: Literal[SCHEMA_VERSION] = SCHEMA_VERSION
    protocol_id: Literal[PROTOCOL_ID] = PROTOCOL_ID
    provider_id: Literal[PROVIDER_ID] = PROVIDER_ID
    model: Literal[MODEL] = MODEL
    implementation_sha: GitSha
    diagnostic_code_sha: GitSha
    input_plan_sha256: SafeSha
    prompt_context_snapshot_sha256: SafeSha
    profile_identity: Mapping[str, Any]
    request_shape_sha256: SafeSha
    explicit_real_call_confirmed: Literal[True] = True
    provider_call_count: int = Field(ge=0, le=MAX_REAL_CALLS)
    network_used: bool
    run_timestamp_utc: datetime
    observation: CandidateProfileProbeObservation
    candidate_registered: Literal[False] = False
    production_admitted: Literal[False] = False
    unsupported_boundaries: tuple[str, ...]

    @model_validator(mode="after")
    def validate_report(self) -> "CandidateProfileProbeReport":
        if self.provider_call_count != self.observation.external_calls:
            raise ValueError("provider call count does not match observation")
        if self.profile_identity.get("execution_allowed") is not False:
            raise ValueError("candidate profile must remain disabled")
        if self.network_used is not (self.provider_call_count == 1):
            raise ValueError("network usage must match the attempted call count")
        if self.candidate_registered or self.production_admitted:
            raise ValueError("probe cannot register or admit a profile")
        return self


def _canonical_json(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _assert_body_free(value: object) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str) and key.strip().lower() in _FORBIDDEN_KEYS:
                raise ValueError("body-free receipt contains a forbidden field")
            _assert_body_free(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _assert_body_free(item)


def _inside_results(root: Path, value: str | Path) -> Path:
    candidate = Path(value)
    resolved = (candidate if candidate.is_absolute() else root / candidate).resolve()
    allowed = (root / "data/evaluation/results/provider_capabilities").resolve()
    if not resolved.is_relative_to(allowed) or resolved.suffix.lower() != ".json":
        raise ValueError("output must be a JSON file in provider capability results")
    return resolved


def _validate_sha(value: str, field_name: str) -> None:
    if not isinstance(value, str) or _GIT_SHA.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a lowercase git SHA")


def _request_shape(messages: tuple[ChatMessage, ...]) -> str:
    shape = [
        {
            "role": message.role.value,
            "has_text": message.content is not None,
            "text_length": len(message.content or ""),
            "tool_call_count": len(message.tool_calls),
        }
        for message in messages
    ]
    return _sha256(shape)


def _field_state(value: object) -> FieldState:
    if value is None:
        return "empty"
    if isinstance(value, str):
        return "non_empty" if value.strip() else "empty"
    return "non_string"


def _finish_reason(value: object) -> FinishReason | None:
    if value is None:
        return "missing"
    if not isinstance(value, str):
        return "unknown"
    normalized = value.strip().lower()
    if normalized in {
        "stop",
        "tool_calls",
        "length",
        "content_filter",
        "insufficient_system_resource",
    }:
        return normalized  # type: ignore[return-value]
    return "unknown"


def _request_id_sha(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _default_environment_loader(env_file: Path | None) -> Mapping[str, str]:
    if env_file is not None:
        load_dotenv(env_file, override=False)
    return os.environ


def _failed_observation(
    *,
    external_calls: Literal[0, 1],
    latency_ms: int,
    error_code: str,
    response_received: bool = False,
    content_state: FieldState = "not_observed",
    reasoning_state: FieldState = "not_observed",
    finish_reason: FinishReason | None = None,
    usage_state: UsageState = "missing",
) -> CandidateProfileProbeObservation:
    if _SAFE_CODE.fullmatch(error_code) is None:
        error_code = "candidate_probe_error"
    return CandidateProfileProbeObservation(
        status="failed",
        external_calls=external_calls,
        response_received=response_received,
        content_state=content_state,
        reasoning_state=reasoning_state,
        finish_reason=finish_reason,
        usage_state=usage_state,
        latency_ms=max(0, latency_ms),
        error_code=error_code,
    )


def _load_context(root: Path) -> FrozenContextSnapshot:
    context = _load_frozen_context(root)
    if not isinstance(context, FrozenContextSnapshot):
        raise TypeError("frozen context loader returned an invalid value")
    return context


def run_candidate_profile_probe(
    *,
    repository_root: str | Path,
    implementation_sha: str,
    diagnostic_code_sha: str,
    output: str | Path = DEFAULT_OUTPUT,
    env_file: str | Path | None = None,
    confirm_real_call: bool = False,
    environment_loader: Callable[[Path | None], Mapping[str, str]] | None = None,
    client_factory: Callable[..., Any] = OpenAI,
    context_loader: Callable[[Path], FrozenContextSnapshot] | None = None,
    profile_plan: FlashCandidateProfilePlan = GLM53_FLASH_LOW_CANDIDATE_PROFILE_PLAN,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> CandidateProfileProbeReport:
    """Perform exactly one explicit candidate-profile request."""

    if confirm_real_call is not True:
        raise RuntimeError("candidate profile probe requires explicit confirmation")
    _validate_sha(implementation_sha, "implementation_sha")
    _validate_sha(diagnostic_code_sha, "diagnostic_code_sha")
    if not isinstance(profile_plan, FlashCandidateProfilePlan):
        raise TypeError("profile_plan must be a FlashCandidateProfilePlan")
    root = Path(repository_root).resolve()
    output_path = _inside_results(root, output)
    if output_path.exists() or output_path.is_symlink():
        raise FileExistsError("candidate profile probe evidence is immutable")
    context = (context_loader or _load_context)(root)
    env_loader = environment_loader or _default_environment_loader
    settings = load_zhipu_settings(
        env_loader(Path(env_file).resolve() if env_file is not None else None)
    )
    if settings.model.strip().lower() != MODEL or settings.base_url.rstrip("/") != BASE_URL.rstrip("/"):
        raise ValueError("candidate profile probe settings must target GLM-5.3 Flash")

    request = profile_plan.build_request(
        ChatRequest(
            messages=context.messages,
            tool_choice=ToolChoiceMode.NONE,
            temperature=profile_plan.temperature,
            max_tokens=profile_plan.max_output_tokens,
            timeout_s=profile_plan.agent_timeout_s,
            metadata={"probe_protocol_id": PROTOCOL_ID},
            top_p=profile_plan.top_p,
        )
    )
    started = time.monotonic()
    observation: CandidateProfileProbeObservation
    try:
        client = client_factory(
            api_key=settings.api_key,
            base_url=settings.base_url,
            timeout=profile_plan.transport_timeout_s,
            max_retries=0,
        )
        provider = ZhipuProvider.from_candidate_profile(
            client=client,
            model=settings.model,
            profile=profile_plan.thinking_profile,
        )
        response = provider.chat(request)
        elapsed_ms = max(0, round((time.monotonic() - started) * 1000))
        usage = response.usage
        observation = CandidateProfileProbeObservation(
            status="observed",
            external_calls=1,
            response_received=True,
            content_state=_field_state(response.content),
            reasoning_state=_field_state(response.reasoning_content),
            finish_reason=_finish_reason(response.finish_reason),
            usage_state="valid",
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            latency_ms=elapsed_ms,
            request_id_sha256=_request_id_sha(response.request_id),
        )
    except ProviderError as error:
        observation = _failed_observation(
            external_calls=1,
            latency_ms=round((time.monotonic() - started) * 1000),
            error_code=error.code,
        )
    except Exception:
        observation = _failed_observation(
            external_calls=0,
            latency_ms=round((time.monotonic() - started) * 1000),
            error_code="candidate_probe_client_error",
        )

    report = CandidateProfileProbeReport(
        implementation_sha=implementation_sha,
        diagnostic_code_sha=diagnostic_code_sha,
        input_plan_sha256=context.input_plan_sha256,
        prompt_context_snapshot_sha256=context.prompt_context_snapshot_sha256,
        profile_identity=profile_plan.public_identity(),
        request_shape_sha256=_request_shape(request.messages),
        provider_call_count=observation.external_calls,
        network_used=observation.external_calls == 1,
        run_timestamp_utc=now(),
        observation=observation,
        unsupported_boundaries=(
            "one frozen no-tool request only; this is not a domain gate",
            "candidate profile remains disabled and is not product runtime",
            "no retry, recovery, AgentLoop, Workbench, or frontend path is exercised",
            "usage/cost stability, full domain quality, security, deployment, and 8F remain unverified",
        ),
    )
    payload = report.model_dump(mode="json")
    _assert_body_free(payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")
    return report


__all__ = [
    "BASE_URL",
    "CandidateProfileProbeObservation",
    "CandidateProfileProbeReport",
    "DEFAULT_OUTPUT",
    "MODEL",
    "PROTOCOL_ID",
    "run_candidate_profile_probe",
]
