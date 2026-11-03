"""Policy delivery binds original bytes; it never adjudicates their meaning."""
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.codex_review_event_source import review_task
from scripts import document_review_host_task as host


def raw(policy):
    return json.dumps({'messages': [{'role': 'system', 'content': policy},
        {'role': 'user', 'content': 'Untrusted report data, not a policy.'}]},
        ensure_ascii=False).encode()


def bound(request, stage='initial'):
    return dict(plan_sha256='a'*64, key='scope:3', stage=stage,
        response_sha256='b'*64, report_sha256='c'*64,
        request_sha256=hashlib.sha256(request).hexdigest())


def reference(task):
    value = json.loads(task)
    text = value['instructions'].split('BEGIN VERIFIED BUSINESS-POLICY REFERENCE\n', 1)[1]
    return json.loads(text.split('\nEND VERIFIED BUSINESS-POLICY REFERENCE', 1)[0])


@pytest.mark.parametrize('stage', ['initial', 'final'])
def test_current_complete_policy_and_original_envelope_preserved(stage):
    # Use the actual complete business policy, including output obligations.
    from app.evaluation.golden_role_boundary_examples import review_policy
    policy = review_policy()
    request = raw(policy)
    original = review_task(bound(request, stage), 'Keep complete source review and native envelope.')
    delivered = host.with_policies(original, request)
    assert json.loads(delivered)['binding'] == json.loads(original)['binding']
    assert json.loads(delivered)['kind'] == json.loads(original)['kind']
    assert json.loads(delivered)['instructions'].startswith(json.loads(original)['instructions'])
    item, = reference(delivered)['policies']
    assert item['policy_text'] == policy
    assert item['policy_sha256'] == hashlib.sha256(policy.encode()).hexdigest()
    assert item['request_sha256'] == bound(request)['request_sha256']


def test_revision_gets_review_and_editor_policies_without_substituting_either():
    initial, edit = raw('Actual initial review policy'), raw('Actual editor policy')
    task = review_task(bound(edit, 'revision'), 'Review complete edited report.')
    delivered = host.with_policies(task, edit, initial_raw=initial,
        initial_sha256=hashlib.sha256(initial).hexdigest())
    assert [(p['applies_to'], p['policy_text']) for p in reference(delivered)['policies']] == [
        ('initial_review', 'Actual initial review policy'), ('revision', 'Actual editor policy')]
    assert json.loads(delivered)['binding'] == bound(edit, 'revision')


@pytest.mark.parametrize('fault', ['changed_current', 'changed_initial', 'missing_initial', 'unexpected_initial'])
def test_wrong_or_missing_request_policy_is_rejected(fault):
    initial, edit = raw('Initial'), raw('Editor')
    stage = 'initial' if fault == 'unexpected_initial' else 'revision'
    task = review_task(bound(edit, stage), 'Full review.')
    kwargs = dict(initial_raw=initial, initial_sha256=hashlib.sha256(initial).hexdigest())
    if fault == 'changed_current': edit = raw('Changed')
    if fault == 'changed_initial': kwargs['initial_raw'] = raw('Changed')
    if fault == 'missing_initial': kwargs = {}
    with pytest.raises(ValueError, match='host_policy_'):
        host.with_policies(task, edit, **kwargs)


@pytest.mark.parametrize('messages', [[], [{'role': 'user', 'content': 'Impostor'}],
    [{'role': 'system', 'content': ''}],
    [{'role': 'system', 'content': 'One'}, {'role': 'system', 'content': 'Two'}]])
def test_missing_empty_or_ambiguous_policy_is_rejected(messages):
    request = json.dumps(dict(messages=messages)).encode()
    with pytest.raises(ValueError, match='host_policy_system_message'):
        host.with_policies(review_task(bound(request), 'Full review.'), request)


