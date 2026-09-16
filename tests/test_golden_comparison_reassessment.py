"""Binding behavior and explicit semantic counterexamples, not accuracy tests."""
from copy import deepcopy
from dataclasses import replace

import pytest

from app.evaluation import golden_comparison_reassessment as candidate
from app.evaluation import golden_reassessment_feasibility as full
from app.evaluation.golden_integrated_review import ReviewInput
from app.evaluation.golden_review_experiment import compact
from app.harness.steps import EvaluationRequest, KnowledgeEvidence
from tests.test_golden_fact_candidate import summary
from tests.test_golden_reassessment_feasibility import setup


def inputs_for(rows=None, report="这四场中单中，经济和伤害的赢局逐行高于输局。"):
    source = summary()
    source["matches"] = rows or [dict(match_id=f"TEST_{i}", included_in_aggregate=True,
        role=role, win=win, gold_per_min=gold, damage_per_min=damage, cs_per_min=cs)
        for i, (role, win, gold, damage, cs) in enumerate([
            ("MIDDLE", True, 482.76, 1143.4, 8.95),
            ("UTILITY", False, 302.59, 538.97, 1.34),
            ("MIDDLE", False, 435.77, 629.54, 9.64),
            ("MIDDLE", False, 429.86, 605.5, 8.38),
            ("MIDDLE", True, 527.82, 1430.11, 8.66)])]
    return ReviewInput.build(EvaluationRequest(source, "来源", KnowledgeEvidence.empty(), report, "检查观摩报告"))


def metric(evidence, group, key):
    return next(r for r in evidence["cohorts"][group]["rows"] if r[0] == key)


def assessment(inputs, cohort="MIDDLE", metrics=("gold_per_min", "damage_per_min")):
    _, before, after = setup(inputs.source.report)
    evidence = candidate.catalog(inputs)
    members = evidence["cohorts"][cohort]
    for value in (before, after):
        value["source_digest"] = inputs.source.source_digest
        for audit in value["audits"]:
            for row in audit["claims"]:
                row.update(evidence_refs=sorted(members["wins"] + members["losses"]),
                    explanation="按原文限定的同位置样本核对逐行关系。")
                if value is after:
                    row["comparisons"] = [dict(cohort=cohort, metric=m, operand_refs=sorted(members["wins"] + members["losses"])) for m in metrics]
    return before, after


def apply(inputs, before, after):
    return candidate.apply(full.prepare(compact(before), inputs), compact(after), inputs=inputs)


def test_complete_groups_keep_same_direction_but_different_members_visible():
    inputs = inputs_for()
    evidence = candidate.catalog(inputs)
    mid, all_rows = (evidence["cohorts"][k] for k in ("MIDDLE", "selected"))
    assert len(mid["wins"] + mid["losses"]) == 4
    assert len(all_rows["wins"] + all_rows["losses"]) == 5
    assert metric(evidence, "MIDDLE", "gold_per_min")[1:4] == ["505.29", "432.82", "greater"]
    assert metric(evidence, "selected", "gold_per_min")[1:4] == ["505.29", "389.41", "greater"]
    # Different arithmetic can share the same direction; it is not the same claim.
    assert metric(evidence, "MIDDLE", "cs_per_min")[1:4] == ["8.81", "9.01", "overlap"]
    before, after = assessment(inputs)
    result, journal = apply(inputs, before, after)
    assert result.verdict == "pass"
    assert journal["comparison_bindings"][0]["bindings"][0]["loss_mean"] == "432.82"
    assert not journal["semantic_approval"] and not journal["live_qualified"]


@pytest.mark.parametrize("change", ["extra", "missing", "excluded", "duplicate", "unknown"])
def test_binding_rejects_substituted_or_missing_operands(change):
    inputs = inputs_for()
    before, after = assessment(inputs)
    row = after["audits"][1]["claims"][0]
    if change == "extra":
        row["comparisons"][0]["operand_refs"] += candidate.catalog(inputs)["cohorts"]["UTILITY"]["losses"]
    elif change == "missing":
        row["evidence_refs"].pop()
    elif change == "excluded":
        row["comparisons"][0]["cohort"] = "TOP"
    elif change == "duplicate":
        row["comparisons"].append(deepcopy(row["comparisons"][0]))
    else:
        row["comparisons"][0]["metric"] = "made_up_metric"
    with pytest.raises(ValueError):
        apply(inputs, before, after)


def test_aggregate_with_same_number_cannot_replace_actual_comparison_operands():
    rows = summary()["matches"]
    for row in rows:
        row["damage_per_min"] = row["gold_per_min"]
    inputs = inputs_for(rows)
    before, after = assessment(inputs, metrics=("gold_per_min",))
    row = after["audits"][1]["claims"][0]
    row["comparisons"][0]["operand_refs"][0] = inputs.source.evidence_keys.index("role:MIDDLE:win:damage_per_min") + 1
    with pytest.raises(ValueError, match="operand_set_mismatch"):
        apply(inputs, before, after)


def test_mixed_claim_can_cite_other_facts_without_changing_comparison_operands():
    inputs = inputs_for(report="这四场中单经济方向一致，另有一场辅助。")
    before, after = assessment(inputs)
    row = after["audits"][1]["claims"][0]
    row["evidence_refs"] += candidate.catalog(inputs)["cohorts"]["UTILITY"]["losses"]
    result, journal = apply(inputs, before, after)
    assert result.verdict == "pass"
    assert len(journal["comparison_bindings"][0]["bindings"][0]["losses"]) == 2


