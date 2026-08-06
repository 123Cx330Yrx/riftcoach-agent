from __future__ import annotations

from app.skills.catalog import SkillCatalog
from app.skills.models import SkillTriggerGroup, SkillTriggers
from app.skills.router import DeterministicSkillRouter
from app.skills.routing_models import (
    RouteOutcome,
    RouteReason,
    RouterRequest,
    SkillRouteCandidate,
)


def recent_form_candidate() -> SkillRouteCandidate:
    return SkillCatalog.from_directory("skills").route_candidates[0]


def synthetic_candidate(
    name: str,
    *groups: tuple[str, tuple[str, ...]],
    excluded_signals: tuple[str, ...] = (),
) -> SkillRouteCandidate:
    return SkillRouteCandidate(
        name=name,
        version="0.1.0",
        description=f"Synthetic candidate for {name} routing tests.",
        triggers=SkillTriggers(
            intent=name.replace("-", "_"),
            positive_examples=(f"positive example for {name}",),
            negative_examples=(f"negative example for {name}",),
            required_signal_groups=tuple(
                SkillTriggerGroup(name=group_name, any_of=signals)
                for group_name, signals in groups
            ),
            excluded_signals=excluded_signals,
        ),
    )


def test_router_rejects_when_no_skills_are_available():
    decision = DeterministicSkillRouter().route(
        RouterRequest(
            utterance="分析我最近十局的状态",
            available_skills=(),
        )
    )

    assert decision.outcome is RouteOutcome.REJECTED
    assert decision.reason is RouteReason.NO_AVAILABLE_SKILLS
    assert decision.evidence == ()


def test_router_selects_one_skill_only_after_every_group_matches():
    decision = DeterministicSkillRouter().route(
        RouterRequest(
            utterance="请分析一下我最近十局的状态",
            available_skills=(recent_form_candidate(),),
        )
    )

    assert decision.outcome is RouteOutcome.SELECTED
    assert decision.reason is RouteReason.MATCHED_SKILL
    assert decision.selected_skill == "recent-form-review"
    assert decision.candidate_skills == ("recent-form-review",)
    assert decision.evidence[0].positive_signals == ("最近十局", "状态")
    assert decision.evidence[0].negative_signals == ()


def test_router_rejects_partial_match_but_preserves_partial_evidence():
    decision = DeterministicSkillRouter().route(
        RouterRequest(
            utterance="我最近换了键盘",
            available_skills=(recent_form_candidate(),),
        )
    )

    assert decision.outcome is RouteOutcome.REJECTED
    assert decision.reason is RouteReason.NO_MATCHING_SKILL
    assert decision.evidence[0].positive_signals == ("最近",)
    assert decision.evidence[0].negative_signals == ()


def test_router_exclusion_vetoes_an_otherwise_complete_match():
    decision = DeterministicSkillRouter().route(
        RouterRequest(
            utterance="分析最近十局里这一场的状态",
            available_skills=(recent_form_candidate(),),
        )
    )

    assert decision.outcome is RouteOutcome.REJECTED
    assert decision.reason is RouteReason.NO_MATCHING_SKILL
    assert decision.evidence[0].positive_signals == ("最近十局", "状态")
    assert decision.evidence[0].negative_signals == ("这一场",)


def test_domain_exclusion_vetoes_an_otherwise_complete_literal_match():
    decision = DeterministicSkillRouter().route(
        RouterRequest(
            utterance="最近天气状态怎么样",
            available_skills=(recent_form_candidate(),),
        )
    )

    assert decision.outcome is RouteOutcome.REJECTED
    assert decision.reason is RouteReason.NO_MATCHING_SKILL
    assert decision.evidence[0].positive_signals == ("最近", "怎么样")
    assert decision.evidence[0].negative_signals == ("天气",)


def test_excluded_candidate_cannot_create_ambiguity_with_a_valid_match():
    training_candidate = synthetic_candidate(
        "training-plan",
        ("training_goal", ("训练重点", "训练计划")),
    )
    decision = DeterministicSkillRouter().route(
        RouterRequest(
            utterance="根据最近十局里这一场的状态给我训练重点",
            available_skills=(recent_form_candidate(), training_candidate),
        )
    )

    assert decision.outcome is RouteOutcome.SELECTED
    assert decision.reason is RouteReason.MATCHED_SKILL
    assert decision.selected_skill == "training-plan"
    assert decision.candidate_skills == ("training-plan",)
    assert tuple(item.skill_name for item in decision.evidence) == (
        "training-plan",
    )


def test_router_rejects_without_fabricating_evidence_when_nothing_matches():
    decision = DeterministicSkillRouter().route(
        RouterRequest(
            utterance="上海明天会下雨吗",
            available_skills=(recent_form_candidate(),),
        )
    )

    assert decision.outcome is RouteOutcome.REJECTED
    assert decision.reason is RouteReason.NO_MATCHING_SKILL
    assert decision.evidence == ()


def test_router_returns_ambiguous_instead_of_breaking_a_tie():
    training_candidate = synthetic_candidate(
        "training-plan",
        ("training_goal", ("训练重点", "训练计划")),
    )
    decision = DeterministicSkillRouter().route(
        RouterRequest(
            utterance="根据最近十局的状态给我一个训练重点",
            available_skills=(recent_form_candidate(), training_candidate),
        )
    )

    assert decision.outcome is RouteOutcome.AMBIGUOUS
    assert decision.reason is RouteReason.MULTIPLE_SKILLS_MATCHED
    assert decision.selected_skill is None
    assert decision.candidate_skills == (
        "recent-form-review",
        "training-plan",
    )
    assert tuple(item.skill_name for item in decision.evidence) == (
        "recent-form-review",
        "training-plan",
    )


def test_router_candidate_order_never_breaks_an_ambiguous_tie():
    recent_candidate = recent_form_candidate()
    training_candidate = synthetic_candidate(
        "training-plan",
        ("training_goal", ("训练重点", "训练计划")),
    )

    for candidates in (
        (recent_candidate, training_candidate),
        (training_candidate, recent_candidate),
    ):
        decision = DeterministicSkillRouter().route(
            RouterRequest(
                utterance="根据最近十局的状态给我一个训练重点",
                available_skills=candidates,
            )
        )

        assert decision.outcome is RouteOutcome.AMBIGUOUS
        assert decision.reason is RouteReason.MULTIPLE_SKILLS_MATCHED
        assert decision.selected_skill is None
        assert set(decision.candidate_skills) == {
            "recent-form-review",
            "training-plan",
        }


def test_router_normalizes_text_and_keeps_the_longest_group_signal():
    candidate = synthetic_candidate(
        "single-match-review",
        ("match_scope", ("match", "MATCH ID")),
        ("review_goal", ("review",)),
    )
    decision = DeterministicSkillRouter().route(
        RouterRequest(
            utterance="Please REVIEW match_id KR_123",
            available_skills=(candidate,),
        )
    )

    assert decision.outcome is RouteOutcome.SELECTED
    assert decision.evidence[0].positive_signals == ("MATCH ID", "review")
