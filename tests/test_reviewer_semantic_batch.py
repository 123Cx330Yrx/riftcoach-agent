"""Offline six-slot integration. Fixture decisions are not semantic evidence."""
from copy import deepcopy
from pathlib import Path
import json
import socket
import sys

import pytest
from scripts import reviewer_profile_batch as batch_module
from scripts import reviewer_responses_process as process
from scripts import reviewer_responses_nonstream as codec
from scripts import prepare_reviewer_semantic_screen as material
from scripts.reviewer_responses_transport import Profile
from tests.test_reviewer_profile_batch import FixtureSource, FakeGate, approve, load

CHILD = """
import json, socket, runpy
import httpx
from scripts import reviewer_responses_nonstream as codec
from scripts import reviewer_responses_process as process
fixture = runpy.run_path('tests/test_reviewer_responses_nonstream.py')
value = fixture['response']()
def forbidden(*args, **kwargs): raise AssertionError('offline child attempted network')
socket.socket = socket.create_connection = forbidden
original = codec.collect
def offline_collect(*args, **kwargs):
    from scripts import prepare_reviewer_semantic_screen as material
    reference = json.loads((material.PACKAGE / 'evaluation.json').read_bytes())
    key = next(p.stem for p in (material.PACKAGE / 'requests').glob('*.json')
               if json.loads(p.read_bytes()) == args[0])
    case, duty = key.split('-')
    value = fixture['response'](reference['synthetic_reference_reviews'][case][duty])
    return original(*args, **kwargs, transport=httpx.MockTransport(lambda request: httpx.Response(200,
        stream=httpx.ByteStream(json.dumps(value).encode()), headers={'content-type':'application/json'})))
codec.collect = offline_collect
process.worker()
"""

@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs): raise AssertionError('offline test attempted network')
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)


def prepare(tmp_path):
    return batch_module.prepare(tmp_path / 'operator', group='GPT-pro', primary='primary-test',
        independent='independent-test', route='proxy-12000', version=batch_module.SEMANTIC_VERSION)


def sender(business, **kwargs):
    return process.run_once(business, api_key='OFFLINE_SENTINEL', command=[sys.executable, '-c', CHILD], **kwargs)


def test_six_actual_workers_gated_and_replayed(tmp_path):
    plan = prepare(tmp_path)
    source = FixtureSource()
    batch = batch_module.ScreenBatch.create(plan, source, gate_factory=FakeGate)
    for key in plan['keys']:
        assert batch.status()['next_key'] == key
        result = batch.send_next(sender)
        assert result['phase'] == 'awaiting_review'
        with pytest.raises(ValueError, match='batch_not_ready'):
            batch.send_next(sender)
        # Explicit fake acceptance of human reference outputs; no quality claim.
        approve(batch, source)
        if key.endswith('-completion'):
            assert batch.status()['phase'] == 'awaiting_pair_review'
            with pytest.raises(ValueError, match='batch_not_ready'):
                batch.send_next(sender)
            preview = process.read_json(Path(source.handles[-1]['folder']) / 'material.json')
            assert source.handles[-1]['binding']['stage'] == 'revision'
            assert source.handles[-1]['binding']['report_sha256'] == material.sha(preview['assembled_report'].encode('utf-8'))
            assert preview['assembled_report'] == (material.PACKAGE / 's01.md').read_text(encoding='utf-8')
            approve_pair(batch, source)
        batch = load(batch.operator, batch.checkpoint_sha, source)
    result = batch.status()
    assert result['phase'] == 'closed' and result['calls'] == 6
    assert result['unused_slots'] == 0 and result['known_tokens'] == 120
    assert result['fixture_only'] and not result['qualified']
    assert all(row['response_mode'] == codec.MODE for row in
        [process.read_json(p) for p in batch.operator.glob('calls/*/receipt.json')])
    with pytest.raises(ValueError, match='batch_not_ready'):
        batch.send_next(sender)


@pytest.mark.parametrize('kind', ['cancel', 'lost', 'reject'])
def test_stop_never_refills_slot(tmp_path, kind):
    source = FixtureSource()
    batch = batch_module.ScreenBatch.create(prepare(tmp_path), source, gate_factory=FakeGate)
    def stopped(business, **kwargs):
        if kind == 'lost': raise RuntimeError('PRIVATE_SENTINEL')
        return process.run_once(business, api_key='OFFLINE_SENTINEL', cancel=lambda: True, **kwargs)
    result = batch.send_next(sender if kind == 'reject' else stopped)
    if kind == 'reject': result = approve(batch, source, accepted=False)
    assert result['phase'] == 'closed' and result['unused_slots'] == 5
    assert result['unknown_reserved_tokens'] == (80384 if kind == 'lost' else 0)
    assert result['not_sent'] == (1 if kind == 'cancel' else 0)
    reopened = load(batch.operator, batch.checkpoint_sha, source)
    with pytest.raises(ValueError, match='batch_not_ready'):
        reopened.send_next(sender)


@pytest.mark.parametrize('key', ['s01-facts', 's01-completion', 's02-facts', 's02-completion', 's03-facts', 's03-completion'])
def test_binding_is_mode_specific_and_rejects_modified_input(key):
    business = process.read_json(material.PACKAGE / 'requests' / (key + '.json'))
    process.screen_validator(business, response_mode=codec.MODE)
    with pytest.raises(ValueError): process.screen_validator(business)
    changed = deepcopy(business)
    changed['messages'][1]['content'] += ' changed'
    with pytest.raises(ValueError): process.screen_validator(changed, response_mode=codec.MODE)