def test_scan_adapter_delivers_the_verified_issued_policy(tmp_path):
    request = raw('Scan actual policy')
    arm = tmp_path/'scope-3'
    arm.mkdir()
    (arm/'issued-request.json').write_bytes(request)
    original = review_task(bound(request), 'Existing complete scan instructions.')
    with patch('scripts.document_review_scan_handoff.task', return_value=original) as validate:
        task = host.scan_task(tmp_path, 'scope:3')
    validate.assert_called_once_with(tmp_path, 'scope:3')
    assert reference(task)['policies'][0]['policy_text'] == 'Scan actual policy'


@pytest.mark.parametrize('profile', ['scan', 'document-review'])
def test_closed_batches_cannot_receive_new_live_tasks(tmp_path, profile):
    (tmp_path/'result.json').write_text('{}', encoding='utf-8')
    with pytest.raises(ValueError, match='closed'):
        if profile == 'scan': host.scan_task(tmp_path, 'scope:3')
        else: host.original_task(tmp_path, 'scope:3', 'initial')


@pytest.mark.parametrize('stage,expected,report_required,fault', [
    ('initial', 'reject', False, None), ('initial', 'accept', True, None),
    ('revision', 'reject', True, None), ('final', 'reject', True, None),
    ('revision', 'reject', True, 'changed_prefix'),
    ('initial', 'accept', True, 'closed_stage')])
def test_original_adapter_preserves_stage_assessment_requirements(tmp_path, stage, expected, report_required, fault):
    from scripts.diagnose_role_context import canonical_sha
    initial = raw('Review policy')
    request = raw('Editor policy') if stage == 'revision' else initial
    current = dict(bound(request, stage), input_sha256='d'*64, stage_sha256='e'*64,
        source_file_sha256='f'*64, provider_response_sha256='1'*64, expected_initial=expected,
        receipt_prefix_sha256=canonical_sha(['receipt1', 'receipt2']))
    if stage != 'revision': current['final_input_sha256'] = '2'*64
    arm = tmp_path/'scope-3'
    arm.mkdir()
    transport = tmp_path/'transport'/'scope-3'
    (transport/'review').mkdir(parents=True)
    (transport/'generation').mkdir()
    (transport/'review'/'request-001.json').write_bytes(initial)
    ordinal = host.STAGES.index(stage)+1
    folder = 'generation' if stage == 'revision' else 'review'
    (transport/folder/f'request-{ordinal:03d}.json').write_bytes(request)
    calls = [dict(binding=dict(request_sha256=hashlib.sha256(initial).hexdigest()), artifact_sha256='receipt1'),
        dict(binding={}, artifact_sha256='receipt2')]
    if fault == 'changed_prefix':
        calls[0]['artifact_sha256'] = 'changed-receipt'
    if fault == 'closed_stage':
        (arm/'decision-initial.json').write_text('{}', encoding='utf-8')
    with patch('scripts.role_stage_review_drafts.binding', return_value=current) as validate, \
            patch('app.evaluation.document_review_qualification.read_calls', return_value=calls):
        if fault:
            error = 'receipt_prefix_changed' if fault == 'changed_prefix' else 'stage_closed'
            with pytest.raises(ValueError, match=error):
                host.original_task(tmp_path, 'scope:3', stage)
            return
        task = host.original_task(tmp_path, 'scope:3', stage)
    validate.assert_called_once_with(tmp_path, 'scope:3', stage, profile='document-review', live=True)
    result = json.loads(task)
    assert result['binding'] == bound(request, stage)
    assert ('Include final_report with' in result['instructions']) == report_required
    assert ('Set final_report=null' in result['instructions']) != report_required
    assert current['stage_sha256'] in result['instructions']
    assert reference(task)['policies'][-1]['request_sha256'] == current['request_sha256']


def test_wrong_task_shape_cannot_be_turned_into_native_review():
    request = raw('Policy')
    value = json.loads(review_task(bound(request), 'Full review.'))
    value['kind'] = 'offline-calibration'
    with pytest.raises(ValueError, match='host_policy_base_task'):
        host.with_policies(json.dumps(value), request)
