"""Contract and budget regressions; scripted semantics are explicitly untrusted."""
from copy import deepcopy
from dataclasses import replace
import json
import socket

import pytest

from app.evaluation import golden_native_issues_review as native
from app.evaluation.golden_integrated_runtime import BudgetedReviewSender
from app.evaluation.golden_review_experiment import compact, digest
from app.harness.steps import RevisionRequest
from app.providers.errors import ProviderResponseError
from scripts.check_native_contract_options import (audit, actual_case, corrected_case3, editor_value,
    OfflineResponses, PASS, path, recovery_responses, prepare_editor_diagnostic)
from scripts.native_contract_options import (OfflineEditorWorkflow, validate_editor, validate_anchors,
    anchored_request, editor_request, body)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*args, **kwargs):
        pytest.fail('offline contract comparison attempted network access')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'create_connection', denied)


def revision(req, initial):
    return RevisionRequest(req.player_summary, req.deterministic_report, req.knowledge, req.report, initial)


def test_complete_offline_audit_preserves_actual_failure_and_semantic_counterexamples():
    result = audit()
    assert result['provider_calls'] == 0 and not result['semantic_fix_proven']
    a, b = result['option_a'], result['option_b']
    assert a['false_positive_still_protocol_valid']
    assert len(a['claim_shapes']) == 7 and len(a['history_shapes']) == 5
    assert len(a['attribution_shapes']) == 2
    assert b['changed_blocks'] == [6] and b['original_review_retained']
    assert b['unaffected_block6_prefix_preserved']
    assert len(b['normal_three_call_path']) == 3 and len(b['maximum_five_call_path']) == 5
    assert b['five_call_full_reservation'] <= b['total_budget']
    # Record the measured boundary rather than making the audit falsely green.
    assert b['historical_full_reservation'] > b['total_budget']
    assert b['historical_saturated_budget']['completed_calls'] == 4
    assert b['historical_saturated_budget']['stop_reason'] == 'token_budget_exhausted'
    assert all(n['protocol_valid'] and not n['semantic_acceptance']
               for n in b['semantically_wrong_but_structurally_valid'])


def test_prepared_editor_diagnostic_does_not_relabel_extraction_as_model_output():
    plan = prepare_editor_diagnostic()
    assert plan['live_status'] == 'offline_unregistered' and plan['provider_calls'] == 0
    assert not plan['initial_reviewer_qualified'] and not plan['existing_guard_bypassed']
    mixed, universal, extracted = plan['cases']
    for row, index in ((mixed, 3), (universal, 4)):
        req, saved = actual_case(index)
        assert row['report'] == req.report
        assert row['proposed_review_raw'] == saved['responses'][0]['content']
        assert row['input_sha256'] == digest(native.build_inputs(req).data_json)
    assert extracted['provenance'].startswith('analyst_extraction')
    assert extracted['source_review_sha256'] == mixed['proposed_review_sha256']
    assert extracted['proposed_review_sha256'] != extracted['source_review_sha256']
    assert extracted['report'] == actual_case(1)[0].report
    assert json.loads(extracted['proposed_review_raw'])['issues'] == [json.loads(mixed['proposed_review_raw'])['issues'][1]]


@pytest.mark.parametrize('damage', ['missing', 'duplicate', 'unknown', 'wrong_hash', 'source',
    'withdraw_changed', 'apply_unchanged', 'truncated', 'wrong_type', 'missing_sections'])
def test_invalid_editor_outputs_stop_without_hidden_retry(damage):
    req, raw, value = corrected_case3()
    bad = deepcopy(value)
    if damage == 'missing': bad['decisions'].pop()
    elif damage == 'duplicate': bad['decisions'][1]['issue_id'] = 1
    elif damage == 'unknown': bad['decisions'][1]['issue_id'] = 3
    elif damage == 'wrong_hash': bad['review_sha256'] = '0'*64
    elif damage == 'source': bad['decisions'][0]['source_ids'] = [999999]
    elif damage == 'withdraw_changed':
        for d in bad['decisions']: d['disposition'] = 'withdraw'
    elif damage == 'apply_unchanged': bad['report'] = req.report
    elif damage == 'wrong_type': bad['decisions'][0]['issue_id'] = '1'
    elif damage == 'missing_sections': bad['report'] = '省略原报告'
    response = compact(bad)
    if damage == 'truncated': response = response[:-10]
    provider = OfflineResponses([raw, response])
    flow = OfflineEditorWorkflow(BudgetedReviewSender(provider))
    initial = flow.evaluate(req)
    with pytest.raises(ValueError): flow.revise(revision(req, initial))
    assert flow.stopped and flow.revisions == 1 and len(provider.requests) == 2
    with pytest.raises(ValueError): flow.revise(revision(req, initial))
    assert len(provider.requests) == 2

def test_real_positive_needs_no_editor_and_real_universal_negative_retains_revision():
    req, saved = actual_case(1)
    provider = OfflineResponses([saved['responses'][0]['content']])
    flow = OfflineEditorWorkflow(BudgetedReviewSender(provider))
    result = flow.evaluate(req)
    assert result.verdict.value == 'pass' and len(provider.requests) == 1
    with pytest.raises(ValueError): flow.revise(revision(req, result))
    req, saved = actual_case(4)
    raw = saved['responses'][0]['content']
    inputs = native.build_inputs(req)
    value = editor_value(inputs, raw, saved['revised_report'], ['apply'])
    flow, provider, _ = path(req, [raw, compact(value), saved['responses'][-1]['content']])
    assert len(provider.requests) == 3 and flow.editor_journal['review_raw'] == raw


