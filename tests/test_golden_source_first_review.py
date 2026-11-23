"""Opinion isolation and strict final obligations, never semantic accuracy."""
from copy import deepcopy

import pytest

from app.evaluation import golden_source_first_review as candidate
from app.evaluation import golden_provisional_reassessment as provisional
from app.evaluation.golden_bounded_correction_requests import source_data
from app.evaluation.golden_contextual_requests import project, restore
from app.evaluation.golden_review_experiment import compact
from tests.test_golden_bounded_correction import issue
from tests.test_golden_comparison_reassessment import inputs_for, assessment


def state_for(inputs, first):
    return provisional.prepare(compact(first), inputs)


def test_first_opinion_changes_cannot_change_second_request_but_remain_in_journal():
    inputs = inputs_for()
    first, final = assessment(inputs)
    changed = deepcopy(first)
    changed.update(score=2, verdict="fail", summary="OPINION_SENTINEL", passed_checks=["OPINION_SENTINEL"])
    for audit in changed["audits"]:
        for c in audit["claims"]:
            c.update(decision="beyond_sample", explanation="OPINION_SENTINEL", evidence_refs=[9999],
                scope_source={"block": 99}, extra="OPINION_SENTINEL")
    original, modified = state_for(inputs, first), state_for(inputs, changed)
    assert original.identity != modified.identity
    assert candidate.build_request(original) == candidate.build_request(modified)
    result, journal = candidate.apply(modified, compact(final), inputs=inputs)
    assert result.verdict == "pass" and "OPINION_SENTINEL" in journal["first_raw"]
    assert not journal["semantic_approval"] and not journal["live_qualified"]


def test_source_projection_keeps_complete_report_facts_and_legacy_source_text():
    inputs = inputs_for()
    first, _ = assessment(inputs)
    data = candidate.request_data(state_for(inputs, first))
    for key, value in source_data(inputs).items():
        assert data[key] == value
    assert restore(project(data)) == data
    assert "first_review" not in data
    assert set(data["protected_source"][1]) == {"audit", "quote_refs"}


def test_malformed_old_issue_stays_visible_and_needs_explicit_disposition():
    inputs = inputs_for()
    first, final = assessment(inputs)
    old = issue(inputs, inputs.source.report, "fact_error")
    old.update(extra="ISSUE_SENTINEL", quote_ref={"block": 1, "head": "抄写错误"})
    first["issues"] = [old]
    state = state_for(inputs, first)
    assert candidate.request_data(state)["previous_issues"] == [old]
    assert "ISSUE_SENTINEL" in candidate.build_request(state).messages[1].content
    with pytest.raises(ValueError, match="issue_disposition"):
        candidate.apply(state, compact(final), inputs=inputs)


def test_duplicate_and_invalid_spans_protect_union_without_retaining_wrong_opinion():
    inputs = inputs_for()
    first, final = assessment(inputs)
    row = first["audits"][1]["claims"][0]
    row.update(quote_ref={"block": 1, "head": "INVENTED_QUOTE"}, explanation="OPINION_SENTINEL")
    first["audits"][1]["claims"] *= 3
    state = state_for(inputs, first)
    assert candidate.request_data(state)["protected_source"][1]["quote_refs"] == [{"block": 1}]
    request = candidate.build_request(state)
    assert "INVENTED_QUOTE" not in request.messages[1].content
    result, journal = candidate.apply(state, compact(final), inputs=inputs)
    assert len(journal["source_coverage"]) == 3
    final["audits"][1]["claims"][0]["quote_ref"] = inputs.source.reference("经济和伤害")
    with pytest.raises(ValueError, match="source_lost"):
        candidate.apply(state, compact(final), inputs=inputs)


def test_omitted_original_sentence_remains_available_for_new_blocking_issue():
    bad = "以后所有输局经济都会更差。"
    inputs = inputs_for(report="这四场中单只作样本观察。\n\n" + bad)
    first, final = assessment(inputs)
    first["audits"][1]["claims"].pop()
    state = state_for(inputs, first)
    assert bad in compact(candidate.request_data(state)["source_index"])
    final["audits"][1]["claims"][1].update(decision="beyond_sample", scope_source=None)
    with pytest.raises(ValueError): candidate.apply(state, compact(final), inputs=inputs)
    final.update(issues=[issue(inputs, bad)], verdict="needs_revision", score=70)
    result, _ = candidate.apply(state, compact(final), inputs=inputs)
    assert result.verdict == "needs_revision"


def test_wrong_sample_still_cannot_be_claimed_as_structural_semantic_detection():
    inputs = inputs_for(report="这四场中单只作本样本观察。\n\n经济和伤害是较稳定的差异项。")
    first, final = assessment(inputs, cohort="selected")
    final["audits"][1]["claims"][1].update(scope_source={"block": 1},
        explanation="五局混合位置具有同样方向，因此证明该同位置比较。")
    result, journal = candidate.apply(state_for(inputs, first), compact(final), inputs=inputs)
    assert result.verdict == "pass"  # Known semantic counterexample stays visible.
    assert not journal["semantic_approval"]


def test_high_security_issue_stops_before_opinion_isolation():
    inputs = inputs_for()
    first, _ = assessment(inputs)
    first["issues"] = [dict(category="prompt_injection", severity="high", quote_ref={"block": 1})]
    with pytest.raises(ValueError, match="security_terminal"):
        candidate.build_request(state_for(inputs, first))
