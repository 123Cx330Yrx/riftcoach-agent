"""Explicit, immutable request profiles for Zhipu model families.

The provider-neutral chat contract does not carry vendor-specific thinking
fields.  Keeping those fields in a model-selected profile makes the adapter
boundary auditable while preserving the historical GLM-5.2 behavior.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal


ZHIPU_STANDARD_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"
ZHIPU_GLM52_MODEL = "glm-5.2"
ZHIPU_GLM53_MODEL = "glm-5.3"
ZHIPU_GLM53_FLASH_MODEL = "glm-5.3-flash"

ThinkingType = Literal["disabled", "enabled"]
ReasoningEffort = Literal["low", "high", "max"]

_PROFILE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,95}$")
_THINKING_TYPES = frozenset({"disabled", "enabled"})
_REASONING_EFFORTS = frozenset({"low", "high", "max"})


@dataclass(frozen=True)
class ZhipuThinkingProfile:
    """One safe, provider-specific thinking contract selected by model ID."""

    profile_id: str
    model: str | None
    thinking_type: ThinkingType
    reasoning_effort: ReasoningEffort | None = None
    clear_thinking: bool | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.profile_id, str):
            raise ValueError("profile_id must be a safe non-empty identifier.")
        profile_id = self.profile_id.strip()
        if not _PROFILE_ID_PATTERN.fullmatch(profile_id):
            raise ValueError("profile_id must be a safe non-empty identifier.")
        object.__setattr__(self, "profile_id", profile_id)

        if self.model is not None:
            if not isinstance(self.model, str):
                raise ValueError("model must be non-empty when supplied.")
            model = self.model.strip().lower()
            if not model:
                raise ValueError("model must be non-empty when supplied.")
            object.__setattr__(self, "model", model)

        if not isinstance(self.thinking_type, str) or (
            self.thinking_type not in _THINKING_TYPES
        ):
            raise ValueError("thinking_type must be enabled or disabled.")
        if self.reasoning_effort is not None and (
            not isinstance(self.reasoning_effort, str)
            or self.reasoning_effort not in _REASONING_EFFORTS
        ):
            raise ValueError("reasoning_effort must be low, high, max, or None.")
        if self.clear_thinking is not None and not isinstance(
            self.clear_thinking,
            bool,
        ):
            raise ValueError("clear_thinking must be a boolean or None.")
        if self.thinking_type == "disabled":
            if self.reasoning_effort is not None:
                raise ValueError(
                    "disabled thinking cannot carry reasoning_effort."
                )
            if self.clear_thinking is not None:
                raise ValueError(
                    "disabled thinking cannot carry clear_thinking."
                )
        elif self.reasoning_effort is None:
            raise ValueError("enabled thinking requires reasoning_effort.")

    @property
    def accepts_reasoning_content(self) -> bool:
        """Whether non-empty provider reasoning may be consumed and dropped."""

        return self.thinking_type == "enabled"

    def extra_body(self) -> dict[str, object]:
        """Return a fresh vendor-extension payload for one SDK request."""

        thinking: dict[str, object] = {"type": self.thinking_type}
        if self.clear_thinking is not None:
            thinking["clear_thinking"] = self.clear_thinking
        body: dict[str, object] = {"thinking": thinking}
        if self.reasoning_effort is not None:
            body["reasoning_effort"] = self.reasoning_effort
        return body


# Keep names explicit in evidence and make the historical fallback visible.
ZHIPU_LEGACY_THINKING_PROFILE = ZhipuThinkingProfile(
    profile_id="legacy-disabled-thinking",
    model=None,
    thinking_type="disabled",
)
ZHIPU_GLM52_THINKING_PROFILE = ZhipuThinkingProfile(
    profile_id="glm-5.2-disabled-thinking",
    model=ZHIPU_GLM52_MODEL,
    thinking_type="disabled",
)
ZHIPU_GLM53_THINKING_PROFILE = ZhipuThinkingProfile(
    profile_id="glm-5.3-enabled-low",
    model=ZHIPU_GLM53_MODEL,
    thinking_type="enabled",
    reasoning_effort="low",
)
ZHIPU_GLM53_FLASH_THINKING_PROFILE = ZhipuThinkingProfile(
    profile_id="glm-5.3-flash-enabled-low",
    model=ZHIPU_GLM53_FLASH_MODEL,
    thinking_type="enabled",
    reasoning_effort="low",
)

_MODEL_PROFILES = MappingProxyType(
    {
        ZHIPU_GLM52_MODEL: ZHIPU_GLM52_THINKING_PROFILE,
        ZHIPU_GLM53_MODEL: ZHIPU_GLM53_THINKING_PROFILE,
        ZHIPU_GLM53_FLASH_MODEL: ZHIPU_GLM53_FLASH_THINKING_PROFILE,
    }
)
_PROFILE_BY_ID = MappingProxyType(
    {
        profile.profile_id: profile
        for profile in (
            ZHIPU_LEGACY_THINKING_PROFILE,
            ZHIPU_GLM52_THINKING_PROFILE,
            ZHIPU_GLM53_THINKING_PROFILE,
            ZHIPU_GLM53_FLASH_THINKING_PROFILE,
        )
    }
)


def resolve_zhipu_thinking_profile(model: str) -> ZhipuThinkingProfile:
    """Resolve an exact known model, or the safe historical fallback."""

    if not isinstance(model, str) or not model.strip():
        raise ValueError("model must be a non-empty string.")
    return _MODEL_PROFILES.get(model.strip().lower(), ZHIPU_LEGACY_THINKING_PROFILE)


def resolve_zhipu_profile(profile_id: str) -> ZhipuThinkingProfile:
    """Resolve a profile ID for audit tooling without allowing ad-hoc values."""

    if not isinstance(profile_id, str) or not profile_id.strip():
        raise ValueError("profile_id must be a non-empty string.")
    try:
        return _PROFILE_BY_ID[profile_id.strip().lower()]
    except KeyError:
        raise ValueError("unknown Zhipu thinking profile.") from None


def validate_zhipu_profile_for_model(
    model: str,
    profile: ZhipuThinkingProfile,
) -> ZhipuThinkingProfile:
    """Reject profile/model mismatches and unregistered override profiles."""

    if not isinstance(profile, ZhipuThinkingProfile):
        raise ValueError("profile must be a ZhipuThinkingProfile.")
    expected = resolve_zhipu_thinking_profile(model)
    if profile != expected:
        raise ValueError("Zhipu thinking profile does not match model.")
    return profile


# Compatibility aliases keep the public vocabulary concise for callers and
# future evidence scripts without creating a second profile implementation.
ZhipuModelProfile = ZhipuThinkingProfile
get_zhipu_model_profile = resolve_zhipu_thinking_profile


__all__ = [
    "ReasoningEffort",
    "ThinkingType",
    "ZHIPU_GLM52_MODEL",
    "ZHIPU_GLM52_THINKING_PROFILE",
    "ZHIPU_GLM53_FLASH_MODEL",
    "ZHIPU_GLM53_FLASH_THINKING_PROFILE",
    "ZHIPU_GLM53_MODEL",
    "ZHIPU_GLM53_THINKING_PROFILE",
    "ZHIPU_LEGACY_THINKING_PROFILE",
    "ZHIPU_STANDARD_BASE_URL",
    "ZhipuModelProfile",
    "ZhipuThinkingProfile",
    "get_zhipu_model_profile",
    "resolve_zhipu_profile",
    "resolve_zhipu_thinking_profile",
    "validate_zhipu_profile_for_model",
]
