"""Trusted, model-specific request budgets for bounded Agent executions.

The Skill manifest remains the source of permissions, iteration/tool limits,
and context ceilings.  A ``ModelRuntimeProfile`` only supplies request
parameters that are known to be appropriate for one exact provider/model
pair.  Profiles are constructed by trusted composition code; they are never
read from user input or model output.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from math import isfinite


_SAFE_ID = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
_CANDIDATE_EVALUATION_SCOPE_TOKEN = object()
_ISSUED_CANDIDATE_EVALUATION_POLICIES: list[object] = []


@dataclass(frozen=True, slots=True)
class ModelRuntimeProfile:
    """One bounded request profile for an exact provider/model pair."""

    profile_id: str
    provider_id: str
    model: str
    agent_timeout_s: float
    llm_tool_timeout_s: float
    transport_timeout_s: float
    max_output_tokens: int
    temperature: float
    top_p: float
    version: str = "1.0.0"

    def __post_init__(self) -> None:
        for field_name in ("profile_id", "provider_id", "model"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not _SAFE_ID.fullmatch(value.strip()):
                raise ValueError(f"{field_name} must be a safe identifier")
            object.__setattr__(self, field_name, value.strip().lower())

        if not isinstance(self.version, str) or not _SEMVER.fullmatch(
            self.version.strip()
        ):
            raise ValueError("version must be a semantic version")
        object.__setattr__(self, "version", self.version.strip())

        for field_name in (
            "agent_timeout_s",
            "llm_tool_timeout_s",
            "transport_timeout_s",
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{field_name} must be in (0, 300]")
            if not isfinite(value) or value <= 0 or value > 300:
                raise ValueError(f"{field_name} must be in (0, 300]")

        if self.llm_tool_timeout_s < self.agent_timeout_s:
            raise ValueError(
                "llm_tool_timeout_s must cover the Agent total deadline"
            )
        if self.transport_timeout_s < self.llm_tool_timeout_s:
            raise ValueError(
                "transport_timeout_s must cover the LLM tool deadline"
            )
        if (
            isinstance(self.max_output_tokens, bool)
            or not isinstance(self.max_output_tokens, int)
            or not 1 <= self.max_output_tokens <= 8192
        ):
            raise ValueError("max_output_tokens must be between 1 and 8192")
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

    def matches(self, provider_id: str, model: str) -> bool:
        """Return whether this profile can be used for the exact pair."""

        return (
            isinstance(provider_id, str)
            and isinstance(model, str)
            and provider_id.strip().lower() == self.provider_id
            and model.strip().lower() == self.model
        )


@dataclass(frozen=True, slots=True)
class CandidateEvaluationRequestPolicy:
    """A capability-scoped request policy for an isolated evaluation only.

    This is intentionally not a ``ModelRuntimeProfile``.  Product composition
    must continue to use the registered profile resolver; this narrower value
    is accepted only through explicitly named evaluation seams.  The private
    scope token is supplied by the evaluation factory below, so ordinary
    callers cannot construct a candidate policy by copying request fields.
    """

    policy_id: str
    version: str
    provider_id: str
    model: str
    agent_timeout_s: float
    llm_tool_timeout_s: float
    transport_timeout_s: float
    max_output_tokens: int
    temperature: float
    top_p: float
    max_retries: int = 0
    deterministic_fallback_allowed: bool = False
    _scope_token: object | None = field(
        default=None,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        if self._scope_token is not _CANDIDATE_EVALUATION_SCOPE_TOKEN:
            raise ValueError(
                "candidate evaluation policy requires its private scope"
            )
        for field_name in ("policy_id", "provider_id", "model"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not _SAFE_ID.fullmatch(
                value.strip().lower()
            ):
                raise ValueError(f"{field_name} must be a safe identifier")
            object.__setattr__(self, field_name, value.strip().lower())
        if not isinstance(self.version, str) or not _SEMVER.fullmatch(
            self.version.strip()
        ):
            raise ValueError("version must be a semantic version")
        object.__setattr__(self, "version", self.version.strip())

        for field_name in (
            "agent_timeout_s",
            "llm_tool_timeout_s",
            "transport_timeout_s",
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{field_name} must be in (0, 300]")
            if not isfinite(value) or value <= 0 or value > 300:
                raise ValueError(f"{field_name} must be in (0, 300]")
        if self.llm_tool_timeout_s < self.agent_timeout_s:
            raise ValueError(
                "llm_tool_timeout_s must cover the Agent total deadline"
            )
        if self.transport_timeout_s < self.llm_tool_timeout_s:
            raise ValueError(
                "transport_timeout_s must cover the LLM tool deadline"
            )
        if (
            isinstance(self.max_output_tokens, bool)
            or not isinstance(self.max_output_tokens, int)
            or not 1 <= self.max_output_tokens <= 8192
        ):
            raise ValueError("max_output_tokens must be between 1 and 8192")
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
        if (
            isinstance(self.max_retries, bool)
            or not isinstance(self.max_retries, int)
            or self.max_retries != 0
        ):
            raise ValueError("candidate evaluation policy must disable retries")
        if self.deterministic_fallback_allowed is not False:
            raise ValueError(
                "candidate evaluation policy must disable deterministic fallback"
            )

    @property
    def max_attempts(self) -> int:
        """The one outbound attempt permitted by this policy."""

        return self.max_retries + 1

    def matches(self, provider_id: str, model: str) -> bool:
        return (
            isinstance(provider_id, str)
            and isinstance(model, str)
            and provider_id.strip().lower() == self.provider_id
            and model.strip().lower() == self.model
        )

    def metadata(self) -> dict[str, object]:
        """Return safe identity/control fields for an outbound request."""

        return {
            "evaluation_policy_id": self.policy_id,
            "evaluation_policy_version": self.version,
            "evaluation_scope": "candidate-only",
            "evaluation_transport_timeout_s": self.transport_timeout_s,
            "deterministic_fallback_allowed": False,
        }


def _issue_candidate_evaluation_request_policy(
    *,
    policy_id: str,
    version: str,
    provider_id: str,
    model: str,
    agent_timeout_s: float,
    llm_tool_timeout_s: float,
    transport_timeout_s: float,
    max_output_tokens: int,
    temperature: float,
    top_p: float,
) -> CandidateEvaluationRequestPolicy:
    """Issue a candidate policy to trusted evaluation composition code."""

    policy = CandidateEvaluationRequestPolicy(
        policy_id=policy_id,
        version=version,
        provider_id=provider_id,
        model=model,
        agent_timeout_s=agent_timeout_s,
        llm_tool_timeout_s=llm_tool_timeout_s,
        transport_timeout_s=transport_timeout_s,
        max_output_tokens=max_output_tokens,
        temperature=temperature,
        top_p=top_p,
        _scope_token=_CANDIDATE_EVALUATION_SCOPE_TOKEN,
    )
    # Retain the exact object identity.  ``dataclasses.replace`` preserves
    # the private token, so identity registration closes that otherwise easy
    # way to clone a trusted policy with silently changed budgets.
    _ISSUED_CANDIDATE_EVALUATION_POLICIES.append(policy)
    return policy


def require_candidate_evaluation_request_policy(
    policy: CandidateEvaluationRequestPolicy,
    *,
    provider_id: str | None = None,
    model: str | None = None,
) -> CandidateEvaluationRequestPolicy:
    """Validate a candidate policy before crossing an evaluation seam."""

    if not isinstance(policy, CandidateEvaluationRequestPolicy):
        raise TypeError(
            "request_policy must be a CandidateEvaluationRequestPolicy"
        )
    if policy._scope_token is not _CANDIDATE_EVALUATION_SCOPE_TOKEN:
        raise ValueError("request_policy is outside the candidate evaluation scope")
    if not any(
        policy is issued for issued in _ISSUED_CANDIDATE_EVALUATION_POLICIES
    ):
        raise ValueError("request_policy is not an issued candidate capability")
    if (provider_id is None) != (model is None):
        raise ValueError("provider_id and model must be supplied together")
    if provider_id is not None and not policy.matches(provider_id, model):
        raise ValueError("request_policy does not match the Provider")
    return policy


# Only the exact Flash pair resolves to this profile.  Product composition may
# bind it automatically from a concrete, matching Provider; GLM-5.2 and unknown
# models resolve to None and keep their existing Skill/Tool/SDK defaults.
GLM53_FLASH_RUNTIME_PROFILE = ModelRuntimeProfile(
    profile_id="glm-5.3-flash-runtime-v1",
    provider_id="zhipu",
    model="glm-5.3-flash",
    agent_timeout_s=90.0,
    llm_tool_timeout_s=90.0,
    transport_timeout_s=120.0,
    max_output_tokens=2048,
    temperature=1.0,
    top_p=0.95,
)


def resolve_model_runtime_profile(
    provider_id: str,
    model: str,
) -> ModelRuntimeProfile | None:
    """Resolve only the explicitly supported model-specific profile."""

    if GLM53_FLASH_RUNTIME_PROFILE.matches(provider_id, model):
        return GLM53_FLASH_RUNTIME_PROFILE
    return None


def require_registered_model_runtime_profile(
    profile: ModelRuntimeProfile,
) -> ModelRuntimeProfile:
    """Accept only the immutable profile registered for its exact model pair.

    The dataclass is intentionally public for readable tests and type
    contracts, so construction alone is not a trust boundary.  Composition
    code must call this helper before allowing a profile to set request
    budgets; equal-by-value forged profiles are rejected as well.
    """

    if not isinstance(profile, ModelRuntimeProfile):
        raise TypeError("runtime_profile must be a ModelRuntimeProfile")
    registered = resolve_model_runtime_profile(profile.provider_id, profile.model)
    if registered is None or profile != registered:
        raise ValueError("runtime_profile is not a registered model profile")
    return registered


__all__ = [
    "CandidateEvaluationRequestPolicy",
    "GLM53_FLASH_RUNTIME_PROFILE",
    "ModelRuntimeProfile",
    "require_candidate_evaluation_request_policy",
    "require_registered_model_runtime_profile",
    "resolve_model_runtime_profile",
]
