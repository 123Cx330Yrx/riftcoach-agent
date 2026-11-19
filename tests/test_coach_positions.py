import copy

import pytest

from app.product.coach_positions import position_context
from app.evaluation.coach_real_data_golden_slice import _training_plan


def row(role, champion="Ahri", included=True):
    return {"role": role, "champion_name_en": champion, "included_in_aggregate": included}


def test_observed_roles_are_not_preference_or_autofill():
    summary = {"matches": [row("MIDDLE"), row("MIDDLE"), row("UTILITY", "Camille")]}
    original = copy.deepcopy(summary)
    result = position_context(summary)
    assert [(r.position, r.games) for r in result.observed] == [("mid", 2), ("support", 1)]
    assert result.long_term_main_position is None
    assert result.autofill_intent == "unknown"
    assert result.goal_source == "unspecified"
    assert result.sample_scope == "selected_matches_only"
    assert summary == original


def test_explicit_transition_does_not_relabel_matches():
    result = position_context({"matches": [row("mid")]}, training_positions=("jungle", "support"))
    assert result.training_positions == ("jungle", "support")
    assert result.goal_source == "explicit_request"
    assert result.observed[0].position == "mid"


@pytest.mark.parametrize("roles", [("unknown",), ("mid", "mid"), ["mid"], ("MIDDLE",)])
def test_reject_invalid_or_ambiguous_goals(roles):
    with pytest.raises(ValueError, match="training_positions_invalid"):
        position_context({"matches": []}, training_positions=roles)


def test_unknown_and_excluded_roles_never_default_to_mid():
    result = position_context({"matches": [row("NONE"), row("mid", included=False)]})
    assert result.observed == ()
    assert result.unknown_position_games == 1
    assert result.excluded_games == 1


def test_support_sample_does_not_receive_farming_target():
    plan = _training_plan({"matches": [row("UTILITY", "Camille")]}, disposition="degraded")
    assert any("辅助的1局" in line for line in plan)
    assert not any("7刀" in line or "补刀作为第一" in line for line in plan)
    assert any("确认" in line for line in plan)


def test_new_goal_without_sample_is_not_evaluated_using_old_role():
    plan = _training_plan({"matches": [row("mid")]}, disposition="complete", training_positions=("jungle",))
    assert len(plan) == 1
    assert "打野暂无本次样本" in plan[0]


def test_observed_counts_do_not_include_short_or_failed_matches():
    result = position_context({"matches": [row("mid"), row("support", included=False)],
                               "failed_matches": [{"role": "jungle"}]})
    assert [(r.position, r.games) for r in result.observed] == [("mid", 1)]


def test_role_metrics_are_separate_and_missing_is_not_zero():
    context = position_context({"matches": [
        {**row("mid"), "cs_per_min": 9.0, "vision_score": None},
        {**row("mid"), "cs_per_min": None, "vision_score": False},
        {**row("support", "Camille"), "cs_per_min": 1.0, "vision_score": 40},
    ]})
    mid, support = context.observed
    assert mid.averages["cs_per_min"] == 9.0
    assert mid.metric_sample_counts["cs_per_min"] == 1
    assert mid.averages["vision_score"] is None
    assert mid.metric_sample_counts["vision_score"] == 0
    assert support.averages["cs_per_min"] == 1.0


def test_case_variants_do_not_create_duplicate_champion_requests():
    context = position_context({"matches": [row("mid", "Anivia"), row("mid", "anivia")]})
    assert context.observed[0].champions == ("Anivia",)
    assert context.observed[0].games == 2
