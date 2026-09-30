"""Native-schema fixtures are offline evidence, not independent authors."""
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace

import pytest

from scripts import codex_review_event_source as host
from scripts import review_independence_contract as contract
from tests.test_review_independence_contract import _binding


def fixture():
    bound = _binding()
    plan = contract.freeze_v2_identity(dict(host_review_submission_mode=contract.MODE_V2),
        root_thread_id='root', primary_id='root', independent_id='child')
    review = dict(accepted=True, defects=[], source_review='Offline source assessment')
    thread = dict(id='child', parentThreadId='root',
        source=dict(subAgent=dict(thread_spawn=dict(parent_thread_id='root', depth=1))))
    turn = dict(id='turn-1', status='completed', itemsView='full', error=None, items=[
        dict(id='dispatch-1', type='userMessage', content=[dict(type='text',
            text=host.review_task(bound, 'Inspect the complete provided source.'))]),
        dict(id='final-1', type='agentMessage', phase='final_answer',
            text=json.dumps(dict(binding=bound, review=review))),
    ])
    requests = []
    def request(method, params):
        requests.append((method, deepcopy(params)))
        assert params['threadId'] == 'child'
        if method == 'thread/read':
            return dict(thread=deepcopy(thread))
        assert method == 'thread/turns/list' and params['itemsView'] == 'full'
        return dict(data=[deepcopy(turn)], nextCursor=None)
    return SimpleNamespace(bound=bound, plan=plan, thread=thread, turn=turn, review=review,
        client=SimpleNamespace(request=request), requests=requests)


def fetch(f):
    return host.CodexHostReviewEventSource(f.client, f.plan).fetch(
        event_id='child/turn-1/final-1', binding=f.bound)


def test_native_adapter_derives_dispatch_author_review_and_raw_digest():
    f = fixture()
    event = fetch(f)
    assert event['dispatch_id'] == 'dispatch-1'
    assert event['author_principal_id'] == 'child'
    assert event['review'] == f.review
    assert event['raw_event_sha256'] == hashlib.sha256(contract.canonical_json(
        dict(thread=f.thread, turn=f.turn))).hexdigest()
    source = host.CodexHostReviewEventSource(f.client, f.plan)
    review = dict(f.review, independent_source_event=event)
    contract.validate_independent_event(review, plan=f.plan, bound=f.bound, event_source=source)
    f.thread.update(status={'type': 'idle'}, updatedAt=123)
    assert fetch(f) == event  # Mutable thread metadata is outside the immutable proof.
    f.turn['items'][1]['text'] += ' '
    with pytest.raises(ValueError, match='event_envelope_mismatch'):
        contract.validate_independent_event(review, plan=f.plan, bound=f.bound, event_source=source)


@pytest.mark.parametrize('mutation,error', [
    (lambda f: f.thread.update(id='root'), 'parent_or_author_mismatch'),
    (lambda f: f.thread.update(parentThreadId='unrelated'), 'parent_or_author_mismatch'),
    (lambda f: f.thread.update(source='vscode'), 'parent_or_author_mismatch'),
    (lambda f: f.turn.update(status='failed'), 'turn_not_completed_full'),
    (lambda f: f.turn.update(status='interrupted'), 'turn_not_completed_full'),
    (lambda f: f.turn.update(itemsView='summary'), 'turn_not_completed_full'),
    (lambda f: f.turn['items'][1].update(phase='commentary'), 'dispatch_or_final_ambiguous'),
    (lambda f: f.turn['items'].reverse(), 'dispatch_order'),
    (lambda f: f.turn['items'][0]['content'][0].update(text='Unbound old task'), 'review_json_required'),
    (lambda f: f.turn['items'][0]['content'][0].update(text=host.review_task(dict(f.bound, stage='initial'), 'Wrong stage')), 'dispatch_or_answer_binding'),
    (lambda f: f.turn['items'][1].update(text=json.dumps(dict(binding=dict(f.bound, request_sha256='f'*64), review=f.review))), 'dispatch_or_answer_binding'),
    (lambda f: f.turn['items'][1].update(text=json.dumps(dict(binding=f.bound, review=dict(f.review, independent_source_event={})))), 'review_body_invalid'),
])
def test_native_adapter_rejects_wrong_author_incomplete_or_crossbound_history(mutation, error):
    f = fixture()
    mutation(f)
    with pytest.raises(ValueError, match=error):
        fetch(f)


