"""A final attestation is an explicit proof policy, not legacy fail-open."""
from copy import deepcopy
import json

import pytest

from scripts import codex_review_event_source as host
from scripts import review_independence_contract as contract
from scripts import run_boundary_examples_v2 as entry
from tests.test_codex_review_event_source import completed_item_fixture, fetch


def opaque_fixture(tmp_path):
    f = completed_item_fixture(tmp_path)
    f.plan[contract.EVIDENCE_POLICY_FIELD] = contract.FINAL_POLICY
    content = f.records[1]['payload']['content']
    content[0]['text'] = content[0]['text'].split('Payload:')[0] + 'Payload:\n'
    content.append(dict(type='encrypted_content', encrypted_content='opaque-host-body'))
    f.save()
    return f


def update_final(f, answer):
    text = json.dumps(answer)
    f.turn['items'][0]['text'] = text
    f.records[2]['payload']['content'][0]['text'] = text
    f.records[3]['payload']['item']['content'][0]['text'] = text
    f.save()


def test_opaque_route_and_real_final_validate_only_with_frozen_policy(tmp_path):
    f = opaque_fixture(tmp_path)
    event = fetch(f)
    assert event[contract.EVIDENCE_POLICY_FIELD] == contract.FINAL_POLICY
    source = host.CodexHostReviewEventSource(f.client, f.plan)
    review = dict(f.review, independent_source_event=event)
    contract.validate_independent_event(review, plan=f.plan, bound=f.bound, event_source=source)
    f.plan.pop(contract.EVIDENCE_POLICY_FIELD)
    with pytest.raises(ValueError, match='dispatch_encrypted'):
        fetch(f)
    # An envelope cannot opt an unchanged legacy plan into new semantics.
    with pytest.raises(ValueError, match='event_evidence_policy_mismatch'):
        contract.validate_independent_event(review, plan=f.plan, bound=f.bound, event=event)


@pytest.mark.parametrize('field', ['plan_sha256', 'key', 'stage', 'response_sha256',
    'report_sha256', 'request_sha256'])
def test_opaque_final_cannot_substitute_any_bound_input(tmp_path, field):
    f = opaque_fixture(tmp_path)
    answer = json.loads(f.turn['items'][0]['text'])
    answer['binding'][field] = 'wrong'
    update_final(f, answer)
    with pytest.raises(ValueError, match='dispatch_or_answer_binding'):
        fetch(f)


@pytest.mark.parametrize('visible', ['conflict', 'null', 'partial'])
def test_visible_dispatch_conflicts_are_not_hidden_by_encrypted_suffix(tmp_path, visible):
    f = opaque_fixture(tmp_path)
    if visible == 'conflict':
        other = deepcopy(f.bound)
        other['request_sha256'] = 'f' * 64
        text = host.review_task(other, 'Conflicting task')
    else:
        text = 'null' if visible == 'null' else '{"binding":'
    f.records[1]['payload']['content'][0]['text'] += text
    f.save()
    with pytest.raises(ValueError, match='dispatch_or_answer_binding|rollout_task_json'):
        fetch(f)


def test_plain_null_task_is_not_mistaken_for_an_opaque_dispatch(tmp_path):
    f = opaque_fixture(tmp_path)
    content = f.records[1]['payload']['content']
    content.pop()
    content[0]['text'] += 'null'
    f.save()
    with pytest.raises(ValueError, match='rollout_task_json'):
        fetch(f)


@pytest.mark.parametrize('fault', ['empty_ciphertext', 'extra_segment', 'missing_route',
    'wrong_author', 'duplicate_dispatch', 'no_final', 'multiple_finals', 'incomplete'])
