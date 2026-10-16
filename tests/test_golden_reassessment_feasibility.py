"""Offline behavior and adverse semantic witnesses; no live-quality claims."""
from copy import deepcopy
from dataclasses import replace

import pytest

from app.evaluation import golden_reassessment_feasibility as candidate
from app.evaluation.golden_review_experiment import compact
from tests.test_golden_bounded_correction import fixture, claim, issue
from tests.test_golden_contextual_patch_wire import first_wire, fixture_decision


def setup(report):
    inputs, old = fixture(report)
    old["audits"][1]["claims"] = [claim(inputs, text) for _, text in inputs.source.blocks
        if not text.startswith("#")]
    before = first_wire(old)
    after = deepcopy(before)
    after["issue_resolutions"] = []
    return inputs, before, after


def run(inputs, before, after):
    raw = compact(before)
    state = candidate.prepare(raw, inputs)
    result, journal = candidate.apply(state, compact(after), inputs=inputs)
    assert state.raw == raw and journal["first_raw"] == raw
    return result, journal


def test_full_block_duplicates_can_be_regrouped_without_losing_source():
    inputs, before, after = setup("这四场经济方向一致，样本伤害方向也一致。")
    before["audits"][1]["claims"] *= 3
    result, journal = run(inputs, before, after)
    assert len(result.audits[1].claims) == 1
    assert len(journal["source_coverage"]) == 3
    assert all(m["final_claim_indices"] == [0] for m in journal["source_coverage"])
    assert not journal["semantic_approval"] and not journal["live_qualified"]


def test_full_block_can_split_only_if_all_original_characters_survive():
    left, right = "这四场经济仅属样本观察。", "这四场伤害仅属样本观察。"
    inputs, before, after = setup(left + right)
    original = after["audits"][1]["claims"][0]
    after["audits"][1]["claims"] = [dict(original, quote_ref=inputs.source.reference(s))
                                    for s in (left, right)]
    result, journal = run(inputs, before, after)
    assert len(result.audits[1].claims) == 2
    assert journal["source_coverage"][0]["final_claim_indices"] == [0, 1]
    after["audits"][1]["claims"][1]["quote_ref"] = inputs.source.reference(right[1:])
    with pytest.raises(ValueError, match="reviewed_source_lost"):
        run(inputs, before, after)


@pytest.mark.parametrize("mutation", ["drop", "shrink", "other_block", "other_audit"])
def test_regrouping_cannot_hide_old_text_or_move_it_to_another_audit(mutation):
    text = "这四场有差异，但尚未说明原因。"
    inputs, before, after = setup(text + "\n\n这四场还需验证。")
    rows = after["audits"][1]["claims"]
    if mutation == "drop": rows.clear()
    elif mutation == "shrink": rows[0]["quote_ref"] = inputs.source.reference("这四场有差异")
    elif mutation == "other_block": rows[0]["quote_ref"] = {"block": 2}
    else: after["audits"][0]["claims"].append(rows.pop(0))
    with pytest.raises(ValueError, match="reviewed_source_lost"):
        run(inputs, before, after)


def test_all_48_claims_can_change_without_a_16_edit_or_64_review_ceiling():
    report = "\n\n".join(f"## 观察{chr(65+i)}\n\n这四场观察{chr(65+i)}仅作样本比较。"
                           for i in range(24))
    inputs, before, after = setup(report)
    before["audits"][0]["claims"] = deepcopy(before["audits"][1]["claims"])
    after["audits"][0]["claims"] = deepcopy(after["audits"][1]["claims"])
    for audit in before["audits"]:
        for row in audit["claims"]: row["explanation"] = "首评待纠正说明"
    result, journal = run(inputs, before, after)
    assert len(journal["source_coverage"]) == 48
    assert sum(len(a.claims) for a in result.audits) == 48
    assert len(before["heading_reviews"]) == 24
    candidate.build_request(candidate.prepare(compact(before), inputs))


def test_more_than_16_headings_can_be_reclassified_with_full_assertions():
    report = "\n\n".join(f"## 这四场观察{chr(65+i)}存在差异" for i in range(17))
    inputs, before, after = setup(report)
    for h in after["heading_reviews"]: h["kind"] = "assertion"
    after["audits"][1]["claims"] = [fixture_decision(claim(inputs, text))
                                    for _, text in inputs.source.blocks]
    result, _ = run(inputs, before, after)
    assert len(result.audits[1].claims) == 17


def test_fact_issues_are_retained_or_explicitly_resolved_with_valid_evidence():
    inputs, before, after = setup("这四场只作样本观察。")
    old_issue = issue(inputs, inputs.source.report, "fact_error")
    before.update(issues=[old_issue], verdict="needs_revision", score=70)
    with pytest.raises(ValueError, match="issue_disposition"):
        run(inputs, before, after)
    after.update(issues=[old_issue], verdict="needs_revision", score=70)
    result, _ = run(inputs, before, after)
    assert result.issues[0].category == "fact_error"
    after.update(issues=[], verdict="pass", score=95,
        issue_resolutions=[dict(target_id="i001", evidence_refs=[1], explanation="脚本显式撤销")])
    _, journal = run(inputs, before, after)
    preserved = journal["resolved_issues"][0]["before"]
    assert preserved["explanation"] == old_issue["explanation"]
    assert inputs.source.resolve(preserved["quote_ref"]) == inputs.source.report
    assert not journal["semantic_approval"]  # Valid source is not proof of resolution.
    for refs in ([], [1, 1], [9999]):
        after["issue_resolutions"][0]["evidence_refs"] = refs
        with pytest.raises(ValueError): run(inputs, before, after)