def test_native_adapter_uses_bounded_pagination_and_rejects_missing_events():
    f = fixture()
    request = f.client.request
    def paginated(method, params):
        if method == 'thread/turns/list' and 'cursor' not in params:
            return dict(data=[], nextCursor='older')
        return request(method, params)
    f.client.request = paginated
    assert fetch(f)['review'] == f.review
    f.client.request = lambda method, params: (dict(thread=f.thread) if method == 'thread/read'
        else dict(data=[], nextCursor='repeated'))
    with pytest.raises(ValueError, match='pagination_loop'):
        fetch(f)


def test_reader_forbids_execution_methods_before_starting_any_process(tmp_path):
    executable = tmp_path/'not-launched.exe'
    executable.touch()
    reader = host.CodexReadOnlyClient(executable)
    for method in ('turn/start', 'thread/start', 'thread/resume', 'thread/fork'):
        with pytest.raises(ValueError, match='method_not_read_only'):
            reader.request(method, {})
    assert reader.process is None


def test_reader_timeout_and_host_errors_fail_closed(tmp_path):
    executable = tmp_path/'not-launched.exe'
    executable.touch()
    reader = host.CodexReadOnlyClient(executable, timeout_seconds=.01)
    from io import StringIO
    reader.process = SimpleNamespace(poll=lambda: None, stdin=StringIO())
    with pytest.raises(ValueError, match='request_timeout'):
        reader.request('thread/read', {})
    reader.messages.put(dict(id=2, error=dict(message='Unavailable')))
    with pytest.raises(ValueError, match='request_failed'):
        reader.request('thread/read', {})


def native_rollout_fixture(tmp_path):
    f = fixture()
    sessions = tmp_path/'sessions'
    sessions.mkdir()
    executable = tmp_path/'unused.exe'
    executable.touch()
    reader = host.CodexReadOnlyClient(executable, session_root=sessions)
    reader.request = f.client.request
    f.reader = reader
    f.client.read_collaboration_dispatch = reader.read_collaboration_dispatch
    spawn = f.thread['source']['subAgent']['thread_spawn']
    spawn['agent_path'] = '/root/reviewer'
    dispatch = f.turn['items'].pop(0)
    final = f.turn['items'][0]
    f.path = sessions/'native.jsonl'
    f.thread['path'] = str(f.path)
    f.records = [
        dict(type='session_meta', payload=dict(id='child', parent_thread_id='root',
            agent_path='/root/reviewer', source=dict(subagent=dict(thread_spawn=deepcopy(spawn))))),
        dict(type='response_item', timestamp='2026-09-29T15:00:00Z', payload=dict(
            type='agent_message', id='actual-dispatch', author='/root', recipient='/root/reviewer',
            internal_chat_message_metadata_passthrough=dict(turn_id='turn-1'),
            content=[dict(type='input_text', text=chr(10).join([
                'Message Type: NEW_TASK', 'Task name: /root/reviewer', 'Sender: /root',
                'Payload:', dispatch['content'][0]['text']]))])),
        dict(type='response_item', payload=dict(type='message', id=final['id'], role='assistant',
            phase='final_answer', internal_chat_message_metadata_passthrough=dict(turn_id='turn-1'),
            content=[dict(type='output_text', text=final['text'])])),
    ]
    f.save = lambda: f.path.write_text(chr(10).join(json.dumps(v) for v in f.records), encoding='utf-8')
    f.save()
    return f


def test_native_rollout_supplies_omitted_agent_dispatch_with_same_final(tmp_path):
    f = native_rollout_fixture(tmp_path)
    event = fetch(f)
    assert event['dispatch_id'] == 'actual-dispatch' and event['review'] == f.review
    proof = f.client.read_collaboration_dispatch(f.thread, f.turn, f.turn['items'][0])
    assert event['raw_event_sha256'] == hashlib.sha256(contract.canonical_json(dict(
        thread={k: f.thread[k] for k in ('id','parentThreadId','source')},
        turn=f.turn, collaboration_dispatch=proof['raw']))).hexdigest()
    # Adding a later unrelated turn does not invalidate the completed event.
    f.records.append(dict(type='event_msg', payload=dict(type='task_started', turn_id='later')))
    f.save()
    assert fetch(f) == event


@pytest.mark.parametrize('fault', ['outside_host', 'wrong_session', 'wrong_parent', 'wrong_author',
    'wrong_recipient', 'wrong_turn', 'missing_dispatch', 'duplicate_dispatch', 'wrong_final',
    'dispatch_after_final', 'unbound_task'])
