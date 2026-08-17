"""Strict contracts for versioned, fingerprinted Prompt Programs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)
from typing_extensions import Annotated

from app.evaluation.prompt_context_identity import ComponentFingerprint


SafeId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        pattern=r"^[A-Za-z][A-Za-z0-9_.:@/_-]*$",
    ),
]
SemVer = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        pattern=r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$",
    ),
]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class PromptProgramContractError(ValueError):
    """Raised when a Prompt Program manifest violates its local contract."""


class PromptProgramManifest(BaseModel):
    """A digest-bound composition of the assets that shape model behavior.

    The manifest intentionally stores component identities, not prompt bodies.
    Bodies remain in their owning Skill/code modules and are re-probed by the
    resolver before a product run is allowed to start.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
    )

    schema_version: Literal["1.0"] = "1.0"
    program_id: SafeId
    program_version: SemVer
    skill_name: SafeId
    skill_version: SemVer
    context_contract_id: SafeId
    context_contract_version: SemVer
    evaluation_contract_id: SafeId
    evaluation_contract_version: SemVer
    component_fingerprints: tuple[ComponentFingerprint, ...] = Field(
        min_length=1,
    )
    program_sha256: Sha256

    @field_validator("component_fingerprints", mode="before")
    @classmethod
    def normalize_component_fingerprints(cls, value: Any) -> Any:
        # JSON arrays are the on-disk representation; keep the in-memory
        # contract immutable after accepting that transport shape.
        if isinstance(value, list):
            return tuple(value)
        return value

    @model_validator(mode="after")
    def validate_manifest(self) -> "PromptProgramManifest":
        component_ids = tuple(
            row.component_id for row in self.component_fingerprints
        )
        if len(set(component_ids)) != len(component_ids):
            raise PromptProgramContractError(
                "Prompt Program component IDs must be unique"
            )
        if self.evaluation_contract_id != "coach_evaluation":
            raise PromptProgramContractError(
                "Prompt Program must use the coach_evaluation contract"
            )
        if self.evaluation_contract_version != "1.1.0":
            raise PromptProgramContractError(
                "Prompt Program requires secure Evaluation contract 1.1.0"
            )
        if self.program_sha256 != self.digest_for(self.model_dump(mode="json")):
            raise PromptProgramContractError(
                "program_sha256 does not match manifest content"
            )
        return self

    @classmethod
    def digest_for(cls, payload: Mapping[str, Any]) -> str:
        """Hash the canonical manifest fields, excluding its self-digest."""

        body = {
            key: value
            for key, value in dict(payload).items()
            if key != "program_sha256"
        }
        return hashlib.sha256(
            json.dumps(
                body,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()


@dataclass(frozen=True)
class VerifiedPromptProgram:
    """A manifest after current Skill-owned assets passed the drift gate."""

    manifest: PromptProgramManifest

    @property
    def program_id(self) -> str:
        return self.manifest.program_id

    @property
    def program_version(self) -> str:
        return self.manifest.program_version

    @property
    def skill_name(self) -> str:
        return self.manifest.skill_name

    @property
    def skill_version(self) -> str:
        return self.manifest.skill_version

    @property
    def context_contract_id(self) -> str:
        return self.manifest.context_contract_id

    @property
    def context_contract_version(self) -> str:
        return self.manifest.context_contract_version

    @property
    def evaluation_contract_id(self) -> str:
        return self.manifest.evaluation_contract_id

    @property
    def evaluation_contract_version(self) -> str:
        return self.manifest.evaluation_contract_version


__all__ = [
    "PromptProgramContractError",
    "PromptProgramManifest",
    "VerifiedPromptProgram",
]
