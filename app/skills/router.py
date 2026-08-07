"""Explainable deterministic routing over validated Skill candidates."""

from __future__ import annotations

from dataclasses import dataclass

from .routing_models import (
    RouteEvidence,
    RouteOutcome,
    RouteReason,
    RouterDecision,
    RouterRequest,
    SkillRouteCandidate,
)
from .routing_text import normalize_routing_text


@dataclass(frozen=True)
class _CandidateEvaluation:
    candidate: SkillRouteCandidate
    matched: bool
    positive_signals: tuple[str, ...]
    negative_signals: tuple[str, ...]

    @property
    def has_evidence(self) -> bool:
        return bool(self.positive_signals or self.negative_signals)

    def to_evidence(self) -> RouteEvidence:
        return RouteEvidence(
            skill_name=self.candidate.name,
            positive_signals=self.positive_signals,
            negative_signals=self.negative_signals,
        )


class DeterministicSkillRouter:
    """Match literal manifest signals without model calls or hidden scores."""

    def route(self, request: RouterRequest) -> RouterDecision:
        if not request.available_skills:
            return RouterDecision(
                outcome=RouteOutcome.REJECTED,
                reason=RouteReason.NO_AVAILABLE_SKILLS,
                explanation="No Skills are available for routing.",
            )

        utterance = normalize_routing_text(request.utterance)
        evaluations = tuple(
            self._evaluate_candidate(utterance, candidate)
            for candidate in request.available_skills
        )
        matches = tuple(item for item in evaluations if item.matched)

        if len(matches) == 1:
            match = matches[0]
            return RouterDecision(
                outcome=RouteOutcome.SELECTED,
                reason=RouteReason.MATCHED_SKILL,
                selected_skill=match.candidate.name,
                selected_skill_version=match.candidate.version,
                candidate_skills=(match.candidate.name,),
                evidence=(match.to_evidence(),),
                explanation=(
                    "Exactly one Skill satisfied every required signal group."
                ),
            )

        if len(matches) > 1:
            return RouterDecision(
                outcome=RouteOutcome.AMBIGUOUS,
                reason=RouteReason.MULTIPLE_SKILLS_MATCHED,
                candidate_skills=tuple(
                    match.candidate.name for match in matches
                ),
                evidence=tuple(match.to_evidence() for match in matches),
                explanation=(
                    "Multiple Skills satisfied every required signal group."
                ),
            )

        return RouterDecision(
            outcome=RouteOutcome.REJECTED,
            reason=RouteReason.NO_MATCHING_SKILL,
            evidence=tuple(
                item.to_evidence() for item in evaluations if item.has_evidence
            ),
            explanation=(
                "No Skill satisfied every required signal group without an "
                "exclusion."
            ),
        )

    @staticmethod
    def _evaluate_candidate(
        utterance: str,
        candidate: SkillRouteCandidate,
    ) -> _CandidateEvaluation:
        positive_signals = tuple(
            signal
            for group in candidate.triggers.required_signal_groups
            if (signal := _longest_matching_signal(utterance, group.any_of))
            is not None
        )
        negative_signals = tuple(
            signal
            for signal in candidate.triggers.excluded_signals
            if normalize_routing_text(signal) in utterance
        )
        matched = (
            len(positive_signals)
            == len(candidate.triggers.required_signal_groups)
            and not negative_signals
        )
        return _CandidateEvaluation(
            candidate=candidate,
            matched=matched,
            positive_signals=positive_signals,
            negative_signals=negative_signals,
        )


def _longest_matching_signal(
    utterance: str,
    signals: tuple[str, ...],
) -> str | None:
    matches = tuple(
        (signal, normalize_routing_text(signal))
        for signal in signals
        if normalize_routing_text(signal) in utterance
    )
    if not matches:
        return None
    return max(matches, key=lambda item: len(item[1]))[0]