def test_all_withdrawn_keeps_original_and_cannot_skip_independent_recheck():
    req, raw, _ = corrected_case3()
    inputs = native.build_inputs(req)
    value = editor_value(inputs, raw, req.report, ['withdraw', 'withdraw'])
    provider = OfflineResponses([raw, compact(value), raw])
    flow = OfflineEditorWorkflow(BudgetedReviewSender(provider))
    initial = flow.evaluate(req)
    draft = flow.revise(revision(req, initial))
    assert draft.report == req.report
    final = flow.evaluate(replace(req, report=draft.report))
    assert final.verdict.value == 'needs_revision' and len(provider.requests) == 3
    assert flow.editor_journal['semantic_approval'] is False
    with pytest.raises(ValueError): flow.revise(revision(req, final))


def test_source_evaluation_and_actual_edit_identity_are_bound():
    req, raw, value = corrected_case3()
    provider = OfflineResponses([raw, compact(value), PASS])
    flow = OfflineEditorWorkflow(BudgetedReviewSender(provider))
    initial = flow.evaluate(req)
    with pytest.raises(ValueError, match='source_changed'):
        flow.revise(replace(revision(req, initial), report=req.report+'\n'))
    # Nested issues are mutable even when the result container is frozen.
    old = initial.issues[0]['suggested_correction']
    initial.issues[0]['suggested_correction'] = 'forged'
    with pytest.raises(ValueError, match='evaluation_changed'):
        flow.revise(revision(req, initial))
    initial.issues[0]['suggested_correction'] = old
    draft = flow.revise(revision(req, initial))
    assert len(provider.requests) == 2
    with pytest.raises(ValueError, match='recheck_source_changed'): flow.evaluate(req)
    assert len(provider.requests) == 2
    flow.evaluate(replace(req, report=draft.report))
    final_input = body(provider.requests[-1])['source_index']['blocks']
    assert [b['text'] for b in final_input] == [t for _, t in native.build_inputs(replace(req, report=draft.report)).source.blocks]


def test_anchor_reassessment_preserves_previous_inventory_and_rejects_forged_quotes():
    req, first, _ = corrected_case3()
    inputs = native.build_inputs(req)
    value = json.loads(first)
    for issue in value['issues']:
        issue.update(claim=inputs.source.blocks[issue['block']-1][1], context=[])
    previous = compact(dict(value, score='70'))
    value['issue_resolutions'] = [dict(previous_id=n, disposition='replaced', final_issue=n,
        source_ids=i['source_ids'], explanation='分析者恢复见证') for n,i in enumerate(value['issues'],1)]
    request = anchored_request(inputs, previous_raw=previous, diagnostics=[{'code':'score_type'}])
    assert request.metadata['review_phase'] == 'offline_anchored_reassessment'
    assert body(request)['previous_review'] == json.loads(previous)
    validate_anchors(compact(value), inputs, previous_raw=previous)
    with pytest.raises(ValueError): validate_anchors(compact(value), inputs)
    value['issues'][0]['claim'] = '原报告没有写过这一句'
    with pytest.raises(ValueError, match='anchor_not_unique'):
        validate_anchors(compact(value), inputs, previous_raw=previous)


def test_security_issue_is_terminal_before_editor():
    req, raw, _ = corrected_case3()
    value = json.loads(raw)
    value['issues'][0]['category'] = 'prompt_injection'
    with pytest.raises(ValueError, match='security_terminal'):
        editor_request(native.build_inputs(req), compact(value))


def test_shared_budget_counts_generation_and_rejects_sixth_or_overrun():
    req, raw, value = corrected_case3()
    inputs = native.build_inputs(req)
    responses = recovery_responses(inputs, raw, value)
    provider = OfflineResponses(responses)
    sender = BudgetedReviewSender(provider)
    # Occupied call slots are independent of generation semantics. Actual
    # generation requests are measured by the separate product compiler test.
    sender.budget.calls = 2
    flow = OfflineEditorWorkflow(sender)
    initial = flow.evaluate(req)
    draft = flow.revise(revision(req, initial))
    with pytest.raises(ProviderResponseError, match='external_call_budget_exhausted'):
        flow.evaluate(replace(req, report=draft.report))
    assert len(provider.requests) == 3 and flow.stopped
    provider = OfflineResponses([raw])
    sender = BudgetedReviewSender(provider)
    sender.budget.tokens = 401920
    with pytest.raises(ProviderResponseError, match='token_budget_exhausted'):
        OfflineEditorWorkflow(sender).evaluate(req)
    assert not provider.requests


def test_remaining_elapsed_time_limits_the_existing_editor_slot():
    req, raw, value = corrected_case3()
    now = [0]
    provider = OfflineResponses([raw, compact(value)])
    sender = BudgetedReviewSender(provider, clock=lambda: now[0])
    flow = OfflineEditorWorkflow(sender)
    initial = flow.evaluate(req)
    now[0] = 890
    draft = flow.revise(revision(req, initial))
    assert provider.requests[-1].timeout_s == 10
    now[0] = 900
    with pytest.raises(ProviderResponseError, match='timeout'):
        flow.evaluate(replace(req, report=draft.report))
    assert len(provider.requests) == 2
