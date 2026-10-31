"""Bad first hints cannot bypass whole-body coverage or final strict review."""
from dataclasses import replace
from types import SimpleNamespace

import pytest

from app.evaluation import golden_provisional_reading_review as candidate
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_review_experiment import compact
from tests.test_golden_grounded_reading_review import reading
from tests.test_golden_comparison_reassessment import inputs_for
from tests.test_golden_typed_review import values, source_scenario
from tests.test_golden_bounded_correction import issue


def test_invalid_first_shape_and_locations_are_retained_not_silently_repaired():
    inputs = inputs_for()
    value = reading(inputs)
    value["readings"][0]["quote_ref"]["head"] = "原文中不存在的过长片段" * 8
    value["readings"][0]["context_refs"] = [{"block": 900}]
    value["readings"][0]["extra"] = "keep"
    value["extra"] = {"provisional": True}
    state = candidate.prepare(compact(value), inputs)
    assert strict_json(state.value_json) == value and state.diagnostics
    request = candidate.second_request(state)
    data = strict_json(request.messages[1].content.split("[UNTRUSTED DATA]\n")[1].split("\n[END UNTRUSTED DATA]")[0])
    assert data["first_extra"] == {"extra": value["extra"]}
    assert "原文中不存在的过长片段" in request.messages[1].content


def test_omitted_first_block_is_still_required_in_final_output():
    inputs = inputs_for()
    before = dict(readings=[], issues=[])
    state = candidate.prepare(compact(before), inputs)
    assert state.diagnostics[-1]["code"] == "first_body_blocks_omitted"
    _, final = values(inputs)
    # The old short-quote fixture does not cover every character of the body.
    for audit in final["audits"]:
        for row in audit["claims"]: row["quote_ref"] = {"block": 1}
    result, journal = candidate.apply(state, compact(final), inputs=inputs)
    assert result.verdict == "pass" and journal["required_body_blocks"] == [1]
    for audit in final["audits"]: audit["claims"] = []
    with pytest.raises(ValueError, match="reviewed_source_lost"):
        candidate.apply(state, compact(final), inputs=inputs)


def test_omitted_tail_cannot_be_hidden_by_correct_first_half():
    inputs = inputs_for(report="这四场中单只指本样本。[K1]以后必定如此。")
    state = candidate.prepare(compact(dict(readings=[], issues=[])), inputs)
    _, final = values(inputs)
    for audit in final["audits"]:
        for row in audit["claims"]:
            row["quote_ref"] = dict(block=1, head="这四场中单只指本样本。[K1]")
    with pytest.raises(ValueError, match="reviewed_source_lost"):
        candidate.apply(state, compact(final), inputs=inputs)


def test_bad_issue_fields_need_explicit_resolution_and_all_original_values_survive():
    inputs, _, final = source_scenario()
    old = issue(inputs, inputs.source.report)
    old["quote_ref"]["head"] = "过长且错误的定位" * 10
    old["extra"] = "this value must survive"
    value = dict(readings=[], issues=[old])
    state = candidate.prepare(compact(value), inputs)
    assert strict_json(state.value_json)["issues"] == [old]
    with pytest.raises(ValueError, match="issue_disposition"):
        candidate.apply(state, compact(final), inputs=inputs)
    final["issue_resolutions"] = [dict(target_id="i001", evidence_refs=[],
        sources=final["source_checks"][0]["sources"], explanation="基于原始官方字段纠正首读误报及坏定位。")]
    _, journal = candidate.apply(state, compact(final), inputs=inputs)
    assert journal["resolved_issues"][0]["before"] == old


@pytest.mark.parametrize("mutation", ["missing_issues", "missing_readings", "not_object", "unknown_block", "conflict", "injection"])
def test_terminal_first_failures_do_not_reach_final_model(mutation):
    inputs = inputs_for()
    value = reading(inputs)
    if mutation == "missing_issues": value.pop("issues")
    if mutation == "missing_readings": value.pop("readings")
    if mutation == "not_object": value["readings"] = ["unexpected"]
    if mutation == "unknown_block": value["readings"][0]["quote_ref"]["block"] = 999
    if mutation == "injection": value["issues"] = [dict(category="prompt_injection", severity="high")]
    raw = compact(value)
    if mutation == "conflict": raw = raw.replace('"block":1', '"block":1,"block":2')
    with pytest.raises(ValueError): candidate.prepare(raw, inputs)