@pytest.mark.parametrize('policy', [contract.DISPATCH_POLICY, contract.FINAL_POLICY])
def test_native_rollout_rejects_untrusted_or_mismatched_dispatch(tmp_path, fault, policy):
    f = native_rollout_fixture(tmp_path)
    f.plan[contract.EVIDENCE_POLICY_FIELD] = policy
    if fault == 'outside_host':
        f.path = tmp_path/'run-event.jsonl'
        f.thread['path'] = str(f.path)
    elif fault == 'wrong_session':f.records[0]['payload']['id'] = 'other'
    elif fault == 'wrong_parent':f.records[0]['payload']['parent_thread_id'] = 'other'
    elif fault == 'wrong_author':f.records[1]['payload']['author'] = '/root/reviewer'
    elif fault == 'wrong_recipient':f.records[1]['payload']['recipient'] = '/root/other'
    elif fault == 'wrong_turn':f.records[1]['payload']['internal_chat_message_metadata_passthrough']['turn_id'] = 'other'
    elif fault == 'missing_dispatch':f.records.pop(1)
    elif fault == 'duplicate_dispatch':f.records.insert(1, deepcopy(f.records[1]))
    elif fault == 'wrong_final':f.records[2]['payload']['content'][0]['text'] = '{}'
    elif fault == 'dispatch_after_final':f.records[1],f.records[2] = f.records[2],f.records[1]
    elif fault == 'unbound_task':
        text = f.records[1]['payload']['content'][0]['text']
        f.records[1]['payload']['content'][0]['text'] = text.replace(f.bound['request_sha256'], 'f'*64)
    f.save()
    with pytest.raises(ValueError, match='codex_review_host_'):
        fetch(f)


def completed_item_fixture(tmp_path):
    f = native_rollout_fixture(tmp_path)
    f.records[2]['payload']['internal_chat_message_metadata_passthrough']['turn_id'] = 'private-transport-turn'
    f.records.append(dict(type='event_msg', payload=dict(type='item_completed',
        thread_id='child', turn_id='turn-1', item=dict(type='AgentMessage',
            id='final-1', phase='final_answer',
            content=[dict(type='Text', text=f.turn['items'][0]['text'])]))))
    f.save()
    return f


@pytest.mark.parametrize('completion_first', [True, False])
def test_native_completed_item_binds_private_transport_turn_to_api(tmp_path, completion_first):
    f = completed_item_fixture(tmp_path)
    completion = f.records[3]
    if completion_first:
        f.records[2], f.records[3] = f.records[3], f.records[2]
        f.save()
    event = fetch(f)
    assert event['review'] == f.review
    proof = f.client.read_collaboration_dispatch(f.thread, f.turn, f.turn['items'][0])
    assert proof['raw']['final_membership'] == completion
    source = host.CodexHostReviewEventSource(f.client, f.plan)
    contract.validate_independent_event(dict(f.review, independent_source_event=event),
        plan=f.plan, bound=f.bound, event_source=source)
    f.records.append(dict(type='event_msg', payload=dict(type='task_started', turn_id='later')))
    f.save()
    assert fetch(f) == event


@pytest.mark.parametrize('fault', ['missing', 'duplicate', 'wrong_thread', 'wrong_turn',
    'wrong_id', 'wrong_body', 'wrong_type', 'wrong_phase', 'wrong_content_type', 'before_dispatch'])
@pytest.mark.parametrize('policy', [contract.DISPATCH_POLICY, contract.FINAL_POLICY])
def test_native_completed_item_requires_exact_unique_membership(tmp_path, fault, policy):
    f = completed_item_fixture(tmp_path)
    f.plan[contract.EVIDENCE_POLICY_FIELD] = policy
    p = f.records[3]['payload']
    if fault == 'missing': f.records.pop()
    elif fault == 'duplicate': f.records.append(deepcopy(f.records[3]))
    elif fault == 'wrong_thread': p['thread_id'] = 'other'
    elif fault == 'wrong_turn': p['turn_id'] = 'other'
    elif fault == 'wrong_id': p['item']['id'] = 'other'
    elif fault == 'wrong_body': p['item']['content'][0]['text'] = '{}'
    elif fault == 'wrong_type': p['item']['type'] = 'UserMessage'
    elif fault == 'wrong_phase': p['item']['phase'] = 'commentary'
    elif fault == 'wrong_content_type': p['item']['content'][0]['type'] = 'Other'
    elif fault == 'before_dispatch': f.records.insert(1, f.records.pop(3))
    f.save()
    with pytest.raises(ValueError, match='codex_review_host_rollout_'):
        fetch(f)


def test_native_legacy_proof_digest_stays_stable_with_completed_projection(tmp_path):
    f = native_rollout_fixture(tmp_path)
    before = fetch(f)
    f.records.append(dict(type='event_msg', payload=dict(type='item_completed',
        thread_id='child', turn_id='turn-1', item=dict(type='AgentMessage',
            id='final-1', phase='final_answer',
            content=[dict(type='Text', text=f.turn['items'][0]['text'])]))))
    f.save()
    assert fetch(f) == before


