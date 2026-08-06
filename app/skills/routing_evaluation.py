"""Versioned exact-match evaluation for Skill routing strategies."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Protocol

from .routing_models import (
    RouteOutcome,
    RouteReason,
    RouterDecision,
    RouterRequest,
    SkillRouteCandidate,
)


class RoutingStrategy(Protocol):
    def route(self, request: RouterRequest) -> RouterDecision: ...


class RoutingDatasetRole(str, Enum):
    DEVELOPMENT = "development"
    HELD_OUT = "held_out"


@dataclass(frozen=True)
class SkillVersionSnapshot:
    name: str
    version: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("snapshot Skill name must not be empty")
        if not self.version.strip():
            raise ValueError("snapshot Skill version must not be empty")


@dataclass(frozen=True)
class CandidateSnapshot:
    snapshot_id: str
    skills: tuple[SkillVersionSnapshot, ...]

    def __post_init__(self) -> None:
        if not self.snapshot_id.strip():
            raise ValueError("candidate snapshot_id must not be empty")
        if not self.skills:
            raise ValueError("candidate snapshot must contain at least one Skill")
        names = [skill.name for skill in self.skills]
        if len(set(names)) != len(names):
            raise ValueError("candidate snapshot Skill names must be unique")


@dataclass(frozen=True)
class RoutingCase:
    case_id: str
    utterance: str
    category: str
    expected_outcome: RouteOutcome
    expected_reason: RouteReason
    expected_selected_skill: str | None
    expected_candidate_skills: tuple[str, ...]
    available_skill_names: tuple[str, ...] | None = None
    contamination_sources: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.case_id.strip():
            raise ValueError("routing case_id must not be empty")
        if not self.utterance.strip():
            raise ValueError("routing utterance must not be empty")
        if not self.category.strip():
            raise ValueError("routing category must not be empty")
        if len(set(self.expected_candidate_skills)) != len(
            self.expected_candidate_skills
        ):
            raise ValueError("expected candidate Skill names must be unique")
        if self.available_skill_names is not None and len(
            set(self.available_skill_names)
        ) != len(self.available_skill_names):
            raise ValueError("available Skill names must be unique")
        if any(not source.strip() for source in self.contamination_sources):
            raise ValueError("contamination sources must not be blank")
        if len(set(self.contamination_sources)) != len(
            self.contamination_sources
        ):
            raise ValueError("contamination sources must be unique")
        self._validate_expected_decision()

    def _validate_expected_decision(self) -> None:
        if self.expected_outcome is RouteOutcome.SELECTED:
            if self.expected_reason is not RouteReason.MATCHED_SKILL:
                raise ValueError("selected case requires matched_skill reason")
            if self.expected_selected_skill is None:
                raise ValueError("selected case requires expected_selected_skill")
            if self.expected_candidate_skills != (
                self.expected_selected_skill,
            ):
                raise ValueError(
                    "selected case requires exactly the selected candidate"
                )
            return

        if self.expected_outcome is RouteOutcome.AMBIGUOUS:
            if self.expected_reason is not RouteReason.MULTIPLE_SKILLS_MATCHED:
                raise ValueError(
                    "ambiguous case requires multiple_skills_matched reason"
                )
            if self.expected_selected_skill is not None:
                raise ValueError("ambiguous case cannot select a Skill")
            if len(self.expected_candidate_skills) < 2:
                raise ValueError(
                    "ambiguous case requires at least two candidates"
                )
            return

        if self.expected_reason not in {
            RouteReason.NO_AVAILABLE_SKILLS,
            RouteReason.NO_MATCHING_SKILL,
        }:
            raise ValueError("rejected case requires a rejection reason")
        if self.expected_selected_skill is not None:
            raise ValueError("rejected case cannot select a Skill")
        if self.expected_candidate_skills:
            raise ValueError("rejected case cannot expose candidates")


@dataclass(frozen=True)
class RoutingCaseResult:
    case_id: str
    category: str
    expected_outcome: RouteOutcome
    actual_outcome: RouteOutcome
    expected_reason: RouteReason
    actual_reason: RouteReason
    expected_selected_skill: str | None
    actual_selected_skill: str | None
    expected_candidate_skills: tuple[str, ...]
    actual_candidate_skills: tuple[str, ...]
    exact_match: bool


@dataclass(frozen=True)
class RoutingEvaluation:
    cases: tuple[RoutingCaseResult, ...]
    exact_match_accuracy: float
    selection_accuracy: float
    rejection_accuracy: float
    ambiguity_accuracy: float
    false_selection_rate: float


@dataclass(frozen=True)
class RoutingDataset:
    dataset_id: str
    dataset_version: str
    role: RoutingDatasetRole
    calibration_excluded: bool
    created_at: str
    candidate_snapshot: CandidateSnapshot
    contamination_notes: tuple[str, ...]
    cases: tuple[RoutingCase, ...]
    metadata: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not self.dataset_id.strip():
            raise ValueError("routing dataset_id must not be empty")
        if not self.dataset_version.strip():
            raise ValueError("routing dataset_version must not be empty")
        try:
            date.fromisoformat(self.created_at)
        except ValueError as exc:
            raise ValueError("routing created_at must be an ISO date") from exc
        if any(not note.strip() for note in self.contamination_notes):
            raise ValueError("contamination notes must not be blank")
        if self.role is RoutingDatasetRole.DEVELOPMENT:
            if self.calibration_excluded:
                raise ValueError(
                    "development dataset cannot be calibration-excluded"
                )
        elif not self.calibration_excluded:
            raise ValueError("held-out dataset must be calibration-excluded")
        if self.role is RoutingDatasetRole.HELD_OUT and any(
            case.contamination_sources for case in self.cases
        ):
            raise ValueError(
                "held-out cases cannot declare calibration contamination"
            )
        case_ids = [case.case_id for case in self.cases]
        if len(set(case_ids)) != len(case_ids):
            raise ValueError("routing dataset case_ids must be unique")
        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(dict(self.metadata)),
        )


def load_routing_dataset(path: Path) -> RoutingDataset:
    payload = json.loads(path.read_text(encoding="utf-8"))
    calibration_excluded = payload["calibration_excluded"]
    if not isinstance(calibration_excluded, bool):
        raise ValueError("calibration_excluded must be a boolean")
    cases = tuple(_load_case(row) for row in payload["cases"])
    if not cases:
        raise ValueError("routing dataset must contain at least one case")
    declared_case_count = payload["case_count"]
    if not isinstance(declared_case_count, int) or isinstance(
        declared_case_count, bool
    ):
        raise ValueError("case_count must be an integer")
    if declared_case_count != len(cases):
        raise ValueError("case_count does not match routing cases")
    candidate_snapshot = _load_candidate_snapshot(payload["candidate_snapshot"])
    contamination_notes = tuple(
        str(note) for note in payload["contamination_notes"]
    )
    return RoutingDataset(
        dataset_id=str(payload["dataset_id"]),
        dataset_version=str(payload["dataset_version"]),
        role=RoutingDatasetRole(payload["role"]),
        calibration_excluded=calibration_excluded,
        created_at=str(payload["created_at"]),
        candidate_snapshot=candidate_snapshot,
        contamination_notes=contamination_notes,
        cases=cases,
        metadata={
            key: value
            for key, value in payload.items()
            if key
            not in {
                "dataset_id",
                "dataset_version",
                "role",
                "calibration_excluded",
                "created_at",
                "candidate_snapshot",
                "contamination_notes",
                "case_count",
                "cases",
            }
        },
    )


def validate_dataset_usage(
    dataset: RoutingDataset,
    expected_role: RoutingDatasetRole,
    *,
    confirm_rules_frozen: bool = False,
) -> None:
    if dataset.role is not expected_role:
        raise ValueError(
            f"routing dataset role is {dataset.role.value}, expected "
            f"{expected_role.value}"
        )
    if (
        expected_role is RoutingDatasetRole.HELD_OUT
        and not confirm_rules_frozen
    ):
        raise ValueError(
            "held-out evaluation requires explicit confirmation that routing "
            "rules are frozen"
        )


def validate_candidate_snapshot(
    dataset: RoutingDataset,
    available_skills: tuple[SkillRouteCandidate, ...],
) -> None:
    expected = tuple(
        sorted(
            (skill.name, skill.version)
            for skill in dataset.candidate_snapshot.skills
        )
    )
    actual = tuple(
        sorted((skill.name, skill.version) for skill in available_skills)
    )
    if actual != expected:
        raise ValueError(
            "routing candidate snapshot mismatch: "
            f"expected {expected}, got {actual}"
        )


def evaluate_routing(
    strategy: RoutingStrategy,
    available_skills: tuple[SkillRouteCandidate, ...],
    cases: tuple[RoutingCase, ...],
) -> RoutingEvaluation:
    candidates_by_name = {
        candidate.name: candidate for candidate in available_skills
    }
    if len(candidates_by_name) != len(available_skills):
        raise ValueError("available routing Skill names must be unique")
    results = tuple(
        _evaluate_case(strategy, candidates_by_name, case) for case in cases
    )
    expected_selections = tuple(
        result
        for result in results
        if result.expected_outcome is RouteOutcome.SELECTED
    )
    expected_rejections = tuple(
        result
        for result in results
        if result.expected_outcome is RouteOutcome.REJECTED
    )
    expected_ambiguities = tuple(
        result
        for result in results
        if result.expected_outcome is RouteOutcome.AMBIGUOUS
    )
    return RoutingEvaluation(
        cases=results,
        exact_match_accuracy=_mean(result.exact_match for result in results),
        selection_accuracy=_mean(
            result.exact_match for result in expected_selections
        ),
        rejection_accuracy=_mean(
            result.exact_match for result in expected_rejections
        ),
        ambiguity_accuracy=_mean(
            result.exact_match for result in expected_ambiguities
        ),
        false_selection_rate=_mean(
            result.actual_outcome is RouteOutcome.SELECTED
            for result in expected_rejections
        ),
    )


def _load_case(row: Mapping[str, Any]) -> RoutingCase:
    available_names = row.get("available_skill_names")
    return RoutingCase(
        case_id=str(row["case_id"]),
        utterance=str(row["utterance"]),
        category=str(row["category"]),
        available_skill_names=(
            None
            if available_names is None
            else tuple(str(name) for name in available_names)
        ),
        expected_outcome=RouteOutcome(row["expected_outcome"]),
        expected_reason=RouteReason(row["expected_reason"]),
        expected_selected_skill=row.get("expected_selected_skill"),
        expected_candidate_skills=tuple(
            str(name) for name in row.get("expected_candidate_skills", [])
        ),
        contamination_sources=tuple(
            str(source) for source in row.get("contamination_sources", [])
        ),
    )


def _load_candidate_snapshot(payload: Mapping[str, Any]) -> CandidateSnapshot:
    return CandidateSnapshot(
        snapshot_id=str(payload["snapshot_id"]),
        skills=tuple(
            SkillVersionSnapshot(
                name=str(skill["name"]),
                version=str(skill["version"]),
            )
            for skill in payload["skills"]
        ),
    )


def _evaluate_case(
    strategy: RoutingStrategy,
    candidates_by_name: Mapping[str, SkillRouteCandidate],
    case: RoutingCase,
) -> RoutingCaseResult:
    expected_names = set(case.expected_candidate_skills)
    if case.expected_selected_skill is not None:
        expected_names.add(case.expected_selected_skill)
    unknown_expected = expected_names - set(candidates_by_name)
    if unknown_expected:
        names = ", ".join(sorted(unknown_expected))
        raise ValueError(f"routing case expects unknown Skill: {names}")

    if case.available_skill_names is None:
        candidates = tuple(candidates_by_name.values())
    else:
        unknown = set(case.available_skill_names) - set(candidates_by_name)
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValueError(f"routing case references unknown Skill: {names}")
        candidates = tuple(
            candidates_by_name[name] for name in case.available_skill_names
        )

    decision = strategy.route(
        RouterRequest(
            utterance=case.utterance,
            available_skills=candidates,
        )
    )
    candidate_match = (
        tuple(sorted(decision.candidate_skills))
        == tuple(sorted(case.expected_candidate_skills))
        if case.expected_outcome is RouteOutcome.AMBIGUOUS
        else decision.candidate_skills == case.expected_candidate_skills
    )
    exact_match = (
        decision.outcome is case.expected_outcome
        and decision.reason is case.expected_reason
        and decision.selected_skill == case.expected_selected_skill
        and candidate_match
    )
    return RoutingCaseResult(
        case_id=case.case_id,
        category=case.category,
        expected_outcome=case.expected_outcome,
        actual_outcome=decision.outcome,
        expected_reason=case.expected_reason,
        actual_reason=decision.reason,
        expected_selected_skill=case.expected_selected_skill,
        actual_selected_skill=decision.selected_skill,
        expected_candidate_skills=case.expected_candidate_skills,
        actual_candidate_skills=decision.candidate_skills,
        exact_match=exact_match,
    )


def _mean(values) -> float:
    rows = tuple(bool(value) for value in values)
    return round(sum(rows) / len(rows), 6) if rows else 0.0
