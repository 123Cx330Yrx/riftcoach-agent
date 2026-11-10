"""Two-state contract tests; synthetic decisions do not certify semantics."""
from copy import deepcopy
from dataclasses import replace
import socket

import pytest

from app.evaluation import golden_native_issues_review as native
from app.evaluation.golden_review_experiment import compact
from app.evaluation.golden_stream_bridge import validate_request, CAPACITY_TRANSPORT_ID
from app.harness.steps import RevisionRequest
from scripts.blind_edit_settlement import (blind_request, settlement_request, validate_settlement,
    expand_original, OfflineBlindEditWorkflow)
from scripts.check_blind_edit_settlement import run, path, settlement_value
from scripts.check_native_contract_options import corrected_case3, assert_complete, OfflineResponses
from scripts.check_native_issue_identity_contract import witnesses
from scripts.native_contract_options import body
from app.evaluation.golden_integrated_runtime import BudgetedReviewSender


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*a, **k): pytest.fail('offline settlement reached network')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'create_connection', denied)


def case():
    req, raw, edit = corrected_case3()
    before = native.build_inputs(req)
    after = native.build_inputs(replace(req, report=edit['report']))
    return req, raw, edit, before, after, settlement_value(before, after, raw)


def test_complete_three_and_five_call_paths_do_not_invent_budget_capacity():
    result = run()
    assert result['normal_reservation'] < 401920 < result['five_reservation']
    assert len(result['five_calls']) == 5 and result['scripted_five_usage'] == 100
    assert result['saturated_five_path']['completed_calls'] == 4
    assert result['saturated_five_path']['stop_reason'] == 'token_budget_exhausted'
    assert result['saturated_five_path']['stopped']
    assert result['real_bad_edit_remains_semantically_rejected']['structure_valid']
    assert not result['real_bad_edit_remains_semantically_rejected']['semantic_approval']


def test_same_block_issues_reordered_do_not_enter_blind_edit_but_stay_in_final():
    req, _, orders = witnesses()
    _, _, edit = corrected_case3()
    before = native.build_inputs(req)
    after = native.build_inputs(replace(req, report=edit['report']))
    blind_wires, final_views = [], []
    for order in orders:
        validity = tuple('confirmed' if d == 'apply' else 'false_positive' for d in order['expected_host_only'])
        status = tuple('corrected' if d == 'apply' else 'not_required' for d in order['expected_host_only'])
        result = settlement_value(before, after, order['raw'], validities=validity, statuses=status)
        final, flow, provider, _ = path(req, [order['raw'], edit['report'], compact(result)])
        assert final.verdict.value == 'pass'
        assert_complete(provider.requests[1], before)
        blind_wires.append(validate_request(provider.requests[1], transport_id=CAPACITY_TRANSPORT_ID))
        final_views.append(body(provider.requests[2])['original_review'])
        assert flow.last_journal['original_review_journal']['raw'] == order['raw']
        assert not flow.last_journal['initial_reviewer_qualified']
    assert blind_wires[0] == blind_wires[1]
    assert final_views[0]['issues'] == final_views[1]['issues'][::-1]


def test_same_claim_distinct_allegations_remain_distinct():
    req, raw, edit, before, after, _ = case()
    value = native.strict_json(raw)
    value['issues'][1] = dict(value['issues'][0],
        explanation='该合并五局比较句把五局都说成中单，遗漏辅助身份。',
        suggested_correction='声明五局包括辅助。')
    # Same compound claim already explicitly includes the support game.
    bound_raw = compact(value)
    response = settlement_value(before, after, bound_raw)
    _, _, journal = validate_settlement(compact(response), after, before, bound_raw)
    assert len(journal['decisions']) == 2
    assert journal['decisions'][1]['original_validity'] == 'false_positive'
    assert not journal['semantic_approval']


def test_source_projection_expands_exactly_with_separate_report_indices():
    req, raw, edit, before, after, _ = case()
    built = settlement_request(after, before, raw)
    data = body(built)
    assert_complete(built, after)
    old = native.request_data(before)
    assert data['original_source_index'] == old['source_index']
    assert data['original_source_index'] != data['source_index']
    for key, identity in [('source_roots', 'catalog_sha256'), ('computed_evidence', 'source_digest')]:
        assert expand_original(data, key, identity) == old[key]
    other = native.build_inputs(replace(req, report=edit['report'], user_utterance='A different user request'))
    with pytest.raises(ValueError, match='source_snapshot_changed'):
        settlement_request(other, before, raw)


@pytest.mark.parametrize('damage', ['missing', 'duplicate', 'original_hash', 'revised_hash',
    'review_hash', 'unknown_source', 'false_positive_corrected', 'unresolved_pass', 'persists_pass',
    'current_bad_block', 'old_security', 'new_security'])
