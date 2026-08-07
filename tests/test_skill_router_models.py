from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.skills.loader import load_skill
from app.skills.routing_models import (
    RouteEvidence,
    RouteOutcome,
    RouteReason,
    RouterDecision,
    RouterRequest,
    SkillRouteCandidate,
)


def recent_form_candidate() -> SkillRouteCandidate:
    loaded = load_skill("skills/recent-form-review")
    return SkillRouteCandidate.from_manifest(loaded.manifest)


def test_router_request_projects_only_routing_metadata_from_manifest():
    candidate = recent_form_candidate()
    request = RouterRequest(
        utterance="  分析我最近十局的状态  ",
        available_skills=(candidate,),
    )

    assert request.utterance == "分析我最近十局的状态"
    assert request.available_skills[0].name == "recent-form-review"
    assert request.available_skills[0].triggers.intent == "recent_form_review"
    assert not hasattr(request.available_skills[0], "permissions")


def test_router_request_rejects_blank_text_and_duplicate_skills():
    candidate = recent_form_candidate()

    with pytest.raises(ValidationError, match="utterance"):
        RouterRequest(utterance="   ")

    with pytest.raises(ValidationError, match="unique names"):
        RouterRequest(
            utterance="分析近期状态",
            available_skills=(candidate, candidate),
        )


def test_selected_decision_requires_one_candidate_and_evidence():
    decision = RouterDecision(
        outcome=RouteOutcome.SELECTED,
        reason=RouteReason.MATCHED_SKILL,
        selected_skill="recent-form-review",
        selected_skill_version="0.2.0",
        candidate_skills=("recent-form-review",),
        evidence=(
            RouteEvidence(
                skill_name="recent-form-review",
                positive_signals=("最近十局", "状态"),
            ),
        ),
        explanation="请求同时表达近期范围和状态分析。",
    )

    assert decision.selected_skill == "recent-form-review"
    assert decision.model_dump(mode="json")["outcome"] == "selected"

    with pytest.raises(ValidationError, match="requires evidence"):
        RouterDecision(
            outcome=RouteOutcome.SELECTED,
            reason=RouteReason.MATCHED_SKILL,
            selected_skill="recent-form-review",
            selected_skill_version="0.2.0",
            candidate_skills=("recent-form-review",),
            explanation="缺少证据。",
        )

    with pytest.raises(ValidationError, match="requires positive evidence"):
        RouterDecision(
            outcome=RouteOutcome.SELECTED,
            reason=RouteReason.MATCHED_SKILL,
            selected_skill="recent-form-review",
            selected_skill_version="0.2.0",
            candidate_skills=("recent-form-review",),
            evidence=(
                RouteEvidence(
                    skill_name="recent-form-review",
                    negative_signals=("请求的是单局",),
                ),
            ),
            explanation="不能仅凭负面证据选中 Skill。",
        )


def test_selected_decision_requires_version_and_non_selected_forbids_it():
    with pytest.raises(ValidationError, match="requires selected_skill_version"):
        RouterDecision(
            outcome=RouteOutcome.SELECTED,
            reason=RouteReason.MATCHED_SKILL,
            selected_skill="recent-form-review",
            candidate_skills=("recent-form-review",),
            evidence=(
                RouteEvidence(
                    skill_name="recent-form-review",
                    positive_signals=("最近十局", "状态"),
                ),
            ),
            explanation="名称不足以锁定将要执行的 Skill 版本。",
        )

    with pytest.raises(ValidationError, match="cannot select a skill version"):
        RouterDecision(
            outcome=RouteOutcome.REJECTED,
            reason=RouteReason.NO_MATCHING_SKILL,
            selected_skill_version="0.2.0",
            explanation="拒绝结果不能携带选中版本。",
        )


def test_rejected_decision_cannot_select_or_expose_candidates():
    decision = RouterDecision(
        outcome=RouteOutcome.REJECTED,
        reason=RouteReason.NO_MATCHING_SKILL,
        evidence=(
            RouteEvidence(
                skill_name="recent-form-review",
                negative_signals=("当前版本胜率",),
            ),
        ),
        explanation="当前没有版本 Meta Skill。",
    )
    assert decision.selected_skill is None

    with pytest.raises(ValidationError, match="cannot select"):
        RouterDecision(
            outcome=RouteOutcome.REJECTED,
            reason=RouteReason.NO_MATCHING_SKILL,
            selected_skill="recent-form-review",
            explanation="非法选择。",
        )

    with pytest.raises(ValidationError, match="cannot contain route evidence"):
        RouterDecision(
            outcome=RouteOutcome.REJECTED,
            reason=RouteReason.NO_AVAILABLE_SKILLS,
            evidence=(
                RouteEvidence(
                    skill_name="recent-form-review",
                    negative_signals=("无候选",),
                ),
            ),
            explanation="没有可用 Skill。",
        )