def test_input_tampering_and_final_duplicate_keys_remain_blocked():
    inputs, _, final = source_scenario()
    state = candidate.prepare(compact(dict(readings=[], issues=[])), inputs)
    with pytest.raises(ValueError, match="state_changed"):
        candidate.apply(state, compact(final), inputs=replace(inputs, data_json=inputs.data_json+" "))
    with pytest.raises(ValueError, match="compact_duplicate_key"):
        candidate.apply(state, '{"score":0,'+compact(final)[1:], inputs=inputs)


def test_grounded_failed_entry_blocks_before_input_or_provider(monkeypatch):
    from scripts import run_golden_integrated_review as runner
    monkeypatch.setattr(runner, "load_inputs", lambda *_: pytest.fail("loaded inputs"))
    with pytest.raises(ValueError, match="strict_first_reference_failed"):
        runner.run(SimpleNamespace(execute=True), grounded=True)


def test_deadline_failed_entry_blocks_before_input_ci_credentials_or_provider(monkeypatch):
    from scripts import run_golden_integrated_review as runner
    monkeypatch.setattr(runner, "load_inputs", lambda *_: pytest.fail("loaded inputs"))
    monkeypatch.setattr(runner, "verify_public_ci", lambda *_: pytest.fail("called CI"))
    with pytest.raises(ValueError, match="provisional_reading_final_review_deadline"):
        runner.run(SimpleNamespace(execute=True), advisory=True)


def test_first_navigation_reading_can_be_classified_without_fabricated_fact_audit():
    inputs, _, final = source_scenario("## 资料\n\n官方补丁16.17。")
    final["reviewed_blocks"] = [1, 2]
    final["heading_reviews"] = [dict(block_id=1, kind="navigation")]
    final["source_checks"][0]["quote_ref"] = dict(block=2)
    first = dict(readings=[dict(quote_ref=dict(block=1), context_refs=[], interpretation="这是导航标题。")], issues=[])
    result, _ = candidate.apply(candidate.prepare(compact(first), inputs), compact(final), inputs=inputs)
    assert result.verdict == "pass"
    final["heading_reviews"][0]["kind"] = "assertion"
    with pytest.raises(ValueError):
        candidate.apply(candidate.prepare(compact(first), inputs), compact(final), inputs=inputs)


@pytest.mark.parametrize("context", [None, "bad reference", [1, "text"], {"block": 1, "tail": "tail"},
    {"block": 1, "head": None}, {"block": 1, "head": "a", "tail": None}, {"extra": True}])
def test_malformed_context_and_reference_projection_roundtrip_exact(context):
    inputs = inputs_for()
    value = reading(inputs)
    value["readings"][0]["context_refs"] = [context]
    value["readings"][0]["quote_ref"]["extra"] = {"unparsed": "keep"}
    state = candidate.prepare(compact(value), inputs)
    projected = candidate.project_readings(value["readings"])
    assert candidate.restore_readings(projected) == value["readings"]
    candidate.second_request(state)


def test_long_provisional_output_stops_locally_before_second_provider_call():
    from tests.test_golden_comparison_workflow import make_request
    from tests.test_golden_integrated_review import ReplayProvider
    from app.evaluation.golden_integrated_runtime import BudgetedReviewSender
    req = make_request(inputs_for())
    raw = compact(dict(readings=[dict(quote_ref=dict(block=1), context_refs=[],
        interpretation="超长待核查内容" * 30000)], issues=[]))
    provider = ReplayProvider(lambda *_: raw)
    flow = candidate.ProvisionalReadingWorkflow(BudgetedReviewSender(provider))
    with pytest.raises(ValueError, match="request_budget_exceeded"):
        flow.evaluate(req)
    assert flow.stopped and len(provider.requests) == 1
