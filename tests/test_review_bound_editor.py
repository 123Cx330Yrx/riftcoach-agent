"""Synthetic protocol/state-machine evidence, not model success or qualification."""
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from app.evaluation import review_bound_editor as editor
from app.evaluation.source_patch_editor import report_inputs
from app.providers.errors import ProviderResponseError
from tests import test_coarse_revision_editor as prior


def operation():
    op = prior.operation()
    return {k: v for k, v in op.items() if k != 'source_ids'}


def reply(request, edits=None):
    return prior.exchange(request, edits=[operation()] if edits is None else edits, name=editor.TOOL)


def test_transaction_provenance_is_not_per_edit_support_and_complete_input_is_kept():
    req, inputs, accepted, _ = prior.cases()['claim-scope:4']
    prepared = editor.edit_request(inputs, accepted)
    assert prepared.messages[1:] == editor.Current.make_request(inputs, accepted=accepted).messages[1:]
    assembly = editor.inspect_exchange(prepared, reply(prepared), inputs, accepted)
    assert assembly.report == req.report.replace(prior.BEFORE, prior.AFTER)
    context = assembly.journal['review_source_context']
    assert context['accepted_review'] == accepted.model_dump(mode='json')
    assert [x['source_id'] for x in context['review_sources'][0]['selected_sources']] == [31, 32]
    assert not context['proves_edit_support'] and not context['editor_selected_sources']
    assert all('selected_sources' not in op and 'source_ids' not in op for op in assembly.journal['operations'])
    assert not assembly.journal['semantic_approval'] and assembly.journal['full_final_review_required']
    final = editor.Current.make_request(report_inputs(inputs, assembly.report))
    assert final.messages[1].content.find(prior.AFTER) >= 0


def test_same_block_multiple_issues_and_cross_block_changes_have_no_invented_issue_mapping():
    _, inputs, accepted, _ = prior.cases()['claim-scope:4']
    duplicate = accepted.issues[0].model_copy(update={'explanation': 'Synthetic second issue on same block'})
    accepted = accepted.model_copy(update={'issues': [*accepted.issues, duplicate]})
    prepared = editor.edit_request(inputs, accepted)
    op = operation()
    # A host-authored cross-block edit checks expressibility, not its necessity.
    cross = dict(block=6, before='补刀稳定', after='补刀数值相近', reason='Synthetic cross-block check')
    assembly = editor.inspect_exchange(prepared, reply(prepared, [op, cross]), inputs, accepted)
    assert len(assembly.journal['review_source_context']['review_sources']) == 2
    assert len(assembly.journal['operations']) == 2
    assert all('issue_id' not in x for x in assembly.journal['operations'])
    assert not assembly.journal['semantic_approval']


@pytest.mark.parametrize('fault', ['source_ids', 'issue_ids', 'overlap', 'anchor', 'block',
    'citation', 'policy', 'accepted', 'source', 'receipt', 'tool', 'model', 'temperature', 'metadata'])
def test_bad_protocol_identity_and_input_cannot_be_repaired_or_applied(fault):
    _, inputs, accepted, _ = prior.cases()['claim-scope:4']
    prepared = editor.edit_request(inputs, accepted)
    op = operation()
    if fault in ('source_ids', 'issue_ids'): op[fault] = [31]
    if fault == 'anchor': op['before'] = 'NOT IN ORIGINAL'
    if fault == 'block': op['block'] = 64
    if fault == 'citation': op['after'] += ' [K9999]'
    if fault == 'policy': op['after'] += ' ' + prepared.messages[0].content.splitlines()[0]
    ex = reply(prepared, [op, op] if fault == 'overlap' else [op])
    if fault == 'accepted': accepted = accepted.model_copy(update={'score': 81})
    if fault == 'source': inputs = replace(inputs, data_json=inputs.data_json.replace('869.5', '999.5'))
    if fault == 'receipt': ex = replace(ex, receipt_request_sha256='0'*64)
    if fault == 'tool': ex = prior.exchange(prepared)
    if fault == 'model': ex = replace(ex, response=replace(ex.response, model='glm-5.3'))
    if fault in ('temperature', 'metadata'):
        issued = replace(prepared, **({'temperature': 0.15} if fault == 'temperature' else
            {'metadata': {**prepared.metadata, 'unauthorized': 'added'}}))
        ex = reply(issued)
    with pytest.raises(ValueError): editor.inspect_exchange(prepared, ex, inputs, accepted)


def test_unknown_review_source_rejected_before_request_and_empty_edit_is_not_resolution():
    _, inputs, accepted, _ = prior.cases()['claim-scope:4']
    bad = accepted.model_copy(update={'issues': [accepted.issues[0].model_copy(update={'source_ids': [9999]})]})
    with pytest.raises(ValueError): editor.edit_request(inputs, bad)
    prepared = editor.edit_request(inputs, accepted)
    assembly = editor.inspect_exchange(prepared, reply(prepared, []), inputs, accepted)
    assert assembly.report == inputs.source.report and not assembly.journal['semantic_approval']
    good, inputs, accepted, _ = prior.cases()['claim-scope:1']
    prepared = editor.edit_request(inputs, accepted)
    assert editor.inspect_exchange(prepared, reply(prepared, []), inputs, accepted).report == good.report