def test_no_12_issue_edit_ceiling_and_no_silent_issue_removal():
    inputs, before, after = setup("这四场只作样本观察。")
    before.update(issues=[dict(issue(inputs, inputs.source.report, "fact_error"),
        explanation=f"独立待核对问题{n}") for n in range(13)], verdict="needs_revision", score=70)
    after["issue_resolutions"] = [dict(target_id=f"i{i:03}", evidence_refs=[1],
        explanation="脚本显式核对") for i in range(1, 14)]
    _, journal = run(inputs, before, after)
    assert len(journal["resolved_issues"]) == 13
    after["issue_resolutions"].pop()
    with pytest.raises(ValueError, match="issue_disposition"):
        run(inputs, before, after)


@pytest.mark.parametrize("phase", ["first", "final"])
def test_security_issue_is_terminal_even_before_schema_validation(phase):
    inputs, before, after = setup("这四场只作样本观察。")
    changed = before if phase == "first" else after
    changed["issues"] = [dict(issue(inputs, inputs.source.report, "prompt_injection"), severity="high")]
    changed["reviewed_blocks"] = []
    with pytest.raises(ValueError, match="security_terminal"):
        run(inputs, before, after)


def test_new_unsupported_future_claim_requires_issue_and_nonpass():
    inputs, before, after = setup("这四场只作样本观察。\n\n所有未来输局都会更差。")
    row = after["audits"][1]["claims"][1]
    row.update(decision="beyond_sample", scope_source=None)
    with pytest.raises(ValueError): run(inputs, before, after)
    after.update(issues=[issue(inputs, inputs.source.blocks[1][1])], score=70, verdict="needs_revision")
    result, _ = run(inputs, before, after)
    assert result.verdict == "needs_revision"


def test_structural_acceptance_does_not_prove_correct_cohort_in_explanation():
    context = "这四场中单逐行方向一致，仅指本样本，不外推长期。"
    target = "经济和伤害是较稳定的差异项。"
    inputs, before, after = setup(context + "\n\n" + target)
    for value in (before, after):
        row = value["audits"][1]["claims"][1]
        row.update(scope_source={"block": 1}, explanation="五局混合位置的差异证明这句话正确。")
    result, journal = run(inputs, before, after)
    assert result.verdict == "pass"
    assert "五局混合" in result.audits[1].claims[1].explanation
    assert not journal["semantic_approval"] and not journal["live_qualified"]


def test_stale_state_and_invalid_final_output_are_not_repaired():
    inputs, before, after = setup("这四场只作样本观察。")
    state = candidate.prepare(compact(before), inputs)
    for raw in (compact(after) + "{}", compact(after)[:-1], compact(after) + "\n`=count"):
        with pytest.raises(ValueError): candidate.apply(state, raw, inputs=inputs)
    with pytest.raises(ValueError, match="state_changed"):
        candidate.apply(replace(state, identity="stale"), compact(after), inputs=inputs)
    after["source_digest"] = "0" * 64
    with pytest.raises(ValueError, match="source_changed"): run(inputs, before, after)


@pytest.mark.parametrize("mutation", ["block", "heading", "audit", "reference", "evidence", "decision"])
def test_full_reassessment_does_not_weaken_existing_source_and_inventory_contracts(mutation):
    inputs, before, after = setup("## 观察\n\n这四场只作样本观察。")
    if mutation == "block": after["reviewed_blocks"].pop()
    elif mutation == "heading": after["heading_reviews"].clear()
    elif mutation == "audit": after["audits"].reverse()
    elif mutation == "reference": after["audits"][1]["claims"][0]["quote_ref"] = {"block": 64}
    elif mutation == "evidence": after["audits"][1]["claims"][0]["evidence_refs"] = [9999]
    else: after["audits"][1]["claims"][0].pop("decision")
    with pytest.raises(ValueError): run(inputs, before, after)


def test_false_direct_number_still_fails_final_validation():
    inputs, before, after = setup("中单经济999999/分。")
    after["audits"][1]["claims"][0].update(decision="direct_supported",
        evidence_refs=[inputs.source.evidence_keys.index("facts:recent_aggregate") + 1])
    with pytest.raises(ValueError, match="number_not_in_evidence"):
        run(inputs, before, after)


def test_repeated_source_text_cannot_be_rebound_to_a_different_occurrence():
    report = "这四场数据，独有分隔，这四场数据。"
    inputs, before, after = setup(report)
    # A unique endpoint pair pins the first occurrence even when the head repeats.
    before["audits"][1]["claims"][0]["quote_ref"] = {"block": 1, "head": "这四场", "tail": "独有"}
    after["audits"][1]["claims"][0]["quote_ref"] = {"block": 1, "head": "这四场数据。"}
    with pytest.raises(ValueError, match="reviewed_source_lost"):
        run(inputs, before, after)
