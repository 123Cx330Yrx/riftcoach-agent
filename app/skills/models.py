"""Machine-readable contracts shared by RiftCoach Skill packages."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .routing_text import normalize_routing_text


_SKILL_NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
_MODEL_REFERENCE_PATTERN = re.compile(
    r"^app(?:\.[a-z_][a-z0-9_]*)+:[A-Z][A-Za-z0-9_]*$"
)


class SkillContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SkillTriggerGroup(SkillContractModel):
    name: str
    any_of: tuple[str, ...] = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not re.fullmatch(r"[a-z][a-z0-9_]*", value):
            raise ValueError(
                "trigger group name must be a lowercase snake_case identifier"
            )
        return value

    @field_validator("any_of")
    @classmethod
    def validate_signals(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized_values = tuple(value.strip() for value in values)
        routing_keys = tuple(
            normalize_routing_text(value) for value in normalized_values
        )
        if any(not key for key in routing_keys):
            raise ValueError(
                "routing signals must contain at least one letter or number"
            )
        if len(set(routing_keys)) != len(routing_keys):
            raise ValueError("routing signals must not contain duplicates")
        return normalized_values


class SkillTriggers(SkillContractModel):
    intent: str = Field(min_length=1)
    positive_examples: tuple[str, ...] = Field(min_length=1)
    negative_examples: tuple[str, ...] = ()
    required_signal_groups: tuple[SkillTriggerGroup, ...] = Field(min_length=1)
    excluded_signals: tuple[str, ...] = ()

    @field_validator("intent")
    @classmethod
    def validate_intent(cls, value: str) -> str:
        if not re.fullmatch(r"[a-z][a-z0-9_]*", value):
            raise ValueError("intent must be a lowercase snake_case identifier")
        return value

    @field_validator("positive_examples", "negative_examples")
    @classmethod
    def validate_examples(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(value.strip() for value in values)
        if any(not value for value in normalized):
            raise ValueError("trigger examples must not be blank")
        if len(set(normalized)) != len(normalized):
            raise ValueError("trigger examples must not contain duplicates")
        return normalized

    @field_validator("excluded_signals")
    @classmethod
    def validate_excluded_signals(
        cls,
        values: tuple[str, ...],
    ) -> tuple[str, ...]:
        normalized_values = tuple(value.strip() for value in values)
        routing_keys = tuple(
            normalize_routing_text(value) for value in normalized_values
        )
        if any(not key for key in routing_keys):
            raise ValueError(
                "excluded signals must contain at least one letter or number"
            )
        if len(set(routing_keys)) != len(routing_keys):
            raise ValueError("excluded signals must not contain duplicates")
        return normalized_values

    @model_validator(mode="after")
    def reject_overlapping_examples(self) -> "SkillTriggers":
        overlap = set(self.positive_examples) & set(self.negative_examples)
        if overlap:
            raise ValueError("positive and negative examples must not overlap")

        group_names = [group.name for group in self.required_signal_groups]
        if len(set(group_names)) != len(group_names):
            raise ValueError("required signal group names must be unique")

        required_keys = [
            normalize_routing_text(signal)
            for group in self.required_signal_groups
            for signal in group.any_of
        ]
        if len(set(required_keys)) != len(required_keys):
            raise ValueError(
                "required routing signals must belong to exactly one group"
            )

        excluded_keys = {
            normalize_routing_text(signal) for signal in self.excluded_signals
        }
        if set(required_keys) & excluded_keys:
            raise ValueError(
                "required and excluded routing signals must not overlap"
            )
        return self


class SkillPermissions(SkillContractModel):
    allowed_tools: tuple[str, ...] = ()

    @field_validator("allowed_tools")
    @classmethod
    def validate_tool_names(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(values)) != len(values):
            raise ValueError("allowed_tools must not contain duplicates")
        for value in values:
            if not re.fullmatch(
                r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+",
                value,
            ):
                raise ValueError(f"invalid tool name: {value!r}")
        return values


class SkillBudgets(SkillContractModel):
    max_iterations: int = Field(ge=1, le=20)
    max_tool_calls: int = Field(ge=1, le=50)
    timeout_s: float = Field(gt=0, le=300)
    max_context_tokens: int = Field(ge=1000, le=200_000)


class SkillQualityGate(SkillContractModel):
    required: bool = True
    minimum_score: int = Field(default=85, ge=0, le=100)
    allow_deterministic_fallback: bool = True

    @model_validator(mode="after")
    def validate_disabled_gate(self) -> "SkillQualityGate":
        if not self.required and self.minimum_score != 0:
            raise ValueError(
                "minimum_score must be 0 when the quality gate is disabled"
            )
        return self


class SkillModelReferences(SkillContractModel):
    input: str
    output: str

    @field_validator("input", "output")
    @classmethod
    def validate_model_reference(cls, value: str) -> str:
        if not _MODEL_REFERENCE_PATTERN.fullmatch(value):
            raise ValueError(
                "model references must use 'app.package.module:ClassName'"
            )
        return value


class SkillManifest(SkillContractModel):
    schema_version: Literal["1.0"]
    name: str
    version: str
    description: str = Field(min_length=1)
    instructions: Literal["SKILL.md"] = "SKILL.md"
    models: SkillModelReferences
    triggers: SkillTriggers
    permissions: SkillPermissions
    budgets: SkillBudgets
    quality_gate: SkillQualityGate

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not _SKILL_NAME_PATTERN.fullmatch(value):
            raise ValueError("skill name must use lowercase hyphen-case")
        return value

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        if not _SEMVER_PATTERN.fullmatch(value):
            raise ValueError("skill version must use MAJOR.MINOR.PATCH")
        return value

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str) -> str:
        return value.strip()
