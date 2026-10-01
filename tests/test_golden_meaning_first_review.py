"""Interpretation isolation and correction; scripted outputs are not quality proof."""
from dataclasses import replace

import pytest

from app.evaluation import golden_meaning_first_review as meaning
from app.evaluation.golden_integrated_runtime import BudgetedReviewSender
from app.evaluation.golden_bounded_correction_requests import source_data
from app.evaluation.golden_contextual_requests import restore
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.harness.steps import EvaluationRequest, RevisionRequest, KnowledgeEvidence
from app.report_validation import COACH_REPORT_HEADINGS
from tests.test_golden_integrated_review import ReplayProvider
from tests.test_golden_typed_review import values, source_scenario, check
from tests.test_golden_comparison_reassessment import inputs_for
from tests.test_golden_bounded_correction import issue
from tests.test_golden_review_source_catalog import source_input
from tests.test_golden_fact_candidate import summary


def reading(inputs, quotes=None, text="只解释原句含义，尚未核对事实。"):
    return dict(report_sha256=digest(inputs.source.report), reviewed_blocks=list(range(1, len(inputs.source.blocks) + 1)),
        readings=[dict(quote_ref=q, context_refs=[], interpretation=text) for q in (quotes or [dict(block=1)])], issues=[])


def test_first_step_sees_complete_report_but_not_facts_or_computed_navigation():
    inputs = inputs_for()
    data = strict_json(inputs.data_json)
    data["deterministic_source_facts"] = "FACT_SENTINEL"
    changed = replace(inputs, data_json=compact(data), pack_json=compact({"not": "sent"}))
    first = meaning.first_request(inputs)
    assert first == meaning.first_request(changed)
    assert inputs.source.blocks[0][1] in first.messages[1].content
    assert "FACT_SENTINEL" not in str(first.messages)
    assert "comparison_evidence" not in first.messages[1].content


def test_second_step_keeps_full_sources_and_challengeable_first_reading():
    inputs = inputs_for()
    before = reading(inputs, text="故意错误地把四场中单读成五局混合样本；下一步须能纠正。")
    state = meaning.prepare(compact(before), inputs)
    second = meaning.second_request(state)
    body = strict_json(second.messages[1].content.split("[UNTRUSTED DATA]\n")[1].split("\n[END UNTRUSTED DATA]")[0])
    assert "reading_tables" in body and "comparison_evidence" not in body
    body["deterministic_source_facts"] = strict_json(inputs.data_json)["deterministic_source_facts"]
    restored = restore(body)
    for k, v in source_data(inputs).items(): assert restored[k] == v
    _, final = values(inputs)
    result, journal = meaning.apply(state, compact(final), inputs=inputs)
    assert result.verdict == "pass"
    assert journal["reading_hypotheses"]["readings"][0]["interpretation"] == before["readings"][0]["interpretation"]
    assert {b["cohort"] for row in journal["comparison_bindings"] for b in row["bindings"]} == {"MIDDLE"}
    assert not journal["semantic_approval"]
    for a in final["audits"]: a["claims"] = []
    with pytest.raises(ValueError, match="reviewed_source_lost"):
        meaning.apply(state, compact(final), inputs=inputs)


@pytest.mark.parametrize("change", ["report", "inventory", "quote", "context", "security"])
def test_invalid_reading_cannot_be_treated_as_a_valid_hypothesis(change):
    inputs = inputs_for()
    value = reading(inputs)
    if change == "report": value["report_sha256"] = "0" * 64
    if change == "inventory": value["reviewed_blocks"] = [2]
    if change == "quote": value["readings"][0]["quote_ref"] = dict(block=999)
    if change == "context": value["readings"][0]["context_refs"] = [dict(block=999)]
    if change == "security": value["issues"] = [dict(issue(inputs, inputs.source.report), category="prompt_injection", severity="high")]
    with pytest.raises(ValueError): meaning.prepare(compact(value), inputs)


def test_textual_issue_cannot_disappear_without_explicit_disposition():
    inputs, _, final = source_scenario()
    before = reading(inputs)
    before["issues"] = [issue(inputs, inputs.source.report)]
    with pytest.raises(ValueError, match="issue_disposition"):
        meaning.apply(meaning.prepare(compact(before), inputs), compact(final), inputs=inputs)


