"""Stable request and decision contracts for Skill routing."""

from __future__ import annotations

from enum import Enum

from pydantic import Field, field_validator, model_validator

from .models import SkillContractModel, SkillManifest, SkillTriggers


class RouteOutcome(str, Enum):
    SELECTED = "selected"
    REJECTED = "rejected"
    AMBIGUOUS = "ambiguous"


class RouteReason(str, Enum):
    MATCHED_SKILL = "matched_skill"
    NO_AVAILABLE_SKILLS = "no_available_skills"
    NO_MATCHING_SKILL = "no_matching_skill"
    MULTIPLE_SKILLS_MATCHED = "multiple_skills_matched"


class SkillRouteCandidate(SkillContractModel):
    """Only the Skill metadata needed by a routing strategy."""

    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    description: str = Field(min_length=1)
    triggers: SkillTriggers

    @field_validator("name", "version", "description")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("routing metadata must not be blank")
        return normalized

    @classmethod
    def from_manifest(cls, manifest: SkillManifest) -> "SkillRouteCandidate":
        return cls(
            name=manifest.name,
            version=manifest.version,
            description=manifest.description,
            triggers=manifest.triggers,
        )


class RouterRequest(SkillContractModel):
    utterance: str = Field(min_length=1)
    available_skills: tuple[SkillRouteCandidate, ...] = ()

    @field_validator("utterance")
    @classmethod
    def normalize_utterance(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("utterance must not be blank")
        return normalized

    @model_validator(mode="after")
    def reject_duplicate_skills(self) -> "RouterRequest":
        names = [skill.name for skill in self.available_skills]
        if len(set(names)) != len(names):
            raise ValueError("available_skills must have unique names")
        return self


class RouteEvidence(SkillContractModel):
    skill_name: str = Field(min_length=1)
    positive_signals: tuple[str, ...] = ()
    negative_signals: tuple[str, ...] = ()

    @field_validator("skill_name")
    @classmethod
    def normalize_skill_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("evidence skill_name must not be blank")
        return normalized

    @field_validator("positive_signals", "negative_signals")
    @classmethod
    def validate_signals(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(value.strip() for value in values)
        if any(not value for value in normalized):
            raise ValueError("route signals must not be blank")
        if len(set(normalized)) != len(normalized):
            raise ValueError("route signals must not contain duplicates")
        return normalized

    @model_validator(mode="after")
    def require_a_signal(self) -> "RouteEvidence":
        if not self.positive_signals and not self.negative_signals:
            raise ValueError("route evidence requires at least one signal")
        return self


class RouterDecision(SkillContractModel):
    outcome: RouteOutcome
    reason: RouteReason
    selected_skill: str | None = None
    selected_skill_version: str | None = None
    candidate_skills: tuple[str, ...] = ()
    evidence: tuple[RouteEvidence, ...] = ()
    explanation: str = Field(min_length=1)

    @field_validator("selected_skill")
    @classmethod
    def normalize_selected_skill(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("selected_skill must not be blank")
        return normalized

    @field_validator("selected_skill_version")
    @classmethod
    def normalize_selected_skill_version(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("selected_skill_version must not be blank")
        return normalized

    @field_validator("candidate_skills")
    @classmethod
    def validate_candidate_skills(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(value.strip() for value in values)
        if any(not value for value in normalized):
            raise ValueError("candidate skill names must not be blank")
        if len(set(normalized)) != len(normalized):
            raise ValueError("candidate skill names must be unique")
        return normalized

    @field_validator("explanation")
    @classmethod
    def normalize_explanation(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("explanation must not be blank")
        return normalized

    @model_validator(mode="after")
    def validate_outcome_invariants(self) -> "RouterDecision":
        evidence_names = [item.skill_name for item in self.evidence]
        if len(set(evidence_names)) != len(evidence_names):
            raise ValueError("route evidence must have unique skill names")

        if self.outcome is RouteOutcome.SELECTED:
            self._validate_selected(evidence_names)
        elif self.outcome is RouteOutcome.AMBIGUOUS:
            self._validate_ambiguous(evidence_names)
        else:
            self._validate_rejected()
        return self

    def _validate_selected(self, evidence_names: list[str]) -> None:
        if self.reason is not RouteReason.MATCHED_SKILL:
            raise ValueError("selected outcome requires matched_skill reason")
        if self.selected_skill is None:
            raise ValueError("selected outcome requires selected_skill")
        if self.selected_skill_version is None:
            raise ValueError(
                "selected outcome requires selected_skill_version"
            )
        if self.candidate_skills != (self.selected_skill,):
            raise ValueError(
                "selected outcome requires exactly the selected candidate"
            )
        if self.selected_skill not in evidence_names:
            raise ValueError("selected outcome requires evidence for the skill")
        if set(evidence_names) != set(self.candidate_skills):
            raise ValueError(
                "selected evidence names must exactly match candidate skills"
            )
        selected_evidence = next(
            item for item in self.evidence if item.skill_name == self.selected_skill
        )
        if not selected_evidence.positive_signals:
            raise ValueError("selected outcome requires positive evidence")
        if selected_evidence.negative_signals:
            raise ValueError(
                "selected candidate cannot contain exclusion evidence"
            )

    def _validate_ambiguous(self, evidence_names: list[str]) -> None:
        if self.reason is not RouteReason.MULTIPLE_SKILLS_MATCHED:
            raise ValueError(
                "ambiguous outcome requires multiple_skills_matched reason"
            )
        if self.selected_skill is not None:
            raise ValueError("ambiguous outcome cannot select a skill")
        if self.selected_skill_version is not None:
            raise ValueError("ambiguous outcome cannot select a skill version")
        if len(self.candidate_skills) < 2:
            raise ValueError("ambiguous outcome requires at least two candidates")
        if not set(self.candidate_skills).issubset(evidence_names):
            raise ValueError("ambiguous outcome requires evidence for every candidate")
        if set(evidence_names) != set(self.candidate_skills):
            raise ValueError(
                "ambiguous evidence names must exactly match candidate skills"
            )
        evidence_by_name = {item.skill_name: item for item in self.evidence}
        if any(
            not evidence_by_name[name].positive_signals
            for name in self.candidate_skills
        ):
            raise ValueError(
                "ambiguous outcome requires positive evidence for every candidate"
            )
        if any(
            evidence_by_name[name].negative_signals
            for name in self.candidate_skills
        ):
            raise ValueError(
                "ambiguous candidates cannot contain exclusion evidence"
            )

    def _validate_rejected(self) -> None:
        if self.reason not in {
            RouteReason.NO_AVAILABLE_SKILLS,
            RouteReason.NO_MATCHING_SKILL,
        }:
            raise ValueError("rejected outcome requires a rejection reason")
        if self.selected_skill is not None:
            raise ValueError("rejected outcome cannot select a skill")
        if self.selected_skill_version is not None:
            raise ValueError("rejected outcome cannot select a skill version")
        if self.candidate_skills:
            raise ValueError("rejected outcome cannot expose candidates")
        if self.reason is RouteReason.NO_AVAILABLE_SKILLS and self.evidence:
            raise ValueError("no_available_skills cannot contain route evidence")
