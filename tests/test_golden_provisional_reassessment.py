"""Provisional input recovery keeps source obligations and strict final output."""
from copy import deepcopy

import pytest

from app.evaluation import golden_provisional_reassessment as candidate
from app.evaluation.golden_review_experiment import compact
from tests.test_golden_comparison_reassessment import inputs_for, assessment
from tests.test_golden_bounded_correction import issue


def run(inputs, before, after):
    state = candidate.prepare(compact(before), inputs)
    result, journal = candidate.apply(state, compact(after), inputs=inputs)
    assert journal["first_raw"] == compact(before)
    assert not journal["semantic_approval"] and not journal["live_qualified"]
    return result, journal


def test_overlong_first_refs_are_retained_but_strict_final_still_applies():
    inputs = inputs_for()
    before, after = assessment(inputs)
    before["audits"][1]["claims"][0]["evidence_refs"] = list(range(1, 15))
    result, journal = run(inputs, before, after)
    assert result.verdict == "pass"
    assert any(r["code"] == "too_long" for r in journal["provisional_diagnostics"])
    request = candidate.build_request(candidate.prepare(compact(before), inputs))
    assert "provisional_diagnostics" in request.messages[1].content
    after["audits"][1]["claims"][0]["evidence_refs"] = list(range(1, 15))
    with pytest.raises(ValueError): run(inputs, before, after)


@pytest.mark.parametrize("ref", [dict(block=1, head="改写的原文"), dict(block=1, head="不存在", extra=True)])
def test_bad_span_protects_whole_real_block_and_does_not_invent_quote(ref):
    inputs = inputs_for()
    before, after = assessment(inputs)
    before["audits"][1]["claims"][0]["quote_ref"] = ref
    _, journal = run(inputs, before, after)
    assert any(r["code"] == "unresolved_quote_protects_complete_block" for r in journal["provisional_diagnostics"])
    after["audits"][1]["claims"][0]["quote_ref"] = inputs.source.reference("经济和伤害")
    with pytest.raises(ValueError, match="source_lost"): run(inputs, before, after)


@pytest.mark.parametrize("bad", [None, {}, {"block": 999}, {"block": True}])
def test_unknown_source_is_terminal_even_when_other_fields_are_recoverable(bad):
    inputs = inputs_for()
    before, after = assessment(inputs)
    before["audits"][1]["claims"][0]["quote_ref"] = bad
    with pytest.raises(ValueError, match="provisional_"): run(inputs, before, after)


def test_provisional_missing_decision_and_bad_scope_keep_full_state_for_reassessment():
    inputs = inputs_for()
    before, after = assessment(inputs)
    row = before["audits"][1]["claims"][0]
    row.pop("decision")
    row.update(scope_source={"block": 99}, extra_observation="原始额外内容不丢弃")
    _, journal = run(inputs, before, after)
    assert "原始额外内容不丢弃" in journal["first_raw"]
    assert any(r["code"] == "invalid_scope_reference" for r in journal["provisional_diagnostics"])


def test_malformed_old_issue_requires_explicit_disposition_and_keeps_raw_issue():
    inputs = inputs_for()
    before, after = assessment(inputs)
    old = issue(inputs, inputs.source.report, "fact_error")
    old["quote_ref"] = {"block": 1, "head": "改写原句"}
    old["unexpected"] = "must survive"
    before["issues"] = [old]
    with pytest.raises(ValueError, match="issue_disposition"): run(inputs, before, after)
    after["issue_resolutions"] = [dict(target_id="i001", evidence_refs=after["audits"][1]["claims"][0]["evidence_refs"],
        explanation="脚本显式核对，而不是自动认可撤销理由。")]
    _, journal = run(inputs, before, after)
    assert journal["resolved_issues"][0]["before"] == old


def test_high_injection_stays_terminal_even_with_invalid_quote():
    inputs = inputs_for()
    before, after = assessment(inputs)
    before["issues"] = [dict(category="prompt_injection", severity="high", quote_ref={"block": 999})]
    with pytest.raises(ValueError, match="security_terminal"): run(inputs, before, after)


@pytest.mark.parametrize("field", ["source_digest", "reviewed_blocks", "heading_reviews", "audits", "issues"])
def test_unidentifiable_inventory_is_not_guessed(field):
    inputs = inputs_for()
    before, after = assessment(inputs)
    before.pop(field)
    with pytest.raises(ValueError): run(inputs, before, after)


def test_truncated_or_suffixed_first_output_is_not_recovered():
    inputs = inputs_for()
    before, _ = assessment(inputs)
    for raw in (compact(before)[:-1], compact(before) + "{}", compact(before) + "suffix"):
        with pytest.raises(ValueError): candidate.prepare(raw, inputs)


def test_offline_workflow_can_reassess_invalid_provisional_fields_without_extra_call():
    from app.evaluation.golden_integrated_runtime import BudgetedReviewSender
    from tests.test_golden_integrated_review import ReplayProvider
    from tests.test_golden_comparison_workflow import make_request
    inputs = inputs_for(report="这四场中单经济方向一致。[K1]")
    req = make_request(inputs)
    inputs = candidate.ProvisionalReassessmentWorkflow.build_inputs(req)
    before, after = assessment(inputs)
    row = before["audits"][1]["claims"][0]
    row["evidence_refs"] = list(range(1, 15))
    row["quote_ref"] = dict(block=1, head="错误抄写的片段")
    provider = ReplayProvider(lambda _, n: compact(before if n == 1 else after))
    flow = candidate.ProvisionalReassessmentWorkflow(BudgetedReviewSender(provider))
    result = flow.evaluate(req)
    assert result.verdict.value == "pass" and len(provider.requests) == 2
    assert len(flow.last_journal["provisional_diagnostics"]) == 2


def test_second_review_can_add_omitted_cross_paragraph_claim_without_losing_old_source():
    inputs = inputs_for(report="这四场中单仅作本样本观察。\n\n经济和伤害是较稳定的差异项。")
    before, after = assessment(inputs)
    before["audits"][1]["claims"].pop()
    after["audits"][1]["claims"][1]["scope_source"] = {"block": 1}
    result, journal = run(inputs, before, after)
    assert len(result.audits[1].claims) == 2
    assert result.audits[1].claims[1].context.quote == inputs.source.blocks[0][1]
    assert len(journal["source_coverage"]) == 1  # Only old source is protected here.


def test_newly_discovered_future_error_requires_issue_and_blocks_pass():
    bad = "以后所有中单输局经济都会更差。"
    inputs = inputs_for(report="这四场中单仅作本样本观察。\n\n" + bad)
    before, after = assessment(inputs)
    before["audits"][1]["claims"].pop()
    after["audits"][1]["claims"][1].update(decision="beyond_sample", scope_source=None)
    with pytest.raises(ValueError): run(inputs, before, after)
    after.update(issues=[issue(inputs, bad)], score=70, verdict="needs_revision")
    result, _ = run(inputs, before, after)
    assert result.verdict == "needs_revision"


def test_too_many_distinct_protected_blocks_stops_before_second_request():
    inputs = inputs_for(report="\n\n".join(f"这四场样本观察{chr(65+i)}。" for i in range(25)))
    before, _ = assessment(inputs)
    with pytest.raises(ValueError, match="coverage_exceeds_final_capacity"):
        candidate.prepare(compact(before), inputs)
