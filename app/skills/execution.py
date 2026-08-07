"""Fail-closed boundary between Skill routing and later Agent execution."""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from app.harness.artifact_content import (
    encode_json_artifact,
    encode_text_artifact,
    sha256_hex,
)
from app.harness.models import ArtifactKind
from app.harness.run_ids import normalize_run_id

from .catalog import SkillCatalog
from .loader import LoadedSkill
from .models import SkillContractModel
from .routing_models import RouteOutcome, RouterDecision
from .text_contracts import normalize_required_text


_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class SkillExecutionBoundaryError(ValueError):
    """Raised before any Skill, tool, model, or Harness run is executed."""


class InputArtifactCommitment(SkillContractModel):
    """Identity and content digest for one future Harness input Artifact."""

    kind: ArtifactKind
    schema_version: str = Field(min_length=1)
    sha256: str

    @field_validator("schema_version")
    @classmethod
    def normalize_schema_version(cls, value: str) -> str:
        return normalize_required_text(value, field_name="schema_version")

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if not _SHA256_PATTERN.fullmatch(value):
            raise ValueError("sha256 must be a lowercase SHA-256 hex digest")
        return value


class SkillInputArtifactBinding(SkillContractModel):
    """Content commitment for the two Harness inputs owned by one run."""

    run_id: str
    player_summary: InputArtifactCommitment
    deterministic_report: InputArtifactCommitment

    @field_validator("run_id")
    @classmethod
    def normalize_binding_run_id(cls, value: str) -> str:
        return normalize_run_id(value)

    @model_validator(mode="after")
    def validate_input_kinds(self) -> "SkillInputArtifactBinding":
        if self.player_summary.kind is not ArtifactKind.PLAYER_SUMMARY:
            raise ValueError(
                "player_summary binding must use the player_summary kind"
            )
        if (
            self.deterministic_report.kind
            is not ArtifactKind.DETERMINISTIC_REPORT
        ):
            raise ValueError(
                "deterministic_report binding must use the "
                "deterministic_report kind"
            )
        return self

    @classmethod
    def from_content(
        cls,
        *,
        run_id: str,
        player_summary: Mapping[str, Any],
        deterministic_report: str,
    ) -> "SkillInputArtifactBinding":
        schema_version = player_summary.get("schema_version")
        if not isinstance(schema_version, str) or not schema_version.strip():
            raise ValueError(
                "player_summary schema_version must be a non-blank string"
            )
        return cls(
            run_id=run_id,
            player_summary=InputArtifactCommitment(
                kind=ArtifactKind.PLAYER_SUMMARY,
                schema_version=schema_version,
                sha256=sha256_hex(encode_json_artifact(player_summary)),
            ),
            deterministic_report=InputArtifactCommitment(
                kind=ArtifactKind.DETERMINISTIC_REPORT,
                schema_version="1.0",
                sha256=sha256_hex(
                    encode_text_artifact(deterministic_report)
                ),
            ),
        )


class SkillExecutionRequest(SkillContractModel):
    """Untrusted application request presented to the execution boundary."""

    run_id: str
    user_utterance: str = Field(min_length=1)
    router_decision: RouterDecision
    input_payload: dict[str, Any]
    input_artifacts: SkillInputArtifactBinding

    @field_validator("run_id")
    @classmethod
    def normalize_request_run_id(cls, value: str) -> str:
        return normalize_run_id(value)

    @field_validator("user_utterance")
    @classmethod
    def normalize_user_utterance(cls, value: str) -> str:
        return normalize_required_text(value, field_name="user_utterance")

    @model_validator(mode="after")
    def bind_one_run_identity(self) -> "SkillExecutionRequest":
        if self.run_id != self.input_artifacts.run_id:
            raise ValueError("request run_id must match input artifact run_id")
        return self


@dataclass(frozen=True)
class ValidatedSkillExecution:
    """Catalog-backed Skill input safe for the next composition checkpoint."""

    run_id: str
    user_utterance: str
    skill: LoadedSkill
    input_artifacts: SkillInputArtifactBinding
    _typed_input: BaseModel = field(repr=False)

    @property
    def typed_input(self) -> BaseModel:
        return self._typed_input.model_copy(deep=True)


class SkillExecutionBoundary:
    """Validate identity, typed input, and artifact content before execution."""

    def __init__(self, catalog: SkillCatalog) -> None:
        self._catalog = catalog

    def validate(
        self,
        request: SkillExecutionRequest,
    ) -> ValidatedSkillExecution:
        decision = request.router_decision
        if decision.outcome is not RouteOutcome.SELECTED:
            raise SkillExecutionBoundaryError(
                "Skill execution requires a selected Router decision"
            )

        skill_name = decision.selected_skill
        skill_version = decision.selected_skill_version
        if skill_name is None or skill_version is None:
            raise SkillExecutionBoundaryError(
                "selected Router decision must bind Skill name and version"
            )

        skill = self._catalog.get(skill_name)
        if skill is None:
            raise SkillExecutionBoundaryError(
                f"selected Skill {skill_name!r} is not in the Catalog"
            )
        if skill.manifest.version != skill_version:
            raise SkillExecutionBoundaryError(
                "selected Skill version mismatch: "
                f"Router chose {skill_version}, Catalog has "
                f"{skill.manifest.version}"
            )

        try:
            safe_run_id = normalize_run_id(request.run_id)
            user_utterance = normalize_required_text(
                request.user_utterance,
                field_name="user_utterance",
            )
        except ValueError as exc:
            raise SkillExecutionBoundaryError(
                "Skill execution request identity is invalid"
            ) from exc
        if safe_run_id != request.input_artifacts.run_id:
            raise SkillExecutionBoundaryError(
                "request run_id does not match input artifact binding"
            )

        try:
            typed_input = skill.input_model.model_validate(
                copy.deepcopy(request.input_payload)
            )
        except ValidationError as exc:
            raise SkillExecutionBoundaryError(
                f"Skill input validation failed for {skill_name!r}"
            ) from exc

        expected_binding = SkillInputArtifactBinding.from_content(
            run_id=safe_run_id,
            player_summary=typed_input.player_summary,
            deterministic_report=typed_input.deterministic_report,
        )
        if request.input_artifacts != expected_binding:
            raise SkillExecutionBoundaryError(
                "Skill input artifact binding mismatch"
            )

        return ValidatedSkillExecution(
            run_id=safe_run_id,
            user_utterance=user_utterance,
            skill=skill,
            input_artifacts=expected_binding,
            _typed_input=typed_input.model_copy(deep=True),
        )