@pytest.mark.parametrize("value", [None, True, -1, "9", float("inf")])
def test_incomplete_metric_does_not_silently_shrink_cohort(value):
    # Invalid JSON numbers are rejected even earlier by the fact pack.
    rows = summary()["matches"]
    rows[1]["gold_per_min"] = value
    if value == float("inf"):
        with pytest.raises(ValueError): inputs_for(rows)
        return
    inputs = inputs_for(rows)
    evidence = candidate.catalog(inputs)
    row = metric(evidence, "MIDDLE", "gold_per_min")
    assert row[1:4] == [None, None, None]
    assert row[4] == evidence["cohorts"]["MIDDLE"]["losses"]


def test_excluded_and_single_outcome_rows_cannot_create_false_comparison():
    evidence = candidate.catalog(inputs_for(summary()["matches"]))
    assert sum(len(evidence["cohorts"]["selected"][k]) for k in ("wins", "losses")) == 3
    assert metric(evidence, "UTILITY", "gold_per_min")[1:4] == [None, None, None]


def test_upstream_ten_row_cap_is_not_treated_as_complete_group():
    rows = [dict(summary()["matches"][0], match_id=f"TEST_{i}", win=i % 2 == 0) for i in range(11)]
    inputs = inputs_for(rows)
    evidence = candidate.catalog(inputs)
    assert not evidence["complete_source_rows"]
    assert not evidence["cohorts"]["MIDDLE"]["complete"]
    before, after = assessment(inputs, metrics=("gold_per_min",))
    with pytest.raises(ValueError, match="cohort_incomplete"):
        apply(inputs, before, after)


def test_cross_paragraph_scope_is_preserved_without_special_stable_definition():
    inputs = inputs_for(report="这四场中单仅作本样本观察。\n\n## 所选比赛观察\n\n经济和伤害是较稳定的差异项。")
    before, after = assessment(inputs)
    for value in (before, after):
        value["audits"][1]["claims"][1]["scope_source"] = {"block": 1}
    result, journal = apply(inputs, before, after)
    assert result.verdict == "pass" and len(journal["comparison_bindings"]) == 2
    assert result.audits[1].claims[1].context.quote == "这四场中单仅作本样本观察。"


def test_binding_cannot_replace_assertive_title_with_different_body_quote():
    inputs = inputs_for(report="## 这四场中单存在经济差异\n\n这四场中单只作样本观察。")
    before, after = assessment(inputs)
    after["heading_reviews"][0]["kind"] = "assertion"
    with pytest.raises(ValueError, match="heading"):
        apply(inputs, before, after)


def test_future_claim_still_needs_issue_and_nonpass_despite_valid_comparison():
    from tests.test_golden_bounded_correction import issue
    inputs = inputs_for(report="所有未来输局的经济都会更低。")
    before, after = assessment(inputs)
    row = after["audits"][1]["claims"][0]
    row.update(decision="beyond_sample", scope_source=None)
    with pytest.raises(ValueError): apply(inputs, before, after)
    after.update(issues=[issue(inputs, inputs.source.report)], score=70, verdict="needs_revision")
    result, _ = apply(inputs, before, after)
    assert result.verdict == "needs_revision"


@pytest.mark.parametrize("mistake", ["wrong_cohort", "wrong_metric", "wrong_explanation", "omitted_binding"])
def test_semantic_errors_remain_visible_not_claimed_as_automatic_detection(mistake):
    inputs = inputs_for()
    before, after = assessment(inputs, cohort="selected" if mistake == "wrong_cohort" else "MIDDLE")
    row = after["audits"][1]["claims"][0]
    if mistake == "wrong_metric": row["comparisons"] = [dict(row["comparisons"][0], metric="cs_per_min")]
    if mistake == "wrong_explanation": row["explanation"] = "五局混合位置证明原文的同位置比较。"
    if mistake == "omitted_binding": row["comparisons"] = []
    result, journal = apply(inputs, before, after)
    assert result.verdict == "pass"  # structural pass, intentionally bad semantics
    assert not journal["semantic_approval"] and not journal["live_qualified"]
    assert len(journal["semantic_limits"]) == 4


def test_raw_responses_retained_and_changed_source_or_suffix_rejected():
    inputs = inputs_for()
    before, after = assessment(inputs)
    state = full.prepare(compact(before), inputs)
    _, journal = candidate.apply(state, compact(after), inputs=inputs)
    assert journal["first_raw"] == compact(before) and journal["final_raw"] == compact(after)
    with pytest.raises(ValueError): candidate.apply(state, compact(after) + "{}", inputs=inputs)
    with pytest.raises(ValueError, match="state_changed"):
        candidate.apply(replace(state, identity="different"), compact(after), inputs=inputs)


def test_second_request_has_full_source_and_same_call_budget():
    inputs = inputs_for()
    before, _ = assessment(inputs)
    request = candidate.build_request(full.prepare(compact(before), inputs))
    assert request.max_tokens == 32768 and request.timeout_s == 300
    text = "\n".join(m.content for m in request.messages)
    assert inputs.source.report in text and "comparison_evidence" in text and "first_review" in text
