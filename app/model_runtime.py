"""Trusted, model-specific request budgets for bounded Agent executions.

The Skill manifest remains the source of permissions, iteration/tool limits,
and context ceilings.  A ``ModelRuntimeProfile`` only supplies request
parameters that are known to be appropriate for one exact provider/model
pair.  Profiles are constructed by trusted composition code; they are never
read from user input or model output.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from math import isfinite


_SAFE_ID = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


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
    "GLM53_FLASH_RUNTIME_PROFILE",
    "ModelRuntimeProfile",
    "require_registered_model_runtime_profile",
    "resolve_model_runtime_profile",
]
