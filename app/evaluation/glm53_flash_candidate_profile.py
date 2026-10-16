"""Offline contract for the next GLM-5.3-Flash profile experiment.

The latest G53-7 attempt stopped after an ``incomplete_chat_response`` while
the registered Flash profile was using maximum reasoning with a 2048-token
request cap.  This module records a narrower hypothesis for an isolated
follow-up: keep the provider's legal thinking controls and sampling values,
select the separately registered low-reasoning candidate profile, and give it
4096 output tokens.  It is a plan, not a product runtime or an automatic
fallback.  No credentials, SDK client, or network operation is imported.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from math import isfinite
from typing import Any, Literal

from app.providers.models import ChatRequest
from app.model_runtime import (
    CandidateEvaluationRequestPolicy,
    _issue_candidate_evaluation_request_policy,
)
from app.providers.zhipu_profiles import (
    ZHIPU_GLM53_FLASH_LOW_CANDIDATE_PROFILE,
    ZHIPU_GLM53_FLASH_MODEL,
    ZhipuThinkingProfile,
    validate_zhipu_candidate_profile_for_model,
)


PROVIDER_ID = "zhipu"
MODEL = ZHIPU_GLM53_FLASH_MODEL
PROFILE_ID = "glm-5.3-flash-candidate-low-4096"
PROFILE_VERSION = "1.0.0"
RUNTIME_PROFILE_ID = "glm-5.3-flash-runtime-low-candidate"
RUNTIME_PROFILE_VERSION = "1.0.0"
MAX_OUTPUT_TOKENS = 4096
AGENT_TIMEOUT_S = 90.0
LLM_TOOL_TIMEOUT_S = 90.0
TRANSPORT_TIMEOUT_S = 120.0
TEMPERATURE = 1.0
TOP_P = 0.95
ACTIVATION_STATE: Literal["candidate"] = "candidate"
REQUEST_POLICY_ID = "glm-5.3-flash-evaluation-low-4096"
REQUEST_POLICY_VERSION = "1.0.0"

_SAFE_ID = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


@dataclass(frozen=True, slots=True)
class FlashCandidateProfilePlan:
    """A trusted, candidate-only request profile.

    The plan owns all provider knobs.  A caller may request a smaller output
    cap or timeout, but cannot raise either value or replace the profile
    metadata.  ``execution_allowed`` is permanently false in this version.
    """

    profile_id: str = PROFILE_ID
    version: str = PROFILE_VERSION
    runtime_profile_id: str = RUNTIME_PROFILE_ID
    runtime_profile_version: str = RUNTIME_PROFILE_VERSION
    provider_id: str = PROVIDER_ID
    model: str = MODEL
    thinking_profile: ZhipuThinkingProfile = field(
        default=ZHIPU_GLM53_FLASH_LOW_CANDIDATE_PROFILE,
        repr=False,
    )
    max_output_tokens: int = MAX_OUTPUT_TOKENS
    agent_timeout_s: float = AGENT_TIMEOUT_S
    llm_tool_timeout_s: float = LLM_TOOL_TIMEOUT_S
    transport_timeout_s: float = TRANSPORT_TIMEOUT_S
    temperature: float = TEMPERATURE
    top_p: float = TOP_P
    activation_state: Literal["candidate"] = ACTIVATION_STATE
    execution_allowed: Literal[False] = False

    def __post_init__(self) -> None:
        for field_name in (
            "profile_id",
            "runtime_profile_id",
            "provider_id",
            "model",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or _SAFE_ID.fullmatch(value.strip().lower()) is None:
                raise ValueError(f"{field_name} must be a safe identifier")
            object.__setattr__(self, field_name, value.strip().lower())
        for field_name in ("version", "runtime_profile_version"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or _SEMVER.fullmatch(value.strip()) is None:
                raise ValueError(f"{field_name} must be semantic version")
            object.__setattr__(self, field_name, value.strip())
        if self.provider_id != PROVIDER_ID or self.model != MODEL:
            raise ValueError("candidate profile must target the exact Flash pair")
        if self.profile_id != PROFILE_ID or self.runtime_profile_id != RUNTIME_PROFILE_ID:
            raise ValueError("unsupported candidate profile identity")
        if self.version != PROFILE_VERSION or self.runtime_profile_version != RUNTIME_PROFILE_VERSION:
            raise ValueError("unsupported candidate profile version")
        if self.activation_state != "candidate" or self.execution_allowed is not False:
            raise ValueError("candidate profile cannot be activated")
        validate_zhipu_candidate_profile_for_model(self.model, self.thinking_profile)
        if self.thinking_profile != ZHIPU_GLM53_FLASH_LOW_CANDIDATE_PROFILE:
            raise ValueError("candidate profile must use the allowlisted low-thinking profile")
        if (
            isinstance(self.max_output_tokens, bool)
            or not isinstance(self.max_output_tokens, int)
            or self.max_output_tokens != MAX_OUTPUT_TOKENS
        ):
            raise ValueError("candidate profile output cap must be exactly 4096")
        for field_name in (
            "agent_timeout_s",
            "llm_tool_timeout_s",
            "transport_timeout_s",
        ):
            value = getattr(self, field_name)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(value)
                or value <= 0
                or value > 300
            ):
                raise ValueError(f"{field_name} must be in (0, 300]")
        if self.llm_tool_timeout_s < self.agent_timeout_s:
            raise ValueError("llm_tool_timeout_s must cover agent timeout")
        if self.transport_timeout_s < self.llm_tool_timeout_s:
            raise ValueError("transport_timeout_s must cover tool timeout")
        if (
            isinstance(self.temperature, bool)
            or not isinstance(self.temperature, (int, float))
            or not isfinite(self.temperature)
            or not 0 <= self.temperature <= 2
        ):
            raise ValueError("temperature must be between 0 and 2")
        if (
            isinstance(self.top_p, bool)
            or not isinstance(self.top_p, (int, float))
            or not isfinite(self.top_p)
            or not 0 <= self.top_p <= 1
        ):
            raise ValueError("top_p must be between 0 and 1")

    def build_request(self, request: ChatRequest) -> ChatRequest:
        """Apply the candidate knobs without changing message/tool meaning."""

        if not isinstance(request, ChatRequest):
            raise TypeError("request must be a ChatRequest")
        requested_tokens = (
            self.max_output_tokens
            if request.max_tokens is None
            else min(request.max_tokens, self.max_output_tokens)
        )
        timeout_s = min(request.timeout_s, self.llm_tool_timeout_s)
        metadata: dict[str, Any] = dict(request.metadata)
        metadata.update(
            {
                "provider_id": self.provider_id,
                "model": self.model,
                "candidate_profile_id": self.profile_id,
                "candidate_profile_version": self.version,
                "runtime_profile_id": self.runtime_profile_id,
                "runtime_profile_version": self.runtime_profile_version,
                "activation_state": self.activation_state,
            }
        )
        return ChatRequest(
            messages=request.messages,
            tools=request.tools,
            tool_choice=request.tool_choice,
            temperature=self.temperature,
            max_tokens=requested_tokens,
            timeout_s=timeout_s,
            response_contract=request.response_contract,
            metadata=metadata,
            top_p=self.top_p,
        )

    @property
    def request_policy(self) -> CandidateEvaluationRequestPolicy:
        """The explicit evaluation-only request policy for this plan."""

        return GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY

    def public_identity(self) -> dict[str, object]:
        """Return only non-sensitive identity/budget fields for receipts."""

        return {
            "provider_id": self.provider_id,
            "model": self.model,
            "candidate_profile_id": self.profile_id,
            "candidate_profile_version": self.version,
            "runtime_profile_id": self.runtime_profile_id,
            "runtime_profile_version": self.runtime_profile_version,
            "thinking_profile_id": self.thinking_profile.profile_id,
            "reasoning_effort": self.thinking_profile.reasoning_effort,
            "clear_thinking": self.thinking_profile.clear_thinking,
            "max_output_tokens": self.max_output_tokens,
            "agent_timeout_s": self.agent_timeout_s,
            "llm_tool_timeout_s": self.llm_tool_timeout_s,
            "transport_timeout_s": self.transport_timeout_s,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "activation_state": self.activation_state,
            "execution_allowed": self.execution_allowed,
            "request_policy_id": REQUEST_POLICY_ID,
            "request_policy_version": REQUEST_POLICY_VERSION,
            "max_retries": self.request_policy.max_retries,
            "deterministic_fallback_allowed": (
                self.request_policy.deterministic_fallback_allowed
            ),
        }


GLM53_FLASH_LOW_CANDIDATE_PROFILE_PLAN = FlashCandidateProfilePlan()

# This policy is deliberately issued by the private factory rather than by a
# public constructor.  It is the only request-policy capability currently
# available to the low-profile evaluation seam; it is not a product runtime
# profile and is never returned by ``resolve_model_runtime_profile``.
GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY = (
    _issue_candidate_evaluation_request_policy(
        policy_id=REQUEST_POLICY_ID,
        version=REQUEST_POLICY_VERSION,
        provider_id=PROVIDER_ID,
        model=MODEL,
        agent_timeout_s=AGENT_TIMEOUT_S,
        llm_tool_timeout_s=LLM_TOOL_TIMEOUT_S,
        transport_timeout_s=TRANSPORT_TIMEOUT_S,
        max_output_tokens=MAX_OUTPUT_TOKENS,
        temperature=TEMPERATURE,
        top_p=TOP_P,
    )
)


def require_glm53_flash_low_candidate_request_policy(
    policy: CandidateEvaluationRequestPolicy | None = None,
) -> CandidateEvaluationRequestPolicy:
    """Accept only the exact low-profile policy issued for this experiment."""

    selected = (
        GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY
        if policy is None
        else policy
    )
    if selected is not GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY:
        raise ValueError("unsupported GLM-5.3 low candidate request policy")
    return selected


def select_candidate_profile_for_failure(
    *,
    failure_code: str | None,
    provider_error_code: str | None,
) -> FlashCandidateProfilePlan | None:
    """Select the hypothesis only for the observed completion failure shape.

    Returning a plan does not execute it.  Any other provider/transport error
    remains unclassified here, so a future caller cannot turn this helper into
    a blanket retry or fallback policy.
    """

    if failure_code == "provider_response_invalid" and provider_error_code == "incomplete_chat_response":
        return GLM53_FLASH_LOW_CANDIDATE_PROFILE_PLAN
    return None


__all__ = [
    "ACTIVATION_STATE",
    "AGENT_TIMEOUT_S",
    "CandidateEvaluationRequestPolicy",
    "FlashCandidateProfilePlan",
    "GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY",
    "GLM53_FLASH_LOW_CANDIDATE_PROFILE_PLAN",
    "LLM_TOOL_TIMEOUT_S",
    "MAX_OUTPUT_TOKENS",
    "MODEL",
    "PROFILE_ID",
    "PROFILE_VERSION",
    "PROVIDER_ID",
    "REQUEST_POLICY_ID",
    "REQUEST_POLICY_VERSION",
    "RUNTIME_PROFILE_ID",
    "RUNTIME_PROFILE_VERSION",
    "TOP_P",
    "TRANSPORT_TIMEOUT_S",
    "select_candidate_profile_for_failure",
    "require_glm53_flash_low_candidate_request_policy",
]
