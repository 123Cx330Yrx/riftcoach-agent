"""Actual controller/NativeGate/worker wiring with offline native/HTTP fixtures.

No model calls or genuine native author judgments are produced by these tests.
"""
from copy import deepcopy
import json
import socket
import sys

import pytest

from scripts import host_review_task_checkpoint as checkpoint
from scripts import reviewer_profile_batch as batch_module
from scripts.codex_review_event_source import CodexHostReviewEventSource
from scripts.reviewer_responses_process import run_once
from tests.test_reviewer_profile_batch import Sender, tree


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('native engineering fixture attempted network')
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)


class NativeClientFixture:
    def __init__(self):
        self.turns = []
        self.thread = dict(id='child', parentThreadId='root',
            source=dict(subAgent=dict(thread_spawn=dict(parent_thread_id='root', depth=1))))

    def request(self, method, params):
        assert params['threadId'] == 'child'
        if method == 'thread/read':
            return dict(thread=deepcopy(self.thread))
        assert method == 'thread/turns/list' and params['itemsView'] == 'full'
        return dict(data=deepcopy(self.turns), nextCursor=None)


@pytest.fixture
def native_batch(tmp_path):
    plan = batch_module.prepare(tmp_path / 'operator', group='GPT-pro', primary='root', independent='child')
    client = NativeClientFixture()
    source = CodexHostReviewEventSource(client, plan)
    batch = batch_module.ScreenBatch.create(plan, source)
    return batch, client, source


def author_fixture(batch, client, *, trailing=b'', accepted=True):
    handle = batch.state['records'][-1]['handle']
    decision = dict(kind='opinion', reviewer='child', material_sha256=handle['material_sha256'],
        source_review='OFFLINE NATIVE-SCHEMA FIXTURE. Not a real semantic judgment.',
        accepted=accepted, defects=[] if accepted else [dict(kind='missed_error', detail='fixture')],
        compatibility=None, actual_report_checked=True, report_assessment=None)
    body = dict(binding=handle['binding'], review=dict(binding=handle['binding'], decision=decision))
    raw = json.dumps(body, ensure_ascii=False, indent=2).encode('utf-8')
    folder = batch_module.Path(handle['folder'])
    answer = batch.workspace.answer_path(folder / 'task-checkpoint.json', handle['checkpoint_sha256'])
    answer.write_bytes(raw + trailing)
    checkpoint.check_answer(folder / 'task-checkpoint.json', handle['checkpoint_sha256'], answer.read_bytes())
    n = len(client.turns) + 1
    client.turns.append(dict(id=f'turn-{n}', status='completed', itemsView='full', error=None, items=[
        dict(id=f'dispatch-{n}', type='userMessage', content=[dict(type='text',
            text=(folder / 'independent-task.json').read_text(encoding='utf-8'))]),
        dict(id=f'final-{n}', type='agentMessage', phase='final_answer', text=raw.decode('utf-8'))]))
    return dict(decision, reviewer='root'), f'child/turn-{n}/final-{n}', answer


def test_default_controller_requires_explicit_preflight_before_sender(native_batch):
    batch, _, _ = native_batch
    sender = Sender()
    with pytest.raises(ValueError, match='live_preflight_required'):
        batch.send_next(sender)
    assert not sender.calls and batch.status()['calls'] == 0


def test_actual_native_gate_author_checkpoint_import_and_readonly_replay(native_batch):
    batch, client, source = native_batch
    batch.send_next(Sender(), before_send=lambda: None)  # Offline preflight fixture.
    primary, event_id, _ = author_fixture(batch, client)
    result = batch.submit_review(primary, event_id)
    assert result['phase'] == 'ready' and result['next_key'] == 'r01-completion'
    assert result['qualified'] is result['publication_allowed'] is False
    before = tree(batch.operator)
    restored = batch_module.ScreenBatch.load(batch.operator, batch.checkpoint_sha, source)
    assert restored.status() == result
    assert tree(batch.operator) == before


def test_equal_json_with_extra_author_lf_is_rejected_and_preserved(native_batch):
    batch, client, _ = native_batch
    batch.send_next(Sender(), before_send=lambda: None)
    primary, event_id, answer = author_fixture(batch, client, trailing=b'\n')
    original = answer.read_bytes()
    with pytest.raises(ValueError, match='review_import_failed'):
        batch.submit_review(primary, event_id)
    assert batch.status()['phase'] == 'closed'
    assert answer.read_bytes() == original
    assert not (batch_module.Path(batch.state['records'][0]['handle']['folder']) / 'submission.json').exists()
    with pytest.raises(ValueError):
        batch.send_next(Sender(), before_send=lambda: None)