@pytest.mark.parametrize(
    ("outcome", "reason", "decision_fields", "message"),
    [
        (
            RouteOutcome.SELECTED,
            RouteReason.NO_MATCHING_SKILL,
            {
                "selected_skill": "recent-form-review",
                "selected_skill_version": "0.2.0",
                "candidate_skills": ("recent-form-review",),
                "evidence": (
                    RouteEvidence(
                        skill_name="recent-form-review",
                        positive_signals=("最近状态",),
                    ),
                ),
            },
            "requires matched_skill reason",
        ),
        (
            RouteOutcome.AMBIGUOUS,
            RouteReason.MATCHED_SKILL,
            {
                "candidate_skills": (
                    "recent-form-review",
                    "single-match-review",
                ),
                "evidence": (
                    RouteEvidence(
                        skill_name="recent-form-review",
                        positive_signals=("最近",),
                    ),
                    RouteEvidence(
                        skill_name="single-match-review",
                        positive_signals=("这一局",),
                    ),
                ),
            },
            "requires multiple_skills_matched reason",
        ),
        (
            RouteOutcome.REJECTED,
            RouteReason.MATCHED_SKILL,
            {},
            "requires a rejection reason",
        ),
    ],
)
def test_route_outcome_and_reason_must_form_a_legal_pair(
    outcome: RouteOutcome,
    reason: RouteReason,
    decision_fields: dict,
    message: str,
):
    with pytest.raises(ValidationError, match=message):
        RouterDecision(
            outcome=outcome,
            reason=reason,
            explanation="状态与原因码不能互相矛盾。",
            **decision_fields,
        )


def test_ambiguous_decision_requires_multiple_candidates_and_evidence():
    decision = RouterDecision(
        outcome=RouteOutcome.AMBIGUOUS,
        reason=RouteReason.MULTIPLE_SKILLS_MATCHED,
        candidate_skills=("recent-form-review", "single-match-review"),
        evidence=(
            RouteEvidence(
                skill_name="recent-form-review",
                positive_signals=("最近",),
            ),
            RouteEvidence(
                skill_name="single-match-review",
                positive_signals=("这一局",),
            ),
        ),
        explanation="请求同时包含近期范围和单局范围。",
    )
    assert decision.outcome is RouteOutcome.AMBIGUOUS
    assert decision.selected_skill is None

    with pytest.raises(ValidationError, match="at least two candidates"):
        RouterDecision(
            outcome=RouteOutcome.AMBIGUOUS,
            reason=RouteReason.MULTIPLE_SKILLS_MATCHED,
            candidate_skills=("recent-form-review",),
            evidence=(
                RouteEvidence(
                    skill_name="recent-form-review",
                    positive_signals=("最近",),
                ),
            ),
            explanation="候选不足。",
        )


@pytest.mark.parametrize(
    ("outcome", "candidate_skills"),
    [
        (RouteOutcome.SELECTED, ("recent-form-review",)),
        (
            RouteOutcome.AMBIGUOUS,
            ("recent-form-review", "training-plan"),
        ),
    ],
)
def test_matched_candidates_cannot_contain_exclusion_evidence(
    outcome: RouteOutcome,
    candidate_skills: tuple[str, ...],
):
    evidence = [
        RouteEvidence(
            skill_name="recent-form-review",
            positive_signals=("最近十局", "状态"),
            negative_signals=("这一场",),
        )
    ]
    if outcome is RouteOutcome.AMBIGUOUS:
        evidence.append(
            RouteEvidence(
                skill_name="training-plan",
                positive_signals=("训练重点",),
            )
        )

    with pytest.raises(ValidationError, match="cannot contain exclusion evidence"):
        RouterDecision(
            outcome=outcome,
            reason=(
                RouteReason.MATCHED_SKILL
                if outcome is RouteOutcome.SELECTED
                else RouteReason.MULTIPLE_SKILLS_MATCHED
            ),
            selected_skill=(
                "recent-form-review"
                if outcome is RouteOutcome.SELECTED
                else None
            ),
            selected_skill_version=(
                "0.2.0" if outcome is RouteOutcome.SELECTED else None
            ),
            candidate_skills=candidate_skills,
            evidence=tuple(evidence),
            explanation="命中排除信号的 Skill 不能成为匹配候选。",
        )

    with pytest.raises(ValidationError, match="positive evidence for every"):
        RouterDecision(
            outcome=RouteOutcome.AMBIGUOUS,
            reason=RouteReason.MULTIPLE_SKILLS_MATCHED,
            candidate_skills=("recent-form-review", "single-match-review"),
            evidence=(
                RouteEvidence(
                    skill_name="recent-form-review",
                    positive_signals=("最近",),
                ),
                RouteEvidence(
                    skill_name="single-match-review",
                    negative_signals=("没有具体 match_id",),
                ),
            ),
            explanation="不能把只有负面证据的 Skill 列为歧义候选。",
        )