def test_native_encrypted_dispatch_is_explicitly_unverifiable(tmp_path):
    f = completed_item_fixture(tmp_path)
    content = f.records[1]['payload']['content']
    content[0]['text'] = content[0]['text'].split('Payload:')[0] + 'Payload:' + chr(10)
    content.append(dict(type='encrypted_content', encrypted_content='opaque-host-payload'))
    # A correct local task and correct final are not evidence of the sent task.
    (tmp_path/'task.json').write_text(host.review_task(f.bound, 'local assertion'), encoding='utf-8')
    f.save()
    with pytest.raises(ValueError, match='codex_review_host_rollout_dispatch_encrypted'):
        fetch(f)


def test_latest_input_probe_accepts_plain_engineering_text_without_granting_review(tmp_path):
    f = native_rollout_fixture(tmp_path)
    content = f.records[1]['payload']['content'][0]
    content['text'] = content['text'].split('Payload:')[0] + 'Payload:\nCheck current host availability.'
    f.save()
    assert f.reader.check_latest_input(f.thread) == dict(thread_id='child', turn_id='turn-1',
        dispatch_id='actual-dispatch', current_input_readable=True, future_input_guaranteed=False)
    with pytest.raises(ValueError, match='rollout_task_json'):
        fetch(f)  # Readability alone is never a signed stage judgment.


@pytest.mark.parametrize('fault', ['encrypted', 'missing', 'duplicate', 'wrong_parent',
    'wrong_author', 'wrong_recipient', 'wrong_turn', 'outside_host', 'running', 'empty'])
def test_latest_input_probe_rejects_unreadable_or_unbound_current_input(tmp_path, fault):
    f = native_rollout_fixture(tmp_path)
    if fault == 'encrypted':
        f.records[1]['payload']['content'].append(dict(type='encrypted_content', encrypted_content='opaque'))
    elif fault == 'missing': f.records.pop(1)
    elif fault == 'duplicate': f.records.insert(1, deepcopy(f.records[1]))
    elif fault == 'wrong_parent': f.records[0]['payload']['parent_thread_id'] = 'other'
    elif fault == 'wrong_author': f.records[1]['payload']['author'] = '/root/reviewer'
    elif fault == 'wrong_recipient': f.records[1]['payload']['recipient'] = '/root/other'
    elif fault == 'wrong_turn':
        f.records[1]['payload']['internal_chat_message_metadata_passthrough']['turn_id'] = 'other'
    elif fault == 'outside_host': f.thread['path'] = str(tmp_path/'outside.jsonl')
    elif fault == 'running': f.turn['status'] = 'inProgress'
    elif fault == 'empty':
        f.records[1]['payload']['content'][0]['text'] = 'Message Type: NEW_TASK\nTask name: /root/reviewer\nSender: /root\nPayload:\n'
    f.save()
    with pytest.raises(ValueError, match='codex_review_host_'):
        f.reader.check_latest_input(f.thread)


@pytest.mark.parametrize('new_state', ['encrypted', 'missing', 'inProgress'])
def test_latest_input_probe_never_falls_back_to_an_old_readable_review(tmp_path, new_state):
    f = native_rollout_fixture(tmp_path)
    assert fetch(f)['review'] == f.review
    old_turn = deepcopy(f.turn)
    f.turn.update(id='turn-2', items=[])
    if new_state == 'inProgress': f.turn['status'] = 'inProgress'
    if new_state == 'encrypted':
        new = deepcopy(f.records[1])
        new['payload']['id'] = 'latest-dispatch'
        new['payload']['internal_chat_message_metadata_passthrough']['turn_id'] = 'turn-2'
        new['payload']['content'].append(dict(type='encrypted_content', encrypted_content='opaque'))
        f.records.append(new)
    f.save()
    queries = []
    def request(method, params):
        queries.append(params)
        return dict(data=[deepcopy(old_turn if params.get('cursor') else f.turn)], nextCursor='older')
    f.reader.request = request
    with pytest.raises(ValueError, match='codex_review_host_'):
        f.reader.check_latest_input(f.thread)
    assert len(queries) == 1 and queries[0]['limit'] == 1 and 'cursor' not in queries[0]


def test_latest_input_probe_supports_native_user_input_projection(tmp_path):
    f = fixture()
    executable = tmp_path/'unused.exe'
    executable.touch()
    reader = host.CodexReadOnlyClient(executable)
    reader.request = f.client.request
    assert reader.check_latest_input(f.thread)['dispatch_id'] == 'dispatch-1'
    f.turn['items'][0]['content'].append(dict(type='encrypted_content'))
    with pytest.raises(ValueError, match='dispatch_format'):
        reader.check_latest_input(f.thread)