def setup_flow(monkeypatch, *, fault=None):
    original_exchange = prior.exchange
    op = operation()
    monkeypatch.setattr(prior, 'operation', lambda: deepcopy(op))
    def adapted(request, **kwargs):
        kwargs.setdefault('name', editor.TOOL)
        return original_exchange(request, **kwargs)
    monkeypatch.setattr(prior, 'exchange', adapted)
    monkeypatch.setattr(prior.editor, 'CoarseRevisionWorkflow', editor.ReviewBoundRevisionWorkflow)
    return prior.setup_flow(monkeypatch, fault=fault)


def test_five_call_existing_workflow_binds_exact_full_fresh_and_forbids_second_edit(monkeypatch):
    req, flow, budget, router, revision, recorded, reviews = setup_flow(monkeypatch)
    draft = flow.revise(revision)
    final = flow.evaluate(replace(req, report=draft.report))
    assert final.verdict.value == 'pass'
    assert budget.calls == 5 and budget.tokens <= 401920
    assert [x['role'] for x in router.attempts] == ['generation', 'generation', 'review', 'revision', 'review']
    assert reviews[-1].messages == editor.Current.make_request(flow._expected_recheck).messages
    assert draft.report == flow.last_edit_journal['assembled_report']
    assert not flow.last_edit_journal['semantic_approval']
    with pytest.raises(ValueError): flow.revise(revision)


def test_wrong_new_fact_is_not_certified_and_full_fresh_can_reject(monkeypatch):
    req, flow, budget, router, revision, _, reviews = setup_flow(monkeypatch)
    base_op = prior.operation()
    base_op['after'] = '辅助局视野分为 999，故能保证今后获胜。'
    monkeypatch.setattr(prior, 'operation', lambda: deepcopy(base_op))
    # A strict source-valid final review rejecting the new statement; synthetic,
    # deliberately supplied by the test, not a claim about actual GLM detection.
    raw = json.loads(prior.cases()['claim-scope:4'][3])
    raw['verdict'] = 'fail'; raw['score'] = 40
    raw['issues'][0]['explanation'] = 'Synthetic final: 999 and guaranteed future wins unsupported'
    reviewer = router.reviewer
    def reject(request):
        reviews.append(request)
        ex = prior.exchange(request, name='submit_report_review')
        call = replace(ex.response.tool_calls[0], arguments=raw)
        response = replace(ex.response, model='glm-5.3', tool_calls=(call,))
        reviewer.last_exchange = replace(ex, response=response)
        return response
    monkeypatch.setattr(reviewer, 'chat', reject)
    draft = flow.revise(revision)
    assert '999' in draft.report
    assert not flow.last_edit_journal['review_source_context']['proves_edit_support']
    assert flow.evaluate(replace(req, report=draft.report)).verdict.value == 'fail'
    assert flow.stopped and budget.calls == 5


@pytest.mark.parametrize('fault', ['policy', 'tool', 'tokens', 'changed_source', 'changed_fresh'])
def test_failures_stop_without_another_request(monkeypatch, fault):
    req, flow, budget, _, revision, recorded, _ = setup_flow(monkeypatch, fault=fault)
    if fault == 'tokens': budget.tokens = 401920
    if fault == 'changed_source': revision = replace(revision, report=revision.report+' changed')
    if fault == 'changed_fresh':
        draft = flow.revise(revision)
        with pytest.raises(ValueError): flow.evaluate(replace(req, report=draft.report+' changed'))
    else:
        error = ProviderResponseError if fault == 'tokens' else ValueError
        with pytest.raises(error): flow.revise(revision)
    calls = budget.calls
    assert calls == (3 if fault in ('tokens', 'changed_source') else 4)
    assert flow.stopped
    with pytest.raises(ValueError): flow.revise(replace(revision, report=req.report))
    assert budget.calls == calls


def test_closed_failed_requests_cannot_be_reinterpreted_under_new_tool():
    _, inputs, accepted, _ = prior.cases()['claim-scope:4']
    old = prior.editor.inline_edit_request(inputs, accepted)
    with pytest.raises(ValueError, match='input_changed'):
        editor.inspect_exchange(old, prior.exchange(old), inputs, accepted)
    # Original strict protocol continues to reject the actual missing field.
    fixture = json.loads((prior.Path('tests/fixtures/coarse_edit_missing_sources_response_20261001.json')).read_bytes())
    ex = prior.exchange(old, edits=fixture['tool_calls'][0]['arguments']['edits'])
    with pytest.raises(ValueError):
        prior.editor.inspect_edit_exchange(old, ex, inputs, accepted, inline_schema=True)
