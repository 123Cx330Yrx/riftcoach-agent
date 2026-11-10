"""Real failed bytes plus synthetic recovery; not evidence of model accuracy."""
from dataclasses import replace
import json
from pathlib import Path

import pytest

from app.evaluation import golden_semantic_review as candidate
from app.evaluation.golden_review_experiment import compact, digest
from app.harness.steps import EvaluationRequest, KnowledgeCitation, KnowledgeEvidence, RevisionRequest
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from tests.test_golden_semantic_review import (
    evaluation_request, fragment_inputs, opinion, problem, resolution, flow_with, request_data,
)


def recorded_failure():
    fixture = json.loads((Path(__file__).parent / 'fixtures/native_heading_recheck_failure.json').read_text(encoding='utf-8'))
    assert digest(fixture['raw']) == fixture['raw_sha256']
    data = fixture['evaluation_request']
    knowledge = data['knowledge']
    knowledge['citations'] = tuple(KnowledgeCitation(**r) for r in knowledge['citations'])
    knowledge['source_ids'] = tuple(knowledge['source_ids'])
    return fixture['raw'], EvaluationRequest(**dict(data, knowledge=KnowledgeEvidence(**knowledge)))


def analyst_corrected_opinion(raw):
    value, _ = candidate.provisional_review(raw)
    value['reviews'][1].update(kind='navigation', explanation='总体结论仅为章节标题。')
    value['reviews'][2]['explanation'] = value['reviews'][2]['explanation'].replace('辅助1局0负', '辅助1局0胜、1负')
    value['summary'] = value['summary'].replace('辅助1局0负', '辅助1局0胜、1负')
    value['reviews'][8].update(kind='navigation', explanation='所选四场中单观察是范围标签；后文另有明确标注的辅助单局说明。')
    return value


def test_real_failure_is_not_accepted_by_trimming_and_all_original_text_reaches_reassessment():
    raw, req = recorded_failure()
    inputs = candidate.build_inputs(req)
    with pytest.raises(json.JSONDecodeError, match='Extra data'):
        candidate.validate(raw, inputs)
    value, suffix = candidate.provisional_review(raw)
    assert suffix == '\n``结束。'
    assert '辅助1局0负' in value['reviews'][2]['explanation']
    assert '生存与发育结果较好' in value['reviews'][1]['explanation']
    built = candidate.request(inputs, previous_raw=raw, diagnostics=[{'code': 'trailing_non_json'}])
    data = request_data(built)
    assert data['previous_review'] == value
    assert data['previous_non_json_suffix'] == suffix
    assert data['previous_raw_sha256'] == digest(raw)
    assert size(built) <= 63936
    # Syntax/source identity alone cannot prove that the explanation is true.
    payload, _, _ = candidate.validate(compact(value), inputs)
    assert payload.verdict == 'pass'  # Known semantic counterexample, NOT approval.


def test_recorded_failure_enters_one_complete_reassessment_and_preserves_receipts():
    raw, req = recorded_failure()
    # Explicitly analyst-authored: demonstrates reachability, not model repair.
    value = analyst_corrected_opinion(raw)
    flow, provider, _ = flow_with([raw, compact(value)])
    result = flow.evaluate(req)
    assert result.verdict.value == 'pass' and len(provider.requests) == 2
    assert flow.last_journal['previous_raw'] == raw
    assert flow.last_journal['semantic_approval'] is False
    assert flow.last_journal['raw'] == compact(value)