def test_contract_and_budget_cannot_be_expanded(tmp_path):
    plan = prepare(tmp_path)
    assert plan['budget']['total_tokens'] == 482304
    assert plan['budget']['supervisor_seconds'] == 1800
    assert plan['budget']['output_per_request'] == 16384
    plan['budget']['max_requests'] = 7
    with pytest.raises(ValueError, match='batch_plan_contract'):
        batch_module.ScreenBatch.create(plan, FixtureSource(), gate_factory=FakeGate)
    assert not (tmp_path / 'operator').exists()
    with pytest.raises(ValueError, match='batch_semantic_route'):
        batch_module.prepare(tmp_path / 'bad', group='GPT-pro', primary='primary-test',
            independent='independent-test', version=batch_module.SEMANTIC_VERSION)


def approve_pair(batch, source, accepted=True):
    event_id = 'fixture-pair-' + str(len(source.decisions))
    source.decisions[event_id] = dict(accepted=accepted, fixture_only=True)
    return batch.submit_pair_review(dict(accepted=accepted, fixture_only=True), event_id)


def test_pair_rejection_closes_before_next_case(tmp_path):
    source = FixtureSource()
    batch = batch_module.ScreenBatch.create(prepare(tmp_path), source, gate_factory=FakeGate)
    for _ in range(2):
        batch.send_next(sender)
        approve(batch, source)
    result = approve_pair(batch, source, accepted=False)
    assert result['phase'] == 'closed' and result['reason'] == 'pair_semantic_rejection'
    assert result['calls'] == 2 and result['unused_slots'] == 4
    with pytest.raises(ValueError, match='batch_not_ready'): batch.send_next(sender)


def test_nonstream_missing_observation_closes(tmp_path):
    source = FixtureSource()
    batch = batch_module.ScreenBatch.create(prepare(tmp_path), source, gate_factory=FakeGate)
    def missing(*args, **kwargs):
        receipt = sender(*args, **kwargs)
        path = kwargs['directory'] / 'observation/observation.json'
        value = process.read_json(path)
        value.pop('response_contract')
        path.write_text(json.dumps(value), encoding='utf-8')
        return receipt
    result = batch.send_next(missing)
    assert result['phase'] == 'closed' and result['reason'] == 'call_nonstream_observation_invalid'
    assert result['known_tokens'] == 20


def test_pair_uses_real_gate_schema_author_bytes_and_replay(tmp_path):
    from tests.test_reviewer_profile_native import NativeClientFixture, author_fixture
    from scripts.codex_review_event_source import CodexHostReviewEventSource
    from scripts import host_review_task_checkpoint as checkpoint
    plan = batch_module.prepare(tmp_path / 'operator', group='GPT-pro', primary='root',
        independent='child', route='proxy-12000', version=batch_module.SEMANTIC_VERSION)
    client = NativeClientFixture()
    source = CodexHostReviewEventSource(client, plan)
    batch = batch_module.ScreenBatch.create(plan, source)
    for _ in range(2):
        batch.send_next(sender, before_send=lambda: None)  # Offline preflight fixture only.
        primary, event, _ = author_fixture(batch, client)
        batch.submit_review(primary, event)
    handle = batch.state['records'][-1]['pair_handle']
    assessment = dict(report_sha256=handle['binding']['report_sha256'], reviewer='child',
        source_review='OFFLINE FIXTURE ONLY', facts_and_sources_correct=True,
        correct_content_preserved=True, identity_and_goal_preserved=True, true_errors_fixed=True)
    decision = dict(kind='edit', reviewer='child', material_sha256=handle['material_sha256'],
        source_review='OFFLINE FIXTURE ONLY', accepted=True, defects=[], compatibility=None,
        actual_report_checked=True, report_assessment=assessment)
    body = dict(binding=handle['binding'], review=dict(binding=handle['binding'], decision=decision))
    raw = json.dumps(body, ensure_ascii=False, indent=2).encode('utf-8')
    folder = Path(handle['folder'])
    answer = batch.workspace.answer_path(folder / 'task-checkpoint.json', handle['checkpoint_sha256'])
    answer.write_bytes(raw)
    checkpoint.check_answer(folder / 'task-checkpoint.json', handle['checkpoint_sha256'], raw)
    client.turns.append(dict(id='pair-turn', status='completed', itemsView='full', error=None, items=[
        dict(id='pair-dispatch', type='userMessage', content=[dict(type='text',
            text=(folder / 'independent-task.json').read_text(encoding='utf-8'))]),
        dict(id='pair-final', type='agentMessage', phase='final_answer', text=raw.decode('utf-8'))]))
    primary = dict(decision, reviewer='root', report_assessment=dict(assessment, reviewer='root'))
    assert batch.submit_pair_review(primary, 'child/pair-turn/pair-final')['next_key'] == 's02-facts'
    assert batch_module.ScreenBatch.load(batch.operator, batch.checkpoint_sha, source).status()['phase'] == 'ready'
    answer.write_bytes(raw + b' ')
    with pytest.raises(ValueError): batch.status()