def test_new_policy_still_requires_real_route_and_unique_completion(tmp_path, fault):
    f = opaque_fixture(tmp_path)
    if fault == 'empty_ciphertext': f.records[1]['payload']['content'][1]['encrypted_content'] = ''
    elif fault == 'extra_segment': f.records[1]['payload']['content'].append(dict(type='input_text', text='extra'))
    elif fault == 'missing_route': f.records.pop(1)
    elif fault == 'wrong_author': f.records[1]['payload']['author'] = '/root/reviewer'
    elif fault == 'duplicate_dispatch': f.records.insert(1, deepcopy(f.records[1]))
    elif fault == 'no_final': f.turn['items'] = []
    elif fault == 'multiple_finals': f.turn['items'].append(deepcopy(f.turn['items'][0]))
    elif fault == 'incomplete': f.turn['status'] = 'inProgress'
    f.save()
    with pytest.raises(ValueError, match='codex_review_host_'):
        fetch(f)
    with pytest.raises(ValueError, match='codex_review_host_'):
        f.reader.check_latest_input(f.thread, evidence_policy=contract.FINAL_POLICY)


def test_readback_is_stable_but_changed_review_cannot_replace_saved_event(tmp_path):
    f = opaque_fixture(tmp_path)
    event = fetch(f)
    source = host.CodexHostReviewEventSource(f.client, f.plan)
    review = dict(f.review, independent_source_event=event)
    f.records.append(dict(type='event_msg', payload=dict(type='task_started', turn_id='unrelated')))
    f.save()
    assert fetch(f) == event
    answer = json.loads(f.turn['items'][0]['text'])
    answer['review']['accepted'] = False
    update_final(f, answer)
    with pytest.raises(ValueError, match='event_envelope_mismatch'):
        contract.validate_independent_event(review, plan=f.plan, bound=f.bound, event_source=source)


def test_preflight_checks_native_route_and_final_without_granting_review(tmp_path):
    f = opaque_fixture(tmp_path)
    result = f.reader.check_latest_input(f.thread, evidence_policy=contract.FINAL_POLICY)
    assert result['current_route_and_final_available'] is True
    assert result['current_input_readable'] is False
    assert result['future_input_guaranteed'] is False
    update_final(f, {'ordinary_engineering_reply': True})
    assert f.reader.check_latest_input(f.thread, evidence_policy=contract.FINAL_POLICY)
    with pytest.raises(ValueError, match='dispatch_or_answer_binding'):
        fetch(f)


def test_unknown_policy_cannot_be_frozen_or_read(tmp_path):
    f = opaque_fixture(tmp_path)
    f.plan[contract.EVIDENCE_POLICY_FIELD] = 'unknown'
    with pytest.raises(ValueError, match='evidence_policy_unadopted'):
        fetch(f)
    with pytest.raises(ValueError, match='evidence_policy_unadopted'):
        contract.freeze_v2_identity(f.plan, root_thread_id='root', primary_id='root', independent_id='child')


def test_both_entrypoints_select_frozen_evidence_policy_before_execution():
    seen = []
    class Client:
        def request(self, method, params):
            return dict(thread=dict(id=params['threadId'], parentThreadId='root',
                source={'subAgent': {'thread_spawn': {'parent_thread_id': 'root', 'agent_path': '/root/child'}}}))
        def check_latest_input(self, thread, *, evidence_policy):
            seen.append(evidence_policy)
            return {'current_route_and_final_available': True}
    plan = contract.freeze_v2_identity(dict(host_review_submission_mode=contract.MODE_V2,
        host_review_evidence_policy=contract.FINAL_POLICY), root_thread_id='root',
        primary_id='root', independent_id='child')
    from scripts.run_boundary_examples_v2_continuation import verify_native_principals
    for verify in (entry.verify_native_principals, verify_native_principals):
        assert verify(Client(), plan)['verified'] is True
    assert seen == [contract.FINAL_POLICY] * 2


def test_new_preparation_freezes_policy_without_changing_product_requests():
    args = dict(root_thread_id='root', independent_thread_id='child', experiment='new-proof-policy')
    old, old_requests = entry.prepare(**args)
    new, new_requests = entry.prepare(**args, host_review_evidence_policy=contract.FINAL_POLICY)
    assert contract.EVIDENCE_POLICY_FIELD not in old
    assert new[contract.EVIDENCE_POLICY_FIELD] == contract.FINAL_POLICY
    assert old['identity'] == new['identity'] and old_requests == new_requests
    assert entry.runner.canonical_sha(old) != entry.runner.canonical_sha(new)
