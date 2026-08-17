"""Runtime identity resolver contracts and explicit non-product compatibility."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class RuntimePromptIdentity(Protocol):
    """The verified identity fields Runtime writes into its safe Trace."""

    @property
    def program_id(self) -> str: ...

    @property
    def program_version(self) -> str: ...

    @property
    def skill_name(self) -> str: ...

    @property
    def skill_version(self) -> str: ...

    @property
    def context_contract_version(self) -> str: ...


class RuntimePromptIdentityResolver(Protocol):
    def resolve(
        self,
        skill_name: str,
        skill_version: str,
    ) -> RuntimePromptIdentity: ...


@dataclass(frozen=True)
class LegacyRuntimeIdentity:
    """Compatibility identity for direct pre-product Runtime tests only."""

    skill_name: str
    skill_version: str
    context_contract_version: str = "1.0.0"

    @property
    def program_id(self) -> str:
        return f"{self.skill_name}-coach"

    @property
    def program_version(self) -> str:
        return "1.0.0"


class LegacyRuntimeIdentityResolver:
    """Explicit adapter; it is not a Prompt Program drift gate."""

    def resolve(
        self,
        skill_name: str,
        skill_version: str,
    ) -> LegacyRuntimeIdentity:
        return LegacyRuntimeIdentity(
            skill_name=skill_name,
            skill_version=skill_version,
        )


__all__ = [
    "LegacyRuntimeIdentity",
    "LegacyRuntimeIdentityResolver",
    "RuntimePromptIdentity",
    "RuntimePromptIdentityResolver",
]