def test_route_evidence_rejects_blank_or_empty_signals():
    with pytest.raises(ValidationError, match="at least one signal"):
        RouteEvidence(skill_name="recent-form-review")

    with pytest.raises(ValidationError, match="must not be blank"):
        RouteEvidence(
            skill_name="recent-form-review",
            positive_signals=("  ",),
        )


def test_router_contract_rejects_text_that_is_blank_after_normalization():
    candidate = recent_form_candidate()

    with pytest.raises(ValidationError, match="routing metadata must not be blank"):
        SkillRouteCandidate(
            name=candidate.name,
            version=candidate.version,
            description="   ",
            triggers=candidate.triggers,
        )

    with pytest.raises(ValidationError, match="skill_name must not be blank"):
        RouteEvidence(skill_name="   ", positive_signals=("最近",))

    with pytest.raises(ValidationError, match="explanation must not be blank"):
        RouterDecision(
            outcome=RouteOutcome.REJECTED,
            reason=RouteReason.NO_AVAILABLE_SKILLS,
            explanation="   ",
        )


def test_router_contract_rejects_duplicate_decision_identity_and_evidence():
    with pytest.raises(ValidationError, match="candidate skill names must be unique"):
        RouterDecision(
            outcome=RouteOutcome.AMBIGUOUS,
            reason=RouteReason.MULTIPLE_SKILLS_MATCHED,
            candidate_skills=("recent-form-review", "recent-form-review"),
            explanation="重复候选没有独立含义。",
        )

    with pytest.raises(ValidationError, match="unique skill names"):
        RouterDecision(
            outcome=RouteOutcome.SELECTED,
            reason=RouteReason.MATCHED_SKILL,
            selected_skill="recent-form-review",
            selected_skill_version="0.2.0",
            candidate_skills=("recent-form-review",),
            evidence=(
                RouteEvidence(
                    skill_name="recent-form-review",
                    positive_signals=("最近",),
                ),
                RouteEvidence(
                    skill_name="recent-form-review",
                    positive_signals=("状态",),
                ),
            ),
            explanation="同一 Skill 只能有一组归并后的证据。",
        )


@pytest.mark.parametrize(
    ("outcome", "selected_skill", "candidate_skills", "evidence"),
    [
        (
            RouteOutcome.SELECTED,
            "recent-form-review",
            ("recent-form-review",),
            (
                RouteEvidence(
                    skill_name="recent-form-review",
                    positive_signals=("最近十局", "状态"),
                ),
                RouteEvidence(
                    skill_name="single-match-review",
                    positive_signals=("这一场",),
                ),
            ),
        ),
        (
            RouteOutcome.AMBIGUOUS,
            None,
            ("recent-form-review", "single-match-review"),
            (
                RouteEvidence(
                    skill_name="recent-form-review",
                    positive_signals=("最近十局", "状态"),
                ),
                RouteEvidence(
                    skill_name="single-match-review",
                    positive_signals=("这一场", "复盘"),
                ),
                RouteEvidence(
                    skill_name="training-plan",
                    positive_signals=("训练计划",),
                ),
            ),
        ),
    ],
)
def test_matched_decision_evidence_identity_must_equal_candidate_identity(
    outcome: RouteOutcome,
    selected_skill: str | None,
    candidate_skills: tuple[str, ...],
    evidence: tuple[RouteEvidence, ...],
):
    with pytest.raises(ValidationError, match="exactly match candidate skills"):
        RouterDecision(
            outcome=outcome,
            reason=(
                RouteReason.MATCHED_SKILL
                if outcome is RouteOutcome.SELECTED
                else RouteReason.MULTIPLE_SKILLS_MATCHED
            ),
            selected_skill=selected_skill,
            selected_skill_version=(
                "0.2.0" if outcome is RouteOutcome.SELECTED else None
            ),
            candidate_skills=candidate_skills,
            evidence=evidence,
            explanation="命中决策不能附带不属于候选集合的额外证据。",
        )
