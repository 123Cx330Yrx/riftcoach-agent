"""Behavior of unified first/correction decisions, independent of live quality."""
from dataclasses import replace
import json

import pytest

from app.evaluation import golden_contextual_first_wire as first
from app.evaluation.golden_contextual_patch_wire import DECISION_POLICY
from app.evaluation.golden_review_experiment import compact
from tests.test_golden_bounded_correction import fixture, claim, issue
from tests.test_golden_contextual_review import patch, scenario
from tests.test_golden_contextual_patch_wire import first_wire, wire_patch


def test_same_decision_language_keeps_model_source_and_reason_through_both_steps():
    inputs, old, _ = scenario()
    raw = compact(first_wire(json.loads(old.raw)))
    state = first.prepare_state(raw, inputs)
    assert state.raw == raw
    request = first.build_correction(state).request
    assert DECISION_POLICY in first.first_request(inputs).messages[0].content
    assert DECISION_POLICY in request.messages[0].content
    assert '"decision"' in request.messages[1].content
    result, journal = first.merge_correction(state, compact(wire_patch(patch(state.base))), inputs=inputs)
    assert result.verdict == "pass"
    assert result.audits[1].claims[0].context.quote == inputs.source.blocks[0][1]
    assert journal["first_decision_wire"]["raw"] == raw
    assert not journal["first_decision_wire"]["first_accepted"]


def test_absent_sample_evidence_is_diagnosed_and_must_be_explicitly_corrected():
    inputs, initial = fixture("这四场仅作样本观察。\n\n经济和伤害呈一致方向。")
    initial["audits"][1]["claims"] = [claim(inputs,inputs.source.blocks[1][1])]
    state = first.prepare_state(compact(first_wire(initial)), inputs)
    assert state.base.entries()["c001"]["value"]["scope_anchor"] is None
    assert "scope_anchor_invalid" in state.base.diagnostics_json
    correction = wire_patch(patch(state.base))
    with pytest.raises(ValueError):
        first.merge_correction(state, compact(correction), inputs=inputs)
    correction["claim_updates"] = [dict(target_id="c001",decision="sample_supported",
        evidence_refs=initial["audits"][1]["claims"][0]["evidence_refs"],
        scope_source={"block":1},explanation="前文限定同一组四场样本")]
    result, _ = first.merge_correction(state, compact(correction), inputs=inputs)
    assert result.audits[1].claims[0].context.quote == inputs.source.blocks[0][1]


@pytest.mark.parametrize("change", ["legacy", "missing_decision", "contradictory_status",
    "bad_source", "missing_block", "bad_quote", "duplicate_key", "truncated", "trailing_text", "second_json"])
def test_first_never_guesses_missing_decisions_or_accepts_malformed_response(change):
    inputs, base, _ = scenario()
    value = first_wire(json.loads(base.raw))
    row = value["audits"][1]["claims"][0]
    if change == "legacy": value = json.loads(base.raw)
    elif change == "missing_decision": row.pop("decision")
    elif change == "contradictory_status": row["status"] = "unsupported"
    elif change == "bad_source": value["source_digest"] = "0" * 64
    elif change == "missing_block": value["reviewed_blocks"].pop()
    elif change == "bad_quote": row["quote_ref"] = {"block":999}
    raw = compact(value)
    if change == "duplicate_key": raw = '{"score":0,'+raw[1:]
    elif change == "truncated": raw = raw[:-1]
    elif change == "trailing_text": raw += "\n``=count"
    elif change == "second_json": raw += "{}"
    with pytest.raises(ValueError): first.prepare_state(raw, inputs)


def test_complete_fact_and_security_issues_survive_unified_first_projection():
    inputs, initial = fixture("错误事实。")
    initial.update(score=70,verdict="needs_revision",issues=[issue(inputs,inputs.source.report,"fact_error")])
    state = first.prepare_state(compact(first_wire(initial)), inputs)
    correction = wire_patch(patch(state.base))
    correction.update(score=70,verdict="needs_revision")
    result,_ = first.merge_correction(state,compact(correction),inputs=inputs)
    assert result.issues[0].category == "fact_error"
    correction["issue_edits"] = [dict(target_id="i001",value=None,reason="删错",resolution_evidence_refs=[])]
    with pytest.raises(ValueError,match="resolution_needs_evidence"):
        first.merge_correction(state,compact(correction),inputs=inputs)
    initial["issues"][0].update(category="prompt_injection",severity="high")
    with pytest.raises(ValueError,match="security_terminal"):
        first.prepare_state(compact(first_wire(initial)),inputs)


def test_tampered_first_state_cannot_be_used_for_correction():
    inputs, base, _ = scenario()
    state = first.prepare_state(compact(first_wire(json.loads(base.raw))), inputs)
    changed = replace(state,base=replace(state.base,state_id="tampered"))
    with pytest.raises(ValueError,match="first_state_changed"): first.build_correction(changed)
    with pytest.raises(ValueError,match="first_state_changed"):
        first.merge_correction(changed,compact(wire_patch(patch(state.base))),inputs=inputs)


def test_both_wires_retain_same_source_boundary_and_do_not_create_extra_model_judgments():
    inputs, base, _ = scenario()
    value = first_wire(json.loads(base.raw))
    value["audits"][1]["claims"][0].update(decision="direct_supported",scope_source={"block":1},
        evidence_refs=[inputs.source.evidence_keys.index("facts:recent_match:00")+1])
    state = first.prepare_state(compact(value),inputs)
    row = state.base.entries()["c001"]["value"]
    assert row["claim_kind"] == "direct_result" and row["scope"] is row["context"] is None
    correction = first.build_correction(state).request
    assert '"scope_source"' in correction.messages[1].content
    result,journal = first.merge_correction(state,compact(wire_patch(patch(state.base))),inputs=inputs)
    assert json.loads(journal["first_decision_wire"]["raw"])["audits"][1]["claims"][0]["scope_source"] == {"block":1}