@pytest.mark.parametrize('first_needs_reassessment', [False, True])
def test_full_revision_path_uses_shared_bound_and_preserves_original_findings(first_needs_reassessment):
    fixture = json.loads((Path(__file__).parent / 'fixtures/native_heading_recheck_failure.json').read_text(encoding='utf-8'))
    raw, recheck = recorded_failure()
    initial = replace(recheck, report=fixture['initial_report'])
    replies = [fixture['initial_review_raw']]
    if first_needs_reassessment:
        corrected = json.loads(replies[0])
        corrected['issue_resolutions'] = [dict(previous_id=1, disposition='retained', final_issue=1,
            source_ids=corrected['reviews'][3]['issues'][0]['source_ids'], explanation='合成回放保留原始标题问题，未声称真实纠正。')]
        replies = [replies[0] + '\ncommentary', compact(corrected)]
    replies.extend([recheck.report, raw, compact(analyst_corrected_opinion(raw))])
    flow, provider, sender = flow_with(replies)
    verdict = flow.evaluate(initial)
    draft = flow.revise(RevisionRequest(initial.player_summary, initial.deterministic_report,
        initial.knowledge, initial.report, verdict))
    result = flow.evaluate(replace(initial, report=draft.report))
    assert result.verdict.value == 'pass'
    assert sender.budget.calls == flow.calls == (5 if first_needs_reassessment else 4)
    assert flow.revisions == 1 and flow.evaluations == 2
    assert flow.last_journal['previous_raw'] == raw
    assert all(size(r) <= 63936 for r in provider.requests)
    assert all(r.max_tokens == 32768 and r.timeout_s <= 300 for r in provider.requests)


def test_trailing_text_does_not_erase_first_issues_or_allow_direct_final_acceptance():
    inputs = fragment_inputs()
    first = opinion(inputs, failed=True)
    raw = compact(first) + '\nSome unstructured commentary.'
    final = opinion(inputs)
    with pytest.raises(ValueError, match='native_issue_resolution_inventory'):
        candidate.validate(compact(final), inputs, previous_raw=raw)
    final['issue_resolutions'] = [resolution(inputs, disposition='withdrawn', final_issue=None)]
    flow, provider, _ = flow_with([raw, compact(final)])
    assert flow.evaluate(evaluation_request()).verdict.value == 'pass'
    assert request_data(provider.requests[1])['previous_issues'][0]['issue'] == first['reviews'][0]['issues'][0]
    assert flow.last_journal['previous_raw'] == raw


@pytest.mark.parametrize('tail', ['\n{}', '\n[]', '\nnull', '\ntrue', '\n42', '\n"second value"', '\nnote: {"issues":[]}',
    '\nnote: {"issues":', '\nnote: [', '\nnote: [1,', '\nnote: [null]', '\nnote: [NaN]', '\nnote: [tru'])
def test_second_json_values_are_ambiguous_and_terminal(tail):
    flow, provider, _ = flow_with([compact(opinion(fragment_inputs())) + tail])
    with pytest.raises(ValueError):
        flow.evaluate(evaluation_request())
    assert flow.stopped and len(provider.requests) == 1


@pytest.mark.parametrize('tail', ['\n说明：[K1]支持本建议。', '\n[reference](https://example.invalid)', '\n占位符{subject}'])
def test_non_json_markdown_is_retained_for_reassessment_but_never_accepted(tail):
    raw = compact(opinion(fragment_inputs())) + tail
    with pytest.raises(ValueError): candidate.validate(raw, fragment_inputs())
    value, suffix = candidate.provisional_review(raw)
    assert suffix == tail
    assert value == opinion(fragment_inputs())
    built = candidate.request(fragment_inputs(), previous_raw=raw)
    assert request_data(built)['previous_non_json_suffix'] == tail


@pytest.mark.parametrize('raw', ['{"reviews":', '{"score":1,"score":2}\nnote', '{"score":NaN}\nnote', 'prefix {"score":1}'])
def test_incomplete_duplicate_nonfinite_or_unanchored_objects_are_terminal(raw):
    flow, provider, _ = flow_with([raw])
    with pytest.raises(ValueError):
        flow.evaluate(evaluation_request())
    assert flow.stopped and len(provider.requests) == 1


def test_high_injection_in_complete_object_still_stops_before_reassessment():
    first = opinion(fragment_inputs(), failed=True)
    first['reviews'][0]['issues'][0] = problem(severity='high', category='prompt_injection')
    flow, provider, _ = flow_with([compact(first) + '\ncommentary'])
    with pytest.raises(ValueError, match='native_security_terminal'):
        flow.evaluate(evaluation_request())
    assert flow.stopped and len(provider.requests) == 1


def test_second_malformed_response_is_not_trimmed_or_retried_again():
    raw = compact(opinion(fragment_inputs())) + '\ncommentary'
    flow, provider, _ = flow_with([raw, raw])
    with pytest.raises(json.JSONDecodeError):
        flow.evaluate(evaluation_request())
    assert flow.stopped and len(provider.requests) == 2