def test_full_revision_flow_uses_native_review_and_rechecks_original_sources():
    report = "\n\n".join(COACH_REPORT_HEADINGS) + "\n\n官方补丁16.18。\n\n建议核对单局。[K1]"
    revised = report.replace("16.18", "16.17")
    data = strict_json(source_input().data_json)
    req = EvaluationRequest(summary(), data["deterministic_source_facts"], KnowledgeEvidence.empty(), report, "检查观摩报告")
    inputs = meaning.MeaningFirstWorkflow.build_inputs(req)
    fixed = meaning.MeaningFirstWorkflow.build_inputs(replace(req, report=revised))
    replies = []
    for current, text, failed in ((inputs, "官方补丁16.18。", True), (fixed, "官方补丁16.17。", False)):
        quote = current.source.reference(text)
        first = reading(current, [quote])
        _, final = values(current)
        for a in final["audits"]: a["claims"] = []
        final["source_checks"] = [check(quote, reported="16.18" if failed else "16.17")]
        if failed:
            final["source_checks"][0]["disposition"] = "unsupported"
            final.update(score=70, verdict="needs_revision", issues=[issue(current, text, "fact_error")])
        replies += [compact(first), compact(final)]
        if failed: replies.append(revised)
    provider = ReplayProvider(lambda _, n: replies[n-1])
    sender = BudgetedReviewSender(provider)
    flow = meaning.MeaningFirstWorkflow(sender)
    initial = flow.evaluate(req)
    draft = flow.revise(RevisionRequest(req.player_summary, req.deterministic_report, req.knowledge, req.report, initial))
    with pytest.raises(ValueError, match="source_changed"):
        flow.evaluate(replace(req, report=draft.report, deterministic_report="changed"))
    final = flow.evaluate(replace(req, report=draft.report))
    assert final.verdict.value == "pass" and flow.calls == sender.budget.calls == 5
    assert flow.last_journal["source_checks"][0]["literals"][0]["matches"]
    assert sender.budget.tokens == 100


def test_prompt_notation_preserves_contract_and_rejects_unknown_schema_constraints():
    from app.evaluation.golden_schema_notation import schema_notation
    from app.evaluation.golden_typed_review import TypedReview
    inputs = inputs_for()
    request = meaning.second_request(meaning.prepare(compact(reading(inputs)), inputs))
    assert request.response_contract.schema_dict() == TypedReview.model_json_schema()
    text = request.messages[1].content
    assert 'comparisons:Array<Comparison>' in text
    assert 'head?:' in text and 'scope_source?:' in text
    assert 'places:(integer' in text  # nullable, but required
    assert '"maxItems":78' in text and '"maximum":100' in text
    assert '"pattern":"^[0-9a-f]{64}$"' in text
    with pytest.raises(ValueError, match="unknown_constraint"):
        schema_notation(dict(type="string", not_implemented=True))


def test_oversized_first_reading_stops_before_another_provider_call():
    inputs = inputs_for()
    value = reading(inputs)
    value["readings"] *= 64
    for row in value["readings"]:
        row["interpretation"] = "说明原文中的主体与完整比较对象及适用范围" * 6
    # Large source plus a valid but verbose first response cannot be truncated
    # or sent using a lowered estimator just to fit the next request.
    data = strict_json(inputs.data_json)
    data["deterministic_source_facts"] += "额外原始资料" * 12000
    enlarged = replace(inputs, data_json=compact(data))
    state = meaning.prepare(compact(value), enlarged)
    with pytest.raises(ValueError, match="budget_exceeded"):
        meaning.second_request(state)


def test_failed_meaning_entry_stops_before_inputs_ci_credentials_or_provider(monkeypatch):
    from types import SimpleNamespace
    from scripts import run_golden_integrated_review as runner
    monkeypatch.setattr(runner, "load_inputs", lambda *_: pytest.fail("loaded inputs"))
    monkeypatch.setattr(runner, "verify_public_ci", lambda *_: pytest.fail("called CI"))
    with pytest.raises(ValueError, match="meaning_first_duplicate_keys_and_interpretation_failed"):
        runner.run(SimpleNamespace(execute=True), meaning=True)