@pytest.mark.parametrize('damage', ['author', 'parent', 'final', 'incomplete'])
def test_native_and_author_rechecked_before_next_send_and_seal(native_batch, damage):
    batch, client, source = native_batch
    sender = Sender()
    batch.send_next(sender, before_send=lambda: None)
    primary, event_id, answer = author_fixture(batch, client)
    batch.submit_review(primary, event_id)
    if damage == 'author':
        answer.write_bytes(answer.read_bytes() + b'\n')
    elif damage == 'parent':
        client.thread['parentThreadId'] = 'unrelated'
    elif damage == 'final':
        client.turns[0]['items'][-1]['text'] += ' '
    else:
        client.turns[0]['status'] = 'in_progress'
    before = tree(batch.operator)
    for operation in (lambda: batch.send_next(sender, before_send=lambda: None), batch.close,
                      lambda: batch_module.ScreenBatch.load(batch.operator, batch.checkpoint_sha, source)):
        with pytest.raises(ValueError):
            operation()
    assert len(sender.calls) == 1 and tree(batch.operator) == before


def test_actual_worker_sdk_supervisor_batch_and_native_import_are_connected(native_batch):
    batch, client, _ = native_batch
    code = '''
import runpy, socket
import httpx
from scripts import reviewer_responses_process as process
from scripts.reviewer_responses_transport import collect
fixture = runpy.run_path('tests/test_reviewer_responses_transport.py')
def forbidden(*args, **kwargs):
    raise AssertionError('offline child attempted network')
socket.socket = socket.create_connection = forbidden
def handler(request):
    return httpx.Response(200, stream=fixture['Bytes'](fixture['events']()),
        headers={'content-type': 'text/event-stream'})
def offline_collect(*args, **kwargs):
    return collect(*args, **kwargs, transport=httpx.MockTransport(handler))
process.collect = offline_collect
process.worker()
'''
    def sender(business, *, profile, directory, timeout_s):
        return run_once(business, profile=profile, directory=directory, timeout_s=timeout_s,
                        api_key='OFFLINE_ONLY', command=[sys.executable, '-c', code])
    result = batch.send_next(sender, before_send=lambda: None)
    assert result['phase'] == 'awaiting_review' and result['known_tokens'] == 195
    primary, event_id, _ = author_fixture(batch, client)
    assert batch.submit_review(primary, event_id)['phase'] == 'ready'
    assert batch.close()['reason'] == 'operator_stop'
    saved = ''.join(p.read_text(encoding='utf-8') for p in batch.operator.rglob('*.json'))
    assert 'OFFLINE_ONLY' not in saved and 'PRIVATE_REASONING_SENTINEL_DO_NOT_RETAIN' not in saved


def test_sender_cannot_launder_prior_artifact_change_into_new_checkpoint(native_batch):
    batch, client, _ = native_batch
    sender = Sender()
    batch.send_next(sender, before_send=lambda: None)
    primary, event_id, _ = author_fixture(batch, client)
    batch.submit_review(primary, event_id)
    receipt_path = sender.calls[0][1] / 'receipt.json'
    def corrupting(*args, **kwargs):
        receipt_path.write_bytes(receipt_path.read_bytes() + b' ')
        return sender(*args, **kwargs)
    with pytest.raises(ValueError, match='evidence_changed_during_operation'):
        batch.send_next(corrupting, before_send=lambda: None)
    with pytest.raises(ValueError):
        batch.status()
    assert len(sender.calls) == 2


@pytest.mark.parametrize('field', ['budget', 'rows', 'execution_authorized'])
def test_proposal_edits_cannot_change_fixed_contract(tmp_path, field):
    plan = batch_module.prepare(tmp_path / 'operator', group='GPT-pro', primary='root', independent='child')
    if field == 'budget':
        plan['budget']['max_requests'] = 5
    elif field == 'rows':
        plan['rows'][0]['report_sha256'] = '0' * 64
    else:
        plan[field] = True
    with pytest.raises(ValueError, match='batch_plan_contract'):
        batch_module.ScreenBatch.create(plan, CodexHostReviewEventSource(NativeClientFixture(), plan))
    assert not (tmp_path / 'operator').exists()


def test_author_change_during_last_import_prevents_seal(native_batch, monkeypatch):
    batch, client, _ = native_batch
    batch.send_next(Sender(), before_send=lambda: None)
    primary, event_id, first = author_fixture(batch, client)
    batch.submit_review(primary, event_id)
    batch.send_next(Sender(), before_send=lambda: None)
    primary, event_id, _ = author_fixture(batch, client, accepted=False)
    original = batch.gate.submit
    def corrupt_after_import(*args, **kwargs):
        accepted = original(*args, **kwargs)
        first.write_bytes(first.read_bytes() + b'\n')
        return accepted
    monkeypatch.setattr(batch.gate, 'submit', corrupt_after_import)
    with pytest.raises(ValueError):
        batch.submit_review(primary, event_id)
    assert not (batch.operator / 'seal.json').exists()
    with pytest.raises(ValueError):
        batch.send_next(Sender(), before_send=lambda: None)
