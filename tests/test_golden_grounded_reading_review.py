"""Provisional parsing is not acceptance; final sources/security stay strict."""
from dataclasses import replace

import pytest

from app.evaluation import golden_grounded_reading_review as candidate
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_review_experiment import compact
from app.evaluation.golden_integrated_runtime import BudgetedReviewSender
from app.harness.steps import EvaluationRequest, RevisionRequest, KnowledgeEvidence
from app.report_validation import COACH_REPORT_HEADINGS
from tests.test_golden_meaning_first_review import reading as old_reading
from tests.test_golden_comparison_reassessment import inputs_for
from tests.test_golden_typed_review import values, source_scenario, check
from tests.test_golden_bounded_correction import issue
from tests.test_golden_integrated_review import ReplayProvider
from tests.test_golden_review_source_catalog import source_input
from tests.test_golden_fact_candidate import summary


def reading(inputs, quotes=None, text="只作原句理解，含义可被最终审查纠正。"):
    old = old_reading(inputs, quotes, text)
    return {k: old[k] for k in ("readings", "issues")}


def test_first_input_includes_exact_source_identity_but_no_source_arithmetic():
    inputs = inputs_for()
    request = candidate.first_request(inputs)
    body = strict_json(request.messages[1].content.split("[UNTRUSTED DATA]\n")[1].split("\n[END UNTRUSTED DATA]")[0])
    data = strict_json(inputs.data_json)
    assert body["source_player"] == data["generation_facts"]["player"]
    assert set(body) == {"blocks", "source_player", "user_utterance"}
    data["deterministic_source_facts"] = "changed arithmetic"
    data["generation_facts"]["aggregate"] = {}
    changed = replace(inputs, data_json=compact(data), pack_json="{}")
    assert request == candidate.first_request(changed)
    data["generation_facts"]["player"]["game_name"] = "Different observed player"
    assert request != candidate.first_request(replace(inputs, data_json=compact(data)))
    assert set(request.response_contract.schema_dict()["properties"]) == {"readings", "issues"}


def test_identical_repetition_keeps_raw_meaning_and_issues_without_accepting_final_duplicates():
    inputs, _, final = source_scenario()
    first = reading(inputs, text="错误首读：这不是观摩对象而是阅读者本人。")
    first["issues"] = [issue(inputs, inputs.source.report)]
    raw = compact(first).replace('"block":1', '"block":1,"block":1')
    state = candidate.prepare(raw, inputs)
    assert state.raw == raw and state.reading.issues and state.diagnostics
    assert state.reading.readings[0].interpretation == first["readings"][0]["interpretation"]
    assert "错误首读" in candidate.second_request(state).messages[1].content
    with pytest.raises(ValueError, match="issue_disposition"):
        candidate.apply(state, compact(final), inputs=inputs)
    final["issue_resolutions"] = [dict(target_id="i001", evidence_refs=[],
        sources=final["source_checks"][0]["sources"], explanation="原始字段反驳这个首读判断。")]
    result, journal = candidate.apply(state, compact(final), inputs=inputs)
    assert result.verdict == "pass" and journal["first_raw"] == raw
    assert journal["first_parse_diagnostics"] == state.diagnostics
    assert journal["resolved_issues"][0]["before"] == state.reading.issues[0].model_dump(mode="json")
    duplicate_final = compact(final).replace('"score":95', '"score":95,"score":95')
    if duplicate_final == compact(final):
        duplicate_final = '{"score":' + str(final["score"]) + ',' + compact(final)[1:]
    with pytest.raises(ValueError, match="compact_duplicate_key"):
        candidate.apply(state, duplicate_final, inputs=inputs)


@pytest.mark.parametrize("raw", ['{"x":1,"x":2}', '{"x":true,"x":1}',
    '{"x":{"y":true},"x":{"y":1}}', '{"x":[1,2],"x":[2,1]}'])
def test_conflicting_duplicates_are_never_selected(raw):
    with pytest.raises(ValueError, match="conflicting_duplicate"):
        candidate.provisional_json(raw)


@pytest.mark.parametrize("raw", ['{"x":', '{"x":NaN}', '{"x":1} {"x":2}'])
def test_malformed_json_is_not_repaired(raw):
    with pytest.raises(ValueError): candidate.provisional_json(raw)


def test_high_security_stops_even_with_identical_duplicates_and_unrelated_bad_schema():
    raw = '{"issues":[{"severity":"high","category":"prompt_injection","category":"prompt_injection"}]}'
    with pytest.raises(ValueError, match="correction_security_terminal"):
        candidate.prepare(raw, inputs_for())


def test_unknown_fields_and_changed_source_do_not_disappear():
    inputs = inputs_for()
    first = reading(inputs)
    with pytest.raises(ValueError): candidate.prepare(compact(dict(first, unexpected="preserve me")), inputs)
    state = candidate.prepare(compact(first), inputs)
    _, final = values(inputs)
    with pytest.raises(ValueError, match="state_changed"):
        candidate.apply(state, compact(final), inputs=replace(inputs, data_json=inputs.data_json + " "))


def test_legacy_replay_is_explicit_and_does_not_relabel_old_live_result():
    inputs = inputs_for()
    raw = compact(old_reading(inputs))
    with pytest.raises(ValueError): candidate.prepare(raw, inputs)
    state = candidate.prepare(raw, inputs, legacy_replay=True)
    _, final = values(inputs)
    _, journal = candidate.apply(state, compact(final), inputs=inputs)
    assert journal["historical_replay_only"] and not journal["semantic_approval"]


def test_complete_revision_path_with_identical_first_duplicates_preserves_five_call_limit():
    report = "\n\n".join(COACH_REPORT_HEADINGS) + "\n\n官方补丁16.18。\n\n建议核对单局。[K1]"
    revised = report.replace("16.18", "16.17")
    data = strict_json(source_input().data_json)
    req = EvaluationRequest(summary(), data["deterministic_source_facts"], KnowledgeEvidence.empty(), report, "检查观摩报告")
    inputs = candidate.GroundedReadingWorkflow.build_inputs(req)
    fixed = candidate.GroundedReadingWorkflow.build_inputs(replace(req, report=revised))
    replies = []
    for current, text, failed in ((inputs, "官方补丁16.18。", True), (fixed, "官方补丁16.17。", False)):
        quote = current.source.reference(text)
        first = compact(reading(current, [quote]))
        first = first.replace(f'"block":{quote["block"]}', f'"block":{quote["block"]},"block":{quote["block"]}')
        _, final = values(current)
        for audit in final["audits"]: audit["claims"] = []
        final["source_checks"] = [check(quote, reported="16.18" if failed else "16.17")]
        if failed:
            final["source_checks"][0]["disposition"] = "unsupported"
            final.update(score=70, verdict="needs_revision", issues=[issue(current, text, "fact_error")])
        replies += [first, compact(final)]
        if failed: replies.append(revised)
    provider = ReplayProvider(lambda _, n: replies[n-1])
    sender = BudgetedReviewSender(provider)
    workflow = candidate.GroundedReadingWorkflow(sender)
    initial = workflow.evaluate(req)
    draft = workflow.revise(RevisionRequest(req.player_summary, req.deterministic_report, req.knowledge, req.report, initial))
    with pytest.raises(ValueError, match="source_changed"):
        workflow.evaluate(replace(req, report=draft.report, deterministic_report="changed"))
    final = workflow.evaluate(replace(req, report=draft.report))
    assert final.verdict.value == "pass" and workflow.calls == sender.budget.calls == 5
    assert workflow.last_journal["first_parse_diagnostics"]
    assert sender.budget.tokens == 100
