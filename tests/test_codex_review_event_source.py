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
