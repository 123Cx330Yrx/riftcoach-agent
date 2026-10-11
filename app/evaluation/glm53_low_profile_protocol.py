"""The fresh, three-call G53-3-L gate for the low-profile candidate.

This module is deliberately an evaluation seam.  It reuses the existing
structured-output plus tool-round-trip protocol runner, but binds the private
low-profile request policy explicitly so the product Runtime registry cannot
be changed by accident.  The public report contains only hashes, counters,
terminal categories and safe identities; no prompt, response, reasoning,
tool arguments or credentials are retained.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.evaluation.provider_adapter_protocol import (
    AdapterProtocolSliceReport,
    AdapterProtocolSliceRunner,
)
from app.model_runtime import CandidateEvaluationRequestPolicy
from app.providers.protocol import LLMProvider

from .glm53_flash_candidate_profile import (
    GLM53_FLASH_LOW_CANDIDATE_PROFILE_PLAN,
    GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY,
    require_glm53_flash_low_candidate_request_policy,
)
from .glm53_low_profile_budget import (
    CandidateEvaluationBudgetState,
    CandidateEvaluationBudgetedProvider,
)


SCHEMA_VERSION = "1.0"
PROTOCOL_ID = "glm-5.3-flash-candidate-low-4096-g53-3l"
PROVIDER_ID = "zhipu"
MODEL = "glm-5.3-flash"
MAX_CALLS = 3
PROTOCOL_CASE_ID = "g53_3l_protocol"
DEFAULT_OUTPUT = Path(
    "data/evaluation/results/provider_capabilities/"
    "zhipu_glm53_flash_candidate_low_4096_g53_3l_rq224_v1.json"
)

GitShaText = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
Sha256Text = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
NonBlankText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
EvidenceOrigin = Literal["offline_fake", "real_provider"]

_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
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


class GLM53LowProfileProtocolReport(_FrozenModel):
    """Body-free evidence for one fresh low-profile three-call protocol."""

    schema_version: Literal[SCHEMA_VERSION] = SCHEMA_VERSION
    protocol_id: Literal[PROTOCOL_ID] = PROTOCOL_ID
    provider_id: Literal[PROVIDER_ID] = PROVIDER_ID
    requested_model: Literal[MODEL] = MODEL
    evidence_origin: EvidenceOrigin
    implementation_sha: GitShaText
    protocol_code_sha: GitShaText
    request_policy_id: NonBlankText
    request_policy_version: NonBlankText
    candidate_profile_id: NonBlankText
    candidate_profile_version: NonBlankText
    explicit_real_call_confirmed: bool = False
    provider_call_count: int = Field(ge=0, le=MAX_CALLS)
    network_used: bool
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    latency_ms: int = Field(ge=0)
    run_timestamp_utc: datetime
    protocol: AdapterProtocolSliceReport
    candidate_registered: Literal[False] = False
    production_admitted: Literal[False] = False
    unsupported_boundaries: tuple[NonBlankText, ...]

    @model_validator(mode="after")
    def validate_report(self) -> "GLM53LowProfileProtocolReport":
        if not _GIT_SHA.fullmatch(self.implementation_sha):
            raise ValueError("implementation_sha must be a lowercase git SHA")
        if self.protocol_code_sha != self.implementation_sha:
            raise ValueError("protocol_code_sha must match implementation_sha")
        policy = GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY
        if (self.request_policy_id, self.request_policy_version) != (
            policy.policy_id,
            policy.version,
        ):
            raise ValueError("report request policy identity is not the allowlisted one")
        if (self.candidate_profile_id, self.candidate_profile_version) != (
            GLM53_FLASH_LOW_CANDIDATE_PROFILE_PLAN.profile_id,
            GLM53_FLASH_LOW_CANDIDATE_PROFILE_PLAN.version,
        ):
            raise ValueError("report candidate profile identity is not the allowlisted one")
        if (self.protocol.provider_id, self.protocol.requested_model) != (
            PROVIDER_ID,
            MODEL,
        ):
            raise ValueError("protocol Provider identity is not the Flash pair")
        if self.protocol.code_sha != self.implementation_sha:
            raise ValueError("protocol code SHA must match implementation SHA")
        if self.provider_call_count != self.protocol.calls_used:
            raise ValueError("provider call count does not match protocol")
        if self.input_tokens != sum(row.input_tokens for row in self.protocol.cases):
            raise ValueError("input token total does not match protocol")
        if self.output_tokens != sum(row.output_tokens for row in self.protocol.cases):
            raise ValueError("output token total does not match protocol")
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("total token count is inconsistent")
        if self.latency_ms != sum(row.latency_ms for row in self.protocol.cases):
            raise ValueError("latency total does not match protocol")
        if self.evidence_origin == "real_provider":
            if self.explicit_real_call_confirmed is not True:
                raise ValueError("real evidence requires explicit confirmation")
            if self.network_used is not (self.provider_call_count > 0):
                raise ValueError("real evidence network flag is inconsistent")
        else:
            if self.explicit_real_call_confirmed or self.network_used:
                raise ValueError("offline evidence cannot claim a real call")
        if self.candidate_registered or self.production_admitted:
            raise ValueError("protocol gate cannot register or admit production")
        if len(set(self.unsupported_boundaries)) != len(self.unsupported_boundaries):
            raise ValueError("unsupported boundaries must be unique")
        return self


def run_glm53_low_profile_protocol(
    *,
    provider: LLMProvider,
    implementation_sha: str,
    evidence_origin: EvidenceOrigin = "offline_fake",
    confirm_real_call: bool = False,
    request_policy: CandidateEvaluationRequestPolicy = (
        GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY
    ),
    clock: Callable[[], float] | None = None,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> GLM53LowProfileProtocolReport:
    """Run exactly the bounded G53-3-L protocol composition.

    ``offline_fake`` is the default and never implies network use.  A caller
    must opt into ``real_provider`` and pass the explicit confirmation flag;
    this keeps a copied test invocation from silently sending API traffic.
    """

    if not isinstance(provider, LLMProvider):
        # ``LLMProvider`` is runtime-checkable, but a useful error is clearer
        # than letting the runner fail halfway through a protocol.
        raise TypeError("provider must implement the LLMProvider protocol")
    if not isinstance(implementation_sha, str) or _GIT_SHA.fullmatch(
        implementation_sha
    ) is None:
        raise ValueError("implementation_sha must be a lowercase git SHA")
    if evidence_origin not in {"offline_fake", "real_provider"}:
        raise ValueError("unsupported evidence origin")
    if evidence_origin == "real_provider" and confirm_real_call is not True:
        raise RuntimeError("real G53-3-L protocol requires explicit confirmation")
    if evidence_origin == "offline_fake" and confirm_real_call:
        raise ValueError("offline protocol cannot claim real-call confirmation")
    policy = require_glm53_flash_low_candidate_request_policy(request_policy)
    if not policy.matches(provider.provider_name, provider.model_name):
        raise ValueError("provider does not match the low-profile Flash policy")

    clock_fn = clock or time.monotonic
    state = CandidateEvaluationBudgetState()
    state.register_case(PROTOCOL_CASE_ID)
    controlled = CandidateEvaluationBudgetedProvider(
        provider=provider,
        state=state,
        case_id=PROTOCOL_CASE_ID,
        request_policy=policy,
        clock=clock_fn,
    )
    protocol = AdapterProtocolSliceRunner(
        provider=controlled,
        code_sha=implementation_sha,
        max_calls=MAX_CALLS,
        request_policy=policy,
        clock=clock_fn,
        now=now,
    ).run()
    snapshot = state.snapshot()
    return GLM53LowProfileProtocolReport(
        evidence_origin=evidence_origin,
        implementation_sha=implementation_sha,
        protocol_code_sha=implementation_sha,
        request_policy_id=policy.policy_id,
        request_policy_version=policy.version,
        candidate_profile_id=GLM53_FLASH_LOW_CANDIDATE_PROFILE_PLAN.profile_id,
        candidate_profile_version=GLM53_FLASH_LOW_CANDIDATE_PROFILE_PLAN.version,
        explicit_real_call_confirmed=(evidence_origin == "real_provider"),
        provider_call_count=protocol.calls_used,
        network_used=(evidence_origin == "real_provider" and protocol.calls_used > 0),
        input_tokens=snapshot["input_tokens"],
        output_tokens=snapshot["output_tokens"],
        total_tokens=snapshot["input_tokens"] + snapshot["output_tokens"],
        latency_ms=sum(row.latency_ms for row in protocol.cases),
        run_timestamp_utc=now(),
        protocol=protocol,
        unsupported_boundaries=(
            "领域任务质量",
            "streaming 生产能力",
            "黄金切片",
            "安全/部署/合规",
            "8F final evaluation",
        ),
    )


def canonical_report_bytes(report: GLM53LowProfileProtocolReport) -> bytes:
    """Serialize only the body-free canonical representation."""

    if not isinstance(report, GLM53LowProfileProtocolReport):
        raise TypeError("report must be a GLM53LowProfileProtocolReport")
    payload = report.model_dump(mode="json")
    _assert_body_free(payload)
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def write_report_create_only(
    report: GLM53LowProfileProtocolReport,
    *,
    repository_root: str | Path,
    output: str | Path = DEFAULT_OUTPUT,
) -> Path:
    """Write a new report only inside the provider-capability result tree."""

    root = Path(repository_root).resolve()
    target = Path(output)
    resolved = (target if target.is_absolute() else root / target).resolve()
    allowed = (root / "data/evaluation/results/provider_capabilities").resolve()
    if not resolved.is_relative_to(allowed) or resolved.suffix.lower() != ".json":
        raise ValueError("output must be a JSON file in provider capability results")
    if resolved.exists() or resolved.is_symlink():
        raise FileExistsError("protocol evidence is immutable")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_bytes(canonical_report_bytes(report))
    return resolved


def _assert_body_free(value: object) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str) and key.strip().lower() in _FORBIDDEN_KEYS:
                raise ValueError("protocol report contains a forbidden body field")
            _assert_body_free(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _assert_body_free(item)


__all__ = [
    "DEFAULT_OUTPUT",
    "GLM53LowProfileProtocolReport",
    "MAX_CALLS",
    "MODEL",
    "PROTOCOL_ID",
    "PROTOCOL_CASE_ID",
    "PROVIDER_ID",
    "SCHEMA_VERSION",
    "canonical_report_bytes",
    "run_glm53_low_profile_protocol",
    "write_report_create_only",
]
