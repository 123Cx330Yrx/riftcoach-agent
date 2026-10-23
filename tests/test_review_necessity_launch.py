"""Real supervisor/SDK with mocked HTTP; fixture Host reviews certify no semantics."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import socket
import sys

import pytest

from app.evaluation.sol_natural_session import exclusive
from scripts import review_necessity_launch as launch
from scripts import reviewer_responses_process as process
from tests.test_reviewer_profile_batch import FakeGate, FixtureSource, tree


CHILD = '''
import json,socket
import httpx
from scripts import reviewer_responses_nonstream as codec, reviewer_responses_process as process
from scripts.review_necessity_candidate import PACKAGE
from tests.test_reviewer_responses_nonstream import response
def deny(*a,**k): raise AssertionError('network forbidden')
socket.socket = socket.create_connection = deny
review=json.loads((PACKAGE/'retained-public-review.json').read_text(encoding='utf-8'))
value=response(review)
value['reasoning']={'effort':EFFORT}
original=codec.collect
def collect(*a,**k):
    return original(*a,**k,transport=httpx.MockTransport(lambda request:
        httpx.Response(STATUS,stream=httpx.ByteStream(json.dumps(
            value if STATUS==200 else {'error':'timeout'}).encode()),headers={'content-type':'application/json'})))
codec.collect=collect
process.worker()
'''


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    def deny(*a, **k):
        raise AssertionError('network forbidden')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(launch, 'current_head', lambda: 'offline-head')
    monkeypatch.setattr(launch, 'source_identity', lambda: {'offline': True})
    monkeypatch.setattr(launch, 'historical_evidence', lambda: {'fixture_history': True})
    monkeypatch.chdir(launch.ROOT)
    monkeypatch.setattr(launch, 'hidden_key', lambda: 'OFFLINE_SECRET_SENTINEL')
    monkeypatch.setattr(launch, 'verify_ci', lambda ci, head: {'run': ci, 'head': head})
    monkeypatch.setattr(launch, 'verify_native_principals', lambda *a: {'fixture_only':True})

    class Connection:
        def __enter__(self): return self
        def __exit__(self, *a): pass
    monkeypatch.setattr(socket, 'create_connection', lambda *a, **k: Connection())
    source = FixtureSource()
    monkeypatch.setattr(launch, 'native_gate', lambda plan, client: FakeGate(plan, None, source))
    operator = tmp_path/'operator'
    root = launch.prepare(operator, primary='primary', independent='independent')
    assert root['status']['phase'] == 'needs_native_preflight'
    native = launch.native_task(operator, root['plan_sha256'], root['checkpoint_sha256'], None)
    source.decisions['fixture-preflight'] = {'accepted':True, 'fixture_only':True}
    root = launch.submit(operator, native['plan_sha256'], native['checkpoint_sha256'], None,
        {'accepted':True, 'fixture_only':True}, 'fixture-preflight')
    source.handles.clear()
    now = datetime.now(timezone.utc)
    grant = tmp_path/'authorization.json'
    value = dict(version=launch.VERSION+'-authorization', plan_sha256=root['plan_sha256'],
        limits=launch.LIMITS, profile=launch.asdict(launch.PROFILE), approved=True,
        account_group_confirmed='GPT-pro', price_cny_per_million={'input':'0.4','output':'2'},
        user_evidence='OFFLINE FIXTURE ONLY; not real consent',
        issued_at=(now-timedelta(minutes=1)).isoformat(), expires_at=(now+timedelta(hours=1)).isoformat())
    process.write_json(grant, value)
    modes = []
    def sender(business, **kwargs):
        status, effort = modes.pop(0)
        return process.run_once(business, **kwargs, command=[sys.executable, '-c',
            f'STATUS={status}\nEFFORT={effort!r}\n'+CHILD])
    monkeypatch.setattr(launch, 'run_once', sender)
    return operator, root, grant, source, modes


def send(prepared, root=None, *, retry=False):
    operator, initial, grant, _, _ = prepared
    root = root or initial
    return launch.send(operator, root['plan_sha256'], root['checkpoint_sha256'],
        grant, launch.sha(grant), 'offline-ci', None, retry=retry)


def submit(prepared, root, *, accepted=True):
    operator, _, _, source, _ = prepared
    decision = dict(accepted=accepted, fixture_only=True)
    source.decisions['fixture-event-'+root['checkpoint_sha256']] = decision
    return launch.submit(operator, root['plan_sha256'], root['checkpoint_sha256'], None,
        decision, 'fixture-event-'+root['checkpoint_sha256'])


def test_three_reviews_resume_and_strict_seal(prepared):
    operator, root, _, source, modes = prepared
    for case in launch.candidate.CASES:
        modes.append((200, 'high'))
        sent = send(prepared, root)
        assert sent['status']['phase'] == 'awaiting_review'
        assert sent['status']['unreviewed_calls'] == 1
        material = process.read_json(Path(source.handles[-1]['folder'])/'material.json')
        assert material['report'] == launch.candidate.materials()[case].source.report
        assert 'evaluation.json' not in json.dumps(material)
        with pytest.raises(ValueError, match='not_ready'):
            send(prepared, sent)
        root = submit(prepared, sent)
    assert root['status']['phase'] == 'complete' and root['status']['attempts'] == 3
    assert root['status']['unknown_reserved_tokens'] == 0
    assert not root['status']['qualified'] and not root['status']['publication_allowed']
    closure = launch.seal(operator, root['plan_sha256'], root['checkpoint_sha256'], None)
    before = tree(operator)
    assert launch.replay(operator, root['plan_sha256'], root['checkpoint_sha256'],
        closure['seal_sha256'], None)['readonly']
    assert tree(operator) == before
    assert 'OFFLINE_SECRET_SENTINEL' not in ''.join(p.read_text(encoding='utf-8')
        for p in operator.rglob('*.json'))
    with pytest.raises(ValueError):
        launch.seal(operator, root['plan_sha256'], root['checkpoint_sha256'], None)
    (operator/'extra.json').write_text('{}', encoding='utf-8')
    with pytest.raises(ValueError, match='sealed_inventory'):
        launch.replay(operator, root['plan_sha256'], root['checkpoint_sha256'], closure['seal_sha256'], None)


def test_timeout_keeps_previous_review_retry_is_explicit_and_once(prepared):
    operator, root, _, _, modes = prepared
    modes.append((200,'high'))
    root = submit(prepared, send(prepared, root))
    first = tree(operator/'attempts/01-a')
    modes.append((524,'high'))
    root = send(prepared, root)
    assert root['status']['phase'] == 'retry_available'
    assert root['status']['known_tokens'] > 0 and root['status']['unknown_reserved_tokens'] == 80384
    assert tree(operator/'attempts/01-a') == first
    with pytest.raises(ValueError, match='explicit_retry'):
        send(prepared, root)
    modes.append((200,'high'))
    root = submit(prepared, send(prepared, root, retry=True))
    assert root['status']['next_case'] == 'c'
    modes.append((524,'high'))
    root = send(prepared, root)
    assert root['status']['phase'] == 'stopped' and root['status']['reason'] == 'retry_budget_exhausted'
    assert root['status']['attempts'] == 4 and root['status']['unknown_reserved_tokens'] == 160768
    assert tree(operator/'attempts/01-a') == first
    with pytest.raises(ValueError, match='not_ready'):
        send(prepared, root, retry=True)


@pytest.mark.parametrize('effort,accepted,reason', [('high',False,'semantic_rejection'),
    ('max',True,'identity_conflict_diagnostic_only')])
def test_semantic_or_identity_failure_retains_opinion_without_rebuy(prepared, effort, accepted, reason):
    operator, root, _, source, modes = prepared
    modes.append((200,effort))
    root = send(prepared, root)
    assert root['status']['phase'] == 'awaiting_review'
    material = process.read_json(Path(source.handles[-1]['folder'])/'material.json')
    assert material['transport_accepted'] is (effort == 'high')
    root = submit(prepared, root, accepted=accepted)
    assert root['status']['phase'] == 'stopped' and root['status']['reason'] == reason
    assert (operator/'attempts/01-a/call/worker-result.json').exists()
    with pytest.raises(ValueError, match='not_ready'):
        send(prepared, root, retry=True)


def test_key_cancel_before_claim_and_exclusive_execution(prepared, monkeypatch):
    operator, root, _, _, modes = prepared
    before = tree(operator)
    def cancel(): raise KeyboardInterrupt
    monkeypatch.setattr(launch, 'hidden_key', cancel)
    with pytest.raises(KeyboardInterrupt): send(prepared)
    assert tree(operator) == before
    with exclusive(operator.with_name(operator.name+'.lock')):
        with pytest.raises(ValueError, match='executor_active'): send(prepared)
    assert not list((operator/'attempts').iterdir())


@pytest.mark.parametrize('fault', ['expired','old_scope','source','python','contaminated'])
def test_preflight_rejects_before_key(prepared, monkeypatch, fault):
    operator, root, grant, _, _ = prepared
    if fault in ('expired','old_scope'):
        value = process.read_json(grant)
        if fault == 'old_scope': value['plan_sha256'] = '0'*64
        else: value['expires_at'] = value['issued_at']
        grant.write_bytes(launch.candidate.encode(value))
    elif fault == 'source': monkeypatch.setattr(launch, 'source_identity', lambda: {'changed':True})
    elif fault == 'python': monkeypatch.setattr(sys, 'executable', str(operator/'wrong.exe'))
    else: (operator/'unexpected.json').write_text('{}', encoding='utf-8')
    monkeypatch.setattr(launch, 'hidden_key', lambda: pytest.fail('unexpected key prompt'))
    with pytest.raises(ValueError): send(prepared)
    assert not list((operator/'attempts').iterdir())


def test_waiting_for_key_does_not_start_worker_but_expiry_is_rechecked(prepared, monkeypatch):
    operator, _, grant, _, _ = prepared
    before = tree(operator)
    def expire():
        value = process.read_json(grant)
        value['expires_at'] = value['issued_at']
        grant.write_bytes(launch.candidate.encode(value))
        return 'OFFLINE_SECRET_SENTINEL'
    monkeypatch.setattr(launch, 'hidden_key', expire)
    with pytest.raises(ValueError, match='authorization'):
        send(prepared)
    assert tree(operator) == before


def test_completed_receipt_after_interruption_is_reconciled_never_resent(prepared, monkeypatch):
    operator, root, _, _, modes = prepared
    modes.append((200,'high'))
    original = launch.finish_pending
    def interrupt(*a,**k): raise KeyboardInterrupt
    monkeypatch.setattr(launch, 'finish_pending', interrupt)
    with pytest.raises(KeyboardInterrupt): send(prepared)
    checkpoints = sorted((operator/'checkpoints').iterdir())
    claim_pin = launch.sha(checkpoints[-1])  # fixture substitutes captured stdout, not live evidence
    assert process.read_json(checkpoints[-1])['state']['phase'] == 'in_flight'
    with pytest.raises(ValueError): send(prepared, dict(root,checkpoint_sha256=claim_pin))
    monkeypatch.setattr(launch, 'finish_pending', original)
    reconciled = original(operator, root['plan_sha256'], claim_pin, None)
    assert reconciled['status']['phase'] == 'awaiting_review' and not modes
    assert len(list((operator/'attempts').iterdir())) == 1


def test_missing_observation_never_creates_business_review_or_second_send(prepared, monkeypatch):
    operator, root, _, source, modes = prepared
    real = launch.run_once
    def broken(*a,**k):
        receipt = real(*a,**k)
        path = k['directory']/'observation/observation.json'
        obs = process.read_json(path)
        obs['closed'] = False
        path.write_bytes(launch.candidate.encode(obs))
        return receipt
    monkeypatch.setattr(launch, 'run_once', broken)
    modes.append((200,'high'))
    root = send(prepared)
    assert root['status']['phase'] == 'stopped' and not source.handles
    assert root['status']['known_tokens'] > 0
    with pytest.raises(ValueError, match='not_ready'): send(prepared, root)


def test_source_inventory_does_not_open_untracked_probe(monkeypatch):
    # Enforce the real unrelated-file boundary while enumerating tracked source.
    original = Path.read_bytes
    def guarded(path):
        assert path.name != 'reviewer_responses_nonstream_probe.py'
        return original(path)
    monkeypatch.setattr(Path, 'read_bytes', guarded)
    assert 'scripts/reviewer_responses_nonstream_probe.py' not in launch.source_identity()['files']


def test_native_preflight_is_mandatory_and_cannot_be_redelivered(prepared, monkeypatch):
    operator, _, grant, source, _ = prepared
    other = operator.with_name('unreviewed-proposal')
    root = launch.prepare(other, primary='primary', independent='independent')
    monkeypatch.setattr(launch, 'hidden_key', lambda: pytest.fail('key before native preflight'))
    with pytest.raises(ValueError, match='not_ready'):
        launch.send(other, root['plan_sha256'], root['checkpoint_sha256'], grant,
                    launch.sha(grant), 'offline-ci', None)
    task = launch.native_task(other, root['plan_sha256'], root['checkpoint_sha256'], None)
    with pytest.raises(ValueError, match='preflight_already_dispatched'):
        launch.native_task(other, task['plan_sha256'], task['checkpoint_sha256'], None)
    source.decisions['rejected-preflight'] = {'accepted':False, 'fixture_only':True}
    result = launch.submit(other, task['plan_sha256'], task['checkpoint_sha256'], None,
        {'accepted':False, 'fixture_only':True}, 'rejected-preflight')
    assert result['status']['phase'] == 'stopped'
    assert result['status']['attempts'] == 0