def test_inconsistent_settlements_cannot_return_pass(damage):
    req, raw, edit, before, after, value = case()
    if damage == 'missing': value['decisions'].pop()
    elif damage == 'duplicate': value['decisions'][1]['issue_id'] = 1
    elif damage == 'original_hash': value['original_report_sha256'] = '0'*64
    elif damage == 'revised_hash': value['revised_report_sha256'] = value['original_report_sha256']
    elif damage == 'review_hash': value['original_review_sha256'] = '0'*64
    elif damage == 'unknown_source': value['decisions'][0]['source_ids'] = [999999]
    elif damage == 'false_positive_corrected': value['decisions'][1]['revision_status'] = 'corrected'
    elif damage == 'unresolved_pass': value['decisions'][0].update(original_validity='unresolved', revision_status='unresolved')
    elif damage == 'persists_pass': value['decisions'][0]['revision_status'] = 'persists'
    elif damage == 'current_bad_block':
        issue = native.strict_json(raw)['issues'][0]
        issue['block'] = 64
        value['review'].update(score=70, verdict='needs_revision', issues=[issue])
    elif damage == 'old_security':
        old = native.strict_json(raw)
        old['issues'][0]['category'] = 'prompt_injection'
        raw = compact(old)
    else:
        issue = native.strict_json(raw)['issues'][0]
        issue['category'] = 'prompt_injection'
        value['review'].update(verdict='fail', score=0, issues=[issue])
    with pytest.raises(ValueError): validate_settlement(compact(value), after, before, raw)


def test_uncorrected_true_error_or_new_error_keeps_report_rejected():
    req, raw, edit, before, after, value = case()
    still_bad = settlement_value(before, before, raw, statuses=('persists', 'not_required'),
        review=native.strict_json(raw))
    payload, _, _ = validate_settlement(compact(still_bad), before, before, raw)
    assert payload.verdict == 'needs_revision'
    claimed = settlement_value(before, before, raw)
    with pytest.raises(ValueError, match='repair_without_change'):
        validate_settlement(compact(claimed), before, before, raw)
    # A separate new-report finding blocks acceptance even if old issues settled.
    value['review'] = native.strict_json(raw)
    payload, _, _ = validate_settlement(compact(value), after, before, raw)
    assert payload.verdict == 'needs_revision'


def test_changed_sources_and_second_revision_are_rejected_without_calls():
    req, raw, edit, before, after, response = case()
    provider = OfflineResponses([raw, edit['report'], compact(response)])
    flow = OfflineBlindEditWorkflow(BudgetedReviewSender(provider))
    first = flow.evaluate(req)
    revision = RevisionRequest(req.player_summary, req.deterministic_report, req.knowledge, req.report, first)
    with pytest.raises(ValueError, match='source_changed'):
        flow.revise(replace(revision, report=req.report+'\n'))
    assert len(provider.requests) == 1
    flow.revise(revision)
    with pytest.raises(ValueError, match='recheck_source_changed'): flow.evaluate(req)
    final = flow.evaluate(replace(req, report=edit['report']))
    assert final.verdict.value == 'pass'
    with pytest.raises(ValueError, match='revision_order_invalid'): flow.revise(revision)
    assert len(provider.requests) == 3


@pytest.mark.parametrize('location', ['top', 'nested'])
def test_misplaced_new_issues_stop_before_recovery_request(location):
    req, raw, edit, before, after, value = case()
    malformed = deepcopy(value)
    extra = {'issues': [native.strict_json(raw)['issues'][0]]}
    malformed.update(extra if location == 'top' else {'unexpected': extra})
    provider = OfflineResponses([raw, edit['report'], compact(malformed), compact(value)])
    flow = OfflineBlindEditWorkflow(BudgetedReviewSender(provider))
    initial = flow.evaluate(req)
    flow.revise(RevisionRequest(req.player_summary, req.deterministic_report, req.knowledge, req.report, initial))
    with pytest.raises(ValueError, match='settlement_recovery_misplaced_issues'):
        flow.evaluate(replace(req, report=edit['report']))
    assert len(provider.requests) == 3 and flow.stopped


def test_nested_current_review_findings_require_explicit_recovery_mapping():
    req, raw, edit, before, after, value = case()
    malformed = deepcopy(value)
    malformed['review'] = native.strict_json(raw)
    malformed['review']['score'] = '70'
    prior_raw = compact(malformed)
    with pytest.raises(ValueError, match='resolution_inventory'):
        validate_settlement(compact(value), after, before, raw, previous_raw=prior_raw)
    recovered = deepcopy(value)
    recovered['review']['issue_resolutions'] = [dict(previous_id=n, disposition='withdrawn', final_issue=None,
        source_ids=d['source_ids'], explanation='分析者映射演练，不是原指控撤销已获语义证明。')
        for n, d in enumerate(value['decisions'], 1)]
    validate_settlement(compact(recovered), after, before, raw, previous_raw=prior_raw)
